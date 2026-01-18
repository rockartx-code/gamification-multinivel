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
  networkMembers: NetworkMember[];
  buyAgainIds: string[];
}
