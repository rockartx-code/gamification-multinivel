import { PortalNotification } from './portal-notification.model';
import { BonusAward, CustomerShippingAddress, ProductCategory, ProductVariant } from './admin.model';

export interface DashboardCustomerProfile {
  id?: string;
  name?: string;
  referralCode?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  addresses: CustomerShippingAddress[];
  defaultAddressId?: string;
  shippingAddresses: CustomerShippingAddress[];
  defaultShippingAddressId?: string;
}

export interface HonorEntry {
  customerId: string;
  name: string;
  vp: number;
  vg: number;
  rank?: string;
  position: number;
  prevPosition?: number;
}

export interface HonorBoard {
  monthKey: string;
  byVg: HonorEntry[];
  byVp: HonorEntry[];
}

export interface DashboardGoal {
  key: string;
  title: string;
  subtitle: string;
  target: number;
  base: number;
  cart: number;
  ctaText: string;
  ctaFragment: string;
  isCountGoal?: boolean;
  achieved?: boolean;
  locked?: boolean;
  /** Unidad de medida para mostrar el progreso */
  unit?: 'mxn' | 'vp' | 'count';
  /** Rango de red al que corresponde esta meta (ORO, PLATINO, DIAMANTE…) */
  rank?: string;
  /** ID de la regla de bono asociada (si aplica) */
  bonusRuleId?: string;
}

export interface DashboardProduct {
  id: string;
  name: string;
  price: number;
  badge: string;
  img: string;
  /** Puntos Comisionables (PC) oficiales que aporta el producto a los logros. */
  vpPoints?: number;
  images?: Array<{ section: string; url: string; assetId?: string }>;
  description?: string;
  copyFacebook?: string;
  copyInstagram?: string;
  copyWhatsapp?: string;
  tags?: string[];
  hook?: string;
  weightKg?: number;
  lengthCm?: number;
  widthCm?: number;
  heightCm?: number;
  variants?: ProductVariant[];
  categoryIds?: string[];
  inOnlineStore?: boolean;
  inPOS?: boolean;
  commissionable?: boolean;
}

export interface NetworkMember {
  name: string;
  level: string;
  spend: number;
  status: 'Activa' | 'En progreso' | 'Inactiva';
  id?: string;
  leaderId?: string;
}

export interface SponsorContact {
  name: string;
  email: string;
  phone: string;
  isDefault?: boolean;
  /** Sin patrocinadora: la ejecutiva asignada o la de la cartera por defecto. */ // paquete F
  isCoach?: boolean; // paquete F
  /** "Tu coach en Finding'U" */ // paquete F
  coachTitle?: string; // paquete F
  /** Enlace wa.me listo para abrir. */ // paquete F
  whatsapp?: string; // paquete F
}

export interface FeaturedItem {
  id: string;
  label: string;
  hook: string;
  story: string;
  feed: string;
  banner: string;
  campaignType?: 'multinivel' | 'producto';
}

export interface DashboardCampaign {
  id: string;
  name: string;
  active?: boolean;
  type?: 'multinivel' | 'producto';
  hook: string;
  description?: string;
  story: string;
  feed: string;
  banner: string;
  heroImage?: string;
  heroBadge?: string;
  heroTitle?: string;
  heroAccent?: string;
  heroTail?: string;
  heroDescription?: string;
  ctaPrimaryText?: string;
  ctaSecondaryText?: string;
  benefits?: string[];
}

export interface DashboardSettings {
  cutoffDay: number;
  /** Neto a partir del cual el envío es gratis; 0 o ausente = sin regla. */
  freeShippingMin?: number;
  cutoffHour: number;
  cutoffMinute: number;
  userCode: string;
  networkGoal: number;
  // ── Paquete G · ronda 26 · propuesta 29 ──
  /** Instante absoluto del próximo corte, del servidor. Manda sobre cutoffDay. */
  cutoffAt?: string;
  /** Reloj del servidor al responder; con él se corrige la deriva del navegador. */
  serverNow?: string;
  /** De qué es el corte, con todas sus letras. */
  cutoffLabel?: string;
}

export interface UserDashboardData {
  /** Consumo propio del mes en pesos (nodo raíz de la red). */
  myNetSpend?: number;
  settings: DashboardSettings;
  goals: DashboardGoal[];
  products: DashboardProduct[];
  featured: FeaturedItem[];
  campaigns?: DashboardCampaign[];
  notifications?: PortalNotification[];
  customer?: DashboardCustomerProfile | null;
  user?: {
    level?: string;
    discountPercent?: number;
    discountActive?: boolean;
  };
  sponsor?: SponsorContact | null;
  isGuest?: boolean;
  productOfMonth?: {
    id: string;
    name: string;
    price: number;
    badge: string;
    img: string;
    hook: string;
    description?: string;
    copyFacebook?: string;
    copyInstagram?: string;
    copyWhatsapp?: string;
    images?: Array<{ section: string; url: string; assetId?: string }>;
    tags?: string[];
  } | null;
  networkMembers: NetworkMember[];
  buyAgainIds: string[];
  categories?: ProductCategory[];
  honorBoard?: HonorBoard;
  /** Volumen Personal del mes en puntos VP */
  vp?: number;
  /** Volumen de Grupo del mes en puntos VP (red hasta nivel 5) */
  vg?: number;
  /** Rango actual calculado (ORO, PLATINO, DIAMANTE…) */
  rank?: string;
  /** Bonos otorgados o pendientes este mes */
  bonuses?: BonusAward[];
  commissions?: {
    monthKey: string;
    pendingTotal: number;
    paidTotal: number;
    blockedTotal?: number;
    monthTotal?: number;
    ledger?: Array<{
      createdAt?: string;
      amount?: number;
      orderId?: string;
      level?: number;
      rate?: number;
      sourceBuyerId?: number;
      buyerType?: string;
      rowId?: string;
      status?: string;
      // ── Paquete A · ronda 26 ──
      /** Fecha del pedido que generó la comisión: la que la socia reconoce (32). */
      orderCreatedAt?: string;
      recalculatedAt?: string;
      recalculatedReason?: string;
      /** Base y tasa con las que se calculó el importe, para poder explicarlo (37). */
      commissionRate?: number;
      commissionBaseNet?: number;
      voidReason?: string;
    }>;
    hasPending: boolean;
    hasConfirmed?: boolean;
    clabeOnFile?: boolean;
    clabeLast4?: string;
    receiptUrl?: string;
    prevReceiptUrl?: string;
    prevStatus?: 'no_moves' | 'pending' | 'paid';
    payoutDay?: number;
    // ── Paquete A · ronda 26 ──
    /** Banco de la CLABE registrada, para reconocer la cuenta (1). */
    bankInstitution?: string;
  } | null;
  /** Modo de la cuenta e indicadores del cliente (paquete B). */
  mode?: 'cliente' | 'socio';
  modeActivatedAt?: string | null; // paquete B
  clientIndicators?: import('./plan-socio.model').IndicadoresCliente | null; // paquete B
}

/** Respuesta de GET /catalog */
export interface CatalogData {
  products: DashboardProduct[];
  productOfMonth: UserDashboardData['productOfMonth'];
  featured?: FeaturedItem[];
  campaigns?: DashboardCampaign[];
  categories?: ProductCategory[];
  config?: {
    vpConfig?: { mxnPerVp: number; maxNetworkLevels: number };
    rankThresholds?: Array<{ rank: string; vg: number }>;
    discountTiers?: Array<{ min: number; max?: number; rate: number }>;
  };
}

/** Respuesta de GET /dashboard (sin datos de catálogo) */
export interface DashboardData {
  /** Consumo propio del mes en pesos, tal como lo devuelve la API. */
  myNetSpend?: number;
  isGuest?: boolean;
  settings: DashboardSettings;
  customer?: DashboardCustomerProfile | null;
  user?: UserDashboardData['user'];
  sponsor?: SponsorContact | null;
  goals: DashboardGoal[];
  featured?: FeaturedItem[];
  campaigns?: DashboardCampaign[];
  networkMembers: NetworkMember[];
  buyAgainIds: string[];
  commissions: UserDashboardData['commissions'];
  notifications?: import('./portal-notification.model').PortalNotification[];
  vp?: number;
  vg?: number;
  rank?: string;
  bonuses?: BonusAward[];
  /** Modo de la cuenta e indicadores del cliente (paquete B). */
  mode?: 'cliente' | 'socio';
  modeActivatedAt?: string | null; // paquete B
  clientIndicators?: import('./plan-socio.model').IndicadoresCliente | null; // paquete B
}

export interface CommissionRequestPayload {
  customerId: number;
  clabe: string;
  monthKey?: string;
}

export interface CommissionReceiptPayload {
  customerId: number;
  name: string;
  contentBase64: string;
  contentType?: string;
  monthKey?: string;
}

export interface CustomerClabePayload {
  customerId: number;
  clabe: string;
  bankInstitution?: string;
}
