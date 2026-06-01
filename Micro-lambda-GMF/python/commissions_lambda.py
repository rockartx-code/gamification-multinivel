import json
import base64
import boto3
from datetime import datetime, timezone
import core_utils as utils # Importado desde la Lambda Layer

# --- CONSTANTES ---
# Plan abril 2026: 5 generaciones (Gen1..Gen5) con compresión dinámica.
MAX_COMMISSION_LEVELS = 5
# Profundidad máxima de ancestros a recorrer al comprimir (saltar no calificados).
MAX_COMPRESSION_DEPTH = 50
PK_MONTH = "COMMISSION_MONTH"
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

# Cliente S3
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)

# --- HELPERS DEL MOTOR MLM ---

def _get_upline_chain(buyer_id):
    """Busca los patrocinadores hacia arriba en la red."""
    return utils._get_customer_upline_ids(buyer_id, MAX_COMMISSION_LEVELS)

def _get_ledger_month(beneficiary_id, month_key):
    """Obtiene o inicializa el registro contable mensual del socio."""
    sk = f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"
    res = utils._table.get_item(Key={"PK": PK_MONTH, "SK": sk})
    item = res.get("Item")
    
    if not item:
        item = {
            "PK": PK_MONTH, "SK": sk, "entityType": "commissionMonth",
            "beneficiaryId": beneficiary_id, "monthKey": month_key,
            "ledger": [], "totalPending": utils.D_ZERO, 
            "totalConfirmed": utils.D_ZERO, "totalBlocked": utils.D_ZERO,
            "status": "IN_PROGRESS", "createdAt": utils._now_iso()
        }
    return item

def _save_ledger_month(item):
    """Recalcula totales y persiste el mes contable."""
    tp, tc, tb = utils.D_ZERO, utils.D_ZERO, utils.D_ZERO
    for r in item.get("ledger", []):
        amt = utils._to_decimal(r.get("amount"))
        st = r.get("status")
        if st == "confirmed": tc += amt
        elif st == "blocked": tb += amt
        else: tp += amt

    item.update({"totalPending": tp, "totalConfirmed": tc, "totalBlocked": tb, "updatedAt": utils._now_iso()})
    utils._table.put_item(Item=item)

# --- MOTOR VP / VG ---

def _mxn_to_vp(net_mxn: float, mxn_per_vp: float) -> float:
    """Convierte MXN netos a puntos VP (fallback cuando no hay vpPoints por producto)."""
    return net_mxn / mxn_per_vp if mxn_per_vp > 0 else 0.0

def _state_to_vp(state: dict, mxn_per_vp: float) -> float:
    """Lee VP de un ASSOCIATE_MONTH: usa netVP si existe, si no convierte netVolume."""
    if state is None:
        return 0.0
    if "netVP" in state:
        return float(utils._to_decimal(state.get("netVP", 0)))
    return _mxn_to_vp(float(utils._to_decimal(state.get("netVolume", 0))), mxn_per_vp)

def _calc_vp(customer_id: str, month_key: str, mxn_per_vp: float) -> float:
    """Volumen Personal: compras propias del mes expresadas en VP."""
    state = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(customer_id, month_key))
    return _state_to_vp(state, mxn_per_vp)

def _compute_order_vp(order: dict, mxn_per_vp: float) -> float:
    """
    Calcula los puntos VP que genera una orden.
    - Si el ítem tiene vpPoints configurado (copiado del catálogo al crear la orden),
      se usan directamente: vpPoints * qty.
    - Si no, se calcula desde el precio: price * qty / mxn_per_vp.
    - Solo ítems comisionables contribuyen.
    - Se aplica el descuento proporcional de la orden al total de VP.
    """
    items = order.get("items") or []
    gross_subtotal = float(utils._to_decimal(order.get("grossSubtotal", 0)))
    net_total      = float(utils._to_decimal(order.get("netTotal", gross_subtotal or 0)))

    # Factor de descuento (1.0 = sin descuento)
    if gross_subtotal > 0:
        discount_factor = net_total / gross_subtotal
    else:
        raw_rate = float(utils._to_decimal(order.get("discountRate", 0)))
        discount_factor = 1.0 - raw_rate

    raw_vp = 0.0
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("commissionable") is False:
            continue
        qty = float(utils._to_decimal(it.get("quantity", 1)))
        vp_pts = it.get("vpPoints")
        if vp_pts is not None:
            raw_vp += float(utils._to_decimal(vp_pts)) * qty
        else:
            price = float(utils._to_decimal(it.get("price", 0)))
            raw_vp += (price * qty / mxn_per_vp) if mxn_per_vp > 0 else 0.0

    return raw_vp * discount_factor

def _get_direct_reports(customer_id: str) -> list:
    """IDs de los referidos directos (nivel 1)."""
    customer = utils._get_by_id("CUSTOMER", customer_id)
    if customer and "directReferralIds" in customer:
        return utils._customer_id_list(customer.get("directReferralIds"))

    all_customers = utils._query_bucket("CUSTOMER")
    return [
        str(c.get("customerId") or c.get("id", ""))
        for c in all_customers
        if str(c.get("leaderId", "")) == str(customer_id)
    ]


def _load_network_customers(customer_id: str) -> list:
    customer = utils._get_by_id("CUSTOMER", customer_id)
    if not customer:
        return []

    has_persisted_descendants = "networkDescendantIds" in customer
    descendant_ids = utils._customer_id_list(customer.get("networkDescendantIds"))
    if not has_persisted_descendants:
        return utils._query_bucket("CUSTOMER")

    scoped = [customer]
    seen = {str(customer.get("customerId") or "")}
    for descendant_id in descendant_ids:
        if descendant_id in seen:
            continue
        item = utils._get_by_id("CUSTOMER", utils._customer_entity_id(descendant_id))
        if not item:
            continue
        scoped.append(item)
        seen.add(descendant_id)
    return scoped

def _calc_vg(customer_id: str, month_key: str, mxn_per_vp: float, max_levels: int = 5) -> float:
    """Volumen de Grupo: VP propio + VP de toda la red hasta max_levels niveles."""
    all_customers = _load_network_customers(customer_id)
    id_map = {str(c.get("customerId") or c.get("id", "")): c for c in all_customers}

    visited: set = set()
    queue: list = [(str(customer_id), 0)]
    total_vp = 0.0

    while queue:
        cid, depth = queue.pop(0)
        if cid in visited or depth > max_levels:
            continue
        visited.add(cid)
        state = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, month_key))
        total_vp += _state_to_vp(state, mxn_per_vp)
        if depth < max_levels:
            for sid, c in id_map.items():
                if str(c.get("leaderId", "")) == cid and sid not in visited:
                    queue.append((sid, depth + 1))

    return total_vp

def _get_rank(vg: float, rank_thresholds: list) -> str:
    """Determina el rango del asociado por VG (gate simple, retrocompatibilidad)."""
    rank = ""
    for rt in sorted(rank_thresholds, key=lambda x: float(x.get("vgMin", 0))):
        if vg >= float(rt.get("vgMin", 0)):
            rank = rt.get("rank", "")
    return rank

def _network_descendant_ids(customer_id: str, max_levels: int) -> list:
    """IDs de toda la descendencia (sin incluirse) hasta `max_levels` niveles."""
    all_customers = _load_network_customers(customer_id)
    id_map = {str(c.get("customerId") or c.get("id", "")): c for c in all_customers}
    visited: set = set()
    queue: list = [(str(customer_id), 0)]
    result: list = []
    while queue:
        cid, depth = queue.pop(0)
        if cid in visited or depth > max_levels:
            continue
        visited.add(cid)
        if depth > 0:
            result.append(cid)
        if depth < max_levels:
            for sid, c in id_map.items():
                if str(c.get("leaderId", "")) == cid and sid not in visited:
                    queue.append((sid, depth + 1))
    return result

def _compute_rank(customer_id: str, month_key: str, vp: float, vg: float,
                  mxn_per_vp: float, max_levels: int, rank_thresholds: list) -> str:
    """
    Rango con gating completo del Plan abril 2026 §6: VG mín., PC personal mín. (vpMin),
    líneas calificadas (minLines × pcMinPerLine) y `requiredLeaders` (N líderes del rango
    inferior `requiredLeaderRank` en la red, evaluado recursivamente).

    Usa memoización por cliente y un guard de ciclos: durante el cálculo del rango de un
    cliente, este se considera provisionalmente "sin rango" para evitar recursión infinita.
    """
    tiers = sorted(rank_thresholds, key=lambda x: float(x.get("vgMin", 0)))
    rank_index = {str(rt.get("rank", "")): i for i, rt in enumerate(tiers)}
    memo: dict = {}

    def rank_at(cid: str, known_vp=None, known_vg=None) -> str:
        cid = str(cid)
        if cid in memo:
            return memo[cid]
        memo[cid] = ""  # guard de ciclos
        cvp = known_vp if known_vp is not None else _calc_vp(cid, month_key, mxn_per_vp)
        cvg = known_vg if known_vg is not None else _calc_vg(cid, month_key, mxn_per_vp, max_levels)

        achieved = ""
        for rt in tiers:
            if cvg < float(rt.get("vgMin", 0) or 0):
                continue
            if cvp < float(rt.get("vpMin", 0) or 0):
                continue
            min_lines   = int(rt.get("minLines", 0) or 0)
            pc_per_line = float(rt.get("pcMinPerLine", 0) or 0)
            if min_lines > 0 and _count_qualifying_lines(cid, month_key, mxn_per_vp, max_levels, pc_per_line) < min_lines:
                continue

            req_leaders = int(rt.get("requiredLeaders", 0) or 0)
            req_rank    = str(rt.get("requiredLeaderRank", "") or "")
            if req_leaders > 0 and req_rank:
                needed_idx = rank_index.get(req_rank, -1)
                if needed_idx >= 0:
                    count = 0
                    for did in _network_descendant_ids(cid, max_levels):
                        if rank_index.get(rank_at(did), -1) >= needed_idx:
                            count += 1
                            if count >= req_leaders:
                                break
                    if count < req_leaders:
                        continue
            achieved = str(rt.get("rank", ""))
        memo[cid] = achieved
        return achieved

    return rank_at(customer_id, vp, vg)

def _is_active(customer_id: str, month_key: str, mxn_per_vp: float, activation_vp: float) -> bool:
    """Activo = acumuló al menos `activation_vp` PC netos personales en el mes (Plan §3)."""
    return _calc_vp(customer_id, month_key, mxn_per_vp) >= activation_vp

def _count_active_directs(customer_id: str, month_key: str, mxn_per_vp: float, activation_vp: float) -> int:
    """Número de referidos directos activos en el mes."""
    return sum(
        1 for d in _get_direct_reports(customer_id)
        if _is_active(d, month_key, mxn_per_vp, activation_vp)
    )

def _count_qualifying_lines(customer_id: str, month_key: str, mxn_per_vp: float,
                            max_levels: int, pc_per_line: float) -> int:
    """
    Número de líneas (cada directo + su descendencia) cuyo VG de línea alcanza `pc_per_line`.
    Una "línea" es la subred que cuelga de un directo, incluyéndolo.
    """
    if pc_per_line <= 0:
        return len(_get_direct_reports(customer_id))
    count = 0
    for d in _get_direct_reports(customer_id):
        if _calc_vg(d, month_key, mxn_per_vp, max_levels) >= pc_per_line:
            count += 1
    return count

def _generation_qualified(beneficiary_id: str, gen_cfg: dict, month_key: str,
                          mxn_per_vp: float, max_levels: int, activation_vp: float) -> bool:
    """
    True si el beneficiario califica para cobrar la generación descrita por `gen_cfg`
    (Plan abril 2026 §4). Requiere estar activo y cumplir los umbrales de directos
    activos, PC personales y líneas calificadas de esa generación.
    """
    # Requisito base de toda generación: estar activo.
    if not _is_active(beneficiary_id, month_key, mxn_per_vp, activation_vp):
        return False

    req_directs   = int(gen_cfg.get("reqActiveDirects", 0) or 0)
    req_personal  = float(gen_cfg.get("reqPersonalPC", 0) or 0)
    req_lines     = int(gen_cfg.get("reqLines", 0) or 0)
    req_pc_line   = float(gen_cfg.get("reqPCPerLine", 0) or 0)

    if req_personal > 0 and _calc_vp(beneficiary_id, month_key, mxn_per_vp) < req_personal:
        return False
    if req_directs > 0 and _count_active_directs(beneficiary_id, month_key, mxn_per_vp, activation_vp) < req_directs:
        return False
    if req_lines > 0 and _count_qualifying_lines(beneficiary_id, month_key, mxn_per_vp, max_levels, req_pc_line) < req_lines:
        return False
    return True

def _has_bonus_award(customer_id: str, rule_id: str, month_key: str, cooldown: str) -> bool:
    """Verifica si ya existe un award según el cooldown."""
    awards = utils._query_bucket("BONUS_AWARD")
    for a in awards:
        if str(a.get("customerId")) != str(customer_id):
            continue
        if a.get("ruleId") != rule_id:
            continue
        if cooldown == "once":
            return True
        if cooldown == "monthly" and a.get("monthKey") == month_key:
            return True
        if cooldown == "annual" and (a.get("monthKey") or "")[:4] == (month_key or "")[:4]:
            return True
    return False

def _check_consecutive_months(customer_id: str, current_month_key: str, n: int,
                               vg_min: float, mxn_per_vp: float, max_levels: int) -> bool:
    """True si el asociado alcanzó vg_min durante los últimos N meses."""
    try:
        year, month = int(current_month_key[:4]), int(current_month_key[5:7])
    except Exception:
        return False
    for i in range(n):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        mk = f"{y}-{m:02d}"
        vg = _calc_vg(customer_id, mk, mxn_per_vp, max_levels)
        if vg < vg_min:
            return False
    return True

def _count_direct_rank(customer_id: str, month_key: str, required_rank: str,
                       mxn_per_vp: float, max_levels: int, rank_thresholds: list) -> int:
    """Cuenta referidos directos que tienen el rango requerido este mes."""
    directs = _get_direct_reports(customer_id)
    count = 0
    for did in directs:
        vg = _calc_vg(did, month_key, mxn_per_vp, max_levels)
        if _get_rank(vg, rank_thresholds) == required_rank:
            count += 1
    return count

def _evaluate_bonus_rule(rule: dict, customer_id: str, month_key: str,
                          vp: float, vg: float, bonus_cfg: dict,
                          customer_data: dict) -> bool:
    """True si el cliente cumple todas las condiciones de la regla."""
    vp_cfg       = bonus_cfg.get("vpConfig", {})
    mxn_per_vp   = float(vp_cfg.get("mxnPerVp", 50))
    max_levels   = int(vp_cfg.get("maxNetworkLevels", 5))
    rank_thresh  = bonus_cfg.get("rankThresholds", [])

    for cond in rule.get("conditions", []):
        ctype  = cond.get("type")
        cvalue = float(cond.get("value") or 0)

        if ctype == "vg_min":
            if vg < cvalue: return False

        elif ctype == "vp_min":
            if vp < cvalue: return False

        elif ctype == "direct_vg_min":
            total = sum(_calc_vg(d, month_key, mxn_per_vp, max_levels)
                        for d in _get_direct_reports(customer_id))
            if total < cvalue: return False

        elif ctype == "consecutive_months":
            # Busca el vg_min que aplica a esta regla
            vg_min_for_rank = next(
                (float(c.get("value") or 0) for c in rule.get("conditions", []) if c.get("type") == "vg_min"),
                0.0
            )
            if not _check_consecutive_months(customer_id, month_key, int(cvalue),
                                             vg_min_for_rank, mxn_per_vp, max_levels):
                return False

        elif ctype == "direct_rank_count":
            count = _count_direct_rank(customer_id, month_key, cond.get("rank", ""),
                                       mxn_per_vp, max_levels, rank_thresh)
            if count < cvalue: return False

        elif ctype == "first_30_days":
            created_at = (customer_data or {}).get("createdAt", "")
            if not created_at: return False
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if (now - created).days > 30: return False
            except Exception:
                return False

        elif ctype == "first_time":
            if _has_bonus_award(customer_id, rule.get("id", ""), month_key, "once"):
                return False

    # Cooldown global (salvo 'first_time' que ya se evaluó arriba)
    cooldown = rule.get("cooldown", "monthly")
    if cooldown in ("once", "annual"):
        if _has_bonus_award(customer_id, rule.get("id", ""), month_key, cooldown):
            return False

    return True

def handle_evaluate_bonuses(customer_id: str, month_key: str) -> dict:
    """Evalúa todas las reglas de bonos activas para un cliente y otorga los que califiquen."""
    cfg       = utils._load_app_config()
    bonus_cfg = cfg.get("bonuses") or {}
    rules     = [r for r in bonus_cfg.get("rules", []) if r.get("active")]
    if not rules:
        return {"awarded": [], "vp": 0, "vg": 0, "rank": ""}

    vp_cfg     = bonus_cfg.get("vpConfig", {})
    mxn_per_vp = float(vp_cfg.get("mxnPerVp", 50))
    max_levels = int(vp_cfg.get("maxNetworkLevels", 5))

    vp            = _calc_vp(customer_id, month_key, mxn_per_vp)
    vg            = _calc_vg(customer_id, month_key, mxn_per_vp, max_levels)
    rank          = _compute_rank(customer_id, month_key, vp, vg, mxn_per_vp, max_levels,
                                  bonus_cfg.get("rankThresholds", []))
    customer_data = utils._get_by_id("CUSTOMER", customer_id) or {}

    awarded = []
    for rule in rules:
        cooldown = rule.get("cooldown", "monthly")
        if cooldown == "monthly":
            if _has_bonus_award(customer_id, rule.get("id", ""), month_key, "monthly"):
                continue
        if not _evaluate_bonus_rule(rule, customer_id, month_key, vp, vg, bonus_cfg, customer_data):
            continue
        for reward in rule.get("rewards", []):
            award_id = f"BONUS-{utils.uuid.uuid4().hex[:10].upper()}"
            award = {
                "entityType": "bonusAward",
                "id": award_id,
                "ruleId": rule.get("id"),
                "ruleName": rule.get("name"),
                "customerId": customer_id,
                "monthKey": month_key,
                "rewardType": reward.get("type"),
                "rewardAmount": float(reward.get("amount") or 0),
                "rewardItemLabel": reward.get("itemLabel"),
                "rewardPct": float(reward.get("pct") or 0),
                "status": "pending",
                "createdAt": utils._now_iso(),
                "updatedAt": utils._now_iso(),
            }
            utils._put_entity("BONUS_AWARD", award_id, award)
            awarded.append(award)

    print(f"[BONUSES] customer={customer_id} month={month_key} vp={vp:.1f} vg={vg:.1f} rank={rank} awarded={len(awarded)}")
    return {"awarded": awarded, "vp": vp, "vg": vg, "rank": rank}

# --- HELPERS DE CONFIGURACIÓN ---

def _default_app_config() -> dict:
    return {
        "version": "app-v1",
        "rewards": {
            # Activación mensual: $1,000 MXN netos = 20 PC (con mxnPerVp=50). Plan abril 2026 §3.
            "activationNetMin": utils.Decimal("20"),
            "payoutDay": utils.Decimal("10"),
            # Compresión dinámica activa: salta posiciones no calificadas y paga al
            # siguiente ascendente calificado (Plan abril 2026 §4).
            "cutRule": "dynamic_compression",
            # Escalera de descuentos por MPN (Monto Personal Neto) acumulado en el mes
            # calendario. Importes en MXN. Plan abril 2026 §3.
            "discountTiers": [
                {"min": utils.Decimal("0"),    "max": utils.Decimal("1000"), "rate": utils.Decimal("0.00")},
                {"min": utils.Decimal("1000"), "max": utils.Decimal("2000"), "rate": utils.Decimal("0.10")},
                {"min": utils.Decimal("2000"), "max": utils.Decimal("3000"), "rate": utils.Decimal("0.20")},
                {"min": utils.Decimal("3000"), "max": utils.Decimal("6000"), "rate": utils.Decimal("0.30")},
                {"min": utils.Decimal("6000"), "max": None,                  "rate": utils.Decimal("0.40")},
            ],
            # Comisiones por generación con requisitos de desbloqueo. Plan abril 2026 §4.
            # reqActiveDirects = directos activos; reqPersonalPC = PC netos personales;
            # reqLines = líneas calificadas; reqPCPerLine = PC netos mínimos por línea.
            "commissionLevels": [
                {"gen": 1, "rate": utils.Decimal("0.10"), "reqActiveDirects": 0, "reqPersonalPC": 0,   "reqLines": 0, "reqPCPerLine": 0},
                {"gen": 2, "rate": utils.Decimal("0.05"), "reqActiveDirects": 2, "reqPersonalPC": 0,   "reqLines": 0, "reqPCPerLine": 0},
                {"gen": 3, "rate": utils.Decimal("0.04"), "reqActiveDirects": 3, "reqPersonalPC": 80,  "reqLines": 2, "reqPCPerLine": 300},
                {"gen": 4, "rate": utils.Decimal("0.03"), "reqActiveDirects": 4, "reqPersonalPC": 120, "reqLines": 3, "reqPCPerLine": 450},
                {"gen": 5, "rate": utils.Decimal("0.02"), "reqActiveDirects": 5, "reqPersonalPC": 160, "reqLines": 3, "reqPCPerLine": 750},
            ],
        },
        "orders": {"requireStockOnShipped": True, "requireDispatchLinesOnShipped": True},
        "pos": {
            "defaultCustomerName": "Publico en General",
            "defaultPaymentStatus": "paid_branch",
            "defaultDeliveryStatus": "delivered_branch",
            "orderStatusByDeliveryStatus": {"delivered_branch": "delivered", "paid_branch": "paid"},
        },
        "stocks": {"requireLinkedUserForTransferReceive": True},
        "payments": {
            "mercadoLibre": {
                "enabled": False, "accessToken": "", "currencyId": "MXN",
                "checkoutPreferencesUrl": "https://api.mercadopago.com/checkout/preferences",
                "paymentInfoUrlTemplate": "https://api.mercadopago.com/v1/payments/{payment_id}",
                "notificationUrl": "", "successUrl": "", "failureUrl": "", "pendingUrl": "", "webhookSecret": "",
            }
        },
        "adminWarnings": {
            "showCommissions": True, "showShipping": True, "showPendingPayments": True,
            "showPendingTransfers": True, "showPosSalesToday": True,
        },
        "shipping": {"enabled": True, "markup": 0.0, "carriers": ["dhl", "fedex"]},
        "customerDocumentTypes": [
            {"key": "constancia", "label": "Constancia de situación fiscal", "required": True},
            {"key": "ine",        "label": "INE (frente y reverso)",          "required": True},
            {"key": "curp",       "label": "CURP",                            "required": True},
        ],
        "bonuses": {
            "vpConfig": {"mxnPerVp": 50, "maxNetworkLevels": 5},
            # Rangos de liderazgo. Plan abril 2026 §6. PC netos (proporcionales al neto pagado).
            # vpMin = PC personal mín.; vgMin = VG mín.; minLines = líneas activas;
            # pcMinPerLine = PC mín. por línea; requiredLeaders/requiredLeaderRank = líderes
            # del rango inferior requeridos en la red.
            "rankThresholds": [
                {"rank": "BRONCE",   "vpMin": 60,  "vgMin": 4500,  "minLines": 3, "pcMinPerLine": 900,  "requiredLeaders": 0, "requiredLeaderRank": "",        "monthlyBonus": 500,   "annualBonus": 6000},
                {"rank": "PLATA",    "vpMin": 90,  "vgMin": 9000,  "minLines": 4, "pcMinPerLine": 1500, "requiredLeaders": 2, "requiredLeaderRank": "BRONCE",  "monthlyBonus": 1500,  "annualBonus": 18000},
                {"rank": "ORO",      "vpMin": 140, "vgMin": 15000, "minLines": 4, "pcMinPerLine": 2500, "requiredLeaders": 2, "requiredLeaderRank": "PLATA",   "monthlyBonus": 3000,  "annualBonus": 36000},
                {"rank": "PLATINO",  "vpMin": 200, "vgMin": 21000, "minLines": 5, "pcMinPerLine": 3000, "requiredLeaders": 2, "requiredLeaderRank": "ORO",     "monthlyBonus": 6000,  "annualBonus": 72000},
                {"rank": "DIAMANTE", "vpMin": 280, "vgMin": 25000, "minLines": 5, "pcMinPerLine": 4000, "requiredLeaders": 2, "requiredLeaderRank": "PLATINO", "monthlyBonus": 10000, "annualBonus": 120000},
            ],
            "rules": [
                {
                    # §7.1 Bono de Inicio Rápido: 600 PC grupales en los primeros 30 días, una sola vez.
                    "id": "inicio_rapido", "name": "Bono de Inicio Rápido", "active": True,
                    "conditions": [{"type": "first_30_days"}, {"type": "vg_min", "value": 600}],
                    "rewards": [{"type": "cash_mxn", "amount": 5000}],
                    "cooldown": "once",
                    "notes": "Primeros 30 días: 600 PC grupales del equipo → $5,000 MXN (una vez).",
                },
                # §7.2 Bono Mensual por Rango: se mantiene el rango 3 meses (calificación, no cobra)
                # y se cobra a partir del 4º mes consecutivo. consecutive_months=4 sobre el vgMin del rango.
                {
                    "id": "bono_rango_bronce", "name": "Bono Mensual BRONCE", "active": True, "rank": "BRONCE",
                    "conditions": [{"type": "vg_min", "value": 4500}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 500}],
                    "cooldown": "monthly",
                    "notes": "$500/mes desde el 4º mes consecutivo en BRONCE.",
                },
                {
                    "id": "bono_rango_plata", "name": "Bono Mensual PLATA", "active": True, "rank": "PLATA",
                    "conditions": [{"type": "vg_min", "value": 9000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 1500}],
                    "cooldown": "monthly",
                    "notes": "$1,500/mes desde el 4º mes consecutivo en PLATA.",
                },
                {
                    "id": "bono_rango_oro", "name": "Bono Mensual ORO", "active": True, "rank": "ORO",
                    "conditions": [{"type": "vg_min", "value": 15000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 3000}],
                    "cooldown": "monthly",
                    "notes": "$3,000/mes desde el 4º mes consecutivo en ORO.",
                },
                {
                    "id": "bono_rango_platino", "name": "Bono Mensual PLATINO", "active": True, "rank": "PLATINO",
                    "conditions": [{"type": "vg_min", "value": 21000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 6000}],
                    "cooldown": "monthly",
                    "notes": "$6,000/mes desde el 4º mes consecutivo en PLATINO.",
                },
                {
                    "id": "bono_rango_diamante", "name": "Bono Mensual DIAMANTE", "active": True, "rank": "DIAMANTE",
                    "conditions": [{"type": "vg_min", "value": 25000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 10000}],
                    "cooldown": "monthly",
                    "notes": "$10,000/mes desde el 4º mes consecutivo en DIAMANTE.",
                },
                # §7.3 Premios físicos por sostenimiento de rango (una sola vez por rango).
                {
                    "id": "premio_bronce_3m", "name": "Premio BRONCE (3 meses)", "active": True, "rank": "BRONCE",
                    "conditions": [{"type": "vg_min", "value": 4500}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Licuadora o Air Fryer", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_plata_3m", "name": "Premio PLATA (3 meses)", "active": True, "rank": "PLATA",
                    "conditions": [{"type": "vg_min", "value": 9000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Microondas o equivalente", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_oro_3m", "name": "Premio ORO (3 meses)", "active": True, "rank": "ORO",
                    "conditions": [{"type": "vg_min", "value": 15000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Pantalla Smart TV", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_platino_3m", "name": "Premio PLATINO (3 meses)", "active": True, "rank": "PLATINO",
                    "conditions": [{"type": "vg_min", "value": 21000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Experiencia premium", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_diamante_6m", "name": "Premio DIAMANTE (6 meses)", "active": True, "rank": "DIAMANTE",
                    "conditions": [{"type": "vg_min", "value": 25000}, {"type": "consecutive_months", "value": 6}],
                    "rewards": [{"type": "item", "itemLabel": "Viaje internacional elite", "triggerMonths": 6}],
                    "cooldown": "once",
                },
            ],
        },
    }

def _merge_dict(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for k, v in override.items():
            merged[k] = _merge_dict(merged.get(k), v)
        return merged
    return override if override is not None else base

def _normalize_app_config(raw) -> dict:
    base = _default_app_config()
    merged = _merge_dict(base, raw if isinstance(raw, dict) else {})
    return merged

def _decimal_clean(obj):
    """Recursively convert float → Decimal so DynamoDB doesn't throw."""
    if isinstance(obj, float):
        return utils.Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _decimal_clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_clean(i) for i in obj]
    return obj

def _save_app_config(cfg: dict) -> dict:
    normalized = _decimal_clean(_normalize_app_config(cfg))
    now = utils._now_iso()
    existing = utils._get_by_id("CONFIG", "app-v1")
    if not existing:
        item = {
            "entityType": "config", "name": "app", "configId": "app-v1",
            "config": normalized, "createdAt": now, "updatedAt": now,
        }
        utils._put_entity("CONFIG", "app-v1", item, created_at_iso=now)
    else:
        utils._update_by_id(
            "CONFIG", "app-v1",
            "SET #c = :c, updatedAt = :u",
            {":c": normalized, ":u": now},
            {"#c": "config"},
        )
    return normalized

# --- HELPERS DE ASSETS ---

def _upload_receipt_s3(name: str, content_base64: str, content_type: str, prefix: str = "comprobantes") -> dict:
    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        raise ValueError("invalid_base64")
    asset_id = f"{prefix}/{utils.uuid.uuid4()}-{name}"
    _s3.put_object(Bucket=BUCKET_NAME, Key=asset_id, Body=raw, ContentType=content_type, ACL="public-read")
    url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    now = utils._now_iso()
    item = {
        "entityType": "asset", "assetId": asset_id, "name": name,
        "contentType": content_type, "url": url, "createdAt": now, "updatedAt": now,
    }
    return utils._put_entity("ASSET", asset_id, item, created_at_iso=now)

# --- HELPERS DE COMISIONABILIDAD ---

def _commissionable_net(order: dict, fallback_net) -> utils.Decimal:
    """
    Calcula el monto neto comisionable de la orden.
    Si todos los ítems tienen commissionable=True (o el campo no existe),
    devuelve el netTotal completo. Si algún ítem no es comisionable,
    recalcula el monto excluyéndolos (proporcionalmente al netTotal).
    """
    items = order.get("items") or []
    if not items:
        return utils._to_decimal(fallback_net)

    # Verificar si hay algún ítem no comisionable
    has_non_commissionable = any(
        i.get("commissionable") is False for i in items if isinstance(i, dict)
    )
    if not has_non_commissionable:
        return utils._to_decimal(fallback_net)

    # Calcular subtotal bruto commissionable vs total para obtener la proporción
    gross_total      = utils.D_ZERO
    gross_commission = utils.D_ZERO
    for it in items:
        if not isinstance(it, dict):
            continue
        price = utils._to_decimal(it.get("price", 0))
        qty   = utils._to_decimal(it.get("quantity", 1))
        line  = price * qty
        gross_total += line
        if it.get("commissionable") is not False:
            gross_commission += line

    if gross_total == utils.D_ZERO:
        return utils.D_ZERO

    net_amount = utils._to_decimal(fallback_net)
    proportion = gross_commission / gross_total
    return (net_amount * proportion).quantize(utils.D_CENT)


# --- PROCESOS DE ORQUESTACIÓN (STEP FUNCTIONS) ---

def handle_apply_rewards(order_id):
    """Acción: ORDER_PAID. Calcula comisiones en estado 'pending'."""
    order = utils._get_by_id("ORDER", order_id)
    if not order: return {"error": "Order not found"}

    app_cfg   = utils._load_app_config()
    cfg       = app_cfg.get("rewards", {})
    bonus_cfg = app_cfg.get("bonuses") or {}
    vp_cfg    = bonus_cfg.get("vpConfig", {})
    mxn_per_vp  = float(vp_cfg.get("mxnPerVp", 50))

    month_key  = order.get("monthKey") or utils._month_key()
    net_amount = utils._to_decimal(order.get("netTotal"))

    # Calcular monto comisionable en MXN (para comisiones al upline)
    commissionable_net = _commissionable_net(order, net_amount)

    # Calcular puntos VP de esta orden (usa vpPoints por producto + descuento)
    order_vp = _compute_order_vp(order, mxn_per_vp)

    # 1. Actualizar volumen personal del comprador
    buyer_id = order.get("customerId")
    if order.get("buyerType") in ["associate", "registered"] and buyer_id:
        # Almacena netVolume en MXN (compatibilidad) y netVP en puntos directos
        utils._increment_associate_month_net_volume(buyer_id, month_key, commissionable_net)
        utils._increment_associate_month_net_vp(buyer_id, month_key, order_vp)

    # 2. Repartir comisiones al upline con compresión dinámica (Plan abril 2026 §4).
    max_levels    = int(vp_cfg.get("maxNetworkLevels", 5))
    activation_vp = float(utils._to_decimal(cfg.get("activationNetMin", 20)))
    cut_rule      = cfg.get("cutRule", "dynamic_compression")
    levels_cfg    = cfg.get("commissionLevels", [])

    # Mapa generación -> config (tasa + requisitos de desbloqueo).
    default_rates = {1: "0.10", 2: "0.05", 3: "0.04", 4: "0.03", 5: "0.02"}
    gens: dict = {}
    for i, lvl in enumerate(levels_cfg[:MAX_COMMISSION_LEVELS]):
        g = int(lvl.get("gen", i + 1))
        gens[g] = dict(lvl)
        gens[g].setdefault("rate", utils.Decimal(default_rates.get(g, "0")))
    for g, r in default_rates.items():
        gens.setdefault(g, {"gen": g, "rate": utils.Decimal(r)})

    # Cadena completa de ancestros (no limitada a 5) para poder comprimir.
    chain = utils._get_customer_upline_ids(order['customerId'], MAX_COMPRESSION_DEPTH)

    def _write_row(b_id, gen, amount, status, reason=None):
        item   = _get_ledger_month(b_id, month_key)
        row_id = f"{order_id}#G{gen}"
        new_row = {
            "rowId": row_id, "orderId": order_id, "amount": amount,
            "level": gen, "generation": gen, "status": status,
            "createdAt": utils._now_iso(),
        }
        if reason:
            new_row["reason"] = reason
        item['ledger'] = [r for r in item['ledger'] if r['rowId'] != row_id]
        item['ledger'].append(new_row)
        _save_ledger_month(item)

    gen = 1  # siguiente generación a cubrir
    for b_id in chain:
        if gen > MAX_COMMISSION_LEVELS:
            break
        gen_cfg = gens.get(gen, {})
        rate    = utils._to_decimal(gen_cfg.get("rate", 0))
        amount  = (commissionable_net * rate).quantize(utils.D_CENT)

        if _generation_qualified(b_id, gen_cfg, month_key, mxn_per_vp, max_levels, activation_vp):
            # Califica: cobra esta generación y avanza el contador.
            _write_row(b_id, gen, amount, "pending")
            gen += 1
        elif cut_rule == "dynamic_compression":
            # No califica: se registra informativo 'blocked' y la posición se brinca
            # (la generación la tomará el siguiente ascendente calificado).
            _write_row(b_id, gen, amount, "blocked", reason="no_califica_gen")
            # No se avanza `gen`: compresión dinámica.
        else:
            # Modo legado sin traspaso: bloquea y avanza igual.
            _write_row(b_id, gen, amount, "blocked", reason="inactivo")
            gen += 1

def handle_confirm_commissions(order_id):
    """Acción: ORDER_DELIVERED. Cambia 'pending' -> 'confirmed' y evalúa bonos."""
    order = utils._get_by_id("ORDER", order_id)
    if not order: return
    month_key = order.get("monthKey") or utils._month_key()
    chain     = _get_upline_chain(order['customerId'])

    for b_id in chain:
        item    = _get_ledger_month(b_id, month_key)
        changed = False
        for r in item['ledger']:
            if r.get('orderId') == order_id and r.get('status') == "pending":
                r['status'] = "confirmed"
                changed = True
        if changed:
            _save_ledger_month(item)

    # Evaluar bonos para el comprador y su upline al confirmar entrega
    buyer_id = str(order.get("customerId", ""))
    if buyer_id:
        try:
            handle_evaluate_bonuses(buyer_id, month_key)
        except Exception as e:
            print(f"[BONUS_EVAL_ERROR] buyer={buyer_id} err={e}")

# --- HANDLERS DE API ---

def handle_payout_request(body):
    """POST /commissions/request"""
    cid = body.get("customerId")
    month_key = utils._month_key()
    ledger = _get_ledger_month(cid, month_key)
    
    if ledger['totalConfirmed'] <= 0:
        return utils._json_response(400, {"message": "No hay saldo confirmado para retirar"})
    
    req_id = f"REQ-{utils.uuid.uuid4().hex[:8].upper()}"
    request_item = {
        "entityType": "commissionRequest", "requestId": req_id, "customerId": cid,
        "amount": ledger['totalConfirmed'], "status": "requested", "createdAt": utils._now_iso()
    }
    utils._put_entity("COMMISSION_REQUEST", req_id, request_item)
    return utils._json_response(201, {"request": request_item})

def handle_admin_receipt(body):
    """POST /admin/commissions/receipt - Admin marca como pagado con comprobante"""
    cid = body.get("customerId")
    month_key = body.get("monthKey") or body.get("month")
    name = body.get("name")
    content_base64 = body.get("contentBase64")

    if not cid or not month_key or not name or not content_base64:
        return utils._json_response(400, {"message": "customerId, monthKey, name y contentBase64 son obligatorios"})

    try:
        asset = _upload_receipt_s3(name, content_base64, body.get("contentType") or "application/pdf", "comprobantes")
    except ValueError:
        return utils._json_response(400, {"message": "contentBase64 invalido"})

    now = utils._now_iso()
    receipt_id = f"{cid}#{month_key}#{utils.uuid.uuid4()}"
    receipt_item = {
        "entityType": "commissionReceipt", "receiptId": receipt_id,
        "customerId": int(cid), "monthKey": month_key,
        "assetId": asset.get("assetId"), "assetUrl": asset.get("url"),
        "status": "paid", "createdAt": now, "updatedAt": now,
    }
    utils._put_entity("COMMISSION_RECEIPT", receipt_id, receipt_item, created_at_iso=now)

    # Marcar el mes contable como PAID
    sk = f"#BENEFICIARY#{cid}#MONTH#{month_key}"
    try:
        utils._table.update_item(
            Key={"PK": PK_MONTH, "SK": sk},
            UpdateExpression="SET #s = :p, paidAt = :now",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":p": "PAID", ":now": now},
        )
    except Exception:
        pass
    return utils._json_response(201, {"receipt": receipt_item, "asset": asset})


def handle_upload_receipt(body) -> dict:
    """POST /commissions/receipt - Socio sube comprobante propio"""
    customer_id = body.get("customerId")
    month_key = body.get("monthKey") or body.get("month") or utils._month_key()
    name = body.get("name")
    content_base64 = body.get("contentBase64")

    if not customer_id or not name or not content_base64:
        return utils._json_response(400, {"message": "customerId, name y contentBase64 son obligatorios"})

    try:
        asset = _upload_receipt_s3(name, content_base64, body.get("contentType") or "image/png", "assets")
    except ValueError:
        return utils._json_response(400, {"message": "contentBase64 invalido"})

    now = utils._now_iso()
    receipt_id = f"{customer_id}#{month_key}#{utils.uuid.uuid4()}"
    receipt_item = {
        "entityType": "commissionReceipt", "receiptId": receipt_id,
        "customerId": int(customer_id), "monthKey": month_key,
        "assetId": asset.get("assetId"), "assetUrl": asset.get("url"),
        "status": "uploaded", "createdAt": now, "updatedAt": now,
    }
    utils._put_entity("COMMISSION_RECEIPT", receipt_id, receipt_item, created_at_iso=now)
    return utils._json_response(201, {"receipt": receipt_item, "asset": asset})


def handle_get_associate_month(associate_id: str, month_key: str) -> dict:
    """GET /associates/{id}/month/{monthKey}"""
    item = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(associate_id, month_key))
    if not item:
        item = {
            "entityType": "associateMonth", "associateId": associate_id,
            "monthKey": month_key, "netVolume": utils.D_ZERO, "isActive": False,
            "createdAt": utils._now_iso(), "updatedAt": utils._now_iso(),
        }
    net_volume = float(utils._to_decimal(item.get("netVolume")))

    # Load config for discount tiers and goals
    cfg = utils._load_app_config() or _default_app_config()
    rewards = cfg.get("rewards") or {}
    discount_tiers = rewards.get("discountTiers") or []
    commission_levels = rewards.get("commissionLevels") or []
    mxn_per_vp = float(utils._to_decimal((cfg.get("bonuses") or {}).get("vpConfig", {}).get("mxnPerVp", 50)))

    # Determine current discount tier for this associate
    current_discount = None
    next_goal = None
    for tier in sorted(discount_tiers, key=lambda t: float(utils._to_decimal(t.get("min", 0)))):
        tier_min = float(utils._to_decimal(tier.get("min", 0)))
        tier_max = tier.get("max")
        tier_max_f = float(utils._to_decimal(tier_max)) if tier_max is not None else None
        if net_volume >= tier_min and (tier_max_f is None or net_volume < tier_max_f):
            current_discount = {
                "rate": float(utils._to_decimal(tier.get("rate", 0))),
                "min": tier_min,
                "max": tier_max_f,
            }
        if next_goal is None and tier_min > net_volume:
            tier_rate = float(utils._to_decimal(tier.get("rate", 0)))
            next_goal = {
                "min": tier_min,
                "rate": tier_rate,
                "label": f"Descuento {round(tier_rate * 100)}%",
            }

    # VP / VG for this month
    vp = _mxn_to_vp(net_volume, mxn_per_vp) if mxn_per_vp > 0 else 0.0

    return utils._json_response(200, {"month": {
        "associateId": associate_id,
        "monthKey": month_key,
        "netVolume": net_volume,
        "vp": vp,
        "isActive": bool(item.get("isActive")),
        "updatedAt": item.get("updatedAt"),
        "currentDiscount": current_discount,
        "nextGoal": next_goal,
        "commissionLevels": [
            {
                "rate": float(utils._to_decimal(lvl.get("rate", 0))),
                "minActiveUsers": int(lvl.get("minActiveUsers") or 0),
                "minIndividualPurchase": float(utils._to_decimal(lvl.get("minIndividualPurchase", 0))),
                "minGroupPurchase": float(utils._to_decimal(lvl.get("minGroupPurchase", 0))),
            }
            for lvl in commission_levels
        ],
    }})

# --- VOID COMMISSIONS ACTION (Step Functions) ---

def _handle_void_commissions_action(order_id: str, reason: str) -> dict:
    """Acción de Step Functions: revertir comisiones por cancelación o devolución aprobada.

    Triggered by: ORDER_CANCELLED, ORDER_REFUNDED, ORDER_RETURNED
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        print(f"[VOID_COMM] Orden {order_id} no encontrada")
        return {"skipped": True}

    month_key = order.get("monthKey") or utils._month_key()
    buyer_id = order.get("customerId")
    if not buyer_id:
        return {"skipped": True, "reason": "no_buyer"}

    # Construir cadena de beneficiarios (upline hasta MAX_COMMISSION_LEVELS)
    beneficiaries = utils._get_customer_upline_ids(buyer_id, MAX_COMMISSION_LEVELS)

    if (order.get("buyerType") or "").lower() == "guest":
        referrer_id = order.get("referrerAssociateId")
        if referrer_id:
            beneficiaries = [str(referrer_id)] + beneficiaries

    voided = []
    for beneficiary_id in beneficiaries:
        sk = f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"
        resp = utils._table.get_item(Key={"PK": PK_MONTH, "SK": sk})
        item = resp.get("Item")
        if not item:
            continue

        ledger = item.get("ledger") or []
        pending_delta = utils.D_ZERO
        confirmed_delta = utils.D_ZERO
        blocked_delta = utils.D_ZERO
        new_ledger = []
        removed = 0

        for row in ledger:
            if row.get("orderId") == order_id:
                amt = utils._to_decimal(row.get("amount"))
                st = (row.get("status") or "").lower()
                if st == "pending":    pending_delta += amt
                elif st == "confirmed": confirmed_delta += amt
                elif st in ("blocked",) or row.get("blocked"): blocked_delta += amt
                removed += 1
                continue
            new_ledger.append(row)

        if removed == 0:
            continue

        try:
            utils._table.update_item(
                Key={"PK": PK_MONTH, "SK": sk},
                UpdateExpression=(
                    "SET ledger = :l, "
                    "totalPending = if_not_exists(totalPending, :z) - :pd, "
                    "totalConfirmed = if_not_exists(totalConfirmed, :z) - :cd, "
                    "totalBlocked = if_not_exists(totalBlocked, :z) - :bd, "
                    "updatedAt = :u"
                ),
                ExpressionAttributeValues={
                    ":l": new_ledger, ":pd": pending_delta,
                    ":cd": confirmed_delta, ":bd": blocked_delta,
                    ":z": utils.D_ZERO, ":u": utils._now_iso(),
                },
            )
            voided.append({
                "beneficiaryId": beneficiary_id, "orderId": order_id,
                "pendingRemoved": float(pending_delta),
                "confirmedRemoved": float(confirmed_delta), "reason": reason,
            })
        except Exception as e:
            print(f"[VOID_SFN_ERROR] beneficiary={beneficiary_id} err={e}")

    print(f"[VOID_COMM] order={order_id} reason={reason} voided={len(voided)}")
    return {"voided": voided, "count": len(voided)}


# --- REPORTE MENSUAL DE OPERACIONES ---

def handle_monthly_stats(month: str) -> dict:
    """Agrega estadísticas operacionales del mes para pedidos, clientes, productos y stocks."""

    # --- PEDIDOS ---
    all_orders = utils._query_bucket("ORDER")
    month_orders = [o for o in all_orders if str(o.get("monthKey", "")) == month]

    orders_count = len(month_orders)
    orders_total = sum(float(utils._to_decimal(o.get("total", 0))) for o in month_orders)
    avg_ticket = (orders_total / orders_count) if orders_count else 0

    # Por estado
    by_status: dict = {}
    for o in month_orders:
        s = o.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    # Por método de pago
    by_payment: dict = {}
    for o in month_orders:
        pm = o.get("paymentMethod", "unknown")
        by_payment[pm] = by_payment.get(pm, 0) + 1

    # Clientes activos (compraron en el mes)
    active_customer_ids = list({str(o.get("customerId", "")) for o in month_orders if o.get("customerId")})
    active_customer_count = len(active_customer_ids)

    # Top clientes por número de pedidos
    cust_order_count: dict = {}
    cust_order_total: dict = {}
    for o in month_orders:
        cid = str(o.get("customerId", ""))
        if cid:
            cust_order_count[cid] = cust_order_count.get(cid, 0) + 1
            cust_order_total[cid] = cust_order_total.get(cid, 0) + float(utils._to_decimal(o.get("total", 0)))
    top_customers = sorted(
        [{"customerId": k, "orders": cust_order_count[k], "total": cust_order_total[k]} for k in cust_order_count],
        key=lambda x: x["orders"], reverse=True
    )[:10]

    # Productos vendidos en pedidos
    product_sales: dict = {}
    for o in month_orders:
        for item in (o.get("items") or []):
            pid = str(item.get("productId", item.get("id", "")))
            if not pid:
                continue
            name = item.get("name", pid)
            qty = int(item.get("quantity", 1))
            price = float(utils._to_decimal(item.get("price", 0)))
            if pid not in product_sales:
                product_sales[pid] = {"productId": pid, "name": name, "units": 0, "revenue": 0.0}
            product_sales[pid]["units"] += qty
            product_sales[pid]["revenue"] += qty * price

    product_sales_list = sorted(product_sales.values(), key=lambda x: x["units"], reverse=True)
    total_units_sold = sum(p["units"] for p in product_sales_list)

    # --- CLIENTES ---
    all_customers = utils._query_bucket("CUSTOMER")
    new_customers = [c for c in all_customers if str(c.get("createdAt", "")).startswith(month)]
    new_customer_count = len(new_customers)

    # Tasa de recompra: clientes activos que tenían al menos 1 pedido en meses anteriores
    prev_buyer_ids = {str(o.get("customerId", "")) for o in all_orders
                      if str(o.get("monthKey", "")) < month and o.get("customerId")}
    repurchase_ids = {cid for cid in active_customer_ids if cid in prev_buyer_ids}
    repurchase_rate = (len(repurchase_ids) / active_customer_count * 100) if active_customer_count else 0

    # --- POS VENTAS ---
    all_pos = utils._query_bucket("POS_SALE")
    month_pos = [p for p in all_pos if str(p.get("createdAt", "")).startswith(month)]
    pos_count = len(month_pos)
    pos_total = sum(float(utils._to_decimal(p.get("total", 0))) for p in month_pos)

    # --- MOVIMIENTOS DE INVENTARIO ---
    all_movements = utils._query_bucket("INVENTORY_MOVEMENT")
    month_movements = [m for m in all_movements if str(m.get("createdAt", "")).startswith(month)]
    movements_by_type: dict = {}
    for mv in month_movements:
        t = mv.get("type", "unknown")
        movements_by_type[t] = movements_by_type.get(t, 0) + 1

    # --- STOCKS ACTUALES ---
    all_stocks = utils._query_bucket("STOCK")
    stock_summary = []
    for st in all_stocks:
        stock_summary.append({
            "stockId": str(st.get("SK", st.get("id", ""))),
            "name": st.get("name", ""),
            "location": st.get("location", ""),
            "totalProducts": int(st.get("totalProducts", 0)),
            "totalValue": float(utils._to_decimal(st.get("totalValue", 0))),
        })

    result = {
        "month": month,
        "orders": {
            "count": orders_count,
            "total": round(orders_total, 2),
            "avgTicket": round(avg_ticket, 2),
            "byStatus": by_status,
            "byPaymentMethod": by_payment,
            "activeCustomers": active_customer_ids,
            "activeCustomerCount": active_customer_count,
            "topCustomers": top_customers,
        },
        "products": {
            "sales": product_sales_list,
            "totalUnitsSold": total_units_sold,
        },
        "customers": {
            "newCount": new_customer_count,
            "activeCount": active_customer_count,
            "repurchaseRate": round(repurchase_rate, 2),
        },
        "pos": {
            "count": pos_count,
            "total": round(pos_total, 2),
        },
        "stocks": {
            "summary": stock_summary,
            "movements": month_movements,
            "movementsByType": movements_by_type,
        },
    }

    print(f"[MONTHLY_STATS] month={month} orders={orders_count} pos={pos_count} customers_new={new_customer_count}")
    return utils._json_response(200, result)


# --- LAMBDA HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    # 1. Detectar si es una invocación de Step Functions
    if "action" in event:
        action = event["action"]
        oid = event.get("orderId")
        if action == "ORDER_PAID" and oid:
            handle_apply_rewards(oid)
        if action == "ORDER_DELIVERED" and oid:
            handle_confirm_commissions(oid)
        if action in ("ORDER_CANCELLED", "ORDER_REFUNDED", "ORDER_RETURNED") and oid:
            _handle_void_commissions_action(oid, action.lower())
        return {"status": "PROCESSED", "action": action, "orderId": oid}

    # 2. Detectar si es una petición de API Gateway
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    headers = event.get("headers") or {}
    # API GW está configurado como ANY /commissions/{proxy+}; el path llega con el prefijo
    raw_segments = [s for s in path.strip("/").split("/") if s]
    segments = raw_segments[1:] if raw_segments and raw_segments[0] == "commissions" else raw_segments

    try:
        if not segments:
            return utils._json_response(200, {"service": "commissions"})

        root = segments[0]

        # GET /commissions/summary?month={monthKey}  — batch export helper
        if root == "summary" and method == "GET":
            err = utils._require_admin(headers, "access_screen_stats")
            if err: return err
            month = (event.get("queryStringParameters") or {}).get("month") or utils._month_key()
            prev_month = (event.get("queryStringParameters") or {}).get("prevMonth")
            # Query all COMMISSION_MONTH records and filter in memory
            all_comm = utils._query_bucket("COMMISSION_MONTH")
            receipts_raw = utils._query_bucket("COMMISSION_RECEIPT")
            receipt_by_cust = {}
            for r in receipts_raw:
                if str(r.get("monthKey")) == str(month):
                    receipt_by_cust[str(r.get("customerId"))] = r.get("assetUrl") or ""
            summary = {}
            for item in all_comm:
                sk = str(item.get("SK") or "")
                if f"#MONTH#{month}" not in sk:
                    continue
                bid = str(item.get("beneficiaryId") or "")
                if not bid:
                    continue
                confirmed = float(utils._to_decimal(item.get("totalConfirmed", 0)))
                receipt_url = receipt_by_cust.get(bid, "")
                if confirmed <= 0:
                    status = "no_moves"
                elif receipt_url:
                    status = "paid"
                else:
                    status = "pending"
                summary[bid] = {
                    "customerId": bid,
                    "monthKey": month,
                    "paidTotal": confirmed,
                    "status": status,
                    "receiptUrl": receipt_url,
                }
            return utils._json_response(200, {"summary": summary, "monthKey": month})

        # POST /commissions/request
        if root == "request" and method == "POST":
            err = utils._require_self_or_admin(headers, body.get("customerId"))
            if err: return err
            return handle_payout_request(body)

        # POST /commissions/receipt
        if root == "receipt" and method == "POST":
            err = utils._require_self_or_admin(headers, body.get("customerId"))
            if err: return err
            return handle_upload_receipt(body)

        # POST /commissions/admin/receipt
        if root == "admin" and len(segments) >= 2 and segments[1] == "receipt":
            if method == "POST":
                err = utils._require_admin(headers, "commissions_register_payment")
                if err: return err
                return handle_admin_receipt(body)

        # /commissions/config/rewards  y  /commissions/config/app
        if root == "config" and len(segments) > 1:
            sub = segments[1]
            if sub == "rewards":
                if method == "GET":
                    return utils._json_response(200, {"config": utils._load_app_config().get("rewards")})
                if method == "PUT":
                    err = utils._require_admin(headers, "config_manage")
                    if err: return err
                    current = utils._load_app_config()
                    current["rewards"] = body
                    saved = _save_app_config(current)
                    return utils._json_response(200, {"config": saved.get("rewards")})
            if sub == "app":
                if method == "GET":
                    err = utils._require_admin(headers, "access_screen_settings")
                    if err: return err
                    cfg = utils._load_app_config()
                    if not cfg:
                        cfg = _default_app_config()
                    return utils._json_response(200, {"config": cfg})
                if method == "PUT":
                    err = utils._require_admin(headers, "config_manage")
                    if err: return err
                    if not body:
                        return utils._json_response(400, {"message": "config invalida"})
                    current = utils._load_app_config() or _default_app_config()
                    incoming = body.get("config") if isinstance(body.get("config"), dict) else body
                    merged = _merge_dict(current, incoming)
                    saved = _save_app_config(merged)
                    utils._audit_event("config.app.update", headers, body, {"scope": "app"})
                    return utils._json_response(200, {"config": saved})

        # /commissions/associates/{id}/commissions  y  /commissions/associates/{id}/month/{monthKey}
        if root == "associates" and len(segments) >= 3:
            aid = segments[1]
            sub = segments[2]
            if sub == "commissions":
                err = utils._require_self_or_admin(headers, aid)
                if err: return err
                month = (event.get("queryStringParameters") or {}).get("month", utils._month_key())
                return utils._json_response(200, _get_ledger_month(aid, month))
            if sub == "month" and len(segments) >= 4:
                err = utils._require_self_or_admin(headers, aid)
                if err: return err
                return handle_get_associate_month(aid, segments[3])

        # /commissions/bonuses/{customerId}  — lista de awards del cliente
        if root == "bonuses" and len(segments) == 2:
            cid = segments[1]
            if method == "GET":
                err = utils._require_self_or_admin(headers, cid)
                if err: return err
                query_params = event.get("queryStringParameters") or {}
                month = query_params.get("month")
                awards = utils._query_bucket("BONUS_AWARD")
                result = [a for a in awards if str(a.get("customerId")) == str(cid)]
                if month:
                    result = [a for a in result if a.get("monthKey") == month]
                # Calcular VP/VG/rango actuales
                cfg       = utils._load_app_config()
                bonus_cfg = cfg.get("bonuses") or {}
                vp_cfg    = bonus_cfg.get("vpConfig", {})
                mk        = month or utils._month_key()
                mxn_per_vp   = float(vp_cfg.get("mxnPerVp", 50))
                max_levels   = int(vp_cfg.get("maxNetworkLevels", 5))
                vp   = _calc_vp(cid, mk, mxn_per_vp)
                vg   = _calc_vg(cid, mk, mxn_per_vp, max_levels)
                rank = _get_rank(vg, bonus_cfg.get("rankThresholds", []))
                return utils._json_response(200, {"awards": result, "vp": vp, "vg": vg, "rank": rank})

        # /bonuses/evaluate  — dispara evaluación manual (admin/sistema)
        if root == "bonuses" and len(segments) == 2 and segments[1] == "evaluate" and method == "POST":
            err = utils._require_admin(headers, "commissions_register_payment")
            if err: return err
            cid       = body.get("customerId")
            month_key = body.get("monthKey") or utils._month_key()
            if not cid:
                return utils._json_response(400, {"message": "customerId requerido"})
            result = handle_evaluate_bonuses(str(cid), month_key)
            return utils._json_response(200, result)

        # GET /commissions/monthly-stats?month=YYYY-MM
        if root == "monthly-stats" and method == "GET":
            err = utils._require_admin(headers, "access_screen_stats")
            if err: return err
            month = (event.get("queryStringParameters") or {}).get("month") or utils._month_key()
            return handle_monthly_stats(month)

        return utils._json_response(404, {"message": "Ruta de comisiones no encontrada"})

    except Exception as e:
        print(f"[COMMISSION_ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Error en motor de comisiones", "error": str(e)})
