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
  status: 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled' | 'en_devolucion' | 'devuelto_validado' | 'devolucion_rechazada';
  shippingType?: 'carrier' | 'personal';
  trackingNumber?: string;
  deliveryPlace?: string;
  deliveryDate?: string;
  recipientName?: string;
  phone?: string;
  street?: string;
  number?: string;
  address?: string;
  city?: string;
  postalCode?: string;
  state?: string;
  country?: string;
  betweenStreets?: string;
  references?: string;
  deliveryNotes?: string;
  items?: AdminOrderItem[];
  stockId?: string;
  attendantUserId?: number | null;
  paymentStatus?: string;
  paymentTransactionId?: string;
  paymentRawStatus?: string;
  paymentWebhookAt?: string;
  paymentProvider?: string;
  paymentPreferenceId?: string;
  paymentInitPoint?: string;
  paymentSandboxInitPoint?: string;
  markedByWebhook?: boolean;
  discountCutoffWindow?: boolean;
  discountCutoffCountdown?: string;
  discountCutoffMessage?: string;
  deliveryStatus?: string;
  shippingAddressId?: string;
  shippingAddressLabel?: string;
  deliveryType?: 'pickup' | 'delivery';
  pickupStockId?: string;
  pickupPaymentMethod?: 'online' | 'at_store';
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
  street?: string;
  number?: string;
  address: string;
  city?: string;
  postalCode: string;
  state: string;
  country?: string;
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
  street?: string;
  number?: string;
  address?: string;
  city?: string;
  postalCode?: string;
  state?: string;
  country?: string;
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
  street?: string;
  number?: string;
  address?: string;
  city?: string;
  postalCode?: string;
  state?: string;
  country?: string;
  betweenStreets?: string;
  references?: string;
  deliveryNotes?: string;
  shippingAddressId?: string;
  shippingAddressLabel?: string;
  saveShippingAddress?: boolean;
  deliveryType?: 'pickup' | 'delivery';
  pickupStockId?: string;
  pickupPaymentMethod?: 'online' | 'at_store';
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
  assetId?: string;
  name: string;
  type: string;
  url?: string;
  uploadedAt?: string;
}

export interface LinkCustomerDocumentPayload {
  assetId: string;
  name?: string;
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
  bankInstitution?: string;
  documents?: CustomerDocument[];
  ownDocuments?: CustomerDocument[];
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
  inOnlineStore?: boolean;
  inPOS?: boolean;
  commissionable?: boolean;
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
  bankInstitution?: string;
  documents?: CustomerDocument[];
}

export interface CustomerDocumentTypeConfig {
  key: string;
  label: string;
  required?: boolean;
}

export interface CustomerOwnDocumentPayload {
  userId: string;
  docType: string;
  docLabel: string;
  contentBase64: string;
  contentType: string;
  fileName: string;
}

export interface ProductVariant {
  id: string;
  name: string;
  price?: number;
  sku?: string;
  active?: boolean;
  /** URL de imagen específica para esta variante */
  img?: string;
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
  inOnlineStore?: boolean;
  inPOS?: boolean;
  commissionable?: boolean;
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
  customerDocumentTypes?: CustomerDocumentTypeConfig[];
  bonuses?: BonusConfig;
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
  name?: string;
  recipientName?: string;
  phone?: string;
  street?: string;
  number?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postalCode?: string;
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

export type OrderReturnMotivo = 'DANADO_DEFECTUOSO' | 'ERROR_ENVIO' | 'DESISTIMIENTO';
export type OrderReturnStatus = 'PENDIENTE' | 'EN_DEVOLUCION' | 'DEVUELTO_VALIDADO' | 'DEVOLUCION_RECHAZADA';

export interface OrderReturnEvidenceFile {
  contentBase64: string;
  contentType: string;
  fileName: string;
}

export interface OrderReturnEvidencePayload {
  fotos_producto: OrderReturnEvidenceFile[];
  fotos_empaque: OrderReturnEvidenceFile[];
  fotos_guia_envio: OrderReturnEvidenceFile[];
}

export interface OrderReturnRequestPayload {
  motivo: OrderReturnMotivo;
  descripcion?: string;
  evidence: OrderReturnEvidencePayload;
}

export interface OrderReturnRequestResponse {
  ok: boolean;
  requestId: string;
  status: OrderReturnStatus;
  shippingResponsibility: 'empresa' | 'cliente';
  message?: string;
}

export interface OrderCancelResponse {
  ok: boolean;
  orderId: string;
  status: string;
  pendingRefund: boolean;
}

// ─── BONUS / VP-VG SYSTEM ─────────────────────────────────────────────────────

/** Tipos de condición que puede evaluar una regla de bono. */
export type BonusConditionType =
  | 'vg_min'             // VG del cliente >= value VP
  | 'vp_min'             // VP personal >= value VP
  | 'direct_vg_min'      // Suma de VG de referidos directos >= value VP
  | 'consecutive_months' // Rango mantenido N meses consecutivos
  | 'direct_rank_count'  // N referidos directos con un rango dado
  | 'first_30_days'      // Cliente se registró hace ≤ 30 días
  | 'first_time';        // Primera vez que se alcanza este bono

/** Tipos de recompensa que puede otorgar un bono. */
export type BonusRewardType = 'cash_mxn' | 'item' | 'monthly_cash' | 'annual_fund_pct';

export interface BonusCondition {
  type: BonusConditionType;
  /** Umbral numérico (VP, meses, conteo…) */
  value?: number;
  /** Para direct_rank_count: rango requerido en los referidos */
  rank?: string;
}

export interface BonusReward {
  type: BonusRewardType;
  /** MXN para cash_mxn / monthly_cash */
  amount?: number;
  /** Descripción del artículo físico (p. ej. "Smart TV") */
  itemLabel?: string;
  /** Porcentaje para annual_fund_pct */
  pct?: number;
  /** Mes consecutivo específico que dispara este premio (p. ej. 2 ó 3) */
  triggerMonths?: number;
}

export interface BonusRule {
  id: string;
  name: string;
  active: boolean;
  /** Rango de la red al que aplica (ORO, PLATINO, DIAMANTE…) */
  rank?: string;
  conditions: BonusCondition[];
  rewards: BonusReward[];
  /** Con qué frecuencia puede otorgarse: 'once' | 'monthly' | 'annual' */
  cooldown?: 'once' | 'monthly' | 'annual';
  notes?: string;
}

export interface RankThreshold {
  rank: string;
  /** VG mínimo (en puntos VP) para alcanzar este rango */
  vgMin: number;
}

export interface VpConfig {
  /** MXN netos (sin IVA ni envío) equivalentes a 1 VP. Default: 50 */
  mxnPerVp: number;
  /** Niveles de red que se suman al VG. Default: 5 */
  maxNetworkLevels: number;
}

export interface BonusConfig {
  vpConfig: VpConfig;
  rankThresholds: RankThreshold[];
  rules: BonusRule[];
}

export interface BonusAward {
  id: string;
  ruleId: string;
  ruleName: string;
  customerId: number | string;
  monthKey: string;
  rewardType: BonusRewardType;
  rewardAmount?: number;
  rewardItemLabel?: string;
  rewardPct?: number;
  status: 'pending' | 'paid' | 'cancelled';
  createdAt?: string;
}
