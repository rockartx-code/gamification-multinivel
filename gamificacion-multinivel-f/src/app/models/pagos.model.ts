// Paquete A · pagos-comisiones: contratos de /commissions/pagos/* (doc 23 §1.3).

export type PagoEstado = 'listo' | 'sin_clabe' | 'pagado' | 'por_confirmar';

/** Lo que frena un importe: el pedido y cuántos días lleva parado (18). */
export interface PagoFreno {
  orderId: string;
  desde: string;
  dias: number;
  texto: string;
  pedidos: number;
}

export interface PagoFila {
  customerId: string;
  name: string;
  email: string;
  phone: string;
  amount: number;
  /** `••••••••••••••1234`; en pantalla nunca va la CLABE completa. */
  clabeMasked: string;
  bankInstitution: string;
  status: PagoEstado;
  receiptUrl: string;
  paidAt?: string | null;
  batchId?: string | null;
  clabeReminderAt?: string | null;
  doNotContact?: boolean;
  // ── Paquete A · ronda 26 · propuesta 18: las tres cifras del mismo dinero ──
  /** Lo que se deposita (igual que `amount`, con su nombre propio). */
  confirmado: number;
  /** Esperando la entrega del pedido. */
  porConfirmar: number;
  /** Sin activación en el mes. */
  bloqueado: number;
  /** confirmado + porConfirmar + bloqueado. */
  reconocido: number;
  frenoPorConfirmar: PagoFreno | null;
  frenoBloqueado: PagoFreno | null;
}

export interface PagoTotal {
  count: number;
  amount: number;
}

export interface PagosMes {
  monthKey: string;
  rows: PagoFila[];
  totals: {
    listo: PagoTotal;
    sinClabe: PagoTotal;
    pagado: PagoTotal;
    porConfirmarFilas: PagoTotal;
    confirmado: number;
    porConfirmar: number;
    bloqueado: number;
    reconocido: number;
  };
  /** La frase de §3.2: sobre qué base se calcula la comisión. */
  baseComisionTexto: string;
}

/** Un mes contable con datos, tal como lo publica `GET /commissions/periodos`. */
export interface PagoPeriodo {
  monthKey: string;
  label: string;
  beneficiarias: number;
  confirmado: number;
  porConfirmar: number;
  bloqueado: number;
  estado: 'IN_PROGRESS' | 'PAID';
}

/**
 * Propuesta 17: los meses del dinero los manda el servidor. Ninguna pantalla
 * vuelve a construirlos con `new Date()` del navegador (§3.6).
 */
export interface PagoPeriodos {
  serverNow: string;
  mesContableVigente: string;
  defaultMonth: string;
  payoutDay: number;
  periodos: PagoPeriodo[];
}

export interface LotePagoPayload {
  monthKey: string;
  customerIds: string[];
  name: string;
  contentType: string;
  contentBase64: string;
  bankReference?: string;
}

export type LoteSaltoCodigo = 'CLABE_REQUIRED' | 'ALREADY_PAID' | 'NO_CONFIRMED';

export interface LotePagoRespuesta {
  batchId: string;
  monthKey: string;
  assetUrl: string;
  paid: Array<{ customerId: string; receiptId: string; amount: number }>;
  skipped: Array<{ customerId: string; code: LoteSaltoCodigo }>;
  totalPaid: number;
}

export interface DeshacerPagoRespuesta {
  ok: boolean;
  receiptsVoided: number;
  status: string;
  customerId: string;
  monthKey: string;
  batchId?: string | null;
}

export interface PedirClabeRespuesta {
  sent: boolean;
  channel: 'email+panel' | 'panel';
  customerId: string;
  name: string;
  email: string;
  monthKey: string;
  clabeReminderAt: string;
}

export interface AvisoBloqueadasRespuesta {
  day: number;
  monthKey: string;
  notified: Array<{
    customerId: string;
    name: string;
    blocked: number;
    vpMissing: number;
    product: { id: string; name: string; units: number; cost: number } | null;
  }>;
  skipped?: string;
  dryRun?: boolean;
}


/**
 * Propuesta 37, §3.2: *"10 % de $1,350.00 netos, sin envío = $135.00"*.
 * La redacción la publica el paquete B en `models/plan-socio.model.ts`;
 * mientras tanto vive aquí con las mismas palabras, para que no haya dos
 * versiones del texto en pantalla.
 */
export function textoBaseComision(neto: number, tasa: number, importe: number): string {
  const pesos = (v: number) => `$${(v ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const porcentaje = (tasa ?? 0) * 100;
  const porcentajeTexto = Math.abs(porcentaje - Math.round(porcentaje)) < 0.05
    ? porcentaje.toFixed(0)
    : porcentaje.toFixed(1);
  return `${porcentajeTexto} % de ${pesos(neto)} netos, sin envío = ${pesos(importe)}`;
}
