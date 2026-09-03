"""Paquete C · checkout-y-sesion: extensión de `order_lambda`.

Rutas (relativas al prefijo /orders):

  GET  /checkout/envio-info?subtotal=      público   tarifa base, umbral de envío gratis y faltante
  POST /checkout/sugerencia-activacion     sesión    producto más barato que cierra los VP que faltan
  POST /checkout/sucursales-recoger        público   sucursales con existencia en la ciudad/estado
  POST /{id}/factura                       dueño, invitado por folio o admin
  POST /{id}/factura/emitida               order_mark_paid

Los diarios de la ronda (docs/qa/22 §5 y §6): cinco socias quedaron en 18-19 VP
con "20 PC" de catálogo y tuvieron que hacer un segundo pedido chico; "Envío
gratis" se volvía $129 al poner el CP; "Recoger en sucursal" aparecía desde
Mérida cuando la única sucursal está en CDMX; y la factura se prometió cuatro
veces recapturando los datos fiscales a mano.
"""
import math
import re
import unicodedata
from typing import Optional

import core_utils as utils
import order_lambda  # anfitrión; el import es circular a propósito y solo se usa dentro de funciones


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

#: RFC del SAT: 3 letras (moral) o 4 (física) + fecha AAMMDD + homoclave de 3.
RFC_SAT = re.compile(r"^([A-ZÑ&]{3}|[A-ZÑ&]{4})\d{6}[A-Z0-9]{3}$")

#: Estados de la República con el mismo código que usa el frontend
#: (`constants/states-mx.ts`). Se acepta el código o el nombre.
_ESTADOS_MX = {
    "AGU": "AGUASCALIENTES", "BCN": "BAJA CALIFORNIA", "BCS": "BAJA CALIFORNIA SUR",
    "CAM": "CAMPECHE", "CHP": "CHIAPAS", "CHH": "CHIHUAHUA", "CMX": "CIUDAD DE MEXICO",
    "COA": "COAHUILA", "COL": "COLIMA", "DUR": "DURANGO", "GUA": "GUANAJUATO",
    "GRO": "GUERRERO", "HID": "HIDALGO", "JAL": "JALISCO", "MIC": "MICHOACAN",
    "MOR": "MORELOS", "MEX": "MEXICO", "NAY": "NAYARIT", "NLE": "NUEVO LEON",
    "OAX": "OAXACA", "PUE": "PUEBLA", "QUE": "QUERETARO", "ROO": "QUINTANA ROO",
    "SLP": "SAN LUIS POTOSI", "SIN": "SINALOA", "SON": "SONORA", "TAB": "TABASCO",
    "TAM": "TAMAULIPAS", "TLA": "TLAXCALA", "VER": "VERACRUZ", "YUC": "YUCATAN",
    "ZAC": "ZACATECAS",
}
_ESTADO_POR_NOMBRE = {nombre: codigo for codigo, nombre in _ESTADOS_MX.items()}
_ESTADO_POR_NOMBRE.update({"CDMX": "CMX", "DF": "CMX", "DISTRITO FEDERAL": "CMX",
                           "ESTADO DE MEXICO": "MEX", "EDOMEX": "MEX"})


def _normalizar(texto) -> str:
    """Mayúsculas, sin acentos ni espacios repetidos; '' si viene vacío."""
    limpio = unicodedata.normalize("NFKD", str(texto or ""))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return " ".join(limpio.upper().split())


def _codigo_estado(texto) -> str:
    """Código de estado ('CMX') a partir de un código o de un nombre; '' si no se reconoce."""
    n = _normalizar(texto)
    if not n:
        return ""
    if n in _ESTADOS_MX:
        return n
    return _ESTADO_POR_NOMBRE.get(n, "")


def _cfg(seccion: str) -> dict:
    return utils._load_app_config().get(seccion) or {}


def _segmentos(request) -> list:
    """Segmentos sin el prefijo del lambda (order_lambda no usa strip_prefix)."""
    seg = list(request.segments or [])
    return seg[1:] if seg[:1] == ["orders"] else seg


# ---------------------------------------------------------------------------
# Envío visible
# ---------------------------------------------------------------------------

def base_envio_gratis(totals: dict):
    """Importe sobre el que se mide la regla de envío gratis (config `shipping.freeShippingBasis`)."""
    basis = str(_cfg("shipping").get("freeShippingBasis") or "gross").lower()
    clave = "grossSubtotal" if basis == "gross" else "netTotal"
    return utils._to_decimal(totals.get(clave) or 0)


def envio_gratis_aplica(totals: dict, envio_cobrado) -> bool:
    """Misma regla para el carrito y para `handle_create_order`."""
    minimo = utils._to_decimal(_cfg("shipping").get("freeShippingMin") or 0)
    if minimo <= 0 or utils._to_decimal(envio_cobrado) <= 0:
        return False
    return base_envio_gratis(totals) >= minimo


def configuracion_checkout() -> dict:
    """Lo que el carrito necesita saber antes de pintar la casilla de factura."""
    ck = _cfg("checkout")
    return {
        "invoiceEnabled": bool(ck.get("invoiceEnabled", True)),
        "regimenesFiscales": list(ck.get("regimenesFiscales") or []),
        "usosCfdi": list(ck.get("usosCfdi") or []),
    }


def info_envio(subtotal, neto=None) -> dict:
    ship = _cfg("shipping")
    minimo = utils._to_decimal(ship.get("freeShippingMin") or 0)
    basis = str(ship.get("freeShippingBasis") or "gross").lower()
    bruto = utils._to_decimal(subtotal)
    base = bruto if basis == "gross" or neto is None else utils._to_decimal(neto)
    gratis = bool(minimo > 0 and base >= minimo)
    faltante = (minimo - base) if (minimo > 0 and not gratis) else utils.D_ZERO
    return {
        "baseRateMxn": utils._to_decimal(ship.get("baseRateMxn") or 0),
        "freeShippingMin": minimo,
        "basis": basis,
        "missingForFree": max(utils.D_ZERO, faltante).quantize(utils.D_CENT),
        "freeNow": gratis,
        "checkout": configuracion_checkout(),
    }


# ---------------------------------------------------------------------------
# Completa tu activación
# ---------------------------------------------------------------------------

def sugerir_producto_activacion(products, gap_vp, rate_fn, factor_cupon=1.0) -> Optional[dict]:
    """Producto más barato que cierra `gap_vp` VP netos (fórmula compartida con el paquete A, §1.5).

    Para cada producto con puntos: `tasa = rate_fn(precio)` (descuento que
    tendría la compra con ese producto agregado), `vpNeto = PC × (1 − tasa) ×
    factor_cupon`, `unidades = ceil(faltan / vpNeto)`, `costo = precio ×
    unidades × (1 − tasa)`. Gana el menor costo; a igual costo, menos unidades.
    Función pura: no toca la base.
    """
    gap = float(gap_vp or 0)
    if gap <= 0:
        return None
    mejor = None
    for p in products or []:
        if not isinstance(p, dict) or not bool(p.get("active", True)):
            continue
        pc = float(utils._to_decimal(p.get("vpPoints") or 0))
        precio = float(utils._to_decimal(p.get("price") or 0))
        if pc <= 0 or precio <= 0:
            continue
        tasa = float(utils._to_decimal(rate_fn(precio)))
        vp_neto = pc * (1.0 - tasa) * float(factor_cupon or 1.0)
        if vp_neto <= 0:
            continue
        unidades = int(math.ceil(round(gap / vp_neto, 6)))
        costo = round(precio * unidades * (1.0 - tasa), 2)
        candidato = {
            "productId": p.get("productId") if p.get("productId") is not None else p.get("id"),
            "name": p.get("name"),
            "price": precio,
            "units": unidades,
            "netVpPerUnit": round(vp_neto, 2),
            "cost": costo,
            "discountRate": tasa,
        }
        if mejor is None or (costo, unidades, precio) < (mejor["cost"], mejor["units"], mejor["price"]):
            mejor = candidato
    return mejor


def _estado_mes(customer_id) -> dict:
    return utils._get_by_id(
        "ASSOCIATE_MONTH", utils._associate_month_entity_id(customer_id, utils._month_key())
    ) or {}


def _vp_del_mes(estado: dict, mxn_per_vp: float) -> float:
    if "netVP" in estado:
        return float(utils._to_decimal(estado.get("netVP") or 0))
    volumen = float(utils._to_decimal(estado.get("netVolume") or 0))
    return volumen / mxn_per_vp if mxn_per_vp > 0 else 0.0


def sugerencia_activacion(body: dict, headers: dict) -> dict:
    customer_id = body.get("customerId")
    if customer_id in (None, ""):
        return utils._json_response(401, {"message": "Inicia sesión para ver qué te falta para activarte."})
    err = utils._require_self_or_admin(headers, customer_id)
    if err:
        return err
    customer = utils._get_by_id("CUSTOMER", customer_id)
    if not customer:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    cfg = utils._load_app_config()
    activacion = utils._activation_vp(cfg)
    mxn_per_vp = utils._mxn_per_vp(cfg)
    tiers = (cfg.get("rewards") or {}).get("discountTiers") or []
    estado = _estado_mes(customer_id)
    vp_now = _vp_del_mes(estado, mxn_per_vp)
    volumen_mes = utils._to_decimal(estado.get("netVolume") or 0)

    # En modo cliente (paquete B) no hay meta de activación.
    if str(customer.get("mode") or "socio").lower() == "cliente":
        return utils._json_response(200, {"applies": False, "reason": "modo_cliente", "vpNow": round(vp_now, 2),
                                          "vpAfterCart": round(vp_now, 2), "gap": 0, "suggestion": None})

    bruto = utils.D_ZERO
    pc_bruto = 0.0
    for it in body.get("items") or []:
        if not isinstance(it, dict):
            continue
        qty = int(utils._to_decimal(it.get("quantity") or 1))
        precio = utils._to_decimal(it.get("price") or 0)
        pid = it.get("productId")
        producto = utils._get_by_id("PRODUCT", pid) if pid not in (None, "") else None
        if producto and producto.get("commissionable") is False:
            continue
        if precio <= 0 and producto:
            precio = utils._to_decimal(producto.get("price") or 0)
        bruto += precio * qty
        pc = it.get("vpPoints")
        if pc is None and producto:
            pc = producto.get("vpPoints")
        pc_bruto += float(utils._to_decimal(pc or 0)) * qty

    tasa_carrito = float(order_lambda._resolve_discount_rate(tiers, volumen_mes + bruto))
    neto_carrito = float(bruto) * (1.0 - tasa_carrito)
    factor_cupon = 1.0
    codigo = order_lambda._coupon_code(body.get("couponCode"))
    if codigo and neto_carrito > 0:
        cupon = utils._get_by_id("COUPON", codigo)
        resultado = order_lambda._evaluate_coupon(cupon, utils._to_decimal(neto_carrito), customer_id)
        if resultado.get("valid"):
            descuento = float(utils._to_decimal(resultado.get("discount") or 0))
            factor_cupon = max(0.0, (neto_carrito - descuento) / neto_carrito)

    vp_carrito = pc_bruto * (1.0 - tasa_carrito) * factor_cupon
    vp_after = vp_now + vp_carrito
    gap = round(activacion - vp_after, 2)
    aplica = 0 < gap <= activacion

    sugerencia = None
    if aplica:
        productos = [p for p in utils._query_bucket("PRODUCT") if bool(p.get("active", True))]
        rate_fn = lambda precio: order_lambda._resolve_discount_rate(tiers, volumen_mes + bruto + utils._to_decimal(precio))
        sugerencia = sugerir_producto_activacion(productos, gap, rate_fn, factor_cupon)
        if sugerencia:
            sugerencia["vpAfter"] = round(vp_after + sugerencia["units"] * sugerencia["netVpPerUnit"], 2)

    return utils._json_response(200, {
        "applies": bool(aplica and sugerencia),
        "activationVp": activacion,
        "vpNow": round(vp_now, 2),
        "vpCart": round(vp_carrito, 2),
        "vpAfterCart": round(vp_after, 2),
        "gap": max(0.0, gap),
        "suggestion": sugerencia,
    })


# ---------------------------------------------------------------------------
# Recoger en sucursal
# ---------------------------------------------------------------------------

def sucursales_recoger(body: dict) -> dict:
    ciudad = _normalizar(body.get("city"))
    estado = _codigo_estado(body.get("state")) or _normalizar(body.get("state"))
    items = [it for it in (body.get("items") or []) if isinstance(it, dict)]
    con_ubicacion = bool(ciudad or estado)

    sucursales = [s for s in utils._query_bucket("STOCK") if s.get("allowPickup")]
    ciudades = sorted({str(s.get("city") or s.get("location") or "").strip()
                       for s in sucursales if str(s.get("city") or s.get("location") or "").strip()})
    salida = []
    for s in sucursales:
        s_ciudad = _normalizar(s.get("city"))
        s_estado = _codigo_estado(s.get("state")) or _normalizar(s.get("state"))
        s_lugar = _normalizar(s.get("location"))
        if con_ubicacion:
            en_zona = bool(
                (estado and s_estado and s_estado == estado)
                or (ciudad and s_ciudad and s_ciudad == ciudad)
                # Sucursales dadas de alta antes de esta ronda solo tienen "Ubicación".
                or (ciudad and s_lugar and ciudad in s_lugar)
            )
        else:
            en_zona = True
        faltantes = order_lambda._faltantes_en_sucursal(s.get("stockId"), items) if items else []
        salida.append({
            "id": s.get("stockId"),
            "name": s.get("name"),
            "location": s.get("location"),
            "city": s.get("city"),
            "state": s.get("state"),
            "inArea": en_zona,
            "canPickup": bool(en_zona and not faltantes),
            "missing": faltantes,
        })
    return utils._json_response(200, {
        "available": any(x["canPickup"] for x in salida),
        "locationGiven": con_ubicacion,
        "cities": ciudades,
        "stocks": salida,
    })


# ---------------------------------------------------------------------------
# Quiero factura
# ---------------------------------------------------------------------------

_CAMPOS_FISCALES = ("rfc", "razonSocial", "regimenFiscal", "cpFiscal", "usoCfdi", "email")


def validar_datos_fiscales(data) -> tuple:
    """(datos_limpios, mensaje_de_error). RFC con la expresión del SAT."""
    data = data if isinstance(data, dict) else {}
    limpio = {
        "rfc": _normalizar(data.get("rfc")).replace(" ", ""),
        "razonSocial": " ".join(str(data.get("razonSocial") or "").split()),
        "regimenFiscal": str(data.get("regimenFiscal") or "").strip(),
        "cpFiscal": str(data.get("cpFiscal") or "").strip(),
        "usoCfdi": str(data.get("usoCfdi") or "").strip().upper(),
        "email": utils._normalize_email(data.get("email")),
    }
    if not RFC_SAT.match(limpio["rfc"]):
        return limpio, "El RFC no tiene el formato del SAT (12 letras y números para empresa, 13 para persona)."
    if not limpio["razonSocial"]:
        return limpio, "Escribe el nombre o razón social tal como aparece en tu constancia fiscal."
    if not limpio["regimenFiscal"]:
        return limpio, "Elige tu régimen fiscal."
    if not re.fullmatch(r"\d{5}", limpio["cpFiscal"]):
        return limpio, "El código postal fiscal debe tener 5 dígitos."
    if not limpio["usoCfdi"]:
        return limpio, "Elige el uso del CFDI."
    if "@" not in limpio["email"]:
        return limpio, "Escribe el correo al que enviaremos la factura."
    return limpio, ""


def estado_factura(order: dict) -> str:
    """Estado efectivo: un pedido cancelado o reembolsado con factura pedida queda en `no_aplica`."""
    if not order:
        return "no_aplica"
    if str(order.get("status") or "").lower() in ("cancelled", "canceled", "refunded"):
        return "no_aplica"
    if order.get("invoiceStatus"):
        return str(order.get("invoiceStatus"))
    return "solicitada" if order.get("invoiceRequested") else "no_aplica"


def campos_factura(order: dict) -> dict:
    """Campos de factura que salen en los listados del back office."""
    return {
        "invoiceRequested": bool(order.get("invoiceRequested")),
        "invoiceStatus": estado_factura(order),
        "invoiceData": order.get("invoiceData"),
        "invoiceRequestedAt": order.get("invoiceRequestedAt"),
        "invoiceIssuedAt": order.get("invoiceIssuedAt"),
        "invoiceFolio": order.get("invoiceFolio"),
        "invoiceFileUrl": order.get("invoiceFileUrl"),
    }


def campos_factura_al_crear(body: dict) -> tuple:
    """Lo que `handle_create_order` guarda cuando el carrito trae `invoiceRequested`."""
    if not body.get("invoiceRequested"):
        return {"invoiceRequested": False, "invoiceStatus": "no_aplica"}, ""
    if not configuracion_checkout()["invoiceEnabled"]:
        return {}, "La solicitud de factura no está disponible por ahora."
    datos, error = validar_datos_fiscales(body.get("invoiceData"))
    if error:
        return {}, error
    return {
        "invoiceRequested": True,
        "invoiceStatus": "solicitada",
        "invoiceData": datos,
        "invoiceRequestedAt": utils._now_iso(),
    }, ""


def solicitar_factura(order_id: str, body: dict, headers: dict) -> dict:
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})
    if not order_lambda._is_guest_order(order):
        err = utils._require_self_or_admin(headers, order.get("customerId"))
        if err:
            return err
    if estado_factura(order) == "no_aplica" and str(order.get("status") or "").lower() in ("cancelled", "canceled", "refunded"):
        return utils._json_response(409, {"message": "Este pedido está cancelado o reembolsado: ya no se puede facturar.",
                                          "code": "INVOICE_NOT_APPLICABLE"})
    if estado_factura(order) == "emitida":
        return utils._json_response(409, {"message": "La factura de este pedido ya fue emitida.", "code": "INVOICE_ALREADY_ISSUED"})
    datos, error = validar_datos_fiscales(body)
    if error:
        return utils._json_response(400, {"message": error, "code": "INVALID_INVOICE_DATA"})
    ahora = utils._now_iso()
    actualizado = utils._update_by_id(
        "ORDER", order_id,
        "SET invoiceRequested = :r, invoiceStatus = :s, invoiceData = :d, invoiceRequestedAt = :a, updatedAt = :u",
        {":r": True, ":s": "solicitada", ":d": datos, ":a": ahora, ":u": ahora},
    )
    utils._upsert_order_customer_history(actualizado)
    utils._audit_event("order.invoice_requested", headers, {"rfc": datos["rfc"]}, {"orderId": order_id})
    return utils._json_response(200, {
        "orderId": order_id, "invoiceStatus": "solicitada", "invoiceRequestedAt": ahora, "invoiceData": datos,
        "message": "Factura solicitada: la recibirás por correo en los próximos días hábiles.",
    })


def marcar_factura_emitida(order_id: str, body: dict, headers: dict) -> dict:
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})
    if estado_factura(order) != "solicitada":
        return utils._json_response(409, {
            "message": "Este pedido no tiene una solicitud de factura pendiente.",
            "code": "INVOICE_NOT_REQUESTED", "invoiceStatus": estado_factura(order),
        })
    ahora = utils._now_iso()
    folio = str(body.get("folioFiscal") or "").strip()
    expresion = "SET invoiceStatus = :s, invoiceIssuedAt = :a, updatedAt = :u"
    valores = {":s": "emitida", ":a": ahora, ":u": ahora}
    if folio:
        expresion += ", invoiceFolio = :f"
        valores[":f"] = folio
    url_archivo = None
    if body.get("contentBase64"):
        try:
            asset = order_lambda._upload_evidence_s3(
                str(body.get("name") or f"factura-{order_id}.pdf"), body.get("contentBase64"),
                str(body.get("contentType") or "application/pdf"), prefix=f"facturas/{order_id}",
            )
        except Exception as ex:  # base64 inválido o S3 caído
            return utils._json_response(400, {"message": "No se pudo guardar el archivo de la factura.", "detail": str(ex)})
        url_archivo = asset["url"]
        expresion += ", invoiceFileUrl = :url"
        valores[":url"] = url_archivo
    actualizado = utils._update_by_id("ORDER", order_id, expresion, valores)
    utils._upsert_order_customer_history(actualizado)
    utils._audit_event("order.invoice_issued", headers, {"folioFiscal": folio}, {"orderId": order_id})
    datos = order.get("invoiceData") or {}
    if datos.get("email"):
        _avisar_factura_emitida(order, datos, folio, url_archivo)
    return utils._json_response(200, {
        "orderId": order_id, "invoiceStatus": "emitida", "invoiceIssuedAt": ahora,
        "invoiceFolio": folio or None, "invoiceFileUrl": url_archivo,
    })


def _avisar_factura_emitida(order: dict, datos: dict, folio: str, url_archivo) -> None:
    from core.email import _email_shell
    oid = order.get("orderId")
    texto = f"Tu factura del pedido {oid} ya está lista"
    if folio:
        texto += f" (folio {folio})"
    texto += "."
    if url_archivo:
        texto += f" Descárgala aquí: {url_archivo}"
    cuerpo = f"""
    <div class="icon">🧾</div>
    <h1 class="title">Tu factura ya está lista</h1>
    <p class="lead">Pedido <strong>{oid}</strong> · RFC <strong>{datos.get('rfc', '')}</strong>{(' · folio ' + folio) if folio else ''}.</p>
    {('<a href="' + url_archivo + '" class="btn">Descargar factura &rarr;</a>') if url_archivo else '<p class="lead">Te la adjuntamos en un correo aparte.</p>'}
    """
    utils._send_ses_email(datos["email"], f"Factura del pedido {oid} · Finding'U", texto, _email_shell(cuerpo))


# ---------------------------------------------------------------------------
# Ruteo
# ---------------------------------------------------------------------------

def atender(request) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = _segmentos(request)
    method, body, headers, query = request.method, request.body, request.headers, request.query

    if len(seg) >= 2 and seg[0] == "checkout":
        if seg[1] == "envio-info" and len(seg) == 2:
            if method != "GET":
                return utils._json_response(405, {"message": "Método no permitido"})
            return utils._json_response(200, info_envio(query.get("subtotal") or 0, query.get("net")))
        if seg[1] == "sugerencia-activacion" and len(seg) == 2:
            if method != "POST":
                return utils._json_response(405, {"message": "Método no permitido"})
            return sugerencia_activacion(body, headers)
        if seg[1] == "sucursales-recoger" and len(seg) == 2:
            if method != "POST":
                return utils._json_response(405, {"message": "Método no permitido"})
            return sucursales_recoger(body)
        return utils._json_response(404, {"message": "Ruta de checkout no encontrada"})

    if len(seg) >= 2 and seg[1] == "factura":
        order_id = seg[0]
        if len(seg) == 2:
            if method != "POST":
                return utils._json_response(405, {"message": "Método no permitido"})
            return solicitar_factura(order_id, body, headers)
        if len(seg) == 3 and seg[2] == "emitida":
            if method != "POST":
                return utils._json_response(405, {"message": "Método no permitido"})
            err = utils._require_admin(headers, "order_mark_paid")
            if err:
                return err
            return marcar_factura_emitida(order_id, body, headers)
        return utils._json_response(404, {"message": "Ruta de factura no encontrada"})

    return None
