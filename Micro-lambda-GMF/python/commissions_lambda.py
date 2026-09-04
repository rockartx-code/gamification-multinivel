import base64
import boto3
from datetime import datetime, timezone
import core_utils as utils # Importado desde la Lambda Layer
import modo_handlers  # paquete B

# --- CONSTANTES ---
# Plan abril 2026: 5 generaciones (Gen1..Gen5) con compresión dinámica.
MAX_COMMISSION_LEVELS = 5
# Profundidad máxima de ancestros a recorrer al comprimir (saltar no calificados).
MAX_COMPRESSION_DEPTH = 50
# Alias local del PK definido en core_utils (única fuente de verdad).
PK_MONTH = utils.COMMISSION_MONTH_PK
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

# Cliente S3
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)

# --- HELPERS DEL MOTOR MLM ---

def _get_upline_chain(buyer_id):
    """Busca los patrocinadores hacia arriba en la red."""
    return utils._get_customer_upline_ids(buyer_id, MAX_COMMISSION_LEVELS)

def _ledger_sk(beneficiary_id, month_key) -> str:
    return utils._ledger_sk(beneficiary_id, month_key)


def _get_ledger_month(beneficiary_id, month_key):
    """Obtiene o inicializa el registro contable mensual del socio."""
    return utils._get_ledger_month(beneficiary_id, month_key)


def _save_ledger_month(item):
    """Recalcula totales y persiste el mes contable (bloqueo optimista)."""
    return utils._save_ledger_month(item)


def _mutate_ledger_month(beneficiary_id, month_key, mutate) -> dict:
    """Aplica `mutate(item)` sobre el mes contable reintentando ante conflicto."""
    return utils._mutate_ledger_month(beneficiary_id, month_key, mutate)


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
    return _state_to_vp(_cached_month_state(customer_id, month_key), mxn_per_vp)

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

# ---------------------------------------------------------------------------
# Caché por invocación
# ---------------------------------------------------------------------------
# `_calc_vp` se pedía una y otra vez para el mismo cliente desde `_is_active`,
# `_count_active_directs` y `_generation_qualified`, y cada llamada era un
# `_get_by_id` (1-3 GetItem). Estos mapas viven mientras dura la invocación del
# Lambda y se vacían al empezar cada acción para no arrastrar datos entre
# eventos distintos de un mismo contenedor tibio.
_CACHE: dict = {"customers": {}, "states": {}, "children": {}, "vg": {}, "activos_forzados": set(),
                "recalculo": {}}


def _reset_request_cache() -> None:
    _CACHE["customers"] = {}
    _CACHE["states"] = {}
    _CACHE["children"] = {}
    _CACHE["vg"] = {}
    # Paquete A: `(cliente, mes)` que se consideran activos aunque el mes no lo
    # diga (gracia `blockedGraceDays`: la activación de este mes libera el anterior).
    _CACHE["activos_forzados"] = set()
    # Paquete A · propuesta 32: "Le movieron la fecha a mis comisiones". Al
    # recalcular se anula la fila (que queda tachada, con su fecha) y se
    # escribe otra con el mismo `rowId`: aquí viaja el motivo del recálculo
    # para poder decirlo en la fila.
    _CACHE["recalculo"] = {}


def _cached_customer(customer_id) -> dict:
    cid = utils._customer_id_str(customer_id)
    if not cid:
        return {}
    if cid not in _CACHE["customers"]:
        _CACHE["customers"][cid] = utils._get_by_id("CUSTOMER", utils._customer_entity_id(cid)) or {}
    return _CACHE["customers"][cid]


def _cached_month_state(customer_id, month_key: str) -> dict:
    cid = utils._customer_id_str(customer_id)
    key = f"{cid}#{month_key}"
    if key not in _CACHE["states"]:
        _CACHE["states"][key] = utils._get_by_id(
            "ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, month_key)
        ) or {}
    return _CACHE["states"][key]


def _prime_month_states(customer_ids: list, month_key: str) -> None:
    """Precarga en bloque los estados del mes que aún no estén en caché."""
    pending = [
        cid for cid in {utils._customer_id_str(c) for c in customer_ids or []}
        if cid and f"{cid}#{month_key}" not in _CACHE["states"]
    ]
    if not pending:
        return
    states = utils._load_month_states(pending, month_key)
    for cid in pending:
        _CACHE["states"][f"{cid}#{month_key}"] = states.get(cid) or {}


def _children_index() -> dict:
    """Mapa `{líder: [hijos]}` del árbol de red persistido, cacheado."""
    if not _CACHE["children"]:
        tree = utils._ensure_network_tree() or {}
        children = {
            str(parent_id): [str(child_id) for child_id in (child_ids or [])]
            for parent_id, child_ids in (tree.get("childrenByParent") or {}).items()
        }
        _CACHE["children"] = children or {"__empty__": []}
    return _CACHE["children"]


def _get_direct_reports(customer_id: str) -> list:
    """IDs de los referidos directos (nivel 1)."""
    customer = _cached_customer(customer_id)
    if customer and "directReferralIds" in customer:
        return utils._customer_id_list(customer.get("directReferralIds"))

    # El árbol persistido evita el barrido de la colección CUSTOMER completa.
    return [
        cid for cid in _children_index().get(utils._customer_id_str(customer_id), [])
        if cid
    ]


def _network_descendant_ids_cached(customer_id: str, max_levels: int) -> list:
    """Descendencia hasta `max_levels` niveles, desde el árbol persistido."""
    children = _children_index()
    root = utils._customer_id_str(customer_id)
    result: list = []
    visited = {root}
    queue = [(root, 0)]
    while queue:
        cid, depth = queue.pop(0)
        if depth >= max_levels:
            continue
        for child_id in children.get(cid, []):
            if not child_id or child_id in visited:
                continue
            visited.add(child_id)
            result.append(child_id)
            queue.append((child_id, depth + 1))
    return result


def _calc_vg(customer_id: str, month_key: str, mxn_per_vp: float, max_levels: int = 5) -> float:
    """Volumen de Grupo: VP propio + VP de la red hasta `max_levels` niveles.

    Antes recorría la red haciendo un `_get_by_id` de ASSOCIATE_MONTH por nodo
    (y, sin `networkDescendantIds` persistido, releía la colección CUSTOMER
    entera en cada llamada). Ahora los ids salen del árbol persistido, los
    estados se precargan en bloque y el resultado se memoiza.
    """
    root = utils._customer_id_str(customer_id)
    cache_key = f"{root}#{month_key}#{max_levels}"
    if cache_key in _CACHE["vg"]:
        return _CACHE["vg"][cache_key]

    member_ids = [root, *_network_descendant_ids_cached(root, max_levels)]
    _prime_month_states(member_ids, month_key)

    total_vp = sum(
        _state_to_vp(_cached_month_state(cid, month_key), mxn_per_vp)
        for cid in member_ids
    )
    _CACHE["vg"][cache_key] = total_vp
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
    return _network_descendant_ids_cached(customer_id, max_levels)

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
    if (utils._customer_id_str(customer_id), month_key) in _CACHE.get("activos_forzados", set()):
        return True
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
    """Verifica si ya existe un award según el cooldown.

    El cooldown acota cuánta historia hace falta leer: "monthly" solo mira de
    ese mes en adelante y "annual" de ese año en adelante. "once" sí necesita
    el histórico completo, por definición.
    """
    if cooldown == "monthly":
        awards = utils._query_bucket("BONUS_AWARD", sk_from=month_key)
    elif cooldown == "annual":
        awards = utils._query_bucket("BONUS_AWARD", sk_from=str(month_key or "")[:4])
    else:
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
    mxn_per_vp   = utils._mxn_per_vp()
    max_levels   = utils._max_network_levels()
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

    mxn_per_vp = utils._mxn_per_vp()
    max_levels = utils._max_network_levels()

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

    utils._log("bonuses_evaluated", "INFO", customerId=customer_id, monthKey=month_key,
               vp=round(vp, 1), vg=round(vg, 1), rank=rank, awarded=len(awarded))
    return {"awarded": awarded, "vp": vp, "vg": vg, "rank": rank}

# --- HELPERS DE CONFIGURACIÓN ---

def _default_app_config() -> dict:
    """Configuración por defecto del plan (definida en core_utils)."""
    return utils._default_app_config()


def _normalize_app_config(raw) -> dict:
    return utils._normalize_app_config(raw)


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
    # El contenedor que guarda no debe seguir sirviendo la config vieja los
    # segundos que le queden de TTL a su caché local.
    utils._invalidate_app_config_cache()
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

def _es_comprador_registrado(order: dict) -> bool:
    """Socio o cliente con cuenta. Los pedidos anteriores a la corrección de
    buyerType quedaron como "guest" aunque llevaran customerId; se reconocen
    por la ficha para poder reacreditar su volumen."""
    if order.get("buyerType") in ["associate", "registered"]:
        return True
    cid = order.get("customerId")
    return bool(cid) and utils._get_by_id("CUSTOMER", cid) is not None


def _generation_map(cfg: dict) -> dict:
    """Mapa generación -> config (tasa + requisitos de desbloqueo)."""
    levels_cfg    = cfg.get("commissionLevels", [])
    default_rates = {1: "0.10", 2: "0.05", 3: "0.04", 4: "0.03", 5: "0.02"}
    gens: dict = {}
    for i, lvl in enumerate(levels_cfg[:MAX_COMMISSION_LEVELS]):
        g = int(lvl.get("gen", i + 1))
        gens[g] = dict(lvl)
        gens[g].setdefault("rate", utils.Decimal(default_rates.get(g, "0")))
    for g, r in default_rates.items():
        gens.setdefault(g, {"gen": g, "rate": utils.Decimal(r)})
    return gens


def _distribute_commissions(order: dict, order_id: str, month_key: str, commissionable_net) -> None:
    """Reparte la comisión de una orden a su línea ascendente con compresión
    dinámica (Plan abril 2026 §4). Escribe filas 'pending' o 'blocked'."""
    cfg           = utils._load_app_config().get("rewards", {})
    mxn_per_vp    = utils._mxn_per_vp()
    max_levels    = utils._max_network_levels()
    activation_vp = utils._activation_vp()
    cut_rule      = cfg.get("cutRule", "dynamic_compression")
    gens          = _generation_map(cfg)

    # Cadena completa de ancestros (no limitada a 5) para poder comprimir.
    chain = utils._get_customer_upline_ids(order['customerId'], MAX_COMPRESSION_DEPTH)

    def _write_row(b_id, gen, amount, status, reason=None):
        row_id = f"{order_id}#G{gen}"

        cambio = {"nuevo": True}
        ahora = utils._now_iso()
        # Propuesta 32: la fecha de la comisión es la del pedido y no se mueve.
        fecha_pedido = str(order.get("createdAt") or "") or ahora

        def _mutate(item):
            # La reevaluación anula la fila (queda tachada, con su fecha) antes
            # de reescribirla con el mismo `rowId`: de ahí sale su nacimiento.
            previa = next((r for r in item['ledger'] if r.get('rowId') == row_id), None)
            nacio = str((previa or {}).get("createdAt") or "") or ahora
            new_row = {
                "rowId": row_id, "orderId": order_id, "amount": amount,
                "level": gen, "generation": gen, "status": status,
                "createdAt": nacio,
                # La fila la lee la socia: se guarda la fecha del pedido y la
                # base sobre la que se calculó, para poder explicar el importe
                # ("10 % de $1,350.00 netos, sin envío = $135.00").
                "orderCreatedAt": fecha_pedido,
                "commissionRate": utils._to_decimal(gens.get(gen, {}).get("rate", 0)),
                "commissionBaseNet": utils._to_decimal(commissionable_net),
            }
            if reason:
                new_row["reason"] = reason
            cambiada = bool(previa) and not (
                (previa.get("status") or "").lower() == status
                and utils._to_decimal(previa.get("amount")) == utils._to_decimal(amount)
            )
            if cambiada and _CACHE["recalculo"].get("motivo"):
                propio = utils._customer_id_str(b_id) == str(_CACHE["recalculo"].get("activador") or "")
                new_row["recalculatedAt"] = ahora
                new_row["recalculatedReason"] = (
                    _CACHE["recalculo"].get("motivoPropio") if propio else _CACHE["recalculo"]["motivo"]
                )
            elif previa and previa.get("recalculatedAt"):
                new_row["recalculatedAt"] = previa["recalculatedAt"]
                new_row["recalculatedReason"] = previa.get("recalculatedReason") or ""
            # Si la fila ya existía igual (reevaluación del mismo pedido), no es un aviso nuevo.
            if previa and not cambiada:
                cambio["nuevo"] = False
            item['ledger'] = [r for r in item['ledger'] if r.get('rowId') != row_id]
            item['ledger'].append(new_row)
            return True

        _mutate_ledger_month(b_id, month_key, _mutate)
        # Paquete B: con fila de comisión ya es socio. Se decide con la ficha
        # ya cacheada: leerla otra vez por beneficiaria rompía el presupuesto
        # de consultas de ORDER_PAID (tools/check_query_budget.py).
        if modo_handlers.modo_de(_cached_customer(b_id)) == "cliente":
            modo_handlers.asegurar_socio(b_id, "comision")
            _CACHE["customers"].pop(utils._customer_id_str(b_id), None)
        return cambio["nuevo"]

    gen = 1  # siguiente generación a cubrir
    for b_id in chain:
        if gen > MAX_COMMISSION_LEVELS:
            break
        gen_cfg = gens.get(gen, {})
        rate    = utils._to_decimal(gen_cfg.get("rate", 0))
        amount  = (commissionable_net * rate).quantize(utils.D_CENT)

        if _generation_qualified(b_id, gen_cfg, month_key, mxn_per_vp, max_levels, activation_vp):
            # Califica: cobra esta generación y avanza el contador.
            # El aviso salía dos veces: al pagar y otra vez cuando la propia compra
            # activaba al comprador y se reevaluaba el mismo pedido.
            if _write_row(b_id, gen, amount, "pending"):
                _avisar_comision(b_id, order, gen, amount, neto=commissionable_net, rate=rate)
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


def _avisar_comision(beneficiary_id, order: dict, gen: int, amount, neto=None, rate=None) -> None:
    """Correo al patrocinador cuando alguien de su red compra y le genera comisión.

    "Mis dos referidas compraron el 3 y yo me enteré el 7, sola, hurgando en el
    panel. Una red se sostiene agradeciendo el mismo día." Nunca interrumpe el reparto.
    """
    try:
        cliente = _cached_customer(beneficiary_id)
        para = str((cliente or {}).get("email") or "").strip()
        if not para or (cliente or {}).get("doNotContact"):
            return
        comprador = order.get("customerName") or "alguien de tu red"
        nombre = (cliente.get("name") or "").split(" ")[0] or "Hola"
        from core.email import _email_shell
        monto = f"${float(amount):,.2f}"
        # Propuesta 37: sobre qué base se calcula, con estas palabras y una
        # sola vez (§3.2). Ximena la buscó en tres pantallas y no la encontró.
        cuenta = (f'<p class="lead">Así sale el número: <strong>{pagos_handlers.texto_base_comision(neto, rate, amount)}</strong>. '
                  f"{pagos_handlers.frase_base_comision()}</p>") if neto is not None and rate is not None else ""
        cuenta_texto = (f" Así sale el número: {pagos_handlers.texto_base_comision(neto, rate, amount)}. "
                        f"{pagos_handlers.frase_base_comision()}") if neto is not None and rate is not None else ""
        cuerpo = f"""
    <div class="icon">🎉</div>
    <h1 class="title">{comprador} compró</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Una compra de tu red (generación {gen}) te genera una comisión de <strong>{monto}</strong>. Queda pendiente hasta que el pedido se entregue; la ves en tu panel, en Comisiones.</p>
    {cuenta}
    <p class="lead">Hoy es buen día para escribirle y darle las gracias.</p>"""
        utils._send_ses_email(para, f"{comprador} compró: comisión de {monto} en camino",
                              f"Hola {nombre}. {comprador} compró; te genera una comisión de {monto} (generación {gen}), "
                              f"pendiente hasta la entrega.{cuenta_texto}",
                              _email_shell(cuerpo))
    except Exception as e:  # pragma: no cover
        utils._log("commission_email_error", "ERROR", beneficiary=beneficiary_id, err=e)



_MOTIVOS_ANULACION = {
    "order_cancelled": "el pedido se canceló", "cancel": "el pedido se canceló",
    "order_refunded": "el pedido se reembolsó", "refund": "el pedido se reembolsó",
    "order_returned": "el pedido se devolvió", "return_approved": "el pedido se devolvió",
}


def _avisar_comision_anulada(beneficiary_id, order: dict, amount, reason: str) -> None:
    """Correo al patrocinador cuando una comisión ya anunciada se anula."""
    try:
        cliente = _cached_customer(beneficiary_id)
        para = str((cliente or {}).get("email") or "").strip()
        if not para or (cliente or {}).get("doNotContact"):
            return
        comprador = order.get("customerName") or "alguien de tu red"
        nombre = (cliente.get("name") or "").split(" ")[0] or "Hola"
        motivo = _MOTIVOS_ANULACION.get(reason, "el pedido se anuló")
        from core.email import _email_shell
        monto = f"${float(amount):,.2f}"
        oid = order.get("orderId") or ""
        cuerpo = f"""
    <div class="icon">↩️</div>
    <h1 class="title">Una comisión se anuló</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. La comisión de <strong>{monto}</strong> por la compra de {comprador} (pedido {oid}) ya no aplica porque {motivo}. Tu panel de Comisiones ya lo refleja.</p>"""
        utils._send_ses_email(para, f"Comisión de {monto} anulada · pedido {oid}",
                              f"Hola {nombre}. La comisión de {monto} por la compra de {comprador} (pedido {oid}) se anuló porque {motivo}.",
                              _email_shell(cuerpo))
    except Exception as e:  # pragma: no cover
        utils._log("commission_void_email_error", "ERROR", beneficiary=beneficiary_id, err=e)

def _confirm_order_rows(order_id: str, month_key: str, chain: list) -> None:
    """Cambia a 'confirmed' las filas 'pending' de una orden ya entregada."""
    def _confirm(item):
        changed = False
        for r in item['ledger']:
            if r.get('orderId') == order_id and r.get('status') == "pending":
                r['status'] = "confirmed"
                changed = True
        return changed

    for b_id in chain:
        _mutate_ledger_month(b_id, month_key, _confirm)


_ESTADOS_ENTREGADOS = ("delivered", "en_devolucion", "devolucion_rechazada")
_ESTADOS_SIN_COMISION = ("cancelled", "canceled", "refunded", "devuelto_validado")


def _reevaluate_blocked_rows(beneficiary_ids: list, month_key: str) -> list:
    """Vuelve a repartir las órdenes del mes que dejaron filas 'blocked' en los
    ledgers indicados.

    Las filas 'blocked' se escribían en el instante en que pagaba el referido,
    según si el patrocinador estaba activo *en ese momento*, y nunca se volvían
    a mirar: una socia que se activaba el día 20 seguía viendo bloqueadas las
    comisiones de sus referidos del día 4, y comprar "para desbloquearlas" no
    servía de nada. El plan habla de estar activo *en el mes*, así que al
    activarse se recalculan esas órdenes con la situación actual del mes.
    """
    orders = {}
    bloqueadas_antes = {}
    for b_id in beneficiary_ids:
        ledger = _get_ledger_month(b_id, month_key)
        for r in ledger.get("ledger") or []:
            if (r.get("status") or "").lower() == "blocked" and r.get("orderId"):
                orders[r["orderId"]] = True
                bloqueadas_antes.setdefault(utils._customer_id_str(b_id), {})[str(r["rowId"])] = utils._to_decimal(r.get("amount"))

    redistribuidas = []
    for oid in orders:
        order = utils._get_by_id("ORDER", oid)
        if not order or (order.get("status") or "").lower() in _ESTADOS_SIN_COMISION:
            continue
        chain = utils._get_customer_upline_ids(order['customerId'], MAX_COMPRESSION_DEPTH)
        for b_id in chain:
            try:
                utils._void_ledger_rows_for_order(b_id, month_key, oid, "recalculada: alguien de la línea se activó")
            except Exception as e:
                utils._log("reeval_void_error", "ERROR", beneficiary=b_id, orderId=oid, err=e)
        net_amount = utils._to_decimal(order.get("netTotal"))
        _distribute_commissions(order, oid, month_key, _commissionable_net(order, net_amount))
        if (order.get("status") or "").lower() in _ESTADOS_ENTREGADOS:
            _confirm_order_rows(oid, month_key, chain)
        redistribuidas.append(oid)
    if redistribuidas:
        utils._log("blocked_rows_reevaluated", "INFO", month=month_key, orders=redistribuidas)
        _avisar_desbloqueadas(bloqueadas_antes, month_key)
    return redistribuidas


def _avisar_desbloqueadas(bloqueadas_antes: dict, month_key: str) -> list:
    """Propuesta 34: "tu comisión bloqueada se desbloqueó".

    Paulina se activó el 20 y sus comisiones bloqueadas se liberaron sin que
    nadie se lo dijera. Se compara lo que estaba bloqueado antes del recálculo
    con lo que quedó: lo que dejó de estarlo se avisa, una sola vez.
    """
    if not utils._load_app_config().get("rewards", {}).get("blockedUnlockNotice", True):
        return []
    avisadas = []
    for cid, filas in bloqueadas_antes.items():
        ledger = _get_ledger_month(cid, month_key)
        vigentes = {str(r.get("rowId")): (r.get("status") or "").lower() for r in ledger.get("ledger") or []}
        liberado = sum(
            (monto for row_id, monto in filas.items() if vigentes.get(row_id) in ("pending", "confirmed")),
            utils.D_ZERO,
        )
        if liberado <= 0:
            continue
        if _correo_desbloqueadas(cid, month_key, liberado):
            avisadas.append(str(cid))
    return avisadas


def _correo_desbloqueadas(cid, month_key: str, monto) -> bool:
    try:
        cliente = _cached_customer(cid)
        para = str((cliente or {}).get("email") or "").strip()
        if not para or (cliente or {}).get("doNotContact"):
            return False
        nombre = (cliente.get("name") or "").split(" ")[0] or "Hola"
        importe = f"${float(monto):,.2f}"
        from core.email import _email_shell
        cuerpo = f"""
    <div class="icon">🔓</div>
    <h1 class="title">Se desbloquearon {importe} de comisiones</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Ya te activaste este mes, así que las comisiones que estaban bloqueadas pasaron a contar: <strong>{importe}</strong>.</p>
    <p class="lead">Se confirman cuando los pedidos de tu red se entreguen, y se depositan el día de pago. Las ves en tu panel, en Comisiones.</p>
    <p class="lead"><a class="btn" href="{pagos_handlers.ENLACE_COMISIONES}">Ver mis comisiones</a></p>"""
        utils._send_ses_email(para, f"Se desbloquearon {importe} de tus comisiones",
                              f"Hola {nombre}. Se desbloquearon {importe} de tus comisiones de {month_key} porque ya te activaste. "
                              f"Las ves en tu panel, en Comisiones: {pagos_handlers.ENLACE_COMISIONES}",
                              _email_shell(cuerpo))
        return True
    except Exception as e:  # pragma: no cover
        utils._log("blocked_unlock_email_error", "ERROR", customer=cid, err=e)
        return False


def handle_apply_rewards(order_id):
    """Acción: ORDER_PAID. Calcula comisiones en estado 'pending'."""
    order = utils._get_by_id("ORDER", order_id)
    if not order: return {"error": "Order not found"}

    cfg        = utils._load_app_config().get("rewards", {})
    mxn_per_vp = utils._mxn_per_vp()
    activation_vp = utils._activation_vp()

    month_key  = order.get("monthKey") or utils._month_key()
    net_amount = utils._to_decimal(order.get("netTotal"))

    # Calcular monto comisionable en MXN (para comisiones al upline)
    commissionable_net = _commissionable_net(order, net_amount)

    # Calcular puntos VP de esta orden (usa vpPoints por producto + descuento)
    order_vp = _compute_order_vp(order, mxn_per_vp)

    # 1. Actualizar volumen personal del comprador
    buyer_id = order.get("customerId")
    se_activo = False
    if _es_comprador_registrado(order) and buyer_id:
        estaba_activo = _is_active(buyer_id, month_key, mxn_per_vp, activation_vp)
        # Almacena netVolume en MXN (compatibilidad) y netVP en puntos directos
        utils._increment_associate_month_net_volume(buyer_id, month_key, commissionable_net)
        utils._increment_associate_month_net_vp(buyer_id, month_key, order_vp)
        # El estado del mes cambió: que el resto del cálculo lo vea fresco.
        _CACHE["states"].pop(f"{utils._customer_id_str(buyer_id)}#{month_key}", None)
        ahora_activo = _is_active(buyer_id, month_key, mxn_per_vp, activation_vp)
        se_activo = (not estaba_activo) and ahora_activo
        # Deja constancia en el pedido de que su volumen ya se acreditó: al
        # cancelarlo solo se resta lo que de verdad se sumó.
        try:
            utils._update_by_id("ORDER", order_id, "SET rewardsAppliedAt = :t", {":t": utils._now_iso()})
        except Exception as e:
            utils._log("rewards_applied_flag_error", "ERROR", order=order_id, err=e)
        try:
            utils._update_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(buyer_id, month_key),
                                "SET isActive = :a", {":a": bool(ahora_activo)})
        except Exception as e:
            utils._log("is_active_flag_error", "ERROR", buyer=buyer_id, err=e)

    # 2. Repartir comisiones al upline con compresión dinámica (Plan abril 2026 §4).
    _distribute_commissions(order, order_id, month_key, commissionable_net)

    # 3. Si con esta compra el comprador se activó, sus comisiones bloqueadas
    #    del mes (y las de su línea ascendente, cuyos requisitos de directos
    #    activos pudieron cambiar) se vuelven a evaluar.
    if se_activo and cfg.get("reevaluateBlockedOnActivation", True):
        chain = utils._get_customer_upline_ids(buyer_id, MAX_COMMISSION_LEVELS)
        # Propuesta 32: el recálculo deja dicho por qué, en la propia fila.
        _CACHE["recalculo"] = {"activador": utils._customer_id_str(buyer_id),
                               "motivoPropio": "te activaste este mes",
                               "motivo": "alguien de tu red se activó"}
        _reevaluate_blocked_rows([str(buyer_id), *chain], month_key)
        # Gracia (política 22, opción a; apagada por omisión): si se activó en
        # los primeros N días del mes, lo bloqueado del mes anterior también se
        # recalcula, contándola como activa en ese mes.
        gracia = int(utils._to_decimal(cfg.get("blockedGraceDays", 0)))
        dia_hoy = int(utils._now_iso()[8:10])
        if gracia > 0 and dia_hoy <= gracia:
            mes_anterior = pagos_handlers._mes_anterior(month_key)
            _CACHE["activos_forzados"].add((utils._customer_id_str(buyer_id), mes_anterior))
            _reevaluate_blocked_rows([str(buyer_id), *chain], mes_anterior)
        _CACHE["recalculo"] = {}

    # 4. Primera activación sin CLABE: se le pide desde ya, no el día de pago.
    if se_activo and cfg.get("clabeReminderOnActivation", True):
        try:
            pagos_handlers.avisar_clabe_al_activarse(buyer_id)
        except Exception as e:  # pragma: no cover
            utils._log("clabe_reminder_error", "ERROR", buyer=buyer_id, err=e)

def handle_confirm_commissions(order_id):
    """Acción: ORDER_DELIVERED. Cambia 'pending' -> 'confirmed' y evalúa bonos."""
    order = utils._get_by_id("ORDER", order_id)
    if not order: return
    month_key = order.get("monthKey") or utils._month_key()
    chain     = _get_upline_chain(order['customerId'])

    _confirm_order_rows(order_id, month_key, chain)

    # Primera comisión confirmada del mes sin CLABE: aviso (uno por mes).
    for b_id in chain:
        try:
            pagos_handlers.avisar_clabe_por_comision_confirmada(b_id, month_key, order_id)
        except Exception as e:  # pragma: no cover
            utils._log("clabe_reminder_error", "ERROR", beneficiary=b_id, err=e)

    # Evaluar bonos para el comprador y su upline al confirmar entrega
    buyer_id = str(order.get("customerId", ""))
    if buyer_id:
        try:
            handle_evaluate_bonuses(buyer_id, month_key)
        except Exception as e:
            utils._log("bonus_eval_error", "ERROR", buyer=buyer_id, err=e)

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


def handle_admin_receipt_revert(body):
    """POST /admin/receipt/revert — deshace un pago registrado por error.

    El mes vuelve a estar pendiente de depósito y el comprobante queda anulado
    (no se borra: se conserva con el motivo).
    """
    cid = body.get("customerId")
    month_key = body.get("monthKey") or body.get("month")
    motivo = str(body.get("reason") or "").strip()
    if not cid or not month_key or not motivo:
        return utils._json_response(400, {"message": "customerId, monthKey y reason son obligatorios"})
    ledger = _get_ledger_month(cid, month_key)
    if str(ledger.get("status") or "").upper() != "PAID":
        return utils._json_response(409, {"message": "Ese mes no está marcado como pagado."})
    now = utils._now_iso()
    anulados = 0
    lotes = []
    for r in utils._query_bucket("COMMISSION_RECEIPT", sk_from=month_key):
        if str(r.get("customerId")) == str(cid) and str(r.get("monthKey")) == str(month_key) and r.get("status") == "paid":
            utils._update_by_id("COMMISSION_RECEIPT", r.get("receiptId"), "SET #s = :s, voidedAt = :t, voidReason = :r, updatedAt = :t",
                                {":s": "voided", ":t": now, ":r": motivo}, {"#s": "status"})
            anulados += 1
            # Un pago de lote se deshace fila por fila: las demás del lote no se tocan.
            if r.get("batchId"):
                lotes.append(str(r.get("batchId")))
    utils._table.update_item(
        Key={"PK": PK_MONTH, "SK": utils._ledger_sk(cid, month_key)},
        UpdateExpression="SET #s = :p, paymentRevertedAt = :now, paymentRevertReason = :r REMOVE paidAt ADD version :one",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":p": "IN_PROGRESS", ":now": now, ":r": motivo, ":one": utils._to_decimal(1)},
    )
    utils._log("commission_payment_reverted", "INFO", customerId=cid, monthKey=month_key, receipts=anulados, batches=lotes)
    return utils._json_response(200, {"ok": True, "receiptsVoided": anulados, "status": "pending",
                                      "customerId": str(cid), "monthKey": month_key,
                                      "batchId": lotes[0] if lotes else None})

def _validar_pago(cid, month_key, permitir_sin_clabe: bool = False):
    """Reglas por fila antes de registrar un depósito: devuelve el código del
    impedimento (`CLABE_REQUIRED`, `ALREADY_PAID`) o None si se puede pagar."""
    # El depósito va a la CLABE del socio: sin CLABE se dejaba marcar "Pagada"
    # sin transferencia real y no había forma de deshacerlo.
    socio = utils._get_by_id("CUSTOMER", utils._customer_entity_id(cid)) or {}
    if not str(socio.get("clabeInterbancaria") or "").strip() and not permitir_sin_clabe:
        return "CLABE_REQUIRED"
    if str(_get_ledger_month(cid, month_key).get("status") or "").upper() == "PAID":
        return "ALREADY_PAID"
    return None


def _registrar_pago(cid, month_key, asset: dict, batch_id=None, bank_reference=None) -> dict:
    """Crea el COMMISSION_RECEIPT, marca el mes PAID y avisa el depósito.

    Lo comparten el pago individual (`handle_admin_receipt`) y el lote
    (`pagos_handlers.handle_pago_lote`): el archivo ya está subido cuando se
    llega aquí, así que un lote sube el comprobante una sola vez.
    """
    now = utils._now_iso()
    receipt_id = f"{cid}#{month_key}#{utils.uuid.uuid4()}"
    receipt_item = {
        "entityType": "commissionReceipt", "receiptId": receipt_id,
        "customerId": utils._customer_entity_id(cid), "monthKey": month_key,
        "assetId": asset.get("assetId"), "assetUrl": asset.get("url"),
        "status": "paid", "createdAt": now, "updatedAt": now,
    }
    if batch_id:
        receipt_item["batchId"] = batch_id
    if bank_reference:
        receipt_item["bankReference"] = bank_reference
    utils._put_entity("COMMISSION_RECEIPT", receipt_id, receipt_item, created_at_iso=now)

    # Marcar el mes contable como PAID
    sk = utils._ledger_sk(cid, month_key)
    try:
        # `ADD version :one` participa en el mismo bloqueo optimista: sin él,
        # una escritura del ledger que hubiera leído el item antes de este
        # cambio pasaría la comprobación de versión y revertiría el estado PAID.
        utils._table.update_item(
            Key={"PK": PK_MONTH, "SK": sk},
            UpdateExpression="SET #s = :p, paidAt = :now ADD version :one",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":p": "PAID", ":now": now, ":one": utils._to_decimal(1)},
        )
    except Exception as ex:
        utils._log_error("commission_month_mark_paid_failed", ex,
                         customerId=cid, monthKey=month_key)
    _avisar_deposito(cid, month_key, str(asset.get("url") or asset.get("assetUrl") or ""))
    return receipt_item


def _avisar_deposito(cid, month_key, enlace: str) -> None:
    """"Hoy es día de pago y de eso tampoco me entero si no me meto": aviso del depósito."""
    try:
        cliente = utils._get_by_id("CUSTOMER", utils._customer_entity_id(cid)) or {}
        para = str(cliente.get("email") or "").strip()
        if not para:
            return
        from core.email import _email_shell
        nombre = (cliente.get("name") or "").split(" ")[0] or "Hola"
        ledger = _get_ledger_month(cid, month_key)
        monto = float(utils._to_decimal(ledger.get("totalConfirmed", 0)))
        comprobante = f'<p class="lead"><a class="btn" href="{enlace}">Ver comprobante</a></p>' if enlace else '<p class="lead">El comprobante lo tienes en tu panel, en Comisiones.</p>'
        cuerpo = f"""
    <div class="icon">💸</div>
    <h1 class="title">Depositamos tus comisiones</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Ya está en camino a tu CLABE el depósito de tus comisiones confirmadas de {month_key}: <strong>${monto:,.2f}</strong>.</p>
    {comprobante}"""
        utils._send_ses_email(para, f"Depositamos tus comisiones de {month_key}: ${monto:,.2f}",
                              f"Hola {nombre}. Depositamos tus comisiones confirmadas de {month_key}: ${monto:,.2f}. Comprobante en tu panel.",
                              _email_shell(cuerpo))
    except Exception as e:  # pragma: no cover
        utils._log("payout_email_error", "ERROR", customer=cid, err=e)


def handle_admin_receipt(body):
    """POST /admin/commissions/receipt - Admin marca como pagado con comprobante"""
    cid = body.get("customerId")
    month_key = body.get("monthKey") or body.get("month")
    name = body.get("name")
    content_base64 = body.get("contentBase64")

    if not cid or not month_key or not name or not content_base64:
        return utils._json_response(400, {"message": "customerId, monthKey, name y contentBase64 son obligatorios"})
    codigo = _validar_pago(cid, month_key, permitir_sin_clabe=bool(body.get("paidWithoutClabe")))
    if codigo == "CLABE_REQUIRED":
        return utils._json_response(409, {"message": "El socio no tiene CLABE registrada: no se puede registrar el depósito. Pídesela y guárdala en su ficha.",
                                          "code": "CLABE_REQUIRED"})
    if codigo == "ALREADY_PAID":
        return utils._json_response(409, {"message": "Ese mes ya está marcado como pagado.", "code": "ALREADY_PAID"})

    try:
        asset = _upload_receipt_s3(name, content_base64, body.get("contentType") or "application/pdf", "comprobantes")
    except ValueError:
        return utils._json_response(400, {"message": "contentBase64 invalido"})

    receipt_item = _registrar_pago(cid, month_key, asset)
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
    cfg = utils._load_app_config()
    rewards = cfg.get("rewards") or {}
    discount_tiers = rewards.get("discountTiers") or []
    commission_levels = rewards.get("commissionLevels") or []
    mxn_per_vp = utils._mxn_per_vp(cfg)

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

    # VP / VG for this month: el mismo valor que decide la activación (netVP si
    # existe); antes se derivaba de pesos ÷ tarifa y el panel decía otra cosa.
    vp = _calc_vp(associate_id, month_key, mxn_per_vp) if mxn_per_vp > 0 else 0.0

    return utils._json_response(200, {"month": {
        "associateId": associate_id,
        "monthKey": month_key,
        "netVolume": net_volume,
        "vp": vp,
        # El flag guardado nunca se recalculaba (nacía False y así se quedaba):
        # una socia con 25.2 VP aparecía "inactiva" en este endpoint.
        "isActive": _state_to_vp(item, mxn_per_vp) >= float(utils._activation_vp()),
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
        utils._log("void_commissions_order_missing", "INFO", orderId=order_id)
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
        try:
            summary = utils._void_ledger_rows_for_order(beneficiary_id, month_key, order_id, reason)
        except Exception as e:
            utils._log("void_sfn_error", "ERROR", beneficiary=beneficiary_id, err=e)
            continue
        if summary:
            voided.append({**summary, "reason": reason})
            # Se le había avisado "comisión en camino"; sin este correo se enteraba
            # sola de que desapareció, hurgando en el panel.
            monto_anulado = utils._to_decimal(summary.get("pendingRemoved") or 0) + utils._to_decimal(summary.get("confirmedRemoved") or 0)
            if monto_anulado > 0:
                _avisar_comision_anulada(beneficiary_id, order, monto_anulado, reason)

    # El volumen y los VP acreditados al comprador al pagar se quedaban tras
    # cancelar, reembolsar o anular: un socio seguía "activo" con un pedido
    # devuelto o una venta de mostrador registrada por error a su nombre.
    # Se restan una sola vez (marca rewardsVoidedAt en el pedido).
    volumen_restado = False
    # Un pedido cancelado antes de pagarse nunca sumó volumen: restarlo dejaba
    # al socio con VP negativo (Verónica quedó en -14.6 VP tras cancelar un
    # carrito de $1,952 que nunca pagó). Pedidos anteriores a la marca
    # rewardsAppliedAt se reconocen por su evidencia de pago.
    # Un reembolso o una devolución solo existen sobre pedidos pagados; la
    # cancelación desde 'paid' deja pendingRefund. Solo la cancelación de un
    # pedido que nunca se pagó queda fuera.
    fue_acreditado = bool(reason != "order_cancelled" or order.get("rewardsAppliedAt") or order.get("paidAt")
                          or order.get("paymentId") or order.get("pendingRefund") or order.get("refundedAt")
                          or order.get("branchSaleId") or order.get("cashSaleId")
                          or (order.get("paymentStatus") or "").lower() in ("paid", "paid_branch"))
    if _es_comprador_registrado(order) and fue_acreditado and not order.get("rewardsVoidedAt"):
        try:
            mxn_per_vp = utils._mxn_per_vp()
            net_amount = utils._to_decimal(order.get("netTotal"))
            commissionable_net = _commissionable_net(order, net_amount)
            order_vp = _compute_order_vp(order, mxn_per_vp)
            utils._increment_associate_month_net_volume(buyer_id, month_key, -commissionable_net)
            utils._increment_associate_month_net_vp(buyer_id, month_key, -order_vp)
            utils._update_by_id("ORDER", order_id, "SET rewardsVoidedAt = :t", {":t": utils._now_iso()})
            _CACHE["states"].pop(f"{utils._customer_id_str(buyer_id)}#{month_key}", None)
            volumen_restado = True
        except Exception as e:
            utils._log("void_volume_error", "ERROR", order=order_id, err=e)

    utils._log("void_comm", "INFO", order=order_id, reason=reason, voided=len(voided), volumeVoided=volumen_restado)
    return {"voided": voided, "count": len(voided), "volumeVoided": volumen_restado}


# --- REPORTE MENSUAL DE OPERACIONES ---

def handle_monthly_stats(month: str) -> dict:
    """Agrega estadísticas operacionales del mes para pedidos, clientes, productos y stocks."""

    # --- PEDIDOS ---
    # `monthKey` de un pedido se deriva de su fecha de creación, así que las
    # órdenes del mes viven en el tramo `SK >= "<mes>"` de la partición; no hace
    # falta traer el histórico completo para filtrarlo en memoria.
    month_orders = [
        o for o in utils._query_bucket("ORDER", sk_prefix=month)
        if str(o.get("monthKey", "")) == month
    ]

    orders_count = len(month_orders)
    orders_total = sum(float(utils._to_decimal(o.get("total") or o.get("netTotal") or 0)) for o in month_orders)
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
    cust_names: dict = {}
    for o in month_orders:
        cid = str(o.get("customerId") or "")
        # Los invitados llegan con customerId 0/None: se agrupan por correo o
        # nombre para no colapsarlos todos en una fila "0".
        if not cid or cid == "0":
            cid = "invitado:" + str(o.get("email") or o.get("customerName") or "")
        if cid:
            cust_order_count[cid] = cust_order_count.get(cid, 0) + 1
            cust_order_total[cid] = cust_order_total.get(cid, 0) + float(utils._to_decimal(o.get("total") or o.get("netTotal") or 0))
            cust_names[cid] = o.get("customerName") or cust_names.get(cid) or ""
    # La pantalla pintaba "1788340136546", "0" y "None": el resumen solo traía
    # el ID y el frontend esperaba un nombre.
    top_customers = sorted(
        [{"customerId": k, "name": cust_names.get(k) or ("Invitado" if k.startswith("invitado:") else k),
          "orders": cust_order_count[k], "count": cust_order_count[k], "total": cust_order_total[k]} for k in cust_order_count],
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
    new_customers = utils._query_bucket("CUSTOMER", sk_prefix=month)
    new_customer_count = len(new_customers)

    # Tasa de recompra: clientes activos con al menos 1 pedido en meses previos.
    # Solo se necesitan customerId y monthKey, así que se proyectan esos campos.
    prev_buyer_ids = {
        str(o.get("customerId", ""))
        for o in utils._query_bucket("ORDER", sk_to=month,
                                     projection=["customerId", "monthKey"])
        if str(o.get("monthKey", "")) < month and o.get("customerId")
    }
    repurchase_ids = {cid for cid in active_customer_ids if cid in prev_buyer_ids}
    repurchase_rate = (len(repurchase_ids) / active_customer_count * 100) if active_customer_count else 0

    # --- POS VENTAS ---
    month_pos = utils._query_bucket("POS_SALE", sk_prefix=month)
    pos_count = len(month_pos)
    pos_total = sum(float(utils._to_decimal(p.get("total", 0))) for p in month_pos)

    # --- MOVIMIENTOS DE INVENTARIO ---
    month_movements = utils._query_bucket("INVENTORY_MOVEMENT", sk_prefix=month)
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

    utils._log("monthly_stats", "INFO", month=month, orders=orders_count, pos=pos_count, customers_new=new_customer_count)
    return utils._json_response(200, result)


# --- LAMBDA HANDLER PRINCIPAL ---


# ---------------------------------------------------------------------------
# HANDLERS DE RUTA
# ---------------------------------------------------------------------------

def handle_commissions_summary(peticion) -> dict:
    """GET /commissions/summary?month= — estado de pago por beneficiario."""
    month = peticion.query.get("month") or utils._month_key()

    # COMMISSION_MONTH ordena por beneficiario, no por fecha, así que no admite
    # recorte por clave; se lee la partición completa (paginada).
    recibos_por_cliente = {
        str(r.get("customerId")): r.get("assetUrl") or ""
        for r in utils._query_bucket("COMMISSION_RECEIPT", sk_from=str(month or ""))
        if str(r.get("monthKey")) == str(month) and r.get("status") != "voided"
    }

    resumen = {}
    for item in utils._query_bucket("COMMISSION_MONTH"):
        if f"#MONTH#{month}" not in str(item.get("SK") or ""):
            continue
        beneficiario = str(item.get("beneficiaryId") or "")
        if not beneficiario:
            continue
        confirmado = float(utils._to_decimal(item.get("totalConfirmed", 0)))
        recibo = recibos_por_cliente.get(beneficiario, "")
        if confirmado <= 0:
            estado = "no_moves"
        elif recibo:
            estado = "paid"
        else:
            # Paquete A: la ficha y la lista distinguen "sin CLABE" de "pendiente".
            ficha = utils._get_by_id("CUSTOMER", utils._customer_entity_id(beneficiario)) or {}
            estado = "pending" if str(ficha.get("clabeInterbancaria") or "").strip() else "sin_clabe"
        resumen[beneficiario] = {
            "customerId": beneficiario,
            "monthKey": month,
            "paidTotal": confirmado,
            "status": estado,
            "receiptUrl": recibo,
        }
    return utils._json_response(200, {"summary": resumen, "monthKey": month})


def handle_get_config(peticion) -> dict:
    """GET /commissions/config/{ámbito} — `rewards` o `app`."""
    if peticion.params["ambito"] == "rewards":
        return utils._json_response(200, {"config": utils._load_app_config().get("rewards")})
    return utils._json_response(200, {"config": utils._load_app_config()})


def handle_put_config(peticion) -> dict:
    """PUT /commissions/config/{ámbito} — guarda y propaga la configuración."""
    ambito = peticion.params["ambito"]
    if ambito == "rewards":
        actual = utils._load_app_config()
        actual["rewards"] = peticion.body
        guardada = _save_app_config(actual)
        return utils._json_response(200, {"config": guardada.get("rewards")})

    if not peticion.body:
        return utils._json_response(400, {"message": "config invalida"})
    entrante = (peticion.body.get("config")
                if isinstance(peticion.body.get("config"), dict) else peticion.body)
    # ── Paquete D · ronda 26 ── el plazo y el responsable del envío entran
    # directo en el importe reembolsado: una política mal escrita se rechaza
    # entera y no se guarda nada (docs/arquitectura/26 §3.4 y §4.5).
    import ayuda_handlers
    error_returns = ayuda_handlers.validar_returns(entrante.get("returns") if isinstance(entrante, dict) else None)
    if error_returns:
        return utils._json_response(400, {"message": error_returns, "code": "INVALID_RETURNS_POLICY"})
    guardada = _save_app_config(utils._merge_dict(utils._load_app_config(), entrante))
    utils._audit_event("config.app.update", peticion.headers, peticion.body, {"scope": "app"})
    return utils._json_response(200, {"config": guardada})


def handle_associate_commissions(peticion) -> dict:
    """GET /commissions/associates/{id}/commissions — mes contable del socio."""
    asociado = peticion.params["id"]
    error = utils._require_self_or_admin(peticion.headers, asociado)
    if error:
        return error
    mes = peticion.query.get("month") or utils._month_key()
    return utils._json_response(200, _get_ledger_month(asociado, mes))


def handle_associate_month_route(peticion) -> dict:
    """GET /commissions/associates/{id}/month/{mes}."""
    asociado = peticion.params["id"]
    error = utils._require_self_or_admin(peticion.headers, asociado)
    if error:
        return error
    return handle_get_associate_month(asociado, peticion.params["mes"])


def handle_customer_bonuses(peticion) -> dict:
    """GET /commissions/bonuses/{id} — bonos del socio y sus métricas."""
    cliente = peticion.params["id"]
    error = utils._require_self_or_admin(peticion.headers, cliente)
    if error:
        return error

    mes_filtro = peticion.query.get("month")
    awards = utils._query_bucket("BONUS_AWARD", sk_from=str(mes_filtro or ""))
    resultado = [a for a in awards if str(a.get("customerId")) == str(cliente)]
    if mes_filtro:
        resultado = [a for a in resultado if a.get("monthKey") == mes_filtro]

    mes = mes_filtro or utils._month_key()
    mxn_per_vp = utils._mxn_per_vp()
    vp = _calc_vp(cliente, mes, mxn_per_vp)
    vg = _calc_vg(cliente, mes, mxn_per_vp, utils._max_network_levels())
    rangos = (utils._load_app_config().get("bonuses") or {}).get("rankThresholds", [])
    return utils._json_response(200, {
        "awards": resultado, "vp": vp, "vg": vg, "rank": _get_rank(vg, rangos),
    })


def handle_evaluate_bonuses_route(peticion) -> dict:
    """POST /commissions/bonuses/evaluate — evaluación manual."""
    cliente = peticion.body.get("customerId")
    if not cliente:
        return utils._json_response(400, {"message": "customerId requerido"})
    mes = peticion.body.get("monthKey") or utils._month_key()
    return utils._json_response(200, handle_evaluate_bonuses(str(cliente), mes))


def handle_payout_request_route(peticion) -> dict:
    """POST /commissions/request — solicitud de pago del socio."""
    error = utils._require_self_or_admin(peticion.headers, peticion.body.get("customerId"))
    return error or handle_payout_request(peticion.body)


def handle_upload_receipt_route(peticion) -> dict:
    """POST /commissions/receipt — el socio sube su comprobante."""
    error = utils._require_self_or_admin(peticion.headers, peticion.body.get("customerId"))
    return error or handle_upload_receipt(peticion.body)


Ruta = utils.routing.Ruta

#: Superficie del motor de comisiones. Rutas con `{}` capturan un segmento.
#: Donde el privilegio depende del actor (dueño o admin) se resuelve dentro
#: del handler con `_require_self_or_admin`; el resto se declara aquí.
RUTAS = [
    Ruta("GET", "summary", privilegio="access_screen_stats",
         descripcion="Export mensual por beneficiario", handler=handle_commissions_summary),
    Ruta("POST", "request", descripcion="Solicitud de pago (dueño o admin)",
         handler=handle_payout_request_route),
    Ruta("POST", "receipt", descripcion="Comprobante subido por el socio",
         handler=handle_upload_receipt_route),
    Ruta("POST", "admin/receipt", privilegio="commissions_register_payment",
         descripcion="Comprobante registrado por el admin",
         handler=lambda p: handle_admin_receipt(p.body)),
    Ruta("POST", "admin/receipt/revert", privilegio="commissions_register_payment",
         descripcion="Deshacer un pago registrado por error",
         handler=lambda p: handle_admin_receipt_revert(p.body)),

    Ruta("GET", "config/{ambito}", privilegio="access_screen_settings",
         descripcion="Leer configuración (rewards | app)", handler=handle_get_config),
    Ruta("PUT", "config/{ambito}", privilegio="config_manage",
         descripcion="Guardar configuración", handler=handle_put_config),

    Ruta("GET", "associates/{id}/commissions", descripcion="Mes contable del socio",
         handler=handle_associate_commissions),
    Ruta("GET", "associates/{id}/month/{mes}", descripcion="Estado mensual del socio",
         handler=handle_associate_month_route),

    Ruta("POST", "bonuses/evaluate", privilegio="commissions_register_payment",
         descripcion="Disparar evaluación de bonos", handler=handle_evaluate_bonuses_route),
    Ruta("GET", "bonuses/{id}", descripcion="Bonos y métricas del socio",
         handler=handle_customer_bonuses),

    Ruta("GET", "monthly-stats", privilegio="access_screen_stats",
         descripcion="Estadísticas operacionales del mes",
         handler=lambda p: handle_monthly_stats(p.query.get("month") or utils._month_key())),
]

#: Acciones que llegan desde Step Functions (no por API Gateway).
ACCIONES_SFN = {
    "ORDER_PAID": lambda oid: handle_apply_rewards(oid),
    "ORDER_DELIVERED": lambda oid: handle_confirm_commissions(oid),
    "ORDER_CANCELLED": lambda oid: _handle_void_commissions_action(oid, "order_cancelled"),
    "ORDER_REFUNDED": lambda oid: _handle_void_commissions_action(oid, "order_refunded"),
    "ORDER_RETURNED": lambda oid: _handle_void_commissions_action(oid, "order_returned"),
}


def lambda_handler(event, context):
    # La caché de red/estados es por invocación: un contenedor tibio no debe
    # arrastrar los datos de un evento al siguiente.
    _reset_request_cache()

    accion = event.get("action")
    if accion:
        order_id = event.get("orderId")
        ejecutar = ACCIONES_SFN.get(accion)
        if ejecutar and order_id:
            ejecutar(order_id)
        return {"status": "PROCESSED", "action": accion, "orderId": order_id}

    return utils.routing.despachar(
        RUTAS, event, strip_prefix="commissions", servicio="commissions",
        requiere_privilegio=utils._require_admin,
    )


# --- Paquete A · pagos-comisiones -------------------------------------------
import pagos_handlers                      # paquete A
RUTAS.extend(pagos_handlers.RUTAS)         # paquete A
TAREAS_PROGRAMADAS = pagos_handlers.TAREAS_PROGRAMADAS   # paquete A
