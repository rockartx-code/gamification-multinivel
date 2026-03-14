import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, type Signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, forkJoin, map, of, switchMap } from 'rxjs';

import { AuthService, AuthUser } from '../../services/auth.service';
import {
  AdminCustomer,
  AdminData,
  AdminCampaign,
  AppBusinessConfig,
  AdminOrder,
  AdminOrderItem,
  AssociateMonth,
  AdminProduct,
  AdminWarning,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload
} from '../../models/admin.model';
import { PortalNotification } from '../../models/portal-notification.model';
import { AdminViewId, AppPrivilege, normalizePrivileges, UserPrivileges } from '../../models/privileges.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';
import { UiKpiCardComponent } from '../../components/ui-kpi-card/ui-kpi-card.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { SidebarLink, UiSidebarNavComponent } from '../../components/ui-sidebar-nav/ui-sidebar-nav.component';
import { UiStatusBadgeComponent } from '../../components/ui-status-badge/ui-status-badge.component';
import { UiDataTableComponent } from '../../components/ui-data-table/ui-data-table.component';
import { UiNetworkGraphComponent } from '../../components/ui-networkgraph/ui-networkgraph.component';
import { AdminControlService } from '../../services/admin-control.service';
import { AdminCampaignsComponent } from './admin-campaigns/admin-campaigns.component';

type StructureNode = {
  id: string;
  role: 'root' | 'L1' | 'L2' | 'L3';
  label: string;
  x: number;
  y: number;
  meta?: Record<string, unknown>;
};

type StructureLink = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

type AdminStock = {
  id: string;
  name: string;
  location: string;
  linkedUserIds: number[];
  inventory: Record<number, number>;
};

type StockTransferLine = {
  productId: number;
  qty: number;
};

type StockTransfer = {
  id: string;
  sourceStockId: string;
  destinationStockId: string;
  lines: StockTransferLine[];
  status: 'pending' | 'received';
  createdAt: string;
  createdByUserId: number | null;
  receivedAt?: string;
  receivedByUserId?: number | null;
};

type StockDamage = {
  id: string;
  stockId: string;
  productId: number;
  qty: number;
  reason: string;
  createdAt: string;
  reportedByUserId: number | null;
};

type PosSale = {
  id: string;
  orderId: string;
  stockId: string;
  attendantUserId: number | null;
  customerId: number | null;
  customerName: string;
  grossSubtotal: number;
  discountRate: number;
  discountAmount: number;
  total: number;
  paymentStatus: 'paid_branch';
  deliveryStatus: 'delivered_branch';
  createdAt: string;
  lines: AdminOrderItem[];
};

type PosCashControl = {
  stockId: string;
  attendantUserId: number | null;
  currentTotal: number;
  salesCount: number;
  startedAt?: string;
  lastCutAt?: string;
  lastCutTotal?: number;
  lastCutSalesCount?: number;
  lastSaleAt?: string;
};

type InventoryMovementType = 'entry' | 'exit_order' | 'exit_transfer' | 'entry_transfer' | 'damaged' | 'pos_sale';

type InventoryMovement = {
  id: string;
  type: InventoryMovementType;
  stockId: string;
  productId: number;
  qty: number;
  createdAt: string;
  userId: number | null;
  reason?: string;
  referenceId?: string;
};

type CustomerPrivilegeOption = {
  key: AppPrivilege;
  label: string;
};

type SelectOption<T extends string | number> = {
  value: T;
  label: string;
};

type ExplainedSelectOption<T extends string | number> = SelectOption<T> & {
  description: string;
};

type PosCustomerRecommendation = {
  id: number;
  name: string;
  email: string;
  label: string;
};

type DiscountTierDraft = AppBusinessConfig['rewards']['discountTiers'][number];

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent, UiModalComponent, UiKpiCardComponent, UiHeaderComponent, UiFooterComponent, UiSidebarNavComponent, UiStatusBadgeComponent, UiDataTableComponent, UiNetworkGraphComponent, AdminCampaignsComponent],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  private readonly adminData: Signal<AdminData | null>;
  private adminNavLinksCache: { user: AuthUser | null; links: SidebarLink[] } | null = null;
  private customerOptionsCache: { customersRef: AdminCustomer[]; options: Array<SelectOption<number>> } | null = null;
  private stockOptionsCache: { stocksRef: AdminStock[]; options: Array<SelectOption<string>> } | null = null;
  private productOptionsCache: { productsRef: AdminProduct[]; options: Array<SelectOption<number>> } | null = null;
  private filteredOrdersCache: { ordersRef: AdminOrder[]; status: AdminOrder['status']; rows: AdminOrder[] } | null = null;
  private structureGraphCache:
    | {
        selectedCustomerId: number | null;
        customersRef: AdminCustomer[];
        graph: { nodes: StructureNode[]; links: StructureLink[] };
      }
    | null = null;
  private stockInventoryRowsCache:
    | {
        selectedStockId: string;
        stockRef: AdminStock | null;
        productsRef: AdminProduct[];
        rows: Array<{ productId: number; productName: string; qty: number }>;
      }
    | null = null;
  private stockTransferRowsCache:
    | {
        transfersRef: StockTransfer[];
        stocksRef: AdminStock[];
        productsRef: AdminProduct[];
        rows: Array<StockTransfer & { sourceName: string; destinationName: string; productSummary: string }>;
      }
    | null = null;
  private inventoryMovementRowsCache:
    | {
        movementsRef: InventoryMovement[];
        stocksRef: AdminStock[];
        productsRef: AdminProduct[];
        customersRef: AdminCustomer[];
        rows: Array<
          InventoryMovement & { stockName: string; productName: string; userName: string; typeLabel: string; signedQty: number }
        >;
      }
    | null = null;
  private warningsCache: { warningsRef: AdminWarning[]; warnings: AdminWarning[] } | null = null;
  private readonly orderStatusOptionsValue: Array<SelectOption<AdminOrder['status']>> = [
    { value: 'pending', label: 'Pendiente' },
    { value: 'paid', label: 'Pagado' },
    { value: 'shipped', label: 'Enviado' },
    { value: 'delivered', label: 'Entregado' }
  ];
  readonly rewardCutRuleOptions: Array<ExplainedSelectOption<string>> = [
    {
      value: 'hard_cut_no_pass',
      label: 'Corte estricto mensual',
      description: 'El descuento se calcula dentro del mes actual y no se arrastra al siguiente periodo.'
    }
  ];
  readonly posPaymentStatusConfigOptions: Array<ExplainedSelectOption<string>> = [
    {
      value: 'paid_branch',
      label: 'Pagado en sucursal',
      description: 'La venta POS se registra como cobrada al momento de capturarla en caja.'
    }
  ];
  readonly posDeliveryStatusConfigOptions: Array<ExplainedSelectOption<string>> = [
    {
      value: 'delivered_branch',
      label: 'Entregado en sucursal',
      description: 'La venta POS se considera entregada en el punto de venta.'
    },
    {
      value: 'paid_branch',
      label: 'Solo pagado en sucursal',
      description: 'La venta POS queda cobrada, pero la orden no se marca como entregada automaticamente.'
    }
  ];
  readonly posOrderStatusMappingConfigOptions: Array<ExplainedSelectOption<string>> = [
    {
      value: 'pending',
      label: 'Pendiente',
      description: 'Crea la orden sin pago confirmado.'
    },
    {
      value: 'paid',
      label: 'Pagado',
      description: 'Marca la orden como pagada, pendiente de entrega o envio.'
    },
    {
      value: 'shipped',
      label: 'Enviado',
      description: 'Marca la orden como enviada.'
    },
    {
      value: 'delivered',
      label: 'Entregado',
      description: 'Marca la orden como completada y entregada.'
    },
    {
      value: 'canceled',
      label: 'Cancelado',
      description: 'Marca la orden como cancelada.'
    },
    {
      value: 'refunded',
      label: 'Reembolsado',
      description: 'Marca la orden como reembolsada.'
    }
  ];
  readonly rewardCutRuleTooltip = this.buildSelectTooltip(this.rewardCutRuleOptions);
  readonly posPaymentStatusConfigTooltip = this.buildSelectTooltip(this.posPaymentStatusConfigOptions);
  readonly posDeliveryStatusConfigTooltip = this.buildSelectTooltip(this.posDeliveryStatusConfigOptions);
  readonly posOrderStatusMappingConfigTooltip = this.buildSelectTooltip(this.posOrderStatusMappingConfigOptions);

  constructor(
    private readonly adminControl: AdminControlService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.adminData = toSignal(this.adminControl.data$, { initialValue: null });
  }

  currentView: AdminViewId = 'orders';
  currentOrderStatus: AdminOrder['status'] = 'pending';
  isActionsModalOpen = false;
  isNewOrderModalOpen = false;
  isAddStructureModalOpen = false;
  isShippingModalOpen = false;
  isReceiptModalOpen = false;
  isUploadingReceipt = false;

  selectedCustomer: AdminCustomer | null = null;
  selectedCustomerAdminAccess = false;
  selectedCustomerPrivilegeDraft: UserPrivileges = {};
  selectedCustomerLeaderId = '';
  selectedCustomerSponsorSearch = '';
  selectedCustomerSponsorRecommendations: Array<{ id: string; name: string; email: string; label: string }> = [];
  selectedSponsorLabel = 'FindingU (sin patrocinador)';
  hasValidSelectedSponsorId = true;
  canSaveSelectedCustomerPosition = false;
  isSavingCustomerPrivileges = false;
  isSavingCustomerPosition = false;
  readonly customerPrivilegeOptions: CustomerPrivilegeOption[] = [
    { key: 'access_screen_orders', label: 'Acceso pantalla: Pedidos' },
    { key: 'access_screen_customers', label: 'Acceso pantalla: Clientes' },
    { key: 'access_screen_products', label: 'Acceso pantalla: Productos' },
    { key: 'access_screen_stocks', label: 'Acceso pantalla: Stocks' },
    { key: 'access_screen_pos', label: 'Acceso pantalla: Punto de Venta' },
    { key: 'access_screen_stats', label: 'Acceso pantalla: Estadisticas' },
    { key: 'access_screen_settings', label: 'Acceso pantalla: Configuracion' },
    { key: 'order_mark_paid', label: 'Cambiar orden a Pagado' },
    { key: 'order_mark_shipped', label: 'Cambiar orden a Enviado' },
    { key: 'order_mark_delivered', label: 'Cambiar orden a Entregado' },
    { key: 'order_create', label: 'Registrar nueva orden' },
    { key: 'customer_add', label: 'Agregar cliente' },
    { key: 'commissions_register_payment', label: 'Registrar pago de comisiones' },
    { key: 'product_add', label: 'Agregar nuevo producto' },
    { key: 'product_update', label: 'Actualizar producto' },
    { key: 'product_set_month', label: 'Establecer producto del mes' },
    { key: 'stock_create', label: 'Crear stock' },
    { key: 'stock_create_transfer', label: 'Crear transferencia' },
    { key: 'stock_add_inventory', label: 'Agregar inventario a stock' },
    { key: 'stock_mark_damaged', label: 'Marcar stock como danado' },
    { key: 'stock_receive_transfer', label: 'Registrar transferencia como entregada' },
    { key: 'pos_register_sale', label: 'Registrar venta' },
    { key: 'user_mark_admin', label: 'Marcar usuario como administrador' },
    { key: 'user_manage_privileges', label: 'Registrar privilegios' },
    { key: 'config_manage', label: 'Gestionar configuracion de negocio' }
  ];
  businessConfigDraft: AppBusinessConfig = this.getDefaultBusinessConfig();
  isSavingBusinessConfig = false;
  businessConfigMessage = '';
  structureForm = {
    name: '',
    phone: '',
    email: '',
    address: '',
    city: ''
  };
  structureLeader: AdminCustomer | null = null;
  structureLevel = 'L1';
  productImagePreviews = new Map<CreateProductAssetPayload['section'], string>();
  productImageUploads = new Map<CreateProductAssetPayload['section'], boolean>();
  productImageFiles = new Map<CreateProductAssetPayload['section'], File>();
  productMessage = '';
  private productMessageTimeout?: number;
  productForm = {
    id: null as number | null,
    name: '',
    price: '',
    sku: '',
    hook: '',
    description: '',
    copyFacebook: '',
    copyInstagram: '',
    copyWhatsapp: '',
    tags: ''
  };
  productExistingImages: AdminProduct['images'] = [];
  notificationMessage = '';
  isSavingNotification = false;
  notificationForm = this.getDefaultNotificationForm();
  productImageSlots = [
    { key: 'redes', label: 'Redes', hint: 'Story / Feed' },
    { key: 'landing', label: 'Landing', hint: 'Hero 16:9' },
    { key: 'miniatura', label: 'Miniatura', hint: '1:1' }
  ] as const;
  newOrderCustomerId: number | null = null;
  newOrderStatus: AdminOrder['status'] = 'pending';
  newOrderItems = new Map<number, number>();
  isSavingOrder = false;
  isSavingStructure = false;
  isSavingProduct = false;
  isSettingProductOfMonth = false;
  shippingTargetOrder: AdminOrder | null = null;
  shippingType: 'carrier' | 'personal' = 'carrier';
  shippingTrackingNumber = '';
  shippingDeliveryPlace = '';
  shippingDeliveryDate = '';
  shippingError = '';
  receiptFile: File | null = null;
  receiptError = '';
  receiptTargetCustomer: AdminCustomer | null = null;
  private readonly updatingOrderIds = new Set<string>();

  stocks: AdminStock[] = [];
  selectedStockId = '';
  stockForm = {
    name: '',
    location: ''
  };
  stockUserLinkDraft = new Set<number>();
  isStockEntryModalOpen = false;
  isStockDamageModalOpen = false;
  stockEntryForm = {
    stockId: '',
    productId: null as number | null,
    qty: 1,
    note: '',
    createdByUserId: null as number | null
  };
  stockTransferForm = {
    sourceStockId: '',
    destinationStockId: '',
    lines: [{ productId: null as number | null, qty: 1 }],
    createdByUserId: null as number | null
  };
  stockDamageForm = {
    stockId: '',
    productId: null as number | null,
    qty: 1,
    reason: '',
    reportedByUserId: null as number | null
  };
  transferReceiverUserId: number | null = null;
  transfers: StockTransfer[] = [];
  stockDamages: StockDamage[] = [];
  inventoryMovements: InventoryMovement[] = [];
  stockFeedbackMessage = '';
  stockFeedbackTone: 'error' | 'success' | '' = '';

  shippingStockId = '';
  shippingFallbackProductId: number | null = null;
  shippingFallbackQty = 1;

  posForm = {
    stockId: '',
    status: 'delivered' as 'paid' | 'delivered'
  };
  posItems = new Map<number, number>();
  posSales: PosSale[] = [];
  posCashControl: PosCashControl | null = null;
  posCustomerSearch = 'Publico en General';
  selectedPosCustomerId: number | null = null;
  posCustomerRecommendations: PosCustomerRecommendation[] = [];
  posSelectedCustomerMonth: AssociateMonth | null = null;
  isLoadingPosCustomerProjection = false;
  isRegisteringPosSale = false;
  isCuttingPosCash = false;
  posFeedbackMessage = '';
  posFeedbackTone: 'error' | 'success' | '' = '';

  ngOnInit(): void {
    this.currentView = this.getFirstAllowedView();
    this.adminControl.load().subscribe(() => {
      if (!this.selectedCustomer) {
        this.selectedCustomer = this.customers[0] ?? null;
      }
      this.syncSelectedCustomerAccessDraft();
      this.ensureCurrentViewAllowed();
      if (!this.newOrderCustomerId) {
        this.newOrderCustomerId = this.customers[0]?.id ?? null;
      }
      this.stockEntryForm.createdByUserId = this.stockEntryForm.createdByUserId ?? this.customers[0]?.id ?? null;
      this.stockTransferForm.createdByUserId = this.stockTransferForm.createdByUserId ?? this.customers[0]?.id ?? null;
      this.stockDamageForm.reportedByUserId = this.stockDamageForm.reportedByUserId ?? this.customers[0]?.id ?? null;
      this.transferReceiverUserId = this.transferReceiverUserId ?? this.customers[0]?.id ?? null;
      this.selectPublicGeneralCustomer();
      this.syncBusinessConfigDraft();
      this.loadStocksAndPosState();
    });
  }

  get orders(): AdminOrder[] {
    return this.adminData()?.orders ?? [];
  }

  get customers(): AdminCustomer[] {
    return this.adminData()?.customers ?? [];
  }

  get products(): AdminProduct[] {
    return this.adminData()?.products ?? [];
  }

  get campaigns(): AdminCampaign[] {
    return this.adminData()?.campaigns ?? [];
  }

  get notifications(): PortalNotification[] {
    return this.adminData()?.notifications ?? [];
  }

  get activeNotificationsCount(): number {
    return this.notifications.filter((item) => item.status === 'active').length;
  }

  get scheduledNotificationsCount(): number {
    return this.notifications.filter((item) => item.status === 'scheduled').length;
  }

  get inactiveNotificationsCount(): number {
    return this.notifications.filter((item) => item.status === 'expired' || item.status === 'inactive').length;
  }

  get productOfMonthId(): number | null {
    return this.adminData()?.productOfMonthId ?? null;
  }

  get customerOptions(): { value: number; label: string }[] {
    return this.customers.map((customer) => ({
      value: customer.id,
      label: `${customer.name} Â· ${customer.email}`
    }));
  }

  get orderStatusOptions(): { value: AdminOrder['status']; label: string }[] {
    return [
      { value: 'pending', label: 'Pendiente' },
      { value: 'paid', label: 'Pagado' },
      { value: 'shipped', label: 'Enviado' },
      { value: 'delivered', label: 'Entregado' }
    ];
  }

  get productOfMonthName(): string {
    const pid = this.productOfMonthId;
    if (pid == null) {
      return '-';
    }
    return this.products.find((product) => product.id === pid)?.name ?? '-';
  }

  get warnings(): AdminWarning[] {
    return this.adminData()?.warnings ?? [];
  }

  get selectedCustomerSponsorName(): string {
    if (this.selectedCustomer?.leaderId == null) {
      return 'FindingU';
    }
    return this.customers.find((customer) => customer.id === this.selectedCustomer?.leaderId)?.name ?? `Usuario ${this.selectedCustomer.leaderId}`;
  }

  get businessConfig(): AppBusinessConfig | null {
    return this.adminData()?.businessConfig ?? null;
  }


  get adminNavLinks(): SidebarLink[] {
    const links: Array<SidebarLink & { view: AdminViewId }> = [
      { id: 'orders', view: 'orders', icon: 'fa-receipt', label: 'Pedidos', subtitle: '' },
      { id: 'customers', view: 'customers', icon: 'fa-users', label: 'Clientes', subtitle: '' },
      { id: 'products', view: 'products', icon: 'fa-boxes-stacked', label: 'Productos', subtitle: '' },
      { id: 'stocks', view: 'stocks', icon: 'fa-warehouse', label: 'Stocks', subtitle: '' },
      { id: 'campaigns', view: 'campaigns', icon: 'fa-bullhorn', label: 'Campanas', subtitle: '' },
      { id: 'pos', view: 'pos', icon: 'fa-cash-register', label: 'Punto de Venta', subtitle: '' },
      { id: 'stats', view: 'stats', icon: 'fa-chart-line', label: 'Estadisticas', subtitle: '' },
      { id: 'notifications', view: 'notifications', icon: 'fa-bell', label: 'Notificaciones', subtitle: '' },
      { id: 'settings', view: 'settings', icon: 'fa-sliders', label: 'Configuracion', subtitle: '' }
    ];
    return links.filter((link) => this.canAccessView(link.view)).map(({ view, ...link }) => link);
  }

  get customerOptionsStable(): Array<SelectOption<number>> {
    if (this.customerOptionsCache?.customersRef === this.customers) {
      return this.customerOptionsCache.options;
    }
    const options = this.customers.map((customer) => ({
      value: customer.id,
      label: `${customer.name} · ${customer.email}`
    }));
    this.customerOptionsCache = { customersRef: this.customers, options };
    return options;
  }

  get orderStatusOptionsStable(): Array<SelectOption<AdminOrder['status']>> {
    return this.orderStatusOptionsValue;
  }

  get warningsStable(): AdminWarning[] {
    const warnings = this.adminData()?.warnings ?? [];
    if (this.warningsCache?.warningsRef === warnings) {
      return this.warningsCache.warnings;
    }
    this.warningsCache = { warningsRef: warnings, warnings };
    return warnings;
  }

  get adminNavLinksStable(): SidebarLink[] {
    if (this.adminNavLinksCache?.user === this.currentUser) {
      return this.adminNavLinksCache.links;
    }
    const links: Array<SidebarLink & { view: AdminViewId }> = [
      { id: 'orders', view: 'orders', icon: 'fa-receipt', label: 'Pedidos', subtitle: '' },
      { id: 'customers', view: 'customers', icon: 'fa-users', label: 'Clientes', subtitle: '' },
      { id: 'products', view: 'products', icon: 'fa-boxes-stacked', label: 'Productos', subtitle: '' },
      { id: 'stocks', view: 'stocks', icon: 'fa-warehouse', label: 'Stocks', subtitle: '' },
      { id: 'campaigns', view: 'campaigns', icon: 'fa-bullhorn', label: 'Campanas', subtitle: '' },
      { id: 'pos', view: 'pos', icon: 'fa-cash-register', label: 'Punto de Venta', subtitle: '' },
      { id: 'stats', view: 'stats', icon: 'fa-chart-line', label: 'Estadisticas', subtitle: '' },
      { id: 'notifications', view: 'notifications', icon: 'fa-bell', label: 'Notificaciones', subtitle: '' },
      { id: 'settings', view: 'settings', icon: 'fa-sliders', label: 'Configuracion', subtitle: '' }
    ];
    const resolved = links.filter((link) => this.canAccessView(link.view)).map(({ view, ...link }) => link);
    this.adminNavLinksCache = { user: this.currentUser, links: resolved };
    return resolved;
  }

  get viewTitle(): string {
    if (this.currentView === 'customers') {
      return 'Clientes';
    }
    if (this.currentView === 'products') {
      return 'Productos';
    }
    if (this.currentView === 'stocks') {
      return 'Stocks';
    }
    if (this.currentView === 'campaigns') {
      return 'Campanas';
    }
    if (this.currentView === 'pos') {
      return 'Punto de Venta';
    }
    if (this.currentView === 'stats') {
      return 'Estadisticas';
    }
    if (this.currentView === 'notifications') {
      return 'Notificaciones';
    }
    if (this.currentView === 'settings') {
      return 'Configuracion';
    }
    return 'Pedidos';
  }

  get viewSubtitle(): string {
    if (this.currentView === 'customers') {
      return 'Niveles, estructura y comisiones.';
    }
    if (this.currentView === 'products') {
      return 'Altas, imagenes y CTA.';
    }
    if (this.currentView === 'stocks') {
      return 'Inventario por sucursal, transferencias, recepciones y danos.';
    }
    if (this.currentView === 'campaigns') {
      return 'Campanas, assets y copy comercial para compartir con la red.';
    }
    if (this.currentView === 'pos') {
      return 'Ventas en sucursal vinculadas a stock y operador.';
    }
    if (this.currentView === 'stats') {
      return 'Ventas, funnel y alertas.';
    }
    if (this.currentView === 'notifications') {
      return 'Recordatorios, noticias y avisos programados para los usuarios.';
    }
    if (this.currentView === 'settings') {
      return 'Variables de negocio para reglas operativas.';
    }
    return 'Cambia estado: pendiente, pagado, enviado, entregado.';
  }

  get stockOptions(): { value: string; label: string }[] {
    return this.stocks.map((stock) => ({
      value: stock.id,
      label: `${stock.name} Â· ${stock.location}`
    }));
  }

  get selectedStock(): AdminStock | null {
    return this.stocks.find((stock) => stock.id === this.selectedStockId) ?? null;
  }

  get stockOptionsStable(): Array<SelectOption<string>> {
    if (this.stockOptionsCache?.stocksRef === this.stocks) {
      return this.stockOptionsCache.options;
    }
    const options = this.stocks.map((stock) => ({
      value: stock.id,
      label: `${stock.name} · ${stock.location}`
    }));
    this.stockOptionsCache = { stocksRef: this.stocks, options };
    return options;
  }

  get productOptionsStable(): Array<SelectOption<number>> {
    if (this.productOptionsCache?.productsRef === this.products) {
      return this.productOptionsCache.options;
    }
    const options = this.products.map((product) => ({
      value: product.id,
      label: `${product.name} · ${this.formatMoney(product.price)}`
    }));
    this.productOptionsCache = { productsRef: this.products, options };
    return options;
  }

  get stockInventoryRowsStable(): Array<{ productId: number; productName: string; qty: number }> {
    const stock = this.selectedStock;
    if (!stock) {
      return [];
    }
    if (
      this.stockInventoryRowsCache?.selectedStockId === this.selectedStockId &&
      this.stockInventoryRowsCache.stockRef === stock &&
      this.stockInventoryRowsCache.productsRef === this.products
    ) {
      return this.stockInventoryRowsCache.rows;
    }
    const rows = this.products.map((product) => ({
      productId: product.id,
      productName: product.name,
      qty: stock.inventory[product.id] ?? 0
    }));
    this.stockInventoryRowsCache = {
      selectedStockId: this.selectedStockId,
      stockRef: stock,
      productsRef: this.products,
      rows
    };
    return rows;
  }

  get stockTransferRowsStable(): Array<StockTransfer & { sourceName: string; destinationName: string; productSummary: string }> {
    if (
      this.stockTransferRowsCache?.transfersRef === this.transfers &&
      this.stockTransferRowsCache.stocksRef === this.stocks &&
      this.stockTransferRowsCache.productsRef === this.products
    ) {
      return this.stockTransferRowsCache.rows;
    }
    const rows = this.transfers.map((transfer) => ({
      ...transfer,
      sourceName: this.stockName(transfer.sourceStockId),
      destinationName: this.stockName(transfer.destinationStockId),
      productSummary: transfer.lines.map((line) => `${this.productName(line.productId)} x${line.qty}`).join(', ')
    }));
    this.stockTransferRowsCache = {
      transfersRef: this.transfers,
      stocksRef: this.stocks,
      productsRef: this.products,
      rows
    };
    return rows;
  }

  get inventoryMovementRowsStable(): Array<
    InventoryMovement & { stockName: string; productName: string; userName: string; typeLabel: string; signedQty: number }
  > {
    if (
      this.inventoryMovementRowsCache?.movementsRef === this.inventoryMovements &&
      this.inventoryMovementRowsCache.stocksRef === this.stocks &&
      this.inventoryMovementRowsCache.productsRef === this.products &&
      this.inventoryMovementRowsCache.customersRef === this.customers
    ) {
      return this.inventoryMovementRowsCache.rows;
    }
    const rows = this.inventoryMovements.map((movement) => ({
      ...movement,
      stockName: this.stockName(movement.stockId),
      productName: this.productName(movement.productId),
      userName: this.customerName(movement.userId),
      typeLabel: this.movementTypeLabel(movement.type),
      signedQty: this.movementSignedQty(movement)
    }));
    this.inventoryMovementRowsCache = {
      movementsRef: this.inventoryMovements,
      stocksRef: this.stocks,
      productsRef: this.products,
      customersRef: this.customers,
      rows
    };
    return rows;
  }

  get filteredOrdersStable(): AdminOrder[] {
    if (
      this.filteredOrdersCache?.ordersRef === this.orders &&
      this.filteredOrdersCache.status === this.currentOrderStatus
    ) {
      return this.filteredOrdersCache.rows;
    }
    const rows = this.orders.filter((order) => order.status === this.currentOrderStatus);
    this.filteredOrdersCache = { ordersRef: this.orders, status: this.currentOrderStatus, rows };
    return rows;
  }

  get productOptions(): { value: number; label: string }[] {
    return this.products.map((product) => ({
      value: product.id,
      label: `${product.name} · ${this.formatMoney(product.price)}`
    }));
  }

  get stockInventoryRows(): Array<{ productId: number; productName: string; qty: number }> {
    const stock = this.selectedStock;
    if (!stock) {
      return [];
    }
    return this.products.map((product) => ({
      productId: product.id,
      productName: product.name,
      qty: stock.inventory[product.id] ?? 0
    }));
  }

  get stockTransferRows(): Array<StockTransfer & { sourceName: string; destinationName: string; productSummary: string }> {
    return this.transfers.map((transfer) => ({
      ...transfer,
      sourceName: this.stockName(transfer.sourceStockId),
      destinationName: this.stockName(transfer.destinationStockId),
      productSummary: transfer.lines.map((line) => `${this.productName(line.productId)} x${line.qty}`).join(', ')
    }));
  }

  get inventoryMovementRows(): Array<
    InventoryMovement & { stockName: string; productName: string; userName: string; typeLabel: string; signedQty: number }
  > {
    return this.inventoryMovements.map((movement) => ({
      ...movement,
      stockName: this.stockName(movement.stockId),
      productName: this.productName(movement.productId),
      userName: this.customerName(movement.userId),
      typeLabel: this.movementTypeLabel(movement.type),
      signedQty: this.movementSignedQty(movement)
    }));
  }

  get currentOperatorId(): number | null {
    const raw = Number(this.currentUser?.userId ?? NaN);
    return Number.isFinite(raw) ? raw : null;
  }

  get currentOperatorName(): string {
    return this.currentUser?.name?.trim() || this.customerName(this.currentOperatorId);
  }

  get linkedPosStocks(): AdminStock[] {
    const operatorId = this.currentOperatorId;
    if (operatorId == null) {
      return [];
    }
    return this.stocks.filter((stock) => stock.linkedUserIds.includes(operatorId));
  }

  get hasLinkedPosStock(): boolean {
    return this.linkedPosStocks.length > 0;
  }

  get currentPosStock(): AdminStock | null {
    return this.linkedPosStocks.find((stock) => stock.id === this.posForm.stockId) ?? this.linkedPosStocks[0] ?? null;
  }

  get posStockOptions(): Array<SelectOption<string>> {
    return this.linkedPosStocks.map((stock) => ({
      value: stock.id,
      label: `${stock.name} · ${stock.location}`
    }));
  }

  get selectedPosCustomer(): AdminCustomer | null {
    return this.customers.find((customer) => customer.id === this.selectedPosCustomerId) ?? null;
  }

  get visiblePosSales(): PosSale[] {
    const stockId = this.currentPosStock?.id;
    const operatorId = this.currentOperatorId;
    return this.posSales.filter(
      (sale) => (!stockId || sale.stockId === stockId) && (operatorId == null || sale.attendantUserId === operatorId)
    );
  }

  get posSubtotal(): number {
    return this.getPosItems().reduce((acc, item) => acc + item.price * item.quantity, 0);
  }

  get pendingTransfersCount(): number {
    return this.transfers.filter((transfer) => transfer.status === 'pending').length;
  }

  get posSalesTotal(): number {
    return this.visiblePosSales.reduce((acc, sale) => acc + sale.total, 0);
  }

  get posCustomerMonthNet(): number {
    return Number(this.posSelectedCustomerMonth?.netVolume ?? 0) || 0;
  }

  get posProjectedMonthNet(): number {
    if (!this.selectedPosCustomer) {
      return 0;
    }
    return this.posCustomerMonthNet + this.posSubtotal;
  }

  get posProjectedDiscountRate(): number {
    const customer = this.selectedPosCustomer;
    if (!customer) {
      return 0;
    }
    return Math.max(this.parseCustomerDiscountRate(customer), this.calculateDiscountTierRate(this.posProjectedMonthNet));
  }

  get posProjectedDiscountAmount(): number {
    return this.roundMoney(this.posSubtotal * this.posProjectedDiscountRate);
  }

  get posProjectedNetTotal(): number {
    return this.roundMoney(this.posSubtotal - this.posProjectedDiscountAmount);
  }

  get posProjectedDiscountLabel(): string {
    return `${Math.round(this.posProjectedDiscountRate * 100)}%`;
  }

  get posCurrentDiscountLabel(): string {
    return this.selectedPosCustomer?.discount ?? '0%';
  }

  get posNextGoal(): { label: string; min: number } | null {
    const rewards = this.businessConfig?.rewards;
    if (!rewards || !this.selectedPosCustomer) {
      return null;
    }
    const milestones = [
      { min: Number(rewards.activationNetMin ?? 0), label: 'Activacion del mes' },
      ...((rewards.discountTiers ?? []).map((tier, index) => ({
        min: Number(tier.min ?? 0),
        label: `Nivel ${index + 1} de descuento`
      })) ?? [])
    ]
      .filter((goal) => Number.isFinite(goal.min) && goal.min > 0)
      .sort((left, right) => left.min - right.min)
      .filter((goal, index, source) => index === source.findIndex((entry) => entry.min === goal.min));
    return milestones.find((goal) => goal.min > this.posProjectedMonthNet) ?? null;
  }

  get posRemainingForNextGoal(): number {
    const nextGoal = this.posNextGoal;
    if (!nextGoal) {
      return 0;
    }
    return Math.max(0, this.roundMoney(nextGoal.min - this.posProjectedMonthNet));
  }

  get canRegisterPosSale(): boolean {
    return Boolean(
      this.hasPermission('pos_register_sale') &&
        this.hasLinkedPosStock &&
        this.currentPosStock &&
        this.posItems.size > 0 &&
        !this.isRegisteringPosSale
    );
  }

  get canCreatePosCashCut(): boolean {
    return Boolean(
      this.hasPermission('pos_register_sale') &&
        this.currentPosStock &&
        (this.posCashControl?.salesCount ?? 0) > 0 &&
        !this.isCuttingPosCash
    );
  }

  get filteredOrders(): AdminOrder[] {
    return this.orders.filter((order) => order.status === this.currentOrderStatus);
  }

  get pendingCount(): number {
    return this.orders.filter((order) => order.status === 'pending').length;
  }

  get paidCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get shipCount(): number {
    return this.orders.filter((order) => order.status === 'shipped').length;
  }

  get deliveredCount(): number {
    return this.orders.filter((order) => order.status === 'delivered').length;
  }


  get ordersCount(): number {
    return this.orders.length;
  }

  get ordersTotal(): number {
    return this.orders.reduce((acc, order) => acc + (order.total || 0), 0);
  }

  get pendingShippingCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get avgTicket(): number {
    return this.ordersCount ? this.ordersTotal / this.ordersCount : 0;
  }

  get conversionRate(): number {
    if (!this.ordersCount) {
      return 0;
    }
    return (this.deliveredCount / this.ordersCount) * 100;
  }

  get repurchaseRate(): number {
    const counts = this.orders.reduce<Record<string, number>>((acc, order) => {
      const key = (order.customer || '').trim() || 'Sin cliente';
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    const unique = Object.keys(counts).length;
    if (!unique) {
      return 0;
    }
    const repeaters = Object.values(counts).filter((count) => count >= 2).length;
    return (repeaters / unique) * 100;
  }

  get commissionsTotal(): number {
    return this.customers.reduce((acc, customer) => acc + customer.commissions, 0);
  }

  get customersCount(): number {
    return this.customers.length;
  }

  get productsCount(): number {
    return this.products.length;
  }

  get currentUser(): AuthUser | null {
    return this.authService.currentUser;
  }

  get canOpenUserDashboard(): boolean {
    return this.authService.hasAdminAndUserAccess(this.currentUser);
  }

  get notificationDescriptionLength(): number {
    return this.notificationForm.description.length;
  }

  get isNotificationFormValid(): boolean {
    return Boolean(
      this.notificationForm.title.trim() &&
        this.notificationForm.description.trim() &&
        this.notificationForm.startAt &&
        this.notificationForm.endAt &&
        this.notificationDescriptionLength <= 300 &&
        new Date(this.notificationForm.endAt).getTime() >= new Date(this.notificationForm.startAt).getTime()
    );
  }

  canAccessView(view: AdminViewId): boolean {
    return this.authService.canAccessAdminView(view, this.currentUser);
  }

  hasPermission(privilege: AppPrivilege): boolean {
    return this.authService.hasPrivilege(privilege, this.currentUser);
  }

  customerHasPrivilege(privilege: AppPrivilege): boolean {
    return this.selectedCustomerPrivilegeDraft?.[privilege] === true;
  }

  private getFirstAllowedView(): AdminViewId {
    const ordered: AdminViewId[] = ['orders', 'customers', 'products', 'stocks', 'campaigns', 'pos', 'stats', 'notifications', 'settings'];
    return ordered.find((view) => this.canAccessView(view)) ?? 'orders';
  }

  private ensureCurrentViewAllowed(): void {
    if (!this.canAccessView(this.currentView)) {
      this.currentView = this.getFirstAllowedView();
    }
  }

  get structureLeaderLabel(): string {
    if (!this.structureLeader) {
      return 'Sin lí­der asignado';
    }
    return this.structureLeader.name;
  }

  get structureRootLabel(): string {
    return this.structureNodeLabel(this.selectedCustomer?.name);
  }

  get structureGraph(): { nodes: StructureNode[]; links: StructureLink[] } {
    if (!this.selectedCustomer) {
      return { nodes: [], links: [] };
    }

    const monthlySpendByCustomer = this.getMonthlySpendByCustomerName();
    const referrals = this.buildReferralMap(this.customers);
    const directReferrals = referrals.get(this.selectedCustomer.id) ?? [];
    const indirectReferrals: Array<{ customer: AdminCustomer; parentId: number }> = [];
    const thirdReferrals: Array<{ customer: AdminCustomer; parentId: number }> = [];

    directReferrals.forEach((member) => {
      const children = referrals.get(member.id) ?? [];
      children.forEach((child) => {
        indirectReferrals.push({ customer: child, parentId: member.id });
      });
    });
    indirectReferrals.forEach((entry) => {
      const children = referrals.get(entry.customer.id) ?? [];
      children.forEach((child) => {
        thirdReferrals.push({ customer: child, parentId: entry.customer.id });
      });
    });

    const l1Positions = this.buildColumnPositions(directReferrals.length, 260);
    const l2Positions = this.buildColumnPositions(indirectReferrals.length, 420, 40, 180);
    const l3Positions = this.buildColumnPositions(thirdReferrals.length, 580, 40, 180);
    const rootY =
      l1Positions.length > 0
        ? (l1Positions[0].y + l1Positions[l1Positions.length - 1].y) / 2
        : l2Positions.length > 0
          ? (l2Positions[0].y + l2Positions[l2Positions.length - 1].y) / 2
          : l3Positions.length > 0
            ? (l3Positions[0].y + l3Positions[l3Positions.length - 1].y) / 2
            : 110;

    const root: StructureNode = {
      id: `customer-${this.selectedCustomer.id}`,
      role: 'root',
      label: this.structureRootLabel,
      x: 120,
      y: rootY,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(this.selectedCustomer.name)) ?? 0 }
    };

    const l1Customers = directReferrals.slice(0, l1Positions.length);
    const l1Nodes: StructureNode[] = l1Customers.map((customer, index) => ({
      id: `customer-${customer.id}`,
      role: 'L1',
      label: this.structureNodeLabel(customer.name),
      x: l1Positions[index].x,
      y: l1Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(customer.name)) ?? 0 }
    }));

    const l1NodeById = new Map(l1Customers.map((customer, index) => [customer.id, l1Nodes[index]]));
    const l2Entries = indirectReferrals
      .filter((entry) => l1NodeById.has(entry.parentId))
      .slice(0, l2Positions.length);
    const l2Nodes: StructureNode[] = l2Entries.map((entry, index) => ({
      id: `customer-${entry.customer.id}`,
      role: 'L2',
      label: this.structureNodeLabel(entry.customer.name),
      x: l2Positions[index].x,
      y: l2Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(entry.customer.name)) ?? 0 }
    }));
    const l2NodeById = new Map(l2Entries.map((entry, index) => [entry.customer.id, l2Nodes[index]]));
    const l3Entries = thirdReferrals
      .filter((entry) => l2NodeById.has(entry.parentId))
      .slice(0, l3Positions.length);
    const l3Nodes: StructureNode[] = l3Entries.map((entry, index) => ({
      id: `customer-${entry.customer.id}`,
      role: 'L3',
      label: this.structureNodeLabel(entry.customer.name),
      x: l3Positions[index].x,
      y: l3Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(entry.customer.name)) ?? 0 }
    }));

    const links: StructureLink[] = l1Nodes.map((node) => ({
      x1: root.x,
      y1: root.y,
      x2: node.x,
      y2: node.y
    }));

    l2Nodes.forEach((node, index) => {
      const entry = l2Entries[index];
      const parent = entry ? l1NodeById.get(entry.parentId) : undefined;
      if (!parent) {
        return;
      }
      links.push({
        x1: parent.x,
        y1: parent.y,
        x2: node.x,
        y2: node.y
      });
    });
    l3Nodes.forEach((node, index) => {
      const entry = l3Entries[index];
      const parent = entry ? l2NodeById.get(entry.parentId) : undefined;
      if (!parent) {
        return;
      }
      links.push({
        x1: parent.x,
        y1: parent.y,
        x2: node.x,
        y2: node.y
      });
    });

    return { nodes: [root, ...l1Nodes, ...l2Nodes, ...l3Nodes], links };
  }

  get structureGraphStable(): { nodes: StructureNode[]; links: StructureLink[] } {
    if (!this.selectedCustomer) {
      return { nodes: [], links: [] };
    }
    if (
      this.structureGraphCache?.selectedCustomerId === this.selectedCustomer.id &&
      this.structureGraphCache.customersRef === this.customers
    ) {
      return this.structureGraphCache.graph;
    }

    const monthlySpendByCustomer = this.getMonthlySpendByCustomerName();
    const referrals = this.buildReferralMap(this.customers);
    const directReferrals = referrals.get(this.selectedCustomer.id) ?? [];
    const indirectReferrals: Array<{ customer: AdminCustomer; parentId: number }> = [];
    const thirdReferrals: Array<{ customer: AdminCustomer; parentId: number }> = [];

    directReferrals.forEach((member) => {
      const children = referrals.get(member.id) ?? [];
      children.forEach((child) => {
        indirectReferrals.push({ customer: child, parentId: member.id });
      });
    });
    indirectReferrals.forEach((entry) => {
      const children = referrals.get(entry.customer.id) ?? [];
      children.forEach((child) => {
        thirdReferrals.push({ customer: child, parentId: entry.customer.id });
      });
    });

    const l1Positions = this.buildColumnPositions(directReferrals.length, 260);
    const l2Positions = this.buildColumnPositions(indirectReferrals.length, 420, 40, 180);
    const l3Positions = this.buildColumnPositions(thirdReferrals.length, 580, 40, 180);
    const rootY =
      l1Positions.length > 0
        ? (l1Positions[0].y + l1Positions[l1Positions.length - 1].y) / 2
        : l2Positions.length > 0
          ? (l2Positions[0].y + l2Positions[l2Positions.length - 1].y) / 2
          : l3Positions.length > 0
            ? (l3Positions[0].y + l3Positions[l3Positions.length - 1].y) / 2
            : 110;

    const root: StructureNode = {
      id: `customer-${this.selectedCustomer.id}`,
      role: 'root',
      label: this.structureRootLabel,
      x: 120,
      y: rootY,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(this.selectedCustomer.name)) ?? 0 }
    };

    const l1Customers = directReferrals.slice(0, l1Positions.length);
    const l1Nodes: StructureNode[] = l1Customers.map((customer, index) => ({
      id: `customer-${customer.id}`,
      role: 'L1',
      label: this.structureNodeLabel(customer.name),
      x: l1Positions[index].x,
      y: l1Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(customer.name)) ?? 0 }
    }));

    const l1NodeById = new Map(l1Customers.map((customer, index) => [customer.id, l1Nodes[index]]));
    const l2Entries = indirectReferrals
      .filter((entry) => l1NodeById.has(entry.parentId))
      .slice(0, l2Positions.length);
    const l2Nodes: StructureNode[] = l2Entries.map((entry, index) => ({
      id: `customer-${entry.customer.id}`,
      role: 'L2',
      label: this.structureNodeLabel(entry.customer.name),
      x: l2Positions[index].x,
      y: l2Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(entry.customer.name)) ?? 0 }
    }));
    const l2NodeById = new Map(l2Entries.map((entry, index) => [entry.customer.id, l2Nodes[index]]));
    const l3Entries = thirdReferrals
      .filter((entry) => l2NodeById.has(entry.parentId))
      .slice(0, l3Positions.length);
    const l3Nodes: StructureNode[] = l3Entries.map((entry, index) => ({
      id: `customer-${entry.customer.id}`,
      role: 'L3',
      label: this.structureNodeLabel(entry.customer.name),
      x: l3Positions[index].x,
      y: l3Positions[index].y,
      meta: { spend: monthlySpendByCustomer.get(this.normalizeCustomerKey(entry.customer.name)) ?? 0 }
    }));

    const links: StructureLink[] = l1Nodes.map((node) => ({
      x1: root.x,
      y1: root.y,
      x2: node.x,
      y2: node.y
    }));

    l2Nodes.forEach((node, index) => {
      const entry = l2Entries[index];
      const parent = entry ? l1NodeById.get(entry.parentId) : undefined;
      if (!parent) {
        return;
      }
      links.push({
        x1: parent.x,
        y1: parent.y,
        x2: node.x,
        y2: node.y
      });
    });
    l3Nodes.forEach((node, index) => {
      const entry = l3Entries[index];
      const parent = entry ? l2NodeById.get(entry.parentId) : undefined;
      if (!parent) {
        return;
      }
      links.push({
        x1: parent.x,
        y1: parent.y,
        x2: node.x,
        y2: node.y
      });
    });

    const graph = { nodes: [root, ...l1Nodes, ...l2Nodes, ...l3Nodes], links };
    this.structureGraphCache = {
      selectedCustomerId: this.selectedCustomer.id,
      customersRef: this.customers,
      graph
    };
    return graph;
  }

  get isStructureFormValid(): boolean {
    return Boolean(this.structureForm.name.trim() && this.structureForm.email.trim());
  }

  get isProductFormValid(): boolean {
    return Boolean(this.productForm.name.trim() && Number(this.productForm.price));
  }

  structureNodeFill(role: StructureNode['role']): string {
    if (role === 'root') {
      return 'rgba(59,130,246,.92)';
    }
    if (role === 'L1') {
      return 'rgba(245,185,66,.92)';
    }
    return 'rgba(139,92,246,.92)';
  }

  structureNodeRadius(role: StructureNode['role']): number {
    if (role === 'root') {
      return 26;
    }
    if (role === 'L1') {
      return 16;
    }
    return 12;
  }

  structureNodeFont(role: StructureNode['role']): number {
    if (role === 'root') {
      return 12;
    }
    if (role === 'L1') {
      return 10;
    }
    return 9;
  }

  formatMoney(value: number): string {
    return this.adminControl.formatMoney(value);
  }

  discountTierPercentValue(tier: DiscountTierDraft): number {
    return this.roundMoney(this.normalizeDiscountRateValue(tier?.rate) * 100);
  }

  discountTierRangeLabel(tier: DiscountTierDraft): string {
    const min = this.parseNonNegativeNumber(tier?.min);
    const max = tier?.max == null ? null : this.parseNonNegativeNumber(tier.max);
    if (max == null || max < min) {
      return `Desde ${this.formatMoney(min)}`;
    }
    return `${this.formatMoney(min)} a ${this.formatMoney(max)}`;
  }

  updateDiscountTierMin(index: number, value: unknown): void {
    const tiers = this.businessConfigDraft.rewards.discountTiers ?? [];
    if (!tiers[index]) {
      return;
    }
    tiers[index].min = this.parseNonNegativeNumber(value);
    this.refreshDiscountTierThresholds();
  }

  updateDiscountTierRate(index: number, value: unknown): void {
    const tiers = this.businessConfigDraft.rewards.discountTiers ?? [];
    if (!tiers[index]) {
      return;
    }
    const percent = Math.min(100, this.parseNonNegativeNumber(value));
    tiers[index].rate = this.roundMoney(percent / 100);
  }

  configOptionDescription(value: string, options: Array<ExplainedSelectOption<string>>): string {
    return options.find((option) => String(option.value) === String(value))?.description ?? '';
  }

  customerStatusClass(customer: AdminCustomer): string {
    return this.isCustomerActive(customer) ? 'badge badge-compact status-active' : 'badge badge-compact status-inactive';
  }

  customerStatusLabel(customer: AdminCustomer): string {
    return this.isCustomerActive(customer) ? 'Activa' : 'Inactiva';
  }

  customerLevelClass(customer: AdminCustomer): string {
    const match = String(customer.level || '').match(/\d+/);
    const parsed = Number(match?.[0] ?? 5);
    const level = Math.max(1, Math.min(5, Number.isFinite(parsed) ? parsed : 5));
    return `badge badge-compact level-${level}`;
  }

  commissionStatusClass(status?: AdminCustomer['commissionsPrevStatus']): string {
    if (status === 'paid') {
      return 'badge badge-compact level-1 status-active';
    }
    if (status === 'pending') {
      return 'badge badge-compact level-3';
    }
    return 'badge badge-compact level-5 status-inactive';
  }

  commissionStatusLabel(status?: AdminCustomer['commissionsPrevStatus']): string {
    if (status === 'paid') {
      return 'Pagada';
    }
    if (status === 'pending') {
      return 'Pendiente de pago';
    }
    return 'Sin movimientos';
  }

  private isCustomerActive(customer: AdminCustomer): boolean {
    const anyCustomer = customer as AdminCustomer & { active?: boolean; status?: string };
    if (typeof anyCustomer.active === 'boolean') {
      return anyCustomer.active;
    }
    if (typeof anyCustomer.status === 'string') {
      const normalized = anyCustomer.status.toLowerCase();
      if (normalized.includes('inactiv')) {
        return false;
      }
      if (normalized.includes('activ')) {
        return true;
      }
    }
    const discount = Number(String(customer.discount || '').replace('%', '').trim());
    const discountActive = Number.isFinite(discount) && discount > 0;
    const commissionsActive =
      (customer.commissionsCurrentConfirmed ?? 0) > 0 ||
      (customer.commissionsCurrentPending ?? 0) > 0 ||
      (customer.commissions ?? 0) > 0;
    return discountActive || commissionsActive;
  }

  openReceipt(url?: string): void {
    if (!url) {
      return;
    }
    window.open(url, '_blank', 'noopener');
  }


  onAdminNavSelect(viewId: string): void {
    this.setView(viewId as AdminViewId);
  }

  setView(view: AdminViewId): void {
    if (!this.canAccessView(view)) {
      return;
    }
    this.currentView = view;
    if (view === 'stocks' || view === 'pos') {
      this.loadStocksAndPosState();
      return;
    }
    if (view === 'settings') {
      this.syncBusinessConfigDraft();
    }
  }

  private loadStocksAndPosState(): void {
    this.adminControl.loadStocksAndPosState().subscribe({
      next: (state) => {
        this.stocks = (state.stocks ?? []).map((stock) => ({
          id: stock.id,
          name: stock.name,
          location: stock.location,
          linkedUserIds: stock.linkedUserIds ?? [],
          inventory: this.normalizeInventoryRecord(stock.inventory as Record<number, number> | Record<string, number>)
        }));

        this.transfers = (state.transfers ?? []).map((transfer) => ({
          id: transfer.id,
          sourceStockId: transfer.sourceStockId,
          destinationStockId: transfer.destinationStockId,
          lines: (transfer.lines ?? []).map((line) => ({ productId: Number(line.productId), qty: Number(line.qty) })),
          status: transfer.status,
          createdAt: transfer.createdAt ?? '',
          createdByUserId: transfer.createdByUserId ?? null,
          receivedAt: transfer.receivedAt,
          receivedByUserId: transfer.receivedByUserId ?? null
        }));

        this.inventoryMovements = (state.movements ?? []).map((movement) => ({
          id: movement.id,
          type: movement.type,
          stockId: movement.stockId,
          productId: Number(movement.productId),
          qty: Number(movement.qty),
          createdAt: movement.createdAt ?? '',
          userId: movement.userId ?? null,
          reason: movement.reason,
          referenceId: movement.referenceId
        }));

        this.stockDamages = this.inventoryMovements
          .filter((movement) => movement.type === 'damaged')
          .map((movement) => ({
            id: movement.referenceId || movement.id,
            stockId: movement.stockId,
            productId: movement.productId,
            qty: movement.qty,
            reason: movement.reason || '',
            createdAt: movement.createdAt,
            reportedByUserId: movement.userId ?? null
          }));

        this.posSales = (state.posSales ?? []).map((sale) => ({
          id: sale.id,
          orderId: sale.orderId,
          stockId: sale.stockId,
          attendantUserId: sale.attendantUserId ?? null,
          customerId: sale.customerId ?? null,
          customerName: sale.customerName,
          grossSubtotal: Number(sale.grossSubtotal ?? sale.total ?? 0),
          discountRate: Number(sale.discountRate ?? 0),
          discountAmount: Number(sale.discountAmount ?? 0),
          total: Number(sale.total),
          paymentStatus: sale.paymentStatus,
          deliveryStatus: sale.deliveryStatus,
          createdAt: sale.createdAt ?? '',
          lines: sale.lines ?? []
        }));

        if (!this.selectedStockId && this.stocks.length) {
          this.selectStock(this.stocks[0].id);
        } else if (this.selectedStockId && !this.stocks.some((stock) => stock.id === this.selectedStockId)) {
          this.selectStock(this.stocks[0]?.id ?? '');
        }
        this.syncPosOperatorContext();
        this.refreshPosCashControl();
      }
    });
  }

  private normalizeInventoryRecord(raw: Record<number, number> | Record<string, number> | undefined): Record<number, number> {
    const source = raw ?? {};
    return Object.entries(source).reduce<Record<number, number>>((acc, [key, value]) => {
      const pid = Number(key);
      if (!Number.isFinite(pid)) {
        return acc;
      }
      acc[pid] = Number(value) || 0;
      return acc;
    }, {});
  }

  setOrderStatus(status: AdminOrder['status']): void {
    this.currentOrderStatus = status;
  }

  showActions(): void {
    if (!this.canAccessView('stats')) {
      return;
    }
    this.currentView = 'stats';
    this.isActionsModalOpen = true;
    setTimeout(() => {
      const actionsPanel = document.getElementById('admin-actions');
      actionsPanel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  }

  openNewOrderModal(): void {
    if (!this.hasPermission('order_create')) {
      return;
    }
    this.resetNewOrderForm();
    this.isNewOrderModalOpen = true;
  }

  openAddStructureModal(): void {
    if (!this.hasPermission('customer_add')) {
      return;
    }
    this.resetStructureForm();
    this.isAddStructureModalOpen = true;
  }

  closeModals(): void {
    console.log('[Admin] closeModals()', {
      isActionsModalOpen: this.isActionsModalOpen,
      isNewOrderModalOpen: this.isNewOrderModalOpen,
      isAddStructureModalOpen: this.isAddStructureModalOpen
    });
    this.isActionsModalOpen = false;
    this.isNewOrderModalOpen = false;
    this.isAddStructureModalOpen = false;
    this.isShippingModalOpen = false;
    this.isReceiptModalOpen = false;
  }

  openReceiptModal(customer: AdminCustomer): void {
    if (!this.hasPermission('commissions_register_payment')) {
      return;
    }
    this.receiptTargetCustomer = customer;
    this.receiptFile = null;
    this.receiptError = '';
    this.isReceiptModalOpen = true;
  }

  closeReceiptModal(): void {
    this.isReceiptModalOpen = false;
    this.receiptTargetCustomer = null;
    this.receiptFile = null;
    this.receiptError = '';
  }

  updateReceiptFile(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0] ?? null;
    this.receiptFile = file;
  }

  private getPrevMonthKey(date = new Date()): string {
    const year = date.getUTCFullYear();
    const month = date.getUTCMonth();
    if (month === 0) {
      return `${year - 1}-12`;
    }
    const prevMonth = String(month).padStart(2, '0');
    return `${year}-${prevMonth}`;
  }

  uploadReceipt(): void {
    if (!this.hasPermission('commissions_register_payment')) {
      return;
    }
    if (!this.receiptTargetCustomer || !this.receiptFile || this.isUploadingReceipt) {
      this.receiptError = 'Selecciona un comprobante.';
      return;
    }
    this.receiptError = '';
    this.isUploadingReceipt = true;
    const file = this.receiptFile;
    const customerId = this.receiptTargetCustomer.id;
    const monthKey = this.receiptTargetCustomer.commissionsPrevMonthKey || this.getPrevMonthKey();
    this.readFileAsDataUrl(file)
      .pipe(
        switchMap((dataUrl) => {
          const contentBase64 = this.extractBase64(dataUrl);
          if (!contentBase64) {
            throw new Error('No se pudo leer el comprobante.');
          }
          return this.adminControl.uploadAdminCommissionReceipt({
            customerId,
            monthKey,
            name: file.name,
            contentBase64,
            contentType: file.type || 'application/octet-stream'
          });
        }),
        switchMap(() => this.adminControl.load()),
        finalize(() => {
          this.isUploadingReceipt = false;
          this.closeReceiptModal();
        })
      )
      .subscribe({
        error: () => {
          this.receiptError = 'No se pudo cargar el comprobante.';
        }
      });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  openUserDashboard(): void {
    void this.router.navigate(['/dashboard']);
  }

  advanceOrder(order: AdminOrder): void {
    if (
      (order.status === 'pending' && !this.hasPermission('order_mark_paid')) ||
      (order.status === 'paid' && !this.hasPermission('order_mark_shipped')) ||
      (order.status === 'shipped' && !this.hasPermission('order_mark_delivered'))
    ) {
      return;
    }
    if (this.updatingOrderIds.has(order.id)) {
      return;
    }
    if (order.status === 'paid') {
      this.openShippingModal(order);
      return;
    }
    const nextStatus =
      order.status === 'pending' ? 'paid' : order.status === 'shipped' ? 'delivered' : order.status;
    if (nextStatus === order.status) {
      return;
    }
    this.updatingOrderIds.add(order.id);
    this.adminControl
      .updateOrderStatus(order.id, { status: nextStatus })
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(order.id);
          this.requestViewUpdate();
        })
      )
      .subscribe();
  }

  openShippingModal(order: AdminOrder): void {
    this.shippingTargetOrder = order;
    this.shippingType = 'carrier';
    this.shippingTrackingNumber = '';
    this.shippingDeliveryPlace = '';
    this.shippingDeliveryDate = '';
    this.shippingStockId = order.stockId ?? this.selectedStockId;
    this.shippingFallbackProductId = this.products[0]?.id ?? null;
    this.shippingFallbackQty = 1;
    this.shippingError = '';
    this.isShippingModalOpen = true;
  }

  closeShippingModal(): void {
    this.isShippingModalOpen = false;
    this.shippingTargetOrder = null;
    this.shippingStockId = '';
    this.shippingFallbackProductId = null;
    this.shippingFallbackQty = 1;
    this.shippingError = '';
  }

  confirmShipping(): void {
    if (!this.hasPermission('order_mark_shipped')) {
      return;
    }
    if (!this.shippingTargetOrder) {
      return;
    }
    if (this.shippingType === 'carrier' && !this.shippingTrackingNumber.trim()) {
      this.shippingError = 'Ingresa el níƒÂºmero de guíƒÂ­a.';
      return;
    }
    if (
      this.shippingType === 'personal' &&
      (!this.shippingDeliveryPlace.trim() || !this.shippingDeliveryDate.trim())
    ) {
      this.shippingError = 'Ingresa lugar y fecha de entrega personal.';
      return;
    }
    if (!this.shippingStockId) {
      this.shippingError = 'Selecciona el stock origen para el envio.';
      return;
    }
    const dispatchLines = this.resolveDispatchLines(this.shippingTargetOrder);
    if (!dispatchLines.length) {
      this.shippingError = 'Agrega producto y cantidad para descontar stock.';
      return;
    }
    this.shippingError = '';
    const payload = {
      status: 'shipped' as const,
      shippingType: this.shippingType,
      trackingNumber: this.shippingType === 'carrier' ? this.shippingTrackingNumber.trim() : undefined,
      deliveryPlace: this.shippingType === 'personal' ? this.shippingDeliveryPlace.trim() : undefined,
      deliveryDate: this.shippingType === 'personal' ? this.shippingDeliveryDate.trim() : undefined,
      stockId: this.shippingStockId,
      dispatchLines: dispatchLines.map((line) => ({ productId: line.productId, quantity: line.quantity }))
    };
    const orderId = this.shippingTargetOrder.id;
    this.updatingOrderIds.add(orderId);
    this.adminControl
      .updateOrderStatus(orderId, payload)
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(orderId);
        })
      )
      .subscribe({
        next: () => {
          this.closeShippingModal();
        },
        error: (error: unknown) => {
          this.shippingError = this.resolveUiErrorMessage(error, 'No se pudo actualizar el envio.');
        }
      });
  }

  confirmShippingWithChangeDetection(): void {
    if (!this.hasPermission('order_mark_shipped')) {
      return;
    }
    if (!this.shippingTargetOrder) {
      return;
    }
    if (this.shippingType === 'carrier' && !this.shippingTrackingNumber.trim()) {
      this.setShippingError('Ingresa el numero de guia.');
      return;
    }
    if (
      this.shippingType === 'personal' &&
      (!this.shippingDeliveryPlace.trim() || !this.shippingDeliveryDate.trim())
    ) {
      this.setShippingError('Ingresa lugar y fecha de entrega personal.');
      return;
    }
    if (!this.shippingStockId) {
      this.setShippingError('Selecciona el stock origen para el envio.');
      return;
    }

    const dispatchLines = this.resolveDispatchLines(this.shippingTargetOrder);
    if (!dispatchLines.length) {
      this.setShippingError('Agrega producto y cantidad para descontar stock.');
      return;
    }

    this.setShippingError('');
    const payload = {
      status: 'shipped' as const,
      shippingType: this.shippingType,
      trackingNumber: this.shippingType === 'carrier' ? this.shippingTrackingNumber.trim() : undefined,
      deliveryPlace: this.shippingType === 'personal' ? this.shippingDeliveryPlace.trim() : undefined,
      deliveryDate: this.shippingType === 'personal' ? this.shippingDeliveryDate.trim() : undefined,
      stockId: this.shippingStockId,
      dispatchLines: dispatchLines.map((line) => ({ productId: line.productId, quantity: line.quantity }))
    };
    const orderId = this.shippingTargetOrder.id;
    this.updatingOrderIds.add(orderId);
    this.requestViewUpdate();

    this.adminControl
      .updateOrderStatus(orderId, payload)
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(orderId);
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: () => {
          this.closeShippingModal();
          this.requestViewUpdate();
        },
        error: (error: unknown) => {
          this.setShippingError(this.resolveUiErrorMessage(error, 'No se pudo actualizar el envio.'));
        }
      });
  }

  isUpdatingOrder(orderId: string): boolean {
    return this.updatingOrderIds.has(orderId);
  }

  canAdvanceOrder(order: AdminOrder): boolean {
    if (order.status === 'pending') {
      return this.hasPermission('order_mark_paid');
    }
    if (order.status === 'paid') {
      return this.hasPermission('order_mark_shipped');
    }
    if (order.status === 'shipped') {
      return this.hasPermission('order_mark_delivered');
    }
    return false;
  }

  updateNewOrderCustomer(customerId: number): void {
    this.newOrderCustomerId = customerId;
  }

  updateNewOrderStatus(status: AdminOrder['status']): void {
    this.newOrderStatus = status;
  }

  toggleProductSelection(productId: number, selected: boolean): void {
    if (selected) {
      this.newOrderItems.set(productId, this.newOrderItems.get(productId) ?? 1);
      return;
    }
    this.newOrderItems.delete(productId);
  }

  updateProductQty(productId: number, quantityValue: string): void {
    const quantity = Math.max(1, Number(quantityValue) || 1);
    if (this.newOrderItems.has(productId)) {
      this.newOrderItems.set(productId, quantity);
    }
  }

  getNewOrderItems(): AdminOrderItem[] {
    return this.products
      .filter((product) => this.newOrderItems.has(product.id))
      .map((product) => ({
        productId: product.id,
        name: product.name,
        price: product.price,
        quantity: this.newOrderItems.get(product.id) ?? 1
      }));
  }

  getNewOrderTotal(): number {
    return this.getNewOrderItems().reduce((acc, item) => acc + item.price * item.quantity, 0);
  }

  getShippingLabel(order: AdminOrder): string {
    const stockId = order.stockId;
    const stockLabel = stockId ? this.stockName(stockId) : '';
    if (order.paymentStatus && order.deliveryStatus) {
      return `${order.paymentStatus} · ${order.deliveryStatus}${stockLabel ? ` · ${stockLabel}` : ''}`;
    }
    if (order.shippingType === 'carrier' && order.trackingNumber) {
      return `Guia: ${order.trackingNumber}${stockLabel ? ` · ${stockLabel}` : ''}`;
    }
    if (order.shippingType === 'personal' && (order.deliveryPlace || order.deliveryDate)) {
      const place = order.deliveryPlace ? order.deliveryPlace : 'Entrega personal';
      const date = order.deliveryDate ? ` · ${order.deliveryDate}` : '';
      return `${place}${date}${stockLabel ? ` · ${stockLabel}` : ''}`;
    }
    return stockLabel || '-';
  }

  saveNewOrder(): void {
    if (!this.hasPermission('order_create')) {
      return;
    }
    console.log('[Admin] saveNewOrder() start', {
      newOrderCustomerId: this.newOrderCustomerId,
      items: this.newOrderItems.size,
      isSavingOrder: this.isSavingOrder
    });
    if (!this.newOrderCustomerId || this.newOrderItems.size === 0 || this.isSavingOrder) {
      console.log('[Admin] saveNewOrder() aborted');
      return;
    }
    const customer = this.customers.find((entry) => entry.id === this.newOrderCustomerId);
    if (!customer) {
      console.log('[Admin] saveNewOrder() aborted: customer not found');
      return;
    }
    const orderItems = this.getNewOrderItems();
    const payload: CreateAdminOrderPayload = {
      customerId: customer.id,
      customerName: customer.name,
      status: this.newOrderStatus,
      items: orderItems
    };
    this.isSavingOrder = true;
    console.log('[Admin] saveNewOrder() call createOrder', payload);
    this.adminControl
      .createOrder(payload)
      .pipe(
        switchMap(() => {
          console.log('[Admin] saveNewOrder() createOrder next -> load()');
          return this.adminControl.load();
        }),
        finalize(() => {
          console.log('[Admin] saveNewOrder() finalize');
          this.isSavingOrder = false;
        })
      )
      .subscribe({
        next: () => {
          console.log('[Admin] saveNewOrder() load next -> closeModals()');
          this.closeModals();
        },
        error: () => {
          console.log('[Admin] saveNewOrder() error -> closeModals()');
          this.closeModals();
        }
      });
  }

  resetNewOrderForm(): void {
    this.newOrderCustomerId = this.customers[0]?.id ?? null;
    this.newOrderStatus = 'pending';
    this.newOrderItems.clear();
    this.isSavingOrder = false;
  }

  resetStructureForm(): void {
    this.structureForm = {
      name: '',
      phone: '',
      email: '',
      address: '',
      city: ''
    };
    this.isSavingStructure = false;
    if (this.selectedCustomer) {
      this.structureLeader = this.selectedCustomer;
      this.structureLevel = 'L1';
      return;
    }
    this.structureLeader = null;
    this.structureLevel = 'Raí­z';
  }

  updateStructureField(
    field: 'name' | 'phone' | 'email' | 'address' | 'city',
    value: string
  ): void {
    this.structureForm = {
      ...this.structureForm,
      [field]: value
    };
  }

  saveStructureCustomer(): void {
    if (!this.hasPermission('customer_add')) {
      return;
    }
    const payload: CreateStructureCustomerPayload = {
      name: this.structureForm.name.trim(),
      email: this.structureForm.email.trim(),
      phone: this.structureForm.phone?.trim() || undefined,
      address: this.structureForm.address?.trim() || undefined,
      city: this.structureForm.city?.trim() || undefined,
      leaderId: this.structureLeader?.id ?? null
    };
    this.isSavingStructure = true;
    this.adminControl.createStructureCustomer(payload).subscribe({
      next: () => {
        this.isSavingStructure = false;
        this.adminControl.load().subscribe();
        this.closeModals();
      },
      error: () => {
        this.isSavingStructure = false;
      }
    });
  }

  selectCustomer(customerId: number): void {
    const selected = this.customers.find((customer) => customer.id === customerId) ?? null;
    this.selectedCustomer = selected;
    this.syncSelectedCustomerAccessDraft();
  }

  updateSelectedCustomerAdminAccess(enabled: boolean): void {
    this.selectedCustomerAdminAccess = enabled;
  }

  updateSelectedCustomerPrivilege(privilege: AppPrivilege, enabled: boolean): void {
    this.selectedCustomerPrivilegeDraft = {
      ...this.selectedCustomerPrivilegeDraft,
      [privilege]: enabled
    };
  }

  updateSelectedCustomerSponsorSearch(value: string): void {
    this.selectedCustomerSponsorSearch = value;
    const normalized = this.normalizeSponsorSearch(value);
    const exactMatch = this.getSelectedCustomerSponsorCandidates().find(
      (customer) => this.normalizeSponsorSearch(`${customer.name} ${customer.email}`) === normalized
    );
    this.selectedCustomerLeaderId = exactMatch ? String(exactMatch.id) : '';
    this.refreshSelectedCustomerSponsorState();
  }

  selectFindingUSponsor(): void {
    this.selectedCustomerLeaderId = '';
    this.selectedCustomerSponsorSearch = 'FindingU';
    this.refreshSelectedCustomerSponsorState();
  }

  selectSponsorRecommendation(sponsorId: string): void {
    const sponsor = this.customers.find((customer) => String(customer.id) === sponsorId);
    if (!sponsor) {
      return;
    }
    this.selectedCustomerLeaderId = sponsorId;
    this.selectedCustomerSponsorSearch = `${sponsor.name} · ${sponsor.email}`;
    this.refreshSelectedCustomerSponsorState();
  }

  saveSelectedCustomerPosition(): void {
    if (!this.selectedCustomer || !this.canSaveSelectedCustomerPosition) {
      return;
    }
    const leaderId = this.selectedCustomerLeaderId ? Number(this.selectedCustomerLeaderId) : null;
    this.isSavingCustomerPosition = true;
    this.refreshSelectedCustomerSponsorState();
    this.adminControl
      .updateCustomer(this.selectedCustomer.id, { leaderId })
      .pipe(
        finalize(() => {
          this.isSavingCustomerPosition = false;
          this.refreshSelectedCustomerSponsorState();
        })
      )
      .subscribe({
        next: (updated) => {
          this.selectedCustomer = { ...this.selectedCustomer, ...updated };
          this.syncSelectedCustomerAccessDraft();
        }
      });
  }

  saveSelectedCustomerAccess(): void {
    if (!this.selectedCustomer || this.isSavingCustomerPrivileges) {
      return;
    }
    if (!this.hasPermission('user_manage_privileges')) {
      return;
    }
    if (!this.hasPermission('user_mark_admin') && this.selectedCustomerAdminAccess) {
      return;
    }
    this.isSavingCustomerPrivileges = true;
    this.adminControl
      .updateCustomerPrivileges(this.selectedCustomer.id, {
        canAccessAdmin: this.selectedCustomerAdminAccess,
        privileges: normalizePrivileges(this.selectedCustomerPrivilegeDraft)
      })
      .pipe(
        finalize(() => {
          this.isSavingCustomerPrivileges = false;
        })
      )
      .subscribe({
        next: (updated) => {
          this.selectedCustomer = { ...this.selectedCustomer, ...updated };
          this.syncSelectedCustomerAccessDraft();
        }
      });
  }

  private syncSelectedCustomerAccessDraft(): void {
    const selected = this.selectedCustomer;
    this.selectedCustomerAdminAccess = Boolean(selected?.canAccessAdmin);
    this.selectedCustomerPrivilegeDraft = normalizePrivileges(selected?.privileges);
    this.selectedCustomerLeaderId = selected?.leaderId != null ? String(selected.leaderId) : '';
    if (selected?.leaderId != null) {
      const sponsor = this.customers.find((customer) => customer.id === selected.leaderId);
      this.selectedCustomerSponsorSearch = sponsor ? `${sponsor.name} · ${sponsor.email}` : '';
    } else {
      this.selectedCustomerSponsorSearch = 'FindingU';
    }
    this.refreshSelectedCustomerSponsorState();
  }

  private normalizeSponsorSearch(value: string): string {
    return (value ?? '').trim().toLowerCase();
  }

  private getSelectedCustomerSponsorCandidates(): AdminCustomer[] {
    const selectedId = this.selectedCustomer?.id;
    return this.customers.filter((customer) => customer.id !== selectedId);
  }

  private refreshSelectedCustomerSponsorState(): void {
    const query = this.normalizeSponsorSearch(this.selectedCustomerSponsorSearch);
    const base = this.getSelectedCustomerSponsorCandidates().map((customer) => ({
      id: String(customer.id),
      name: customer.name,
      email: customer.email,
      label: `${customer.name} · ${customer.email}`
    }));

    this.selectedCustomerSponsorRecommendations = (!query
      ? base
      : base.filter((candidate) => this.normalizeSponsorSearch(`${candidate.name} ${candidate.email}`).includes(query))
    ).slice(0, 8);

    if (this.selectedCustomerLeaderId === '') {
      this.selectedSponsorLabel = 'FindingU (sin patrocinador)';
      this.hasValidSelectedSponsorId = true;
    } else {
      const sponsor = this.customers.find((customer) => String(customer.id) === this.selectedCustomerLeaderId && customer.id !== this.selectedCustomer?.id);
      this.selectedSponsorLabel = sponsor ? `${sponsor.name} · ${sponsor.email}` : 'Sin patrocinador valido';
      this.hasValidSelectedSponsorId = Boolean(sponsor);
    }

    const nextLeaderId = this.selectedCustomerLeaderId ? Number(this.selectedCustomerLeaderId) : null;
    this.canSaveSelectedCustomerPosition = Boolean(
      !this.isSavingCustomerPosition &&
      this.selectedCustomer &&
      this.hasValidSelectedSponsorId &&
      (this.selectedCustomer.leaderId ?? null) !== nextLeaderId
    );
  }

  editProduct(product: AdminProduct): void {
    this.productForm = {
      id: product.id,
      name: product.name,
      price: String(product.price),
      sku: product.sku ?? '',
      hook: product.hook ?? '',
      description: product.description ?? '',
      copyFacebook: product.copyFacebook ?? '',
      copyInstagram: product.copyInstagram ?? '',
      copyWhatsapp: product.copyWhatsapp ?? '',
      tags: (product.tags ?? []).join(', ')
    };
    this.resetProductAssets();
    this.productExistingImages = product.images ?? [];
    this.applyProductImagePreviews(product.images);
    this.announceProductMessage(`Editando ${product.name}.`);
  }

  updateProductField(
    field: 'name' | 'price' | 'sku' | 'hook' | 'description' | 'copyFacebook' | 'copyInstagram' | 'copyWhatsapp' | 'tags',
    value: string
  ): void {
    this.productForm = {
      ...this.productForm,
      [field]: value
    };
  }

  setProductOfMonth(product: AdminProduct): void {
    if (!this.hasPermission('product_set_month')) {
      return;
    }
    if (this.isSettingProductOfMonth) {
      return;
    }
    this.isSettingProductOfMonth = true;
    this.adminControl
      .setProductOfMonth(product.id)
      .pipe(
        finalize(() => {
          this.isSettingProductOfMonth = false;
        })
      )
      .subscribe({
        next: () => {
          this.announceProductMessage(`Producto del mes actualizado: ${product.name}.`);
        },
        error: () => {
          this.announceProductMessage('No se pudo actualizar el producto del mes.');
        }
      });
  }


  saveProduct(): void {
    const isEditing = this.productForm.id != null;
    if (isEditing && !this.hasPermission('product_update')) {
      return;
    }
    if (!isEditing && !this.hasPermission('product_add')) {
      return;
    }
    if (this.isSavingProduct || !this.isProductFormValid) {
      return;
    }
    this.isSavingProduct = true;
    this.uploadProductImages()
      .pipe(
        switchMap((uploads) => {
          const payload = {
            id: this.productForm.id,
            productId: this.productForm.id ?? undefined,
            name: this.productForm.name.trim(),
            price: Number(this.productForm.price),
            active: true,
            sku: this.productForm.sku.trim() || undefined,
            hook: this.productForm.hook.trim() || undefined,
            description: this.productForm.description || undefined,
            copyFacebook: this.productForm.copyFacebook || undefined,
            copyInstagram: this.productForm.copyInstagram || undefined,
            copyWhatsapp: this.productForm.copyWhatsapp || undefined,
            tags: this.normalizeTags(this.productForm.tags),
            images: this.mergeProductImages(uploads)
          };
          return this.adminControl.saveProduct(payload).pipe(
            map((product) => ({
              product,
              uploads
            }))
          );
        }),
        finalize(() => {
          this.isSavingProduct = false;
        })
      )
      .subscribe({
        next: ({ product, uploads }) => {
          const hasFailures = uploads.some((upload) => !upload.success);
          if (hasFailures) {
            this.announceProductMessage(
              `Producto guardado: ${product.name}. Algunas imagenes no se pudieron subir.`
            );
          } else {
            this.announceProductMessage(
              this.productForm.id ? `Producto actualizado: ${product.name}.` : `Producto creado: ${product.name}.`
            );
          }
          this.adminControl.load().subscribe();
          this.resetProductForm();
        },
        error: () => {
          this.announceProductMessage('No se pudo guardar el producto.');
        }
      });
  }

  editNotification(notification: PortalNotification): void {
    this.notificationForm = {
      id: notification.id,
      title: notification.title,
      description: notification.description,
      linkUrl: notification.linkUrl || '',
      linkText: notification.linkText || 'Ver',
      startAt: this.toDateTimeLocalInput(notification.startAt),
      endAt: this.toDateTimeLocalInput(notification.endAt),
      active: notification.active !== false
    };
    this.notificationMessage = `Editando notificacion: ${notification.title}.`;
  }

  updateNotificationField(
    field: 'title' | 'description' | 'linkUrl' | 'linkText' | 'startAt' | 'endAt',
    value: string
  ): void {
    this.notificationForm = {
      ...this.notificationForm,
      [field]: value
    };
  }

  saveNotification(): void {
    if (!this.hasPermission('config_manage') || this.isSavingNotification || !this.isNotificationFormValid) {
      return;
    }
    this.isSavingNotification = true;
    const linkUrl = this.notificationForm.linkUrl.trim();
    this.adminControl
      .saveNotification({
        id: this.notificationForm.id || undefined,
        title: this.notificationForm.title.trim(),
        description: this.notificationForm.description.trim(),
        linkUrl: linkUrl || undefined,
        linkText: linkUrl ? this.notificationForm.linkText.trim() || 'Ver' : undefined,
        startAt: this.fromDateTimeLocalInput(this.notificationForm.startAt),
        endAt: this.fromDateTimeLocalInput(this.notificationForm.endAt),
        active: this.notificationForm.active
      })
      .pipe(
        finalize(() => {
          this.isSavingNotification = false;
        })
      )
      .subscribe({
        next: (notification) => {
          this.notificationMessage = this.notificationForm.id
            ? `Notificacion actualizada: ${notification.title}.`
            : `Notificacion creada: ${notification.title}.`;
          this.resetNotificationForm();
        },
        error: () => {
          this.notificationMessage = 'No se pudo guardar la notificacion.';
        }
      });
  }

  resetNotificationForm(): void {
    this.notificationForm = this.getDefaultNotificationForm();
  }

  private resetProductForm(): void {
    this.productForm = {
      id: null,
      name: '',
      price: '',
      sku: '',
      hook: '',
      description: '',
      copyFacebook: '',
      copyInstagram: '',
      copyWhatsapp: '',
      tags: ''
    };
    this.resetProductAssets();
    this.productExistingImages = [];
  }

  private announceProductMessage(message: string): void {
    this.productMessage = message;
    if (this.productMessageTimeout) {
      window.clearTimeout(this.productMessageTimeout);
    }
    this.productMessageTimeout = window.setTimeout(() => {
      this.productMessage = '';
    }, 2800);
  }

  notificationStatusLabel(status?: PortalNotification['status']): string {
    if (status === 'scheduled') {
      return 'Programada';
    }
    if (status === 'expired') {
      return 'Expirada';
    }
    if (status === 'inactive') {
      return 'Inactiva';
    }
    return 'Activa';
  }

  notificationStatusClass(status?: PortalNotification['status']): string {
    if (status === 'scheduled') {
      return 'badge badge-pending';
    }
    if (status === 'expired' || status === 'inactive') {
      return 'badge badge-inactive';
    }
    return 'badge badge-active';
  }

  notificationWindowLabel(notification: PortalNotification): string {
    const start = this.formatDateTime(notification.startAt);
    const end = this.formatDateTime(notification.endAt);
    if (!start && !end) {
      return 'Sin ventana programada';
    }
    return `${start || '-'} a ${end || '-'}`;
  }

  formatDateTime(value?: string): string {
    if (!value) {
      return '';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return '';
    }
    return parsed.toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  private getDefaultNotificationForm(): {
    id: string;
    title: string;
    description: string;
    linkUrl: string;
    linkText: string;
    startAt: string;
    endAt: string;
    active: boolean;
  } {
    const now = new Date();
    const end = new Date(now.getTime() + 1000 * 60 * 60 * 24 * 7);
    return {
      id: '',
      title: '',
      description: '',
      linkUrl: '',
      linkText: 'Ver',
      startAt: this.toDateTimeLocalInput(now.toISOString()),
      endAt: this.toDateTimeLocalInput(end.toISOString()),
      active: true
    };
  }

  private toDateTimeLocalInput(value?: string): string {
    if (!value) {
      return '';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return '';
    }
    const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  }

  private fromDateTimeLocalInput(value: string): string {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '' : parsed.toISOString();
  }

  uploadProductImage(event: Event, section: CreateProductAssetPayload['section']): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      return;
    }
    this.setProductImagePreview(section, file);
    this.productImageFiles.set(section, file);
    this.productImageUploads.set(section, false);
  }

  private setProductImagePreview(section: CreateProductAssetPayload['section'], file: File): void {
    const previewUrl = URL.createObjectURL(file);
    const currentUrl = this.productImagePreviews.get(section);
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
    }
    this.productImagePreviews.set(section, previewUrl);
  }

  private resetProductAssets(): void {
    this.productImageFiles.clear();
    this.productImageUploads.clear();
    this.productImagePreviews.forEach((value) => {
      if (value.startsWith('blob:')) {
        URL.revokeObjectURL(value);
      }
    });
    this.productImagePreviews.clear();
  }

  private applyProductImagePreviews(images?: AdminProduct['images']): void {
    if (!images || !Array.isArray(images)) {
      return;
    }
    images.forEach((image) => {
      if (!image?.section || !image?.url) {
        return;
      }
      this.productImagePreviews.set(image.section, image.url);
      this.productImageUploads.set(image.section, false);
    });
  }

  private mergeProductImages(
    uploads: Array<{ section: CreateProductAssetPayload['section']; success: boolean; assetId?: string; url?: string }>
  ): AdminProduct['images'] | undefined {
    const existing = Array.isArray(this.productExistingImages) ? this.productExistingImages : [];
    const uploaded = uploads
      .filter((upload) => upload.success && upload.url)
      .map((upload) => ({
        section: upload.section,
        url: upload.url ?? '',
        assetId: upload.assetId
      }));
    if (!uploaded.length) {
      return existing.length ? existing : undefined;
    }
    const uploadedSections = new Set(uploaded.map((img) => img.section));
    const preserved = existing.filter((img) => img?.section && !uploadedSections.has(img.section));
    const merged = [...preserved, ...uploaded];
    return merged.length ? merged : undefined;
  }


  private uploadProductImages(): Observable<
    Array<{ section: CreateProductAssetPayload['section']; success: boolean; assetId?: string; url?: string }>
  > {
    const entries = Array.from(this.productImageFiles.entries());
    if (entries.length === 0) {
      return of([]);
    }
    entries.forEach(([section]) => {
      this.productImageUploads.set(section, true);
    });
    const uploads = entries.map(([section, file]) => {
      return this.createAssetFromFile(file).pipe(
        switchMap((asset) => {
          const assetId = asset.asset?.assetId;
          const url = asset.asset?.url;
          if (!assetId || !url) {
            return of({ section, success: false });
          }
          return of({ section, success: true, assetId, url });
        }),
        catchError(() => of({ section, success: false })),
        finalize(() => {
          this.productImageUploads.set(section, false);
        })
      );
    });
    return forkJoin(uploads);
  }

  private createAssetFromFile(file: File): Observable<AssetResponse> {
    return this.readFileAsDataUrl(file).pipe(
      switchMap((dataUrl) => {
        const contentBase64 = this.extractBase64(dataUrl);
        if (!contentBase64) {
          return of({ asset: { assetId: '' } });
        }
        const payload: CreateAssetPayload = {
          name: file.name,
          contentBase64,
          contentType: file.type || 'application/octet-stream'
        };
        return this.adminControl.createAsset(payload);
      })
    );
  }

  private readFileAsDataUrl(file: File): Observable<string> {
    return new Observable<string>((observer) => {
      const reader = new FileReader();
      reader.onload = () => {
        observer.next(String(reader.result ?? ''));
        observer.complete();
      };
      reader.onerror = () => {
        observer.error(new Error('No se pudo leer la imagen.'));
      };
      reader.readAsDataURL(file);
    });
  }

  private extractBase64(dataUrl: string): string {
    const parts = dataUrl.split(',');
    if (parts.length < 2) {
      return '';
    }
    return parts[1] ?? '';
  }

  private normalizeTags(value: string): string[] | undefined {
    const tags = (value ?? '')
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    return tags.length ? tags : undefined;
  }

  createStock(): void {
    if (!this.hasPermission('stock_create')) {
      return;
    }
    const name = this.stockForm.name.trim();
    const location = this.stockForm.location.trim();
    if (!name || !location) {
      return;
    }
    this.adminControl.createStock({ name, location }).subscribe({
      next: (stock) => {
        this.stockForm = { name: '', location: '' };
        this.selectedStockId = stock.id;
        this.loadStocksAndPosState();
      }
    });
  }

  selectStock(stockId: string): void {
    this.selectedStockId = stockId;
    const selected = this.selectedStock;
    if (!selected) {
      return;
    }
    this.stockDamageForm.stockId = selected.id;
    this.stockEntryForm.stockId = selected.id;
    this.stockTransferForm.sourceStockId = this.stockTransferForm.sourceStockId || selected.id;
    this.posForm.stockId = this.posForm.stockId || selected.id;
    this.stockUserLinkDraft = new Set(selected.linkedUserIds);
  }

  saveStockLinks(): void {
    const stock = this.selectedStock;
    if (!stock) {
      return;
    }
    this.adminControl
      .updateStock(stock.id, { linkedUserIds: [...this.stockUserLinkDraft] })
      .subscribe({ next: () => this.loadStocksAndPosState() });
  }

  openStockEntryModal(productId: number): void {
    const stockId = this.selectedStockId;
    if (!stockId) {
      return;
    }
    this.setStockFeedback('', '');
    this.stockEntryForm.stockId = stockId;
    this.stockEntryForm.productId = productId;
    this.stockEntryForm.qty = 1;
    this.stockEntryForm.note = '';
    this.isStockEntryModalOpen = true;
  }

  closeStockEntryModal(): void {
    this.isStockEntryModalOpen = false;
  }

  registerStockEntry(): void {
    if (!this.hasPermission('stock_add_inventory')) {
      return;
    }
    const { stockId, productId, qty, note, createdByUserId } = this.stockEntryForm;
    if (!stockId || !productId || qty <= 0) {
      this.setStockFeedback('Selecciona stock, producto y una cantidad valida.', 'error');
      return;
    }
    const normalizedQty = Math.floor(Number(qty));
    if (!Number.isFinite(normalizedQty) || normalizedQty <= 0) {
      this.setStockFeedback('La cantidad debe ser mayor a cero.', 'error');
      return;
    }
    this.setStockFeedback('', '');
    this.adminControl.registerStockEntry(stockId, {
      productId,
      qty: normalizedQty,
      note: note.trim() || undefined,
      userId: createdByUserId
    }).subscribe({
      next: () => {
        this.setStockFeedback('Entrada de inventario registrada.', 'success');
        this.closeStockEntryModal();
        this.loadStocksAndPosState();
      },
      error: (error: { error?: { message?: string }; message?: string }) => {
        this.setStockFeedback(
          error?.error?.message || error?.message || 'No se pudo registrar la entrada de inventario.',
          'error'
        );
      }
    });
  }

  addTransferLine(): void {
    this.stockTransferForm.lines = [...this.stockTransferForm.lines, { productId: null, qty: 1 }];
  }

  removeTransferLine(index: number): void {
    if (this.stockTransferForm.lines.length <= 1) {
      return;
    }
    this.stockTransferForm.lines = this.stockTransferForm.lines.filter((_, idx) => idx !== index);
  }

  createTransfer(): void {
    if (!this.hasPermission('stock_create_transfer')) {
      return;
    }
    const { sourceStockId, destinationStockId, createdByUserId } = this.stockTransferForm;
    const normalizedLines = this.normalizeTransferLines(this.stockTransferForm.lines);
    if (!sourceStockId || !destinationStockId || sourceStockId === destinationStockId || !normalizedLines.length) {
      this.setStockFeedback('Completa origen, destino y al menos una linea valida.', 'error');
      return;
    }
    const sourceStock = this.stocks.find((stock) => stock.id === sourceStockId);
    if (!sourceStock) {
      this.setStockFeedback('Selecciona un stock origen valido.', 'error');
      return;
    }
    const insufficientLine = normalizedLines.find((line) => (sourceStock.inventory[line.productId] ?? 0) < line.qty);
    if (insufficientLine) {
      this.setStockFeedback(`Stock insuficiente para ${this.productName(insufficientLine.productId)}.`, 'error');
      return;
    }
    this.setStockFeedback('', '');
    this.adminControl
      .createStockTransfer({ sourceStockId, destinationStockId, lines: normalizedLines, createdByUserId })
      .subscribe({
        next: () => {
          this.setStockFeedback('Transferencia creada.', 'success');
          this.stockTransferForm.lines = [{ productId: this.products[0]?.id ?? null, qty: 1 }];
          this.loadStocksAndPosState();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.setStockFeedback(
            error?.error?.message || error?.message || 'No se pudo crear la transferencia.',
            'error'
          );
        }
      });
  }

  receiveTransfer(transferId: string): void {
    if (!this.hasPermission('stock_receive_transfer')) {
      return;
    }
    const transfer = this.transfers.find((item) => item.id === transferId);
    if (!transfer || transfer.status === 'received') {
      return;
    }
    const destination = this.stocks.find((stock) => stock.id === transfer.destinationStockId);
    if (!destination || !this.transferReceiverUserId) {
      this.setStockFeedback('Selecciona un usuario valido para recibir la transferencia.', 'error');
      return;
    }
    if (!destination.linkedUserIds.includes(this.transferReceiverUserId)) {
      this.setStockFeedback('El usuario seleccionado no esta vinculado al stock destino.', 'error');
      return;
    }

    this.setStockFeedback('', '');
    this.adminControl
      .receiveStockTransfer(transferId, { receivedByUserId: this.transferReceiverUserId })
      .subscribe({
        next: () => {
          this.setStockFeedback('Transferencia recibida.', 'success');
          this.loadStocksAndPosState();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.setStockFeedback(
            error?.error?.message || error?.message || 'No se pudo recibir la transferencia.',
            'error'
          );
        }
      });
  }

  openDamageModal(productId: number): void {
    const stockId = this.selectedStockId;
    if (!stockId) {
      return;
    }
    this.setStockFeedback('', '');
    this.stockDamageForm.stockId = stockId;
    this.stockDamageForm.productId = productId;
    this.stockDamageForm.qty = 1;
    this.stockDamageForm.reason = '';
    this.isStockDamageModalOpen = true;
  }

  closeDamageModal(): void {
    this.isStockDamageModalOpen = false;
  }

  registerDamage(): void {
    if (!this.hasPermission('stock_mark_damaged')) {
      return;
    }
    const { stockId, productId, qty, reason, reportedByUserId } = this.stockDamageForm;
    if (!stockId || !productId || qty <= 0 || !reason.trim()) {
      this.setStockFeedback('Completa stock, producto, cantidad y motivo.', 'error');
      return;
    }
    const stock = this.stocks.find((entry) => entry.id === stockId);
    if (!stock) {
      this.setStockFeedback('Selecciona un stock valido.', 'error');
      return;
    }
    const currentQty = stock.inventory[productId] ?? 0;
    if (currentQty < qty) {
      this.setStockFeedback(`Stock insuficiente para ${this.productName(productId)}.`, 'error');
      return;
    }
    this.setStockFeedback('', '');
    this.adminControl.registerStockDamage(stockId, {
      productId,
      qty,
      reason: reason.trim(),
      userId: reportedByUserId
    }).subscribe({
      next: () => {
        this.setStockFeedback('Dano registrado en inventario.', 'success');
        this.stockDamageForm.qty = 1;
        this.stockDamageForm.reason = '';
        this.closeDamageModal();
        this.loadStocksAndPosState();
      },
      error: (error: { error?: { message?: string }; message?: string }) => {
        this.setStockFeedback(
          error?.error?.message || error?.message || 'No se pudo registrar el dano de inventario.',
          'error'
        );
      }
    });
  }

  toggleStockUserLink(userId: number, enabled: boolean): void {
    if (enabled) {
      this.stockUserLinkDraft.add(userId);
      return;
    }
    this.stockUserLinkDraft.delete(userId);
  }

  isStockUserLinked(userId: number): boolean {
    return this.stockUserLinkDraft.has(userId);
  }

  isReceiverEligible(transfer: StockTransfer): boolean {
    const destination = this.stocks.find((stock) => stock.id === transfer.destinationStockId);
    if (!destination || !this.transferReceiverUserId) {
      return false;
    }
    return destination.linkedUserIds.includes(this.transferReceiverUserId);
  }

  movementQtyClass(movement: InventoryMovement): string {
    return this.movementSignedQty(movement) >= 0 ? 'text-accent' : 'text-red-600';
  }

  stockName(stockId: string): string {
    return this.stocks.find((stock) => stock.id === stockId)?.name ?? 'Sin stock';
  }

  customerName(customerId: number | null | undefined): string {
    if (!customerId) {
      return '-';
    }
    return this.customers.find((customer) => customer.id === customerId)?.name ?? `Usuario ${customerId}`;
  }

  productName(productId: number): string {
    return this.products.find((product) => product.id === productId)?.name ?? `Producto ${productId}`;
  }

  get availablePosProducts(): AdminProduct[] {
    const stockId = this.currentPosStock?.id;
    if (!stockId) {
      return [];
    }
    return this.products.filter((product) => product.active && this.stockQty(stockId, product.id) > 0);
  }

  stockQty(stockId: string, productId: number): number {
    const stock = this.stocks.find((entry) => entry.id === stockId);
    return stock?.inventory[productId] ?? 0;
  }

  setPosStock(stockId: string): void {
    this.posForm.stockId = stockId;
    this.syncPosSelectedItems();
    this.refreshPosCashControl();
  }

  updatePosCustomerSearch(value: string): void {
    this.posCustomerSearch = value;
    this.refreshPosCustomerRecommendations();
  }

  selectPublicGeneralCustomer(): void {
    this.selectedPosCustomerId = null;
    this.posCustomerSearch = 'Publico en General';
    this.posSelectedCustomerMonth = null;
    this.isLoadingPosCustomerProjection = false;
    this.refreshPosCustomerRecommendations();
  }

  selectPosCustomerRecommendation(customerId: number): void {
    const customer = this.customers.find((entry) => entry.id === customerId);
    if (!customer) {
      return;
    }
    this.selectedPosCustomerId = customer.id;
    this.posCustomerSearch = `${customer.name} · ${customer.email}`;
    this.refreshPosCustomerRecommendations();
    this.loadSelectedPosCustomerProjection();
  }

  togglePosProductSelection(productId: number, selected: boolean): void {
    const stockId = this.currentPosStock?.id;
    if (!stockId) {
      return;
    }
    if (selected) {
      const availableQty = this.stockQty(stockId, productId);
      if (availableQty <= 0) {
        return;
      }
      this.posItems.set(productId, Math.min(this.posItems.get(productId) ?? 1, availableQty));
      return;
    }
    this.posItems.delete(productId);
  }

  updatePosQty(productId: number, qtyRaw: string): void {
    const maxQty = this.stockQty(this.currentPosStock?.id ?? '', productId);
    const qty = Math.max(1, Math.min(maxQty || 1, Number(qtyRaw) || 1));
    if (!this.posItems.has(productId)) {
      return;
    }
    this.posItems.set(productId, qty);
  }

  getPosItems(): AdminOrderItem[] {
    return this.availablePosProducts
      .filter((product) => this.posItems.has(product.id))
      .map((product) => ({
        productId: product.id,
        name: product.name,
        price: product.price,
        quantity: this.posItems.get(product.id) ?? 1
      }));
  }

  registerPosSale(): void {
    if (!this.canRegisterPosSale || !this.currentPosStock) {
      return;
    }
    const lineItems = this.getPosItems();
    if (!lineItems.length) {
      return;
    }
    const stockError = this.validateStockAvailability(this.currentPosStock.id, lineItems);
    if (stockError) {
      this.setPosFeedback(stockError, 'error');
      return;
    }
    this.isRegisteringPosSale = true;
    this.setPosFeedback('', '');
    this.adminControl
      .registerPosSale({
        stockId: this.currentPosStock.id,
        customerId: this.selectedPosCustomer?.id,
        customerName: this.selectedPosCustomer?.name || 'Publico en General',
        paymentStatus: 'paid_branch',
        deliveryStatus: 'delivered_branch',
        items: lineItems
      })
      .pipe(finalize(() => (this.isRegisteringPosSale = false)))
      .subscribe({
        next: () => {
          this.posItems.clear();
          this.posForm.status = 'delivered';
          this.selectPublicGeneralCustomer();
          this.setPosFeedback('Venta registrada en caja.', 'success');
          this.adminControl.load().subscribe({
            next: () => this.loadStocksAndPosState(),
            error: () => this.loadStocksAndPosState()
          });
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.setPosFeedback(error?.error?.message || error?.message || 'No se pudo registrar la venta.', 'error');
        }
      });
  }

  createPosCashCut(): void {
    if (!this.canCreatePosCashCut || !this.currentPosStock) {
      return;
    }
    this.isCuttingPosCash = true;
    this.setPosFeedback('', '');
    this.adminControl
      .createPosCashCut({ stockId: this.currentPosStock.id })
      .pipe(finalize(() => (this.isCuttingPosCash = false)))
      .subscribe({
        next: ({ control }) => {
          this.posCashControl = {
            stockId: control.stockId,
            attendantUserId: control.attendantUserId ?? null,
            currentTotal: Number(control.currentTotal ?? 0),
            salesCount: Number(control.salesCount ?? 0),
            startedAt: control.startedAt,
            lastCutAt: control.lastCutAt,
            lastCutTotal: Number(control.lastCutTotal ?? 0),
            lastCutSalesCount: Number(control.lastCutSalesCount ?? 0),
            lastSaleAt: control.lastSaleAt
          };
          this.setPosFeedback('Corte de caja registrado.', 'success');
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.setPosFeedback(error?.error?.message || error?.message || 'No se pudo registrar el corte.', 'error');
        }
      });
  }

  private syncPosOperatorContext(): void {
    const linkedStocks = this.linkedPosStocks;
    if (!linkedStocks.length) {
      this.posForm.stockId = '';
      this.posItems.clear();
      this.posCashControl = null;
      this.refreshPosCustomerRecommendations();
      return;
    }
    if (!linkedStocks.some((stock) => stock.id === this.posForm.stockId)) {
      this.posForm.stockId = linkedStocks[0].id;
    }
    this.syncPosSelectedItems();
    this.refreshPosCustomerRecommendations();
  }

  private syncPosSelectedItems(): void {
    const stockId = this.posForm.stockId;
    if (!stockId) {
      this.posItems.clear();
      return;
    }
    for (const [productId, qty] of [...this.posItems.entries()]) {
      const available = this.stockQty(stockId, productId);
      if (available <= 0) {
        this.posItems.delete(productId);
        continue;
      }
      if (qty > available) {
        this.posItems.set(productId, available);
      }
    }
  }

  private normalizePosCustomerSearch(value: string): string {
    return (value ?? '').trim().toLowerCase();
  }

  private refreshPosCustomerRecommendations(): void {
    const query = this.normalizePosCustomerSearch(this.posCustomerSearch);
    const base = this.customers.map((customer) => ({
      id: customer.id,
      name: customer.name,
      email: customer.email,
      label: `${customer.name} · ${customer.email}`
    }));
    this.posCustomerRecommendations = (!query || query === this.normalizePosCustomerSearch('Publico en General')
      ? base
      : base.filter((candidate) => this.normalizePosCustomerSearch(`${candidate.name} ${candidate.email}`).includes(query))
    ).slice(0, 8);
  }

  private loadSelectedPosCustomerProjection(): void {
    const customer = this.selectedPosCustomer;
    if (!customer) {
      this.posSelectedCustomerMonth = null;
      return;
    }
    this.isLoadingPosCustomerProjection = true;
    this.adminControl
      .getAssociateMonth(String(customer.id), this.currentMonthKey())
      .pipe(
        finalize(() => (this.isLoadingPosCustomerProjection = false)),
        catchError(() =>
          of({
            associateId: String(customer.id),
            monthKey: this.currentMonthKey(),
            netVolume: 0,
            isActive: false
          })
        )
      )
      .subscribe((month) => {
        this.posSelectedCustomerMonth = {
          associateId: String(month.associateId),
          monthKey: month.monthKey,
          netVolume: Number(month.netVolume ?? 0),
          isActive: Boolean(month.isActive)
        };
      });
  }

  private refreshPosCashControl(): void {
    const stockId = this.currentPosStock?.id;
    if (!stockId) {
      this.posCashControl = null;
      return;
    }
    this.adminControl
      .getPosCashControl(stockId)
      .pipe(catchError(() => of(null)))
      .subscribe((control) => {
        if (!control) {
          this.posCashControl = null;
          return;
        }
        this.posCashControl = {
          stockId: control.stockId,
          attendantUserId: control.attendantUserId ?? null,
          currentTotal: Number(control.currentTotal ?? 0),
          salesCount: Number(control.salesCount ?? 0),
          startedAt: control.startedAt,
          lastCutAt: control.lastCutAt,
          lastCutTotal: Number(control.lastCutTotal ?? 0),
          lastCutSalesCount: Number(control.lastCutSalesCount ?? 0),
          lastSaleAt: control.lastSaleAt
        };
      });
  }

  private parseCustomerDiscountRate(customer: AdminCustomer): number {
    const match = String(customer.discount ?? '').match(/(\d+(?:\.\d+)?)\s*%/);
    if (!match) {
      return 0;
    }
    const value = Number(match[1]);
    return Number.isFinite(value) ? value / 100 : 0;
  }

  private calculateDiscountTierRate(volume: number): number {
    const tiers = this.businessConfig?.rewards?.discountTiers ?? [];
    for (const tier of tiers) {
      const min = Number(tier.min ?? 0);
      const max = tier.max == null ? null : Number(tier.max);
      const rate = Number(tier.rate ?? 0);
      if (volume >= min && (max == null || volume <= max)) {
        return Number.isFinite(rate) ? rate : 0;
      }
    }
    return 0;
  }

  private currentMonthKey(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  private roundMoney(value: number): number {
    return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
  }

  private setPosFeedback(message: string, tone: 'error' | 'success' | ''): void {
    this.posFeedbackMessage = message;
    this.posFeedbackTone = tone;
    this.requestViewUpdate();
  }

  private setStockFeedback(message: string, tone: 'error' | 'success' | ''): void {
    this.stockFeedbackMessage = message;
    this.stockFeedbackTone = tone;
    this.requestViewUpdate();
  }

  private setShippingError(message: string): void {
    this.shippingError = message;
    this.requestViewUpdate();
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }

  private resolveUiErrorMessage(error: unknown, fallback: string): string {
    if (typeof error === 'string' && error.trim()) {
      return error.trim();
    }
    if (!error || typeof error !== 'object') {
      return fallback;
    }

    const candidate = error as {
      message?: unknown;
      error?: unknown;
      body?: unknown;
    };

    if (typeof candidate.message === 'string' && candidate.message.trim()) {
      return candidate.message.trim();
    }

    const nested = candidate.error;
    if (typeof nested === 'string' && nested.trim()) {
      try {
        const parsed = JSON.parse(nested) as { message?: unknown; body?: unknown };
        if (typeof parsed.message === 'string' && parsed.message.trim()) {
          return parsed.message.trim();
        }
        if (typeof parsed.body === 'string' && parsed.body.trim()) {
          const parsedBody = JSON.parse(parsed.body) as { message?: unknown };
          if (typeof parsedBody.message === 'string' && parsedBody.message.trim()) {
            return parsedBody.message.trim();
          }
        }
      } catch {
        return nested.trim();
      }
    }

    if (nested && typeof nested === 'object') {
      const nestedRecord = nested as { message?: unknown; body?: unknown };
      if (typeof nestedRecord.message === 'string' && nestedRecord.message.trim()) {
        return nestedRecord.message.trim();
      }
      if (typeof nestedRecord.body === 'string' && nestedRecord.body.trim()) {
        try {
          const parsedBody = JSON.parse(nestedRecord.body) as { message?: unknown };
          if (typeof parsedBody.message === 'string' && parsedBody.message.trim()) {
            return parsedBody.message.trim();
          }
        } catch {
          return nestedRecord.body.trim();
        }
      }
    }

    if (typeof candidate.body === 'string' && candidate.body.trim()) {
      try {
        const parsedBody = JSON.parse(candidate.body) as { message?: unknown };
        if (typeof parsedBody.message === 'string' && parsedBody.message.trim()) {
          return parsedBody.message.trim();
        }
      } catch {
        return candidate.body.trim();
      }
    }

    return fallback;
  }

  saveBusinessConfig(): void {
    if (!this.hasPermission('config_manage')) {
      return;
    }
    this.isSavingBusinessConfig = true;
    this.businessConfigMessage = '';
    const configToSave = this.normalizeBusinessConfigForSave(this.businessConfigDraft);
    this.businessConfigDraft = structuredClone(configToSave);
    this.adminControl
      .saveBusinessConfig({ config: structuredClone(configToSave) })
      .pipe(finalize(() => (this.isSavingBusinessConfig = false)))
      .subscribe({
        next: (config) => {
          this.businessConfigDraft = this.normalizeBusinessConfigDraft(config);
          this.businessConfigMessage = 'Configuracion guardada.';
        },
        error: () => {
          this.businessConfigMessage = 'No se pudo guardar la configuracion.';
        }
      });
  }

  restoreBusinessConfigDefaults(): void {
    if (!this.hasPermission('config_manage')) {
      return;
    }
    this.businessConfigDraft = this.normalizeBusinessConfigDraft(this.getDefaultBusinessConfig());
    this.businessConfigMessage = 'Se cargaron valores por defecto locales. Guarda para aplicar.';
  }

  private syncBusinessConfigDraft(): void {
    const inlineConfig = this.businessConfig;
    if (inlineConfig) {
      this.businessConfigDraft = this.normalizeBusinessConfigDraft(inlineConfig);
      return;
    }
    this.adminControl.getBusinessConfig().subscribe({
      next: (config) => {
        this.businessConfigDraft = this.normalizeBusinessConfigDraft(config);
      }
    });
  }

  private normalizeBusinessConfigDraft(config: AppBusinessConfig): AppBusinessConfig {
    const draft = structuredClone(config);
    draft.rewards.discountTiers = this.normalizeDiscountTiers(draft.rewards.discountTiers, false);
    this.normalizeBusinessConfigSelectValues(draft);
    return draft;
  }

  private normalizeBusinessConfigForSave(config: AppBusinessConfig): AppBusinessConfig {
    const next = structuredClone(config);
    next.rewards.discountTiers = this.normalizeDiscountTiers(next.rewards.discountTiers, true);
    this.normalizeBusinessConfigSelectValues(next);
    return next;
  }

  private normalizeBusinessConfigSelectValues(config: AppBusinessConfig): void {
    config.rewards.cutRule = this.ensureAllowedConfigValue(
      config.rewards.cutRule,
      this.rewardCutRuleOptions,
      'hard_cut_no_pass'
    );
    config.pos.defaultPaymentStatus = this.ensureAllowedConfigValue(
      config.pos.defaultPaymentStatus,
      this.posPaymentStatusConfigOptions,
      'paid_branch'
    );
    config.pos.defaultDeliveryStatus = this.ensureAllowedConfigValue(
      config.pos.defaultDeliveryStatus,
      this.posDeliveryStatusConfigOptions,
      'delivered_branch'
    );
    config.pos.orderStatusByDeliveryStatus.delivered_branch = this.ensureAllowedConfigValue(
      config.pos.orderStatusByDeliveryStatus.delivered_branch,
      this.posOrderStatusMappingConfigOptions,
      'delivered'
    );
    config.pos.orderStatusByDeliveryStatus.paid_branch = this.ensureAllowedConfigValue(
      config.pos.orderStatusByDeliveryStatus.paid_branch,
      this.posOrderStatusMappingConfigOptions,
      'paid'
    );
  }

  private normalizeDiscountTiers(tiers: DiscountTierDraft[], sortByMin: boolean): DiscountTierDraft[] {
    const fallback = this.getDefaultBusinessConfig().rewards.discountTiers;
    const source = Array.isArray(tiers) && tiers.length ? tiers : fallback;
    const normalized = source.map((tier) => ({
      min: this.parseNonNegativeNumber(tier?.min),
      max: null,
      rate: this.normalizeDiscountRateValue(tier?.rate)
    }));
    const ordered = sortByMin ? [...normalized].sort((left, right) => left.min - right.min) : normalized;
    return ordered.map((tier, index) => {
      const nextMin = ordered[index + 1]?.min;
      return {
        ...tier,
        max: Number.isFinite(nextMin) && nextMin > tier.min ? nextMin - 1 : null
      };
    });
  }

  private refreshDiscountTierThresholds(): void {
    this.businessConfigDraft.rewards.discountTiers = this.normalizeDiscountTiers(
      this.businessConfigDraft.rewards.discountTiers ?? [],
      false
    );
  }

  private parseNonNegativeNumber(value: unknown): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return 0;
    }
    return this.roundMoney(parsed);
  }

  private normalizeDiscountRateValue(value: unknown): number {
    const parsed = this.parseNonNegativeNumber(value);
    const normalized = parsed > 1 ? parsed / 100 : parsed;
    return Math.min(1, this.roundMoney(normalized));
  }

  private ensureAllowedConfigValue<T extends string | number>(
    value: unknown,
    options: Array<ExplainedSelectOption<T>>,
    fallback: T
  ): T {
    const matched = options.find((option) => String(option.value) === String(value));
    return matched?.value ?? fallback;
  }

  private buildSelectTooltip(options: Array<ExplainedSelectOption<string>>): string {
    return options.map((option) => `${option.label}: ${option.description}`).join('\n');
  }

  private getDefaultBusinessConfig(): AppBusinessConfig {
    return {
      version: 'app-v1',
      rewards: {
        version: 'v1',
        activationNetMin: 2500,
        discountTiers: [
          { min: 3600, max: 8000, rate: 0.3 },
          { min: 8001, max: 12000, rate: 0.4 },
          { min: 12001, max: null, rate: 0.5 }
        ],
        commissionByDepth: { '1': 0.1, '2': 0.05, '3': 0.03 },
        payoutDay: 10,
        cutRule: 'hard_cut_no_pass'
      },
      orders: {
        requireStockOnShipped: true,
        requireDispatchLinesOnShipped: true
      },
      pos: {
        defaultCustomerName: 'Publico en General',
        defaultPaymentStatus: 'paid_branch',
        defaultDeliveryStatus: 'delivered_branch',
        orderStatusByDeliveryStatus: {
          delivered_branch: 'delivered',
          paid_branch: 'paid'
        }
      },
      stocks: {
        requireLinkedUserForTransferReceive: true
      },
      adminWarnings: {
        showCommissions: true,
        showShipping: true,
        showPendingPayments: true,
        showPendingTransfers: true,
        showPosSalesToday: true
      }
    };
  }

  private resolveDispatchLines(order: AdminOrder): AdminOrderItem[] {
    const existingLines = Array.isArray(order.items) ? order.items : [];
    if (existingLines.length) {
      return existingLines;
    }
    if (!this.shippingFallbackProductId || this.shippingFallbackQty <= 0) {
      return [];
    }
    const product = this.products.find((entry) => entry.id === this.shippingFallbackProductId);
    if (!product) {
      return [];
    }
    const lines: AdminOrderItem[] = [
      {
        productId: product.id,
        name: product.name,
        price: product.price,
        quantity: this.shippingFallbackQty
      }
    ];
    return lines;
  }

  private validateStockAvailability(stockId: string, lines: AdminOrderItem[]): string {
    for (const item of lines) {
      const currentQty = this.stockQty(stockId, item.productId);
      if (currentQty < item.quantity) {
        return `Stock insuficiente para ${this.productName(item.productId)}.`;
      }
    }
    return '';
  }

  private normalizeTransferLines(lines: Array<{ productId: number | null; qty: number }>): StockTransferLine[] {
    const grouped = new Map<number, number>();
    for (const line of lines) {
      if (!line.productId) {
        continue;
      }
      const qty = Math.floor(Number(line.qty));
      if (!Number.isFinite(qty) || qty <= 0) {
        continue;
      }
      grouped.set(line.productId, (grouped.get(line.productId) ?? 0) + qty);
    }
    return Array.from(grouped.entries()).map(([productId, qty]) => ({ productId, qty }));
  }

  private movementTypeLabel(type: InventoryMovementType): string {
    if (type === 'entry') {
      return 'Entrada';
    }
    if (type === 'exit_order') {
      return 'Salida por envio';
    }
    if (type === 'exit_transfer') {
      return 'Salida por transferencia';
    }
    if (type === 'entry_transfer') {
      return 'Entrada por transferencia';
    }
    if (type === 'damaged') {
      return 'Dano';
    }
    return 'Salida por venta POS';
  }

  private movementSignedQty(movement: InventoryMovement): number {
    if (movement.type === 'entry' || movement.type === 'entry_transfer') {
      return movement.qty;
    }
    return movement.qty * -1;
  }

  private structureNodeLabel(name?: string): string {
    const value = (name ?? '').trim();
    if (!value) {
      return 'Cliente';
    }
    const first = value.split(' ')[0] ?? value;
    return first.slice(0, 6);
  }

  private buildReferralMap(customers: AdminCustomer[]): Map<number, AdminCustomer[]> {
    const map = new Map<number, AdminCustomer[]>();
    customers.forEach((customer) => {
      if (customer.leaderId == null) {
        return;
      }
      const entries = map.get(customer.leaderId) ?? [];
      entries.push(customer);
      map.set(customer.leaderId, entries);
    });
    return map;
  }

  private buildColumnPositions(count: number, x: number, top = 50, bottom = 170): { x: number; y: number }[] {
    if (count <= 0) {
      return [];
    }
    if (count === 1) {
      return [{ x, y: (top + bottom) / 2 }];
    }
    const spacing = (bottom - top) / (count - 1);
    return Array.from({ length: count }, (_, index) => ({
      x,
      y: top + spacing * index
    }));
  }

  private getMonthlySpendByCustomerName(date = new Date()): Map<string, number> {
    const month = date.getMonth();
    const year = date.getFullYear();
    const totals = new Map<string, number>();

    for (const order of this.orders) {
      if (!order.createdAt) {
        continue;
      }
      const orderDate = new Date(order.createdAt);
      if (Number.isNaN(orderDate.getTime())) {
        continue;
      }
      if (orderDate.getMonth() !== month || orderDate.getFullYear() !== year) {
        continue;
      }
      const key = this.normalizeCustomerKey(order.customer);
      if (!key) {
        continue;
      }
      const total = Number(order.total) || 0;
      totals.set(key, (totals.get(key) ?? 0) + total);
    }

    return totals;
  }

  private normalizeCustomerKey(name?: string): string {
    return (name ?? '').trim().toLowerCase();
  }

}




