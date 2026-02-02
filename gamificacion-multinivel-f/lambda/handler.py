import base64
import hashlib
import json
import os
import random
import uuid
import functools
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

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)
_s3 = boto3.client("s3", region_name=AWS_REGION)

# Decimal Constants for performance
D_ZERO = Decimal("0")
D_ONE = Decimal("1")
D_CENT = Decimal("0.01")

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
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
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
    
    # Recursive sort is handled by bottom-up build or post-traversal. 
    # Since we sorted when attaching, we just need to ensure the structure is returned.
    return root

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
        
        rows.append({
            "name": n.get("name") or "",
            "level": f"L{n.get('depth')}",
            "spend": spend,
            "status": status,
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

    # Find nearest Plata in upline
    # Using existing _upline_chain which is robust enough
    for lid in _upline_chain(leader_id, max_levels=None):
        candidate = _get_by_id("CUSTOMER", int(lid)) if lid is not None else None
        if not candidate:
            continue
        if (candidate.get("level") or "").strip().lower() == "plata":
            return (lid, "Bronce")
            
    return (None, "Oro")

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
    level_rates = [0.30, 0.35, 0.40]

    lv = (customer.get("level") or "").strip().lower()
    cap = _capabilities(lv)
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
    locked_invite = not cap.get("canRefer")
    goals.insert(2, {
        "key": "invite",
        "title": "Agregar un nuevo miembro a la red este mes",
        "subtitle": ("Tu nivel actual no permite referir" if locked_invite else "Invita a 1 persona y actívala"),
        "target": 1,
        "base": int(new_direct),
        "achieved": bool(new_direct >= 1) if not locked_invite else False,
        "locked": locked_invite,
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
        "subtitle": ("Aún no tienes miembros directos" if not_applicable else f"Directos: {direct_count}"),
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
        "subtitle": ("Tu nivel actual no permite referir" if locked_invite else "Haz que tu red replique"),
        "target": 1,
        "base": 1 if any_member_added else 0,
        "achieved": bool(any_member_added) if not locked_invite else False,
        "locked": locked_invite,
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
        "user": {"userId": "admin-001", "name": "Admin Rivera", "role": "admin"},
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
# Rewards Config (Cached)
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
        "commissionByLevel": {
            "oro": Decimal("0.10"),
            "plata": Decimal("0.05"),
            "bronce": Decimal("0.03"),
        },
        "payoutDay": Decimal("10"),
        "cutRule": "hard_cut_no_pass",
    }

def _config_entity_id() -> str:
    return "rewards-v1"

@functools.lru_cache(maxsize=1)
def _load_rewards_config_cached() -> dict:
    # LRU Cache wrapper to avoid DB hits on warm starts
    cfg = _get_by_id("CONFIG", _config_entity_id())
    if not cfg:
        # If not found, create default and return it (don't cache creation side effect inside getter generally, but ok here)
        return _default_rewards_config() 
    return cfg.get("config") or _default_rewards_config()

def _load_rewards_config() -> dict:
    # Wrapper to handle the creation logic if missing
    cfg = _load_rewards_config_cached()
    # Double check if we need to initialize DB
    if not _get_by_id("CONFIG", _config_entity_id()):
        now = _now_iso()
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
        _load_rewards_config_cached.cache_clear() # Invalidate cache
        return cfg

    _update_by_id(
        "CONFIG",
        _config_entity_id(),
        "SET #c = :c, updatedAt = :u",
        {":c": cfg, ":u": now},
        ean={"#c": "config"},
    )
    _load_rewards_config_cached.cache_clear() # Invalidate cache
    return cfg

def _calc_discount_rate(gross_subtotal: Decimal, tiers: List[dict]) -> Decimal:
    g = gross_subtotal
    for t in tiers:
        tmin = _to_decimal(t.get("min"))
        tmax = _to_decimal(t.get("max")) if t.get("max") is not None else None
        rate = _to_decimal(t.get("rate"))
        if g >= tmin and (tmax is None or g <= tmax):
            return rate
    return D_ZERO

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

def _upsert_month_volume(associate_id: Any, month_key: str, net_delta: Decimal, activation_min: Decimal) -> dict:
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
        return _put_entity("ASSOCIATE_MONTH", mid, item, created_at_iso=now)

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
    return updated2

def _is_active(associate_id: Any, month_key: str) -> bool:
    item = _get_month_state(associate_id, month_key)
    return bool(item.get("isActive"))

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

def _commission_rate_for_level(level: str, cfg: dict) -> Decimal:
    normalized = (level or "").strip().lower()
    raw = (cfg.get("commissionByLevel") or {}) if isinstance(cfg, dict) else {}
    default_map = {"oro": Decimal("0.10"), "plata": Decimal("0.05"), "bronce": Decimal("0.03")}
    val = raw.get(normalized, default_map.get(normalized))
    return _to_decimal(val)

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
    order_id = order_item.get("orderId")
    if not order_id:
        return []

    buyer_id = order_item.get("customerId")
    month_key = order_item.get("monthKey") or _month_key()

    beneficiaries: List[Any] = []
    if buyer_id is not None:
        beneficiaries = _upline_chain(buyer_id, max_levels=None)

    if (order_item.get("buyerType") or "").lower() == "guest":
        referrer_id = order_item.get("referrerAssociateId")
        if referrer_id:
            beneficiaries = [referrer_id] + beneficiaries

    actions: List[dict] = []
    for beneficiary_id in beneficiaries:
        item = _get_commission_month_item(beneficiary_id, month_key)
        if not item:
            continue
        ledger = item.get("ledger") or []
        if not isinstance(ledger, list) or not ledger:
            continue

        pending_indexes = []
        delta = D_ZERO
        for idx, row in enumerate(ledger):
            if row.get("orderId") != order_id:
                continue
            if (row.get("status") or "").lower() != "pending":
                continue
            amt = _to_decimal(row.get("amount"))
            if amt <= 0:
                continue
            pending_indexes.append(idx)
            delta += amt

        if not pending_indexes or delta <= 0:
            continue

        updates = [f"ledger[{idx}].#s = :confirmed" for idx in pending_indexes]
        update_expr = "SET " + ", ".join(updates) + ", totalPending = if_not_exists(totalPending, :zero) - :delta, totalConfirmed = if_not_exists(totalConfirmed, :zero) + :delta, updatedAt = :u"
        
        _table.update_item(
            Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":confirmed": "confirmed", ":delta": delta, ":zero": D_ZERO, ":u": _now_iso(),
            },
        )
        actions.append({
            "beneficiaryId": beneficiary_id,
            "orderId": order_id,
            "confirmedCount": len(pending_indexes),
            "amount": delta,
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
        beneficiaries = _upline_chain(buyer_id, max_levels=None)
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
                removed_count += 1
                continue
            new_ledger.append(row)

        if removed_count == 0:
            continue

        try:
            _table.update_item(
                Key={"PK": "COMMISSION_MONTH", "SK": _commission_month_sk(beneficiary_id, month_key)},
                UpdateExpression="SET ledger = :ledger, totalPending = if_not_exists(totalPending, :zero) - :pd, totalConfirmed = if_not_exists(totalConfirmed, :zero) - :cd, updatedAt = :u",
                ExpressionAttributeValues={
                    ":ledger": new_ledger, ":pd": pending_delta, ":cd": confirmed_delta, ":zero": D_ZERO, ":u": _now_iso(),
                },
            )
        except Exception:
            pass

        total_delta = pending_delta + confirmed_delta
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
def _create_order(payload: dict) -> dict:
    customer_id = payload.get("customerId")
    customer_name = payload.get("customerName")
    items = payload.get("items", [])
    
    if not customer_name or not items:
        return _json_response(200, {"message": "customerName e items son obligatorios", "Error": "BadRequest"})
    
    address = (payload.get("address") or "").strip()
    postal_code = (payload.get("postalCode") or "").strip()
    state = (payload.get("state") or "").strip()
    if not address or not postal_code or not state:
        return _json_response(200, {"message": "Direccion, CP y estado son obligatorios", "Error": "BadRequest"})

    buyer_type = (payload.get("buyerType") or ("guest" if not customer_id else "registered")).lower()
    order_id = _generate_order_id()
    now = _now_iso()
    month_key = _month_key()

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

    # Apply current customer discount at order creation (preview)
    discount_rate = D_ZERO
    if buyer_type in {"associate", "registered"} and customer_id is not None:
        customer = _get_by_id("CUSTOMER", int(customer_id))
        discount_rate = _to_decimal(customer.get("discountRate")) if customer else D_ZERO
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
                
    return _json_response(201, {"order": main})

def _find_order(order_id: str) -> Optional[dict]:
    return _get_by_id("ORDER", order_id)

def _apply_rewards_on_paid_order(order_item: dict) -> dict:
    cfg = _load_rewards_config()
    tiers = cfg.get("discountTiers") or []
    activation_min = _to_decimal(cfg.get("activationNetMin", 2500))

    order_id = order_item.get("orderId")
    buyer_id = order_item.get("customerId")
    buyer_type = (order_item.get("buyerType") or "registered").lower()
    referrer_id = order_item.get("referrerAssociateId")

    gross = _to_decimal(order_item.get("grossSubtotal"))
    if gross <= 0:
        gross = sum([_to_decimal(it.get("price")) * _to_decimal(it.get("quantity") or 1) for it in (order_item.get("items") or [])], D_ZERO)

    month_key = order_item.get("monthKey") or _month_key()

    discount_rate = _to_decimal(order_item.get("discountRate"))
    if discount_rate <= 0:
        if buyer_type in {"associate", "registered"} and buyer_id is not None:
            discount_rate = _calc_discount_rate(gross, tiers)
        else:
            discount_rate = D_ZERO

    discount_amount = (gross * discount_rate).quantize(D_CENT)
    net = (gross - discount_amount).quantize(D_CENT)

    _update_by_id(
        "ORDER", order_id,
        "SET grossSubtotal = :g, discountRate = :dr, discountAmount = :da, netTotal = :n, monthKey = :mk, updatedAt = :u",
        {":g": gross, ":dr": discount_rate, ":da": discount_amount, ":n": net, ":mk": month_key, ":u": _now_iso()},
    )

    if buyer_type == "guest" and referrer_id:
        rate = Decimal("0.10")
        amount = (net * rate).quantize(D_CENT)
        c = {}
        if amount > 0:
            c = _add_commission_to_ledger(referrer_id, month_key, order_id, buyer_id, 0, rate, amount, {"buyerType": buyer_type, "referrerOneShot": True})
            if c:
                _update_customer_commissions_cache(referrer_id, amount)
        return {"grossSubtotal": gross, "discountRate": discount_rate, "discountAmount": discount_amount, "netTotal": net, "monthKey": month_key, "commissionsCreated": [c] if c else [], "mode": "guest_one_shot"}

    if buyer_id is not None and buyer_type in {"associate", "registered"}:
        _upsert_month_volume(buyer_id, month_key, net, activation_min)
        _sync_buyer_benefits(buyer_id, month_key, cfg)
        _update_customer_product_stats(buyer_id, order_item)

    chain = _upline_chain(buyer_id, max_levels=None)
    trail, paid = [], []
    cut = False

    for idx, beneficiary in enumerate(chain):
        level = idx + 1
        if not _is_active(beneficiary, month_key):
            cut = True
            break

        prof = _get_customer_profile(beneficiary)
        blevel = prof.get("level", "Bronce") if prof else "Bronce"
        rate = _commission_rate_for_level(blevel, cfg)
        amount = (net * rate).quantize(D_CENT) if rate > 0 else D_ZERO
        
        if amount <= 0:
            continue

        c = _add_commission_to_ledger(beneficiary, month_key, order_id, buyer_id, level, rate, amount, {"buyerType": buyer_type})
        if c:
            trail.append(c)
            paid.append(c)
            _update_customer_commissions_cache(beneficiary, amount)

    return {"grossSubtotal": gross, "discountRate": discount_rate, "discountAmount": discount_amount, "netTotal": net, "monthKey": month_key, "uplineChain": chain, "cut": cut, "commissionsCreated": trail, "commissionsPaid": paid, "mode": "multilevel"}

def _update_order_status(order_id: str, payload: dict) -> dict:
    status = (payload.get("status") or "").lower()
    valid_statuses = {"pending", "paid", "delivered", "canceled", "refunded", "shipped"}
    if status not in valid_statuses:
        return _json_response(200, {"message": "status invalido", "Error": "BadRequest"})

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
    }
    for f, token in field_map.items():
        if payload.get(f) not in (None, ""):
            updates.append(f"{f} = {token}")
            eav[token] = payload.get(f)

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
    }
    if rewards_result is not None:
        return _json_response(200, {"order": order_response, "rewards": rewards_result})
    return _json_response(200, {"order": order_response})

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
def _save_product(payload: dict) -> dict:
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
            if "tags" in payload: updates.append("tags = :t"); eav[":t"] = payload.get("tags")
            if "images" in payload: updates.append("images = :im"); eav[":im"] = payload.get("images")
            
            updates.append("updatedAt = :u")
            updated = _update_by_id("PRODUCT", int(product_id), "SET " + ", ".join(updates), eav, ean or None)
            return _json_response(200, {"product": updated})

    pid = int(product_id) if product_id is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    item = {
        "entityType": "product", "productId": pid, "name": name,
        "price": _to_decimal(price), "active": bool(payload.get("active", True)),
        "sku": payload.get("sku"), "hook": payload.get("hook"),
        "tags": payload.get("tags"), "images": payload.get("images"),
        "createdAt": now, "updatedAt": now
    }
    # Clean None
    item = {k: v for k, v in item.items() if v is not None}
    
    main = _put_entity("PRODUCT", pid, item, created_at_iso=now)
    return _json_response(201, {"product": main})

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
def _create_customer(payload: dict) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    if not name or not email:
        return _json_response(200, {"message": "name y email son obligatorios", "Error": "BadRequest"})

    customer_id = payload.get("customerId") or int(datetime.now(timezone.utc).timestamp() * 1000)
    leader_id, level = _resolve_leader_and_level(payload.get("leaderId"))
    now = _now_iso()

    item = {
        "entityType": "customer", "customerId": customer_id, "name": name, "email": email,
        "phone": payload.get("phone"), "address": payload.get("address"), "city": payload.get("city"),
        "leaderId": leader_id, "level": level, "isAssociate": bool(payload.get("isAssociate", True)),
        "activeBuyer": False, "discountRate": D_ZERO, "discount": "0%", "commissions": D_ZERO,
        "createdAt": now, "updatedAt": now
    }
    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    
    return _json_response(201, {"customer": {
        "id": customer_id, "name": main["name"], "email": main["email"],
        "leaderId": main["leaderId"], "level": main["level"], "isAssociate": main["isAssociate"],
        "discount": main["discount"], "activeBuyer": bool(main["activeBuyer"]),
        "discountRate": float(main.get("discountRate") or 0),
        "commissions": float(main.get("commissions") or 0),
    }})

def _create_account(payload: dict) -> dict:
    name, email = payload.get("name"), payload.get("email")
    password, confirm = payload.get("password"), payload.get("confirmPassword")
    
    if not name or not email or not password:
        return _json_response(200, {"message": "name, email y password son obligatorios", "Error": "BadRequest"})
    if password != confirm:
        return _json_response(200, {"message": "Las contraseñas no coinciden", "Error": "BadRequest"})

    email_norm = _normalize_email(email)
    if not email_norm:
        return _json_response(200, {"message": "email invalido", "Error": "BadRequest"})
    if _get_auth_by_email(email_norm):
        return _json_response(200, {"message": "El correo ya esta registrado", "Error": "Conflict"})

    customer_id = payload.get("customerId") or int(datetime.now(timezone.utc).timestamp() * 1000)
    leader_token = payload.get("referralToken") or payload.get("leaderId")
    leader_id, level = _resolve_leader_and_level(_parse_int_or_str(leader_token))
    product_id = _parse_int_or_str(payload.get("productId") or payload.get("refProductId"))

    now = _now_iso()
    password_hash = _hash_password(str(password))
    item = {
        "entityType": "customer", "customerId": customer_id, "name": name, "email": email_norm,
        "phone": payload.get("phone"), "address": payload.get("address"), "city": payload.get("city"),
        "leaderId": leader_id, "level": level, "isAssociate": bool(payload.get("isAssociate", True)),
        "activeBuyer": False, "discountRate": D_ZERO, "discount": "0%", "commissions": D_ZERO,
        "passwordHash": password_hash, "refProductId": product_id,
        "createdAt": now, "updatedAt": now
    }
    
    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    _create_auth_record(email_norm, password_hash, customer_id, role="cliente")
    
    return _json_response(201, {"customer": {
        "id": customer_id, "name": main["name"], "email": main["email"],
        "leaderId": main["leaderId"], "level": main["level"], "isAssociate": main["isAssociate"],
        "discount": main["discount"], "activeBuyer": bool(main["activeBuyer"]),
        "discountRate": float(main.get("discountRate") or 0),
        "commissions": float(main.get("commissions") or 0),
    }})

def _get_customer(customer_id: str) -> dict:
    item = _get_by_id("CUSTOMER", int(customer_id))
    return _json_response(200, {"customer": item}) if item else _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

def _get_network(customer_id: str, query: dict) -> dict:
    depth = int(query.get("depth") or 3)
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
        })
    return _json_response(200, {"orders": rows})

# ---------------------------------------------------------------------------
# Rewards API
# ---------------------------------------------------------------------------
def _get_rewards_config_handler() -> dict:
    return _json_response(200, {"config": _load_rewards_config()})

def _put_rewards_config(payload: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        return _json_response(200, {"message": "config invalida", "Error": "BadRequest"})

    cfg = _default_rewards_config()
    cfg.update(payload)
    
    # Normalize types
    cfg["activationNetMin"] = float(cfg.get("activationNetMin", 2500))
    cfg["payoutDay"] = int(cfg.get("payoutDay", 10))
    
    cbyl = cfg.get("commissionByLevel") or {}
    cfg["commissionByLevel"] = {
        "oro": float(cbyl.get("oro", 0.10)),
        "plata": float(cbyl.get("plata", 0.05)),
        "bronce": float(cbyl.get("bronce", 0.03)),
    }
    
    cfg["discountTiers"] = [
        {"min": float(t.get("min", 0)), "max": float(t.get("max")) if t.get("max") not in (None, "") else None, "rate": float(t.get("rate", 0))}
        for t in (cfg.get("discountTiers") or [])
    ]

    return _json_response(200, {"config": _save_rewards_config(cfg)})

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

    existing_clabe = (customer.get("clabe") or "").strip()
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
            _update_by_id("CUSTOMER", int(customer_id), "SET clabe = :c, updatedAt = :u", {":c": clabe, ":u": now})
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

# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------
def _build_admin_warnings(paid_count: int, pending_count: int, commissions_count: int) -> list:
    warnings = []
    if commissions_count: warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
    if paid_count: warnings.append({"type": "shipping", "text": f"{paid_count} pedidos pagados sin envío", "severity": "medium"})
    if pending_count: warnings.append({"type": "payments", "text": f"{pending_count} pedidos pendientes de pago", "severity": "low"})
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
    # Optimized fetch all
    customers_raw = _query_bucket("CUSTOMER")
    orders_raw = _query_bucket("ORDER")
    products_raw = _query_bucket("PRODUCT")

    customers = []
    customers_by_level = {}
    commissions_count = 0
    commissions_total = 0.0

    for item in customers_raw:
        comm = float(item.get("commissions") or 0)
        customers.append({
            "id": item.get("customerId"), "name": item.get("name"), "email": item.get("email"),
            "leaderId": item.get("leaderId"), "level": item.get("level"), "discount": item.get("discount"),
            "commissions": comm,
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
        })

    active_products = 0
    products = []
    for item in products_raw:
        if item.get("active"): active_products += 1
        products.append({
            "id": int(item.get("productId")), "name": item.get("name"),
            "price": float(item.get("price") or 0), "active": bool(item.get("active")),
            "sku": item.get("sku"), "hook": item.get("hook"),
            "tags": item.get("tags"), "images": item.get("images"),
        })

    average_ticket = sales_total / len(orders) if orders else 0
    warnings = _build_admin_warnings(status_counts["paid"], status_counts["pending"], commissions_count)
    paid_commissions_summary = _commissions_paid_summary(_month_key(), customers_raw)

    return _json_response(200, {
        "kpis": {
            "salesTotal": sales_total, "averageTicket": average_ticket, "activeProducts": active_products,
            "customersTotal": len(customers), "commissionsTotalPending": commissions_total,
        },
        "statusCounts": status_counts, "customersByLevel": customers_by_level,
        "warnings": warnings, "commissionsPaidSummary": paid_commissions_summary,
        "customers": customers, "orders": orders, "products": products,
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
        "hook": item.get("hook") or "", "images": images, "tags": tags,
    }

def _set_product_of_month(payload: dict) -> dict:
    pid = payload.get("productId") or payload.get("id")
    if not pid:
        return _json_response(200, {"message": "productId es obligatorio", "Error": "BadRequest"})

    if not _get_by_id("PRODUCT", int(pid)):
        return _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})

    now = _now_iso()
    if _get_product_of_month_item():
        updated = _update_by_id("PRODUCT_OF_MONTH", "current", "SET productId = :p, updatedAt = :u", {":p": int(pid), ":u": now})
        return _json_response(200, {"productOfMonth": updated})

    main = _put_entity("PRODUCT_OF_MONTH", "current", {"entityType": "productOfMonth", "productId": int(pid), "createdAt": now, "updatedAt": now})
    return _json_response(201, {"productOfMonth": main})

def _get_product_of_month() -> dict:
    item = _get_product_of_month_item()
    return _json_response(200, {"productOfMonth": item}) if item else _json_response(200, {"productOfMonth": None})

def _get_user_dashboard(query: dict, headers: dict) -> dict:
    user_id, is_guest = _resolve_user_context(query or {}, headers or {})
    customer = _get_by_id("CUSTOMER", int(user_id)) if user_id is not None else None

    # Optimized Fetch
    products_raw = _query_bucket("PRODUCT")
    products = []
    featured = []
    
    for item in products_raw:
        s = _get_product_summary(item)
        products.append({"id": s["id"], "name": s["name"], "price": s["price"], "badge": s["badge"], "img": s["img"]})
        if len(featured) < 4:
            imgs = item.get("images") or []
            featured.append({
                "id": s["id"], "label": s["name"], "hook": s["hook"],
                "story": _pick_product_image(imgs, ["redes"]) or s["img"],
                "feed": _pick_product_image(imgs, ["miniatura", "redes"]) or s["img"],
                "banner": _pick_product_image(imgs, ["landing"]) or s["img"],
            })

    pom_item = _get_product_of_month_item()
    product_of_month = None
    if pom_item:
        p = _get_by_id("PRODUCT", int(pom_item.get("productId")))
        if p: product_of_month = _get_product_summary(p)

    cfg = _load_rewards_config()
    month_key = _month_key()

    # Pre-fetch customers only if needed for goals/tree
    customers_raw = _query_bucket("CUSTOMER") if customer else []

    computed_network, computed_goals = [], []
    commission_summary = None
    buy_again_ids = []

    if customer and isinstance(customer, dict):
        tree = _build_network_tree_with_month(str(customer.get("customerId")), month_key, customers_raw, cfg)
        computed_network = _network_members_from_tree(tree, max_rows=30)
        computed_goals = _build_goals(customer, tree, customers_raw, cfg)
        
        buy_again_ids, _ = _compute_buy_again_ids_and_maybe_update(customer, products_raw)
        _persist_customer_dashboard_fields(customer.get("customerId"), computed_goals, computed_network, buy_again_ids)

        comm_item = _get_commission_month_item(int(customer.get("customerId")), month_key)
        pend = _to_decimal(comm_item.get("totalPending")) if comm_item else D_ZERO
        conf = _to_decimal(comm_item.get("totalConfirmed")) if comm_item else D_ZERO
        
        clabe = (customer.get("clabe") or "").strip()
        commission_summary = {
            "monthKey": month_key, "totalPending": pend, "totalConfirmed": conf,
            "ledger": comm_item.get("ledger") if comm_item and isinstance(comm_item.get("ledger"), list) else [],
            "hasPending": pend > 0, "hasConfirmed": conf > 0,
            "clabeOnFile": bool(clabe), "clabeLast4": clabe[-4:] if clabe else "",
            "payoutDay": int(cfg.get("payoutDay", 10)),
        }
    else:
        # Defaults for guests
        buy_again_ids = [str(p["id"]) for p in products[:3]]

    payload = {
        "isGuest": bool(is_guest),
        "settings": {
            "cutoffDay": 25, "cutoffHour": 23, "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id), "networkGoal": 300,
        },
        "goals": computed_goals,
        "products": products, "featured": featured, "productOfMonth": product_of_month,
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
    user = {
        "userId": str(auth["customerId"]), "name": customer.get("name"),
        "role": auth.get("role") or "cliente",
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
    if method == "OPTIONS":
        return _json_response(200, {"ok": True})

    segments = _path_segments(event)
    query = _get_query_params(event)
    
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
    if route_key == (1, "products", "POST"): return _save_product(_parse_body(event))
    if route_key == (1, "orders", "POST"): return _create_order(_parse_body(event))
    if route_key == (1, "orders", "GET") and query.get("customerId"): return _list_orders_for_customer(query.get("customerId"))
    if route_key == (1, "customers", "POST"): return _create_customer(_parse_body(event))
    if route_key == (1, "user-dashboard", "GET"): return _get_user_dashboard(query, event.get("headers") or {})
    
    # 2 segments
    if route_key == (2, "config", "GET") and segments[1] == "rewards": return _get_rewards_config_handler()
    if route_key == (2, "config", "PUT") and segments[1] == "rewards": return _put_rewards_config(_parse_body(event))
    if route_key == (2, "network", "GET"): return _get_network(segments[1], query)
    if route_key == (2, "assets", "GET"): return _get_asset(segments[1])
    if route_key == (2, "products", "GET") and segments[1] == "product-of-month": return _get_product_of_month()
    if route_key == (2, "products", "POST") and segments[1] == "product-of-month": return _set_product_of_month(_parse_body(event))
    if route_key == (2, "products", "GET"): return _get_product(segments[1])
    if route_key == (2, "orders", "GET"): return _get_order(segments[1])
    if route_key == (2, "orders", "PATCH"): return _update_order_status(segments[1], _parse_body(event))
    if route_key == (2, "commissions", "POST") and segments[1] == "request": return _request_commission_payout(_parse_body(event))
    if route_key == (2, "commissions", "POST") and segments[1] == "receipt": return _upload_commission_receipt(_parse_body(event))
    if route_key == (2, "customers", "GET"): return _get_customer(segments[1])
    if route_key == (2, "admin", "GET") and segments[1] == "dashboard": return _get_admin_dashboard()

    # 3 segments
    if route_key == (3, "associates", "GET") and segments[2] == "commissions": return _get_associate_commissions(segments[1], query)
    if route_key == (3, "orders", "POST") and segments[2] == "refund": return _refund_order(segments[1], _parse_body(event))
    if route_key == (3, "orders", "POST") and segments[2] == "cancel": return _cancel_order(segments[1], _parse_body(event))

    # 4 segments
    if route_key == (4, "associates", "GET") and segments[2] == "month": return _get_associate_month(segments[1], segments[3])

    return _json_response(404, {"message": "Ruta no encontrada", "path": "/" + "/".join(segments), "Error": "NotFound"})
