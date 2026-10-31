"""Árbol de red, estados mensuales del asociado e historial de pedidos."""

import json
from typing import Any, Dict, List, Optional, Tuple
from .settings import D_ZERO, NETWORK_TREE_ID, NETWORK_TREE_ROOT_KEY, NETWORK_TREE_SK
from .values import _associate_month_entity_id, _customer_entity_id, _customer_id_list, _customer_id_str, _json_default, _now_iso, _to_decimal
from . import db
from .db import _batch_get_entities, _batch_get_items, _get_by_id, _normalize_batch_entity_id, _query_bucket, _ref_pk, _safe_get_item


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
    db._table.put_item(Item=item)
    return item

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
    db._table.put_item(Item=migrated_item)
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

    resp_ref = db._table.get_item(Key={"PK": _ref_pk("ASSOCIATE_MONTH", normalized_entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref:
        return None
    resp_main = db._table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return _migrate_associate_month_item(normalized_entity_id, resp_main.get("Item"))

def _batch_get_associate_months(entity_ids: List[str]) -> List[dict]:
    """Lote de ASSOCIATE_MONTH: clave directa, con respaldo al puntero legado.

    Vivía dentro de `_batch_get_entities` como un `if entity == ...`; ahora se
    registra, de modo que la capa de datos no necesita conocer la entidad.
    """
    direct_items = _batch_get_items([_associate_month_key(eid) for eid in entity_ids])
    loaded_ids = {
        _associate_month_entity_id(item.get("associateId"), str(item.get("monthKey") or ""))
        for item in direct_items
        if isinstance(item, dict)
    }
    missing_ids = [eid for eid in entity_ids if eid not in loaded_ids]
    if not missing_ids:
        return direct_items

    legacy_items = _batch_get_items([
        {"PK": _ref_pk("ASSOCIATE_MONTH", eid), "SK": "REF"} for eid in missing_ids
    ])
    if not legacy_items:
        return direct_items

    main_items = _batch_get_items([
        {"PK": ref["refPK"], "SK": ref["refSK"]}
        for ref in legacy_items if ref.get("refPK") and ref.get("refSK")
    ])
    migrados = [
        _migrate_associate_month_item(
            _associate_month_entity_id(item.get("associateId"), str(item.get("monthKey") or "")),
            item,
        )
        for item in main_items if isinstance(item, dict)
    ]
    return direct_items + [item for item in migrados if item]



def _put_associate_month_ref(entity_id: str, updated_at: str) -> None:
    db._table.put_item(Item={
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
    resp = db._table.update_item(
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

def _increment_associate_month_net_vp(associate_id: Any, month_key: str, delta_vp: float) -> dict:
    """Acumula puntos VP directos en el registro mensual del asociado."""
    entity_id = _associate_month_entity_id(associate_id, month_key)
    if not entity_id:
        raise ValueError("ASSOCIATE_MONTH_INVALID_ID")
    normalized_associate_id = _customer_id_str(associate_id)
    now = _now_iso()
    resp = db._table.update_item(
        Key=_associate_month_key(entity_id),
        UpdateExpression=(
            "SET entityType = if_not_exists(entityType, :entity_type), "
            "associateId = if_not_exists(associateId, :associate_id), "
            "monthKey = if_not_exists(monthKey, :month_key), "
            "createdAt = if_not_exists(createdAt, :created_at), "
            "updatedAt = :updated_at, "
            "netVP = if_not_exists(netVP, :zero) + :delta, "
            "isActive = if_not_exists(isActive, :inactive)"
        ),
        ExpressionAttributeValues={
            ":entity_type": "associateMonth",
            ":associate_id": normalized_associate_id,
            ":month_key": str(month_key or "").strip(),
            ":created_at": now,
            ":updated_at": now,
            ":zero": _to_decimal(0),
            ":delta": _to_decimal(delta_vp),
            ":inactive": False,
        },
        ReturnValues="ALL_NEW",
    )
    _put_associate_month_ref(entity_id, now)
    return resp.get("Attributes") or {}

def _session_key(token: str) -> dict:
    """Clave directa de una sesión: `PK="SESSION#<token>", SK="SESSION"`."""
    return {"PK": f"SESSION#{str(token or '').strip()}", "SK": "SESSION"}


def _put_session(token: str, datos: dict, ttl_epoch: Optional[int] = None) -> dict:
    """Escribe la sesión con clave directa (1 item en vez de 2).

    El patrón bucket+REF obliga a 2 GetItem para validar un Bearer, en CADA
    petición autenticada, y deja además un puntero REF por sesión que se
    acumula. Una sesión se busca siempre por su token, nunca se lista ni se
    ordena por fecha: no necesita el patrón.
    """
    item = {**_session_key(token), "entityType": "session", **datos}
    if ttl_epoch is not None:
        item["ttl"] = ttl_epoch
    db._table.put_item(Item=item)
    return item


def _get_session(token: str) -> Optional[dict]:
    """Lee una sesión por su token.

    Intenta primero la clave directa y, si no está, cae al patrón bucket+REF
    para no invalidar las sesiones abiertas antes de este cambio. Las sesiones
    viejas caducan solas por TTL, así que el respaldo se puede retirar pasado
    `SESSION_TTL_SECONDS`.
    """
    token = str(token or "").strip()
    if not token:
        return None
    directa = db._table.get_item(Key=_session_key(token)).get("Item")
    if directa:
        return directa
    return _get_by_id("SESSION", token)


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
    db._table.put_item(Item=payload)
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

def _load_month_states(associate_ids: List[Any], month_key: str) -> Dict[str, dict]:
    """Estados ASSOCIATE_MONTH de varios asociados en `⌈N/100⌉` BatchGetItem.

    Sustituye al patrón `for cid in ids: _get_by_id("ASSOCIATE_MONTH", ...)`,
    que hacía 1-3 GetItem secuenciales por asociado.
    """
    entity_ids: List[str] = []
    seen = set()
    for associate_id in associate_ids or []:
        cid = _customer_id_str(associate_id)
        if not cid or cid in seen:
            continue
        seen.add(cid)
        entity_id = _associate_month_entity_id(cid, month_key)
        if entity_id:
            entity_ids.append(entity_id)

    if not entity_ids:
        return {}

    states = _batch_get_entities("ASSOCIATE_MONTH", entity_ids)
    return {
        _customer_id_str(item.get("associateId")): item
        for item in states
        if isinstance(item, dict) and item.get("associateId") not in (None, "")
    }

def _load_network_scope(customer: dict, max_depth: Optional[int] = None) -> Tuple[List[dict], dict]:
    """Carga el cliente y su descendencia usando el árbol de red persistido.

    Resuelve los ids con `_network_tree_descendant_ids` (1 GetItem al singleton
    del árbol) y trae los items en `BatchGetItem` de 100 en 100, en lugar de
    leer la colección CUSTOMER entera o hacer un `_get_by_id` por descendiente.

    Devuelve `(items, meta)`; `items[0]` es siempre el propio cliente.
    """
    if not customer or not isinstance(customer, dict):
        return [], {"source": "empty", "requestedCount": 0, "loadedCount": 0, "missingCount": 0}

    customer_id = _customer_id_str(customer.get("customerId"))
    if not customer_id:
        return [], {"source": "empty", "requestedCount": 0, "loadedCount": 0, "missingCount": 0}

    def _load_from_tree(tree_payload):
        descendant_ids = _network_tree_descendant_ids(tree_payload, customer_id, max_depth)
        batch_ids = [customer_id, *descendant_ids]
        loaded = _batch_get_entities("CUSTOMER", batch_ids)

        by_id = {
            _customer_id_str(item.get("customerId")): item
            for item in loaded
            if isinstance(item, dict) and item.get("customerId") not in (None, "")
        }
        by_id[customer_id] = customer

        scoped = [by_id[cid] for cid in batch_ids if by_id.get(cid)]
        return descendant_ids, scoped

    source = "network_tree_batch_get"
    tree = _ensure_network_tree()
    descendant_ids, scoped = _load_from_tree(tree)
    missing = max(0, 1 + len(descendant_ids) - len(scoped))

    if missing and descendant_ids:
        # El árbol quedó desfasado respecto a CUSTOMER: se reconstruye una vez.
        _sync_customer_network_metadata()
        tree = _ensure_network_tree()
        descendant_ids, scoped = _load_from_tree(tree)
        missing = max(0, 1 + len(descendant_ids) - len(scoped))
        source = "network_tree_batch_get_rebuilt"

    return scoped, {
        "source": source,
        "requestedCount": len(descendant_ids),
        "loadedCount": len(scoped),
        "missingCount": missing,
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
        db._table.put_item(Item=customer)
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
