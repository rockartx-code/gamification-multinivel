import base64
import json
import boto3
import urllib.error
import urllib.parse
import urllib.request
import core_utils as utils  # Importado desde la Layer
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal

# Clientes de AWS
sfn = boto3.client('stepfunctions')
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)

# Configuración de Entorno
ORDER_SFN_ARN = utils.os.getenv("ORDER_FULFILLMENT_SFN_ARN")
ML_TOKEN = utils.os.getenv("MERCADOPAGO_ACCESS_TOKEN")
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

MAX_COMMISSION_LEVELS = 3
DEFAULT_ORDER_HISTORY_PAGE_SIZE = 10
MAX_ORDER_HISTORY_PAGE_SIZE = 50        # clientes
MAX_ADMIN_ORDER_PAGE_SIZE = 500         # admins

# ---------------------------------------------------------------------------
# HELPERS DE LÓGICA DE NEGOCIO
# ---------------------------------------------------------------------------

def _enrich_items_commissionable(items: list) -> list:
    """
    Añade la bandera commissionable a cada ítem según el catálogo de productos.
    Si el producto no se encuentra, se asume commissionable=True.
    """
    enriched = []
    for it in items:
        item = dict(it) if isinstance(it, dict) else {}
        if "commissionable" not in item:
            pid = item.get("productId")
            if pid is not None:
                product = utils._get_by_id("PRODUCT", pid)
                if product:
                    item["commissionable"] = bool(product.get("commissionable", True))
        enriched.append(item)
    return enriched


def _calculate_totals(items, customer_id, buyer_type):
    gross = utils.D_ZERO
    for it in items:
        price = utils._to_decimal(it.get("price", 0))
        qty = int(it.get("quantity", 1))
        gross += price * qty

    cfg = utils._load_app_config().get("rewards", {})
    rate = utils.Decimal("0.0")
    if buyer_type in ["associate", "registered"]:
        if gross >= 3600:
            rate = utils.Decimal("0.30")

    discount_amount = (gross * rate).quantize(utils.D_CENT)
    return {
        "grossSubtotal": gross,
        "discountRate": rate,
        "discountAmount": discount_amount,
        "netTotal": (gross - discount_amount).quantize(utils.D_CENT),
    }


def _parse_orders_page_size(raw_limit) -> int:
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return DEFAULT_ORDER_HISTORY_PAGE_SIZE
    return max(1, min(limit, MAX_ORDER_HISTORY_PAGE_SIZE))


def _apply_stock_delta(stock_id: str, deltas: dict):
    stock = utils._get_by_id("STOCK", stock_id)
    if not stock:
        return None, "Almacen no encontrado"

    inventory = {str(k): int(v) for k, v in (stock.get("inventory") or {}).items()}
    for pid, delta in (deltas or {}).items():
        current = inventory.get(str(pid), 0)
        next_qty = current + int(delta)
        if next_qty < 0:
            return None, f"Stock insuficiente para el producto {pid}"
        inventory[str(pid)] = next_qty

    updated = utils._update_by_id(
        "STOCK",
        stock_id,
        "SET inventory = :inv, updatedAt = :u",
        {":inv": inventory, ":u": utils._now_iso()},
    )
    return updated, None


def _log_inventory_movement(stock_id, movement_type, product_id, qty, reference_id, user_id, reason=""):
    move_id = f"MOV-{utils.uuid.uuid4().hex[:12].upper()}"
    return utils._put_entity("INVENTORY_MOVEMENT", move_id, {
        "entityType": "inventoryMovement",
        "movementId": move_id,
        "stockId": stock_id,
        "movementType": movement_type,
        "type": movement_type,
        "productId": int(product_id),
        "qty": int(qty),
        "referenceId": reference_id,
        "userId": user_id,
        "reason": reason,
        "createdAt": utils._now_iso(),
    })


def _user_can_operate_pickup_stock(user_id, pickup_stock_id) -> bool:
    if user_id in (None, "") or not pickup_stock_id:
        return False
    stock = utils._get_by_id("STOCK", pickup_stock_id)
    if not stock:
        return False
    linked_ids = {str(item) for item in (stock.get("linkedUserIds") or []) if item is not None}
    return str(user_id) in linked_ids


def _register_branch_sale_for_pickup_order(order: dict, user_id, now_iso: str, payment_method: str) -> str:
    sale_id = f"SALE-{utils.uuid.uuid4().hex[:8].upper()}"
    pickup_stock_id = order.get("pickupStockId")
    sale_item = {
        "entityType": "posSale",
        "saleId": sale_id,
        "orderId": order.get("orderId"),
        "stockId": pickup_stock_id,
        "attendantUserId": user_id,
        "customerId": order.get("customerId"),
        "customerName": order.get("customerName") or "Cliente",
        "paymentStatus": "paid_branch",
        "deliveryStatus": "paid_branch",
        "paymentMethod": payment_method,
        "grossSubtotal": order.get("grossSubtotal") or order.get("netTotal") or order.get("total") or utils.D_ZERO,
        "discountRate": order.get("discountRate") or utils.D_ZERO,
        "discountAmount": order.get("discountAmount") or utils.D_ZERO,
        "total": order.get("netTotal") or order.get("total") or utils.D_ZERO,
        "lines": order.get("items") or [],
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "source": f"pickup_{payment_method}_payment",
    }
    utils._put_entity("POS_SALE", sale_id, sale_item, created_at_iso=now_iso)
    return sale_id


def _encode_orders_next_token(last_evaluated_key: dict) -> str:
    if not last_evaluated_key:
        return ""
    payload = {"sk": str(last_evaluated_key.get("SK") or "").strip()}
    token = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("utf-8").rstrip("=")


def _decode_orders_next_token(token, customer_id):
    token_value = str(token or "").strip()
    if not token_value:
        return None

    try:
        padded = token_value + ("=" * (-len(token_value) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
    except Exception:
        raise ValueError("invalid_next_token")

    start_sk = str((payload or {}).get("sk") or "").strip()
    if not start_sk:
        raise ValueError("invalid_next_token")

    return {
        "PK": utils._order_customer_history_pk(customer_id),
        "SK": start_sk,
    }


def _serialize_order_list_item(item: dict) -> dict:
    total = item.get("total")
    if total in (None, ""):
        total = item.get("netTotal")
    if total in (None, ""):
        total = item.get("grossSubtotal", utils.D_ZERO)

    return {
        "orderId": item.get("orderId"),
        "customerId": item.get("customerId"),
        "customerName": item.get("customerName") or "Cliente",
        "status": item.get("status") or "pending",
        "items": item.get("items") or [],
        "grossSubtotal": item.get("grossSubtotal", utils.D_ZERO),
        "discountRate": item.get("discountRate", utils.D_ZERO),
        "discountAmount": item.get("discountAmount", utils.D_ZERO),
        "netTotal": item.get("netTotal", total),
        "total": total,
        # Delivery / shipping
        "deliveryType": item.get("deliveryType"),
        "deliveryNotes": item.get("deliveryNotes"),
        "shippingAddressLabel": item.get("shippingAddressLabel"),
        "shippingType": item.get("shippingType"),
        "trackingNumber": item.get("trackingNumber"),
        "deliveryPlace": item.get("deliveryPlace"),
        "deliveryDate": item.get("deliveryDate"),
        "deliveredAt": item.get("deliveredAt"),
        # Address fields
        "recipientName": item.get("recipientName"),
        "phone": item.get("phone"),
        "street": item.get("street"),
        "number": item.get("number"),
        "address": item.get("address"),
        "city": item.get("city"),
        "postalCode": item.get("postalCode"),
        "state": item.get("state"),
        "country": item.get("country"),
        "betweenStreets": item.get("betweenStreets"),
        "references": item.get("references"),
        # Pickup
        "pickupStockId": item.get("pickupStockId"),
        "pickupPaymentMethod": item.get("pickupPaymentMethod"),
        # Stock dispatched from
        "stockId": item.get("stockId"),
        "attendantUserId": item.get("attendantUserId"),
        # Cancellation / return / refund
        "cancelReason": item.get("cancelReason"),
        "cancelledAt": item.get("cancelledAt"),
        "returnRequestId": item.get("returnRequestId"),
        "rejectionReason": item.get("rejectionReason"),
        "rejectedAt": item.get("rejectedAt"),
        "refundReceiptUrl": item.get("refundReceiptUrl"),
        "refundedAt": item.get("refundedAt"),
        # Payment
        "paymentMethod": item.get("paymentMethod"),
        "paymentStatus": item.get("paymentStatus"),
        "paymentProvider": item.get("paymentProvider"),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }


def _query_customer_order_history(customer_id, limit: int, next_token=None):
    query_kwargs = {
        "KeyConditionExpression": utils.Key("PK").eq(utils._order_customer_history_pk(customer_id)),
        "ScanIndexForward": False,
        "Limit": limit,
    }
    start_key = _decode_orders_next_token(next_token, customer_id)
    if start_key:
        query_kwargs["ExclusiveStartKey"] = start_key
    response = utils._table.query(**query_kwargs)
    items = response.get("Items", [])
    return items, _encode_orders_next_token(response.get("LastEvaluatedKey"))


def _backfill_customer_order_history(customer_id) -> int:
    normalized_customer_id = utils._customer_entity_id(customer_id)
    matches = [
        order for order in utils._query_bucket("ORDER")
        if str(utils._customer_entity_id(order.get("customerId"))) == str(normalized_customer_id)
    ]
    matches.sort(
        key=lambda order: (
            str(order.get("createdAt") or ""),
            str(order.get("orderId") or ""),
        ),
        reverse=True,
    )
    for order in matches:
        utils._upsert_order_customer_history(order)
    return len(matches)


def handle_list_orders(customer_id, query, headers):
    next_token = query.get("nextToken")
    status_filter = (query.get("status") or "").lower().strip()
    stock_id_filter = (query.get("stockId") or "").strip()

    # Admin: devuelve todas las órdenes sin filtrar por customerId
    admin_actor = utils._extract_admin_actor(headers)
    bearer_actor = utils._extract_actor_from_bearer(headers)
    is_admin = admin_actor.get("role") in ("admin", "employee") or bearer_actor.get("role") in ("admin", "employee")

    if is_admin:
        # Para admins usamos un límite de página mayor
        raw_limit = query.get("limit")
        try:
            limit = max(1, min(int(raw_limit), MAX_ADMIN_ORDER_PAGE_SIZE)) if raw_limit else MAX_ADMIN_ORDER_PAGE_SIZE
        except (TypeError, ValueError):
            limit = MAX_ADMIN_ORDER_PAGE_SIZE

        items = utils._query_bucket("ORDER", forward=False)
        if status_filter:
            items = [o for o in items if (o.get("status") or "").lower() == status_filter]
        # Filtrar por stock (stockId = stock de despacho, pickupStockId = sucursal de retiro)
        if stock_id_filter:
            items = [
                o for o in items
                if o.get("stockId") == stock_id_filter or o.get("pickupStockId") == stock_id_filter
            ]
        total = len(items)
        # Paginación manual sobre la lista filtrada
        try:
            offset = int(next_token) if next_token and str(next_token).isdigit() else 0
        except (ValueError, TypeError):
            offset = 0
        page = items[offset: offset + limit]
        next_offset = offset + limit
        has_more = next_offset < total
        return utils._json_response(200, {
            "orders": [_serialize_order_list_item(o) for o in page],
            "total": total,
            "count": len(page),
            "pageSize": limit,
            "nextToken": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "source": "admin-scan",
        })

    limit = _parse_orders_page_size(query.get("limit"))

    # Cliente: requiere customerId y solo ve sus propias órdenes
    if not customer_id:
        return utils._json_response(400, {"message": "customerId requerido"})

    err = utils._require_self_or_admin(headers, customer_id)
    if err:
        return err

    try:
        items, response_next_token = _query_customer_order_history(customer_id, limit, next_token)
    except ValueError:
        return utils._json_response(400, {"message": "nextToken invalido"})

    source = "customer-history"
    if not items and not next_token:
        if _backfill_customer_order_history(customer_id):
            items, response_next_token = _query_customer_order_history(customer_id, limit)
            source = "customer-history-backfilled"

    if status_filter:
        items = [o for o in items if (o.get("status") or "").lower() == status_filter]

    return utils._json_response(200, {
        "orders": [_serialize_order_list_item(item) for item in items],
        "pageSize": limit,
        "count": len(items),
        "nextToken": response_next_token or None,
        "hasMore": bool(response_next_token),
        "source": source,
    })


def _upload_evidence_s3(name: str, content_b64: str, content_type: str, prefix: str) -> dict:
    try:
        raw = base64.b64decode(content_b64)
    except Exception:
        raise ValueError("invalid_base64")
    asset_id = f"{prefix}/{utils.uuid.uuid4()}-{name}"
    _s3.put_object(Bucket=BUCKET_NAME, Key=asset_id, Body=raw,
                   ContentType=content_type, ACL="public-read")
    url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    now = utils._now_iso()
    item = {"entityType": "asset", "assetId": asset_id, "name": name,
            "contentType": content_type, "url": url, "createdAt": now, "updatedAt": now}
    utils._put_entity("ASSET", asset_id, item, created_at_iso=now)
    return {"assetId": asset_id, "url": url}


def _void_commissions_for_order(order_id: str, reason: str) -> list:
    """Revierte comisiones del ledger para todos los beneficiarios de una orden."""
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return []

    month_key = order.get("monthKey") or utils._month_key()
    buyer_id = order.get("customerId")

    beneficiaries = utils._get_customer_upline_ids(buyer_id, MAX_COMMISSION_LEVELS)

    if (order.get("buyerType") or "").lower() == "guest":
        referrer_id = order.get("referrerAssociateId")
        if referrer_id:
            beneficiaries = [str(referrer_id)] + beneficiaries

    out = []
    pk_month = "COMMISSION_MONTH"
    for beneficiary_id in beneficiaries:
        sk = f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"
        resp = utils._table.get_item(Key={"PK": pk_month, "SK": sk})
        item = resp.get("Item")
        if not item:
            continue

        ledger = item.get("ledger") or []
        pending_delta = utils.D_ZERO
        confirmed_delta = utils.D_ZERO
        blocked_delta = utils.D_ZERO
        new_ledger = []
        removed = 0

        for row in ledger:
            if row.get("orderId") == order_id:
                amt = utils._to_decimal(row.get("amount"))
                st = (row.get("status") or "").lower()
                if st == "pending":
                    pending_delta += amt
                elif st == "confirmed":
                    confirmed_delta += amt
                elif st == "blocked" or row.get("blocked"):
                    blocked_delta += amt
                removed += 1
                continue
            new_ledger.append(row)

        if removed == 0:
            continue

        try:
            utils._table.update_item(
                Key={"PK": pk_month, "SK": sk},
                UpdateExpression=(
                    "SET ledger = :l, "
                    "totalPending = if_not_exists(totalPending, :z) - :pd, "
                    "totalConfirmed = if_not_exists(totalConfirmed, :z) - :cd, "
                    "totalBlocked = if_not_exists(totalBlocked, :z) - :bd, "
                    "updatedAt = :u"
                ),
                ExpressionAttributeValues={
                    ":l": new_ledger, ":pd": pending_delta,
                    ":cd": confirmed_delta, ":bd": blocked_delta,
                    ":z": utils.D_ZERO, ":u": utils._now_iso(),
                },
            )
        except Exception as e:
            print(f"[VOID_COMM_ERROR] {e}")

        out.append({
            "action": "void", "beneficiaryId": beneficiary_id,
            "orderId": order_id, "pendingRemoved": float(pending_delta),
            "confirmedRemoved": float(confirmed_delta), "reason": reason,
        })
    return out


# ---------------------------------------------------------------------------
# HANDLERS — CRUD BÁSICO
# ---------------------------------------------------------------------------

def handle_create_order(body, headers):
    """POST /orders/create"""
    customer_id = body.get("customerId")
    customer_name = body.get("customerName", "Cliente")
    buyer_type = body.get("buyerType", "guest").lower()

    if customer_id and buyer_type != "guest":
        utils._get_by_id("CUSTOMER", customer_id)

    raw_items = body.get("items", [])
    # Enriquecer ítems con la bandera commissionable del catálogo
    enriched_items = _enrich_items_commissionable(raw_items)
    totals = _calculate_totals(enriched_items, customer_id, buyer_type)
    order_id = f"ORD-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()

    delivery_type = body.get("deliveryType", "delivery")
    shipping_address = body.get("shippingAddress", {}) if isinstance(body.get("shippingAddress"), dict) else {}
    order_item = {
        "entityType": "order", "orderId": order_id, "customerId": customer_id,
        "customerName": customer_name, "buyerType": buyer_type, "status": "pending",
        "items": enriched_items, "shippingAddress": shipping_address,
        "deliveryType": delivery_type,
        "recipientName": body.get("recipientName") or shipping_address.get("recipientName"),
        "phone": body.get("phone") or shipping_address.get("phone"),
        "street": body.get("street") or shipping_address.get("street"),
        "number": body.get("number") or shipping_address.get("number"),
        "address": body.get("address") or shipping_address.get("address"),
        "city": body.get("city") or shipping_address.get("city"),
        "postalCode": body.get("postalCode") or shipping_address.get("postalCode"),
        "state": body.get("state") or shipping_address.get("state"),
        "country": body.get("country") or shipping_address.get("country"),
        "betweenStreets": body.get("betweenStreets") or shipping_address.get("betweenStreets"),
        "references": body.get("references") or shipping_address.get("references"),
        "deliveryNotes": body.get("deliveryNotes") or shipping_address.get("deliveryNotes"),
        "shippingAddressId": body.get("shippingAddressId") or shipping_address.get("addressId") or shipping_address.get("id"),
        "shippingAddressLabel": body.get("shippingAddressLabel") or shipping_address.get("label"),
        "monthKey": utils._month_key(), "createdAt": now, "updatedAt": now,
        **totals,
    }
    if delivery_type == "pickup":
        if body.get("pickupStockId"):
            order_item["pickupStockId"] = body.get("pickupStockId")
        pickup_payment = body.get("pickupPaymentMethod", "online")
        if pickup_payment not in ("online", "at_store"):
            pickup_payment = "online"
        order_item["pickupPaymentMethod"] = pickup_payment

    utils._put_entity("ORDER", order_id, order_item)
    utils._upsert_order_customer_history(order_item)
    utils._audit_event("order.create", headers, body, {"orderId": order_id})
    return utils._json_response(201, {"order": order_item})


def handle_update_status(order_id, body, headers):
    """PATCH /orders/{id}"""
    new_status = body.get("status", "").lower()
    valid_statuses = ["paid", "shipped", "delivered", "canceled", "cancelled", "refunded",
                      "en_devolucion", "devuelto_validado", "devolucion_rechazada"]

    if new_status not in valid_statuses:
        return utils._json_response(400, {"message": "Status inválido"})

    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "No encontrada"})

    actor = utils._extract_actor(headers)
    actor_user_id = actor.get("user_id")
    pickup_stock_id = order.get("pickupStockId")
    pickup_stock_id_str = str(pickup_stock_id or "").strip()
    is_pickup_order = order.get("deliveryType") == "pickup" and pickup_stock_id_str

    if is_pickup_order and new_status in ("paid", "delivered"):
        if not _user_can_operate_pickup_stock(actor_user_id, pickup_stock_id_str):
            return utils._json_response(403, {"message": "El usuario logueado no esta vinculado a la sucursal de entrega"})

    action_map = {
        "paid": "ORDER_PAID",
        "delivered": "ORDER_DELIVERED",
        "canceled": "ORDER_CANCELLED",
        "cancelled": "ORDER_CANCELLED",
        "refunded": "ORDER_REFUNDED",
    }

    sfn_action = action_map.get(new_status)
    if sfn_action and ORDER_SFN_ARN:
        try:
            sfn.start_execution(
                stateMachineArn=ORDER_SFN_ARN,
                input=json.dumps({"orderId": order_id, "action": sfn_action, "payload": body}),
            )
        except Exception as e:
            print(f"[SFN_ERROR] {e}")

    extra_updates = {}
    now = utils._now_iso()
    payment_method = (body.get("paymentMethod") or order.get("paymentMethod") or "").strip().lower()
    if payment_method and payment_method not in ("cash", "card", "transfer"):
        return utils._json_response(400, {"message": "Forma de pago invalida"})
    if payment_method:
        extra_updates["paymentMethod"] = payment_method
    if is_pickup_order and new_status in ("paid", "delivered") and actor_user_id not in (None, ""):
        extra_updates["attendantUserId"] = actor_user_id
        extra_updates["stockId"] = pickup_stock_id_str
    if new_status == "paid" and is_pickup_order and order.get("pickupPaymentMethod") == "at_store":
        extra_updates["paymentStatus"] = body.get("paymentStatus") or "paid_branch"
        if payment_method and not (order.get("cashSaleId") or order.get("branchSaleId")):
            branch_sale_id = _register_branch_sale_for_pickup_order(order, actor_user_id, now, payment_method)
            extra_updates["branchSaleId"] = branch_sale_id
            if payment_method == "cash":
                extra_updates["cashSaleId"] = branch_sale_id
    if new_status == "delivered":
        extra_updates["deliveredAt"] = now
        if is_pickup_order and not order.get("pickupStockDeductedAt"):
            deltas = {}
            for line in order.get("items") or []:
                pid = str(line.get("productId") or "").strip()
                qty = int(line.get("quantity") or line.get("qty") or 0)
                if pid and qty > 0:
                    deltas[pid] = deltas.get(pid, 0) - qty
            if deltas:
                _, stock_error = _apply_stock_delta(pickup_stock_id_str, deltas)
                if stock_error:
                    return utils._json_response(400, {"message": stock_error})
                for line in order.get("items") or []:
                    qty = int(line.get("quantity") or line.get("qty") or 0)
                    if qty <= 0:
                        continue
                    _log_inventory_movement(
                        pickup_stock_id_str,
                        "exit_order",
                        line.get("productId"),
                        qty,
                        order_id,
                        actor_user_id,
                        f"Entrega pickup orden {order_id}",
                    )
                extra_updates["pickupStockDeductedAt"] = now
    if new_status == "devolucion_rechazada":
        rejection_reason = (body.get("rejectionReason") or "").strip()
        if rejection_reason:
            extra_updates["rejectionReason"] = rejection_reason
        extra_updates["rejectedAt"] = now
    if new_status == "shipped":
        if body.get("shippingType"):
            extra_updates["shippingType"] = body["shippingType"]
        if body.get("trackingNumber"):
            extra_updates["trackingNumber"] = body["trackingNumber"]
        if body.get("deliveryPlace"):
            extra_updates["deliveryPlace"] = body["deliveryPlace"]
        if body.get("deliveryDate"):
            extra_updates["deliveryDate"] = body["deliveryDate"]
        if body.get("stockId"):
            extra_updates["stockId"] = body["stockId"]
        # Procesar salida de inventario si se proveen dispatchLines
        dispatch_lines = body.get("dispatchLines") or []
        stock_id_for_dispatch = body.get("stockId")
        if dispatch_lines and stock_id_for_dispatch:
            deltas = {}
            for line in dispatch_lines:
                pid = str(line.get("productId", ""))
                qty = int(line.get("quantity") or line.get("qty") or 0)
                if pid and qty > 0:
                    deltas[pid] = deltas.get(pid, 0) - qty
            if deltas:
                stock = utils._get_by_id("STOCK", stock_id_for_dispatch)
                if stock:
                    inventory = {str(k): int(v) for k, v in (stock.get("inventory") or {}).items()}
                    for pid, delta in deltas.items():
                        inventory[pid] = max(0, inventory.get(pid, 0) + delta)
                    utils._update_by_id(
                        "STOCK", stock_id_for_dispatch,
                        "SET inventory = :inv, updatedAt = :u",
                        {":inv": inventory, ":u": now},
                    )
                    user_id = actor_user_id or body.get("attendantUserId")
                    for pid, delta in deltas.items():
                        _log_inventory_movement(stock_id_for_dispatch, "exit_order", pid, abs(delta), order_id, user_id, f"Despacho orden {order_id}")

    update_expr = "SET #s = :s, updatedAt = :u"
    eav = {":s": new_status, ":u": now}
    for k, v in extra_updates.items():
        safe_key = k.replace(".", "_")
        update_expr += f", {safe_key} = :{safe_key}"
        eav[f":{safe_key}"] = v

    updated = utils._update_by_id("ORDER", order_id, update_expr, eav, {"#s": "status"})
    utils._upsert_order_customer_history(updated)
    return utils._json_response(200, {"order": updated})


def handle_mercadopago_checkout(order_id, body):
    """POST /orders/{id}/checkout"""
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "No encontrada"})

    # Cargar configuración para URLs y secretos (asumiendo que está en utils)
    app_cfg = utils._load_app_config()
    ml_cfg = app_cfg.get("payments", {}).get("mercadoLibre", {})

    success_url = str(body.get("successUrl") or ml_cfg.get("successUrl") or "").strip()
    failure_url = str(body.get("failureUrl") or ml_cfg.get("failureUrl") or "").strip()
    pending_url = str(body.get("pendingUrl") or ml_cfg.get("pendingUrl") or "").strip()
    notification_url = str(body.get("notificationUrl") or ml_cfg.get("notificationUrl") or "").strip()
    webhook_secret = str(ml_cfg.get("webhookSecret") or "").strip()

    if notification_url and webhook_secret:
        sep = "&" if "?" in notification_url else "?"
        if "webhookSecret=" not in notification_url:
            notification_url = f"{notification_url}{sep}webhookSecret={urllib.parse.quote(webhook_secret, safe='')}"

    mp_payload = {
        "items": [
            {
                # Fallback seguro para el título
                "title": str(i.get("name") or f"Producto {i.get('productId', '')}").strip(), 
                "quantity": int(i.get("quantity", 1) or 1),
                "unit_price": float(i.get("price", 0)), 
                "currency_id": "MXN"
            }
            for i in order.get("items", [])
        ],
        "external_reference": order_id,
        "metadata": {
            "orderId": order_id,
            "customerId": str(order.get("customerId") or "")
        },
        "auto_return": "approved",
    }

    # Asignar back_urls si existen
    if success_url or failure_url or pending_url:
        mp_payload["back_urls"] = {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        }

    # Asignar webhook
    if notification_url:
        mp_payload["notification_url"] = notification_url

    headers = {"Authorization": f"Bearer {ML_TOKEN}", "Content-Type": "application/json"}
    
    req = urllib.request.Request(
        "https://api.mercadopago.com/checkout/preferences",
        data=json.dumps(mp_payload, default=utils._json_default).encode(), 
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            result = json.loads(res.read().decode())
            # Actualizar orden con datos del proveedor
            utils._update_by_id(
                "ORDER", order_id, 
                "SET paymentProvider = :pp, paymentPreferenceId = :id, paymentInitPoint = :ip", 
                {
                    ":pp": "mercadolibre", 
                    ":id": result["id"], 
                    ":ip": result.get("init_point")
                }
            )
            preference_id = result["id"]
            init_point = result.get("init_point")
            sandbox_init_point = result.get("sandbox_init_point")
            return utils._json_response(200, {
                "orderId": order_id,
                "checkout": {
                    "provider": "mercadolibre",
                    "preferenceId": preference_id,
                    "initPoint": init_point,
                    "sandboxInitPoint": sandbox_init_point,
                    "externalReference": order_id,
                },
                "preferenceId": preference_id,
                "init_point": init_point,
                "sandbox_init_point": sandbox_init_point,
            })
            
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode()
        print(f"[Checkout] HTTPError {exc.code}: {err_msg}")
        return utils._json_response(502, {"message": "Error al comunicarse con Mercado Libre", "provider_error": err_msg})
    except Exception as e:
        print(f"[Checkout] Error: {e}")
        return utils._json_response(500, {"message": str(e)})


# ---------------------------------------------------------------------------
# HANDLER — CANCELACIÓN (Regla 2.1 y 2.2)
# ---------------------------------------------------------------------------

def handle_cancel_order(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/cancel

    Regla 2.1: Solo si status == 'paid' → cancelación automática
    Regla 2.2: Cualquier otro estado → 409 bloqueado
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    current_status = (order.get("status") or "").lower()

    # REGLA 2.2 — Bloqueado
    if current_status != "paid":
        if current_status in ("shipped", "delivered", "en_devolucion", "devuelto_validado", "devolucion_rechazada"):
            return utils._json_response(409, {
                "message": "Pedido en proceso logístico, solicitar devolución",
                "code": "LOGISTIC_IN_PROGRESS",
            })
        if current_status in ("cancelled", "canceled"):
            return utils._json_response(409, {"message": "El pedido ya fue cancelado.", "code": "ALREADY_CANCELLED"})
        if current_status == "refunded":
            return utils._json_response(409, {"message": "El pedido ya fue reembolsado.", "code": "ALREADY_REFUNDED"})
        return utils._json_response(409, {
            "message": f"No se puede cancelar un pedido en estado '{current_status}'. Solo se permiten cancelaciones de órdenes pagadas.",
            "code": "INVALID_STATUS_FOR_CANCEL",
        })

    # REGLA 2.1 — Cancelación automática
    reason = body.get("reason") or "customer_request"
    now = utils._now_iso()

    updated_order = utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, cancelReason = :r, pendingRefund = :pr, cancelledAt = :ca, updatedAt = :u",
        {":s": "cancelled", ":r": reason, ":pr": True, ":ca": now, ":u": now},
        {"#s": "status"},
    )
    utils._upsert_order_customer_history(updated_order)

    # Void commissions
    commission_actions = _void_commissions_for_order(order_id, reason="cancel")

    # Trigger Step Functions (notify admin, etc.)
    if ORDER_SFN_ARN:
        try:
            sfn.start_execution(
                stateMachineArn=ORDER_SFN_ARN,
                input=json.dumps({"orderId": order_id, "action": "ORDER_CANCELLED", "payload": body}),
            )
        except Exception as e:
            print(f"[SFN_CANCEL_ERROR] {e}")

    utils._audit_event("order.cancel", headers, body, {"orderId": order_id, "reason": reason})

    return utils._json_response(200, {
        "ok": True,
        "orderId": order_id,
        "status": "cancelled",
        "pendingRefund": True,
        "commissionActions": commission_actions,
    })


# ---------------------------------------------------------------------------
# HANDLER — SOLICITUD DE DEVOLUCIÓN (Reglas 3.1, 3.2, 3.3, 4)
# ---------------------------------------------------------------------------

def handle_return_request(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/return

    Regla 3.1: Validación de tiempo (48h daños/error, 7d desistimiento)
    Regla 3.3: Evidencia obligatoria (3 categorías)
    Regla 4:   Costo logístico según motivo
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    current_status = (order.get("status") or "").lower()
    if current_status != "delivered":
        return utils._json_response(409, {
            "message": "Solo se pueden solicitar devoluciones de pedidos entregados.",
            "code": "NOT_DELIVERED",
        })

    # Validar que no haya solicitud activa
    if order.get("returnRequestId"):
        return utils._json_response(409, {
            "message": "Ya existe una solicitud de devolución activa para este pedido.",
            "code": "RETURN_ALREADY_EXISTS",
        })

    motivo = (body.get("motivo") or "").upper().strip()
    valid_motivos = {"DANADO_DEFECTUOSO", "ERROR_ENVIO", "DESISTIMIENTO"}
    if motivo not in valid_motivos:
        return utils._json_response(400, {
            "message": "Motivo inválido. Use: DANADO_DEFECTUOSO, ERROR_ENVIO o DESISTIMIENTO.",
            "code": "INVALID_MOTIVO",
        })

    # REGLA 3.1 — Validación de tiempo
    delivered_at = order.get("deliveredAt") or order.get("updatedAt") or utils._now_iso()
    try:
        delivered_dt = datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        hours_since = (now_dt - delivered_dt).total_seconds() / 3600
        days_since = hours_since / 24
    except Exception:
        hours_since = 0.0
        days_since = 0.0

    if motivo in ("DANADO_DEFECTUOSO", "ERROR_ENVIO"):
        if hours_since > 48:
            return utils._json_response(409, {
                "message": f"Han transcurrido {int(hours_since)} horas desde la entrega. El plazo máximo para reportar daños o errores es 48 horas.",
                "code": "TIME_EXPIRED",
                "hoursSinceDelivery": float(hours_since),
            })
    elif motivo == "DESISTIMIENTO":
        if days_since > 7:
            return utils._json_response(409, {
                "message": f"Han transcurrido {int(days_since)} días desde la entrega. El plazo máximo para desistimiento es 7 días.",
                "code": "TIME_EXPIRED",
                "daysSinceDelivery": float(days_since),
            })

    # REGLA 3.3 — Validación de evidencia
    evidence_raw = body.get("evidence") or {}
    fotos_producto = evidence_raw.get("fotos_producto") or []
    fotos_empaque = evidence_raw.get("fotos_empaque") or []
    fotos_guia = evidence_raw.get("fotos_guia_envio") or []

    missing = []
    if not fotos_producto: missing.append("fotos_producto")
    if not fotos_empaque: missing.append("fotos_empaque")
    if not fotos_guia: missing.append("fotos_guia_envio")

    if missing:
        return utils._json_response(400, {
            "message": f"Evidencia incompleta. Faltan: {', '.join(missing)}",
            "code": "MISSING_EVIDENCE",
            "missing": missing,
        })

    # REGLA 4 — Costo logístico
    shipping_responsibility = "empresa" if motivo in ("DANADO_DEFECTUOSO", "ERROR_ENVIO") else "cliente"

    # Subir evidencias a S3
    request_id = f"RET-{utils.uuid.uuid4().hex[:8].upper()}"
    uploaded_evidence = {}

    def _upload_one(category, i, f):
        if isinstance(f, dict):
            cb64 = f.get("contentBase64", "")
            ct = f.get("contentType", "image/jpeg")
            fname = f.get("fileName", f"{category}_{i + 1}.jpg")
        else:
            cb64, ct, fname = str(f), "image/jpeg", f"{category}_{i + 1}.jpg"
        try:
            asset = _upload_evidence_s3(
                fname, cb64, ct,
                prefix=f"devoluciones/{order_id}/{request_id}/{category}",
            )
            return category, i, asset["url"]
        except Exception as e:
            print(f"[S3_EVIDENCE] {e}")
            return category, i, None

    upload_tasks = []
    for category, files in [
        ("fotos_producto", fotos_producto),
        ("fotos_empaque", fotos_empaque),
        ("fotos_guia_envio", fotos_guia),
    ]:
        uploaded_evidence[category] = []
        for i, f in enumerate(files):
            upload_tasks.append((category, i, f))

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_upload_one, cat, i, f): (cat, i) for cat, i, f in upload_tasks}
        for future in as_completed(futures):
            cat, i, url = future.result()
            if url:
                uploaded_evidence[cat].append(url)

    # Crear entidad RETURN_REQUEST
    now = utils._now_iso()
    return_item = {
        "entityType": "returnRequest",
        "requestId": request_id,
        "orderId": order_id,
        "customerId": order.get("customerId"),
        "motivo": motivo,
        "descripcion": body.get("descripcion") or "",
        "status": "PENDIENTE",
        "shippingResponsibility": shipping_responsibility,
        "evidence": uploaded_evidence,
        "horasDesdEntrega": Decimal(str(round(hours_since, 4))),
        "inspection": None,
        "createdAt": now,
        "updatedAt": now,
    }
    utils._put_entity("RETURN_REQUEST", request_id, return_item, created_at_iso=now)

    # Actualizar orden → EN_DEVOLUCION
    updated_order = utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, returnRequestId = :rid, updatedAt = :u",
        {":s": "en_devolucion", ":rid": request_id, ":u": now},
        {"#s": "status"},
    )
    utils._upsert_order_customer_history(updated_order)

    utils._audit_event("order.return_request", headers, body,
                       {"orderId": order_id, "requestId": request_id, "motivo": motivo})

    return utils._json_response(201, {
        "ok": True,
        "requestId": request_id,
        "status": "PENDIENTE",
        "shippingResponsibility": shipping_responsibility,
        "message": (
            "Solicitud de devolución registrada. Te notificaremos el resultado de la inspección. "
            + ("El costo de envío de la devolución corre a cargo de la empresa."
               if shipping_responsibility == "empresa"
               else "El costo de envío de la devolución corre a tu cargo.")
        ),
    })


# ---------------------------------------------------------------------------
# HANDLER — INSPECCIÓN BACKOFFICE (Reglas 5.1, 5.2)
# ---------------------------------------------------------------------------

def handle_return_inspection(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/return/inspect

    Regla 5.1: Todas validaciones OK → DEVUELTO_VALIDADO + void commissions
    Regla 5.2: Cualquier validación falla → DEVOLUCION_RECHAZADA
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    request_id = order.get("returnRequestId")
    if not request_id:
        return utils._json_response(404, {"message": "No hay solicitud de devolución activa para este pedido."})

    return_req = utils._get_by_id("RETURN_REQUEST", request_id)
    if not return_req:
        return utils._json_response(404, {"message": "Solicitud de devolución no encontrada."})

    inspection = body.get("inspection") or {}

    # Checklist de recepción (Regla 3.2 / Paso 2 - Inspección física)
    empaque_original = bool(inspection.get("empaque_original"))
    sellos_intactos = bool(inspection.get("sellos_intactos"))
    sin_uso = bool(inspection.get("sin_uso"))

    # Checklist de validación interna
    producto_abierto = bool(inspection.get("producto_abierto"))   # Falla si True
    danio_no_empresa = bool(inspection.get("danio_no_empresa"))   # Falla si True
    coincide_con_pedido = bool(inspection.get("coincide_con_pedido"))
    trazabilidad_valida = bool(inspection.get("trazabilidad_valida"))

    # Regla 5.1 / 5.2
    approved = (
        empaque_original and
        sellos_intactos and
        sin_uso and
        not producto_abierto and
        not danio_no_empresa and
        coincide_con_pedido and
        trazabilidad_valida
    )

    now = utils._now_iso()
    new_return_status = "DEVUELTO_VALIDADO" if approved else "DEVOLUCION_RECHAZADA"
    new_order_status = "devuelto_validado" if approved else "devolucion_rechazada"
    actor_header = (headers or {})
    actor = actor_header.get("x-user-id") or actor_header.get("x-actor-id") or "admin"

    # Subir imágenes del paquete recibido si se proporcionan
    package_image_urls = []
    for i, img in enumerate(body.get("packageImages") or []):
        if isinstance(img, dict):
            cb64 = img.get("contentBase64", "")
            ct = img.get("contentType", "image/jpeg")
            fname = img.get("fileName", f"paquete_{i+1}.jpg")
        else:
            cb64, ct, fname = str(img), "image/jpeg", f"paquete_{i+1}.jpg"
        try:
            asset = _upload_evidence_s3(
                fname, cb64, ct,
                prefix=f"devoluciones/{order_id}/{request_id}/paquete_recibido",
            )
            package_image_urls.append(asset["url"])
        except Exception as e:
            print(f"[S3_PACKAGE_IMG] {e}")

    inspection_record = {**inspection}
    if package_image_urls:
        inspection_record["packageImageUrls"] = package_image_urls

    # Motivo de rechazo opcional (cuando admin rechaza desde devuelto_validado)
    rejection_reason = (body.get("rejectionReason") or "").strip()

    utils._update_by_id(
        "RETURN_REQUEST", request_id,
        "SET #s = :s, inspection = :i, inspectedAt = :ia, inspectedBy = :ib, updatedAt = :u",
        {":s": new_return_status, ":i": inspection_record, ":ia": now, ":ib": actor, ":u": now},
        {"#s": "status"},
    )

    order_update_expr = "SET #s = :s, updatedAt = :u"
    order_eav = {":s": new_order_status, ":u": now}
    if not approved and rejection_reason:
        order_update_expr += ", rejectionReason = :rr, rejectedAt = :ra"
        order_eav[":rr"] = rejection_reason
        order_eav[":ra"] = now

    updated_order = utils._update_by_id(
        "ORDER", order_id, order_update_expr, order_eav, {"#s": "status"},
    )
    utils._upsert_order_customer_history(updated_order)

    commission_actions = []
    if approved:
        commission_actions = _void_commissions_for_order(order_id, reason="return_approved")

    utils._audit_event("order.return_inspected", headers, body, {
        "orderId": order_id, "requestId": request_id, "approved": approved,
    })

    return utils._json_response(200, {
        "ok": True,
        "requestId": request_id,
        "returnStatus": new_return_status,
        "orderStatus": new_order_status,
        "approved": approved,
        "commissionActions": commission_actions,
        "message": (
            "Devolución aprobada. Las comisiones han sido revertidas."
            if approved
            else "Devolución rechazada. Se generará orden de reenvío al cliente con costo a su cargo."
        ),
    })


def handle_refund_order(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/refund
    Acepta un comprobante de depósito (receiptBase64) para registrar el reembolso.
    Puede llamarse desde órdenes canceladas o con devolución validada.
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    allowed_statuses = {"cancelled", "canceled", "devuelto_validado"}
    current_status = (order.get("status") or "").lower()
    if current_status not in allowed_statuses:
        return utils._json_response(409, {
            "message": f"No se puede reembolsar un pedido en estado '{current_status}'. Solo cancelados o devoluciones validadas.",
            "code": "INVALID_STATUS_FOR_REFUND",
        })

    now = utils._now_iso()
    refund_receipt_url = None

    # Subir comprobante de depósito si se proporciona
    receipt_b64 = (body.get("receiptBase64") or "").strip()
    if receipt_b64:
        receipt_name = body.get("receiptName") or "comprobante_reembolso.jpg"
        receipt_ct = body.get("receiptContentType") or "image/jpeg"
        try:
            asset = _upload_evidence_s3(
                receipt_name, receipt_b64, receipt_ct,
                prefix=f"reembolsos/{order_id}",
            )
            refund_receipt_url = asset["url"]
        except Exception as e:
            print(f"[S3_REFUND_RECEIPT] {e}")
            return utils._json_response(400, {"message": "No se pudo procesar el comprobante de depósito.", "detail": str(e)})

    update_expr = "SET #s = :s, refundReason = :r, refundedAt = :ra, updatedAt = :u"
    eav = {":s": "refunded", ":r": body.get("reason") or "refund", ":ra": now, ":u": now}
    if refund_receipt_url:
        update_expr += ", refundReceiptUrl = :rru"
        eav[":rru"] = refund_receipt_url

    updated_order = utils._update_by_id("ORDER", order_id, update_expr, eav, {"#s": "status"})
    utils._upsert_order_customer_history(updated_order)
    actions = _void_commissions_for_order(order_id, reason="refund")
    utils._audit_event("order.refund", headers, body, {"orderId": order_id})
    return utils._json_response(200, {
        "orderId": order_id,
        "status": "refunded",
        "refundReceiptUrl": refund_receipt_url,
        "commissionActions": actions,
    })


def handle_mp_webhook(query, body):
    """POST /webhooks/mercadolibre"""
    topic = query.get("topic") or body.get("type")
    resource_id = query.get("id") or body.get("data", {}).get("id")

    if topic == "payment" and resource_id:
        req = urllib.request.Request(
            f"https://api.mercadopago.com/v1/payments/{resource_id}",
            headers={"Authorization": f"Bearer {ML_TOKEN}"},
        )
        with urllib.request.urlopen(req) as res:
            payment_info = json.loads(res.read().decode())
        status = payment_info.get("status")
        order_id = payment_info.get("external_reference")
        if status == "approved" and order_id:
            return handle_update_status(order_id, {"status": "paid", "paymentId": resource_id}, {})

    return utils._json_response(200, {"ok": True})


# ---------------------------------------------------------------------------
# LAMBDA ROUTER
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    segments = [s for s in path.strip("/").split("/") if s]
    print(segments)
    try:
        if "webhooks" in segments:
            return handle_mp_webhook(query, body)

        if "orders" in segments:
            # /orders (legacy alias) and /orders/find
            

            if len(segments) == 2 and segments[1] == "find" and method == "GET":
                actor = utils._extract_actor(headers)
                return handle_list_orders(actor.get("user_id"), query, headers)
            
            if len(segments) == 1:
                if method == "POST":
                    actor = utils._extract_actor(headers)
                    if actor.get("user_id"):
                        err = utils._require_self_or_admin(headers, body.get("customerId"))
                        if err: return err
                    return handle_create_order(body, headers)
                if method == "GET":
                    actor = utils._extract_actor(headers)
                    return handle_list_orders(actor.get("user_id"), query, headers)

            if len(segments) == 2 and segments[1] == "create" and method == "POST":
                actor = utils._extract_actor(headers)
                if actor.get("user_id"):
                    err = utils._require_self_or_admin(headers, body.get("customerId"))
                    if err: return err
                return handle_create_order(body, headers)

            order_id = segments[1]

            # /orders/{id}
            if len(segments) == 2:
                if method == "GET":
                    order = utils._get_by_id("ORDER", order_id)
                    if not order:
                        return utils._json_response(404, {"message": "Pedido no encontrado"})
                    err = utils._require_self_or_admin(headers, order.get("customerId"))
                    if err: return err
                    return utils._json_response(200, {"order": order})
                if method == "PATCH":
                    err = utils._require_admin(headers, "order_mark_paid")
                    if err: return err
                    return handle_update_status(order_id, body, headers)

            # /orders/{id}/...
            if len(segments) >= 3:
                sub = segments[2]
                if sub == "checkout" and method == "POST":
                    # Checkout: el propio cliente o admin pueden iniciarlo
                    order = utils._get_by_id("ORDER", order_id)
                    if order:
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    return handle_mercadopago_checkout(order_id, body)
                if sub == "refund" and method == "POST":
                    err = utils._require_admin(headers, "order_mark_paid")
                    if err: return err
                    return handle_refund_order(order_id, body, headers)
                if sub == "cancel" and method == "POST":
                    order = utils._get_by_id("ORDER", order_id)
                    if order:
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    return handle_cancel_order(order_id, body, headers)
                if sub == "return" and method == "POST":
                    if len(segments) == 4 and segments[3] == "inspect":
                        err = utils._require_admin(headers, "access_screen_orders")
                        if err: return err
                        return handle_return_inspection(order_id, body, headers)
                    order = utils._get_by_id("ORDER", order_id)
                    if order:
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    return handle_return_request(order_id, body, headers)
                if sub == "status":
                    order = utils._get_by_id("ORDER", order_id)
                    if not order:
                        return utils._json_response(404, {"message": "Pedido no encontrado"})
                    err = utils._require_self_or_admin(headers, order.get("customerId"))
                    if err: return err
                    return utils._json_response(200, {
                        "status": order.get("status"),
                        "payment": order.get("paymentStatus"),
                    })

        return utils._json_response(404, {"message": "Ruta no encontrada en Order Service"})

    except Exception as e:
        print(f"[ORDER_ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Critical Error", "error": str(e)})
