/** Modelos del paquete H: suscripción mensual y conciliación de pagos. */

export type SuscripcionEstado = 'active' | 'paused' | 'cancelled';
export type SuscripcionEntrega = 'delivery' | 'shipping' | 'pickup';

export interface SuscripcionItem {
  productId: string | number;
  name: string;
  quantity: number;
  /** Precio de lista al momento de guardar; el descuento se aplica al generar cada pedido. */
  price: number;
  vpPoints?: number;
}

export interface SuscripcionDireccion {
  id?: string;
  addressId?: string;
  label?: string;
  recipientName?: string;
  phone?: string;
  street?: string;
  number?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
}

export interface Suscripcion {
  subscriptionId: string;
  customerId: string | number;
  customerName?: string;
  items: SuscripcionItem[];
  /** Día del mes (1–28) en que se crea el pedido. */
  dayOfMonth: number;
  deliveryType: SuscripcionEntrega;
  shippingAddress?: SuscripcionDireccion | null;
  shippingAddressId?: string | null;
  pickupStockId?: string | null;
  pickupStockName?: string | null;
  status: SuscripcionEstado;
  pausedUntil?: string | null;
  nextRunDate?: string | null;
  lastRunDate?: string | null;
  lastOrderId?: string | null;
  cancelledAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SuscripcionItemPayload {
  productId: string | number;
  quantity: number;
}

export interface SuscripcionPayload {
  customerId?: string | number;
  items: SuscripcionItemPayload[];
  dayOfMonth: number;
  deliveryType: SuscripcionEntrega;
  shippingAddressId?: string;
  shippingAddress?: SuscripcionDireccion;
  pickupStockId?: string;
}

export interface SuscripcionCambios {
  items?: SuscripcionItemPayload[];
  dayOfMonth?: number;
  deliveryType?: SuscripcionEntrega;
  shippingAddressId?: string;
  shippingAddress?: SuscripcionDireccion;
  pickupStockId?: string;
  status?: 'active' | 'paused';
  pausedUntil?: string;
}

export interface SuscripcionRespuesta {
  subscription: Suscripcion;
  alreadyCancelled?: boolean;
}

export interface ConciliacionAcreditado {
  orderId: string;
  paymentId: string;
  dryRun?: boolean;
}

export interface ConciliacionResultado {
  runId: string;
  checked: number;
  credited: ConciliacionAcreditado[];
  unpaid: string[];
  errors: Array<{ orderId: string; error: string }>;
  dryRun?: boolean;
  hours?: number;
  /** Solo cuando MercadoPago no respondió para ningún pedido (502). */
  message?: string;
  // ── Paquete G · ronda 26 · propuesta 26 ──
  /** Cuántos pedidos revisó como mucho esta corrida. */
  limit?: number;
  /** Cuántos quedaron fuera del tope y faltan por revisar. */
  pending?: number;
  hasMore?: boolean;
  /** Hora del **servidor**, para no fecharla con el reloj del navegador. */
  startedAt?: string;
  finishedAt?: string;
}

export interface ConciliacionCorrida extends ConciliacionResultado {
  triggeredBy?: string;
}

export interface ConciliacionPayload {
  hours?: number;
  /** Fecha de inicio (AAAA-MM-DD); el servidor la traduce a horas con su reloj. */ // paquete G · ronda 26
  since?: string; // paquete G · ronda 26
  /** Tope de pedidos por corrida: cada uno consulta a MercadoPago. */ // paquete G · ronda 26
  limit?: number; // paquete G · ronda 26
  orderIds?: string[];
  dryRun?: boolean;
}
