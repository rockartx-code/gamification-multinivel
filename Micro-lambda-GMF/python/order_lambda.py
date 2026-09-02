import base64
import json
import boto3
import urllib.error
import urllib.parse
import urllib.request
import core_utils as utils  # Importado desde la Layer
from core import order_emails
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

MAX_COMMISSION_LEVELS = 5  # Plan abril 2026: 5 generaciones
DEFAULT_ORDER_HISTORY_PAGE_SIZE = 10
MAX_ORDER_HISTORY_PAGE_SIZE = 50        # clientes
MAX_ADMIN_ORDER_PAGE_SIZE = 500         # admins

# ---------------------------------------------------------------------------
# HELPERS DE LÓGICA DE NEGOCIO
# ---------------------------------------------------------------------------

def _enrich_items_commissionable(items: list) -> list:
    """
    Añade commissionable y vpPoints a cada ítem según el catálogo de productos.
    Si el producto no se encuentra, se asume commissionable=True y vpPoints=None.
    """
    enriched = []
    for it in items:
        item = dict(it) if isinstance(it, dict) else {}
        pid = item.get("productId")
        if pid is not None:
            product = utils._get_by_id("PRODUCT", pid)
            if product:
                if "commissionable" not in item:
                    item["commissionable"] = bool(product.get("commissionable", True))
                if "vpPoints" not in item and product.get("vpPoints") is not None:
                    # Decimal, no float: el serializador de DynamoDB rechaza floats y
                    # el pedido entero fallaba con "Float types are not supported"
                    # para cualquier producto con puntos, sea invitado o socio.
                    item["vpPoints"] = utils._to_decimal(product["vpPoints"])
        enriched.append(item)
    return enriched


def _resolve_discount_rate(discount_tiers, basis) -> utils.Decimal:
    """
    Devuelve la tasa de descuento de la escalera (Plan abril 2026 §3) para un MPN `basis`.
    `basis` = MPN acumulado del mes + monto de la compra actual. Sin retroactividad:
    el nivel resultante aplica a TODA la compra actual.
    """
    rate = utils.Decimal("0.0")
    for tier in sorted(discount_tiers, key=lambda t: float(utils._to_decimal(t.get("min", 0)))):
        t_min = utils._to_decimal(tier.get("min", 0))
        t_max = tier.get("max")
        t_max_d = utils._to_decimal(t_max) if t_max is not None else None
        if basis >= t_min and (t_max_d is None or basis < t_max_d):
            rate = utils._to_decimal(tier.get("rate", 0))
            break
    return rate


def _calculate_totals(items, customer_id, buyer_type):
    gross = utils.D_ZERO
    for it in items:
        price = utils._to_decimal(it.get("price", 0))
        qty = int(it.get("quantity", 1))
        gross += price * qty

    cfg = utils._load_app_config().get("rewards", {})
    rate = utils.Decimal("0.0")

    if buyer_type in ["associate", "registered"] and customer_id:
        discount_tiers = cfg.get("discountTiers") or []
        # MPN previo acumulado del mes (neto pagado en compras personales).
        month_key = utils._month_key()
        m_state = utils._get_by_id(
            "ASSOCIATE_MONTH", utils._associate_month_entity_id(customer_id, month_key)
        ) or {}
        prior_mpn = utils._to_decimal(m_state.get("netVolume", 0))
        # El nivel se determina sumando el acumulado previo + la compra actual (bruto).
        basis = prior_mpn + gross
        rate = _resolve_discount_rate(discount_tiers, basis)

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
    for beneficiary_id in beneficiaries:
        # Mismo bloqueo optimista que el resto de escrituras del ledger: antes
        # esto era un read-modify-write con deltas que podía descuadrar los
        # totales si otra orden escribía el mismo mes a la vez.
        try:
            summary = utils._void_ledger_rows_for_order(beneficiary_id, month_key, order_id)
        except Exception as e:
            utils._log("void_comm_error", "ERROR", beneficiary=beneficiary_id, err=e)
            continue
        if not summary:
            continue
        out.append({
            "action": "void",
            "beneficiaryId": beneficiary_id,
            "orderId": order_id,
            "removed": summary.get("removedRows"),
            "pendingRemoved": summary.get("pendingRemoved"),
            "confirmedRemoved": summary.get("confirmedRemoved"),
            "blockedRemoved": summary.get("blockedRemoved"),
            "reason": reason,
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
    # El frontend no manda buyerType, así que TODO pedido llegaba como "guest",
    # también los de socios con sesión: sin descuento por escalera, sin volumen
    # personal y sin activación mensual. El tipo de comprador se decide por el
    # customerId, no por lo que diga el cliente.
    if customer_id and buyer_type == "guest" and utils._get_by_id("CUSTOMER", customer_id):
        buyer_type = "associate"

    if customer_id and buyer_type != "guest":
        utils._get_by_id("CUSTOMER", customer_id)

    raw_items = body.get("items", [])
    # Enriquecer ítems con la bandera commissionable del catálogo
    enriched_items = _enrich_items_commissionable(raw_items)
    totals = _calculate_totals(enriched_items, customer_id, buyer_type)
    # Cupón / código de descuento (H7): reduce el neto pagado (y por tanto PC/comisiones).
    coupon_fields = _apply_coupon_to_totals(body.get("couponCode"), totals, customer_id)
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
        # Sin esto el pedido de un invitado no tenía a quién escribirle.
        "email": str(body.get("email") or body.get("customerEmail") or shipping_address.get("email") or "").strip().lower() or None,
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
        # El frontend cotiza y manda el envío, pero el pedido lo descartaba: el
        # seguimiento mostraba $960 donde el carrito cobró $1,089 y la
        # pasarela cobraba solo los productos. netTotal sigue siendo la base
        # comisionable (el envío no genera comisión); total es lo que se paga.
        "shippingCost": utils._to_decimal(body.get("shippingCost") or 0),
        "shippingCarrier": body.get("shippingCarrier") or None,
        "shippingService": body.get("shippingService") or None,
        "total": (totals["netTotal"] + utils._to_decimal(body.get("shippingCost") or 0)).quantize(utils.D_CENT),
        **coupon_fields,
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
            utils._log_error("step_functions_start_failed", e, orderId=order_id)

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
    if new_status in ("paid", "shipped", "delivered") and (order.get("status") or "").lower() != new_status:
        _avisar(updated, new_status, body)
    return utils._json_response(200, {"order": updated})


def _avisar(order: dict, evento: str, datos: dict | None = None) -> None:
    """Correo al comprador por cada paso del pedido (docs/qa/18: no existía ninguno)."""
    order_emails.notificar_pedido(
        order or {}, evento, datos,
        lambda cid: utils._get_by_id("CUSTOMER", cid),
        utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx"),
    )


def _con_totales_visibles(order: dict) -> dict:
    """El item guarda grossSubtotal/netTotal; las pantallas leen subtotal/total."""
    return {
        **order,
        "subtotal": order.get("subtotal") if order.get("subtotal") is not None else order.get("grossSubtotal"),
        "total": order.get("total") if order.get("total") is not None else order.get("netTotal"),
    }


def _is_guest_order(order: dict) -> bool:
    """Pedido creado sin cuenta: buyerType guest o sin customerId."""
    return str(order.get("buyerType") or "").lower() == "guest" or not order.get("customerId")


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
        ] + ([{
            "title": f"Envío ({order.get('shippingCarrier') or 'paquetería'})",
            "quantity": 1,
            "unit_price": float(utils._to_decimal(order.get("shippingCost"))),
        }] if utils._to_decimal(order.get("shippingCost")) > 0 else []),
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
        utils._log("mercadopago_checkout_http_error", "ERROR",
                   status=exc.code, body=err_msg)
        return utils._json_response(502, {"message": "Error al comunicarse con Mercado Libre", "provider_error": err_msg})
    except Exception as e:
        utils._log_error("mercadopago_checkout_failed", e)
        return utils._json_response(500, {"message": str(e)})


# ---------------------------------------------------------------------------
# HANDLER — CANCELACIÓN (Regla 2.1 y 2.2)
# ---------------------------------------------------------------------------

def handle_cancel_order(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/cancel

    Regla 2.1a: status == 'paid'    → cancelación con pendingRefund=True
    Regla 2.1b: status == 'pending' → cancelación sin reembolso (pago no confirmado)
    Regla 2.2:  Cualquier otro estado → 409 bloqueado
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    current_status = (order.get("status") or "").lower()

    # REGLA 2.2 — Bloqueado
    if current_status not in ("paid", "pending"):
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
            "message": f"No se puede cancelar un pedido en estado '{current_status}'.",
            "code": "INVALID_STATUS_FOR_CANCEL",
        })

    reason = body.get("reason") or "customer_request"
    now = utils._now_iso()

    # Órdenes pagadas generan reembolso pendiente; las pendientes no (pago no confirmado)
    pending_refund = current_status == "paid"

    updated_order = utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, cancelReason = :r, pendingRefund = :pr, cancelledAt = :ca, updatedAt = :u",
        {":s": "cancelled", ":r": reason, ":pr": pending_refund, ":ca": now, ":u": now},
        {"#s": "status"},
    )
    utils._upsert_order_customer_history(updated_order)

    # Void commissions solo si había pago confirmado
    commission_actions = _void_commissions_for_order(order_id, reason="cancel") if pending_refund else []

    # Trigger Step Functions (notify admin, etc.)
    if ORDER_SFN_ARN:
        try:
            sfn.start_execution(
                stateMachineArn=ORDER_SFN_ARN,
                input=json.dumps({"orderId": order_id, "action": "ORDER_CANCELLED", "payload": body}),
            )
        except Exception as e:
            utils._log_error("step_functions_cancel_failed", e, orderId=order_id)

    utils._audit_event("order.cancel", headers, body, {"orderId": order_id, "reason": reason, "previousStatus": current_status})
    _avisar(updated_order, "cancelled", {"pendingRefund": pending_refund})

    return utils._json_response(200, {
        "ok": True,
        "orderId": order_id,
        "status": "cancelled",
        "pendingRefund": pending_refund,
        "commissionActions": commission_actions,
    })


# ---------------------------------------------------------------------------
# HANDLER — SOLICITUD DE DEVOLUCIÓN (Reglas 3.1, 3.2, 3.3, 4)
# ---------------------------------------------------------------------------

#: Plazos máximos para solicitar devolución, por motivo (Regla 3.1).
RETURN_MOTIVOS = {
    "DANADO_DEFECTUOSO": {"limite_horas": 48, "responsable_envio": "empresa"},
    "ERROR_ENVIO": {"limite_horas": 48, "responsable_envio": "empresa"},
    "DESISTIMIENTO": {"limite_horas": 7 * 24, "responsable_envio": "cliente"},
}
#: Categorías de evidencia obligatorias (Regla 3.3).
RETURN_EVIDENCIA_REQUERIDA = ("fotos_producto", "fotos_empaque", "fotos_guia_envio")


def _horas_desde_entrega(order: dict) -> float:
    """Horas transcurridas desde que el pedido se marcó entregado."""
    entregado_en = order.get("deliveredAt") or order.get("updatedAt") or utils._now_iso()
    try:
        momento = datetime.fromisoformat(str(entregado_en).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - momento).total_seconds() / 3600
    except (TypeError, ValueError):
        return 0.0


def _validar_solicitud_devolucion(order: dict, motivo: str, evidencia: dict, horas: float):
    """Aplica las reglas 3.1 y 3.3. Devuelve una respuesta de error o None."""
    if (order.get("status") or "").lower() != utils.OrderStatus.DELIVERED:
        return utils._json_response(409, {
            "message": "Solo se pueden solicitar devoluciones de pedidos entregados.",
            "code": "NOT_DELIVERED",
        })

    if order.get("returnRequestId"):
        return utils._json_response(409, {
            "message": "Ya existe una solicitud de devolución activa para este pedido.",
            "code": "RETURN_ALREADY_EXISTS",
        })

    regla = RETURN_MOTIVOS.get(motivo)
    if not regla:
        return utils._json_response(400, {
            "message": "Motivo inválido. Use: " + ", ".join(RETURN_MOTIVOS) + ".",
            "code": "INVALID_MOTIVO",
        })

    # Regla 3.1 — plazo según el motivo
    if horas > regla["limite_horas"]:
        if regla["limite_horas"] >= 24:
            transcurrido = f"{int(horas / 24)} días"
            plazo = f"{regla['limite_horas'] // 24} días"
            campo = {"daysSinceDelivery": float(horas / 24)}
        else:
            transcurrido = f"{int(horas)} horas"
            plazo = f"{regla['limite_horas']} horas"
            campo = {"hoursSinceDelivery": float(horas)}
        return utils._json_response(409, {
            "message": f"Han transcurrido {transcurrido} desde la entrega. "
                       f"El plazo máximo para este motivo es {plazo}.",
            "code": "TIME_EXPIRED",
            **campo,
        })

    # Regla 3.3 — las tres categorías de evidencia son obligatorias
    faltantes = [c for c in RETURN_EVIDENCIA_REQUERIDA if not (evidencia.get(c) or [])]
    if faltantes:
        return utils._json_response(400, {
            "message": f"Evidencia incompleta. Faltan: {', '.join(faltantes)}",
            "code": "MISSING_EVIDENCE",
            "missing": faltantes,
        })
    return None


def _subir_evidencia_devolucion(order_id: str, request_id: str, evidencia: dict) -> dict:
    """Sube en paralelo las fotos de todas las categorías y devuelve sus URLs."""
    def _subir_una(categoria, indice, archivo):
        if isinstance(archivo, dict):
            contenido = archivo.get("contentBase64", "")
            tipo = archivo.get("contentType", "image/jpeg")
            nombre = archivo.get("fileName", f"{categoria}_{indice + 1}.jpg")
        else:
            contenido, tipo = str(archivo), "image/jpeg"
            nombre = f"{categoria}_{indice + 1}.jpg"
        try:
            asset = _upload_evidence_s3(
                nombre, contenido, tipo,
                prefix=f"devoluciones/{order_id}/{request_id}/{categoria}",
            )
            return categoria, asset["url"]
        except Exception as ex:
            utils._log_error("return_evidence_upload_failed", ex,
                             orderId=order_id, requestId=request_id, category=categoria)
            return categoria, None

    subidas = {categoria: [] for categoria in RETURN_EVIDENCIA_REQUERIDA}
    tareas = [
        (categoria, indice, archivo)
        for categoria in RETURN_EVIDENCIA_REQUERIDA
        for indice, archivo in enumerate(evidencia.get(categoria) or [])
    ]
    if not tareas:
        return subidas

    with ThreadPoolExecutor(max_workers=6) as executor:
        futuros = [executor.submit(_subir_una, *tarea) for tarea in tareas]
        for futuro in as_completed(futuros):
            categoria, url = futuro.result()
            if url:
                subidas[categoria].append(url)
    return subidas


def handle_return_request(order_id: str, body: dict, headers: dict) -> dict:
    """POST /orders/{id}/return — registra una solicitud de devolución.

    Reglas: 3.1 plazo según motivo, 3.3 evidencia obligatoria en las tres
    categorías, 4 responsabilidad del costo logístico. La validación vive en
    `_validar_solicitud_devolucion` y la subida de fotos en
    `_subir_evidencia_devolucion`.
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})

    motivo = (body.get("motivo") or "").upper().strip()
    evidencia = body.get("evidence") or {}
    horas = _horas_desde_entrega(order)

    error = _validar_solicitud_devolucion(order, motivo, evidencia, horas)
    if error:
        return error

    # Regla 4 — quién paga el envío de la devolución
    responsable = RETURN_MOTIVOS[motivo]["responsable_envio"]

    request_id = f"RET-{utils.uuid.uuid4().hex[:8].upper()}"
    subidas = _subir_evidencia_devolucion(order_id, request_id, evidencia)

    now = utils._now_iso()
    utils._put_entity("RETURN_REQUEST", request_id, {
        "entityType": "returnRequest",
        "requestId": request_id,
        "orderId": order_id,
        "customerId": order.get("customerId"),
        "motivo": motivo,
        "descripcion": body.get("descripcion") or "",
        "status": "PENDIENTE",
        "shippingResponsibility": responsable,
        "evidence": subidas,
        # Lo que el cliente pagó por regresar el paquete (ticket de paquetería);
        # se suma al reembolso por omisión.
        "returnShippingCost": utils._to_decimal(body.get("returnShippingCost") or 0),
        "horasDesdEntrega": Decimal(str(round(horas, 4))),
        "inspection": None,
        "createdAt": now,
        "updatedAt": now,
    }, created_at_iso=now)

    updated_order = utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, returnRequestId = :rid, returnShippingCost = :rsc, updatedAt = :u",
        {":s": "en_devolucion", ":rid": request_id, ":rsc": utils._to_decimal(body.get("returnShippingCost") or 0), ":u": now},
        {"#s": "status"},
    )
    utils._upsert_order_customer_history(updated_order)
    utils._audit_event("order.return_request", headers, body,
                       {"orderId": order_id, "requestId": request_id, "motivo": motivo})
    _avisar(utils._get_by_id("ORDER", order_id) or order, "return_received", {"requestId": request_id})

    return utils._json_response(201, {
        "ok": True,
        "requestId": request_id,
        "status": "PENDIENTE",
        "shippingResponsibility": responsable,
        "message": (
            "Solicitud de devolución registrada. Te notificaremos el resultado de la inspección. "
            + ("El costo de envío de la devolución corre a cargo de la empresa."
               if responsable == "empresa"
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
    _avisar(updated_order, "return_approved" if approved else "return_rejected",
            {"reason": body.get("reason") or body.get("motivo") or inspection.get("comentarios")})

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

    # Importe reembolsado: por omisión el total cobrado más el envío de regreso
    # que el cliente haya declarado en su solicitud de devolución. La gerente
    # reembolsaba "la única cifra que el sistema mostraba" y el cliente
    # reclamaba después su ticket de paquetería.
    importe_base = utils._to_decimal(order.get("total") if order.get("total") is not None else order.get("netTotal"))
    envio_regreso = utils._to_decimal(order.get("returnShippingCost") or 0)
    refund_amount = utils._to_decimal(body.get("amount")) if body.get("amount") not in (None, "") else importe_base + envio_regreso
    if refund_amount < utils.D_ZERO:
        return utils._json_response(400, {"message": "El importe del reembolso no puede ser negativo"})
    update_expr = "SET #s = :s, refundReason = :r, refundedAt = :ra, refundAmount = :amt, updatedAt = :u"
    eav = {":s": "refunded", ":r": body.get("reason") or "refund", ":ra": now, ":amt": refund_amount, ":u": now}
    if refund_receipt_url:
        update_expr += ", refundReceiptUrl = :rru"
        eav[":rru"] = refund_receipt_url

    updated_order = utils._update_by_id("ORDER", order_id, update_expr, eav, {"#s": "status"})
    utils._upsert_order_customer_history(updated_order)
    actions = _void_commissions_for_order(order_id, reason="refund")
    utils._audit_event("order.refund", headers, body, {"orderId": order_id})
    _avisar(updated_order, "refunded", {"amount": updated_order.get("refundAmount") or updated_order.get("total") or updated_order.get("netTotal")})
    return utils._json_response(200, {
        "orderId": order_id,
        "status": "refunded",
        "refundAmount": refund_amount,
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

# ---------------------------------------------------------------------------
# CUPONES / CÓDIGOS DE DESCUENTO (H7)
# ---------------------------------------------------------------------------

def _coupon_code(raw) -> str:
    return str(raw or "").strip().upper()


def _evaluate_coupon(coupon: dict, subtotal, customer_id=None) -> dict:
    """
    Devuelve {'valid': bool, 'message': str, 'discount': Decimal} para un cupón.
    `subtotal` es la base (neto tras descuento por volumen) sobre la que aplica el cupón.
    """
    if not coupon:
        return {"valid": False, "message": "Cupón no encontrado", "discount": utils.D_ZERO}
    if not coupon.get("active", True):
        return {"valid": False, "message": "Cupón inactivo", "discount": utils.D_ZERO}

    now = utils._now_iso()
    valid_from = coupon.get("validFrom")
    valid_to = coupon.get("validTo")
    if valid_from and now < str(valid_from):
        return {"valid": False, "message": "Cupón aún no vigente", "discount": utils.D_ZERO}
    if valid_to and now > str(valid_to):
        return {"valid": False, "message": "Cupón expirado", "discount": utils.D_ZERO}

    subtotal_d = utils._to_decimal(subtotal)
    min_subtotal = utils._to_decimal(coupon.get("minSubtotal", 0))
    if subtotal_d < min_subtotal:
        return {"valid": False, "message": f"Requiere subtotal mínimo de ${min_subtotal}", "discount": utils.D_ZERO}

    max_red = coupon.get("maxRedemptions")
    if max_red is not None and int(coupon.get("redemptions", 0)) >= int(max_red):
        return {"valid": False, "message": "Cupón agotado", "discount": utils.D_ZERO}

    ctype = (coupon.get("type") or "percent").lower()
    value = utils._to_decimal(coupon.get("value", 0))
    if ctype == "percent":
        discount = (subtotal_d * value / utils.Decimal("100")).quantize(utils.D_CENT)
    else:  # fixed
        discount = value.quantize(utils.D_CENT)
    # Nunca descontar más que el subtotal.
    if discount > subtotal_d:
        discount = subtotal_d
    if discount <= utils.D_ZERO:
        return {"valid": False, "message": "Cupón sin descuento aplicable", "discount": utils.D_ZERO}

    return {"valid": True, "message": "Cupón aplicado", "discount": discount}


def handle_validate_coupon(body) -> dict:
    """POST /coupons/validate — valida un cupón sin consumirlo."""
    code = _coupon_code(body.get("code"))
    if not code:
        return utils._json_response(400, {"valid": False, "message": "Código requerido"})
    subtotal = body.get("subtotal", 0)
    coupon = utils._get_by_id("COUPON", code)
    result = _evaluate_coupon(coupon, subtotal, body.get("customerId"))
    status = 200 if result["valid"] else 200  # siempre 200; el front lee 'valid'
    return utils._json_response(status, {
        "valid": result["valid"],
        "message": result["message"],
        "discount": float(result["discount"]),
        "code": code,
        "type": (coupon or {}).get("type"),
        "value": float(utils._to_decimal((coupon or {}).get("value", 0))),
    })


def handle_list_coupons() -> dict:
    """GET /coupons — listado (admin)."""
    coupons = utils._query_bucket("COUPON")
    return utils._json_response(200, {"coupons": coupons})


def handle_save_coupon(body) -> dict:
    """POST /coupons — crear/actualizar (admin)."""
    code = _coupon_code(body.get("code"))
    if not code:
        return utils._json_response(400, {"message": "Código requerido"})
    ctype = (body.get("type") or "percent").lower()
    if ctype not in ("percent", "fixed"):
        return utils._json_response(400, {"message": "type debe ser 'percent' o 'fixed'"})

    existing = utils._get_by_id("COUPON", code) or {}
    now = utils._now_iso()
    item = {
        "entityType": "coupon",
        "code": code,
        "type": ctype,
        "value": utils._to_decimal(body.get("value", 0)),
        "active": bool(body.get("active", True)),
        "minSubtotal": utils._to_decimal(body.get("minSubtotal", 0)),
        "maxRedemptions": int(body["maxRedemptions"]) if body.get("maxRedemptions") not in (None, "") else None,
        "redemptions": int(existing.get("redemptions", 0)),
        "validFrom": body.get("validFrom") or existing.get("validFrom"),
        "validTo": body.get("validTo") or existing.get("validTo"),
        "description": body.get("description") or "",
        "updatedAt": now,
    }
    saved = utils._put_entity("COUPON", code, item, created_at_iso=existing.get("createdAt"))
    utils._audit_event("coupon.save", None, body, {"code": code})
    return utils._json_response(201, {"coupon": saved})


def handle_delete_coupon(code) -> dict:
    """DELETE /coupons/{code} (admin)."""
    code = _coupon_code(code)
    existing = utils._get_by_id("COUPON", code)
    if not existing:
        return utils._json_response(404, {"message": "Cupón no encontrado"})
    item = dict(existing)
    item["active"] = False
    item["updatedAt"] = utils._now_iso()
    utils._put_entity("COUPON", code, item, created_at_iso=existing.get("createdAt"))
    return utils._json_response(200, {"message": "Cupón desactivado", "code": code})


def _apply_coupon_to_totals(coupon_code: str, totals: dict, customer_id=None) -> dict:
    """
    Aplica un cupón sobre el neto (tras descuento por volumen). Reduce `netTotal`
    porque los PC y comisiones se calculan sobre el neto efectivamente pagado
    (Plan abril 2026 §2). Devuelve campos extra para la orden.
    """
    code = _coupon_code(coupon_code)
    if not code:
        return {}
    coupon = utils._get_by_id("COUPON", code)
    base = totals.get("netTotal", utils.D_ZERO)
    result = _evaluate_coupon(coupon, base, customer_id)
    if not result["valid"]:
        return {"couponCode": code, "couponDiscount": utils.D_ZERO, "couponMessage": result["message"]}
    discount = result["discount"]
    totals["netTotal"] = (utils._to_decimal(base) - discount).quantize(utils.D_CENT)
    # Consumir una redención.
    try:
        item = dict(coupon)
        item["redemptions"] = int(coupon.get("redemptions", 0)) + 1
        item["updatedAt"] = utils._now_iso()
        utils._put_entity("COUPON", code, item, created_at_iso=coupon.get("createdAt"))
    except Exception as e:
        utils._log_error("coupon_redeem_failed", e, code=code)
    return {"couponCode": code, "couponDiscount": discount, "couponMessage": result["message"]}


def lambda_handler(event, context):
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return utils._cors_preflight_response()
    request = utils._http_request(event)
    method = request.method
    body, query, headers = request.body, request.query, request.headers
    segments = request.segments
    try:
        if "webhooks" in segments:
            return handle_mp_webhook(query, body)

        if "coupons" in segments:
            # API Gateway solo enruta /orders/{proxy+} a esta Lambda: la ruta
            # /coupons a secas nunca llegaba en producción y el frontend la
            # llamaba tal cual (cupones muertos). Se acepta /orders/coupons/...
            # y se conserva /coupons/... para invocación directa.
            if segments and segments[0] == "orders":
                segments = segments[1:]
            # POST /coupons/validate — público (cliente en checkout)
            if len(segments) == 2 and segments[1] == "validate" and method == "POST":
                return handle_validate_coupon(body)
            # GET /coupons — admin
            if len(segments) == 1 and method == "GET":
                err = utils._require_admin(headers, "config_manage")
                if err: return err
                return handle_list_coupons()
            # POST /coupons — admin
            if len(segments) == 1 and method == "POST":
                err = utils._require_admin(headers, "config_manage")
                if err: return err
                return handle_save_coupon(body)
            # DELETE /coupons/{code} — admin
            if len(segments) == 2 and method == "DELETE":
                err = utils._require_admin(headers, "config_manage")
                if err: return err
                return handle_delete_coupon(segments[1])
            return utils._json_response(404, {"message": "Ruta de cupones no encontrada"})

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
                    # Un pedido de invitado no tiene dueño con sesión: su único
                    # comprobante es el propio ID. Sin esta excepción, el
                    # invitado no podía ni ver el seguimiento de lo que compró.
                    if not _is_guest_order(order):
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    # Se devolvía el item crudo, sin "total": el cálculo guarda
                    # netTotal y la pantalla de seguimiento mostraba "$0".
                    return utils._json_response(200, {"order": _con_totales_visibles(order)})
                if method == "PATCH":
                    err = utils._require_admin(headers, "order_mark_paid")
                    if err: return err
                    return handle_update_status(order_id, body, headers)

            # /orders/{id}/...
            if len(segments) >= 3:
                sub = segments[2]
                if sub == "checkout" and method == "POST":
                    # Checkout: el propio cliente o admin pueden iniciarlo. Para un
                    # pedido de invitado no hay sesión que exigir: la tienda ofrece
                    # comprar sin cuenta y el pedido se creaba bien, pero aquí se
                    # respondía 401 y el invitado nunca podía pagar.
                    order = utils._get_by_id("ORDER", order_id)
                    if order and not _is_guest_order(order):
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    return handle_mercadopago_checkout(order_id, body)
                if sub == "refund" and method == "POST":
                    err = utils._require_admin(headers, "order_mark_paid")
                    if err: return err
                    return handle_refund_order(order_id, body, headers)
                if sub == "cancel" and method == "POST":
                    # Un invitado (sin cuenta) también puede cancelar su propio
                    # pedido pendiente: no tiene sesión que exigirle.
                    order = utils._get_by_id("ORDER", order_id)
                    if order and not _is_guest_order(order):
                        err = utils._require_self_or_admin(headers, order.get("customerId"))
                        if err: return err
                    return handle_cancel_order(order_id, body, headers)
                if sub == "return" and method == "POST":
                    if len(segments) == 4 and segments[3] == "inspect":
                        err = utils._require_admin(headers, "access_screen_orders")
                        if err: return err
                        return handle_return_inspection(order_id, body, headers)
                    order = utils._get_by_id("ORDER", order_id)
                    if order and not _is_guest_order(order):
                        # Un pedido de invitado no tiene sesión que exigir: el asistente de
                        # devolución dejaba llenar los tres pasos y respondía "No autenticado".
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
        utils._log_error("order_unhandled_error", e)
        return utils._json_response(500, {"message": "Critical Error", "error": str(e)})
