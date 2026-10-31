"""Vocabulario único de estados y métodos de pago (paquete G, propuesta 25).

Julio contó cuatro nombres para el mismo estado en cuatro pantallas —"Pago
registrado", "Pagada", "Pendiente/Pagada/Enviada/Entregada" y `paid` crudo, en
inglés— y Alma se topó con `mixed`, también en inglés, justo en el número que
venía a cuadrar en el corte de caja. No era una traducción incompleta: eran
cuatro tablas distintas escritas en cuatro sitios.

Este módulo es **la** tabla. Es auxiliar y puro (no toca DynamoDB ni la
configuración): quien no es su dueño lo importa, no lo edita. Su gemelo en el
frontend es `models/vocabulario.model.ts`, con exactamente los mismos textos.

Reglas que se aplican en todas las salidas (docs/arquitectura/26 §3.7 y §4.17):

- Español de México, **sin género**: "Pagado", "Entregado", "Cancelado". Al
  señor de 63 años el sistema le dijo "socia" cinco veces, incluso por correo.
- La recolección en sucursal tiene matiz propio: `paid` + `pickup` es
  "Listo para recoger", no "Pagado"; `delivered` + `pickup` es
  "Entregado en sucursal".
- `mixed` se dice completo —"Mixto (efectivo + tarjeta)"— y, cuando se conocen
  las dos partes, con su desglose al centavo.
"""
#: Estado guardado → texto en pantalla (§3.7). Sin género y en español.
ESTADOS_PEDIDO = {
    "pending": "Pendiente de pago",
    "paid": "Pagado",
    "shipped": "Enviado",
    "delivered": "Entregado",
    "cancelled": "Cancelado",
    "returned": "Devuelto",
    "refunded": "Reembolsado",
    "rejected": "Rechazado",
    "en_devolucion": "Devolución en curso",
    "devuelto_validado": "Devolución validada",
    "devolucion_rechazada": "Devolución rechazada",
}

#: Matiz de recolección en sucursal: el mismo estado, dicho como lo vive quien recoge.
ESTADOS_PEDIDO_PICKUP = {
    "paid": "Listo para recoger",
    "delivered": "Entregado en sucursal",
}

#: Variantes que la base guardó a lo largo del tiempo y significan lo mismo.
ALIAS_ESTADO = {
    "canceled": "cancelled",
    "cancelada": "cancelled",
    "devuelta": "returned",
    "return_validated": "devuelto_validado",
    "return_rejected": "devolucion_rechazada",
    "in_return": "en_devolucion",
}

#: Método de pago guardado → texto en pantalla (§3.7).
METODOS_PAGO = {
    "cash": "Efectivo",
    "card": "Tarjeta",
    "transfer": "Transferencia",
    "mercadopago": "MercadoPago",
    "branch": "Pago en sucursal",
    "mixed": "Mixto (efectivo + tarjeta)",
}

#: Tipo de entrega → texto en pantalla.
TIPOS_ENTREGA = {
    "delivery": "Envío a domicilio",
    "pickup": "Recoger en sucursal",
}


def _clave(valor) -> str:
    clave = str(valor or "").strip().lower()
    return ALIAS_ESTADO.get(clave, clave)


def estado_pedido(status, delivery_type=None) -> str:
    """Texto del estado del pedido, con el matiz de recolección si aplica.

    Devuelve el valor guardado tal cual cuando no está en la tabla: es
    preferible enseñar el dato crudo a inventarle un nombre nuevo (que es
    justo como nacieron los cuatro nombres del mismo estado).
    """
    clave = _clave(status)
    if not clave:
        return ""
    if str(delivery_type or "").strip().lower() == "pickup" and clave in ESTADOS_PEDIDO_PICKUP:
        return ESTADOS_PEDIDO_PICKUP[clave]
    return ESTADOS_PEDIDO.get(clave, str(status))


def metodo_pago(method, efectivo=None, no_efectivo=None) -> str:
    """Texto del método de pago; `mixed` con su desglose cuando se conoce.

    "Mixto (efectivo + tarjeta) · $500.00 en efectivo · $260.00 con tarjeta"
    es exactamente el número que Alma venía a cuadrar y que la pantalla le
    escondía detrás de una palabra en inglés.
    """
    clave = str(method or "").strip().lower()
    texto = METODOS_PAGO.get(clave, str(method or ""))
    if clave == "mixed" and efectivo is not None and no_efectivo is not None:
        return f"{texto} · {formato_monto(efectivo)} en efectivo · {formato_monto(no_efectivo)} con tarjeta"
    return texto


def tipo_entrega(delivery_type) -> str:
    clave = str(delivery_type or "").strip().lower()
    return TIPOS_ENTREGA.get(clave, str(delivery_type or ""))


def formato_monto(valor) -> str:
    """$1,350.00 — el mismo formato en pantalla, en el correo y en el CSV."""
    try:
        return "${:,.2f}".format(float(valor or 0))
    except (TypeError, ValueError):
        return "$0.00"


MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def fecha_larga(iso, con_hora: bool = True) -> str:
    """«2 de marzo de 2027, 11:18» a partir de un ISO. Nunca un ISO crudo.

    Ernesto preguntó "«Creada: 2027-03-02T11:18:04Z»: ¿qué es esa T y esa Z?".
    """
    texto = str(iso or "").strip()
    if not texto:
        return ""
    from datetime import datetime
    try:
        fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return texto
    salida = f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"
    if con_hora:
        salida += f", {fecha.hour:02d}:{fecha.minute:02d}"
    return salida


def mes_largo(month_key) -> str:
    """«marzo de 2027» a partir de «2027-03»."""
    partes = str(month_key or "").split("-")
    if len(partes) != 2:
        return str(month_key or "")
    try:
        anio, mes = int(partes[0]), int(partes[1])
    except ValueError:
        return str(month_key or "")
    if not 1 <= mes <= 12:
        return str(month_key or "")
    return f"{MESES[mes - 1]} de {anio}"

