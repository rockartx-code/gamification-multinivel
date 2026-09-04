/**
 * Vocabulario único de estados y métodos de pago (paquete G, propuesta 25).
 *
 * Julio contó cuatro nombres para el mismo estado en cuatro pantallas —"Pago
 * registrado", "Pagada", "Pendiente/Pagada/Enviada/Entregada" y `paid` crudo,
 * en inglés— y Alma se topó con `mixed`, también en inglés, justo en el número
 * que venía a cuadrar en el corte de caja.
 *
 * Este archivo es **la** tabla del frontend, gemela de
 * `Micro-lambda-GMF/python/vocabulario.py`: los mismos textos, palabra por
 * palabra. Cada pantalla la usa; ninguna escribe su propia versión.
 *
 * Reglas (docs/arquitectura/26 §3.7 y §4.17):
 * - Español de México y **sin género**: "Pagado", "Entregado", "Cancelado".
 * - La recolección tiene matiz propio: `paid` + `pickup` es "Listo para
 *   recoger"; `delivered` + `pickup` es "Entregado en sucursal".
 * - `mixed` se dice completo, "Mixto (efectivo + tarjeta)", con su desglose
 *   cuando se conocen las dos partes.
 * - Fechas con `DatePipe` y locale `es-MX`: `FORMATO_FECHA_LARGA` en pantalla
 *   y `FORMATO_FECHA_TABLA` en tablas. Nunca un ISO crudo.
 */

/** Estado guardado → texto en pantalla. */
export const ESTADOS_PEDIDO: Readonly<Record<string, string>> = {
  pending: 'Pendiente de pago',
  paid: 'Pagado',
  shipped: 'Enviado',
  delivered: 'Entregado',
  cancelled: 'Cancelado',
  returned: 'Devuelto',
  refunded: 'Reembolsado',
  rejected: 'Rechazado',
  en_devolucion: 'Devolución en curso',
  devuelto_validado: 'Devolución validada',
  devolucion_rechazada: 'Devolución rechazada'
};

/** Matiz de recolección en sucursal: el mismo estado, dicho como lo vive quien recoge. */
export const ESTADOS_PEDIDO_PICKUP: Readonly<Record<string, string>> = {
  paid: 'Listo para recoger',
  delivered: 'Entregado en sucursal'
};

/** Variantes que la base guardó a lo largo del tiempo y significan lo mismo. */
export const ALIAS_ESTADO: Readonly<Record<string, string>> = {
  canceled: 'cancelled',
  cancelada: 'cancelled',
  devuelta: 'returned',
  return_validated: 'devuelto_validado',
  return_rejected: 'devolucion_rechazada',
  in_return: 'en_devolucion'
};

/** Método de pago guardado → texto en pantalla. */
export const METODOS_PAGO: Readonly<Record<string, string>> = {
  cash: 'Efectivo',
  card: 'Tarjeta',
  transfer: 'Transferencia',
  mercadopago: 'MercadoPago',
  branch: 'Pago en sucursal',
  mixed: 'Mixto (efectivo + tarjeta)'
};

/** Tipo de entrega → texto en pantalla. */
export const TIPOS_ENTREGA: Readonly<Record<string, string>> = {
  delivery: 'Envío a domicilio',
  pickup: 'Recoger en sucursal'
};

/** Formato de fecha en pantalla: «2 de marzo de 2027, 11:18». */
export const FORMATO_FECHA_LARGA = "d 'de' MMMM 'de' y, HH:mm";
/** Formato de fecha en tablas: «02/03/2027». */
export const FORMATO_FECHA_TABLA = 'dd/MM/yyyy';
/** Locale único de todas las fechas del producto. */
export const LOCALE_MX = 'es-MX';

function claveEstado(valor: string | null | undefined): string {
  const clave = String(valor ?? '').trim().toLowerCase();
  return ALIAS_ESTADO[clave] ?? clave;
}

/**
 * Texto del estado del pedido, con el matiz de recolección si aplica.
 * Un estado que no está en la tabla se devuelve tal cual: enseñar el dato
 * crudo es preferible a inventarle un quinto nombre.
 */
export function textoEstadoPedido(status: string | null | undefined, deliveryType?: string | null): string {
  const clave = claveEstado(status);
  if (!clave) {
    return '';
  }
  if (String(deliveryType ?? '').trim().toLowerCase() === 'pickup' && ESTADOS_PEDIDO_PICKUP[clave]) {
    return ESTADOS_PEDIDO_PICKUP[clave];
  }
  return ESTADOS_PEDIDO[clave] ?? String(status ?? '');
}

/** $1,350.00 — el mismo formato en pantalla, en el correo y en el CSV. */
export function formatoMonto(valor: number | string | null | undefined): string {
  const numero = Number(valor ?? 0);
  const seguro = Number.isFinite(numero) ? numero : 0;
  return `$${seguro.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Texto del método de pago; `mixed` con su desglose cuando se conocen las dos
 * partes: "Mixto (efectivo + tarjeta) · $500.00 en efectivo · $260.00 con tarjeta".
 */
export function textoMetodoPago(
  method: string | null | undefined,
  efectivo?: number | null,
  noEfectivo?: number | null
): string {
  const clave = String(method ?? '').trim().toLowerCase();
  const texto = METODOS_PAGO[clave] ?? String(method ?? '');
  if (clave === 'mixed' && efectivo !== null && efectivo !== undefined && noEfectivo !== null && noEfectivo !== undefined) {
    return `${texto} · ${formatoMonto(efectivo)} en efectivo · ${formatoMonto(noEfectivo)} con tarjeta`;
  }
  return texto;
}

/** Texto del tipo de entrega. */
export function textoTipoEntrega(deliveryType: string | null | undefined): string {
  const clave = String(deliveryType ?? '').trim().toLowerCase();
  return TIPOS_ENTREGA[clave] ?? String(deliveryType ?? '');
}

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
];

/**
 * «lunes 25 de marzo de 2027, 23:59» a partir de un ISO o un Date, para los
 * textos donde la fecha se escribe dentro de una frase y no cabe un `DatePipe`.
 */
export function fechaEnLetras(valor: string | Date | null | undefined, conDia = false): string {
  if (!valor) {
    return '';
  }
  const fecha = valor instanceof Date ? valor : new Date(valor);
  if (Number.isNaN(fecha.getTime())) {
    return String(valor);
  }
  const dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
  const hora = `${String(fecha.getHours()).padStart(2, '0')}:${String(fecha.getMinutes()).padStart(2, '0')}`;
  const cuerpo = `${fecha.getDate()} de ${MESES[fecha.getMonth()]} de ${fecha.getFullYear()}, ${hora}`;
  return conDia ? `${dias[fecha.getDay()]} ${cuerpo}` : cuerpo;
}

/** «marzo de 2027» a partir de «2027-03». */
export function mesEnLetras(monthKey: string | null | undefined): string {
  const partes = String(monthKey ?? '').split('-');
  if (partes.length !== 2) {
    return String(monthKey ?? '');
  }
  const anio = Number(partes[0]);
  const mes = Number(partes[1]);
  if (!Number.isInteger(anio) || !Number.isInteger(mes) || mes < 1 || mes > 12) {
    return String(monthKey ?? '');
  }
  return `${MESES[mes - 1]} de ${anio}`;
}
