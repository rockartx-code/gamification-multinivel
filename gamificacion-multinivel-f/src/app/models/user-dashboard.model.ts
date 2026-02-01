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
}

export interface NetworkMember {
  name: string;
  level: string;
  spend: number;
  status: 'Activa' | 'En progreso' | 'Inactiva';
}

export interface FeaturedItem {
  id: string;
  label: string;
  hook: string;
  story: string;
  feed: string;
  banner: string;
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
  isGuest?: boolean;
  productOfMonth?: {
    id: string;
    name: string;
    price: number;
    badge: string;
    img: string;
    hook: string;
    images?: Array<{ section: string; url: string; assetId?: string }>;
    tags?: string[];
  } | null;
  networkMembers: NetworkMember[];
  buyAgainIds: string[];
  commissions?: {
    monthKey: string;
    pendingTotal: number;
    paidTotal: number;
    hasPending: boolean;
    clabeOnFile?: boolean;
    clabeLast4?: string;
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
