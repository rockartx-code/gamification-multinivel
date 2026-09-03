// Paquete A · pagos-comisiones: contratos de /commissions/pagos/* (doc 23 §1.3).

export type PagoEstado = 'listo' | 'sin_clabe' | 'pagado';

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
}

export interface PagoTotal {
  count: number;
  amount: number;
}

export interface PagosMes {
  monthKey: string;
  rows: PagoFila[];
  totals: { listo: PagoTotal; sinClabe: PagoTotal; pagado: PagoTotal };
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
