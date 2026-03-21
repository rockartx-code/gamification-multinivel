import { UserPrivileges } from './privileges.model';
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
  shippingAddressId?: string;
  shippingAddressLabel?: string;
  saveShippingAddress?: boolean;
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

export interface CustomerProfile {
  id: number | string;
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  addresses?: CustomerShippingAddress[];
  defaultAddressId?: string;
  shippingAddresses?: CustomerShippingAddress[];
  defaultShippingAddressId?: string;
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
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
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

export interface RewardsConfig {
  version: string;
  activationNetMin: number;
  discountTiers: Array<{ min: number; max: number | null; rate: number }>;
  commissionByDepth: { '1': number; '2': number; '3': number };
  payoutDay: number;
  cutRule: string;
}

export interface BusinessConfigPaymentsConfig {
  mercadoLibre: {
    enabled: boolean;
    accessToken: string;
    checkoutPreferencesUrl: string;
    paymentInfoUrlTemplate: string;
    notificationUrl: string;
    successUrl: string;
    failureUrl: string;
    pendingUrl: string;
    currencyId: string;
    webhookSecret: string;
  };
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
  payments: BusinessConfigPaymentsConfig;
  adminWarnings: {
    showCommissions: boolean;
    showShipping: boolean;
    showPendingPayments: boolean;
    showPendingTransfers: boolean;
    showPosSalesToday: boolean;
  };
}

export interface AdminAssetSlot {
  label: string;
  hint: string;
}

export interface AdminData {
  orders: AdminOrder[];
  customers: AdminCustomer[];
  products: AdminProduct[];
  campaigns?: AdminCampaign[];
  notifications?: PortalNotification[];
  businessConfig?: AppBusinessConfig;
  warnings: AdminWarning[];
  assetSlots: AdminAssetSlot[];
  productOfMonthId?: number | null;
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
