import base64
import hashlib
import json
import os
import random
import uuid
import functools
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
from boto3.dynamodb.conditions import Attr, Key

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")
BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MERCADOLIBRE_ACCESS_TOKEN = (os.getenv("MERCADOLIBRE_ACCESS_TOKEN") or "").strip()
_MERCADOLIBRE_ENABLED_RAW = (
    os.getenv("MERCADOLIBRE_ENABLED")
    or os.getenv("MERCADO_LIBRE_ENABLED")
    or ""
).strip().lower()
MERCADOLIBRE_ENABLED_ENV: Optional[bool] = (
    None if _MERCADOLIBRE_ENABLED_RAW == "" else _MERCADOLIBRE_ENABLED_RAW in {"1", "true", "yes", "on"}
)

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)
_s3 = boto3.client("s3", region_name=AWS_REGION)

# Decimal Constants for performance
D_ZERO = Decimal("0")
D_ONE = Decimal("1")
D_CENT = Decimal("0.01")
MAX_NETWORK_DEPTH = 3
MAX_COMMISSION_LEVELS = 3
DEFAULT_COMMISSION_BY_DEPTH = {
    1: Decimal("0.10"),
    2: Decimal("0.05"),
    3: Decimal("0.03"),
}

# ---------------------------------------------------------------------------
# JSON / HTTP helpers
# ---------------------------------------------------------------------------
def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": (
                "Content-Type,Authorization,"
                "X-User-Id,X-User-Name,X-User-Role,"
                "x-user-id,x-user-name,x-user-role,"
                "X-Webhook-Secret,x-webhook-secret,"
                "X-MercadoLibre-Signature,x-mercadolibre-signature"
            ),
        },
        "body": json.dumps(payload, default=_json_default),
    }

def _public_s3_url(bucket: str, key: str, region: str) -> str:
    if not bucket or not key:
        return ""
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
    # Use timezone-aware UTC
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _generate_order_id(now: Optional[datetime] = None, max_attempts: int = 6) -> str:
    base_dt = now or datetime.now(timezone.utc)
    prefix = base_dt.strftime("%y%m%d")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # Try simpler suffix first
    for _ in range(max_attempts):
        suffix = "".join(random.choices(alphabet, k=6))
        order_id = f"{prefix}{suffix}"
        if not _get_by_id("ORDER", order_id):
            return order_id
            
    # Fallback
    suffix = "".join(random.choices(alphabet, k=8))
    return f"{prefix}{suffix}"

def _month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"

def _prev_month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    if d.month == 1:
        return f"{d.year - 1:04d}-12"
    return f"{d.year:04d}-{d.month - 1:02d}"

def _to_decimal(n: Any) -> Decimal:
    if isinstance(n, Decimal):
        return n
    if n is None:
        return D_ZERO
    try:
        return Decimal(str(n))
    except Exception:
        return D_ZERO

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
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            return {}
    try:
        return json.loads(body)
    except Exception:
        return {}

def _get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}

def _get_path(event: dict) -> str:
    # Normalized path extraction
    path_params = event.get("pathParameters") or {}
    proxy = path_params.get("proxy")
    
    if proxy:
        path = f"/{proxy}"
    else:
        path = event.get("path", "/") or "/"

    stage = (event.get("requestContext") or {}).get("stage")
    if stage and path.startswith(f"/{stage}/"):
        path = path[len(stage) + 1:]

    if path.startswith("/Multinivel/"):
        path = path[11:] # len("/Multinivel")

    return path if path.startswith("/") else f"/{path}"

def _path_segments(event: dict) -> List[str]:
    path = _get_path(event).strip("/")
    return [seg for seg in path.split("/") if seg]

def _month_start_end(dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    d = dt or datetime.now(timezone.utc)
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
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.fromisoformat(iso)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Network & Goals Logic
# ---------------------------------------------------------------------------
def _build_network_tree_with_month(
    root_id: Any,
    month_key: str,
    customers_raw: List[dict],
    cfg: dict,
    max_depth: Optional[int] = None,
) -> dict:
    nodes: Dict[str, dict] = {}
    children_by_leader: Dict[str, List[str]] = {}
    
    root_id_str = str(root_id)
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))

    # Pre-process customers into nodes (O(N))
    for c in customers_raw:
        cid = str(c.get("customerId"))
        if not cid:
            continue
        print(f"LeadderId for customerId {cid} is {c.get('leaderId')}")
        nodes[cid] = {
            "id": cid,
            "name": c.get("name") or "",
            "level": (c.get("level") or "").strip(),
            "leaderId": str(c.get("leaderId")) if c.get("leaderId") else None,
            "createdAt": c.get("createdAt"),
            "monthSpend": 0.0,
            "isActive": False,
            "children": [],
        }
        
        lid = nodes[cid]["leaderId"]
        if lid:
            children_by_leader.setdefault(lid, []).append(cid)

    # Fill metrics. Note: _get_month_state causes N+1 if not careful.
    # Ideally, we should fetch all month states in batch, but Pattern 1 structure makes batching via PK hard without Query.
    # We proceed with individual lookups but relying on DynamoDB speed. 
    # Optimization: Only fetch for the relevant subtree if possible? 
    # For now, we iterate all nodes as per original logic, but ensure types are handled efficiently.
    
    # NOTE: If customers_raw is huge, this loop is slow. 
    # However, without changing schema to aggregate month stats, we must read.
    for cid, n in nodes.items():
        st = _get_month_state(cid, month_key)
        netv = _to_decimal(st.get("netVolume"))
        n["monthSpend"] = float(netv)
        n["isActive"] = bool(netv >= activation_min)

    # Assemble tree
    for lid, kids in children_by_leader.items():
        if lid in nodes:
            # Sort children by spend desc directly here
            child_nodes = [nodes[k] for k in kids if k in nodes]
            child_nodes.sort(key=lambda x: x["monthSpend"], reverse=True)
            nodes[lid]["children"] = child_nodes

    root = nodes.get(root_id_str)
    if not root:
        return {"id": root_id_str, "name": "", "level": "", "monthSpend": 0.0, "children": []}

    if max_depth is not None:
        root = _trim_tree_by_depth(root, max_depth)

    # Recursive sort is handled by bottom-up build or post-traversal.
    # Since we sorted when attaching, we just need to ensure the structure is returned.
    return root

def _trim_tree_by_depth(root: dict, max_depth: int) -> dict:
    if max_depth is None:
        return root

    def _trim(node: dict, depth: int) -> dict:
        if depth >= max_depth:
            node["children"] = []
            return node
        children = node.get("children") or []
        node["children"] = [_trim(ch, depth + 1) for ch in children]
        return node

    return _trim(root, 0)

def _flatten_tree(root: dict) -> List[dict]:
    out = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        out.append({**node, "depth": depth})
        # Reverse to maintain order when popping
        children = node.get("children", [])
        if children:
            for ch in reversed(children):
                stack.append((ch, depth + 1))
    return out

def _network_members_from_tree(root: dict, max_rows: int = 30) -> List[dict]:
    rows = []
    # Flattening efficiently
    for n in _flatten_tree(root):
        if n.get("depth", 0) == 0:
            continue
        
        spend = n.get("monthSpend", 0.0)
        status = "Activa" if n.get("isActive") else ("En progreso" if spend > 0 else "Inactiva")
        print(f"LeaderId: {n.get('leaderId')}, MemberId: {n.get('id')}, Spend: {spend}, Status: {status}")
        rows.append({
            "name": n.get("name") or "",
            "level": f"L{n.get('depth')}",
            "spend": spend,
            "status": status,
            "id": n.get("id"),
            "leaderId": n.get("leaderId"),
        })
        if len(rows) >= max_rows:
            break
    return rows

def _resolve_leader_id(leader_id: Any) -> Optional[Any]:
    if leader_id is None or leader_id == "":
        return None
    lid = _parse_int_or_str(leader_id)
    leader = _get_by_id("CUSTOMER", int(lid)) if isinstance(lid, int) else _get_by_id("CUSTOMER", lid)
    return lid if leader else None

def _discount_tier_targets(cfg: dict) -> List[dict]:
    tiers = cfg.get("discountTiers") or []
    normalized = []
    for t in tiers:
        normalized.append({
            "min": float(_to_decimal(t.get("min"))),
            "max": float(_to_decimal(t.get("max"))) if t.get("max") is not None else None,
            "rate": float(_to_decimal(t.get("rate"))),
        })
    normalized.sort(key=lambda x: x["rate"])
    return normalized

def _count_new_direct_members_this_month(root_id: str, customers_raw: List[dict], now_dt: Optional[datetime]=None) -> int:
    start, end = _month_start_end(now_dt)
    cnt = 0
    root_id_str = str(root_id)
    for c in customers_raw:
        if str(c.get("leaderId") or "") != root_id_str:
            continue
        created = _iso_to_dt(c.get("createdAt"))
        if created and start <= created < end:
            cnt += 1
    return cnt

def _any_member_added_member_this_month(root_tree: dict, customers_raw: List[dict], now_dt: Optional[datetime]=None) -> bool:
    start, end = _month_start_end(now_dt)
    
    # Get all IDs in the tree
    tree_ids = {n["id"] for n in _flatten_tree(root_tree)}
    
    for c in customers_raw:
        lid = str(c.get("leaderId") or "")
        if lid in tree_ids:
            created = _iso_to_dt(c.get("createdAt"))
            if created and start <= created < end:
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
        return (False, 0)
    
    for ch in direct:
        if _to_decimal(ch.get("monthSpend")) < activation_min:
            return (False, len(direct))
            
    return (True, len(direct))

def _build_goals(customer: dict, root_tree: dict, customers_raw: List[dict], cfg: dict) -> List[dict]:
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    tiers = _discount_tier_targets(cfg)
    level_rates = [0.30, 0.40, 0.50]

    cid = str(customer.get("customerId"))

    st = _get_month_state(cid, _month_key())
    my_net = _to_decimal(st.get("netVolume"))
    my_active = my_net >= activation_min

    my_discount_rate = _to_decimal(customer.get("discountRate"))
    computed_rate = _calc_discount_rate(my_net, cfg.get("discountTiers") or [])
    effective_rate = max(my_discount_rate, computed_rate)
    
    now_dt = datetime.now(timezone.utc)
    new_direct = _count_new_direct_members_this_month(cid, customers_raw, now_dt)

    any_member_active = _any_member_reached_activation(root_tree, activation_min)
    all_direct_ok, direct_count = _all_direct_reached_activation(root_tree, activation_min)
    any_member_added = _any_member_added_member_this_month(root_tree, customers_raw, now_dt)

    def tier_min_for_rate(rate_threshold: float) -> float:
        for t in tiers:
            if t["rate"] >= rate_threshold:
                return t["min"]
        return float(activation_min)

    goals = []

    # 1. Active Buyer
    goals.append({
        "key": "active",
        "title": "Alcanzar consumo mensual para ser usuario activo",
        "subtitle": f"Meta mensual: ${int(activation_min):,} neto",
        "target": float(activation_min),
        "base": float(my_net),
        "achieved": my_active,
        "locked": False,
        "isCountGoal": False,
        "ctaText": "Ir a tienda",
        "ctaFragment": "merchant",
    })

    # Discount levels
    for idx, r in enumerate(level_rates, start=1):
        target = tier_min_for_rate(r)
        achieved = float(effective_rate) >= r
        goals.append({
            "key": f"discount_{idx}",
            "title": f"Alcanzar el nivel {idx} de descuento",
            "subtitle": f"Objetivo: {int(r*100)}% (consumo aprox. desde ${int(target):,})",
            "target": target,
            "base": float(my_net),
            "achieved": achieved,
            "locked": False,
            "isCountGoal": False,
            "ctaText": "Completar consumo",
            "ctaFragment": "merchant",
        })

    # Invite goal
    locked_invite = False
    goals.insert(2, {
        "key": "invite",
        "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": "Invita a 1 persona y actÃ­vala",
        "target": 1,
        "base": int(new_direct),
        "achieved": bool(new_direct >= 1),
        "locked": False,
        "isCountGoal": True,
        "ctaText": "Invitar ahora",
        "ctaFragment": "links",
    })

    # Network active goal
    goals.insert(4, {
        "key": "network_one_active",
        "title": "Lograr que un miembro de la red alcance su meta mensual",
        "subtitle": f"Meta por miembro: ${int(activation_min):,} neto",
        "target": 1,
        "base": 1 if any_member_active else 0,
        "achieved": any_member_active,
        "locked": False,
        "isCountGoal": True,
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    # Directs all active
    not_applicable = (direct_count == 0)
    goals.insert(6, {
        "key": "direct_all_active",
        "title": "Lograr que todos los miembros del nivel inmediato inferior logren su meta mensual",
        "subtitle": ("AÃºn no tienes miembros directos" if not_applicable else f"Directos: {direct_count}"),
        "target": direct_count if direct_count else 1,
        "base": direct_count if all_direct_ok and direct_count else 0,
        "achieved": bool(all_direct_ok and direct_count > 0),
        "locked": not_applicable,
        "isCountGoal": True,
        "ctaText": "Impulsar a mi red",
        "ctaFragment": "links",
    })

    # Network replication
    goals.append({
        "key": "network_member_invited",
        "title": "Lograr que un miembro de la red agregue un nuevo miembro",
        "subtitle": "Haz que tu red replique",
        "target": 1,
        "base": 1 if any_member_added else 0,
        "achieved": bool(any_member_added),
        "locked": False,
        "isCountGoal": True,
        "ctaText": "Compartir enlace",
        "ctaFragment": "links",
    })

    # Set Primary/Secondary
    primary_idx = None
    for i, g in enumerate(goals):
        if not g.get("locked") and not g.get("achieved"):
            primary_idx = i
            break
            
    for i, g in enumerate(goals):
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
    if not customer or not isinstance(customer, dict):
        return ([], False)

    counts = customer.get("productCounts")
    existing = customer.get("buyAgainIds")

    if not isinstance(counts, dict) or not counts:
        should_persist = (isinstance(existing, list) and len(existing) > 0)
        return ([], should_persist)

    ordered = sorted(counts.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
    top = [str(pid) for pid, _ in ordered[:3]]

    existing_norm = [str(x) for x in existing] if isinstance(existing, list) else []
    should_persist = (existing_norm[:3] != top)
    return (top, should_persist)

# ---------------------------------------------------------------------------
# Pattern 1: BUCKET PK + REF mapping
# ---------------------------------------------------------------------------
def _bucket_pk(entity: str) -> str:
    return entity.upper()

def _ref_pk(entity: str, entity_id: Any) -> str:
    return f"{entity.upper()}#{entity_id}"

def _make_bucket_sk(created_at_iso: str, entity_id: Any) -> str:
    return f"{created_at_iso}#{entity_id}"

def _put_entity(entity: str, entity_id: Any, item: dict, created_at_iso: Optional[str] = None) -> dict:
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

    # TransactWriteItems could guarantee atomicity, but PutItem is faster/cheaper. 
    # Reliability tradeoff acceptable for this demo scope.
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

def _query_bucket(entity: str, limit: Optional[int] = None, scan_forward: bool = False) -> List[dict]:
    """
    Optimized to handle pagination automatically if limit is not provided,
    ensuring full data retrieval for dashboards.
    """
    pk = _bucket_pk(entity)
    items = []
    
    query_kwargs = {
        "KeyConditionExpression": Key("PK").eq(pk),
        "ScanIndexForward": scan_forward,
    }
    
    if limit:
        query_kwargs["Limit"] = limit
        # Single fetch with limit
        resp = _table.query(**query_kwargs)
        return resp.get("Items", []) or []
    
    # Loop fetch (Pagination)
    while True:
        resp = _table.query(**query_kwargs)
        batch = resp.get("Items", [])
        items.extend(batch)
        
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        query_kwargs["ExclusiveStartKey"] = lek
        
        # Safety break for huge tables to avoid timeout
        if len(items) > 5000:
            break
            
    return items

# ---------------------------------------------------------------------------
# Auth Logic
# ---------------------------------------------------------------------------
_LOGIN_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "email": "admin@demo.local",
        "user": {
            "userId": "admin-001",
            "name": "Admin",
            "role": "admin",
            "canAccessAdmin": True,
            "isSuperUser": True,
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
            "canAccessAdmin": False,
            "privileges": {},
            "discountPercent": 15,
            "discountActive": True,
        },
    },
]

_ALL_PRIVILEGES = [
    "access_screen_orders",
    "access_screen_customers",
    "access_screen_products",
    "access_screen_stocks",
    "access_screen_pos",
    "access_screen_stats",
    "access_screen_settings",
    "order_mark_paid",
    "order_mark_shipped",
    "order_mark_delivered",
    "order_create",
    "customer_add",
    "commissions_register_payment",
    "product_add",
    "product_update",
    "product_set_month",
    "stock_create",
    "stock_create_transfer",
    "stock_add_inventory",
    "stock_mark_damaged",
    "stock_receive_transfer",
    "pos_register_sale",
    "user_mark_admin",
    "user_manage_privileges",
    "config_manage",
]

def _normalize_privileges(raw: Any) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {priv: bool(data.get(priv)) for priv in _ALL_PRIVILEGES}

def _is_super_user_record(auth_user: dict, customer: Optional[dict]) -> bool:
    uid = str(auth_user.get("customerId") or auth_user.get("userId") or "")
    name = (customer.get("name") if isinstance(customer, dict) else auth_user.get("name")) or ""
    return uid == "admin-001" or str(name).strip().lower() == "admin"

def _resolve_actor(headers: Optional[dict], payload: Optional[dict] = None) -> Tuple[Optional[Any], str, str]:
    h = headers or {}
    p = payload or {}
    actor_user_id = _parse_int_or_str(
        h.get("x-user-id")
        or h.get("X-User-Id")
        or p.get("actorUserId")
        or p.get("userId")
        or p.get("createdByUserId")
        or p.get("attendantUserId")
        or p.get("reportedByUserId")
        or p.get("receivedByUserId")
    )
    actor_name = (h.get("x-user-name") or h.get("X-User-Name") or "").strip()
    actor_role = (h.get("x-user-role") or h.get("X-User-Role") or "").strip()
    return actor_user_id, actor_name, actor_role

def _audit_event(action: str, headers: Optional[dict], payload: Optional[dict] = None, target: Optional[dict] = None) -> None:
    actor_user_id, actor_name, actor_role = _resolve_actor(headers, payload or {})
    now = _now_iso()
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    item = {
        "entityType": "adminEvent",
        "eventId": event_id,
        "action": action,
        "actorUserId": actor_user_id,
        "actorName": actor_name,
        "actorRole": actor_role,
        "target": target or {},
        "payload": payload or {},
        "createdAt": now,
        "updatedAt": now,
    }
    try:
        _put_entity("ADMIN_EVENT", event_id, item, created_at_iso=now)
    except Exception:
        pass

def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()

def _get_auth_by_email(email: str) -> Optional[dict]:
    auth_id = _normalize_email(email)
    return _get_by_id("AUTH", auth_id) if auth_id else None

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
    # Optimization: If email was a GSI, this would be faster. 
    # With Pattern 1 bucket scan, it's slow. 
    # However, keeping structure, we use the optimized query bucket.
    customers = _query_bucket("CUSTOMER")
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
    try:
        return f"{int((rate * 100).quantize(D_ONE))}%"
    except Exception:
        return "0%"

def _sync_buyer_benefits(buyer_id: Any, month_key: str, cfg: dict) -> Optional[dict]:
    if buyer_id is None:
        return None

    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))
    tiers = cfg.get("discountTiers") or []

    month_state = _get_month_state(buyer_id, month_key)
    net_volume = _to_decimal(month_state.get("netVolume"))
    active = bool(net_volume >= activation_min)

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
# Business Config (Cached)
# ---------------------------------------------------------------------------
def _ensure_commission_by_depth(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        return cfg

    cbd = cfg.get("commissionByDepth")
    if isinstance(cbd, list):
        mapping = {str(i + 1): cbd[i] for i in range(min(3, len(cbd)))}
    elif isinstance(cbd, dict):
        mapping = cbd
    else:
        mapping = {}

    return {
        **cfg,
        "commissionByDepth": {
            "1": _to_decimal(mapping.get("1", mapping.get(1, DEFAULT_COMMISSION_BY_DEPTH[1]))),
            "2": _to_decimal(mapping.get("2", mapping.get(2, DEFAULT_COMMISSION_BY_DEPTH[2]))),
            "3": _to_decimal(mapping.get("3", mapping.get(3, DEFAULT_COMMISSION_BY_DEPTH[3]))),
        },
    }

def _default_rewards_config() -> dict:
    return {
        "version": "v1",
        "activationNetMin": Decimal("2500"),
        "discountTiers": [
            {"min": Decimal("3600"), "max": Decimal("8000"), "rate": Decimal("0.30")},
            {"min": Decimal("8001"), "max": Decimal("12000"), "rate": Decimal("0.40")},
            {"min": Decimal("12001"), "max": None,           "rate": Decimal("0.50")},
        ],
        "commissionByDepth": {
            "1": Decimal("0.10"),
            "2": Decimal("0.05"),
            "3": Decimal("0.03"),
        },
        "payoutDay": Decimal("10"),
        "cutRule": "hard_cut_no_pass",
    }

def _default_app_config() -> dict:
    return {
        "version": "app-v1",
        "rewards": _default_rewards_config(),
        "orders": {
            "requireStockOnShipped": True,
            "requireDispatchLinesOnShipped": True,
        },
        "pos": {
            "defaultCustomerName": "Venta mostrador",
            "defaultPaymentStatus": "paid_branch",
            "defaultDeliveryStatus": "delivered_branch",
            "orderStatusByDeliveryStatus": {
                "delivered_branch": "delivered",
                "paid_branch": "paid",
            },
        },
        "stocks": {
            "requireLinkedUserForTransferReceive": True,
        },
        "payments": {
            "mercadoLibre": {
                "enabled": False,
                "accessToken": "",
                "checkoutPreferencesUrl": "https://api.mercadopago.com/checkout/preferences",
                "paymentInfoUrlTemplate": "https://api.mercadopago.com/v1/payments/{payment_id}",
                "notificationUrl": "https://m85v7secp8.execute-api.us-east-1.amazonaws.com/default/Multinivel/webhooks/mercadolibre",
                "successUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=success",
                "failureUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=failure",
                "pendingUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=pending",
                "currencyId": "MXN",
                "webhookSecret": "",
            },
        },
        "adminWarnings": {
            "showCommissions": True,
            "showShipping": True,
            "showPendingPayments": True,
            "showPendingTransfers": True,
            "showPosSalesToday": True,
        },
    }

def _legacy_rewards_config_entity_id() -> str:
    return "rewards-v1"

def _app_config_entity_id() -> str:
    return "app-v1"

def _merge_dict(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _merge_dict(merged.get(key), value)
        return merged
    return override if override is not None else base

def _normalize_rewards_config(raw: Any) -> dict:
    base = _default_rewards_config()
    merged = _merge_dict(base, raw if isinstance(raw, dict) else {})
    cfg = _ensure_commission_by_depth(merged)
    tiers_raw = cfg.get("discountTiers") or []
    tiers: List[dict] = []
    for tier in tiers_raw:
        if not isinstance(tier, dict):
            continue
        min_value = _to_decimal(tier.get("min"))
        max_raw = tier.get("max")
        max_value = _to_decimal(max_raw) if max_raw not in (None, "") else None
        rate = _to_decimal(tier.get("rate"))
        tiers.append({"min": min_value, "max": max_value, "rate": rate})
    if not tiers:
        tiers = base.get("discountTiers") or []
    cbd = cfg.get("commissionByDepth") or {}
    return {
        "version": "v1",
        "activationNetMin": _to_decimal(cfg.get("activationNetMin", base.get("activationNetMin"))),
        "discountTiers": tiers,
        "commissionByDepth": {
            "1": _to_decimal(cbd.get("1", DEFAULT_COMMISSION_BY_DEPTH[1])),
            "2": _to_decimal(cbd.get("2", DEFAULT_COMMISSION_BY_DEPTH[2])),
            "3": _to_decimal(cbd.get("3", DEFAULT_COMMISSION_BY_DEPTH[3])),
        },
        "payoutDay": _to_decimal(cfg.get("payoutDay", base.get("payoutDay"))),
        "cutRule": str(cfg.get("cutRule") or base.get("cutRule") or "hard_cut_no_pass"),
    }

def _normalize_app_config(raw: Any) -> dict:
    merged = _merge_dict(_default_app_config(), raw if isinstance(raw, dict) else {})
    rewards = _normalize_rewards_config(merged.get("rewards"))
    orders_raw = merged.get("orders") if isinstance(merged.get("orders"), dict) else {}
    pos_raw = merged.get("pos") if isinstance(merged.get("pos"), dict) else {}
    stocks_raw = merged.get("stocks") if isinstance(merged.get("stocks"), dict) else {}
    payments_raw = merged.get("payments") if isinstance(merged.get("payments"), dict) else {}
    ml_raw = payments_raw.get("mercadoLibre") if isinstance(payments_raw.get("mercadoLibre"), dict) else {}
    warnings_raw = merged.get("adminWarnings") if isinstance(merged.get("adminWarnings"), dict) else {}
    order_status_map = pos_raw.get("orderStatusByDeliveryStatus") if isinstance(pos_raw.get("orderStatusByDeliveryStatus"), dict) else {}

    return {
        "version": str(merged.get("version") or "app-v1"),
        "rewards": rewards,
        "orders": {
            "requireStockOnShipped": bool(orders_raw.get("requireStockOnShipped", True)),
            "requireDispatchLinesOnShipped": bool(orders_raw.get("requireDispatchLinesOnShipped", True)),
        },
        "pos": {
            "defaultCustomerName": str(pos_raw.get("defaultCustomerName") or "Venta mostrador"),
            "defaultPaymentStatus": str(pos_raw.get("defaultPaymentStatus") or "paid_branch"),
            "defaultDeliveryStatus": str(pos_raw.get("defaultDeliveryStatus") or "delivered_branch"),
            "orderStatusByDeliveryStatus": {
                "delivered_branch": str(order_status_map.get("delivered_branch") or "delivered"),
                "paid_branch": str(order_status_map.get("paid_branch") or "paid"),
            },
        },
        "stocks": {
            "requireLinkedUserForTransferReceive": bool(stocks_raw.get("requireLinkedUserForTransferReceive", True)),
        },
        "payments": {
            "mercadoLibre": {
                "enabled": bool(ml_raw.get("enabled", False)),
                "accessToken": str(ml_raw.get("accessToken") or ""),
                "checkoutPreferencesUrl": str(ml_raw.get("checkoutPreferencesUrl") or "https://api.mercadopago.com/checkout/preferences"),
                "paymentInfoUrlTemplate": str(ml_raw.get("paymentInfoUrlTemplate") or "https://api.mercadopago.com/v1/payments/{payment_id}"),
                "notificationUrl": str(ml_raw.get("notificationUrl") or ""),
                "successUrl": str(ml_raw.get("successUrl") or ""),
                "failureUrl": str(ml_raw.get("failureUrl") or ""),
                "pendingUrl": str(ml_raw.get("pendingUrl") or ""),
                "currencyId": str(ml_raw.get("currencyId") or "MXN"),
                "webhookSecret": str(ml_raw.get("webhookSecret") or ""),
            },
        },
        "adminWarnings": {
            "showCommissions": bool(warnings_raw.get("showCommissions", True)),
            "showShipping": bool(warnings_raw.get("showShipping", True)),
            "showPendingPayments": bool(warnings_raw.get("showPendingPayments", True)),
            "showPendingTransfers": bool(warnings_raw.get("showPendingTransfers", True)),
            "showPosSalesToday": bool(warnings_raw.get("showPosSalesToday", True)),
        },
    }

@functools.lru_cache(maxsize=1)
def _load_app_config_cached() -> dict:
    cfg = _get_by_id("CONFIG", _app_config_entity_id())
    if cfg and isinstance(cfg, dict):
        return _normalize_app_config(cfg.get("config"))
    # Backward-compatible bootstrap from legacy rewards config.
    legacy_rewards_item = _get_by_id("CONFIG", _legacy_rewards_config_entity_id())
    if legacy_rewards_item and isinstance(legacy_rewards_item.get("config"), dict):
        base = _default_app_config()
        base["rewards"] = legacy_rewards_item.get("config") or _default_rewards_config()
        return _normalize_app_config(base)
    return _normalize_app_config(_default_app_config())

def _load_app_config() -> dict:
    cfg = _load_app_config_cached()
    if not _get_by_id("CONFIG", _app_config_entity_id()):
        now = _now_iso()
        item = {
            "entityType": "config",
            "name": "app",
            "configId": _app_config_entity_id(),
            "config": cfg,
            "createdAt": now,
            "updatedAt": now,
        }
        _put_entity("CONFIG", _app_config_entity_id(), item, created_at_iso=now)
    return cfg

def _save_legacy_rewards_config(cfg: dict) -> None:
    now = _now_iso()
    existing = _get_by_id("CONFIG", _legacy_rewards_config_entity_id())
    normalized_rewards = _normalize_rewards_config(cfg)
    if not existing:
        item = {
            "entityType": "config",
            "name": "rewards",
            "configId": _legacy_rewards_config_entity_id(),
            "config": normalized_rewards,
            "createdAt": now,
            "updatedAt": now,
        }
        _put_entity("CONFIG", _legacy_rewards_config_entity_id(), item, created_at_iso=now)
        return

    _update_by_id(
        "CONFIG",
        _legacy_rewards_config_entity_id(),
        "SET #c = :c, updatedAt = :u",
        {":c": normalized_rewards, ":u": now},
        ean={"#c": "config"},
    )

def _save_app_config(cfg: dict) -> dict:
    now = _now_iso()
    normalized = _normalize_app_config(cfg)
    existing = _get_by_id("CONFIG", _app_config_entity_id())
    if not existing:
        item = {
            "entityType": "config",
            "name": "app",
            "configId": _app_config_entity_id(),
            "config": normalized,
            "createdAt": now,
            "updatedAt": now,
        }
        _put_entity("CONFIG", _app_config_entity_id(), item, created_at_iso=now)
    else:
        _update_by_id(
            "CONFIG",
            _app_config_entity_id(),
            "SET #c = :c, updatedAt = :u",
            {":c": normalized, ":u": now},
            ean={"#c": "config"},
        )
    _save_legacy_rewards_config(normalized.get("rewards") or _default_rewards_config())
    _load_app_config_cached.cache_clear()
    return normalized

def _load_rewards_config() -> dict:
    cfg = _load_app_config()
    rewards = cfg.get("rewards") if isinstance(cfg, dict) else None
    return _normalize_rewards_config(rewards)

def _save_rewards_config(cfg: dict) -> dict:
    app_cfg = _load_app_config()
    app_cfg["rewards"] = _normalize_rewards_config(cfg)
    saved = _save_app_config(app_cfg)
    return saved.get("rewards") or _default_rewards_config()

def _calc_discount_rate(gross_subtotal: Decimal, tiers: List[dict]) -> Decimal:
    g = gross_subtotal
    for t in tiers:
        tmin = _to_decimal(t.get("min"))
        tmax = _to_decimal(t.get("max")) if t.get("max") is not None else None
        rate = _to_decimal(t.get("rate"))
        if g >= tmin and (tmax is None or g <= tmax):
            return rate
    return D_ZERO

def _effective_discount_rate_for_order(
    buyer_id: Any,
    buyer_type: str,
    gross_subtotal: Decimal,
    month_key: str,
    tiers: List[dict],
    current_order_rate: Decimal = D_ZERO,
) -> Decimal:
    if buyer_id is None or buyer_type not in {"associate", "registered"}:
        return D_ZERO

    buyer_key = _parse_int_or_str(buyer_id)
    if buyer_key is None or buyer_key == "":
        return D_ZERO
    customer = _get_by_id("CUSTOMER", int(buyer_key)) if isinstance(buyer_key, int) else _get_by_id("CUSTOMER", buyer_key)
    customer_rate = _to_decimal(customer.get("discountRate")) if customer else D_ZERO
    month_state = _get_month_state(buyer_key, month_key)
    month_net = _to_decimal(month_state.get("netVolume"))
    projected_net = month_net + _to_decimal(gross_subtotal)
    projected_rate = _calc_discount_rate(projected_net, tiers)
    return max(customer_rate, projected_rate, _to_decimal(current_order_rate))

def _discount_cutoff_payload(now_dt: Optional[datetime] = None) -> dict:
    now = now_dt or datetime.now(timezone.utc)
    end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc) if now.month == 12 else datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    diff = max(0, int((end - now).total_seconds()))
    days = diff // 86400
    hours = (diff % 86400) // 3600
    minutes = (diff % 3600) // 60
    return {
        "isWindow": diff <= (3 * 24 * 60 * 60),
        "secondsLeft": diff,
        "countdownLabel": f"{days}d {hours:02d}h {minutes:02d}m",
        "message": "Tu descuento solo aplicara hasta el corte de mes.",
    }

# ---------------------------------------------------------------------------
# Associate Monthly State
# ---------------------------------------------------------------------------
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
        "netVolume": D_ZERO,
        "isActive": False,
        "createdAt": now,
        "updatedAt": now,
    }

def _upsert_month_volume(associate_id: Any, month_key: str, net_delta: Decimal, activation_min: Decimal) -> Tuple[dict, bool]:
    mid = _associate_month_id(associate_id, month_key)
    existing = _get_by_id("ASSOCIATE_MONTH", mid)
    now = _now_iso()

    if not existing:
        net_volume = net_delta
        item = {
            "entityType": "associateMonth",
            "associateId": associate_id,
            "monthKey": month_key,
            "netVolume": net_volume,
            "isActive": bool(net_volume >= activation_min),
            "createdAt": now,
            "updatedAt": now,
        }
        created = _put_entity("ASSOCIATE_MONTH", mid, item, created_at_iso=now)
        return created, bool(created.get("isActive"))

    prev_active = bool(existing.get("isActive"))
    updated = _update_by_id(
        "ASSOCIATE_MONTH",
        mid,
        "SET netVolume = if_not_exists(netVolume, :z) + :d, updatedAt = :u",
        {":z": D_ZERO, ":d": net_delta, ":u": now},
    )
    net_volume = _to_decimal(updated.get("netVolume"))
    updated2 = _update_by_id(
        "ASSOCIATE_MONTH",
        mid,
        "SET isActive = :ia, updatedAt = :u",
        {":ia": bool(net_volume >= activation_min), ":u": now},
    )
    became_active = (not prev_active) and bool(updated2.get("isActive"))
    return updated2, became_active

def _is_active(associate_id: Any, month_key: str) -> bool:
    item = _get_month_state(associate_id, month_key)
    return bool(item.get("isActive"))

def _is_active_cached(associate_id: Any, month_key: str, cache: dict) -> bool:
    if associate_id in cache:
        return cache[associate_id]
    active = _is_active(associate_id, month_key)
    cache[associate_id] = active
    return active

# ---------------------------------------------------------------------------
# Customer Helpers
# ---------------------------------------------------------------------------
def _get_customer_profile(customer_id: Any) -> Optional[dict]:
    return _get_by_id("CUSTOMER", customer_id) if customer_id is not None else None

def _update_customer_commissions_cache(customer_id: Any, delta: Decimal) -> None:
    if customer_id is None:
        return
    try:
        _update_by_id(
            "CUSTOMER",
            customer_id,
            "SET commissions = if_not_exists(commissions, :z) + :d, updatedAt = :u",
            {":z": D_ZERO, ":d": delta, ":u": _now_iso()},
        )
    except Exception:
        pass

def _upline_chain(buyer_id: Any, max_levels: Optional[int] = 3, safety_cap: int = 50) -> List[Any]:
    chain: List[Any] = []
    current_id = buyer_id
    seen = set()
    hard_limit = safety_cap if max_levels is None else min(int(max_levels), safety_cap)

    for _ in range(hard_limit):
        if current_id in seen:
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
# Commission Ledger
# ---------------------------------------------------------------------------
def _commission_month_sk(beneficiary_id: Any, month_key: str) -> str:
    return f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"

def _get_commission_month_item(beneficiary_id: Any, month_key: str) -> Optional[dict]:
    if beneficiary_id is None or not month_key:
        return None
    resp = _table.get_item(Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)})
    return resp.get("Item")

def _commission_rate_for_depth(depth: int, cfg: dict) -> Decimal:
    depth_int = int(depth) if depth is not None else 0
    if depth_int <= 0:
        return D_ZERO

    raw = cfg.get("commissionByDepth") if isinstance(cfg, dict) else None
    if isinstance(raw, list):
        idx = depth_int - 1
        if 0 <= idx < len(raw):
            return _to_decimal(raw[idx])
    if isinstance(raw, dict):
        if depth_int in raw:
            return _to_decimal(raw.get(depth_int))
        key = str(depth_int)
        if key in raw:
            return _to_decimal(raw.get(key))

    return _to_decimal(DEFAULT_COMMISSION_BY_DEPTH.get(depth_int, D_ZERO))

def _recalc_commission_totals(ledger: List[dict]) -> Tuple[Decimal, Decimal, Decimal]:
    pending = D_ZERO
    confirmed = D_ZERO
    blocked = D_ZERO
    for r in ledger or []:
        amt = _to_decimal(r.get("amount"))
        status = (r.get("status") or "").strip().lower()
        if status == "confirmed":
            confirmed += amt
        elif status == "blocked" or r.get("blocked") is True:
            blocked += amt
        else:
            pending += amt
    return pending, confirmed, blocked

def _compute_block_status(
    source_buyer_id: Any,
    level: Any,
    month_key: str,
    active_cache: dict,
) -> Tuple[bool, Optional[Any]]:
    if source_buyer_id is None:
        return (False, None)
    try:
        lvl = int(level)
    except Exception:
        return (True, None)
    if lvl <= 0:
        return (False, None)

    chain = _upline_chain(source_buyer_id, max_levels=lvl)
    if len(chain) < lvl:
        return (True, None)

    for leader_id in chain[:lvl]:
        if not _is_active_cached(leader_id, month_key, active_cache):
            return (True, leader_id)
    return (False, None)

def _unlock_blocked_commissions_for_customer(customer_id: Any, month_key: str) -> None:
    if customer_id is None:
        return

    active_cache: Dict[Any, bool] = {}
    beneficiaries = [customer_id] + _upline_chain(customer_id, max_levels=None)
    for beneficiary_id in beneficiaries:
        item = _get_commission_month_item(beneficiary_id, month_key)
        if not item:
            continue
        ledger = item.get("ledger") or []
        if not isinstance(ledger, list) or not ledger:
            continue

        changed = False
        for row in ledger:
            status = (row.get("status") or "").strip().lower()
            if status != "blocked" and row.get("blocked") is not True:
                continue
            blocked_by = row.get("blockedBy")
            if blocked_by is not None and str(blocked_by) != str(customer_id):
                continue

            should_block, new_blocked_by = _compute_block_status(
                row.get("sourceBuyerId"),
                row.get("level"),
                month_key,
                active_cache,
            )
            if not should_block:
                next_status = row.get("blockedStatus") if row.get("blockedStatus") in {"confirmed", "pending"} else "pending"
                row["status"] = next_status
                row.pop("blockedBy", None)
                row.pop("blockedStatus", None)
                row["blocked"] = False
                changed = True
            else:
                if new_blocked_by is not None and str(new_blocked_by) != str(blocked_by):
                    row["blockedBy"] = new_blocked_by
                    row["blocked"] = True
                    row["status"] = "blocked"
                    changed = True

        if not changed:
            continue

        tp, tc, tb = _recalc_commission_totals(ledger)
        _table.update_item(
            Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
            UpdateExpression="SET ledger = :l, totalPending = :tp, totalConfirmed = :tc, totalBlocked = :tb, updatedAt = :u",
            ExpressionAttributeValues={
                ":l": ledger,
                ":tp": tp,
                ":tc": tc,
                ":tb": tb,
                ":u": _now_iso(),
            },
        )

def _add_commission_to_ledger(
    beneficiary_id: Any, month_key: str, order_id: str, source_buyer_id: Any,
    level: int, rate: Decimal, amount: Decimal, meta: Optional[dict] = None,
) -> dict:
    if beneficiary_id is None or not month_key or not order_id:
        return {}
    amount = _to_decimal(amount)
    if amount <= 0:
        return {}

    now = _now_iso()
    row = {
        "orderId": order_id,
        "sourceBuyerId": source_buyer_id,
        "level": int(level),
        "rate": _to_decimal(rate),
        "amount": amount,
        "status": "pending",
        "createdAt": now,
    }
    if source_buyer_id is None:
        row.pop("sourceBuyerId", None)
    if meta:
        row.update({k: v for k, v in meta.items() if v is not None})

    try:
        _table.update_item(
            Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
            UpdateExpression=(
                "SET ledger = list_append(if_not_exists(ledger, :empty), :rows), "
                "totalPending = if_not_exists(totalPending, :zero) + :amt, "
                "totalConfirmed = if_not_exists(totalConfirmed, :zero), "
                "#s = if_not_exists(#s, :in_progress), "
                "entityType = if_not_exists(entityType, :etype), "
                "beneficiaryId = if_not_exists(beneficiaryId, :bid), "
                "monthKey = if_not_exists(monthKey, :mk), "
                "createdAt = if_not_exists(createdAt, :u), "
                "updatedAt = :u"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":empty": [], ":rows": [row], ":zero": D_ZERO, ":amt": amount,
                ":in_progress": "IN_PROGRESS", ":etype": "commissionMonth",
                ":bid": beneficiary_id, ":mk": month_key, ":u": now,
            },
        )
    except Exception:
        return {}

    return {"beneficiaryId": beneficiary_id, "monthKey": month_key, **row}

def _confirm_order_commissions(order_item: dict) -> List[dict]:
    """
    NUEVO COMPORTAMIENTO (delivered):
    - NO agrega filas nuevas.
    - Solo cambia status 'pending' -> 'confirmed' de filas existentes del ledger para esa orderId.
    - Recalcula totalPending/totalConfirmed a partir del ledger actualizado.
    """

    print("_confirm_order_commissions called")
    order_id = order_item.get("orderId")
    if not order_id:
        return []

    buyer_id = order_item.get("customerId")
    month_key = order_item.get("monthKey") or _month_key()
    buyer_type = (order_item.get("buyerType") or "").lower()

    beneficiaries: List[Any] = []
    if buyer_id is not None:
        beneficiaries = _upline_chain(buyer_id, max_levels=MAX_COMMISSION_LEVELS)

    # Si es guest, tambiÃ©n incluye referrer (si existe)
    
    print("_confirm_order_commissions called - buyer_type:", buyer_type)
    if buyer_type == "guest":
        referrer_id = order_item.get("referrerAssociateId")
        if referrer_id:
            beneficiaries = [referrer_id] + beneficiaries

    actions: List[dict] = []

    for beneficiary_id in beneficiaries:
        print("_confirm_order_commissions processing beneficiary_id:", beneficiary_id)
        item = _get_commission_month_item(beneficiary_id, month_key)
        if not item:
            continue

        ledger = item.get("ledger") or []
        if not isinstance(ledger, list) or not ledger:
            continue

        changed = False
        confirmed_count = 0
        confirmed_amount = D_ZERO

        for r in ledger:
            if r.get("orderId") != order_id:
                continue
            st = (r.get("status") or "").strip().lower()
            if st == "pending":
                r["status"] = "confirmed"
                changed = True
                confirmed_count += 1
                confirmed_amount += _to_decimal(r.get("amount"))
            elif st == "blocked" or r.get("blocked") is True:
                if r.get("blockedStatus") != "confirmed":
                    r["blockedStatus"] = "confirmed"
                    changed = True

        if not changed:
            continue

        tp, tc, tb = _recalc_commission_totals(ledger)

        # Persistir SOLO ledger+totales (no agrega nada)
        _table.update_item(
            Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
            UpdateExpression="SET ledger = :l, totalPending = :tp, totalConfirmed = :tc, totalBlocked = :tb, updatedAt = :u",
            ExpressionAttributeValues={
                ":l": ledger,
                ":tp": tp,
                ":tc": tc,
                ":tb": tb,
                ":u": _now_iso(),
            },
        )

        actions.append({
            "beneficiaryId": beneficiary_id,
            "orderId": order_id,
            "confirmedCount": confirmed_count,
            "amount": confirmed_amount,
        })

    return actions


def _void_commissions_for_order(order_id: str, reason: str) -> List[dict]:
    order_item = _find_order(order_id)
    if not order_item:
        return []

    month_key = order_item.get("monthKey") or _month_key()
    buyer_id = order_item.get("customerId")
    
    beneficiaries = []
    if buyer_id is not None:
        beneficiaries = _upline_chain(buyer_id, max_levels=MAX_COMMISSION_LEVELS)
    if (order_item.get("buyerType") or "").lower() == "guest":
        referrer_id = order_item.get("referrerAssociateId")
        if referrer_id:
            beneficiaries = [referrer_id] + beneficiaries

    out: List[dict] = []
    for beneficiary_id in beneficiaries:
        item = _get_commission_month_item(beneficiary_id, month_key)
        if not item:
            continue
        ledger = item.get("ledger") or []
        
        pending_delta = D_ZERO
        confirmed_delta = D_ZERO
        blocked_delta = D_ZERO
        new_ledger = []
        removed_count = 0

        for row in ledger:
            if row.get("orderId") == order_id:
                amt = _to_decimal(row.get("amount"))
                status = (row.get("status") or "").lower()
                if status == "pending":
                    pending_delta += amt
                elif status == "confirmed":
                    confirmed_delta += amt
                elif status == "blocked" or row.get("blocked") is True:
                    blocked_delta += amt
                removed_count += 1
                continue
            new_ledger.append(row)

        if removed_count == 0:
            continue

        try:
            _table.update_item(
                Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
                UpdateExpression="SET ledger = :ledger, totalPending = if_not_exists(totalPending, :zero) - :pd, totalConfirmed = if_not_exists(totalConfirmed, :zero) - :cd, totalBlocked = if_not_exists(totalBlocked, :zero) - :bd, updatedAt = :u",
                ExpressionAttributeValues={
                    ":ledger": new_ledger, ":pd": pending_delta, ":cd": confirmed_delta, ":bd": blocked_delta, ":zero": D_ZERO, ":u": _now_iso(),
                },
            )
        except Exception:
            pass

        total_delta = pending_delta + confirmed_delta + blocked_delta
        if total_delta > 0:
            _update_customer_commissions_cache(beneficiary_id, -total_delta)

        out.append({
            "action": "void", "beneficiaryId": beneficiary_id, "orderId": order_id,
            "pendingRemoved": pending_delta, "confirmedRemoved": confirmed_delta, "reason": reason,
        })
    return out

# ---------------------------------------------------------------------------
# Order Logic
# ---------------------------------------------------------------------------
def _mercadolibre_config() -> dict:
    app_cfg = _load_app_config()
    payments = app_cfg.get("payments") if isinstance(app_cfg, dict) else {}
    ml = payments.get("mercadoLibre") if isinstance(payments, dict) else {}
    cfg = ml if isinstance(ml, dict) else {}
    env_overrides = {}
    if MERCADOLIBRE_ACCESS_TOKEN:
        env_overrides["accessToken"] = MERCADOLIBRE_ACCESS_TOKEN
    if MERCADOLIBRE_ENABLED_ENV is not None:
        env_overrides["enabled"] = bool(MERCADOLIBRE_ENABLED_ENV)
    if env_overrides:
        return {**cfg, **env_overrides}
    return cfg

def _http_json_request(
    method: str,
    url: str,
    headers: Optional[dict] = None,
    payload: Optional[dict] = None,
    timeout_seconds: int = 15,
) -> Tuple[int, dict]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body = None
    if payload is not None:
        body = json.dumps(payload, default=_json_default).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8") if resp else ""
            return int(getattr(resp, "status", 200) or 200), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if getattr(e, "fp", None) else ""
        parsed = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
        return int(e.code or 500), parsed
    except Exception as e:
        return 500, {"message": str(e)}

def _mercadolibre_order_items(order: dict) -> List[dict]:
    items = order.get("items") or []
    out: List[dict] = []
    for item in items:
        qty = max(1, int(item.get("quantity") or 1))
        price = float(_to_decimal(item.get("price")))
        out.append(
            {
                "title": str(item.get("name") or f"Producto {item.get('productId') or ''}").strip(),
                "quantity": qty,
                "unit_price": price,
                "currency_id": "MXN",
            }
        )
    return out

def _mercadolibre_status_to_order_status(status: str) -> Optional[str]:
    st = (status or "").strip().lower()
    if st in {"approved", "authorized"}:
        return "paid"
    if st in {"in_process", "pending"}:
        return "pending"
    if st in {"refunded", "charged_back"}:
        return "refunded"
    if st in {"cancelled", "rejected"}:
        return "canceled"
    return None

def _resolve_webhook_secret(query: Optional[dict], body: Optional[dict], headers: Optional[dict]) -> str:
    q = query or {}
    b = body if isinstance(body, dict) else {}
    h = headers or {}
    raw = (
        q.get("webhookSecret")
        or q.get("secret")
        or b.get("webhookSecret")
        or b.get("secret")
        or
        h.get("x-webhook-secret")
        or h.get("X-Webhook-Secret")
        or h.get("x-mercadolibre-signature")
        or h.get("X-MercadoLibre-Signature")
        or h.get("authorization")
        or h.get("Authorization")
        or ""
    )
    v = str(raw).strip()
    if not v:
        return ""
    if v.lower().startswith("bearer "):
        return v[7:].strip()
    return v

def _find_order_by_payment_reference(reference: str) -> Optional[dict]:
    ref = str(reference or "").strip()
    if not ref:
        return None
    direct = _find_order(ref)
    if direct:
        return direct

    orders_raw = _query_bucket("ORDER")
    for item in orders_raw:
        if str(item.get("paymentTransactionId") or "").strip() == ref:
            return item
        if str(item.get("paymentPreferenceId") or "").strip() == ref:
            return item
        if str(item.get("paymentExternalReference") or "").strip() == ref:
            return item
    return None

def _resolve_payment_id_from_webhook(query: dict, body: dict) -> Optional[str]:
    data = body.get("data") if isinstance(body, dict) else {}
    if isinstance(data, dict) and data.get("id"):
        return str(data.get("id"))
    if body.get("id"):
        return str(body.get("id"))
    if query.get("id"):
        return str(query.get("id"))
    topic = str(query.get("topic") or body.get("topic") or body.get("type") or "").lower()
    resource = str(query.get("resource") or body.get("resource") or "")
    if topic == "payment" and resource:
        rid = resource.rstrip("/").split("/")[-1]
        return rid or None
    return None

def _create_mercadolibre_checkout(order_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    print(f"[checkout][start] order_id={order_id}")
    order_item = _find_order(order_id)
    if not order_item:
        print(f"[checkout][error] order_not_found order_id={order_id}")
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    ml_cfg = _mercadolibre_config()
    enabled = bool(ml_cfg.get("enabled"))
    token = str(ml_cfg.get("accessToken") or "").strip()
    endpoint = str(ml_cfg.get("checkoutPreferencesUrl") or "").strip()
    print(
        f"[checkout][config] enabled={enabled} endpoint={endpoint} "
        f"token_present={bool(token)}"
    )
    if not enabled or not token or not endpoint:
        print(
            f"[checkout][error] bad_config enabled={enabled} "
            f"token_present={bool(token)} endpoint_present={bool(endpoint)}"
        )
        return _json_response(200, {"message": "Mercado Libre no configurado", "Error": "BadRequest"})

    currency_id = str((payload.get("currencyId") or ml_cfg.get("currencyId") or "MXN")).strip() or "MXN"
    items = _mercadolibre_order_items(order_item)
    print(f"[checkout][items] count={len(items)} currency={currency_id}")
    for item in items:
        item["currency_id"] = currency_id
    if not items:
        print(f"[checkout][error] empty_items order_id={order_id}")
        return _json_response(200, {"message": "Pedido sin productos", "Error": "BadRequest"})

    success_url = str(payload.get("successUrl") or ml_cfg.get("successUrl") or "").strip()
    failure_url = str(payload.get("failureUrl") or ml_cfg.get("failureUrl") or "").strip()
    pending_url = str(payload.get("pendingUrl") or ml_cfg.get("pendingUrl") or "").strip()
    notification_url = str(payload.get("notificationUrl") or ml_cfg.get("notificationUrl") or "").strip()
    webhook_secret = str(ml_cfg.get("webhookSecret") or "").strip()
    if notification_url and webhook_secret:
        sep = "&" if "?" in notification_url else "?"
        if "webhookSecret=" not in notification_url:
            notification_url = f"{notification_url}{sep}webhookSecret={urllib.parse.quote(webhook_secret, safe='')}"
    print(
        f"[checkout][urls] success={bool(success_url)} failure={bool(failure_url)} "
        f"pending={bool(pending_url)} notification={bool(notification_url)}"
    )

    checkout_payload = {
        "external_reference": str(order_item.get("orderId")),
        "items": items,
        "metadata": {
            "orderId": str(order_item.get("orderId")),
            "customerId": str(order_item.get("customerId") or ""),
        },
    }
    if success_url or failure_url or pending_url:
        checkout_payload["back_urls"] = {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        }
        checkout_payload["auto_return"] = "approved"
    if notification_url:
        checkout_payload["notification_url"] = notification_url

    print(
        f"[checkout][request] endpoint={endpoint} external_reference={checkout_payload.get('external_reference')} "
        f"items={len(checkout_payload.get('items') or [])}"
    )
    status_code, response = _http_json_request(
        "POST",
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
        payload=checkout_payload,
    )
    print(
        f"[checkout][response] status_code={status_code} "
        f"response_keys={list(response.keys()) if isinstance(response, dict) else 'non_dict'}"
    )
    if status_code >= 400:
        print(f"[checkout][error] provider_error status_code={status_code} response={response}")
        return _json_response(200, {"message": "No se pudo crear checkout de Mercado Libre", "Error": "BadGateway", "provider": response})

    pref_id = str(response.get("id") or "")
    init_point = str(response.get("init_point") or "")
    sandbox_init_point = str(response.get("sandbox_init_point") or "")
    if not pref_id or not (init_point or sandbox_init_point):
        print(
            f"[checkout][error] invalid_provider_response "
            f"pref_id_present={bool(pref_id)} init_present={bool(init_point)} sandbox_present={bool(sandbox_init_point)}"
        )
        return _json_response(200, {"message": "Respuesta invalida de Mercado Libre", "Error": "BadGateway", "provider": response})

    print(f"[checkout][persist] order_id={order_id} preference_id={pref_id}")
    _update_by_id(
        "ORDER",
        order_id,
        "SET paymentProvider = :pp, paymentPreferenceId = :pid, paymentExternalReference = :er, paymentInitPoint = :ip, paymentSandboxInitPoint = :sip, updatedAt = :u",
        {
            ":pp": "mercadolibre",
            ":pid": pref_id,
            ":er": str(order_item.get("orderId")),
            ":ip": init_point,
            ":sip": sandbox_init_point,
            ":u": _now_iso(),
        },
    )
    print(f"[checkout][ok] order_id={order_id} preference_id={pref_id}")
    _audit_event("order.checkout.mercadolibre", headers, payload, {"orderId": order_id, "preferenceId": pref_id})
    return _json_response(
        200,
        {
            "orderId": str(order_item.get("orderId")),
            "checkout": {
                "provider": "mercadolibre",
                "preferenceId": pref_id,
                "initPoint": init_point,
                "sandboxInitPoint": sandbox_init_point,
                "externalReference": str(order_item.get("orderId")),
            },
        },
    )

def _mercadolibre_webhook(query: dict, payload: dict, headers: Optional[dict] = None) -> dict:
    print(
        f"[mp-webhook][start] query_keys={list((query or {}).keys())} "
        f"payload_keys={list((payload or {}).keys()) if isinstance(payload, dict) else 'non_dict'}"
    )
    ml_cfg = _mercadolibre_config()
    expected_secret = str(ml_cfg.get("webhookSecret") or "").strip()
    if expected_secret:
        incoming = _resolve_webhook_secret(query, payload, headers)
        print(f"[mp-webhook][auth] secret_required=True incoming_present={bool(incoming)}")
        if incoming != expected_secret:
            print("[mp-webhook][error] unauthorized_secret_mismatch")
            return _json_response(401, {"message": "Webhook no autorizado", "Error": "Unauthorized"})
    else:
        print("[mp-webhook][auth] secret_required=False")

    payment_id = _resolve_payment_id_from_webhook(query or {}, payload or {})
    print(f"[mp-webhook][payment-id] resolved={payment_id}")
    if not payment_id:
        print("[mp-webhook][ignored] payment_id_not_found")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "payment_id_not_found"})

    token = str(ml_cfg.get("accessToken") or "").strip()
    payment_info_template = str(ml_cfg.get("paymentInfoUrlTemplate") or "").strip()
    print(f"[mp-webhook][config] token_present={bool(token)} payment_info_template={payment_info_template}")
    if not token or not payment_info_template:
        print("[mp-webhook][ignored] mercadolibre_not_configured")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "mercadolibre_not_configured"})

    payment_url = payment_info_template.replace("{payment_id}", urllib.parse.quote(str(payment_id), safe=""))
    print(f"[mp-webhook][provider-request] payment_url={payment_url}")
    status_code, payment_data = _http_json_request(
        "GET",
        payment_url,
        headers={"Authorization": f"Bearer {token}"},
        payload=None,
    )
    print(
        f"[mp-webhook][provider-response] status_code={status_code} "
        f"keys={list(payment_data.keys()) if isinstance(payment_data, dict) else 'non_dict'}"
    )
    if status_code >= 400:
        print(f"[mp-webhook][ignored] payment_lookup_failed status_code={status_code} payment_id={payment_id}")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "payment_lookup_failed", "provider": payment_data})

    external_ref = str(payment_data.get("external_reference") or "")
    if not external_ref:
        metadata = payment_data.get("metadata") if isinstance(payment_data.get("metadata"), dict) else {}
        external_ref = str(metadata.get("orderId") or metadata.get("order_id") or "")
    print(f"[mp-webhook][external-ref] value={external_ref}")
    if not external_ref:
        print("[mp-webhook][ignored] external_reference_not_found")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "external_reference_not_found"})

    next_status = _mercadolibre_status_to_order_status(str(payment_data.get("status") or ""))
    print(f"[mp-webhook][status-map] provider={payment_data.get('status')} mapped={next_status}")
    if not next_status:
        print("[mp-webhook][ignored] status_not_mapped")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "status_not_mapped", "paymentStatus": payment_data.get("status")})

    order_item = _find_order(external_ref)
    if not order_item:
        print(f"[mp-webhook][ignored] order_not_found external_ref={external_ref}")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "order_not_found", "orderId": external_ref})

    prev = str(order_item.get("status") or "").lower()
    if next_status == "pending" and prev in {"paid", "shipped", "delivered", "canceled", "refunded"}:
        print(f"[mp-webhook][ignored] downgrade_blocked prev={prev} next={next_status} order_id={external_ref}")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "status_downgrade_blocked", "orderId": external_ref, "currentStatus": prev})
    if next_status == "paid" and prev in {"shipped", "delivered", "canceled", "refunded"}:
        print(f"[mp-webhook][ignored] downgrade_blocked prev={prev} next={next_status} order_id={external_ref}")
        return _json_response(200, {"ok": True, "ignored": True, "reason": "status_downgrade_blocked", "orderId": external_ref, "currentStatus": prev})

    print(f"[mp-webhook][order-update] order_id={order_item.get('orderId')} prev={prev} next={next_status}")
    result = _update_order_status(
        str(order_item.get("orderId")),
        {
            "status": next_status,
            "paymentStatus": f"mercadolibre_{str(payment_data.get('status') or '').lower()}",
            "paymentTransactionId": str(payment_data.get("id") or payment_id),
        },
        headers,
    )

    try:
        _update_by_id(
            "ORDER",
            str(order_item.get("orderId")),
            "SET paymentProvider = :pp, paymentTransactionId = :tx, paymentRawStatus = :prs, paymentExternalReference = :er, paymentWebhookAt = :wa, updatedAt = :u",
            {
                ":pp": "mercadolibre",
                ":tx": str(payment_data.get("id") or payment_id),
                ":prs": str(payment_data.get("status") or ""),
                ":er": external_ref,
                ":wa": _now_iso(),
                ":u": _now_iso(),
            },
        )
    except Exception:
        print(f"[mp-webhook][warn] could_not_persist_payment_fields order_id={order_item.get('orderId')}")
        pass

    print(f"[mp-webhook][ok] order_id={order_item.get('orderId')} payment_id={payment_id} mapped_status={next_status}")
    _audit_event("order.webhook.mercadolibre", headers, payload, {"orderId": str(order_item.get("orderId")), "paymentId": str(payment_id)})
    body_raw = result.get("body") if isinstance(result, dict) else None
    parsed_result = {}
    if isinstance(body_raw, str):
        try:
            parsed_result = json.loads(body_raw)
        except Exception:
            parsed_result = {}
    return _json_response(
        200,
        {
            "ok": True,
            "orderId": str(order_item.get("orderId")),
            "paymentId": str(payment_id),
            "providerStatus": str(payment_data.get("status") or ""),
            "mappedStatus": next_status,
            "result": parsed_result,
        },
    )

def _get_order_status(order_id: str) -> dict:
    item = _find_order_by_payment_reference(order_id)
    if not item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})
    st = str(item.get("status") or "pending").lower()
    cutoff = _discount_cutoff_payload()
    is_in_process = st == "pending"
    return _json_response(
        200,
        {
            "orderId": str(item.get("orderId")),
            "status": st,
            "paymentStatus": item.get("paymentStatus"),
            "deliveryStatus": item.get("deliveryStatus"),
            "paymentProvider": item.get("paymentProvider"),
            "paymentPreferenceId": item.get("paymentPreferenceId"),
            "paymentTransactionId": item.get("paymentTransactionId"),
            "paymentRawStatus": item.get("paymentRawStatus"),
            "paymentInitPoint": item.get("paymentInitPoint"),
            "paymentSandboxInitPoint": item.get("paymentSandboxInitPoint"),
            "paymentWebhookAt": item.get("paymentWebhookAt"),
            "markedByWebhook": bool(item.get("paymentWebhookAt")),
            "discountCutoffWindow": bool(is_in_process and cutoff.get("isWindow")),
            "discountCutoffCountdown": cutoff.get("countdownLabel") if is_in_process and cutoff.get("isWindow") else "",
            "discountCutoffMessage": cutoff.get("message") if is_in_process and cutoff.get("isWindow") else "",
            "updatedAt": item.get("updatedAt"),
        },
    )

def _create_order(payload: dict, headers: Optional[dict] = None) -> dict:
    customer_id = payload.get("customerId")
    customer_name = payload.get("customerName")
    items = payload.get("items", [])
    
    if not customer_name or not items:
        return _json_response(200, {"message": "customerName e items son obligatorios", "Error": "BadRequest"})
    
    address = (payload.get("address") or "").strip()
    postal_code = (payload.get("postalCode") or "").strip()
    state = (payload.get("state") or "").strip()

    buyer_type = (payload.get("buyerType") or ("guest" if not customer_id else "registered")).lower()
    order_id = _generate_order_id()
    now = _now_iso()
    month_key = _month_key()
    print(
        f"[order][create][start] order_id={order_id} customer_id={customer_id} "
        f"buyer_type={buyer_type} items_count={len(items)}"
    )

    normalized_items = []
    gross = D_ZERO

    for item in items:
        quantity = max(1, int(item.get("quantity") or 1))
        price = _to_decimal(item.get("price", 0))
        normalized_items.append({
            "productId": item.get("productId"),
            "name": item.get("name"),
            "price": price,
            "quantity": quantity
        })
        gross += price * quantity

    # Aplica descuento proyectado con acumulado mensual + compra actual.
    rewards_cfg = _load_rewards_config()
    tiers = rewards_cfg.get("discountTiers") or []
    discount_rate = _effective_discount_rate_for_order(
        buyer_id=_parse_int_or_str(customer_id),
        buyer_type=buyer_type,
        gross_subtotal=gross,
        month_key=month_key,
        tiers=tiers,
        current_order_rate=D_ZERO,
    )
    discount_amount = (gross * discount_rate).quantize(D_CENT)
    net_total = (gross - discount_amount).quantize(D_CENT)

    order_item = {
        "entityType": "order",
        "orderId": order_id,
        "customerId": customer_id,
        "customerName": customer_name,
        "buyerType": buyer_type,
        "referrerAssociateId": payload.get("referrerAssociateId"),
        "status": payload.get("status", "pending"),
        "items": normalized_items,
        "grossSubtotal": gross.quantize(D_CENT),
        "discountRate": discount_rate,
        "discountAmount": discount_amount,
        "netTotal": net_total,
        "total": net_total,
        "monthKey": month_key,
        "createdAt": now,
        "updatedAt": now,
    }
    
    # Optional fields
    for field in ["shippingType", "trackingNumber", "deliveryPlace", "deliveryDate", "recipientName", "phone", "address", "postalCode", "state"]:
        val = payload.get(field)
        if val:
            order_item[field] = val.strip() if isinstance(val, str) else val

    main = _put_entity("ORDER", order_id, order_item, created_at_iso=now)
    print(
        f"[order][create][ok] order_id={order_id} status={order_item.get('status')} "
        "mercadopago_flow=not_started"
    )
    
    # Update customer profile address if applicable
    cid_val = _parse_int_or_str(customer_id)
    if isinstance(cid_val, int) and cid_val > 0:
        updates = []
        eav = {":u": now}
        if address: updates.append("address = :a"); eav[":a"] = address
        if state: updates.append("state = :st"); eav[":st"] = state
        if postal_code: updates.append("postalCode = :pc"); eav[":pc"] = postal_code
        if payload.get("phone"): updates.append("phone = :ph"); eav[":ph"] = payload.get("phone")
        
        if updates:
            try:
                _update_by_id("CUSTOMER", cid_val, "SET " + ", ".join(updates) + ", updatedAt = :u", eav)
            except Exception:
                pass
                
    _audit_event("order.create", headers, payload, {"orderId": order_id, "customerId": customer_id})
    return _json_response(201, {"order": main})

def _find_order(order_id: str) -> Optional[dict]:
    return _get_by_id("ORDER", order_id)

def _apply_rewards_on_paid_order(order_item: dict) -> dict:
    """
    NUEVO COMPORTAMIENTO (paid):
    - Por cada beneficiario, crea o actualiza el item COMMISSION_MONTH (PK fijo, SK por beneficiary+month).
    - Inserta/reemplaza (idempotente) la fila del ledger que corresponde a esta orden (rowId determinÃ­stico).
    - Recalcula totalPending/totalConfirmed SIEMPRE a partir del ledger (no incrementos).
    - NO confirma pagos aquÃ­ (siguen como 'pending'); eso pasa en delivered.
    """

    def _row_id(order_id: str, level: int) -> str:
        return f"ORDER#{order_id}#L{int(level)}"

    def _recalc_totals(ledger: List[dict]) -> Tuple[Decimal, Decimal, Decimal]:
        return _recalc_commission_totals(ledger)

    def _upsert_ledger_row(existing_ledger: List[dict], new_row: dict) -> Tuple[List[dict], Decimal]:
        """
        Devuelve (nuevo_ledger, delta_amount_para_cache).
        Delta es (new_amt - old_amt) si reemplaza, o new_amt si agrega, o 0 si no cambia.
        """
        if not isinstance(existing_ledger, list):
            existing_ledger = []

        rid = new_row.get("rowId")
        if not rid:
            return existing_ledger, D_ZERO

        new_amt = _to_decimal(new_row.get("amount"))
        delta = D_ZERO

        for i, r in enumerate(existing_ledger):
            if r.get("rowId") == rid:
                old_amt = _to_decimal(r.get("amount"))
                # Reemplaza fila (idempotente)
                existing_ledger[i] = new_row
                delta = (new_amt - old_amt)
                return existing_ledger, delta

        # No existÃ­a, agrega
        existing_ledger.append(new_row)
        delta = new_amt
        return existing_ledger, delta

    cfg = _load_rewards_config()
    tiers = cfg.get("discountTiers") or []
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))

    order_id = order_item.get("orderId")
    buyer_id = order_item.get("customerId")
    buyer_type = (order_item.get("buyerType") or "registered").lower()
    referrer_id = order_item.get("referrerAssociateId")

    gross = _to_decimal(order_item.get("grossSubtotal"))
    if gross <= 0:
        gross = sum(
            [_to_decimal(it.get("price")) * _to_decimal(it.get("quantity") or 1) for it in (order_item.get("items") or [])],
            D_ZERO
        )

    month_key = order_item.get("monthKey") or _month_key()

    # Determina descuento aplicable y lo valida contra acumulado mensual + compra actual.
    discount_rate = _effective_discount_rate_for_order(
        buyer_id=buyer_id,
        buyer_type=buyer_type,
        gross_subtotal=gross,
        month_key=month_key,
        tiers=tiers,
        current_order_rate=_to_decimal(order_item.get("discountRate")),
    )

    discount_amount = (gross * discount_rate).quantize(D_CENT)
    net = (gross - discount_amount).quantize(D_CENT)

    # Persistir totales de la orden (igual que antes)
    _update_by_id(
        "ORDER", order_id,
        "SET grossSubtotal = :g, discountRate = :dr, discountAmount = :da, netTotal = :n, monthKey = :mk, updatedAt = :u",
        {":g": gross, ":dr": discount_rate, ":da": discount_amount, ":n": net, ":mk": month_key, ":u": _now_iso()},
    )

    # Si es guest + referrer: comisiÃ³n one-shot (solo referrer)
    if buyer_type == "guest" and referrer_id:
        rate = Decimal("0.10")
        amount = (net * rate).quantize(D_CENT)
        if amount <= 0:
            return {
                "grossSubtotal": gross, "discountRate": discount_rate, "discountAmount": discount_amount,
                "netTotal": net, "monthKey": month_key, "commissionsCreated": [], "mode": "guest_one_shot"
            }

        beneficiary_id = referrer_id
        now = _now_iso()

        # 1) Lee o crea el month item
        item = _get_commission_month_item(beneficiary_id, month_key)
        if not item:
            item = {
                "PK": "COMMISSION_MONTH",
                "SK": _commission_month_sk(beneficiary_id, month_key),
                "entityType": "commissionMonth",
                "beneficiaryId": beneficiary_id,
                "monthKey": month_key,
                "status": "IN_PROGRESS",
                "ledger": [],
                "totalPending": D_ZERO,
                "totalConfirmed": D_ZERO,
                "totalBlocked": D_ZERO,
                "createdAt": now,
                "updatedAt": now,
            }

        # 2) Upsert fila idempotente
        row = {
            "rowId": _row_id(order_id, 0),
            "orderId": order_id,
            "sourceBuyerId": buyer_id,
            "level": 0,
            "rate": _to_decimal(rate),
            "amount": _to_decimal(amount),
            "status": "pending",
            "createdAt": now,
            "buyerType": buyer_type,
            "referrerOneShot": True,
        }
        ledger, delta_for_cache = _upsert_ledger_row(item.get("ledger") or [], row)
        tp, tc, tb = _recalc_totals(ledger)

        # 3) Guardar el item mensual (reemplaza ledger + totales)
        _table.put_item(Item={
            "PK": "COMMISSION_MONTH",
            "SK": _commission_month_sk(beneficiary_id, month_key),
            "entityType": "commissionMonth",
            "beneficiaryId": beneficiary_id,
            "monthKey": month_key,
            "status": item.get("status") or "IN_PROGRESS",
            "ledger": ledger,
            "totalPending": tp,
            "totalConfirmed": tc,
            "totalBlocked": tb,
            "createdAt": item.get("createdAt") or now,
            "updatedAt": _now_iso(),
        })

        # Cache (opcional): ajusta solo por delta (idempotente)
        if delta_for_cache != 0:
            _update_customer_commissions_cache(beneficiary_id, delta_for_cache)

        return {
            "grossSubtotal": gross, "discountRate": discount_rate, "discountAmount": discount_amount,
            "netTotal": net, "monthKey": month_key,
            "commissionsCreated": [{
                "beneficiaryId": beneficiary_id, "monthKey": month_key,
                "orderId": order_id, "level": 0, "rate": rate, "amount": amount, "status": "pending"
            }],
            "mode": "guest_one_shot",
        }

    # Compras de usuario registrado/asociado: actualiza estado mensual + beneficios + stats (igual que antes)
    if buyer_id is not None and buyer_type in {"associate", "registered"}:
        _, became_active = _upsert_month_volume(buyer_id, month_key, net, activation_min)
        _sync_buyer_benefits(buyer_id, month_key, cfg)
        _update_customer_product_stats(buyer_id, order_item)
        if became_active:
            _unlock_blocked_commissions_for_customer(buyer_id, month_key)

    # Multinivel: beneficiarios = upline
    chain = _upline_chain(buyer_id, max_levels=MAX_COMMISSION_LEVELS)
    trail = []
    blocked_by = None
    active_cache: Dict[Any, bool] = {}

    for idx, beneficiary_id in enumerate(chain):
        level = idx + 1
        print(f"Processing commission for beneficiary_id: {beneficiary_id} at level {level}")
        if blocked_by is None and not _is_active_cached(beneficiary_id, month_key, active_cache):
            blocked_by = beneficiary_id
        rate = _commission_rate_for_depth(level, cfg)
        amount = (net * rate).quantize(D_CENT) if rate > 0 else D_ZERO
        if amount <= 0:
            continue
        print(f"Calculated commission for beneficiary_id: {beneficiary_id} at level {level} is amount: {amount} with rate: {rate}")
        now = _now_iso()

        # 1) Lee o crea COMMISSION_MONTH
        item = _get_commission_month_item(beneficiary_id, month_key)
        print(f"Fetched commission month item for beneficiary_id: {beneficiary_id}, month_key: {month_key}: {item}")
        if not item:
            item = {
                "PK": "COMMISSION_MONTH",
                "SK": _commission_month_sk(beneficiary_id, month_key),
                "entityType": "commissionMonth",
                "beneficiaryId": beneficiary_id,
                "monthKey": month_key,
                "status": "IN_PROGRESS",
                "ledger": [],
                "totalPending": D_ZERO,
                "totalConfirmed": D_ZERO,
                "totalBlocked": D_ZERO,
                "createdAt": now,
                "updatedAt": now,
            }
            print(f"Created new commission month item for beneficiary_id: {beneficiary_id}, month_key: {month_key}")

        is_blocked = blocked_by is not None
        row_status = "blocked" if is_blocked else "pending"
        # 2) Upsert fila idempotente para esta orden+level
        row = {
            "rowId": _row_id(order_id, level),
            "orderId": order_id,
            "sourceBuyerId": buyer_id,
            "level": int(level),
            "rate": _to_decimal(rate),
            "amount": _to_decimal(amount),
            "status": row_status,
            "createdAt": now,
            "buyerType": buyer_type,
        }
        if is_blocked:
            row["blocked"] = True
            row["blockedBy"] = blocked_by
            row["blockedStatus"] = "pending"
        print(f"Upserting ledger row for beneficiary_id: {beneficiary_id}, order_id: {order_id}, level: {level}")
        ledger, delta_for_cache = _upsert_ledger_row(item.get("ledger") or [], row)
        print(f"Updated ledger for beneficiary_id: {beneficiary_id}, new ledger length: {len(ledger)}")
        tp, tc, tb = _recalc_totals(ledger)

        # 3) Persistir (ledger + totales recalculados)
        _table.put_item(Item={
            "PK": "COMMISSION_MONTH",
            "SK": _commission_month_sk(beneficiary_id, month_key),
            "entityType": "commissionMonth",
            "beneficiaryId": beneficiary_id,
            "monthKey": month_key,
            "status": item.get("status") or "IN_PROGRESS",
            "ledger": ledger,
            "totalPending": tp,
            "totalConfirmed": tc,
            "totalBlocked": tb,
            "createdAt": item.get("createdAt") or now,
            "updatedAt": _now_iso(),
        })
        print(f"Persisted commission month item for beneficiary_id: {beneficiary_id}, month_key: {month_key}")
        # Cache (opcional): ajusta solo por delta (idempotente)
        if delta_for_cache != 0:
            _update_customer_commissions_cache(beneficiary_id, delta_for_cache)

        trail.append({
            "beneficiaryId": beneficiary_id,
            "monthKey": month_key,
            "orderId": order_id,
            "level": int(level),
            "rate": rate,
            "amount": amount,
            "status": row_status,
            "blocked": is_blocked,
            "blockedBy": blocked_by,
        })

    return {
        "grossSubtotal": gross,
        "discountRate": discount_rate,
        "discountAmount": discount_amount,
        "netTotal": net,
        "monthKey": month_key,
        "uplineChain": chain,
        "cut": bool(blocked_by),
        "commissionsCreated": trail,
        "commissionsPaid": [],  # ya no "pagas" aquÃ­, solo generas ledger en pending
        "mode": "multilevel",
    }


def _update_order_status(order_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    status = (payload.get("status") or "").lower()
    valid_statuses = {"pending", "paid", "delivered", "canceled", "refunded", "shipped"}
    if status not in valid_statuses:
        return _json_response(200, {"message": "status invalido", "Error": "BadRequest"})
    app_cfg = _load_app_config()
    orders_cfg = app_cfg.get("orders") if isinstance(app_cfg, dict) else {}
    require_stock_on_shipped = bool((orders_cfg or {}).get("requireStockOnShipped", True))
    require_dispatch_lines_on_shipped = bool((orders_cfg or {}).get("requireDispatchLinesOnShipped", True))

    order_item = _find_order(order_id)
    if not order_item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    prev_status = (order_item.get("status") or "").lower()
    now = _now_iso()

    updates = ["#s = :s", "updatedAt = :u"]
    eav = {":s": status, ":u": now}
    ean = {"#s": "status"}

    field_map = {
        "shippingType": ":st",
        "trackingNumber": ":tn",
        "deliveryPlace": ":dp",
        "deliveryDate": ":dd",
        "stockId": ":sid",
        "paymentStatus": ":ps",
        "paymentTransactionId": ":ptx",
        "paymentRawStatus": ":prs",
        "deliveryStatus": ":ds",
        "attendantUserId": ":au",
    }
    for f, token in field_map.items():
        if payload.get(f) not in (None, ""):
            updates.append(f"{f} = {token}")
            eav[token] = payload.get(f)

    stock_movements: List[dict] = []
    dispatch_lines_raw = payload.get("dispatchLines")
    dispatch_lines = _normalize_lines(dispatch_lines_raw)
    stock_id = _stock_id(payload.get("stockId") or order_item.get("stockId"))
    if status == "shipped" and prev_status != "shipped":
        if require_stock_on_shipped and not stock_id:
            return _json_response(200, {"message": "Se requiere stock origen para enviar", "Error": "BadRequest"})
        if require_dispatch_lines_on_shipped and not dispatch_lines:
            return _json_response(200, {"message": "Se requieren lineas para descontar inventario", "Error": "BadRequest"})
    if status == "shipped" and prev_status != "shipped" and stock_id and dispatch_lines:
        deltas: Dict[str, int] = {}
        for line in dispatch_lines:
            pid_key = str(line.get("productId"))
            qty = int(line.get("qty") or 0)
            if qty <= 0:
                continue
            deltas[pid_key] = deltas.get(pid_key, 0) - qty
        _, stock_error = _apply_stock_delta(stock_id, deltas)
        if stock_error:
            return _json_response(200, {"message": stock_error, "Error": "BadRequest"})
        for line in dispatch_lines:
            stock_movements.append(
                _movement_payload(
                    _create_inventory_movement(
                        movement_type="exit_order",
                        stock_id=stock_id,
                        product_id=line.get("productId"),
                        qty=int(line.get("qty") or 0),
                        user_id=None,
                        reference_id=order_id,
                    )
                )
            )

    updated = _update_by_id("ORDER", order_id, "SET " + ", ".join(updates), eav, ean=ean)

    rewards_result = None
    if status == "paid" and prev_status != "paid":
        rewards_result = _apply_rewards_on_paid_order(updated)
    if status == "delivered" and prev_status != "delivered":
        try:
            _confirm_order_commissions(updated)
        except Exception:
            pass

    order_response = {
        "id": updated.get("orderId"),
        "createdAt": updated.get("createdAt"),
        "customer": updated.get("customerName"),
        "grossSubtotal": float(updated.get("grossSubtotal") or 0),
        "discountRate": float(updated.get("discountRate") or 0),
        "discountAmount": float(updated.get("discountAmount") or 0),
        "netTotal": float(updated.get("netTotal") or updated.get("total") or 0),
        "total": float(updated.get("netTotal") or updated.get("total") or 0),
        "status": updated.get("status"),
        # Map fields
        "shippingType": updated.get("shippingType"),
        "trackingNumber": updated.get("trackingNumber"),
        "deliveryPlace": updated.get("deliveryPlace"),
        "deliveryDate": updated.get("deliveryDate"),
        "recipientName": updated.get("recipientName"),
        "phone": updated.get("phone"),
        "address": updated.get("address"),
        "postalCode": updated.get("postalCode"),
        "state": updated.get("state"),
        "items": updated.get("items") or [],
        "stockId": updated.get("stockId"),
        "attendantUserId": updated.get("attendantUserId"),
        "paymentStatus": updated.get("paymentStatus"),
        "paymentTransactionId": updated.get("paymentTransactionId"),
        "paymentRawStatus": updated.get("paymentRawStatus"),
        "deliveryStatus": updated.get("deliveryStatus"),
    }
    if rewards_result is not None:
        _audit_event("order.status.update", headers, payload, {"orderId": order_id, "status": status})
        return _json_response(200, {"order": order_response, "rewards": rewards_result, "movements": stock_movements})
    _audit_event("order.status.update", headers, payload, {"orderId": order_id, "status": status})
    return _json_response(200, {"order": order_response, "movements": stock_movements})

def _refund_order(order_id: str, payload: dict) -> dict:
    reason = payload.get("reason") or "refund"
    if not _find_order(order_id):
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    _update_by_id("ORDER", order_id, "SET #s = :s, refundReason = :r, updatedAt = :u", {":s": "refunded", ":r": reason, ":u": _now_iso()}, ean={"#s": "status"})
    actions = _void_commissions_for_order(order_id, reason="refund")
    return _json_response(200, {"orderId": order_id, "status": "refunded", "commissionActions": actions})

def _cancel_order(order_id: str, payload: dict) -> dict:
    reason = payload.get("reason") or "cancel"
    if not _find_order(order_id):
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    _update_by_id("ORDER", order_id, "SET #s = :s, cancelReason = :r, updatedAt = :u", {":s": "canceled", ":r": reason, ":u": _now_iso()}, ean={"#s": "status"})
    actions = _void_commissions_for_order(order_id, reason="cancel")
    return _json_response(200, {"orderId": order_id, "status": "canceled", "commissionActions": actions})

# ---------------------------------------------------------------------------
# Product Logic
# ---------------------------------------------------------------------------
def _save_product(payload: dict, headers: Optional[dict] = None) -> dict:
    product_id = payload.get("productId") or payload.get("id")
    name = payload.get("name")
    price = payload.get("price")
    
    if not name or price is None:
        return _json_response(200, {"message": "name y price son obligatorios", "Error": "BadRequest"})

    now = _now_iso()
    
    if product_id is not None:
        if _get_by_id("PRODUCT", int(product_id)):
            updates = []
            eav = {":u": now}
            ean = {}
            if "name" in payload: updates.append("#n = :n"); eav[":n"] = name; ean["#n"] = "name"
            if "price" in payload: updates.append("price = :p"); eav[":p"] = _to_decimal(price)
            if "active" in payload: updates.append("active = :a"); eav[":a"] = bool(payload.get("active", True))
            if "sku" in payload: updates.append("sku = :sku"); eav[":sku"] = payload.get("sku")
            if "hook" in payload: updates.append("hook = :h"); eav[":h"] = payload.get("hook")
            if "description" in payload: updates.append("description = :d"); eav[":d"] = payload.get("description")
            if "copyFacebook" in payload: updates.append("copyFacebook = :cf"); eav[":cf"] = payload.get("copyFacebook")
            if "copyInstagram" in payload: updates.append("copyInstagram = :ci"); eav[":ci"] = payload.get("copyInstagram")
            if "copyWhatsapp" in payload: updates.append("copyWhatsapp = :cw"); eav[":cw"] = payload.get("copyWhatsapp")
            if "tags" in payload: updates.append("tags = :t"); eav[":t"] = payload.get("tags")
            if "images" in payload: updates.append("images = :im"); eav[":im"] = payload.get("images")
            
            updates.append("updatedAt = :u")
            updated = _update_by_id("PRODUCT", int(product_id), "SET " + ", ".join(updates), eav, ean or None)
            _audit_event("product.update", headers, payload, {"productId": int(product_id)})
            return _json_response(200, {"product": updated})

    pid = int(product_id) if product_id is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    item = {
        "entityType": "product", "productId": pid, "name": name,
        "price": _to_decimal(price), "active": bool(payload.get("active", True)),
        "sku": payload.get("sku"), "hook": payload.get("hook"),
        "description": payload.get("description"),
        "copyFacebook": payload.get("copyFacebook"),
        "copyInstagram": payload.get("copyInstagram"),
        "copyWhatsapp": payload.get("copyWhatsapp"),
        "tags": payload.get("tags"), "images": payload.get("images"),
        "createdAt": now, "updatedAt": now
    }
    # Clean None
    item = {k: v for k, v in item.items() if v is not None}
    
    main = _put_entity("PRODUCT", pid, item, created_at_iso=now)
    _audit_event("product.create", headers, payload, {"productId": pid})
    return _json_response(201, {"product": main})

def _campaign_payload(item: dict) -> dict:
    return {
        "id": item.get("campaignId"),
        "name": item.get("name") or "",
        "active": bool(item.get("active", True)),
        "hook": item.get("hook") or "",
        "description": item.get("description") or "",
        "story": item.get("story") or "",
        "feed": item.get("feed") or "",
        "banner": item.get("banner") or "",
        "heroImage": item.get("heroImage") or "",
        "heroBadge": item.get("heroBadge") or "",
        "heroTitle": item.get("heroTitle") or "",
        "heroAccent": item.get("heroAccent") or "",
        "heroTail": item.get("heroTail") or "",
        "heroDescription": item.get("heroDescription") or "",
        "ctaPrimaryText": item.get("ctaPrimaryText") or "",
        "ctaSecondaryText": item.get("ctaSecondaryText") or "",
        "benefits": item.get("benefits") or [],
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }

def _save_campaign(payload: dict, headers: Optional[dict] = None) -> dict:
    name = (payload.get("name") or "").strip()
    hook = (payload.get("hook") or "").strip()
    story = (payload.get("story") or "").strip()
    feed = (payload.get("feed") or "").strip()
    banner = (payload.get("banner") or "").strip()
    if not name or not hook or not story or not feed or not banner:
        return _json_response(200, {"message": "name, hook, story, feed y banner son obligatorios", "Error": "BadRequest"})

    campaign_id = (payload.get("id") or payload.get("campaignId") or "").strip()
    now = _now_iso()
    if campaign_id and _get_by_id("CAMPAIGN", campaign_id):
        updated = _update_by_id(
            "CAMPAIGN",
            campaign_id,
            "SET #n = :n, active = :a, hook = :h, description = :d, story = :s, feed = :f, banner = :b, heroImage = :hi, heroBadge = :hb, heroTitle = :ht, heroAccent = :ha, heroTail = :htl, heroDescription = :hd, ctaPrimaryText = :cp, ctaSecondaryText = :cs, benefits = :be, updatedAt = :u",
            {
                ":n": name,
                ":a": bool(payload.get("active", True)),
                ":h": hook,
                ":d": (payload.get("description") or "").strip(),
                ":s": story,
                ":f": feed,
                ":b": banner,
                ":hi": (payload.get("heroImage") or "").strip(),
                ":hb": (payload.get("heroBadge") or "").strip(),
                ":ht": (payload.get("heroTitle") or "").strip(),
                ":ha": (payload.get("heroAccent") or "").strip(),
                ":htl": (payload.get("heroTail") or "").strip(),
                ":hd": (payload.get("heroDescription") or "").strip(),
                ":cp": (payload.get("ctaPrimaryText") or "").strip(),
                ":cs": (payload.get("ctaSecondaryText") or "").strip(),
                ":be": payload.get("benefits") if isinstance(payload.get("benefits"), list) else [],
                ":u": now,
            },
            ean={"#n": "name"},
        )
        _audit_event("campaign.update", headers, payload, {"campaignId": campaign_id})
        return _json_response(200, {"campaign": _campaign_payload(updated)})

    campaign_id = campaign_id or f"CMP-{uuid.uuid4().hex[:10].upper()}"
    item = {
        "entityType": "campaign",
        "campaignId": campaign_id,
        "name": name,
        "active": bool(payload.get("active", True)),
        "hook": hook,
        "description": (payload.get("description") or "").strip(),
        "story": story,
        "feed": feed,
        "banner": banner,
        "heroImage": (payload.get("heroImage") or "").strip(),
        "heroBadge": (payload.get("heroBadge") or "").strip(),
        "heroTitle": (payload.get("heroTitle") or "").strip(),
        "heroAccent": (payload.get("heroAccent") or "").strip(),
        "heroTail": (payload.get("heroTail") or "").strip(),
        "heroDescription": (payload.get("heroDescription") or "").strip(),
        "ctaPrimaryText": (payload.get("ctaPrimaryText") or "").strip(),
        "ctaSecondaryText": (payload.get("ctaSecondaryText") or "").strip(),
        "benefits": payload.get("benefits") if isinstance(payload.get("benefits"), list) else [],
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("CAMPAIGN", campaign_id, item, created_at_iso=now)
    _audit_event("campaign.create", headers, payload, {"campaignId": campaign_id})
    return _json_response(201, {"campaign": _campaign_payload(main)})

def _get_product(product_id: Any) -> dict:
    item = _get_by_id("PRODUCT", int(product_id))
    return _json_response(200, {"product": item}) if item else _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def _save_asset_from_base64(name: str, content_base64: str, content_type: str) -> dict:
    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        raise ValueError("invalid_base64")

    asset_id = f"assets/{uuid.uuid4()}-{name}"
    _s3.put_object(Bucket=BUCKET_NAME, Key=asset_id, Body=raw, ContentType=content_type, ACL="public-read")
    now = _now_iso()

    item = {
        "entityType": "asset", "assetId": asset_id, "name": name,
        "contentType": content_type, "url": _public_s3_url(BUCKET_NAME, asset_id, AWS_REGION),
        "createdAt": now, "updatedAt": now
    }
    return _put_entity("ASSET", asset_id, item, created_at_iso=now)

def _save_receipt_from_base64(name: str, content_base64: str, content_type: str) -> dict:
    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        raise ValueError("invalid_base64")

    asset_id = f"comprobantes/{uuid.uuid4()}-{name}"
    _s3.put_object(Bucket=BUCKET_NAME, Key=asset_id, Body=raw, ContentType=content_type, ACL="public-read")
    now = _now_iso()

    item = {
        "entityType": "asset", "assetId": asset_id, "name": name,
        "contentType": content_type, "url": _public_s3_url(BUCKET_NAME, asset_id, AWS_REGION),
        "createdAt": now, "updatedAt": now
    }
    return _put_entity("ASSET", asset_id, item, created_at_iso=now)

def _create_asset(payload: dict) -> dict:
    if not payload.get("name") or not payload.get("contentBase64"):
        return _json_response(200, {"message": "name y contentBase64 son obligatorios", "Error": "BadRequest"})
    try:
        main = _save_asset_from_base64(payload["name"], payload["contentBase64"], payload.get("contentType") or "image/png")
    except ValueError:
        return _json_response(200, {"message": "contentBase64 invalido", "Error": "BadRequest"})
    return _json_response(201, {"asset": main})

def _get_asset(asset_id: str) -> dict:
    item = _get_by_id("ASSET", asset_id)
    return _json_response(200, {"asset": item}) if item else _json_response(200, {"message": "Asset no encontrado", "Error": "NoEncontrado"})

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def _create_customer(payload: dict, headers: Optional[dict] = None) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    if not name or not email:
        return _json_response(200, {"message": "name y email son obligatorios", "Error": "BadRequest"})

    customer_id = payload.get("customerId") or int(datetime.now(timezone.utc).timestamp() * 1000)
    leader_id = _resolve_leader_id(payload.get("leaderId"))
    now = _now_iso()

    item = {
        "entityType": "customer", "customerId": customer_id, "name": name, "email": email,
        "phone": payload.get("phone"), "address": payload.get("address"), "city": payload.get("city"),
        "leaderId": leader_id, "isAssociate": bool(payload.get("isAssociate", True)),
        "canAccessAdmin": bool(payload.get("canAccessAdmin", False)),
        "privileges": _normalize_privileges(payload.get("privileges")),
        "activeBuyer": False, "discountRate": D_ZERO, "discount": "0%", "commissions": D_ZERO,
        "createdAt": now, "updatedAt": now
    }
    if payload.get("level") is not None:
        item["level"] = payload.get("level")
    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    
    response = {"customer": {
        "id": customer_id, "name": main["name"], "email": main["email"],
        "leaderId": main["leaderId"], "level": main.get("level"), "isAssociate": main["isAssociate"],
        "canAccessAdmin": bool(main.get("canAccessAdmin")),
        "privileges": _normalize_privileges(main.get("privileges")),
        "discount": main["discount"], "activeBuyer": bool(main["activeBuyer"]),
        "discountRate": float(main.get("discountRate") or 0),
        "commissions": float(main.get("commissions") or 0),
    }}
    _audit_event("customer.create", headers, payload, {"customerId": customer_id})
    return _json_response(201, response)

def _create_account(payload: dict) -> dict:
    name, email = payload.get("name"), payload.get("email")
    password, confirm = payload.get("password"), payload.get("confirmPassword")
    
    if not name or not email or not password:
        return _json_response(200, {"message": "name, email y password son obligatorios", "Error": "BadRequest"})
    if password != confirm:
        return _json_response(200, {"message": "Las contraseÃ±as no coinciden", "Error": "BadRequest"})

    email_norm = _normalize_email(email)
    if not email_norm:
        return _json_response(200, {"message": "email invalido", "Error": "BadRequest"})
    if _get_auth_by_email(email_norm):
        return _json_response(200, {"message": "El correo ya esta registrado", "Error": "Conflict"})

    customer_id = payload.get("customerId") or int(datetime.now(timezone.utc).timestamp() * 1000)
    leader_token = payload.get("referralToken") or payload.get("leaderId")
    leader_id = _resolve_leader_id(_parse_int_or_str(leader_token))
    product_id = _parse_int_or_str(payload.get("productId") or payload.get("refProductId"))

    now = _now_iso()
    password_hash = _hash_password(str(password))
    item = {
        "entityType": "customer", "customerId": customer_id, "name": name, "email": email_norm,
        "phone": payload.get("phone"), "address": payload.get("address"), "city": payload.get("city"),
        "leaderId": leader_id, "isAssociate": bool(payload.get("isAssociate", True)),
        "canAccessAdmin": False,
        "privileges": _normalize_privileges(None),
        "activeBuyer": False, "discountRate": D_ZERO, "discount": "0%", "commissions": D_ZERO,
        "passwordHash": password_hash, "refProductId": product_id,
        "createdAt": now, "updatedAt": now
    }
    if payload.get("level") is not None:
        item["level"] = payload.get("level")
    
    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    _create_auth_record(email_norm, password_hash, customer_id, role="cliente")
    
    return _json_response(201, {"customer": {
        "id": customer_id, "name": main["name"], "email": main["email"],
        "leaderId": main["leaderId"], "level": main.get("level"), "isAssociate": main["isAssociate"],
        "canAccessAdmin": bool(main.get("canAccessAdmin")),
        "privileges": _normalize_privileges(main.get("privileges")),
        "discount": main["discount"], "activeBuyer": bool(main["activeBuyer"]),
        "discountRate": float(main.get("discountRate") or 0),
        "commissions": float(main.get("commissions") or 0),
    }})

def _get_customer(customer_id: str) -> dict:
    item = _get_by_id("CUSTOMER", int(customer_id))
    return _json_response(200, {"customer": item}) if item else _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

def _update_customer_privileges(customer_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    cid = int(customer_id)
    customer = _get_by_id("CUSTOMER", cid)
    if not customer:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    can_access_admin = bool(payload.get("canAccessAdmin", customer.get("canAccessAdmin", False)))
    privileges = _normalize_privileges(payload.get("privileges", customer.get("privileges")))
    updated = _update_by_id(
        "CUSTOMER",
        cid,
        "SET canAccessAdmin = :ca, privileges = :pr, updatedAt = :u",
        {":ca": can_access_admin, ":pr": privileges, ":u": _now_iso()},
    )
    auth = _get_auth_by_email(_normalize_email(customer.get("email")))
    if auth:
        next_role = "admin" if can_access_admin else "cliente"
        try:
            _update_by_id("AUTH", auth.get("authId"), "SET #r = :r, updatedAt = :u", {":r": next_role, ":u": _now_iso()}, ean={"#r": "role"})
        except Exception:
            pass

    response_customer = {
        "id": updated.get("customerId"),
        "name": updated.get("name"),
        "email": updated.get("email"),
        "leaderId": updated.get("leaderId"),
        "level": updated.get("level"),
        "discount": updated.get("discount"),
        "commissions": float(updated.get("commissions") or 0),
        "canAccessAdmin": bool(updated.get("canAccessAdmin")),
        "privileges": _normalize_privileges(updated.get("privileges")),
    }
    _audit_event("customer.privileges.update", headers, payload, {"customerId": cid})
    return _json_response(200, {"customer": response_customer})

def _get_network(customer_id: str, query: dict) -> dict:
    depth = int(query.get("depth") or MAX_NETWORK_DEPTH)
    depth = min(depth, MAX_NETWORK_DEPTH)
    customers_raw = _query_bucket("CUSTOMER") # Optimized fetch-all

    nodes = {}
    for c in customers_raw:
        cid = str(c.get("customerId"))
        nodes[cid] = {
            "id": cid, "name": c.get("name"),
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
        if d <= 0: return {**n, "children": []}
        return {**n, "children": [trim(ch, d - 1) for ch in n.get("children", [])]}

    return _json_response(200, {"network": trim(root, depth)})

def _get_order(order_id: str) -> dict:
    item = _get_by_id("ORDER", order_id)
    if not item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})
    return _json_response(200, {"order": {
        "id": item.get("orderId"), "createdAt": item.get("createdAt"), "customer": item.get("customerName"),
        "grossSubtotal": float(item.get("grossSubtotal") or 0),
        "discountRate": float(item.get("discountRate") or 0),
        "discountAmount": float(item.get("discountAmount") or 0),
        "netTotal": float(item.get("netTotal") or 0),
        "total": float(item.get("netTotal") or item.get("total") or 0), "status": item.get("status"),
        "shippingType": item.get("shippingType"), "trackingNumber": item.get("trackingNumber"),
        "deliveryPlace": item.get("deliveryPlace"), "deliveryDate": item.get("deliveryDate"),
        "recipientName": item.get("recipientName"), "phone": item.get("phone"),
        "address": item.get("address"), "postalCode": item.get("postalCode"), "state": item.get("state"),
        "items": item.get("items") or [],
        "stockId": item.get("stockId"),
        "attendantUserId": item.get("attendantUserId"),
        "paymentStatus": item.get("paymentStatus"),
        "paymentTransactionId": item.get("paymentTransactionId"),
        "paymentRawStatus": item.get("paymentRawStatus"),
        "paymentProvider": item.get("paymentProvider"),
        "paymentPreferenceId": item.get("paymentPreferenceId"),
        "paymentInitPoint": item.get("paymentInitPoint"),
        "paymentSandboxInitPoint": item.get("paymentSandboxInitPoint"),
        "deliveryStatus": item.get("deliveryStatus"),
    }})

def _list_orders_for_customer(customer_id: str) -> dict:
    # Optimized fetch
    items = _query_bucket("ORDER")
    rows = []
    cid_str = str(customer_id)
    for item in items:
        if str(item.get("customerId") or "") != cid_str:
            continue
        rows.append({
            "id": item.get("orderId"), "createdAt": item.get("createdAt"),
            "customer": item.get("customerName"),
            "total": float(item.get("netTotal") or item.get("total") or 0),
            "status": item.get("status"),
            "items": item.get("items") or [],
            "stockId": item.get("stockId"),
            "attendantUserId": item.get("attendantUserId"),
            "paymentStatus": item.get("paymentStatus"),
            "deliveryStatus": item.get("deliveryStatus"),
        })
    return _json_response(200, {"orders": rows})

# ---------------------------------------------------------------------------
# Stocks & POS
# ---------------------------------------------------------------------------
def _stock_id(value: Any) -> str:
    return str(value or "").strip()

def _normalize_inventory(raw: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        pid = str(k or "").strip()
        if not pid:
            continue
        try:
            qty = int(v or 0)
        except Exception:
            qty = 0
        out[pid] = max(0, qty)
    return out

def _normalize_user_ids(raw: Any) -> List[int]:
    if not isinstance(raw, list):
        return []
    out: List[int] = []
    seen = set()
    for value in raw:
        try:
            uid = int(value)
        except Exception:
            continue
        if uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
    return out

def _normalize_lines(raw: Any) -> List[dict]:
    if not isinstance(raw, list):
        return []
    grouped: Dict[str, int] = {}
    for line in raw:
        if not isinstance(line, dict):
            continue
        pid_raw = line.get("productId")
        if pid_raw is None or pid_raw == "":
            continue
        pid = str(pid_raw).strip()
        try:
            qty = int(line.get("qty") or line.get("quantity") or 0)
        except Exception:
            qty = 0
        if qty <= 0:
            continue
        grouped[pid] = grouped.get(pid, 0) + qty
    rows = []
    for pid, qty in grouped.items():
        rows.append({"productId": _parse_int_or_str(pid), "qty": qty})
    return rows

def _stock_payload(item: dict) -> dict:
    return {
        "id": item.get("stockId"),
        "name": item.get("name") or "",
        "location": item.get("location") or "",
        "linkedUserIds": _normalize_user_ids(item.get("linkedUserIds")),
        "inventory": _normalize_inventory(item.get("inventory")),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }

def _transfer_payload(item: dict) -> dict:
    return {
        "id": item.get("transferId"),
        "sourceStockId": item.get("sourceStockId"),
        "destinationStockId": item.get("destinationStockId"),
        "status": item.get("status") or "pending",
        "lines": _normalize_lines(item.get("lines")),
        "createdByUserId": item.get("createdByUserId"),
        "receivedByUserId": item.get("receivedByUserId"),
        "createdAt": item.get("createdAt"),
        "receivedAt": item.get("receivedAt"),
    }

def _movement_payload(item: dict) -> dict:
    return {
        "id": item.get("movementId"),
        "stockId": item.get("stockId"),
        "productId": item.get("productId"),
        "qty": int(item.get("qty") or 0),
        "type": item.get("movementType"),
        "reason": item.get("reason"),
        "referenceId": item.get("referenceId"),
        "userId": item.get("userId"),
        "createdAt": item.get("createdAt"),
    }

def _create_inventory_movement(
    movement_type: str,
    stock_id: str,
    product_id: Any,
    qty: int,
    user_id: Any = None,
    reason: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> dict:
    now = _now_iso()
    movement_id = f"MOV-{uuid.uuid4().hex[:12]}"
    item = {
        "entityType": "inventoryMovement",
        "movementId": movement_id,
        "movementType": movement_type,
        "stockId": stock_id,
        "productId": _parse_int_or_str(product_id),
        "qty": int(qty),
        "userId": _parse_int_or_str(user_id) if user_id not in (None, "") else None,
        "reason": reason or "",
        "referenceId": reference_id or "",
        "createdAt": now,
        "updatedAt": now,
    }
    return _put_entity("INVENTORY_MOVEMENT", movement_id, item, created_at_iso=now)

def _apply_stock_delta(stock_id: str, deltas: Dict[str, int]) -> Tuple[Optional[dict], Optional[str]]:
    stock = _get_by_id("STOCK", stock_id)
    if not stock:
        return None, "Stock no encontrado"
    inventory = _normalize_inventory(stock.get("inventory"))
    next_inventory = dict(inventory)

    for pid, delta in deltas.items():
        current = int(next_inventory.get(pid, 0))
        nxt = current + int(delta)
        if nxt < 0:
            return None, f"Stock insuficiente para producto {pid}"
        next_inventory[pid] = nxt

    updated = _update_by_id(
        "STOCK",
        stock_id,
        "SET inventory = :inv, updatedAt = :u",
        {":inv": next_inventory, ":u": _now_iso()},
    )
    return updated, None

def _list_stocks() -> dict:
    items = _query_bucket("STOCK")
    rows = [_stock_payload(item) for item in items]
    return _json_response(200, {"stocks": rows})

def _create_stock(payload: dict, headers: Optional[dict] = None) -> dict:
    name = (payload.get("name") or "").strip()
    location = (payload.get("location") or "").strip()
    if not name or not location:
        return _json_response(200, {"message": "name y location son obligatorios", "Error": "BadRequest"})

    stock_id = _stock_id(payload.get("stockId") or f"STK-{uuid.uuid4().hex[:8].upper()}")
    if _get_by_id("STOCK", stock_id):
        return _json_response(200, {"message": "stockId ya existe", "Error": "Conflict"})

    now = _now_iso()
    item = {
        "entityType": "stock",
        "stockId": stock_id,
        "name": name,
        "location": location,
        "linkedUserIds": _normalize_user_ids(payload.get("linkedUserIds")),
        "inventory": _normalize_inventory(payload.get("inventory")),
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("STOCK", stock_id, item, created_at_iso=now)
    _audit_event("stock.create", headers, payload, {"stockId": stock_id})
    return _json_response(201, {"stock": _stock_payload(main)})

def _update_stock(stock_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    stock_id = _stock_id(stock_id)
    if not stock_id:
        return _json_response(200, {"message": "stockId invalido", "Error": "BadRequest"})
    if not _get_by_id("STOCK", stock_id):
        return _json_response(200, {"message": "Stock no encontrado", "Error": "NoEncontrado"})

    updates = ["updatedAt = :u"]
    eav: dict = {":u": _now_iso()}
    ean: dict = {}

    if "name" in payload:
        updates.append("#n = :n")
        ean["#n"] = "name"
        eav[":n"] = (payload.get("name") or "").strip()
    if "location" in payload:
        updates.append("#l = :l")
        ean["#l"] = "location"
        eav[":l"] = (payload.get("location") or "").strip()
    if "linkedUserIds" in payload:
        updates.append("linkedUserIds = :uids")
        eav[":uids"] = _normalize_user_ids(payload.get("linkedUserIds"))
    if "inventory" in payload:
        updates.append("inventory = :inv")
        eav[":inv"] = _normalize_inventory(payload.get("inventory"))

    if len(updates) <= 1:
        return _json_response(200, {"message": "Sin cambios para actualizar", "Error": "BadRequest"})

    updated = _update_by_id("STOCK", stock_id, "SET " + ", ".join(updates), eav, ean=ean if ean else None)
    _audit_event("stock.update", headers, payload, {"stockId": stock_id})
    return _json_response(200, {"stock": _stock_payload(updated)})

def _register_stock_entry(stock_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    product_id = payload.get("productId")
    qty = int(payload.get("qty") or payload.get("quantity") or 0)
    if product_id in (None, "") or qty <= 0:
        return _json_response(200, {"message": "productId y qty (>0) son obligatorios", "Error": "BadRequest"})

    sid = _stock_id(stock_id)
    updated, error = _apply_stock_delta(sid, {str(product_id): qty})
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    movement = _create_inventory_movement(
        movement_type="entry",
        stock_id=sid,
        product_id=product_id,
        qty=qty,
        user_id=payload.get("userId") or payload.get("createdByUserId"),
        reason=(payload.get("reason") or payload.get("note") or "").strip(),
    )
    _audit_event("stock.entry.create", headers, payload, {"stockId": sid, "productId": product_id, "qty": qty})
    return _json_response(201, {"stock": _stock_payload(updated), "movement": _movement_payload(movement)})

def _register_stock_damage(stock_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    product_id = payload.get("productId")
    qty = int(payload.get("qty") or payload.get("quantity") or 0)
    reason = (payload.get("reason") or "").strip()
    if product_id in (None, "") or qty <= 0 or not reason:
        return _json_response(200, {"message": "productId, qty (>0) y reason son obligatorios", "Error": "BadRequest"})

    sid = _stock_id(stock_id)
    updated, error = _apply_stock_delta(sid, {str(product_id): -qty})
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    now = _now_iso()
    damage_id = f"DMG-{uuid.uuid4().hex[:10].upper()}"
    damage_item = {
        "entityType": "stockDamage",
        "damageId": damage_id,
        "stockId": sid,
        "productId": _parse_int_or_str(product_id),
        "qty": qty,
        "reason": reason,
        "reportedByUserId": _parse_int_or_str(payload.get("userId") or payload.get("reportedByUserId")),
        "createdAt": now,
        "updatedAt": now,
    }
    damage = _put_entity("STOCK_DAMAGE", damage_id, damage_item, created_at_iso=now)
    movement = _create_inventory_movement(
        movement_type="damaged",
        stock_id=sid,
        product_id=product_id,
        qty=qty,
        user_id=payload.get("userId") or payload.get("reportedByUserId"),
        reason=reason,
        reference_id=damage_id,
    )
    _audit_event("stock.damage.create", headers, payload, {"stockId": sid, "productId": product_id, "qty": qty})
    return _json_response(
        201,
        {
            "stock": _stock_payload(updated),
            "damage": {
                "id": damage.get("damageId"),
                "stockId": damage.get("stockId"),
                "productId": damage.get("productId"),
                "qty": damage.get("qty"),
                "reason": damage.get("reason"),
                "reportedByUserId": damage.get("reportedByUserId"),
                "createdAt": damage.get("createdAt"),
            },
            "movement": _movement_payload(movement),
        },
    )

def _create_stock_transfer(payload: dict, headers: Optional[dict] = None) -> dict:
    source_stock_id = _stock_id(payload.get("sourceStockId"))
    destination_stock_id = _stock_id(payload.get("destinationStockId"))
    lines = _normalize_lines(payload.get("lines"))
    created_by_user_id = _parse_int_or_str(payload.get("createdByUserId"))

    if not source_stock_id or not destination_stock_id or source_stock_id == destination_stock_id:
        return _json_response(200, {"message": "sourceStockId y destinationStockId validos son obligatorios", "Error": "BadRequest"})
    if not lines:
        return _json_response(200, {"message": "lines debe incluir al menos un producto", "Error": "BadRequest"})

    source = _get_by_id("STOCK", source_stock_id)
    destination = _get_by_id("STOCK", destination_stock_id)
    if not source or not destination:
        return _json_response(200, {"message": "Stock origen o destino no encontrado", "Error": "NoEncontrado"})

    source_inventory = _normalize_inventory(source.get("inventory"))
    deltas: Dict[str, int] = {}
    for line in lines:
        pid_key = str(line.get("productId"))
        qty = int(line.get("qty") or 0)
        if qty <= 0:
            continue
        if int(source_inventory.get(pid_key, 0)) < qty:
            return _json_response(200, {"message": f"Stock insuficiente para producto {pid_key}", "Error": "BadRequest"})
        deltas[pid_key] = deltas.get(pid_key, 0) - qty

    updated_source, error = _apply_stock_delta(source_stock_id, deltas)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    now = _now_iso()
    transfer_id = f"TRF-{uuid.uuid4().hex[:10].upper()}"
    transfer_item = {
        "entityType": "stockTransfer",
        "transferId": transfer_id,
        "sourceStockId": source_stock_id,
        "destinationStockId": destination_stock_id,
        "lines": lines,
        "status": "pending",
        "createdByUserId": created_by_user_id,
        "createdAt": now,
        "updatedAt": now,
    }
    transfer = _put_entity("STOCK_TRANSFER", transfer_id, transfer_item, created_at_iso=now)

    movements = []
    for line in lines:
        movements.append(
            _movement_payload(
                _create_inventory_movement(
                    movement_type="exit_transfer",
                    stock_id=source_stock_id,
                    product_id=line.get("productId"),
                    qty=int(line.get("qty") or 0),
                    user_id=created_by_user_id,
                    reference_id=transfer_id,
                )
            )
        )
    _audit_event("stock.transfer.create", headers, payload, {"transferId": transfer_id, "sourceStockId": source_stock_id, "destinationStockId": destination_stock_id})
    return _json_response(201, {"transfer": _transfer_payload(transfer), "sourceStock": _stock_payload(updated_source), "movements": movements})

def _receive_stock_transfer(transfer_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    app_cfg = _load_app_config()
    stocks_cfg = app_cfg.get("stocks") if isinstance(app_cfg, dict) else {}
    require_linked_user = bool((stocks_cfg or {}).get("requireLinkedUserForTransferReceive", True))
    transfer = _get_by_id("STOCK_TRANSFER", transfer_id)
    if not transfer:
        return _json_response(200, {"message": "Transferencia no encontrada", "Error": "NoEncontrado"})
    if (transfer.get("status") or "").lower() == "received":
        return _json_response(200, {"message": "La transferencia ya fue recibida", "Error": "BadRequest"})

    destination_stock_id = _stock_id(transfer.get("destinationStockId"))
    destination = _get_by_id("STOCK", destination_stock_id)
    if not destination:
        return _json_response(200, {"message": "Stock destino no encontrado", "Error": "NoEncontrado"})

    receiver = _parse_int_or_str(payload.get("receivedByUserId") or payload.get("userId"))
    linked = _normalize_user_ids(destination.get("linkedUserIds"))
    if require_linked_user and receiver not in (None, "") and linked and int(receiver) not in linked:
        return _json_response(200, {"message": "El usuario no esta vinculado al stock destino", "Error": "BadRequest"})

    lines = _normalize_lines(transfer.get("lines"))
    deltas = {str(line.get("productId")): int(line.get("qty") or 0) for line in lines}
    updated_destination, error = _apply_stock_delta(destination_stock_id, deltas)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    now = _now_iso()
    updated_transfer = _update_by_id(
        "STOCK_TRANSFER",
        transfer_id,
        "SET #s = :s, receivedAt = :ra, receivedByUserId = :rb, updatedAt = :u",
        {":s": "received", ":ra": now, ":rb": receiver, ":u": now},
        ean={"#s": "status"},
    )

    movements = []
    for line in lines:
        movements.append(
            _movement_payload(
                _create_inventory_movement(
                    movement_type="entry_transfer",
                    stock_id=destination_stock_id,
                    product_id=line.get("productId"),
                    qty=int(line.get("qty") or 0),
                    user_id=receiver,
                    reference_id=transfer_id,
                )
            )
        )
    _audit_event("stock.transfer.receive", headers, payload, {"transferId": transfer_id, "destinationStockId": destination_stock_id})
    return _json_response(200, {"transfer": _transfer_payload(updated_transfer), "destinationStock": _stock_payload(updated_destination), "movements": movements})

def _list_stock_transfers(query: dict) -> dict:
    stock_id = _stock_id(query.get("stockId"))
    status_filter = (query.get("status") or "").strip().lower()
    items = _query_bucket("STOCK_TRANSFER")
    rows = []
    for item in items:
        if stock_id and stock_id not in {_stock_id(item.get("sourceStockId")), _stock_id(item.get("destinationStockId"))}:
            continue
        status = (item.get("status") or "").strip().lower()
        if status_filter and status != status_filter:
            continue
        rows.append(_transfer_payload(item))
    return _json_response(200, {"transfers": rows})

def _list_inventory_movements(query: dict) -> dict:
    stock_id = _stock_id(query.get("stockId"))
    movement_type = (query.get("type") or "").strip().lower()
    items = _query_bucket("INVENTORY_MOVEMENT")
    rows = []
    for item in items:
        if stock_id and _stock_id(item.get("stockId")) != stock_id:
            continue
        current_type = (item.get("movementType") or "").strip().lower()
        if movement_type and current_type != movement_type:
            continue
        rows.append(_movement_payload(item))
    return _json_response(200, {"movements": rows})

def _pos_sale_payload(item: dict) -> dict:
    return {
        "id": item.get("saleId"),
        "orderId": item.get("orderId"),
        "stockId": item.get("stockId"),
        "attendantUserId": item.get("attendantUserId"),
        "customerName": item.get("customerName"),
        "paymentStatus": item.get("paymentStatus"),
        "deliveryStatus": item.get("deliveryStatus"),
        "total": float(_to_decimal(item.get("total"))),
        "lines": item.get("lines") or [],
        "createdAt": item.get("createdAt"),
    }

def _register_pos_sale(payload: dict, headers: Optional[dict] = None) -> dict:
    app_cfg = _load_app_config()
    pos_cfg = app_cfg.get("pos") if isinstance(app_cfg, dict) else {}
    stock_id = _stock_id(payload.get("stockId"))
    if not stock_id:
        return _json_response(200, {"message": "stockId es obligatorio", "Error": "BadRequest"})
    if not _get_by_id("STOCK", stock_id):
        return _json_response(200, {"message": "Stock no encontrado", "Error": "NoEncontrado"})

    raw_items = payload.get("items") or payload.get("lines") or []
    if not isinstance(raw_items, list) or not raw_items:
        return _json_response(200, {"message": "items es obligatorio", "Error": "BadRequest"})

    products = _query_bucket("PRODUCT")
    product_by_id = {str(item.get("productId")): item for item in products}

    deltas: Dict[str, int] = {}
    lines: List[dict] = []
    total = D_ZERO
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        pid_raw = raw.get("productId")
        if pid_raw in (None, ""):
            continue
        pid_key = str(pid_raw).strip()
        qty = int(raw.get("qty") or raw.get("quantity") or 0)
        if qty <= 0:
            continue

        product = product_by_id.get(pid_key) or {}
        price = _to_decimal(raw.get("price") if raw.get("price") is not None else product.get("price"))
        name = raw.get("name") or product.get("name") or f"Producto {pid_key}"
        line = {
            "productId": _parse_int_or_str(pid_key),
            "name": name,
            "price": price,
            "quantity": qty,
        }
        lines.append(line)
        deltas[pid_key] = deltas.get(pid_key, 0) - qty
        total += price * qty

    if not lines:
        return _json_response(200, {"message": "items no contiene lineas validas", "Error": "BadRequest"})

    updated_stock, error = _apply_stock_delta(stock_id, deltas)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    now = _now_iso()
    sale_id = _stock_id(payload.get("saleId") or f"SALE-{uuid.uuid4().hex[:10].upper()}")
    order_id = _stock_id(payload.get("orderId") or f"POS-{uuid.uuid4().hex[:10].upper()}")
    sale_item = {
        "entityType": "posSale",
        "saleId": sale_id,
        "orderId": order_id,
        "stockId": stock_id,
        "attendantUserId": _parse_int_or_str(payload.get("attendantUserId")),
        "customerName": (payload.get("customerName") or pos_cfg.get("defaultCustomerName") or "Venta mostrador").strip() or "Venta mostrador",
        "paymentStatus": payload.get("paymentStatus") or pos_cfg.get("defaultPaymentStatus") or "paid_branch",
        "deliveryStatus": payload.get("deliveryStatus") or pos_cfg.get("defaultDeliveryStatus") or "delivered_branch",
        "total": total.quantize(D_CENT),
        "lines": lines,
        "createdAt": now,
        "updatedAt": now,
    }
    sale = _put_entity("POS_SALE", sale_id, sale_item, created_at_iso=now)

    status_by_delivery = pos_cfg.get("orderStatusByDeliveryStatus") if isinstance(pos_cfg.get("orderStatusByDeliveryStatus"), dict) else {}
    order_status = str(status_by_delivery.get(sale_item.get("deliveryStatus")) or "")
    if order_status not in {"pending", "paid", "shipped", "delivered", "canceled", "refunded"}:
        order_status = "delivered" if sale_item.get("deliveryStatus") == "delivered_branch" else "paid"
    order_item = {
        "entityType": "order",
        "orderId": order_id,
        "customerId": None,
        "customerName": sale_item.get("customerName"),
        "buyerType": "guest",
        "status": order_status,
        "items": lines,
        "grossSubtotal": total.quantize(D_CENT),
        "discountRate": D_ZERO,
        "discountAmount": D_ZERO,
        "netTotal": total.quantize(D_CENT),
        "total": total.quantize(D_CENT),
        "monthKey": _month_key(),
        "shippingType": "personal",
        "deliveryPlace": f"Sucursal: {stock_id}",
        "stockId": stock_id,
        "attendantUserId": sale_item.get("attendantUserId"),
        "paymentStatus": sale_item.get("paymentStatus"),
        "deliveryStatus": sale_item.get("deliveryStatus"),
        "createdAt": now,
        "updatedAt": now,
    }
    _put_entity("ORDER", order_id, order_item, created_at_iso=now)

    movements = []
    for line in lines:
        movements.append(
            _movement_payload(
                _create_inventory_movement(
                    movement_type="pos_sale",
                    stock_id=stock_id,
                    product_id=line.get("productId"),
                    qty=int(line.get("quantity") or 0),
                    user_id=payload.get("attendantUserId"),
                    reference_id=order_id,
                )
            )
        )
    _audit_event("pos.sale.register", headers, payload, {"saleId": sale_id, "orderId": order_id, "stockId": stock_id})
    return _json_response(201, {"sale": _pos_sale_payload(sale), "order": order_item, "stock": _stock_payload(updated_stock), "movements": movements})

def _list_pos_sales(query: dict) -> dict:
    stock_id = _stock_id(query.get("stockId"))
    items = _query_bucket("POS_SALE")
    rows = []
    for item in items:
        if stock_id and _stock_id(item.get("stockId")) != stock_id:
            continue
        rows.append(_pos_sale_payload(item))
    return _json_response(200, {"sales": rows})

# ---------------------------------------------------------------------------
# Rewards API
# ---------------------------------------------------------------------------
def _get_rewards_config_handler() -> dict:
    return _json_response(200, {"config": _load_rewards_config()})

def _put_rewards_config(payload: dict, headers: Optional[dict] = None) -> dict:
    if not isinstance(payload, dict) or not payload:
        return _json_response(200, {"message": "config invalida", "Error": "BadRequest"})
    candidate = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    cfg = _normalize_rewards_config(candidate)
    saved = _save_rewards_config(cfg)
    _audit_event("config.rewards.update", headers, payload, {"scope": "rewards"})
    return _json_response(200, {"config": saved})

def _get_app_config_handler() -> dict:
    return _json_response(200, {"config": _load_app_config()})

def _put_app_config(payload: dict, headers: Optional[dict] = None) -> dict:
    if not isinstance(payload, dict) or not payload:
        return _json_response(200, {"message": "config invalida", "Error": "BadRequest"})
    current = _load_app_config()
    incoming = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    merged = _merge_dict(current, incoming)
    saved = _save_app_config(merged)
    _audit_event("config.app.update", headers, payload, {"scope": "app"})
    return _json_response(200, {"config": saved})

def _get_associate_month(associate_id: str, month_key: str) -> dict:
    item = _get_month_state(associate_id, month_key)
    return _json_response(200, {"month": {
        "associateId": associate_id, "monthKey": month_key,
        "netVolume": float(_to_decimal(item.get("netVolume"))),
        "isActive": bool(item.get("isActive")), "updatedAt": item.get("updatedAt"),
    }})

def _get_associate_commissions(associate_id: str, query: dict) -> dict:
    month_key = query.get("month") or _month_key()
    status = (query.get("status") or "").lower()
    limit = min(200, int(query.get("limit") or 100))

    commission_item = _get_commission_month_item(associate_id, month_key)
    ledger = commission_item.get("ledger") if isinstance(commission_item, dict) else []
    if not isinstance(ledger, list): ledger = []

    rows = []
    total = D_ZERO
    for row in ledger:
        if status and (row.get("status") or "").lower() != status:
            continue
        amt = _to_decimal(row.get("amount"))
        total += amt
        rows.append({
            "id": f"{month_key}#{row.get('orderId')}#L{row.get('level')}",
            "orderId": row.get("orderId"), "monthKey": month_key,
            "level": row.get("level"), "rate": _to_decimal(row.get("rate")),
            "amount": amt, "status": row.get("status"),
            "sourceBuyerId": row.get("sourceBuyerId"), "createdAt": row.get("createdAt"),
        })
        if len(rows) >= limit: break

    return _json_response(200, {"associateId": associate_id, "count": len(rows), "total": total, "commissions": rows})

def _request_commission_payout(payload: dict) -> dict:
    customer_id = payload.get("customerId") or payload.get("associateId")
    clabe = (payload.get("clabe") or payload.get("clabeInterbancaria") or "").strip()
    month_key = payload.get("monthKey") or payload.get("month") or _month_key()

    if not customer_id:
        return _json_response(200, {"message": "customerId es obligatorio", "Error": "BadRequest"})

    customer = _get_by_id("CUSTOMER", int(customer_id))
    if not customer:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    existing_clabe = (customer.get("clabeInterbancaria") or customer.get("clabe") or "").strip()
    if not clabe and not existing_clabe:
        return _json_response(200, {"message": "CLABE es obligatoria", "Error": "BadRequest"})
    if clabe and len(clabe) < 10:
        return _json_response(200, {"message": "CLABE invalida", "Error": "BadRequest"})

    summary = _commission_summary_for_beneficiary(int(customer_id), month_key)
    confirmed_total = _to_decimal(summary.get("totalConfirmed"))
    if confirmed_total <= 0:
        return _json_response(200, {"message": "No hay comisiones por cobrar", "Error": "BadRequest"})

    now = _now_iso()
    if clabe:
        try:
            _update_by_id(
                "CUSTOMER",
                int(customer_id),
                "SET clabe = :c, clabeInterbancaria = :c, updatedAt = :u",
                {":c": clabe, ":u": now},
            )
        except Exception:
            pass

    request_id = str(uuid.uuid4())
    clabe_final = clabe or existing_clabe
    request_item = {
        "entityType": "commissionRequest", "requestId": request_id, "customerId": int(customer_id),
        "monthKey": month_key, "amount": confirmed_total.quantize(D_CENT), "status": "requested",
        "clabeLast4": clabe_final[-4:], "createdAt": now, "updatedAt": now,
    }
    main = _put_entity("COMMISSION_REQUEST", request_id, request_item, created_at_iso=now)
    return _json_response(201, {"request": main, "summary": summary})

def _update_customer_clabe(payload: dict) -> dict:
    customer_id = payload.get("customerId")
    clabe = (payload.get("clabe") or payload.get("clabeInterbancaria") or "").strip()

    if not customer_id:
        return _json_response(200, {"message": "customerId es obligatorio", "Error": "BadRequest"})
    if not clabe:
        return _json_response(200, {"message": "CLABE es obligatoria", "Error": "BadRequest"})
    if len(clabe) != 18 or not clabe.isdigit():
        return _json_response(200, {"message": "CLABE invalida", "Error": "BadRequest"})

    customer = _get_by_id("CUSTOMER", int(customer_id))
    if not customer:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    now = _now_iso()
    _update_by_id(
        "CUSTOMER",
        int(customer_id),
        "SET clabe = :c, clabeInterbancaria = :c, updatedAt = :u",
        {":c": clabe, ":u": now},
    )
    return _json_response(200, {"ok": True, "clabeLast4": clabe[-4:]})

def _upload_commission_receipt(payload: dict) -> dict:
    customer_id = payload.get("customerId")
    month_key = payload.get("monthKey") or payload.get("month") or _month_key()
    name = payload.get("name")
    content_base64 = payload.get("contentBase64")
    
    if not customer_id or not name or not content_base64:
        return _json_response(200, {"message": "customerId, name y contentBase64 son obligatorios", "Error": "BadRequest"})

    try:
        asset = _save_asset_from_base64(name, content_base64, payload.get("contentType") or "image/png")
    except ValueError:
        return _json_response(200, {"message": "contentBase64 invalido", "Error": "BadRequest"})

    now = _now_iso()
    receipt_id = f"{customer_id}#{month_key}#{uuid.uuid4()}"
    receipt_item = {
        "entityType": "commissionReceipt", "receiptId": receipt_id, "customerId": int(customer_id),
        "monthKey": month_key, "assetId": asset.get("assetId"), "assetUrl": asset.get("url"),
        "status": "uploaded", "createdAt": now, "updatedAt": now,
    }
    main = _put_entity("COMMISSION_RECEIPT", receipt_id, receipt_item, created_at_iso=now)
    return _json_response(201, {"receipt": main, "asset": asset})

def _upload_admin_commission_receipt(payload: dict, headers: Optional[dict] = None) -> dict:
    customer_id = payload.get("customerId")
    month_key = payload.get("monthKey") or payload.get("month") or _prev_month_key()
    name = payload.get("name")
    content_base64 = payload.get("contentBase64")

    if not customer_id or not name or not content_base64:
        return _json_response(200, {"message": "customerId, name y contentBase64 son obligatorios", "Error": "BadRequest"})

    try:
        asset = _save_receipt_from_base64(name, content_base64, payload.get("contentType") or "application/pdf")
    except ValueError:
        return _json_response(200, {"message": "contentBase64 invalido", "Error": "BadRequest"})

    now = _now_iso()
    receipt_id = f"{customer_id}#{month_key}#{uuid.uuid4()}"
    receipt_item = {
        "entityType": "commissionReceipt", "receiptId": receipt_id, "customerId": int(customer_id),
        "monthKey": month_key, "assetId": asset.get("assetId"), "assetUrl": asset.get("url"),
        "status": "paid", "createdAt": now, "updatedAt": now,
    }
    main = _put_entity("COMMISSION_RECEIPT", receipt_id, receipt_item, created_at_iso=now)
    try:
        _table.update_item(
            Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(int(customer_id), month_key)},
            UpdateExpression="SET #s = :s, updatedAt = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "PAID", ":u": _now_iso()},
        )
    except Exception:
        pass
    _audit_event("commission.admin_receipt.upload", headers, payload, {"customerId": int(customer_id), "monthKey": month_key, "receiptId": receipt_id})
    return _json_response(201, {"receipt": main, "asset": asset})

# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------
def _build_admin_warnings(
    paid_count: int,
    pending_count: int,
    commissions_count: int,
    pending_transfers_count: int = 0,
    pos_sales_today_count: int = 0,
) -> list:
    app_cfg = _load_app_config()
    warning_cfg = app_cfg.get("adminWarnings") if isinstance(app_cfg.get("adminWarnings"), dict) else {}
    warnings = []
    if bool(warning_cfg.get("showCommissions", True)) and commissions_count:
        warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
    if bool(warning_cfg.get("showShipping", True)) and paid_count:
        warnings.append({"type": "shipping", "text": f"{paid_count} pedidos pagados sin envio", "severity": "medium"})
    if bool(warning_cfg.get("showPendingPayments", True)) and pending_count:
        warnings.append({"type": "payments", "text": f"{pending_count} pedidos pendientes de pago", "severity": "low"})
    if bool(warning_cfg.get("showPendingTransfers", True)) and pending_transfers_count:
        warnings.append({"type": "stocks", "text": f"{pending_transfers_count} transferencias pendientes por recibir", "severity": "medium"})
    if bool(warning_cfg.get("showPosSalesToday", True)) and pos_sales_today_count:
        warnings.append({"type": "pos", "text": f"{pos_sales_today_count} ventas POS registradas hoy", "severity": "low"})
    return warnings

def _commission_summary_for_beneficiary(beneficiary_id: Any, month_key: str) -> dict:
    if beneficiary_id is None:
        return {"monthKey": month_key, "totalPending": D_ZERO, "totalConfirmed": D_ZERO, "hasPending": False, "hasConfirmed": False}
    item = _get_commission_month_item(beneficiary_id, month_key)
    pending = _to_decimal(item.get("totalPending")) if item else D_ZERO
    confirmed = _to_decimal(item.get("totalConfirmed")) if item else D_ZERO
    return {"monthKey": month_key, "totalPending": pending, "totalConfirmed": confirmed, "hasPending": pending > 0, "hasConfirmed": confirmed > 0}

def _commissions_paid_summary(month_key: str, customers_raw: List[dict]) -> dict:
    if not month_key:
        return {"monthKey": "", "count": 0, "total": 0.0, "rows": []}
    
    # Optimized: Query bucket ledger directly
    resp = _table.query(KeyConditionExpression=Key("PK").eq("COMMISSION_MONTH"), FilterExpression=Attr("monthKey").eq(month_key))
    items = resp.get("Items", []) or []

    # Map customers for O(1) lookup
    customers_by_id = {str(c.get("customerId")): c for c in customers_raw}
    total = D_ZERO
    rows = []

    for item in items:
        beneficiary_id = item.get("beneficiaryId")
        customer = customers_by_id.get(str(beneficiary_id)) or {}
        ledger = item.get("ledger") or []
        
        for row in ledger:
            if (row.get("status") or "").lower() != "confirmed":
                continue
            amt = _to_decimal(row.get("amount"))
            total += amt
            rows.append({
                "beneficiaryId": beneficiary_id,
                "beneficiaryName": customer.get("name") or "",
                "orderId": row.get("orderId"),
                "amount": float(amt),
                "createdAt": row.get("createdAt"),
            })
            if len(rows) >= 1000: break
        if len(rows) >= 1000: break

    return {"monthKey": month_key, "count": len(rows), "total": float(total), "rows": rows}

def _get_admin_dashboard() -> dict:
    app_cfg = _load_app_config()
    # Optimized fetch all
    customers_raw = _query_bucket("CUSTOMER")
    orders_raw = _query_bucket("ORDER")
    products_raw = _query_bucket("PRODUCT")
    campaigns_raw = _query_bucket("CAMPAIGN")
    receipts_raw = _query_bucket("COMMISSION_RECEIPT")
    pom_item = _get_product_of_month_item()
    product_of_month_id = int(pom_item.get("productId")) if pom_item and pom_item.get("productId") is not None else None

    customers = []
    customers_by_level = {}
    commissions_count = 0
    commissions_total = 0.0
    prev_month_key = _prev_month_key()
    current_month_key = _month_key()

    receipt_by_customer_month: Dict[str, str] = {}
    for r in receipts_raw:
        cid = r.get("customerId")
        mk = r.get("monthKey")
        url = r.get("assetUrl")
        if cid is None or not mk or not url:
            continue
        key = f"{cid}#{mk}"
        if key not in receipt_by_customer_month:
            receipt_by_customer_month[key] = url

    for item in customers_raw:
        comm = float(item.get("commissions") or 0)
        cid = item.get("customerId")
        comm_item = _get_commission_month_item(cid, current_month_key) if cid is not None else None
        current_pending = float(_to_decimal(comm_item.get("totalPending")) if comm_item else D_ZERO)
        current_confirmed = float(_to_decimal(comm_item.get("totalConfirmed")) if comm_item else D_ZERO)

        prev_comm_item = _get_commission_month_item(cid, prev_month_key) if cid is not None else None
        prev_confirmed = float(_to_decimal(prev_comm_item.get("totalConfirmed")) if prev_comm_item else D_ZERO)

        receipt_key = f"{cid}#{prev_month_key}" if cid is not None else ""
        prev_receipt_url = receipt_by_customer_month.get(receipt_key, "")
        if prev_confirmed <= 0:
            prev_status = "no_moves"
        elif prev_receipt_url:
            prev_status = "paid"
        else:
            prev_status = "pending"

        clabe_interbancaria = (item.get("clabeInterbancaria") or item.get("clabe") or "").strip()
        customers.append({
            "id": item.get("customerId"), "name": item.get("name"), "email": item.get("email"),
            "leaderId": item.get("leaderId"), "level": item.get("level"), "discount": item.get("discount"),
            "canAccessAdmin": bool(item.get("canAccessAdmin")),
            "privileges": _normalize_privileges(item.get("privileges")),
            "commissions": comm,
            "commissionsPrevMonthKey": prev_month_key,
            "commissionsPrevMonth": prev_confirmed,
            "commissionsCurrentPending": current_pending,
            "commissionsCurrentConfirmed": current_confirmed,
            "commissionsPrevStatus": prev_status,
            "commissionsPrevReceiptUrl": prev_receipt_url,
            "clabeInterbancaria": clabe_interbancaria,
        })
        level = item.get("level") or "Sin nivel"
        customers_by_level[level] = customers_by_level.get(level, 0) + 1
        if comm > 0:
            commissions_count += 1
            commissions_total += comm

    status_counts = {"pending": 0, "paid": 0, "delivered": 0, "shipped": 0, "canceled": 0, "refunded": 0}
    sales_total = 0.0
    orders = []
    
    for item in orders_raw:
        st = (item.get("status") or "").lower()
        if st in status_counts:
            status_counts[st] += 1
        tot = float(item.get("netTotal") or item.get("total") or 0)
        sales_total += tot
        orders.append({
            "id": item.get("orderId"), "createdAt": item.get("createdAt"),
            "customer": item.get("customerName"), "total": tot, "status": item.get("status"),
            "items": item.get("items") or [],
            "stockId": item.get("stockId"),
            "attendantUserId": item.get("attendantUserId"),
            "paymentStatus": item.get("paymentStatus"),
            "deliveryStatus": item.get("deliveryStatus"),
            "shippingType": item.get("shippingType"),
            "trackingNumber": item.get("trackingNumber"),
            "deliveryPlace": item.get("deliveryPlace"),
            "deliveryDate": item.get("deliveryDate"),
        })

    active_products = 0
    products = []
    for item in products_raw:
        if item.get("active"): active_products += 1
        products.append({
            "id": int(item.get("productId")), "name": item.get("name"),
            "price": float(item.get("price") or 0), "active": bool(item.get("active")),
            "sku": item.get("sku"), "hook": item.get("hook"),
            "description": item.get("description"),
            "copyFacebook": item.get("copyFacebook"),
            "copyInstagram": item.get("copyInstagram"),
            "copyWhatsapp": item.get("copyWhatsapp"),
            "tags": item.get("tags"), "images": item.get("images"),
        })

    campaigns = [_campaign_payload(item) for item in campaigns_raw]

    stock_transfers_raw = _query_bucket("STOCK_TRANSFER")
    pending_transfers_count = 0
    for transfer in stock_transfers_raw:
        if (transfer.get("status") or "").strip().lower() == "pending":
            pending_transfers_count += 1

    pos_sales_raw = _query_bucket("POS_SALE")
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pos_sales_today_count = 0
    for sale in pos_sales_raw:
        created_at = str(sale.get("createdAt") or "")
        if created_at.startswith(today_prefix):
            pos_sales_today_count += 1

    average_ticket = sales_total / len(orders) if orders else 0
    warnings = _build_admin_warnings(
        status_counts["paid"],
        status_counts["pending"],
        commissions_count,
        pending_transfers_count,
        pos_sales_today_count,
    )

    return _json_response(200, {
        "kpis": {
            "salesTotal": sales_total, "averageTicket": average_ticket, "activeProducts": active_products,
            "customersTotal": len(customers), "commissionsTotalPending": commissions_total,
        },
        "statusCounts": status_counts, "customersByLevel": customers_by_level,
        "warnings": warnings,
        "customers": customers, "orders": orders, "products": products, "campaigns": campaigns,
        "productOfMonthId": product_of_month_id,
        "businessConfig": app_cfg,
    })

# ---------------------------------------------------------------------------
# User Dashboard
# ---------------------------------------------------------------------------
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
    badge = str(tags[0]) if tags else ""
    img = _pick_product_image(images, ["miniatura", "landing", "redes"])
    return {
        "id": str(item.get("productId")), "name": item.get("name"),
        "price": float(item.get("price") or 0), "badge": badge, "img": img,
        "hook": item.get("hook") or "", "description": item.get("description") or "",
        "copyFacebook": item.get("copyFacebook") or "",
        "copyInstagram": item.get("copyInstagram") or "",
        "copyWhatsapp": item.get("copyWhatsapp") or "",
        "images": images, "tags": tags,
    }

def _set_product_of_month(payload: dict, headers: Optional[dict] = None) -> dict:
    pid = payload.get("productId") or payload.get("id")
    if not pid:
        return _json_response(200, {"message": "productId es obligatorio", "Error": "BadRequest"})

    if not _get_by_id("PRODUCT", int(pid)):
        return _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})

    now = _now_iso()
    if _get_product_of_month_item():
        updated = _update_by_id("PRODUCT_OF_MONTH", "current", "SET productId = :p, updatedAt = :u", {":p": int(pid), ":u": now})
        _audit_event("product.set_month", headers, payload, {"productId": int(pid)})
        return _json_response(200, {"productOfMonth": updated})

    main = _put_entity("PRODUCT_OF_MONTH", "current", {"entityType": "productOfMonth", "productId": int(pid), "createdAt": now, "updatedAt": now})
    _audit_event("product.set_month", headers, payload, {"productId": int(pid)})
    return _json_response(201, {"productOfMonth": main})

def _get_product_of_month() -> dict:
    item = _get_product_of_month_item()
    return _json_response(200, {"productOfMonth": item}) if item else _json_response(200, {"productOfMonth": None})

def _get_user_dashboard(query: dict, headers: dict) -> dict:
    user_id, is_guest = _resolve_user_context(query or {}, headers or {})
    customer = _get_by_id("CUSTOMER", int(user_id)) if user_id is not None else None

    # Optimized Fetch
    products_raw = _query_bucket("PRODUCT")
    campaigns_raw = _query_bucket("CAMPAIGN")
    products = []
    featured = []
    campaigns = []
    
    for item in products_raw:
        s = _get_product_summary(item)
        products.append({
            "id": s["id"], "name": s["name"], "price": s["price"],
            "badge": s["badge"], "img": s["img"], "description": s["description"],
            "copyFacebook": s["copyFacebook"], "copyInstagram": s["copyInstagram"], "copyWhatsapp": s["copyWhatsapp"],
        })
        if len(featured) < 4:
            imgs = item.get("images") or []
            featured.append({
                "id": s["id"], "label": s["name"], "hook": s["hook"],
                "story": _pick_product_image(imgs, ["redes"]) or s["img"],
                "feed": _pick_product_image(imgs, ["miniatura", "redes"]) or s["img"],
                "banner": _pick_product_image(imgs, ["landing"]) or s["img"],
            })

    for item in campaigns_raw:
        campaign = _campaign_payload(item)
        if not campaign.get("active", True):
            continue
        campaigns.append(campaign)

    pom_item = _get_product_of_month_item()
    product_of_month = None
    if pom_item:
        p = _get_by_id("PRODUCT", int(pom_item.get("productId")))
        if p: product_of_month = _get_product_summary(p)

    cfg = _load_rewards_config()
    month_key = _month_key()
    prev_month_key = _prev_month_key()

    # Pre-fetch customers only if needed for goals/tree
    customers_raw = _query_bucket("CUSTOMER") if customer else []
    print(customers_raw)
    computed_network, computed_goals = [], []
    commission_summary = None
    buy_again_ids = []

    if customer and isinstance(customer, dict):
        tree = _build_network_tree_with_month(
            str(customer.get("customerId")),
            month_key,
            customers_raw,
            cfg,
            max_depth=MAX_NETWORK_DEPTH,
        )
        print(tree)
        computed_network = _network_members_from_tree(tree, max_rows=30)
        computed_goals = _build_goals(customer, tree, customers_raw, cfg)
        
        buy_again_ids, _ = _compute_buy_again_ids_and_maybe_update(customer, products_raw)
        _persist_customer_dashboard_fields(customer.get("customerId"), computed_goals, computed_network, buy_again_ids)

        cid = int(customer.get("customerId"))
        comm_item = _get_commission_month_item(cid, month_key)
        pend = _to_decimal(comm_item.get("totalPending")) if comm_item else D_ZERO
        conf = _to_decimal(comm_item.get("totalConfirmed")) if comm_item else D_ZERO
        blocked = _to_decimal(comm_item.get("totalBlocked")) if comm_item else D_ZERO

        prev_comm_item = _get_commission_month_item(cid, prev_month_key)
        prev_confirmed = _to_decimal(prev_comm_item.get("totalConfirmed")) if prev_comm_item else D_ZERO

        receipt_url = ""
        receipts = _query_bucket("COMMISSION_RECEIPT")
        for r in receipts:
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
            "monthKey": month_key, "totalPending": pend, "totalConfirmed": conf,
            "totalBlocked": blocked,
            "ledger": comm_item.get("ledger") if comm_item and isinstance(comm_item.get("ledger"), list) else [],
            "hasPending": pend > 0, "hasConfirmed": conf > 0,
            "clabeOnFile": bool(clabe), "clabeLast4": clabe[-4:] if clabe else "",
            "payoutDay": int(cfg.get("payoutDay", 10)),
            "paidTotal": prev_confirmed,
            "receiptUrl": receipt_url,
            "prevReceiptUrl": receipt_url,
            "prevStatus": prev_status,
        }
    else:
        # Defaults for guests
        buy_again_ids = [str(p["id"]) for p in products[:3]]

    user_payload = None
    if customer and isinstance(customer, dict):
        dr = _to_decimal(customer.get("discountRate"))
        user_payload = {
            "discountPercent": int((dr * 100).quantize(D_ONE)) if dr else 0,
            "discountActive": bool(customer.get("activeBuyer") or dr > 0),
        }

    payload = {
        "isGuest": bool(is_guest),
        "settings": {
            "cutoffDay": 25, "cutoffHour": 23, "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id), "networkGoal": 300,
        },
        "user": user_payload,
        "goals": computed_goals,
        "products": products, "featured": featured, "productOfMonth": product_of_month,
        "campaigns": campaigns,
        "networkMembers": computed_network, "buyAgainIds": buy_again_ids,
        "commissions": commission_summary,
    }
    return _json_response(200, payload)

def _update_customer_product_stats(customer_id: Any, order_item: dict) -> None:
    if customer_id is None: return
    items = order_item.get("items") or []
    if not items: return
    
    customer = _get_by_id("CUSTOMER", customer_id)
    if not customer: return

    counts = customer.get("productCounts") or {}
    for it in items:
        pid = it.get("productId")
        if pid is not None:
            k = str(pid)
            counts[k] = int(counts.get(k, 0)) + int(it.get("quantity") or 1)

    try:
        _update_by_id("CUSTOMER", customer_id, "SET productCounts = :pc, updatedAt = :u", {":pc": counts, ":u": _now_iso()})
    except Exception:
        pass

def _login(payload: dict) -> dict:
    username = payload.get("username")
    email = payload.get("email") or username
    password = payload.get("password")
    
    if not email or not password:
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    identifier = (email or "").strip()
    
    # Check demo users
    for user in _LOGIN_USERS:
        if identifier in {user.get("username"), user.get("email")} and user["password"] == password:
            return _json_response(200, {"token": "demo-token", "user": user["user"]})

    # DB Auth
    auth = _get_auth_by_email(identifier)
    password_hash = _hash_password(str(password))

    if not auth:
        customer = _find_customer_by_email(identifier)
        if customer and customer.get("passwordHash") == password_hash:
            auth = _create_auth_record(identifier, password_hash, customer.get("customerId"))
        else:
            return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    if auth.get("passwordHash") != password_hash:
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    customer = _get_by_id("CUSTOMER", int(auth["customerId"]))
    if not customer:
        return _json_response(401, {"message": "Credenciales invalidas", "Error": "Unauthorized"})

    dr = _to_decimal(customer.get("discountRate"))
    privileges = _normalize_privileges(customer.get("privileges"))
    can_access_admin = bool(customer.get("canAccessAdmin") or auth.get("role") == "admin")
    is_super_user = _is_super_user_record(auth, customer)
    if is_super_user:
        privileges = {priv: True for priv in _ALL_PRIVILEGES}
        can_access_admin = True
    user = {
        "userId": str(auth["customerId"]), "name": customer.get("name"),
        "role": auth.get("role") or "cliente",
        "canAccessAdmin": can_access_admin,
        "privileges": privileges,
        "isSuperUser": is_super_user,
        "discountPercent": int((dr * 100).quantize(D_ONE)) if dr else 0,
        "discountActive": bool(customer.get("activeBuyer") or dr > 0),
        "level": customer.get("level"),
    }
    return _json_response(200, {"token": "demo-token", "user": user})

# ---------------------------------------------------------------------------
# Lambda Router (Optimized Dispatch)
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
    print(
        f"[lambda][entry] method={method} path={event.get('path') or ''} "
        f"rawPath={event.get('rawPath') or ''}"
    )
    if method == "OPTIONS":
        return _json_response(200, {"ok": True})

    segments = _path_segments(event)
    query = _get_query_params(event)
    headers = event.get("headers") or {}
    
    if not segments:
        return _json_response(200, {"ok": True})

    # Dispatcher Map for O(1) routing instead of O(N) if/else
    # Keys: (segment_count, first_segment, method)
    # Using tuple keys for efficiency
    
    route_key = (len(segments), segments[0], method)
    
    # 1 segment
    if route_key == (1, "login", "POST"): return _login(_parse_body(event))
    if route_key == (1, "crearcuenta", "POST"): return _create_account(_parse_body(event))
    if route_key == (1, "assets", "POST"): return _create_asset(_parse_body(event))
    if route_key == (1, "products", "POST"): return _save_product(_parse_body(event), headers)
    if route_key == (1, "campaigns", "POST"): return _save_campaign(_parse_body(event), headers)
    if route_key == (1, "orders", "POST"): return _create_order(_parse_body(event), headers)
    if route_key == (1, "orders", "GET") and query.get("customerId"): return _list_orders_for_customer(query.get("customerId"))
    if route_key == (1, "customers", "POST"): return _create_customer(_parse_body(event), headers)
    if route_key == (1, "stocks", "GET"): return _list_stocks()
    if route_key == (1, "stocks", "POST"): return _create_stock(_parse_body(event), headers)
    if route_key == (1, "campaigns", "GET"): return _json_response(200, {"campaigns": [_campaign_payload(item) for item in _query_bucket("CAMPAIGN")]})
    if route_key == (1, "user-dashboard", "GET"): return _get_user_dashboard(query, headers)
    
    # 2 segments
    if route_key == (2, "config", "GET") and segments[1] == "rewards": return _get_rewards_config_handler()
    if route_key == (2, "config", "PUT") and segments[1] == "rewards": return _put_rewards_config(_parse_body(event), headers)
    if route_key == (2, "config", "GET") and segments[1] == "app": return _get_app_config_handler()
    if route_key == (2, "config", "PUT") and segments[1] == "app": return _put_app_config(_parse_body(event), headers)
    if route_key == (2, "network", "GET"): return _get_network(segments[1], query)
    if route_key == (2, "assets", "GET"): return _get_asset(segments[1])
    if route_key == (2, "products", "GET") and segments[1] == "product-of-month": return _get_product_of_month()
    if route_key == (2, "products", "POST") and segments[1] == "product-of-month": return _set_product_of_month(_parse_body(event), headers)
    if route_key == (2, "products", "GET"): return _get_product(segments[1])
    if route_key == (2, "orders", "GET"): return _get_order(segments[1])
    if route_key == (2, "orders", "PATCH"): return _update_order_status(segments[1], _parse_body(event), headers)
    if route_key == (2, "commissions", "POST") and segments[1] == "request": return _request_commission_payout(_parse_body(event))
    if route_key == (2, "commissions", "POST") and segments[1] == "receipt": return _upload_commission_receipt(_parse_body(event))
    if route_key == (2, "customers", "GET"): return _get_customer(segments[1])
    if route_key == (2, "customers", "POST") and segments[1] == "clabe": return _update_customer_clabe(_parse_body(event))
    if route_key == (2, "admin", "GET") and segments[1] == "dashboard": return _get_admin_dashboard()
    if route_key == (2, "stocks", "PATCH"): return _update_stock(segments[1], _parse_body(event), headers)
    if route_key == (2, "stocks", "GET") and segments[1] == "transfers": return _list_stock_transfers(query)
    if route_key == (2, "stocks", "POST") and segments[1] == "transfers": return _create_stock_transfer(_parse_body(event), headers)
    if route_key == (2, "stocks", "GET") and segments[1] == "movements": return _list_inventory_movements(query)
    if route_key == (2, "pos", "GET") and segments[1] == "sales": return _list_pos_sales(query)
    if route_key == (2, "pos", "POST") and segments[1] == "sales": return _register_pos_sale(_parse_body(event), headers)
    if route_key == (2, "webhooks", "POST") and segments[1] == "mercadolibre": return _mercadolibre_webhook(query, _parse_body(event), headers)
    if route_key == (2, "webhooks", "GET") and segments[1] == "mercadolibre": return _mercadolibre_webhook(query, _parse_body(event), headers)

    # 3 segments
    if route_key == (3, "admin", "POST") and segments[1] == "commissions" and segments[2] == "receipt": return _upload_admin_commission_receipt(_parse_body(event), headers)
    if route_key == (3, "associates", "GET") and segments[2] == "commissions": return _get_associate_commissions(segments[1], query)
    if route_key == (3, "orders", "POST") and segments[2] == "refund": return _refund_order(segments[1], _parse_body(event))
    if route_key == (3, "orders", "POST") and segments[2] == "cancel": return _cancel_order(segments[1], _parse_body(event))
    if route_key == (3, "orders", "POST") and segments[2] == "checkout": return _create_mercadolibre_checkout(segments[1], _parse_body(event), headers)
    if route_key == (3, "orders", "GET") and segments[2] == "status": return _get_order_status(segments[1])
    if route_key == (3, "stocks", "POST") and segments[2] == "entries": return _register_stock_entry(segments[1], _parse_body(event), headers)
    if route_key == (3, "stocks", "POST") and segments[2] == "damages": return _register_stock_damage(segments[1], _parse_body(event), headers)
    if route_key == (3, "customers", "PATCH") and segments[2] == "privileges": return _update_customer_privileges(segments[1], _parse_body(event), headers)

    # 4 segments
    if route_key == (4, "associates", "GET") and segments[2] == "month": return _get_associate_month(segments[1], segments[3])
    if route_key == (4, "stocks", "POST") and segments[1] == "transfers" and segments[3] == "receive":
        return _receive_stock_transfer(segments[2], _parse_body(event), headers)

    return _json_response(404, {"message": "Ruta no encontrada", "path": "/" + "/".join(segments), "Error": "NotFound"})
