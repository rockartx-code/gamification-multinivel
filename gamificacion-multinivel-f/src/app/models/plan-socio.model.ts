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

/**
 * Lo que de verdad cuesta activarse, de lo más barato a lo más caro según el
 * producto (propuesta 14). Sustituye al `pesosAprox` que la propia página
 * desmentía tres renglones abajo. `null` cuando el catálogo no tiene PC.
 */
export interface PlanRangoActivacion {
  min: number;
  max: number;
  notaProducto: string;
}

/** Sobre qué base se paga la comisión, dicho por el servidor (propuesta 37). */
export interface PlanBaseComision {
  clave: string;
  frase: string;
  /** Neto de la canasta más barata que de verdad activa. */
  compraEjemplo: number;
  /** Cómo es esa canasta: `2 × Klinhart`. */
  canastaEjemplo: string;
}

/** El IVA que ya llevan dentro los precios de lista (propuesta 38). */
export interface PlanIva {
  tasa: number;
  etiqueta: string;
  preciosIncluyenIva: boolean;
  aplicaAlEnvio: boolean;
}

export interface PlanSocio {
  version: string;
  unidades: { mxnPerVp: number; maxLevels: number; pc: string; vp: string; vg: string };
  activacion: {
    vpNetos: number;
    rango: PlanRangoActivacion | null;
    ejemplos: PlanEjemploActivacion[];
    nota: string;
  };
  descuento: { tramos: PlanTramo[]; ejemplos: PlanEjemploDescuento[] };
  generaciones: PlanGeneracion[];
  baseComision: PlanBaseComision;
  iva: PlanIva;
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

// ── Simulador del plan (paquete B, propuesta 36) ───────────────────────────

export interface SimuladorEntrada {
  directos: number;
  /** Lo que paga cada persona al mes, ya con su descuento y sin envío. */
  compraPorDirecto: number;
  /** Tu propia compra del mes, a precio de lista. */
  compraPropia: number;
  nivelesProfundidad: number;
}

export interface SimuladorGeneracion {
  gen: number;
  rate: number;
  personas: number;
  compraNetaPorPersona: number;
  requisitoTexto: string;
  cumple: boolean;
  /** Por qué cumple o por qué no, con el número que falta. */
  porQue: string;
  comision: number;
  /** `10 % de $1,350.00 netos, sin envío = $135.00`. */
  textoBase: string;
  /** De la generación 2 en adelante son personas que el usuario NO capturó. */
  supuesta?: boolean;
}

export interface SimuladorResultado {
  tuCompra: {
    bruto: number;
    tramo: number;
    descuento: number;
    netoPagado: number;
    vp: number;
    activa: boolean;
    vpParaActivar: number;
    iva: { base: number; iva: number; tasa: number; etiqueta: string };
  };
  generaciones: SimuladorGeneracion[];
  comisionTotal: number;
  gastoPropio: number;
  /** Comisiones menos gasto propio. Se muestra siempre, también en rojo. */
  gananciaNeta: number;
  baseComision: string;
  fraseBaseComision: string;
  explicacion: string[];
  /** Aviso del acantilado del tramo de descuento: '' si esta compra no está en un escalón. */
  advertenciaTramo?: string;
  supuestos: string[];
  aviso: string;
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
  /** VP netos acumulados del mes (también se acumulan en modo cliente). */
  monthVp?: number;
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

// ── Paquete B · ronda 26 ────────────────────────────────────────────────────
// Gemelas de `Micro-lambda-GMF/python/impuestos.py`: la misma cuenta del IVA y
// la misma redacción de la base de la comisión, escritas una sola vez.

/** Importe siempre con centavos: `$1,350.00`. Es dinero, no un dato suelto. */
export function formatoPesosExactos(valor: number): string {
  const monto = Number.isFinite(valor) ? valor : 0;
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(monto);
}

export interface DesgloseIva {
  /** Lo que se cobra. No cambia: el IVA se desglosa, nunca se suma. */
  total: number;
  /** Base gravable: `total / (1 + tasa)`, redondeada a dos decimales. */
  base: number;
  /** `total − base`, de modo que `base + iva === total` al centavo. */
  iva: number;
  rate: number;
  label: string;
}

/**
 * Desglosa el IVA de un total que ya lo incluye, con el mismo supuesto que el
 * servidor (docs/arquitectura/26 §3.1): una sola redondeada, a dos decimales,
 * mitad arriba, al final y sobre el total; nunca por línea.
 */
export function desgloseIva(totalCobrado: number, rate: number, label = 'IVA'): DesgloseIva {
  const total = Math.round((Number(totalCobrado) || 0) * 100) / 100;
  const tasa = Number(rate) || 0;
  if (total <= 0 || tasa <= 0 || tasa >= 1) {
    return { total, base: total, iva: 0, rate: tasa, label };
  }
  const base = Math.round((total / (1 + tasa)) * 100) / 100;
  return { total, base, iva: Math.round((total - base) * 100) / 100, rate: tasa, label };
}

/** Cómo llama el negocio a la base de la comisión, con las palabras del plan. */
export const BASE_COMISION = 'neto pagado por producto, sin envío';

/** La frase larga: página del plan, simulador y correo de comisión. */
export const FRASE_BASE_COMISION =
  'Tu comisión se calcula sobre el neto que pagó tu referida por producto ' +
  '—el precio ya con su descuento, con IVA incluido— y sin contar el envío.';

/** La frase por fila: `10 % de $1,350.00 netos, sin envío = $135.00`. */
export function textoBaseComision(neto: number, tasa: number, importe: number): string {
  return `${formatoPorcentaje(tasa)} de ${formatoPesosExactos(neto)} netos, sin envío = ${formatoPesosExactos(importe)}`;
}
