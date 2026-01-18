export interface AdminOrder {
  id: string;
  customer: string;
  total: number;
  status: 'pending' | 'paid' | 'delivered';
}

export interface AdminCustomer {
  id: number;
  name: string;
  email: string;
  level: string;
  discount: string;
  commissions: number;
}

export interface AdminProduct {
  id: number;
  name: string;
  price: number;
  active: boolean;
}

export interface AdminWarning {
  type: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
}

export interface AdminAssetSlot {
  label: string;
  hint: string;
}

export interface AdminData {
  orders: AdminOrder[];
  customers: AdminCustomer[];
  products: AdminProduct[];
  warnings: AdminWarning[];
  assetSlots: AdminAssetSlot[];
}
