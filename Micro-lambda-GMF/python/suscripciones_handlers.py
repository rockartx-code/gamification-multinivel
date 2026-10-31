"""Suscripción mensual: "recibe esto cada mes" (paquete H, propuesta 14).

Bety, Rosa y Patricia recompran lo mismo cada mes y su activación dependía de
acordarse del día 20 (docs/qa/22 §6 tarea 8). La socia elige productos, día
del mes (1–28) y dirección; el día indicado el sistema crea el pedido con el
descuento del tramo real de ese día, genera el enlace de pago y lo manda por
correo. No hay cobro automático: no se guardan tarjetas (docs/arquitectura/23 §13).

Rutas (extensión de `order_lambda`, §0.2):
  GET    /orders/suscripciones             sesión propia (admin: ?customerId=)
  POST   /orders/suscripciones             sesión propia
  PATCH  /orders/suscripciones/{id}        dueño o admin
  DELETE /orders/suscripciones/{id}        dueño o admin
  POST   /orders/suscripciones/generar     order_create o superadmin (programable)
"""
import calendar
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import core_utils as utils
from core import email as _correo

TAREAS_PROGRAMADAS = [("POST", "/orders/suscripciones/generar")]

ENTIDAD = "SUBSCRIPTION"
ESTADOS = ("active", "paused", "cancelled")
TIPOS_ENTREGA = ("delivery", "shipping", "pickup")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------------------
# Ruteo
# ---------------------------------------------------------------------------

def _segmentos(request) -> list:
    seg = list(request.segments or [])
    return seg[1:] if seg[:1] == ["orders"] else seg


def atender(request) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = _segmentos(request)
    if not seg or seg[0] != "suscripciones":
        return None
    metodo, headers, body = request.method, request.headers, request.body or {}

    if len(seg) == 1:
        if metodo == "GET":
            return handle_listar(request.query or {}, headers)
        if metodo == "POST":
            return handle_crear(body, headers)
        return utils._json_response(405, {"message": f"Método {metodo} no permitido en suscripciones"})

    if len(seg) == 2 and seg[1] == "generar":
        if metodo != "POST":
            return utils._json_response(405, {"message": f"Método {metodo} no permitido en suscripciones/generar"})
        err = utils._require_admin(headers, "order_create")
        if err:
            return err
        return handle_generar(body, headers)

    if len(seg) == 2:
        if metodo == "PATCH":
            return handle_editar(seg[1], body, headers)
        if metodo == "DELETE":
            return handle_cancelar(seg[1], body, headers)
        if metodo == "GET":
            return handle_una(seg[1], headers)
        return utils._json_response(405, {"message": f"Método {metodo} no permitido en la suscripción"})
    return None


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

def _hoy() -> date:
    return datetime.now(timezone.utc).date()


def _fecha_iso(d: date) -> str:
    return d.isoformat()


def _parse_fecha(texto) -> Optional[date]:
    try:
        return date.fromisoformat(str(texto)[:10])
    except Exception:
        return None


def _proxima_fecha(dia: int, desde: date, incluir_hoy: bool = False) -> date:
    """Próxima fecha con ese día del mes, estrictamente posterior a `desde`
    (o `desde` misma si `incluir_hoy`)."""
    anio, mes = desde.year, desde.month
    candidata = date(anio, mes, min(dia, calendar.monthrange(anio, mes)[1]))
    if candidata > desde or (incluir_hoy and candidata == desde):
        return candidata
    mes += 1
    if mes > 12:
        mes, anio = 1, anio + 1
    return date(anio, mes, min(dia, calendar.monthrange(anio, mes)[1]))


def _fecha_larga(d: Optional[date]) -> str:
    if not d:
        return ""
    return f"{d.day} de {MESES[d.month - 1]}"


# ---------------------------------------------------------------------------
# Config y validación
# ---------------------------------------------------------------------------

def _cfg() -> dict:
    return utils._load_app_config().get("subscriptions") or {}


def _dia_valido(valor) -> Optional[int]:
    cfg = _cfg()
    try:
        dia = int(utils._to_decimal(valor))
    except Exception:
        return None
    minimo, maximo = int(utils._to_decimal(cfg.get("minDay"))), int(utils._to_decimal(cfg.get("maxDay")))
    return dia if minimo <= dia <= maximo else None


def _validar_items(raw_items) -> tuple:
    """Devuelve (items normalizados, mensaje de error)."""
    if not isinstance(raw_items, list) or not raw_items:
        return [], "Elige al menos un producto para tu suscripción"
    items = []
    for entrada in raw_items:
        if not isinstance(entrada, dict):
            continue
        pid = entrada.get("productId")
        cantidad = entrada.get("quantity") if entrada.get("quantity") is not None else entrada.get("qty")
        try:
            qty = int(utils._to_decimal(1 if cantidad is None else cantidad))
        except Exception:
            qty = 0
        if pid in (None, "") or qty <= 0:
            return [], "Cada producto necesita una cantidad mayor a cero"
        producto = utils._get_by_id("PRODUCT", pid) or utils._get_by_id("PRODUCT", str(pid))
        if not producto or producto.get("active") is False:
            return [], f"El producto {entrada.get('name') or pid} ya no está disponible"
        items.append({
            "productId": producto.get("productId", pid), "name": producto.get("name") or str(pid),
            "quantity": qty, "price": utils._to_decimal(producto.get("price") or 0),
            "vpPoints": utils._to_decimal(producto.get("vpPoints") or 0),
        })
    if not items:
        return [], "Elige al menos un producto para tu suscripción"
    return items, ""


def _direccion_del_cliente(customer: dict, address_id: str) -> Optional[dict]:
    for entrada in (customer.get("addresses") or customer.get("shippingAddresses") or []):
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("addressId") or entrada.get("id") or "") == str(address_id):
            return dict(entrada)
    return None


def _resolver_entrega(body: dict, customer: dict, actual: Optional[dict] = None) -> tuple:
    """Devuelve ({deliveryType, shippingAddress, shippingAddressId, pickupStockId}, error)."""
    actual = actual or {}
    tipo = str(body.get("deliveryType") or actual.get("deliveryType") or "delivery").lower()
    if tipo not in TIPOS_ENTREGA:
        return {}, "El tipo de entrega debe ser envío a domicilio o recoger en sucursal"
    salida = {"deliveryType": tipo, "shippingAddress": actual.get("shippingAddress") or {},
              "shippingAddressId": actual.get("shippingAddressId"), "pickupStockId": actual.get("pickupStockId")}
    if tipo == "pickup":
        stock_id = str(body.get("pickupStockId") or actual.get("pickupStockId") or "").strip()
        stock = utils._get_by_id("STOCK", stock_id) if stock_id else None
        if not stock or not stock.get("allowPickup"):
            return {}, "Elige una sucursal donde se pueda recoger el pedido"
        salida["pickupStockId"] = stock_id
        salida["pickupStockName"] = stock.get("name") or stock_id
        return salida, ""
    if body.get("shippingAddressId"):
        direccion = _direccion_del_cliente(customer, str(body["shippingAddressId"]))
        if not direccion:
            return {}, "La dirección elegida no está entre tus direcciones guardadas"
        salida["shippingAddress"] = direccion
        salida["shippingAddressId"] = str(body["shippingAddressId"])
    elif isinstance(body.get("shippingAddress"), dict) and body.get("shippingAddress"):
        salida["shippingAddress"] = dict(body["shippingAddress"])
        salida["shippingAddressId"] = body["shippingAddress"].get("addressId") or body["shippingAddress"].get("id")
    if not salida["shippingAddress"]:
        return {}, "Indica a qué dirección enviamos tu pedido mensual"
    salida["pickupStockId"] = None
    return salida, ""


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def _publica(sub: dict) -> dict:
    return {k: v for k, v in sub.items() if k not in ("PK", "SK")}


def _resumen_items(sub: dict) -> str:
    return ", ".join(f"{int(i.get('quantity') or 1)} × {i.get('name')}" for i in sub.get("items") or [])


def _total_lista(sub: dict) -> Decimal:
    total = utils.D_ZERO
    for i in sub.get("items") or []:
        total += utils._to_decimal(i.get("price") or 0) * int(i.get("quantity") or 1)
    return total.quantize(utils.D_CENT)


# ---------------------------------------------------------------------------
# Correos
# ---------------------------------------------------------------------------

def _mxn(valor) -> str:
    return f"${utils._to_decimal(valor or 0):,.2f}"


def _frontend() -> str:
    return utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx").rstrip("/")


def _correo_suscripcion(customer: dict, sub: dict, evento: str, datos: Optional[dict] = None) -> bool:
    """Un correo por evento: creada, pausada, reanudada, cancelada, pedido generado."""
    datos = datos or {}
    para = str(customer.get("email") or "").strip()
    if not para:
        return False
    nombre = customer.get("name") or "Hola"
    productos = _resumen_items(sub)
    proximo = _fecha_larga(_parse_fecha(sub.get("nextRunDate")))
    panel = f"{_frontend()}/#/dashboard"
    dia = int(sub.get("dayOfMonth") or 0)
    nota_descuento = "El descuento de tu tramo se aplica al generar cada pedido, así que el total puede ser menor al precio de lista."

    if evento == "created":
        asunto = "Tu suscripción mensual quedó guardada"
        titulo, icono = "Recibirás esto cada mes", "🔁"
        lead = (f"Guardamos tu suscripción <strong>{sub.get('subscriptionId')}</strong>: {productos}. "
                f"Cada día <strong>{dia}</strong> crearemos tu pedido y te mandaremos el enlace para pagarlo; "
                f"el primero será el <strong>{proximo}</strong>. {nota_descuento} "
                "Puedes pausarla o cancelarla cuando quieras desde tu panel, sin llamar a nadie.")
        boton = "Ver mi suscripción"
        url = panel
    elif evento == "paused":
        hasta = _fecha_larga(_parse_fecha(sub.get("pausedUntil")))
        asunto = "Pausamos tu suscripción mensual"
        titulo, icono = "Suscripción en pausa", "⏸️"
        lead = (f"Tu suscripción <strong>{sub.get('subscriptionId')}</strong> queda en pausa"
                f"{(' hasta el <strong>' + hasta + '</strong>') if hasta else ''}: no crearemos pedidos mientras dure. "
                f"Se reanuda sola al terminar la pausa; también puedes reanudarla antes desde tu panel.")
        boton, url = "Ver mi suscripción", panel
    elif evento == "resumed":
        asunto = "Tu suscripción mensual vuelve a estar activa"
        titulo, icono = "Suscripción reanudada", "▶️"
        lead = (f"Reanudamos tu suscripción <strong>{sub.get('subscriptionId')}</strong>: {productos}. "
                f"El próximo pedido se creará el <strong>{proximo}</strong>.")
        boton, url = "Ver mi suscripción", panel
    elif evento == "cancelled":
        asunto = "Cancelamos tu suscripción mensual"
        titulo, icono = "Suscripción cancelada", "🚫"
        lead = (f"Tu suscripción <strong>{sub.get('subscriptionId')}</strong> quedó cancelada: ya no crearemos pedidos ni te cobraremos nada. "
                "Si cambias de opinión, puedes crear una nueva desde tu panel en cualquier momento.")
        boton, url = "Ir a mi panel", panel
    elif evento == "updated":
        asunto = "Actualizamos tu suscripción mensual"
        titulo, icono = "Suscripción actualizada", "✏️"
        lead = (f"Tu suscripción <strong>{sub.get('subscriptionId')}</strong> ahora es: {productos}, cada día <strong>{dia}</strong>. "
                f"El próximo pedido se creará el <strong>{proximo}</strong>. {nota_descuento}")
        boton, url = "Ver mi suscripción", panel
    elif evento == "order_generated":
        oid = datos.get("orderId")
        total = datos.get("total")
        asunto = f"Tu pedido mensual está listo: paga aquí · {oid}"
        titulo, icono = "Tu pedido mensual ya está creado", "🛍️"
        pago = datos.get("initPoint") or f"{_frontend()}/#/orden/{oid}"
        detalle_descuento = ""
        if datos.get("discountRate"):
            detalle_descuento = f" Ya incluye tu descuento del {int(round(float(datos['discountRate']) * 100))} %."
        lead = (f"Creamos el pedido <strong>{oid}</strong> de tu suscripción: {productos}. "
                f"Total a pagar: <strong>{_mxn(total)}</strong>.{detalle_descuento} "
                "Solo falta que lo pagues; hasta entonces no se prepara ni se envía. "
                "Si este mes no lo quieres, puedes cancelar el pedido desde su seguimiento sin ningún cargo.")
        boton, url = "Pagar mi pedido", pago
    else:
        return False

    cuerpo = f"""
    <div class="icon">{icono}</div>
    <h1 class="title">{titulo}</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. {lead}</p>
    <div class="info-box">
      <p><strong>Suscripción {sub.get('subscriptionId')}</strong></p>
      <p>{productos}</p>
      <p>Precio de lista: {_mxn(_total_lista(sub))} · Día {dia} de cada mes</p>
    </div>
    <a class="btn" href="{url}">{boton}</a>
    """
    texto = (f"{titulo}\n\nHola {nombre}. " + lead.replace("<strong>", "").replace("</strong>", "")
             + f"\n\nSuscripción {sub.get('subscriptionId')}: {productos}. {boton}: {url}\n")
    try:
        _correo._send_ses_email(para, asunto, texto, _correo._email_shell(cuerpo))
        return True
    except Exception as e:  # pragma: no cover - el correo nunca rompe la suscripción
        print(f"[SUBSCRIPTION_EMAIL_ERROR] {sub.get('subscriptionId')}: {e}")
        return False


# ---------------------------------------------------------------------------
# Handlers CRUD
# ---------------------------------------------------------------------------

def _cliente(customer_id) -> Optional[dict]:
    if customer_id in (None, ""):
        return None
    return utils._get_by_id("CUSTOMER", customer_id) or utils._get_by_id("CUSTOMER", str(customer_id))


def _cargar(sub_id: str) -> Optional[dict]:
    return utils._get_by_id(ENTIDAD, sub_id)


def _del_cliente(customer_id) -> list:
    """Las suscripciones de un cliente (volumen pequeño: se filtra en memoria)."""
    objetivo = str(customer_id)
    return [_publica(s) for s in utils._query_bucket(ENTIDAD) if str(s.get("customerId")) == objetivo]


def _autorizar(headers: dict, customer_id, privilegio: str):
    """Dueño o admin; un empleado solo con el privilegio (como el resto de rutas nuevas)."""
    if utils._extract_actor(headers).get("role") == "employee":
        return utils._require_admin(headers, privilegio)
    return utils._require_self_or_admin(headers, customer_id)


def handle_listar(query: dict, headers: dict) -> dict:
    actor = utils._extract_actor(headers)
    customer_id = actor.get("user_id")
    if actor.get("role") in ("admin", "employee") and query.get("customerId"):
        err = _autorizar(headers, query.get("customerId"), "access_screen_orders")
        if err:
            return err
        customer_id = query.get("customerId")
    if not customer_id:
        return utils._json_response(401, {"message": "No autenticado"})
    subs = sorted(_del_cliente(customer_id), key=lambda s: str(s.get("createdAt") or ""), reverse=True)
    return utils._json_response(200, {"subscriptions": subs})


def handle_una(sub_id: str, headers: dict) -> dict:
    sub = _cargar(sub_id)
    if not sub:
        return utils._json_response(404, {"message": "Suscripción no encontrada"})
    err = _autorizar(headers, sub.get("customerId"), "access_screen_orders")
    if err:
        return err
    return utils._json_response(200, {"subscription": _publica(sub)})


def handle_crear(body: dict, headers: dict) -> dict:
    actor = utils._extract_actor(headers)
    customer_id = body.get("customerId") or actor.get("user_id")
    if not customer_id:
        return utils._json_response(401, {"message": "No autenticado"})
    err = _autorizar(headers, customer_id, "order_create")
    if err:
        return err
    if not _cfg().get("enabled", True):
        return utils._json_response(409, {"message": "Las suscripciones no están habilitadas por ahora"})
    customer = _cliente(customer_id)
    if not customer:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    items, error = _validar_items(body.get("items"))
    if error:
        return utils._json_response(400, {"message": error})
    dia = _dia_valido(body.get("dayOfMonth"))
    if dia is None:
        cfg = _cfg()
        return utils._json_response(400, {"message": f"Elige un día del mes entre {int(utils._to_decimal(cfg.get('minDay')))} y {int(utils._to_decimal(cfg.get('maxDay')))}"})
    entrega, error = _resolver_entrega(body, customer)
    if error:
        return utils._json_response(400, {"message": error})

    hoy = _hoy()
    now = utils._now_iso()
    sub_id = f"SUS-{utils.uuid.uuid4().hex[:8].upper()}"
    sub = {
        "entityType": "subscription", "subscriptionId": sub_id, "customerId": customer.get("customerId", customer_id),
        "customerName": customer.get("name"), "items": items, "dayOfMonth": dia,
        **entrega,
        "status": "active", "pausedUntil": None,
        "nextRunDate": _fecha_iso(_proxima_fecha(dia, hoy)), "lastRunDate": None, "lastOrderId": None,
        "createdAt": now, "updatedAt": now,
    }
    utils._put_entity(ENTIDAD, sub_id, sub)
    utils._audit_event("subscription.create", headers, body, {"subscriptionId": sub_id})
    _correo_suscripcion(customer, sub, "created")
    return utils._json_response(201, {"subscription": _publica(sub)})


def _guardar_cambios(sub: dict, cambios: dict) -> dict:
    """SET de los campos indicados sobre la suscripción."""
    cambios = {**cambios, "updatedAt": utils._now_iso()}
    expr = "SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(cambios)))
    nombres = {f"#f{i}": k for i, k in enumerate(cambios)}
    valores = {f":v{i}": v for i, v in enumerate(cambios.values())}
    return utils._update_by_id(ENTIDAD, sub["subscriptionId"], expr, valores, nombres)


def handle_editar(sub_id: str, body: dict, headers: dict) -> dict:
    sub = _cargar(sub_id)
    if not sub:
        return utils._json_response(404, {"message": "Suscripción no encontrada"})
    err = _autorizar(headers, sub.get("customerId"), "order_create")
    if err:
        return err
    if sub.get("status") == "cancelled":
        return utils._json_response(409, {"message": "Esta suscripción ya está cancelada; crea una nueva si quieres volver a recibir tus productos"})
    customer = _cliente(sub.get("customerId")) or {}

    cambios = {}
    evento = "updated"
    if "items" in body:
        items, error = _validar_items(body.get("items"))
        if error:
            return utils._json_response(400, {"message": error})
        cambios["items"] = items
    dia = int(sub.get("dayOfMonth") or 1)
    if "dayOfMonth" in body:
        dia_nuevo = _dia_valido(body.get("dayOfMonth"))
        if dia_nuevo is None:
            cfg = _cfg()
            return utils._json_response(400, {"message": f"Elige un día del mes entre {int(utils._to_decimal(cfg.get('minDay')))} y {int(utils._to_decimal(cfg.get('maxDay')))}"})
        dia = dia_nuevo
        cambios["dayOfMonth"] = dia
    if any(k in body for k in ("deliveryType", "shippingAddress", "shippingAddressId", "pickupStockId")):
        entrega, error = _resolver_entrega(body, customer, sub)
        if error:
            return utils._json_response(400, {"message": error})
        cambios.update(entrega)

    hoy = _hoy()
    nuevo_estado = str(body.get("status") or "").lower()
    if nuevo_estado:
        if nuevo_estado not in ("active", "paused"):
            return utils._json_response(400, {"message": "El estado solo puede ser activa o pausada; para cancelar usa el botón Cancelar"})
        if nuevo_estado == "paused" and sub.get("status") != "paused":
            hasta = _parse_fecha(body.get("pausedUntil"))
            if not hasta:
                # "Pausar un mes": se salta el próximo pedido y se reanuda antes del siguiente.
                proximo = _parse_fecha(sub.get("nextRunDate")) or _proxima_fecha(dia, hoy)
                hasta = _proxima_fecha(dia, proximo)
            cambios["status"] = "paused"
            cambios["pausedUntil"] = _fecha_iso(hasta)
            cambios["nextRunDate"] = _fecha_iso(_proxima_fecha(dia, hasta, incluir_hoy=True))
            evento = "paused"
        elif nuevo_estado == "active" and sub.get("status") != "active":
            cambios["status"] = "active"
            cambios["pausedUntil"] = None
            cambios["nextRunDate"] = _fecha_iso(_proxima_fecha(dia, hoy))
            evento = "resumed"
    if "dayOfMonth" in cambios and "nextRunDate" not in cambios and (cambios.get("status") or sub.get("status")) == "active":
        cambios["nextRunDate"] = _fecha_iso(_proxima_fecha(dia, hoy))

    if not cambios:
        return utils._json_response(400, {"message": "No hay nada que cambiar"})
    actualizada = _guardar_cambios(sub, cambios)
    utils._audit_event("subscription.update", headers, body, {"subscriptionId": sub_id, "cambios": sorted(cambios)})
    _correo_suscripcion(customer, actualizada, evento)
    return utils._json_response(200, {"subscription": _publica(actualizada)})


def handle_cancelar(sub_id: str, body: dict, headers: dict) -> dict:
    sub = _cargar(sub_id)
    if not sub:
        return utils._json_response(404, {"message": "Suscripción no encontrada"})
    err = _autorizar(headers, sub.get("customerId"), "order_create")
    if err:
        return err
    if sub.get("status") == "cancelled":
        return utils._json_response(200, {"subscription": _publica(sub), "alreadyCancelled": True})
    actualizada = _guardar_cambios(sub, {"status": "cancelled", "cancelledAt": utils._now_iso(),
                                         "cancelReason": str((body or {}).get("reason") or "").strip() or None,
                                         "nextRunDate": None})
    utils._audit_event("subscription.cancel", headers, body, {"subscriptionId": sub_id})
    _correo_suscripcion(_cliente(sub.get("customerId")) or {}, actualizada, "cancelled")
    return utils._json_response(200, {"subscription": _publica(actualizada)})


# ---------------------------------------------------------------------------
# Generación programada
# ---------------------------------------------------------------------------

def _cuerpo_del_pedido(sub: dict, customer: dict) -> dict:
    """Lo que mandaría el carrito de la socia: precios actuales del catálogo."""
    items = []
    for linea in sub.get("items") or []:
        producto = utils._get_by_id("PRODUCT", linea.get("productId")) or {}
        if producto.get("active") is False:
            raise ValueError(f"El producto {linea.get('name')} ya no está disponible")
        items.append({
            "productId": linea.get("productId"), "name": producto.get("name") or linea.get("name"),
            "price": utils._to_decimal(producto.get("price") if producto.get("price") is not None else linea.get("price") or 0),
            "quantity": int(linea.get("quantity") or 1),
        })
    direccion = dict(sub.get("shippingAddress") or {})
    cuerpo = {
        "customerId": sub.get("customerId"), "customerName": customer.get("name") or sub.get("customerName"),
        "email": customer.get("email"), "phone": direccion.get("phone") or customer.get("phone"),
        "recipientName": direccion.get("recipientName") or customer.get("name"),
        "items": items, "deliveryType": sub.get("deliveryType") or "delivery",
        "shippingAddress": direccion, "shippingAddressId": sub.get("shippingAddressId"),
        "shippingAddressLabel": direccion.get("label"),
    }
    if cuerpo["deliveryType"] == "pickup":
        cuerpo["pickupStockId"] = sub.get("pickupStockId")
        cuerpo["pickupPaymentMethod"] = "online"
    else:
        # Sin cotización en línea: tarifa base de envío (la fija C en shipping.baseRateMxn)
        # y paquetería "por confirmar"; el almacén la define al despachar.
        shipping_cfg = utils._load_app_config().get("shipping") or {}
        cuerpo["shippingCost"] = utils._to_decimal(shipping_cfg.get("baseRateMxn") or 0)
        cuerpo["shippingCarrier"] = "por confirmar"
    return cuerpo


def _generar_una(sub: dict, fecha: date, dry_run: bool) -> tuple:
    """Devuelve (generado, omitido) para una suscripción."""
    import order_lambda  # anfitrión; import tardío para evitar el ciclo de importación

    sid = sub.get("subscriptionId")
    estado = sub.get("status")
    if estado == "cancelled":
        return None, {"subscriptionId": sid, "reason": "cancelled"}
    if estado == "paused":
        hasta = _parse_fecha(sub.get("pausedUntil"))
        if not hasta or hasta > fecha:
            return None, {"subscriptionId": sid, "reason": "paused"}
        # La pausa venció: vuelve a activa y sigue la evaluación normal.
        if not dry_run:
            sub = _guardar_cambios(sub, {"status": "active", "pausedUntil": None})
    # Idempotente por día: se comprueba ANTES de la fecha, porque tras generar
    # el nextRunDate ya apunta al mes siguiente y parecería "aún no toca".
    if str(sub.get("lastRunDate") or "") == _fecha_iso(fecha):
        return None, {"subscriptionId": sid, "reason": "already_generated_today", "orderId": sub.get("lastOrderId")}
    proximo = _parse_fecha(sub.get("nextRunDate"))
    if not proximo or proximo > fecha:
        return None, {"subscriptionId": sid, "reason": "not_due", "nextRunDate": sub.get("nextRunDate")}
    customer = _cliente(sub.get("customerId"))
    if not customer:
        return None, {"subscriptionId": sid, "reason": "customer_not_found"}
    try:
        cuerpo = _cuerpo_del_pedido(sub, customer)
    except ValueError as e:
        return None, {"subscriptionId": sid, "reason": "product_inactive", "detail": str(e)}
    if dry_run:
        return {"subscriptionId": sid, "orderId": None, "dryRun": True, "customerId": sub.get("customerId")}, None

    respuesta = order_lambda.handle_create_order(cuerpo, {})
    if respuesta.get("statusCode") not in (200, 201):
        detalle = json.loads(respuesta.get("body") or "{}").get("message") or "No se pudo crear el pedido"
        return None, {"subscriptionId": sid, "reason": "order_error", "detail": detalle}
    pedido = json.loads(respuesta["body"]).get("order") or {}
    oid = pedido.get("orderId")
    utils._update_by_id("ORDER", oid, "SET subscriptionId = :s", {":s": sid})

    init_point = None
    try:
        checkout = order_lambda.handle_mercadopago_checkout(oid, {})
        if checkout.get("statusCode") == 200:
            init_point = (json.loads(checkout["body"]).get("checkout") or {}).get("initPoint")
    except Exception as e:  # noqa: BLE001 - sin enlace, el correo lleva el pedido
        utils._log_error("subscription_checkout_failed", e, subscriptionId=sid, orderId=oid)

    dia = int(sub.get("dayOfMonth") or 1)
    actualizada = _guardar_cambios(sub, {
        "lastRunDate": _fecha_iso(fecha), "lastOrderId": oid,
        "nextRunDate": _fecha_iso(_proxima_fecha(dia, fecha)),
    })
    _correo_suscripcion(customer, actualizada, "order_generated", {
        "orderId": oid, "initPoint": init_point,
        "total": pedido.get("total") if pedido.get("total") is not None else pedido.get("netTotal"),
        "discountRate": pedido.get("discountRate"),
    })
    return {"subscriptionId": sid, "orderId": oid, "initPoint": init_point,
            "total": pedido.get("total"), "customerId": sub.get("customerId")}, None


def handle_generar(body: dict, headers: dict) -> dict:
    """POST /orders/suscripciones/generar — {date?, dryRun?}. Idempotente por día."""
    fecha = _parse_fecha(body.get("date")) if body.get("date") else _hoy()
    if not fecha:
        return utils._json_response(400, {"message": "La fecha debe tener el formato AAAA-MM-DD"})
    dry_run = bool(body.get("dryRun"))
    if not _cfg().get("enabled", True):
        return utils._json_response(200, {"date": _fecha_iso(fecha), "generated": [], "skipped": [], "disabled": True})

    generados, omitidos = [], []
    for sub in utils._query_bucket(ENTIDAD):
        try:
            generado, omitido = _generar_una(sub, fecha, dry_run)
        except Exception as e:  # noqa: BLE001 - una suscripción rota no detiene a las demás
            utils._log_error("subscription_generate_failed", e, subscriptionId=sub.get("subscriptionId"))
            omitido = {"subscriptionId": sub.get("subscriptionId"), "reason": "error", "detail": str(e)}
            generado = None
        if generado:
            generados.append(generado)
        if omitido:
            omitidos.append(omitido)
    utils._audit_event("subscription.generate", headers, {"date": _fecha_iso(fecha), "dryRun": dry_run},
                       {"generated": len(generados), "skipped": len(omitidos)})
    return utils._json_response(200, {"date": _fecha_iso(fecha), "dryRun": dry_run,
                                      "generated": generados, "skipped": omitidos})
