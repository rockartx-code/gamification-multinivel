import json
import boto3
import core_utils as utils # Importado desde la Lambda Layer
from datetime import datetime

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

def handle_transfers(method, body, query, transfer_id=None):
    """POST /stocks/transfers (Crear), POST /transfers/{id}/receive (Recibir)"""
    if method == "GET":
        items = utils._query_bucket("STOCK_TRANSFER")
        return utils._json_response(200, {"transfers": items})

    if method == "POST":
        if transfer_id: # Lógica de recibir
            trf = utils._get_by_id("STOCK_TRANSFER", transfer_id)
            if not trf or trf.get("status") == "received":
                return utils._json_response(400, {"message": "Transferencia inválida o ya recibida"})
            
            # Sumar a destino
            deltas = {str(line['productId']): int(line['qty']) for line in trf['lines']}
            _apply_stock_delta(trf['destinationStockId'], deltas)
            
            # Actualizar transferencia
            updated = utils._update_by_id("STOCK_TRANSFER", transfer_id, 
                                         "SET #s = :s, receivedAt = :ra", 
                                         {":s": "received", ":ra": utils._now_iso()}, {"#s": "status"})
            return utils._json_response(200, {"transfer": updated})

        # Crear transferencia (Salida de origen)
        source_id = body.get("sourceStockId")
        lines = body.get("lines", [])
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

def handle_pos_sale(body, headers):
    """POST /pos/sales"""
    stock_id = body.get("stockId")
    items = body.get("items", [])
    user_id = headers.get("x-user-id", "system")
    payment_method = str(body.get("paymentMethod") or "cash").strip().lower()
    if payment_method not in ("cash", "card", "transfer"):
        return utils._json_response(400, {"message": "Forma de pago invalida"})

    # 1. Aplicar descuento de stock
    deltas = {str(it['productId']): -int(it['quantity']) for it in items}
    _, error = _apply_stock_delta(stock_id, deltas)
    if error: return utils._json_response(400, {"message": error})

    # 2. Calcular totales y crear Orden
    total = sum([utils._to_decimal(it['price']) * int(it['quantity']) for it in items])
    order_id = f"POS-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()

    order_item = {
        "entityType": "order", "orderId": order_id, "customerId": body.get("customerId"),
        "customerName": body.get("customerName", "Público General"),
        "status": "delivered", "items": items, "netTotal": total, "total": total,
        "deliveryType": "pickup", "stockId": stock_id, "attendantUserId": user_id,
        "monthKey": utils._month_key(), "paymentMethod": payment_method, "createdAt": now
    }
    utils._put_entity("ORDER", order_id, order_item)
    utils._upsert_order_customer_history(order_item)

    # 3. Crear registro de venta POS (para contabilidad de sucursal)
    sale_id = f"SALE-{utils.uuid.uuid4().hex[:8].upper()}"
    sale_item = {
        "entityType": "posSale", "saleId": sale_id, "orderId": order_id,
        "stockId": stock_id,
        "total": total,
        "grossSubtotal": total,
        "discountRate": 0,
        "discountAmount": 0,
        "attendantUserId": user_id,
        "customerId": body.get("customerId"),
        "customerName": body.get("customerName", "Público General"),
        "paymentStatus": body.get("paymentStatus") or "paid_branch",
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
    sfn.start_execution(
        stateMachineArn=ORDER_SFN_ARN,
        input=json.dumps({"orderId": order_id, "action": "ORDER_DELIVERED"})
    )

    return utils._json_response(201, {"sale": sale_item, "saleId": sale_id, "orderId": order_id})

def _stock_id_str(value) -> str:
    """Normaliza stockId a string."""
    if value is None:
        return ""
    return str(value).strip()

def _last_pos_cash_cut(stock_id: str, attendant_user_id) -> dict:
    """Devuelve el último corte de caja de un operador en un almacén."""
    cuts = [
        item for item in utils._query_bucket("POS_CASH_CUT")
        if _stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
        and str(item.get("attendantUserId")) == str(attendant_user_id)
    ]
    if not cuts:
        return {}
    cuts.sort(key=lambda x: str(x.get("createdAt") or ""), reverse=True)
    return cuts[0]

def _build_pos_cash_control(stock_id: str, attendant_user_id) -> dict:
    """Calcula el estado actual del control de caja."""
    last_cut = _last_pos_cash_cut(stock_id, attendant_user_id)
    last_cut_at = str(last_cut.get("createdAt") or "") if last_cut else ""
    sales = [
        item for item in utils._query_bucket("POS_SALE")
        if _stock_id_str(item.get("stockId")) == _stock_id_str(stock_id)
        and str(item.get("attendantUserId")) == str(attendant_user_id)
        and str(item.get("paymentMethod") or "cash").lower() == "cash"
        and (not last_cut_at or str(item.get("createdAt") or "") > last_cut_at)
    ]
    sales.sort(key=lambda x: str(x.get("createdAt") or ""))
    current_total = sum((utils._to_decimal(item.get("total")) for item in sales), utils.D_ZERO)
    return {
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "currentTotal": float(current_total),
        "salesCount": len(sales),
        "cashToKeepSuggested": float(current_total),
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
    
    # Buscar todas las ventas POS de este usuario en este stock que no estén en un corte
    all_sales = utils._query_bucket("POS_SALE")
    # (En una implementación real, usaríamos un GSI para filtrar por stock/status)
    pending_sales = [
        s for s in all_sales
        if s['stockId'] == stock_id
        and str(s.get("attendantUserId")) == str(user_id)
        and str(s.get("paymentMethod") or "cash").lower() == "cash"
        and not s.get("cashCutId")
    ]
    
    if not pending_sales:
        return utils._json_response(400, {"message": "No hay ventas pendientes para corte"})

    total_cash = sum([utils._to_decimal(s['total']) for s in pending_sales])
    if cash_to_keep < utils.D_ZERO:
        return utils._json_response(400, {"message": "El monto a dejar en caja no puede ser negativo"})
    if cash_to_keep > total_cash:
        return utils._json_response(400, {"message": "El monto a dejar en caja no puede exceder el total en efectivo"})
    cut_id = f"CUT-{utils.uuid.uuid4().hex[:8].upper()}"
    now = utils._now_iso()

    cut_item = {
        "entityType": "posCashCut", "cashCutId": cut_id, "stockId": stock_id,
        "total": total_cash,
        "salesCount": len(pending_sales),
        "cashToKeep": cash_to_keep,
        "withdrawnAmount": total_cash - cash_to_keep,
        "attendantUserId": user_id,
        "startedAt": pending_sales[0].get("createdAt") if pending_sales else now,
        "endedAt": now,
        "createdAt": now
    }
    utils._put_entity("POS_CASH_CUT", cut_id, cut_item)

    # Marcar ventas con el ID del corte
    for s in pending_sales:
        utils._update_by_id("POS_SALE", s['saleId'], "SET cashCutId = :c", {":c": cut_id})

    return utils._json_response(201, {"cut": cut_item, "control": _build_pos_cash_control(stock_id, user_id)})

# --- LAMBDA ROUTER ---

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    raw_segments = [s for s in path.strip("/").split("/") if s]
    # Strip "inventory" prefix: API Gateway sends /inventory/{proxy+}
    segments = raw_segments[1:] if raw_segments and raw_segments[0] == "inventory" else raw_segments

    try:
        if not segments: return utils._json_response(200, {"service": "inventory-pos"})

        root = segments[0]

        # /inventory/stocks  →  root == "stocks"
        if root == "stocks":
            if len(segments) == 1:
                if method in ("POST", "PATCH"):
                    err = utils._require_admin(headers, "stock_create")
                    if err: return err
                return handle_stocks(method, body)

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
        if root == "pos":
            if segments[1] == "sales":
                err = utils._require_admin(headers, "pos_register_sale")
                if err: return err
                if method == "GET":
                    sid = query.get("stockId")
                    sales = utils._query_bucket("POS_SALE")
                    if sid:
                        sales = [s for s in sales if str(s.get("stockId") or "") == str(sid)]
                    return utils._json_response(200, {"sales": sales})
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
                # Si no se provee stockId, usar el primero vinculado al operador
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

        # /pickup-stocks
        if root == "pickup-stocks":
            stocks = [s for s in utils._query_bucket("STOCK") if s.get("allowPickup")]
            return utils._json_response(200, {"stocks": stocks})

        return utils._json_response(404, {"message": "Ruta de inventario no encontrada"})

    except Exception as e:
        print(f"[INVENTORY_ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Internal Inventory Error", "error": str(e)})
