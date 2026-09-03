"""Lógica compartida por los dashboards de socio.

`GET /customers/dashboard` (costumer_lambda) nació como copia de
`GET /user-dashboard` (dashboard_lambda) y todo este bloque —utilidades de
red, plantillas de correo de metas y normalización de catálogo— acabó
existiendo dos veces. Las copias ya habían empezado a divergir, así que un
arreglo aplicado en un módulo no llegaba al otro.

Las funciones que viven aquí se verificaron equivalentes en ambos módulos
(comparación de AST con renombrado alfa) antes de unificarse.
"""
from datetime import datetime, timezone

import core_utils as utils

FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")


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

def _prev_month_key() -> str:
    d = datetime.now(timezone.utc)
    if d.month == 1:
        return f"{d.year - 1:04d}-12"
    return f"{d.year:04d}-{d.month - 1:02d}"

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

def _campaign_payload(item: dict) -> dict:
    return {
        "id": item.get("campaignId"),
        "title": item.get("title"),
        "description": item.get("description"),
        "imageUrl": item.get("imageUrl"),
        "linkUrl": item.get("linkUrl"),
        "active": bool(item.get("active", True)),
        "startAt": item.get("startAt"),
        "endAt": item.get("endAt"),
    }

def _get_month_state(associate_id, month_key: str, states_by_associate=None) -> dict:
    if isinstance(states_by_associate, dict):
        cached = states_by_associate.get(utils._customer_id_str(associate_id))
        if cached:
            return cached
    state = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(associate_id, month_key))
    if state:
        return state
    now = utils._now_iso()
    return {
        "associateId": associate_id,
        "monthKey": month_key,
        "netVolume": utils.D_ZERO,
        "isActive": False,
        "createdAt": now,
    }

def _flatten_tree(root: dict) -> list:
    out = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        out.append({**node, "depth": depth})
        children = node.get("children") or []
        for child in reversed(children):
            stack.append((child, depth + 1))
    return out

def _network_members_from_tree(root: dict, max_rows: int = 30) -> list:
    rows = []
    for node in _flatten_tree(root):
        if node.get("depth", 0) == 0:
            continue
        spend = node.get("monthSpend", 0.0)
        status = "Activa" if node.get("isActive") else ("En progreso" if spend > 0 else "Inactiva")
        rows.append({
            "name": node.get("name") or "",
            "level": f"L{node.get('depth')}",
            "spend": spend,
            "status": status,
            "id": node.get("id"),
            "leaderId": node.get("leaderId"),
        })
        if len(rows) >= max_rows:
            break
    return rows

def _mxn_to_vp_dash(net_mxn: float, mxn_per_vp: float) -> float:
    return net_mxn / mxn_per_vp if mxn_per_vp > 0 else 0.0

def _state_vp_dash(state: dict, mxn_per_vp: float) -> float:
    """VP de un estado mensual, con la MISMA regla que el motor de comisiones:
    netVP (puntos por producto del catálogo) si existe; si no, pesos ÷ tarifa.

    El panel convertía siempre pesos ÷ tarifa e ignoraba netVP, así que un
    socio que compraba exactamente 20 PC según la tienda veía 19.2 en su panel
    y "Te faltan $1", mientras el motor ya lo tenía en 20."""
    if not state:
        return 0.0
    if state.get("netVP") is not None:
        return float(utils._to_decimal(state.get("netVP", 0)))
    return _mxn_to_vp_dash(float(utils._to_decimal(state.get("netVolume", 0))), mxn_per_vp)

def _calc_vg_from_tree(root_tree: dict, mxn_per_vp: float) -> float:
    total_vp = 0.0
    for node in _flatten_tree(root_tree):
        # Nodos construidos por otras rutas traen solo monthSpend (pesos).
        if node.get("monthVP") is not None:
            total_vp += float(node.get("monthVP", 0))
        else:
            total_vp += _mxn_to_vp_dash(float(node.get("monthSpend", 0)), mxn_per_vp)
    return total_vp

def _compute_buy_again_ids(customer: dict, products_raw: list) -> list:
    if not customer or not isinstance(customer, dict):
        return []
    counts = customer.get("productCounts")
    if not isinstance(counts, dict) or not counts:
        return []
    active_ids = {str(product.get("productId")) for product in products_raw if _is_product_active(product)}
    ordered = sorted(counts.items(), key=lambda item: int(item[1] or 0), reverse=True)
    return [str(product_id) for product_id, _ in ordered if str(product_id) in active_ids][:3]

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

def _goal_reward_lines(goal: dict, bonus_rules_map: dict) -> list:
    key = goal.get("key", "")
    title = goal.get("title", "")

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
    if key.startswith("rank_"):
        return [f"¡Alcanzaste el rango {title}!", "Bonos especiales desbloqueados"]

    rule_id = goal.get("bonusRuleId") or ""
    rule = bonus_rules_map.get(rule_id) or {}
    rule_rewards = rule.get("rewards") or []
    lines = []
    for reward in rule_rewards:
        reward_type = reward.get("type")
        if reward_type == "cash_mxn" and reward.get("amount"):
            lines.append(f"${reward['amount']:,.0f} MXN en efectivo")
        elif reward_type == "monthly_cash" and reward.get("amount"):
            lines.append(f"${reward['amount']:,.0f} MXN/mes")
        elif reward_type == "item" and reward.get("itemLabel"):
            lines.append(reward["itemLabel"])
        elif reward_type == "annual_fund_pct" and reward.get("pct"):
            lines.append(f"{reward['pct']}% del fondo anual")
    return lines or [title]

def _bonus_approaching_msg(goal: dict, bonus_rules_map: dict) -> str:
    rule_id = goal.get("bonusRuleId") or ""
    if not rule_id:
        return ""

    rule = bonus_rules_map.get(rule_id) or {}
    months_required = 0
    for cond in (rule.get("conditions") or []):
        if cond.get("type") in ("months_min", "months_consecutive", "months_active"):
            months_required = int(cond.get("value") or 0)
            break

    if months_required <= 1:
        return ""

    base = float(goal.get("base") or 0)
    target = float(goal.get("target") or 1)
    pct = min(base / target, 1.0) if target > 0 else 1.0
    months_done = max(1, round(pct * months_required))
    months_left = max(0, months_required - months_done)

    bonus_name = rule.get("name") or goal.get("title") or "este bono"
    if months_left <= 0:
        return ""
    return (
        f"Estás más cerca de obtener \"{bonus_name}\". "
        f"Mantente constante {months_left} mes{'es' if months_left != 1 else ''} más para obtenerlo."
    )


# ---------------------------------------------------------------------------
# Patrocinador por defecto (cuando el cliente no tiene líder asignado)
# ---------------------------------------------------------------------------
DEFAULT_SPONSOR = {
    "name": "FindingU",
    "email": "contacto@findingu.com.mx",
    "phone": "+52 1 55 1498 2351",
}
DEFAULT_SPONSOR_WHATSAPP = "https://wa.me/5215514982351"

#: Niveles de descuento que se muestran como meta en el dashboard.
_DISCOUNT_GOAL_RATES = (0.30, 0.40, 0.50)


def _get_product_summary(item: dict) -> dict:
    images = item.get("images") or []
    tags = item.get("tags") or []
    badge = str(tags[0]) if tags else ""
    img = _pick_product_image(images, ["miniatura", "landing", "redes"])

    raw_variants = item.get("variants") or []
    variants = []
    for variant_raw in raw_variants:
        if not isinstance(variant_raw, dict):
            continue
        variant = {
            "id": str(variant_raw.get("id") or ""),
            "name": str(variant_raw.get("name") or ""),
            "active": bool(variant_raw.get("active", True)),
        }
        variant_price = variant_raw.get("price")
        if variant_price is not None:
            variant["price"] = float(variant_price)
        if variant_raw.get("sku"):
            variant["sku"] = str(variant_raw.get("sku"))
        if variant_raw.get("img"):
            variant["img"] = str(variant_raw.get("img"))
        variants.append(variant)

    return {
        "id": str(item.get("productId")),
        "name": item.get("name"),
        "price": float(item.get("price") or 0),
        "badge": badge,
        "img": img,
        "hook": item.get("hook") or "",
        "description": item.get("description") or "",
        "copyFacebook": item.get("copyFacebook") or "",
        "copyInstagram": item.get("copyInstagram") or "",
        "copyWhatsapp": item.get("copyWhatsapp") or "",
        "images": images,
        "tags": tags,
        "variants": variants,
        "categoryIds": list(item.get("categoryIds") or []),
        "weightKg": item.get("weightKg"),
        "lengthCm": item.get("lengthCm"),
        "widthCm": item.get("widthCm"),
        "heightCm": item.get("heightCm"),
        "inOnlineStore": bool(item.get("inOnlineStore", True)),
        "inPOS": bool(item.get("inPOS", True)),
        # PC oficiales del producto (Plan abril 2026 §5). Vivía solo en la copia
        # legacy: `/customers/dashboard` los devolvía siempre vacíos pese a que
        # el frontend los lee para pintar el badge de PC.
        "vpPoints": float(utils._to_decimal(item["vpPoints"])) if item.get("vpPoints") is not None else None,
        "commissionable": bool(item.get("commissionable", True)),
    }


def _get_direct_vg_dash(cid: str, month_key: str, customers_raw: list, mxn_per_vp: float, month_states=None) -> float:
    total = 0.0
    for customer in customers_raw:
        if str(customer.get("leaderId", "")) == str(cid):
            state = _get_month_state(str(customer.get("customerId", "")), month_key, month_states)
            total += _state_vp_dash(state, mxn_per_vp)
    return total


def _active_notifications_for_customer(customer_id) -> list:
    if customer_id in (None, ""):
        return []
    now_str = utils._now_iso()[:10]

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
        notification_id = str(item.get("notificationId") or "").strip()
        if not notification_id:
            continue
        # Paquete A: un aviso dirigido (targetCustomerId) solo lo ve su cliente.
        destinatario = str(item.get("targetCustomerId") or "").strip()
        if destinatario and destinatario != str(customer_id):
            continue
        start_at = (item.get("startAt") or "")[:10]
        end_at = (item.get("endAt") or "")[:10]
        if start_at and now_str < start_at:
            continue
        if end_at and now_str > end_at:
            continue
        notifications.append({
            "id": notification_id,
            "title": item.get("title"),
            "description": item.get("description"),
            "linkUrl": item.get("linkUrl"),
            "startAt": item.get("startAt"),
            "endAt": item.get("endAt"),
            "read": notification_id in read_ids,
            "status": "active",
        })

    notifications.sort(key=lambda item: (item.get("startAt") or "", item.get("id") or ""), reverse=True)
    return notifications


def _find_effective_sponsor(customer) -> dict:
    default_sponsor = {**DEFAULT_SPONSOR, "isDefault": True}
    if not customer or not isinstance(customer, dict):
        return {**default_sponsor, "whatsapp": DEFAULT_SPONSOR_WHATSAPP}
    leader_id = customer.get("leaderId")
    if leader_id in (None, ""):
        return {**default_sponsor, "whatsapp": DEFAULT_SPONSOR_WHATSAPP}
    # _customer_entity_id tolera IDs legados no numéricos; int() a secas
    # tumbaba el dashboard entero con un 500 para esos clientes.
    sponsor = utils._get_by_id("CUSTOMER", utils._customer_entity_id(leader_id))
    if not sponsor:
        return {**default_sponsor, "whatsapp": DEFAULT_SPONSOR_WHATSAPP}
    phone = sponsor.get("phone") or DEFAULT_SPONSOR["phone"]
    return {
        "name": sponsor.get("name") or DEFAULT_SPONSOR["name"],
        "email": sponsor.get("email") or DEFAULT_SPONSOR["email"],
        "phone": phone,
        "whatsapp": f"https://wa.me/52{phone}" if phone else DEFAULT_SPONSOR_WHATSAPP,
        "isDefault": False,
    }


def _notify_goal_achievements(customer: dict, new_goals: list, bonus_cfg: dict) -> None:
    try:
        cust_email = str(customer.get("email") or "")
        cust_name = str(customer.get("name") or "Usuario")
        if not cust_email:
            return

        prev_goals_raw = customer.get("goals") or []
        prev_achieved = {goal.get("key") for goal in prev_goals_raw if goal.get("achieved")}
        bonus_rules_map = {rule.get("id"): rule for rule in (bonus_cfg.get("rules") or []) if rule.get("active")}

        for goal in new_goals:
            key = goal.get("key", "")
            achieved = bool(goal.get("achieved"))
            if not achieved or key in prev_achieved:
                continue

            title = goal.get("title", "Meta")
            rewards = _goal_reward_lines(goal, bonus_rules_map)
            approaching_msg = _bonus_approaching_msg(goal, bonus_rules_map)
            subject, text, html = _build_goal_achieved_email(
                name=cust_name,
                goal_title=title,
                reward_lines=rewards,
                bonus_approaching=approaching_msg,
            )
            utils._send_ses_email(cust_email, subject, text, html)

    except Exception as ex:
        utils._log_error("goal_email_failed", ex)


class _GoalContext:
    """Métricas del mes que comparten todos los constructores de metas."""

    __slots__ = ("cid", "month_key", "customers_raw", "month_states", "mxn_per_vp",
                 "activation_vp", "tiers", "rank_thresholds", "bonus_rules",
                 "my_net", "my_vp", "my_vg", "my_active", "new_direct",
                 "any_member_active", "direct_count", "all_direct_ok", "any_member_added")

    def __init__(self, customer, root_tree, customers_raw, cfg, bonus_cfg, month_states):
        bonus_cfg = bonus_cfg or {}
        self.cid = str(customer.get("customerId"))
        self.month_key = utils._month_key()
        self.customers_raw = customers_raw
        self.month_states = month_states

        self.mxn_per_vp = utils._mxn_per_vp()
        self.activation_vp = utils._activation_vp()
        self.tiers = sorted(
            ({"min": float(utils._to_decimal(t.get("min"))),
              "rate": float(utils._to_decimal(t.get("rate")))}
             for t in (cfg.get("discountTiers") or [])),
            key=lambda item: item["rate"],
        )
        self.rank_thresholds = sorted(
            bonus_cfg.get("rankThresholds") or [],
            key=lambda item: float(item.get("vgMin", 0)),
        )
        self.bonus_rules = [r for r in (bonus_cfg.get("rules") or []) if r.get("active")]

        state = _get_month_state(self.cid, self.month_key, month_states)
        self.my_net = utils._to_decimal(state.get("netVolume", 0))
        self.my_vp = _state_vp_dash(state, self.mxn_per_vp)
        self.my_vg = _calc_vg_from_tree(root_tree, self.mxn_per_vp)
        self.my_active = self.my_vp >= self.activation_vp

        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        self.new_direct = sum(
            1 for direct in customers_raw
            if str(direct.get("leaderId") or "") == self.cid
            and direct.get("createdAt", "") >= month_start
        )

        tree_nodes = _flatten_tree(root_tree)
        self.any_member_active = any(
            node.get("isActive") and node.get("depth", 0) > 0 for node in tree_nodes
        )
        direct_children = [node for node in tree_nodes if node.get("depth") == 1]
        self.direct_count = len(direct_children)
        self.all_direct_ok = bool(direct_children) and all(
            node.get("isActive") for node in direct_children
        )
        tree_ids = {node["id"] for node in tree_nodes}
        self.any_member_added = any(
            str(member.get("leaderId") or "") in tree_ids
            and member.get("createdAt", "") >= month_start
            for member in customers_raw
        )


def _goal_activacion(ctx: _GoalContext) -> dict:
    """Meta base: alcanzar el mínimo de PC que activa el mes."""
    return {
        "key": "active",
        "title": "Alcanzar VP mínimo (usuario activo)",
        "subtitle": f"Meta mensual: {ctx.activation_vp:.0f} VP",
        "target": ctx.activation_vp,
        "base": round(ctx.my_vp, 2),
        "cart": 0,
        "achieved": ctx.my_active,
        "locked": False,
        "isCountGoal": False,
        "unit": "vp",
        "ctaText": "Ir a tienda",
        "ctaFragment": "merchant",
    }


def _goals_descuento(ctx: _GoalContext) -> list:
    """Una meta por cada peldaño de la escalera de descuentos (en MXN)."""
    def minimo_para(rate_threshold):
        for tier in ctx.tiers:
            if tier["rate"] >= rate_threshold:
                return tier["min"]
        return float(ctx.my_net)

    # Las metas salían de una lista fija de tasas (30/40/50%) que no coincide
    # con la escalera configurada (10/20/30/40%): al socio se le pedía
    # "nivel 1 (30%)" desde $3,000 y existía un "nivel 3 (50%)" imposible. Se
    # generan desde la configuración real, numeradas como en el plan.
    metas = []
    escalones = [t for t in ctx.tiers if float(t.get("rate") or 0) > 0]
    for index, tier in enumerate(escalones, start=1):
        rate = float(tier["rate"])
        target = float(tier["min"])
        metas.append({
            "key": f"discount_{index}",
            "title": f"Alcanzar nivel {index} de descuento ({int(round(rate * 100))}%)",
            "subtitle": f"Consumo objetivo desde ${int(target):,} MXN",
            "target": target,
            "base": float(ctx.my_net),
            "cart": 0,
            "achieved": float(ctx.my_net) >= target,
            "locked": False,
            "isCountGoal": False,
            "unit": "mxn",
            "ctaText": "Completar consumo",
            "ctaFragment": "merchant",
        })
    return metas


def _goal_invitar(ctx: _GoalContext) -> dict:
    return {
        "key": "invite",
        "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": "Invita a 1 persona y actívala",
        "target": 1,
        "base": int(ctx.new_direct),
        "cart": 0,
        "achieved": bool(ctx.new_direct >= 1),
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Invitar ahora",
        "ctaFragment": "links",
    }


def _goal_un_miembro_activo(ctx: _GoalContext) -> dict:
    return {
        "key": "network_one_active",
        "title": "Lograr que un miembro de la red alcance su meta",
        "subtitle": f"Meta por miembro: {ctx.activation_vp:.0f} VP",
        "target": 1,
        "base": 1 if ctx.any_member_active else 0,
        "cart": 0,
        "achieved": ctx.any_member_active,
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    }


def _goal_directos_activos(ctx: _GoalContext) -> dict:
    return {
        "key": "direct_all_active",
        "title": "Todos los directos logran su meta",
        "subtitle": ("Aún no tienes miembros directos" if not ctx.direct_count
                     else f"Directos: {ctx.direct_count}"),
        "target": ctx.direct_count if ctx.direct_count else 1,
        "base": ctx.direct_count if ctx.all_direct_ok else 0,
        "cart": 0,
        "achieved": bool(ctx.all_direct_ok and ctx.direct_count > 0),
        "locked": not ctx.direct_count,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Impulsar a mi red",
        "ctaFragment": "links",
    }


def _goal_red_replica(ctx: _GoalContext) -> dict:
    return {
        "key": "network_member_invited",
        "title": "Tu red replica: un miembro agrega a otro",
        "subtitle": "Haz que tu red crezca sola",
        "target": 1,
        "base": 1 if ctx.any_member_added else 0,
        "cart": 0,
        "achieved": bool(ctx.any_member_added),
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    }


def _goals_rango(ctx: _GoalContext) -> list:
    """Una meta por rango del plan, ordenadas por VG mínimo."""
    return [
        {
            "key": f"rank_{str(rt.get('rank', '')).lower()}",
            "title": f"Alcanzar rango {rt.get('rank', '')}",
            "subtitle": f"VG mínimo: {float(rt.get('vgMin', 0)):,.0f} VP",
            "target": float(rt.get("vgMin", 0)),
            "base": round(ctx.my_vg, 2),
            "cart": 0,
            "achieved": ctx.my_vg >= float(rt.get("vgMin", 0)),
            "locked": False,
            "isCountGoal": False,
            "unit": "vp",
            "rank": rt.get("rank", ""),
            "ctaText": "Impulsar tu red",
            "ctaFragment": "red",
        }
        for rt in ctx.rank_thresholds
    ]


def _goals_bono(ctx: _GoalContext) -> list:
    """Una meta por regla de bono activa que tenga una condición medible."""
    metas = []
    direct_vg = None
    for rule in ctx.bonus_rules:
        condicion = next(
            (c for c in rule.get("conditions", [])
             if c.get("type") in ("vg_min", "vp_min", "direct_vg_min")),
            None,
        )
        if not condicion:
            continue

        target = float(condicion.get("value") or 0)
        if target <= 0:
            continue

        tipo = condicion.get("type")
        if tipo == "vg_min":
            base_val = round(ctx.my_vg, 2)
        elif tipo == "vp_min":
            base_val = round(ctx.my_vp, 2)
        else:  # direct_vg_min — se calcula como mucho una vez
            if direct_vg is None:
                direct_vg = _get_direct_vg_dash(
                    ctx.cid, ctx.month_key, ctx.customers_raw, ctx.mxn_per_vp, ctx.month_states
                )
            base_val = round(direct_vg, 2)

        rule_id = rule.get("id", "")
        metas.append({
            "key": f"bonus_{rule_id}",
            "title": rule.get("name", ""),
            "subtitle": rule.get("notes") or f"Meta: {target:,.0f} VP",
            "target": target,
            "base": base_val,
            "cart": 0,
            "achieved": base_val >= target,
            "locked": False,
            "isCountGoal": False,
            "unit": "vp",
            "bonusRuleId": rule_id,
            "ctaText": "Ver bonos",
            "ctaFragment": "volumen",
        })
    return metas


def _marcar_meta_primaria(goals: list) -> list:
    """Marca como `primary` la primera meta alcanzable y aún no lograda."""
    primaria = next(
        (i for i, goal in enumerate(goals) if not goal.get("locked") and not goal.get("achieved")),
        None,
    )
    for i, goal in enumerate(goals):
        goal["primary"] = primaria == i
        goal["secondary"] = primaria is not None and primaria != i
        goal.setdefault("cart", 0)
    return goals


def _build_goals(customer: dict, root_tree: dict, customers_raw: list, cfg: dict,
                 bonus_cfg=None, month_states=None) -> list:
    """Metas del dashboard del socio, en el orden en que se muestran.

    El orden intercala metas de consumo y de red a propósito para que el
    usuario no vea tres metas seguidas del mismo tipo. Antes se conseguía con
    `goals.insert(2, ...)`, `insert(4, ...)`, `insert(6, ...)` sobre la lista
    ya construida: índices mágicos que se desplazaban en silencio si cambiaba
    el número de peldaños de descuento. Ahora la secuencia es explícita.
    """
    ctx = _GoalContext(customer, root_tree, customers_raw, cfg, bonus_cfg, month_states)
    descuentos = _goals_descuento(ctx)

    goals = [
        _goal_activacion(ctx),
        descuentos[0],
        _goal_invitar(ctx),
        descuentos[1],
        _goal_un_miembro_activo(ctx),
        descuentos[2],
        _goal_directos_activos(ctx),
        _goal_red_replica(ctx),
        *_goals_rango(ctx),
        *_goals_bono(ctx),
    ]
    return _marcar_meta_primaria(goals)



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


# ---------------------------------------------------------------------------
# Bloques compartidos por los dos dashboards de socio
# ---------------------------------------------------------------------------
def build_commission_summary(customer: dict, month_key: str, prev_month_key: str,
                             payout_day: int = 10) -> dict:
    """Resumen de comisiones del mes en curso y estado de pago del anterior.

    Este bloque estaba escrito dos veces, casi igual, en ambos dashboards.
    """
    customer_id = utils._customer_entity_id(customer.get("customerId"))

    actual = utils._table.get_item(Key={
        "PK": utils.COMMISSION_MONTH_PK, "SK": utils._ledger_sk(customer_id, month_key),
    }).get("Item") or {}
    previo = utils._table.get_item(Key={
        "PK": utils.COMMISSION_MONTH_PK, "SK": utils._ledger_sk(customer_id, prev_month_key),
    }).get("Item") or {}

    pendiente = utils._to_decimal(actual.get("totalPending"))
    confirmado = utils._to_decimal(actual.get("totalConfirmed"))
    bloqueado = utils._to_decimal(actual.get("totalBlocked"))
    confirmado_previo = utils._to_decimal(previo.get("totalConfirmed"))

    # Un comprobante del mes previo se emite en ese mes o después.
    receipt_url = ""
    for receipt in utils._query_bucket("COMMISSION_RECEIPT", sk_from=prev_month_key):
        if (utils._customer_entity_id(receipt.get("customerId")) == customer_id
                and str(receipt.get("monthKey")) == str(prev_month_key)
                and receipt.get("assetUrl")):
            receipt_url = receipt.get("assetUrl")
            break

    if confirmado_previo <= 0:
        estado_previo = "no_moves"
    elif receipt_url:
        estado_previo = "paid"
    else:
        estado_previo = "pending"

    clabe = (customer.get("clabeInterbancaria") or customer.get("clabe") or "").strip()
    return {
        "monthKey": month_key,
        "totalPending": float(pendiente),
        "totalConfirmed": float(confirmado),
        "totalBlocked": float(bloqueado),
        "ledger": actual.get("ledger") if isinstance(actual.get("ledger"), list) else [],
        "hasPending": pendiente > 0,
        "hasConfirmed": confirmado > 0,
        "clabeOnFile": bool(clabe),
        "clabeLast4": clabe[-4:] if clabe else "",
        "payoutDay": int(payout_day),
        "paidTotal": float(confirmado_previo),
        "receiptUrl": receipt_url,
        "prevReceiptUrl": receipt_url,
        "prevStatus": estado_previo,
    }


def load_bonus_awards(customer_id, month_key: str) -> list:
    """Bonos otorgados al socio en el mes."""
    cid = str(customer_id)
    return [
        award for award in utils._query_bucket("BONUS_AWARD", sk_from=month_key)
        if str(award.get("customerId", "")) == cid and award.get("monthKey") == month_key
    ]


def persist_dashboard_cache(customer: dict, goals: list, network: list, buy_again: list) -> bool:
    """Guarda en el cliente el resultado del dashboard (caché accesorio).

    Que falle no invalida la respuesta, pero sí conviene enterarse.
    """
    try:
        utils._update_by_id(
            "CUSTOMER", customer.get("customerId"),
            "SET goals = :g, networkMembers = :n, buyAgainIds = :b, updatedAt = :u",
            {":g": goals, ":n": network, ":b": buy_again, ":u": utils._now_iso()},
        )
        return True
    except Exception as ex:
        utils._log_error("dashboard_cache_persist_failed", ex,
                         customerId=customer.get("customerId"))
        return False


def _build_month_node_index(month_key: str, customers_raw: list, cfg: dict,
                            month_states: dict = None) -> tuple:
    """Construye una sola vez el índice `{id: nodo}` + `{líder: [hijos]}` del mes.

    Los estados ASSOCIATE_MONTH se cargan en bloque con `_load_month_states`
    (BatchGetItem) en lugar de un GetItem secuencial por cliente. El índice es
    reutilizable para construir el árbol de cualquier raíz sin releer nada.
    """
    # `activationNetMin` está en PC (plan abril 2026 §3), no en MXN: comparar
    # `netVolume` en pesos contra él daba "activo" a cualquiera que comprara
    # más de 20 pesos. Se convierte el volumen del mes a PC antes de comparar.
    activation_vp = utils._activation_vp()
    mxn_per_vp = utils._mxn_per_vp()

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
        net_volume = float(utils._to_decimal(state.get("netVolume")))
        node["monthSpend"] = net_volume
        node["monthVP"] = _state_vp_dash(state, mxn_per_vp)
        node["isActive"] = bool(node["monthVP"] >= activation_vp)

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
