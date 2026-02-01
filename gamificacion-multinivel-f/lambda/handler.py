import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Attr, Key

TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")
BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)
_s3 = boto3.client("s3", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# JSON / HTTP helpers
# ---------------------------------------------------------------------------
def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(payload, default=_json_default),
    }


def _public_s3_url(bucket: str, key: str, region: str) -> str:
    if not bucket or not key:
        return ""
    # us-east-1 uses the same hostname format, keep consistent.
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _normalize_asset_url(url: Optional[str]) -> str:
    if not url:
        return ""
    if url.startswith("s3://"):
        parts = url.replace("s3://", "").split("/", 1)
        if len(parts) == 2:
            return _public_s3_url(parts[0], parts[1], AWS_REGION)
    return url


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_key(dt: Optional[datetime] = None) -> str:
    d = dt or _utc_now()
    return f"{d.year:04d}-{d.month:02d}"


def _to_decimal(n: Any) -> Decimal:
    if isinstance(n, Decimal):
        return n
    if n is None:
        return Decimal("0")
    return Decimal(str(n))


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _parse_int_or_str(value: Any) -> Any:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return value


def _parse_body(event: dict) -> dict:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if not body:
        return {}
    try:
        return json.loads(body)
    except Exception:
        return {}


def _get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def _get_path(event: dict) -> str:
    # 1. Proxy path (API Gateway REST con {proxy+})
    path_params = event.get("pathParameters") or {}
    proxy = path_params.get("proxy")
    if proxy:
        path = f"/{proxy}"
    else:
        path = event.get("path", "/") or "/"

    # 2. Eliminar stage (default, prod, etc.)
    stage = (event.get("requestContext") or {}).get("stage")
    if stage and path.startswith(f"/{stage}/"):
        path = path[len(stage) + 1:]

    # 3. Eliminar prefijo del servicio (/Multinivel)
    if path.startswith("/Multinivel/"):
        path = path[len("/Multinivel"):]

    # 4. Normalizar root
    return path if path.startswith("/") else f"/{path}"



def _path_segments(event: dict) -> List[str]:
    path = _get_path(event).strip("/")
    return [seg for seg in path.split("/") if seg]

def _month_start_end(dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    d = dt or _utc_now()
    start = datetime(d.year, d.month, 1, tzinfo=timezone.utc)
    if d.month == 12:
        end = datetime(d.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(d.year, d.month + 1, 1, tzinfo=timezone.utc)
    return start, end

def _iso_to_dt(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        # "2026-01-31T12:34:56Z"
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.fromisoformat(iso)
    except Exception:
        return None

def _build_network_tree_with_month(
    root_id: Any,
    month_key: str,
    customers_raw: List[dict],
    cfg: dict,
) -> dict:
    """
    Returns:
      {
        "id": str(root_id),
        "name": ...,
        "level": ...,
        "monthSpend": float,
        "children": [...]
      }
    """
    # index nodes
    nodes: Dict[str, dict] = {}
    children_by_leader: Dict[str, List[str]] = {}

    for c in customers_raw:
        cid = str(c.get("customerId"))
        if not cid:
            continue
        nodes[cid] = {
            "id": cid,
            "name": c.get("name") or "",
            "level": (c.get("level") or "").strip(),
            "leaderId": str(c.get("leaderId")) if c.get("leaderId") else None,
            "createdAt": c.get("createdAt"),
            "monthSpend": 0.0,   # filled later
            "isActive": False,   # filled later
            "children": [],
        }
        lid = nodes[cid]["leaderId"]
        if lid:
            children_by_leader.setdefault(lid, []).append(cid)

    # fill month metrics (ASSOCIATE_MONTH is Pattern 1 id lookup)
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    for cid, n in nodes.items():
        st = _get_month_state(cid, month_key)
        netv = _to_decimal(st.get("netVolume"))
        n["monthSpend"] = float(netv)
        n["isActive"] = bool(netv >= activation_min)

    # attach children
    for lid, kids in children_by_leader.items():
        if lid in nodes:
            nodes[lid]["children"] = [nodes[k] for k in kids if k in nodes]

    root = nodes.get(str(root_id))
    if not root:
        return {"id": str(root_id), "name": "", "level": "", "monthSpend": 0.0, "children": []}

    # Optional: sort children by spend desc
    def sort_rec(n: dict):
        n["children"] = sorted(n.get("children", []), key=lambda x: float(x.get("monthSpend") or 0), reverse=True)
        for ch in n["children"]:
            sort_rec(ch)

    sort_rec(root)
    return root

def _flatten_tree(root: dict) -> List[dict]:
    out = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        out.append({**node, "depth": depth})
        for ch in reversed(node.get("children", []) or []):
            stack.append((ch, depth + 1))
    return out

def _network_members_from_tree(root: dict, max_rows: int = 30) -> List[dict]:
    rows = []
    for n in _flatten_tree(root):
        if n.get("depth", 0) == 0:
            continue
        rows.append({
            "name": n.get("name") or "",
            "level": f"L{n.get('depth')}",
            "spend": float(n.get("monthSpend") or 0),
            "status": ("Activa" if n.get("isActive") else ("En progreso" if (n.get("monthSpend") or 0) > 0 else "Inactiva")),
            "id": n.get("id"),
        })
        if len(rows) >= max_rows:
            break
    return rows

def _capabilities(level: str) -> dict:
    lv = (level or "").strip().lower()
    if lv == "oro":
        return {"canRefer": True, "allowedDownlineLevels": {"plata", "bronce"}}
    if lv == "plata":
        return {"canRefer": True, "allowedDownlineLevels": {"bronce"}}
    return {"canRefer": False, "allowedDownlineLevels": set()}

def _resolve_leader_and_level(leader_id: Any) -> Tuple[Optional[Any], str]:
    """
    Reglas:
    - Sin leader => nivel Oro.
    - Leader Oro => nuevo Plata.
    - Leader Plata => nuevo Bronce.
    - Leader Bronce => reasignar al Plata mas cercano en upline y nuevo Bronce.
    """
    if not leader_id:
        return (None, "Oro")

    leader = _get_by_id("CUSTOMER", int(leader_id)) if leader_id is not None else None
    if not leader:
        return (None, "Oro")

    leader_level = (leader.get("level") or "").strip().lower()
    if leader_level == "oro":
        return (leader_id, "Plata")
    if leader_level == "plata":
        return (leader_id, "Bronce")

    # Bronce no puede tener referidos: buscar el Plata mas cercano en la cadena
    nearest_plata = None
    for lid in _upline_chain(leader_id, max_levels=None):
        candidate = _get_by_id("CUSTOMER", int(lid)) if lid is not None else None
        if not candidate:
            continue
        if (candidate.get("level") or "").strip().lower() == "plata":
            nearest_plata = lid
            break
    if nearest_plata is not None:
        return (nearest_plata, "Bronce")
    return (None, "Oro")

def _discount_tier_targets(cfg: dict) -> List[dict]:
    # normalize tiers sorted by rate asc
    tiers = cfg.get("discountTiers") or []
    normalized = []
    for t in tiers:
        normalized.append({
            "min": float(_to_decimal(t.get("min"))),
            "max": (None if t.get("max") is None else float(_to_decimal(t.get("max")))),
            "rate": float(_to_decimal(t.get("rate"))),
        })
    normalized.sort(key=lambda x: x["rate"])
    return normalized

def _best_discount_rate_for_volume(net_volume: Decimal, cfg: dict) -> Decimal:
    tiers = cfg.get("discountTiers") or []
    return _calc_discount_rate(net_volume, tiers)

def _count_new_direct_members_this_month(root_id: str, customers_raw: List[dict], now_dt: Optional[datetime]=None) -> int:
    start, end = _month_start_end(now_dt)
    cnt = 0
    for c in customers_raw:
        if str(c.get("leaderId") or "") != str(root_id):
            continue
        created = _iso_to_dt(c.get("createdAt"))
        if created and (created >= start) and (created < end):
            cnt += 1
    return cnt

def _any_member_added_member_this_month(root_tree: dict, customers_raw: List[dict], now_dt: Optional[datetime]=None) -> bool:
    # For any node in tree, check if it has a direct child created this month.
    start, end = _month_start_end(now_dt)
    ids = [n["id"] for n in _flatten_tree(root_tree)]
    leaders = set(ids)
    for c in customers_raw:
        lid = str(c.get("leaderId") or "")
        if lid not in leaders:
            continue
        created = _iso_to_dt(c.get("createdAt"))
        if created and (created >= start) and (created < end):
            return True
    return False

def _any_member_reached_activation(root_tree: dict, activation_min: Decimal) -> bool:
    for n in _flatten_tree(root_tree):
        if n.get("depth", 0) == 0:
            continue
        if _to_decimal(n.get("monthSpend")) >= activation_min:
            return True
    return False

def _all_direct_reached_activation(root_tree: dict, activation_min: Decimal) -> Tuple[bool, int]:
    direct = root_tree.get("children") or []
    if not direct:
        return (False, 0)  # notApplicable scenario handled outside
    ok = True
    for ch in direct:
        if _to_decimal(ch.get("monthSpend")) < activation_min:
            ok = False
            break
    return (ok, len(direct))

def _build_goals(
    customer: dict,
    root_tree: dict,
    customers_raw: List[dict],
    cfg: dict,
) -> List[dict]:
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    tiers = _discount_tier_targets(cfg)

    # discount "levels" by rate thresholds (match your 3 steps)
    # pick the 3 highest canonical rates in tiers, but keep stable thresholds
    level_rates = [0.30, 0.35, 0.40]

    lv = (customer.get("level") or "").strip().lower()
    cap = _capabilities(lv)

    month_key = _month_key()
    st = _get_month_state(str(customer.get("customerId")), month_key)
    my_net = _to_decimal(st.get("netVolume"))
    my_active = bool(my_net >= activation_min)

    my_discount_rate = _to_decimal(customer.get("discountRate"))
    # what would be achieved based on this month volume:
    computed_rate = _best_discount_rate_for_volume(my_net, cfg)
    effective_rate = max(my_discount_rate, computed_rate)

    # new member counts (direct)
    new_direct = _count_new_direct_members_this_month(str(customer.get("customerId")), customers_raw, _utc_now())

    # network performance checks
    any_member_active = _any_member_reached_activation(root_tree, activation_min)
    all_direct_ok, direct_count = _all_direct_reached_activation(root_tree, activation_min)
    any_member_added = _any_member_added_member_this_month(root_tree, customers_raw, _utc_now())

    # helper to find tier min target for rate
    def tier_min_for_rate(rate_threshold: float) -> float:
        # choose the first tier with rate >= threshold, else fallback activation_min
        for t in tiers:
            if (t.get("rate") or 0) >= rate_threshold:
                return float(t.get("min") or 0)
        return float(activation_min)

    goals = []

    # 1) active buyer
    goals.append({
        "key": "active",
        "title": "Alcanzar consumo mensual para ser usuario activo",
        "subtitle": f"Meta mensual: ${int(activation_min):,} neto",
        "target": float(activation_min),
        "base": float(my_net),
        "achieved": bool(my_active),
        "locked": False,
        "isCountGoal": False,
        "ctaText": "Ir a tienda",
        "ctaFragment": "merchant",
    })

    # 2/4/6) discount levels
    for idx, r in enumerate(level_rates, start=1):
        target = tier_min_for_rate(r)
        achieved = float(effective_rate) >= r
        goals.append({
            "key": f"discount_{idx}",
            "title": f"Alcanzar el nivel {idx} de descuento",
            "subtitle": f"Objetivo: {int(r*100)}% (consumo aprox. desde ${int(target):,})",
            "target": float(target),
            "base": float(my_net),
            "achieved": bool(achieved),
            "locked": False,
            "isCountGoal": False,
            "ctaText": "Completar consumo",
            "ctaFragment": "merchant",
        })

    # 3) add new member this month (direct)
    locked_invite = (not cap.get("canRefer"))
    goals.insert(2, {  # position 3 in your sequence
        "key": "invite",
        "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": ("Tu nivel actual no permite referir" if locked_invite else "Invita a 1 persona y actívala"),
        "target": 1,
        "base": int(new_direct),
        "achieved": bool(new_direct >= 1) if not locked_invite else False,
        "locked": bool(locked_invite),
        "isCountGoal": True,
        "ctaText": "Invitar ahora",
        "ctaFragment": "links",
    })

    # 5) one network member reaches their monthly goal
    goals.insert(4, {
        "key": "network_one_active",
        "title": "Lograr que un miembro de la red alcance su meta mensual",
        "subtitle": f"Meta por miembro: ${int(activation_min):,} neto",
        "target": 1,
        "base": (1 if any_member_active else 0),
        "achieved": bool(any_member_active),
        "locked": False,
        "isCountGoal": True,
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    # 7) all direct members reach their monthly goal
    not_applicable = (direct_count == 0)
    goals.insert(6, {
        "key": "direct_all_active",
        "title": "Lograr que todos los miembros del nivel inmediato inferior logren su meta mensual",
        "subtitle": ("Aún no tienes miembros directos" if not_applicable else f"Directos: {direct_count}"),
        "target": direct_count if direct_count else 1,
        "base": (direct_count if all_direct_ok and direct_count else 0),
        "achieved": bool(all_direct_ok and direct_count > 0),
        "locked": bool(not_applicable),
        "isCountGoal": True,
        "ctaText": "Impulsar a mi red",
        "ctaFragment": "links",
    })

    # 8) a network member adds a new member
    goals.append({
        "key": "network_member_invited",
        "title": "Lograr que un miembro de la red agregue un nuevo miembro",
        "subtitle": ("Tu nivel actual no permite referir" if locked_invite else "Haz que tu red replique"),
        "target": 1,
        "base": (1 if any_member_added else 0),
        "achieved": bool(any_member_added) if not locked_invite else False,
        "locked": bool(locked_invite),
        "isCountGoal": True,
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    # Now mark primary/secondary
    primary_idx = None
    for i,g in enumerate(goals):
        if g.get("locked"):
            continue
        if not g.get("achieved"):
            primary_idx = i
            break

    for i,g in enumerate(goals):
        g["primary"] = (primary_idx == i)
        g["secondary"] = (primary_idx is not None and primary_idx != i)

    return goals

def _persist_customer_dashboard_fields(customer_id: Any, goals: List[dict], network_members: List[dict], buy_again_ids: List[str]) -> None:
    if customer_id is None:
        return
    try:
        _update_by_id(
            "CUSTOMER",
            customer_id,
            "SET goals = :g, networkMembers = :n, buyAgainIds = :b, updatedAt = :u",
            {":g": goals, ":n": network_members, ":b": buy_again_ids, ":u": _now_iso()},
        )
    except Exception:
        pass

def _compute_buy_again_ids_and_maybe_update(customer: Optional[dict], products: List[dict]) -> Tuple[List[str], bool]:
    """
    buyAgainIds estrictos:
    - SOLO basado en historial (productCounts).
    - Si no hay compras => [].
    - Devuelve (buy_again_ids, should_persist).
    """
    if not customer or not isinstance(customer, dict):
        return ([], False)

    counts = customer.get("productCounts")
    existing = customer.get("buyAgainIds")

    # No historial => buyAgainIds vacío.
    if not isinstance(counts, dict) or not counts:
        # Si antes guardaste seeds, aquí los limpiamos persistiendo [].
        should_persist = (isinstance(existing, list) and len(existing) > 0)
        return ([], should_persist)

    ordered = sorted(counts.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
    top = [str(pid) for pid, _ in ordered[:3]]

    # Persistir solo si cambió
    existing_norm = [str(x) for x in existing] if isinstance(existing, list) else []
    should_persist = (existing_norm[:3] != top)
    return (top, should_persist)




# ---------------------------------------------------------------------------
# Pattern 1: BUCKET PK + REF mapping (point lookup/update without GSI)
# ---------------------------------------------------------------------------
# For each entity:
#   - Main item: PK="<ENTITY>", SK="<createdAt>#<id>"
#   - REF item : PK="<ENTITY>#<id>", SK="REF", with refPK/refSK pointing to main item
#
# This makes:
#   - list/query by PK cheap (Query PK=ENTITY)
#   - get/update by id cheap (GetItem REF then UpdateItem main)
# ---------------------------------------------------------------------------
def _bucket_pk(entity: str) -> str:
    return entity.upper()


def _ref_pk(entity: str, entity_id: Any) -> str:
    return f"{entity.upper()}#{entity_id}"


def _make_bucket_sk(created_at_iso: str, entity_id: Any) -> str:
    return f"{created_at_iso}#{entity_id}"


def _put_entity(entity: str, entity_id: Any, item: dict, created_at_iso: Optional[str] = None) -> dict:
    """
    Writes:
      - main item in BUCKET
      - REF item for id-based lookup/update
    """
    entity = entity.upper()
    created_at = created_at_iso or item.get("createdAt") or _now_iso()
    sk = item.get("SK") or _make_bucket_sk(created_at, entity_id)

    main_item = dict(item)
    main_item["PK"] = _bucket_pk(entity)
    main_item["SK"] = sk
    main_item["createdAt"] = main_item.get("createdAt") or created_at
    main_item["updatedAt"] = main_item.get("updatedAt") or created_at

    ref_item = {
        "PK": _ref_pk(entity, entity_id),
        "SK": "REF",
        "entityType": f"{entity.lower()}Ref",
        "entityId": entity_id,
        "refPK": main_item["PK"],
        "refSK": main_item["SK"],
        "createdAt": created_at,
        "updatedAt": created_at,
    }

    _table.put_item(Item=main_item)
    _table.put_item(Item=ref_item)
    return main_item


def _get_ref(entity: str, entity_id: Any) -> Optional[dict]:
    resp = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    return resp.get("Item")


def _get_by_id(entity: str, entity_id: Any) -> Optional[dict]:
    ref = _get_ref(entity, entity_id)
    if not ref:
        return None
    resp = _table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return resp.get("Item")


def _update_by_id(
    entity: str,
    entity_id: Any,
    update_expression: str,
    eav: dict,
    ean: Optional[dict] = None,
    return_values: str = "ALL_NEW",
) -> dict:
    ref = _get_ref(entity, entity_id)
    if not ref:
        raise KeyError(f"{entity.upper()}_REF_NOT_FOUND")

    kwargs = {
        "Key": {"PK": ref["refPK"], "SK": ref["refSK"]},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": eav,
        "ReturnValues": return_values,
    }
    if ean:
        kwargs["ExpressionAttributeNames"] = ean

    resp = _table.update_item(**kwargs)
    return resp.get("Attributes") or {}


def _query_bucket(entity: str, limit: int = 200, scan_forward: bool = False) -> List[dict]:
    pk = _bucket_pk(entity)
    resp = _table.query(
        KeyConditionExpression=Key("PK").eq(pk),
        Limit=limit,
        ScanIndexForward=scan_forward,
    )
    return resp.get("Items", []) or []


# ---------------------------------------------------------------------------
# Mock auth users (demo)
# ---------------------------------------------------------------------------
_LOGIN_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "email": "admin@demo.local",
        "user": {
            "userId": "admin-001",
            "name": "Admin Rivera",
            "role": "admin",
        },
    },
    {
        "username": "cliente",
        "password": "cliente123",
        "email": "cliente@demo.local",
        "user": {
            "userId": "client-001",
            "name": "Valeria Torres",
            "role": "cliente",
            "discountPercent": 15,
            "discountActive": True,
            "level": "Oro",
        },
    },
]

def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _get_auth_by_email(email: str) -> Optional[dict]:
    auth_id = _normalize_email(email)
    if not auth_id:
        return None
    return _get_by_id("AUTH", auth_id)


def _create_auth_record(email: str, password_hash: str, customer_id: Any, role: str = "cliente") -> dict:
    now = _now_iso()
    auth_id = _normalize_email(email)
    item = {
        "entityType": "auth",
        "authId": auth_id,
        "email": auth_id,
        "customerId": customer_id,
        "role": role,
        "passwordHash": password_hash,
        "createdAt": now,
        "updatedAt": now,
    }
    return _put_entity("AUTH", auth_id, item, created_at_iso=now)


def _find_customer_by_email(email: str) -> Optional[dict]:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None
    customers = _query_bucket("CUSTOMER", limit=500, scan_forward=False)
    for customer in customers:
        if _normalize_email(customer.get("email")) == email_norm:
            return customer
    return None


def _normalize_user_id(value: Any) -> Optional[Any]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return str(value).strip()


def _resolve_user_context(query: dict, headers: dict) -> Tuple[Optional[Any], bool]:
    user_id_raw = (query or {}).get("userId") or (headers or {}).get("x-user-id")
    email_raw = (query or {}).get("email") or (headers or {}).get("x-user-email")

    user_id = _normalize_user_id(user_id_raw)
    if user_id is not None:
        return user_id, False

    if email_raw:
        email_norm = _normalize_email(email_raw)
        auth = _get_auth_by_email(email_norm)
        if auth and auth.get("customerId") is not None:
            return auth.get("customerId"), False
        customer = _find_customer_by_email(email_norm)
        if customer and customer.get("customerId") is not None:
            return customer.get("customerId"), False

    return None, True

def _rate_to_percent_str(rate: Decimal) -> str:
    # 0.30 -> "30%"
    try:
        return f"{int((rate * Decimal('100')).quantize(Decimal('1')))}%"
    except Exception:
        return "0%"

def _sync_buyer_benefits(buyer_id: Any, month_key: str, cfg: dict) -> Optional[dict]:
    """
    Actualiza en CUSTOMER:
      - activeBuyer (si alcanza activationNetMin en el mes)
      - discountRate/discount (según tiers por consumo mensual neto)
    """
    if buyer_id is None:
        return None

    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    tiers = cfg.get("discountTiers") or []

    month_state = _get_month_state(buyer_id, month_key)
    net_volume = _to_decimal(month_state.get("netVolume"))
    active = bool(net_volume >= activation_min)

    # descuento por consumo del mes (puedes cambiar net_volume por gross si prefieres)
    discount_rate = _calc_discount_rate(net_volume, tiers)
    discount_str = _rate_to_percent_str(discount_rate)

    updated = _update_by_id(
        "CUSTOMER",
        buyer_id,
        "SET activeBuyer = :ab, discountRate = :dr, discount = :ds, updatedAt = :u",
        {":ab": active, ":dr": discount_rate, ":ds": discount_str, ":u": _now_iso()},
    )
    return updated


# ---------------------------------------------------------------------------
# Rewards config / engine
# ---------------------------------------------------------------------------
def _default_rewards_config() -> dict:
    return {
        "version": "v1",
        "activationNetMin": Decimal("2500"),
        "discountTiers": [
            {"min": Decimal("3600"), "max": Decimal("8000"), "rate": Decimal("0.30")},
            {"min": Decimal("8001"), "max": Decimal("12000"), "rate": Decimal("0.35")},
            {"min": Decimal("12001"), "max": None,           "rate": Decimal("0.40")},
        ],
        "commissionLevels": [Decimal("0.10"), Decimal("0.05"), Decimal("0.03")],
        "payoutDay": Decimal("10"),
        "cutRule": "hard_cut_no_pass",
    }


def _config_entity_id() -> str:
    # treated as "id" under Pattern 1
    return "rewards-v1"


def _load_rewards_config() -> dict:
    cfg = _get_by_id("CONFIG", _config_entity_id())
    if not cfg:
        now = _now_iso()
        item = {
            "entityType": "config",
            "name": "rewards",
            "configId": _config_entity_id(),
            "config": _default_rewards_config(),
            "createdAt": now,
            "updatedAt": now,
        }
        _put_entity("CONFIG", _config_entity_id(), item, created_at_iso=now)
        return item["config"]
    return cfg.get("config") or _default_rewards_config()


def _save_rewards_config(cfg: dict) -> dict:
    now = _now_iso()
    existing = _get_by_id("CONFIG", _config_entity_id())
    if not existing:
        item = {
            "entityType": "config",
            "name": "rewards",
            "configId": _config_entity_id(),
            "config": cfg,
            "createdAt": now,
            "updatedAt": now,
        }
        _put_entity("CONFIG", _config_entity_id(), item, created_at_iso=now)
        return cfg

    _update_by_id(
        "CONFIG",
        _config_entity_id(),
        "SET #c = :c, updatedAt = :u",
        {":c": cfg, ":u": now},
        ean={"#c": "config"},
    )
    return cfg


def _calc_discount_rate(gross_subtotal: Decimal, tiers: List[dict]) -> Decimal:
    g = gross_subtotal
    for t in tiers:
        tmin = _to_decimal(t.get("min"))
        tmax_raw = t.get("max")
        tmax = _to_decimal(tmax_raw) if tmax_raw is not None else None
        rate = _to_decimal(t.get("rate"))
        if g >= tmin and (tmax is None or g <= tmax):
            return rate
    return Decimal("0")


# Associate monthly state uses Pattern 1 as well:
def _associate_month_id(associate_id: Any, month_key: str) -> str:
    return f"{associate_id}#{month_key}"


def _get_month_state(associate_id: Any, month_key: str) -> dict:
    state = _get_by_id("ASSOCIATE_MONTH", _associate_month_id(associate_id, month_key))
    if state:
        return state
    now = _now_iso()
    return {
        "entityType": "associateMonth",
        "associateId": associate_id,
        "monthKey": month_key,
        "netVolume": Decimal("0"),
        "isActive": False,
        "createdAt": now,
        "updatedAt": now,
    }


def _upsert_month_volume(associate_id: Any, month_key: str, net_delta: Decimal, activation_min: Decimal) -> dict:
    mid = _associate_month_id(associate_id, month_key)
    existing = _get_by_id("ASSOCIATE_MONTH", mid)

    now = _now_iso()
    if not existing:
        net_volume = (Decimal("0") + net_delta)
        is_active = bool(net_volume >= activation_min)
        item = {
            "entityType": "associateMonth",
            "associateId": associate_id,
            "monthKey": month_key,
            "netVolume": net_volume,
            "isActive": is_active,
            "createdAt": now,
            "updatedAt": now,
        }
        return _put_entity("ASSOCIATE_MONTH", mid, item, created_at_iso=now)

    # Update main item by ID using REF
    updated = _update_by_id(
        "ASSOCIATE_MONTH",
        mid,
        "SET netVolume = if_not_exists(netVolume, :z) + :d, updatedAt = :u",
        {":z": Decimal("0"), ":d": net_delta, ":u": now},
    )
    net_volume = _to_decimal(updated.get("netVolume"))
    is_active = bool(net_volume >= activation_min)
    updated2 = _update_by_id(
        "ASSOCIATE_MONTH",
        mid,
        "SET isActive = :ia, updatedAt = :u",
        {":ia": is_active, ":u": now},
    )
    return updated2


def _is_active(associate_id: Any, month_key: str) -> bool:
    item = _get_month_state(associate_id, month_key)
    return bool(item.get("isActive"))


def _discount_for_level(level: str) -> str:
    # Legacy display
    normalized = (level or "").strip().lower()
    if normalized == "oro":
        return "15%"
    if normalized == "plata":
        return "10%"
    return "5%"


# ---------------------------------------------------------------------------
# CUSTOMER helpers (Pattern 1)
# ---------------------------------------------------------------------------
def _get_customer_profile(customer_id: Any) -> Optional[dict]:
    if customer_id is None:
        return None
    return _get_by_id("CUSTOMER", customer_id)


def _update_customer_commissions_cache(customer_id: Any, delta: Decimal) -> None:
    """
    Cache "pendiente por depositar" en el item CUSTOMER (fuente de verdad sigue siendo ledger).
    Bajo Pattern 1: update via REF.
    """
    if customer_id is None:
        return
    try:
        _update_by_id(
            "CUSTOMER",
            customer_id,
            "SET commissions = if_not_exists(commissions, :z) + :d, updatedAt = :u",
            {":z": Decimal("0"), ":d": delta, ":u": _now_iso()},
        )
    except Exception:
        pass


def _upline_chain(buyer_id: Any, max_levels: Optional[int] = 3, safety_cap: int = 50) -> List[Any]:
    """
    Devuelve la cadena de leaders (upline) partiendo del buyer.
    - max_levels: número máximo de niveles a devolver. Si None => hasta que se termine la cadena.
    - safety_cap: evita loops/estructuras corruptas (cap duro).
    """
    chain: List[Any] = []
    current_id = buyer_id
    seen = set()

    # Determinar el límite real
    hard_limit = safety_cap if max_levels is None else min(int(max_levels), safety_cap)

    for _ in range(hard_limit):
        if current_id in seen:
            # loop detectado (data corrupta)
            break
        seen.add(current_id)

        prof = _get_customer_profile(current_id)
        if not prof:
            break

        leader = prof.get("leaderId")
        if not leader:
            break

        chain.append(leader)
        current_id = leader

    return chain



# ---------------------------------------------------------------------------
# COMMISSION ledger (kept efficient per beneficiary; Pattern 1 not applied here)
# ---------------------------------------------------------------------------
def _commission_pk(beneficiary_id: Any) -> str:
    return f"COMMISSION#{beneficiary_id}"


def _commission_sk(month_key: str, order_id: str, level: int) -> str:
    return f"{month_key}#{order_id}#L{level}"


def _create_commission_entry(
    beneficiary_id: Any,
    month_key: str,
    order_id: str,
    source_buyer_id: Any,
    level: int,
    rate: Decimal,
    amount: Decimal,
    status: str,
    meta: dict,
) -> dict:
    now = _now_iso()
    item = {
        "PK": _commission_pk(beneficiary_id),
        "SK": _commission_sk(month_key, order_id, level),
        "entityType": "commission",
        "beneficiaryId": beneficiary_id,
        "monthKey": month_key,
        "orderId": order_id,
        "sourceBuyerId": source_buyer_id,
        "level": int(level),
        "rate": rate,
        "amount": amount,
        "status": status,
        "createdAt": now,
        "updatedAt": now,
        **(meta or {}),
    }
    _table.put_item(Item=item)
    return item


def _void_commissions_for_order(order_id: str, reason: str) -> List[dict]:
    # Demo scan; in prod add GSI by orderId.
    resp = _table.scan(
        FilterExpression=Attr("entityType").eq("commission") & Attr("orderId").eq(order_id),
        Limit=1000,
    )
    items = resp.get("Items", []) or []
    out = []
    for c in items:
        beneficiary = c.get("beneficiaryId")
        status = (c.get("status") or "").lower()
        amt = _to_decimal(c.get("amount"))
        month_key = c.get("monthKey") or _month_key()
        level = int(c.get("level") or 0)

        if status in {"pending", "confirmed"}:
            _table.update_item(
                Key={"PK": c["PK"], "SK": c["SK"]},
                UpdateExpression="SET #s = :v, reasonVoid = :r, updatedAt = :u",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":v": "void", ":r": reason, ":u": _now_iso()},
            )
            _update_customer_commissions_cache(beneficiary, -amt)
            out.append({"action": "void", "beneficiaryId": beneficiary, "amount": amt, "level": level})
        elif status == "paid":
            claw = _create_commission_entry(
                beneficiary_id=beneficiary,
                month_key=month_key,
                order_id=order_id,
                source_buyer_id=c.get("sourceBuyerId"),
                level=level,
                rate=_to_decimal(c.get("rate")),
                amount=-amt,
                status="clawback",
                meta={"reasonVoid": reason, "note": "Compensación por devolución/cancelación"},
            )
            _update_customer_commissions_cache(beneficiary, -amt)
            out.append({"action": "clawback", "beneficiaryId": beneficiary, "amount": float(-amt), "level": level, "id": claw["SK"]})
    return out


# ---------------------------------------------------------------------------
# ORDER (Pattern 1)
# ---------------------------------------------------------------------------
def _create_order(payload: dict) -> dict:
    """
    - Main: PK="ORDER", SK="<createdAt>#<orderId>"
    - REF : PK="ORDER#<orderId>", SK="REF"
    """
    customer_id = payload.get("customerId")
    customer_name = payload.get("customerName")
    status = payload.get("status", "pending")
    items = payload.get("items", [])

    if not customer_name or not items:
        return _json_response(200, {"message": "customerName e items son obligatorios", "Error": "BadRequest"})

    buyer_type = (payload.get("buyerType") or ("guest" if not customer_id else "registered")).lower()
    referrer_id = payload.get("referrerAssociateId")

    order_id = payload.get("orderId") or str(uuid.uuid4())
    now = _now_iso()
    month_key = _month_key()

    normalized_items = []
    gross = Decimal("0")

    for item in items:
        quantity = max(1, int(item.get("quantity") or 1))
        price = _to_decimal(item.get("price", 0))
        normalized_items.append(
            {"productId": item.get("productId"), "name": item.get("name"), "price": price, "quantity": quantity}
        )
        gross += price * _to_decimal(quantity)

    order_item = {
        "entityType": "order",
        "orderId": order_id,
        "customerId": customer_id,
        "customerName": customer_name,
        "buyerType": buyer_type,
        "referrerAssociateId": referrer_id,
        "status": status,
        "items": normalized_items,
        "grossSubtotal": gross.quantize(Decimal("0.01")),
        "total": gross.quantize(Decimal("0.01")),  # legacy field
        "monthKey": month_key,
        "createdAt": now,
        "updatedAt": now,
    }

    main = _put_entity("ORDER", order_id, order_item, created_at_iso=now)
    return _json_response(201, {"order": main})


def _find_order(order_id: str) -> Optional[dict]:
    return _get_by_id("ORDER", order_id)


def _apply_rewards_on_paid_order(order_item: dict) -> dict:
    cfg = _load_rewards_config()
    tiers = cfg.get("discountTiers") or []
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    commission_levels = [_to_decimal(x) for x in (cfg.get("commissionLevels") or [0.10, 0.05, 0.03])]

    order_id = order_item.get("orderId")
    buyer_id = order_item.get("customerId")
    buyer_type = (order_item.get("buyerType") or "registered").lower()
    referrer_id = order_item.get("referrerAssociateId")

    gross = _to_decimal(order_item.get("grossSubtotal"))
    if gross <= 0:
        gross = Decimal("0")
        for it in (order_item.get("items") or []):
            gross += _to_decimal(it.get("price")) * _to_decimal(it.get("quantity") or 1)

    month_key = order_item.get("monthKey") or _month_key()

    discount_rate = _to_decimal(order_item.get("discountRate"))
    if discount_rate <= 0:
        if buyer_type in {"associate", "registered"} and buyer_id is not None:
            discount_rate = _calc_discount_rate(gross, tiers)
        else:
            discount_rate = Decimal("0")

    discount_amount = (gross * discount_rate).quantize(Decimal("0.01"))
    net = (gross - discount_amount).quantize(Decimal("0.01"))

    # Persist computed values via Pattern 1 update
    _update_by_id(
        "ORDER",
        order_id,
        "SET grossSubtotal = :g, discountRate = :dr, discountAmount = :da, netTotal = :n, monthKey = :mk, updatedAt = :u",
        {":g": gross, ":dr": discount_rate, ":da": discount_amount, ":n": net, ":mk": month_key, ":u": _now_iso()},
    )

    # Guest one-shot referral commission (10%)
    if buyer_type == "guest" and referrer_id:
        rate = Decimal("0.10")
        amount = (net * rate).quantize(Decimal("0.01"))
        c = _create_commission_entry(
            beneficiary_id=referrer_id,
            month_key=month_key,
            order_id=order_id,
            source_buyer_id=buyer_id,
            level=0,
            rate=rate,
            amount=amount,
            status="pending",
            meta={"buyerType": buyer_type, "referrerOneShot": True},
        )
        _update_customer_commissions_cache(referrer_id, amount)
        return {
            "grossSubtotal": gross,
            "discountRate": discount_rate,
            "discountAmount": discount_amount,
            "netTotal": net,
            "monthKey": month_key,
            "commissionsCreated": [c],
            "mode": "guest_one_shot",
        }

    # Activation for buyer
    if buyer_id is not None and buyer_type in {"associate", "registered"}:
        _upsert_month_volume(buyer_id, month_key, net, activation_min)
        buyer_profile_updated = _sync_buyer_benefits(buyer_id, month_key, cfg)
        _update_customer_product_stats(buyer_id, order_item)

    chain = _upline_chain(buyer_id, max_levels=None)
    trail: List[dict] = []
    paid: List[dict] = []
    cut = False

    for idx, beneficiary in enumerate(chain):
        level = idx + 1

        # Regla de corte: si un leader NO esta activo este mes, se corta y NO se continúa hacia arriba
        if not _is_active(beneficiary, month_key):
            cut = True
            break

        # "Comisión adecuada" por nivel (si ya no hay rate configurado, se registra 0 como auditoría)
        rate = commission_levels[idx] if idx < len(commission_levels) else Decimal("0")
        amount = (net * rate).quantize(Decimal("0.01")) if rate > 0 else Decimal("0.00")

        status = "pending" if amount > 0 else "skipped"
        meta = {
            "buyerType": buyer_type,
            "note": ("Sin rate configurado para este nivel" if rate <= 0 else None),
        }
        # Limpieza: no guardes note=None
        if meta.get("note") is None:
            meta.pop("note", None)

        c = _create_commission_entry(
            beneficiary_id=beneficiary,
            month_key=month_key,
            order_id=order_id,
            source_buyer_id=buyer_id,
            level=level,
            rate=rate,
            amount=amount,
            status=status,
            meta=meta,
        )
        trail.append(c)

        if amount > 0:
            paid.append(c)
            _update_customer_commissions_cache(beneficiary, amount)

    return {
        "grossSubtotal": gross,
        "discountRate": discount_rate,
        "discountAmount": discount_amount,
        "netTotal": net,
        "monthKey": month_key,
        "uplineChain": chain,
        "cut": cut,
        "commissionsCreated": trail,
        "commissionsPaid": paid,
        "mode": "multilevel",
    }


def _update_order_status(order_id: str, payload: dict) -> dict:
    status = (payload.get("status") or "").lower()
    if status not in {"pending", "paid", "delivered", "canceled", "refunded"}:
        return _json_response(200, {"message": "status invalido", "Error": "BadRequest"})

    order_item = _find_order(order_id)
    if not order_item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    prev_status = (order_item.get("status") or "").lower()
    now = _now_iso()

    updated = _update_by_id(
        "ORDER",
        order_id,
        "SET #s = :s, updatedAt = :u",
        {":s": status, ":u": now},
        ean={"#s": "status"},
    )

    rewards_result = None
    if status == "paid" and prev_status != "paid":
        rewards_result = _apply_rewards_on_paid_order(updated)

    order_response = {
        "id": updated.get("orderId"),
        "createdAt": updated.get("createdAt"),
        "customer": updated.get("customerName"),
        "grossSubtotal": float(updated.get("grossSubtotal") or 0),
        "discountRate": float(updated.get("discountRate") or 0),
        "discountAmount": float(updated.get("discountAmount") or 0),
        "netTotal": float(updated.get("netTotal") or updated.get("total") or 0),
        "status": updated.get("status"),
    }
    if rewards_result is not None:
        return _json_response(200, {"order": order_response, "rewards": rewards_result})
    return _json_response(200, {"order": order_response})


def _refund_order(order_id: str, payload: dict) -> dict:
    reason = payload.get("reason") or "refund"
    order_item = _find_order(order_id)
    if not order_item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    _update_by_id(
        "ORDER",
        order_id,
        "SET #s = :s, refundReason = :r, updatedAt = :u",
        {":s": "refunded", ":r": reason, ":u": _now_iso()},
        ean={"#s": "status"},
    )
    actions = _void_commissions_for_order(order_id, reason="refund")
    return _json_response(200, {"orderId": order_id, "status": "refunded", "commissionActions": actions})


def _cancel_order(order_id: str, payload: dict) -> dict:
    reason = payload.get("reason") or "cancel"
    order_item = _find_order(order_id)
    if not order_item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    _update_by_id(
        "ORDER",
        order_id,
        "SET #s = :s, cancelReason = :r, updatedAt = :u",
        {":s": "canceled", ":r": reason, ":u": _now_iso()},
        ean={"#s": "status"},
    )
    actions = _void_commissions_for_order(order_id, reason="cancel")
    return _json_response(200, {"orderId": order_id, "status": "canceled", "commissionActions": actions})


# ---------------------------------------------------------------------------
# PRODUCT (Pattern 1)
# ---------------------------------------------------------------------------
def _save_product(payload: dict) -> dict:
    product_id = payload.get("productId") or payload.get("id")
    name = payload.get("name")
    price = payload.get("price")
    active = payload.get("active", True)
    sku = payload.get("sku")
    hook = payload.get("hook")
    tags = payload.get("tags")
    images = payload.get("images")

    if not name or price is None:
        return _json_response(200, {"message": "name y price son obligatorios", "Error": "BadRequest"})

    now = _now_iso()

    if product_id is not None:
        existing = _get_by_id("PRODUCT", int(product_id))
        if existing:
            updates = []
            eav = {":u": now}
            ean = {}

            if "name" in payload:
                updates.append("#n = :n")
                eav[":n"] = name
                ean["#n"] = "name"
            if "price" in payload:
                updates.append("price = :p")
                eav[":p"] = _to_decimal(price)
            if "active" in payload:
                updates.append("active = :a")
                eav[":a"] = bool(active)
            if "sku" in payload:
                updates.append("sku = :sku")
                eav[":sku"] = sku
            if "hook" in payload:
                updates.append("hook = :h")
                eav[":h"] = hook
            if isinstance(tags, list):
                updates.append("tags = :t")
                eav[":t"] = tags
            if isinstance(images, list):
                updates.append("images = :im")
                eav[":im"] = images

            updates.append("updatedAt = :u")
            update_expression = "SET " + ", ".join(updates)
            updated = _update_by_id("PRODUCT", int(product_id), update_expression, eav, ean or None)
            return _json_response(200, {"product": updated})

    # Create new
    product_id = int(product_id) if product_id is not None else int(datetime.utcnow().timestamp() * 1000)
    item = {
        "entityType": "product",
        "productId": int(product_id),
        "name": name,
        "price": _to_decimal(price),
        "active": bool(active),
        "sku": sku,
        "hook": hook,
        "createdAt": now,
        "updatedAt": now,
    }
    if isinstance(tags, list):
        item["tags"] = tags
    if isinstance(images, list):
        item["images"] = images
    main = _put_entity("PRODUCT", int(product_id), item, created_at_iso=now)
    return _json_response(201, {"product": main})


def _get_product(product_id: Any) -> dict:
    item = _get_by_id("PRODUCT", int(product_id))
    if not item:
        return _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})
    return _json_response(200, {"product": item})


# ---------------------------------------------------------------------------
# ASSET (Pattern 1)
# ---------------------------------------------------------------------------
def _create_asset(payload: dict) -> dict:
    name = payload.get("name")
    content_base64 = payload.get("contentBase64")
    content_type = payload.get("contentType") or "image/png"
    if not name or not content_base64:
        return _json_response(200, {"message": "name y contentBase64 son obligatorios", "Error": "BadRequest"})

    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        return _json_response(200, {"message": "contentBase64 invalido", "Error": "BadRequest"})

    asset_id = f"assets/{uuid.uuid4()}-{name}"
    _s3.put_object(
        Bucket=BUCKET_NAME,
        Key=asset_id,
        Body=raw,
        ContentType=content_type,
        ACL="public-read",
    )
    url = _public_s3_url(BUCKET_NAME, asset_id, AWS_REGION)
    now = _now_iso()

    item = {
        "entityType": "asset",
        "assetId": asset_id,
        "name": name,
        "contentType": content_type,
        "url": url,
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("ASSET", asset_id, item, created_at_iso=now)
    return _json_response(201, {"asset": main})


def _get_asset(asset_id: str) -> dict:
    item = _get_by_id("ASSET", asset_id)
    if not item:
        return _json_response(200, {"message": "Asset no encontrado", "Error": "NoEncontrado"})
    return _json_response(200, {"asset": item})


# ---------------------------------------------------------------------------
# PRODUCT-ASSET link (still direct by composite key under Pattern 1 bucket)
# You can also Pattern-1 it, but simplest is keep as a separate bucket entity.
# ---------------------------------------------------------------------------
def _create_product_asset(payload: dict) -> dict:
    product_id = payload.get("productId")
    asset_id = payload.get("assetId") or payload.get("assetKey")
    if not product_id or not asset_id:
        return _json_response(200, {"message": "productId y assetId son obligatorios", "Error": "BadRequest"})

    link_id = f"{product_id}#{asset_id}"
    now = _now_iso()
    item = {
        "entityType": "productAsset",
        "productId": int(product_id),
        "assetId": asset_id,
        "linkId": link_id,
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("PRODUCT_ASSET", link_id, item, created_at_iso=now)
    return _json_response(201, {"productAsset": main})


# ---------------------------------------------------------------------------
# CUSTOMER (Pattern 1)
# ---------------------------------------------------------------------------
def _create_customer(payload: dict) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    if not name or not email:
        return _json_response(200, {"message": "name y email son obligatorios", "Error": "BadRequest"})

    customer_id = payload.get("customerId")
    if not customer_id:
        customer_id = int(datetime.utcnow().timestamp() * 1000)

    raw_leader_id = payload.get("leaderId")
    leader_id, level = _resolve_leader_and_level(raw_leader_id)

    now = _now_iso()
    item = {
        "entityType": "customer",
        "customerId": customer_id,
        "name": name,
        "email": email,
        "phone": payload.get("phone"),
        "address": payload.get("address"),
        "city": payload.get("city"),
        "leaderId": leader_id,
        "level": level,
        "isAssociate": bool(payload.get("isAssociate", True)),
        "activeBuyer": False,
        "discountRate": Decimal("0"),
        "discount": "0%",
        "commissions": Decimal("0"),
        "createdAt": now,
        "updatedAt": now,
    }

    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    return _json_response(
        201,
        {
            "customer": {
                "id": customer_id,
                "name": main.get("name"),
                "email": main.get("email"),
                "leaderId": main.get("leaderId"),
                "level": main.get("level"),
                "isAssociate": main.get("isAssociate"),
                "discount": main.get("discount"),
                "activeBuyer": bool(main.get("activeBuyer")),
                "discountRate": float(main.get("discountRate") or 0),
                "commissions": float(main.get("commissions") or 0),
            }
        },
    )


def _create_account(payload: dict) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")
    confirm = payload.get("confirmPassword")
    if not name or not email or not password:
        return _json_response(200, {"message": "name, email y password son obligatorios", "Error": "BadRequest"})
    if password != confirm:
        return _json_response(200, {"message": "Las contraseÃ±as no coinciden", "Error": "BadRequest"})

    email_norm = _normalize_email(email)
    if not email_norm:
        return _json_response(200, {"message": "email invalido", "Error": "BadRequest"})
    if _get_auth_by_email(email_norm):
        return _json_response(200, {"message": "El correo ya esta registrado", "Error": "Conflict"})

    customer_id = payload.get("customerId")
    if not customer_id:
        customer_id = int(datetime.utcnow().timestamp() * 1000)

    leader_token = payload.get("referralToken") or payload.get("leaderId")
    raw_leader_id = _parse_int_or_str(leader_token)
    leader_id, level = _resolve_leader_and_level(raw_leader_id)

    product_id = _parse_int_or_str(payload.get("productId") or payload.get("refProductId"))

    now = _now_iso()
    password_hash = _hash_password(str(password))
    item = {
        "entityType": "customer",
        "customerId": customer_id,
        "name": name,
        "email": email_norm,
        "phone": payload.get("phone"),
        "address": payload.get("address"),
        "city": payload.get("city"),
        "leaderId": leader_id,
        "level": level,
        "isAssociate": bool(payload.get("isAssociate", True)),
        "activeBuyer": False,
        "discountRate": Decimal("0"),
        "discount": "0%",
        "commissions": Decimal("0"),
        "passwordHash": password_hash,
        "refProductId": product_id,
        "createdAt": now,
        "updatedAt": now,
    }

    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    _create_auth_record(email_norm, password_hash, customer_id, role="cliente")
    return _json_response(
        201,
        {
            "customer": {
                "id": customer_id,
                "name": main.get("name"),
                "email": main.get("email"),
                "leaderId": main.get("leaderId"),
                "level": main.get("level"),
                "isAssociate": main.get("isAssociate"),
                "discount": main.get("discount"),
                "activeBuyer": bool(main.get("activeBuyer")),
                "discountRate": float(main.get("discountRate") or 0),
                "commissions": float(main.get("commissions") or 0),
            }
        },
    )


def _get_customer(customer_id: str) -> dict:
    item = _get_by_id("CUSTOMER", int(customer_id))
    if not item:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})
    return _json_response(200, {"customer": item})


def _get_network(customer_id: str, query: dict) -> dict:
    depth = int(query.get("depth") or 3)
    customers_raw = _query_bucket("CUSTOMER", limit=500, scan_forward=False)

    nodes = {}
    for c in customers_raw:
        cid = str(c.get("customerId"))
        nodes[cid] = {
            "id": cid,
            "name": c.get("name"),
            "leaderId": str(c.get("leaderId")) if c.get("leaderId") else None,
            "children": [],
        }

    for cid, node in nodes.items():
        lid = node.get("leaderId")
        if lid and lid in nodes:
            nodes[lid]["children"].append(node)

    root = nodes.get(str(customer_id))
    if not root:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    def trim(n: dict, d: int) -> dict:
        if d <= 0:
            return {**n, "children": []}
        return {**n, "children": [trim(ch, d - 1) for ch in n.get("children", [])]}

    return _json_response(200, {"network": trim(root, depth)})


# ---------------------------------------------------------------------------
# Rewards API
# ---------------------------------------------------------------------------
def _get_rewards_config() -> dict:
    cfg = _load_rewards_config()
    return _json_response(200, {"config": cfg})


def _put_rewards_config(payload: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        return _json_response(200, {"message": "config invalida", "Error": "BadRequest"})

    cfg = _default_rewards_config()
    cfg.update(payload)

    cfg["activationNetMin"] = float(cfg.get("activationNetMin", 2500))
    cfg["payoutDay"] = int(cfg.get("payoutDay", 10))
    cfg["commissionLevels"] = [float(x) for x in (cfg.get("commissionLevels") or [0.10, 0.05, 0.03])]

    tiers = []
    for t in (cfg.get("discountTiers") or []):
        tiers.append(
            {
                "min": float(t.get("min", 0)),
                "max": (None if t.get("max") in (None, "") else float(t.get("max"))),
                "rate": float(t.get("rate", 0)),
            }
        )
    cfg["discountTiers"] = tiers

    saved = _save_rewards_config(cfg)
    return _json_response(200, {"config": saved})


def _get_associate_month(associate_id: str, month_key: str) -> dict:
    item = _get_month_state(associate_id, month_key)
    out = {
        "associateId": associate_id,
        "monthKey": month_key,
        "netVolume": float(_to_decimal(item.get("netVolume"))),
        "isActive": bool(item.get("isActive")),
        "updatedAt": item.get("updatedAt"),
    }
    return _json_response(200, {"month": out})


def _get_associate_commissions(associate_id: str, query: dict) -> dict:
    month = query.get("month")
    status = (query.get("status") or "").lower()
    limit = min(200, int(query.get("limit") or 100))

    pk = _commission_pk(associate_id)
    resp = _table.query(KeyConditionExpression=Key("PK").eq(pk), Limit=limit, ScanIndexForward=False)
    items = resp.get("Items", []) or []

    def ok(it: dict) -> bool:
        if month and (it.get("monthKey") != month):
            return False
        if status and (it.get("status") or "").lower() != status:
            return False
        return True

    rows = []
    total = Decimal("0")
    for it in items:
        if not ok(it):
            continue
        amt = _to_decimal(it.get("amount"))
        total += amt
        rows.append(
            {
                "id": it.get("SK"),
                "orderId": it.get("orderId"),
                "monthKey": it.get("monthKey"),
                "level": it.get("level"),
                "rate": float(_to_decimal(it.get("rate"))),
                "amount": float(amt),
                "status": it.get("status"),
                "sourceBuyerId": it.get("sourceBuyerId"),
                "reasonVoid": it.get("reasonVoid"),
                "createdAt": it.get("createdAt"),
            }
        )

    return _json_response(200, {"associateId": associate_id, "count": len(rows), "total": float(total), "commissions": rows})


# ---------------------------------------------------------------------------
# Admin dashboard (lists via BUCKET Query)
# ---------------------------------------------------------------------------
def _build_admin_warnings(paid_count: int, pending_count: int, commissions_count: int) -> list:
    warnings = []
    if commissions_count:
        warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
    if paid_count:
        warnings.append({"type": "shipping", "text": f"{paid_count} pedidos pagados sin envío", "severity": "medium"})
    if pending_count:
        warnings.append({"type": "payments", "text": f"{pending_count} pedidos pendientes de pago", "severity": "low"})
    return warnings


def _get_admin_dashboard() -> dict:
    customers_raw = _query_bucket("CUSTOMER", limit=500, scan_forward=False)
    orders_raw = _query_bucket("ORDER", limit=500, scan_forward=False)
    products_raw = _query_bucket("PRODUCT", limit=500, scan_forward=False)

    customers = [
        {
            "id": item.get("customerId"),
            "name": item.get("name"),
            "email": item.get("email"),
            "leaderId": item.get("leaderId"),
            "level": item.get("level"),
            "discount": item.get("discount"),
            "commissions": float(item.get("commissions") or 0),
        }
        for item in customers_raw
    ]

    orders = [
        {
            "id": item.get("orderId"),
            "createdAt": item.get("createdAt"),
            "customer": item.get("customerName"),
            "total": float(item.get("netTotal") or item.get("total") or 0),
            "status": item.get("status"),
        }
        for item in orders_raw
    ]

    products = [
        {
            "id": int(item.get("productId")),
            "name": item.get("name"),
            "price": float(item.get("price") or 0),
            "active": bool(item.get("active")),
            "sku": item.get("sku"),
            "hook": item.get("hook"),
            "tags": item.get("tags"),
            "images": item.get("images"),
        }
        for item in products_raw
    ]

    status_counts = {"pending": 0, "paid": 0, "delivered": 0, "canceled": 0, "refunded": 0}
    for order in orders:
        st = (order.get("status") or "").lower()
        if st in status_counts:
            status_counts[st] += 1

    customers_by_level = {}
    commissions_count = 0
    commissions_total = 0
    for customer in customers:
        level = customer.get("level") or "Sin nivel"
        customers_by_level[level] = customers_by_level.get(level, 0) + 1
        commission_value = float(customer.get("commissions") or 0)
        if commission_value > 0:
            commissions_count += 1
            commissions_total += commission_value

    sales_total = sum(order.get("total", 0) for order in orders)
    average_ticket = sales_total / len(orders) if orders else 0
    active_products = sum(1 for product in products if product.get("active"))

    warnings = _build_admin_warnings(status_counts["paid"], status_counts["pending"], commissions_count)

    return _json_response(
        200,
        {
            "kpis": {
                "salesTotal": sales_total,
                "averageTicket": average_ticket,
                "activeProducts": active_products,
                "customersTotal": len(customers),
                "commissionsTotalPending": commissions_total,
            },
            "statusCounts": status_counts,
            "customersByLevel": customers_by_level,
            "warnings": warnings,
            "customers": customers,
            "orders": orders,
            "products": products,
        },
    )


def _pick_product_image(images: Optional[list], preferred_sections: List[str]) -> str:
    if not images or not isinstance(images, list):
        return ""
    for section in preferred_sections:
        for img in images:
            if img.get("section") == section and img.get("url"):
                return _normalize_asset_url(img.get("url"))
    for img in images:
        if img.get("url"):
            return _normalize_asset_url(img.get("url"))
    return ""

def _get_product_of_month_item() -> Optional[dict]:
    return _get_by_id("PRODUCT_OF_MONTH", "current")


def _get_product_summary(item: dict) -> dict:
    images = item.get("images") or []
    tags = item.get("tags") or []
    badge = str(tags[0]) if isinstance(tags, list) and tags else ""
    img = _pick_product_image(images, ["miniatura", "landing", "redes"])
    return {
        "id": str(item.get("productId")),
        "name": item.get("name"),
        "price": float(item.get("price") or 0),
        "badge": badge,
        "img": img,
        "hook": item.get("hook") or "",
        "images": images,
        "tags": tags,
    }


def _set_product_of_month(payload: dict) -> dict:
    product_id = payload.get("productId") or payload.get("id")
    if not product_id:
        return _json_response(200, {"message": "productId es obligatorio", "Error": "BadRequest"})

    product = _get_by_id("PRODUCT", int(product_id))
    if not product:
        return _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})

    now = _now_iso()
    existing = _get_product_of_month_item()
    if existing:
        updated = _update_by_id(
            "PRODUCT_OF_MONTH",
            "current",
            "SET productId = :p, updatedAt = :u",
            {":p": int(product_id), ":u": now},
        )
        return _json_response(200, {"productOfMonth": updated})

    item = {
        "entityType": "productOfMonth",
        "productId": int(product_id),
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("PRODUCT_OF_MONTH", "current", item, created_at_iso=now)
    return _json_response(201, {"productOfMonth": main})


def _get_product_of_month() -> dict:
    item = _get_product_of_month_item()
    if not item:
        return _json_response(200, {"productOfMonth": None})
    return _json_response(200, {"productOfMonth": item})

def _get_user_dashboard(query: dict, headers: dict) -> dict:
    user_id, is_guest = _resolve_user_context(query or {}, headers or {})
    customer = _get_by_id("CUSTOMER", int(user_id)) if user_id is not None else None

    products_raw = _query_bucket("PRODUCT", limit=500, scan_forward=False)
    products = []
    featured = []
    product_of_month = None

    for item in products_raw:
        summary = _get_product_summary(item)
        products.append({"id": summary["id"], "name": summary["name"], "price": summary["price"], "badge": summary["badge"], "img": summary["img"]})
        if len(featured) < 4:
            images = item.get("images") or []
            story = _pick_product_image(images, ["redes"]) or summary["img"]
            feed = _pick_product_image(images, ["miniatura", "redes"]) or summary["img"]
            banner = _pick_product_image(images, ["landing"]) or summary["img"]
            featured.append({"id": summary["id"], "label": summary["name"], "hook": summary["hook"], "story": story, "feed": feed, "banner": banner})

    pom_item = _get_product_of_month_item()
    if pom_item:
        product = _get_by_id("PRODUCT", int(pom_item.get("productId")))
        if product:
            product_of_month = _get_product_summary(product)

    # Defaults become computed + persisted (only for logged-in customers)
    cfg = _load_rewards_config()
    month_key = _month_key()

    customers_raw = _query_bucket("CUSTOMER", limit=500, scan_forward=False)

    computed_network_members = None
    computed_goals = None

    if customer and isinstance(customer, dict):
        # Build tree with month consumption
        tree = _build_network_tree_with_month(str(customer.get("customerId")), month_key, customers_raw, cfg)
        computed_network_members = _network_members_from_tree(tree, max_rows=30)

        # Goals from customer + network
        computed_goals = _build_goals(customer, tree, customers_raw, cfg)

        # buyAgainIds seed/update logic
        buy_again_ids = _compute_buy_again_ids_and_maybe_update(customer, products)

        # persist the computed fields
        _persist_customer_dashboard_fields(customer.get("customerId"), computed_goals, computed_network_members, buy_again_ids)
    else:
        buy_again_ids = [p["id"] for p in products[:3]]

    payload = {
        "isGuest": bool(is_guest),
        "settings": {
            "cutoffDay": 25,
            "cutoffHour": 23,
            "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id),
            "networkGoal": 300,
        },
        "goals": (computed_goals if computed_goals is not None else []),
        "products": products,
        "featured": featured,
        "productOfMonth": product_of_month,
        "networkMembers": (computed_network_members if computed_network_members is not None else []),
        "buyAgainIds": buy_again_ids,
    }
    return _json_response(200, payload)



def _compute_buy_again_ids(customer: Optional[dict], products: List[dict]) -> List[str]:
    if not customer or not isinstance(customer, dict):
        return []
    counts = customer.get("productCounts")
    if not isinstance(counts, dict) or not counts:
        return []
    ordered = sorted(counts.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
    top = [str(pid) for pid, _ in ordered[:3]]
    return top


def _update_customer_product_stats(customer_id: Any, order_item: dict) -> None:
    if customer_id is None:
        return
    items = order_item.get("items") or []
    if not items:
        return
    try:
        customer = _get_by_id("CUSTOMER", customer_id)
    except Exception:
        customer = None
    counts = customer.get("productCounts") if isinstance(customer, dict) else None
    if not isinstance(counts, dict):
        counts = {}

    for it in items:
        pid = it.get("productId")
        if pid is None:
            continue
        key = str(pid)
        qty = int(it.get("quantity") or 1)
        prev = counts.get(key) or 0
        counts[key] = int(prev) + qty

    try:
        _update_by_id(
            "CUSTOMER",
            customer_id,
            "SET productCounts = :pc, updatedAt = :u",
            {":pc": counts, ":u": _now_iso()},
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Auth (demo)
# ---------------------------------------------------------------------------
def _login(payload: dict) -> dict:
    username = payload.get("username")
    email = payload.get("email") or username
    password = payload.get("password")
    if not email or not password:
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    identifier = (email or "").strip()
    for user in _LOGIN_USERS:
        if identifier in {user.get("username"), user.get("email")} and user["password"] == password:
            return _json_response(200, {"token": "demo-token", "user": user["user"]})

    auth = _get_auth_by_email(identifier)
    if not auth:
        customer = _find_customer_by_email(identifier)
        if customer and customer.get("passwordHash") == _hash_password(str(password)):
            auth = _create_auth_record(identifier, customer.get("passwordHash"), customer.get("customerId"))
        else:
            return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    if auth.get("passwordHash") != _hash_password(str(password)):
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    customer_id = auth.get("customerId")
    customer = _get_by_id("CUSTOMER", int(customer_id)) if customer_id is not None else None
    if not customer:
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    discount_rate = _to_decimal(customer.get("discountRate"))
    discount_percent = int((discount_rate * Decimal("100")).quantize(Decimal("1"))) if discount_rate else 0

    user = {
        "userId": str(customer_id),
        "name": customer.get("name"),
        "role": auth.get("role") or "cliente",
        "discountPercent": discount_percent,
        "discountActive": bool(customer.get("activeBuyer") or discount_rate > 0),
        "level": customer.get("level"),
    }
    return _json_response(200, {"token": "demo-token", "user": user})


# ---------------------------------------------------------------------------
# Lambda entrypoint / router
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
    if method == "OPTIONS":
        return _json_response(200, {"ok": True})

    segments = _path_segments(event)
    query = _get_query_params(event)

    if not segments:
        return _json_response(200, {"ok": True})

    # Auth
    if segments[0] == "login" and method == "POST":
        return _login(_parse_body(event))
    if segments[0] == "crearcuenta" and method == "POST":
        return _create_account(_parse_body(event))

    # Rewards config
    if segments == ["config", "rewards"]:
        if method == "GET":
            return _get_rewards_config()
        if method == "PUT":
            return _put_rewards_config(_parse_body(event))

    # Associate views
    if len(segments) == 4 and segments[0] == "associates" and segments[2] == "month" and method == "GET":
        return _get_associate_month(segments[1], segments[3])

    if len(segments) == 3 and segments[0] == "associates" and segments[2] == "commissions" and method == "GET":
        return _get_associate_commissions(segments[1], query)

    # Network
    if segments[0] == "network" and len(segments) == 2 and method == "GET":
        return _get_network(segments[1], query)

    # Assets
    if segments[0] == "assets":
        if method == "POST" and len(segments) == 1:
            return _create_asset(_parse_body(event))
        if method == "GET" and len(segments) == 2:
            return _get_asset(segments[1])

    # Products
    if segments[0] == "products":
        if len(segments) == 2 and segments[1] == "product-of-month":
            if method == "GET":
                return _get_product_of_month()
            if method == "POST":
                return _set_product_of_month(_parse_body(event))
        if len(segments) == 1 and method == "POST":
            return _save_product(_parse_body(event))
        if len(segments) == 2 and method == "GET":
            return _get_product(segments[1])
        if len(segments) == 2 and segments[1] == "assets" and method == "POST":
            return _create_product_asset(_parse_body(event))

    # Orders
    if segments[0] == "orders":
        if method == "POST" and len(segments) == 1:
            return _create_order(_parse_body(event))
        if method == "PATCH" and len(segments) == 2:
            return _update_order_status(segments[1], _parse_body(event))
        if method == "POST" and len(segments) == 3 and segments[2] == "refund":
            return _refund_order(segments[1], _parse_body(event))
        if method == "POST" and len(segments) == 3 and segments[2] == "cancel":
            return _cancel_order(segments[1], _parse_body(event))

    # Customers
    if segments[0] == "customers":
        if method == "POST" and len(segments) == 1:
            return _create_customer(_parse_body(event))
        if method == "GET" and len(segments) == 2:
            return _get_customer(segments[1])

    # Admin
    if segments == ["admin", "dashboard"] and method == "GET":
        return _get_admin_dashboard()

    # User dashboard
    if segments == ["user-dashboard"] and method == "GET":
        return _get_user_dashboard(query, event.get("headers") or {})

    return _json_response(404, {"message": "Ruta no encontrada", "path": "/" + "/".join(segments), "Error": "NotFound"})

