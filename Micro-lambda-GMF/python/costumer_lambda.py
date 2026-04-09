import base64
import json
import time
import boto3
import core_utils as utils  # Importado desde la Lambda Layer
from datetime import datetime, timezone

# Cliente S3 para subida de documentos propios del cliente
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)
FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")
DEFAULT_SPONSOR = {
    "name": "FindingU",
    "email": "coach@findingu.com.mx",
    "phone": "+52 1 55 1498 2351",
}

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

# --- HELPERS DE NORMALIZACIÓN ---

def _format_customer_output(item):
    """Limpia el objeto de DynamoDB para el frontend y normaliza direcciones/documentos."""
    if not item:
        return None

    out = dict(item)
    # Eliminar llaves internas de DynamoDB
    out.pop("PK", None)
    out.pop("SK", None)
    out.pop("passwordHash", None)  # Nunca enviar el hash

    # Normalizar Direcciones
    addresses = item.get("addresses") or item.get("shippingAddresses") or []
    out["addresses"] = addresses
    out["shippingAddresses"] = addresses

    # Documentos del administrador (los que admin liga al cliente)
    out["documents"] = item.get("documents") or []

    # Documentos propios del cliente (subidos por él mismo)
    out["ownDocuments"] = item.get("ownDocuments") or []

    # Institución bancaria
    out["bankInstitution"] = item.get("bankInstitution") or ""

    # Asegurar tipos decimales a float para JSON
    out["commissions"] = float(utils._to_decimal(item.get("commissions", 0)))
    out["discountRate"] = float(utils._to_decimal(item.get("discountRate", 0)))

    return out


def _normalize_dashboard_customer(customer):
    if not customer or not isinstance(customer, dict):
        return None

    raw_addresses = customer.get("addresses") or customer.get("shippingAddresses") or []
    default_address_id = str(customer.get("defaultAddressId") or customer.get("defaultShippingAddressId") or "").strip()
    addresses = []

    for index, entry in enumerate(raw_addresses):
        if not isinstance(entry, dict):
            continue

        address = str(entry.get("address") or "").strip()
        postal_code = str(entry.get("postalCode") or "").strip()
        state = str(entry.get("state") or entry.get("city") or "").strip()
        between_streets = str(entry.get("betweenStreets") or "").strip()
        references = str(entry.get("references") or entry.get("reference") or "").strip()

        if not any([address, postal_code, state, between_streets, references]):
            continue

        address_id = str(entry.get("addressId") or entry.get("id") or f"addr-{index + 1}").strip()
        is_default = bool(entry.get("isDefault")) or bool(default_address_id and address_id == default_address_id)

        addresses.append({
            "id": address_id,
            "label": str(entry.get("label") or "").strip(),
            "recipientName": str(entry.get("recipientName") or customer.get("name") or "").strip(),
            "phone": str(entry.get("phone") or customer.get("phone") or "").strip(),
            "street": str(entry.get("street") or "").strip(),
            "number": str(entry.get("number") or "").strip(),
            "address": address,
            "city": str(entry.get("city") or customer.get("city") or "").strip(),
            "postalCode": postal_code,
            "state": state,
            "country": str(entry.get("country") or "MX").strip(),
            "betweenStreets": between_streets,
            "references": references,
            "isDefault": is_default,
        })

    resolved_default_id = default_address_id or next((item["id"] for item in addresses if item.get("isDefault")), "")

    return {
        "id": str(customer.get("customerId") or "").strip(),
        "name": str(customer.get("name") or "").strip(),
        "phone": str(customer.get("phone") or "").strip(),
        "address": str(customer.get("address") or "").strip(),
        "city": str(customer.get("city") or "").strip(),
        "state": str(customer.get("state") or "").strip(),
        "postalCode": str(customer.get("postalCode") or "").strip(),
        "addresses": addresses,
        "defaultAddressId": resolved_default_id,
        "shippingAddresses": addresses,
        "defaultShippingAddressId": resolved_default_id,
    }


def _check_leader_cycle(customer_id, new_leader_id):
    """Evita que un usuario sea su propio abuelo (ciclos infinitos)."""
    if str(customer_id) == str(new_leader_id):
        return True

    leader_profile = utils._get_by_id("CUSTOMER", new_leader_id)
    if leader_profile and str(customer_id) in utils._get_customer_upline_ids(leader_profile):
        return True

    current_leader = new_leader_id
    visited = set()

    while current_leader:
        if current_leader in visited:
            break
        if str(current_leader) == str(customer_id):
            return True
        visited.add(current_leader)
        leader_profile = utils._get_by_id("CUSTOMER", current_leader)
        current_leader = leader_profile.get("leaderId") if leader_profile else None

    return False


class _DashboardTimer:
    def __init__(self, customer_id):
        self.customer_id = str(customer_id or "")
        self.request_id = utils.uuid.uuid4().hex[:12]
        self.started_at = time.perf_counter()
        self.last_at = self.started_at

    def mark(self, stage: str, **extra):
        now = time.perf_counter()
        payload = {
            "event": "customer_dashboard_timing",
            "requestId": self.request_id,
            "customerId": self.customer_id,
            "stage": stage,
            "elapsedMs": round((now - self.last_at) * 1000, 2),
            "totalMs": round((now - self.started_at) * 1000, 2),
        }
        if extra:
            payload.update(extra)
        print(json.dumps(payload, default=utils._json_default))
        self.last_at = now


def _load_customer_network_scope(customer: dict) -> tuple:
    if not customer or not isinstance(customer, dict):
        return [], {"source": "empty"}

    customer_id = utils._customer_id_str(customer.get("customerId"))
    source = "network_tree_batch_get"

    def _load_from_tree(tree_payload):
        descendant_ids = utils._network_tree_descendant_ids(tree_payload, customer_id)
        batch_ids = [customer_id, *descendant_ids]
        loaded = utils._batch_get_entities("CUSTOMER", batch_ids)

        by_id = {
            utils._customer_id_str(item.get("customerId")): item
            for item in loaded
            if isinstance(item, dict) and item.get("customerId") not in (None, "")
        }
        by_id[customer_id] = customer

        scoped = []
        for cid in batch_ids:
            item = by_id.get(cid)
            if item:
                scoped.append(item)
        return descendant_ids, scoped

    tree = utils._ensure_network_tree()
    descendant_ids, scoped = _load_from_tree(tree)
    missing = max(0, 1 + len(descendant_ids) - len(scoped))

    if missing and descendant_ids:
        utils._sync_customer_network_metadata()
        tree = utils._ensure_network_tree()
        descendant_ids, scoped = _load_from_tree(tree)
        missing = max(0, 1 + len(descendant_ids) - len(scoped))
        source = "network_tree_batch_get_rebuilt"

    return scoped, {
        "source": source,
        "requestedCount": len(descendant_ids),
        "loadedCount": len(scoped),
        "missingCount": missing,
    }


# --- HELPERS S3 ---

def _upload_document_s3(name: str, content_base64: str, content_type: str, prefix: str = "documentos-clientes") -> dict:
    """Sube un archivo a S3 y devuelve el objeto de asset."""
    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        raise ValueError("invalid_base64")

    asset_id = f"{prefix}/{utils.uuid.uuid4()}-{name}"
    _s3.put_object(
        Bucket=BUCKET_NAME,
        Key=asset_id,
        Body=raw,
        ContentType=content_type,
        ACL="public-read",
    )
    url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    now = utils._now_iso()
    asset_item = {
        "entityType": "asset",
        "assetId": asset_id,
        "name": name,
        "contentType": content_type,
        "url": url,
        "createdAt": now,
        "updatedAt": now,
    }
    utils._put_entity("ASSET", asset_id, asset_item, created_at_iso=now)
    return {"assetId": asset_id, "url": url, "contentType": content_type}


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
        "commissionable": bool(item.get("commissionable", True)),
    }


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


def _load_month_states(associate_ids, month_key: str) -> dict:
    entity_ids = []
    seen = set()
    for associate_id in associate_ids or []:
        cid = str(associate_id or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        entity_ids.append(f"{cid}#{month_key}")

    states = utils._batch_get_entities("ASSOCIATE_MONTH", entity_ids)
    return {
        str(item.get("associateId") or ""): item
        for item in states
        if isinstance(item, dict) and item.get("associateId") not in (None, "")
    }


def _get_month_state(associate_id, month_key: str, states_by_associate=None) -> dict:
    if isinstance(states_by_associate, dict):
        cached = states_by_associate.get(str(associate_id or ""))
        if cached:
            return cached
    state = utils._get_by_id("ASSOCIATE_MONTH", f"{associate_id}#{month_key}")
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


def _build_network_tree_with_month(root_id, month_key: str, customers_raw: list, cfg: dict, max_depth=3, month_states=None) -> dict:
    activation_min = utils._to_decimal(cfg.get("activationNetMin", 2500))
    nodes = {}
    children_by_leader = {}

    for customer in customers_raw:
        cid = str(customer.get("customerId"))
        if not cid:
            continue
        nodes[cid] = {
            "id": cid,
            "name": customer.get("name") or "",
            "level": (customer.get("level") or "").strip(),
            "leaderId": str(customer.get("leaderId")) if customer.get("leaderId") else None,
            "createdAt": customer.get("createdAt"),
            "monthSpend": 0.0,
            "isActive": False,
            "children": [],
        }
        leader_id = nodes[cid]["leaderId"]
        if leader_id:
            children_by_leader.setdefault(leader_id, []).append(cid)

    for cid, node in nodes.items():
        state = _get_month_state(cid, month_key, month_states)
        net_volume = utils._to_decimal(state.get("netVolume"))
        node["monthSpend"] = float(net_volume)
        node["isActive"] = bool(net_volume >= activation_min)

    for leader_id, kids in children_by_leader.items():
        if leader_id in nodes:
            child_nodes = sorted([nodes[kid] for kid in kids if kid in nodes], key=lambda item: item["monthSpend"], reverse=True)
            nodes[leader_id]["children"] = child_nodes

    root = nodes.get(str(root_id))
    if not root:
        return {"id": str(root_id), "name": "", "level": "", "monthSpend": 0.0, "children": []}

    def _trim(node, depth):
        if depth >= max_depth:
            node["children"] = []
            return node
        node["children"] = [_trim(child, depth + 1) for child in (node.get("children") or [])]
        return node

    return _trim(root, 0)


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


def _calc_vg_from_tree(root_tree: dict, mxn_per_vp: float) -> float:
    total_mxn = 0.0
    for node in _flatten_tree(root_tree):
        total_mxn += float(node.get("monthSpend", 0))
    return _mxn_to_vp_dash(total_mxn, mxn_per_vp)


def _get_rank_dash(vg: float, rank_thresholds: list) -> str:
    rank = ""
    for rank_threshold in sorted(rank_thresholds, key=lambda item: float(item.get("vgMin", 0))):
        if vg >= float(rank_threshold.get("vgMin", 0)):
            rank = rank_threshold.get("rank", "")
    return rank


def _get_direct_vg_dash(cid: str, month_key: str, customers_raw: list, mxn_per_vp: float, month_states=None) -> float:
    total = 0.0
    for customer in customers_raw:
        if str(customer.get("leaderId", "")) == str(cid):
            state = _get_month_state(str(customer.get("customerId", "")), month_key, month_states)
            total += float(utils._to_decimal(state.get("netVolume", 0)))
    return _mxn_to_vp_dash(total, mxn_per_vp)


def _build_goals(customer: dict, root_tree: dict, customers_raw: list, cfg: dict, bonus_cfg=None, month_states=None) -> list:
    bonus_cfg = bonus_cfg or {}
    vp_cfg = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp = float(vp_cfg.get("mxnPerVp", 50))
    rank_thresh = bonus_cfg.get("rankThresholds") or []
    bonus_rules = [rule for rule in (bonus_cfg.get("rules") or []) if rule.get("active")]

    activation_vp = float(utils._to_decimal(cfg.get("activationNetMin", 50)))
    tiers = [{"min": float(utils._to_decimal(tier.get("min"))), "rate": float(utils._to_decimal(tier.get("rate")))} for tier in (cfg.get("discountTiers") or [])]
    tiers.sort(key=lambda item: item["rate"])
    level_rates = [0.30, 0.40, 0.50]

    cid = str(customer.get("customerId"))
    month_key = utils._month_key()
    state = _get_month_state(cid, month_key, month_states)
    my_net = utils._to_decimal(state.get("netVolume", 0))
    my_vp = _mxn_to_vp_dash(float(my_net), mxn_per_vp)
    my_vg = _calc_vg_from_tree(root_tree, mxn_per_vp)
    my_active = my_vp >= activation_vp

    now_dt = datetime.now(timezone.utc)
    month_start = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    new_direct = sum(
        1 for direct in customers_raw
        if str(direct.get("leaderId") or "") == cid and direct.get("createdAt", "") >= month_start.isoformat()
    )

    tree_nodes = _flatten_tree(root_tree)
    any_member_active = any(node.get("isActive") and node.get("depth", 0) > 0 for node in tree_nodes)
    direct_children = [node for node in tree_nodes if node.get("depth") == 1]
    all_direct_ok = bool(direct_children) and all(node.get("isActive") for node in direct_children)
    tree_ids = {node["id"] for node in tree_nodes}
    any_member_added = any(
        str(member.get("leaderId") or "") in tree_ids and member.get("createdAt", "") >= month_start.isoformat()
        for member in customers_raw
    )

    goals = []
    goals.append({
        "key": "active",
        "title": "Alcanzar VP mínimo (usuario activo)",
        "subtitle": f"Meta mensual: {activation_vp:.0f} VP",
        "target": activation_vp,
        "base": round(my_vp, 2),
        "cart": 0,
        "achieved": my_active,
        "locked": False,
        "isCountGoal": False,
        "unit": "vp",
        "ctaText": "Ir a tienda",
        "ctaFragment": "merchant",
    })

    def tier_min_for_rate(rate_threshold):
        for tier in tiers:
            if tier["rate"] >= rate_threshold:
                return tier["min"]
        return float(my_net)

    for index, rate in enumerate(level_rates, start=1):
        target = tier_min_for_rate(rate)
        goals.append({
            "key": f"discount_{index}",
            "title": f"Alcanzar nivel {index} de descuento ({int(rate * 100)}%)",
            "subtitle": f"Consumo objetivo desde ${int(target):,} MXN",
            "target": target,
            "base": float(my_net),
            "cart": 0,
            "achieved": float(my_net) >= target,
            "locked": False,
            "isCountGoal": False,
            "unit": "mxn",
            "ctaText": "Completar consumo",
            "ctaFragment": "merchant",
        })

    goals.insert(2, {
        "key": "invite",
        "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": "Invita a 1 persona y actívala",
        "target": 1,
        "base": int(new_direct),
        "cart": 0,
        "achieved": bool(new_direct >= 1),
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Invitar ahora",
        "ctaFragment": "links",
    })

    goals.insert(4, {
        "key": "network_one_active",
        "title": "Lograr que un miembro de la red alcance su meta",
        "subtitle": f"Meta por miembro: {activation_vp:.0f} VP",
        "target": 1,
        "base": 1 if any_member_active else 0,
        "cart": 0,
        "achieved": any_member_active,
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    direct_count = len(direct_children)
    goals.insert(6, {
        "key": "direct_all_active",
        "title": "Todos los directos logran su meta",
        "subtitle": "Aún no tienes miembros directos" if not direct_count else f"Directos: {direct_count}",
        "target": direct_count if direct_count else 1,
        "base": direct_count if all_direct_ok else 0,
        "cart": 0,
        "achieved": bool(all_direct_ok and direct_count > 0),
        "locked": not direct_count,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Impulsar a mi red",
        "ctaFragment": "links",
    })

    goals.append({
        "key": "network_member_invited",
        "title": "Tu red replica: un miembro agrega a otro",
        "subtitle": "Haz que tu red crezca sola",
        "target": 1,
        "base": 1 if any_member_added else 0,
        "cart": 0,
        "achieved": bool(any_member_added),
        "locked": False,
        "isCountGoal": True,
        "unit": "count",
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    for rank_threshold in sorted(rank_thresh, key=lambda item: float(item.get("vgMin", 0))):
        rank_name = rank_threshold.get("rank", "")
        vg_min = float(rank_threshold.get("vgMin", 0))
        achieved = my_vg >= vg_min
        goals.append({
            "key": f"rank_{rank_name.lower()}",
            "title": f"Alcanzar rango {rank_name}",
            "subtitle": f"VG mínimo: {vg_min:,.0f} VP",
            "target": vg_min,
            "base": round(my_vg, 2),
            "cart": 0,
            "achieved": achieved,
            "locked": False,
            "isCountGoal": False,
            "unit": "vp",
            "rank": rank_name,
            "ctaText": "Impulsar tu red",
            "ctaFragment": "red",
        })

    direct_vg = None
    for rule in bonus_rules:
        rule_id = rule.get("id", "")
        rule_name = rule.get("name", "")

        main_cond = None
        for cond in rule.get("conditions", []):
            if cond.get("type") in ("vg_min", "vp_min", "direct_vg_min"):
                main_cond = cond
                break
        if not main_cond:
            continue

        cond_type = main_cond.get("type")
        target = float(main_cond.get("value") or 0)
        if target <= 0:
            continue

        if cond_type == "vg_min":
            base_val = round(my_vg, 2)
        elif cond_type == "vp_min":
            base_val = round(my_vp, 2)
        elif cond_type == "direct_vg_min":
            if direct_vg is None:
                direct_vg = _get_direct_vg_dash(cid, month_key, customers_raw, mxn_per_vp, month_states)
            base_val = round(direct_vg, 2)
        else:
            continue

        achieved = base_val >= target
        goals.append({
            "key": f"bonus_{rule_id}",
            "title": rule_name,
            "subtitle": rule.get("notes") or f"Meta: {target:,.0f} VP",
            "target": target,
            "base": base_val,
            "cart": 0,
            "achieved": achieved,
            "locked": False,
            "isCountGoal": False,
            "unit": "vp",
            "bonusRuleId": rule_id,
            "ctaText": "Ver bonos",
            "ctaFragment": "volumen",
        })

    primary_idx = next((index for index, goal in enumerate(goals) if not goal.get("locked") and not goal.get("achieved")), None)
    for index, goal in enumerate(goals):
        goal["primary"] = primary_idx == index
        goal["secondary"] = primary_idx is not None and primary_idx != index
        goal.setdefault("cart", 0)

    return goals


def _compute_buy_again_ids(customer: dict, products_raw: list) -> list:
    if not customer or not isinstance(customer, dict):
        return []
    counts = customer.get("productCounts")
    if not isinstance(counts, dict) or not counts:
        return []
    active_ids = {str(product.get("productId")) for product in products_raw if _is_product_active(product)}
    ordered = sorted(counts.items(), key=lambda item: int(item[1] or 0), reverse=True)
    return [str(product_id) for product_id, _ in ordered if str(product_id) in active_ids][:3]


def _active_notifications_for_customer(customer_id) -> list:
    if customer_id in (None, ""):
        return []
    now_str = utils._now_iso()[:10]

    try:
        resp = utils._table.query(
            KeyConditionExpression=utils.Key("PK").eq(f"NOTIFICATION_READ#{customer_id}")
        )
        read_ids = {item.get("SK") for item in resp.get("Items", [])}
    except Exception:
        read_ids = set()

    notifications = []
    for item in utils._query_bucket("NOTIFICATION"):
        if not bool(item.get("active", True)):
            continue
        notification_id = str(item.get("notificationId") or "").strip()
        if not notification_id:
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
        return {**default_sponsor, "whatsapp": "https://wa.me/5215514982351"}
    leader_id = customer.get("leaderId")
    if leader_id in (None, ""):
        return {**default_sponsor, "whatsapp": "https://wa.me/5215514982351"}
    sponsor = utils._get_by_id("CUSTOMER", int(leader_id))
    if not sponsor:
        return {**default_sponsor, "whatsapp": "https://wa.me/5215514982351"}
    phone = sponsor.get("phone") or DEFAULT_SPONSOR["phone"]
    return {
        "name": sponsor.get("name") or DEFAULT_SPONSOR["name"],
        "email": sponsor.get("email") or DEFAULT_SPONSOR["email"],
        "phone": phone,
        "whatsapp": f"https://wa.me/52{phone}" if phone else "https://wa.me/5215514982351",
        "isDefault": False,
    }


def handle_get_public_sponsor(sponsor_id):
    """GET /customers/sponsor/{idSponsor}"""
    raw_sponsor_id = str(sponsor_id or "").strip()
    if not raw_sponsor_id:
        return utils._json_response(400, {"message": "idSponsor es obligatorio"})

    sponsor = utils._get_by_id("CUSTOMER", raw_sponsor_id)
    if not sponsor:
        try:
            sponsor = utils._get_by_id("CUSTOMER", int(raw_sponsor_id))
        except Exception:
            sponsor = None

    if not sponsor:
        return utils._json_response(200, {
            "sponsor": {
                **DEFAULT_SPONSOR,
                "isDefault": True,
            }
        })

    return utils._json_response(200, {
        "sponsor": {
            "name": sponsor.get("name") or DEFAULT_SPONSOR["name"],
            "email": sponsor.get("email") or DEFAULT_SPONSOR["email"],
            "phone": sponsor.get("phone") or DEFAULT_SPONSOR["phone"],
            "isDefault": False,
        }
    })


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
        print(f"[GOAL_EMAIL_ERROR] {ex}")


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


def _resolve_clabe_customer_id(customer_id, body, headers):
    headers = headers or {}
    body = body or {}
    requested_customer_id = customer_id
    if not requested_customer_id or requested_customer_id == "clabe":
        requested_customer_id = str(body.get("customerId", "")).strip() or None

    bearer_actor = utils._extract_actor_from_bearer(headers)
    if bearer_actor.get("role") in ("admin", "employee"):
        if not requested_customer_id:
            return None, utils._json_response(400, {"message": "customerId requerido"})
        return utils._customer_entity_id(requested_customer_id), None

    legacy_admin = utils._extract_admin_actor(headers)
    if legacy_admin.get("role") in ("admin", "employee"):
        if not requested_customer_id:
            return None, utils._json_response(400, {"message": "customerId requerido"})
        return utils._customer_entity_id(requested_customer_id), None

    if not bearer_actor.get("user_id"):
        return None, utils._json_response(401, {"message": "No autenticado"})

    resolved_customer_id = utils._customer_entity_id(bearer_actor.get("user_id"))
    if requested_customer_id and str(requested_customer_id) != str(resolved_customer_id):
        return None, utils._json_response(403, {"message": "Acceso denegado: solo puedes actualizar tu propia CLABE"})
    return resolved_customer_id, None


# --- HANDLERS DE ENDPOINTS ---

def handle_get_customer(customer_id, headers=None):
    """GET /customers/{id}"""
    item = utils._get_by_id("CUSTOMER", customer_id)
    if not item:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    err = utils._require_self_or_admin_from_bearer(headers or {}, item.get("customerId", customer_id))
    if err: return err
    return utils._json_response(200, {"customer": _format_customer_output(item)})


def handle_update_customer(customer_id, body, headers):
    """PATCH /customers/{id}"""
    cid = utils._customer_entity_id(customer_id)
    existing = utils._get_by_id("CUSTOMER", cid)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    err = utils._require_self_or_admin_from_bearer(headers or {}, existing.get("customerId", cid))
    if err: return err

    updates = ["updatedAt = :u"]
    eav = {":u": utils._now_iso()}
    ean = {}

    # 1. Cambio de Patrocinador (Lógica Crítica)
    leader_changed = False
    if "leaderId" in body:
        new_leader = body["leaderId"]
        if new_leader and _check_leader_cycle(cid, new_leader):
            return utils._json_response(400, {"message": "El cambio generaría un ciclo inválido en la red"})
        leader_changed = existing.get("leaderId") != new_leader
        updates.append("leaderId = :lid")
        eav[":lid"] = new_leader

    # 2. Campos básicos
    fields = ["name", "phone", "address", "city", "level", "isAssociate"]
    for f in fields:
        if f in body:
            updates.append(f"{f} = :{f}")
            eav[f":{f}"] = body[f]

    # 3. Direcciones (Upsert en lista)
    if "shippingAddress" in body:
        if "addresses" in body:
            updates.append("addresses = :addr")
            updates.append("shippingAddresses = :addr")
            eav[":addr"] = body["addresses"]

    updated = utils._update_by_id("CUSTOMER", cid, f"SET {', '.join(updates)}", eav, ean)

    if leader_changed:
        try:
            utils._sync_customer_network_metadata()
            updated = utils._get_by_id("CUSTOMER", cid) or updated
        except Exception as ex:
            print(f"[CUSTOMER_NETWORK_SYNC_ERROR] action=update_customer customerId={cid} error={ex}")

    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_update_clabe(customer_id, body, headers):
    """POST /customers/{id}/clabe  o  POST /customers/clabe (customerId en body)"""
    customer_id, err = _resolve_clabe_customer_id(customer_id, body, headers)
    if err:
        return err

    clabe = str(body.get("clabe", "")).strip()
    if len(clabe) != 18 or not clabe.isdigit():
        return utils._json_response(400, {"message": "CLABE debe tener 18 dígitos numéricos"})

    update_expr = "SET clabe = :c, clabeInterbancaria = :c, updatedAt = :u"
    eav = {":c": clabe, ":u": utils._now_iso()}

    bank_institution = str(body.get("bankInstitution", "")).strip()
    if bank_institution:
        update_expr += ", bankInstitution = :bi"
        eav[":bi"] = bank_institution

    utils._update_by_id("CUSTOMER", customer_id, update_expr, eav)

    return utils._json_response(200, {"ok": True, "clabeLast4": clabe[-4:]})


def handle_add_document(customer_id, body, headers):
    """POST /customers/{id}/documents  — Admin liga un asset existente al cliente"""
    err = utils._require_admin(headers or {}, "access_screen_customers")
    if err: return err
    asset_id = body.get("assetId")
    doc_name = body.get("name", "Documento")

    asset = utils._get_by_id("ASSET", asset_id)
    if not asset:
        return utils._json_response(404, {"message": "El archivo (asset) no existe en S3"})

    doc_entry = {
        "documentId": f"DOC-{utils.uuid.uuid4().hex[:8].upper()}",
        "assetId": asset_id,
        "name": doc_name,
        "url": asset.get("url"),
        "contentType": asset.get("contentType"),
        "uploadedAt": utils._now_iso(),
    }

    utils._update_by_id(
        "CUSTOMER", customer_id,
        "SET documents = list_append(if_not_exists(documents, :empty), :d), updatedAt = :u",
        {":empty": [], ":d": [doc_entry], ":u": utils._now_iso()},
    )

    updated = utils._get_by_id("CUSTOMER", customer_id)
    return utils._json_response(201, {"customer": _format_customer_output(updated)})


def handle_upload_own_document(body, headers):
    """POST /profile/documents  — El cliente sube su propio documento (Constancia, INE, CURP, etc.)

    Payload esperado:
      docType        : str   — clave del tipo (ej: "constancia", "ine", "curp")
      docLabel       : str   — nombre legible del documento
      contentBase64  : str   — contenido del archivo en base64
      contentType    : str   — MIME type (ej: "application/pdf")
      fileName       : str   — nombre original del archivo
    """
    headers = headers or {}
    actor = utils._extract_actor_from_bearer(headers)
    user_id = actor.get("user_id")
    if not user_id:
        return utils._json_response(401, {"message": "No autenticado"})

    doc_type  = str(body.get("docType", "")).strip()
    doc_label = str(body.get("docLabel", doc_type)).strip() or "Documento"
    content_b64 = str(body.get("contentBase64", "")).strip()
    content_type = str(body.get("contentType", "application/octet-stream")).strip()
    file_name = str(body.get("fileName", f"{doc_type}.bin")).strip()

    if not doc_type:
        return utils._json_response(400, {"message": "docType requerido"})
    if not content_b64:
        return utils._json_response(400, {"message": "contentBase64 requerido"})

    # 1. Subir a S3
    try:
        asset = _upload_document_s3(file_name, content_b64, content_type, prefix=f"docs-cliente/{user_id}")
    except ValueError:
        return utils._json_response(400, {"message": "Contenido base64 inválido"})
    except Exception as e:
        print(f"[S3_UPLOAD_ERROR] {e}")
        return utils._json_response(500, {"message": "Error al subir el archivo"})

    now = utils._now_iso()
    new_doc = {
        "documentId": f"ODOC-{utils.uuid.uuid4().hex[:8].upper()}",
        "assetId": asset["assetId"],
        "docType": doc_type,
        "name": doc_label,
        "url": asset["url"],
        "contentType": content_type,
        "uploadedAt": now,
    }

    # 2. Obtener documentos propios actuales y reemplazar el del mismo tipo
    existing = utils._get_by_id("CUSTOMER", user_id)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    own_docs = [d for d in (existing.get("ownDocuments") or []) if d.get("docType") != doc_type]
    own_docs.append(new_doc)

    utils._update_by_id(
        "CUSTOMER", user_id,
        "SET ownDocuments = :od, updatedAt = :u",
        {":od": own_docs, ":u": now},
    )

    updated = utils._get_by_id("CUSTOMER", user_id)
    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_get_network(customer_id, query):
    """GET /network/{id} - Construye el árbol de profundidad N"""
    depth = int(query.get("depth", 3))
    root_customer = utils._get_by_id("CUSTOMER", customer_id)
    if not root_customer:
        return utils._json_response(404, {"message": "Usuario no encontrado en la red"})

    all_customers, _ = _load_customer_network_scope(root_customer)
    month_key = utils._month_key()
    month_states = _load_month_states([item.get("customerId") for item in all_customers], month_key)
    tree = _build_network_tree_with_month(
        str(root_customer.get("customerId")),
        month_key,
        all_customers,
        {},
        max_depth=depth,
        month_states=month_states,
    )
    return utils._json_response(200, {"network": tree})


def handle_rebuild_network_tree(headers):
    """POST /customers/network-tree/rebuild - Reconstuye el arbol persistido de red."""
    err = utils._require_admin(headers or {}, "access_screen_customers")
    if err:
        return err
    result = utils._sync_customer_network_metadata()
    return utils._json_response(200, {"ok": True, "networkTree": result})


def handle_customer_dashboard(headers):
    """GET /customers/dashboard - Dashboard autenticado derivado del dashboard legacy."""
    timer = _DashboardTimer("unknown")
    actor = utils._extract_actor_from_bearer(headers or {})
    actor_user_id = actor.get("user_id")
    if not actor_user_id:
        timer.mark("auth_missing")
        return utils._json_response(401, {"message": "No autenticado"})

    customer_id = utils._customer_entity_id(actor_user_id)
    timer = _DashboardTimer(customer_id)
    customer = utils._get_by_id("CUSTOMER", customer_id)
    if not customer or not isinstance(customer, dict):
        timer.mark("customer_missing")
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    timer.mark("load_customer")

    products_raw = utils._query_bucket("PRODUCT")
    #campaigns_raw = utils._query_bucket("CAMPAIGN")
    #featured = []
    #for item in products_raw:
    #    if not _is_product_active(item):
    #        continue
    #    if not bool(item.get("inOnlineStore", True)):
    #        continue
    #    summary = _get_product_summary(item)
    #    if len(featured) < 4:
    #        images = item.get("images") or []
    #        featured.append({
    #            "id": summary["id"],
    #            "label": summary["name"],
    #            "hook": summary.get("hook") or "",
    #            "story": _pick_product_image(images, ["redes"]) or summary["img"],
    #            "feed": _pick_product_image(images, ["miniatura", "redes"]) or summary["img"],
    #            "banner": _pick_product_image(images, ["landing"]) or summary["img"],
    #        })
    #timer.mark("load_catalog", products=len(products_raw), campaigns=len(campaigns_raw), featured=len(featured))

    #campaigns = [
    #    _campaign_payload(item)
    #    for item in campaigns_raw
    #    if bool(item.get("active", True))
    #]
    #timer.mark("prepare_campaigns", activeCampaigns=len(campaigns))

    app_cfg = utils._load_app_config()
    cfg = app_cfg.get("rewards") or {}
    bonus_cfg = app_cfg.get("bonuses") or {}
    vp_cfg = bonus_cfg.get("vpConfig") or {}
    mxn_per_vp = float(vp_cfg.get("mxnPerVp", 50))
    rank_thresh = bonus_cfg.get("rankThresholds") or []
    month_key = utils._month_key()
    prev_month_key = _prev_month_key()
    timer.mark("load_config", monthKey=month_key, prevMonthKey=prev_month_key)

    customers_raw, network_scope_meta = _load_customer_network_scope(customer)
    timer.mark("load_network_scope", **network_scope_meta)
    month_states = _load_month_states([item.get("customerId") for item in customers_raw], month_key)
    timer.mark("load_month_states", states=len(month_states))

    tree = _build_network_tree_with_month(
        str(customer.get("customerId")), month_key, customers_raw, cfg, max_depth=5, month_states=month_states
    )
    timer.mark("build_network_tree", scopeCustomers=len(customers_raw))

    computed_network = _network_members_from_tree(tree, max_rows=30)
    computed_goals = _build_goals(customer, tree, customers_raw, cfg, bonus_cfg=bonus_cfg, month_states=month_states)
    buy_again_ids = _compute_buy_again_ids(customer, products_raw)
    active_notifications = _active_notifications_for_customer(customer.get("customerId"))
    timer.mark(
        "compute_dashboard_data",
        networkMembers=len(computed_network),
        goals=len(computed_goals),
        buyAgain=len(buy_again_ids),
        notifications=len(active_notifications),
    )

    cid = str(customer.get("customerId", ""))
    st = _get_month_state(cid, month_key, month_states)
    my_net = float(utils._to_decimal(st.get("netVolume", 0)))
    vp_val = _mxn_to_vp_dash(my_net, mxn_per_vp)
    vg_val = _calc_vg_from_tree(tree, mxn_per_vp)
    rank_val = _get_rank_dash(vg_val, rank_thresh)
    timer.mark("compute_rank_metrics", vp=round(vp_val, 2), vg=round(vg_val, 2), rank=rank_val)

    all_awards = utils._query_bucket("BONUS_AWARD")
    bonus_awards = [
        award for award in all_awards
        if str(award.get("customerId", "")) == cid and award.get("monthKey") == month_key
    ]
    timer.mark("load_bonus_awards", awards=len(bonus_awards), scannedAwards=len(all_awards))

    #_notify_goal_achievements(customer, computed_goals, bonus_cfg)

    try:
        utils._update_by_id(
            "CUSTOMER", customer.get("customerId"),
            "SET goals = :g, networkMembers = :n, buyAgainIds = :b, updatedAt = :u",
            {":g": computed_goals, ":n": computed_network, ":b": buy_again_ids, ":u": utils._now_iso()},
        )
        timer.mark("persist_dashboard_cache")
    except Exception:
        timer.mark("persist_dashboard_cache_failed")

    customer_numeric_id = utils._customer_entity_id(customer.get("customerId"))
    sk_curr = f"#BENEFICIARY#{customer_numeric_id}#MONTH#{month_key}"
    comm_item = utils._table.get_item(Key={"PK": "COMMISSION_MONTH", "SK": sk_curr}).get("Item") or {}
    pend = utils._to_decimal(comm_item.get("totalPending"))
    conf = utils._to_decimal(comm_item.get("totalConfirmed"))
    blocked = utils._to_decimal(comm_item.get("totalBlocked"))
    timer.mark("load_current_commissions")

    sk_prev = f"#BENEFICIARY#{customer_numeric_id}#MONTH#{prev_month_key}"
    prev_comm = utils._table.get_item(Key={"PK": "COMMISSION_MONTH", "SK": sk_prev}).get("Item") or {}
    prev_confirmed = utils._to_decimal(prev_comm.get("totalConfirmed"))
    timer.mark("load_previous_commissions")

    receipt_url = ""
    receipts_raw = utils._query_bucket("COMMISSION_RECEIPT")
    for receipt in receipts_raw:
        if utils._customer_entity_id(receipt.get("customerId")) != customer_numeric_id:
            continue
        if str(receipt.get("monthKey")) != str(prev_month_key):
            continue
        if receipt.get("assetUrl"):
            receipt_url = receipt.get("assetUrl")
            break
    timer.mark("load_receipts", scannedReceipts=len(receipts_raw), hasReceipt=bool(receipt_url))

    clabe = (customer.get("clabeInterbancaria") or customer.get("clabe") or "").strip()
    if prev_confirmed <= 0:
        prev_status = "no_moves"
    elif receipt_url:
        prev_status = "paid"
    else:
        prev_status = "pending"

    commission_summary = {
        "monthKey": month_key,
        "totalPending": float(pend),
        "totalConfirmed": float(conf),
        "totalBlocked": float(blocked),
        "ledger": comm_item.get("ledger") if isinstance(comm_item.get("ledger"), list) else [],
        "hasPending": pend > 0,
        "hasConfirmed": conf > 0,
        "clabeOnFile": bool(clabe),
        "clabeLast4": clabe[-4:] if clabe else "",
        "payoutDay": int(utils._to_decimal(cfg.get("payoutDay", 10))),
        "paidTotal": float(prev_confirmed),
        "receiptUrl": receipt_url,
        "prevReceiptUrl": receipt_url,
        "prevStatus": prev_status,
    }

    discount_rate = utils._to_decimal(customer.get("discountRate"))
    user_payload = {
        "discountPercent": int((discount_rate * 100).quantize(utils.D_ONE)) if discount_rate else 0,
        "discountActive": bool(customer.get("activeBuyer") or discount_rate > 0),
    }
    timer.mark("assemble_response")

    response = utils._json_response(200, {
        "isGuest": False,
        "settings": {
            "cutoffDay": 25,
            "cutoffHour": 23,
            "cutoffMinute": 59,
            "userCode": str(customer.get("customerId") or ""),
            "networkGoal": 300,
        },
        "customer": _normalize_dashboard_customer(customer),
        "user": user_payload,
        "sponsor": _find_effective_sponsor(customer),
        "goals": computed_goals,
        "featured": [],
        "campaigns": [],
        "notifications": active_notifications,
        "networkMembers": computed_network,
        "buyAgainIds": buy_again_ids,
        "commissions": commission_summary,
        "vp": round(vp_val, 2),
        "vg": round(vg_val, 2),
        "rank": rank_val,
        "bonuses": bonus_awards,
    })
    timer.mark("complete", status="ok")
    return response


# --- LAMBDA HANDLER ---

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    segments = [s for s in path.strip("/").split("/") if s]

    if not segments:
        return utils._json_response(200, {"service": "customer-profile"})

    try:
        root = segments[0]

        # ── GET /customers  (lista completa para admin) ────────────────
        if root == "customers" and len(segments) == 1 and method == "GET":
            err = utils._require_admin(headers, "access_screen_customers")
            if err: return err
            items = utils._query_bucket("CUSTOMER")
            return utils._json_response(200, {"customers": items})

        # ── /customers/... ─────────────────────────────────────────────
        if root == "customers" and len(segments) > 1:
            target_id = segments[1]

            if target_id == "network-tree" and len(segments) == 3 and segments[2] == "rebuild" and method == "POST":
                return handle_rebuild_network_tree(headers)
            
            if method == "GET":
                if segments[1] == "dashboard":
                    return handle_customer_dashboard(headers)

            if target_id == "sponsor" and len(segments) == 3 and method == "GET":
                return handle_get_public_sponsor(segments[2])

            # POST /customers/clabe  (customerId en el body)
            if target_id == "clabe" and method == "POST":
                return handle_update_clabe("clabe", body, headers)

            if len(segments) == 2:  # /customers/{id}
                if method == "GET":   return handle_get_customer(target_id, headers)
                if method == "PATCH": return handle_update_customer(target_id, body, headers)

            if len(segments) == 3:
                sub = segments[2]
                # POST /customers/{id}/clabe
                if sub == "clabe" and method == "POST":
                    return handle_update_clabe(target_id, body, headers)
                # POST /customers/{id}/documents  (admin liga documento)
                if sub == "documents" and method == "POST":
                    return handle_add_document(target_id, body, headers)
                # PATCH /customers/{id}/privileges  (admin only)
                if sub == "privileges" and method == "PATCH":
                    err = utils._require_admin(headers, "user_manage_privileges")
                    if err: return err
                    return handle_update_customer(
                        target_id, {"privileges": body.get("privileges")}, headers
                    )

        # ── POST /profile/documents  (cliente sube su propio doc) ──────
        if root == "profile" and len(segments) == 2 and segments[1] == "documents":
            if method == "POST":
                return handle_upload_own_document(body, headers)


        # ── /network/{id} ──────────────────────────────────────────────
        if root == "network" and len(segments) > 1:
            return handle_get_network(segments[1], query)

        return utils._json_response(404, {"message": "Ruta no encontrada en Customer Service"})

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Error interno", "error": str(e)})
