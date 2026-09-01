import boto3
import base64
import time
from datetime import datetime, timezone
from decimal import Decimal
import core_utils as utils # Importado desde la Layer

FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")
_s3 = boto3.client('s3', region_name=utils.AWS_REGION)

_GOAL_EMAIL_BASE_CSS = """
body { margin:0; padding:0; background-color:#F9F7F2; font-family:'Segoe UI',Arial,sans-serif; }
.wrap { width:100%; max-width:600px; margin:0 auto; padding:24px 16px; }
.card { background:#ffffff; border-radius:24px; padding:40px 36px; text-align:center; border:1px solid #e8e3d8; }
.card-gold { border:2px solid #D4AF37; }
.logo { margin-bottom:24px; }
.icon { font-size:48px; margin-bottom:8px; }
.title { color:#2D3436; font-family:Georgia,serif; font-size:26px; font-weight:bold; margin:0 0 16px; }
.lead { color:#636e72; line-height:1.7; font-size:15px; margin:0 0 20px; }
.reward-box { padding:20px; border-radius:14px; background:linear-gradient(135deg,#FFFDF5 0%,#F4E7B5 100%); margin:20px 0; }
.reward-box h3 { margin:0 0 8px; color:#846D1C; font-size:15px; }
.reward-box p { margin:0; font-size:18px; font-weight:bold; color:#2D3436; }
.warn-box { background:#FFF8E7; border:1px solid #F0D080; border-radius:14px; padding:14px 16px; margin:16px 0; font-size:13px; color:#7A5C00; text-align:left; }
.btn { background:#D4AF37; color:#333 !important; padding:14px 32px; border-radius:50px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:20px; font-size:15px; }
.divider { border:none; border-top:1px solid #eee; margin:28px 0; }
.footer { font-size:12px; color:#aaa; margin-top:24px; }
"""


def _goal_email_shell(card_class: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_GOAL_EMAIL_BASE_CSS}</style></head>
<body>
<div class="wrap">
  <div class="logo" style="text-align:center">
    <img src="https://www.findingu.com.mx/Logo-colores.svg" alt="Finding'u" width="140">
  </div>
  <div class="card {card_class}">
    {body_html}
    <hr class="divider">
    <div class="footer">&copy; 2026 Finding&rsquo;U &nbsp;&bull;&nbsp; Nutrici&oacute;n que te impulsa</div>
  </div>
</div>
</body></html>"""


def _build_goal_achieved_email(
    name: str,
    goal_title: str,
    reward_lines: list,
    bonus_approaching: str = "",
    dashboard_url: str = "",
) -> tuple:
    url = dashboard_url or FRONTEND_URL + "/dashboard"
    rewards_html = "".join(
        f'<p style="font-size:16px;font-weight:bold;margin:6px 0">{reward}</p>'
        for reward in reward_lines
    ) or '<p style="font-size:15px;font-weight:bold">¡Sigue así!</p>'

    approaching_block = ""
    if bonus_approaching:
        approaching_block = f"""
        <div class="warn-box">
          ⏳ {bonus_approaching}
        </div>
        """

    body = f"""
    <div class="icon">🏆</div>
    <h1 class="title">¡Felicidades, meta lograda!</h1>
    <p class="lead">Hola <strong>{name}</strong>,<br>
    has alcanzado la meta <strong>\"{goal_title}\"</strong>.</p>

    <div class="reward-box">
      <h3>Nueva Recompensa Liberada:</h3>
      {rewards_html}
    </div>

    {approaching_block}

    <p class="lead" style="font-size:14px;">
      Tu constancia en la comunidad Finding&rsquo;U está dando frutos. ¡Sigue así!
    </p>

    <a href="{url}" class="btn">Reclamar mis beneficios &rarr;</a>
    """
    html = _goal_email_shell("card-gold", body)
    text = f"¡Felicidades {name}! Lograste la meta '{goal_title}'. Ingresa a ver tus beneficios: {url}"
    return f"¡Meta lograda: {goal_title}! — Finding'U", text, html

# Clientes de AWS (Athena para análitica avanzada, opcional)
try:
    athena = boto3.client('athena')
    ATHENA_DB = utils.os.getenv("ATHENA_DATABASE", "findingu_analytics")
    ATHENA_OUTPUT = f"s3://{utils.BUCKET_NAME}/athena-results/"
    _ATHENA_ENABLED = True
except Exception:
    _ATHENA_ENABLED = False

# --- HELPERS DE FECHA ---

def _prev_month_key() -> str:
    d = datetime.now(timezone.utc)
    if d.month == 1:
        return f"{d.year - 1:04d}-12"
    return f"{d.year:04d}-{d.month - 1:02d}"

# --- HELPERS DE PRODUCTOS Y CAMPAÑAS ---

def _pick_product_image(images, preferred_sections):
    if not images or not isinstance(images, list):
        return ""
    for section in preferred_sections:
        for img in images:
            if img.get("section") == section and img.get("url"):
                return img.get("url")
    for img in images:
        if img.get("url"):
            return img.get("url")
    return ""

def _is_product_active(item) -> bool:
    if not item or not isinstance(item, dict):
        return False
    return bool(item.get("active", True))

def _get_product_summary(item: dict) -> dict:
    images = item.get("images") or []
    tags = item.get("tags") or []
    badge = str(tags[0]) if tags else ""
    img = _pick_product_image(images, ["miniatura", "landing", "redes"])

    # Normalizar variantes: asegurar que img de variante sea string limpio
    raw_variants = item.get("variants") or []
    variants = []
    for v in raw_variants:
        if not isinstance(v, dict):
            continue
        variant = {
            "id": str(v.get("id") or ""),
            "name": str(v.get("name") or ""),
            "active": bool(v.get("active", True)),
        }
        if v.get("price") is not None:
            variant["price"] = float(v.get("price"))
        if v.get("sku"):
            variant["sku"] = str(v.get("sku"))
        if v.get("img"):
            variant["img"] = str(v.get("img"))
        variants.append(variant)

    return {
        "id": str(item.get("productId")), "name": item.get("name"),
        "price": float(item.get("price") or 0), "badge": badge, "img": img,
        "hook": item.get("hook") or "", "description": item.get("description") or "",
        "copyFacebook": item.get("copyFacebook") or "",
        "copyInstagram": item.get("copyInstagram") or "",
        "copyWhatsapp": item.get("copyWhatsapp") or "",
        "images": images, "tags": tags,
        "variants": variants,
        "categoryIds": list(item.get("categoryIds") or []),
        "weightKg": item.get("weightKg"),
        "lengthCm": item.get("lengthCm"),
        "widthCm":  item.get("widthCm"),
        "heightCm": item.get("heightCm"),
        # Banderas de canal / comisiones (default True para retrocompatibilidad)
        "inOnlineStore": bool(item.get("inOnlineStore", True)),
        "inPOS":         bool(item.get("inPOS", True)),
        "commissionable": bool(item.get("commissionable", True)),
        # PC oficiales del producto (puntos que aporta a los logros del asociado).
        "vpPoints": float(utils._to_decimal(item["vpPoints"])) if item.get("vpPoints") is not None else None,
    }

def _campaign_payload(item: dict) -> dict:
    return {
        "id": item.get("campaignId"), "title": item.get("title"),
        "description": item.get("description"), "imageUrl": item.get("imageUrl"),
        "linkUrl": item.get("linkUrl"), "active": bool(item.get("active", True)),
        "startAt": item.get("startAt"), "endAt": item.get("endAt"),
    }

# --- HELPERS DE RED Y METAS ---

def _get_month_state(associate_id, month_key: str, states_by_associate=None) -> dict:
    if isinstance(states_by_associate, dict):
        cached = states_by_associate.get(utils._customer_id_str(associate_id))
        if cached:
            return cached
    state = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(associate_id, month_key))
    if state:
        return state
    now = utils._now_iso()
    return {"associateId": associate_id, "monthKey": month_key, "netVolume": utils.D_ZERO, "isActive": False, "createdAt": now}

def _flatten_tree(root: dict) -> list:
    out = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        out.append({**node, "depth": depth})
        children = node.get("children") or []
        for ch in reversed(children):
            stack.append((ch, depth + 1))
    return out

def _build_month_node_index(month_key: str, customers_raw: list, cfg: dict,
                            month_states: dict = None) -> tuple:
    """Construye una sola vez el índice `{id: nodo}` + `{líder: [hijos]}` del mes.

    Los estados ASSOCIATE_MONTH se cargan en bloque con `_load_month_states`
    (BatchGetItem) en lugar de un GetItem secuencial por cliente. El índice es
    reutilizable para construir el árbol de cualquier raíz sin releer nada.
    """
    activation_min = utils._to_decimal(cfg.get("activationNetMin", 2500))

    nodes = {}
    children_by_leader = {}
    for c in customers_raw:
        if not isinstance(c, dict):
            continue
        cid = utils._customer_id_str(c.get("customerId"))
        if not cid:
            continue
        leader_id = utils._customer_id_str(c.get("leaderId")) or None
        nodes[cid] = {
            "id": cid, "name": c.get("name") or "",
            "level": (c.get("level") or "").strip(),
            "leaderId": leader_id,
            "createdAt": c.get("createdAt"),
            "monthSpend": 0.0, "isActive": False, "children": [],
        }
        if leader_id:
            children_by_leader.setdefault(leader_id, []).append(cid)

    if month_states is None:
        month_states = utils._load_month_states(list(nodes.keys()), month_key)

    for cid, node in nodes.items():
        state = month_states.get(cid) or {}
        net_volume = utils._to_decimal(state.get("netVolume"))
        node["monthSpend"] = float(net_volume)
        node["isActive"] = bool(net_volume >= activation_min)

    for leader_id, child_ids in children_by_leader.items():
        child_ids.sort(key=lambda k: nodes[k]["monthSpend"] if k in nodes else 0.0, reverse=True)

    return nodes, children_by_leader


def _tree_from_node_index(root_id, nodes: dict, children_by_leader: dict, max_depth: int = 3) -> dict:
    """Materializa el árbol de una raíz a partir del índice, recortado a `max_depth`.

    Copia los nodos en lugar de mutarlos para que el índice pueda reutilizarse
    en varias raíces (necesario en el cuadro de honor).
    """
    root_key = utils._customer_id_str(root_id)
    if root_key not in nodes:
        return {"id": str(root_id), "name": "", "level": "", "monthSpend": 0.0, "children": []}

    def _build(cid, depth, visited):
        node = dict(nodes[cid])
        if depth >= max_depth:
            node["children"] = []
            return node
        node["children"] = [
            _build(child_id, depth + 1, visited | {child_id})
            for child_id in children_by_leader.get(cid, [])
            if child_id in nodes and child_id not in visited
        ]
        return node

    return _build(root_key, 0, {root_key})


def _build_network_tree_with_month(root_id, month_key: str, customers_raw: list, cfg: dict,
                                   max_depth=3, month_states: dict = None) -> dict:
    nodes, children_by_leader = _build_month_node_index(month_key, customers_raw, cfg, month_states)
    return _tree_from_node_index(root_id, nodes, children_by_leader, max_depth)

def _network_members_from_tree(root: dict, max_rows: int = 30) -> list:
    rows = []
    for n in _flatten_tree(root):
        if n.get("depth", 0) == 0:
            continue
        spend = n.get("monthSpend", 0.0)
        status = "Activa" if n.get("isActive") else ("En progreso" if spend > 0 else "Inactiva")
        rows.append({
            "name": n.get("name") or "", "level": f"L{n.get('depth')}",
            "spend": spend, "status": status,
            "id": n.get("id"), "leaderId": n.get("leaderId"),
        })
        if len(rows) >= max_rows:
            break
    return rows

# --- VP / VG HELPERS (inline, sin importar commissions_lambda) ---

def _mxn_to_vp_dash(net_mxn: float, mxn_per_vp: float) -> float:
    return net_mxn / mxn_per_vp if mxn_per_vp > 0 else 0.0

def _calc_vg_from_tree(root_tree: dict, mxn_per_vp: float) -> float:
    """Suma el monthSpend de todos los nodos del árbol y convierte a VP."""
    total_mxn = 0.0
    for n in _flatten_tree(root_tree):
        total_mxn += float(n.get("monthSpend", 0))
    return _mxn_to_vp_dash(total_mxn, mxn_per_vp)

def _postorder_node_ids(nodes: dict, children_by_leader: dict) -> list:
    """Ids en orden post-orden (hijos antes que padres), iterativo y sin ciclos."""
    order = []
    visited = set()
    roots = [
        cid for cid, node in nodes.items()
        if not node.get("leaderId") or node["leaderId"] not in nodes
    ]
    stack = [(cid, False) for cid in roots]
    while stack:
        cid, expanded = stack.pop()
        if expanded:
            order.append(cid)
            continue
        if cid in visited:
            continue
        visited.add(cid)
        stack.append((cid, True))
        for child_id in children_by_leader.get(cid, []):
            if child_id in nodes and child_id not in visited:
                stack.append((child_id, False))

    # Nodos en un ciclo o con líder inexistente: no se alcanzan desde ninguna raíz.
    for cid in nodes:
        if cid not in visited:
            visited.add(cid)
            order.append(cid)
    return order


def _aggregate_vg_by_node(nodes: dict, children_by_leader: dict, vp_by_id: dict,
                          max_levels: int) -> dict:
    """VG de TODOS los nodos en una sola pasada, O(N × max_levels).

    Para cada nodo se guarda el VP acumulado por nivel de profundidad
    (`acc[d]` = VP de los descendientes a exactamente `d` niveles). En orden
    post-orden, el vector de un padre es el de sus hijos desplazado un nivel,
    así que el VG (suma del vector) sale sin recorrer la subred de cada nodo.
    """
    levels = {}
    for cid in _postorder_node_ids(nodes, children_by_leader):
        acc = [0.0] * (max_levels + 1)
        acc[0] = vp_by_id.get(cid, 0.0)
        for child_id in children_by_leader.get(cid, []):
            child_acc = levels.get(child_id)
            if not child_acc:
                continue
            for depth in range(1, max_levels + 1):
                acc[depth] += child_acc[depth - 1]
        levels[cid] = acc
    return {cid: sum(acc) for cid, acc in levels.items()}


def _get_rank_dash(vg: float, rank_thresholds: list, vp: float = None) -> str:
    """
    Rango para el dashboard. Si se pasa `vp` (PC personales), exige también `vpMin`
    (Plan abril 2026 §6). No evalúa líneas ni líderes (display aproximado).
    """
    rank = ""
    for rt in sorted(rank_thresholds, key=lambda x: float(x.get("vgMin", 0))):
        if vg < float(rt.get("vgMin", 0) or 0):
            continue
        if vp is not None and vp < float(rt.get("vpMin", 0) or 0):
            continue
        rank = rt.get("rank", "")
    return rank

def _get_direct_vg_dash(cid: str, month_key: str, customers_raw: list, mxn_per_vp: float) -> float:
    """Suma el VP de los referidos directos del cliente."""
    total = 0.0
    for c in customers_raw:
        if str(c.get("leaderId", "")) == str(cid):
            st = _get_month_state(str(c.get("customerId", "")), month_key)
            total += float(utils._to_decimal(st.get("netVolume", 0)))
    return _mxn_to_vp_dash(total, mxn_per_vp)

def _count_direct_at_rank_dash(cid: str, month_key: str, customers_raw: list,
                                required_rank: str, mxn_per_vp: float, rank_thresholds: list) -> int:
    count = 0
    for c in customers_raw:
        if str(c.get("leaderId", "")) != str(cid):
            continue
        did = str(c.get("customerId", ""))
        # Build a small tree just for this direct to get their VG (up to 5 levels is expensive; use netVolume as proxy for simplicity)
        st = _get_month_state(did, month_key)
        direct_net = float(utils._to_decimal(st.get("netVolume", 0)))
        direct_vg = _mxn_to_vp_dash(direct_net, mxn_per_vp)
        if _get_rank_dash(direct_vg, rank_thresholds) == required_rank:
            count += 1
    return count

def _build_goals(customer: dict, root_tree: dict, customers_raw: list, cfg: dict,
                 bonus_cfg=None, month_states=None) -> list:
    bonus_cfg    = bonus_cfg or {}
    vp_cfg       = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp   = float(vp_cfg.get("mxnPerVp", 50))
    rank_thresh  = bonus_cfg.get("rankThresholds") or []
    bonus_rules  = [r for r in (bonus_cfg.get("rules") or []) if r.get("active")]

    # Unidad de activación ahora en VP
    activation_vp = float(utils._to_decimal(cfg.get("activationNetMin", 50)))
    tiers = [{"min": float(utils._to_decimal(t.get("min"))), "rate": float(utils._to_decimal(t.get("rate")))} for t in (cfg.get("discountTiers") or [])]
    tiers.sort(key=lambda x: x["rate"])
    level_rates = [0.30, 0.40, 0.50]

    cid       = str(customer.get("customerId"))
    month_key = utils._month_key()
    st        = _get_month_state(cid, month_key, month_states)
    my_net    = utils._to_decimal(st.get("netVolume", 0))
    my_vp     = _mxn_to_vp_dash(float(my_net), mxn_per_vp)
    my_vg     = _calc_vg_from_tree(root_tree, mxn_per_vp)
    my_active = my_vp >= activation_vp

    now_dt      = datetime.now(timezone.utc)
    month_start = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Contar nuevos directos este mes
    new_direct = sum(
        1 for c in customers_raw
        if str(c.get("leaderId") or "") == cid and c.get("createdAt", "") >= month_start.isoformat()
    )

    # Métricas de red
    tree_nodes = _flatten_tree(root_tree)
    any_member_active = any(n.get("isActive") and n.get("depth", 0) > 0 for n in tree_nodes)
    direct_children   = [n for n in tree_nodes if n.get("depth") == 1]
    all_direct_ok     = bool(direct_children) and all(n.get("isActive") for n in direct_children)
    tree_ids          = {n["id"] for n in tree_nodes}
    any_member_added  = any(
        str(c.get("leaderId") or "") in tree_ids and c.get("createdAt", "") >= month_start.isoformat()
        for c in customers_raw
    )

    goals = []

    # ── Meta de activación (VP) ──────────────────────────────────────────────
    goals.append({
        "key": "active",
        "title": "Alcanzar VP mínimo (usuario activo)",
        "subtitle": f"Meta mensual: {activation_vp:.0f} VP",
        "target": activation_vp, "base": round(my_vp, 2), "cart": 0,
        "achieved": my_active, "locked": False, "isCountGoal": False,
        "unit": "vp", "ctaText": "Ir a tienda", "ctaFragment": "merchant",
    })

    # ── Metas de descuento (MXN) — se mantienen para el sistema de descuentos ─
    def tier_min_for_rate(rate_threshold):
        for t in tiers:
            if t["rate"] >= rate_threshold:
                return t["min"]
        return float(my_net)

    for idx, r in enumerate(level_rates, start=1):
        target = tier_min_for_rate(r)
        goals.append({
            "key": f"discount_{idx}",
            "title": f"Alcanzar nivel {idx} de descuento ({int(r*100)}%)",
            "subtitle": f"Consumo objetivo desde ${int(target):,} MXN",
            "target": target, "base": float(my_net), "cart": 0,
            "achieved": float(my_net) >= target, "locked": False, "isCountGoal": False,
            "unit": "mxn", "ctaText": "Completar consumo", "ctaFragment": "merchant",
        })

    # ── Meta: invitar ────────────────────────────────────────────────────────
    goals.insert(2, {
        "key": "invite", "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": "Invita a 1 persona y actívala",
        "target": 1, "base": int(new_direct), "cart": 0,
        "achieved": bool(new_direct >= 1), "locked": False, "isCountGoal": True,
        "unit": "count", "ctaText": "Invitar ahora", "ctaFragment": "links",
    })

    # ── Meta: miembro activo en red ──────────────────────────────────────────
    goals.insert(4, {
        "key": "network_one_active", "title": "Lograr que un miembro de la red alcance su meta",
        "subtitle": f"Meta por miembro: {activation_vp:.0f} VP",
        "target": 1, "base": 1 if any_member_active else 0, "cart": 0,
        "achieved": any_member_active, "locked": False, "isCountGoal": True,
        "unit": "count", "ctaText": "Compartir enlace", "ctaFragment": "links",
    })

    direct_count = len(direct_children)
    goals.insert(6, {
        "key": "direct_all_active",
        "title": "Todos los directos logran su meta",
        "subtitle": "Aún no tienes miembros directos" if not direct_count else f"Directos: {direct_count}",
        "target": direct_count if direct_count else 1,
        "base": direct_count if all_direct_ok else 0, "cart": 0,
        "achieved": bool(all_direct_ok and direct_count > 0), "locked": not direct_count,
        "isCountGoal": True, "unit": "count", "ctaText": "Impulsar a mi red", "ctaFragment": "links",
    })

    goals.append({
        "key": "network_member_invited", "title": "Tu red replica: un miembro agrega a otro",
        "subtitle": "Haz que tu red crezca sola",
        "target": 1, "base": 1 if any_member_added else 0, "cart": 0,
        "achieved": bool(any_member_added), "locked": False, "isCountGoal": True,
        "unit": "count", "ctaText": "Compartir enlace", "ctaFragment": "links",
    })

    # ── Metas de Rango (VG) — una por cada umbral configurado ───────────────
    for rt in sorted(rank_thresh, key=lambda x: float(x.get("vgMin", 0))):
        rank_name  = rt.get("rank", "")
        vg_min     = float(rt.get("vgMin", 0))
        achieved   = my_vg >= vg_min
        goals.append({
            "key": f"rank_{rank_name.lower()}",
            "title": f"Alcanzar rango {rank_name}",
            "subtitle": f"VG mínimo: {vg_min:,.0f} VP",
            "target": vg_min, "base": round(my_vg, 2), "cart": 0,
            "achieved": achieved, "locked": False, "isCountGoal": False,
            "unit": "vp", "rank": rank_name,
            "ctaText": "Impulsar tu red", "ctaFragment": "red",
        })

    # ── Metas de Bonos (una por cada regla activa) ───────────────────────────
    direct_vg = None  # se calcula lazy

    for rule in bonus_rules:
        rule_id   = rule.get("id", "")
        rule_name = rule.get("name", "")

        # Determinar condición principal para mostrar el progreso
        main_cond = None
        for cond in rule.get("conditions", []):
            if cond.get("type") in ("vg_min", "vp_min", "direct_vg_min"):
                main_cond = cond
                break
        if not main_cond:
            continue  # sin condición cuantificable, no genera meta visual

        ctype  = main_cond.get("type")
        target = float(main_cond.get("value") or 0)
        if target <= 0:
            continue

        if ctype == "vg_min":
            base_val = round(my_vg, 2)
        elif ctype == "vp_min":
            base_val = round(my_vp, 2)
        elif ctype == "direct_vg_min":
            if direct_vg is None:
                direct_vg = _get_direct_vg_dash(cid, month_key, customers_raw, mxn_per_vp)
            base_val = round(direct_vg, 2)
        else:
            continue

        achieved = base_val >= target

        goals.append({
            "key": f"bonus_{rule_id}",
            "title": rule_name,
            "subtitle": rule.get("notes") or f"Meta: {target:,.0f} VP",
            "target": target, "base": base_val, "cart": 0,
            "achieved": achieved, "locked": False, "isCountGoal": False,
            "unit": "vp", "bonusRuleId": rule_id,
            "ctaText": "Ver bonos", "ctaFragment": "volumen",
        })

    primary_idx = next((i for i, g in enumerate(goals) if not g.get("locked") and not g.get("achieved")), None)
    for i, g in enumerate(goals):
        g["primary"]   = (primary_idx == i)
        g["secondary"] = (primary_idx is not None and primary_idx != i)
        g.setdefault("cart", 0)

    return goals

def _compute_buy_again_ids(customer: dict, products_raw: list) -> list:
    if not customer or not isinstance(customer, dict):
        return []
    counts = customer.get("productCounts")
    if not isinstance(counts, dict) or not counts:
        return []
    active_ids = {str(p.get("productId")) for p in products_raw if _is_product_active(p)}
    ordered = sorted(counts.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
    return [str(pid) for pid, _ in ordered if str(pid) in active_ids][:3]

def _active_notifications_for_customer(customer_id) -> list:
    if customer_id in (None, ""):
        return []
    now_str = utils._now_iso()[:10]  # YYYY-MM-DD para comparación simple

    # Leer IDs ya leídas
    try:
        # _query_all_pages recorre LastEvaluatedKey: con una sola página, las
        # notificaciones ya leídas reaparecían como no leídas al pasar de 1 MB.
        read_items = utils._query_all_pages(
            KeyConditionExpression=utils.Key("PK").eq(f"NOTIFICATION_READ#{customer_id}")
        )
        read_ids = {item.get("SK") for item in read_items}
    except Exception:
        read_ids = set()

    notifications = []
    for item in utils._query_bucket("NOTIFICATION"):
        if not bool(item.get("active", True)):
            continue
        nid = str(item.get("notificationId") or "").strip()
        if not nid:
            continue
        start_at = (item.get("startAt") or "")[:10]
        end_at = (item.get("endAt") or "")[:10]
        if start_at and now_str < start_at:
            continue
        if end_at and now_str > end_at:
            continue
        notifications.append({
            "id": nid, "title": item.get("title"), "description": item.get("description"),
            "linkUrl": item.get("linkUrl"), "startAt": item.get("startAt"), "endAt": item.get("endAt"),
            "read": nid in read_ids, "status": "active",
        })

    notifications.sort(key=lambda x: (x.get("startAt") or "", x.get("id") or ""), reverse=True)
    return notifications

def _find_effective_sponsor(customer) -> dict:
    if not customer or not isinstance(customer, dict):
        return {"name": None, "phone": None, "whatsapp": None}
    leader_id = customer.get("leaderId")
    if leader_id in (None, ""):
        return {"name": None, "phone": None, "whatsapp": None}
    sponsor = utils._get_by_id("CUSTOMER", int(leader_id))
    if not sponsor:
        return {"name": None, "phone": None, "whatsapp": None}
    phone = sponsor.get("phone") or ""
    return {
        "name": sponsor.get("name"), "phone": phone,
        "whatsapp": f"https://wa.me/52{phone}" if phone else None,
    }

def _resolve_user_context(query: dict, headers: dict):
    """Devuelve (user_id, is_guest)."""
    user_id_raw = (query or {}).get("userId") or (headers or {}).get("x-user-id")
    if user_id_raw is not None:
        try:
            return int(user_id_raw), False
        except (ValueError, TypeError):
            return str(user_id_raw), False

    email_raw = (query or {}).get("email") or (headers or {}).get("x-user-email")
    if email_raw:
        email_norm = email_raw.strip().lower()
        auth = utils._get_by_id("AUTH", email_norm)
        if auth and auth.get("customerId") is not None:
            return auth.get("customerId"), False

    return None, True

# --- TAREA DE ORQUESTACIÓN: SYNC S3 TABLES ---

def handle_sync_iceberg(order_id):
    """
    Invocado por Step Functions.
    Crea un registro optimizado en S3 (Iceberg) para consultas SQL masivas.
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order: return {"status": "NOT_FOUND"}

    # Aquí se enviaría el dato a un Glue DataBrew o se escribiría directamente
    # como Parquet en la ruta de S3 Tables. 
    # Por ahora, simulamos el éxito de la integración analítica.
    print(f"[ANALYTICS] Sincronizando orden {order_id} a S3 Tables...")
    return {"status": "SYNCED", "orderId": order_id}

# --- HELPERS DE ATHENA (REPORTES) ---

def _query_athena(sql):
    """Ejecuta SQL y retorna el primer registro (para KPIs)."""
    try:
        execution = athena.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={'Database': ATHENA_DB},
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT}
        )
        query_id = execution['QueryExecutionId']
        
        # Espera simple (Máximo 5 segundos para mantener UX)
        for _ in range(5):
            state = athena.get_query_execution(QueryExecutionId=query_id)['QueryExecution']['Status']['State']
            if state == 'SUCCEEDED': break
            if state in ['FAILED', 'CANCELLED']: return None
            time.sleep(1)
        
        results = athena.get_query_results(QueryExecutionId=query_id)
        rows = results['ResultSet']['Rows']
        if len(rows) < 2: return {}
        
        headers = [c['VarCharValue'] for c in rows[0]['Data']]
        values = [c.get('VarCharValue', '0') for c in rows[1]['Data']]
        return dict(zip(headers, values))
    except Exception as e:
        print(f"[ATHENA_ERROR] {e}")
        return None

# --- HANDLERS ADMIN (GRANULARES) ---

def get_admin_stats():
    """GET /admin/stats - Usa S3 Tables (Athena)"""
    month = utils._month_key()
    sql = f"""
        SELECT sum(netTotal) as total_sales, count(*) as order_count 
        FROM orders_iceberg WHERE monthKey = '{month}'
    """
    stats = _query_athena(sql)
    return utils._json_response(200, {"stats": stats or {"total_sales": 0, "order_count": 0}})

def get_admin_orders(query):
    """GET /admin/orders?status=X&limit=N - Órdenes filtradas por status"""
    limit = int(query.get("limit", 50))
    status_filter = (query.get("status") or "").lower().strip()
    items = utils._query_bucket("ORDER", forward=False)
    if status_filter:
        items = [o for o in items if (o.get("status") or "").lower() == status_filter]
    total = len(items)
    items = items[:limit]
    return utils._json_response(200, {"orders": items, "total": total, "limit": limit})

def get_admin_warnings():
    """GET /admin/warnings - Alertas reales desde DynamoDB"""
    cfg = utils._load_app_config()
    warning_cfg = cfg.get("adminWarnings") if isinstance(cfg.get("adminWarnings"), dict) else {}

    orders = utils._query_bucket("ORDER")
    now_date = utils._now_iso()[:10]

    paid_no_ship = sum(1 for o in orders if (o.get("status") or "").lower() == "paid")
    pending_pay = sum(1 for o in orders if (o.get("status") or "").lower() == "pending")

    # Comisiones pendientes de depositar (status CONFIRMED, sin recibo).
    # Esta query leía UNA sola página: con más de 1 MB de meses contables el
    # aviso salía corto y se dejaban de pagar comisiones sin ninguna señal.
    from boto3.dynamodb.conditions import Key as _Key
    try:
        comm_items = utils._query_all_pages(
            KeyConditionExpression=_Key("PK").eq("COMMISSION_MONTH")
        )
    except Exception:
        comm_items = []
    commissions_count = sum(
        1 for item in comm_items
        if utils._to_decimal(item.get("totalConfirmed")) > 0 and (item.get("status") or "") != "PAID"
    )

    # Transferencias pendientes
    transfers = utils._query_bucket("STOCK_TRANSFER")
    pending_transfers = sum(1 for t in transfers if (t.get("status") or "").lower() == "pending")

    # Ventas POS de hoy
    pos_sales_today = sum(
        1 for s in utils._query_bucket("POS_SALE", sk_prefix=now_date)
        if str(s.get("createdAt") or "")[:10] == now_date
    )

    warnings = []
    if warning_cfg.get("showCommissions", True) and commissions_count:
        warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
    if warning_cfg.get("showShipping", True) and paid_no_ship:
        warnings.append({"type": "shipping", "text": f"{paid_no_ship} pedidos pagados sin envío", "severity": "medium"})
    if warning_cfg.get("showPendingPayments", True) and pending_pay:
        warnings.append({"type": "payments", "text": f"{pending_pay} pedidos pendientes de pago", "severity": "low"})
    if warning_cfg.get("showPendingTransfers", True) and pending_transfers:
        warnings.append({"type": "stocks", "text": f"{pending_transfers} transferencias pendientes por recibir", "severity": "medium"})
    if warning_cfg.get("showPosSalesToday", True) and pos_sales_today:
        warnings.append({"type": "pos", "text": f"{pos_sales_today} ventas POS registradas hoy", "severity": "low"})

    return utils._json_response(200, {"warnings": warnings})

# --- HANDLERS USUARIO (GRANULARES) ---

def _notify_goal_achievements(customer: dict, new_goals: list, bonus_cfg: dict) -> None:
    """
    Compara las metas recién calculadas con las almacenadas en el registro del cliente.
    Por cada meta que transicionó de achieved=False a achieved=True envía un correo.
    Para metas de bono que aún no se logran pero tienen progreso, adjunta mensaje motivacional.
    """
    try:
        cust_email = str(customer.get("email") or "")
        cust_name  = str(customer.get("name") or "Usuario")
        if not cust_email:
            return

        prev_goals_raw = customer.get("goals") or []
        prev_achieved  = {g.get("key") for g in prev_goals_raw if g.get("achieved")}

        bonus_rules_map = {r.get("id"): r for r in (bonus_cfg.get("rules") or []) if r.get("active")}

        for goal in new_goals:
            key      = goal.get("key", "")
            achieved = bool(goal.get("achieved"))
            if not achieved or key in prev_achieved:
                continue  # no es nueva transición

            title   = goal.get("title", "Meta")
            rewards = _goal_reward_lines(goal, bonus_rules_map)

            # Para metas de bono: añadir mensaje "N meses más"
            approaching_msg = _bonus_approaching_msg(goal, bonus_rules_map)

            subj, txt, html = _build_goal_achieved_email(
                name=cust_name,
                goal_title=title,
                reward_lines=rewards,
                bonus_approaching=approaching_msg,
            )
            utils._send_ses_email(cust_email, subj, txt, html)

    except Exception as ex:
        print(f"[GOAL_EMAIL_ERROR] {ex}")


def _goal_reward_lines(goal: dict, bonus_rules_map: dict) -> list:
    """Genera lista de strings describiendo los beneficios de la meta."""
    key = goal.get("key", "")
    title = goal.get("title", "")

    # Metas de descuento
    if key.startswith("discount_"):
        pct = int(float(goal.get("target", 0)))
        return [f"Descuento del {pct}% en tus compras"]

    if key == "active":
        return ["Usuario activo — acceso a comisiones y bonos del mes"]

    if key == "new_direct":
        return ["¡Nuevo miembro directo en tu red!", "Potencial de comisión incrementado"]

    if key in ("network_one_active", "all_direct_active"):
        return ["Tu red está activa", "Comisiones de red desbloqueadas"]

    if key == "network_grow":
        return ["Tu red ha crecido este mes", "Bonos de expansión disponibles"]

    # Metas de rango / VG
    if key.startswith("rank_"):
        return [f"¡Alcanzaste el rango {title}!", "Bonos especiales desbloqueados"]

    # Metas de bono
    rule_id = goal.get("bonusRuleId") or ""
    rule    = bonus_rules_map.get(rule_id) or {}
    rule_rewards = rule.get("rewards") or []
    lines = []
    for r in rule_rewards:
        rtype = r.get("type")
        if rtype == "cash_mxn" and r.get("amount"):
            lines.append(f"${r['amount']:,.0f} MXN en efectivo")
        elif rtype == "monthly_cash" and r.get("amount"):
            lines.append(f"${r['amount']:,.0f} MXN/mes")
        elif rtype == "item" and r.get("itemLabel"):
            lines.append(r["itemLabel"])
        elif rtype == "annual_fund_pct" and r.get("pct"):
            lines.append(f"{r['pct']}% del fondo anual")
    return lines or [title]


def _bonus_approaching_msg(goal: dict, bonus_rules_map: dict) -> str:
    """
    Si la meta es un bono y el bono tiene condición de meses mínimos,
    devuelve el mensaje motivacional. Para metas ya logradas indica cuántos
    meses falta para el siguiente umbral si aplica.
    """
    rule_id = goal.get("bonusRuleId") or ""
    if not rule_id:
        return ""

    rule = bonus_rules_map.get(rule_id) or {}
    # Buscar condición de meses mínimos consecutivos
    months_required = 0
    for cond in (rule.get("conditions") or []):
        if cond.get("type") in ("months_min", "months_consecutive", "months_active"):
            months_required = int(cond.get("value") or 0)
            break

    if months_required <= 1:
        return ""  # el bono no requiere acumular meses

    # Calcular cuántos meses ya lleva con la meta lograda
    # Esto requeriría historial; usamos la estimación basada en progreso
    base  = float(goal.get("base") or 0)
    target = float(goal.get("target") or 1)
    pct   = min(base / target, 1.0) if target > 0 else 1.0
    # Estimar meses completados de la acumulación
    months_done   = max(1, round(pct * months_required))
    months_left   = max(0, months_required - months_done)

    bonus_name = rule.get("name") or goal.get("title") or "este bono"
    if months_left <= 0:
        return ""
    return (f"Estás más cerca de obtener \"{bonus_name}\". "
            f"Mantente constante {months_left} mes{'es' if months_left != 1 else ''} más para obtenerlo.")


def get_user_performance(user_id):
    """GET /user/performance - Metas y Volumen"""
    app_cfg   = utils._load_app_config()
    cfg       = app_cfg.get("rewards") or {}
    bonus_cfg = app_cfg.get("bonuses") or {}
    vp_cfg    = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp    = float(vp_cfg.get("mxnPerVp", 50))
    activation_vp = float(utils._to_decimal(cfg.get("activationNetMin", 50)))

    month_key = utils._month_key()
    state     = utils._get_by_id("ASSOCIATE_MONTH", f"{user_id}#{month_key}")
    net_vol   = utils._to_decimal(state.get("netVolume") if state else 0)
    vp        = _mxn_to_vp_dash(float(net_vol), mxn_per_vp)

    return utils._json_response(200, {
        "monthKey": month_key,
        "netVolume": float(net_vol),
        "vp": round(vp, 2),
        "isActive": vp >= activation_vp,
        "activationVp": activation_vp,
    })

def get_user_commissions(user_id):
    """GET /user/commissions - Saldo actual"""
    month_key = utils._month_key()
    comm_item = utils._table.get_item(
        Key={"PK": "COMMISSION_MONTH", "SK": f"#BENEFICIARY#{user_id}#MONTH#{month_key}"}
    ).get("Item", {})

    return utils._json_response(200, {
        "pending": float(utils._to_decimal(comm_item.get("totalPending", 0))),
        "confirmed": float(utils._to_decimal(comm_item.get("totalConfirmed", 0))),
        "blocked": float(utils._to_decimal(comm_item.get("totalBlocked", 0)))
    })

# --- HANDLERS USUARIO COMPLETOS ---

def get_user_dashboard(query: dict, headers: dict) -> dict:
    """GET /user-dashboard - Dashboard completo del socio/invitado"""
    user_id, is_guest = _resolve_user_context(query, headers)
    customer = utils._get_by_id("CUSTOMER", int(user_id)) if user_id is not None else None

    # Cargar productos y campañas
    products_raw = utils._query_bucket("PRODUCT")
    campaigns_raw = utils._query_bucket("CAMPAIGN")

    products = []
    featured = []
    for item in products_raw:
        if not _is_product_active(item):
            continue
        # Excluir productos que no están habilitados para la tienda en línea
        if not bool(item.get("inOnlineStore", True)):
            continue
        s = _get_product_summary(item)
        products.append({
            "id": s["id"], "name": s["name"], "price": s["price"],
            "badge": s["badge"], "img": s["img"], "description": s["description"],
            "copyFacebook": s["copyFacebook"], "copyInstagram": s["copyInstagram"], "copyWhatsapp": s["copyWhatsapp"],
            "variants": s["variants"], "categoryIds": s["categoryIds"],
            "tags": s["tags"],
            "inOnlineStore": s["inOnlineStore"],
            "inPOS": s["inPOS"],
            "commissionable": s["commissionable"],
        })
        if len(featured) < 4:
            imgs = item.get("images") or []
            featured.append({
                "id": s["id"], "label": s["name"], "hook": s.get("hook") or "",
                "story": _pick_product_image(imgs, ["redes"]) or s["img"],
                "feed": _pick_product_image(imgs, ["miniatura", "redes"]) or s["img"],
                "banner": _pick_product_image(imgs, ["landing"]) or s["img"],
            })

    campaigns = [_campaign_payload(c) for c in campaigns_raw if bool(c.get("active", True))]

    # Producto del mes
    pom_item = utils._get_by_id("PRODUCT_OF_MONTH", "current")
    product_of_month = None
    if pom_item:
        p = utils._get_by_id("PRODUCT", int(pom_item.get("productId")))
        if _is_product_active(p):
            product_of_month = _get_product_summary(p)

    app_cfg   = utils._load_app_config()
    cfg       = app_cfg.get("rewards") or {}
    bonus_cfg = app_cfg.get("bonuses") or {}
    vp_cfg    = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp   = float(vp_cfg.get("mxnPerVp", 50))
    rank_thresh  = bonus_cfg.get("rankThresholds") or []

    month_key      = utils._month_key()
    prev_month_key = _prev_month_key()

    computed_network, computed_goals, buy_again_ids = [], [], []
    commission_summary = None
    active_notifications = []
    vp_val, vg_val, rank_val = 0.0, 0.0, ""
    bonus_awards = []

    if customer and isinstance(customer, dict):
        # Solo el cliente y su descendencia (árbol persistido + BatchGetItem),
        # en lugar de leer la colección CUSTOMER completa y hacer un GetItem
        # de ASSOCIATE_MONTH por cada cliente del sistema.
        max_network_levels = int(vp_cfg.get("maxNetworkLevels", 5))
        customers_raw, _scope_meta = utils._load_network_scope(customer, max_depth=max_network_levels)
        month_states = utils._load_month_states(
            [c.get("customerId") for c in customers_raw], month_key
        )
        tree = _build_network_tree_with_month(
            str(customer.get("customerId")), month_key, customers_raw, cfg,
            max_depth=max_network_levels, month_states=month_states,
        )
        computed_network = _network_members_from_tree(tree, max_rows=30)
        computed_goals   = _build_goals(customer, tree, customers_raw, cfg,
                                        bonus_cfg=bonus_cfg, month_states=month_states)
        buy_again_ids    = _compute_buy_again_ids(customer, products_raw)
        active_notifications = _active_notifications_for_customer(customer.get("customerId"))

        # Calcular VP, VG, rango
        cid = str(customer.get("customerId", ""))
        st  = _get_month_state(cid, month_key, month_states)
        my_net = float(utils._to_decimal(st.get("netVolume", 0)))
        vp_val = _mxn_to_vp_dash(my_net, mxn_per_vp)
        vg_val = _calc_vg_from_tree(tree, mxn_per_vp)
        rank_val = _get_rank_dash(vg_val, rank_thresh, vp=vp_val)

        # Bonos del mes. SK = "{createdAt}#{id}"; un award de `month_key` nunca
        # se crea antes de ese mes, así que `sk_from` acota sin perder filas
        # (a diferencia de begins_with, que perdería los emitidos al cierre).
        bonus_awards = [
            a for a in utils._query_bucket("BONUS_AWARD", sk_from=month_key)
            if str(a.get("customerId", "")) == cid and a.get("monthKey") == month_key
        ]

        # Detectar metas recién logradas (transición False → True) y enviar correo
        _notify_goal_achievements(customer, computed_goals, bonus_cfg)

        # Persistir estado del dashboard en el cliente
        try:
            utils._update_by_id(
                "CUSTOMER", customer.get("customerId"),
                "SET goals = :g, networkMembers = :n, buyAgainIds = :b, updatedAt = :u",
                {":g": computed_goals, ":n": computed_network, ":b": buy_again_ids, ":u": utils._now_iso()},
            )
        except Exception:
            pass

        cid = int(customer.get("customerId"))
        # Comisiones mes actual
        sk_curr = f"#BENEFICIARY#{cid}#MONTH#{month_key}"
        comm_item = utils._table.get_item(Key={"PK": "COMMISSION_MONTH", "SK": sk_curr}).get("Item") or {}
        pend = utils._to_decimal(comm_item.get("totalPending"))
        conf = utils._to_decimal(comm_item.get("totalConfirmed"))
        blocked = utils._to_decimal(comm_item.get("totalBlocked"))

        # Comisiones mes anterior
        sk_prev = f"#BENEFICIARY#{cid}#MONTH#{prev_month_key}"
        prev_comm = utils._table.get_item(Key={"PK": "COMMISSION_MONTH", "SK": sk_prev}).get("Item") or {}
        prev_confirmed = utils._to_decimal(prev_comm.get("totalConfirmed"))

        # Comprobante mes anterior
        receipt_url = ""
        # Un comprobante del mes previo se emite en ese mes o después.
        for r in utils._query_bucket("COMMISSION_RECEIPT", sk_from=prev_month_key):
            if int(r.get("customerId") or 0) != cid:
                continue
            if str(r.get("monthKey")) != str(prev_month_key):
                continue
            if r.get("assetUrl"):
                receipt_url = r.get("assetUrl")
                break

        clabe = (customer.get("clabeInterbancaria") or customer.get("clabe") or "").strip()
        if prev_confirmed <= 0:
            prev_status = "no_moves"
        elif receipt_url:
            prev_status = "paid"
        else:
            prev_status = "pending"

        commission_summary = {
            "monthKey": month_key, "totalPending": float(pend), "totalConfirmed": float(conf),
            "totalBlocked": float(blocked),
            "ledger": comm_item.get("ledger") if isinstance(comm_item.get("ledger"), list) else [],
            "hasPending": pend > 0, "hasConfirmed": conf > 0,
            "clabeOnFile": bool(clabe), "clabeLast4": clabe[-4:] if clabe else "",
            "payoutDay": int(utils._to_decimal(cfg.get("payoutDay", 10))),
            "paidTotal": float(prev_confirmed),
            "receiptUrl": receipt_url, "prevReceiptUrl": receipt_url, "prevStatus": prev_status,
        }
    else:
        buy_again_ids = [str(p["id"]) for p in products[:3]]

    user_payload = None
    if customer and isinstance(customer, dict):
        dr = utils._to_decimal(customer.get("discountRate"))
        user_payload = {
            "discountPercent": int((dr * 100).quantize(utils.D_ONE)) if dr else 0,
            "discountActive": bool(customer.get("activeBuyer") or dr > 0),
        }

    # Categorías activas para el catálogo
    categories_raw = utils._query_bucket("PRODUCT_CATEGORY")
    categories = [
        {
            "id": str(c.get("categoryId") or c.get("id") or ""),
            "name": str(c.get("name") or ""),
            "parentId": c.get("parentId"),
            "position": int(c.get("position") or 0),
            "active": bool(c.get("active", True)),
        }
        for c in categories_raw
        if bool(c.get("active", True))
    ]

    return utils._json_response(200, {
        "isGuest": bool(is_guest),
        "settings": {
            "cutoffDay": 25, "cutoffHour": 23, "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id), "networkGoal": 300,
        },
        "user": user_payload,
        "sponsor": _find_effective_sponsor(customer),
        "goals": computed_goals,
        "products": products, "featured": featured, "productOfMonth": product_of_month,
        "campaigns": campaigns,
        "categories": categories,
        "notifications": active_notifications,
        "networkMembers": computed_network, "buyAgainIds": buy_again_ids,
        "commissions": commission_summary,
        "vp": round(vp_val, 2),
        "vg": round(vg_val, 2),
        "rank": rank_val,
        "bonuses": bonus_awards,
    })


# --- HONOR BOARD ---

def get_honor_board() -> dict:
    """
    GET /honor-board — Top 10 por VG y Top 10 por VP del mes actual + mes anterior para delta.
    Complejidad O(N_customers) por mes; adecuado para redes de hasta ~5 000 socios.
    """
    app_cfg    = utils._load_app_config()
    bonus_cfg  = app_cfg.get("bonuses") or {}
    vp_cfg     = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp = float(vp_cfg.get("mxnPerVp", 50))
    rank_thresh = bonus_cfg.get("rankThresholds") or []

    month_key  = utils._month_key()
    prev_mk    = _prev_month_key()

    customers_raw = utils._query_bucket("CUSTOMER")
    cfg_rewards = app_cfg.get("rewards") or {}
    max_levels = int(vp_cfg.get("maxNetworkLevels", 5))

    def _compute_ranking(mk: str):
        """Devuelve [{customerId, name, vp, vg, rank}] para el mes `mk`.

        Antes construía el árbol COMPLETO del sistema una vez por cada cliente
        (y cada construcción hacía un GetItem por cliente): 3N² operaciones,
        ~1.9 M con 800 clientes, muy por encima del timeout de Lambda.

        Ahora los estados del mes se cargan en un solo bloque y el VG de todos
        los clientes sale de un único recorrido post-orden del bosque: cada
        nodo acumula su VP y el de sus descendientes hasta `max_levels`.
        """
        month_states = utils._load_month_states(
            [c.get("customerId") for c in customers_raw if isinstance(c, dict)], mk
        )
        nodes, children_by_leader = _build_month_node_index(mk, customers_raw, cfg_rewards, month_states)

        # VP por nodo (mismo criterio que _calc_vg_from_tree: netVolume → VP).
        vp_by_id = {cid: _mxn_to_vp_dash(node["monthSpend"], mxn_per_vp) for cid, node in nodes.items()}

        vg_by_id = _aggregate_vg_by_node(nodes, children_by_leader, vp_by_id, max_levels)

        entries = []
        for cid, node in nodes.items():
            vg = vg_by_id.get(cid, 0.0)
            entries.append({
                "customerId": cid,
                "name": node.get("name") or "",
                "vp": round(vp_by_id.get(cid, 0.0), 2),
                "vg": round(vg, 2),
                "rank": _get_rank_dash(vg, rank_thresh),
            })
        return entries

    # Cálculo mes actual
    current = _compute_ranking(month_key)

    # Top 10 por VG
    by_vg_sorted = sorted(current, key=lambda e: e["vg"], reverse=True)[:10]
    # Top 10 por VP
    by_vp_sorted = sorted(current, key=lambda e: e["vp"], reverse=True)[:10]

    # Posición anterior para delta (mes previo)
    prev = _compute_ranking(prev_mk)
    prev_vg_pos = {e["customerId"]: i + 1 for i, e in enumerate(sorted(prev, key=lambda e: e["vg"], reverse=True)[:10])}
    prev_vp_pos = {e["customerId"]: i + 1 for i, e in enumerate(sorted(prev, key=lambda e: e["vp"], reverse=True)[:10])}

    def _enrich(entries, prev_pos_map):
        result = []
        for i, e in enumerate(entries):
            entry = {**e, "position": i + 1}
            prev_pos = prev_pos_map.get(e["customerId"])
            if prev_pos is not None:
                entry["prevPosition"] = prev_pos
            result.append(entry)
        return result

    return utils._json_response(200, {
        "monthKey": month_key,
        "byVg": _enrich(by_vg_sorted, prev_vg_pos),
        "byVp": _enrich(by_vp_sorted, prev_vp_pos),
    })


def _normalize_campaign(item: dict) -> dict:
    """Normalize a campaign item: ensure 'id' is present."""
    cid = item.get("campaignId") or item.get("id") or ""
    return {**item, "id": cid}

def _handle_campaign_asset(method, body, headers):
    """POST /dashboard/campaigns/assets — sube un asset de campana a S3."""
    err = utils._require_admin(headers, "access_screen_stocks")
    if err:
        return err
    if method != "POST":
        return utils._json_response(405, {"message": "Método no permitido"})
    name = body.get("name", "upload")
    b64_data = body.get("contentBase64")
    content_type = body.get("contentType", "image/png")
    if not b64_data:
        return utils._json_response(400, {"message": "contentBase64 requerido"})
    try:
        raw_data = base64.b64decode(b64_data)
        asset_id = f"assets/{utils.uuid.uuid4()}-{name}"
        _s3.put_object(
            Bucket=BUCKET_NAME,
            Key=asset_id,
            Body=raw_data,
            ContentType=content_type,
            ACL='public-read'
        )
        url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    except Exception as e:
        print(f"[S3_CAMPAIGN_ASSET_ERROR] {e}")
        return utils._json_response(500, {"message": "Error al subir a S3"})
    asset_item = {
        "entityType": "asset", "assetId": asset_id, "name": name,
        "url": url, "contentType": content_type, "createdAt": utils._now_iso()
    }
    utils._put_entity("ASSET", asset_id, asset_item)
    return utils._json_response(201, {"asset": asset_item})


def _handle_campaigns(method, body):
    """GET /campaigns  |  POST /campaigns — también resuelve /dashboard/campaigns"""
    if method == "GET":
        items = utils._query_bucket("CAMPAIGN")
        return utils._json_response(200, {"campaigns": [_normalize_campaign(c) for c in items]})
    if method == "POST":
        cid = body.get("id") or f"CMP-{utils.uuid.uuid4().hex[:8].upper()}"
        now = utils._now_iso()
        existing = utils._get_by_id("CAMPAIGN", cid) if body.get("id") else None
        campaign = {
            "entityType": "campaign", "campaignId": cid, "id": cid,
            "name": body.get("name"), "active": bool(body.get("active", True)),
            "type": body.get("type") or "multinivel",
            "hook": body.get("hook") or "",
            "description": body.get("description") or "",
            "banner": body.get("banner"), "story": body.get("story"), "feed": body.get("feed"),
            "heroImage": body.get("heroImage"),
            "heroBadge": body.get("heroBadge"),
            "heroTitle": body.get("heroTitle"),
            "heroAccent": body.get("heroAccent"),
            "heroTail": body.get("heroTail"),
            "heroDescription": body.get("heroDescription"),
            "ctaPrimaryText": body.get("ctaPrimaryText"),
            "ctaSecondaryText": body.get("ctaSecondaryText"),
            "benefits": body.get("benefits") or [],
            "updatedAt": now,
        }
        saved = utils._put_entity("CAMPAIGN", cid, campaign, created_at_iso=existing.get("createdAt") if existing else None)
        return utils._json_response(201, {"campaign": _normalize_campaign(saved)})
    return utils._json_response(405, {"message": "Método no permitido"})


def _handle_notifications(method, body, segments):
    """GET /notifications  |  POST /notifications  |  POST /notifications/{id}/read
    También resuelve /dashboard/notifications/* tras strip del prefijo."""
    if method == "GET":
        items = utils._query_bucket("NOTIFICATION")
        return utils._json_response(200, {"notifications": items})
    if method == "POST":
        if len(segments) == 3 and segments[2] == "read":
            ntf_id = segments[1]
            user_id = body.get("userId") or body.get("customerId")
            pk = f"NOTIFICATION_READ#{user_id}"
            utils._table.put_item(Item={
                "PK": pk, "SK": ntf_id, "readAt": utils._now_iso(), "entityType": "notificationRead"
            })
            return utils._json_response(200, {"ok": True})
        nid = body.get("id") or f"NTF-{utils.uuid.uuid4().hex[:8].upper()}"
        ntf = {
            "entityType": "notification", "notificationId": nid,
            "title": body.get("title"), "description": body.get("description"),
            "linkUrl": body.get("linkUrl"), "startAt": body.get("startAt"),
            "endAt": body.get("endAt"), "active": True, "createdAt": utils._now_iso()
        }
        saved = utils._put_entity("NOTIFICATION", nid, ntf)
        return utils._json_response(201, {"notification": saved})
    return utils._json_response(405, {"message": "Método no permitido"})


# --- LAMBDA HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    # 1. Detectar invocación de Step Functions (Sync Analítico)
    if event.get("task") == "sync_iceberg":
        return handle_sync_iceberg(event.get("orderId"))

    # 2. Peticiones de API Gateway
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    raw_segments = [s for s in path.strip("/").split("/") if s]
    # Strip "dashboard" prefix: API Gateway sends /dashboard/{proxy+}
    segments = raw_segments[1:] if raw_segments and raw_segments[0] == "dashboard" else raw_segments

    try:
        root = segments[0] if segments else ""

        # ── /admin/*  (también resuelve /dashboard/admin/* tras strip del prefijo) ─
        if root == "admin":
            err = utils._require_admin(headers, "access_screen_stats")
            if err: return err
            sub = segments[1] if len(segments) > 1 else ""
            if sub == "stats": return get_admin_stats()
            if sub == "orders": return get_admin_orders(query)
            if sub == "warnings": return get_admin_warnings()

        # ── /user/* ─────────────────────────────────────────────────────────────
        if root == "user":
            uid = headers.get("x-user-id") or query.get("userId")
            if not uid: return utils._json_response(400, {"message": "userId missing"})
            err = utils._require_self_or_admin(headers, uid)
            if err: return err
            sub = segments[1] if len(segments) > 1 else ""
            if sub == "performance": return get_user_performance(uid)
            if sub == "commissions": return get_user_commissions(uid)

        # ── /user-dashboard  ────────────────────────────────────────────────────
        if root == "user-dashboard":
            uid = headers.get("x-user-id") or query.get("userId")
            err = utils._require_self_or_admin(headers, uid)
            if err: return err
            return get_user_dashboard(query, headers)

        # ── /honor-board  (también /dashboard/honor-board) ──────────────────────
        if root == "honor-board" and method == "GET":
            return get_honor_board()

        # ── /campaigns  (también /dashboard/campaigns) ───────────────────────────
        if root == "campaigns":
            if len(segments) > 1 and segments[1] == "assets":
                return _handle_campaign_asset(method, body, headers)
            if method == "POST":
                err = utils._require_admin(headers, "access_screen_stocks")
                if err: return err
            return _handle_campaigns(method, body)

        # ── /notifications  (también /dashboard/notifications) ───────────────────
        if root == "notifications":
            if method == "POST" and not (len(segments) == 3 and segments[2] == "read"):
                err = utils._require_admin(headers, "config_manage")
                if err: return err
            return _handle_notifications(method, body, segments)

        return utils._json_response(404, {"message": "Dashboard endpoint not found"})

    except Exception as e:
        print(f"[DASHBOARD_ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Error cargando datos", "error": str(e)})
