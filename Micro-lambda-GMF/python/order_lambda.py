import base64
import json
import boto3
import urllib.error
import urllib.parse
import urllib.request
import core_utils as utils  # Importado desde la Layer
from datetime import datetime, timezone

# Clientes de AWS
sfn = boto3.client('stepfunctions')
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)

# Configuración de Entorno
ORDER_SFN_ARN = utils.os.getenv("ORDER_FULFILLMENT_SFN_ARN")
ML_TOKEN = utils.os.getenv("MERCADOPAGO_ACCESS_TOKEN")
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

MAX_COMMISSION_LEVELS = 3

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

    beneficiaries = []
    curr = buyer_id
    for _ in range(MAX_COMMISSION_LEVELS):
        profile = utils._get_by_id("CUSTOMER", curr)
        if not profile or not profile.get("leaderId"):
            break
        leader_id = profile.get("leaderId")
        beneficiaries.append(str(leader_id))
        curr = leader_id

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
    if new_status == "delivered":
        extra_updates["deliveredAt"] = utils._now_iso()

    update_expr = "SET #s = :s, updatedAt = :u"
    eav = {":s": new_status, ":u": utils._now_iso()}
    for k, v in extra_updates.items():
        update_expr += f", {k} = :{k}"
        eav[f":{k}"] = v

    updated = utils._update_by_id("ORDER", order_id, update_expr, eav, {"#s": "status"})
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

    utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, cancelReason = :r, pendingRefund = :pr, cancelledAt = :ca, updatedAt = :u",
        {":s": "cancelled", ":r": reason, ":pr": True, ":ca": now, ":u": now},
        {"#s": "status"},
    )

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

    for category, files in [
        ("fotos_producto", fotos_producto),
        ("fotos_empaque", fotos_empaque),
        ("fotos_guia_envio", fotos_guia),
    ]:
        urls = []
        for i, f in enumerate(files):
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
                urls.append(asset["url"])
            except Exception as e:
                print(f"[S3_EVIDENCE] {e}")
        uploaded_evidence[category] = urls

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
        "horasDesdEntrega": float(hours_since),
        "inspection": None,
        "createdAt": now,
        "updatedAt": now,
    }
    utils._put_entity("RETURN_REQUEST", request_id, return_item, created_at_iso=now)

    # Actualizar orden → EN_DEVOLUCION
    utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, returnRequestId = :rid, updatedAt = :u",
        {":s": "en_devolucion", ":rid": request_id, ":u": now},
        {"#s": "status"},
    )

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
    actor = (headers or {}).get("x-user-id") or (headers or {}).get("x-actor-id") or "admin"

    utils._update_by_id(
        "RETURN_REQUEST", request_id,
        "SET #s = :s, inspection = :i, inspectedAt = :ia, inspectedBy = :ib, updatedAt = :u",
        {":s": new_return_status, ":i": inspection, ":ia": now, ":ib": actor, ":u": now},
        {"#s": "status"},
    )
    utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, updatedAt = :u",
        {":s": new_order_status, ":u": now},
        {"#s": "status"},
    )

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
    """POST /orders/{id}/refund"""
    if not utils._get_by_id("ORDER", order_id):
        return utils._json_response(404, {"message": "Pedido no encontrado"})
    now = utils._now_iso()
    utils._update_by_id(
        "ORDER", order_id,
        "SET #s = :s, refundReason = :r, updatedAt = :u",
        {":s": "refunded", ":r": body.get("reason") or "refund", ":u": now},
        {"#s": "status"},
    )
    actions = _void_commissions_for_order(order_id, reason="refund")
    utils._audit_event("order.refund", headers, body, {"orderId": order_id})
    return utils._json_response(200, {"orderId": order_id, "status": "refunded", "commissionActions": actions})


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
            # /orders
            if len(segments) == 1:
                if method == "POST":
                    actor = utils._extract_actor(headers)
                    if actor.get("user_id"):
                        err = utils._require_self_or_admin(headers, body.get("customerId"))
                        if err: return err
                    return handle_create_order(body, headers)
                if method == "GET":
                    cid = query.get("customerId")
                    # Customer puede ver solo sus propias órdenes; admin puede filtrar por cualquier ID
                    err = utils._require_self_or_admin(headers, cid)
                    if err: return err
                    items = [o for o in utils._query_bucket("ORDER") if str(o.get("customerId")) == str(cid)]
                    return utils._json_response(200, {"orders": items})

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
