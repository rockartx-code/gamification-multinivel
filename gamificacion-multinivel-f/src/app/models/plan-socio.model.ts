/**
 * Modo cliente / modo socio y plan publicado (paquete B).
 *
 * Todo lo que se pinta sale de `GET /catalog/plan` o de `GET /customers/modo`:
 * ningún porcentaje ni umbral vive en el frontend.
 */

export type ModoCuenta = 'cliente' | 'socio';

export interface PlanTramo {
  min: number;
  max: number | null;
  rate: number;
}

export interface PlanProductoEjemplo {
  id: string;
  name: string;
  price: number;
  pc: number;
  qty: number;
}

export interface PlanEjemploActivacion {
  productos: PlanProductoEjemplo[];
  bruto: number;
  rate: number;
  vp: number;
  activa: boolean;
}

export interface PlanEjemploDescuento {
  compraMes: number;
  rate: number;
  descuento: number;
  pagas: number;
}

export interface PlanGeneracion {
  gen: number;
  rate: number;
  requisitos: { activeDirects: number; personalPC: number; lines: number; pcPerLine: number };
  requisitoTexto: string;
  ejemplo: { compraReferido: number; comision: number };
}

export interface PlanRango {
  rank: string;
  vgMin: number;
  vpMin: number;
  minLines: number;
  monthlyBonus: number;
}

export interface PlanSocio {
  version: string;
  unidades: { mxnPerVp: number; maxLevels: number; pc: string; vp: string; vg: string };
  activacion: { vpNetos: number; pesosAprox: number; ejemplos: PlanEjemploActivacion[]; nota: string };
  descuento: { tramos: PlanTramo[]; ejemplos: PlanEjemploDescuento[] };
  generaciones: PlanGeneracion[];
  compresionDinamica: boolean;
  pago: {
    dia: number;
    estados: string[];
    reevaluaBloqueadasAlActivarse?: boolean;
    bloqueo: { avisos: number[]; graciaDias: number };
  };
  datos: Array<{ cuando: string; que: string[] }>;
  rangos: PlanRango[];
  bonos: Array<{ id: string; name: string; notes: string }>;
}

export interface SiguienteTramo {
  rate: number;
  missing: number;
}

export interface AhorroSocio {
  gross: number;
  monthNet: number;
  projected: number;
  rate: number;
  savings: number;
  nextTier: SiguienteTramo | null;
}

export interface IndicadoresCliente {
  monthKey: string;
  /** Neto comprado este mes (sí se acredita aunque esté en modo cliente). */
  monthSpend: number;
  /** Suma de `partnerSavings` de los pedidos pagados del mes. */
  monthSavingsIfPartner: number;
  currentRateIfPartner: number;
  nextTier: SiguienteTramo | null;
  exampleEarnings: { friends: number; purchaseEach: number; rate: number; total: number };
}

export interface ModoCuentaRespuesta {
  mode: ModoCuenta;
  modeSince?: string | null;
  modeActivatedAt?: string | null;
  modeReason?: string | null;
  planVersion: string;
  indicators: IndicadoresCliente;
}

export interface ActivacionModoSocioRespuesta {
  mode: ModoCuenta;
  modeActivatedAt: string | null;
  alreadyPartner: boolean;
  customerId: string;
  name: string;
  modeReason?: string | null;
  planVersion: string;
}

/** Misma regla que `order_lambda._resolve_discount_rate`: acumulado previo + compra, sin retroactividad. */
export function tasaDeTramos(tramos: PlanTramo[], basis: number): number {
  const ordenados = [...tramos].sort((a, b) => a.min - b.min);
  for (const tramo of ordenados) {
    if (basis >= tramo.min && (tramo.max == null || basis < tramo.max)) {
      return tramo.rate;
    }
  }
  return 0;
}

export function tramoDe(tramos: PlanTramo[], basis: number): PlanTramo | null {
  const ordenados = [...tramos].sort((a, b) => a.min - b.min);
  return ordenados.find((t) => basis >= t.min && (t.max == null || basis < t.max)) ?? null;
}

export function siguienteTramo(tramos: PlanTramo[], basis: number): SiguienteTramo | null {
  const ordenados = [...tramos].sort((a, b) => a.min - b.min);
  const siguiente = ordenados.find((t) => t.min > basis);
  return siguiente ? { rate: siguiente.rate, missing: Math.round((siguiente.min - basis) * 100) / 100 } : null;
}

export function calcularAhorroConTramos(tramos: PlanTramo[], gross: number, monthNet: number): AhorroSocio {
  const bruto = Math.max(0, Number(gross) || 0);
  const neto = Math.max(0, Number(monthNet) || 0);
  const proyectado = neto + bruto;
  const rate = tasaDeTramos(tramos, proyectado);
  return {
    gross: bruto,
    monthNet: neto,
    projected: proyectado,
    rate,
    savings: Math.round(bruto * rate * 100) / 100,
    nextTier: siguienteTramo(tramos, proyectado)
  };
}

export function formatoPesos(valor: number): string {
  const monto = Number.isFinite(valor) ? valor : 0;
  const centavos = Number.isInteger(Math.round(monto * 100) / 100) ? 0 : 2;
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: centavos,
    maximumFractionDigits: centavos
  }).format(monto);
}

/** 0.1 → "10 %". */
export function formatoPorcentaje(rate: number): string {
  const valor = Math.round((Number(rate) || 0) * 1000) / 10;
  return `${valor} %`;
}

export function formatoPuntos(valor: number): string {
  const numero = Number.isFinite(valor) ? valor : 0;
  return Number.isInteger(Math.round(numero * 10) / 10) ? String(Math.round(numero)) : numero.toFixed(1);
}
