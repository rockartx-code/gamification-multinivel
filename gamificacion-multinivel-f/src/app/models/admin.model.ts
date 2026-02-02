export interface AdminOrder {
  id: string;
  createdAt?: string;
  customer: string;
  grossSubtotal?: number;
  discountRate?: number;
  discountAmount?: number;
  netTotal?: number;
  total: number;
  status: 'pending' | 'paid' | 'shipped' | 'delivered';
  shippingType?: 'carrier' | 'personal';
  trackingNumber?: string;
  deliveryPlace?: string;
  deliveryDate?: string;
  recipientName?: string;
  phone?: string;
  address?: string;
  postalCode?: string;
  state?: string;
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
  recipientName?: string;
  phone?: string;
  address?: string;
  postalCode?: string;
  state?: string;
}

export interface UpdateOrderStatusPayload {
  status: AdminOrder['status'];
  shippingType?: AdminOrder['shippingType'];
  trackingNumber?: string;
  deliveryPlace?: string;
  deliveryDate?: string;
}

export interface CustomerProfile {
  id: number;
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
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
  assetId?: string;
  assetKey?: string;
  section: 'redes' | 'landing' | 'miniatura';
  filename?: string;
  contentType?: string;
}

export interface SaveAdminProductPayload {
  id: number | null;
  productId?: number;
  name: string;
  price: number;
  active: boolean;
  sku?: string;
  hook?: string;
  tags?: string[];
  images?: Array<{
    section: CreateProductAssetPayload['section'];
    url: string;
    assetId?: string;
  }>;
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

export interface ProductOfMonthPayload {
  productId: number;
}

export interface ProductOfMonthResponse {
  productOfMonth: {
    productId: number;
    createdAt?: string;
    updatedAt?: string;
  } | null;
}

export interface CreateAssetPayload {
  name: string;
  contentBase64: string;
  contentType?: string;
}

export interface AssetResponse {
  asset: {
    assetId: string;
    name?: string;
    contentType?: string;
    url?: string;
    createdAt?: string;
    updatedAt?: string;
  };
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
  sku?: string;
  hook?: string;
  tags?: string[];
  images?: Array<{
    section: CreateProductAssetPayload['section'];
    url: string;
    assetId?: string;
  }>;
}

export interface AdminWarning {
  type: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
}

export interface CommissionsPaidSummary {
  monthKey: string;
  count: number;
  total: number;
  rows: Array<{
    beneficiaryId: number | string;
    beneficiaryName: string;
    orderId?: string;
    amount: number;
    createdAt?: string;
  }>;
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
  commissionsPaidSummary?: CommissionsPaidSummary;
}
