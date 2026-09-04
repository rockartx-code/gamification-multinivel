"""Correos del ciclo de vida del pedido.

Durante un mes de simulación con clientes reales (docs/qa/18) ningún
comprador recibió un solo correo después de activar su cuenta: ni de pago,
ni de envío, ni de entrega, ni de devolución. Una compradora vivió trece
días sin saber si su paquete existía. Estos correos cierran ese hueco.
"""
from decimal import Decimal

from . import email as _correo



def _direccion_bodega_principal() -> str:
    """Nombre y dirección del almacén marcado como principal (para devoluciones)."""
    try:
        from core import db as _db
        for stock in _db._query_bucket("STOCK") or []:
            if stock.get("isMainWarehouse"):
                return ", ".join(x for x in (stock.get("name"), stock.get("location")) if x)
    except Exception:
        pass
    return ""


def _sucursal_de_recoleccion(order: dict) -> str:
    """Nombre y dirección de la sucursal donde se recoge el pedido ("Sucursal Guadalajara, Av. Chapultepec 480")."""
    if str(order.get("deliveryType") or "") != "pickup":
        return ""
    stock_id = str(order.get("pickupStockId") or "").strip()
    if not stock_id:
        return ""
    try:
        from core import db as _db
        stock = _db._get_by_id("STOCK", stock_id) or {}
    except Exception:
        return ""
    return ", ".join(x for x in (stock.get("name"), stock.get("location")) if x)


def _mxn(valor) -> str:
    try:
        return f"${Decimal(str(valor or 0)):,.2f}"
    except Exception:
        return "$0.00"


def _destinatario(order: dict, buscar_cliente) -> str:
    """Correo del comprador: el del pedido (invitado) o el de su ficha."""
    correo = str(order.get("email") or order.get("customerEmail") or "").strip()
    if correo:
        return correo
    cid = order.get("customerId")
    if cid:
        cliente = buscar_cliente(cid) or {}
        return str(cliente.get("email") or "").strip()
    return ""


def _renglones_detalle(order: dict) -> list[str]:
    """El detalle del pedido, renglón a renglón, para el correo HTML y el de texto plano.

    Mariana compró sin cuenta y su único comprobante fue un correo que no decía qué había
    comprado: la versión de texto plano nunca llamaba a este detalle.
    """
    filas = []
    for it in order.get("items") or []:
        qty = int(it.get("quantity") or it.get("qty") or 1)
        filas.append(f"{qty} × {it.get('name') or it.get('productId')} — {_mxn(Decimal(str(it.get('price') or 0)) * qty)}")
    descuento = order.get("discountAmount")
    if descuento:
        filas.append(f"Descuento — -{_mxn(descuento)}")
    envio = order.get("shippingCost")
    if envio:
        filas.append(f"Envío ({order.get('shippingCarrier') or 'paquetería'}) — {_mxn(envio)}")
    total = order.get("total") if order.get("total") is not None else order.get("netTotal")
    filas.extend(_renglones_iva(order))
    filas.append(f"Total — {_mxn(total)}")
    return filas


def _renglones_iva(order: dict) -> list[str]:
    """Desglose del IVA guardado en el pedido (paquete B, §38): el total no cambia, se explica.

    Los pedidos anteriores a la ronda no traen `taxBase`/`taxAmount`; en ese caso no se
    inventa nada y el correo enseña el total como siempre.
    """
    base, iva = order.get("taxBase"), order.get("taxAmount")
    if base is None or iva is None:
        return []
    try:
        tasa = Decimal(str(order.get("vatRate") or 0)) * 100
    except Exception:
        tasa = Decimal(0)
    etiqueta = f"IVA {tasa.quantize(Decimal('1'))} %" if tasa > 0 else "IVA"
    return [f"Subtotal sin IVA — {_mxn(base)}", f"{etiqueta} — {_mxn(iva)}"]


def _lineas(order: dict) -> str:
    renglones = _renglones_detalle(order)
    if not renglones:
        return ""
    cuerpo = "".join(f"<p>{fila}</p>" for fila in renglones[:-1])
    return cuerpo + f"<p><strong>{renglones[-1]}</strong></p>"


def _renglones_entrega(order: dict) -> list[str]:
    """Cómo y a dónde se entrega, con las palabras que la persona eligió en el carrito."""
    if str(order.get("deliveryType") or "") == "pickup":
        sucursal = _sucursal_de_recoleccion(order)
        # Tres personas que eligieron recoger recibieron "estamos preparando tu paquete
        # y te avisaremos cuando salga": nadie iba a salir a ningún lado.
        renglones = [f"Recoges en {sucursal}" if sucursal else "Recoges en sucursal"]
        if str(order.get("pickupPaymentMethod") or "") == "at_store":
            renglones.append("Pagas al recoger, en la caja de la sucursal.")
        return renglones
    direccion = ", ".join(
        str(x).strip() for x in (
            order.get("address") or " ".join(str(x) for x in (order.get("street"), order.get("number")) if x),
            order.get("city"), order.get("state"), order.get("postalCode"),
        ) if x
    )
    if not direccion:
        return []
    nombre = order.get("recipientName") or order.get("customerName") or ""
    return [f"Envío a domicilio: {direccion}" + (f" · a nombre de {nombre}" if nombre else "")]


def _renglones_factura(order: dict) -> list[str]:
    """El detalle fiscal que la persona capturó. Aurora abandonó buscando dónde releer su RFC."""
    if not order.get("invoiceRequested"):
        return []
    datos = order.get("invoiceData") or {}
    nombre = str(datos.get("razonSocial") or "").strip()
    rfc = str(datos.get("rfc") or "").strip()
    correo = str(datos.get("email") or "").strip()
    estado = str(order.get("invoiceStatus") or "").strip()
    cabecera = "Factura emitida" if estado == "emitida" else "Factura solicitada"
    renglones = [cabecera + (f" a nombre de {nombre}" if nombre else "") + (f" · RFC {rfc}" if rfc else "")]
    if correo:
        renglones.append(f"Te la mandamos a {correo}.")
    folio = str(order.get("invoiceFolio") or "").strip()
    if folio:
        renglones.append(f"Folio fiscal {folio}.")
    return renglones


def _bloque_pedido(order: dict) -> str:
    """La caja de "esto fue lo que compraste": detalle, entrega y factura, en ese orden."""
    extras = "".join(f"<p>{fila}</p>" for fila in _renglones_entrega(order) + _renglones_factura(order))
    return _lineas(order) + extras


def _politica_reembolso(datos: dict) -> dict:
    """Medio y plazo del reembolso: los de la solicitud o, si no vienen, los de config."""
    politica = datos.get("refundPolicy") or (datos.get("refund") or {})
    metodo, plazo = politica.get("method"), politica.get("businessDays")
    if not (metodo and plazo):
        try:
            from core import config as _config
            cfg = _config._load_app_config().get("returns") or {}
        except Exception:
            cfg = {}
        metodo = metodo or cfg.get("refundMethod") or "mismo medio de pago"
        plazo = plazo or cfg.get("refundBusinessDays") or "3 a 5"
    return {"method": str(metodo), "businessDays": str(plazo)}


def _texto_plazo(datos: dict) -> str:
    p = _politica_reembolso(datos)
    return f"al <strong>{p['method']}</strong>, en <strong>{p['businessDays']} días hábiles</strong>"


def _lineas_devueltas(datos: dict) -> str:
    """Bloque 'Lo que devuelves' con las líneas de la solicitud (vacío si no hay)."""
    lineas = datos.get("lines") or []
    if not lineas:
        return ""
    filas = "".join(
        f"<p>{int(l.get('quantity') or 0)} × {l.get('name') or l.get('productId')}"
        + (f" — {_mxn(Decimal(str(l.get('unitNet') or 0)) * int(l.get('quantity') or 0))}" if l.get('unitNet') is not None else "")
        + "</p>"
        for l in lineas
    )
    titulo = "Lo que devuelves" if datos.get("partial") else "Devuelves el pedido completo"
    return f'<div class="info-box"><p><strong>{titulo}</strong></p>{filas}</div>'


# ── Paquete D · ronda 26 ── la política de devolución en el correo ─────────
# Julio preguntó por WhatsApp las cuatro cosas —plazo, evidencia, quién paga el
# envío y a dónde se manda— porque no estaban escritas en ninguna pantalla. El
# texto no se escribe aquí: se lee de `ayuda_handlers.texto_politica`, la misma
# fuente que `#/devoluciones` y el asistente, para que cambiar el plazo en
# configuración lo cambie en las cuatro salidas a la vez.

def _motivos_publicados_seguro() -> list:
    try:
        import ayuda_handlers
        return ayuda_handlers.motivos_publicados()
    except Exception:   # pragma: no cover - el correo nunca rompe el pedido
        return []


def _pasos_politica_devolucion() -> list:
    try:
        import ayuda_handlers
        return ayuda_handlers.texto_politica()
    except Exception:   # pragma: no cover - el correo nunca rompe el pedido
        return []


def _bloque_politica_devolucion(titulo: str = "Cómo funciona una devolución") -> str:
    pasos = _pasos_politica_devolucion()
    if not pasos:
        return ""
    filas = "".join(f"<p><strong>{p['titulo']}.</strong> {p['texto']}</p>" for p in pasos)
    return f'<div class="info-box"><p><strong>{titulo}</strong></p>{filas}</div>'


def _seguimiento(order: dict, frontend_url: str) -> str:
    # La ruta real del seguimiento es /#/orden/{id}; la primera versión
    # enlazaba a una página que no existe ("link muerto" en el primer correo útil).
    return f"{frontend_url.rstrip('/')}/#/orden/{order.get('orderId')}"


def _parrafo_ahorro_socio(order: dict, frontend_url: str) -> str:
    """Paquete B: al comprador en modo cliente (o invitado) le decimos cuánto habría ahorrado como socia.

    Los campos `partnerSavings*` los deja `_calculate_totals` en el pedido; a un socio no se le dice nada.
    """
    if str(order.get("partnerMode") or "") not in ("cliente", "invitado"):
        return ""
    ahorro = Decimal(str(order.get("partnerSavings") or 0))
    enlace = f"{frontend_url.rstrip('/')}/#/modo-socio?desde=orden&id={order.get('orderId')}"
    if ahorro > 0:
        frase = f"Como socia habrías ahorrado <strong>{_mxn(ahorro)}</strong> en esta compra."
    else:
        faltan = Decimal(str(order.get("partnerSavingsNextMissing") or 0))
        tasa = Decimal(str(order.get("partnerSavingsNextRate") or 0)) * 100
        if faltan <= 0 or tasa <= 0:
            return ""
        frase = f"Como socia, con <strong>{_mxn(faltan)}</strong> más de compra este mes tendrías {tasa:.0f} % de descuento."
    return (f'<div class="info-box"><p>{frase} El modo socio es gratis, no te pide datos extra y lo activas cuando quieras.</p>'
            f'<p><a href="{enlace}">Conoce el modo socio</a></p></div>')


def _plantillas(order: dict, evento: str, datos: dict, frontend_url: str):
    nombre = order.get("recipientName") or order.get("customerName") or "Hola"
    oid = order.get("orderId")
    url = _seguimiento(order, frontend_url)
    guia = datos.get("trackingNumber") or order.get("trackingNumber") or ""
    paqueteria = datos.get("shippingCarrier") or order.get("shippingCarrier") or "la paquetería"
    lugar = datos.get("deliveryPlace") or order.get("deliveryPlace") or ""
    fecha = datos.get("deliveryDate") or order.get("deliveryDate") or ""

    recoge = str(order.get("deliveryType") or "") == "pickup"
    sucursal = _sucursal_de_recoleccion(order)

    if evento == "paid":
        asunto = f"Recibimos tu pago · pedido {oid}"
        titulo, icono = "¡Gracias por tu compra!", "✅"
        if recoge:
            # A tres compradores de mostrador este correo les prometió un paquete en camino.
            lead = ("Tu pago quedó confirmado. Lo preparamos y te avisamos por este medio en cuanto esté "
                    + (f"listo para recoger en <strong>{sucursal}</strong>." if sucursal else "listo para recoger en la sucursal que elegiste."))
        else:
            lead = "Tu pago quedó confirmado. Estamos preparando tu paquete y te avisaremos por este medio cuando salga."
        if order.get("invoiceRequested"):
            lead += " Recibimos tu solicitud de factura: te la mandaremos al correo que nos diste."
        extra = _parrafo_ahorro_socio(order, frontend_url)
    elif evento == "shipped" and recoge:
        asunto = f"Tu pedido {oid} ya está listo para recoger"
        titulo, icono = "Ya lo puedes recoger", "🏪"
        lead = ("Pasa por él a " + (f"<strong>{sucursal}</strong>" if sucursal else "la sucursal que elegiste")
                + " con tu folio y una identificación.")
        extra = ""
    elif evento == "shipped":
        asunto = f"Tu pedido {oid} va en camino"
        titulo, icono = "Tu paquete ya salió", "🚚"
        if guia:
            lead = f"Lo enviamos por {paqueteria}. Guía: <strong>{guia}</strong>. Suele llegar en 2 a 5 días hábiles."
        elif lugar or fecha:
            lead = f"Lo entregamos en persona{(' en ' + lugar) if lugar else ''}{(' el ' + fecha) if fecha else ''}."
        else:
            lead = "Ya salió de nuestro almacén."
        extra = ""
    elif evento == "delivered":
        asunto = f"Tu pedido {oid} fue entregado"
        # C · propuesta 7: quien recogió en mostrador no leyó "llegó tu pedido".
        titulo, icono = ("Recogiste tu pedido" if recoge else "¡Llegó tu pedido!"), "📦"
        entregado = ("Ya nos consta que recogiste tu pedido" + (f" en {sucursal}" if sucursal else " en sucursal") + ". "
                     if recoge else "")
        # D · propuesta 39: los plazos no se escriben a mano en el correo (decían
        # 48 h y 7 días aunque la configuración dijera otra cosa); se leen de la
        # misma política que publica la pantalla de devoluciones.
        plazos = " ".join(f"«{m['label']}»: {m['plazoTexto']}."
                          for m in _motivos_publicados_seguro())
        lead = (entregado
                + "Revisa que todo esté bien. Si algo salió mal puedes pedir la devolución desde tu "
                  "seguimiento, del pedido completo o solo de lo que falló. "
                + (f"El plazo se cuenta desde hoy. {plazos}" if plazos else ""))
        extra = _bloque_politica_devolucion()
    elif evento == "return_received":
        asunto = f"Recibimos tu solicitud de devolución · {datos.get('requestId') or oid}"
        titulo, icono = "Solicitud de devolución recibida", "↩️"
        # "Envía el paquete a nuestro almacén" sin dirección: la clienta tuvo que
        # preguntar a soporte a dónde mandarlo y si iba todo el pedido.
        direccion = datos.get("direccionAlmacen") or _direccion_bodega_principal()
        # La pantalla decía "el envío corre a tu cargo" y este correo prometía reembolsarlo: depende del motivo.
        paga_cliente = str(datos.get("shippingResponsibility") or "").lower() == "cliente"
        envio_txt = ("El envío de regreso corre por tu cuenta (devolución por arrepentimiento)."
                     if paga_cliente else
                     "El envío de regreso lo paga la empresa: guarda tu ticket de paquetería, te lo reembolsamos junto con el producto.")
        que = "solo los productos que marcaste (no todo el pedido)" if datos.get("partial") else "el pedido completo"
        reembolso = datos.get("refund") or {}
        monto = reembolso.get("suggested")
        cuanto = (f" Cuando lo revisemos te devolvemos <strong>{_mxn(monto)}</strong> {_texto_plazo(datos)}."
                  if monto is not None else f" Cuando lo revisemos te devolvemos tu dinero {_texto_plazo(datos)}.")
        lead = (f"Folio <strong>{datos.get('requestId') or ''}</strong>. Envía {que}, en su empaque, a "
                f"<strong>{direccion or 'nuestro almacén'}</strong> con el folio escrito en el paquete. {envio_txt}{cuanto}")
        extra = _lineas_devueltas(datos) + _bloque_politica_devolucion("El proceso, paso a paso")
    elif evento == "return_approved":
        asunto = f"Devolución aprobada · pedido {oid}"
        titulo, icono = "Devolución aprobada", "👍"
        monto = datos.get("amount")
        lead = ("Ya recibimos y revisamos tu paquete. "
                + (f"Te devolvemos <strong>{_mxn(monto)}</strong> " if monto is not None else "Te devolvemos tu dinero ")
                + f"{_texto_plazo(datos)}; te confirmaremos por aquí cuando salga.")
        extra = _lineas_devueltas(datos)
    elif evento == "return_rejected":
        asunto = f"Devolución no procedente · pedido {oid}"
        titulo, icono = "No pudimos aprobar la devolución", "ℹ️"
        motivo = str(datos.get('reason') or 'no cumple las condiciones de devolución').strip().rstrip('.')
        lead = f"Motivo: {motivo}. Si crees que es un error, responde a este correo y lo revisamos contigo."
        if datos.get("courtesyCode"):
            pct = datos.get("courtesyPercent")
            lead += (f" Como cortesía te dejamos el cupón <strong>{datos['courtesyCode']}</strong>"
                     f"{f' ({int(float(pct))}% de descuento)' if pct else ''}: escríbelo en el carrito en tu próxima compra; es personal y de un solo uso.")
        extra = ""
    elif evento == "refunded":
        asunto = f"Reembolso realizado · pedido {oid}"
        titulo, icono = "Tu reembolso ya salió", "💸"
        monto = datos.get("amount")
        politica = _politica_reembolso(datos)
        cuando = str(datos.get("refundedAt") or "")[:10]
        lead = ((f"Hoy{' (' + cuando + ')' if cuando else ''} devolvimos <strong>{_mxn(monto)}</strong>" if monto is not None
                 else f"Hoy{' (' + cuando + ')' if cuando else ''} devolvimos tu reembolso")
                + f" al <strong>{politica['method']}</strong> con el que compraste. Según tu banco puede tardar hasta 2 días hábiles en reflejarse.")
        extra = _lineas_devueltas(datos)
    elif evento == "pos_sale":
        asunto = f"Registramos una compra a tu nombre en tienda · {oid}"
        titulo, icono = "Compra en tienda registrada", "🏪"
        lead = (f"Hoy se registró en nuestra tienda física una compra a tu nombre por <strong>{_mxn(order.get('total') if order.get('total') is not None else order.get('netTotal'))}</strong>, "
                "que cuenta para tu consumo del mes. <strong>Si no fuiste tú</strong>, responde a este correo o escríbenos por WhatsApp hoy mismo y la anulamos.")
        extra = ""
    elif evento == "pos_voided":
        asunto = f"Anulamos la compra en tienda {oid}"
        titulo, icono = "Compra en tienda anulada", "↩️"
        lead = "Retiramos de tu cuenta la compra en tienda que nos reportaste: ya no cuenta para tu consumo ni genera comisiones. Gracias por avisarnos."
        extra = ""
    elif evento == "cancelled":
        asunto = f"Pedido {oid} cancelado"
        titulo, icono = "Tu pedido quedó cancelado", "🚫"
        # Hallazgo 2 de la ronda 4: el correo prometía el reembolso sin decir cuándo ni a dónde.
        lead = (f"Como el pago ya estaba confirmado, te devolvemos el importe completo {_texto_plazo(datos)}; te avisaremos cuando salga."
                if datos.get("pendingRefund") else "No se hizo ningún cargo. Si fue un error, puedes volver a comprar cuando quieras.")
        extra = ""
    elif evento == "delivery_check":
        # Paquete D: a los N días sin confirmación de entrega se le pregunta al
        # comprador. "Sí, llegó" marca el pedido entregado a su nombre; "Aún no"
        # abre un correo a soporte con el folio.
        asunto = f"¿Te llegó tu pedido {oid}?"
        titulo, icono = "¿Ya recibiste tu paquete?", "📬"
        lead = (f"Lo enviamos por {paqueteria}{(' con la guía ' + guia) if guia else ''} y no tenemos confirmación de entrega. "
                "Dinos si ya lo tienes: así cerramos tu pedido y liberamos las comisiones de tu equipo.")
        confirmar = datos.get("confirmUrl") or url
        soporte = datos.get("supportUrl") or f"mailto:info@findingu.com.mx?subject=Mi pedido {oid} no ha llegado"
        extra = (f'<p style="margin:16px 0 0"><a class="btn" href="{confirmar}">Sí, ya llegó</a></p>'
                 f'<p style="margin:12px 0 0"><a href="{soporte}">Aún no llega, avisar a soporte</a></p>')
    else:
        return None

    cuerpo = f"""
    <div class="icon">{icono}</div>
    <h1 class="title">{titulo}</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. {lead}</p>
    <div class="info-box">
      <p><strong>Pedido {oid}</strong></p>
      {_bloque_pedido(order)}
    </div>
    {extra}
    <a class="btn" href="{url}">Ver mi pedido</a>
    """
    # El correo de texto plano repite el mismo detalle: era el único comprobante de
    # quien compró sin cuenta y llegaba sin una sola línea de lo comprado.
    detalle_plano = "\n".join(_renglones_detalle(order) + _renglones_entrega(order) + _renglones_factura(order))
    texto = (f"{titulo}\n\nHola {nombre}. " + lead.replace("<strong>", "").replace("</strong>", "")
             + f"\n\nPedido {oid}\n{detalle_plano}\n\nSeguimiento: {url}\n")
    if evento == "delivery_check":
        texto += f"\nSí, ya llegó: {datos.get('confirmUrl') or url}\nAún no llega: {datos.get('supportUrl') or ''}\n"
    elif extra:
        import re as _re
        # Las etiquetas en línea (<strong>) no dejan espacios ("con  $300.00  más")
        # y el enlace va en su propia línea, no pegado al párrafo.
        plano = _re.sub(r"</p>\s*<p[^>]*>", "\n", extra)
        plano = _re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>([^<]*)</a>", r"\2: \1", plano)
        plano = _re.sub(r"<[^>]+>", "", plano)
        plano = _re.sub(r"[ \t]{2,}", " ", plano)
        texto += "\n" + "\n".join(l.strip() for l in plano.strip().splitlines()) + "\n"
    return asunto, texto, _correo._email_shell(cuerpo)


def notificar_pedido(order: dict, evento: str, datos: dict | None, buscar_cliente, frontend_url: str) -> bool:
    """Manda el correo del evento si el pedido tiene a quién. Nunca interrumpe el flujo."""
    try:
        para = _destinatario(order, buscar_cliente)
        if not para:
            return False
        plantilla = _plantillas(order, evento, datos or {}, frontend_url)
        if not plantilla:
            return False
        asunto, texto, html = plantilla
        _correo._send_ses_email(para, asunto, texto, html)
        return True
    except Exception as e:  # pragma: no cover - el correo nunca rompe el pedido
        print(f"[ORDER_EMAIL_ERROR] {order.get('orderId')}: {e}")
        return False
