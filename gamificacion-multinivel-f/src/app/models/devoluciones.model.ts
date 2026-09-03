/**
 * Paquete G · devoluciones por producto (propuesta 18).
 * Contratos de `POST /orders/{id}/return` (ampliado), `GET /orders/{id}/devolucion`
 * y los campos nuevos de inspección y reembolso del back office.
 */

export type DevolucionMotivo = 'DANADO_DEFECTUOSO' | 'ERROR_ENVIO' | 'DESISTIMIENTO';
export type DevolucionEstado = 'PENDIENTE' | 'DEVUELTO_VALIDADO' | 'DEVOLUCION_RECHAZADA';
export type DevolucionCategoriaEvidencia = 'fotos_paquete_cerrado' | 'fotos_producto' | 'fotos_empaque' | 'fotos_guia_envio';

export interface DevolucionArchivo {
  contentBase64: string;
  contentType: string;
  fileName: string;
}

/** Línea del pedido que se devuelve (la responde el servidor con el neto unitario). */
export interface DevolucionLinea {
  productId: number | string;
  name: string;
  quantity: number;
  purchasedQuantity?: number;
  unitPrice?: number;
  unitNet?: number;
}

export interface DevolucionReembolso {
  suggested: number | null;
  products: number | null;
  returnShipping: number | null;
  originalShipping: number | null;
  /** "mismo medio de pago" */
  method: string;
  /** "3 a 5" (días hábiles) */
  businessDays: string;
}

export type DevolucionEvidencia = Partial<Record<DevolucionCategoriaEvidencia, DevolucionArchivo[]>>;

export interface DevolucionSolicitudPayload {
  motivo: DevolucionMotivo;
  descripcion?: string;
  /** Qué se devuelve; sin este campo el servidor toma todo el pedido. */
  lines: Array<{ productId: number | string; quantity: number }>;
  evidence: DevolucionEvidencia;
  /** Lo que la clienta pagó por el envío de regreso (se reembolsa si el motivo es nuestro). */
  returnShippingCost?: number;
}

export interface DevolucionSolicitudResponse {
  ok: boolean;
  requestId: string;
  status: DevolucionEstado;
  shippingResponsibility: 'empresa' | 'cliente';
  lines: DevolucionLinea[];
  partial: boolean;
  refund: DevolucionReembolso;
  warehouseAddress: string;
  message: string;
}

export interface DevolucionLineaRecibida {
  productId: number | string;
  quantity: number;
  matches: boolean;
}

/** `GET /orders/{id}/devolucion` → `{ request: DevolucionDetalle }`. */
export interface DevolucionDetalle {
  requestId: string;
  orderId: string;
  status: DevolucionEstado;
  orderStatus: string;
  motivo: DevolucionMotivo;
  motivoLabel: string;
  descripcion: string;
  lines: DevolucionLinea[];
  partial: boolean;
  evidence: Partial<Record<DevolucionCategoriaEvidencia, string[]>>;
  evidenceRule: 'paquete_cerrado' | 'completa' | null;
  shippingResponsibility: 'empresa' | 'cliente';
  returnShippingCost: number;
  refund: DevolucionReembolso;
  inspection: { inspectedAt: string; notes?: string | null; linesReceived: DevolucionLineaRecibida[] } | null;
  rejectionReason?: string | null;
  courtesyCoupon?: string | null;
  refundedAt?: string | null;
  refundAmount?: number | null;
  refundAdjustmentReason?: string | null;
  warehouseAddress: string;
  createdAt: string;
}

/** Desglose del reembolso sugerido, tal como lo guarda la solicitud. */
export interface DevolucionDesglose {
  products: number | null;
  returnShipping: number | null;
  originalShipping: number | null;
}
