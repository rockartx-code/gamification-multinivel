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
  status: 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled' | 'refunded' | 'en_devolucion' | 'devuelto_validado' | 'devolucion_rechazada';
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
  paymentMethod?: 'cash' | 'card' | 'transfer';
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
  cancelReason?: string;
  cancelledAt?: string;
  /** Ahorro que habría tenido como socia (solo en modo cliente e invitado). */ // paquete B
  partnerMode?: 'cliente' | 'socio' | 'invitado';
  partnerSavings?: number; // paquete B
  partnerSavingsRate?: number; // paquete B
  partnerSavingsNextRate?: number; // paquete B
  partnerSavingsNextMissing?: number; // paquete B
  /** Envío cobrado al cliente y paquetería cotizada. */
  shippingCost?: number;
  shippingCarrier?: string;
  /** Envío de regreso que el cliente declaró en su devolución. */
  returnShippingCost?: number;
  refundAmount?: number;
  refundReason?: string;
  /** Notas internas del back office; solo se añaden. */
  adminNotes?: Array<{ text: string; by: string; byName?: string; at: string }>;
  returnRequestId?: string;
  returnInspection?: {
    requestId: string;
    status?: string;
    motivo?: string;
    descripcion?: string;
    evidence?: string[];
    inspectedAt?: string;
    inspectedBy?: string;
    notes?: string;
    packageImageUrls?: string[];
    checklist?: Record<string, boolean>;
    // paquete G: líneas devueltas y reembolso sugerido por líneas
    motivoLabel?: string;
    lines?: Array<{ productId: number | string; name: string; quantity: number; purchasedQuantity?: number; unitPrice?: number; unitNet?: number }>;
    partial?: boolean;
    shippingResponsibility?: 'empresa' | 'cliente';
    returnShippingCost?: number;
    refundSuggested?: number | null;
    refundBreakdown?: { products: number | null; returnShipping: number | null; originalShipping: number | null } | null;
    refundPolicy?: { method: string; businessDays: string } | null;
    linesReceived?: Array<{ productId: number | string; quantity: number; matches: boolean }>;
    courtesyCoupon?: string | null;
  };
  rejectionReason?: string;
  rejectedAt?: string;
  refundReceiptUrl?: string;
  refundedAt?: string;
  // paquete C · factura ("Quiero factura" en el checkout; sin timbrado)
  invoiceRequested?: boolean;
  invoiceStatus?: 'no_aplica' | 'solicitada' | 'emitida';
  invoiceData?: { rfc: string; razonSocial: string; regimenFiscal: string; cpFiscal: string; usoCfdi: string; email: string };
  invoiceRequestedAt?: string;
  invoiceIssuedAt?: string;
  invoiceFolio?: string;
  invoiceFileUrl?: string;
  // paquete D · despacho y paquetería
  shippedAt?: string;
  shippedBy?: string;
  deliveredBy?: string;
  deliverySignedBy?: string;
  // paquete G
  returnedLines?: Array<{ productId: number | string; name: string; quantity: number; unitNet?: number }>;
  refundSuggested?: number;
  refundAdjustmentReason?: string;
  /** Pago que acreditó el pedido y por qué camino llegó. */ // paquete H
  paymentId?: string;
  paidVia?: 'mercadopago' | 'branch' | 'admin' | 'reconciliation';
  subscriptionId?: string;
}

export interface AdminRefundPayload {
  reason?: string;
  /** Importe reembolsado; por omisión el total más el envío de regreso declarado. */
  amount?: number;
  receiptBase64?: string;
  receiptName?: string;
  receiptContentType?: string;
  /** paquete G: obligatorio cuando `amount` difiere del reembolso sugerido por líneas. */
  adjustmentReason?: string;
}

export interface AdminRefundResponse {
  orderId: string;
  status: string;
  refundReceiptUrl?: string;
  // paquete G
  refundAmount?: number;
  refundSuggested?: number;
  breakdown?: { products: number | null; returnShipping: number | null; originalShipping: number | null };
  refundAdjustmentReason?: string | null;
  refundPolicy?: { method: string; businessDays: string };
  refundedAt?: string;
  message?: string;
}

export interface AdminReturnInspectPayload {
  inspection: {
    empaque_original: boolean;
    sellos_intactos: boolean;
    sin_uso: boolean;
    producto_abierto: boolean;
    danio_no_empresa: boolean;
    coincide_con_pedido: boolean;
    trazabilidad_valida: boolean;
  };
  packageImages?: Array<{ contentBase64: string; fileName: string; contentType: string }>;
  rejectionReason?: string;
  notes?: string;
  courtesyPercent?: number;
  /** paquete G: por línea devuelta, si lo recibido coincide con lo declarado. */
  lines?: Array<{ productId: number | string; quantity: number; matches: boolean }>;
}

export interface AdminReturnInspectResponse {
  ok: boolean;
  requestId: string;
  returnStatus: string;
  orderStatus: string;
  approved: boolean;
  // paquete G
  refundSuggested?: number | null;
  refundBreakdown?: { products: number | null; returnShipping: number | null; originalShipping: number | null } | null;
  linesReceived?: Array<{ productId: number | string; quantity: number; matches: boolean }>;
  message?: string;
}

export interface CustomerOrdersPage {
  orders: AdminOrder[];
  pageSize: number;
  count: number;
  nextToken?: string | null;
  hasMore: boolean;
  source?: string;
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
  vp?: number;
  currentDiscount?: { rate: number; min: number; max: number | null } | null;
  nextGoal?: { min: number; rate: number; label: string } | null;
  commissionLevels?: CommissionLevel[];
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
  shippingCarrier?: string;
  deliveryPlace?: string;
  deliveryDate?: string;
  stockId?: string;
  paymentMethod?: 'cash' | 'card' | 'transfer';
  cashReceived?: number;
  attendantUserId?: number | null;
  dispatchLines?: Array<{ productId: number; quantity: number }>;
}

export interface CustomerDocument {
  id: string;
  assetId?: string;
  docType?: string;
  name: string;
  type: string;
  url?: string;
  uploadedAt?: string;
}

export interface LinkCustomerDocumentPayload {
  assetId?: string;
  name?: string;
  contentBase64?: string;
  contentType?: string;
  fileName?: string;
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
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  leaderId?: number | null;
}

export interface CreateProductAssetPayload {
  productId: string | number;
  section: 'redes' | 'landing' | 'miniatura' | 'variante';
  contentBase64?: string;
  fileName?: string;
  contentType?: string;
  assetId?: string;
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
  vpPoints?: number;
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
    url?: string;
    bucket?: string;
    key?: string;
    ownerType?: string;
    ownerId?: string;
    section?: string;
    contentType?: string;
    createdAt?: string;
    updatedAt?: string;
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
  /** Teléfono de contacto: el backend lo guarda desde el alta, pero el
   *  back office no lo mostraba y nadie podía escribirle al cliente. */
  phone?: string;
  isSuperUser?: boolean;
  leaderId?: number | null;
  level: string;
  discount: string;
  commissions: number;
  commissionsPrevMonth?: number;
  commissionsPrevMonthKey?: string;
  commissionsCurrentPending?: number;
  commissionsCurrentConfirmed?: number;
  commissionsPrevStatus?: 'no_moves' | 'pending' | 'paid' | 'sin_clabe'; // paquete A
  commissionsPrevReceiptUrl?: string;
  clabeInterbancaria?: string;
  bankInstitution?: string;
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
  lastPurchaseAt?: string;
  documents?: CustomerDocument[];
  /** Seguimiento: el cliente pidió no ser contactado (o fue dado de baja). */
  doNotContact?: boolean;
  /** Bitácora de contactos; solo se añade. */
  contactNotes?: CustomerContactNote[];
  /** De dónde llegó: anuncio, red social, referido, orgánico… */
  origin?: string;
  /** Fecha de baja de datos (ARCO); la ficha queda anonimizada. */
  deletedAt?: string;
  /** Modo de la cuenta: cliente (precio de lista, sin red) o socio. */ // paquete B
  mode?: 'cliente' | 'socio';
  modeActivatedAt?: string; // paquete B
  /** Por dónde prefiere que le escriban: whatsapp | email | none. */ // paquete F
  contactPreference?: string; // paquete F
  /** Empleada que la atiende (EMPLOYEE); vacío = cartera FindingU. */ // paquete F
  executiveId?: string; // paquete F
  /** Última nota de contacto registrada. */ // paquete F
  lastContactAt?: string; // paquete F
}

export interface CustomerContactNote {
  text: string;
  by: string;
  at: string;
  /** whatsapp | email | call, cuando la nota la dejó "Seguimiento de hoy". */ // paquete F
  channel?: string; // paquete F
  templateKey?: string; // paquete F
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
  /** Puntos VP fijos por unidad vendida. Si es null, se calcula desde el precio. */
  vpPoints?: number;
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
  /** Mes (reloj del servidor) al que lleva "Ir a resolver" en los avisos de comisiones. */
  monthKey?: string;
}

export interface Coupon {
  code: string;
  type: 'percent' | 'fixed';
  value: number;
  active: boolean;
  minSubtotal?: number;
  maxRedemptions?: number | null;
  redemptions?: number;
  validFrom?: string | null;
  validTo?: string | null;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface SaveCouponPayload {
  code: string;
  type: 'percent' | 'fixed';
  value: number;
  active: boolean;
  minSubtotal?: number;
  maxRedemptions?: number | null;
  validFrom?: string | null;
  validTo?: string | null;
  description?: string;
}

export interface CouponValidation {
  valid: boolean;
  message: string;
  discount: number;
  code: string;
  type?: string;
  value?: number;
}

export interface CommissionLevel {
  /** Número de generación (1..5). Plan abril 2026. */
  gen?: number;
  rate: number;
  /** Requisitos de desbloqueo de la generación (Plan abril 2026 §4). */
  reqActiveDirects?: number;
  reqPersonalPC?: number;
  reqLines?: number;
  reqPCPerLine?: number;
  /** Campos legados (configuraciones anteriores). Mantener para compatibilidad. */
  minActiveUsers?: number;
  minIndividualPurchase?: number;
  minGroupPurchase?: number;
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
  /** Correo de acceso; si la ficha no tenía, el backend crea el acceso y avisa. */
  email?: string;
  doNotContact?: boolean;
  /** Nota nueva para la bitácora de contactos. */
  note?: string;
  origin?: string;
  contactPreference?: 'whatsapp' | 'email' | 'none'; // paquete F
  executiveId?: string; // paquete F
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
  // paquete C · recoger en sucursal solo si hay sucursal en tu ciudad/estado
  city?: string;
  state?: string;
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
  /** Nombre del empleado guardado con el movimiento (almacén no puede listar empleados). */
  userName?: string;
  paymentMethod?: 'cash' | 'card' | 'transfer';
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
  paymentStatus: 'paid_branch' | 'partial_branch' | 'credit_branch';
  deliveryStatus: 'paid_branch' | 'delivered_branch';
  paymentMethod?: 'cash' | 'card' | 'transfer';
  grossSubtotal?: number;
  discountRate?: number;
  discountAmount?: number;
  total: number;
  lines: AdminOrderItem[];
  createdAt?: string;
  cashCutId?: string;
  paymentType?: 'full' | 'partial' | 'credit';
  amountPaid?: number;
  pendingAmount?: number;
  cashierDiscountMode?: 'percent' | 'amount';
  cashierDiscountAmount?: number;
  /** 'voided' cuando la venta fue anulada (inventario devuelto, pedido cancelado). */
  status?: string;
  voidReason?: string;
  voidedAt?: string;
  // paquete E: pago mixto
  payments?: Array<{ method: 'cash' | 'card' | 'transfer'; amount: number }>;
  cashPortion?: number;
  change?: number | null;
}

export interface PosCashControl {
  stockId: string;
  attendantUserId?: number | null;
  currentTotal: number;
  salesCount: number;
  cashToKeepSuggested?: number;
  startedAt?: string;
  lastCutAt?: string;
  lastCutTotal?: number;
  lastCutSalesCount?: number;
  lastCutCashToKeep?: number;
  lastCutWithdrawnAmount?: number;
  lastSaleAt?: string;
  withdrawalCount?: number;
  totalWithdrawn?: number;
}

export interface PosCashCut {
  id: string;
  stockId: string;
  attendantUserId?: number | null;
  total: number;
  salesCount: number;
  cashToKeep?: number;
  withdrawnAmount?: number;
  startedAt?: string;
  endedAt?: string;
  createdAt?: string;
  sales?: PosSale[];
  withdrawals?: PosWithdrawal[];
  totalWithdrawals?: number;
  // paquete E: arqueo
  cashExpected?: number;
  cashCounted?: number;
  difference?: number;
  differenceReason?: string;
  withdrawalReceiver?: string;
  openingCash?: number;
}

export interface PosWithdrawal {
  id: string;
  stockId: string;
  attendantUserId?: number | null;
  amount: number;
  reason: string;
  createdAt?: string;
  // paquete E
  receiver?: string;
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
  /** Lo que el cliente pagó por regresar el paquete; se suma al reembolso. */
  returnShippingCost?: number;
  /** paquete G: líneas que se devuelven; sin el campo, todo el pedido. */
  lines?: Array<{ productId: number | string; quantity: number }>;
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
  /** VG mínimo (en puntos VP/PC) para alcanzar este rango */
  vgMin: number;
  /** PC personal mínimo (Plan abril 2026 §6). */
  vpMin?: number;
  /** Líneas activas requeridas. */
  minLines?: number;
  /** PC mínimos por línea calificada. */
  pcMinPerLine?: number;
  /** Líderes del rango inferior requeridos en la red. */
  requiredLeaders?: number;
  requiredLeaderRank?: string;
  /** Bono mensual del rango (desde el 4º mes consecutivo). */
  monthlyBonus?: number;
  /** Bono anual si mantiene el rango 12 meses. */
  annualBonus?: number;
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

// --- ESTADÍSTICAS MENSUALES ---

export interface MonthlyProductSale {
  productId: string;
  name: string;
  units: number;
  revenue: number;
}

export interface MonthlyTopCustomer {
  customerId: string;
  orders: number;
  total: number;
}

export interface MonthlyStockSummary {
  stockId: string;
  name: string;
  location: string;
  totalProducts: number;
  totalValue: number;
}

export interface MonthlyStatsResult {
  month: string;
  orders: {
    count: number;
    total: number;
    avgTicket: number;
    byStatus: Record<string, number>;
    byPaymentMethod: Record<string, number>;
    activeCustomers: string[];
    activeCustomerCount: number;
    topCustomers: MonthlyTopCustomer[];
  };
  products: {
    sales: MonthlyProductSale[];
    totalUnitsSold: number;
  };
  customers: {
    newCount: number;
    activeCount: number;
    repurchaseRate: number;
  };
  pos: {
    count: number;
    total: number;
  };
  stocks: {
    summary: MonthlyStockSummary[];
    movements: Record<string, unknown>[];
    movementsByType: Record<string, number>;
  };
}
