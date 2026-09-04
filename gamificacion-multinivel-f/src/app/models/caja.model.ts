/** Caja y arqueo (paquete E): lo que devuelve `/inventory/pos/*` para el corte, el retiro y el pago mixto. */

export type MovimientoCajaTipo = 'opening' | 'sale' | 'settlement' | 'mixed' | 'withdrawal';

export interface MovimientoCaja {
  type: MovimientoCajaTipo;
  id?: string | null;
  at?: string | null;
  /** Positivo entra al cajón; negativo (retiro) sale. */
  amount: number;
  label: string;
  customerName?: string;
}

export interface ArqueoCaja {
  stockId: string;
  attendantUserId?: string | number | null;
  since?: string | null;
  lastCutId?: string | null;
  lastCutAt?: string | null;
  openingCash: number;
  cashSales: number;
  cashSettlements: number;
  cashFromMixed: number;
  withdrawals: number;
  withdrawalCount: number;
  nonCashTotal: number;
  expectedCash: number;
  salesCount: number;
  startedAt?: string | null;
  lastSaleAt?: string | null;
  movements: MovimientoCaja[];
  /**
   * De dónde sale el fondo inicial (paquete F · ronda 26, propuesta 5):
   * `apertura` lo declaró quien abrió el turno, `corte_anterior` lo dejó el
   * corte de ayer y `sin_declarar` significa que esta caja nunca ha cerrado un
   * corte: la pantalla pide capturarlo en vez de enseñar un $0.00 de adorno.
   */
  openingSource?: OrigenFondoCaja;
  openingDeclaredAt?: string | null;
  openingDeclaredBy?: string;
  /** Hay que declarar el fondo antes de operar. */
  needsOpening?: boolean;
  config: {
    denominations: number[];
    requireDifferenceReason: boolean;
    notifyEmailConfigured: boolean;
    /** Con False, el corte no pide el fondo aunque la caja nunca haya cortado. */
    requireOpeningCash?: boolean;
    /** ¿La gerencia ya configuró un código de autorización? (propuesta 6). */
    authCodeConfigured?: boolean;
  };
}

export type OrigenFondoCaja = 'apertura' | 'corte_anterior' | 'sin_declarar';

export interface AperturaTurnoPayload {
  stockId: string;
  openingCash: number;
  note?: string;
}

export interface AperturaTurnoRespuesta {
  opening: {
    openingId: string;
    stockId: string;
    openingCash: number;
    declaredBy: string;
    createdAt: string;
    reabierto?: boolean;
  };
  arqueo: ArqueoCaja;
}

export interface CorteCaja {
  cashCutId: string;
  stockId: string;
  attendantUserId?: string | number | null;
  total: number;
  salesCount: number;
  cashToKeep: number;
  withdrawnAmount: number;
  totalWithdrawals: number;
  withdrawalCount?: number;
  openingCash?: number;
  cashSales?: number;
  cashSettlements?: number;
  cashFromMixed?: number;
  nonCashTotal?: number;
  cashExpected?: number;
  cashCounted?: number;
  difference?: number;
  differenceReason?: string;
  denominations?: Record<string, number>;
  withdrawalReceiver?: string;
  cutWithdrawalId?: string;
  startedAt?: string;
  endedAt?: string;
  createdAt?: string;
  notifiedTo?: string;
  notifiedAt?: string;
}

export interface CerrarCortePayload {
  stockId: string;
  cashCounted: number;
  denominations?: Record<string, number>;
  differenceReason?: string;
  cashToKeep: number;
  withdrawalAmount: number;
  withdrawalReceiver?: string;
  authCode?: string;
}

export interface RetiroCaja {
  withdrawalId: string;
  stockId: string;
  amount: number;
  reason: string;
  receiver?: string;
  cashCutId?: string;
  createdAt?: string;
}

export interface RetiroCajaPayload {
  stockId: string;
  amount: number;
  reason: string;
  receiver: string;
  authCode: string;
}

export interface RetiroCajaRespuesta {
  withdrawal: RetiroCaja;
  control: { currentTotal: number; salesCount: number; withdrawalCount?: number; totalWithdrawn?: number };
  remainingCash: number;
}

export type MetodoPagoCaja = 'cash' | 'card' | 'transfer';

export interface PagoVenta {
  method: MetodoPagoCaja;
  amount: number;
}

export interface VentaCajaPayload {
  stockId: string;
  customerId?: number | null;
  customerName?: string;
  paymentMethod?: MetodoPagoCaja | 'mixed';
  payments?: PagoVenta[];
  paymentStatus?: string;
  deliveryStatus?: string;
  items: Array<{ productId: number; name: string; price: number; quantity: number }>;
  discountAmount?: number;
  discountRate?: number;
  cashReceived?: number;
  cashierDiscountMode?: 'percent' | 'amount';
  cashierDiscountValue?: number;
  paymentType?: 'full' | 'partial' | 'credit';
  amountPaid?: number;
  authCode?: string;
}

/** Lo que el servidor guardó: la confirmación se arma con esto, no con el formulario. */
export interface VentaCajaRespuesta {
  saleId: string;
  orderId: string;
  total: number;
  amountPaid: number;
  pendingAmount: number;
  cashPortion: number;
  change: number | null;
  payments: PagoVenta[];
  sale: { paymentMethod?: string; customerName?: string; createdAt?: string };
}

export interface AbonoCajaRespuesta {
  pendingAmount: number;
  payment: { saleId: string; total: number; paymentMethod: string; orderId?: string };
  sale: { saleId: string; orderId?: string; paymentStatus?: string; amountPaid?: number };
}

export interface AnulacionCajaRespuesta {
  ok: boolean;
  saleId: string;
  orderId?: string;
  status: string;
}
