/**
 * Paquete D · almacén, despacho y paquetería.
 * Contratos de `/inventory/despacho/*`, `/inventory/envios/*` y `/inventory/turno/resumen`
 * (docs/arquitectura/23 §4.3).
 */

export interface DespachoItem {
  productId: string;
  name: string;
  quantity: number;
}

export interface DespachoPendiente {
  id: string;
  customer: string;
  recipientName?: string;
  createdAt?: string;
  paidAt?: string;
  daysSincePaid: number | null;
  items: DespachoItem[];
  city?: string;
  state?: string;
  hasInvoiceRequest: boolean;
  shippingCarrier?: string;
  trackingNumber?: string;
  total?: number | string | null;
  status?: string;
}

export interface EnvioRezagado {
  id: string;
  customer: string;
  shippedAt?: string;
  daysSinceShipped: number;
  trackingNumber?: string;
  shippingCarrier?: string;
  deliveryCheckEmailSentAt?: string | null;
}

export interface CarrierIntegrationInfo {
  enabled: boolean;
  provider: string;
  trackingEnabled: boolean;
  askDays: number;
  autoCloseDays: number;
}

export interface DespachoPendientesResponse {
  orders: DespachoPendiente[];
  staleShipped: EnvioRezagado[];
  carrierIntegration: CarrierIntegrationInfo;
}

export interface SurtidoOtraBodega {
  stockId: string;
  name: string;
  available: number;
}

export interface SurtidoLinea {
  productId: string;
  name: string;
  needed: number;
  available: number;
  status: 'ok' | 'short';
  short: number;
  elsewhere: SurtidoOtraBodega[];
}

export interface PedidoBloqueado {
  orderId: string;
  reason: string;
}

export interface SurtidoResponse {
  stockId: string;
  stockName: string;
  canDispatch: boolean;
  lines: SurtidoLinea[];
  reasons: string[];
  blockedOrders: PedidoBloqueado[];
  orderIds: string[];
  orderCount: number;
}

export interface EnvioGuia {
  orderId: string;
  carrier: string;
  trackingNumber: string;
}

export interface DespachoEnviarPayload {
  stockId: string;
  shipments?: EnvioGuia[];
  csv?: string;
  generateLabels?: boolean;
  orderIds?: string[];
}

export interface PedidoDespachado {
  orderId: string;
  trackingNumber: string;
  carrier: string;
  labelUrl?: string;
  status: string;
  customer?: string;
}

export interface DespachoEnviarResponse {
  batchId: string;
  stockId: string;
  stockName: string;
  shipped: PedidoDespachado[];
  failed: PedidoBloqueado[];
}

export interface PreferenciasDespacho {
  defaultStockId: string | null;
  stockName: string | null;
}

export interface BodegaResumen {
  id: string;
  name: string;
  location?: string;
}

export interface RastreoResponse {
  enabled: boolean;
  dryRun?: boolean;
  checked: number;
  delivered: Array<{ orderId: string; deliveredAt: string; signedBy: string }>;
  inTransit: string[];
  errors: Array<{ orderId: string; text: string }>;
  message?: string;
}

export interface CierreResponse {
  enabled: boolean;
  dryRun?: boolean;
  checked: number;
  askDays?: number;
  autoCloseDays?: number;
  asked: string[];
  closed: string[];
  message?: string;
}

export interface ResumenTurnoDespachado {
  orderId: string;
  customer: string;
  carrier: string;
  trackingNumber: string;
  stock: string;
  at?: string;
}

export interface ResumenTurnoEntregado {
  orderId: string;
  customer: string;
  signedBy: string;
  at?: string;
}

export interface ResumenTurnoTransferencia {
  transferId: string;
  source: string;
  destination?: string;
  lines?: number;
  missing?: number;
  discrepancies?: Array<{ productId: string; sent: number; received: number; missing: number }>;
  at?: string;
}

export interface ResumenTurnoMovimiento {
  productId: string;
  name: string;
  qty: number;
  reason?: string;
  stock: string;
  at?: string;
}

export interface ResumenTurno {
  user: { id: string; name: string };
  date: string;
  dispatched: ResumenTurnoDespachado[];
  delivered: ResumenTurnoEntregado[];
  transfers: { created: ResumenTurnoTransferencia[]; received: ResumenTurnoTransferencia[] };
  entries: ResumenTurnoMovimiento[];
  damages: ResumenTurnoMovimiento[];
  pos: {
    sales: Array<{ saleId: string; orderId: string; total: number; customer: string; paymentMethod: string; at?: string }>;
    salesTotal: number;
    cuts: Array<{ cashCutId: string; total: number; at?: string }>;
  };
  events: Array<{ action: string; target: Record<string, unknown>; at?: string }>;
  counters: Record<string, number>;
  text: string;
  /** Solo llega a quien puede ver el turno de otros (access_screen_stats). */
  team?: Array<{ id: string; name: string }>;
}
