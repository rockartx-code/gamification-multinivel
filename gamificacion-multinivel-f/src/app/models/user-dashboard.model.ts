import { PortalNotification } from './portal-notification.model';
import { ProductVariant } from './admin.model';

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
}

export interface DashboardProduct {
  id: string;
  name: string;
  price: number;
  badge: string;
  img: string;
  description?: string;
  copyFacebook?: string;
  copyInstagram?: string;
  copyWhatsapp?: string;
  tags?: string[];
  weightKg?: number;
  lengthCm?: number;
  widthCm?: number;
  heightCm?: number;
  variants?: ProductVariant[];
  categoryIds?: string[];
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
  cutoffHour: number;
  cutoffMinute: number;
  userCode: string;
  networkGoal: number;
}

export interface UserDashboardData {
  settings: DashboardSettings;
  goals: DashboardGoal[];
  products: DashboardProduct[];
  featured: FeaturedItem[];
  campaigns?: DashboardCampaign[];
  notifications?: PortalNotification[];
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
    }>;
    hasPending: boolean;
    hasConfirmed?: boolean;
    clabeOnFile?: boolean;
    clabeLast4?: string;
    receiptUrl?: string;
    prevReceiptUrl?: string;
    prevStatus?: 'no_moves' | 'pending' | 'paid';
    payoutDay?: number;
  } | null;
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
}
