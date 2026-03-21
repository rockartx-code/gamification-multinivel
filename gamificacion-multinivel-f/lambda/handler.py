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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
from app.admin import AdminDashboardService
from app.campaigns import CampaignService
from app.config import ConfigService
from app.notifications import NotificationService
from app.user_dashboard import UserDashboardService
from boto3.dynamodb.conditions import Attr, Key
from helpers.auth import generate_otp_code, hash_otp, hash_password
from helpers.http import get_path, get_query_params, parse_body, path_segments
from helpers.responses import json_default, json_response

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")
BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = (os.getenv("SES_FROM_EMAIL") or os.getenv("SES_SOURCE_EMAIL") or "info@findingu.com.mx").strip()
SES_REPLY_TO = (os.getenv("SES_REPLY_TO") or "").strip()
FRONTEND_BASE_URL = (os.getenv("FRONTEND_BASE_URL") or "https://www.findingu.com.mx/").strip().rstrip("/")
PASSWORD_RESET_OTP_TTL_MINUTES = int(os.getenv("PASSWORD_RESET_OTP_TTL_MINUTES", "15"))
DEFAULT_SPONSOR_NAME = (os.getenv("DEFAULT_SPONSOR_NAME") or "FindingU").strip() or "FindingU"
DEFAULT_SPONSOR_EMAIL = (os.getenv("DEFAULT_SPONSOR_EMAIL") or "coach@findingu.com.mx").strip()
DEFAULT_SPONSOR_PHONE = (os.getenv("DEFAULT_SPONSOR_PHONE") or "+52 1 55 1498 2351").strip()
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
_ses = boto3.client("ses", region_name=AWS_REGION)

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
NOTIFICATION_LINK_TEXT_DEFAULT = "Ver"
MAX_NOTIFICATION_DESCRIPTION_LENGTH = 300

# ---------------------------------------------------------------------------
# JSON / HTTP helpers
# ---------------------------------------------------------------------------
def _json_default(value):
    return json_default(value)

def _json_response(status_code: int, payload: dict) -> dict:
    return json_response(status_code, payload)

def _debug_json(value: Any) -> str:
    try:
        return json.dumps(value, default=_json_default, sort_keys=True)
    except Exception as exc:
        return f"<json_error:{exc}> {value!r}"

def _address_log(step: str, **fields: Any) -> None:
    print(f"[order][address][{step}] {_debug_json(fields)}")

def _address_snapshot_for_log(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    return {
        "addressId": value.get("addressId") or value.get("id"),
        "label": value.get("label"),
        "recipientName": value.get("recipientName"),
        "phone": value.get("phone"),
        "address": value.get("address"),
        "postalCode": value.get("postalCode"),
        "state": value.get("state") or value.get("city"),
        "isDefault": value.get("isDefault"),
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
    return hash_password(password)

def _hash_otp(otp: str) -> str:
    return hash_otp(otp)

def _generate_otp_code(length: int = 6) -> str:
    return generate_otp_code(length)

def _parse_int_or_str(value: Any) -> Any:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return value

def _parse_body(event: dict) -> dict:
    return parse_body(event)

def _get_query_params(event: dict) -> dict:
    return get_query_params(event)

def _get_path(event: dict) -> str:
    return get_path(event)

def _path_segments(event: dict) -> List[str]:
    return path_segments(event)

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
        parsed = datetime.fromisoformat(iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
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
        "subtitle": "Invita a 1 persona y actí­vala",
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
    active_product_ids = {
        str(item.get("productId"))
        for item in products
        if isinstance(item, dict) and bool(item.get("active", True))
    }

    if not isinstance(counts, dict) or not counts:
        should_persist = (isinstance(existing, list) and len(existing) > 0)
        return ([], should_persist)

    ordered = sorted(counts.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
    top = [str(pid) for pid, _ in ordered if str(pid) in active_product_ids][:3]

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
    if entity in {"ORDER", "CUSTOMER"}:
        _address_log(
            "put_entity.start",
            entity=entity,
            entityId=entity_id,
            pk=main_item["PK"],
            sk=main_item["SK"],
            address=_address_snapshot_for_log(main_item.get("shippingAddress") or main_item),
            addressCount=len(main_item.get("addresses") or main_item.get("shippingAddresses") or []),
        )
    try:
        _table.put_item(Item=main_item)
        _table.put_item(Item=ref_item)
    except Exception as exc:
        if entity in {"ORDER", "CUSTOMER"}:
            _address_log(
                "put_entity.error",
                entity=entity,
                entityId=entity_id,
                pk=main_item["PK"],
                sk=main_item["SK"],
                error=str(exc),
            )
        raise
    if entity in {"ORDER", "CUSTOMER"}:
        _address_log(
            "put_entity.ok",
            entity=entity,
            entityId=entity_id,
            pk=main_item["PK"],
            sk=main_item["SK"],
            address=_address_snapshot_for_log(main_item.get("shippingAddress") or main_item),
            addressCount=len(main_item.get("addresses") or main_item.get("shippingAddresses") or []),
        )
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
        if str(entity).upper() == "CUSTOMER":
            _address_log("update_by_id.ref_missing", entity=str(entity).upper(), entityId=entity_id)
        raise KeyError(f"{entity.upper()}_REF_NOT_FOUND")

    kwargs = {
        "Key": {"PK": ref["refPK"], "SK": ref["refSK"]},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": eav,
        "ReturnValues": return_values,
    }
    if ean:
        kwargs["ExpressionAttributeNames"] = ean

    if str(entity).upper() == "CUSTOMER":
        _address_log(
            "update_by_id.start",
            entity=str(entity).upper(),
            entityId=entity_id,
            ref=ref,
            updateExpression=update_expression,
            expressionAttributeValues=eav,
            expressionAttributeNames=ean or {},
        )
    try:
        resp = _table.update_item(**kwargs)
    except Exception as exc:
        if str(entity).upper() == "CUSTOMER":
            _address_log(
                "update_by_id.error",
                entity=str(entity).upper(),
                entityId=entity_id,
                ref=ref,
                updateExpression=update_expression,
                expressionAttributeValues=eav,
                expressionAttributeNames=ean or {},
                error=str(exc),
            )
        raise
    if str(entity).upper() == "CUSTOMER":
        attrs = resp.get("Attributes") or {}
        _address_log(
            "update_by_id.ok",
            entity=str(entity).upper(),
            entityId=entity_id,
            address=_address_snapshot_for_log(attrs),
            defaultAddressId=attrs.get("defaultAddressId"),
            defaultShippingAddressId=attrs.get("defaultShippingAddressId"),
            addressCount=len(attrs.get("addresses") or attrs.get("shippingAddresses") or []),
        )
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

def _query_exact_pk(pk: str, limit: Optional[int] = None, scan_forward: bool = False) -> List[dict]:
    items = []
    query_kwargs = {
        "KeyConditionExpression": Key("PK").eq(pk),
        "ScanIndexForward": scan_forward,
    }

    if limit:
        query_kwargs["Limit"] = limit
        resp = _table.query(**query_kwargs)
        return resp.get("Items", []) or []

    while True:
        resp = _table.query(**query_kwargs)
        batch = resp.get("Items", [])
        items.extend(batch)

        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        query_kwargs["ExclusiveStartKey"] = lek

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

def _password_reset_url(email: str, otp: str) -> str:
    if not FRONTEND_BASE_URL:
        return ""
    query = urllib.parse.urlencode({"email": email, "otp": otp})
    return f"{FRONTEND_BASE_URL}/#/recuperar-contrasena?{query}"

def _send_email_via_ses(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    if not SES_FROM_EMAIL:
        raise RuntimeError("SES_FROM_EMAIL no configurado")

    payload = {
        "Source": SES_FROM_EMAIL,
        "Destination": {"ToAddresses": [to_email]},
        "Message": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    }
    if SES_REPLY_TO:
        payload["ReplyToAddresses"] = [SES_REPLY_TO]

    _ses.send_email(**payload)

def _send_password_reset_otp_email(name: str, email: str, otp: str) -> None:
    reset_url = _password_reset_url(email, otp)
    ttl_minutes = PASSWORD_RESET_OTP_TTL_MINUTES
    subject = "Recupera tu contrasena"
    text_lines = [
        f"Hola {name or 'usuario'},",
        "",
        f"Tu codigo OTP para recuperar la contrasena es: {otp}",
        f"Este codigo vence en {ttl_minutes} minutos.",
    ]
    if reset_url:
        text_lines.extend(["", f"Tambien puedes abrir este enlace: {reset_url}"])
    text_lines.extend(["", "Si no solicitaste este cambio, ignora este correo."])
    text_body = "\n".join(text_lines)

    html_body = (
        f"<html><body>"
        f"<p>Hola {name or 'usuario'},</p>"
        f"<p>Tu codigo OTP para recuperar la contrasena es:</p>"
        f"<p style='font-size:24px;font-weight:bold;letter-spacing:4px;'>{otp}</p>"
        f"<p>Este codigo vence en {ttl_minutes} minutos.</p>"
        + (f"<p><a href='{reset_url}'>Abrir pantalla de cambio de contrasena</a></p>" if reset_url else "")
        + "<p>Si no solicitaste este cambio, ignora este correo.</p>"
        + "</body></html>"
    )
    _send_email_via_ses(email, subject, text_body, html_body)

def _send_welcome_email(name: str, email: str) -> None:
    subject = "Bienvenido a FindingU"
    text_body = (
        f"Hola {name or 'usuario'},\n\n"
        "Tu registro fue completado correctamente.\n"
        "Ya puedes iniciar sesion y acceder a tu panel.\n\n"
        "Gracias por unirte a FindingU."
    )
    html_body = (
        f"<html><body>"
        f"<p>Hola {name or 'usuario'},</p>"
        "<p>Tu registro fue completado correctamente.</p>"
        "<p>Ya puedes iniciar sesion y acceder a tu panel.</p>"
        "<p>Gracias por unirte a <strong>FindingU</strong>.</p>"
        "</body></html>"
    )
    _send_email_via_ses(email, subject, text_body, html_body)

def _send_network_join_email(sponsor: dict, member: dict) -> None:
    sponsor_email = _normalize_email(sponsor.get("email"))
    if not sponsor_email:
        return

    sponsor_name = sponsor.get("name") or "usuario"
    member_name = member.get("name") or "Nuevo miembro"
    member_email = member.get("email") or ""
    member_phone = member.get("phone") or ""
    subject = "Nuevo miembro en tu red"
    text_body = (
        f"Hola {sponsor_name},\n\n"
        f"{member_name} acaba de entrar a tu red.\n"
        f"Correo: {member_email or '-'}\n"
        f"Telefono: {member_phone or '-'}\n\n"
        "Entra a tu panel para darle seguimiento."
    )
    html_body = (
        f"<html><body>"
        f"<p>Hola {sponsor_name},</p>"
        f"<p><strong>{member_name}</strong> acaba de entrar a tu red.</p>"
        f"<p>Correo: {member_email or '-'}</p>"
        f"<p>Telefono: {member_phone or '-'}</p>"
        f"<p>Entra a tu panel para darle seguimiento.</p>"
        f"</body></html>"
    )
    _send_email_via_ses(sponsor_email, subject, text_body, html_body)

def _sponsor_contact_payload(customer: Optional[dict]) -> dict:
    return _user_dashboard_service.sponsor_contact_payload(customer)

def _find_effective_sponsor(customer: Optional[dict]) -> dict:
    return _user_dashboard_service.build_sponsor_payload(customer)

def _would_create_leader_cycle(customers_raw: List[dict], customer_id: Any, leader_id: Any) -> bool:
    if customer_id in (None, "") or leader_id in (None, ""):
        return False
    customer_id_str = str(customer_id)
    current = str(leader_id)
    leader_by_customer = {
        str(item.get("customerId")): str(item.get("leaderId"))
        for item in customers_raw
        if item.get("customerId") not in (None, "") and item.get("leaderId") not in (None, "")
    }
    seen = set()
    while current and current not in seen:
        if current == customer_id_str:
            return True
        seen.add(current)
        current = leader_by_customer.get(current, "")
    return False

def _store_password_reset_otp(email: str, customer_id: Any, otp: str) -> dict:
    now_dt = _utc_now()
    now_iso = now_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    expires_at = (now_dt + timedelta(minutes=PASSWORD_RESET_OTP_TTL_MINUTES)).replace(microsecond=0)
    expires_iso = expires_at.isoformat().replace("+00:00", "Z")
    item = {
        "entityType": "passwordReset",
        "passwordResetId": email,
        "email": email,
        "customerId": customer_id,
        "otpHash": _hash_otp(otp),
        "otpLast4": otp[-4:],
        "used": False,
        "attempts": 0,
        "expiresAt": expires_iso,
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    return _put_entity("PASSWORD_RESET", email, item, created_at_iso=now_iso)

def _request_password_recovery(payload: dict) -> dict:
    email_norm = _normalize_email(payload.get("email"))
    if not email_norm:
        return _json_response(200, {"message": "Ingresa un correo electronico valido", "Error": "BadRequest"})

    auth = _get_auth_by_email(email_norm)
    customer = _find_customer_by_email(email_norm)
    customer_id = None
    name = ""
    if auth and auth.get("customerId") is not None:
        customer_id = auth.get("customerId")
        customer = customer or _get_by_id("CUSTOMER", customer_id)
    elif customer and customer.get("customerId") is not None:
        customer_id = customer.get("customerId")

    if customer:
        name = customer.get("name") or ""

    if customer_id is None:
        return _json_response(200, {
            "ok": True,
            "message": "Si el correo existe, te enviamos un codigo OTP para recuperar tu contrasena."
        })

    otp = _generate_otp_code()
    _store_password_reset_otp(email_norm, customer_id, otp)
    try:
        _send_password_reset_otp_email(name, email_norm, otp)
    except Exception as exc:
        print(f"[password-recovery] SES send failed: {exc}")
        return _json_response(200, {"message": "No se pudo enviar el correo OTP", "Error": "EmailSendFailed"})

    return _json_response(200, {
        "ok": True,
        "message": "Si el correo existe, te enviamos un codigo OTP para recuperar tu contrasena."
    })

def _reset_password(payload: dict) -> dict:
    email_norm = _normalize_email(payload.get("email"))
    otp = str(payload.get("otp") or "").strip()
    password = payload.get("password")
    confirm = payload.get("confirmPassword")

    if not email_norm or not otp or not password or not confirm:
        return _json_response(200, {"message": "email, otp, password y confirmPassword son obligatorios", "Error": "BadRequest"})
    if password != confirm:
        return _json_response(200, {"message": "Las contrasenas no coinciden", "Error": "BadRequest"})

    reset_record = _get_by_id("PASSWORD_RESET", email_norm)
    if not reset_record:
        return _json_response(200, {"message": "OTP invalido o expirado", "Error": "Unauthorized"})
    if bool(reset_record.get("used")):
        return _json_response(200, {"message": "OTP invalido o expirado", "Error": "Unauthorized"})
    expires_at = _iso_to_dt(reset_record.get("expiresAt"))
    if not expires_at or expires_at <= _utc_now():
        return _json_response(200, {"message": "OTP invalido o expirado", "Error": "Unauthorized"})
    if reset_record.get("otpHash") != _hash_otp(otp):
        attempts = int(reset_record.get("attempts") or 0) + 1
        try:
            _update_by_id(
                "PASSWORD_RESET",
                email_norm,
                "SET attempts = :a, updatedAt = :u",
                {":a": attempts, ":u": _now_iso()},
            )
        except Exception:
            pass
        return _json_response(200, {"message": "OTP invalido o expirado", "Error": "Unauthorized"})

    auth = _get_auth_by_email(email_norm)
    customer = _find_customer_by_email(email_norm)
    if not auth and customer and customer.get("customerId") is not None:
        auth = _create_auth_record(email_norm, _hash_password(str(password)), customer.get("customerId"))
    if not auth:
        return _json_response(200, {"message": "No existe una cuenta asociada al correo", "Error": "NoEncontrado"})

    password_hash = _hash_password(str(password))
    _update_by_id("AUTH", email_norm, "SET passwordHash = :p, updatedAt = :u", {":p": password_hash, ":u": _now_iso()})

    customer_id = auth.get("customerId")
    if customer_id is not None:
        try:
            _update_by_id("CUSTOMER", customer_id, "SET passwordHash = :p, updatedAt = :u", {":p": password_hash, ":u": _now_iso()})
        except Exception:
            pass

    _update_by_id(
        "PASSWORD_RESET",
        email_norm,
        "SET used = :used, usedAt = :usedAt, updatedAt = :u",
        {":used": True, ":usedAt": _now_iso(), ":u": _now_iso()},
    )

    return _json_response(200, {"ok": True, "message": "Contrasena actualizada correctamente"})

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

_config_service = ConfigService(
    default_commission_by_depth=DEFAULT_COMMISSION_BY_DEPTH,
    json_response=_json_response,
    audit_event=_audit_event,
    get_by_id=_get_by_id,
    put_entity=_put_entity,
    update_by_id=_update_by_id,
    now_iso=_now_iso,
    to_decimal=_to_decimal,
)


def _default_rewards_config() -> dict:
    return _config_service.default_rewards_config()


def _default_app_config() -> dict:
    return _config_service.default_app_config()


def _legacy_rewards_config_entity_id() -> str:
    return _config_service.legacy_rewards_config_entity_id()


def _app_config_entity_id() -> str:
    return _config_service.app_config_entity_id()


def _merge_dict(base: Any, override: Any) -> Any:
    return _config_service.merge_dict(base, override)


def _normalize_rewards_config(raw: Any) -> dict:
    return _config_service.normalize_rewards_config(raw)


def _normalize_app_config(raw: Any) -> dict:
    return _config_service.normalize_app_config(raw)


def _load_app_config() -> dict:
    return _config_service.load_app_config()


def _save_legacy_rewards_config(cfg: dict) -> None:
    _config_service.save_legacy_rewards_config(cfg)


def _save_app_config(cfg: dict) -> dict:
    return _config_service.save_app_config(cfg)


def _load_rewards_config() -> dict:
    return _config_service.load_rewards_config()


def _save_rewards_config(cfg: dict) -> dict:
    return _config_service.save_rewards_config(cfg)

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
def _clean_str(value: Any) -> str:
    return str(value or "").strip()

def _customer_entity_id(value: Any) -> Optional[Any]:
    normalized = _parse_int_or_str(value)
    return None if normalized in (None, "", 0, "0") else normalized

def _truthy_flag(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return _clean_str(value).lower() in {"1", "true", "yes", "on"}

def _build_shipping_address_entry(
    *,
    recipient_name: str = "",
    phone: str = "",
    address: str = "",
    postal_code: str = "",
    state: str = "",
    label: str = "",
    address_id: Optional[str] = None,
    is_default: bool = False,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Optional[dict]:
    recipient_name = _clean_str(recipient_name)
    phone = _clean_str(phone)
    address = _clean_str(address)
    postal_code = _clean_str(postal_code)
    state = _clean_str(state)
    label = _clean_str(label)

    if not any([address, postal_code, state]):
        return None

    item = {
        "label": label,
        "recipientName": recipient_name,
        "phone": phone,
        "address": address,
        "postalCode": postal_code,
        "state": state,
        "isDefault": bool(is_default),
    }
    if address_id:
        item["addressId"] = address_id
    if created_at:
        item["createdAt"] = created_at
    if updated_at:
        item["updatedAt"] = updated_at
    return item

def _shipping_address_from_payload(payload: dict, fallback_label: str = "") -> Optional[dict]:
    if not isinstance(payload, dict):
        _address_log("payload.invalid", payloadType=type(payload).__name__)
        return None
    shipping_address = payload.get("shippingAddress") if isinstance(payload.get("shippingAddress"), dict) else {}
    snapshot = _build_shipping_address_entry(
        recipient_name=shipping_address.get("recipientName") or payload.get("recipientName") or payload.get("customerName"),
        phone=shipping_address.get("phone") or payload.get("phone"),
        address=shipping_address.get("address") or payload.get("address"),
        postal_code=shipping_address.get("postalCode") or payload.get("postalCode"),
        state=shipping_address.get("state") or shipping_address.get("city") or payload.get("state") or payload.get("city"),
        label=shipping_address.get("label") or payload.get("shippingAddressLabel") or fallback_label,
        address_id=shipping_address.get("addressId") or shipping_address.get("id") or payload.get("shippingAddressId"),
        is_default=bool(shipping_address.get("isDefault")),
    )
    _address_log(
        "payload.snapshot",
        customerId=payload.get("customerId"),
        shippingAddress=_address_snapshot_for_log(shipping_address),
        directAddress={
            "recipientName": payload.get("recipientName"),
            "phone": payload.get("phone"),
            "address": payload.get("address"),
            "postalCode": payload.get("postalCode"),
            "state": payload.get("state") or payload.get("city"),
            "shippingAddressId": payload.get("shippingAddressId"),
            "shippingAddressLabel": payload.get("shippingAddressLabel"),
            "saveShippingAddress": payload.get("saveShippingAddress"),
        },
        snapshot=_address_snapshot_for_log(snapshot),
    )
    return snapshot

def _normalize_customer_shipping_addresses(customer: Optional[dict]) -> List[dict]:
    if not customer or not isinstance(customer, dict):
        _address_log("normalize_addresses.empty_customer", customer=customer)
        return []

    addresses: List[dict] = []
    default_id = _clean_str(customer.get("defaultAddressId") or customer.get("defaultShippingAddressId"))
    raw_items = customer.get("addresses")
    if not isinstance(raw_items, list):
        raw_items = customer.get("shippingAddresses")
    if isinstance(raw_items, list):
        for idx, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, dict):
                continue
            entry = _build_shipping_address_entry(
                recipient_name=raw.get("recipientName") or customer.get("name"),
                phone=raw.get("phone") or customer.get("phone"),
                address=raw.get("address"),
                postal_code=raw.get("postalCode"),
                state=raw.get("state") or raw.get("city") or customer.get("state") or customer.get("city"),
                label=raw.get("label") or f"Direccion {idx}",
                address_id=_clean_str(raw.get("addressId")) or f"ADDR-{idx}",
                is_default=bool(raw.get("isDefault")),
                created_at=raw.get("createdAt"),
                updated_at=raw.get("updatedAt"),
            )
            if entry:
                addresses.append(entry)

    if not addresses:
        legacy = _build_shipping_address_entry(
            recipient_name=customer.get("name"),
            phone=customer.get("phone"),
            address=customer.get("address"),
            postal_code=customer.get("postalCode"),
            state=customer.get("state") or customer.get("city"),
            label=customer.get("defaultShippingAddressLabel") or "Principal",
            address_id=default_id or "default",
            is_default=True,
            created_at=customer.get("createdAt"),
            updated_at=customer.get("updatedAt"),
        )
        if legacy:
            addresses.append(legacy)

    if default_id:
        matched = False
        for entry in addresses:
            is_default = _clean_str(entry.get("addressId")) == default_id
            entry["isDefault"] = is_default
            matched = matched or is_default
        if not matched and addresses:
            addresses[0]["isDefault"] = True
    elif addresses and not any(bool(entry.get("isDefault")) for entry in addresses):
        addresses[0]["isDefault"] = True

    addresses.sort(key=lambda entry: 0 if entry.get("isDefault") else 1)
    _address_log(
        "normalize_addresses.result",
        customerId=customer.get("customerId"),
        defaultAddressId=default_id,
        count=len(addresses),
        addresses=[_address_snapshot_for_log(entry) for entry in addresses],
    )
    return addresses

def _set_customer_addresses_fields(item: dict, addresses: List[dict]) -> dict:
    if not isinstance(item, dict):
        return item
    if not addresses:
        item.pop("addresses", None)
        item.pop("shippingAddresses", None)
        item.pop("defaultAddressId", None)
        item.pop("defaultShippingAddressId", None)
        return item

    item["addresses"] = addresses
    item["defaultAddressId"] = addresses[0].get("addressId")
    # Transitional aliases while frontend/backend code paths converge.
    item["shippingAddresses"] = addresses
    item["defaultShippingAddressId"] = addresses[0].get("addressId")
    return item

def _default_shipping_address(customer: Optional[dict]) -> Optional[dict]:
    addresses = _normalize_customer_shipping_addresses(customer)
    return addresses[0] if addresses else None

def _upsert_customer_shipping_address(
    customer: Optional[dict],
    payload: dict,
    persist_address: bool = False,
) -> Tuple[List[dict], Optional[dict]]:
    addresses = _normalize_customer_shipping_addresses(customer)
    snapshot = _shipping_address_from_payload(payload)
    if not snapshot:
        _address_log(
            "upsert.skip_no_snapshot",
            customerId=(customer or {}).get("customerId") if isinstance(customer, dict) else None,
            persistAddress=persist_address,
        )
        return addresses, None

    shipping_address = payload.get("shippingAddress") if isinstance(payload.get("shippingAddress"), dict) else {}
    requested_id = _clean_str(payload.get("shippingAddressId") or shipping_address.get("addressId") or shipping_address.get("id"))
    save_address = persist_address or _truthy_flag(payload.get("saveShippingAddress"), default=False)
    _address_log(
        "upsert.start",
        customerId=(customer or {}).get("customerId") if isinstance(customer, dict) else None,
        requestedId=requested_id,
        saveAddress=save_address,
        persistAddress=persist_address,
        currentCount=len(addresses),
        snapshot=_address_snapshot_for_log(snapshot),
    )

    existing = next((entry for entry in addresses if _clean_str(entry.get("addressId")) == requested_id), None) if requested_id else None
    if existing and not snapshot.get("label"):
        snapshot["label"] = existing.get("label") or ""

    if not save_address:
        _address_log(
            "upsert.snapshot_only",
            customerId=(customer or {}).get("customerId") if isinstance(customer, dict) else None,
            requestedId=requested_id,
            snapshot=_address_snapshot_for_log(snapshot),
        )
        return addresses, snapshot

    now = _now_iso()
    match_index = None
    if requested_id:
        for idx, entry in enumerate(addresses):
            if _clean_str(entry.get("addressId")) == requested_id:
                match_index = idx
                break

    if match_index is None:
        for idx, entry in enumerate(addresses):
            if (
                _clean_str(entry.get("address")) == _clean_str(snapshot.get("address"))
                and _clean_str(entry.get("postalCode")) == _clean_str(snapshot.get("postalCode"))
                and _clean_str(entry.get("state")) == _clean_str(snapshot.get("state"))
                and _clean_str(entry.get("recipientName")) == _clean_str(snapshot.get("recipientName"))
                and _clean_str(entry.get("phone")) == _clean_str(snapshot.get("phone"))
            ):
                match_index = idx
                break

    if match_index is not None:
        current = addresses[match_index]
        saved = {
            **current,
            **snapshot,
            "addressId": _clean_str(current.get("addressId")) or requested_id or f"ADDR-{uuid.uuid4().hex[:10].upper()}",
            "label": _clean_str(snapshot.get("label")) or _clean_str(current.get("label")) or f"Direccion {match_index + 1}",
            "isDefault": True,
            "createdAt": current.get("createdAt") or now,
            "updatedAt": now,
        }
        addresses[match_index] = saved
    else:
        saved = {
            **snapshot,
            "addressId": requested_id or f"ADDR-{uuid.uuid4().hex[:10].upper()}",
            "label": _clean_str(snapshot.get("label")) or f"Direccion {len(addresses) + 1}",
            "isDefault": True,
            "createdAt": now,
            "updatedAt": now,
        }
        addresses.insert(0, saved)

    saved_id = _clean_str(saved.get("addressId"))
    for entry in addresses:
        entry["isDefault"] = _clean_str(entry.get("addressId")) == saved_id
    addresses.sort(key=lambda entry: 0 if entry.get("isDefault") else 1)
    _address_log(
        "upsert.result",
        customerId=(customer or {}).get("customerId") if isinstance(customer, dict) else None,
        requestedId=requested_id,
        matchIndex=match_index,
        saved=_address_snapshot_for_log(saved),
        count=len(addresses),
        addresses=[_address_snapshot_for_log(entry) for entry in addresses],
    )
    return addresses, saved

def _ensure_customer_shell_record(customer_id: Any, customer_name: str, payload: dict, now_iso: Optional[str] = None) -> Optional[dict]:
    entity_id = _customer_entity_id(customer_id)
    if entity_id is None:
        _address_log("ensure_customer_shell.invalid_id", customerId=customer_id)
        return None

    existing = _get_by_id("CUSTOMER", entity_id)
    if existing:
        _address_log(
            "ensure_customer_shell.exists",
            customerId=entity_id,
            address=_address_snapshot_for_log(existing),
            defaultAddressId=existing.get("defaultAddressId"),
            count=len(existing.get("addresses") or existing.get("shippingAddresses") or []),
        )
        return existing

    now = now_iso or _now_iso()
    fallback_email = f"{entity_id}@placeholder.local"
    item = {
        "entityType": "customer",
        "customerId": entity_id,
        "name": _clean_str(customer_name) or _clean_str(payload.get("recipientName")) or "Cliente",
        "email": _normalize_email(payload.get("email")) or fallback_email,
        "phone": payload.get("phone"),
        "address": payload.get("address"),
        "city": payload.get("state"),
        "leaderId": None,
        "isAssociate": True,
        "canAccessAdmin": False,
        "privileges": _normalize_privileges(None),
        "activeBuyer": False,
        "discountRate": D_ZERO,
        "discount": "0%",
        "commissions": D_ZERO,
        "createdAt": now,
        "updatedAt": now,
    }
    shipping_addresses = _normalize_customer_shipping_addresses(item)
    _set_customer_addresses_fields(item, shipping_addresses)
    _address_log(
        "ensure_customer_shell.create",
        customerId=entity_id,
        itemAddress=_address_snapshot_for_log(item),
        count=len(shipping_addresses),
        addresses=[_address_snapshot_for_log(entry) for entry in shipping_addresses],
    )
    return _put_entity("CUSTOMER", entity_id, item, created_at_iso=now)

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

    # Si es guest, también incluye referrer (si existe)
    
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
    
    shipping_address = payload.get("shippingAddress") if isinstance(payload.get("shippingAddress"), dict) else {}
    address = _clean_str(payload.get("address") or shipping_address.get("address"))
    postal_code = _clean_str(payload.get("postalCode") or shipping_address.get("postalCode"))
    state = _clean_str(payload.get("state") or shipping_address.get("state") or shipping_address.get("city"))
    phone = _clean_str(payload.get("phone") or shipping_address.get("phone"))
    recipient_name = _clean_str(payload.get("recipientName") or shipping_address.get("recipientName"))
    shipping_address_label = _clean_str(payload.get("shippingAddressLabel") or shipping_address.get("label"))
    shipping_address_id = _clean_str(payload.get("shippingAddressId") or shipping_address.get("addressId") or shipping_address.get("id"))

    buyer_type = (payload.get("buyerType") or ("guest" if not customer_id else "registered")).lower()
    order_id = _generate_order_id()
    now = _now_iso()
    month_key = _month_key()
    print(
        f"[order][create][start] order_id={order_id} customer_id={customer_id} "
        f"buyer_type={buyer_type} items_count={len(items)}"
    )
    _address_log(
        "create_order.input",
        orderId=order_id,
        customerIdRaw=customer_id,
        customerName=customer_name,
        buyerType=buyer_type,
        itemCount=len(items),
        shippingAddress=_address_snapshot_for_log(shipping_address),
        directAddress={
            "recipientName": recipient_name,
            "phone": phone,
            "address": address,
            "postalCode": postal_code,
            "state": state,
            "shippingAddressId": shipping_address_id,
            "shippingAddressLabel": shipping_address_label,
            "saveShippingAddress": payload.get("saveShippingAddress"),
        },
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

    cid_val = _customer_entity_id(customer_id)
    _address_log("create_order.customer_id", orderId=order_id, customerIdRaw=customer_id, customerIdNormalized=cid_val)
    customer_item = _get_by_id("CUSTOMER", cid_val) if cid_val is not None else None
    _address_log(
        "create_order.customer_lookup",
        orderId=order_id,
        customerIdNormalized=cid_val,
        found=bool(customer_item),
        customerAddress=_address_snapshot_for_log(customer_item),
        defaultAddressId=customer_item.get("defaultAddressId") if isinstance(customer_item, dict) else None,
        addressCount=len((customer_item or {}).get("addresses") or (customer_item or {}).get("shippingAddresses") or []) if isinstance(customer_item, dict) else 0,
    )
    if customer_item is None and cid_val is not None and buyer_type in {"registered", "associate"}:
        customer_item = _ensure_customer_shell_record(cid_val, customer_name, payload, now_iso=now)
        _address_log(
            "create_order.customer_shell_result",
            orderId=order_id,
            customerIdNormalized=cid_val,
            created=bool(customer_item),
            customerAddress=_address_snapshot_for_log(customer_item),
            defaultAddressId=customer_item.get("defaultAddressId") if isinstance(customer_item, dict) else None,
            addressCount=len((customer_item or {}).get("addresses") or (customer_item or {}).get("shippingAddresses") or []) if isinstance(customer_item, dict) else 0,
        )
    shipping_addresses_to_save, persisted_shipping_address = _upsert_customer_shipping_address(
        customer_item,
        payload,
        persist_address=cid_val is not None,
    )
    shipping_snapshot = persisted_shipping_address or _shipping_address_from_payload(payload)
    default_shipping_address = _default_shipping_address(customer_item)
    _address_log(
        "create_order.address_after_upsert",
        orderId=order_id,
        customerIdNormalized=cid_val,
        persistedShippingAddress=_address_snapshot_for_log(persisted_shipping_address),
        shippingSnapshot=_address_snapshot_for_log(shipping_snapshot),
        defaultShippingAddress=_address_snapshot_for_log(default_shipping_address),
        addressCount=len(shipping_addresses_to_save),
        addresses=[_address_snapshot_for_log(entry) for entry in shipping_addresses_to_save],
    )
    if not shipping_snapshot and default_shipping_address:
        shipping_snapshot = {
            "addressId": default_shipping_address.get("addressId"),
            "label": default_shipping_address.get("label") or "",
            "recipientName": default_shipping_address.get("recipientName") or "",
            "phone": default_shipping_address.get("phone") or "",
            "address": default_shipping_address.get("address") or "",
            "postalCode": default_shipping_address.get("postalCode") or "",
            "state": default_shipping_address.get("state") or "",
            "isDefault": bool(default_shipping_address.get("isDefault")),
        }
    if shipping_snapshot:
        shipping_address_id = _clean_str(
            persisted_shipping_address.get("addressId") if persisted_shipping_address else shipping_address_id or shipping_snapshot.get("addressId")
        )
        shipping_address_label = _clean_str(shipping_snapshot.get("label")) or shipping_address_label
    _address_log(
        "create_order.address_final",
        orderId=order_id,
        customerIdNormalized=cid_val,
        shippingSnapshot=_address_snapshot_for_log(shipping_snapshot),
        shippingAddressId=shipping_address_id,
        shippingAddressLabel=shipping_address_label,
    )

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

    if shipping_snapshot:
        order_item["shippingAddress"] = shipping_snapshot
        if shipping_address_id:
            order_item["shippingAddressId"] = shipping_address_id
        if shipping_address_label:
            order_item["shippingAddressLabel"] = shipping_address_label
        if shipping_snapshot.get("recipientName"):
            order_item["recipientName"] = shipping_snapshot.get("recipientName")
        if shipping_snapshot.get("phone"):
            order_item["phone"] = shipping_snapshot.get("phone")
        if shipping_snapshot.get("address"):
            order_item["address"] = shipping_snapshot.get("address")
        if shipping_snapshot.get("postalCode"):
            order_item["postalCode"] = shipping_snapshot.get("postalCode")
        if shipping_snapshot.get("state"):
            order_item["state"] = shipping_snapshot.get("state")
    
    # Optional fields
    for field in ["shippingType", "trackingNumber", "deliveryPlace", "deliveryDate", "recipientName", "phone", "address", "postalCode", "state"]:
        val = payload.get(field)
        if val:
            order_item[field] = val.strip() if isinstance(val, str) else val

    _address_log(
        "create_order.order_item_before_put",
        orderId=order_id,
        customerIdNormalized=cid_val,
        orderAddress=_address_snapshot_for_log(order_item.get("shippingAddress") or order_item),
        shippingAddressId=order_item.get("shippingAddressId"),
        shippingAddressLabel=order_item.get("shippingAddressLabel"),
    )
    main = _put_entity("ORDER", order_id, order_item, created_at_iso=now)
    print(
        f"[order][create][ok] order_id={order_id} status={order_item.get('status')} "
        "mercadopago_flow=not_started"
    )
    _address_log(
        "create_order.order_saved",
        orderId=order_id,
        customerIdNormalized=cid_val,
        orderAddress=_address_snapshot_for_log(main.get("shippingAddress") or main),
        shippingAddressId=main.get("shippingAddressId"),
        shippingAddressLabel=main.get("shippingAddressLabel"),
    )
    
    # Update customer profile address if applicable
    if cid_val is not None:
        updates = []
        eav = {":u": now}
        ean = {}
        selected_shipping_address = persisted_shipping_address if persisted_shipping_address else None
        if selected_shipping_address:
            if selected_shipping_address.get("address"): updates.append("address = :a"); eav[":a"] = selected_shipping_address.get("address")
            if selected_shipping_address.get("state"):
                updates.append("#state = :st")
                eav[":st"] = selected_shipping_address.get("state")
                ean["#state"] = "state"
            if selected_shipping_address.get("postalCode"): updates.append("postalCode = :pc"); eav[":pc"] = selected_shipping_address.get("postalCode")
            if selected_shipping_address.get("phone"): updates.append("phone = :ph"); eav[":ph"] = selected_shipping_address.get("phone")
            if selected_shipping_address.get("addressId"):
                updates.append("defaultAddressId = :dsa")
                updates.append("defaultShippingAddressId = :dsa")
                eav[":dsa"] = selected_shipping_address.get("addressId")
            if shipping_addresses_to_save:
                updates.append("addresses = :sa")
                updates.append("shippingAddresses = :sa")
                eav[":sa"] = shipping_addresses_to_save
        else:
            if address: updates.append("address = :a"); eav[":a"] = address
            if state:
                updates.append("#state = :st")
                eav[":st"] = state
                ean["#state"] = "state"
            if postal_code: updates.append("postalCode = :pc"); eav[":pc"] = postal_code
            if phone: updates.append("phone = :ph"); eav[":ph"] = phone
        
        if updates:
            update_expression = "SET " + ", ".join(updates) + ", updatedAt = :u"
            _address_log(
                "create_order.customer_update.prepared",
                orderId=order_id,
                customerIdNormalized=cid_val,
                updateExpression=update_expression,
                expressionAttributeValues=eav,
                expressionAttributeNames=ean,
            )
            try:
                customer_updated = _update_by_id("CUSTOMER", cid_val, update_expression, eav, ean=ean or None)
                _address_log(
                    "create_order.customer_update.ok",
                    orderId=order_id,
                    customerIdNormalized=cid_val,
                    customerAddress=_address_snapshot_for_log(customer_updated),
                    defaultAddressId=customer_updated.get("defaultAddressId"),
                    defaultShippingAddressId=customer_updated.get("defaultShippingAddressId"),
                    addressCount=len(customer_updated.get("addresses") or customer_updated.get("shippingAddresses") or []),
                )
                customer_reloaded = _get_by_id("CUSTOMER", cid_val)
                _address_log(
                    "create_order.customer_update.reload",
                    orderId=order_id,
                    customerIdNormalized=cid_val,
                    found=bool(customer_reloaded),
                    customerAddress=_address_snapshot_for_log(customer_reloaded),
                    defaultAddressId=customer_reloaded.get("defaultAddressId") if isinstance(customer_reloaded, dict) else None,
                    defaultShippingAddressId=customer_reloaded.get("defaultShippingAddressId") if isinstance(customer_reloaded, dict) else None,
                    addressCount=len((customer_reloaded or {}).get("addresses") or (customer_reloaded or {}).get("shippingAddresses") or []) if isinstance(customer_reloaded, dict) else 0,
                )
            except Exception as exc:
                _address_log(
                    "create_order.customer_update.error",
                    orderId=order_id,
                    customerIdNormalized=cid_val,
                    error=str(exc),
                    updateExpression=update_expression,
                    expressionAttributeValues=eav,
                )
                pass
        else:
            _address_log(
                "create_order.customer_update.skipped",
                orderId=order_id,
                customerIdNormalized=cid_val,
                reason="no_updates",
                selectedShippingAddress=_address_snapshot_for_log(selected_shipping_address),
                directAddress={
                    "phone": phone,
                    "address": address,
                    "postalCode": postal_code,
                    "state": state,
                },
            )
    else:
        _address_log("create_order.customer_update.skipped", orderId=order_id, customerIdNormalized=cid_val, reason="customer_id_missing")
                
    _audit_event("order.create", headers, payload, {"orderId": order_id, "customerId": customer_id})
    return _json_response(201, {"order": main})

def _find_order(order_id: str) -> Optional[dict]:
    return _get_by_id("ORDER", order_id)

def _apply_rewards_on_paid_order(order_item: dict) -> dict:
    """
    NUEVO COMPORTAMIENTO (paid):
    - Por cada beneficiario, crea o actualiza el item COMMISSION_MONTH (PK fijo, SK por beneficiary+month).
    - Inserta/reemplaza (idempotente) la fila del ledger que corresponde a esta orden (rowId determiní­stico).
    - Recalcula totalPending/totalConfirmed SIEMPRE a partir del ledger (no incrementos).
    - NO confirma pagos aquí­ (siguen como 'pending'); eso pasa en delivered.
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

        # No existí­a, agrega
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

    # Si es guest + referrer: comisión one-shot (solo referrer)
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
        "commissionsPaid": [],  # ya no "pagas" aquí­, solo generas ledger en pending
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
        "shippingAddressId": updated.get("shippingAddressId"),
        "shippingAddressLabel": updated.get("shippingAddressLabel"),
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
    return _campaign_service.campaign_payload(item)


def _save_campaign(payload: dict, headers: Optional[dict] = None) -> dict:
    return _campaign_service.save_campaign(payload, headers=headers)


def _list_campaigns() -> List[dict]:
    return _campaign_service.list_campaigns()


def _list_active_campaigns() -> List[dict]:
    return _campaign_service.list_active_campaigns()

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
    shipping_addresses = _normalize_customer_shipping_addresses(item)
    _set_customer_addresses_fields(item, shipping_addresses)
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
        return _json_response(200, {"message": "Las contraseñas no coinciden", "Error": "BadRequest"})

    email_norm = _normalize_email(email)
    if not email_norm:
        return _json_response(200, {"message": "email invalido", "Error": "BadRequest"})
    if _get_auth_by_email(email_norm) or _find_customer_by_email(email_norm):
        return _json_response(200, {"message": "El correo ya esta registrado. Intenta usar recuperar contrasena.", "Error": "Conflict"})

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
    shipping_addresses = _normalize_customer_shipping_addresses(item)
    _set_customer_addresses_fields(item, shipping_addresses)
    
    main = _put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    _create_auth_record(email_norm, password_hash, customer_id, role="cliente")
    try:
        _send_welcome_email(name, email_norm)
    except Exception as exc:
        print(f"[create-account] welcome email failed: {exc}")
    if leader_id not in (None, ""):
        try:
            sponsor = _get_by_id("CUSTOMER", int(leader_id))
            if sponsor:
                _send_network_join_email(sponsor, main)
        except Exception as exc:
            print(f"[create-account] network join email failed: {exc}")
    
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
    entity_id = _customer_entity_id(customer_id)
    item = _get_by_id("CUSTOMER", entity_id) if entity_id is not None else None
    if not item:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    customer_payload = dict(item)
    shipping_addresses = _normalize_customer_shipping_addresses(item)
    customer_payload["addresses"] = shipping_addresses
    customer_payload["shippingAddresses"] = shipping_addresses
    if shipping_addresses:
        default_shipping = shipping_addresses[0]
        customer_payload["defaultAddressId"] = default_shipping.get("addressId")
        customer_payload["defaultShippingAddressId"] = default_shipping.get("addressId")
    return _json_response(200, {"customer": customer_payload})

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
        "SET canAccessAdmin = :ca, #pr = :pr, updatedAt = :u",
        {":ca": can_access_admin, ":pr": privileges, ":u": _now_iso()},
        ean={"#pr": "privileges"},
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

def _update_customer(customer_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    cid = int(customer_id)
    customer = _get_by_id("CUSTOMER", cid)
    if not customer:
        return _json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

    customers_raw = _query_bucket("CUSTOMER")
    updates = ["updatedAt = :u"]
    eav: dict = {":u": _now_iso()}
    ean: dict = {}
    leader_changed = False
    next_leader_id = customer.get("leaderId")

    if "leaderId" in payload:
        raw_leader_id = payload.get("leaderId")
        if raw_leader_id in ("", None):
            resolved_leader_id = None
        else:
            resolved_leader_id = _resolve_leader_id(raw_leader_id)
            if resolved_leader_id is None:
                return _json_response(200, {"message": "Patrocinador no encontrado", "Error": "BadRequest"})
        if resolved_leader_id == cid:
            return _json_response(200, {"message": "Un usuario no puede ser su propio patrocinador", "Error": "BadRequest"})
        if _would_create_leader_cycle(customers_raw, cid, resolved_leader_id):
            return _json_response(200, {"message": "El cambio generaria un ciclo en la red", "Error": "BadRequest"})
        next_leader_id = resolved_leader_id
        if next_leader_id != customer.get("leaderId"):
            updates.append("leaderId = :lid")
            eav[":lid"] = next_leader_id
            leader_changed = True

    if "level" in payload:
        updates.append("#lvl = :lvl")
        ean["#lvl"] = "level"
        eav[":lvl"] = (payload.get("level") or "").strip()

    if len(updates) <= 1:
        return _json_response(200, {"message": "Sin cambios para actualizar", "Error": "BadRequest"})

    updated = _update_by_id("CUSTOMER", cid, "SET " + ", ".join(updates), eav, ean=ean if ean else None)

    if leader_changed and next_leader_id not in (None, ""):
        try:
            sponsor = _get_by_id("CUSTOMER", int(next_leader_id))
            if sponsor:
                _send_network_join_email(sponsor, updated)
        except Exception as exc:
            print(f"[customer.update] network join email failed: {exc}")

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
    _audit_event("customer.update", headers, payload, {"customerId": cid, "leaderId": next_leader_id})
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
        "shippingAddressId": item.get("shippingAddressId"),
        "shippingAddressLabel": item.get("shippingAddressLabel"),
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

def _product_display_name(product_id: Any) -> str:
    product_key = _parse_int_or_str(product_id)
    if product_key in (None, ""):
        return "producto"
    product = _get_by_id("PRODUCT", int(product_key)) if isinstance(product_key, int) else _get_by_id("PRODUCT", product_key)
    product_name = (product or {}).get("name") if isinstance(product, dict) else None
    return str(product_name or product_id).strip() or "producto"

def _stock_insufficient_message(product_id: Any) -> str:
    return f"Stock insuficiente para {_product_display_name(product_id)}"

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
            return None, _stock_insufficient_message(pid)
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
            return _json_response(200, {"message": _stock_insufficient_message(pid_key), "Error": "BadRequest"})
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
        "customerId": item.get("customerId"),
        "customerName": item.get("customerName"),
        "paymentStatus": item.get("paymentStatus"),
        "deliveryStatus": item.get("deliveryStatus"),
        "grossSubtotal": float(_to_decimal(item.get("grossSubtotal"))),
        "discountRate": float(_to_decimal(item.get("discountRate"))),
        "discountAmount": float(_to_decimal(item.get("discountAmount"))),
        "total": float(_to_decimal(item.get("total"))),
        "lines": item.get("lines") or [],
        "createdAt": item.get("createdAt"),
    }

def _pos_cash_cut_payload(item: dict) -> dict:
    return {
        "id": item.get("cashCutId"),
        "stockId": item.get("stockId"),
        "attendantUserId": item.get("attendantUserId"),
        "total": float(_to_decimal(item.get("total"))),
        "salesCount": int(item.get("salesCount") or 0),
        "startedAt": item.get("startedAt"),
        "endedAt": item.get("endedAt"),
        "createdAt": item.get("createdAt"),
    }

def _resolve_pos_operator_and_stock(stock_candidate: Any, headers: Optional[dict], payload: Optional[dict] = None) -> Tuple[Optional[int], Optional[dict], Optional[str]]:
    actor_user_id, _, _ = _resolve_actor(headers, payload or {})
    try:
        attendant_user_id = int(actor_user_id)
    except Exception:
        return None, None, "Se requiere un usuario logeado para operar POS"

    linked_stocks = [
        stock
        for stock in _query_bucket("STOCK")
        if attendant_user_id in _normalize_user_ids(stock.get("linkedUserIds"))
    ]
    if not linked_stocks:
        return attendant_user_id, None, "El usuario logeado no tiene un stock vinculado"

    requested_stock_id = _stock_id(stock_candidate)
    if not requested_stock_id:
        return attendant_user_id, linked_stocks[0], None

    selected_stock = next((stock for stock in linked_stocks if _stock_id(stock.get("stockId")) == requested_stock_id), None)
    if not selected_stock:
        return attendant_user_id, None, "El stock no esta vinculado al usuario logeado"

    return attendant_user_id, selected_stock, None

def _last_pos_cash_cut(stock_id: str, attendant_user_id: int) -> Optional[dict]:
    cuts = [
        item
        for item in _query_bucket("POS_CASH_CUT")
        if _stock_id(item.get("stockId")) == _stock_id(stock_id) and _parse_int_or_str(item.get("attendantUserId")) == attendant_user_id
    ]
    if not cuts:
        return None
    cuts.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
    return cuts[0]

def _build_pos_cash_control(stock_id: str, attendant_user_id: int) -> dict:
    last_cut = _last_pos_cash_cut(stock_id, attendant_user_id)
    last_cut_at = str(last_cut.get("createdAt") or "") if isinstance(last_cut, dict) else ""
    sales = [
        item
        for item in _query_bucket("POS_SALE")
        if _stock_id(item.get("stockId")) == _stock_id(stock_id)
        and _parse_int_or_str(item.get("attendantUserId")) == attendant_user_id
        and (not last_cut_at or str(item.get("createdAt") or "") > last_cut_at)
    ]
    sales.sort(key=lambda item: str(item.get("createdAt") or ""))
    current_total = sum((_to_decimal(item.get("total")) for item in sales), D_ZERO)
    return {
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "currentTotal": float(current_total),
        "salesCount": len(sales),
        "startedAt": sales[0].get("createdAt") if sales else (last_cut.get("createdAt") if isinstance(last_cut, dict) else None),
        "lastCutAt": last_cut.get("createdAt") if isinstance(last_cut, dict) else None,
        "lastCutTotal": float(_to_decimal(last_cut.get("total"))) if isinstance(last_cut, dict) else 0.0,
        "lastCutSalesCount": int(last_cut.get("salesCount") or 0) if isinstance(last_cut, dict) else 0,
        "lastSaleAt": sales[-1].get("createdAt") if sales else None,
    }

def _get_pos_cash_control(query: dict, headers: Optional[dict] = None) -> dict:
    attendant_user_id, stock, error = _resolve_pos_operator_and_stock(query.get("stockId"), headers, query)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})
    stock_id = _stock_id(stock.get("stockId"))
    control = _build_pos_cash_control(stock_id, attendant_user_id)
    return _json_response(200, {"control": control})

def _create_pos_cash_cut(payload: dict, headers: Optional[dict] = None) -> dict:
    attendant_user_id, stock, error = _resolve_pos_operator_and_stock(payload.get("stockId"), headers, payload)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    stock_id = _stock_id(stock.get("stockId"))
    control = _build_pos_cash_control(stock_id, attendant_user_id)
    if control.get("salesCount", 0) <= 0 or _to_decimal(control.get("currentTotal")) <= 0:
        return _json_response(200, {"message": "No hay ventas pendientes para corte", "Error": "BadRequest"})

    now = _now_iso()
    cut_id = _stock_id(payload.get("cashCutId") or f"CUT-{uuid.uuid4().hex[:10].upper()}")
    cut_item = {
        "entityType": "posCashCut",
        "cashCutId": cut_id,
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "total": _to_decimal(control.get("currentTotal")),
        "salesCount": int(control.get("salesCount") or 0),
        "startedAt": control.get("startedAt"),
        "endedAt": now,
        "createdAt": now,
        "updatedAt": now,
    }
    main = _put_entity("POS_CASH_CUT", cut_id, cut_item, created_at_iso=now)
    next_control = _build_pos_cash_control(stock_id, attendant_user_id)
    _audit_event("pos.cash.cut", headers, payload, {"cashCutId": cut_id, "stockId": stock_id, "attendantUserId": attendant_user_id})
    return _json_response(201, {"cut": _pos_cash_cut_payload(main), "control": next_control})

def _register_pos_sale(payload: dict, headers: Optional[dict] = None) -> dict:
    app_cfg = _load_app_config()
    pos_cfg = app_cfg.get("pos") if isinstance(app_cfg, dict) else {}
    attendant_user_id, stock, stock_error = _resolve_pos_operator_and_stock(payload.get("stockId"), headers, payload)
    if stock_error:
        return _json_response(200, {"message": stock_error, "Error": "BadRequest"})
    stock_id = _stock_id(stock.get("stockId"))

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

    month_key = _month_key()
    customer_id = _parse_int_or_str(payload.get("customerId"))
    customer = None
    if customer_id is not None:
        customer = _get_by_id("CUSTOMER", int(customer_id)) if isinstance(customer_id, int) else _get_by_id("CUSTOMER", customer_id)
        if not customer:
            return _json_response(200, {"message": "Cliente no encontrado", "Error": "NoEncontrado"})

    updated_stock, error = _apply_stock_delta(stock_id, deltas)
    if error:
        return _json_response(200, {"message": error, "Error": "BadRequest"})

    now = _now_iso()
    sale_id = _stock_id(payload.get("saleId") or f"SALE-{uuid.uuid4().hex[:10].upper()}")
    order_id = _stock_id(payload.get("orderId") or f"POS-{uuid.uuid4().hex[:10].upper()}")
    buyer_type = "guest"
    if customer:
        buyer_type = "associate" if bool(customer.get("isAssociate", True)) else "registered"

    gross_subtotal = total.quantize(D_CENT)
    discount_rate = _effective_discount_rate_for_order(
        buyer_id=customer_id,
        buyer_type=buyer_type,
        gross_subtotal=gross_subtotal,
        month_key=month_key,
        tiers=((app_cfg.get("rewards") or {}).get("discountTiers") or []),
        current_order_rate=D_ZERO,
    ) if customer else D_ZERO
    discount_amount = (gross_subtotal * discount_rate).quantize(D_CENT)
    net_total = (gross_subtotal - discount_amount).quantize(D_CENT)
    customer_name = (
        customer.get("name")
        if customer
        else (payload.get("customerName") or pos_cfg.get("defaultCustomerName") or "Publico en General").strip() or "Publico en General"
    )
    sale_item = {
        "entityType": "posSale",
        "saleId": sale_id,
        "orderId": order_id,
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "customerId": customer_id,
        "customerName": customer_name,
        "paymentStatus": payload.get("paymentStatus") or pos_cfg.get("defaultPaymentStatus") or "paid_branch",
        "deliveryStatus": payload.get("deliveryStatus") or pos_cfg.get("defaultDeliveryStatus") or "delivered_branch",
        "grossSubtotal": gross_subtotal,
        "discountRate": discount_rate,
        "discountAmount": discount_amount,
        "total": net_total,
        "lines": lines,
        "createdAt": now,
        "updatedAt": now,
    }

    status_by_delivery = pos_cfg.get("orderStatusByDeliveryStatus") if isinstance(pos_cfg.get("orderStatusByDeliveryStatus"), dict) else {}
    order_status = str(status_by_delivery.get(sale_item.get("deliveryStatus")) or "")
    if order_status not in {"pending", "paid", "shipped", "delivered", "canceled", "refunded"}:
        order_status = "delivered" if sale_item.get("deliveryStatus") == "delivered_branch" else "paid"
    order_item = {
        "entityType": "order",
        "orderId": order_id,
        "customerId": customer_id,
        "customerName": sale_item.get("customerName"),
        "buyerType": buyer_type,
        "status": order_status,
        "items": lines,
        "grossSubtotal": gross_subtotal,
        "discountRate": discount_rate,
        "discountAmount": discount_amount,
        "netTotal": net_total,
        "total": net_total,
        "monthKey": month_key,
        "shippingType": "personal",
        "deliveryPlace": f"Sucursal: {stock_id}",
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "paymentStatus": sale_item.get("paymentStatus"),
        "deliveryStatus": sale_item.get("deliveryStatus"),
        "createdAt": now,
        "updatedAt": now,
    }
    stored_order = _put_entity("ORDER", order_id, order_item, created_at_iso=now)
    if customer and order_status in {"paid", "delivered"}:
        _apply_rewards_on_paid_order(stored_order)
        stored_order = _find_order(order_id) or stored_order
        if order_status == "delivered":
            try:
                _confirm_order_commissions(stored_order)
            except Exception:
                pass
            stored_order = _find_order(order_id) or stored_order

    sale = _put_entity("POS_SALE", sale_id, sale_item, created_at_iso=now)

    movements = []
    for line in lines:
        movements.append(
            _movement_payload(
                _create_inventory_movement(
                    movement_type="pos_sale",
                    stock_id=stock_id,
                    product_id=line.get("productId"),
                    qty=int(line.get("quantity") or 0),
                    user_id=attendant_user_id,
                    reference_id=order_id,
                )
            )
        )
    _audit_event(
        "pos.sale.register",
        headers,
        payload,
        {"saleId": sale_id, "orderId": order_id, "stockId": stock_id, "attendantUserId": attendant_user_id, "customerId": customer_id},
    )
    return _json_response(201, {"sale": _pos_sale_payload(sale), "order": stored_order, "stock": _stock_payload(updated_stock), "movements": movements})

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
    return _config_service.get_rewards_config_handler()


def _put_rewards_config(payload: dict, headers: Optional[dict] = None) -> dict:
    return _config_service.put_rewards_config(payload, headers=headers)


def _get_app_config_handler() -> dict:
    return _config_service.get_app_config_handler()


def _put_app_config(payload: dict, headers: Optional[dict] = None) -> dict:
    return _config_service.put_app_config(payload, headers=headers)

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
# Notifications
# ---------------------------------------------------------------------------
_notification_service = NotificationService(
    default_link_text=NOTIFICATION_LINK_TEXT_DEFAULT,
    max_description_length=MAX_NOTIFICATION_DESCRIPTION_LENGTH,
    utc_now=_utc_now,
    iso_to_dt=_iso_to_dt,
    now_iso=_now_iso,
    json_response=_json_response,
    query_bucket=_query_bucket,
    query_exact_pk=_query_exact_pk,
    resolve_actor=_resolve_actor,
    get_by_id=_get_by_id,
    put_entity=_put_entity,
    audit_event=_audit_event,
    parse_int_or_str=_parse_int_or_str,
    table=_table,
)

_campaign_service = CampaignService(
    now_iso=_now_iso,
    json_response=_json_response,
    query_bucket=_query_bucket,
    get_by_id=_get_by_id,
    put_entity=_put_entity,
    update_by_id=_update_by_id,
    audit_event=_audit_event,
)

_user_dashboard_service = UserDashboardService(
    to_decimal=_to_decimal,
    decimal_one=D_ONE,
    default_sponsor_name=DEFAULT_SPONSOR_NAME,
    default_sponsor_email=DEFAULT_SPONSOR_EMAIL,
    default_sponsor_phone=DEFAULT_SPONSOR_PHONE,
    get_by_id=_get_by_id,
    normalize_email=_normalize_email,
    normalize_asset_url=_normalize_asset_url,
    truthy_flag=_truthy_flag,
)

_admin_dashboard_service = AdminDashboardService(
    load_app_config=_load_app_config,
)


def _notification_reads_pk(customer_id: Any) -> str:
    return _notification_service.notification_reads_pk(customer_id)


def _notification_status(item: Optional[dict], now_dt: Optional[datetime] = None) -> str:
    return _notification_service.notification_status(item, now_dt=now_dt)


def _notification_payload(
    item: dict,
    *,
    read_at: Optional[str] = None,
    now_dt: Optional[datetime] = None,
) -> dict:
    return _notification_service.notification_payload(item, read_at=read_at, now_dt=now_dt)


def _list_notifications_for_admin() -> List[dict]:
    return _notification_service.list_notifications_for_admin()


def _notification_reads_for_customer(customer_id: Any) -> Dict[str, str]:
    return _notification_service.notification_reads_for_customer(customer_id)


def _active_notifications_for_customer(customer_id: Any) -> List[dict]:
    return _notification_service.active_notifications_for_customer(customer_id)


def _save_notification(payload: dict, headers: Optional[dict] = None) -> dict:
    return _notification_service.save_notification(payload, headers=headers)


def _mark_notification_read(notification_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
    return _notification_service.mark_notification_read(notification_id, payload, headers=headers)

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
    return _admin_dashboard_service.build_admin_warnings(
        paid_count,
        pending_count,
        commissions_count,
        pending_transfers_count,
        pos_sales_today_count,
    )

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
    receipts_raw = _query_bucket("COMMISSION_RECEIPT")
    commission_month_items = _query_exact_pk("COMMISSION_MONTH")
    pom_item = _get_product_of_month_item()
    product_of_month_id = int(pom_item.get("productId")) if pom_item and pom_item.get("productId") is not None else None

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

    commission_month_by_customer_month: Dict[str, dict] = {}
    for item in commission_month_items:
        beneficiary_id = item.get("beneficiaryId")
        month_key = item.get("monthKey")
        if beneficiary_id in (None, "") or not month_key:
            continue
        commission_month_by_customer_month[f"{beneficiary_id}#{month_key}"] = item

    customers, customers_by_level, commissions_count, commissions_total = (
        _admin_dashboard_service.transform_customers_for_admin(
            customers_raw,
            commission_month_by_customer_month,
            receipt_by_customer_month,
            prev_month_key,
            current_month_key,
            {},  # commissions_by_id not used in this path
        )
    )

    status_counts, sales_total, orders = (
        _admin_dashboard_service.transform_orders_for_admin(orders_raw)
    )

    active_products, products = (
        _admin_dashboard_service.transform_products_for_admin(products_raw)
    )

    campaigns = _list_campaigns()
    notifications = _list_notifications_for_admin()

    stock_transfers_raw = _query_bucket("STOCK_TRANSFER")
    pos_sales_raw = _query_bucket("POS_SALE")
    alerts_payload = _admin_dashboard_service.dashboard_alerts_payload(
        paid_count=status_counts["paid"],
        pending_count=status_counts["pending"],
        commissions_count=commissions_count,
        transfers_raw=stock_transfers_raw,
        pos_sales_raw=pos_sales_raw,
    )

    warnings = alerts_payload.get("warnings") or []

    return _json_response(200, {
        "kpis": _admin_dashboard_service.aggregate_kpis(
            customers, orders, active_products, commissions_total, sales_total
        ),
        "statusCounts": status_counts, "customersByLevel": customers_by_level,
        "warnings": warnings,
        "customers": customers, "orders": orders, "products": products, "campaigns": campaigns,
        "notifications": notifications,
        "productOfMonthId": product_of_month_id,
        "businessConfig": app_cfg,
    })

# ---------------------------------------------------------------------------
# User Dashboard
# ---------------------------------------------------------------------------
def _pick_product_image(images: Optional[list], preferred_sections: List[str]) -> str:
    return _user_dashboard_service.pick_product_image(images, preferred_sections)

def _get_product_of_month_item() -> Optional[dict]:
    return _get_by_id("PRODUCT_OF_MONTH", "current")

def _is_product_active(item: Optional[dict]) -> bool:
    return _user_dashboard_service.is_product_active(item)

def _get_product_summary(item: dict) -> dict:
    return _user_dashboard_service.product_summary(item)

def _set_product_of_month(payload: dict, headers: Optional[dict] = None) -> dict:
    pid = payload.get("productId") or payload.get("id")
    if not pid:
        return _json_response(200, {"message": "productId es obligatorio", "Error": "BadRequest"})

    product = _get_by_id("PRODUCT", int(pid))
    if not product:
        return _json_response(200, {"message": "Producto no encontrado", "Error": "NoEncontrado"})
    if not _is_product_active(product):
        return _json_response(200, {"message": "El producto retirado no puede ser producto del mes", "Error": "BadRequest"})

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

    products_raw = _query_bucket("PRODUCT")
    products, featured = _user_dashboard_service.build_products_payload(products_raw)
    campaigns = _list_active_campaigns()

    pom_item = _get_product_of_month_item()
    product_of_month = _user_dashboard_service.build_product_of_month_payload(pom_item)

    cfg = _load_rewards_config()
    month_key = _month_key()
    prev_month_key = _prev_month_key()

    # Pre-fetch customers only if needed for goals/tree
    customers_raw = _query_bucket("CUSTOMER") if customer else []
    print(customers_raw)
    computed_network, computed_goals = [], []
    commission_summary = None
    buy_again_ids = []
    active_notifications: List[dict] = []

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
        active_notifications = _active_notifications_for_customer(customer.get("customerId"))

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

    sponsor_payload = _user_dashboard_service.build_sponsor_payload(customer)
    user_payload = _user_dashboard_service.build_user_payload(customer)

    payload = {
        "isGuest": bool(is_guest),
        "settings": _user_dashboard_service.build_settings_payload(user_id, bool(is_guest)),
        "user": user_payload,
        "sponsor": sponsor_payload,
        "goals": computed_goals,
        "products": products, "featured": featured, "productOfMonth": product_of_month,
        "campaigns": campaigns,
        "notifications": active_notifications,
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
    if route_key == (1, "notifications", "POST"): return _save_notification(_parse_body(event), headers)
    if route_key == (1, "orders", "POST"): return _create_order(_parse_body(event), headers)
    if route_key == (1, "orders", "GET") and query.get("customerId"): return _list_orders_for_customer(query.get("customerId"))
    if route_key == (1, "customers", "POST"): return _create_customer(_parse_body(event), headers)
    if route_key == (1, "stocks", "GET"): return _list_stocks()
    if route_key == (1, "stocks", "POST"): return _create_stock(_parse_body(event), headers)
    if route_key == (1, "campaigns", "GET"): return _json_response(200, {"campaigns": _list_campaigns()})
    if route_key == (1, "notifications", "GET"): return _json_response(200, {"notifications": _list_notifications_for_admin()})
    if route_key == (1, "user-dashboard", "GET"): return _get_user_dashboard(query, headers)
    
    # 2 segments
    if route_key == (2, "password", "POST") and segments[1] == "recovery": return _request_password_recovery(_parse_body(event))
    if route_key == (2, "password", "POST") and segments[1] == "reset": return _reset_password(_parse_body(event))
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
    if route_key == (2, "customers", "PATCH"): return _update_customer(segments[1], _parse_body(event), headers)
    if route_key == (2, "customers", "POST") and segments[1] == "clabe": return _update_customer_clabe(_parse_body(event))
    if route_key == (2, "admin", "GET") and segments[1] == "dashboard": return _get_admin_dashboard()
    if route_key == (2, "stocks", "PATCH"): return _update_stock(segments[1], _parse_body(event), headers)
    if route_key == (2, "stocks", "GET") and segments[1] == "transfers": return _list_stock_transfers(query)
    if route_key == (2, "stocks", "POST") and segments[1] == "transfers": return _create_stock_transfer(_parse_body(event), headers)
    if route_key == (2, "stocks", "GET") and segments[1] == "movements": return _list_inventory_movements(query)
    if route_key == (2, "pos", "GET") and segments[1] == "sales": return _list_pos_sales(query)
    if route_key == (2, "pos", "GET") and segments[1] == "cash-control": return _get_pos_cash_control(query, headers)
    if route_key == (2, "pos", "POST") and segments[1] == "sales": return _register_pos_sale(_parse_body(event), headers)
    if route_key == (2, "pos", "POST") and segments[1] == "cash-cut": return _create_pos_cash_cut(_parse_body(event), headers)
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
    if route_key == (3, "notifications", "POST") and segments[2] == "read": return _mark_notification_read(segments[1], _parse_body(event), headers)

    # 4 segments
    if route_key == (4, "associates", "GET") and segments[2] == "month": return _get_associate_month(segments[1], segments[3])
    if route_key == (4, "stocks", "POST") and segments[1] == "transfers" and segments[3] == "receive":
        return _receive_stock_transfer(segments[2], _parse_body(event), headers)

    return _json_response(404, {"message": "Ruta no encontrada", "path": "/" + "/".join(segments), "Error": "NotFound"})
