"""Correos del ciclo de vida del pedido.

Durante un mes de simulación con clientes reales (docs/qa/18) ningún
comprador recibió un solo correo después de activar su cuenta: ni de pago,
ni de envío, ni de entrega, ni de devolución. Una compradora vivió trece
días sin saber si su paquete existía. Estos correos cierran ese hueco.
"""
from decimal import Decimal

from . import email as _correo


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


def _lineas(order: dict) -> str:
    filas = []
    for it in order.get("items") or []:
        qty = int(it.get("quantity") or it.get("qty") or 1)
        filas.append(f"<p>{qty} × {it.get('name') or it.get('productId')} — {_mxn(Decimal(str(it.get('price') or 0)) * qty)}</p>")
    envio = order.get("shippingCost")
    if envio:
        filas.append(f"<p>Envío ({order.get('shippingCarrier') or 'paquetería'}) — {_mxn(envio)}</p>")
    total = order.get("total") if order.get("total") is not None else order.get("netTotal")
    filas.append(f"<p><strong>Total — {_mxn(total)}</strong></p>")
    return "".join(filas)


def _seguimiento(order: dict, frontend_url: str) -> str:
    # La ruta real del seguimiento es /#/orden/{id}; la primera versión
    # enlazaba a una página que no existe ("link muerto" en el primer correo útil).
    return f"{frontend_url.rstrip('/')}/#/orden/{order.get('orderId')}"


def _plantillas(order: dict, evento: str, datos: dict, frontend_url: str):
    nombre = order.get("recipientName") or order.get("customerName") or "Hola"
    oid = order.get("orderId")
    url = _seguimiento(order, frontend_url)
    guia = datos.get("trackingNumber") or order.get("trackingNumber") or ""
    paqueteria = datos.get("shippingCarrier") or order.get("shippingCarrier") or "la paquetería"
    lugar = datos.get("deliveryPlace") or order.get("deliveryPlace") or ""
    fecha = datos.get("deliveryDate") or order.get("deliveryDate") or ""

    if evento == "paid":
        asunto = f"Recibimos tu pago · pedido {oid}"
        titulo, icono = "¡Gracias por tu compra!", "✅"
        lead = "Tu pago quedó confirmado. Estamos preparando tu paquete y te avisaremos por este medio cuando salga."
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
        titulo, icono = "¡Llegó tu pedido!", "📦"
        lead = "Revisa que todo esté bien. Si algo llegó dañado tienes 48 horas para pedir la devolución desde tu seguimiento; si simplemente te arrepentiste, 7 días."
        extra = ""
    elif evento == "return_received":
        asunto = f"Recibimos tu solicitud de devolución · {datos.get('requestId') or oid}"
        titulo, icono = "Solicitud de devolución recibida", "↩️"
        lead = (f"Folio <strong>{datos.get('requestId') or ''}</strong>. Envía el paquete a nuestro almacén y guarda tu ticket de envío: "
                "te lo reembolsamos junto con el producto una vez que lo revisemos (1 a 3 días hábiles tras recibirlo).")
        extra = ""
    elif evento == "return_approved":
        asunto = f"Devolución aprobada · pedido {oid}"
        titulo, icono = "Devolución aprobada", "👍"
        lead = "Ya recibimos y revisamos tu paquete. El reembolso se procesa en los próximos 3 días hábiles y te confirmaremos por aquí cuando salga."
        extra = ""
    elif evento == "return_rejected":
        asunto = f"Devolución no procedente · pedido {oid}"
        titulo, icono = "No pudimos aprobar la devolución", "ℹ️"
        lead = f"Motivo: {datos.get('reason') or 'no cumple las condiciones de devolución'}. Si crees que es un error, responde a este correo y lo revisamos contigo."
        extra = ""
    elif evento == "refunded":
        asunto = f"Reembolso realizado · pedido {oid}"
        titulo, icono = "Tu reembolso ya salió", "💸"
        monto = datos.get("amount")
        lead = (f"Transferimos <strong>{_mxn(monto)}</strong> a la cuenta que nos indicaste." if monto is not None
                else "Transferimos el reembolso a la cuenta que nos indicaste.") + " Puede tardar hasta 2 días hábiles en reflejarse."
        extra = ""
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
        lead = ("Como el pago ya estaba confirmado, te reembolsaremos el importe completo y te avisaremos cuando salga."
                if datos.get("pendingRefund") else "No se hizo ningún cargo. Si fue un error, puedes volver a comprar cuando quieras.")
        extra = ""
    else:
        return None

    cuerpo = f"""
    <div class="icon">{icono}</div>
    <h1 class="title">{titulo}</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. {lead}</p>
    <div class="info-box">
      <p><strong>Pedido {oid}</strong></p>
      {_lineas(order)}
    </div>
    {extra}
    <a class="btn" href="{url}">Ver mi pedido</a>
    """
    texto = f"{titulo}\n\nHola {nombre}. " + lead.replace("<strong>", "").replace("</strong>", "") + f"\n\nPedido {oid}. Seguimiento: {url}\n"
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
