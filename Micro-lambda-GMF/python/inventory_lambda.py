import json
import boto3
import core_utils as utils
from core import order_emails # Importado desde la Lambda Layer

# Clientes de AWS
sfn = boto3.client('stepfunctions')

# Configuración de Orquestación
ORDER_SFN_ARN = utils.os.getenv("ORDER_FULFILLMENT_SFN_ARN")

# --- HELPERS DE INVENTARIO (Lógica Atómica) ---

def _apply_stock_delta(stock_id: str, deltas: dict):
    """
    Actualiza el inventario de forma segura.
    deltas: {"prod_id_1": -5, "prod_id_2": 10}
    """
    stock = utils._get_by_id("STOCK", stock_id)
    if not stock:
        return None, "Almacén no encontrado"
    
    inventory = stock.get("inventory") or {}
    # Convertir todas las llaves a string para consistencia
    next_inventory = {str(k): int(v) for k, v in inventory.items()}

    for pid, delta in deltas.items():
        curr = next_inventory.get(str(pid), 0)
        nxt = curr + int(delta)
        if nxt < 0:
            return None, f"Stock insuficiente para el producto {pid}"
        next_inventory[str(pid)] = nxt

    updated = utils._update_by_id(
        "STOCK", stock_id,
        "SET inventory = :inv, updatedAt = :u",
        {":inv": next_inventory, ":u": utils._now_iso()}
    )
    return updated, None

def _log_movement(stock_id, m_type, product_id, qty, ref_id, user_id, reason="", payment_method=None):
    """Crea un registro individual de movimiento de inventario."""
    move_id = f"MOV-{utils.uuid.uuid4().hex[:12].upper()}"
    item = {
        "entityType": "inventoryMovement",
        "movementId": move_id,
        "stockId": stock_id,
        "movementType": m_type,
        "type": m_type,
        "productId": product_id,
        "qty": int(qty),
        "referenceId": ref_id,
        "userId": user_id,
        "paymentMethod": payment_method,
        "reason": reason,
        "createdAt": utils._now_iso()
    }
    return utils._put_entity("INVENTORY_MOVEMENT", move_id, item)

# --- HANDLERS: GESTIÓN DE ALMACENES ---

def handle_stocks(method, body, stock_id=None):
    """GET, POST, PATCH /stocks"""
    if method == "GET":
        items = utils._query_bucket("STOCK")
        return utils._json_response(200, {"stocks": items})

    if method == "POST":
        sid = body.get("stockId") or f"STK-{utils.uuid.uuid4().hex[:6].upper()}"
        item = {
            "entityType": "stock", "stockId": sid, "name": body.get("name"),
            "location": body.get("location"),
            "allowPickup": bool(body.get("allowPickup", False)),
            "isMainWarehouse": bool(body.get("isMainWarehouse", False)),
            "linkedUserIds": [int(u) for u in (body.get("linkedUserIds") or []) if u is not None],
            "inventory": body.get("inventory") or {}, "createdAt": utils._now_iso()
        }
        utils._put_entity("STOCK", sid, item)
        return utils._json_response(201, {"stock": item})

    if method == "PATCH" and stock_id:
        updates = ["updatedAt = :u"]
        eav = {":u": utils._now_iso()}
        for f in ["name", "location", "allowPickup", "isMainWarehouse", "inventory"]:
            if f in body:
                updates.append(f"{f} = :{f}")
                eav[f":{f}"] = body[f]
        if "linkedUserIds" in body:
            updates.append("linkedUserIds = :linkedUserIds")
            eav[":linkedUserIds"] = [int(u) for u in (body["linkedUserIds"] or []) if u is not None]
        updated = utils._update_by_id("STOCK", stock_id, f"SET {', '.join(updates)}", eav)
        return utils._json_response(200, {"stock": updated})

# --- HANDLERS: TRANSFERENCIAS ---

def handle_transfers(method, body, query, transfer_id=None, headers=None):
    """POST /stocks/transfers (Crear), POST /transfers/{id}/receive (Recibir)"""
    if method == "GET":
        items = utils._query_bucket("STOCK_TRANSFER")
        return utils._json_response(200, {"transfers": items})

    if method == "POST":
        if transfer_id: # Lógica de recibir
            trf = utils._get_by_id("STOCK_TRANSFER", transfer_id)
            if not trf or trf.get("status") == "received":
                return utils._json_response(400, {"message": "Transferencia inválida o ya recibida"})
            
            # Recepción con cantidades reales: el almacén contó 4 de 5 y solo
            # podía "confirmar 5" o no confirmar nada. `received` trae lo que
            # llegó por producto; lo que falte queda como discrepancia y se
            # registra como merma en el origen (ya había salido de ahí).
            recibidas = (body or {}).get("received") or {}
            deltas, discrepancias, lineas_recibidas = {}, [], []
            for line in trf['lines']:
                pid = str(line['productId']); enviado = int(line['qty'])
                real = int(recibidas.get(pid, enviado)) if isinstance(recibidas, dict) else enviado
                real = max(0, min(real, enviado))
                deltas[pid] = real
                lineas_recibidas.append({"productId": pid, "sent": enviado, "received": real})
                if real < enviado:
                    discrepancias.append({"productId": pid, "sent": enviado, "received": real, "missing": enviado - real})
            _, error = _apply_stock_delta(trf['destinationStockId'], {k: v for k, v in deltas.items() if v > 0})
            if error:
                return utils._json_response(400, {"message": error})
            actor = (headers or {}).get("x-user-id") or "system"
            for d in discrepancias:
                _log_movement(trf.get("sourceStockId"), "damage", d["productId"], d["missing"], transfer_id, actor,
                              reason=f"Faltante en transferencia {transfer_id}: enviados {d['sent']}, recibidos {d['received']}")

            # Actualizar transferencia
            updated = utils._update_by_id("STOCK_TRANSFER", transfer_id,
                                         "SET #s = :s, receivedAt = :ra, receivedBy = :rb, receivedLines = :rl, discrepancies = :d",
                                         {":s": "received", ":ra": utils._now_iso(), ":rb": str(actor),
                                          ":rl": lineas_recibidas, ":d": discrepancias}, {"#s": "status"})
            return utils._json_response(200, {"transfer": updated, "discrepancies": discrepancias})

        # Crear transferencia (Salida de origen)
        source_id = body.get("sourceStockId")
        lines = [l for l in (body.get("lines") or []) if int(l.get("qty") or 0) > 0]
        if not lines or not source_id or not body.get("destinationStockId") or source_id == body.get("destinationStockId"):
            return utils._json_response(400, {"message": "La transferencia necesita origen, destino distinto y al menos un producto con cantidad"})
        deltas = {str(line['productId']): -int(line['qty']) for line in lines}
        
        _, error = _apply_stock_delta(source_id, deltas)
        if error: return utils._json_response(400, {"message": error})

        tid = f"TRF-{utils.uuid.uuid4().hex[:8].upper()}"
        item = {
            "entityType": "stockTransfer", "transferId": tid,
            "sourceStockId": source_id, "destinationStockId": body.get("destinationStockId"),
            "lines": lines, "status": "pending", "createdAt": utils._now_iso()
        }
        utils._put_entity("STOCK_TRANSFER", tid, item)
        return utils._json_response(201, {"transfer": item})

# --- HANDLERS: PUNTO DE VENTA (POS) ---

def _validate_pos_auth(code: str) -> bool:
    """Validates a POS authorization code against stored config."""
    cfg = utils._get_by_id("CONFIG", "pos-auth-v1")
    if not cfg:
        return False
    stored_code = str(cfg.get("posAuthCode") or "").strip()
    if not stored_code:
        return False
    return stored_code == str(code or "").strip()

def handle_pos_sale(body, headers):
    """POST /pos/sales"""
    stock_id = body.get("stockId")
    items = body.get("items", [])
    user_id = headers.get("x-user-id", "system")
    payment_method = str(body.get("paymentMethod") or "cash").strip().lower()
    if payment_method not in ("cash", "card", "transfer"):
        return utils._json_response(400, {"message": "Forma de pago invalida"})

    payment_type = str(body.get("paymentType") or "full").strip().lower()
    if payment_type not in ("full", "partial", "credit"):
        payment_type = "full"

    cashier_discount_mode = body.get("cashierDiscountMode")
    cashier_discount_value = utils._to_decimal(body.get("cashierDiscountValue") or 0)
    auth_code = str(body.get("authCode") or "").strip()

    # 1. Aplicar descuento de stock
    deltas = {str(it['productId']): -int(it['quantity']) for it in items}
    _, error = _apply_stock_delta(stock_id, deltas)
    if error: return utils._json_response(400, {"message": error})

    # 1b. Copiar los puntos del catálogo a cada línea, como hace la tienda en
    # línea: sin vpPoints el motor de comisiones convertía pesos ÷ tarifa y el
    # socio que compraba en mostrador recibía otros puntos que en la web.
    for it in items:
        if it.get("vpPoints") is None:
            producto = utils._get_by_id("PRODUCT", it.get("productId")) or {}
            if producto.get("vpPoints") is not None:
                it["vpPoints"] = producto.get("vpPoints")
            if producto.get("commissionable") is False:
                it["commissionable"] = False

    # 2. Calcular totales
    gross_subtotal = sum([utils._to_decimal(it['price']) * int(it['quantity']) for it in items])

    # Calcular descuento cajero
    cashier_discount_amount = utils.D_ZERO
    if cashier_discount_mode and cashier_discount_value > utils.D_ZERO:
        if not _validate_pos_auth(auth_code):
            return utils._json_response(403, {"message": "Codigo de autorizacion requerido para aplicar descuento"})
        if cashier_discount_mode == "percent":
            cashier_discount_amount = utils._to_decimal(gross_subtotal * (cashier_discount_value / 100))
        else:
            cashier_discount_amount = min(cashier_discount_value, gross_subtotal)

    # Validar auth para pago parcial/credito
    if payment_type != "full":
        if not _validate_pos_auth(auth_code):
            return utils._json_response(403, {"message": "Codigo de autorizacion requerido para pagos parciales o credito"})

    # Calcular total neto (descuentos de cliente vienen del cuerpo o se calculan en otro paso)
    customer_discount_amount = utils._to_decimal(body.get("discountAmount") or 0)
    total = gross_subtotal - customer_discount_amount - cashier_discount_amount
    if total < utils.D_ZERO:
        total = utils.D_ZERO

    # Calcular monto pagado ahora
    if payment_type == "full":
        amount_paid = total
    elif payment_type == "credit":
        amount_paid = utils.D_ZERO
    else:
        amount_paid_raw = utils._to_decimal(body.get("amountPaid") or 0)
        amount_paid = min(amount_paid_raw, total)

    pending_amount = total - amount_paid

    # Determinar paymentStatus
    if payment_type == "full":
        payment_status = "paid_branch"
    elif payment_type == "partial":
        payment_status = "partial_branch"
    else:
        payment_status = "credit_branch"

    order_id = f"POS-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()

    order_item = {
        "entityType": "order", "orderId": order_id, "customerId": body.get("customerId"),
        "customerName": body.get("customerName", "Publico General"),
        "status": "delivered", "items": items, "netTotal": total, "total": total,
        "deliveryType": "pickup", "stockId": stock_id, "attendantUserId": user_id,
        "monthKey": utils._month_key(), "paymentMethod": payment_method, "createdAt": now
    }
    utils._put_entity("ORDER", order_id, order_item)
    utils._upsert_order_customer_history(order_item)

    # 3. Crear registro de venta POS
    sale_id = f"SALE-{utils.uuid.uuid4().hex[:8].upper()}"
    sale_item = {
        "entityType": "posSale", "saleId": sale_id, "orderId": order_id,
        "stockId": stock_id,
        "total": total,
        "grossSubtotal": gross_subtotal,
        "discountRate": utils._to_decimal(body.get("discountRate") or 0),
        "discountAmount": customer_discount_amount,
        "cashReceived": utils._to_decimal(body.get("cashReceived")) if body.get("cashReceived") is not None else None,
        "cashierDiscountMode": cashier_discount_mode,
        "cashierDiscountAmount": cashier_discount_amount,
        "paymentType": payment_type,
        "amountPaid": amount_paid,
        "pendingAmount": pending_amount,
        "attendantUserId": user_id,
        "customerId": body.get("customerId"),
        "customerName": body.get("customerName", "Publico General"),
        "paymentStatus": payment_status,
        "deliveryStatus": body.get("deliveryStatus") or "delivered_branch",
        "paymentMethod": payment_method,
        "lines": items,
        "createdAt": now,
        "updatedAt": now,
    }
    utils._put_entity("POS_SALE", sale_id, sale_item)

    # 4. Registrar movimientos
    for it in items:
        _log_movement(stock_id, "pos_sale", it['productId'], it['quantity'], order_id, user_id, payment_method=payment_method)

    # 5. DISPARAR STEP FUNCTION (Motor de Comisiones)
    # Una venta de mostrador nace pagada y entregada. Antes solo se disparaba
    # ORDER_DELIVERED, que confirma comisiones "pending" que nunca existieron:
    # el socio que compraba en tienda física no acumulaba volumen ni VP y su
    # patrocinador no recibía comisión. ORDER_PAID aplica la activación y las
    # comisiones (solo cuenta si el comprador es un cliente registrado);
    # después ORDER_DELIVERED las confirma.
    if ORDER_SFN_ARN:
        acciones = ["ORDER_PAID", "ORDER_DELIVERED"] if body.get("customerId") else ["ORDER_DELIVERED"]
        for accion in acciones:
            try:
                sfn.start_execution(
                    stateMachineArn=ORDER_SFN_ARN,
                    input=json.dumps({"orderId": order_id, "action": accion})
                )
            except Exception as e:
                utils._log("sfn_error", "ERROR", pos_sale=sale_id, action=accion, err=e)

    # Aviso al cliente ligado: el cajero puede ligar una venta a cualquier cuenta
    # buscando por nombre; el titular debe enterarse y poder objetar.
    if body.get("customerId"):
        _avisar_pos(order_item, "pos_sale")

    return utils._json_response(201, {"sale": sale_item, "saleId": sale_id, "orderId": order_id})


def _avisar_pos(order: dict, evento: str) -> None:
    order_emails.notificar_pedido(
        order or {}, evento, {},
        lambda cid: utils._get_by_id("CUSTOMER", cid),
        utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx"),
    )



def handle_settle_pos_sale(sale_id, body, headers):
    """POST /pos/sales/{id}/payments — abono al saldo de una venta con pago parcial.

    El saldo pendiente solo se veía al cobrar y después no había forma de
    liquidarlo. El abono se registra como una venta de caja sin productos
    (source=settlement) para que entre al efectivo y al corte como cualquier cobro.
    """
    sale = utils._get_by_id("POS_SALE", sale_id)
    if not sale:
        return utils._json_response(404, {"message": "Venta no encontrada"})
    if sale.get("status") == "voided":
        return utils._json_response(409, {"message": "La venta está anulada"})
    pendiente = utils._to_decimal(sale.get("pendingAmount") or 0)
    if pendiente <= utils.D_ZERO:
        return utils._json_response(409, {"message": "Esta venta no tiene saldo pendiente"})
    monto = utils._to_decimal((body or {}).get("amount") or pendiente)
    if monto <= utils.D_ZERO or monto > pendiente:
        return utils._json_response(400, {"message": f"El abono debe ser mayor a 0 y hasta ${pendiente}"})
    metodo = str((body or {}).get("paymentMethod") or "cash").strip().lower()
    if metodo not in ("cash", "card", "transfer"):
        return utils._json_response(400, {"message": "Forma de pago invalida"})
    actor = utils._extract_actor(headers or {})
    user_id = actor.get("user_id") or (headers or {}).get("x-user-id")
    now = utils._now_iso()
    abono_id = f"SALE-{utils.uuid.uuid4().hex[:8].upper()}"
    nuevo_pendiente = pendiente - monto
    abono = {
        "entityType": "posSale", "saleId": abono_id, "orderId": sale.get("orderId"),
        "source": "settlement", "settlesSaleId": sale_id,
        "stockId": sale.get("stockId"), "attendantUserId": user_id,
        "customerId": sale.get("customerId"), "customerName": sale.get("customerName"),
        "total": monto, "grossSubtotal": monto, "discountRate": utils.D_ZERO, "discountAmount": utils.D_ZERO,
        "paymentType": "full", "amountPaid": monto, "pendingAmount": utils.D_ZERO,
        "paymentStatus": "paid", "deliveryStatus": "delivered_branch", "paymentMethod": metodo,
        "lines": [], "createdAt": now, "updatedAt": now,
    }
    utils._put_entity("POS_SALE", abono_id, abono)
    pagos = list(sale.get("payments") or []) + [{"saleId": abono_id, "amount": monto, "paymentMethod": metodo, "at": now, "by": str(user_id)}]
    actualizado = utils._update_by_id(
        "POS_SALE", sale_id,
        "SET amountPaid = :p, pendingAmount = :r, paymentStatus = :st, payments = :pg, updatedAt = :u",
        {":p": utils._to_decimal(sale.get("amountPaid") or 0) + monto, ":r": nuevo_pendiente,
         ":st": "paid" if nuevo_pendiente <= utils.D_ZERO else "partial", ":pg": pagos, ":u": now},
    )
    if sale.get("orderId") and nuevo_pendiente <= utils.D_ZERO:
        try:
            utils._update_by_id("ORDER", sale.get("orderId"), "SET paymentStatus = :st, updatedAt = :u", {":st": "paid", ":u": now})
        except Exception as e:
            utils._log("settle_order_update_error", "ERROR", saleId=sale_id, err=e)
    return utils._json_response(200, {"sale": actualizado, "payment": abono, "pendingAmount": float(nuevo_pendiente)})

def handle_void_pos_sale(sale_id: str, body: dict, headers: dict) -> dict:
    """POST /pos/sales/{id}/void — anula una venta de mostrador.

    Un cliente encontró en su cuenta una venta de tienda que no hizo y no
    había forma de quitarla: regresa el inventario, marca la venta y el
    pedido como anulados, dispara la reversión de comisiones y volumen, y
    avisa al cliente ligado.
    """
    sale = utils._get_by_id("POS_SALE", sale_id)
    if not sale:
        return utils._json_response(404, {"message": "Venta no encontrada"})
    if sale.get("status") == "voided":
        return utils._json_response(409, {"message": "La venta ya está anulada."})
    now = utils._now_iso()
    actor = headers.get("x-user-id") or "admin"
    motivo = str((body or {}).get("reason") or "anulación").strip()[:300]
    stock_id = sale.get("stockId")
    order_id = sale.get("orderId")

    # 1. Regresar inventario
    deltas = {}
    for it in sale.get("lines") or sale.get("items") or []:
        pid = str(it.get("productId") or "").strip()
        qty = int(it.get("quantity") or it.get("qty") or 0)
        if pid and qty > 0:
            deltas[pid] = deltas.get(pid, 0) + qty
    if deltas:
        _, error = _apply_stock_delta(stock_id, deltas)
        if error:
            return utils._json_response(400, {"message": error})
        for pid, qty in deltas.items():
            _log_movement(stock_id, "entry", pid, qty, order_id, actor, payment_method=None)

    # 2. Marcar venta y pedido
    utils._update_by_id("POS_SALE", sale_id, "SET #s = :s, voidedAt = :t, voidedBy = :by, voidReason = :r, updatedAt = :t",
                        {":s": "voided", ":t": now, ":by": str(actor), ":r": motivo}, {"#s": "status"})
    order = None
    if order_id:
        order = utils._update_by_id("ORDER", order_id, "SET #s = :s, cancelReason = :r, cancelledAt = :t, updatedAt = :t",
                                    {":s": "cancelled", ":r": f"pos_void: {motivo}", ":t": now}, {"#s": "status"})
        # Sin esto la lista de pedidos del cliente seguía diciendo "Entregada"
        # mientras el detalle decía "Cancelado".
        try:
            utils._upsert_order_customer_history(order)
        except Exception as e:
            utils._log("pos_void_history_error", "ERROR", orderId=order_id, err=e)
        if ORDER_SFN_ARN:
            try:
                sfn.start_execution(stateMachineArn=ORDER_SFN_ARN,
                                    input=json.dumps({"orderId": order_id, "action": "ORDER_CANCELLED", "payload": {"reason": motivo}}))
            except Exception as e:
                utils._log("sfn_error", "ERROR", pos_void=sale_id, err=e)

    # 3. Avisar al cliente ligado
    if order and order.get("customerId"):
        _avisar_pos(order, "pos_voided")

    utils._audit_event("pos.sale_voided", headers, body, {"saleId": sale_id, "orderId": order_id, "reason": motivo})
    return utils._json_response(200, {"ok": True, "saleId": sale_id, "orderId": order_id, "status": "voided"})

def _stock_id_str(value) -> str:
    """Normaliza stockId a string."""
    if value is None:
        return ""
    return str(value).strip()

def _last_pos_cash_cut(stock_id: str, attendant_user_id) -> dict:
    """Último corte de caja de un operador en un almacén.

    Recorre la colección de más reciente a más antiguo y corta en el primer
    acierto, en lugar de traer todos los cortes históricos para ordenarlos.
    """
    for item in utils._iter_bucket("POS_CASH_CUT", forward=False):
        if (_stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
                and str(item.get("attendantUserId")) == str(attendant_user_id)):
            return item
    return {}

def _build_pos_cash_control(stock_id: str, attendant_user_id) -> dict:
    """Calcula el estado actual del control de caja."""
    last_cut = _last_pos_cash_cut(stock_id, attendant_user_id)
    last_cut_at = str(last_cut.get("createdAt") or "") if last_cut else ""
    # Solo interesan las ventas posteriores al último corte: `sk_from` las acota
    # en la condición de clave (SK = "{createdAt}#{id}") en vez de leer todo el
    # histórico de ventas del punto de venta en cada refresco de la pantalla.
    sales = [
        item for item in utils._query_bucket("POS_SALE", sk_from=last_cut_at or None)
        if _stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
        and str(item.get("attendantUserId")) == str(attendant_user_id)
        and str(item.get("paymentMethod") or "cash").lower() == "cash"
        and (not last_cut_at or str(item.get("createdAt") or "") > last_cut_at)
    ]
    sales.sort(key=lambda x: str(x.get("createdAt") or ""))
    cash_carry = utils._to_decimal(last_cut.get("cashToKeep")) if last_cut else utils.D_ZERO

    # Usar amountPaid en lugar de total para ventas parciales/credito
    sales_total = sum(
        (utils._to_decimal(item.get("amountPaid") if item.get("paymentType") in ("partial", "credit") else item.get("total"))
         for item in sales),
        utils.D_ZERO
    )

    # Restar retiros desde el ultimo corte
    # Un retiro anterior al último corte ya lleva `cashCutId`, así que basta con
    # mirar de esa fecha en adelante.
    withdrawals = [
        item for item in utils._query_bucket("POS_WITHDRAWAL", sk_from=last_cut_at or None)
        if _stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
        and str(item.get("attendantUserId")) == str(attendant_user_id)
        and not item.get("cashCutId")
    ]
    withdrawals_total = sum((utils._to_decimal(w.get("amount")) for w in withdrawals), utils.D_ZERO)

    current_total = cash_carry + sales_total - withdrawals_total
    return {
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "currentTotal": float(current_total),
        "salesCount": len(sales),
        "cashToKeepSuggested": float(current_total),
        "withdrawalCount": len(withdrawals),
        "totalWithdrawn": float(withdrawals_total),
        "startedAt": sales[0].get("createdAt") if sales else (last_cut.get("createdAt") if last_cut else None),
        "lastCutAt": last_cut.get("createdAt") if last_cut else None,
        "lastCutTotal": float(utils._to_decimal(last_cut.get("total"))) if last_cut else 0.0,
        "lastCutSalesCount": int(last_cut.get("salesCount") or 0) if last_cut else 0,
        "lastCutCashToKeep": float(utils._to_decimal(last_cut.get("cashToKeep"))) if last_cut else 0.0,
        "lastCutWithdrawnAmount": float(utils._to_decimal(last_cut.get("withdrawnAmount"))) if last_cut else 0.0,
        "lastSaleAt": sales[-1].get("createdAt") if sales else None,
    }

def handle_cash_cut(body, headers):
    """POST /pos/cash-cut"""
    stock_id = body.get("stockId")
    user_id = headers.get("x-user-id")
    cash_to_keep = utils._to_decimal(body.get("cashToKeep") or 0)

    # Ventas y retiros pendientes son, por definición, posteriores al último
    # corte de este operador: acotarlos por esa fecha evita releer todo el
    # histórico del punto de venta en cada cierre de caja.
    last_cut = _last_pos_cash_cut(stock_id, user_id)
    since = str(last_cut.get("createdAt") or "") or None

    pending_sales = [
        s for s in utils._query_bucket("POS_SALE", sk_from=since)
        if _stock_id_str(s.get("stockId")) == _stock_id_str(stock_id)
        and str(s.get("attendantUserId")) == str(user_id)
        and str(s.get("paymentMethod") or "cash").lower() == "cash"
        and not s.get("cashCutId")
    ]

    pending_withdrawals = [
        w for w in utils._query_bucket("POS_WITHDRAWAL", sk_from=since)
        if _stock_id_str(w.get("stockId")) == _stock_id_str(stock_id)
        and str(w.get("attendantUserId")) == str(user_id)
        and not w.get("cashCutId")
    ]

    if not pending_sales and not pending_withdrawals:
        return utils._json_response(400, {"message": "No hay ventas pendientes para corte"})

    # Usar amountPaid para ventas parciales/credito
    total_cash = sum([
        utils._to_decimal(s.get("amountPaid") if s.get("paymentType") in ("partial", "credit") else s.get("total"))
        for s in pending_sales
    ], utils.D_ZERO)
    withdrawals_total = sum([utils._to_decimal(w.get("amount")) for w in pending_withdrawals], utils.D_ZERO)
    net_total = total_cash - withdrawals_total

    if cash_to_keep < utils.D_ZERO:
        return utils._json_response(400, {"message": "El monto a dejar en caja no puede ser negativo"})

    last_cut = _last_pos_cash_cut(stock_id, user_id)
    cash_carry = utils._to_decimal(last_cut.get("cashToKeep")) if last_cut else utils.D_ZERO
    available = cash_carry + net_total
    if cash_to_keep > available:
        return utils._json_response(400, {"message": "El monto a dejar en caja no puede exceder el total disponible"})

    cut_id = f"CUT-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()

    cut_item = {
        "entityType": "posCashCut", "cashCutId": cut_id, "stockId": stock_id,
        # DynamoDB rechaza float ("Float types are not supported"): el corte de
        # caja respondía 500 y el cajero no podía cerrar. Se guardan Decimal.
        "total": utils._to_decimal(net_total),
        "salesCount": len(pending_sales),
        "cashToKeep": utils._to_decimal(cash_to_keep),
        "withdrawnAmount": utils._to_decimal(available - cash_to_keep),
        "totalWithdrawals": utils._to_decimal(withdrawals_total),
        "withdrawalCount": len(pending_withdrawals),
        "attendantUserId": user_id,
        "startedAt": pending_sales[0].get("createdAt") if pending_sales else now,
        "endedAt": now,
        "createdAt": now,
        "sales": pending_sales,
        "withdrawals": pending_withdrawals,
    }
    utils._put_entity("POS_CASH_CUT", cut_id, cut_item)

    for s in pending_sales:
        utils._update_by_id("POS_SALE", s['saleId'], "SET cashCutId = :c", {":c": cut_id})
    for w in pending_withdrawals:
        w_id = w.get("withdrawalId") or w.get("id")
        if w_id:
            utils._update_by_id("POS_WITHDRAWAL", w_id, "SET cashCutId = :c", {":c": cut_id})

    return utils._json_response(201, {"cut": cut_item, "control": _build_pos_cash_control(stock_id, user_id)})


def handle_validate_pos_auth(body, headers):
    """POST /pos/validate-auth"""
    code = str(body.get("code") or "").strip()
    if not code:
        return utils._json_response(400, {"message": "Se requiere el codigo de autorizacion"})
    if not _validate_pos_auth(code):
        return utils._json_response(403, {"message": "Codigo de autorizacion incorrecto"})
    return utils._json_response(200, {"ok": True})


def handle_pos_auth_config(method, body, headers):
    """GET|PUT /pos/auth-config - Gestiona el codigo de autorizacion POS"""
    if method == "GET":
        cfg = utils._get_by_id("CONFIG", "pos-auth-v1")
        has_code = bool(cfg and str(cfg.get("posAuthCode") or "").strip())
        return utils._json_response(200, {"configured": has_code})
    if method == "PUT":
        new_code = str(body.get("posAuthCode") or "").strip()
        if not new_code:
            return utils._json_response(400, {"message": "El codigo no puede estar vacio"})
        if len(new_code) < 4:
            return utils._json_response(400, {"message": "El codigo debe tener al menos 4 caracteres"})
        now = utils._now_iso()
        utils._put_entity("CONFIG", "pos-auth-v1", {
            "entityType": "config",
            "configId": "pos-auth-v1",
            "posAuthCode": new_code,
            "updatedAt": now,
            "createdAt": now,
        })
        return utils._json_response(200, {"ok": True, "configured": True})
    return utils._json_response(405, {"message": "Metodo no permitido"})


def handle_pos_withdrawal(body, headers):
    """POST /pos/withdrawal"""
    stock_id = body.get("stockId")
    user_id = headers.get("x-user-id")
    amount = utils._to_decimal(body.get("amount"))
    reason = str(body.get("reason") or "").strip()
    auth_code = str(body.get("authCode") or "").strip()

    if not reason:
        return utils._json_response(400, {"message": "Se requiere el motivo del retiro"})
    if amount <= utils.D_ZERO:
        return utils._json_response(400, {"message": "El monto debe ser mayor a cero"})
    if not _validate_pos_auth(auth_code):
        return utils._json_response(403, {"message": "Codigo de autorizacion incorrecto"})

    wdr_id = f"WDR-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()
    item = {
        "entityType": "posWithdrawal",
        "withdrawalId": wdr_id,
        "stockId": stock_id,
        "attendantUserId": user_id,
        # Decimal: como float, DynamoDB lo rechazaba y el retiro respondía 500.
        "amount": utils._to_decimal(amount),
        "reason": reason,
        "createdAt": now,
        "updatedAt": now
    }
    utils._put_entity("POS_WITHDRAWAL", wdr_id, item)

    control = _build_pos_cash_control(stock_id, user_id)
    return utils._json_response(201, {"withdrawal": item, "control": control})


MAX_CASH_CUTS_PAGE = 50


def handle_list_cash_cuts(stock_id, user_id, limit: int = MAX_CASH_CUTS_PAGE):
    """GET /pos/cash-cuts — los `limit` cortes más recientes del operador."""
    # Se piden limit+1 cortes: el extra marca el límite temporal inferior de la
    # ventana, y las ventas/retiros de los cortes devueltos son todos
    # posteriores a él. Así el detalle se acota por clave en vez de leer los
    # históricos completos de POS_SALE y POS_WITHDRAWAL.
    window = []
    for item in utils._iter_bucket("POS_CASH_CUT", forward=False):
        if (_stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
                and str(item.get("attendantUserId")) == str(user_id)):
            window.append(item)
            if len(window) > limit:
                break

    boundary_cut = window[limit] if len(window) > limit else None
    cuts = window[:limit]
    since = str((boundary_cut or {}).get("createdAt") or "") or None

    if cuts:
        sales = utils._query_bucket("POS_SALE", sk_from=since)
        withdrawals = utils._query_bucket("POS_WITHDRAWAL", sk_from=since)
    else:
        sales, withdrawals = [], []

    sales_by_cut = {}
    for sale in sales:
        sales_by_cut.setdefault(sale.get("cashCutId"), []).append(sale)
    withdrawals_by_cut = {}
    for withdrawal in withdrawals:
        withdrawals_by_cut.setdefault(withdrawal.get("cashCutId"), []).append(withdrawal)

    for cut in cuts:
        cut_id = cut.get("cashCutId") or cut.get("cutId")
        if not cut.get("sales"):
            cut["sales"] = sales_by_cut.get(cut_id, [])
        if not cut.get("withdrawals"):
            cut["withdrawals"] = withdrawals_by_cut.get(cut_id, [])

    return utils._json_response(200, {"cuts": cuts, "count": len(cuts),
                                      "hasMore": boundary_cut is not None})

# --- LAMBDA ROUTER ---

def _route_stocks(method: str, segments: list, body: dict, query: dict, headers: dict):
    """Sub-rutas de /inventory/stocks. Devuelve None si ninguna coincide."""
    root = segments[0] if segments else ""
    if root == "stocks":
        if len(segments) == 1:
            if method in ("POST", "PATCH"):
                err = utils._require_admin(headers, "stock_create")
                if err: return err
            return handle_stocks(method, body)

        # /stocks/transfers/{id}/receive — nunca llegaba a handle_transfers con
        # el id: caía en "crear transferencia" sin origen y respondía "Almacén
        # no encontrado". Recibir una transferencia estaba roto de raíz.
        if segments[1] == "transfers" and len(segments) >= 4 and segments[3] == "receive" and method == "POST":
            err = utils._require_admin(headers, "stock_receive_transfer")
            if err: return err
            return handle_transfers(method, body, query, transfer_id=segments[2], headers=headers)

        # /stocks/transfers
        if segments[1] == "transfers":
            if method == "POST":
                err = utils._require_admin(headers, "stock_create_transfer")
                if err: return err
            return handle_transfers(method, body, query)

        # /stocks/movements
        if segments[1] == "movements":
            err = utils._require_admin(headers, "access_screen_stocks")
            if err: return err

            moves = utils._query_bucket("INVENTORY_MOVEMENT")

            # Si el actor es employee (no admin completo), filtrar por sus stocks ligados
            actor = utils._extract_actor(headers)
            if actor.get("role") == "employee":
                actor_user_id = actor.get("user_id")
                if actor_user_id:
                    # Obtener los stocks donde este usuario está en linkedUserIds
                    all_stocks = utils._query_bucket("STOCK")
                    linked_stock_ids = {
                        _stock_id_str(s.get("stockId") or s.get("id") or s.get("SK"))
                        for s in all_stocks
                        if actor_user_id in [str(u) for u in (s.get("linkedUserIds") or [])]
                    } - {""}
                    if linked_stock_ids:
                        moves = [m for m in moves if _stock_id_str(m.get("stockId")) in linked_stock_ids]

            # Filtrar por stockId explícito si viene en query params (aplicado después del scope de permisos)
            stock_id_filter = query.get("stockId")
            if stock_id_filter:
                moves = [m for m in moves if _stock_id_str(m.get("stockId")) == _stock_id_str(stock_id_filter)]

            return utils._json_response(200, {"movements": moves})

        # /stocks/{id}/...
        sid = segments[1]
        if len(segments) == 2:
            if method in ("POST", "PATCH"):
                err = utils._require_admin(headers, "stock_create")
                if err: return err
            return handle_stocks(method, body, sid)

        sub = segments[2]
        if sub == "entries" and method == "POST":
            err = utils._require_admin(headers, "stock_add_inventory")
            if err: return err
            _, error = _apply_stock_delta(sid, {str(body['productId']): int(body['qty'])})
            if error: return utils._json_response(400, {"message": error})
            _log_movement(sid, "entry", body['productId'], body['qty'], "manual", body.get("userId"))
            return utils._json_response(200, {"ok": True})

        if sub == "damages" and method == "POST":
            err = utils._require_admin(headers, "stock_mark_damaged")
            if err: return err
            _, error = _apply_stock_delta(sid, {str(body['productId']): -int(body['qty'])})
            if error: return utils._json_response(400, {"message": error})
            _log_movement(sid, "damage", body['productId'], body['qty'], "manual", body.get("userId"), body.get("reason") or "")
            return utils._json_response(200, {"ok": True})

    # /pos
    return None


def _route_pos(method: str, segments: list, body: dict, query: dict, headers: dict):
    """Sub-rutas de /inventory/pos. Devuelve None si ninguna coincide."""
    root = segments[0] if segments else ""
    if root == "pos":
        if len(segments) < 2:
            return utils._json_response(404, {"message": "Ruta de inventario no encontrada"})
        if segments[1] == "sales" and len(segments) == 4 and segments[3] == "payments" and method == "POST":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            return handle_settle_pos_sale(segments[2], body, headers)
        if segments[1] == "sales" and len(segments) == 4 and segments[3] == "void" and method == "POST":
            err = utils._require_admin(headers, "order_mark_paid")
            if err: return err
            return handle_void_pos_sale(segments[2], body, headers)
        if segments[1] == "sales":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            if method == "GET":
                sid = query.get("stockId")
                # `from`/`to` (YYYY-MM-DD o YYYY-MM) acotan por clave. Sin
                # ellos se mantiene el histórico completo: cambiar el rango
                # por defecto rompería los reportes de meses anteriores.
                date_from = (query.get("from") or "").strip() or None
                date_to = (query.get("to") or "").strip() or None
                sales = utils._query_bucket("POS_SALE", sk_from=date_from,
                                            sk_to=(date_to + "\uffff") if date_to else None)
                if sid:
                    sales = [s for s in sales if str(s.get("stockId") or "") == str(sid)]
                return utils._json_response(200, {"sales": sales, "from": date_from, "to": date_to})
            return handle_pos_sale(body, headers)
        if segments[1] == "cash-cut":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            return handle_cash_cut(body, headers)
        if segments[1] == "cash-control" and method == "GET":
            err = utils._require_admin(headers, "access_screen_pos")
            if err: return err
            user_id = headers.get("x-user-id")
            sid = query.get("stockId")
            if not user_id:
                return utils._json_response(400, {"message": "Se requiere x-user-id"})
            if not sid:
                for stock in utils._query_bucket("STOCK"):
                    linked = stock.get("linkedUserIds") or []
                    if str(user_id) in [str(u) for u in linked]:
                        sid = str(stock.get("stockId"))
                        break
            if not sid:
                return utils._json_response(400, {"message": "El usuario no tiene stock vinculado"})
            control = _build_pos_cash_control(sid, user_id)
            return utils._json_response(200, {"control": control})
        if segments[1] == "validate-auth" and method == "POST":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            return handle_validate_pos_auth(body, headers)
        if segments[1] == "withdrawal":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            if method == "POST":
                return handle_pos_withdrawal(body, headers)
            if method == "GET":
                user_id = headers.get("x-user-id")
                sid = query.get("stockId")
                withdrawals = utils._query_bucket("POS_WITHDRAWAL")
                if sid:
                    withdrawals = [w for w in withdrawals if _stock_id_str(w.get("stockId")) == _stock_id_str(sid)]
                if user_id:
                    withdrawals = [w for w in withdrawals if str(w.get("attendantUserId")) == str(user_id)]
                return utils._json_response(200, {"withdrawals": withdrawals})
        if segments[1] == "cash-cuts":
            err = utils._require_admin(headers, "pos_register_sale")
            if err: return err
            if method == "GET":
                user_id = headers.get("x-user-id")
                sid = query.get("stockId")
                return handle_list_cash_cuts(sid, user_id)
        if segments[1] == "auth-config":
            err = utils._require_admin(headers, "config_manage")
            if err: return err
            return handle_pos_auth_config(method, body, headers)

    # /pickup-stocks
    return None


def lambda_handler(event, context):
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return utils._cors_preflight_response()
    # API Gateway entrega /inventory/{proxy+}: se quita el prefijo del recurso.
    request = utils._http_request(event, strip_prefix="inventory")
    method = request.method
    body, query, headers = request.body, request.query, request.headers
    segments = request.segments

    try:
        if not segments: return utils._json_response(200, {"service": "inventory-pos"})

        root = segments[0]

        # /inventory/stocks  →  root == "stocks"
        for enrutador in (_route_stocks, _route_pos):
            respuesta = enrutador(method, segments, body, query, headers)
            if respuesta is not None:
                return respuesta


        if root == "pickup-stocks":
            stocks = [s for s in utils._query_bucket("STOCK") if s.get("allowPickup")]
            return utils._json_response(200, {"stocks": stocks})

        return utils._json_response(404, {"message": "Ruta de inventario no encontrada"})

    except Exception as e:
        utils._log_error("inventory_unhandled_error", e)
        return utils._json_response(500, {"message": "Internal Inventory Error", "error": str(e)})
