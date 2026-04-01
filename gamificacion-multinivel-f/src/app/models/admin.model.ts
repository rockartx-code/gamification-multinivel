import { UserPrivileges } from './privileges.model';
import { AdminEmployee } from './employee.model';
import { PortalNotification, SavePortalNotificationPayload } from './portal-notification.model';

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
  betweenStreets?: string;
  references?: string;
  items?: AdminOrderItem[];
  stockId?: string;
  attendantUserId?: number | null;
  paymentStatus?: string;
  paymentTransactionId?: string;
  paymentRawStatus?: string;
  paymentProvider?: string;
  paymentPreferenceId?: string;
  paymentInitPoint?: string;
  paymentSandboxInitPoint?: string;
  deliveryStatus?: string;
  shippingAddressId?: string;
  shippingAddressLabel?: string;
  deliveryType?: 'pickup' | 'delivery';
  pickupStockId?: string;
}

export interface OrderStatusLookup {
  orderId: string;
  status: string;
  paymentStatus?: string;
  paymentTransactionId?: string;
  paymentRawStatus?: string;
  paymentWebhookAt?: string;
  markedByWebhook?: boolean;
  discountCutoffWindow?: boolean;
  discountCutoffCountdown?: string;
  discountCutoffMessage?: string;
}

export interface AssociateMonth {
  associateId: string;
  monthKey: string;
  netVolume: number;
  isActive: boolean;
}

export interface AdminOrderItem {
  productId: number;
  name: string;
  price: number;
  quantity: number;
}

export interface CustomerShippingAddress {
  id: string;
  label: string;
  recipientName?: string;
  phone?: string;
  address: string;
  postalCode: string;
  state: string;
  betweenStreets?: string;
  references?: string;
  isDefault?: boolean;
}

export interface OrderShippingAddressPayload {
  id?: string;
  addressId?: string;
  label?: string;
  recipientName?: string;
  phone?: string;
  address?: string;
  postalCode?: string;
  state?: string;
  betweenStreets?: string;
  references?: string;
  isDefault?: boolean;
}

export interface CreateAdminOrderPayload {
  customerId: number | string;
  customerName: string;
  status: AdminOrder['status'];
  items: AdminOrderItem[];
  shippingAddress?: OrderShippingAddressPayload;
  recipientName?: string;
  phone?: string;
  address?: string;
  postalCode?: string;
  state?: string;
  betweenStreets?: string;
  references?: string;
  shippingAddressId?: string;
  shippingAddressLabel?: string;
  saveShippingAddress?: boolean;
  deliveryType?: 'pickup' | 'delivery';
  pickupStockId?: string;
}

export interface UpdateOrderStatusPayload {
  status: AdminOrder['status'];
  shippingType?: AdminOrder['shippingType'];
  trackingNumber?: string;
  deliveryPlace?: string;
  deliveryDate?: string;
  stockId?: string;
  dispatchLines?: Array<{ productId: number; quantity: number }>;
}

export interface CustomerDocument {
  id: string;
  name: string;
  type: string;
  url?: string;
  uploadedAt?: string;
}

export interface CustomerProfile {
  id: number | string;
  name: string;
  email: string;
  phone?: string;
  rfc?: string;
  curp?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  clabeInterbancaria?: string;
  clabeLast4?: string;
  documents?: CustomerDocument[];
  addresses?: CustomerShippingAddress[];
  defaultAddressId?: string;
  shippingAddresses?: CustomerShippingAddress[];
  defaultShippingAddressId?: string;
}

export interface UpdateProfilePayload {
  name?: string;
  phone?: string;
  rfc?: string;
  curp?: string;
}

export interface CreateStructureCustomerPayload {
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  leaderId?: number | null;
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
  isSuperUser?: boolean;
  leaderId?: number | null;
  level: string;
  discount: string;
  commissions: number;
  commissionsPrevMonth?: number;
  commissionsPrevMonthKey?: string;
  commissionsCurrentPending?: number;
  commissionsCurrentConfirmed?: number;
  commissionsPrevStatus?: 'no_moves' | 'pending' | 'paid';
  commissionsPrevReceiptUrl?: string;
  clabeInterbancaria?: string;
}

export interface ProductVariant {
  id: string;
  name: string;
  price?: number;
  sku?: string;
  active?: boolean;
}

export interface ProductCategory {
  id: string;
  name: string;
  parentId?: string | null;
  position?: number;
  active?: boolean;
  createdAt?: string;
}

export interface AdminProduct {
  id: number;
  name: string;
  price: number;
  active: boolean;
  sku?: string;
  hook?: string;
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
  images?: Array<{
    section: CreateProductAssetPayload['section'];
    url: string;
    assetId?: string;
  }>;
}

export interface AdminCampaign {
  id: string;
  name: string;
  active: boolean;
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
  createdAt?: string;
  updatedAt?: string;
}

export interface AdminWarning {
  type: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
}

export interface CommissionLevel {
  rate: number;
  minActiveUsers: number;
  minIndividualPurchase: number;
  minGroupPurchase: number;
}

export interface RewardsConfig {
  version: string;
  activationNetMin: number;
  discountTiers: Array<{ min: number; max: number | null; rate: number }>;
  commissionLevels: CommissionLevel[];
  payoutDay: number;
  cutRule: string;
}

export interface AppBusinessConfig {
  version: string;
  rewards: RewardsConfig;
  orders: {
    requireStockOnShipped: boolean;
    requireDispatchLinesOnShipped: boolean;
  };
  pos: {
    defaultCustomerName: string;
    defaultPaymentStatus: string;
    defaultDeliveryStatus: string;
    orderStatusByDeliveryStatus: {
      delivered_branch: string;
      paid_branch: string;
    };
  };
  stocks: {
    requireLinkedUserForTransferReceive: boolean;
  };
  adminWarnings: {
    showCommissions: boolean;
    showShipping: boolean;
    showPendingPayments: boolean;
    showPendingTransfers: boolean;
    showPosSalesToday: boolean;
  };
  shipping: {
    enabled: boolean;
    markup: number;
    carriers: string[];
  };
}

export interface AdminAssetSlot {
  label: string;
  hint: string;
}

export interface AdminData {
  orders: AdminOrder[];
  customers: AdminCustomer[];
  employees?: AdminEmployee[];
  products: AdminProduct[];
  campaigns?: AdminCampaign[];
  notifications?: PortalNotification[];
  businessConfig?: AppBusinessConfig;
  warnings: AdminWarning[];
  assetSlots: AdminAssetSlot[];
  productOfMonthId?: number | null;
  categories?: ProductCategory[];
}

export interface UpdateCustomerPrivilegesPayload {
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
}

export interface UpdateCustomerPayload {
  leaderId?: number | null;
  level?: string;
}

export interface SaveAdminCampaignPayload {
  id?: string;
  name: string;
  active: boolean;
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

export interface AdminStock {
  id: string;
  name: string;
  location: string;
  postalCode?: string;
  isMainWarehouse?: boolean;
  allowPickup?: boolean;
  linkedUserIds: number[];
  inventory: Record<number, number> | Record<string, number>;
  createdAt?: string;
  updatedAt?: string;
}

export interface StockTransferLine {
  productId: number;
  qty: number;
}

export interface StockTransfer {
  id: string;
  sourceStockId: string;
  destinationStockId: string;
  lines: StockTransferLine[];
  status: 'pending' | 'received';
  createdByUserId?: number | null;
  receivedByUserId?: number | null;
  createdAt?: string;
  receivedAt?: string;
}

export interface InventoryMovement {
  id: string;
  type: 'entry' | 'exit_order' | 'exit_transfer' | 'entry_transfer' | 'damaged' | 'pos_sale';
  stockId: string;
  productId: number;
  qty: number;
  userId?: number | null;
  reason?: string;
  referenceId?: string;
  createdAt?: string;
}

export interface PosSale {
  id: string;
  orderId: string;
  stockId: string;
  attendantUserId?: number | null;
  customerId?: number | null;
  customerName: string;
  paymentStatus: 'paid_branch';
  deliveryStatus: 'delivered_branch';
  grossSubtotal?: number;
  discountRate?: number;
  discountAmount?: number;
  total: number;
  lines: AdminOrderItem[];
  createdAt?: string;
}

export interface PosCashControl {
  stockId: string;
  attendantUserId?: number | null;
  currentTotal: number;
  salesCount: number;
  startedAt?: string;
  lastCutAt?: string;
  lastCutTotal?: number;
  lastCutSalesCount?: number;
  lastSaleAt?: string;
}

export interface PosCashCut {
  id: string;
  stockId: string;
  attendantUserId?: number | null;
  total: number;
  salesCount: number;
  startedAt?: string;
  endedAt?: string;
  createdAt?: string;
}

export interface UpdateBusinessConfigPayload {
  config: AppBusinessConfig;
}

export type SaveAdminNotificationPayload = SavePortalNotificationPayload;

export interface SaveProductCategoryPayload {
  id?: string;
  name: string;
  parentId?: string | null;
  position?: number;
  active?: boolean;
}

export interface ShippingQuoteItem {
  weightKg: number;
  lengthCm: number;
  widthCm: number;
  heightCm: number;
  quantity: number;
}

export interface ShippingQuoteRequest {
  zipTo: string;
  items?: ShippingQuoteItem[];
  /** @deprecated — kept for backward compat; prefer items[] */
  weightKg?: number;
  /** @deprecated */
  lengthCm?: number;
  /** @deprecated */
  widthCm?: number;
  /** @deprecated */
  heightCm?: number;
}

export interface ShippingRate {
  carrier: string | null;
  service: string | null;
  price: number | null;
  displayPrice: number;
  currency: string | null;
  transitDays: number | null;
  deliveryEstimate?: string | null;
}
