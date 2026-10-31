/** Paquete C · checkout-y-sesion: contratos de `GET/POST /orders/checkout/*`, factura y enlace de acceso. */

export interface OpcionSat {
  key: string;
  label: string;
}

export interface CheckoutConfig {
  invoiceEnabled: boolean;
  regimenesFiscales: OpcionSat[];
  usosCfdi: OpcionSat[];
}

export interface EnvioInfo {
  /** Tarifa desde la que se anuncia el envío antes de cotizar ("Envío desde $129"). */
  baseRateMxn: number;
  /** Importe desde el que el envío es gratis; 0 = sin regla. */
  freeShippingMin: number;
  basis: 'gross' | 'net';
  missingForFree: number;
  freeNow: boolean;
  checkout: CheckoutConfig;
}

export interface SugerenciaActivacionItem {
  productId: number | string;
  quantity: number;
  price: number;
}

export interface ProductoSugerido {
  productId: number | string;
  name: string;
  price: number;
  units: number;
  netVpPerUnit: number;
  cost: number;
  discountRate: number;
  vpAfter: number;
}

export interface SugerenciaActivacion {
  applies: boolean;
  reason?: string;
  activationVp?: number;
  vpNow: number;
  vpCart?: number;
  vpAfterCart: number;
  gap: number;
  suggestion: ProductoSugerido | null;
}

export interface SucursalRecoger {
  id: string;
  name: string;
  location: string;
  city?: string | null;
  state?: string | null;
  inArea: boolean;
  canPickup: boolean;
  missing: string[];
}

export interface SucursalesRecoger {
  available: boolean;
  locationGiven: boolean;
  cities: string[];
  stocks: SucursalRecoger[];
}

export interface DatosFiscales {
  rfc: string;
  razonSocial: string;
  regimenFiscal: string;
  cpFiscal: string;
  usoCfdi: string;
  email: string;
}

export type EstadoFactura = 'no_aplica' | 'solicitada' | 'emitida';

export interface FacturaSolicitada {
  orderId: string;
  invoiceStatus: EstadoFactura;
  invoiceRequestedAt: string;
  invoiceData: DatosFiscales;
  message: string;
}

export interface FacturaEmitidaPayload {
  folioFiscal?: string;
  name?: string;
  contentType?: string;
  contentBase64?: string;
}

export interface FacturaEmitida {
  orderId: string;
  invoiceStatus: EstadoFactura;
  invoiceIssuedAt: string;
  invoiceFolio?: string | null;
  invoiceFileUrl?: string | null;
}

export interface SesionAbierta {
  token: string;
  expiresAt?: string;
  rememberMe?: boolean;
  user: {
    userId?: string | number;
    name: string;
    role: 'admin' | 'cliente' | 'employee';
    canAccessAdmin?: boolean;
    privileges?: Record<string, boolean>;
    isEmployee?: boolean;
    mode?: 'cliente' | 'socio' | null; // paquete B
  };
}

export interface RespuestaOk {
  ok: boolean;
  message: string;
}
