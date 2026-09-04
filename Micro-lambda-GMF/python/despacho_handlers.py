"""Paquete D · almacén, despacho y paquetería (propuestas 9, 13, 20 y 23a).

Extensión en cascada de `inventory_lambda` (docs/arquitectura/23 §0.2 y §4).
Rutas (prefijo `/inventory` ya retirado por el anfitrión):

    GET  despacho/pendientes?stockId=          order_mark_shipped
    POST despacho/surtido                      order_mark_shipped
    POST despacho/enviar                       order_mark_shipped
    GET  despacho/preferencias                 sesión de empleado
    PUT  despacho/preferencias                 sesión de empleado
    POST envios/rastrear        (programable)  order_mark_delivered o superadmin
    POST envios/cerrar          (programable)  order_mark_delivered o superadmin
    GET|POST envios/{orderId}/confirmar-entrega?token=   pública (enlace del correo)
    GET  turno/resumen?userId=&date=           access_screen_stats o el propio usuario
    POST turno/resumen/enviar                  access_screen_stats o el propio usuario

Lo que vivió la gente (docs/qa/22 §6): Beto transcribía 13 productos por 10
pedidos para saber si alcanzaba el inventario, copiaba cada guía de WhatsApp
en 7 pasos, marcaba entregados uno a uno y redactaba a mano el mensaje de
cierre de turno; cuatro pedidos se quedaron meses en "Enviada".
"""
import csv
import html
import io
import json
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import core_utils as utils
from core import email as correo
from core import order_emails
from core.http import HttpRequest

import carriers
import order_lambda


TAREAS_PROGRAMADAS = [
    ("POST", "/inventory/envios/rastrear"),
    ("POST", "/inventory/envios/cerrar"),
]

FRONTEND_BASE_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")
# URL pública del API para el enlace "Sí, ya llegó" del correo. Sin ella el
# botón lleva al seguimiento del pedido (donde el cliente ve el estado).
API_BASE_URL = utils.os.getenv("API_BASE_URL", "").rstrip("/")

# Ventana de lectura de pedidos: los enviados/pagados que importan son recientes
# y el SK lleva la fecha de creación, así se acota la consulta por clave.
DIAS_VENTANA_PEDIDOS = 120
MAX_EVENTOS_RASTREO = 50


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _fecha(iso) -> Optional[datetime]:
    texto = str(iso or "").strip()
    if not texto:
        return None
    try:
        dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _dias_desde(iso) -> Optional[int]:
    dt = _fecha(iso)
    return None if dt is None else max(0, (_ahora() - dt).days)


def _desde(dias: int) -> str:
    return (_ahora() - timedelta(days=dias)).strftime("%Y-%m-%d")


def _integracion(cfg=None) -> dict:
    cfg = cfg if cfg is not None else utils._load_app_config()
    return dict(((cfg.get("shipping") or {}).get("carrierIntegration")) or {})


def _es_domicilio(order: dict) -> bool:
    return str(order.get("deliveryType") or "").strip().lower() != "pickup"


def _cantidad(item: dict) -> int:
    try:
        return int(item.get("quantity") or item.get("qty") or 0)
    except (TypeError, ValueError):
        return 0


def _lineas_pedido(order: dict, nombres: Optional[dict] = None) -> list:
    """Líneas del pedido con nombre. Si la línea no lo trae, se resuelve desde
    el catálogo (`nombres` cachea por invocación) en vez de mostrar el id."""
    salida = []
    for it in order.get("items") or []:
        pid = str(it.get("productId") or "").strip()
        qty = _cantidad(it)
        if pid and qty > 0:
            nombre = it.get("name")
            if not nombre:
                if nombres is None:
                    nombres = {}
                if pid not in nombres:
                    nombres[pid] = (utils._get_by_id("PRODUCT", pid) or {}).get("name") or f"Producto {pid}"
                nombre = nombres[pid]
            salida.append({"productId": pid, "name": nombre, "quantity": qty})
    return salida


def _nombre_stock(stock: dict) -> str:
    return str(stock.get("name") or stock.get("stockId") or "").strip()


def _stock_id(stock: dict) -> str:
    return str(stock.get("stockId") or stock.get("id") or "").strip()


def _resumen_pedido(order: dict, nombres: Optional[dict] = None) -> dict:
    """Lo que la pantalla de despacho necesita de cada pedido pagado."""
    return {
        "id": order.get("orderId"),
        "customer": order.get("customerName") or order.get("recipientName") or "Cliente",
        "recipientName": order.get("recipientName") or order.get("customerName") or "",
        "createdAt": order.get("createdAt"),
        "paidAt": order.get("paidAt") or order.get("updatedAt"),
        "daysSincePaid": _dias_desde(order.get("paidAt") or order.get("updatedAt")),
        "items": _lineas_pedido(order, nombres),
        "city": order.get("city") or (order.get("shippingAddress") or {}).get("city") or "",
        "state": order.get("state") or (order.get("shippingAddress") or {}).get("state") or "",
        "hasInvoiceRequest": bool(order.get("invoiceRequested") or order.get("invoiceStatus")),
        "shippingCarrier": order.get("shippingCarrier") or "",
        "trackingNumber": order.get("trackingNumber") or "",
        "total": order.get("total") if order.get("total") is not None else order.get("netTotal"),
        "status": order.get("status"),
    }


def _pedidos_recientes() -> list:
    return utils._query_bucket("ORDER", sk_from=_desde(DIAS_VENTANA_PEDIDOS))


def _pedidos_por_despachar() -> list:
    """Pagados con envío a domicilio: los únicos que entran al bloque."""
    return [o for o in _pedidos_recientes()
            if str(o.get("status") or "").lower() == "paid" and _es_domicilio(o)]


def _pedidos_enviados() -> list:
    return [o for o in _pedidos_recientes()
            if str(o.get("status") or "").lower() == "shipped" and _es_domicilio(o)]


def _cabeceras_internas(headers: dict) -> dict:
    """Cabeceras con las que se llama a `handle_update_status` desde una tarea.

    Si quien dispara es un actor del back office se conservan (queda su id en
    el pedido); si es el enlace público del cliente o un programador, se usa
    el actor de sistema para que el pedido acepte los campos de entrega.
    """
    actor = utils._extract_actor(headers or {})
    if actor.get("role") in ("admin", "employee") and actor.get("user_id"):
        return headers
    return {"x-user-id": "sistema", "x-user-role": "admin"}


def _marcar_entregado(order: dict, headers: dict, delivered_by: str, delivered_at: str = "",
                      signed_by: str = "", extra: Optional[dict] = None):
    """Entrega "normal": pasa por `handle_update_status` (inventario, correo,
    ORDER_DELIVERED → confirma comisiones) y después guarda los campos propios."""
    oid = order.get("orderId")
    cuerpo = {"status": "delivered", "deliveredBy": delivered_by}
    if delivered_at:
        cuerpo["deliveredAt"] = delivered_at
    if signed_by:
        cuerpo["deliverySignedBy"] = signed_by
    respuesta = order_lambda.handle_update_status(oid, cuerpo, _cabeceras_internas(headers))
    if respuesta.get("statusCode") != 200:
        return None, respuesta
    if extra:
        partes, valores = [], {}
        for i, (campo, valor) in enumerate(extra.items()):
            partes.append(f"{campo} = :v{i}")
            valores[f":v{i}"] = valor
        utils._update_by_id("ORDER", oid, "SET " + ", ".join(partes), valores)
    return utils._get_by_id("ORDER", oid), None


# ─────────────────────────────────────────────────────────────────────────────
# Despacho en bloque
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_surtido(stock: dict, orders: list, todos_los_stocks: Optional[list] = None) -> dict:
    """Consolida por producto y compara contra el inventario de la bodega.

    Devuelve las líneas con semáforo (`ok` / `short`) y, en rojo, qué otras
    bodegas sí tienen el faltante, para que el motivo del bloqueo diga a dónde
    ir en vez de solo "no alcanza".
    """
    necesario, nombres = {}, {}
    for order in orders:
        for linea in _lineas_pedido(order, nombres):
            entrada = necesario.setdefault(linea["productId"], {"name": linea["name"], "needed": 0})
            entrada["needed"] += linea["quantity"]

    inventario = {str(k): int(v) for k, v in (stock.get("inventory") or {}).items()}
    otros = [s for s in (todos_los_stocks if todos_los_stocks is not None else utils._query_bucket("STOCK"))
             if _stock_id(s) != _stock_id(stock)]

    lineas, motivos = [], []
    for pid, datos in sorted(necesario.items(), key=lambda kv: kv[1]["name"].lower()):
        disponible = inventario.get(pid, 0)
        faltan = max(0, datos["needed"] - disponible)
        linea = {"productId": pid, "name": datos["name"], "needed": datos["needed"],
                 "available": disponible, "status": "short" if faltan else "ok", "short": faltan, "elsewhere": []}
        if faltan:
            for otro in otros:
                existencia = int((otro.get("inventory") or {}).get(pid, 0) or 0)
                if existencia >= faltan:
                    linea["elsewhere"].append({"stockId": _stock_id(otro), "name": _nombre_stock(otro), "available": existencia})
            if linea["elsewhere"]:
                donde = "; ".join(f"{e['name']} tiene {e['available']}" for e in linea["elsewhere"])
                motivos.append(f"Faltan {faltan} {datos['name']} en {_nombre_stock(stock)}; {donde}: transfiere o quita el pedido que lo lleva.")
            else:
                motivos.append(f"Faltan {faltan} {datos['name']} en {_nombre_stock(stock)} y ninguna otra bodega los tiene: quita el pedido que lo lleva o registra una entrada.")
        lineas.append(linea)

    return {
        "stockId": _stock_id(stock),
        "stockName": _nombre_stock(stock),
        "canDispatch": bool(orders) and not any(l["status"] == "short" for l in lineas),
        "lines": lineas,
        "reasons": motivos,
        "orderCount": len(orders),
    }


def _clasificar_pedidos(order_ids: list):
    """Separa los pedidos que pueden ir al bloque de los que no, con el motivo."""
    aptos, bloqueados, vistos = [], [], set()
    for oid in order_ids:
        oid = str(oid or "").strip()
        if not oid or oid in vistos:
            continue
        vistos.add(oid)
        order = utils._get_by_id("ORDER", oid)
        if not order:
            bloqueados.append({"orderId": oid, "reason": "El pedido no existe"})
        elif str(order.get("status") or "").lower() != "paid":
            bloqueados.append({"orderId": oid, "reason": f"Está en estado '{order.get('status')}'; solo se despachan pedidos pagados"})
        elif not _es_domicilio(order):
            bloqueados.append({"orderId": oid, "reason": "Es para recoger en sucursal; se entrega en mostrador, no se despacha"})
        else:
            aptos.append(order)
    return aptos, bloqueados


def handle_despacho_pendientes(query: dict) -> dict:
    """GET despacho/pendientes — pagados a domicilio y enviados sin entrega."""
    integracion = _integracion()
    ask_days = int(integracion.get("askDays") or 7)
    nombres = {}
    pendientes = sorted((_resumen_pedido(o, nombres) for o in _pedidos_por_despachar()),
                        key=lambda p: str(p.get("paidAt") or ""))
    rezagados = []
    for order in _pedidos_enviados():
        dias = _dias_desde(order.get("shippedAt") or order.get("updatedAt"))
        if dias is not None and dias >= ask_days:
            rezagados.append({
                "id": order.get("orderId"),
                "customer": order.get("customerName") or order.get("recipientName") or "Cliente",
                "shippedAt": order.get("shippedAt") or order.get("updatedAt"),
                "daysSinceShipped": dias,
                "trackingNumber": order.get("trackingNumber") or "",
                "shippingCarrier": order.get("shippingCarrier") or "",
                "deliveryCheckEmailSentAt": order.get("deliveryCheckEmailSentAt"),
            })
    rezagados.sort(key=lambda r: -int(r["daysSinceShipped"]))
    return utils._json_response(200, {
        "orders": pendientes,
        "staleShipped": rezagados,
        "carrierIntegration": {
            "enabled": bool(integracion.get("enabled")),
            "provider": integracion.get("provider") or "envia",
            "trackingEnabled": bool(integracion.get("trackingEnabled")),
            "askDays": ask_days,
            "autoCloseDays": int(integracion.get("autoCloseDays") or 10),
        },
    })


def handle_despacho_surtido(body: dict) -> dict:
    """POST despacho/surtido — lista consolidada con semáforo."""
    order_ids = list((body or {}).get("orderIds") or [])
    if not order_ids:
        return utils._json_response(400, {"message": "Selecciona al menos un pedido para calcular el surtido"})
    stock_id = str((body or {}).get("stockId") or "").strip()
    stock = utils._get_by_id("STOCK", stock_id) if stock_id else None
    if not stock:
        return utils._json_response(404, {"message": "La bodega no existe; elige una de la lista"})
    aptos, bloqueados = _clasificar_pedidos(order_ids)
    surtido = _calcular_surtido(stock, aptos)
    surtido["blockedOrders"] = bloqueados
    surtido["orderIds"] = [o.get("orderId") for o in aptos]
    return utils._json_response(200, surtido)


def _leer_csv_guias(texto: str) -> dict:
    """`orderId,carrier,tracking` (con o sin encabezado; coma, punto y coma o tabulador)."""
    guias = {}
    if not texto:
        return guias
    for fila in csv.reader(io.StringIO(str(texto).replace("\t", ",").replace(";", ","))):
        celdas = [c.strip() for c in fila]
        if not celdas or not celdas[0]:
            continue
        if celdas[0].lower() in ("orderid", "pedido", "folio", "order", "id"):
            continue
        oid = celdas[0]
        carrier = celdas[1] if len(celdas) > 1 else ""
        tracking = celdas[2] if len(celdas) > 2 else ""
        guias[oid] = {"carrier": carrier, "trackingNumber": tracking}
    return guias


def handle_despacho_enviar(body: dict, headers: dict) -> dict:
    """POST despacho/enviar — marca en bloque como enviados.

    Primero se valida el surtido completo (409 STOCK_SHORT si falta algo);
    después se despacha lo que se puede, pedido por pedido, y se informa lo
    que falló con su motivo. Cada pedido pasa por `handle_update_status`:
    misma salida de inventario y mismo correo "va en camino" que el despacho
    de uno en uno.
    """
    body = body or {}
    stock_id = str(body.get("stockId") or "").strip()
    stock = utils._get_by_id("STOCK", stock_id) if stock_id else None
    if not stock:
        return utils._json_response(404, {"message": "La bodega no existe; elige una de la lista"})

    guias = {}
    for envio in body.get("shipments") or []:
        oid = str((envio or {}).get("orderId") or "").strip()
        if oid:
            guias[oid] = {"carrier": str(envio.get("carrier") or "").strip(),
                          "trackingNumber": str(envio.get("trackingNumber") or envio.get("tracking") or "").strip()}
    for oid, guia in _leer_csv_guias(body.get("csv") or "").items():
        previa = guias.get(oid) or {}
        guias[oid] = {"carrier": guia["carrier"] or previa.get("carrier", ""),
                      "trackingNumber": guia["trackingNumber"] or previa.get("trackingNumber", "")}
    for oid in body.get("orderIds") or []:
        guias.setdefault(str(oid).strip(), {"carrier": "", "trackingNumber": ""})

    aptos, bloqueados = _clasificar_pedidos(list(guias))
    if not aptos:
        return utils._json_response(400, {"message": "No hay pedidos pagados a domicilio en la selección",
                                          "failed": bloqueados})

    surtido = _calcular_surtido(stock, aptos)
    if not surtido["canDispatch"]:
        return utils._json_response(409, {
            "code": "STOCK_SHORT",
            "message": "El surtido no alcanza en esta bodega. " + " ".join(surtido["reasons"]),
            **surtido, "blockedOrders": bloqueados,
        })

    integracion = _integracion()
    generar = bool(body.get("generateLabels")) and bool(integracion.get("enabled"))
    paqueteria = carriers.paqueteria_activa() if generar else None
    actor = utils._extract_actor(headers or {})
    batch_id = f"DSP-{utils.uuid.uuid4().hex[:10].upper()}"
    enviados, fallidos = [], list(bloqueados)

    for order in aptos:
        oid = order.get("orderId")
        guia = guias.get(oid) or {}
        carrier = guia.get("carrier") or order.get("shippingCarrier") or ""
        tracking = guia.get("trackingNumber") or ""
        label_url = ""
        if not tracking and paqueteria is not None:
            try:
                generada = paqueteria.generar_guia(order)
                carrier, tracking, label_url = generada.get("carrier") or carrier, generada.get("trackingNumber") or "", generada.get("labelUrl") or ""
            except Exception as exc:  # noqa: BLE001 — un pedido sin guía no detiene el bloque
                fallidos.append({"orderId": oid, "reason": f"La paquetería no generó la guía: {exc}"})
                continue
        if not tracking:
            fallidos.append({"orderId": oid, "reason": "Falta la guía: captúrala, impórtala por CSV o genérala con la paquetería"})
            continue
        cuerpo = {
            "status": "shipped", "stockId": stock_id, "shippingType": "carrier",
            "shippingCarrier": carrier or "Paquetería", "trackingNumber": tracking,
            "dispatchLines": [{"productId": l["productId"], "quantity": l["quantity"]} for l in _lineas_pedido(order)],
            "dispatchBatchId": batch_id,
        }
        if label_url:
            cuerpo["labelUrl"] = label_url
        respuesta = order_lambda.handle_update_status(oid, cuerpo, headers)
        if respuesta.get("statusCode") == 200:
            enviados.append({"orderId": oid, "trackingNumber": tracking, "carrier": cuerpo["shippingCarrier"],
                             "labelUrl": label_url, "status": "shipped",
                             "customer": order.get("customerName") or order.get("recipientName") or "Cliente"})
        else:
            try:
                motivo = json.loads(respuesta.get("body") or "{}").get("message") or "No se pudo marcar como enviado"
            except Exception:
                motivo = "No se pudo marcar como enviado"
            fallidos.append({"orderId": oid, "reason": motivo})

    lote = {
        "entityType": "dispatchBatch", "batchId": batch_id, "stockId": stock_id,
        "orderIds": [o.get("orderId") for o in aptos],
        "shipments": [{"orderId": e["orderId"], "carrier": e["carrier"], "trackingNumber": e["trackingNumber"]} for e in enviados],
        "createdBy": str(actor.get("user_id") or (headers or {}).get("x-user-id") or "system"),
        "createdAt": utils._now_iso(),
        "results": {"shipped": len(enviados), "failed": len(fallidos)},
    }
    utils._put_entity("DISPATCH_BATCH", batch_id, lote)
    utils._audit_event("despacho.enviar", headers, {"stockId": stock_id, "orderIds": lote["orderIds"]},
                       {"batchId": batch_id, "shipped": [e["orderId"] for e in enviados]})
    return utils._json_response(200, {"batchId": batch_id, "stockId": stock_id, "stockName": _nombre_stock(stock),
                                      "shipped": enviados, "failed": fallidos})


# ─────────────────────────────────────────────────────────────────────────────
# Bodega por defecto del empleado
# ─────────────────────────────────────────────────────────────────────────────

def _perfil_empleado(user_id):
    """(entidad, item) del perfil que opera el back office: EMPLOYEE o, si es
    una socia con acceso, CUSTOMER."""
    if user_id in (None, ""):
        return None, None
    for entidad, clave in (("EMPLOYEE", user_id), ("CUSTOMER", utils._customer_entity_id(user_id))):
        try:
            item = utils._get_by_id(entidad, clave)
        except Exception:
            item = None
        if item:
            return entidad, item
    return None, None


def handle_preferencias(method: str, body: dict, headers: dict) -> dict:
    """GET|PUT despacho/preferencias — la bodega con la que arranca la persona."""
    actor = utils._extract_actor(headers or {})
    if actor.get("role") not in ("admin", "employee") or not actor.get("user_id"):
        return utils._json_response(401, {"message": "Inicia sesión con tu cuenta de empleado"})
    entidad, perfil = _perfil_empleado(actor.get("user_id"))
    if not perfil:
        return utils._json_response(404, {"message": "No encontramos tu perfil de empleado"})

    if method == "GET":
        stock_id = str(perfil.get("defaultStockId") or "").strip()
        stock = utils._get_by_id("STOCK", stock_id) if stock_id else None
        return utils._json_response(200, {"defaultStockId": stock_id or None,
                                          "stockName": _nombre_stock(stock) if stock else None})

    stock_id = str((body or {}).get("defaultStockId") or "").strip()
    if not stock_id:
        return utils._json_response(400, {"message": "Elige la bodega que quieres usar por defecto"})
    stock = utils._get_by_id("STOCK", stock_id)
    if not stock:
        return utils._json_response(404, {"message": "La bodega no existe; elige una de la lista"})
    clave = actor.get("user_id") if entidad == "EMPLOYEE" else utils._customer_entity_id(actor.get("user_id"))
    utils._update_by_id(entidad, clave, "SET defaultStockId = :s, updatedAt = :u", {":s": stock_id, ":u": utils._now_iso()})
    return utils._json_response(200, {"defaultStockId": stock_id, "stockName": _nombre_stock(stock)})


# ─────────────────────────────────────────────────────────────────────────────
# Rastreo y cierre automático (tareas programables)
# ─────────────────────────────────────────────────────────────────────────────

def _eventos_rastreo(order: dict, nuevos: list) -> list:
    previos = list(order.get("trackingEvents") or [])
    vistos = {(e.get("at"), e.get("text")) for e in previos if isinstance(e, dict)}
    for ev in nuevos or []:
        if isinstance(ev, dict) and (ev.get("at"), ev.get("text")) not in vistos:
            previos.append({"at": ev.get("at"), "text": ev.get("text")})
            vistos.add((ev.get("at"), ev.get("text")))
    return previos[-MAX_EVENTOS_RASTREO:]


def handle_envios_rastrear(body: dict, headers: dict) -> dict:
    """POST envios/rastrear — consulta la paquetería y entrega con fecha y firma."""
    body = body or {}
    dry_run = bool(body.get("dryRun"))
    cfg = utils._load_app_config()
    integracion = _integracion(cfg)
    if not (integracion.get("enabled") and integracion.get("trackingEnabled")):
        return utils._json_response(200, {
            "enabled": False, "checked": 0, "delivered": [], "inTransit": [], "errors": [],
            "message": "El rastreo automático está apagado: enciende shipping.carrierIntegration.enabled y trackingEnabled en Configuración.",
        })

    if body.get("orderIds"):
        pedidos = [o for o in (utils._get_by_id("ORDER", oid) for oid in body["orderIds"]) if o]
    else:
        pedidos = _pedidos_enviados()
    pedidos = [o for o in pedidos if str(o.get("status") or "").lower() == "shipped" and o.get("trackingNumber")]

    paqueteria = carriers.paqueteria_activa(cfg)
    entregados, en_transito, errores = [], [], []
    for order in pedidos:
        oid = order.get("orderId")
        resultado = paqueteria.rastrear(order.get("shippingCarrier") or "", order.get("trackingNumber") or "", order=order)
        eventos = _eventos_rastreo(order, resultado.get("events") or [])
        estado = resultado.get("status")
        if estado == "delivered":
            entregados.append({"orderId": oid, "deliveredAt": resultado.get("deliveredAt") or utils._now_iso(),
                               "signedBy": resultado.get("signedBy") or ""})
            if not dry_run:
                _, error = _marcar_entregado(
                    order, headers, "carrier", resultado.get("deliveredAt") or utils._now_iso(),
                    resultado.get("signedBy") or "",
                    {"carrierDeliveredAt": resultado.get("deliveredAt") or utils._now_iso(), "trackingEvents": eventos})
                if error:
                    errores.append({"orderId": oid, "text": "No se pudo marcar entregado", "detail": error.get("body")})
        else:
            if estado == "exception":
                # La incidencia se anota en el pedido sin cambiar su estado.
                errores.append({"orderId": oid, "text": eventos[-1]["text"] if eventos else "Incidencia en la paquetería"})
            else:
                en_transito.append(oid)
            if not dry_run:
                utils._update_by_id("ORDER", oid, "SET trackingEvents = :e, lastTrackedAt = :t",
                                    {":e": eventos, ":t": utils._now_iso()})
    return utils._json_response(200, {"enabled": True, "dryRun": dry_run, "checked": len(pedidos),
                                      "delivered": entregados, "inTransit": en_transito, "errors": errores})


def _url_confirmacion(order_id: str, token: str) -> str:
    if API_BASE_URL:
        return f"{API_BASE_URL}/inventory/envios/{order_id}/confirmar-entrega?token={token}"
    return f"{FRONTEND_BASE_URL.rstrip('/')}/#/orden/{order_id}"


def _preguntar_si_llego(order: dict) -> bool:
    """Manda "¿te llegó?" con un enlace de un solo uso; devuelve si hubo a quién."""
    oid = order.get("orderId")
    token = secrets.token_urlsafe(24)
    datos = {
        "confirmUrl": _url_confirmacion(oid, token),
        "supportUrl": f"mailto:{utils.SES_FROM_EMAIL}?subject=Mi pedido {oid} no ha llegado",
    }
    enviado = order_emails.notificar_pedido(order, "delivery_check", datos,
                                            lambda cid: utils._get_by_id("CUSTOMER", cid), FRONTEND_BASE_URL)
    utils._update_by_id("ORDER", oid, "SET deliveryCheckEmailSentAt = :a, deliveryCheckTokenHash = :h",
                        {":a": utils._now_iso(), ":h": utils._hash_token(token)})
    return enviado


def handle_envios_cerrar(body: dict, headers: dict) -> dict:
    """POST envios/cerrar — "¿te llegó?" a los askDays y cierre a los autoCloseDays."""
    body = body or {}
    dry_run = bool(body.get("dryRun"))
    integracion = _integracion()
    if not integracion.get("enabled"):
        return utils._json_response(200, {
            "enabled": False, "checked": 0, "asked": [], "closed": [],
            "message": "El cierre automático está apagado: enciende shipping.carrierIntegration.enabled en Configuración.",
        })
    ask_days = int(integracion.get("askDays") or 7)
    close_days = int(integracion.get("autoCloseDays") or 10)

    pedidos = _pedidos_enviados()
    preguntados, cerrados = [], []
    for order in pedidos:
        oid = order.get("orderId")
        dias = _dias_desde(order.get("shippedAt") or order.get("updatedAt"))
        if dias is None:
            continue
        if dias >= close_days:
            cerrados.append(oid)
            if not dry_run:
                nota = {"text": f"Cerrado automáticamente a los {dias} días del envío sin confirmación de entrega.",
                        "by": "sistema", "at": utils._now_iso()}
                _marcar_entregado(order, headers, "auto", utils._now_iso(), "",
                                  {"autoClosedAt": utils._now_iso(),
                                   "adminNotes": (list(order.get("adminNotes") or []) + [nota])[-200:]})
        elif dias >= ask_days and not order.get("deliveryCheckEmailSentAt"):
            preguntados.append(oid)
            if not dry_run:
                _preguntar_si_llego(order)
    return utils._json_response(200, {"enabled": True, "dryRun": dry_run, "checked": len(pedidos),
                                      "askDays": ask_days, "autoCloseDays": close_days,
                                      "asked": preguntados, "closed": cerrados})


_PAGINA_CONFIRMACION = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Finding'U · Entrega confirmada</title>
<style>body{{font-family:system-ui,sans-serif;background:#F9F7F2;margin:0}}main{{max-width:480px;margin:48px auto;background:#fff;border-radius:16px;padding:32px;text-align:center;border:1px solid #e8e3d8}}
h1{{font-size:22px;color:#2D3436}}p{{color:#636e72;line-height:1.6}}a{{display:inline-block;margin-top:16px;background:#D4AF37;color:#333;padding:12px 28px;border-radius:50px;text-decoration:none;font-weight:bold}}</style></head>
<body><main><h1>{titulo}</h1><p>{texto}</p>{formulario}<a href="{url}">Ver mi pedido</a></main></body></html>"""

# El botón del correo es un enlace (GET) y los escáneres de correo (SafeLinks,
# Gmail, antivirus) siguen los enlaces: el GET solo muestra la página con el
# botón; el cambio de estado vive únicamente en el POST del formulario (§4.3).
_FORMULARIO_CONFIRMACION = ("""<form method="post" action="{accion}" style="margin-top:16px">"""
                            """<button type="submit" style="background:#D4AF37;color:#333;border:0;padding:12px 28px;border-radius:50px;font-weight:bold;cursor:pointer">Sí, ya llegó</button></form>""")


def _respuesta_confirmacion(en_navegador: bool, status: int, titulo: str, texto: str, order_id: str,
                            estado: str = "", formulario: str = "") -> dict:
    if en_navegador:
        html = _PAGINA_CONFIRMACION.format(titulo=titulo, texto=texto, formulario=formulario,
                                           url=f"{FRONTEND_BASE_URL.rstrip('/')}/#/orden/{order_id}")
        return {"statusCode": status, "headers": utils._cors_headers("text/html; charset=utf-8"), "body": html}
    return utils._json_response(status, {"status": estado, "message": texto})


def handle_confirmar_entrega(order_id: str, method: str, query: dict, headers: dict) -> dict:
    """GET|POST envios/{orderId}/confirmar-entrega?token= — "Sí, ya llegó" del correo.

    GET: página con el botón (sin efectos). POST: marca la entrega; con `ui=1`
    (el formulario de la página) responde HTML, si no JSON.
    """
    query = query or {}
    token = str(query.get("token") or "").strip()
    en_navegador = method == "GET" or str(query.get("ui") or "") == "1"
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return _respuesta_confirmacion(en_navegador, 404, "No encontramos el pedido", "Revisa el enlace del correo o escríbenos a soporte.", order_id)
    esperado = str(order.get("deliveryCheckTokenHash") or "")
    if not token or not esperado or utils._hash_token(token) != esperado:
        return _respuesta_confirmacion(en_navegador, 401, "Enlace no válido",
                                       "Este enlace ya no sirve. Entra a tu seguimiento para ver el estado del pedido.", order_id)
    if str(order.get("status") or "").lower() == "delivered":
        return _respuesta_confirmacion(en_navegador, 200, "Tu pedido ya estaba marcado como entregado",
                                       "Gracias por confirmarnos. No hace falta hacer nada más.", order_id, "delivered")
    if str(order.get("status") or "").lower() != "shipped":
        return _respuesta_confirmacion(en_navegador, 409, "El pedido no está en camino",
                                       f"Está en estado '{order.get('status')}'; revisa tu seguimiento.", order_id, str(order.get("status")))
    if method == "GET":
        accion = f"?token={urllib.parse.quote(token, safe='')}&ui=1"
        return _respuesta_confirmacion(True, 200, "¿Ya te llegó tu pedido?",
                                       f"Confírmanos con un clic que el pedido {order_id} llegó bien.", order_id, "shipped",
                                       formulario=_FORMULARIO_CONFIRMACION.format(accion=accion))
    _, error = _marcar_entregado(order, headers, "cliente", utils._now_iso(), "Confirmado por el cliente desde el correo")
    if error:
        return _respuesta_confirmacion(en_navegador, 500, "No pudimos guardar la confirmación", "Inténtalo de nuevo en unos minutos.", order_id)
    return _respuesta_confirmacion(en_navegador, 200, "¡Gracias! Marcamos tu pedido como entregado",
                                   f"El pedido {order_id} quedó cerrado. Si algo llegó mal, pide la devolución desde tu seguimiento.",
                                   order_id, "delivered")


# ─────────────────────────────────────────────────────────────────────────────
# Resumen de turno
# ─────────────────────────────────────────────────────────────────────────────

def _mismo_dia(iso, fecha: str) -> bool:
    return str(iso or "").startswith(fecha)


def _nombre_usuario(user_id) -> str:
    _, perfil = _perfil_empleado(user_id)
    return str((perfil or {}).get("name") or user_id or "").strip()


def _nombres_de_stocks() -> dict:
    return {_stock_id(s): _nombre_stock(s) for s in utils._query_bucket("STOCK")}


def _nombres_de_productos(ids: set) -> dict:
    nombres = {}
    for pid in ids:
        producto = utils._get_by_id("PRODUCT", pid) or {}
        nombres[str(pid)] = producto.get("name") or f"Producto {pid}"
    return nombres


def _texto_resumen(resumen: dict) -> str:
    """El mensaje que Beto redactaba a mano al cerrar (texto plano para WhatsApp)."""
    partes = [f"Resumen de turno · {resumen['user']['name']} · {resumen['date']}"]
    d = resumen["dispatched"]
    partes.append(f"Despachados ({len(d)}): " + (", ".join(
        f"{x['orderId']} ({x['carrier']} {x['trackingNumber']})".replace("( ", "(").replace(" )", ")") for x in d) if d else "ninguno"))
    e = resumen["delivered"]
    partes.append(f"Entregados ({len(e)}): " + (", ".join(
        f"{x['orderId']}" + (f" (firmó {x['signedBy']})" if x.get("signedBy") else "") for x in e) if e else "ninguno"))
    tc, tr = resumen["transfers"]["created"], resumen["transfers"]["received"]
    if tc:
        partes.append("Transferencias creadas: " + ", ".join(f"{t['transferId']} → {t['destination']}" for t in tc))
    if tr:
        partes.append("Transferencias recibidas: " + ", ".join(
            f"{t['transferId']}" + (f" (faltaron {t['missing']})" if t.get("missing") else " (completa)") for t in tr))
    if resumen["entries"]:
        partes.append("Entradas: " + ", ".join(f"{x['qty']} {x['name']}" for x in resumen["entries"]))
    if resumen["damages"]:
        partes.append("Mermas: " + ", ".join(f"{x['qty']} {x['name']}" + (f" ({x['reason']})" if x.get("reason") else "") for x in resumen["damages"]))
    pos = resumen["pos"]
    if pos["sales"] or pos["cuts"]:
        partes.append(f"Caja: {len(pos['sales'])} ventas por ${pos['salesTotal']:,.2f}; cortes: {len(pos['cuts'])}")
    return "\n".join(partes)


def _escapar(texto) -> str:
    return html.escape(str(texto or ""))


def _id_resumen(user_id: str, fecha: str) -> str:
    """Un registro de envío por persona y día: mandar dos veces no duplica."""
    return f"TRN-{user_id}-{fecha}"


def _correo_resumen_configurado() -> str:
    """`pos.shiftSummaryNotifyEmail`: a quién se le entrega el turno."""
    pos = dict((utils._load_app_config() or {}).get("pos") or {})
    return str(pos.get("shiftSummaryNotifyEmail") or "").strip()


def _html_resumen(resumen: dict) -> str:
    """El mismo texto del resumen, en el correo, sin volver a calcularlo."""
    lineas = "".join(f"<p style='margin:6px 0'>{_escapar(linea)}</p>"
                     for linea in str(resumen.get("text") or "").split("\n") if linea.strip())
    cuerpo = (f"<h1 class='title'>Resumen de turno · {_escapar(str(resumen['user']['name']))}</h1>"
              f"<p>{_escapar(str(resumen['date']))}</p>{lineas}")
    return correo._email_shell(cuerpo)


def handle_enviar_resumen(body: dict, headers: dict) -> dict:
    """POST turno/resumen/enviar — entregar el turno sin WhatsApp (propuesta 30).

    Toño se lo mandaba a Renata por WhatsApp y Mireya no tuvo dónde reportar el
    sobrante. Calcado del correo del corte de caja: mismo destinatario
    configurable, mismo sello para que no se mande dos veces sin rastro.
    """
    user_id, fecha, err = _turno_pedido(body or {}, headers)
    if err:
        return err
    destino = str((body or {}).get("email") or "").strip() or _correo_resumen_configurado()
    if not destino or "@" not in destino:
        return utils._json_response(400, {
            "message": "No hay un correo al que entregar el turno: escribe uno aquí o pide a la gerente que lo "
                       "configure en Configuración → Punto de venta → Correo para resúmenes de turno."})

    registro_id = _id_resumen(user_id, fecha)
    previo = utils._get_by_id("POS_SHIFT_SUMMARY", registro_id) or {}
    if previo.get("notifiedAt") and not bool((body or {}).get("reenviar")):
        return utils._json_response(200, {
            "sent": False, "alreadySent": True, "to": previo.get("notifiedTo"), "sentAt": previo.get("notifiedAt"),
            "message": f"Este turno ya se entregó a {previo.get('notifiedTo')} el "
                       f"{previo.get('notifiedAt')}. Vuelve a enviarlo solo si hace falta."})

    resumen = armar_resumen(user_id, fecha)
    c = resumen["counters"]
    asunto = (f"Resumen de turno · {resumen['user']['name']} · {fecha}: "
              f"{c['dispatched']} despachados, {c['delivered']} entregados")
    correo._send_ses_email(destino, asunto, resumen["text"], _html_resumen(resumen))
    now = utils._now_iso()
    utils._put_entity("POS_SHIFT_SUMMARY", registro_id, {
        "entityType": "posShiftSummary", "summaryId": registro_id,
        "userId": user_id, "date": fecha,
        "notifiedTo": destino, "notifiedAt": now,
        "sentCount": int(previo.get("sentCount") or 0) + 1,
        "counters": c, "createdAt": previo.get("createdAt") or now,
    }, created_at_iso=previo.get("createdAt"))
    utils._audit_event("turno.resumen_enviado", headers, {"userId": user_id, "date": fecha},
                       {"to": destino})
    return utils._json_response(200, {"sent": True, "to": destino, "sentAt": now,
                                      "userId": user_id, "date": fecha, "counters": c})


def _turno_pedido(datos: dict, headers: dict):
    """(userId, fecha, error) del turno solicitado, con la misma autorización.

    El propio turno siempre; el de otra persona exige `access_screen_stats`.
    """
    actor = utils._extract_actor(headers or {})
    if actor.get("role") not in ("admin", "employee"):
        return "", "", utils._json_response(403, {"message": "Acceso denegado: se requiere perfil admin"})
    user_id = str((datos or {}).get("userId") or actor.get("user_id") or "").strip()
    if not user_id:
        return "", "", utils._json_response(400, {"message": "Indica de quién es el turno (userId)"})
    if user_id != str(actor.get("user_id") or ""):
        err = utils._require_admin(headers, "access_screen_stats")
        if err:
            return "", "", err
    fecha = str((datos or {}).get("date") or "").strip() or _ahora().strftime("%Y-%m-%d")
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return "", "", utils._json_response(400, {"message": "La fecha debe ir como AAAA-MM-DD"})
    return user_id, fecha, None


def armar_resumen(user_id: str, fecha: str) -> dict:
    """El resumen del turno, calculado una sola vez desde la bitácora.

    Es de los endpoints más llamados de la simulación: ni se recalcula dos
    veces ni se amplían sus ventanas de fecha.
    """
    stocks = _nombres_de_stocks()

    despachados, entregados = [], []
    for order in utils._query_bucket("ORDER", sk_from=_desde_fecha(fecha, 90), sk_to=fecha + "\uffff"):
        if str(order.get("shippedBy") or "") == user_id and _mismo_dia(order.get("shippedAt"), fecha):
            despachados.append({"orderId": order.get("orderId"), "customer": order.get("customerName") or order.get("recipientName") or "",
                                "carrier": order.get("shippingCarrier") or "", "trackingNumber": order.get("trackingNumber") or "",
                                "stock": stocks.get(str(order.get("stockId") or ""), str(order.get("stockId") or "")),
                                "at": order.get("shippedAt")})
        if str(order.get("deliveredBy") or "") == user_id and _mismo_dia(order.get("deliveredAt"), fecha):
            entregados.append({"orderId": order.get("orderId"), "customer": order.get("customerName") or order.get("recipientName") or "",
                               "signedBy": order.get("deliverySignedBy") or "", "at": order.get("deliveredAt")})

    creadas, recibidas = [], []
    for trf in utils._query_bucket("STOCK_TRANSFER", sk_from=_desde_fecha(fecha, 60), sk_to=fecha + "\uffff"):
        tid = trf.get("transferId")
        if str(trf.get("createdBy") or "") == user_id and _mismo_dia(trf.get("createdAt"), fecha):
            creadas.append({"transferId": tid, "source": stocks.get(str(trf.get("sourceStockId")), str(trf.get("sourceStockId"))),
                            "destination": stocks.get(str(trf.get("destinationStockId")), str(trf.get("destinationStockId"))),
                            "lines": len(trf.get("lines") or []), "at": trf.get("createdAt")})
        if str(trf.get("receivedBy") or "") == user_id and _mismo_dia(trf.get("receivedAt"), fecha):
            faltantes = trf.get("discrepancies") or []
            recibidas.append({"transferId": tid, "source": stocks.get(str(trf.get("sourceStockId")), str(trf.get("sourceStockId"))),
                              "missing": int(sum(int(d.get("missing") or 0) for d in faltantes)),
                              "discrepancies": faltantes, "at": trf.get("receivedAt")})

    movimientos = sorted((m for m in utils._query_bucket("INVENTORY_MOVEMENT", sk_prefix=fecha)
                          if str(m.get("userId") or "") == user_id),
                         key=lambda m: (str(m.get("createdAt") or ""), str(m.get("movementId") or "")))
    nombres = _nombres_de_productos({str(m.get("productId")) for m in movimientos})
    entradas = [{"productId": str(m.get("productId")), "name": nombres.get(str(m.get("productId"))), "qty": int(m.get("qty") or 0),
                 "stock": stocks.get(str(m.get("stockId")), str(m.get("stockId"))), "at": m.get("createdAt")}
                for m in movimientos if m.get("type") == "entry"]
    mermas = [{"productId": str(m.get("productId")), "name": nombres.get(str(m.get("productId"))), "qty": int(m.get("qty") or 0),
               "reason": m.get("reason") or "", "stock": stocks.get(str(m.get("stockId")), str(m.get("stockId"))), "at": m.get("createdAt")}
              for m in movimientos if m.get("type") in ("damage", "damaged")]

    ventas = [{"saleId": s.get("saleId"), "orderId": s.get("orderId"), "total": float(s.get("total") or 0),
               "customer": s.get("customerName") or "", "paymentMethod": s.get("paymentMethod") or "", "at": s.get("createdAt")}
              for s in utils._query_bucket("POS_SALE", sk_prefix=fecha)
              if str(s.get("attendantUserId") or "") == user_id and str(s.get("status") or "") != "voided"]
    cortes = [{"cashCutId": c.get("cashCutId"), "total": float(c.get("total") or 0), "at": c.get("createdAt")}
              for c in utils._query_bucket("POS_CASH_CUT", sk_prefix=fecha) if str(c.get("attendantUserId") or "") == user_id]

    eventos = [{"action": ev.get("action"), "target": ev.get("target") or {}, "at": ev.get("createdAt")}
               for ev in utils._query_bucket("ADMIN_EVENT", sk_prefix=fecha) if str(ev.get("actorUserId") or "") == user_id]

    resumen = {
        "user": {"id": user_id, "name": _nombre_usuario(user_id)},
        "date": fecha,
        "dispatched": sorted(despachados, key=lambda x: (str(x.get("at") or ""), str(x.get("orderId") or ""))),
        "delivered": sorted(entregados, key=lambda x: (str(x.get("at") or ""), str(x.get("orderId") or ""))),
        "transfers": {"created": creadas, "received": recibidas},
        "entries": entradas,
        "damages": mermas,
        "pos": {"sales": ventas, "salesTotal": round(sum(v["total"] for v in ventas), 2), "cuts": cortes},
        "events": eventos,
        "counters": {
            "dispatched": len(despachados), "delivered": len(entregados),
            "transfersCreated": len(creadas), "transfersReceived": len(recibidas),
            "entries": len(entradas), "damages": len(mermas),
            "posSales": len(ventas), "cashCuts": len(cortes), "events": len(eventos),
        },
    }
    resumen["text"] = _texto_resumen(resumen)
    return resumen


def handle_turno_resumen(query: dict, headers: dict) -> dict:
    """GET turno/resumen?userId=&date= — calculado al vuelo desde la bitácora."""
    user_id, fecha, err = _turno_pedido(query, headers)
    if err:
        return err
    resumen = armar_resumen(user_id, fecha)
    envio = utils._get_by_id("POS_SHIFT_SUMMARY", _id_resumen(user_id, fecha)) or {}
    if envio.get("notifiedAt"):
        resumen["notifiedTo"] = envio.get("notifiedTo")
        resumen["notifiedAt"] = envio.get("notifiedAt")
    resumen["notifyEmailConfigured"] = bool(_correo_resumen_configurado())
    # La gerente elige de quién es el turno: solo quien puede ver el de otros recibe la lista.
    if utils._require_admin(headers, "access_screen_stats") is None:
        resumen["team"] = sorted(
            ({"id": str(e.get("employeeId")), "name": e.get("name") or str(e.get("employeeId"))}
             for e in utils._query_bucket("EMPLOYEE") if e.get("active", True)),
            key=lambda e: e["name"].lower())
    return utils._json_response(200, resumen)


def _desde_fecha(fecha: str, dias: int) -> str:
    return (datetime.strptime(fecha, "%Y-%m-%d") - timedelta(days=dias)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Ruteo de la extensión
# ─────────────────────────────────────────────────────────────────────────────

def atender(peticion: HttpRequest) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = peticion.segments[1:] if peticion.segments[:1] == ["inventory"] else list(peticion.segments)
    if not seg or seg[0] not in ("despacho", "envios", "turno"):
        return None
    metodo, cuerpo, query, headers = peticion.method, peticion.body, peticion.query, peticion.headers

    if seg == ["despacho", "pendientes"] and metodo == "GET":
        err = utils._require_admin(headers, "order_mark_shipped")
        return err or handle_despacho_pendientes(query)
    if seg == ["despacho", "surtido"] and metodo == "POST":
        err = utils._require_admin(headers, "order_mark_shipped")
        return err or handle_despacho_surtido(cuerpo)
    if seg == ["despacho", "enviar"] and metodo == "POST":
        err = utils._require_admin(headers, "order_mark_shipped")
        return err or handle_despacho_enviar(cuerpo, headers)
    if seg == ["despacho", "preferencias"] and metodo in ("GET", "PUT"):
        return handle_preferencias(metodo, cuerpo, headers)
    if seg == ["envios", "rastrear"] and metodo == "POST":
        err = utils._require_admin(headers, "order_mark_delivered")
        return err or handle_envios_rastrear(cuerpo, headers)
    if seg == ["envios", "cerrar"] and metodo == "POST":
        err = utils._require_admin(headers, "order_mark_delivered")
        return err or handle_envios_cerrar(cuerpo, headers)
    if len(seg) == 3 and seg[0] == "envios" and seg[2] == "confirmar-entrega" and metodo in ("GET", "POST"):
        return handle_confirmar_entrega(seg[1], metodo, query, headers)
    if seg == ["turno", "resumen"] and metodo == "GET":
        return handle_turno_resumen(query, headers)
    if seg == ["turno", "resumen", "enviar"] and metodo == "POST":
        return handle_enviar_resumen(cuerpo, headers)
    return None
