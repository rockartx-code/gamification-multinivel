import base64
import hashlib
import json
import os
import time
import uuid
import functools
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Configuración Global (Extraída de Variables de Entorno)
# ---------------------------------------------------------------------------
TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")
_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

_table = _dynamodb.Table(TABLE_NAME)
_ddb_client = _table.meta.client
_ddb_serializer = TypeSerializer()
_ddb_deserializer = TypeDeserializer()

# Constantes de Negocio
D_ZERO = Decimal("0")
D_ONE = Decimal("1")
D_CENT = Decimal("0.01")
MAX_NETWORK_DEPTH = 3
NETWORK_TREE_ID = "customers"
NETWORK_TREE_ROOT_KEY = "__ROOT__"
NETWORK_TREE_SK = "TREE"

# ---------------------------------------------------------------------------
# Helpers de Tipos y JSON
# ---------------------------------------------------------------------------
def _to_decimal(n: Any) -> Decimal:
    if isinstance(n, Decimal): return n
    if n is None or n == "": return D_ZERO
    try:
        return Decimal(str(n))
    except:
        return D_ZERO

def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

def _cors_headers(content_type: Optional[str] = "application/json") -> dict:
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-User-Id,X-User-Name,X-User-Role",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers

def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(payload, default=_json_default),
    }

def _cors_preflight_response() -> dict:
    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({"ok": True}),
    }

def _parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body: return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except:
        return {}

# ---------------------------------------------------------------------------
# Manejo de Tiempo
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"

# ---------------------------------------------------------------------------
# Patrón de Persistencia (Pattern 1: BUCKET PK + REF)
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
    
    main_item = dict(item)
    main_item["PK"] = _bucket_pk(entity)
    main_item["SK"] = main_item.get("SK") or _make_bucket_sk(created_at, entity_id)
    main_item["createdAt"] = main_item.get("createdAt") or created_at
    main_item["updatedAt"] = _now_iso()

    ref_item = {
        "PK": _ref_pk(entity, entity_id),
        "SK": "REF",
        "entityId": entity_id,
        "refPK": main_item["PK"],
        "refSK": main_item["SK"],
        "updatedAt": main_item["updatedAt"]
    }

    _table.put_item(Item=main_item)
    _table.put_item(Item=ref_item)
    return main_item

def _get_by_id(entity: str, entity_id: Any) -> Optional[dict]:
    if str(entity or "").upper() == "ASSOCIATE_MONTH":
        return _get_associate_month_by_id(entity_id)
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: return None
    resp_main = _table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return resp_main.get("Item")

def _update_by_id(entity: str, entity_id: Any, expression: str, values: dict, names: Optional[dict] = None) -> dict:
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: raise KeyError(f"{entity}_NOT_FOUND")

    kwargs = {
        "Key": {"PK": ref["refPK"], "SK": ref["refSK"]},
        "UpdateExpression": expression,
        "ExpressionAttributeValues": values,
        "ReturnValues": "ALL_NEW"
    }
    if names: kwargs["ExpressionAttributeNames"] = names
    
    resp = _table.update_item(**kwargs)
    return resp.get("Attributes")

def _query_bucket(entity: str, limit: Optional[int] = None, forward: bool = False) -> List[dict]:
    pk = _bucket_pk(entity)
    query_kwargs = {"KeyConditionExpression": Key("PK").eq(pk), "ScanIndexForward": forward}
    if limit: query_kwargs["Limit"] = limit
    
    items = []
    while True:
        resp = _table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek or (limit and len(items) >= limit): break
        query_kwargs["ExclusiveStartKey"] = lek
    return items

def _log_get_item_failure(event: str, key: dict, error: Exception, **extra) -> None:
    payload = {
        "event": event,
        "table": TABLE_NAME,
        "key": _normalize_ddb_key(key) or key,
        "errorType": error.__class__.__name__,
        "message": str(error),
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload, default=_json_default))

def _safe_get_item(key: dict, log_event: Optional[str] = None, **extra) -> Optional[dict]:
    try:
        resp = _table.get_item(Key=key)
    except Exception as ex:
        if log_event:
            _log_get_item_failure(log_event, key, ex, **extra)
        raise
    return resp.get("Item")

def _normalize_ddb_key(key: dict) -> Optional[dict]:
    if not isinstance(key, dict):
        return None

    pk = key.get("PK")
    sk = key.get("SK")
    if pk in (None, "") or sk in (None, ""):
        return None

    return {
        "PK": str(pk),
        "SK": str(sk),
    }

def _dedupe_ddb_keys(keys: List[dict]) -> List[dict]:
    normalized: List[dict] = []
    seen = set()

    for raw_key in keys or []:
        key = _normalize_ddb_key(raw_key)
        if not key:
            continue
        dedupe_key = (key["PK"], key["SK"])
        if dedupe_key in seen:
            continue
        normalized.append(key)
        seen.add(dedupe_key)

    return normalized

def _get_item_by_key(key: dict) -> Optional[dict]:
    normalized_key = _normalize_ddb_key(key)
    if not normalized_key:
        return None
    item = _safe_get_item(normalized_key, "ddb_parallel_get_item_failed")
    if not item:
        return None
    return item

def _ddb_serialize_key(key: dict) -> dict:
    return {key_name: _ddb_serializer.serialize(value) for key_name, value in key.items()}

def _ddb_deserialize_item(item: dict) -> dict:
    return {key_name: _ddb_deserializer.deserialize(value) for key_name, value in item.items()}

def _ddb_key_request_shape(keys: List[dict]) -> str:
    if not keys:
        return "empty"
    sample = keys[0]
    if not isinstance(sample, dict):
        return "invalid"
    if all(isinstance(value, dict) and len(value) == 1 for value in sample.values()):
        return "attribute_value"
    return "plain"

def _batch_get_items(keys: List[dict]) -> List[dict]:
    normalized_keys = _dedupe_ddb_keys(keys)
    if not normalized_keys:
        return []

    loaded_items: List[dict] = []
    pending = list(normalized_keys)

    while pending:
        chunk = pending[:100]
        pending = pending[100:]
        
        # 1. ¡CAMBIO AQUÍ! Pasamos el chunk directo, SIN llamar a _ddb_serialize_key
        request = {
            TABLE_NAME: {
                "Keys": chunk,
            }
        }

        retries = 0
        while True:
            try:
                # 2. ¡CAMBIO AQUÍ! Usamos _dynamodb (Resource) en vez de _ddb_client
                resp = _dynamodb.batch_get_item(RequestItems=request)
            except ClientError as ex:
                error = ex.response.get("Error", {}) if isinstance(ex.response, dict) else {}
                print(json.dumps({
                    "event": "ddb_batch_get_failed",
                    "table": TABLE_NAME,
                    "errorType": error.get("Code") or ex.__class__.__name__,
                    "message": error.get("Message") or str(ex),
                    "requestKeyShape": _ddb_key_request_shape(request.get(TABLE_NAME, {}).get("Keys", [])),
                    "keys": chunk,
                }, default=_json_default))
                raise

            # 3. ¡CAMBIO AQUÍ! _dynamodb ya devuelve diccionarios normales, NO usamos _ddb_deserialize_item
            raw_items = resp.get("Responses", {}).get(TABLE_NAME, [])
            loaded_items.extend(raw_items)

            unprocessed = resp.get("UnprocessedKeys", {}).get(TABLE_NAME, {})
            unprocessed_keys = unprocessed.get("Keys", [])
            if not unprocessed_keys:
                break

            retries += 1
            time.sleep(min(0.05 * (2 ** (retries - 1)), 1.0))
            request = {
                TABLE_NAME: {
                    "Keys": unprocessed_keys,
                }
            }

    return loaded_items
def _batch_get_entities(entity: str, entity_ids: List[Any]) -> List[dict]:
    entity = str(entity or "").upper()
    normalized_ids: List[Any] = []
    seen = set()
    for raw_id in entity_ids or []:
        entity_id = _normalize_batch_entity_id(entity, raw_id)
        dedupe_key = json.dumps(entity_id, default=str)
        if entity_id in (None, "") or dedupe_key in seen:
            continue
        normalized_ids.append(entity_id)
        seen.add(dedupe_key)

    if not normalized_ids:
        return []

    if entity == "ASSOCIATE_MONTH":
        direct_items = _batch_get_items([
            _associate_month_key(entity_id)
            for entity_id in normalized_ids
        ])
        loaded_ids = {
            _associate_month_entity_id(item.get("associateId"), str(item.get("monthKey") or ""))
            for item in direct_items
            if isinstance(item, dict)
        }
        missing_ids = [entity_id for entity_id in normalized_ids if entity_id not in loaded_ids]
        if not missing_ids:
            return direct_items

        legacy_items = _batch_get_items([
            {"PK": _ref_pk(entity, entity_id), "SK": "REF"}
            for entity_id in missing_ids
        ])
        if not legacy_items:
            return direct_items

        main_items = _batch_get_items([
            {"PK": ref_item["refPK"], "SK": ref_item["refSK"]}
            for ref_item in legacy_items
            if ref_item.get("refPK") and ref_item.get("refSK")
        ])
        migrated_main_items = [
            _migrate_associate_month_item(
                _associate_month_entity_id(item.get("associateId"), str(item.get("monthKey") or "")),
                item,
            )
            for item in main_items
            if isinstance(item, dict)
        ]
        return direct_items + [item for item in migrated_main_items if item]

    ref_items = _batch_get_items([
        {"PK": _ref_pk(entity, entity_id), "SK": "REF"}
        for entity_id in normalized_ids
    ])
    if not ref_items:
        return []

    main_items = _batch_get_items([
        {"PK": ref_item["refPK"], "SK": ref_item["refSK"]}
        for ref_item in ref_items
        if ref_item.get("refPK") and ref_item.get("refSK")
    ])
    return main_items

def _order_customer_history_pk(customer_id: Any) -> str:
    return f"ORDER_BY_CUSTOMER#{_customer_entity_id(customer_id)}"

def _order_customer_history_sk(created_at_iso: str, order_id: Any) -> str:
    created_at = str(created_at_iso or _now_iso()).strip() or _now_iso()
    return f"{created_at}#{order_id}"

def _build_order_customer_history_item(order: dict) -> Optional[dict]:
    customer_id = order.get("customerId")
    order_id = str(order.get("orderId") or "").strip()
    if customer_id in (None, "") or not order_id:
        return None

    created_at = str(order.get("createdAt") or _now_iso()).strip() or _now_iso()
    total = order.get("total")
    if total in (None, ""):
        total = order.get("netTotal")
    if total in (None, ""):
        total = order.get("grossSubtotal", D_ZERO)

    return {
        "PK": _order_customer_history_pk(customer_id),
        "SK": _order_customer_history_sk(created_at, order_id),
        "entityType": "orderCustomerHistory",
        "customerId": _customer_entity_id(customer_id),
        "orderId": order_id,
        "customerName": order.get("customerName") or order.get("customer") or "Cliente",
        "status": order.get("status") or "pending",
        "items": order.get("items") or [],
        "grossSubtotal": order.get("grossSubtotal", D_ZERO),
        "discountRate": order.get("discountRate", D_ZERO),
        "discountAmount": order.get("discountAmount", D_ZERO),
        "netTotal": order.get("netTotal", total),
        "total": total,
        "deliveryType": order.get("deliveryType"),
        "deliveryNotes": order.get("deliveryNotes"),
        "shippingAddressLabel": order.get("shippingAddressLabel"),
        "createdAt": created_at,
        "updatedAt": order.get("updatedAt") or _now_iso(),
    }

def _upsert_order_customer_history(order: dict) -> Optional[dict]:
    item = _build_order_customer_history_item(order)
    if not item:
        return None
    _table.put_item(Item=item)
    return item

# ---------------------------------------------------------------------------
# Seguridad y Privilegios
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()

def _customer_entity_id(raw_id: Any) -> Any:
    """Convierte el ID de un customer al tipo correcto (int si es numérico, str si no)."""
    try:
        return int(raw_id)
    except (ValueError, TypeError):
        return raw_id

def _customer_id_str(raw_id: Any) -> str:
    value = _customer_entity_id(raw_id)
    if value in (None, ""):
        return ""
    return str(value)

def _associate_month_entity_id(associate_id: Any, month_key: str) -> str:
    customer_id = _customer_id_str(associate_id)
    normalized_month_key = str(month_key or "").strip()
    if not customer_id or not normalized_month_key:
        return ""
    return f"{customer_id}#{normalized_month_key}"

def _associate_month_key(entity_id: str) -> dict:
    normalized_entity_id = str(entity_id or "").strip()
    return {
        "PK": "ASSOCIATE_MONTH",
        "SK": normalized_entity_id,
    }

def _migrate_associate_month_item(entity_id: str, item: Optional[dict]) -> Optional[dict]:
    if not item or not isinstance(item, dict):
        return None

    key = _associate_month_key(entity_id)
    if item.get("PK") == key["PK"] and item.get("SK") == key["SK"]:
        return item

    associate_id, _, month_key = str(entity_id).partition("#")
    migrated_item = dict(item)
    migrated_item.update(key)
    migrated_item["entityType"] = migrated_item.get("entityType") or "associateMonth"
    migrated_item["associateId"] = migrated_item.get("associateId") or associate_id
    migrated_item["monthKey"] = migrated_item.get("monthKey") or month_key
    migrated_item["createdAt"] = migrated_item.get("createdAt") or _now_iso()
    migrated_item["updatedAt"] = migrated_item.get("updatedAt") or migrated_item["createdAt"]
    _table.put_item(Item=migrated_item)
    _put_associate_month_ref(entity_id, str(migrated_item.get("updatedAt") or _now_iso()))
    return migrated_item

def _get_associate_month_by_id(entity_id: Any) -> Optional[dict]:
    normalized_entity_id = _normalize_batch_entity_id("ASSOCIATE_MONTH", entity_id)
    if not normalized_entity_id:
        return None

    direct_item = _safe_get_item(
        _associate_month_key(normalized_entity_id),
        "associate_month_get_item_failed",
        entityId=normalized_entity_id,
    )
    if direct_item:
        return direct_item

    resp_ref = _table.get_item(Key={"PK": _ref_pk("ASSOCIATE_MONTH", normalized_entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref:
        return None
    resp_main = _table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return _migrate_associate_month_item(normalized_entity_id, resp_main.get("Item"))

def _put_associate_month_ref(entity_id: str, updated_at: str) -> None:
    _table.put_item(Item={
        "PK": _ref_pk("ASSOCIATE_MONTH", entity_id),
        "SK": "REF",
        "entityId": entity_id,
        "refPK": "ASSOCIATE_MONTH",
        "refSK": entity_id,
        "updatedAt": updated_at,
    })

def _increment_associate_month_net_volume(associate_id: Any, month_key: str, delta: Any) -> dict:
    entity_id = _associate_month_entity_id(associate_id, month_key)
    if not entity_id:
        raise ValueError("ASSOCIATE_MONTH_INVALID_ID")

    normalized_associate_id = _customer_id_str(associate_id)
    now = _now_iso()
    resp = _table.update_item(
        Key=_associate_month_key(entity_id),
        UpdateExpression=(
            "SET entityType = if_not_exists(entityType, :entity_type), "
            "associateId = if_not_exists(associateId, :associate_id), "
            "monthKey = if_not_exists(monthKey, :month_key), "
            "createdAt = if_not_exists(createdAt, :created_at), "
            "updatedAt = :updated_at, "
            "netVolume = if_not_exists(netVolume, :zero) + :delta, "
            "isActive = if_not_exists(isActive, :inactive)"
        ),
        ExpressionAttributeValues={
            ":entity_type": "associateMonth",
            ":associate_id": normalized_associate_id,
            ":month_key": str(month_key or "").strip(),
            ":created_at": now,
            ":updated_at": now,
            ":zero": D_ZERO,
            ":delta": _to_decimal(delta),
            ":inactive": False,
        },
        ReturnValues="ALL_NEW",
    )
    _put_associate_month_ref(entity_id, now)
    return resp.get("Attributes") or {}

def _normalize_batch_entity_id(entity: str, raw_id: Any) -> Any:
    entity = str(entity or "").upper()
    if entity == "CUSTOMER":
        return _customer_entity_id(raw_id)
    if entity == "ASSOCIATE_MONTH":
        raw_value = str(raw_id or "").strip()
        if not raw_value:
            return ""
        associate_id, separator, month_key = raw_value.partition("#")
        if not separator:
            return raw_value
        return _associate_month_entity_id(associate_id, month_key)
    return raw_id

def _customer_id_list(raw_ids: Any) -> List[str]:
    if not isinstance(raw_ids, list):
        return []
    out: List[str] = []
    seen = set()
    for raw_id in raw_ids:
        cid = _customer_id_str(raw_id)
        if not cid or cid in seen:
            continue
        out.append(cid)
        seen.add(cid)
    return out

def _get_customer_upline_ids(customer_or_id: Any, max_levels: Optional[int] = None) -> List[str]:
    customer = customer_or_id if isinstance(customer_or_id, dict) else _get_by_id("CUSTOMER", customer_or_id)
    if not customer:
        return []

    stored = _customer_id_list(customer.get("uplineIds"))
    if stored:
        return stored[:max_levels] if max_levels is not None else stored

    chain: List[str] = []
    current = customer.get("leaderId")
    visited = { _customer_id_str(customer.get("customerId")) }

    while current:
        cid = _customer_id_str(current)
        if not cid or cid in visited:
            break
        chain.append(cid)
        if max_levels and len(chain) >= max_levels:
            break
        visited.add(cid)
        profile = _get_by_id("CUSTOMER", current)
        current = profile.get("leaderId") if profile else None

    return chain

def _build_network_tree_payload(customers: List[dict]) -> dict:
    children_by_parent: Dict[str, List[str]] = {NETWORK_TREE_ROOT_KEY: []}
    parent_by_child: Dict[str, Optional[str]] = {}
    customer_ids: List[str] = []
    seen_ids = set()

    for customer in customers:
        cid = _customer_id_str(customer.get("customerId"))
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        customer_ids.append(cid)

        leader_id = _customer_id_str(customer.get("leaderId")) or None
        parent_by_child[cid] = leader_id

        parent_key = leader_id or NETWORK_TREE_ROOT_KEY
        children_by_parent.setdefault(parent_key, []).append(cid)
        children_by_parent.setdefault(cid, [])

    for parent_key, child_ids in list(children_by_parent.items()):
        children_by_parent[parent_key] = sorted(set(child_ids), key=lambda value: str(value))

    return {
        "entityType": "networkTree",
        "treeId": NETWORK_TREE_ID,
        "schemaVersion": 1,
        "customerIds": sorted(customer_ids, key=lambda value: str(value)),
        "rootIds": list(children_by_parent.get(NETWORK_TREE_ROOT_KEY, [])),
        "childrenByParent": children_by_parent,
        "parentByChild": parent_by_child,
    }

def _network_tree_key(tree_id: str = NETWORK_TREE_ID) -> dict:
    normalized_tree_id = str(tree_id or NETWORK_TREE_ID).strip() or NETWORK_TREE_ID
    return {
        "PK": f"NETWORK_TREE#{normalized_tree_id}",
        "SK": NETWORK_TREE_SK,
    }

def _normalize_network_tree_item(tree: Optional[dict]) -> Optional[dict]:
    if not tree or not isinstance(tree, dict):
        return None
    tree.setdefault("childrenByParent", {NETWORK_TREE_ROOT_KEY: []})
    tree.setdefault("parentByChild", {})
    tree.setdefault("customerIds", [])
    tree.setdefault("rootIds", list(tree["childrenByParent"].get(NETWORK_TREE_ROOT_KEY, [])))
    return tree

def _get_network_tree_legacy(tree_id: str = NETWORK_TREE_ID) -> Optional[dict]:
    ref_key = {"PK": _ref_pk("NETWORK_TREE", tree_id), "SK": "REF"}
    ref = _safe_get_item(ref_key, "network_tree_legacy_ref_get_item_failed", treeId=tree_id)
    if not ref:
        return None

    main_key = {"PK": ref.get("refPK"), "SK": ref.get("refSK")}
    tree = _safe_get_item(main_key, "network_tree_legacy_main_get_item_failed", treeId=tree_id)
    return _normalize_network_tree_item(tree)

def _put_network_tree(tree_payload: dict, updated_at: Optional[str] = None) -> dict:
    timestamp = updated_at or _now_iso()
    payload = dict(tree_payload or {})
    payload.update(_network_tree_key(payload.get("treeId") or NETWORK_TREE_ID))
    payload["createdAt"] = payload.get("createdAt") or timestamp
    payload["updatedAt"] = timestamp
    payload["customerCount"] = len(payload.get("customerIds") or [])
    _table.put_item(Item=payload)
    return payload

def _get_network_tree(tree_id: str = NETWORK_TREE_ID) -> Optional[dict]:
    key = _network_tree_key(tree_id)
    tree = _safe_get_item(
        key,
        "network_tree_get_item_failed",
        treeId=tree_id,
        keyPattern="PK=NETWORK_TREE#{treeId}, SK=TREE",
    )
    if tree:
        return _normalize_network_tree_item(tree)

    legacy_tree = _get_network_tree_legacy(tree_id)
    if not legacy_tree:
        return None

    migrated_tree = _put_network_tree(
        legacy_tree,
        updated_at=legacy_tree.get("updatedAt") or legacy_tree.get("createdAt") or _now_iso(),
    )
    print(json.dumps({
        "event": "network_tree_migrated_to_singleton_key",
        "treeId": tree_id,
        "key": key,
    }, default=_json_default))
    return _normalize_network_tree_item(migrated_tree)

def _network_tree_descendant_ids(tree: Optional[dict], customer_id: Any, max_depth: Optional[int] = None) -> List[str]:
    if not tree or not isinstance(tree, dict):
        return []

    root_id = _customer_id_str(customer_id)
    if not root_id:
        return []

    children_by_parent = tree.get("childrenByParent") or {}
    descendants: List[str] = []
    queue: List[Tuple[str, int]] = [(root_id, 0)]
    visited = {root_id}

    while queue:
        current_id, depth = queue.pop(0)
        if max_depth is not None and depth >= max_depth:
            continue
        for child_id in children_by_parent.get(current_id, []) or []:
            normalized_child_id = _customer_id_str(child_id)
            if not normalized_child_id or normalized_child_id in visited:
                continue
            visited.add(normalized_child_id)
            descendants.append(normalized_child_id)
            queue.append((normalized_child_id, depth + 1))

    return descendants

def _ensure_network_tree() -> dict:
    tree = _get_network_tree()
    if tree:
        return tree
    _sync_customer_network_metadata()
    return _get_network_tree() or {
        "treeId": NETWORK_TREE_ID,
        "childrenByParent": {NETWORK_TREE_ROOT_KEY: []},
        "parentByChild": {},
        "customerIds": [],
        "rootIds": [],
    }

def _sync_customer_network_metadata() -> dict:
    customers = _query_bucket("CUSTOMER")
    tree_payload = _build_network_tree_payload(customers)
    nodes = {}
    children_by_leader = {
        parent_id: [child_id for child_id in child_ids if parent_id != NETWORK_TREE_ROOT_KEY]
        for parent_id, child_ids in (tree_payload.get("childrenByParent") or {}).items()
        if parent_id != NETWORK_TREE_ROOT_KEY
    }

    for customer in customers:
        cid = _customer_id_str(customer.get("customerId"))
        if not cid:
            continue
        leader_id = (tree_payload.get("parentByChild") or {}).get(cid)
        nodes[cid] = {
            "customer": customer,
            "leaderId": leader_id,
        }

    upline_cache: Dict[str, List[str]] = {}
    descendant_cache: Dict[str, List[str]] = {}

    def _compute_upline(cid: str) -> List[str]:
        if cid in upline_cache:
            return list(upline_cache[cid])
        chain: List[str] = []
        visited = {cid}
        current = (nodes.get(cid) or {}).get("leaderId")
        while current:
            if current in visited:
                break
            chain.append(current)
            visited.add(current)
            current = (nodes.get(current) or {}).get("leaderId")
        upline_cache[cid] = list(chain)
        return list(chain)

    def _compute_descendants(cid: str, trail=None) -> List[str]:
        if cid in descendant_cache:
            return list(descendant_cache[cid])
        trail = set(trail or set())
        if cid in trail:
            return []
        trail.add(cid)

        descendants: List[str] = []
        seen = set()
        for child_id in children_by_leader.get(cid, []):
            if child_id in trail or child_id in seen:
                continue
            descendants.append(child_id)
            seen.add(child_id)
            for nested_id in _compute_descendants(child_id, trail):
                if nested_id in seen:
                    continue
                descendants.append(nested_id)
                seen.add(nested_id)

        descendant_cache[cid] = list(descendants)
        return list(descendants)

    updated = 0
    timestamp = _now_iso()

    for cid, node in nodes.items():
        customer = dict(node["customer"])
        upline_ids = _compute_upline(cid)
        descendant_ids = _compute_descendants(cid)
        direct_ids = list(children_by_leader.get(cid, []))
        desired = {
            "uplineIds": upline_ids,
            "networkPath": "/".join(list(reversed(upline_ids)) + [cid]),
            "networkDepth": len(upline_ids),
            "rootLeaderId": upline_ids[-1] if upline_ids else None,
            "directReferralIds": direct_ids,
            "networkDescendantIds": descendant_ids,
            "networkDescendantCount": len(descendant_ids),
        }

        changed = False
        for field, value in desired.items():
            if customer.get(field) != value:
                customer[field] = value
                changed = True

        if not changed:
            continue

        customer["updatedAt"] = timestamp
        customer["networkMetadataUpdatedAt"] = timestamp
        _table.put_item(Item=customer)
        updated += 1

    _put_network_tree(tree_payload, updated_at=timestamp)

    result = {
        "customers": len(nodes),
        "updated": updated,
        "treeId": NETWORK_TREE_ID,
        "treeCustomerCount": len(tree_payload.get("customerIds") or []),
        "updatedAt": timestamp,
    }
    print(json.dumps({"event": "customer_network_sync", **result}))
    return result

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
    "employee_add",
    "employee_manage_privileges",
    "access_screen_employees",
    "config_manage",
    "access_screen_honor_board",
]

_SUPERADMIN_TOKEN = "demo-token-8d522a140ce34cbc"

def _superadmin_actor() -> dict:
    """Actor con todos los privilegios para el token de superadmin."""
    return {
        "user_id": "superadmin",
        "role": "admin",
        "privileges": {p: True for p in _ALL_PRIVILEGES},
    }

def _normalize_privileges(raw: Any) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {p: bool(data.get(p)) for p in _ALL_PRIVILEGES}


# ---------------------------------------------------------------------------
# Autenticación y Autorización
# ---------------------------------------------------------------------------

def _extract_actor(headers: dict) -> dict:
    """Extrae identidad del actor desde headers inyectados por API Gateway / Authorizer.

    Retorna dict con:
      user_id    : str | None
      role       : str  — 'admin' | 'employee' | 'cliente' | ''
      privileges : dict — mapa de privilegios (vacío si no es admin/employee)
    """
    h = headers or {}

    # Bearer token tiene prioridad: contiene rol y privilegios completos de la sesión
    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if token:
        if token == _SUPERADMIN_TOKEN:
            return _superadmin_actor()
        session = _get_by_id("SESSION", token)
        if isinstance(session, dict):
            return {
                "user_id": str(session.get("userId") or "").strip() or None,
                "role": str(session.get("role") or "").strip().lower(),
                "privileges": _normalize_privileges(session.get("privileges")),
            }

    # Fallback: headers legacy inyectados por API Gateway / Authorizer
    user_id = (h.get("x-user-id") or h.get("X-User-Id") or "").strip() or None
    role = (h.get("x-user-role") or h.get("X-User-Role") or "").strip().lower()
    raw_privs = h.get("x-user-privileges") or h.get("X-User-Privileges") or "{}"
    try:
        privs = json.loads(raw_privs) if isinstance(raw_privs, str) else (raw_privs or {})
    except Exception:
        privs = {}
    return {"user_id": user_id, "role": role, "privileges": _normalize_privileges(privs)}


def _extract_actor_from_bearer(headers: dict) -> dict:
    """Extrae identidad unicamente desde Authorization: Bearer <token>."""
    h = headers or {}
    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if not token:
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    if token == _SUPERADMIN_TOKEN:
        return _superadmin_actor()

    session = _get_by_id("SESSION", token)
    if not isinstance(session, dict):
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    return {
        "user_id": str(session.get("userId") or "").strip() or None,
        "role": str(session.get("role") or "").strip().lower(),
        "privileges": _normalize_privileges(session.get("privileges")),
    }


def _extract_admin_actor(headers: dict) -> dict:
    """Extrae actor administrativo desde headers x-user-* legacy."""
    actor = _extract_actor(headers)
    if actor.get("role") in ("admin", "employee"):
        return actor
    return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}


def _extract_bearer_token(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    prefix = "bearer "
    if raw.lower().startswith(prefix):
        token = raw[len(prefix):].strip()
        return token or None
    return None


def _require_admin(headers: dict, privilege: Optional[str] = None) -> Optional[dict]:
    """Devuelve respuesta 403 si el actor NO es admin/employee con el privilegio requerido.

    Si el actor está autorizado, devuelve None (sin error).
    Uso:
        err = _require_admin(headers, "order_mark_paid")
        if err: return err
    """
    actor = _extract_actor(headers)
    if actor["role"] not in ("admin", "employee"):
        return _json_response(403, {"message": "Acceso denegado: se requiere perfil admin"})
    # admin tiene acceso total; los privilegios solo restringen a employee
    if privilege and actor["role"] == "employee" and not actor["privileges"].get(privilege):
        return _json_response(403, {"message": f"Acceso denegado: privilegio '{privilege}' requerido"})
    return None


def _require_self_or_admin(headers: dict, resource_customer_id: Any) -> Optional[dict]:
    """Devuelve respuesta 403 si el actor NO es el propietario del recurso ni un admin.

    Un customer sólo puede acceder a recursos cuyo customerId coincida con su user_id.
    Un admin/employee siempre puede acceder.
    Uso:
        err = _require_self_or_admin(headers, order["customerId"])
        if err: return err
    """
    actor = _extract_actor(headers)
    if actor["role"] in ("admin", "employee"):
        return None
    if not actor["user_id"]:
        return _json_response(401, {"message": "No autenticado"})
    if str(actor["user_id"]) != str(resource_customer_id):
        return _json_response(403, {"message": "Acceso denegado: solo puedes ver tus propios recursos"})
    return None


def _require_self_or_admin_from_bearer(headers: dict, resource_customer_id: Any) -> Optional[dict]:
    """Protege endpoints self-service con Bearer para customers y conserva admin legacy."""
    bearer_actor = _extract_actor_from_bearer(headers)
    if bearer_actor["role"] in ("admin", "employee"):
        return None
    if bearer_actor["user_id"]:
        if str(bearer_actor["user_id"]) != str(resource_customer_id):
            return _json_response(403, {"message": "Acceso denegado: solo puedes ver tus propios recursos"})
        return None

    admin_actor = _extract_admin_actor(headers)
    if admin_actor["role"] in ("admin", "employee"):
        return None
    return _json_response(401, {"message": "No autenticado"})

# ---------------------------------------------------------------------------
# Carga de Configuración (con Cache)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def _load_app_config() -> dict:
    # Intenta cargar la configuración global del negocio
    cfg = _get_by_id("CONFIG", "app-v1")
    if cfg: return cfg.get("config", {})
    return {} # Retornar default si no existe

def _audit_event(action: str, headers, payload=None, target=None) -> None:
    """Registra un evento de auditoría."""
    headers = headers or {}
    actor_user_id = headers.get("x-user-id") or headers.get("x-actor-id")
    now = _now_iso()
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    item = {
        "entityType": "adminEvent", "eventId": event_id, "action": action,
        "actorUserId": actor_user_id, "target": target or {},
        "payload": payload or {}, "createdAt": now, "updatedAt": now,
    }
    try:
        _put_entity("ADMIN_EVENT", event_id, item, created_at_iso=now)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Email (SES) — Envío Genérico
# ---------------------------------------------------------------------------

_ses_client = None

def _get_ses():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses", region_name=AWS_REGION)
    return _ses_client

SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "info@findingu.com.mx")
def _send_ses_email(to_email: str, subject: str, text: str, html: str) -> None:
    """Envía un correo vía SES. Falla silenciosamente para no interrumpir el flujo."""
    try:
        _get_ses().send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            },
        )
    except Exception as e:
        print(f"[SES_ERROR] {to_email}: {e}")
