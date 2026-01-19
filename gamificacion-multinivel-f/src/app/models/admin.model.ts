export interface AdminOrder {
  id: string;
  customer: string;
  total: number;
  status: 'pending' | 'paid' | 'delivered';
}

export interface AdminOrderItem {
  productId: number;
  name: string;
  price: number;
  quantity: number;
}

export interface CreateAdminOrderPayload {
  customerId: number;
  customerName: string;
  status: AdminOrder['status'];
  items: AdminOrderItem[];
}

export interface CreateStructureCustomerPayload {
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  leaderId?: number | null;
  level: 'Oro' | 'Plata' | 'Bronce';
}

export interface CreateProductAssetPayload {
  productId: string;
  section: 'redes' | 'landing' | 'miniatura';
  filename: string;
  contentType?: string;
}

export interface SaveAdminProductPayload {
  id: number | null;
  name: string;
  price: number;
  active: boolean;
  sku?: string;
  hook?: string;
}

export interface ProductAssetUpload {
  asset: {
    assetId: string;
    bucket: string;
    key: string;
    ownerType: string;
    ownerId: string;
    section: string;
    contentType: string;
    createdAt: string;
    updatedAt: string;
  };
  uploadUrl?: string;
}

export interface AdminCustomer {
  id: number;
  name: string;
  email: string;
  leaderId?: number | null;
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
