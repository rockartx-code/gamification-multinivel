import * as XLSX from 'xlsx';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject, type Signal } from '@angular/core';
import { ConciliacionService } from '../../services/conciliacion.service'; // WP-H
import { ConciliacionCorrida, ConciliacionPayload, ConciliacionResultado } from '../../models/suscripcion.model'; // WP-H
import { fechaEnLetras, mesEnLetras, textoEstadoPedido, textoMetodoPago } from '../../models/vocabulario.model'; // paquete G · ronda 26
import { DomSanitizer, type SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { Observable, catchError, finalize, forkJoin, map, of, switchMap } from 'rxjs';

import { AuthService, AuthUser } from '../../services/auth.service';
import {
  AdminCustomer,
  AdminData,
  AdminCampaign,
  AppBusinessConfig,
  Coupon,
  SaveCouponPayload,
  AdminOrder,
  AdminOrderItem,
  AssociateMonth,
  AdminProduct,
  AdminWarning,
  AssetResponse,
  BonusCondition,
  BonusConditionType,
  BonusConfig,
  BonusReward,
  BonusRewardType,
  BonusRule,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  AdminRefundPayload,
  AdminReturnInspectPayload,
  CreateStructureCustomerPayload,
  CustomerDocument,
  CustomerDocumentTypeConfig,
  CustomerProfile,
  ProductCategory,
  ProductVariant,
  RankThreshold,
  VpConfig,
  UpdateCustomerPayload
} from '../../models/admin.model';
import { AdminEmployee } from '../../models/employee.model';
import { PortalNotification } from '../../models/portal-notification.model';
import {
  ADMIN_ROUTE_BY_VIEW,
  AdminMenuEntry,
  adminMenuVisible,
  AdminViewId,
  AppPrivilege,
  normalizePrivileges,
  UserPrivileges
} from '../../models/privileges.model';
import { AccesoPantallaService } from '../../services/acceso-pantalla.service';
import { UiAvisoSinAccesoComponent } from '../../components/ui-aviso-sin-acceso/ui-aviso-sin-acceso.component';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiCheckboxComponent } from '../../components/ui-checkbox/ui-checkbox.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';
import { UiKpiCardComponent } from '../../components/ui-kpi-card/ui-kpi-card.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { SidebarLink, UiSidebarNavComponent } from '../../components/ui-sidebar-nav/ui-sidebar-nav.component';
import { UiStatusBadgeComponent } from '../../components/ui-status-badge/ui-status-badge.component';
import { UiDataTableComponent } from '../../components/ui-data-table/ui-data-table.component';
import { UiNetworkGraphComponent } from '../../components/ui-networkgraph/ui-networkgraph.component';
import { UiPaginationComponent } from '../../components/ui-pagination/ui-pagination.component';
import { AdminControlService } from '../../services/admin-control.service';
import { ApiService } from '../../services/api.service';
import { AdminCampaignsComponent } from './admin-campaigns/admin-campaigns.component';
import { AdminCategoriesComponent } from './admin-categories/admin-categories.component';
import { PagosMesComponent } from './pagos-mes/pagos-mes.component'; // WP-A
import { PagosService } from '../../services/pagos.service'; // WP-A · propuesta 17
import { PagoPeriodo } from '../../models/pagos.model'; // WP-A · propuesta 17
import { AdminArqueoComponent } from './arqueo/admin-arqueo.component'; // WP-E
import { CajaService } from '../../services/caja.service'; // WP-E
import { AbonoCajaRespuesta, AnulacionCajaRespuesta, VentaCajaRespuesta } from '../../models/caja.model'; // WP-E
import { HonorBoard, HonorEntry } from '../../models/user-dashboard.model';
import { AdminModoClienteComponent } from './modo-cliente/admin-modo-cliente.component'; // WP-B
import { FacturaPedidoComponent } from './checkout/factura-pedido.component'; // WP-C
import { ESTADOS_MX_OPTIONS } from '../../constants/states-mx'; // WP-C
import { CheckoutService } from '../../services/checkout.service'; // WP-C
import { FacturaEmitida } from '../../models/checkout.model'; // WP-C
import { DespachoService } from '../../services/despacho.service'; // WP-D
import { UiConfirmComponent } from '../../components/ui-confirm/ui-confirm.component'; // WP-I1
import { UiTablaDescuentoComponent } from '../../components/ui-tabla-descuento/ui-tabla-descuento.component'; // WP-I1
import { UiDesgloseIvaComponent } from '../../components/ui-desglose-iva/ui-desglose-iva.component'; // paquete B · ronda 26
import { UiClabeFormComponent } from '../../components/ui-clabe-form/ui-clabe-form.component'; // paquete A · ronda 26
import { PlanSocioService } from '../../services/plan-socio.service'; // paquete B · ronda 26 (tasa de IVA)

/** Diálogo de confirmación genérico del back office (I1): un solo `ui-confirm` para todas las acciones. */
/**
 * Paquete E · ronda 26 · Una entrada del menú del back office: su URL propia,
 * la vista que monta (si vive dentro del caparazón) y el privilegio que exige.
 * Se escribe una sola vez y la reusan la barra lateral y la barra del móvil.
 */
/** Pestañas del bloque de reportes (guarda 14: la lista vive en el componente). */
type StatsReportTabId = 'resumen' | 'pedidos' | 'clientes' | 'productos' | 'stocks';

type ConfirmacionAdmin = {
  title: string;
  effect: string;
  requireReason: boolean;
  reasonLabel?: string;
  reasonPlaceholder?: string;
  confirmLabel: string;
  danger: boolean;
  busy: boolean;
  error: string;
  result: string | null;
  resultTitle?: string;
  /** Recibe el motivo escrito y hace la llamada; al terminar debe llamar a `confirmacionLista`/`confirmacionFallo`. */
  ejecutar: (motivo: string) => void;
};

/** Línea del traspaso que se está recibiendo: lo enviado y lo que realmente llegó. */
type LineaRecepcion = { productId: number | string; name: string; sent: number; received: number };

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
  allowPickup?: boolean;
  isMainWarehouse?: boolean;
  city?: string;   // paquete C
  state?: string;  // paquete C
};

/** Una fila de la tabla producto × sucursal de Stocks (paquete F · ronda 26). */
type InventarioPorSucursalFila = {
  productId: number;
  productName: string;
  /** Mínimo del producto (el suyo o el de la configuración). 0 = no se vigila. */
  minStock: number;
  /** Piezas sumando todas las sucursales. */
  total: number;
  porSucursal: Array<{ stockId: string; stockName: string; qty: number; bajoMinimo: boolean }>;
  bajoMinimo: boolean;
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
  cashierDiscountAmount?: number;
  total: number;
  paymentStatus: 'paid_branch' | 'partial_branch' | 'credit_branch';
  deliveryStatus: 'paid_branch' | 'delivered_branch';
  paymentMethod?: 'cash' | 'card' | 'transfer' | 'mixed';
  createdAt: string;
  lines: AdminOrderItem[];
  cashCutId?: string;
  status?: string;
  voidReason?: string;
  paymentType?: 'full' | 'partial' | 'credit';
  amountPaid?: number;
  pendingAmount?: number;
};

type PosCashCut = {
  id: string;
  stockId: string;
  attendantUserId?: number | null;
  total: number;
  salesCount: number;
  cashToKeep?: number;
  withdrawnAmount?: number;
  totalWithdrawals?: number;
  startedAt?: string;
  endedAt?: string;
  createdAt?: string;
  sales?: PosSale[];
  withdrawals?: PosWithdrawal[];
  // paquete E: arqueo
  cashExpected?: number;
  cashCounted?: number;
  difference?: number;
  differenceReason?: string;
  withdrawalReceiver?: string;
  openingCash?: number;
};

type PosWithdrawal = {
  id: string;
  stockId: string;
  attendantUserId?: number | null;
  amount: number;
  reason: string;
  createdAt?: string;
};

type PosCashControl = {
  stockId: string;
  attendantUserId: number | null;
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
  userName?: string;
  paymentMethod?: 'cash' | 'card' | 'transfer';
  reason?: string;
  referenceId?: string;
};

type CustomerPrivilegeOption = {
  key: AppPrivilege;
  label: string;
  /** Qué concede en la práctica. Sin esto hay que adivinar por el nombre. */
  description: string;
  /** Agrupa la lista por área para no leer 27 casillas seguidas. */
  group: 'Acceso a pantallas' | 'Pedidos' | 'Catálogo' | 'Inventario' | 'Personas y dinero' | 'Sistema';
  /** Permiso de pantalla sin el cual este no sirve de nada. */
  requires?: AppPrivilege;
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
type CommissionLevelDraft = AppBusinessConfig['rewards']['commissionLevels'][number];

type ReceiveReturnCheck = 'coincide_con_pedido' | 'trazabilidad_valida' | 'empaque_original' | 'sellos_intactos' | 'sin_uso' | 'danio_no_empresa';
const RECEIVE_RETURN_CHECKLIST_DEFAULT: Record<ReceiveReturnCheck, boolean> = {
  coincide_con_pedido: true, trazabilidad_valida: true, empaque_original: true, sellos_intactos: true, sin_uso: true, danio_no_empresa: false
};

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, UiAvisoSinAccesoComponent, UiButtonComponent, UiCheckboxComponent, UiFormFieldComponent, UiModalComponent, UiKpiCardComponent, UiHeaderComponent, UiFooterComponent, UiSidebarNavComponent, UiStatusBadgeComponent, UiDataTableComponent, UiNetworkGraphComponent, AdminCampaignsComponent, AdminCategoriesComponent, UiPaginationComponent, PagosMesComponent /* WP-A */, AdminModoClienteComponent /* WP-B */, FacturaPedidoComponent /* WP-C */, AdminArqueoComponent /* WP-E */, UiConfirmComponent /* WP-I1 */, UiTablaDescuentoComponent /* WP-I1 */, UiDesgloseIvaComponent /* paquete B · ronda 26 */, UiClabeFormComponent /* paquete A · ronda 26 */],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  private readonly adminData: Signal<AdminData | null>;
  private adminNavLinksCache: { user: AuthUser | null; links: SidebarLink[]; entries: AdminMenuEntry[] } | null = null;
  private customerOptionsCache: { customersRef: AdminCustomer[]; options: Array<SelectOption<number>> } | null = null;
  private employeeOptionsCache: { employeesRef: AdminEmployee[]; options: Array<SelectOption<number>> } | null = null;
  private stockOptionsCache: { stocksRef: AdminStock[]; options: Array<SelectOption<string>> } | null = null;
  private productOptionsCache: { productsRef: AdminProduct[]; options: Array<SelectOption<number>> } | null = null;
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
        employeesRef: AdminEmployee[];
        rows: Array<
          InventoryMovement & { stockName: string; productName: string; userName: string; typeLabel: string; signedQty: number }
        >;
      }
    | null = null;
  private inventarioPorSucursalCache:
    | {
        stocksRef: AdminStock[];
        productsRef: AdminProduct[];
        minimosRef: Record<string, number>;
        rows: InventarioPorSucursalFila[];
      }
    | null = null;
  private warningsCache: { warningsRef: AdminWarning[]; warnings: AdminWarning[] } | null = null;
  /**
   * Paquete G · ronda 26 (propuesta 25), montado en la integración.
   *
   * Los textos ya no se escriben aquí: salen de `ESTADOS_PEDIDO`, la tabla
   * única de §3.7. Antes esta lista decía "Pendiente", "Por devolver" y
   * "Devuelto" mientras el resto del producto decía otra cosa para el mismo
   * pedido, y de aquí salía además el nombre de la pestaña.
   */
  private readonly orderStatusOptionsValue: Array<SelectOption<AdminOrder['status']>> =
    (['pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded',
      'en_devolucion', 'devuelto_validado', 'devolucion_rechazada'] as Array<AdminOrder['status']>)
      .map((value) => ({ value, label: textoEstadoPedido(value) }));

  /**
   * Paquete E · ronda 26 · La tira de pestañas de Pedidos, fuera de la plantilla.
   *
   * Estaba escrita como literal dentro de un `*ngFor`: la aplicación es zoneless
   * y cada escucha agenda una pasada de detección, así que el arreglo se creaba
   * de nuevo y sus nodos se recreaban en cada pasada — el clic salía del botón
   * antes de llegar a `toggleOrderDetail()`. Ocho reproducciones entre dos
   * empleados. Ahora es un campo `readonly` con `trackBy` por clave.
   *
   * "Factura solicitada" es la bandeja de la propuesta 20: filtra en memoria
   * sobre los pedidos ya cargados (nunca con el filtro del servidor, que
   * rompería la lógica de secciones cargadas de `admin-control.service`).
   */
  readonly orderTabs: ReadonlyArray<{ key: string; status?: AdminOrder['status']; label: string }> = [
    { key: 'pending', status: 'pending', label: textoEstadoPedido('pending') },
    { key: 'paid', status: 'paid', label: textoEstadoPedido('paid') },
    { key: 'shipped', status: 'shipped', label: textoEstadoPedido('shipped') },
    { key: 'delivered', status: 'delivered', label: textoEstadoPedido('delivered') },
    { key: 'factura_solicitada', label: 'Factura solicitada' },
    { key: 'cancelled', status: 'cancelled', label: textoEstadoPedido('cancelled') },
    { key: 'refunded', status: 'refunded', label: textoEstadoPedido('refunded') },
    { key: 'en_devolucion', status: 'en_devolucion', label: textoEstadoPedido('en_devolucion') },
    { key: 'devuelto_validado', status: 'devuelto_validado', label: textoEstadoPedido('devuelto_validado') },
    { key: 'devolucion_rechazada', status: 'devolucion_rechazada', label: textoEstadoPedido('devolucion_rechazada') }
  ];

  /** Pestaña encendida: una clave de estado o la bandeja de facturas. */
  currentOrderTab = 'pending';

  trackOrderTab(_index: number, tab: { key: string }): string {
    return tab.key;
  }
  readonly rewardCutRuleOptions: Array<ExplainedSelectOption<string>> = [
    {
      value: 'dynamic_compression',
      label: 'Compresión dinámica',
      description: 'Salta posiciones no calificadas y paga la comisión al siguiente ascendente calificado (Plan abril 2026).'
    },
    {
      value: 'hard_cut_no_pass',
      label: 'Corte estricto mensual',
      description: 'Bloquea la comisión si el beneficiario no califica, sin traspasarla a otro ascendente.'
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
  readonly posOrderPaymentMethodOptions: Array<SelectOption<'cash' | 'card' | 'transfer' | 'mixed'>> = [
    { value: 'cash', label: 'Efectivo' },
    { value: 'card', label: 'Tarjeta' },
    { value: 'transfer', label: 'Transferencia' },
    { value: 'mixed', label: 'Efectivo + tarjeta/transferencia' }
  ];
  readonly posMixedSecondMethodOptions: Array<SelectOption<'card' | 'transfer'>> = [
    { value: 'card', label: 'Tarjeta' },
    { value: 'transfer', label: 'Transferencia' }
  ];
  readonly posSettleMethodOptions: Array<SelectOption<'cash' | 'card' | 'transfer'>> = [
    { value: 'cash', label: 'Efectivo' },
    { value: 'card', label: 'Tarjeta' },
    { value: 'transfer', label: 'Transferencia' }
  ];
  readonly rewardCutRuleTooltip = this.buildSelectTooltip(this.rewardCutRuleOptions);
  readonly posPaymentStatusConfigTooltip = this.buildSelectTooltip(this.posPaymentStatusConfigOptions);
  readonly posDeliveryStatusConfigTooltip = this.buildSelectTooltip(this.posDeliveryStatusConfigOptions);
  readonly posOrderStatusMappingConfigTooltip = this.buildSelectTooltip(this.posOrderStatusMappingConfigOptions);

  constructor(
    private readonly adminControl: AdminControlService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly route: ActivatedRoute, // paquete E · ronda 26: la vista viene de la URL
    private readonly acceso: AccesoPantallaService, // paquete E · ronda 26: el aviso de pantalla negada

    private readonly cdr: ChangeDetectorRef,
    private readonly api: ApiService,
    private readonly sanitizer: DomSanitizer,
    private readonly checkoutService: CheckoutService, // WP-C
    private readonly caja: CajaService // WP-E
  ) {
    this.adminData = toSignal(this.adminControl.data$, { initialValue: null });
  }

  currentView: AdminViewId = 'orders';

  // --- Cupones (H7) ---
  coupons: Coupon[] = [];
  couponsLoading = false;
  couponsError = '';
  couponFeedback = '';
  couponDraft: SaveCouponPayload = this.emptyCouponDraft();
  couponEditingCode: string | null = null;
  readonly couponTypeOptions: ReadonlyArray<{ value: string; label: string }> = [
    { value: 'percent', label: 'Porcentaje (%)' },
    { value: 'fixed', label: 'Monto fijo ($)' }
  ];
  currentOrderStatus: AdminOrder['status'] = 'pending';
  /** Mes que abre Pagos del mes al llegar desde un aviso (WP-A). */
  pagosMesMonth = '';
  orderStockFilter: string = '';
  expandedOrderDetailId: string | null = null;
  isActionsModalOpen = false;
  isNewOrderModalOpen = false;
  /** Aviso dentro del modal de nuevo pedido (p. ej. fallo al cargar listas). */
  newOrderMessage = '';
  isAddStructureModalOpen = false;
  isShippingModalOpen = false;
  isReceiptModalOpen = false;
  isUploadingReceipt = false;

  // Refund modal (from cancelled or devuelto_validado)
  isRefundModalOpen = false;
  refundTargetOrder: AdminOrder | null = null;
  refundReceiptBase64 = '';
  refundReceiptName = '';
  refundReason = '';
  refundError = '';
  isSavingRefund = false;

  // Receive return modal (from en_devolucion)
  isReceiveReturnModalOpen = false;
  receiveReturnOrder: AdminOrder | null = null;
  receiveReturnImages: Array<{ contentBase64: string; fileName: string; contentType: string }> = [];
  receiveReturnError = '';
  isSavingReceiveReturn = false;

  // Reject return modal (from devuelto_validado)
  isRejectReturnModalOpen = false;
  rejectReturnOrder: AdminOrder | null = null;
  rejectReturnReason = '';
  rejectReturnError = '';
  isSavingRejectReturn = false;

  readonly PAGE_SIZE = 15;
  readonly ORDER_PAGE_SIZE = 10;

  orderSearch = '';
  orderPage = 0;
  /**
   * Paquete F · ronda 26 (propuesta 21), montado en la integración sobre la
   * región de Pedidos, que es de E.
   *
   * "1 pedido pagado sin envío · 37 días" decía el aviso, y en la tabla no
   * había manera de saber cuál. La columna de antigüedad se puede ordenar y
   * se pinta en rojo desde `agingRedDays` (7 por omisión). El reloj es el del
   * servidor (§3.6): con el mundo en 2027 y el navegador en 2026, medirlo con
   * `new Date()` daba números imposibles.
   */
  orderAgingSort: 'none' | 'desc' | 'asc' = 'none';
  customerSearch = '';
  customerPage = 0;
  productSearch = '';
  productPage = 0;
  employeeSearch = '';
  employeePage = 0;
  notificationSearch = '';
  notificationPage = 0;

  selectedCustomer: AdminCustomer | null = null;
  selectedCustomerProfile: CustomerProfile | null = null;
  selectedCustomerAdminAccess = false;
  selectedCustomerPrivilegeDraft: UserPrivileges = {};
  selectedCustomerLeaderId = '';
  selectedCustomerSponsorSearch = '';
  selectedCustomerSponsorRecommendations: Array<{ id: string; name: string; email: string; label: string }> = [];
  customerDocumentFile: File | null = null;
  customerDocumentName = '';
  customerDocumentError = '';
  customerDocumentMessage = '';
  isCustomerDocumentMessageError = false;
  isLoadingSelectedCustomerProfile = false;
  isUploadingCustomerDocument = false;
  selectedSponsorLabel = 'FindingU (sin patrocinador)';
  hasValidSelectedSponsorId = true;
  canSaveSelectedCustomerPosition = false;
  isChangingSponsor = false;
  isSavingCustomerPrivileges = false;
  isSavingCustomerPosition = false;
  readonly customerPrivilegeOptions: CustomerPrivilegeOption[] = [
    // Pantallas: sin estos, los permisos de acción de abajo no se pueden ejercer.
    { key: 'access_screen_orders', label: 'Ver Pedidos', group: 'Acceso a pantallas',
      description: 'Entra a la sección Pedidos. Verá el nombre del cliente y el importe.' },
    { key: 'access_screen_customers', label: 'Ver Clientes', group: 'Acceso a pantallas',
      description: 'Entra a la sección Clientes: datos de contacto, red y comisiones.' },
    { key: 'access_screen_products', label: 'Ver Productos', group: 'Acceso a pantallas',
      description: 'Entra al catálogo. Verá precios y márgenes.' },
    { key: 'access_screen_stocks', label: 'Ver Stocks', group: 'Acceso a pantallas',
      description: 'Entra a inventario, transferencias y daños.' },
    { key: 'access_screen_pos', label: 'Ver Punto de Venta', group: 'Acceso a pantallas',
      description: 'Entra al mostrador para cobrar en tienda.' },
    { key: 'access_screen_stats', label: 'Ver Estadísticas', group: 'Acceso a pantallas',
      description: 'Entra a los informes de ventas de todo el negocio.' },
    { key: 'access_screen_settings', label: 'Ver Configuración', group: 'Acceso a pantallas',
      description: 'Entra a las reglas del negocio: comisiones, rangos y bonos.' },
    { key: 'access_screen_employees', label: 'Ver Empleados', group: 'Acceso a pantallas',
      description: 'Entra a la sección Empleados y ve quién tiene qué acceso.' },
    { key: 'access_screen_honor_board', label: 'Ver Cuadro de Honor', group: 'Acceso a pantallas',
      description: 'Entra al ranking mensual de distribuidores.' },

    { key: 'order_mark_paid', label: 'Marcar pedido como Pagado', group: 'Pedidos',
      description: 'Confirma que el dinero entró. Es el paso que libera la preparación.',
      requires: 'access_screen_orders' },
    { key: 'order_mark_shipped', label: 'Marcar pedido como Enviado', group: 'Pedidos',
      description: 'Registra la salida del paquete y su número de guía.',
      requires: 'access_screen_orders' },
    { key: 'order_mark_delivered', label: 'Marcar pedido como Entregado', group: 'Pedidos',
      description: 'Cierra el pedido. A partir de aquí cuenta para comisiones.',
      requires: 'access_screen_orders' },
    { key: 'order_create', label: 'Crear pedidos a mano', group: 'Pedidos',
      description: 'Levanta un pedido por teléfono o mostrador a nombre de un cliente.',
      requires: 'access_screen_orders' },

    { key: 'product_add', label: 'Crear productos', group: 'Catálogo',
      description: 'Da de alta un producto nuevo, con su precio y sus puntos.',
      requires: 'access_screen_products' },
    { key: 'product_update', label: 'Editar productos', group: 'Catálogo',
      description: 'Cambia precio, descripción e imágenes. El precio afecta a los puntos VP.',
      requires: 'access_screen_products' },
    { key: 'product_delete', label: 'Eliminar productos', group: 'Catálogo',
      description: 'Borra un producto del catálogo. Acción destructiva.',
      requires: 'access_screen_products' },
    { key: 'product_set_month', label: 'Elegir el producto del mes', group: 'Catálogo',
      description: 'Decide qué producto se destaca en la tienda del cliente.',
      requires: 'access_screen_products' },

    { key: 'stock_create', label: 'Crear almacenes', group: 'Inventario',
      description: 'Da de alta una bodega o sucursal donde guardar mercancía.',
      requires: 'access_screen_stocks' },
    { key: 'stock_add_inventory', label: 'Registrar entradas de mercancía', group: 'Inventario',
      description: 'Suma unidades cuando llega el proveedor.',
      requires: 'access_screen_stocks' },
    { key: 'stock_create_transfer', label: 'Crear transferencias', group: 'Inventario',
      description: 'Mueve mercancía de un almacén a otro.',
      requires: 'access_screen_stocks' },
    { key: 'stock_receive_transfer', label: 'Recibir transferencias', group: 'Inventario',
      description: 'Confirma que la mercancía llegó al almacén de destino.',
      requires: 'access_screen_stocks' },
    { key: 'stock_mark_damaged', label: 'Registrar mercancía dañada', group: 'Inventario',
      description: 'Da de baja unidades rotas o caducadas. Resta del inventario.',
      requires: 'access_screen_stocks' },

    { key: 'pos_register_sale', label: 'Cobrar en el mostrador', group: 'Personas y dinero',
      description: 'Registra una venta presencial y descuenta del inventario.',
      requires: 'access_screen_pos' },
    { key: 'customer_add', label: 'Dar de alta clientes', group: 'Personas y dinero',
      description: 'Registra un cliente nuevo y lo cuelga de un patrocinador.',
      requires: 'access_screen_customers' },
    { key: 'commissions_register_payment', label: 'Registrar pagos de comisiones', group: 'Personas y dinero',
      description: 'Marca como pagado el dinero que el negocio debe a un distribuidor.',
      requires: 'access_screen_customers' },
    { key: 'employee_add', label: 'Dar de alta empleados', group: 'Personas y dinero',
      description: 'Crea cuentas de operador y genera su contraseña temporal.',
      requires: 'access_screen_employees' },

    { key: 'user_mark_admin', label: 'Conceder acceso al panel', group: 'Sistema',
      description: 'Permite que un cliente entre al back office. Concédelo con cuidado.' },
    { key: 'user_manage_privileges', label: 'Cambiar permisos de otros', group: 'Sistema',
      description: 'Quien tenga esto puede darse a sí mismo cualquier otro permiso.' },
    { key: 'employee_manage_privileges', label: 'Cambiar permisos de empleados', group: 'Sistema',
      description: 'Edita el acceso de los operadores desde la sección Empleados.',
      requires: 'access_screen_employees' },
    { key: 'config_manage', label: 'Cambiar reglas del negocio', group: 'Sistema',
      description: 'Toca comisiones, rangos, bonos y avisos. Afecta a lo que cobra la red.',
      requires: 'access_screen_settings' }
  ];

  /** Permisos agrupados por área: 27 casillas seguidas no se pueden revisar. */
  get privilegeGroups(): Array<{ group: string; options: CustomerPrivilegeOption[] }> {
    const orden = ['Acceso a pantallas', 'Pedidos', 'Catálogo', 'Inventario', 'Personas y dinero', 'Sistema'];
    return orden
      .map((group) => ({ group, options: this.customerPrivilegeOptions.filter((o) => o.group === group) }))
      .filter((g) => g.options.length > 0);
  }

  /** Cuántos permisos tiene concedidos el empleado seleccionado. */
  get selectedEmployeeGrantedCount(): number {
    return this.customerPrivilegeOptions.filter((o) => this.employeeHasPrivilege(o.key)).length;
  }

  /**
   * Un permiso de acción sin su permiso de pantalla no sirve de nada: el
   * empleado no puede llegar al botón. Antes esto se concedía en silencio.
   */
  employeePrivilegeIsInert(option: CustomerPrivilegeOption): boolean {
    if (!option.requires) return false;
    return this.employeeHasPrivilege(option.key) && !this.employeeHasPrivilege(option.requires);
  }

  employeePrivilegeInertHint(option: CustomerPrivilegeOption): string {
    const pantalla = this.customerPrivilegeOptions.find((o) => o.key === option.requires);
    return `No tendrá efecto: falta «${pantalla?.label ?? option.requires}».`;
  }

  businessConfigDraft: AppBusinessConfig = this.getDefaultBusinessConfig();
  isSavingBusinessConfig = false;
  businessConfigMessage = '';
  structureForm = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
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
  variantImageFiles = new Map<string, File>();
  variantImagePreviews = new Map<string, string>();
  productMessage = '';
  private productMessageTimeout?: number;
  private readonly updatingProductStatusIds = new Set<number>();
  productForm = {
    id: null as number | null,
    name: '',
    price: '',
    active: true,
    inOnlineStore: true,
    inPOS: true,
    commissionable: true,
    vpPoints: '' as string | number,
    sku: '',
    hook: '',
    description: '',
    copyFacebook: '',
    copyInstagram: '',
    copyWhatsapp: '',
    tags: '',
    variants: [] as Array<{ id: string; name: string; price: string; sku: string; active: boolean; img: string }>,
    categoryIds: [] as string[],
    weightKg: '' as string | number,
    lengthCm: '' as string | number,
    widthCm: '' as string | number,
    heightCm: '' as string | number,
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
  // ─── Honor Board ─────────────────────────────────────────────────────────
  honorBoardData: HonorBoard | null = null;
  honorBoardSort: 'vg' | 'vp' | 'alpha' = 'vg';
  isLoadingHonorBoard = false;
  isSavingStructure = false;
  isSavingProduct = false;
  isSettingProductOfMonth = false;
  isDeletingProduct = false;
  productToDelete: AdminProduct | null = null;
  shippingTargetOrder: AdminOrder | null = null;
  shippingType: 'carrier' | 'personal' = 'carrier';
  shippingTrackingNumber = '';
  shippingCarrierDraft = '';
  readonly shippingCarrierOptions = [
    { value: 'Estafeta', label: 'Estafeta' },
    { value: 'DHL', label: 'DHL' },
    { value: 'FedEx', label: 'FedEx' },
    { value: 'Paquetexpress', label: 'Paquetexpress' },
    { value: 'Redpack', label: 'Redpack' },
    { value: 'Otra', label: 'Otra paquetería' }
  ];
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
    location: '',
    postalCode: '',
    isMainWarehouse: false,
    allowPickup: false,
    city: '',   // paquete C
    state: ''   // paquete C
  };
  /** Paquete C: ciudad y estado editables del stock activo. */
  stockUbicacionDraft = { city: '', state: '' };

  // ── Paquete F · ronda 26 (propuesta 28) ─────────────────────────────────
  // Toño: "el día que Guadalajara se quede en 1 pieza, nadie se va a enterar
  // hasta que un cliente pague y no haya". La vista abre con el inventario de
  // todas las sucursales, con su total y su mínimo; fundar una bodega queda
  // detrás de un botón.
  /** Formulario de alta de bodega, plegado por omisión. */
  altaStockAbierta = false;
  /** Mínimo por producto, tal como lo guardó el servidor. */
  stockMinimos: Record<string, number> = {};
  minStockDefault = 0;
  /** Lo que la persona está escribiendo en la columna "Mínimo". */
  minimoBorrador: Record<string, string> = {};
  guardandoMinimos = false;
  mensajeMinimos = '';
  errorMinimos = '';
  private minimosPedidos = false;
  readonly estadoOptionsStock = ESTADOS_MX_OPTIONS;
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
  isImportingInventory = false;
  inventoryImportResults: Array<{ productName: string; qty: number; ok: boolean; message?: string }> = [];

  // --- STATS / REPORTES ---
  statsReportMonth = '';
  statsReportTab: StatsReportTabId = 'resumen';
  /**
   * Guarda 14 (informe 27 §4): la tira de pestañas de reportes vive aquí, no
   * como literal dentro del `*ngFor` de la plantilla. Un literal escrito en la
   * plantilla se vuelve a crear en **cada** ciclo de detección de cambios, así
   * que Angular destruía y rehacía los cinco botones sin parar: es el sustrato
   * del botón que se pulsa y no abre.
   */
  readonly statsReportTabs: ReadonlyArray<{ id: StatsReportTabId; label: string }> = [
    { id: 'resumen', label: 'Resumen' },
    { id: 'pedidos', label: 'Pedidos' },
    { id: 'clientes', label: 'Clientes' },
    { id: 'productos', label: 'Productos' },
    { id: 'stocks', label: 'Stocks' }
  ];

  trackStatsReportTab(_index: number, tab: { id: StatsReportTabId }): string {
    return tab.id;
  }

  /**
   * Guarda 14: identidad estable de una fila de tabla. Sin `trackBy`, cambiar
   * una celda obliga a Angular a rehacer la tabla entera (y con ella el botón
   * que alguien tenía debajo del dedo). Se compone con los campos que
   * identifican la fila; si no hay ninguno, la posición, que al menos no
   * cambia mientras la lista no cambie.
   */
  trackFila(index: number, fila: unknown): string {
    const f = (fila ?? {}) as Record<string, unknown>;
    for (const campo of ['id', 'customerId', 'orderId', 'productId', 'sku', 'code', 'key', 'email', 'name']) {
      const valor = f[campo];
      if (valor) {
        return `${campo}:${String(valor)}`;
      }
    }
    // Renglones de informe que no traen identidad propia (sucursal + producto).
    if (f['stock'] && f['product']) {
      return `${String(f['stock'])}·${String(f['product'])}`;
    }
    return `#${index}`;
  }
  statsData: import('../../models/admin.model').MonthlyStatsResult | null = null;
  isLoadingStats = false;

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
  posSalePaymentMethod: 'cash' | 'card' | 'transfer' | 'mixed' = 'cash';
  /** Pago mixto (paquete E): parte en efectivo; el resto va a tarjeta o transferencia. */
  posMixedCashAmount = '';
  posMixedSecondMethod: 'card' | 'transfer' = 'card';
  /** Se incrementa tras cada venta, abono o anulación para que el arqueo se recargue. */
  posCajaRefreshToken = 0;
  /** Última venta tal como la guardó el servidor: folio y montos reales, no los del formulario. */
  posUltimaVenta: VentaCajaRespuesta | null = null;
  // Abono a saldo pendiente (modal en lugar de prompt)
  isPosSettleModalOpen = false;
  posSettleTarget: PosSale | null = null;
  posSettleAmount = '';
  posSettleMethod: 'cash' | 'card' | 'transfer' = 'cash';
  posSettleError = '';
  isSettlingPosSale = false;
  posSettleResult: AbonoCajaRespuesta | null = null;
  // Anulación de venta (modal en lugar de prompt)
  isPosVoidModalOpen = false;
  posVoidTarget: PosSale | null = null;
  posVoidReason = '';
  posVoidError = '';
  isVoidingPosSale = false;
  posVoidResult: AnulacionCajaRespuesta | null = null;
  posCustomerSearch = 'Público en general';
  selectedPosCustomerId: number | null = null;
  posCustomerRecommendations: PosCustomerRecommendation[] = [];
  posSelectedCustomerMonth: AssociateMonth | null = null;
  isLoadingPosCustomerProjection = false;
  isRegisteringPosSale = false;
  /** Efectivo que entrega el cliente en mostrador; el POS no lo pedía y el cajero sacaba el cambio de cabeza. */
  posCashReceived = '';

  get posCashReceivedNumber(): number {
    const n = Number(String(this.posCashReceived).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? n : 0;
  }

  /** Parte del total que se paga en efectivo (todo, la parte mixta o nada). */
  get posCashPortion(): number {
    if (this.posPaymentTypeMode !== 'full') {
      return this.posSalePaymentMethod === 'cash' ? this.posAmountPaidNow : 0;
    }
    if (this.posSalePaymentMethod === 'cash') return this.posEffectiveTotal;
    if (this.posSalePaymentMethod === 'mixed') return this.posMixedCashNumber;
    return 0;
  }

  get posMixedCashNumber(): number {
    const n = Number(String(this.posMixedCashAmount).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? this.roundMoney(n) : 0;
  }

  /** Lo que va a tarjeta o transferencia en un pago mixto: se autocompleta. */
  get posMixedRemainder(): number {
    return this.roundMoney(Math.max(0, this.posEffectiveTotal - this.posMixedCashNumber));
  }

  get posMixedInvalidReason(): string {
    if (this.posSalePaymentMethod !== 'mixed') return '';
    if (this.posPaymentTypeMode !== 'full') return 'El pago mixto solo aplica a pago completo: elige una sola forma de pago para el pago parcial o crédito.';
    if (!String(this.posMixedCashAmount).trim()) return 'Escribe cuánto paga en efectivo; el resto se cobra con tarjeta o transferencia.';
    if (this.posMixedCashNumber <= 0 || this.posMixedCashNumber >= this.posEffectiveTotal) {
      return `En pago mixto la parte en efectivo debe ser mayor a $0 y menor al total (${this.formatMoney(this.posEffectiveTotal)}).`;
    }
    return '';
  }

  get posChangeDue(): number {
    if (!(this.posSalePaymentMethod === 'cash' || this.posSalePaymentMethod === 'mixed') || this.posPaymentTypeMode !== 'full') {
      return 0;
    }
    return this.roundMoney(Math.max(0, this.posCashReceivedNumber - this.posCashPortion));
  }

  get posCashShort(): number {
    if (!(this.posSalePaymentMethod === 'cash' || this.posSalePaymentMethod === 'mixed') || this.posPaymentTypeMode !== 'full' || !this.posCashReceived) {
      return 0;
    }
    return this.roundMoney(Math.max(0, this.posCashPortion - this.posCashReceivedNumber));
  }
  posFeedbackMessage = '';
  posFeedbackTone: 'error' | 'success' | '' = '';

  isPosAuthModalOpen = false;
  posAuthCode = '';
  posAuthError = '';
  posAuthAction = '';
  posAuthPendingCallback: (() => void) | null = null;
  isValidatingPosAuth = false;
  posValidatedAuthCode = '';

  isPosDiscountModalOpen = false;
  posDiscountMode: 'percent' | 'amount' = 'percent';
  posDiscountValue = '';
  posDiscountError = '';
  posAppliedCashierDiscount: { mode: 'percent' | 'amount'; value: number; displayLabel: string } | null = null;

  posPaymentTypeMode: 'full' | 'partial' | 'credit' = 'full';
  posPartialAmountPaid = '';

  posCashCuts: PosCashCut[] = [];
  isLoadingPosCashCuts = false;
  isPosCashCutsOpen = false;
  expandedCutId: string | null = null;

  posAuthCodeDraft = '';
  isSavingPosAuthCode = false;
  posAuthCodeMessage = '';
  posAuthCodeIsError = false;
  isPosPaymentModalOpen = false;
  posPaymentTargetOrder: AdminOrder | null = null;
  posPaymentMethod: 'cash' | 'card' | 'transfer' = 'cash';
  isSubmittingPosPayment = false;
  posPaymentError = '';
  isPosCustomerModalOpen = false;
  posCustomerError = '';
  isSavingPosCustomer = false;
  posCustomerForm = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
    phone: '',
    email: '',
    address: '',
    city: ''
  };

  selectedEmployee: AdminEmployee | null = null;
  selectedEmployeePrivilegeDraft: UserPrivileges = {};
  selectedEmployeeAdminAccess = true;
  isSavingEmployeePrivileges = false;
  isSavingEmployee = false;
  employeeMessage = '';
  employeeMessageIsError = false;
  employeeTempPassword = '';

  snackbar: { message: string; tone: 'success' | 'error'; visible: boolean } = { message: '', tone: 'success', visible: false };
  private snackbarTimeout?: number;
  employeeForm = {
    name: '',
    email: '',
    phone: '',
    jobTitle: '' // paquete E · ronda 26: el puesto que pinta la insignia
  };

  ngOnInit(): void {
    // Paquete E · ronda 26 · La vista la manda la URL, no un campo interno. El
    // componente no inyectaba `ActivatedRoute`: por eso recargar `#/admin`
    // siempre volvía a la vista por omisión y Renata no podía mandar un enlace
    // ("tendría que contestarle: en Clientes, hasta abajo, después de los
    // documentos"). `getFirstAllowedView()` es solo el respaldo de `#/admin`.
    //
    // El orden importa: los parámetros de la URL se leen ANTES de montar la
    // vista, para que la pestaña que pidió la URL no la pise el cálculo de
    // "la primera pestaña con trabajo".
    this.route.queryParamMap.subscribe((params) => {
      // `?estado=paid` (la cola de trabajo y las acciones urgentes) y `?mes=`
      // (Comisiones y pagos) viajan en la URL para sobrevivir a la navegación.
      const estado = params.get('estado');
      if (estado) {
        // "factura_solicitada" es una bandeja, no un estado guardado: se abre
        // como pestaña y el filtro por estado se queda como estaba.
        if (estado !== 'factura_solicitada') {
          this.currentOrderStatus = estado as AdminOrder['status'];
        }
        this.currentOrderTab = estado;
        this.orderStatusFijadoPorUrl = true;
      }
      const mes = params.get('mes');
      if (mes) {
        this.pagosMesMonth = mes;
      }
      // La guarda de pantalla no quita una pantalla en silencio: dice cuál era.
      // El aviso lo pinta `ui-aviso-sin-acceso` desde `AccesoPantallaService`;
      // aquí solo se recoge el que viene en la URL, que es el caso de la
      // recarga completa (la guarda no corrió en esta pestaña).
      const sinAcceso = params.get('sinAcceso') ?? '';
      if (sinAcceso) {
        this.acceso.anotar(sinAcceso);
      }
    });
    this.route.paramMap.subscribe((params) => {
      // `#/admin/pedido/:idPedido`: el pedido abre su detalle solo, sin buscarlo.
      const idPedido = params.get('idPedido');
      if (idPedido) {
        this.expandedOrderDetailId = idPedido;
        this.orderDeepLinkId = idPedido;
        this.abrirPedidoDeUrl();
      }
    });
    this.route.data.subscribe((data) => {
      const vista = (data['view'] as AdminViewId | undefined) ?? this.getFirstAllowedView();
      this.aplicarVistaDeRuta(vista, (data['panel'] as string | undefined) ?? '');
    });
    // Carga mínima: solo warnings (ya cacheados si se viene de otra pantalla).
    if (!this.adminControl.hasLoadedWarnings()) {
      this.adminControl.load().subscribe();
    }
    // Integración de la ronda 26 (§3.1): la tasa del IVA del resumen del POS.
    // `plan$` está cacheado y es público; si no llega, se queda la de la
    // configuración por omisión y el desglose sigue cuadrando al centavo.
    this.planSocio.plan$.subscribe({
      next: (plan) => {
        this.vatRate = plan?.iva?.tasa ?? this.vatRate;
        this.vatLabel = plan?.iva?.etiqueta || this.vatLabel;
        this.requestViewUpdate();
      },
      error: () => undefined
    });
  }

  /** Pedido pedido por URL (`#/admin/pedido/:idPedido`), para abrirlo al llegar. */
  orderDeepLinkId: string | null = null;

  /** true cuando la pestaña de Pedidos la eligió la URL: no se recalcula sola. */
  private orderStatusFijadoPorUrl = false;

  /** Pantalla que se quiso abrir sin tener su privilegio; se dice y se puede cerrar. */

  private aplicarVistaDeRuta(vista: AdminViewId, panel: string): void {
    this.currentView = vista;
    this.orderPage = 0;
    this.customerPage = 0;
    this.productPage = 0;
    this.employeePage = 0;
    this.notificationPage = 0;
    this.loadViewData(vista);
    if (panel) {
      // Comisiones y pagos vive dentro de Clientes; al llegar por su URL la
      // pantalla baja sola al bloque, en vez de dejarlo "hasta abajo".
      setTimeout(() => document.getElementById(panel)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
    }
  }

  private loadViewData(view: AdminViewId): void {
    switch (view) {
      case 'orders':
        if (!this.adminControl.hasLoadedOrders()) {
          // Carga inicial sin filtro de status para ver todos los pedidos
          this.adminControl.loadOrders().subscribe(() => {
            this.syncInitialOrderDeps();
          });
        } else {
          this.abrirPrimeraPestanaConTrabajo();
          this.abrirPedidoDeUrl();
        }
        break;
      case 'customers':
        // WP-A · 17: «Comisiones y pagos» vive en esta vista y su KPI exporta
        // `commissionsMonthKey`. Sin pedir los periodos aquí, el mes salía de
        // `new Date()` del navegador y la pantalla enseñaba dos meses del mismo
        // dinero: el panel decía «abril 2027» y el botón «Exportar 2026-08».
        this.cargarPeriodosDelServidor();
        this.adminControl.loadCustomers().subscribe(() => {
          if (!this.selectedCustomer) {
            this.selectedCustomer = this.customers[0] ?? null;
            if (this.selectedCustomer) this.loadSelectedCustomerProfile(this.selectedCustomer.id);
          }
          this.syncSelectedCustomerAccessDraft();
          if (!this.newOrderCustomerId) this.newOrderCustomerId = this.customers[0]?.id ?? null;
        });
        break;
      case 'products':
        this.adminControl.loadProducts().subscribe();
        break;
      case 'employees':
        this.adminControl.loadEmployees().subscribe(() => {
          if (!this.selectedEmployee) {
            this.selectedEmployee = this.employees[0] ?? null;
            this.syncSelectedEmployeePrivilegeDraft();
            this.syncEmployeeContactDraft();
          }
          this.stockEntryForm.createdByUserId ??= this.employees[0]?.id ?? null;
          this.stockTransferForm.createdByUserId ??= this.employees[0]?.id ?? null;
          this.stockDamageForm.reportedByUserId ??= this.employees[0]?.id ?? null;
          this.transferReceiverUserId ??= this.employees[0]?.id ?? null;
        });
        break;
      case 'campaigns':
        this.adminControl.loadCampaigns().subscribe();
        break;
      case 'notifications':
        this.adminControl.loadNotifications().subscribe();
        break;
      case 'coupons':
        this.loadCoupons();
        break;
      case 'stocks':
      case 'pos':
        this.loadStocksAndPosState();
        // La tabla única de descuento del POS lee `businessConfig`, que solo se
        // llenaba al guardar Configuración: salía sin tramos y cobraba sin descuento.
        if (view === 'pos' && !this.businessConfig) {
          this.adminControl.loadBusinessConfig().subscribe({ next: () => this.requestViewUpdate(), error: () => undefined });
        }
        this.adminControl.loadCustomers().subscribe();
        if (!this.adminControl.hasLoadedOrders()) {
          this.adminControl.loadOrders().subscribe();
        }
        this.adminControl.loadEmployees().subscribe();
        this.cargarPeriodosDelServidor();   // WP-A · 17
        break;
      case 'settings':
        this.syncBusinessConfigDraft();
        break;
      case 'stats':
        this.adminControl.loadCustomers().subscribe();
        this.cargarPeriodosDelServidor();   // WP-A · 17
        this.loadMonthlyStats(this.activeReportMonth);
        break;
      case 'honor_board':
        if (!this.honorBoardData && !this.isLoadingHonorBoard) {
          this.loadHonorBoard();
        }
        break;
    }
  }

  private syncInitialOrderDeps(): void {
    this.ensureCurrentViewAllowed();
    this.selectPublicGeneralCustomer();
    this.abrirPrimeraPestanaConTrabajo();
    this.abrirPedidoDeUrl();
  }

  /**
   * Paquete E · ronda 26 · propuesta 33 · Pedidos abre donde hay trabajo.
   *
   * Abría siempre en "Pendiente", vacía, mientras el resumen de al lado decía
   * "Pagados 3": Toño leyó las dos cosas a la vez y anotó "si yo fuera menos
   * necio me voy a la bodega a barrer". La cola de trabajo (`nextActions`) ya
   * calcula cuál es la primera pestaña con algo que hacer; se usa esa. Si la
   * pestaña la pidió la URL (`?estado=`) o se llegó a un pedido concreto, manda
   * la URL: nunca se le mueve la pantalla a quien pidió una en particular.
   */
  private abrirPrimeraPestanaConTrabajo(): void {
    if (this.orderStatusFijadoPorUrl || this.orderDeepLinkId) {
      return;
    }
    const primera = this.nextActions.find((accion) => !!accion.status);
    if (primera?.status) {
      this.currentOrderStatus = primera.status;
      this.currentOrderTab = primera.status;
      this.orderPage = 0;
    }
  }

  /**
   * `#/admin/pedido/:idPedido`: el pedido se abre solo, en la pestaña de su
   * estado, sin que nadie tenga que adivinar en cuál de las diez está. Antes el
   * detalle era un acordeón dentro de una pantalla sin dirección: no había
   * enlace que mandarle al dueño ni forma de volver a él.
   */
  private abrirPedidoDeUrl(): void {
    if (!this.orderDeepLinkId) {
      return;
    }
    const pedido = this.orders.find((o) => o.id === this.orderDeepLinkId);
    if (!pedido) {
      return;
    }
    this.currentOrderStatus = pedido.status;
    this.currentOrderTab = pedido.status;
    this.orderStatusFijadoPorUrl = true;
    this.orderSearch = pedido.id;
    this.orderPage = 0;
  }

  get orders(): AdminOrder[] {
    return this.adminData()?.orders ?? [];
  }

  /**
   * Tasa y etiqueta del IVA para el resumen del POS (§3.1), montado en la
   * integración. Salen de `GET /catalog/plan`, que es público y ya está
   * cacheado por `PlanSocioService`: el back office no inventa el número.
   */
  vatRate = 0.16;
  vatLabel = 'IVA';

  /** Umbral en días a partir del cual la antigüedad va en rojo (configuración). */
  get agingRedDays(): number {
    return Number(this.adminData()?.agingRedDays ?? 7) || 7;
  }

  /** El reloj del servidor: el de los avisos o, si aún no llegó, el de los periodos. */
  private get relojDelServidorMs(): number {
    const iso = this.adminData()?.serverNow || this.serverNow;
    const t = iso ? Date.parse(iso) : NaN;
    return Number.isFinite(t) ? t : Date.now();
  }

  /** Días completos que lleva el pedido desde que se creó. `null` si no se sabe. */
  orderAgingDays(order: AdminOrder): number | null {
    const creado = Date.parse(String(order.createdAt ?? ''));
    if (!Number.isFinite(creado)) {
      return null;
    }
    return Math.max(0, Math.floor((this.relojDelServidorMs - creado) / 86400000));
  }

  /** "37 días", "1 día", "hoy": como lo diría una persona. */
  orderAgingLabel(order: AdminOrder): string {
    const dias = this.orderAgingDays(order);
    if (dias === null) {
      return '—';
    }
    if (dias === 0) {
      return 'hoy';
    }
    return dias === 1 ? '1 día' : `${dias} días`;
  }

  orderAgingIsRed(order: AdminOrder): boolean {
    const dias = this.orderAgingDays(order);
    return dias !== null && dias >= this.agingRedDays;
  }

  /** Sin ordenar → más viejos primero → más nuevos primero → sin ordenar. */
  toggleOrderAgingSort(): void {
    this.orderAgingSort = this.orderAgingSort === 'none' ? 'desc'
      : this.orderAgingSort === 'desc' ? 'asc' : 'none';
    this.orderPage = 0;
    this.requestViewUpdate();
  }

  get orderAgingSortLabel(): string {
    return this.orderAgingSort === 'desc' ? 'De más viejo a más nuevo'
      : this.orderAgingSort === 'asc' ? 'De más nuevo a más viejo'
      : 'Sin ordenar por antigüedad';
  }

  get customers(): AdminCustomer[] {
    return this.adminData()?.customers ?? [];
  }

  /** Filtro "fríos": sin compra en 30+ días o nunca. Antes se cruzaban siete pestañas de Pedidos a mano. */
  customersColdOnly = false;

  /**
   * Guarda 13 (informe 27 §4): los días se cuentan con el reloj del servidor,
   * como la antigüedad de los pedidos. Con `Date.now()` el navegador de Alma
   * (2026-09) restaba contra compras del mundo simulado (2027-04) y toda la
   * lista salía en "0 días", que se lee como "nadie compra".
   */
  daysSinceLastPurchase(customer: AdminCustomer): number | null {
    if (!customer.lastPurchaseAt) return null;
    const t = new Date(customer.lastPurchaseAt).getTime();
    if (!Number.isFinite(t)) return null;
    return Math.max(0, Math.floor((this.relojDelServidorMs - t) / 86400000));
  }

  isColdCustomer(customer: AdminCustomer): boolean {
    if (customer.deletedAt) return false;
    const days = this.daysSinceLastPurchase(customer);
    return days === null || days >= 30;
  }

  get filteredCustomers(): AdminCustomer[] {
    const q = this.customerSearch.trim().toLowerCase();
    const base = this.customersColdOnly ? this.customers.filter((c) => this.isColdCustomer(c)) : this.customers;
    if (!q) return base;
    return base.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.level || '').toLowerCase().includes(q) ||
        (c.discount || '').toLowerCase().includes(q)
    );
  }

  toggleCustomersColdOnly(): void {
    this.customersColdOnly = !this.customersColdOnly;
    this.customerPage = 0;
  }

  /** Exportar la lista filtrada (nombre, correo, teléfono, patrocinador, última compra, mes anterior) a CSV. */
  exportCustomersCsv(): void {
    const rows = this.filteredCustomers.map((c) => [
      c.name, c.email, c.phone || '', c.leaderId != null ? String(c.leaderId) : 'FindingU',
      c.lastPurchaseAt ? c.lastPurchaseAt.slice(0, 10) : 'nunca',
      String(this.daysSinceLastPurchase(c) ?? ''), String(c.commissionsPrevMonth ?? 0), c.doNotContact ? 'no contactar' : ''
    ]);
    const esc = (v: string) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const csv = [['Nombre', 'Correo', 'Teléfono', 'Patrocinador', 'Última compra', 'Días', 'Comisión mes anterior', 'Contacto'], ...rows]
      .map((r) => r.map(esc).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `clientes-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  get pagedCustomers(): AdminCustomer[] {
    return this.filteredCustomers.slice(this.customerPage * this.PAGE_SIZE, (this.customerPage + 1) * this.PAGE_SIZE);
  }

  get customersTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredCustomers.length / this.PAGE_SIZE));
  }

  get filteredProducts(): AdminProduct[] {
    const q = this.productSearch.trim().toLowerCase();
    if (!q) return this.products;
    return this.products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.sku || '').toLowerCase().includes(q) ||
        (p.hook || '').toLowerCase().includes(q) ||
        (p.active ? 'activo' : 'retirado').includes(q)
    );
  }

  get pagedProducts(): AdminProduct[] {
    return this.filteredProducts.slice(this.productPage * this.PAGE_SIZE, (this.productPage + 1) * this.PAGE_SIZE);
  }

  get productsTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredProducts.length / this.PAGE_SIZE));
  }

  get filteredEmployees(): AdminEmployee[] {
    const q = this.employeeSearch.trim().toLowerCase();
    const list = this.adminData()?.employees ?? [];
    if (!q) return list;
    return list.filter(
      (e) =>
        e.name.toLowerCase().includes(q) ||
        e.email.toLowerCase().includes(q) ||
        (e.active ? 'activo' : 'inactivo').includes(q)
    );
  }

  get pagedEmployees(): AdminEmployee[] {
    return this.filteredEmployees.slice(this.employeePage * this.PAGE_SIZE, (this.employeePage + 1) * this.PAGE_SIZE);
  }

  get employeesTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredEmployees.length / this.PAGE_SIZE));
  }

  get filteredNotifications(): PortalNotification[] {
    const q = this.notificationSearch.trim().toLowerCase();
    if (!q) return this.notifications;
    return this.notifications.filter(
      (n) =>
        (n.title || '').toLowerCase().includes(q) ||
        (n.description || '').toLowerCase().includes(q) ||
        (n.status || '').toLowerCase().includes(q)
    );
  }

  get pagedNotifications(): PortalNotification[] {
    return this.filteredNotifications.slice(this.notificationPage * this.PAGE_SIZE, (this.notificationPage + 1) * this.PAGE_SIZE);
  }

  get notificationsTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredNotifications.length / this.PAGE_SIZE));
  }

  get employees(): AdminEmployee[] {
    return this.adminData()?.employees ?? [];
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

  get commissionLevelsErrors(): string[] {
    const errors: string[] = [];
    const levels = this.businessConfigDraft?.rewards?.commissionLevels ?? [];
    for (let i = 1; i < levels.length; i++) {
      const prev = levels[i - 1];
      const curr = levels[i];
      const label = `Gen ${i} → Gen ${i + 1}`;
      // Los requisitos de cada generación deben ser ≥ a los de la anterior.
      if ((curr.reqActiveDirects ?? 0) < (prev.reqActiveDirects ?? 0)) {
        errors.push(`${label}: directos activos debe ser ≥ ${prev.reqActiveDirects ?? 0}`);
      }
      if ((curr.reqPersonalPC ?? 0) < (prev.reqPersonalPC ?? 0)) {
        errors.push(`${label}: PC personales debe ser ≥ ${prev.reqPersonalPC ?? 0}`);
      }
      if ((curr.reqLines ?? 0) < (prev.reqLines ?? 0)) {
        errors.push(`${label}: líneas calificadas debe ser ≥ ${prev.reqLines ?? 0}`);
      }
    }
    return errors;
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

  get employeeOptionsStable(): Array<SelectOption<number>> {
    if (this.employeeOptionsCache?.employeesRef === this.employees) {
      return this.employeeOptionsCache.options;
    }
    const options = this.employees.map((emp) => ({
      value: emp.id,
      label: `${emp.name} · ${emp.email}`
    }));
    this.employeeOptionsCache = { employeesRef: this.employees, options };
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
    // A la cajera le salía "socias sin CLABE · Ir a resolver" sin poder abrir Clientes.
    const visibles = warnings.filter((w) => this.canAccessView(this.warningTargetView(w.type)));
    this.warningsCache = { warningsRef: warnings, warnings: visibles };
    return visibles;
  }

  private warningTargetView(type: string): AdminViewId {
    const map: Record<string, AdminViewId> = {
      commissions: 'customers',
      commissions_ready: 'customers',
      commissions_no_clabe: 'customers',
      shipping: 'orders',
      pickup: 'orders',      // paquete F · ronda 26: pedidos por recoger en mostrador
      assets: 'products',
      stocks: 'stocks',
      stock_min: 'stocks',   // paquete F · ronda 26: productos bajo su mínimo
      pos: 'pos',
      payments: 'orders',
      refunds: 'orders',
      // Propuesta 20: la pestaña "Factura solicitada" existía y el contador de
      // Acciones urgentes no; sin el aviso, la bandeja dependía de que alguien
      // abriera Pedidos y mirara la novena pestaña.
      invoices: 'orders'
    };
    return map[type] ?? 'stats';
  }

  /**
   * Paquete E · ronda 26 · El menú del back office, escrito UNA sola vez.
   *
   * Antes eran dos copias de doce enlaces (la barra lateral y la barra inferior
   * del móvil), y ninguna de las dos nombraba el trabajo de tres personas:
   * Comisiones y pagos vivía al fondo de la ficha de un cliente ("Alma buscó
   * «Comisiones» en el menú siete veces"), Seguimiento de hoy era un botón
   * encima de una tabla dentro de Clientes y Despacho en bloque estaba entre
   * las pestañas de estado de Pedidos. Ahora cada entrada lleva su URL.
   */
  private get adminMenuGroups(): Array<{ label: string; entries: AdminMenuEntry[] }> {
    return adminMenuVisible(this.currentUser?.privileges, this.authService.isSuperUser(this.currentUser));
  }

  /** Las entradas visibles, sin encabezados: la barra inferior del móvil las reusa. */
  get adminMenuLinksStable(): AdminMenuEntry[] {
    this.buildAdminMenuCache();
    return this.adminNavLinksCache!.entries;
  }

  /** Las mismas entradas con sus encabezados de grupo, para la barra lateral. */
  get adminNavLinksStable(): SidebarLink[] {
    this.buildAdminMenuCache();
    return this.adminNavLinksCache!.links;
  }

  private buildAdminMenuCache(): void {
    if (this.adminNavLinksCache?.user === this.currentUser) {
      return;
    }
    const links: SidebarLink[] = [];
    const entries: AdminMenuEntry[] = [];
    for (const group of this.adminMenuGroups) {
      links.push({ id: `heading-${group.label}`, icon: '', label: group.label, heading: true });
      for (const entrada of group.entries) {
        links.push({ id: entrada.id, icon: entrada.icon, label: entrada.label, subtitle: '' });
        entries.push(entrada);
      }
    }
    this.adminNavLinksCache = { user: this.currentUser, links, entries };
  }

  /** Qué entrada del menú está encendida: se lee de la URL, no de un campo suelto. */
  get activeMenuId(): string {
    const url = (this.router.url || '').split('?')[0];
    if (url.startsWith('/admin/comisiones')) {
      return 'comisiones';
    }
    const porRuta = this.adminMenuLinksStable.find((entrada) => url === entrada.route);
    return porRuta?.id ?? this.currentView;
  }

  /** Traza estable de las entradas del menú: evita recrear los nodos en cada pasada. */
  trackMenuEntry(_index: number, entrada: AdminMenuEntry): string {
    return entrada.id;
  }

  get viewTitle(): string {
    if (this.currentView === 'customers') {
      return 'Clientes';
    }
    if (this.currentView === 'employees') {
      return 'Empleados';
    }
    if (this.currentView === 'products') {
      return 'Productos';
    }
    if (this.currentView === 'stocks') {
      return 'Stocks';
    }
    if (this.currentView === 'campaigns') {
      return 'Campañas';
    }
    if (this.currentView === 'pos') {
      return 'Punto de Venta';
    }
    if (this.currentView === 'stats') {
      return 'Estadísticas';
    }
    if (this.currentView === 'honor_board') {
      return 'Cuadro de Honor';
    }
    if (this.currentView === 'notifications') {
      return 'Notificaciones';
    }
    if (this.currentView === 'coupons') {
      return 'Cupones';
    }
    if (this.currentView === 'settings') {
      return 'Configuración';
    }
    return 'Pedidos';
  }

  get viewSubtitle(): string {
    if (this.currentView === 'customers') {
      return 'Niveles, estructura y comisiones.';
    }
    if (this.currentView === 'employees') {
      return 'Alta, acceso y privilegios de operadores.';
    }
    if (this.currentView === 'products') {
      return 'Altas, imágenes y CTA.';
    }
    if (this.currentView === 'stocks') {
      return 'Inventario por sucursal, transferencias, recepciones y danos.';
    }
    if (this.currentView === 'campaigns') {
      return 'Campañas, assets y copy comercial para compartir con la red.';
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
    if (this.currentView === 'coupons') {
      return 'Crea códigos de descuento y controla su vigencia y usos.';
    }
    if (this.currentView === 'honor_board') {
      return 'Top 10 del mes por volumen de red (VG) y personal (VP).';
    }
    if (this.currentView === 'settings') {
      return 'Variables de negocio para reglas operativas.';
    }
    return 'Flujo del pedido: Pendiente → Pagado → Enviado → Entregado. Cancelaciones y devoluciones se atienden en sus propias pestañas.';
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

  /** Opciones del filtro por stock de la lista de pedidos (solo el nombre). */
  get stockFilterOptions(): Array<SelectOption<string>> {
    return this.stocks.map((stock) => ({ value: stock.id, label: stock.name }));
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

  /** Stocks a los que el operador actual tiene acceso (para modales de inventario). Admin ve todos. */
  get accessibleStockOptionsStable(): Array<SelectOption<string>> {
    const operatorId = this.currentOperatorId;
    const accessible = operatorId != null && !this.hasPermission('config_manage')
      ? this.stocks.filter((s) => s.linkedUserIds.map(Number).includes(operatorId))
      : this.stocks;
    return accessible.map((stock) => ({
      value: stock.id,
      label: `${stock.name} · ${stock.location}`
    }));
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

  /**
   * Inventario producto × sucursal, con el total de cada producto y su mínimo.
   * Sale del estado que la pantalla ya tiene (`stocks[].inventory`): ni una
   * consulta más al servidor.
   */
  get inventarioPorSucursalStable(): InventarioPorSucursalFila[] {
    if (
      this.inventarioPorSucursalCache?.stocksRef === this.stocks &&
      this.inventarioPorSucursalCache.productsRef === this.products &&
      this.inventarioPorSucursalCache.minimosRef === this.stockMinimos
    ) {
      return this.inventarioPorSucursalCache.rows;
    }
    const rows: InventarioPorSucursalFila[] = this.products.map((product) => {
      const minimo = this.minimoDe(product.id);
      const porSucursal = this.stocks.map((stock) => {
        const qty = Number((stock.inventory as Record<string, number>)[String(product.id)] ?? 0);
        return { stockId: stock.id, stockName: stock.name, qty, bajoMinimo: minimo > 0 && qty < minimo };
      });
      return {
        productId: product.id,
        productName: product.name,
        minStock: minimo,
        total: porSucursal.reduce((suma, celda) => suma + celda.qty, 0),
        porSucursal,
        bajoMinimo: porSucursal.some((celda) => celda.bajoMinimo)
      };
    });
    this.inventarioPorSucursalCache = {
      stocksRef: this.stocks,
      productsRef: this.products,
      minimosRef: this.stockMinimos,
      rows
    };
    return rows;
  }

  /** Totales por sucursal (el renglón de abajo de la tabla). */
  get totalesPorSucursalStable(): Array<{ stockId: string; stockName: string; total: number }> {
    return this.stocks.map((stock) => ({
      stockId: stock.id,
      stockName: stock.name,
      total: Object.values((stock.inventory as Record<string, number>) ?? {}).reduce((a, b) => a + Number(b ?? 0), 0)
    }));
  }

  get totalDeTodoElInventario(): number {
    return this.totalesPorSucursalStable.reduce((suma, s) => suma + s.total, 0);
  }

  /** Cuántos productos están por debajo de su mínimo en alguna sucursal. */
  get productosBajoMinimo(): number {
    return this.inventarioPorSucursalStable.filter((fila) => fila.bajoMinimo).length;
  }

  minimoDe(productId: number): number {
    const propio = this.stockMinimos[String(productId)];
    return Number.isFinite(propio) ? Number(propio) : this.minStockDefault;
  }

  /** Trae los mínimos guardados; sin permiso de almacén, la tabla no los pinta. */
  private cargarMinimosDeStock(): void {
    if (this.minimosPedidos || !this.hasPermission('access_screen_stocks')) {
      return;
    }
    this.minimosPedidos = true;
    this.despachoService.minimosDeStock().subscribe({
      next: (res) => {
        this.minStockDefault = Number(res.minStockDefault ?? 0);
        this.stockMinimos = { ...(res.minimos ?? {}) };
        this.minimoBorrador = {};
        this.requestViewUpdate();
      },
      error: () => { this.minimosPedidos = false; }
    });
  }

  cambiarMinimo(productId: number, valor: string): void {
    this.minimoBorrador = { ...this.minimoBorrador, [String(productId)]: valor };
    this.mensajeMinimos = '';
    this.errorMinimos = '';
  }

  minimoEnPantalla(productId: number): string {
    const borrador = this.minimoBorrador[String(productId)];
    return borrador !== undefined ? borrador : String(this.minimoDe(productId));
  }

  get hayMinimosSinGuardar(): boolean {
    return Object.keys(this.minimoBorrador).some(
      (pid) => Number(this.minimoBorrador[pid]) !== this.minimoDe(Number(pid))
    );
  }

  /** Guarda de un golpe los mínimos que se cambiaron. */
  guardarMinimos(): void {
    if (this.guardandoMinimos || !this.hayMinimosSinGuardar) {
      return;
    }
    const cambios: Record<string, number> = {};
    for (const [pid, valor] of Object.entries(this.minimoBorrador)) {
      const piezas = Number(valor);
      if (!Number.isFinite(piezas) || piezas < 0) {
        this.errorMinimos = 'Un mínimo tiene que ser un número de piezas de 0 en adelante.';
        this.requestViewUpdate();
        return;
      }
      if (piezas !== this.minimoDe(Number(pid))) {
        cambios[pid] = Math.round(piezas);
      }
    }
    this.guardandoMinimos = true;
    this.errorMinimos = '';
    this.mensajeMinimos = '';
    this.despachoService.guardarMinimosDeStock(cambios).subscribe({
      next: () => {
        this.stockMinimos = { ...this.stockMinimos, ...cambios };
        this.minimoBorrador = {};
        this.guardandoMinimos = false;
        const cuantos = Object.keys(cambios).length;
        this.mensajeMinimos = `Mínimo guardado en ${cuantos} producto${cuantos === 1 ? '' : 's'}. `
          + 'Por debajo de él, la existencia se pinta en rojo y sale en Acciones urgentes.';
        this.requestViewUpdate();
      },
      error: (err: unknown) => {
        this.guardandoMinimos = false;
        this.errorMinimos = this.mensajeDeErrorStock(err, 'No se pudieron guardar los mínimos.');
        this.requestViewUpdate();
      }
    });
  }

  private mensajeDeErrorStock(err: unknown, porOmision: string): string {
    const e = err as { error?: { message?: string }; message?: string } | null;
    return e?.error?.message || e?.message || porOmision;
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

  /** IDs de stocks permitidos para el usuario actual. null = sin restricción (super admin). */
  private get permittedStockIds(): Set<string> | null {
    const linked = this.linkedPosStocks;
    return linked.length > 0 ? new Set(linked.map((s) => s.id)) : null;
  }

  get inventoryMovementRowsStable(): Array<
    InventoryMovement & { stockName: string; productName: string; userName: string; typeLabel: string; signedQty: number }
  > {
    if (
      this.inventoryMovementRowsCache?.movementsRef === this.inventoryMovements &&
      this.inventoryMovementRowsCache.stocksRef === this.stocks &&
      this.inventoryMovementRowsCache.productsRef === this.products &&
      this.inventoryMovementRowsCache.customersRef === this.customers &&
      this.inventoryMovementRowsCache.employeesRef === this.employees
    ) {
      return this.inventoryMovementRowsCache.rows;
    }
    const allowed = this.permittedStockIds;
    const rows = this.inventoryMovements
      .filter((m) => !allowed || allowed.has(m.stockId))
      .map((movement) => ({
        ...movement,
        stockName: this.stockName(movement.stockId),
        productName: this.productName(movement.productId),
        userName: movement.userName || this.employeeName(movement.userId),
        typeLabel: this.movementTypeLabel(movement.type),
        signedQty: this.movementSignedQty(movement)
      }));
    this.inventoryMovementRowsCache = {
      movementsRef: this.inventoryMovements,
      stocksRef: this.stocks,
      productsRef: this.products,
      customersRef: this.customers,
      employeesRef: this.employees,
      rows
    };
    return rows;
  }

  get filteredOrdersStable(): AdminOrder[] {
    const q = this.orderSearch.trim().toLowerCase();
    // Paquete E · ronda 26 · propuesta 33 · Buscar cruza estados: se busca sobre
    // todos los pedidos cargados, no solo sobre la pestaña abierta. Cada fila
    // muestra su estado, así que no hay dónde perderse. Antes había que adivinar
    // en cuál de las diez pestañas estaba "Ximena" antes de poder encontrarla.
    let byStatus = q
      ? this.orders
      : this.currentOrderTab === 'factura_solicitada'
        ? this.orders.filter((o) => o.invoiceStatus === 'solicitada')
        : this.orders.filter((o) => o.status === this.currentOrderStatus);
    // Stock filter (applies to all statuses when a stock is selected)
    if (this.orderStockFilter) {
      byStatus = byStatus.filter(
        (o) => o.stockId === this.orderStockFilter || o.pickupStockId === this.orderStockFilter
      );
    }
    const filtradas = !q ? byStatus : byStatus.filter((o) =>
      (o.customer || '').toLowerCase().includes(q) ||
      (o.id || '').toLowerCase().includes(q) ||
      (o.trackingNumber || '').toLowerCase().includes(q) ||
      (o.address || '').toLowerCase().includes(q) ||
      (o.phone || '').toLowerCase().includes(q) ||
      (o.recipientName || '').toLowerCase().includes(q) ||
      (o.cancelReason || '').toLowerCase().includes(q)
    );
    if (this.orderAgingSort === 'none') {
      return filtradas;
    }
    // Copia antes de ordenar: `orders` es el arreglo del servicio.
    const signo = this.orderAgingSort === 'desc' ? -1 : 1;
    return [...filtradas].sort((a, b) => {
      const ta = Date.parse(String(a.createdAt ?? ''));
      const tb = Date.parse(String(b.createdAt ?? ''));
      const va = Number.isFinite(ta) ? ta : Number.MAX_SAFE_INTEGER;
      const vb = Number.isFinite(tb) ? tb : Number.MAX_SAFE_INTEGER;
      return (va - vb) * signo;
    });
  }

  get pagedOrders(): AdminOrder[] {
    return this.filteredOrdersStable.slice(this.orderPage * this.ORDER_PAGE_SIZE, (this.orderPage + 1) * this.ORDER_PAGE_SIZE);
  }

  get ordersTotalPages(): number {
    return Math.max(1, Math.ceil(this.filteredOrdersStable.length / this.ORDER_PAGE_SIZE));
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
    const allowed = this.permittedStockIds;
    return this.inventoryMovements
      .filter((m) => !allowed || allowed.has(m.stockId))
      .map((movement) => ({
        ...movement,
        stockName: this.stockName(movement.stockId),
        productName: this.productName(movement.productId),
        userName: movement.userName || this.employeeName(movement.userId),
        typeLabel: this.movementTypeLabel(movement.type),
        signedQty: this.movementSignedQty(movement)
      }));
  }

  get currentOperatorId(): number | null {
    const raw = Number(this.currentUser?.userId ?? NaN);
    return Number.isFinite(raw) ? raw : null;
  }

  get currentOperatorName(): string {
    return this.currentUser?.name?.trim() || this.employeeName(this.currentOperatorId);
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

  /** Pedidos de pickup pendientes donde el cliente pagará en sucursal. */
  get pendingPickupAtStoreOrders(): AdminOrder[] {
    return this.orders.filter((order) =>
      order.deliveryType === 'pickup' &&
      order.pickupPaymentMethod === 'at_store' &&
      order.status === 'pending' &&
      this.canCurrentOperatorHandlePickupOrder(order)
    );
  }

  get pendingPickupDeliveryOrders(): AdminOrder[] {
    return this.orders.filter((order) =>
      order.deliveryType === 'pickup' &&
      order.status === 'paid' &&
      this.canCurrentOperatorHandlePickupOrder(order)
    );
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

  get canSavePosCustomer(): boolean {
    return Boolean(
      this.hasPermission('customer_add') &&
      this.posCustomerForm.firstName.trim() &&
      this.posCustomerForm.apellidoPaterno.trim() &&

      !this.isSavingPosCustomer
    );
  }

  get selectedPosCustomer(): AdminCustomer | null {
    return this.customers.find((customer) => customer.id === this.selectedPosCustomerId) ?? null;
  }

  /** Ventas con saldo pendiente de esta sucursal, estén o no en un corte cerrado:
   *  la cajera encontró la venta parcial dentro del historial de cortes, en texto plano. */
  get posSalesWithBalance(): PosSale[] {
    const stockId = this.currentPosStock?.id;
    return this.posSales.filter(
      (sale) => (!stockId || sale.stockId === stockId) && sale.status !== 'voided' && Number(sale.pendingAmount || 0) > 0
    );
  }

  get visiblePosSales(): PosSale[] {
    const stockId = this.currentPosStock?.id;
    const operatorId = this.currentOperatorId;
    return this.posSales.filter(
      (sale) =>
        (!stockId || sale.stockId === stockId) &&
        (operatorId == null || sale.attendantUserId === operatorId) &&
        !sale.cashCutId
    );
  }

  get visibleCashPosSales(): PosSale[] {
    return this.visiblePosSales.filter((sale) => (sale.paymentMethod ?? 'cash') === 'cash');
  }

  get visibleCardPosSales(): PosSale[] {
    return this.visiblePosSales.filter((sale) => sale.paymentMethod === 'card');
  }

  get visibleTransferPosSales(): PosSale[] {
    return this.visiblePosSales.filter((sale) => sale.paymentMethod === 'transfer');
  }

  /** Pagos mixtos (paquete E): efectivo + tarjeta/transferencia. */
  get visibleMixedPosSales(): PosSale[] {
    return this.visiblePosSales.filter((sale) => sale.paymentMethod === 'mixed');
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
    // Modo cliente (paquete B): no aplica la escalera de descuento de socio.
    if (this.posCustomerIsClientMode) {
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

  get posCashierDiscountAmount(): number {
    if (!this.posAppliedCashierDiscount) return 0;
    if (this.posAppliedCashierDiscount.mode === 'percent') {
      return this.roundMoney(this.posSubtotal * (this.posAppliedCashierDiscount.value / 100));
    }
    return Math.min(this.posAppliedCashierDiscount.value, this.posSubtotal);
  }

  get posTotalDiscountAmount(): number {
    return this.roundMoney(this.posProjectedDiscountAmount + this.posCashierDiscountAmount);
  }

  get posEffectiveTotal(): number {
    return this.roundMoney(this.posSubtotal - this.posTotalDiscountAmount);
  }

  get posAmountPaidNow(): number {
    if (this.posPaymentTypeMode === 'full') return this.posEffectiveTotal;
    if (this.posPaymentTypeMode === 'credit') return 0;
    return Math.min(this.roundMoney(Number(this.posPartialAmountPaid) || 0), this.posEffectiveTotal);
  }

  get posPendingAmount(): number {
    return this.roundMoney(this.posEffectiveTotal - this.posAmountPaidNow);
  }

  get posProjectedDiscountLabel(): string {
    return `${Math.round(this.posProjectedDiscountRate * 100)}%`;
  }

  get posCurrentDiscountLabel(): string {
    const apiDiscount = this.posSelectedCustomerMonth?.currentDiscount;
    if (apiDiscount) {
      return `${Math.round(apiDiscount.rate * 100)}%`;
    }
    return this.selectedPosCustomer?.discount ?? '0%';
  }

  get posNextGoal(): { label: string; min: number } | null {
    const apiNextGoal = this.posSelectedCustomerMonth?.nextGoal;
    if (apiNextGoal) {
      return {
        min: apiNextGoal.min,
        label: apiNextGoal.label || `Descuento ${Math.round(apiNextGoal.rate * 100)}%`
      };
    }
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
    return this.posDisabledReason('cobrar') === '';
  }

  /** El cliente seleccionado está en modo cliente (paquete B): paga precio de lista, sin descuento de socio. */
  get posCustomerIsClientMode(): boolean {
    const modo = (this.selectedPosCustomer as { mode?: string } | null)?.mode;
    return String(modo || '').toLowerCase() === 'cliente';
  }

  /**
   * Por qué un botón del POS está deshabilitado, en una línea para alguien sin
   * capacitación (Nadia: el corte "deshabilitado sin ningún tooltip o mensaje").
   * Devuelve '' cuando el botón está habilitado.
   */
  posDisabledReason(accion: 'cobrar' | 'parcial' | 'descuento'): string {
    if (!this.hasPermission('pos_register_sale')) {
      return 'No tienes el permiso "Ventas en caja": pídeselo a tu gerente.';
    }
    if (!this.hasLinkedPosStock || !this.currentPosStock) {
      return 'Sin sucursal vinculada: pide a tu gerente que te agregue en Stocks → tu sucursal → "Empleados vinculados".';
    }
    if (accion === 'descuento') {
      if (this.posSubtotal <= 0) return 'Elige al menos un producto para aplicar un descuento.';
      return '';
    }
    if (accion === 'parcial') {
      if (this.posSalePaymentMethod === 'mixed') return 'El pago mixto solo aplica a pago completo. Cambia la forma de pago para cobrar en parcial o a crédito.';
      return '';
    }
    if (this.isRegisteringPosSale) return 'Registrando la venta…';
    if (this.posItems.size === 0) return 'Elige al menos un producto.';
    if (this.posMixedInvalidReason) return this.posMixedInvalidReason;
    if (this.posPaymentTypeMode === 'partial' && (this.posAmountPaidNow <= 0 || this.posAmountPaidNow >= this.posEffectiveTotal)) {
      return `Escribe cuánto paga ahora el cliente: mayor a $0 y menor al total (${this.formatMoney(this.posEffectiveTotal)}).`;
    }
    if (this.posCashShort > 0) {
      return `Faltan ${this.formatMoney(this.posCashShort)} de efectivo para cubrir la parte en efectivo (${this.formatMoney(this.posCashPortion)}).`;
    }
    return '';
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

  /** Pedidos en un estado dado; alimenta los contadores de las pestañas. */
  orderCountByStatus(status: AdminOrder['status']): number {
    return this.orders.filter((order) => order.status === status).length;
  }

  /** Productos activos sin ninguna imagen cargada (KPI "Assets faltantes"). */
  get productsMissingAssetsCount(): number {
    return this.products.filter((p) => p.active && !(p.images ?? []).some((img) => (img.url ?? '').trim())).length;
  }

  /**
   * Cola de trabajo derivada de los datos reales: le dice al operador qué es
   * lo siguiente que hay que hacer, en orden del flujo del pedido. Vacía = al día.
   */
  get nextActions(): Array<{ icon: string; label: string; count: number; view: AdminViewId; status?: AdminOrder['status'] }> {
    const actions: Array<{ icon: string; label: string; count: number; view: AdminViewId; status?: AdminOrder['status'] }> = [];
    const push = (icon: string, label: string, count: number, status: AdminOrder['status']) => {
      if (count > 0) {
        actions.push({ icon, label, count, view: 'orders', status });
      }
    };
    push('fa-hourglass-half', 'Confirmar pagos', this.orderCountByStatus('pending'), 'pending');
    push('fa-box', 'Preparar envíos', this.orderCountByStatus('paid'), 'paid');
    push('fa-truck', 'Confirmar entregas', this.orderCountByStatus('shipped'), 'shipped');
    push('fa-rotate-left', 'Recibir devoluciones', this.orderCountByStatus('en_devolucion'), 'en_devolucion');
    push('fa-money-bill-transfer', 'Resolver devoluciones validadas', this.orderCountByStatus('devuelto_validado'), 'devuelto_validado');
    return actions.slice(0, 4);
  }

  runNextAction(action: { view: AdminViewId; status?: AdminOrder['status'] }): void {
    // El estado viaja en la URL: al navegar, el caparazón se vuelve a montar y
    // un campo asignado aquí se perdería por el camino.
    this.router.navigate([ADMIN_ROUTE_BY_VIEW[action.view]],
                         action.status ? { queryParams: { estado: action.status } } : {});
  }


  get ordersCount(): number {
    return this.orders.length;
  }

  get ordersTotal(): number {
    return this.orders.reduce((acc, order) => acc + (order.total || 0), 0);
  }

  /** Dinero ya cobrado: excluye los pedidos que siguen pendientes de pago. */
  get ordersCollectedTotal(): number {
    return this.orders
      .filter((order) => order.status !== 'pending' && order.status !== 'cancelled')
      .reduce((acc, order) => acc + (order.total || 0), 0);
  }

  /** Dinero comprometido pero aún no cobrado. */
  get ordersPendingTotal(): number {
    return this.orders
      .filter((order) => order.status === 'pending')
      .reduce((acc, order) => acc + (order.total || 0), 0);
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
    // `commissions` es un campo histórico de la ficha que nadie actualiza; el
    // tablero decía "$0" con $126 confirmados por pagar este mes.
    // "Por depositar" = lo del mes anterior que sigue pendiente de pago (el día
    // 10 se paga el mes anterior), más lo ya confirmado del mes en curso.
    return this.customers.reduce((acc, customer) => {
      const prev = customer.commissionsPrevStatus === 'pending' ? (customer.commissionsPrevMonth ?? 0) : 0;
      return acc + prev + (customer.commissionsCurrentConfirmed ?? 0);
    }, 0);
  }

  get customersCount(): number {
    return this.customers.length;
  }

  /** Promedio del descuento vigente de los clientes (antes valor fijo en la vista). */
  get averageDiscountLabel(): string {
    if (!this.customers.length) {
      return '—';
    }
    const total = this.customers.reduce((sum, c) => sum + (parseFloat(c.discount) || 0), 0);
    return `${Math.round(total / this.customers.length)}%`;
  }

  get productsCount(): number {
    return this.products.length;
  }

  // --- STATS REPORT HELPERS ---

  loadMonthlyStats(month: string): void {
    if (this.isLoadingStats) return;
    this.isLoadingStats = true;
    this.statsData = null;
    this.adminControl.getMonthlyStats(month).subscribe({
      next: (data) => { this.statsData = data; this.isLoadingStats = false; this.requestViewUpdate(); },
      error: () => { this.isLoadingStats = false; this.requestViewUpdate(); }
    });
  }

  // ── WP-A · ronda 26 · propuesta 17: el mes lo manda el servidor ──────────
  /** Meses contables con datos, tal como los publica `GET /commissions/periodos`. */
  serverPeriodos: PagoPeriodo[] = [];
  /** Mes por omisión del servidor; nunca se calcula con el reloj del navegador. */
  serverDefaultMonth = '';
  /** Hora del servidor en el momento de cargar los periodos (§3.6). */
  serverNow = '';
  private readonly pagosService = inject(PagosService);
  private readonly planSocio = inject(PlanSocioService);

  /**
   * Alma estuvo media hora creyendo que marzo había cerrado en ceros y se bajó
   * un `reporte-mensual-2026-09.xlsx`: el navegador iba en 2026-09 y el mundo
   * en 2027-04. Los meses del dinero salen del servidor.
   */
  private cargarPeriodosDelServidor(): void {
    if (this.serverPeriodos.length || !this.hasPermission('commissions_register_payment')) {
      return;
    }
    this.pagosService.getPeriodos().subscribe({
      next: (datos) => {
        this.serverPeriodos = datos.periodos ?? [];
        this.serverDefaultMonth = datos.defaultMonth || '';
        this.serverNow = datos.serverNow || '';
        this.reportMonthsCache = null;
        if (!this.pagosMesMonth) {
          this.pagosMesMonth = this.serverDefaultMonth;
        }
        this.requestViewUpdate();
      },
      error: () => undefined
    });
  }

  /** El mes de las comisiones que se está viendo (17): del servidor, no del reloj. */
  get commissionsMonthKey(): string {
    return this.pagosMesMonth || this.serverDefaultMonth || this.getPrevMonthKey();
  }

  /** El mismo mes, en letras (§3.7): «marzo de 2027», nunca la clave cruda. */
  get commissionsMonthLabel(): string {
    return mesEnLetras(this.commissionsMonthKey);
  }

  private reportMonthsCache: { ordersRef: AdminOrder[]; months: { value: string; label: string }[] } | null = null;

  get availableReportMonths(): { value: string; label: string }[] {
    // Cachear por referencia de orders: un array nuevo en cada ciclo de
    // detección de cambios re-renderizaba el select en bucle (NG0103).
    if (this.reportMonthsCache?.ordersRef === this.orders) {
      return this.reportMonthsCache.months;
    }
    const monthSet = new Set<string>();
    // WP-A · 17: primero los meses que el servidor dice que tienen dinero.
    for (const periodo of this.serverPeriodos) {
      monthSet.add(periodo.monthKey);
    }
    if (this.serverNow) {
      monthSet.add(this.serverNow.slice(0, 7));
    }
    for (const order of this.orders) {
      if (order.createdAt) {
        const d = new Date(order.createdAt);
        if (!isNaN(d.getTime())) {
          monthSet.add(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
        }
      }
    }
    const months = [...monthSet]
      .sort((a, b) => b.localeCompare(a))
      .map((mk) => {
        const [y, m] = mk.split('-');
        const label = new Date(Number(y), Number(m) - 1, 1).toLocaleDateString('es-MX', { year: 'numeric', month: 'long' });
        return { value: mk, label: label.charAt(0).toUpperCase() + label.slice(1) };
      });
    this.reportMonthsCache = { ordersRef: this.orders, months };
    return months;
  }

  get activeReportMonth(): string {
    if (this.statsReportMonth) return this.statsReportMonth;
    // WP-A · 17: el mes vigente del servidor, no el del navegador; si todavía
    // no llegó, el primero de la lista, que sí tiene pedidos.
    if (this.serverNow) return this.serverNow.slice(0, 7);
    return this.availableReportMonths[0]?.value ?? '';
  }

  /** WP-A · 17: se dice cuando el mes que se está viendo no tiene movimientos. */
  get avisoMesEstadisticasSinDatos(): string {
    const mes = this.activeReportMonth;
    if (!mes || this.isLoadingStats || this.reportOrders.length) {
      return '';
    }
    const conDatos = this.availableReportMonths.filter((m) => m.value !== mes);
    const nombre = this.availableReportMonths.find((m) => m.value === mes)?.label ?? mes;
    return conDatos.length
      ? `${nombre} no tiene pedidos registrados. Elige otro mes: ${conDatos.slice(0, 6).map((m) => m.label).join(', ')}.`
      : `${nombre} no tiene pedidos registrados.`;
  }

  private isInReportMonth(isoDate?: string): boolean {
    if (!isoDate) return false;
    return isoDate.startsWith(this.activeReportMonth);
  }

  get reportOrders(): AdminOrder[] {
    return this.orders.filter((o) => this.isInReportMonth(o.createdAt));
  }

  get reportPosSales(): PosSale[] {
    return this.posSales.filter((s) => this.isInReportMonth(s.createdAt));
  }

  get reportMovements(): InventoryMovement[] {
    return this.inventoryMovements.filter((m) => this.isInReportMonth(m.createdAt));
  }

  // PEDIDOS — usa statsData del backend cuando esté disponible
  get reportOrdersTotal(): number {
    return this.statsData?.orders.total ?? this.reportOrders.reduce((s, o) => s + (o.total || 0), 0);
  }

  get reportOrdersCount(): number {
    return this.statsData?.orders.count ?? this.reportOrders.length;
  }

  get reportAvgTicket(): number {
    return this.statsData?.orders.avgTicket ?? (this.reportOrdersCount ? this.reportOrdersTotal / this.reportOrdersCount : 0);
  }

  get reportDeliveredCount(): number {
    return this.statsData?.orders.byStatus?.['delivered'] ?? this.reportOrders.filter((o) => o.status === 'delivered').length;
  }

  get reportConversionRate(): number {
    return this.reportOrdersCount ? (this.reportDeliveredCount / this.reportOrdersCount) * 100 : 0;
  }

  get reportOrdersByStatus(): Array<{ status: string; count: number; total: number }> {
    if (this.statsData) {
      return Object.entries(this.statsData.orders.byStatus).map(([status, count]) => ({ status, count, total: 0 })).sort((a, b) => b.count - a.count);
    }
    const map = new Map<string, { count: number; total: number }>();
    for (const o of this.reportOrders) {
      const s = o.status || 'unknown';
      const cur = map.get(s) ?? { count: 0, total: 0 };
      map.set(s, { count: cur.count + 1, total: cur.total + (o.total || 0) });
    }
    return [...map.entries()].map(([status, v]) => ({ status, ...v })).sort((a, b) => b.count - a.count);
  }

  get reportOrdersByPaymentMethod(): Array<{ method: string; count: number; total: number }> {
    if (this.statsData) {
      return Object.entries(this.statsData.orders.byPaymentMethod).map(([method, count]) => ({ method, count, total: 0 })).sort((a, b) => b.count - a.count);
    }
    const map = new Map<string, { count: number; total: number }>();
    for (const o of this.reportOrders) {
      const m = (o as AdminOrder & { paymentMethod?: string }).paymentMethod || 'online';
      const cur = map.get(m) ?? { count: 0, total: 0 };
      map.set(m, { count: cur.count + 1, total: cur.total + (o.total || 0) });
    }
    return [...map.entries()].map(([method, v]) => ({ method, ...v })).sort((a, b) => b.total - a.total);
  }

  get reportTopCustomersByOrders(): Array<{ name: string; count: number; total: number }> {
    if (this.statsData) {
      // Pintaba el ID como nombre; el resumen ya trae el nombre del cliente.
      return this.statsData.orders.topCustomers.map((c) => ({ name: (c as { name?: string }).name || String(c.customerId), count: c.orders, total: c.total }));
    }
    const map = new Map<string, { count: number; total: number }>();
    for (const o of this.reportOrders) {
      const key = (o.customer || 'Público General').trim();
      const cur = map.get(key) ?? { count: 0, total: 0 };
      map.set(key, { count: cur.count + 1, total: cur.total + (o.total || 0) });
    }
    return [...map.entries()]
      .map(([name, v]) => ({ name, ...v }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 15);
  }

  // CLIENTES
  get reportActiveCustomers(): Array<{ id: number; name: string; email: string; orderCount: number; total: number; level: string }> {
    const map = new Map<string, { id: number; name: string; email: string; orderCount: number; total: number; level: string }>();
    for (const o of this.reportOrders) {
      const key = (o.customer || '').trim().toLowerCase();
      if (!key) continue;
      const customer = this.customers.find((c) => c.name.trim().toLowerCase() === key);
      const cur = map.get(key) ?? { id: customer?.id ?? 0, name: o.customer || '', email: customer?.email || '', orderCount: 0, total: 0, level: customer?.level || '' };
      map.set(key, { ...cur, orderCount: cur.orderCount + 1, total: cur.total + (o.total || 0) });
    }
    return [...map.values()].sort((a, b) => b.total - a.total);
  }

  get reportActiveCustomersCount(): number {
    return this.statsData?.customers.activeCount ?? this.reportActiveCustomers.length;
  }

  get reportRepurchaseRate(): number {
    if (this.statsData) return this.statsData.customers.repurchaseRate;
    const total = this.reportActiveCustomers.length;
    if (!total) return 0;
    const repeaters = this.reportActiveCustomers.filter((c) => c.orderCount >= 2).length;
    return (repeaters / total) * 100;
  }

  get reportNewCustomersCount(): number {
    return this.statsData?.customers.newCount ?? 0;
  }

  // PRODUCTOS — usa statsData del backend cuando esté disponible
  get reportProductSales(): Array<{ id: number; name: string; sku: string; units: number; revenue: number; price: number }> {
    if (this.statsData) {
      return this.statsData.products.sales.map((p) => ({
        id: Number(p.productId) || 0,
        name: p.name,
        sku: this.products.find((pr) => String(pr.id) === String(p.productId))?.sku || '',
        units: p.units,
        revenue: p.revenue,
        price: p.units ? p.revenue / p.units : 0,
      }));
    }
    const map = new Map<number, { id: number; name: string; sku: string; units: number; revenue: number; price: number }>();
    const addLine = (productId: number, name: string, price: number, quantity: number) => {
      const product = this.products.find((p) => p.id === productId);
      const cur = map.get(productId) ?? { id: productId, name: product?.name || name, sku: product?.sku || '', units: 0, revenue: 0, price: product?.price ?? price };
      map.set(productId, { ...cur, units: cur.units + quantity, revenue: cur.revenue + price * quantity });
    };
    for (const o of this.reportOrders) {
      for (const line of ((o as AdminOrder & { lines?: AdminOrderItem[] }).lines ?? [])) {
        addLine(line.productId, line.name, line.price, line.quantity);
      }
    }
    for (const s of this.reportPosSales) {
      for (const line of (s.lines ?? [])) {
        addLine(line.productId, line.name, line.price, line.quantity);
      }
    }
    return [...map.values()].sort((a, b) => b.revenue - a.revenue);
  }

  get reportTotalUnitsSold(): number {
    return this.statsData?.products.totalUnitsSold ?? this.reportProductSales.reduce((s, p) => s + p.units, 0);
  }

  // STOCKS
  get reportStockSummary(): Array<{ stockId: string; name: string; location: string; entries: number; exits: number; sales: number }> {
    return this.stocks.map((stock) => {
      const moves = this.reportMovements.filter((m) => m.stockId === stock.id);
      const entries = moves.filter((m) => ['entry', 'entry_transfer'].includes(m.type)).reduce((s, m) => s + (m.qty || 0), 0);
      const exits = moves.filter((m) => ['exit_order', 'exit_transfer', 'pos_sale', 'damaged'].includes(m.type)).reduce((s, m) => s + (m.qty || 0), 0);
      const sales = this.reportPosSales.filter((s) => s.stockId === stock.id).reduce((acc, s) => acc + s.total, 0);
      return { stockId: stock.id, name: stock.name, location: stock.location, entries, exits, sales };
    });
  }

  get reportStockInventoryLines(): Array<{ stock: string; product: string; qty: number }> {
    const lines: Array<{ stock: string; product: string; qty: number }> = [];
    for (const stock of this.stocks) {
      for (const [pid, qty] of Object.entries(stock.inventory ?? {})) {
        const product = this.products.find((p) => String(p.id) === String(pid));
        if (product) {
          lines.push({ stock: stock.name, product: product.name, qty: Number(qty) });
        }
      }
    }
    return lines.sort((a, b) => a.stock.localeCompare(b.stock) || a.product.localeCompare(b.product));
  }

  // EXCEL DOWNLOADS

  /**
   * Construye una hoja garantizando los encabezados de columna AUNQUE no haya datos.
   * `XLSX.utils.json_to_sheet([])` produce una hoja vacía sin títulos; este helper
   * emite siempre la fila de encabezados (H11). Con datos, fija además el orden de columnas.
   */
  private buildSheet(rows: Array<Record<string, unknown>>, headers: string[]): XLSX.WorkSheet {
    if (!rows.length) {
      return XLSX.utils.aoa_to_sheet([headers]);
    }
    return XLSX.utils.json_to_sheet(rows, { header: headers });
  }

  downloadOrdersReport(): void {
    const month = this.activeReportMonth;
    const orders = this.reportOrders;
    const rows = orders.map((o) => ({
      'Folio': o.id,
      'Fecha': o.createdAt ? new Date(o.createdAt).toLocaleString('es-MX') : '',
      'Cliente': o.customer || 'Público General',
      'Estado': o.status,
      'Método pago': (o as AdminOrder & { paymentMethod?: string }).paymentMethod || 'online',
      'Subtotal': o.grossSubtotal ?? o.total,
      'Descuento': o.discountAmount ?? 0,
      'Total': o.total
    }));
    const wsByStatus = this.reportOrdersByStatus.map((r) => ({
      'Estado': r.status,
      'Pedidos': r.count,
      'Total': r.total
    }));
    const wsTop = this.reportTopCustomersByOrders.map((r) => ({
      'Cliente': r.name,
      'Pedidos': r.count,
      'Total': r.total
    }));
    const wb = XLSX.utils.book_new();
    const ws1 = this.buildSheet(rows, ['Folio', 'Fecha', 'Cliente', 'Estado', 'Método pago', 'Subtotal', 'Descuento', 'Total']);
    ws1['!cols'] = [{ wch: 18 }, { wch: 20 }, { wch: 28 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 12 }, { wch: 12 }];
    XLSX.utils.book_append_sheet(wb, ws1, 'Pedidos');
    const ws2 = this.buildSheet(wsByStatus, ['Estado', 'Pedidos', 'Total']);
    ws2['!cols'] = [{ wch: 20 }, { wch: 10 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws2, 'Por estado');
    const ws3 = this.buildSheet(wsTop, ['Cliente', 'Pedidos', 'Total']);
    ws3['!cols'] = [{ wch: 28 }, { wch: 10 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws3, 'Top clientes');
    XLSX.writeFile(wb, `pedidos-${month}.xlsx`);
  }

  // ── WP-H · Conciliar pagos con MercadoPago ────────────────────────────────
  // Para cuando alguien pagó y el webhook se perdió: el pedido sigue en
  // "Pendiente" aunque el dinero ya salió (rodrigo-dia3).
  private readonly conciliacion = inject(ConciliacionService);
  isConciliacionModalOpen = false;
  isConciliando = false;
  conciliacionResultado: ConciliacionResultado | null = null;
  conciliacionUltima: ConciliacionCorrida | null = null;
  conciliacionError = '';

  // ── Paquete G · ronda 26 · propuesta 26: la conciliación con rango ─────────
  // El endpoint acepta hasta 90 días y la pantalla la dejaba clavada en 72 h:
  // a Renata le encargaron revisar **todo marzo** y obtuvo "Revisados 0".
  readonly conciliacionRangos: Array<{ value: string; label: string; hours: number }> = [
    { value: '72', label: 'Últimas 72 horas', hours: 72 },
    { value: '168', label: 'Últimos 7 días', hours: 168 },
    { value: '720', label: 'Últimos 30 días', hours: 720 },
    { value: '2160', label: 'Últimos 90 días (lo máximo)', hours: 2160 },
    { value: 'desde', label: 'Desde una fecha…', hours: 0 }
  ];
  conciliacionRango = '72';
  /** Fecha de inicio en AAAA-MM-DD; la traduce a horas **el servidor**. */
  conciliacionDesde = '';
  /** Cada pedido revisado dispara una consulta a MercadoPago: se revisa por lotes. */
  conciliacionTope = 50;

  get conciliacionRangoEsFecha(): boolean {
    return this.conciliacionRango === 'desde';
  }

  get conciliacionRangoTexto(): string {
    const elegido = this.conciliacionRangos.find((r) => r.value === this.conciliacionRango);
    if (this.conciliacionRangoEsFecha) {
      return this.conciliacionDesde ? `desde el ${this.conciliacionDesde}` : 'desde la fecha que elijas';
    }
    return (elegido?.label ?? 'las últimas 72 horas').toLowerCase();
  }

  /** ¿Ya se está usando el periodo más largo que ofrece la pantalla? */
  get conciliacionEnElMaximo(): boolean {
    if (this.conciliacionRangoEsFecha) {
      return false;
    }
    const horas = this.conciliacionRangos.find((r) => r.value === this.conciliacionRango)?.hours ?? 0;
    return horas >= Math.max(...this.conciliacionRangos.map((r) => r.hours));
  }

  /**
   * Qué decir cuando la corrida no revisó nada.
   *
   * Ronda 7 · Marisol (crítica): con cuatro pedidos "Pendiente de pago" en esa
   * misma pantalla, la conciliación contestaba «no había nada que revisar.
   * Prueba con un periodo más largo» en los cuatro periodos, incluido el máximo
   * de 90 días: un consejo imposible de seguir y una respuesta falsa. Los
   * pendientes existen; lo que pasa es que no se pagan por MercadoPago.
   */
  get textoConciliacionSinRevisar(): string {
    const sinReferencia = this.conciliacionResultado?.withoutReference ?? 0;
    if (sinReferencia > 0) {
      const folios = (this.conciliacionResultado?.withoutReferenceOrderIds ?? []).join(', ');
      return (
        `En ${this.conciliacionRangoTexto} hay ${sinReferencia} ` +
        `${sinReferencia === 1 ? 'pedido pendiente que no tiene' : 'pedidos pendientes que no tienen'} ` +
        'pago en línea que consultar (se cobran en sucursal, por transferencia o se capturaron a mano), ' +
        'así que la conciliación no puede resolverlos: hay que darlos por cobrado uno por uno desde su pedido' +
        (folios ? `. Son: ${folios}.` : '.')
      );
    }
    if (this.conciliacionEnElMaximo) {
      return `No hay ningún pedido pendiente de pago en ${this.conciliacionRangoTexto}, que es el periodo más largo que se puede revisar: no quedó nada por conciliar.`;
    }
    return `No hay pedidos pendientes de pago en el periodo que elegiste (${this.conciliacionRangoTexto}): no había nada que revisar. Puedes probar con un periodo más largo.`;
  }

  get conciliacionBloqueada(): string {
    if (this.isConciliando) {
      return 'Consultando a MercadoPago…';
    }
    if (this.conciliacionRangoEsFecha && !this.conciliacionDesde) {
      return 'Elige desde qué fecha quieres revisar';
    }
    return '';
  }

  cambiarRangoConciliacion(value: string): void {
    this.conciliacionRango = value || '72';
    this.requestViewUpdate();
  }

  abrirConciliacion(): void {
    this.conciliacionResultado = null;
    this.conciliacionError = '';
    this.isConciliacionModalOpen = true;
    this.conciliacion.ultimaCorrida().subscribe({
      next: (run) => { this.conciliacionUltima = run; this.requestViewUpdate(); },
      error: () => { this.conciliacionUltima = null; this.requestViewUpdate(); }
    });
  }

  cerrarConciliacion(): void {
    this.isConciliacionModalOpen = false;
  }

  conciliarPagos(): void {
    if (this.isConciliando || this.conciliacionBloqueada) {
      return;
    }
    this.isConciliando = true;
    this.conciliacionError = '';
    const rango = this.conciliacionRangos.find((r) => r.value === this.conciliacionRango);
    const payload: ConciliacionPayload = this.conciliacionRangoEsFecha
      ? { since: this.conciliacionDesde, limit: this.conciliacionTope }
      : { hours: rango?.hours ?? 72, limit: this.conciliacionTope };
    this.conciliacion.conciliar(payload).pipe(
      finalize(() => { this.isConciliando = false; this.requestViewUpdate(); })
    ).subscribe({
      next: (resultado) => {
        // Lo que se muestra es lo que el servidor hizo, no lo que se pidió; y la
        // hora es la suya: escribirle encima `new Date()` dejaba la corrida
        // fechada en 2026-09 con el mundo en 2027-04.
        this.conciliacionResultado = resultado;
        this.conciliacionUltima = { ...resultado };
        if (resultado.credited.length) {
          this.adminControl.loadOrders().subscribe();
        }
        this.showSnackbar(this.resumenConciliacion(resultado));
      },
      error: (err: unknown) => {
        const cuerpo = (err as { error?: ConciliacionResultado } | null)?.error;
        if (cuerpo && Array.isArray(cuerpo.errors)) {
          this.conciliacionResultado = cuerpo;
        }
        this.conciliacionError = this.resolveUiErrorMessage(err, 'No se pudo consultar a MercadoPago. Inténtalo de nuevo en unos minutos.');
      }
    });
  }

  resumenConciliacion(r: ConciliacionResultado): string {
    const folios = r.credited.map((c) => c.orderId).join(', ');
    const base = `Revisados ${r.checked} · Acreditados ${r.credited.length}${folios ? ` (${folios})` : ''} · Sin pago ${r.unpaid.length}`;
    const conErrores = r.errors.length ? `${base} · Sin respuesta ${r.errors.length}` : base;
    return r.pending ? `${conErrores} · Faltan ${r.pending} por revisar` : conErrores;
  }

  downloadCustomersReport(): void {
    const month = this.activeReportMonth;
    const active = this.reportActiveCustomers;
    const allRows = this.customers.map((c) => {
      const act = active.find((a) => a.id === c.id);
      return {
        'ID': c.id,
        'Nombre': c.name,
        'Email': c.email,
        'Nivel': c.level,
        'Descuento': c.discount,
        'Pedidos en periodo': act?.orderCount ?? 0,
        'Compras en periodo': act?.total ?? 0,
        'Comisiones pendientes': c.commissionsCurrentPending ?? 0,
        'Comisiones confirmadas': c.commissionsCurrentConfirmed ?? 0,
        'CLABE': c.clabeInterbancaria || ''
      };
    });
    const activeRows = active.map((a) => ({
      'Nombre': a.name,
      'Email': a.email,
      'Nivel': a.level,
      'Pedidos': a.orderCount,
      'Total compras': a.total
    }));
    const wb = XLSX.utils.book_new();
    const ws1 = this.buildSheet(allRows, ['ID', 'Nombre', 'Email', 'Nivel', 'Descuento', 'Pedidos en periodo', 'Compras en periodo', 'Comisiones pendientes', 'Comisiones confirmadas', 'CLABE']);
    ws1['!cols'] = [{ wch: 8 }, { wch: 28 }, { wch: 30 }, { wch: 10 }, { wch: 12 }, { wch: 18 }, { wch: 18 }, { wch: 22 }, { wch: 22 }, { wch: 22 }];
    XLSX.utils.book_append_sheet(wb, ws1, 'Todos los clientes');
    const ws2 = this.buildSheet(activeRows, ['Nombre', 'Email', 'Nivel', 'Pedidos', 'Total compras']);
    ws2['!cols'] = [{ wch: 28 }, { wch: 30 }, { wch: 10 }, { wch: 10 }, { wch: 16 }];
    XLSX.utils.book_append_sheet(wb, ws2, `Activos ${month}`);
    XLSX.writeFile(wb, `clientes-${month}.xlsx`);
  }

  downloadProductsReport(): void {
    const month = this.activeReportMonth;
    const sales = this.reportProductSales;
    const salesRows = sales.map((p) => ({
      'ID': p.id,
      'Producto': p.name,
      'SKU': p.sku,
      'Precio unitario': p.price,
      'Unidades vendidas': p.units,
      'Ingresos': p.revenue
    }));
    const catalogRows = this.products.map((p) => {
      const s = sales.find((x) => x.id === p.id);
      return {
        'ID': p.id,
        'Producto': p.name,
        'SKU': p.sku || '',
        'Precio': p.price,
        'Activo': p.active ? 'Sí' : 'No',
        'En tienda': (p as AdminProduct & { inOnlineStore?: boolean }).inOnlineStore ? 'Sí' : 'No',
        'En POS': (p as AdminProduct & { inPOS?: boolean }).inPOS ? 'Sí' : 'No',
        'Unidades vendidas': s?.units ?? 0,
        'Ingresos': s?.revenue ?? 0
      };
    });
    const wb = XLSX.utils.book_new();
    const ws1 = this.buildSheet(salesRows, ['ID', 'Producto', 'SKU', 'Precio unitario', 'Unidades vendidas', 'Ingresos']);
    ws1['!cols'] = [{ wch: 8 }, { wch: 30 }, { wch: 14 }, { wch: 14 }, { wch: 18 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws1, `Ventas ${month}`);
    const ws2 = this.buildSheet(catalogRows, ['ID', 'Producto', 'SKU', 'Precio', 'Activo', 'En tienda', 'En POS', 'Unidades vendidas', 'Ingresos']);
    ws2['!cols'] = [{ wch: 8 }, { wch: 30 }, { wch: 14 }, { wch: 10 }, { wch: 8 }, { wch: 10 }, { wch: 8 }, { wch: 18 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws2, 'Catálogo');
    XLSX.writeFile(wb, `productos-${month}.xlsx`);
  }

  downloadStocksReport(): void {
    const month = this.activeReportMonth;
    const invRows = this.reportStockInventoryLines;
    const mvRows = this.reportMovements.map((m) => ({
      'Fecha': m.createdAt ? new Date(m.createdAt).toLocaleString('es-MX') : '',
      'Almacén': this.stockName(m.stockId),
      'Tipo': m.type,
      'Producto ID': m.productId,
      'Cantidad': m.qty,
      'Referencia': (m as InventoryMovement & { referenceId?: string }).referenceId || ''
    }));
    const summaryRows = this.reportStockSummary.map((s) => ({
      'Almacén': s.name,
      'Ubicación': s.location,
      'Entradas (uds)': s.entries,
      'Salidas (uds)': s.exits,
      'Ventas POS ($)': s.sales
    }));
    const wb = XLSX.utils.book_new();
    const ws1 = this.buildSheet(invRows.map((r) => ({ 'Almacén': r.stock, 'Producto': r.product, 'Stock actual': r.qty })), ['Almacén', 'Producto', 'Stock actual']);
    ws1['!cols'] = [{ wch: 24 }, { wch: 30 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws1, 'Inventario actual');
    const ws2 = this.buildSheet(summaryRows, ['Almacén', 'Ubicación', 'Entradas (uds)', 'Salidas (uds)', 'Ventas POS ($)']);
    ws2['!cols'] = [{ wch: 24 }, { wch: 24 }, { wch: 16 }, { wch: 16 }, { wch: 16 }];
    XLSX.utils.book_append_sheet(wb, ws2, `Resumen ${month}`);
    const ws3 = this.buildSheet(mvRows, ['Fecha', 'Almacén', 'Tipo', 'Producto ID', 'Cantidad', 'Referencia']);
    ws3['!cols'] = [{ wch: 20 }, { wch: 24 }, { wch: 16 }, { wch: 12 }, { wch: 10 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, ws3, 'Movimientos');
    XLSX.writeFile(wb, `stocks-${month}.xlsx`);
  }

  downloadFullReport(): void {
    const month = this.activeReportMonth;
    const wb = XLSX.utils.book_new();

    // Resumen ejecutivo
    const resumeRows = [
      { 'Indicador': 'Mes', 'Valor': month },
      { 'Indicador': 'Pedidos', 'Valor': this.reportOrdersCount },
      { 'Indicador': 'Ventas totales', 'Valor': this.reportOrdersTotal },
      { 'Indicador': 'Ticket promedio', 'Valor': this.reportAvgTicket },
      { 'Indicador': 'Tasa de entrega', 'Valor': `${this.reportConversionRate.toFixed(1)}%` },
      { 'Indicador': 'Clientes activos', 'Valor': this.reportActiveCustomersCount },
      { 'Indicador': 'Tasa recompra', 'Valor': `${this.reportRepurchaseRate.toFixed(1)}%` },
      { 'Indicador': 'Productos con ventas', 'Valor': this.reportProductSales.length },
      { 'Indicador': 'Unidades vendidas', 'Valor': this.reportTotalUnitsSold }
    ];
    const wsResumen = this.buildSheet(resumeRows, ['Indicador', 'Valor']);
    wsResumen['!cols'] = [{ wch: 28 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, wsResumen, 'Resumen');

    // Pedidos
    const ordersRows = this.reportOrders.map((o) => ({
      'Folio': o.id,
      'Fecha': o.createdAt ? new Date(o.createdAt).toLocaleString('es-MX') : '',
      'Cliente': o.customer || 'Público General',
      'Estado': o.status,
      'Total': o.total
    }));
    const wsOrders = this.buildSheet(ordersRows, ['Folio', 'Fecha', 'Cliente', 'Estado', 'Total']);
    wsOrders['!cols'] = [{ wch: 18 }, { wch: 20 }, { wch: 28 }, { wch: 14 }, { wch: 12 }];
    XLSX.utils.book_append_sheet(wb, wsOrders, 'Pedidos');

    // Clientes activos
    const custRows = this.reportActiveCustomers.map((c) => ({
      'Nombre': c.name,
      'Email': c.email,
      'Pedidos': c.orderCount,
      'Total': c.total
    }));
    const wsCust = this.buildSheet(custRows, ['Nombre', 'Email', 'Pedidos', 'Total']);
    wsCust['!cols'] = [{ wch: 28 }, { wch: 30 }, { wch: 10 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, wsCust, 'Clientes activos');

    // Productos
    const prodRows = this.reportProductSales.map((p) => ({
      'Producto': p.name,
      'SKU': p.sku,
      'Unidades': p.units,
      'Ingresos': p.revenue
    }));
    const wsProd = this.buildSheet(prodRows, ['Producto', 'SKU', 'Unidades', 'Ingresos']);
    wsProd['!cols'] = [{ wch: 30 }, { wch: 14 }, { wch: 12 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, wsProd, 'Productos');

    // Stocks
    const stockRows = this.reportStockInventoryLines.map((r) => ({
      'Almacén': r.stock,
      'Producto': r.product,
      'Stock actual': r.qty
    }));
    const wsStock = this.buildSheet(stockRows, ['Almacén', 'Producto', 'Stock actual']);
    wsStock['!cols'] = [{ wch: 24 }, { wch: 30 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, wsStock, 'Inventario');

    XLSX.writeFile(wb, `reporte-mensual-${month}.xlsx`);
  }

  get currentUser(): AuthUser | null {
    return this.authService.currentUser;
  }

  /**
   * Paquete E · ronda 26 · propuesta 27c · El puesto que pinta la insignia.
   * Decía ADMIN sobre el nombre de la cajera de tercer día, igual que sobre el
   * de la gerente de operaciones, y es lo primero que ve el cliente que se
   * asoma al mostrador. `role` sigue siendo `admin`: es la llave de las guardas.
   */
  get puestoDelUsuario(): string {
    return this.authService.jobTitleLabel(this.currentUser);
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
    const ordered: AdminViewId[] = ['orders', 'customers', 'employees', 'products', 'stocks', 'campaigns', 'pos', 'stats', 'honor_board', 'notifications', 'settings'];
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
      this.structureGraphCache !== null &&
      this.structureGraphCache.selectedCustomerId === this.selectedCustomer.id &&
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
    return Boolean(this.structureForm.firstName.trim() && this.structureForm.apellidoPaterno.trim());
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

  addDiscountTier(): void {
    const tiers = this.businessConfigDraft.rewards.discountTiers ?? [];
    const lastMin = tiers.length ? (tiers[tiers.length - 1].min ?? 0) : 0;
    tiers.push({ min: lastMin + 1000, max: null, rate: 0 });
    this.businessConfigDraft.rewards.discountTiers = tiers;
    this.refreshDiscountTierThresholds();
  }

  removeDiscountTier(index: number): void {
    const tiers = this.businessConfigDraft.rewards.discountTiers ?? [];
    tiers.splice(index, 1);
    this.businessConfigDraft.rewards.discountTiers = [...tiers];
    this.refreshDiscountTierThresholds();
  }

  addCommissionLevel(): void {
    const levels = this.businessConfigDraft.rewards.commissionLevels ?? [];
    levels.push({ gen: levels.length + 1, rate: 0, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 });
    this.businessConfigDraft.rewards.commissionLevels = [...levels];
  }

  removeCommissionLevel(index: number): void {
    const levels = this.businessConfigDraft.rewards.commissionLevels ?? [];
    if (levels.length <= 1) return;
    levels.splice(index, 1);
    this.businessConfigDraft.rewards.commissionLevels = [...levels];
  }

  commissionLevelPercentValue(level: CommissionLevelDraft): number {
    return this.roundMoney(this.normalizeDiscountRateValue(level?.rate) * 100);
  }

  updateCommissionLevelRate(index: number, value: unknown): void {
    const levels = this.businessConfigDraft.rewards.commissionLevels ?? [];
    if (!levels[index]) return;
    const percent = Math.min(100, this.parseNonNegativeNumber(value));
    levels[index].rate = this.roundMoney(percent / 100);
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

  downloadCommissionsReport(): void {
    // WP-A · 17: el archivo se llama y trae los datos del mes **seleccionado**.
    // Renata mandó como constancia del cierre de marzo un archivo que se
    // llamaba agosto de 2026 y se contradecía entre sus dos hojas.
    const prevMonthKey = this.commissionsMonthKey;
    // First fetch commission summary for prev month, then generate report
    this.adminControl.getCommissionsSummary(prevMonthKey).subscribe({
      next: (summary) => this._buildAndDownloadCommissionsReport(prevMonthKey, summary),
      error: () => this._buildAndDownloadCommissionsReport(prevMonthKey, {})
    });
  }

  private _buildAndDownloadCommissionsReport(
    prevMonthKey: string,
    summary: Record<string, { paidTotal: number; status: string; receiptUrl: string }>
  ): void {
    // Merge commission summary into customers for this export run
    const enrichedCustomers = this.customers.map((c) => {
      const s = summary[String(c.id)];
      if (!s) return c;
      return {
        ...c,
        commissionsPrevMonth: s.paidTotal,
        commissionsPrevStatus: s.status as AdminCustomer['commissionsPrevStatus'],
        commissionsPrevMonthKey: prevMonthKey,
        commissionsPrevReceiptUrl: s.receiptUrl || c.commissionsPrevReceiptUrl,
      };
    });
    const commissionLevels = this.businessConfig?.rewards?.commissionLevels ?? [];

    // --- helpers ---
    const prevDate = (() => {
      const [y, m] = prevMonthKey.split('-').map(Number);
      return new Date(y, (m as number) - 1, 1);
    })();
    const spendByName = this.getMonthlySpendByCustomerName(prevDate);
    const memberSpend = (name: string): number =>
      spendByName.get(this.normalizeCustomerKey(name)) ?? 0;

    const referralMap = this.buildReferralMap(enrichedCustomers);

    // Build tree levels for a given leader (L1, L2, L3)
    const buildTree = (leaderId: number): Array<{ member: AdminCustomer; treeLevel: number }> => {
      const result: Array<{ member: AdminCustomer; treeLevel: number }> = [];
      const l1 = referralMap.get(leaderId) ?? [];
      for (const m1 of l1) {
        result.push({ member: m1, treeLevel: 1 });
        const l2 = referralMap.get(m1.id) ?? [];
        for (const m2 of l2) {
          result.push({ member: m2, treeLevel: 2 });
          const l3 = referralMap.get(m2.id) ?? [];
          for (const m3 of l3) {
            result.push({ member: m3, treeLevel: 3 });
          }
        }
      }
      return result;
    };

    // Equivalencias en MXN para evaluar requisitos en PC (Plan abril 2026).
    const mxnPerVp = this.businessConfig?.bonuses?.vpConfig?.mxnPerVp ?? 50;
    const activationMxn = (this.businessConfig?.rewards?.activationNetMin ?? 20) * mxnPerVp;
    // Gasto de una "línea" (un directo + toda su descendencia) en MXN.
    const lineSpend = (rootId: number): number => {
      let total = 0;
      const queue = [rootId];
      const seen = new Set<number>();
      while (queue.length) {
        const id = queue.shift() as number;
        if (seen.has(id)) continue;
        seen.add(id);
        const node = enrichedCustomers.find((c) => c.id === id);
        if (node) total += memberSpend(node.name);
        for (const child of referralMap.get(id) ?? []) queue.push(child.id);
      }
      return total;
    };

    // Determine qualification for each commission level (generación)
    const checkQualification = (
      leader: AdminCustomer,
      treeMembers: Array<{ member: AdminCustomer; treeLevel: number }>,
      levelIndex: number
    ): { qualified: boolean; reason: string } => {
      const lvl = commissionLevels[levelIndex];
      if (!lvl) return { qualified: false, reason: 'Generación no configurada' };

      const leaderSpend = memberSpend(leader.name);
      const leaderPc = leaderSpend / mxnPerVp;
      const l1Members = treeMembers.filter((e) => e.treeLevel === 1);
      const activeDirects = l1Members.filter((e) => memberSpend(e.member.name) >= activationMxn).length;
      const reqPcLineMxn = (lvl.reqPCPerLine ?? 0) * mxnPerVp;
      const qualifyingLines = l1Members.filter((e) => lineSpend(e.member.id) >= reqPcLineMxn).length;

      const reasons: string[] = [];
      // Base: estar activo ($1,000 netos / mes).
      if (leaderSpend < activationMxn) {
        reasons.push(`inactivo: $${leaderSpend.toFixed(0)} < $${activationMxn.toFixed(0)} netos`);
      }
      if ((lvl.reqActiveDirects ?? 0) > 0 && activeDirects < (lvl.reqActiveDirects ?? 0)) {
        reasons.push(`${activeDirects} directos activos < mín ${lvl.reqActiveDirects}`);
      }
      if ((lvl.reqPersonalPC ?? 0) > 0 && leaderPc < (lvl.reqPersonalPC ?? 0)) {
        reasons.push(`${leaderPc.toFixed(1)} PC personales < mín ${lvl.reqPersonalPC}`);
      }
      if ((lvl.reqLines ?? 0) > 0 && qualifyingLines < (lvl.reqLines ?? 0)) {
        reasons.push(`${qualifyingLines} líneas de ${lvl.reqPCPerLine} PC < mín ${lvl.reqLines}`);
      }
      return reasons.length === 0
        ? { qualified: true, reason: '' }
        : { qualified: false, reason: reasons.join('; ') };
    };

    // --- Sheet 1: Summary (existing behaviour, all customers) ---
    const summaryRows = enrichedCustomers
      .filter((c) => (c.commissionsPrevMonth ?? 0) > 0 || c.commissionsPrevStatus === 'pending')
      .sort((a, b) => {
        if (a.commissionsPrevStatus === 'pending' && b.commissionsPrevStatus !== 'pending') return -1;
        if (b.commissionsPrevStatus === 'pending' && a.commissionsPrevStatus !== 'pending') return 1;
        return (b.commissionsPrevMonth ?? 0) - (a.commissionsPrevMonth ?? 0);
      })
      .map((c) => ({
        'Nombre': c.name,
        'Email': c.email,
        'Nivel': c.level,
        'Descuento': c.discount,
        'Período': c.commissionsPrevMonthKey || prevMonthKey,
        'Comisión a pagar': c.commissionsPrevMonth ?? 0,
        'Estado': this.commissionStatusLabel(c.commissionsPrevStatus),
        'CLABE': c.clabeInterbancaria || ''
      }));

    const wsSummary = this.buildSheet(summaryRows, ['Nombre', 'Email', 'Nivel', 'Descuento', 'Período', 'Comisión a pagar', 'Estado', 'CLABE']);
    wsSummary['!cols'] = [
      { wch: 28 }, { wch: 30 }, { wch: 8 }, { wch: 12 },
      { wch: 10 }, { wch: 18 }, { wch: 22 }, { wch: 22 }
    ];

    // --- Sheet 2: Per-customer tree breakdown ---
    type DesgloceRow = {
      'Líder': string;
      'Email líder': string;
      'CLABE líder': string;
      'Comisión registrada': number | string;
      'Estado pago': string;
      'Miembro del árbol': string;
      'Nivel en árbol': string;
      'Compra del miembro ($)': number;
      'Tasa comisión (%)': number;
      'Comisión ganada ($)': number;
      'Comisión perdida ($)': number;
      'Motivo de pérdida': string;
    };

    const desgloceRows: DesgloceRow[] = [];

    // Include all customers that have any tree OR any commissions
    const leadersToInclude = enrichedCustomers.filter((c) => {
      const hasTree = (referralMap.get(c.id) ?? []).length > 0;
      const hasCommissions = (c.commissionsPrevMonth ?? 0) > 0 || c.commissionsPrevStatus === 'pending';
      return hasTree || hasCommissions;
    });

    for (const leader of leadersToInclude) {
      const treeMembers = buildTree(leader.id);

      if (treeMembers.length === 0) {
        // No tree — still show as a row with no breakdown
        desgloceRows.push({
          'Líder': leader.name,
          'Email líder': leader.email,
          'CLABE líder': leader.clabeInterbancaria || '',
          'Comisión registrada': leader.commissionsPrevMonth ?? 0,
          'Estado pago': this.commissionStatusLabel(leader.commissionsPrevStatus),
          'Miembro del árbol': '(sin red)',
          'Nivel en árbol': '',
          'Compra del miembro ($)': 0,
          'Tasa comisión (%)': 0,
          'Comisión ganada ($)': 0,
          'Comisión perdida ($)': 0,
          'Motivo de pérdida': ''
        });
        continue;
      }

      // Pre-compute qualification per commission level
      const qualByLevel: Array<{ qualified: boolean; reason: string }> = commissionLevels.map((_, idx) =>
        checkQualification(leader, treeMembers, idx)
      );

      let firstRowForLeader = true;
      for (const { member, treeLevel } of treeMembers) {
        const levelIndex = treeLevel - 1;
        const lvl = commissionLevels[levelIndex];
        const rate = lvl ? Number(lvl.rate ?? 0) : 0;
        const ratePercent = this.roundMoney(rate * 100);
        const spend = memberSpend(member.name);
        const potential = this.roundMoney(spend * rate);

        const qual = qualByLevel[levelIndex] ?? { qualified: false, reason: 'Nivel no configurado' };
        const earned = qual.qualified ? potential : 0;
        const lost = qual.qualified ? 0 : potential;

        desgloceRows.push({
          'Líder': firstRowForLeader ? leader.name : '',
          'Email líder': firstRowForLeader ? leader.email : '',
          'CLABE líder': firstRowForLeader ? (leader.clabeInterbancaria || '') : '',
          'Comisión registrada': firstRowForLeader ? (leader.commissionsPrevMonth ?? 0) : '',
          'Estado pago': firstRowForLeader ? this.commissionStatusLabel(leader.commissionsPrevStatus) : '',
          'Miembro del árbol': member.name,
          'Nivel en árbol': `L${treeLevel}`,
          'Compra del miembro ($)': spend,
          'Tasa comisión (%)': ratePercent,
          'Comisión ganada ($)': earned,
          'Comisión perdida ($)': lost,
          'Motivo de pérdida': qual.qualified ? '' : qual.reason
        });
        firstRowForLeader = false;
      }

      // Totals row per leader
      const totalEarned = this.roundMoney(
        treeMembers.reduce((s, { member, treeLevel }) => {
          const idx = treeLevel - 1;
          const rate = commissionLevels[idx] ? Number(commissionLevels[idx].rate ?? 0) : 0;
          return s + ((qualByLevel[idx]?.qualified ? memberSpend(member.name) * rate : 0));
        }, 0)
      );
      const totalLost = this.roundMoney(
        treeMembers.reduce((s, { member, treeLevel }) => {
          const idx = treeLevel - 1;
          const rate = commissionLevels[idx] ? Number(commissionLevels[idx].rate ?? 0) : 0;
          return s + ((!qualByLevel[idx]?.qualified ? memberSpend(member.name) * rate : 0));
        }, 0)
      );
      desgloceRows.push({
        'Líder': '',
        'Email líder': '',
        'CLABE líder': '',
        'Comisión registrada': '',
        'Estado pago': '',
        'Miembro del árbol': 'TOTAL',
        'Nivel en árbol': '',
        'Compra del miembro ($)': treeMembers.reduce((s, { member }) => s + memberSpend(member.name), 0),
        'Tasa comisión (%)': 0,
        'Comisión ganada ($)': totalEarned,
        'Comisión perdida ($)': totalLost,
        'Motivo de pérdida': ''
      });
      // Blank separator between leaders
      desgloceRows.push({
        'Líder': '', 'Email líder': '', 'CLABE líder': '', 'Comisión registrada': '', 'Estado pago': '',
        'Miembro del árbol': '', 'Nivel en árbol': '', 'Compra del miembro ($)': 0,
        'Tasa comisión (%)': 0, 'Comisión ganada ($)': 0, 'Comisión perdida ($)': 0, 'Motivo de pérdida': ''
      });
    }

    const wsDesgloce = this.buildSheet(desgloceRows, ['Líder', 'Email líder', 'CLABE líder', 'Comisión registrada', 'Estado pago', 'Miembro del árbol', 'Nivel en árbol', 'Compra del miembro ($)', 'Tasa comisión (%)', 'Comisión ganada ($)', 'Comisión perdida ($)', 'Motivo de pérdida']);
    wsDesgloce['!cols'] = [
      { wch: 28 }, { wch: 30 }, { wch: 22 }, { wch: 22 }, { wch: 18 },
      { wch: 28 }, { wch: 14 }, { wch: 22 }, { wch: 18 }, { wch: 22 }, { wch: 22 }, { wch: 45 }
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, wsSummary, 'Resumen');
    XLSX.utils.book_append_sheet(wb, wsDesgloce, 'Desglose por árbol');
    XLSX.writeFile(wb, `comisiones-${prevMonthKey}.xlsx`);
  }
  // end _buildAndDownloadCommissionsReport

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


  onAdminNavSelect(entryId: string): void {
    const entrada = this.adminMenuLinksStable.find((e) => e.id === entryId);
    if (entrada) {
      this.irAEntradaDeMenu(entrada);
    }
  }

  /**
   * Paquete E · ronda 26 · Cambiar de vista NAVEGA, ya no asigna un campo: así
   * la URL siempre dice en qué pantalla estás, se puede mandar por correo y
   * recargar te devuelve al mismo sitio.
   */
  setView(view: AdminViewId): void {
    if (!this.canAccessView(view)) {
      return;
    }
    this.router.navigateByUrl(ADMIN_ROUTE_BY_VIEW[view]);
  }

  /** Abre una pantalla del back office por su URL (menú lateral y barra móvil). */
  irAEntradaDeMenu(entrada: AdminMenuEntry): void {
    this.router.navigateByUrl(entrada.route);
  }

  private loadStocksAndPosState(): void {
    // Los mínimos por producto (paquete F) viajan aparte y una sola vez: la
    // tabla los necesita para pintar en rojo lo que está por debajo.
    this.cargarMinimosDeStock();
    this.adminControl.loadStocksAndPosState().subscribe({
      next: (state) => {
        this.stocks = (state.stocks ?? []).map((stock) => ({
          id: stock.id,
          name: stock.name,
          location: stock.location,
          linkedUserIds: stock.linkedUserIds ?? [],
          inventory: this.normalizeInventoryRecord(stock.inventory as Record<number, number> | Record<string, number>),
          allowPickup: Boolean((stock as { allowPickup?: boolean }).allowPickup),
          isMainWarehouse: Boolean((stock as { isMainWarehouse?: boolean }).isMainWarehouse),
          city: (stock as { city?: string }).city || undefined,     // paquete C
          state: (stock as { state?: string }).state || undefined   // paquete C
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
          paymentMethod: movement.paymentMethod,
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
          status: sale.status ? String(sale.status) : undefined,
          voidReason: sale.voidReason ? String(sale.voidReason) : undefined,
          discountAmount: Number(sale.discountAmount ?? 0),
          cashierDiscountAmount: sale.cashierDiscountAmount != null ? Number(sale.cashierDiscountAmount) : undefined,
          total: Number(sale.total),
          paymentStatus: sale.paymentStatus,
          deliveryStatus: sale.deliveryStatus,
          paymentMethod: sale.paymentMethod,
          createdAt: sale.createdAt ?? '',
          lines: sale.lines ?? [],
          cashCutId: sale.cashCutId,
          paymentType: sale.paymentType,
          amountPaid: sale.amountPaid != null ? Number(sale.amountPaid) : undefined,
          pendingAmount: sale.pendingAmount != null ? Number(sale.pendingAmount) : undefined,
        }));

        if (!this.selectedStockId && this.stocks.length) {
          this.selectStock(this.stocks[0].id);
        } else if (this.selectedStockId && !this.stocks.some((stock) => stock.id === this.selectedStockId)) {
          this.selectStock(this.stocks[0]?.id ?? '');
        }
        // Ronda 7 · Rubén: una sección que el rol no puede leer se queda vacía,
        // pero se dice con esas palabras. Antes el 403 se convertía en «no hay
        // ninguna bodega dada de alta» y el cajero pasaba el turno buscando un
        // alta que no le tocaba hacer.
        this.seccionesSinAcceso = state.sinAcceso ?? [];
        this.syncPosOperatorContext();
        this.refreshPosCashControl();
        this.applyEmployeeDefaultStock(); // WP-D
        this.requestViewUpdate();
      }
    });
  }

  /** Secciones que el rol no puede leer (403), para no fingir que están vacías. */
  seccionesSinAcceso: string[] = [];

  get avisoSeccionesSinAcceso(): string {
    if (!this.seccionesSinAcceso.length) {
      return '';
    }
    const lista = this.seccionesSinAcceso.join(', ');
    return `No tienes permiso para ver ${lista}. No es que esté vacío: pídele a quien administra los permisos que te lo conceda.`;
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
    this.currentOrderTab = status;
    this.orderPage = 0;
    // El buscador YA NO se borra al cambiar de pestaña: se escribía "Ximena",
    // se cambiaba de estado para encontrarla y la búsqueda desaparecía sola.
    // Si no hay carga inicial completa, cargar el status específico
    if (!this.adminControl.hasLoadedOrders()) {
      this.adminControl.loadOrders(status).subscribe();
    }
  }

  /** Cambia de pestaña en Pedidos: un estado o la bandeja de facturas (propuesta 20). */
  setOrderTab(tab: { key: string; status?: AdminOrder['status'] }): void {
    this.orderStatusFijadoPorUrl = true;
    if (tab.status) {
      this.setOrderStatus(tab.status);
      return;
    }
    this.currentOrderTab = tab.key;
    this.orderPage = 0;
  }

  /**
   * Contador de cada pestaña. La bandeja de facturas cuenta las solicitadas
   * sobre los pedidos ya cargados: dos del 4 de marzo con 37 días encima, que
   * Alma armó abriendo pedido por pedido.
   */
  orderTabCount(tab: { key: string; status?: AdminOrder['status'] }): number {
    if (tab.status) {
      return this.orderCountByStatus(tab.status);
    }
    return this.orders.filter((order) => order.invoiceStatus === 'solicitada').length;
  }

  pageRange(totalPages: number, current: number): number[] {
    const delta = 2;
    const start = Math.max(0, current - delta);
    const end = Math.min(totalPages - 1, current + delta);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }

  setPage(table: 'orders' | 'customers' | 'products' | 'employees' | 'notifications', page: number): void {
    if (table === 'orders') this.orderPage = page;
    else if (table === 'customers') this.customerPage = page;
    else if (table === 'products') this.productPage = page;
    else if (table === 'employees') this.employeePage = page;
    else if (table === 'notifications') this.notificationPage = page;
  }

  onTableSearch(table: 'orders' | 'customers' | 'products' | 'employees' | 'notifications', value: string): void {
    if (table === 'orders') { this.orderSearch = value; this.orderPage = 0; }
    else if (table === 'customers') { this.customerSearch = value; this.customerPage = 0; }
    else if (table === 'products') { this.productSearch = value; this.productPage = 0; }
    else if (table === 'employees') { this.employeeSearch = value; this.employeePage = 0; }
    else if (table === 'notifications') { this.notificationSearch = value; this.notificationPage = 0; }
  }

  showActions(): void {
    this.isActionsModalOpen = true;
  }

  resolveWarning(warning: { type: string; monthKey?: string }): void {
    this.isActionsModalOpen = false;
    if (warning.type === 'commissions_ready' || warning.type === 'commissions_no_clabe') { // WP-A
      // Comisiones y pagos ya tiene URL propia: se llega por ella, no bajando
      // hasta el fondo de la ficha de un cliente sin comisiones.
      this.router.navigate(['/admin/comisiones'],
                           warning.monthKey ? { queryParams: { mes: warning.monthKey } } : {});
      return;
    }
    const target: AdminViewId = this.warningTargetView(warning.type);
    // 'pickup' entra aquí por el paquete F (propuesta 21): los pedidos por
    // recoger en mostrador también están pagados y esperando trabajo.
    const estado = warning.type === 'shipping' || warning.type === 'pickup' ? 'paid'
      : warning.type === 'payments' ? 'pending'
      : warning.type === 'refunds' ? 'cancelled'
      : warning.type === 'invoices' ? 'factura_solicitada'
      : '';
    this.router.navigate([ADMIN_ROUTE_BY_VIEW[target]], estado ? { queryParams: { estado } } : {});
  }

  openNewOrderModal(): void {
    if (!this.hasPermission('order_create')) {
      return;
    }
    this.resetNewOrderForm();
    this.newOrderMessage = '';
    this.isNewOrderModalOpen = true;
    // El modal necesita clientes y productos, pero esas listas solo se cargaban
    // al ENTRAR en sus respectivas secciones. Abriéndolo desde Pedidos —que es
    // la pantalla de inicio— salía con el desplegable de clientes vacío y la
    // caja de productos en blanco, sin explicar por qué. Ambos cargadores
    // devuelven la caché si ya se pidieron, así que esto no repite trabajo.
    forkJoin({
      customers: this.adminControl.loadCustomers(),
      products: this.adminControl.loadProducts()
    }).subscribe({
      next: () => {
        this.newOrderCustomerId ??= this.customers[0]?.id ?? null;
        this.requestViewUpdate();
      },
      error: () => {
        this.newOrderMessage = 'No se pudieron cargar clientes y productos. Reintenta en unos segundos.';
        this.requestViewUpdate();
      }
    });
  }

  openAddStructureModal(): void {
    if (!this.hasPermission('customer_add')) {
      return;
    }
    this.resetStructureForm();
    this.isAddStructureModalOpen = true;
  }

  openPosCustomerModal(): void {
    if (!this.hasPermission('customer_add')) {
      return;
    }
    this.resetPosCustomerForm();
    this.isPosCustomerModalOpen = true;
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
    this.isPosCustomerModalOpen = false;
    this.isPosPaymentModalOpen = false;
    this.isShippingModalOpen = false;
    this.isReceiptModalOpen = false;
  }

  closePosCustomerModal(): void {
    this.isPosCustomerModalOpen = false;
    this.resetPosCustomerForm();
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

  /**
   * Último recurso mientras `GET /commissions/periodos` no ha respondido.
   * Quien decide el mes es el servidor (`commissionsMonthKey`).
   */
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
    const monthKey = this.receiptTargetCustomer.commissionsPrevMonthKey || this.commissionsMonthKey;
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
        switchMap((respuesta) => this.adminControl.load().pipe(map(() => respuesta))),
        finalize(() => {
          this.isUploadingReceipt = false;
          this.closeReceiptModal();
        })
      )
      .subscribe({
        next: (respuesta) => {
          const recibo = (respuesta as { receipt?: { receiptId?: string; monthKey?: string; status?: string } })?.receipt;
          this.showSnackbar(recibo?.receiptId
            ? `Comprobante ${recibo.receiptId} guardado para ${recibo.monthKey || monthKey}: el mes quedó ${recibo.status === 'paid' ? 'pagado' : (recibo.status || 'registrado')}.`
            : 'Comprobante cargado.');
        },
        error: () => {
          this.receiptError = 'No se pudo cargar el comprobante.';
        }
      });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  /** Último pedido cuyo enlace se copió; el botón lo dice sin abrir un toast. */
  enlacePedidoCopiadoId: string | null = null; // paquete E · ronda 26

  /**
   * Copia la dirección de este pedido. El detalle era un acordeón dentro de una
   * pantalla sin dirección: "Si alguien me pregunta dónde se pagan las
   * comisiones tendría que contestarle: en Clientes, hasta abajo" era el mismo
   * problema una pantalla más allá.
   */
  copiarEnlaceDePedido(order: AdminOrder): void {
    const base = typeof window !== 'undefined' ? window.location.href.split('#')[0] : '';
    const enlace = `${base}#/admin/pedido/${order.id}`;
    const portapapeles = typeof navigator !== 'undefined' ? navigator.clipboard : undefined;
    if (!portapapeles?.writeText) {
      this.showSnackbar('Tu navegador no deja copiar solo; selecciona el enlace y cópialo a mano.', 'error');
      return;
    }
    portapapeles.writeText(enlace).then(
      () => {
        this.enlacePedidoCopiadoId = order.id;
        this.showSnackbar('Enlace del pedido copiado. Ya se puede mandar por correo o WhatsApp.');
        this.cdr.detectChanges();
      },
      () => this.showSnackbar('No se pudo copiar; selecciona el enlace y cópialo a mano.', 'error')
    );
  }

  toggleOrderDetail(orderId: string): void {
    this.expandedOrderDetailId = this.expandedOrderDetailId === orderId ? null : orderId;
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
    // Ronda 7 · Marisol (crítica): «"Marcar como pagado" mueve dinero de un
    // clic: sin confirmación, sin referencia y sin deshacer». Dar por cobrado
    // un pedido dispara comisiones y no hay acción para revertirlo; borrar los
    // datos de un cliente sí avisaba con tres renglones. El acto que toca el
    // dinero es el que ahora pregunta, y pide la referencia del depósito.
    if (nextStatus === 'paid') {
      this.abrirConfirmacion({
        title: `Dar por pagado ${order.id}`,
        effect:
          `Vas a registrar el cobro de ${this.formatMoney(order.total ?? 0)} de ${order.customer}. ` +
          'El pedido pasa a Pagado, se dispara el cálculo de comisiones y se avisa por correo. ' +
          'No hay forma de revertirlo desde esta pantalla: si te equivocas, tendrás que cancelar el pedido.',
        requireReason: true,
        reasonLabel: 'Referencia del depósito o del pago',
        reasonPlaceholder: 'Folio de la transferencia, terminal o "efectivo en mostrador"',
        confirmLabel: 'Sí, ya se cobró',
        danger: true,
        ejecutar: (referencia: string) => this.marcarPedidoPagado(order, referencia)
      });
      return;
    }
    this.cambiarEstadoPedido(order, nextStatus);
  }

  /** Registra el cobro con su referencia; la confirmación muestra lo que guardó el servidor. */
  private marcarPedidoPagado(order: AdminOrder, referencia: string): void {
    this.updatingOrderIds.add(order.id);
    this.adminControl
      .updateOrderStatus(order.id, { status: 'paid', paymentReference: referencia.trim() })
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(order.id);
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (guardado) => {
          const texto = `Pedido ${guardado?.id || order.id} de ${order.customer}: quedó ${this.orderStatusLabel(guardado?.status || 'paid')}` +
            (referencia.trim() ? ` con la referencia ${referencia.trim()}.` : '.');
          this.confirmacionLista(texto, 'Cobro registrado');
          this.showSnackbar(texto);
        },
        error: (error: unknown) => {
          const mensaje = this.resolveUiErrorMessage(error, 'No se pudo registrar el cobro.');
          this.confirmacionFallo(mensaje);
          this.showSnackbar(mensaje, 'error');
        }
      });
  }

  private cambiarEstadoPedido(order: AdminOrder, nextStatus: AdminOrder['status']): void {
    this.updatingOrderIds.add(order.id);
    this.adminControl
      .updateOrderStatus(order.id, { status: nextStatus })
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(order.id);
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (guardado) =>
          // El estado que se anuncia es el que devolvió el servidor, no el que se pidió.
          this.showSnackbar(
            `Pedido ${guardado?.id || order.id} de ${order.customer}: quedó ${this.orderStatusLabel(guardado?.status || nextStatus)}.`
          ),
        error: (error: unknown) => {
          this.showSnackbar(this.resolveUiErrorMessage(error, 'No se pudo actualizar la orden.'), 'error');
        }
      });
  }

  orderNoteDrafts: Record<string, string> = {};

  isChangePasswordModalOpen = false;
  isSavingPassword = false;
  passwordError = '';
  passwordForm = { current: '', next: '', confirm: '' };

  openChangePasswordModal(): void {
    this.passwordForm = { current: '', next: '', confirm: '' };
    this.passwordError = '';
    this.isChangePasswordModalOpen = true;
  }

  closeChangePasswordModal(): void {
    this.isChangePasswordModalOpen = false;
  }

  submitChangePassword(): void {
    const { current, next, confirm } = this.passwordForm;
    if (!current || !next) {
      this.passwordError = 'Escribe tu contraseña actual y la nueva.';
      return;
    }
    if (next.length < 8) {
      this.passwordError = 'La nueva contraseña debe tener al menos 8 caracteres.';
      return;
    }
    if (next !== confirm) {
      this.passwordError = 'Las contraseñas no coinciden.';
      return;
    }
    this.passwordError = '';
    this.isSavingPassword = true;
    this.api
      .changePassword(String(this.currentUser?.userId ?? ''), { currentPassword: current, newPassword: next })
      .pipe(finalize(() => { this.isSavingPassword = false; this.requestViewUpdate(); }))
      .subscribe({
        next: () => {
          this.closeChangePasswordModal();
          this.showSnackbar('Contraseña actualizada. Te llegará un correo de confirmación.');
        },
        error: (error: unknown) => {
          this.passwordError = this.resolveUiErrorMessage(error, 'No se pudo cambiar la contraseña.');
        }
      });
  }

  addOrderNote(order: AdminOrder): void {
    const text = (this.orderNoteDrafts[order.id] || '').trim();
    if (!text) {
      return;
    }
    this.adminControl.addOrderNote(order.id, text).subscribe({
      next: (guardado) => {
        this.orderNoteDrafts[order.id] = '';
        const total = guardado?.adminNotes?.length ?? 0;
        this.showSnackbar(`Nota guardada: el pedido ${guardado?.id || order.id} tiene ${total} nota${total === 1 ? '' : 's'} interna${total === 1 ? '' : 's'}.`);
        this.requestViewUpdate();
      },
      error: (error: unknown) => this.showSnackbar(this.resolveUiErrorMessage(error, 'No se pudo guardar la nota.'), 'error')
    });
  }

  canCancelOrder(order: AdminOrder): boolean {
    return (order.status === 'pending' || order.status === 'paid') && this.hasPermission('order_mark_paid');
  }

  cancelOrderFromAdmin(order: AdminOrder): void {
    if (!this.canCancelOrder(order) || this.updatingOrderIds.has(order.id)) {
      return;
    }
    const aviso = order.status === 'paid'
      ? `El pedido ya está pagado: quedará cancelado con el pago pendiente de reembolso (${this.formatMoney(order.total)}) y se le avisará al cliente por correo.`
      : 'Este pedido no se ha pagado: quedará cancelado y se le avisará al cliente por correo.';
    // Antes era un prompt del navegador sin efecto escrito (Sofía).
    this.abrirConfirmacion({
      title: `Cancelar el pedido ${order.id} de ${order.customer}`,
      effect: `${aviso} El motivo queda en el pedido y en el aviso al cliente.`,
      requireReason: true,
      reasonLabel: 'Motivo de la cancelación',
      confirmLabel: 'Cancelar el pedido',
      danger: true,
      ejecutar: (motivo) => {
        this.updatingOrderIds.add(order.id);
        this.adminControl
          .cancelOrder(order.id, motivo || 'admin_request')
          .pipe(
            finalize(() => {
              this.updatingOrderIds.delete(order.id);
              this.requestViewUpdate();
            })
          )
          .subscribe({
            next: (respuesta) => {
              // Lo que quedó guardado, leído de la respuesta (no del formulario).
              const estado = this.orderStatusLabel((respuesta?.status || 'cancelled') as AdminOrder['status']);
              const reembolso = respuesta?.pendingRefund ? ' Queda un reembolso pendiente: hazlo desde "Reembolsar".' : ' No hay reembolso pendiente.';
              this.confirmacionLista(`El servidor dejó el pedido ${respuesta?.orderId || order.id} en estado "${estado}".${reembolso}`, 'Pedido cancelado');
              this.showSnackbar(`Pedido ${respuesta?.orderId || order.id}: ahora está ${estado}.`);
            },
            error: (error: unknown) => {
              this.confirmacionFallo(this.resolveUiErrorMessage(error, 'No se pudo cancelar el pedido.'));
            }
          });
      }
    });
  }

  openShippingModal(order: AdminOrder): void {
    this.shippingTargetOrder = order;
    this.shippingCarrierDraft = order.shippingCarrier || 'Estafeta';
    this.shippingType = 'carrier';
    this.shippingTrackingNumber = '';
    this.shippingDeliveryPlace = '';
    this.shippingDeliveryDate = '';
    this.shippingStockId = order.stockId ?? this.selectedStockId;
    // Los almacenes solo se cargaban al entrar en Stocks: desde Pedidos el
    // desplegable "Stock origen" salía vacío y el operador tenía que
    // adivinar que había que visitar otra sección primero.
    if (!this.stocks.length) {
      this.loadStocksAndPosState();
    }
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
      shippingCarrier: this.shippingType === 'carrier' ? (this.shippingCarrierDraft || undefined) : undefined,
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
        next: (guardado) => {
          this.closeShippingModal();
          this.showSnackbar(this.resumenEnvioGuardado(guardado, orderId));
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
      shippingCarrier: this.shippingType === 'carrier' ? (this.shippingCarrierDraft || undefined) : undefined,
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
        next: (guardado) => {
          this.closeShippingModal();
          this.requestViewUpdate();
          this.showSnackbar(this.resumenEnvioGuardado(guardado, orderId));
        },
        error: (error: unknown) => {
          this.setShippingError(this.resolveUiErrorMessage(error, 'No se pudo actualizar el envio.'));
        }
      });
  }

  isUpdatingOrder(orderId: string): boolean {
    return this.updatingOrderIds.has(orderId);
  }

  /** Etiqueta legible de un estado de pedido, para avisos y botones. */
  orderStatusLabel(status: AdminOrder['status']): string {
    return this.orderStatusOptionsValue.find((o) => o.value === status)?.label ?? String(status);
  }

  /** Nombra el paso concreto que dará el botón, en vez de "Cambiar estado". */
  advanceOrderLabel(order: AdminOrder): string {
    switch (order.status) {
      case 'pending': return 'Marcar como pagado';
      case 'paid': return 'Registrar envío';
      case 'shipped': return 'Marcar como entregado';
      default: return 'Cambiar estado';
    }
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

  canMarkBranchDelivered(order: AdminOrder): boolean {
    if (order.status !== 'paid' && order.status !== 'shipped') {
      return false;
    }
    if (order.deliveryType !== 'pickup') {
      return false;
    }
    return this.canCurrentOperatorHandlePickupOrder(order);
  }

  canReceivePickupPayment(order: AdminOrder): boolean {
    if (order.status !== 'pending' || order.deliveryType !== 'pickup' || order.pickupPaymentMethod !== 'at_store') {
      return false;
    }
    return this.canCurrentOperatorHandlePickupOrder(order);
  }

  private canCurrentOperatorHandlePickupOrder(order: AdminOrder): boolean {
    if (!order.pickupStockId) {
      return false;
    }
    const operatorId = this.currentOperatorId;
    if (operatorId == null) {
      return false;
    }
    const currentStockId = this.currentPosStock?.id;
    if (currentStockId && order.pickupStockId !== currentStockId) {
      return false;
    }
    const stock = this.stocks.find((s) => s.id === order.pickupStockId);
    return Boolean(stock?.linkedUserIds?.includes(operatorId));
  }

  openReceivePickupPaymentModal(order: AdminOrder): void {
    if (!this.canReceivePickupPayment(order)) {
      return;
    }
    this.posPaymentTargetOrder = order;
    this.posPaymentMethod = 'cash';
    this.posPaymentError = '';
    this.isPosPaymentModalOpen = true;
  }

  closeReceivePickupPaymentModal(): void {
    this.isPosPaymentModalOpen = false;
    this.posPaymentTargetOrder = null;
    this.posPaymentMethod = 'cash';
    this.posPaymentError = '';
    this.pickupCashReceived = '';
  }

  /** Efectivo que entregó el cliente al recoger; la cajera lo calculaba de cabeza. */
  pickupCashReceived = '';

  get pickupCashReceivedNumber(): number {
    const n = Number(String(this.pickupCashReceived).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? n : 0;
  }

  get pickupChangeDue(): number {
    const total = this.posPaymentTargetOrder?.total ?? 0;
    if (this.posPaymentMethod !== 'cash' || !this.pickupCashReceived) return 0;
    return this.roundMoney(Math.max(0, this.pickupCashReceivedNumber - total));
  }

  get pickupCashShortfall(): number {
    const total = this.posPaymentTargetOrder?.total ?? 0;
    if (this.posPaymentMethod !== 'cash' || !this.pickupCashReceived) return 0;
    return this.roundMoney(Math.max(0, total - this.pickupCashReceivedNumber));
  }

  confirmReceivePickupPayment(): void {
    const order = this.posPaymentTargetOrder;
    if (!order || !this.canReceivePickupPayment(order) || this.isSubmittingPosPayment) {
      return;
    }
    if (this.posPaymentMethod === 'cash' && this.pickupCashReceived && this.pickupCashShortfall > 0) {
      this.posPaymentError = `Faltan ${this.formatMoney(this.pickupCashShortfall)}: el efectivo recibido es menor al total.`;
      return;
    }
    this.isSubmittingPosPayment = true;
    this.posPaymentError = '';
    this.updatingOrderIds.add(order.id);
    const changeDue = this.pickupChangeDue;
    this.adminControl
      .updateOrderStatus(order.id, {
        status: 'paid',
        paymentMethod: this.posPaymentMethod,
        cashReceived: this.posPaymentMethod === 'cash' && this.pickupCashReceivedNumber > 0 ? this.pickupCashReceivedNumber : undefined
      })
      .pipe(
        finalize(() => {
          this.isSubmittingPosPayment = false;
          this.updatingOrderIds.delete(order.id);
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: () => {
          const successMessage =
            this.posPaymentMethod === 'cash'
              ? (changeDue > 0 ? `Pago recibido y registrado en caja. Cambio a entregar: ${this.formatMoney(changeDue)}.` : 'Pago recibido y registrado en caja.')
              : 'Pago recibido correctamente.';
          this.closeReceivePickupPaymentModal();
          this.showSnackbar(successMessage);
          this.refreshPosCashControl();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.posPaymentError = error?.error?.message || error?.message || 'No se pudo registrar el pago.';
        }
      });
  }

  markBranchDelivered(order: AdminOrder): void {
    if (!this.canMarkBranchDelivered(order)) {
      return;
    }
    if (this.updatingOrderIds.has(order.id)) {
      return;
    }
    this.updatingOrderIds.add(order.id);
    this.adminControl
      .updateOrderStatus(order.id, { status: 'delivered' })
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(order.id);
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (guardado) => this.showSnackbar(`Pedido ${guardado?.id || order.id}: el servidor lo dejó ${this.orderStatusLabel(guardado?.status || 'delivered')}.`),
        error: (error: unknown) => {
          this.showSnackbar(this.resolveUiErrorMessage(error, 'No se pudo registrar la entrega.'), 'error');
        }
      });
  }

  // ── Refund modal ──────────────────────────────────────────────────────────

  refundAmount = '';

  /** Monto sugerido: el calculado por líneas en la solicitud (productos con descuento + envíos según el motivo);
   *  si la solicitud es anterior a esa regla, la de la ronda 4 (en arrepentimiento no se devuelve el envío). */
  private suggestedRefundFor(o: AdminOrder): number {
    const porLineas = o.returnInspection?.refundSuggested;
    if (porLineas != null && Number.isFinite(Number(porLineas))) {
      return this.roundMoney(Math.max(0, Number(porLineas)));
    }
    const arrepentimiento = (o.returnInspection?.motivo || '').toUpperCase() === 'DESISTIMIENTO';
    const base = arrepentimiento ? (o.total || 0) - (o.shippingCost || 0) : (o.total || 0) + (o.returnShippingCost || 0);
    return this.roundMoney(Math.max(0, base));
  }

  /** Desglose del sugerido por líneas, para mostrarlo en el modal (paquete G). */
  get refundBreakdown(): { products: number; returnShipping: number; originalShipping: number } | null {
    const b = this.refundTargetOrder?.returnInspection?.refundBreakdown;
    if (!b) return null;
    return { products: Number(b.products ?? 0), returnShipping: Number(b.returnShipping ?? 0), originalShipping: Number(b.originalShipping ?? 0) };
  }

  get refundReturnedLines(): Array<{ name: string; quantity: number; unitNet?: number }> {
    return this.refundTargetOrder?.returnInspection?.lines ?? [];
  }

  /** Importe escrito en el modal, como número (NaN si no es válido). */
  get refundAmountNumber(): number {
    return Number(String(this.refundAmount).replace(/[^0-9.]/g, ''));
  }

  /** Apartarse del sugerido por líneas exige motivo (la clienta lo verá en su página). */
  get refundNeedsAdjustmentReason(): boolean {
    const o = this.refundTargetOrder;
    if (!o || o.returnInspection?.refundSuggested == null) return false;
    const importe = this.refundAmountNumber;
    return Number.isFinite(importe) && this.roundMoney(importe) !== this.refundSuggestedAmount;
  }

  get refundSuggestedAmount(): number {
    const o = this.refundTargetOrder;
    return o ? this.suggestedRefundFor(o) : 0;
  }

  get refundSuggestedHint(): string {
    const o = this.refundTargetOrder;
    if (!o) return '';
    if (o.returnInspection?.refundSuggested != null) {
      return o.returnInspection.partial
        ? 'Calculado por las líneas que devolvió, con su descuento. Si cambias el importe, escribe por qué.'
        : 'Calculado por el pedido completo, con su descuento. Si cambias el importe, escribe por qué.';
    }
    return (o.returnInspection?.motivo || '').toUpperCase() === 'DESISTIMIENTO'
      ? 'Arrepentimiento: se sugiere solo el producto; el envío no se reembolsa.'
      : 'Se sugiere el total cobrado más el envío de regreso si el cliente lo pagó.';
  }

  refundAdjustmentReason = '';

  openRefundModal(order: AdminOrder): void {
    this.refundTargetOrder = order;
    this.refundAmount = String(this.suggestedRefundFor(order));
    this.refundReceiptBase64 = '';
    this.refundReceiptName = '';
    this.refundReason = '';
    this.refundAdjustmentReason = '';
    this.refundError = '';
    this.isRefundModalOpen = true;
  }

  closeRefundModal(): void {
    this.isRefundModalOpen = false;
    this.refundTargetOrder = null;
  }

  onRefundReceiptFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.refundReceiptName = file.name;
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = (e.target as FileReader).result as string;
      this.refundReceiptBase64 = result.split(',')[1] ?? result;
      this.requestViewUpdate();
    };
    reader.readAsDataURL(file);
  }

  confirmRefund(): void {
    if (!this.refundTargetOrder) return;
    if (!this.refundReceiptBase64) {
      this.refundError = 'Adjunta el comprobante de depósito.';
      return;
    }
    this.refundError = '';
    this.isSavingRefund = true;
    const orderId = this.refundTargetOrder.id;
    const importe = this.refundAmountNumber;
    if (!Number.isFinite(importe) || importe < 0) {
      this.isSavingRefund = false;
      this.refundError = 'Escribe un importe válido.';
      return;
    }
    if (this.refundNeedsAdjustmentReason && !this.refundAdjustmentReason.trim()) {
      this.isSavingRefund = false;
      this.refundError = `El importe (${this.formatMoney(importe)}) es distinto al sugerido (${this.formatMoney(this.refundSuggestedAmount)}). Escribe el motivo del ajuste: el cliente lo verá.`;
      return;
    }
    const payload: AdminRefundPayload = {
      reason: this.refundReason || 'refund',
      amount: importe,
      receiptBase64: this.refundReceiptBase64,
      receiptName: this.refundReceiptName || 'comprobante.jpg',
      receiptContentType: this.refundReceiptName.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg',
      adjustmentReason: this.refundNeedsAdjustmentReason ? this.refundAdjustmentReason.trim() : undefined,
    };
    this.api.refundOrder(orderId, payload).pipe(
      finalize(() => { this.isSavingRefund = false; this.requestViewUpdate(); })
    ).subscribe({
      next: (res) => {
        this.closeRefundModal();
        this.adminControl.loadOrders().subscribe();
        // La confirmación dice lo que quedó guardado (respuesta del servidor), no lo del formulario.
        const monto = res?.refundAmount != null ? this.formatMoney(Number(res.refundAmount)) : this.formatMoney(importe);
        this.showSnackbar(`Reembolso de ${monto} registrado para el pedido ${res?.orderId || orderId}; se avisó al cliente por correo.`);
      },
      error: (err: unknown) => {
        this.refundError = this.resolveUiErrorMessage(err, 'No se pudo registrar el reembolso.');
      }
    });
  }

  // ── Receive return modal (en_devolucion → devuelto_validado) ──────────────

  openReceiveReturnModal(order: AdminOrder): void {
    this.receiveReturnOrder = order;
    this.receiveReturnImages = [];
    this.receiveReturnError = '';
    this.receiveReturnChecklist = { ...RECEIVE_RETURN_CHECKLIST_DEFAULT };
    this.receiveReturnNotes = '';
    const coincidencias: Record<string, boolean> = {};
    for (const l of order.returnInspection?.lines ?? []) { coincidencias[String(l.productId)] = true; }
    this.receiveReturnLineMatches = coincidencias;
    this.isReceiveReturnModalOpen = true;
  }

  /** Líneas que la clienta dijo que devolvía (paquete G); la bodega marca si cada una coincide. */
  receiveReturnLineMatches: Record<string, boolean> = {};

  get receiveReturnLines(): Array<{ productId: number | string; name: string; quantity: number; unitNet?: number }> {
    return this.receiveReturnOrder?.returnInspection?.lines ?? [];
  }

  toggleReceiveReturnLine(productId: number | string, value: boolean): void {
    this.receiveReturnLineMatches = { ...this.receiveReturnLineMatches, [String(productId)]: value };
  }

  get receiveReturnAllLinesMatch(): boolean {
    return this.receiveReturnLines.every((l) => this.receiveReturnLineMatches[String(l.productId)] !== false);
  }

  /** Checklist de inspección (reglas 3.2 y 5): antes se mandaba todo en verde y recibir era aprobar. */
  receiveReturnChecklist: Record<ReceiveReturnCheck, boolean> = { ...RECEIVE_RETURN_CHECKLIST_DEFAULT };
  receiveReturnNotes = '';
  readonly receiveReturnChecks: Array<{ key: ReceiveReturnCheck; label: string; hint: string }> = [
    { key: 'coincide_con_pedido', label: 'Lo recibido coincide con el pedido', hint: 'Producto y cantidad que reportó el cliente.' },
    { key: 'trazabilidad_valida', label: 'Trae folio o guía identificable', hint: 'Folio RET en el paquete o guía de retorno.' },
    { key: 'empaque_original', label: 'Empaque original', hint: 'Caja o bote original, aunque venga golpeado.' },
    { key: 'sellos_intactos', label: 'Sello de seguridad intacto', hint: 'Si el sello ya estaba abierto, la devolución no procede.' },
    { key: 'sin_uso', label: 'Sin señales de uso', hint: 'Contenido completo, sin consumo.' },
    { key: 'danio_no_empresa', label: 'El daño lo causó el cliente o la paquetería', hint: 'Márcalo solo si el daño no es de fábrica ni de nuestro empaque.' }
  ];

  toggleReceiveReturnCheck(key: ReceiveReturnCheck, value: boolean): void {
    this.receiveReturnChecklist = { ...this.receiveReturnChecklist, [key]: value };
  }

  get receiveReturnWouldApprove(): boolean {
    const c = this.receiveReturnChecklist;
    const coincide = this.receiveReturnLines.length ? this.receiveReturnAllLinesMatch : c.coincide_con_pedido;
    return coincide && c.trazabilidad_valida && c.empaque_original && c.sellos_intactos && c.sin_uso && !c.danio_no_empresa;
  }

  closeReceiveReturnModal(): void {
    this.isReceiveReturnModalOpen = false;
    this.receiveReturnOrder = null;
    this.receiveReturnImages = [];
  }

  onReceiveReturnImageFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    let pending = files.length;
    if (!pending) return;
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = (e.target as FileReader).result as string;
        this.receiveReturnImages.push({
          contentBase64: result.split(',')[1] ?? result,
          fileName: file.name,
          contentType: file.type || 'image/jpeg',
        });
        pending--;
        if (pending === 0) this.requestViewUpdate();
      };
      reader.readAsDataURL(file);
    });
  }

  confirmReceiveReturn(): void {
    if (!this.receiveReturnOrder) return;
    if (!this.receiveReturnImages.length) {
      this.receiveReturnError = 'Adjunta al menos una imagen del estado del paquete.';
      return;
    }
    this.receiveReturnError = '';
    this.isSavingReceiveReturn = true;
    const orderId = this.receiveReturnOrder.id;
    const c = this.receiveReturnChecklist;
    const aprobada = this.receiveReturnWouldApprove;
    const payload: AdminReturnInspectPayload = {
      inspection: {
        empaque_original: c.empaque_original,
        sellos_intactos: c.sellos_intactos,
        sin_uso: c.sin_uso,
        producto_abierto: !c.sellos_intactos,
        danio_no_empresa: c.danio_no_empresa,
        coincide_con_pedido: this.receiveReturnLines.length ? this.receiveReturnAllLinesMatch : c.coincide_con_pedido,
        trazabilidad_valida: c.trazabilidad_valida,
      },
      packageImages: this.receiveReturnImages,
      notes: this.receiveReturnNotes.trim() || undefined,
      rejectionReason: aprobada ? undefined : (this.receiveReturnNotes.trim() || (this.receiveReturnLines.length && !this.receiveReturnAllLinesMatch ? 'Lo recibido no coincide con lo que se declaró devolver' : 'No pasó la inspección física del paquete')),
      lines: this.receiveReturnLines.length
        ? this.receiveReturnLines.map((l) => ({ productId: l.productId, quantity: l.quantity, matches: this.receiveReturnLineMatches[String(l.productId)] !== false }))
        : undefined,
    };
    this.api.inspectReturn(orderId, payload).pipe(
      finalize(() => { this.isSavingReceiveReturn = false; this.requestViewUpdate(); })
    ).subscribe({
      next: (res) => {
        this.closeReceiveReturnModal();
        this.adminControl.loadOrders().subscribe();
        // Confirmación con lo guardado: folio, resultado y reembolso sugerido que devuelve el servidor.
        const folio = res?.requestId ? ` ${res.requestId}` : '';
        if (res?.approved ?? aprobada) {
          const sugerido = res?.refundSuggested != null ? ` Reembolso sugerido: ${this.formatMoney(Number(res.refundSuggested))}.` : '';
          this.showSnackbar(`Paquete recibido. Devolución${folio} validada.${sugerido}`);
        } else {
          this.showSnackbar(`Paquete recibido. Devolución${folio} rechazada por la inspección; se avisó al cliente.`);
        }
      },
      error: (err: unknown) => {
        this.receiveReturnError = this.resolveUiErrorMessage(err, 'No se pudo registrar la recepción del paquete.');
      }
    });
  }

  // ── Reject return modal (devuelto_validado → devolucion_rechazada) ────────

  openRejectReturnModal(order: AdminOrder): void {
    this.rejectReturnOrder = order;
    this.rejectReturnReason = '';
    this.rejectReturnCourtesy = '';
    this.rejectReturnError = '';
    this.isRejectReturnModalOpen = true;
  }

  closeRejectReturnModal(): void {
    this.isRejectReturnModalOpen = false;
    this.rejectReturnOrder = null;
  }

  /** Cortesía al rechazar: % en la próxima compra, emitido como cupón personal (antes solo se prometía en el texto). */
  rejectReturnCourtesy = '';

  confirmRejectReturn(): void {
    if (!this.rejectReturnOrder) return;
    if (!this.rejectReturnReason.trim()) {
      this.rejectReturnError = 'Ingresa el motivo del rechazo.';
      return;
    }
    this.rejectReturnError = '';
    this.isSavingRejectReturn = true;
    const orderId = this.rejectReturnOrder.id;
    const payload: AdminReturnInspectPayload = {
      inspection: {
        empaque_original: false,
        sellos_intactos: false,
        sin_uso: false,
        producto_abierto: true,
        danio_no_empresa: false,
        coincide_con_pedido: true,
        trazabilidad_valida: true,
      },
      rejectionReason: this.rejectReturnReason.trim(),
      courtesyPercent: Number(this.rejectReturnCourtesy) > 0 ? Math.min(100, Math.floor(Number(this.rejectReturnCourtesy))) : undefined,
    };
    this.api.inspectReturn(orderId, payload).pipe(
      finalize(() => { this.isSavingRejectReturn = false; this.requestViewUpdate(); })
    ).subscribe({
      next: (res) => {
        this.closeRejectReturnModal();
        this.adminControl.loadOrders().subscribe();
        const cortesia = payload.courtesyPercent ? ` con ${payload.courtesyPercent}% de cortesía` : '';
        this.showSnackbar(`Devolución ${res?.requestId || orderId} rechazada; se avisó al cliente${cortesia}.`);
      },
      error: (err: unknown) => {
        this.rejectReturnError = this.resolveUiErrorMessage(err, 'No se pudo rechazar la devolución.');
      }
    });
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
        switchMap((creado) => {
          console.log('[Admin] saveNewOrder() createOrder next -> load()');
          return this.adminControl.load().pipe(map(() => creado));
        }),
        finalize(() => {
          console.log('[Admin] saveNewOrder() finalize');
          this.isSavingOrder = false;
        })
      )
      .subscribe({
        next: (creado) => {
          console.log('[Admin] saveNewOrder() load next -> closeModals()');
          this.closeModals();
          this.showSnackbar(`Pedido ${creado?.id} creado para ${creado?.customer || customer.name}: ${this.orderStatusLabel(creado?.status || this.newOrderStatus)} por ${this.formatMoney(creado?.total ?? 0)}.`);
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
      firstName: '',
      apellidoPaterno: '',
      apellidoMaterno: '',
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

  resetPosCustomerForm(): void {
    this.posCustomerForm = {
      firstName: '',
      apellidoPaterno: '',
      apellidoMaterno: '',
      phone: '',
      email: '',
      address: '',
      city: ''
    };
    this.posCustomerError = '';
    this.isSavingPosCustomer = false;
  }

  updatePosCustomerField(
    field: 'firstName' | 'apellidoPaterno' | 'apellidoMaterno' | 'phone' | 'email' | 'address' | 'city',
    value: string
  ): void {
    this.posCustomerForm = {
      ...this.posCustomerForm,
      [field]: value
    };
  }

  private buildCustomerFullName(form: {
    firstName: string;
    apellidoPaterno: string;
    apellidoMaterno: string;
  }): string {
    return `${form.firstName.trim()} ${form.apellidoPaterno.trim()} ${form.apellidoMaterno.trim()}`.trim();
  }

  updateStructureField(
    field: 'firstName' | 'apellidoPaterno' | 'apellidoMaterno' | 'phone' | 'email' | 'address' | 'city',
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
    const fullName = this.buildCustomerFullName(this.structureForm);
    const email = this.structureForm.email.trim();
    const payload: CreateStructureCustomerPayload = {
      name: fullName,
      email: email || undefined,
      phone: this.structureForm.phone?.trim() || undefined,
      address: this.structureForm.address?.trim() || undefined,
      city: this.structureForm.city?.trim() || undefined,
      leaderId: this.structureLeader?.id ?? null
    };
    this.isSavingStructure = true;
    this.adminControl.createStructureCustomer(payload).subscribe({
      next: (creado) => {
        this.isSavingStructure = false;
        this.adminControl.load().subscribe();
        this.closeModals();
        this.showSnackbar(`Miembro creado: ${creado?.name || fullName} (ficha ${creado?.id}).`);
      },
      error: () => {
        this.isSavingStructure = false;
      }
    });
  }

  savePosCustomer(): void {
    if (!this.canSavePosCustomer) {
      return;
    }
    this.isSavingPosCustomer = true;
    this.posCustomerError = '';
    const email = this.posCustomerForm.email.trim();
    const payload: CreateStructureCustomerPayload = {
      name: this.buildCustomerFullName(this.posCustomerForm),
      email: email || undefined,
      phone: this.posCustomerForm.phone.trim() || undefined,
      address: this.posCustomerForm.address.trim() || undefined,
      city: this.posCustomerForm.city.trim() || undefined,
      leaderId: null
    };
    this.adminControl.createStructureCustomer(payload).subscribe({
      next: (customer) => {
        this.isSavingPosCustomer = false;
        this.closePosCustomerModal();
        this.selectPosCustomerRecommendation(customer.id);
        this.showSnackbar(`Cliente ${customer?.name} creado (ficha ${customer?.id}) y seleccionado en la venta.`);
      },
      error: (error: { error?: { message?: string }; message?: string }) => {
        this.isSavingPosCustomer = false;
        this.posCustomerError = error?.error?.message || error?.message || 'No se pudo crear el cliente.';
      }
    });
  }

  selectCustomer(customerId: number): void {
    const selected = this.customers.find((customer) => customer.id === customerId) ?? null;
    this.selectedCustomer = selected;
    this.customerEmailDraft = selected?.email && !selected.email.endsWith('@anonimizado.local') ? selected.email : '';
    this.isChangingSponsor = false;
    this.syncSelectedCustomerAccessDraft();
    this.resetCustomerDocumentDraft();
    this.customerDocumentMessage = '';
    this.customerDocumentError = '';
    this.selectedCustomerProfile = null;
    if (selected) {
      this.loadSelectedCustomerProfile(selected.id);
    }
  }

  onCustomerDocumentFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0] ?? null;
    this.customerDocumentError = '';
    this.customerDocumentMessage = '';
    this.isCustomerDocumentMessageError = false;

    if (!file) {
      this.customerDocumentFile = null;
      this.customerDocumentName = '';
      return;
    }
    if (!this.isSupportedCustomerDocumentFile(file)) {
      this.customerDocumentFile = null;
      this.customerDocumentName = '';
      this.customerDocumentError = 'Solo se permiten PDF, PNG o JPG.';
      target.value = '';
      return;
    }

    this.customerDocumentFile = file;
    this.customerDocumentName = file.name.replace(/\.[^.]+$/, '');
    target.value = '';
  }

  uploadCustomerDocument(): void {
    if (!this.selectedCustomer || !this.customerDocumentFile || this.isUploadingCustomerDocument) {
      this.customerDocumentError = 'Selecciona un documento valido.';
      return;
    }

    const file = this.customerDocumentFile;
    const customerId = String(this.selectedCustomer.id);
    const name = (this.customerDocumentName || file.name.replace(/\.[^.]+$/, '')).trim();
    if (!name) {
      this.customerDocumentError = 'Ingresa un nombre para el documento.';
      return;
    }

    this.customerDocumentError = '';
    this.customerDocumentMessage = '';
    this.isCustomerDocumentMessageError = false;
    this.isUploadingCustomerDocument = true;
    this.readFileAsDataUrl(file)
      .pipe(
        switchMap((dataUrl) => {
          const contentBase64 = this.extractBase64(dataUrl);
          if (!contentBase64) throw new Error('No se pudo leer el archivo.');
          return this.adminControl.addCustomerDocument(customerId, {
            name,
            contentBase64,
            contentType: file.type || 'application/octet-stream',
            fileName: file.name,
          });
        }),
        finalize(() => {
          this.isUploadingCustomerDocument = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (profile) => {
          this.selectedCustomerProfile = profile;
          this.resetCustomerDocumentDraft();
          this.customerDocumentMessage = 'Documento asociado correctamente al cliente.';
          this.isCustomerDocumentMessageError = false;
          this.requestViewUpdate();
        },
        error: () => {
          this.customerDocumentError = 'No se pudo cargar el documento.';
          this.customerDocumentMessage = '';
          this.isCustomerDocumentMessageError = true;
        }
      });
  }

  openCustomerDocument(doc: CustomerDocument): void {
    if (!doc.url) {
      return;
    }
    window.open(doc.url, '_blank', 'noopener,noreferrer');
  }

  safeResourceUrl(url: string): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
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

  customerNoteDraft = '';
  customerEmailDraft = '';
  isSavingCustomerFollowUp = false;
  readonly customerOriginOptions = [
    { value: '', label: 'Sin registrar' },
    { value: 'organico', label: 'Búsqueda orgánica' },
    { value: 'referido', label: 'Referido por un socio' },
    { value: 'red_social', label: 'Red social de un socio (TikTok, Instagram, YouTube)' },
    { value: 'anuncio_google', label: 'Anuncio en Google' },
    { value: 'anuncio_facebook', label: 'Anuncio en Facebook' },
    { value: 'anuncio_instagram', label: 'Anuncio en Instagram' },
    { value: 'anuncio_youtube', label: 'Anuncio en YouTube' },
    { value: 'tienda_fisica', label: 'Tienda física' }
  ];

  /**
   * Paquete A · propuesta 1, montado en la integración.
   *
   * El formulario ya no vive aquí: lo guarda `ui-clabe-form` (el mismo del
   * panel y del perfil) y esto solo refresca la ficha abierta con lo que el
   * servidor confirmó, para que "No se puede depositar" desaparezca sin
   * recargar la pantalla.
   */
  onClabeGuardadaDesdeFicha(customer: AdminCustomer | null | undefined,
                            evento: { clabeLast4: string; bankInstitution: string; removed: boolean }): void {
    if (!customer) {
      return;
    }
    const patch = {
      clabeInterbancaria: evento.removed ? '' : `********${evento.clabeLast4}`,
      clabeLast4: evento.removed ? '' : evento.clabeLast4,
      bankInstitution: evento.bankInstitution || ''
    };
    this.adminControl.patchCustomer(customer.id, patch);
    if (this.selectedCustomer?.id === customer.id) {
      this.selectedCustomer = { ...this.selectedCustomer, ...patch };
    }
    this.showSnackbar(evento.removed
      ? `Se quitó la CLABE de ${customer.name}.`
      : `CLABE guardada (termina en ${evento.clabeLast4}). Ya puedes registrar el depósito de ${customer.name}.`);
    this.requestViewUpdate();
  }

  // ── Paquete G · ronda 26 · propuesta 25: un solo vocabulario ──────────────
  // Julio contó cuatro nombres para el mismo estado en cuatro pantallas y el
  // cuarto era `paid` crudo, en inglés, aquí en Estadísticas. Alma se topó con
  // `mixed`, también en inglés, en el número que venía a cuadrar.

  /** Estado del pedido en español, con el matiz de recolección si aplica. */
  estadoTexto(status?: string | null, deliveryType?: string | null): string {
    return textoEstadoPedido(status, deliveryType) || '—';
  }

  /** Método de pago en español; `mixed` con su desglose cuando se conoce. */
  metodoPagoTexto(method?: string | null, efectivo?: number | null, noEfectivo?: number | null): string {
    return textoMetodoPago(method, efectivo, noEfectivo) || '—';
  }

  /** «2 de marzo de 2027, 11:18»: nunca un ISO crudo. */
  fechaTexto(value?: string | null): string {
    return fechaEnLetras(value ?? '');
  }

  /** Nombre de quien escribió la nota; el id solo si no hay nada mejor. */
  noteAuthor(note: { by?: string; byName?: string }): string {
    if (note.byName?.trim()) {
      return note.byName.trim();
    }
    const id = Number(note.by);
    return Number.isFinite(id) && id > 0 ? this.employeeName(id) : (note.by || 'sistema');
  }

  private saveCustomerFollowUp(customer: AdminCustomer, payload: UpdateCustomerPayload, ok: string): void {
    this.isSavingCustomerFollowUp = true;
    this.adminControl
      .updateCustomer(customer.id, payload)
      .pipe(finalize(() => { this.isSavingCustomerFollowUp = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (updated) => {
          this.selectedCustomer = { ...this.selectedCustomer, ...updated };
          this.showSnackbar(ok);
        },
        error: (error: unknown) => this.showSnackbar(this.resolveUiErrorMessage(error, 'No se pudo guardar el seguimiento.'), 'error')
      });
  }

  toggleDoNotContact(customer: AdminCustomer): void {
    const next = !customer.doNotContact;
    this.saveCustomerFollowUp(customer, { doNotContact: next }, next ? 'Marcado como "no contactar".' : 'Se puede volver a contactar.');
  }

  saveCustomerOrigin(customer: AdminCustomer, origin: string): void {
    if ((customer.origin || '') === (origin || '')) {
      return;
    }
    this.saveCustomerFollowUp(customer, { origin }, 'Origen guardado.');
  }

  /** Deshacer un pago de comisiones registrado por error (se marcó "Pagada" sin CLABE). */
  revertCommissionPayment(customer: AdminCustomer): void {
    const mes = customer.commissionsPrevMonthKey;
    if (!mes || !this.hasPermission('commissions_register_payment')) return;
    this.abrirConfirmacion({
      title: `Deshacer el pago de ${mes} de ${customer.name}`,
      effect: 'El mes vuelve a "pendiente de depósito" y el comprobante queda anulado (se conserva con el motivo). Si el dinero ya salió del banco, tendrás que registrar el pago otra vez con el comprobante correcto.',
      requireReason: true,
      reasonLabel: 'Motivo de la reversa',
      confirmLabel: 'Deshacer el pago',
      danger: true,
      ejecutar: (motivo) => {
        this.adminControl.revertCommissionPayment(customer.id, mes, motivo).subscribe({
          next: (respuesta) => {
            const r = respuesta as { status?: string; receiptsVoided?: number; monthKey?: string };
            const comprobantes = Number(r?.receiptsVoided ?? 0);
            this.confirmacionLista(
              `El servidor dejó el mes ${r?.monthKey || mes} en estado "${r?.status === 'pending' ? 'pendiente de depósito' : r?.status || 'pendiente'}" y anuló ${comprobantes} comprobante${comprobantes === 1 ? '' : 's'}.`,
              'Pago deshecho'
            );
            this.showSnackbar(`Pago de ${r?.monthKey || mes} deshecho: el mes volvió a pendiente de depósito.`);
            this.adminControl.loadCustomers().subscribe(() => {
              this.selectedCustomer = this.customers.find((c) => c.id === customer.id) ?? this.selectedCustomer;
              this.requestViewUpdate();
            });
          },
          error: (err: unknown) => this.confirmacionFallo(this.resolveUiErrorMessage(err, 'No se pudo deshacer el pago.'))
        });
      }
    });
  }

  saveCustomerEmail(customer: AdminCustomer): void {
    const email = this.customerEmailDraft.trim().toLowerCase();
    if (!email || email === (customer.email || '').toLowerCase()) {
      return;
    }
    this.saveCustomerFollowUp(customer, { email }, 'Correo guardado. Si no tenía acceso, ya se le envió su contraseña temporal.');
  }

  addCustomerNote(customer: AdminCustomer): void {
    const note = this.customerNoteDraft.trim();
    if (!note) {
      return;
    }
    this.customerNoteDraft = '';
    this.saveCustomerFollowUp(customer, { note }, 'Nota agregada.');
  }

  deleteCustomerData(customer: AdminCustomer): void {
    if (!this.hasPermission('user_manage_privileges') || this.isSavingCustomerFollowUp) {
      return;
    }
    this.abrirConfirmacion({
      title: `Baja de datos de ${customer.name}`,
      effect: 'Se borran nombre, correo, teléfono, direcciones, documentos, CLABE y acceso; queda marcado "no contactar" y se le manda un correo de confirmación antes de perder la dirección. Sus pedidos y comisiones se conservan sin datos que lo identifiquen. No se puede deshacer.',
      requireReason: true,
      reasonLabel: 'Motivo de la baja (queda en la bitácora)',
      confirmLabel: 'Dar de baja los datos',
      danger: true,
      ejecutar: (motivo) => {
        this.isSavingCustomerFollowUp = true;
        this.adminControl
          .deleteCustomerData(customer.id, motivo)
          .pipe(finalize(() => { this.isSavingCustomerFollowUp = false; this.requestViewUpdate(); }))
          .subscribe({
            next: (updated) => {
              this.selectedCustomer = { ...this.selectedCustomer, ...updated };
              const cuando = updated?.deletedAt ? ` el ${this.formatDateTime(updated.deletedAt)}` : '';
              this.confirmacionLista(
                `El servidor guardó la ficha como "${updated?.name || 'Cliente eliminado'}"${cuando}, sin correo ni teléfono y marcada "no contactar". La confirmación se envió al correo anterior.`,
                'Datos dados de baja'
              );
              this.showSnackbar(`Ficha ${updated?.name || 'Cliente eliminado'}: datos eliminados.`);
            },
            error: (error: unknown) => this.confirmacionFallo(this.resolveUiErrorMessage(error, 'No se pudo dar de baja.'))
          });
      }
    });
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
          this.isChangingSponsor = false;
          this.syncSelectedCustomerAccessDraft();
          const patrocinador = this.customers.find((c) => c.id === (updated?.leaderId ?? null));
          this.showSnackbar(`Posición guardada: el patrocinador de ${updated?.name || this.selectedCustomer?.name} ahora es ${patrocinador?.name || 'nadie (sin patrocinador)'}.`);
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
          this.showSnackbar('Permisos guardados.');
        }
      });
  }

  /** Mes consultado en el Cuadro de Honor (vacío = mes en curso). En diciembre no se podía ver el de noviembre. */
  honorBoardMonth = '';

  loadHonorBoard(month?: string): void {
    if (month !== undefined) {
      this.honorBoardMonth = month;
    }
    this.isLoadingHonorBoard = true;
    this.api.getHonorBoard(this.honorBoardMonth || undefined).subscribe({
      next: (board) => { this.honorBoardData = board; this.isLoadingHonorBoard = false; this.requestViewUpdate(); },
      error: () => { this.isLoadingHonorBoard = false; this.requestViewUpdate(); }
    });
  }

  isSavingEmployeeActive = false;

  /** Desactivar o reactivar al empleado seleccionado (no se borra: se conserva su historial). */
  toggleSelectedEmployeeActive(): void {
    const emp = this.selectedEmployee;
    if (!emp || this.isSavingEmployeeActive) return;
    const next = !emp.active;
    const guardar = (): void => {
      this.isSavingEmployeeActive = true;
      this.adminControl
        .updateEmployee(emp.id, { active: next, canAccessAdmin: next })
        .pipe(finalize(() => { this.isSavingEmployeeActive = false; this.requestViewUpdate(); }))
        .subscribe({
          next: (updated) => {
            this.selectedEmployee = { ...emp, ...updated };
            // El estado que se muestra es el que respondió el servidor, no el que se pidió.
            const activo = updated?.active ?? next;
            const texto = `El servidor dejó a ${updated?.name || emp.name} como ${activo ? 'activo (puede entrar al back office)' : 'inactivo (sin acceso al back office ni al POS)'}.`;
            this.confirmacionLista(texto, activo ? 'Empleado reactivado' : 'Empleado desactivado');
            this.showSnackbar(texto);
          },
          error: (error: unknown) => {
            const mensaje = this.resolveUiErrorMessage(error, 'No se pudo cambiar el estado del empleado.');
            this.confirmacionFallo(mensaje);
            this.showSnackbar(mensaje, 'error');
          }
        });
    };
    if (next) {
      guardar();
      return;
    }
    // Antes era un confirm del navegador; ahora se lee el efecto antes de confirmar.
    this.abrirConfirmacion({
      title: `Desactivar a ${emp.name}`,
      effect: 'Ya no podrá entrar al back office ni cobrar en el POS. No se borra: su historial de ventas y movimientos se conserva y puedes reactivarlo cuando quieras.',
      requireReason: false,
      confirmLabel: 'Desactivar',
      danger: true,
      ejecutar: () => guardar()
    });
  }

  selectEmployee(employeeId: number): void {
    this.selectedEmployee = this.employees.find((emp) => emp.id === employeeId) ?? null;
    this.syncSelectedEmployeePrivilegeDraft();
    this.syncEmployeeContactDraft();
  }

  employeeNameDraft = '';
  employeePhoneDraft = '';
  isSavingEmployeeContact = false;

  private syncEmployeeContactDraft(): void {
    this.employeeNameDraft = this.selectedEmployee?.name ?? '';
    this.employeePhoneDraft = this.selectedEmployee?.phone ?? '';
  }

  get employeeContactDirty(): boolean {
    const emp = this.selectedEmployee;
    if (!emp) return false;
    return this.employeeNameDraft.trim() !== (emp.name ?? '') || this.employeePhoneDraft.trim() !== (emp.phone ?? '');
  }

  saveEmployeeContact(): void {
    const emp = this.selectedEmployee;
    if (!emp || this.isSavingEmployeeContact || !this.employeeContactDirty) return;
    const name = this.employeeNameDraft.trim();
    if (!name) {
      this.showSnackbar('El nombre no puede quedar vacío.');
      return;
    }
    this.isSavingEmployeeContact = true;
    this.adminControl
      .updateEmployee(emp.id, { name, phone: this.employeePhoneDraft.trim() })
      .pipe(finalize(() => { this.isSavingEmployeeContact = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (updated) => {
          this.selectedEmployee = { ...emp, ...updated };
          this.syncEmployeeContactDraft();
          this.showSnackbar(`Empleado guardado como "${updated?.name || emp.name}"${updated?.phone ? ` · tel. ${updated.phone}` : ''}.`);
        },
        error: () => this.showSnackbar('No se pudieron guardar los datos del empleado.')
      });
  }

  updateSelectedEmployeeAdminAccess(enabled: boolean): void {
    this.selectedEmployeeAdminAccess = enabled;
  }

  updateSelectedEmployeePrivilege(privilege: AppPrivilege, enabled: boolean): void {
    this.selectedEmployeePrivilegeDraft = {
      ...this.selectedEmployeePrivilegeDraft,
      [privilege]: enabled
    };
  }

  saveSelectedEmployeePrivileges(): void {
    if (!this.selectedEmployee || this.isSavingEmployeePrivileges) {
      return;
    }
    if (!this.hasPermission('employee_manage_privileges')) {
      return;
    }
    this.isSavingEmployeePrivileges = true;
    this.adminControl
      .updateEmployeePrivileges(this.selectedEmployee.id, {
        canAccessAdmin: this.selectedEmployeeAdminAccess,
        privileges: normalizePrivileges(this.selectedEmployeePrivilegeDraft)
      })
      .pipe(finalize(() => { this.isSavingEmployeePrivileges = false; }))
      .subscribe({
        next: (updated) => {
          this.selectedEmployee = { ...this.selectedEmployee!, ...updated };
          this.syncSelectedEmployeePrivilegeDraft();
          this.showSnackbar('Permisos del empleado guardados.');
        }
      });
  }

  saveEmployee(): void {
    if (!this.hasPermission('employee_add')) {
      return;
    }
    if (this.isSavingEmployee || !this.employeeForm.name.trim() || !this.employeeForm.email.trim()) {
      return;
    }
    this.isSavingEmployee = true;
    this.employeeTempPassword = '';
    this.adminControl
      .createEmployee({
        name: this.employeeForm.name.trim(),
        email: this.employeeForm.email.trim(),
        phone: this.employeeForm.phone.trim() || undefined,
        jobTitle: this.employeeForm.jobTitle.trim() || undefined,
        canAccessAdmin: true,
        privileges: normalizePrivileges(null)
      })
      .pipe(finalize(() => { this.isSavingEmployee = false; }))
      .subscribe({
        next: (emp) => {
          this.employeeTempPassword = emp.tempPassword ?? '';
          this.employeeMessage = `Empleado creado: ${emp.name}.`;
          this.employeeMessageIsError = false;
          this.showSnackbar(`Empleado creado: ${emp.name}.`);
          this.employeeForm = { name: '', email: '', phone: '', jobTitle: '' };
          this.selectedEmployee = emp;
          this.syncSelectedEmployeePrivilegeDraft();
          this.cdr.detectChanges();
        },
        error: (err) => {
          const serverMsg = err?.error?.message || err?.error?.Error;
          this.employeeMessage = serverMsg ? serverMsg : 'No se pudo crear el empleado.';
          this.employeeMessageIsError = true;
        }
      });
  }

  employeeHasPrivilege(privilege: AppPrivilege): boolean {
    return this.selectedEmployeePrivilegeDraft?.[privilege] === true;
  }

  startChangingSponsor(): void {
    this.isChangingSponsor = true;
    this.syncSelectedCustomerAccessDraft();
  }

  isCustomerAccessOpen = false;

  get selectedCustomerGrantedCount(): number {
    return Object.values(this.selectedCustomerPrivilegeDraft ?? {}).filter(Boolean).length;
  }

  private syncSelectedCustomerAccessDraft(): void {
    const selected = this.selectedCustomer;
    this.selectedCustomerAdminAccess = Boolean(selected?.canAccessAdmin);
    this.selectedCustomerPrivilegeDraft = { ...(selected?.privileges ?? {}) };
    this.selectedCustomerLeaderId = selected?.leaderId != null ? String(selected.leaderId) : '';
    if (selected?.leaderId != null) {
      const sponsor = this.customers.find((customer) => customer.id === selected.leaderId);
      this.selectedCustomerSponsorSearch = sponsor ? `${sponsor.name} · ${sponsor.email}` : '';
    } else {
      this.selectedCustomerSponsorSearch = 'FindingU';
    }
    this.refreshSelectedCustomerSponsorState();
  }

  private loadSelectedCustomerProfile(customerId: number): void {
    this.isLoadingSelectedCustomerProfile = true;
    this.adminControl.getCustomer(String(customerId))
      .pipe(
        finalize(() => {
          this.isLoadingSelectedCustomerProfile = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (profile) => {
          if (String(this.selectedCustomer?.id ?? '') !== String(customerId)) {
            return;
          }
          this.selectedCustomerProfile = profile;
        },
        error: () => {
          if (String(this.selectedCustomer?.id ?? '') !== String(customerId)) {
            return;
          }
          this.selectedCustomerProfile = null;
          this.customerDocumentMessage = '';
          this.customerDocumentError = 'No se pudieron cargar los documentos del cliente.';
          this.isCustomerDocumentMessageError = true;
        }
      });
  }

  private resetCustomerDocumentDraft(): void {
    this.customerDocumentFile = null;
    this.customerDocumentName = '';
  }

  private isSupportedCustomerDocumentFile(file: File): boolean {
    const type = String(file.type || '').toLowerCase();
    return type === 'application/pdf' || type === 'image/png' || type === 'image/jpeg';
  }

  syncSelectedEmployeePrivilegeDraft(): void {
    const selected = this.selectedEmployee;
    this.selectedEmployeeAdminAccess = Boolean(selected?.canAccessAdmin);
    this.selectedEmployeePrivilegeDraft = normalizePrivileges(selected?.privileges);
  }

  isGeneratingEmployeePassword = false;

  generateEmployeePassword(): void {
    if (!this.selectedEmployee || this.isGeneratingEmployeePassword) return;
    this.isGeneratingEmployeePassword = true;
    this.adminControl.generateEmployeePassword(this.selectedEmployee.id)
      .pipe(finalize(() => { this.isGeneratingEmployeePassword = false; }))
      .subscribe({
        next: ({ tempPassword }) => {
          this.employeeTempPassword = tempPassword;
          this.cdr.detectChanges();
          this.showSnackbar('Nueva contraseña temporal generada.');
        },
        error: () => {
          this.showSnackbar('No se pudo generar la contraseña.');
        }
      });
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
      active: product.active !== false,
      inOnlineStore: product.inOnlineStore !== false,
      inPOS: product.inPOS !== false,
      commissionable: product.commissionable !== false,
      vpPoints: product.vpPoints ?? '',
      sku: product.sku ?? '',
      hook: product.hook ?? '',
      description: product.description ?? '',
      copyFacebook: product.copyFacebook ?? '',
      copyInstagram: product.copyInstagram ?? '',
      copyWhatsapp: product.copyWhatsapp ?? '',
      tags: (product.tags ?? []).join(', '),
      variants: (product.variants ?? []).map((v) => ({
        id: v.id,
        name: v.name,
        price: v.price != null ? String(v.price) : '',
        sku: v.sku ?? '',
        active: v.active !== false,
        img: v.img ?? ''
      })),
      categoryIds: product.categoryIds ?? [],
      weightKg: product.weightKg ?? '',
      lengthCm: product.lengthCm ?? '',
      widthCm: product.widthCm ?? '',
      heightCm: product.heightCm ?? ''
    };
    this.resetProductAssets();
    this.productExistingImages = product.images ?? [];
    this.applyProductImagePreviews(product.images);
    (product.variants ?? []).forEach((v) => {
      if (v.img) this.variantImagePreviews.set(v.id, v.img);
    });
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

  updateProductActive(active: boolean): void {
    this.productForm = {
      ...this.productForm,
      active
    };
  }

  addProductVariant(): void {
    this.productForm = {
      ...this.productForm,
      variants: [
        ...this.productForm.variants,
        { id: `v-${Date.now()}`, name: '', price: '', sku: '', active: true, img: '' }
      ]
    };
  }

  removeProductVariant(index: number): void {
    const variants = [...this.productForm.variants];
    variants.splice(index, 1);
    this.productForm = { ...this.productForm, variants };
  }

  updateProductVariant(index: number, field: 'name' | 'price' | 'sku' | 'img', value: string): void {
    const variants = this.productForm.variants.map((v, i) =>
      i === index ? { ...v, [field]: value } : v
    );
    this.productForm = { ...this.productForm, variants };
  }

  trackByIndex(index: number): number { return index; }

  trackByVariantId(index: number, v: any): string {
    return v.id;
  }

  toggleProductCategoryId(catId: string): void {
    const ids = this.productForm.categoryIds;
    this.productForm = {
      ...this.productForm,
      categoryIds: ids.includes(catId) ? ids.filter((id) => id !== catId) : [...ids, catId]
    };
  }

  get flatCategories(): ProductCategory[] {
    return this.adminData()?.categories ?? [];
  }

  onCategoriesChanged(cats: ProductCategory[]): void {
    this.adminControl.updateCategories(cats);
  }

  get categoriesTree(): Array<ProductCategory & { depth: number }> {
    const build = (parentId: string | null, depth: number): Array<ProductCategory & { depth: number }> =>
      this.flatCategories
        .filter((c) => (c.parentId ?? null) === parentId && c.active !== false)
        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
        .flatMap((c) => [{ ...c, depth }, ...build(c.id, depth + 1)]);
    return build(null, 0);
  }

  toggleProductActive(product: AdminProduct): void {
    if (!this.hasPermission('product_update')) {
      return;
    }
    if (this.updatingProductStatusIds.has(product.id)) {
      return;
    }

    const nextActive = !product.active;
    this.updatingProductStatusIds.add(product.id);
    this.adminControl
      .saveProduct({
        id: product.id,
        productId: product.id,
        name: product.name,
        price: product.price,
        active: nextActive,
        inOnlineStore: product.inOnlineStore,
        inPOS: product.inPOS,
        commissionable: product.commissionable,
        sku: product.sku,
        hook: product.hook,
        description: product.description,
        copyFacebook: product.copyFacebook,
        copyInstagram: product.copyInstagram,
        copyWhatsapp: product.copyWhatsapp,
        tags: product.tags,
        images: product.images,
        variants: product.variants,
        categoryIds: product.categoryIds,
        weightKg: product.weightKg,
        lengthCm: product.lengthCm,
        widthCm: product.widthCm,
        heightCm: product.heightCm,
      })
      .pipe(
        finalize(() => {
          this.updatingProductStatusIds.delete(product.id);
        })
      )
      .subscribe({
        next: (updatedProduct) => {
          if (this.productForm.id === updatedProduct.id) {
            this.updateProductActive(updatedProduct.active !== false);
          }
          this.announceProductMessage(
            updatedProduct.active ? `Producto reactivado: ${updatedProduct.name}.` : `Producto retirado: ${updatedProduct.name}.`
          );
        },
        error: () => {
          this.announceProductMessage('No se pudo actualizar el estado del producto.');
        }
      });
  }

  isUpdatingProductStatus(productId: number): boolean {
    return this.updatingProductStatusIds.has(productId);
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


  confirmDeleteProduct(product: AdminProduct): void {
    this.productToDelete = product;
  }

  cancelDeleteProduct(): void {
    this.productToDelete = null;
  }

  removeProduct(): void {
    const product = this.productToDelete;
    if (!product || !this.hasPermission('product_delete') || this.isDeletingProduct) {
      return;
    }
    this.isDeletingProduct = true;
    this.adminControl
      .deleteProduct(product.id)
      .pipe(finalize(() => { this.isDeletingProduct = false; this.productToDelete = null; }))
      .subscribe({
        next: () => {
          this.announceProductMessage(`Producto eliminado: ${product.name}.`);
        },
        error: () => {
          this.announceProductMessage('No se pudo eliminar el producto.');
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
        switchMap((uploads) =>
          this.uploadVariantImages().pipe(map((varImgMap) => ({ uploads, varImgMap })))
        ),
        switchMap(({ uploads, varImgMap }) => {
          const payload = {
            id: this.productForm.id,
            productId: this.productForm.id ?? undefined,
            name: this.productForm.name.trim(),
            price: Number(this.productForm.price),
            active: this.productForm.active,
            inOnlineStore: this.productForm.inOnlineStore,
            inPOS: this.productForm.inPOS,
            commissionable: this.productForm.commissionable,
            vpPoints: this.productForm.vpPoints !== '' ? Number(this.productForm.vpPoints) : undefined,
            sku: this.productForm.sku.trim() || undefined,
            hook: this.productForm.hook.trim() || undefined,
            description: this.productForm.description || undefined,
            copyFacebook: this.productForm.copyFacebook || undefined,
            copyInstagram: this.productForm.copyInstagram || undefined,
            copyWhatsapp: this.productForm.copyWhatsapp || undefined,
            tags: this.normalizeTags(this.productForm.tags),
            images: this.mergeProductImages(uploads),
            variants: this.productForm.variants
              .filter((v) => v.name.trim())
              .map((v) => ({
                id: v.id,
                name: v.name.trim(),
                price: v.price ? Number(v.price) : undefined,
                sku: v.sku.trim() || undefined,
                active: v.active,
                img: varImgMap.get(v.id) || v.img || undefined
              })),
            categoryIds: this.productForm.categoryIds,
            weightKg: this.productForm.weightKg !== '' ? Number(this.productForm.weightKg) : undefined,
            lengthCm: this.productForm.lengthCm !== '' ? Number(this.productForm.lengthCm) : undefined,
            widthCm: this.productForm.widthCm !== '' ? Number(this.productForm.widthCm) : undefined,
            heightCm: this.productForm.heightCm !== '' ? Number(this.productForm.heightCm) : undefined,
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
            const msg = `Producto guardado: ${product.name}. Algunas imagenes no se pudieron subir.`;
            this.announceProductMessage(msg);
            this.showSnackbar(msg, 'error');
          } else {
            const msg = this.productForm.id ? `Producto actualizado: ${product.name}.` : `Producto creado: ${product.name}.`;
            this.announceProductMessage(msg);
            this.showSnackbar(msg);
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
          const msg = this.notificationForm.id
            ? `Notificacion actualizada: ${notification.title}.`
            : `Notificacion creada: ${notification.title}.`;
          this.notificationMessage = msg;
          this.showSnackbar(msg);
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
      id: Date.now(),
      name: '',
      price: '',
      active: true,
      inOnlineStore: true,
      inPOS: true,
      commissionable: true,
      vpPoints: '',
      sku: '',
      hook: '',
      description: '',
      copyFacebook: '',
      copyInstagram: '',
      copyWhatsapp: '',
      tags: '',
      variants: [],
      categoryIds: [],
      weightKg: '',
      lengthCm: '',
      widthCm: '',
      heightCm: ''
    };
    this.resetProductAssets();
    this.productExistingImages = [];
  }

  showSnackbar(message: string, tone: 'success' | 'error' = 'success'): void {
    if (this.snackbarTimeout) {
      window.clearTimeout(this.snackbarTimeout);
    }
    this.snackbar = { message, tone, visible: true };
    this.snackbarTimeout = window.setTimeout(() => {
      this.snackbar = { ...this.snackbar, visible: false };
    }, 3500);
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

  uploadVariantImage(event: Event, variantId: string): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    const existing = this.variantImagePreviews.get(variantId);
    if (existing?.startsWith('blob:')) URL.revokeObjectURL(existing);
    this.variantImagePreviews.set(variantId, previewUrl);
    this.variantImageFiles.set(variantId, file);
  }

  private uploadVariantImages(): Observable<Map<string, string>> {
    const entries = Array.from(this.variantImageFiles.entries());
    if (entries.length === 0) return of(new Map<string, string>());
    const productId = this.productForm.id ?? Date.now();
    const uploads = entries.map(([variantId, file]) =>
      this.readFileAsDataUrl(file).pipe(
        switchMap((dataUrl) => {
          const contentBase64 = this.extractBase64(dataUrl);
          if (!contentBase64) return of({ variantId, url: '' });
          return this.adminControl.createProductAsset({
            productId,
            section: 'variante',
            contentBase64,
            fileName: file.name,
            contentType: file.type || 'image/jpeg',
          }).pipe(
            map((res) => ({ variantId, url: res.asset?.url ?? '' })),
            catchError(() => of({ variantId, url: '' }))
          );
        }),
        catchError(() => of({ variantId, url: '' }))
      )
    );
    return forkJoin(uploads).pipe(
      map((results) => new Map(results.filter((r) => r.url).map((r) => [r.variantId, r.url])))
    );
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
      if (value.startsWith('blob:')) URL.revokeObjectURL(value);
    });
    this.productImagePreviews.clear();
    this.variantImageFiles.clear();
    this.variantImagePreviews.forEach((value) => {
      if (value.startsWith('blob:')) URL.revokeObjectURL(value);
    });
    this.variantImagePreviews.clear();
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
    const productId = this.productForm.id ?? Date.now();
    const uploads = entries.map(([section, file]) => {
      return this.readFileAsDataUrl(file).pipe(
        switchMap((dataUrl) => {
          const contentBase64 = this.extractBase64(dataUrl);
          if (!contentBase64) return of({ section, success: false });
          return this.adminControl.createProductAsset({
            productId,
            section,
            contentBase64,
            fileName: file.name,
            contentType: file.type || 'image/jpeg',
          }).pipe(
            map((res) => {
              const assetId = res.asset?.assetId ?? '';
              const url = res.asset?.url ?? '';
              return assetId && url ? { section, success: true, assetId, url } : { section, success: false };
            }),
            catchError(() => of({ section, success: false }))
          );
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
    const postalCode = this.stockForm.postalCode.trim();
    const isMainWarehouse = this.stockForm.isMainWarehouse;
    const allowPickup = this.stockForm.allowPickup;
    // Paquete C: ciudad y estado del almacén (recoger en sucursal solo en tu zona).
    const city = this.stockForm.city.trim();
    const state = this.stockForm.state.trim();
    if (allowPickup && (!city || !state)) {
      this.showSnackbar('Para permitir recoger en esta sucursal escribe su ciudad y elige su estado: así solo se ofrece a clientes de esa zona.', 'error');
      return;
    }
    const payload = { name, location, postalCode: postalCode || undefined, isMainWarehouse, allowPickup, city: city || undefined, state: state || undefined };
    this.adminControl.createStock(payload).subscribe({
      next: (stock) => {
        this.stockForm = { name: '', location: '', postalCode: '', isMainWarehouse: false, allowPickup: false, city: '', state: '' };
        this.selectedStockId = stock.id;
        this.loadStocksAndPosState();
        const zona = (stock as { city?: string; state?: string }).city
          ? ` · ${(stock as { city?: string }).city}, ${(stock as { state?: string }).state ?? ''}`
          : '';
        this.showSnackbar(`Stock creado: ${stock.name}${zona}.`);
      }
    });
  }

  selectStock(stockId: string): void {
    this.selectedStockId = stockId;
    const selected = this.selectedStock;
    if (!selected) {
      return;
    }
    this.stockUbicacionDraft = { city: selected.city ?? '', state: selected.state ?? '' }; // paquete C
    this.stockDamageForm.stockId = selected.id;
    this.stockEntryForm.stockId = selected.id;
    this.stockTransferForm.sourceStockId = this.stockTransferForm.sourceStockId || selected.id;
    this.posForm.stockId = this.posForm.stockId || selected.id;
    this.stockUserLinkDraft = new Set(selected.linkedUserIds.map(Number));
    // Auto-fill "registrado por" con el primer empleado vinculado al stock
    const linkedEmployee = this.employees.find((e) => selected.linkedUserIds.map(Number).includes(e.id));
    const defaultOperator = linkedEmployee?.id ?? this.employees[0]?.id ?? null;
    this.stockEntryForm.createdByUserId = defaultOperator;
    this.stockDamageForm.reportedByUserId = defaultOperator;
    this.stockTransferForm.createdByUserId = defaultOperator;
  }

  saveStockLinks(): void {
    const stock = this.selectedStock;
    if (!stock) {
      return;
    }
    this.adminControl
      .updateStock(stock.id, { linkedUserIds: [...this.stockUserLinkDraft] })
      .subscribe({ next: () => { this.loadStocksAndPosState(); this.showSnackbar('Usuarios vinculados guardados.'); } });
  }

  saveStockAllowPickup(stockId: string, value: boolean): void {
    this.adminControl
      .updateStock(stockId, { allowPickup: value })
      .subscribe({ next: () => this.loadStocksAndPosState() });
  }

  saveStockIsMainWarehouse(stockId: string, value: boolean): void {
    this.adminControl
      .updateStock(stockId, { isMainWarehouse: value })
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
    const { note, createdByUserId } = this.stockEntryForm;
    const stockId = this.stockEntryForm.stockId;
    const productId = Number(this.stockEntryForm.productId) || null;
    const normalizedQty = Math.floor(Number(this.stockEntryForm.qty));
    if (!stockId) {
      this.setStockFeedback('Selecciona un stock.', 'error');
      return;
    }
    if (!productId) {
      this.setStockFeedback('Selecciona un producto.', 'error');
      return;
    }
    if (!Number.isFinite(normalizedQty) || normalizedQty <= 0) {
      this.setStockFeedback('Ingresa una cantidad válida mayor a cero.', 'error');
      return;
    }
    this.setStockFeedback('', '');
    this.adminControl.registerStockEntry(stockId, {
      productId,
      qty: normalizedQty,
      note: note.trim() || undefined,
      userId: createdByUserId
    }).subscribe({
      next: (respuesta) => {
        const existencia = productId != null ? (respuesta?.stock?.inventory as Record<string, number> | undefined)?.[String(productId)] : undefined;
        const texto = existencia != null
          ? `Entrada registrada: ${this.productName(Number(productId))} ahora tiene ${existencia} en ${this.stockName(stockId)}.`
          : 'Entrada de inventario registrada.';
        this.setStockFeedback(texto, 'success');
        this.closeStockEntryModal();
        this.loadStocksAndPosState();
        this.showSnackbar(texto);
      },
      error: (error: { error?: { message?: string }; message?: string }) => {
        this.setStockFeedback(
          error?.error?.message || error?.message || 'No se pudo registrar la entrada de inventario.',
          'error'
        );
      }
    });
  }

  downloadInventoryTemplate(): void {
    const rows: Array<Record<string, string | number>> = [
      { productId: 'ID', producto: 'Nombre del producto', cantidad_a_agregar: 'Cantidad (número)' }
    ];
    for (const product of this.products) {
      const stock = this.selectedStock;
      rows.push({
        productId: product.id,
        producto: product.name,
        cantidad_a_agregar: stock ? (stock.inventory[product.id] ?? 0) : 0
      });
    }
    const ws = XLSX.utils.json_to_sheet(rows, { skipHeader: true });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Inventario');
    const stockName = (this.selectedStock?.name || 'stock').replace(/[^a-zA-Z0-9_-]/g, '_');
    XLSX.writeFile(wb, `plantilla_inventario_${stockName}.xlsx`);
  }

  importInventoryFromExcel(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      return;
    }
    const stockId = this.selectedStockId;
    if (!stockId) {
      this.setStockFeedback('Selecciona un stock antes de importar.', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer);
      const wb = XLSX.read(data, { type: 'array' });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const rows: Array<Record<string, unknown>> = XLSX.utils.sheet_to_json(ws);

      const validRows: Array<{ productId: number; productName: string; qty: number }> = [];
      for (const row of rows) {
        const rawId = row['productId'] ?? row['ProductId'] ?? row['producto_id'];
        const rawQty = row['cantidad_a_agregar'] ?? row['cantidad'] ?? row['qty'] ?? row['Cantidad'];
        const pid = rawId !== undefined && rawId !== '' ? Number(rawId) : NaN;
        const qty = rawQty !== undefined && rawQty !== '' ? Number(rawQty) : NaN;
        if (isNaN(pid) || isNaN(qty) || qty <= 0) {
          continue;
        }
        const product = this.products.find((p) => p.id === pid);
        if (!product) {
          continue;
        }
        validRows.push({ productId: pid, productName: product.name, qty: Math.floor(qty) });
      }

      if (!validRows.length) {
        this.setStockFeedback('El archivo no contiene filas validas. Verifica el formato de la plantilla.', 'error');
        target.value = '';
        return;
      }

      this.isImportingInventory = true;
      this.inventoryImportResults = [];
      this.setStockFeedback('', '');

      const requests = validRows.map((row) =>
        this.adminControl.registerStockEntry(stockId, { productId: row.productId, qty: row.qty }).pipe(
          map(() => ({ productName: row.productName, qty: row.qty, ok: true })),
          catchError((err: { error?: { message?: string }; message?: string }) => of({
            productName: row.productName,
            qty: row.qty,
            ok: false,
            message: err?.error?.message || err?.message || 'Error al registrar'
          }))
        )
      );

      forkJoin(requests)
        .pipe(finalize(() => {
          this.isImportingInventory = false;
          target.value = '';
          this.loadStocksAndPosState();
        }))
        .subscribe((results) => {
          this.inventoryImportResults = results;
          const ok = results.filter((r) => r.ok).length;
          const fail = results.filter((r) => !r.ok).length;
          this.setStockFeedback(
            fail === 0
              ? `Importación completada: ${ok} entradas registradas.`
              : `Importación: ${ok} exitosas, ${fail} fallidas.`,
            fail === 0 ? 'success' : 'error'
          );
        });
    };
    reader.readAsArrayBuffer(file);
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
      const msg = 'Completa origen, destino y al menos una linea valida.';
      this.setStockFeedback(msg, 'error');
      this.showSnackbar(msg);
      return;
    }
    const sourceStock = this.stocks.find((stock) => stock.id === sourceStockId);
    if (!sourceStock) {
      const msg = 'Selecciona un stock origen valido.';
      this.setStockFeedback(msg, 'error');
      this.showSnackbar(msg);
      return;
    }
    const insufficientLine = normalizedLines.find((line) => (sourceStock.inventory[line.productId] ?? 0) < line.qty);
    if (insufficientLine) {
      const msg = `Stock insuficiente para ${this.productName(insufficientLine.productId)}.`;
      this.setStockFeedback(msg, 'error');
      this.showSnackbar(msg);
      return;
    }
    this.setStockFeedback('', '');
    this.adminControl
      .createStockTransfer({ sourceStockId, destinationStockId, lines: normalizedLines, createdByUserId })
      .subscribe({
        next: (respuesta) => {
          const creada = respuesta?.transfer;
          const texto = creada?.id
            ? `Traspaso ${creada.id} creado (${creada.status === 'pending' ? 'pendiente de recibir' : creada.status}): ya salió de ${this.stockName(creada.sourceStockId)}.`
            : 'Transferencia creada.';
          this.setStockFeedback(texto, 'success');
          this.stockTransferForm.lines = [{ productId: this.products[0]?.id ?? null, qty: 1 }];
          this.loadStocksAndPosState();
          this.showSnackbar(texto);
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          const msg = error?.error?.message || error?.message || 'No se pudo crear la transferencia.';
          this.setStockFeedback(msg, 'error');
          this.showSnackbar(msg);
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

    // Cantidades reales en un modal (antes: un prompt por producto y "el clic
    // en Recibir no hizo nada visible", Beto). El almacén contó 4 de 5 y solo
    // podía confirmar 5 o nada.
    this.setStockFeedback('', '');
    this.recepcionTraspaso = {
      transfer,
      lines: transfer.lines.map((line) => ({
        productId: line.productId,
        name: this.productName(line.productId),
        sent: Number(line.qty || 0),
        received: Number(line.qty || 0)
      })),
      busy: false,
      error: '',
      result: null
    };
  }

  /** Modal de recepción de traspaso con cantidades reales (I1). */
  recepcionTraspaso: { transfer: StockTransfer; lines: LineaRecepcion[]; busy: boolean; error: string; result: string | null } | null = null;

  cerrarRecepcionTraspaso(): void {
    if (this.recepcionTraspaso?.busy) {
      return;
    }
    this.recepcionTraspaso = null;
  }

  actualizarCantidadRecibida(linea: LineaRecepcion, valor: unknown): void {
    const n = Math.floor(Number(valor));
    linea.received = Number.isFinite(n) ? Math.max(0, Math.min(linea.sent, n)) : 0;
  }

  get faltantesRecepcion(): LineaRecepcion[] {
    return (this.recepcionTraspaso?.lines ?? []).filter((l) => l.received < l.sent);
  }

  /** Qué va a pasar al confirmar, con las mermas ya calculadas. */
  get efectoRecepcionTraspaso(): string {
    const r = this.recepcionTraspaso;
    if (!r) {
      return '';
    }
    const destino = this.stockName(r.transfer.destinationStockId);
    const faltantes = this.faltantesRecepcion;
    if (!faltantes.length) {
      return `Las cantidades entran al inventario de ${destino} y el traspaso ${r.transfer.id} queda como "Recibida".`;
    }
    const detalle = faltantes.map((l) => `${l.sent - l.received} ${l.name}`).join(', ');
    return `Entra al inventario de ${destino} solo lo que llegó. Faltan ${detalle}: se registran como merma en el origen (${this.stockName(r.transfer.sourceStockId)}) y quedan anotados en el traspaso.`;
  }

  get motivoBloqueoRecepcion(): string {
    const r = this.recepcionTraspaso;
    if (!r) {
      return '';
    }
    if (r.busy) {
      return 'Recibiendo…';
    }
    if (r.lines.some((l) => !Number.isFinite(l.received))) {
      return 'Escribe una cantidad válida en cada producto.';
    }
    if (!this.transferReceiverUserId) {
      return 'Elige quién recibe el traspaso.';
    }
    return '';
  }

  confirmarRecepcionTraspaso(): void {
    const r = this.recepcionTraspaso;
    if (!r || this.motivoBloqueoRecepcion) {
      return;
    }
    const received: Record<string, number> = {};
    for (const linea of r.lines) {
      received[String(linea.productId)] = linea.received;
    }
    const faltantes = this.faltantesRecepcion.length;
    r.busy = true;
    r.error = '';
    this.adminControl
      .receiveStockTransfer(r.transfer.id, { receivedByUserId: this.transferReceiverUserId, received })
      .pipe(finalize(() => { r.busy = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (respuesta) => {
          const guardado = respuesta?.transfer;
          const discrepancias = (respuesta as { discrepancies?: Array<{ productId: string; missing: number }> })?.discrepancies ?? [];
          const estado = guardado?.status === 'received' ? 'Recibida' : String(guardado?.status || 'Recibida');
          const merma = discrepancias.length
            ? ` Mermas registradas en el origen: ${discrepancias.map((d) => `${d.missing} ${this.productName(Number(d.productId))}`).join(', ')}.`
            : ' Sin faltantes.';
          r.result = `El servidor dejó el traspaso ${guardado?.id || r.transfer.id} como "${estado}"${guardado?.receivedAt ? ` el ${this.formatDateTime(guardado.receivedAt)}` : ''}.${merma}`;
          this.setStockFeedback(faltantes ? 'Traspaso recibido con faltantes registrados.' : 'Traspaso recibido.', 'success');
          this.loadStocksAndPosState();
          this.showSnackbar(`Traspaso ${guardado?.id || r.transfer.id}: ${estado}.`);
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          r.error = error?.error?.message || error?.message || 'No se pudo recibir el traspaso.';
          this.setStockFeedback(r.error, 'error');
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
    const { reason, reportedByUserId } = this.stockDamageForm;
    const stockId = this.stockDamageForm.stockId;
    const productId = Number(this.stockDamageForm.productId) || null;
    const qty = Math.floor(Number(this.stockDamageForm.qty));
    if (!stockId) { this.setStockFeedback('Selecciona un stock.', 'error'); return; }
    if (!productId) { this.setStockFeedback('Selecciona un producto.', 'error'); return; }
    if (!Number.isFinite(qty) || qty <= 0) { this.setStockFeedback('Ingresa una cantidad válida mayor a cero.', 'error'); return; }
    if (!reason.trim()) { this.setStockFeedback('Ingresa el motivo del daño.', 'error'); return; }
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
      next: (respuesta) => {
        const existencia = productId != null ? (respuesta?.stock?.inventory as Record<string, number> | undefined)?.[String(productId)] : undefined;
        const texto = existencia != null
          ? `Daño registrado: ${this.productName(Number(productId))} queda con ${existencia} en ${this.stockName(stockId)}.`
          : 'Daño registrado en inventario.';
        this.setStockFeedback(texto, 'success');
        this.stockDamageForm.qty = 1;
        this.stockDamageForm.reason = '';
        this.closeDamageModal();
        this.loadStocksAndPosState();
        this.showSnackbar(texto);
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
    // Devolvía "Sin stock" cuando la lista de almacenes aún no se había
    // cargado (solo se carga al entrar en Stocks): el detalle de un pedido
    // recién enviado decía "Stock origen: Sin stock" y alarmaba a la gerente.
    const nombre = this.stocks.find((stock) => stock.id === stockId)?.name;
    if (nombre) return nombre;
    if (!this.stocks.length && stockId) {
      this.loadStocksAndPosState();
      return stockId;
    }
    return stockId || 'Sin stock';
  }

  customerName(customerId: number | null | undefined): string {
    if (!customerId) {
      return '-';
    }
    return this.customers.find((customer) => customer.id === customerId)?.name ?? `Usuario ${customerId}`;
  }

  employeeName(employeeId: number | null | undefined): string {
    if (!employeeId) {
      return '-';
    }
    // Quien no puede listar empleados (almacén) al menos se ve a sí mismo por su nombre.
    if (String(this.currentUser?.userId ?? '') === String(employeeId) && this.currentUser?.name) {
      return this.currentUser.name;
    }
    return this.employees.find((emp) => emp.id === employeeId)?.name ?? `Empleado ${employeeId}`;
  }

  productName(productId: number): string {
    return this.products.find((product) => product.id === productId)?.name ?? `Producto ${productId}`;
  }

  get availablePosProducts(): AdminProduct[] {
    const stockId = this.currentPosStock?.id;
    if (!stockId) {
      return [];
    }
    return this.products.filter(
      (product) => product.active && product.inPOS !== false && this.stockQty(stockId, product.id) > 0
    );
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
    this.posCustomerSearch = 'Público en general';
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

  openPosAuthModal(action: string, callback: () => void): void {
    this.posAuthAction = action;
    this.posAuthCode = '';
    this.posAuthError = '';
    this.posAuthPendingCallback = callback;
    this.isPosAuthModalOpen = true;
  }

  closePosAuthModal(): void {
    this.isPosAuthModalOpen = false;
    this.posAuthCode = '';
    this.posAuthError = '';
    this.posAuthPendingCallback = null;
  }

  confirmPosAuth(): void {
    if (!this.posAuthCode.trim() || this.isValidatingPosAuth) return;
    this.isValidatingPosAuth = true;
    this.adminControl.validatePosAuth(this.posAuthCode.trim()).pipe(
      finalize(() => (this.isValidatingPosAuth = false))
    ).subscribe({
      next: () => {
        this.posValidatedAuthCode = this.posAuthCode.trim();
        const cb = this.posAuthPendingCallback;
        this.closePosAuthModal();
        if (cb) cb();
        // El código validaba (200) y el diálogo de descuento no aparecía: la
        // vista no se refrescaba tras la respuesta y el cajero pulsó Cobrar
        // tres veces, dejando tres ventas.
        this.requestViewUpdate();
      },
      error: (err: { error?: { message?: string }; message?: string }) => {
        this.posAuthError = err?.error?.message || 'Codigo incorrecto.';
        this.requestViewUpdate();
      }
    });
  }

  openPosDiscountModal(): void {
    this.openPosAuthModal('aplicar descuento', () => {
      this.posDiscountMode = 'percent';
      this.posDiscountValue = '';
      this.posDiscountError = '';
      this.isPosDiscountModalOpen = true;
    });
  }

  closePosDiscountModal(): void {
    this.isPosDiscountModalOpen = false;
    this.posDiscountError = '';
    this.requestViewUpdate();
  }

  applyPosDiscount(): void {
    const val = Number(this.posDiscountValue);
    if (!Number.isFinite(val) || val <= 0) {
      this.posDiscountError = 'Ingresa un valor valido mayor a cero.';
      return;
    }
    if (this.posDiscountMode === 'percent' && val > 100) {
      this.posDiscountError = 'El porcentaje no puede ser mayor a 100%.';
      return;
    }
    if (this.posDiscountMode === 'amount' && val > this.posSubtotal) {
      this.posDiscountError = 'El descuento no puede exceder el subtotal.';
      return;
    }
    const displayLabel = this.posDiscountMode === 'percent' ? `${val}%` : this.formatMoney(val);
    this.posAppliedCashierDiscount = { mode: this.posDiscountMode, value: val, displayLabel };
    this.closePosDiscountModal();
    // 'Aplicar descuento' no procesaba nada: el diálogo seguía abierto y el
    // total intacto hasta el siguiente evento que refrescara la vista.
    this.requestViewUpdate();
  }

  removePosDiscount(): void {
    this.posAppliedCashierDiscount = null;
    this.requestViewUpdate();
  }

  enablePosPartialPayment(mode: 'full' | 'partial' | 'credit'): void {
    if (mode === 'full') {
      this.posPaymentTypeMode = 'full';
      this.posPartialAmountPaid = '';
      this.posValidatedAuthCode = '';
      return;
    }
    this.openPosAuthModal(mode === 'credit' ? 'registrar venta a credito' : 'registrar pago parcial', () => {
      this.posPaymentTypeMode = mode;
      this.posPartialAmountPaid = '';
    });
  }

  loadPosCashCuts(): void {
    if (!this.currentPosStock) return;
    this.isLoadingPosCashCuts = true;
    this.adminControl.listPosCashCuts(this.currentPosStock.id).pipe(
      finalize(() => (this.isLoadingPosCashCuts = false))
    ).subscribe({
      next: (cuts) => {
        this.posCashCuts = (cuts as unknown as PosCashCut[]);
        this.isPosCashCutsOpen = true;
        this.requestViewUpdate();
      }
    });
  }

  toggleCutExpansion(cutId: string): void {
    this.expandedCutId = this.expandedCutId === cutId ? null : cutId;
  }

  downloadCutReport(cut: PosCashCut): void {
    const sales = cut.sales ?? [];
    const withdrawals = cut.withdrawals ?? [];
    const rows: string[] = [
      'Tipo,Hora,Cliente,Metodo Pago,Subtotal,Descuento,Total,Estado'
    ];
    for (const sale of sales) {
      rows.push([
        'Venta',
        sale.createdAt ? new Date(sale.createdAt).toLocaleString('es-MX') : '',
        sale.customerName || 'Público en general',
        sale.paymentMethod || 'cash',
        (sale.grossSubtotal ?? sale.total).toFixed(2),
        ((sale.discountAmount ?? 0) + (sale.cashierDiscountAmount ?? 0)).toFixed(2),
        sale.total.toFixed(2),
        sale.paymentStatus || 'paid_branch'
      ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','));
    }
    for (const wdr of withdrawals) {
      rows.push([
        'Retiro',
        wdr.createdAt ? new Date(wdr.createdAt).toLocaleString('es-MX') : '',
        wdr.reason || '',
        'efectivo',
        '',
        '',
        (-wdr.amount).toFixed(2),
        'retiro'
      ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','));
    }
    const totalSales = sales.reduce((sum, s) => sum + s.total, 0);
    const totalWdr = withdrawals.reduce((sum, w) => sum + w.amount, 0);
    rows.push(`"TOTAL","","","","",""," ${(totalSales - totalWdr).toFixed(2)}",""`);
    const csv = rows.join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const date = cut.createdAt ? new Date(cut.createdAt).toISOString().slice(0, 10) : 'fecha';
    link.href = url;
    link.download = `corte-${cut.id}-${date}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  canVoidPosSale(sale: PosSale): boolean {
    return sale.status !== 'voided' && this.hasPermission('order_mark_paid');
  }

  canSettlePosSale(sale: PosSale): boolean {
    return sale.status !== 'voided' && Number(sale.pendingAmount || 0) > 0 && this.hasPermission('pos_register_sale');
  }

  /** Abono al saldo de una venta con pago parcial: abre el modal (antes era un prompt del navegador). */
  settlePosSale(sale: PosSale): void {
    if (!this.canSettlePosSale(sale)) {
      return;
    }
    this.posSettleTarget = sale;
    this.posSettleAmount = String(this.roundMoney(Number(sale.pendingAmount || 0)));
    this.posSettleMethod = 'cash';
    this.posSettleError = '';
    this.posSettleResult = null;
    this.isPosSettleModalOpen = true;
    this.requestViewUpdate();
  }

  closePosSettleModal(): void {
    if (this.isSettlingPosSale) return;
    this.isPosSettleModalOpen = false;
    this.posSettleTarget = null;
    this.posSettleResult = null;
    this.requestViewUpdate();
  }

  get posSettleAmountNumber(): number {
    const n = Number(String(this.posSettleAmount).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? this.roundMoney(n) : 0;
  }

  /** Por qué no se puede confirmar el abono todavía ('' si se puede). */
  get posSettleBlockReason(): string {
    const pendiente = this.roundMoney(Number(this.posSettleTarget?.pendingAmount || 0));
    if (!this.posSettleTarget) return 'Elige una venta con saldo pendiente.';
    if (this.isSettlingPosSale) return 'Registrando el abono…';
    if (!String(this.posSettleAmount).trim() || this.posSettleAmountNumber <= 0) return 'Escribe cuánto abona el cliente (mayor a $0).';
    if (this.posSettleAmountNumber > pendiente + 0.001) return `El abono no puede ser mayor al saldo pendiente (${this.formatMoney(pendiente)}).`;
    return '';
  }

  confirmPosSettle(): void {
    const sale = this.posSettleTarget;
    if (!sale || this.posSettleBlockReason) {
      this.posSettleError = this.posSettleBlockReason;
      this.requestViewUpdate();
      return;
    }
    this.isSettlingPosSale = true;
    this.posSettleError = '';
    this.caja
      .abonar(sale.id, { amount: this.posSettleAmountNumber, paymentMethod: this.posSettleMethod })
      .pipe(finalize(() => { this.isSettlingPosSale = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (respuesta) => {
          // Confirmación con lo que el servidor guardó: folio del abono, monto y saldo que queda.
          this.posSettleResult = respuesta;
          const restante = Number(respuesta.pendingAmount || 0);
          this.showSnackbar(restante > 0
            ? `Abono ${respuesta.payment?.saleId || ''} registrado por ${this.formatMoney(Number(respuesta.payment?.total || 0))}. Saldo pendiente: ${this.formatMoney(restante)}.`
            : `Abono ${respuesta.payment?.saleId || ''} registrado. La venta ${sale.orderId} quedó liquidada.`);
          this.posCajaRefreshToken++;
          this.refreshPosCashControl();
          this.loadStocksAndPosState();
        },
        error: (err: unknown) => {
          this.posSettleError = this.resolveUiErrorMessage(err, 'No se pudo registrar el abono.');
        }
      });
  }

  /** Anular una venta: abre el modal con el efecto escrito (antes era un prompt del navegador). */
  voidPosSale(sale: PosSale): void {
    if (!this.canVoidPosSale(sale)) {
      return;
    }
    this.posVoidTarget = sale;
    this.posVoidReason = '';
    this.posVoidError = '';
    this.posVoidResult = null;
    this.isPosVoidModalOpen = true;
    this.requestViewUpdate();
  }

  closePosVoidModal(): void {
    if (this.isVoidingPosSale) return;
    this.isPosVoidModalOpen = false;
    this.posVoidTarget = null;
    this.posVoidResult = null;
    this.requestViewUpdate();
  }

  confirmPosVoid(): void {
    const sale = this.posVoidTarget;
    if (!sale || this.isVoidingPosSale) return;
    const reason = this.posVoidReason.trim();
    if (!reason) {
      this.posVoidError = 'Escribe el motivo de la anulación: queda en el pedido y en el aviso al cliente.';
      this.requestViewUpdate();
      return;
    }
    this.isVoidingPosSale = true;
    this.posVoidError = '';
    this.caja
      .anular(sale.id, reason)
      .pipe(finalize(() => { this.isVoidingPosSale = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (respuesta) => {
          this.posVoidResult = respuesta;
          this.posSales = this.posSales.map((s) => (s.id === sale.id ? { ...s, status: respuesta.status || 'voided', voidReason: reason } : s));
          this.adminControl.loadOrders().subscribe();
          this.showSnackbar(`Venta ${respuesta.orderId || sale.orderId} anulada (estado: ${respuesta.status || 'voided'}).`);
          this.posCajaRefreshToken++;
          this.refreshPosCashControl();
        },
        error: (error: unknown) => {
          this.posVoidError = this.resolveUiErrorMessage(error, 'No se pudo anular la venta.');
        }
      });
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
    const esMixto = this.posSalePaymentMethod === 'mixed';
    const cobraEfectivo = this.posSalePaymentMethod === 'cash' || esMixto;
    this.isRegisteringPosSale = true;
    this.setPosFeedback('', '');
    this.caja
      .registrarVenta({
        stockId: this.currentPosStock.id,
        customerId: this.selectedPosCustomer?.id,
        customerName: this.selectedPosCustomer?.name || 'Público en general',
        paymentMethod: esMixto ? undefined : this.posSalePaymentMethod,
        // Pago mixto (paquete E): dos partes que suman el total; el servidor lo comprueba centavo a centavo.
        payments: esMixto
          ? [
              { method: 'cash', amount: this.posMixedCashNumber },
              { method: this.posMixedSecondMethod, amount: this.posMixedRemainder }
            ]
          : undefined,
        paymentStatus: 'paid_branch',
        deliveryStatus: 'delivered_branch',
        items: lineItems,
        // El escalón de descuento se mostraba en pantalla ("alcanzó meta 10%") pero
        // no viajaba en la venta: el backend aplicaba 0% y el socio pagaba de más.
        discountAmount: this.posProjectedDiscountAmount,
        discountRate: this.posProjectedDiscountRate,
        cashReceived: cobraEfectivo && this.posCashReceivedNumber > 0 ? this.posCashReceivedNumber : undefined,
        cashierDiscountMode: this.posAppliedCashierDiscount?.mode,
        cashierDiscountValue: this.posAppliedCashierDiscount?.value,
        paymentType: this.posPaymentTypeMode,
        amountPaid: this.posPaymentTypeMode !== 'full' ? this.posAmountPaidNow : undefined,
        authCode: this.posValidatedAuthCode || undefined
      })
      .pipe(finalize(() => { this.isRegisteringPosSale = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (venta) => {
          this.posUltimaVenta = venta;
          this.posItems.clear();
          this.posForm.status = 'delivered';
          this.posSalePaymentMethod = 'cash';
          this.posMixedCashAmount = '';
          this.posMixedSecondMethod = 'card';
          this.posCashReceived = '';
          this.posAppliedCashierDiscount = null;
          this.posPaymentTypeMode = 'full';
          this.posPartialAmountPaid = '';
          this.posValidatedAuthCode = '';
          this.selectPublicGeneralCustomer();
          // La confirmación dice lo que el servidor guardó, no lo que decía el formulario.
          const mensaje = this.describirVentaGuardada(venta);
          this.setPosFeedback(mensaje, 'success');
          this.showSnackbar(`Venta ${venta.orderId} registrada por ${this.formatMoney(Number(venta.total || 0))}.`);
          this.posCajaRefreshToken++;
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

  /** Texto de confirmación de una venta con los datos devueltos por el servidor. */
  describirVentaGuardada(venta: VentaCajaRespuesta): string {
    const partes = [`Venta ${venta.orderId} registrada por ${this.formatMoney(Number(venta.total || 0))}.`];
    const metodo = venta.sale?.paymentMethod;
    if (metodo === 'mixed' && venta.payments?.length) {
      partes.push('Pago: ' + venta.payments.map((p) => `${this.posMethodLabel(p.method)} ${this.formatMoney(Number(p.amount || 0))}`).join(' + ') + '.');
    } else if (metodo) {
      partes.push(`Pago: ${this.posMethodLabel(metodo)}.`);
    }
    if (Number(venta.pendingAmount || 0) > 0) {
      partes.push(`Pagó ahora ${this.formatMoney(Number(venta.amountPaid || 0))}; saldo pendiente ${this.formatMoney(Number(venta.pendingAmount || 0))}.`);
    }
    if (venta.change != null && Number(venta.cashPortion || 0) > 0) {
      partes.push(`Cambio a entregar: ${this.formatMoney(Number(venta.change || 0))}.`);
    }
    return partes.join(' ');
  }

  /**
   * Paquete G · propuesta 25 (§3.7), montado en la integración.
   *
   * Alma se topó con `mixed` en inglés justo en el número que venía a cuadrar.
   * El texto sale del vocabulario único; ninguna pantalla escribe el suyo.
   */
  posMethodLabel(metodo: string | undefined): string {
    return textoMetodoPago(metodo);
  }

  /** Tras un corte o un retiro en <app-admin-arqueo>: refresca caja, ventas e historial. */
  onCajaCambio(): void {
    this.refreshPosCashControl();
    this.loadStocksAndPosState();
    if (this.isPosCashCutsOpen) {
      this.loadPosCashCuts();
    }
    this.requestViewUpdate();
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
    this.posCustomerRecommendations = (!query || query === this.normalizePosCustomerSearch('Público en general')
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
            isActive: false,
            vp: undefined
          })
        )
      )
      .subscribe((month) => {
        this.posSelectedCustomerMonth = {
          associateId: String(month.associateId),
          monthKey: month.monthKey,
          netVolume: Number(month.netVolume ?? 0),
          isActive: Boolean(month.isActive),
          vp: ('currentDiscount' in month && month.vp != null) ? Number(month.vp) : undefined,
          currentDiscount: 'currentDiscount' in month ? month.currentDiscount : undefined,
          nextGoal: 'nextGoal' in month ? month.nextGoal : undefined,
          commissionLevels: 'commissionLevels' in month ? month.commissionLevels : undefined
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
          this.requestViewUpdate();
          return;
        }
        this.posCashControl = {
          stockId: control.stockId,
          attendantUserId: control.attendantUserId ?? null,
          currentTotal: Number(control.currentTotal ?? 0),
          salesCount: Number(control.salesCount ?? 0),
          cashToKeepSuggested: Number(control.cashToKeepSuggested ?? 0),
          startedAt: control.startedAt,
          lastCutAt: control.lastCutAt,
          lastCutTotal: Number(control.lastCutTotal ?? 0),
          lastCutSalesCount: Number(control.lastCutSalesCount ?? 0),
          lastCutCashToKeep: Number(control.lastCutCashToKeep ?? 0),
          lastCutWithdrawnAmount: Number(control.lastCutWithdrawnAmount ?? 0),
          lastSaleAt: control.lastSaleAt
        };
        this.requestViewUpdate();
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

  onShippingCarriersChange(value: string): void {
    this.businessConfigDraft.shipping.carriers = value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  addCustomerDocumentType(): void {
    const types = this.businessConfigDraft.customerDocumentTypes ?? [];
    types.push({ key: `doc_${Date.now()}`, label: '', required: false });
    this.businessConfigDraft.customerDocumentTypes = [...types];
  }

  removeCustomerDocumentType(index: number): void {
    const types = [...(this.businessConfigDraft.customerDocumentTypes ?? [])];
    types.splice(index, 1);
    this.businessConfigDraft.customerDocumentTypes = types;
  }

  // ─── Bonus config helpers ────────────────────────────────────────────────────

  get bonusConfig(): BonusConfig {
    return this.businessConfigDraft.bonuses ?? this.getDefaultBonusConfig();
  }

  addRankThreshold(): void {
    const cfg = this.bonusConfig;
    cfg.rankThresholds = [...cfg.rankThresholds, { rank: '', vgMin: 0, vpMin: 0, minLines: 0, pcMinPerLine: 0, monthlyBonus: 0 }];
    this.businessConfigDraft.bonuses = { ...cfg };
  }

  // --- Cupones (H7) ---
  private emptyCouponDraft(): SaveCouponPayload {
    return { code: '', type: 'percent', value: 0, active: true, minSubtotal: 0, maxRedemptions: null, validFrom: null, validTo: null, description: '' };
  }

  loadCoupons(): void {
    this.couponsLoading = true;
    this.couponsError = '';
    this.api.listCoupons().subscribe({
      next: (list) => {
        this.coupons = [...list].sort((a, b) => a.code.localeCompare(b.code));
        this.couponsLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.couponsError = 'No se pudieron cargar los cupones.';
        this.couponsLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  newCoupon(): void {
    this.couponEditingCode = null;
    this.couponDraft = this.emptyCouponDraft();
    this.couponFeedback = '';
  }

  editCoupon(c: Coupon): void {
    this.couponEditingCode = c.code;
    this.couponDraft = {
      code: c.code,
      type: c.type,
      value: c.value,
      active: c.active,
      minSubtotal: c.minSubtotal ?? 0,
      maxRedemptions: c.maxRedemptions ?? null,
      validFrom: c.validFrom ?? null,
      validTo: c.validTo ?? null,
      description: c.description ?? ''
    };
    this.couponFeedback = '';
  }

  saveCoupon(): void {
    const code = (this.couponDraft.code || '').trim().toUpperCase();
    if (!code) {
      this.couponFeedback = 'El código es obligatorio.';
      return;
    }
    if (!(this.couponDraft.value > 0)) {
      this.couponFeedback = 'El valor debe ser mayor a 0.';
      return;
    }
    const payload: SaveCouponPayload = { ...this.couponDraft, code };
    this.api.saveCoupon(payload).subscribe({
      next: () => {
        this.couponFeedback = 'Cupón guardado.';
        this.couponEditingCode = null;
        this.couponDraft = this.emptyCouponDraft();
        this.loadCoupons();
      },
      error: () => {
        this.couponFeedback = 'No se pudo guardar el cupón.';
        this.cdr.markForCheck();
      }
    });
  }

  /** Encender un cupón apagado no tenía botón propio: había que editarlo. */
  activateCoupon(c: Coupon): void {
    const restantes = c.maxRedemptions != null ? c.maxRedemptions - (c.redemptions ?? 0) : null;
    const aviso = restantes != null && restantes <= 0
      ? ` Atención: ya se agotaron sus ${c.maxRedemptions} usos, así que no lo podrá canjear nadie hasta que subas el límite.`
      : restantes != null
        ? ` Quedan ${restantes} de ${c.maxRedemptions} usos.`
        : '';
    this.abrirConfirmacion({
      title: `Activar el cupón ${c.code}`,
      effect: `Desde ahora cualquier cliente podrá canjearlo en el carrito.${aviso}`,
      requireReason: false,
      confirmLabel: 'Activar el cupón',
      danger: false,
      ejecutar: () => {
        this.api.saveCoupon({ ...c, active: true } as SaveCouponPayload).subscribe({
          next: (guardado) => {
            const activo = guardado?.active ?? true;
            this.couponFeedback = `Cupón ${guardado?.code || c.code}: el servidor lo dejó ${activo ? 'activo' : 'inactivo'}.`;
            this.confirmacionLista(this.couponFeedback, 'Cupón activado');
            this.loadCoupons();
          },
          error: (error: unknown) => {
            this.couponFeedback = `No se pudo activar el cupón ${c.code}.`;
            this.confirmacionFallo(this.resolveUiErrorMessage(error, this.couponFeedback));
            this.cdr.markForCheck();
          }
        });
      }
    });
  }

  deleteCoupon(c: Coupon): void {
    this.abrirConfirmacion({
      title: `Desactivar el cupón ${c.code}`,
      effect: 'Deja de aceptarse en el carrito desde ahora; los pedidos que ya lo usaron no cambian. No se borra: puedes volver a activarlo cuando quieras.',
      requireReason: false,
      confirmLabel: 'Desactivar el cupón',
      danger: true,
      ejecutar: () => {
        this.api.deleteCoupon(c.code).subscribe({
          next: (respuesta) => {
            const guardado = (respuesta as { coupon?: Coupon })?.coupon;
            const activo = guardado?.active ?? false;
            this.couponFeedback = `Cupón ${respuesta?.code || c.code}: el servidor lo dejó ${activo ? 'activo' : 'inactivo'}.`;
            this.confirmacionLista(this.couponFeedback, 'Cupón desactivado');
            this.loadCoupons();
          },
          error: (error: unknown) => {
            this.couponFeedback = 'No se pudo desactivar el cupón.';
            this.confirmacionFallo(this.resolveUiErrorMessage(error, this.couponFeedback));
            this.cdr.markForCheck();
          }
        });
      }
    });
  }

  removeRankThreshold(index: number): void {
    const cfg = this.bonusConfig;
    const thresholds = [...cfg.rankThresholds];
    thresholds.splice(index, 1);
    this.businessConfigDraft.bonuses = { ...cfg, rankThresholds: thresholds };
  }

  addBonusRule(): void {
    const cfg = this.bonusConfig;
    const newRule: BonusRule = {
      id: `rule_${Date.now()}`,
      name: 'Nuevo Bono',
      active: true,
      conditions: [],
      rewards: [],
      cooldown: 'monthly'
    };
    this.businessConfigDraft.bonuses = { ...cfg, rules: [...cfg.rules, newRule] };
  }

  removeBonusRule(index: number): void {
    const cfg = this.bonusConfig;
    const rules = [...cfg.rules];
    rules.splice(index, 1);
    this.businessConfigDraft.bonuses = { ...cfg, rules };
  }

  addBonusCondition(ruleIndex: number): void {
    const cfg = this.bonusConfig;
    const rules = cfg.rules.map((r, i) =>
      i === ruleIndex ? { ...r, conditions: [...r.conditions, { type: 'vg_min' as BonusConditionType, value: 0 }] } : r
    );
    this.businessConfigDraft.bonuses = { ...cfg, rules };
  }

  removeBonusCondition(ruleIndex: number, condIndex: number): void {
    const cfg = this.bonusConfig;
    const rules = cfg.rules.map((r, i) => {
      if (i !== ruleIndex) return r;
      const conditions = [...r.conditions];
      conditions.splice(condIndex, 1);
      return { ...r, conditions };
    });
    this.businessConfigDraft.bonuses = { ...cfg, rules };
  }

  addBonusReward(ruleIndex: number): void {
    const cfg = this.bonusConfig;
    const rules = cfg.rules.map((r, i) =>
      i === ruleIndex ? { ...r, rewards: [...r.rewards, { type: 'cash_mxn' as BonusRewardType, amount: 0 }] } : r
    );
    this.businessConfigDraft.bonuses = { ...cfg, rules };
  }

  removeBonusReward(ruleIndex: number, rewIndex: number): void {
    const cfg = this.bonusConfig;
    const rules = cfg.rules.map((r, i) => {
      if (i !== ruleIndex) return r;
      const rewards = [...r.rewards];
      rewards.splice(rewIndex, 1);
      return { ...r, rewards };
    });
    this.businessConfigDraft.bonuses = { ...cfg, rules };
  }

  readonly bonusConditionTypeOptions: Array<{ value: BonusConditionType; label: string }> = [
    { value: 'vg_min',            label: 'VG mínimo (VP)' },
    { value: 'vp_min',            label: 'VP personal mínimo (VP)' },
    { value: 'direct_vg_min',     label: 'VG de referidos directos (VP)' },
    { value: 'consecutive_months', label: 'Meses consecutivos en rango' },
    { value: 'direct_rank_count', label: 'Número de referidos directos con rango' },
    { value: 'first_30_days',     label: 'Registro en los primeros 30 días' },
    { value: 'first_time',        label: 'Primera vez que alcanza este bono' }
  ];

  readonly bonusRewardTypeOptions: Array<{ value: BonusRewardType; label: string }> = [
    { value: 'cash_mxn',         label: 'Efectivo MXN (único)' },
    { value: 'monthly_cash',     label: 'Efectivo MXN (mensual recurrente)' },
    { value: 'item',             label: 'Artículo físico (TV, viaje…)' },
    { value: 'annual_fund_pct',  label: '% del fondo anual acumulado' }
  ];

  readonly bonusCooldownOptions: Array<{ value: 'once' | 'monthly' | 'annual'; label: string }> = [
    { value: 'once',    label: 'Una sola vez (de por vida)' },
    { value: 'monthly', label: 'Una vez por mes' },
    { value: 'annual',  label: 'Una vez por año' }
  ];

  conditionNeedsValue(type: BonusConditionType): boolean {
    return ['vg_min', 'vp_min', 'direct_vg_min', 'consecutive_months', 'direct_rank_count'].includes(type);
  }

  conditionNeedsRank(type: BonusConditionType): boolean {
    return type === 'direct_rank_count';
  }

  rewardNeedsAmount(type: BonusRewardType): boolean {
    return type === 'cash_mxn' || type === 'monthly_cash';
  }

  rewardNeedsItem(type: BonusRewardType): boolean {
    return type === 'item';
  }

  rewardNeedsPct(type: BonusRewardType): boolean {
    return type === 'annual_fund_pct';
  }

  // ─── Honor Board helpers ─────────────────────────────────────────────────
  get sortedHonorEntries(): HonorEntry[] {
    const list = this.honorBoardSort === 'vp'
      ? [...(this.honorBoardData?.byVp ?? [])]
      : [...(this.honorBoardData?.byVg ?? [])];
    if (this.honorBoardSort === 'alpha') {
      list.sort((a, b) => a.name.localeCompare(b.name, 'es'));
      return list;
    }
    // Ordenar aquí y no confiar en el orden de llegada: la tabla afirma estar
    // ordenada por una columna concreta y tiene que cumplirlo pase lo que pase.
    const campo = this.honorBoardSort === 'vp' ? 'vp' : 'vg';
    list.sort((a, b) => (b[campo] ?? 0) - (a[campo] ?? 0));
    return list;
  }

  /** Cuánto le falta a esta persona para alcanzar a la de arriba. */
  honorGapToPrevious(entry: HonorEntry): number | null {
    const list = this.sortedHonorEntries;
    const i = list.indexOf(entry);
    if (i <= 0) return null;
    const campo = this.honorBoardSort === 'vp' ? 'vp' : 'vg';
    return (list[i - 1][campo] ?? 0) - (entry[campo] ?? 0);
  }

  honorPositionDeltaLabel(entry: HonorEntry): string {
    if (!entry.prevPosition) return '';
    const d = entry.prevPosition - entry.position;
    if (d > 0) return `▲${d}`;
    if (d < 0) return `▼${Math.abs(d)}`;
    return '—';
  }

  honorPositionDeltaClass(entry: HonorEntry): string {
    if (!entry.prevPosition) return 'text-gray-400';
    const d = entry.prevPosition - entry.position;
    if (d > 0) return 'text-green-600';
    if (d < 0) return 'text-red-500';
    return 'text-gray-400';
  }

  savePosAuthCode(): void {
    if (!this.hasPermission('config_manage') || this.isSavingPosAuthCode) return;
    const code = (this.posAuthCodeDraft || '').trim();
    if (code.length < 4) return;
    this.isSavingPosAuthCode = true;
    this.posAuthCodeMessage = '';
    this.adminControl.savePosAuthCode(code).pipe(finalize(() => (this.isSavingPosAuthCode = false))).subscribe({
      next: () => {
        this.posAuthCodeDraft = '';
        this.posAuthCodeIsError = false;
        this.posAuthCodeMessage = 'Codigo actualizado correctamente.';
      },
      error: (err: { error?: { message?: string }; message?: string }) => {
        this.posAuthCodeIsError = true;
        this.posAuthCodeMessage = err?.error?.message || 'No se pudo actualizar el codigo.';
      }
    });
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
          const tramos = config?.rewards?.discountTiers?.length ?? 0;
          const generaciones = config?.rewards?.commissionLevels?.length ?? 0;
          this.businessConfigMessage = `Configuración guardada: activación ${config?.rewards?.activationNetMin ?? '?'} VP, ${tramos} tramo${tramos === 1 ? '' : 's'} de descuento, ${generaciones} generaci${generaciones === 1 ? 'ón' : 'ones'} de comisión.`;
          this.showSnackbar(this.businessConfigMessage);
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
    draft.rewards.commissionLevels = this.normalizeCommissionLevels(draft.rewards.commissionLevels);
    this.normalizeBusinessConfigSelectValues(draft);
    return draft;
  }

  private normalizeBusinessConfigForSave(config: AppBusinessConfig): AppBusinessConfig {
    const next = structuredClone(config);
    next.rewards.discountTiers = this.normalizeDiscountTiers(next.rewards.discountTiers, true);
    next.rewards.commissionLevels = this.normalizeCommissionLevels(next.rewards.commissionLevels);
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

  private normalizeCommissionLevels(raw: unknown): CommissionLevelDraft[] {
    const def: CommissionLevelDraft = { gen: 1, rate: 0, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 };
    if (Array.isArray(raw) && raw.length) {
      return raw.map((lvl, i) => ({ ...def, gen: i + 1, ...lvl }));
    }
    return this.getDefaultBusinessConfig().rewards.commissionLevels;
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
        activationNetMin: 20,
        discountTiers: [
          { min: 0, max: 999, rate: 0 },
          { min: 1000, max: 1999, rate: 0.1 },
          { min: 2000, max: 2999, rate: 0.2 },
          { min: 3000, max: 5999, rate: 0.3 },
          { min: 6000, max: null, rate: 0.4 }
        ],
        commissionLevels: [
          { gen: 1, rate: 0.1, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
          { gen: 2, rate: 0.05, reqActiveDirects: 2, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
          { gen: 3, rate: 0.04, reqActiveDirects: 3, reqPersonalPC: 80, reqLines: 2, reqPCPerLine: 300 },
          { gen: 4, rate: 0.03, reqActiveDirects: 4, reqPersonalPC: 120, reqLines: 3, reqPCPerLine: 450 },
          { gen: 5, rate: 0.02, reqActiveDirects: 5, reqPersonalPC: 160, reqLines: 3, reqPCPerLine: 750 }
        ],
        payoutDay: 10,
        cutRule: 'dynamic_compression'
      },
      orders: {
        requireStockOnShipped: true,
        requireDispatchLinesOnShipped: true
      },
      pos: {
        defaultCustomerName: 'Público en general',
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
      },
      shipping: {
        enabled: true,
        markup: 0,
        carriers: ['dhl', 'fedex']
      },
      customerDocumentTypes: [
        { key: 'constancia', label: 'Constancia de situación fiscal', required: true },
        { key: 'ine', label: 'INE (frente y reverso)', required: true },
        { key: 'curp', label: 'CURP', required: true }
      ],
      bonuses: this.getDefaultBonusConfig()
    };
  }

  private getDefaultBonusConfig(): BonusConfig {
    return {
      vpConfig: { mxnPerVp: 50, maxNetworkLevels: 5 },
      // Rangos de liderazgo del Plan abril 2026 §6.
      rankThresholds: [
        { rank: 'BRONCE', vpMin: 60, vgMin: 4500, minLines: 3, pcMinPerLine: 900, requiredLeaders: 0, requiredLeaderRank: '', monthlyBonus: 500, annualBonus: 6000 },
        { rank: 'PLATA', vpMin: 90, vgMin: 9000, minLines: 4, pcMinPerLine: 1500, requiredLeaders: 2, requiredLeaderRank: 'BRONCE', monthlyBonus: 1500, annualBonus: 18000 },
        { rank: 'ORO', vpMin: 140, vgMin: 15000, minLines: 4, pcMinPerLine: 2500, requiredLeaders: 2, requiredLeaderRank: 'PLATA', monthlyBonus: 3000, annualBonus: 36000 },
        { rank: 'PLATINO', vpMin: 200, vgMin: 21000, minLines: 5, pcMinPerLine: 3000, requiredLeaders: 2, requiredLeaderRank: 'ORO', monthlyBonus: 6000, annualBonus: 72000 },
        { rank: 'DIAMANTE', vpMin: 280, vgMin: 25000, minLines: 5, pcMinPerLine: 4000, requiredLeaders: 2, requiredLeaderRank: 'PLATINO', monthlyBonus: 10000, annualBonus: 120000 }
      ],
      rules: [
        {
          id: 'inicio_rapido',
          name: 'Bono de Inicio Rápido',
          active: true,
          conditions: [
            { type: 'first_30_days' },
            { type: 'vg_min', value: 600 }
          ],
          rewards: [{ type: 'cash_mxn', amount: 5000 }],
          cooldown: 'once',
          notes: 'Primeros 30 días: 600 PC grupales del equipo → $5,000 MXN (una vez).'
        },
        {
          id: 'bono_rango_bronce',
          name: 'Bono Mensual BRONCE',
          active: true,
          rank: 'BRONCE',
          conditions: [{ type: 'vg_min', value: 4500 }, { type: 'consecutive_months', value: 4 }],
          rewards: [{ type: 'monthly_cash', amount: 500 }],
          cooldown: 'monthly',
          notes: '$500/mes desde el 4º mes consecutivo en BRONCE.'
        },
        {
          id: 'bono_rango_plata',
          name: 'Bono Mensual PLATA',
          active: true,
          rank: 'PLATA',
          conditions: [{ type: 'vg_min', value: 9000 }, { type: 'consecutive_months', value: 4 }],
          rewards: [{ type: 'monthly_cash', amount: 1500 }],
          cooldown: 'monthly',
          notes: '$1,500/mes desde el 4º mes consecutivo en PLATA.'
        },
        {
          id: 'bono_rango_oro',
          name: 'Bono Mensual ORO',
          active: true,
          rank: 'ORO',
          conditions: [{ type: 'vg_min', value: 15000 }, { type: 'consecutive_months', value: 4 }],
          rewards: [{ type: 'monthly_cash', amount: 3000 }],
          cooldown: 'monthly',
          notes: '$3,000/mes desde el 4º mes consecutivo en ORO.'
        },
        {
          id: 'bono_rango_platino',
          name: 'Bono Mensual PLATINO',
          active: true,
          rank: 'PLATINO',
          conditions: [{ type: 'vg_min', value: 21000 }, { type: 'consecutive_months', value: 4 }],
          rewards: [{ type: 'monthly_cash', amount: 6000 }],
          cooldown: 'monthly',
          notes: '$6,000/mes desde el 4º mes consecutivo en PLATINO.'
        },
        {
          id: 'bono_rango_diamante',
          name: 'Bono Mensual DIAMANTE',
          active: true,
          rank: 'DIAMANTE',
          conditions: [{ type: 'vg_min', value: 25000 }, { type: 'consecutive_months', value: 4 }],
          rewards: [{ type: 'monthly_cash', amount: 10000 }],
          cooldown: 'monthly',
          notes: '$10,000/mes desde el 4º mes consecutivo en DIAMANTE.'
        }
      ]
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

  /** El mismo vocabulario único de §3.7, también en la bitácora de movimientos. */
  posPaymentMethodLabel(method?: PosSale['paymentMethod'] | InventoryMovement['paymentMethod']): string {
    return textoMetodoPago(method ?? 'cash');
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

  // ── Paquete C · factura y ubicación de sucursal ──

  /** El bloque de factura ya guardó en el servidor; aquí se refleja en la fila y se avisa con el dato guardado. */
  markInvoiceIssued(order: AdminOrder, respuesta: FacturaEmitida): void {
    order.invoiceStatus = respuesta.invoiceStatus;
    order.invoiceIssuedAt = respuesta.invoiceIssuedAt;
    order.invoiceFolio = respuesta.invoiceFolio ?? undefined;
    order.invoiceFileUrl = respuesta.invoiceFileUrl ?? undefined;
    this.showSnackbar(
      `Pedido ${order.id}: factura ${respuesta.invoiceStatus}` +
      (respuesta.invoiceFolio ? ` · folio ${respuesta.invoiceFolio}` : '') +
      '. Se avisó al cliente por correo.'
    );
    this.requestViewUpdate();
  }

  guardarUbicacionSucursal(stock: AdminStock): void {
    const city = this.stockUbicacionDraft.city.trim();
    const state = this.stockUbicacionDraft.state.trim();
    if (!city || !state) {
      this.showSnackbar('Escribe la ciudad y elige el estado de la sucursal.', 'error');
      return;
    }
    this.checkoutService.actualizarUbicacionSucursal(stock.id, { city, state }).subscribe({
      next: (respuesta) => {
        const guardado = (respuesta?.stock ?? {}) as { city?: string; state?: string };
        stock.city = guardado.city ?? city;
        stock.state = guardado.state ?? state;
        this.showSnackbar(`Ubicación guardada: ${stock.name} · ${stock.city}, ${stock.state}. Recoger en sucursal se ofrecerá a clientes de esa zona.`);
        this.requestViewUpdate();
      },
      error: (error: unknown) => {
        this.showSnackbar(this.resolveUiErrorMessage(error, 'No se pudo guardar la ubicación de la sucursal.'), 'error');
      }
    });
  }

  // ── WP-D · bodega por defecto del empleado (paquete D) ──────────────────
  private readonly despachoService = inject(DespachoService);
  private employeeDefaultStockApplied = false;

  /** Aplica una sola vez la bodega guardada en el perfil: Stocks y POS arrancan con ella. */
  private applyEmployeeDefaultStock(): void {
    if (this.employeeDefaultStockApplied || !this.stocks.length) {
      return;
    }
    this.employeeDefaultStockApplied = true;
    this.despachoService.preferencias().subscribe({
      next: (prefs) => {
        const stockId = prefs.defaultStockId ?? '';
        if (!stockId || !this.stocks.some((stock) => stock.id === stockId)) {
          return;
        }
        this.selectStock(stockId);
        if (this.linkedPosStocks.some((stock) => stock.id === stockId)) {
          this.posForm.stockId = stockId;
          this.syncPosSelectedItems();
          this.refreshPosCashControl();
        }
        this.requestViewUpdate();
      },
      error: () => undefined
    });
  }

  // ───────────────────────── I1 · transversal-admin ─────────────────────────

  /** Diálogo de confirmación abierto (uno solo para todo el back office). */
  confirmacion: ConfirmacionAdmin | null = null;

  abrirConfirmacion(cfg: Omit<ConfirmacionAdmin, 'busy' | 'error' | 'result'>): void {
    this.confirmacion = { ...cfg, busy: false, error: '', result: null };
    this.requestViewUpdate();
  }

  cerrarConfirmacion(): void {
    if (this.confirmacion?.busy) {
      return;
    }
    this.confirmacion = null;
    this.requestViewUpdate();
  }

  ejecutarConfirmacion(motivo: string): void {
    const c = this.confirmacion;
    if (!c || c.busy) {
      return;
    }
    c.busy = true;
    c.error = '';
    this.requestViewUpdate();
    c.ejecutar(motivo);
  }

  /** La acción terminó: se muestra lo que el servidor guardó y un botón "Listo". */
  confirmacionLista(resultado: string, titulo = 'Listo'): void {
    if (this.confirmacion) {
      this.confirmacion.busy = false;
      this.confirmacion.result = resultado;
      this.confirmacion.resultTitle = titulo;
    }
    this.requestViewUpdate();
  }

  confirmacionFallo(mensaje: string): void {
    if (this.confirmacion) {
      this.confirmacion.busy = false;
      this.confirmacion.error = mensaje;
    }
    this.requestViewUpdate();
  }

  /** Motivo de "Guardando…" para los botones de un pedido mientras hay una llamada en curso. */
  motivoPedidoOcupado(orderId: string): string {
    return this.isUpdatingOrder(orderId) ? 'Guardando el cambio de este pedido…' : '';
  }

  /** Motivo por el que no se puede guardar el correo del cliente. */
  get motivoGuardarCorreoCliente(): string {
    if (this.isSavingCustomerFollowUp) return 'Guardando…';
    const draft = this.customerEmailDraft.trim();
    if (!draft) return 'Escribe el correo nuevo.';
    if (draft === (this.selectedCustomer?.email || '')) return 'Es el mismo correo que ya tiene.';
    return '';
  }

  get motivoGuardarEmpleado(): string {
    if (this.isSavingEmployee) return 'Guardando…';
    if (!this.employeeForm.name.trim()) return 'Escribe el nombre del empleado.';
    if (!this.employeeForm.email.trim()) return 'Escribe el correo: ahí le llega su contraseña temporal.';
    return '';
  }

  get motivoGuardarProducto(): string {
    if (this.isSavingProduct) return 'Guardando…';
    if (!this.productForm.name.trim()) return 'Escribe el nombre del producto.';
    if (!Number(this.productForm.price)) return 'Escribe un precio mayor a $0.';
    return '';
  }

  get motivoGuardarPedidoNuevo(): string {
    if (this.isSavingOrder) return 'Guardando el pedido…';
    if (!this.newOrderCustomerId) return 'Elige el cliente del pedido.';
    if (this.newOrderItems.size === 0) return 'Agrega al menos un producto.';
    return '';
  }

  get motivoGuardarPosicionCliente(): string {
    if (this.isSavingCustomerPosition) return 'Guardando…';
    if (!this.selectedCustomer) return 'Elige un cliente.';
    if (!this.hasValidSelectedSponsorId) return 'Elige un patrocinador válido (no puede ser el mismo cliente).';
    const nextLeaderId = this.selectedCustomerLeaderId ? Number(this.selectedCustomerLeaderId) : null;
    if ((this.selectedCustomer.leaderId ?? null) === nextLeaderId) return 'Es el mismo patrocinador que ya tiene.';
    return '';
  }

  motivoRecibirTraspaso(transfer: StockTransfer): string {
    if (transfer.status === 'received') return 'Este traspaso ya se recibió.';
    if (!this.transferReceiverUserId) return 'Elige arriba quién recibe.';
    if (!this.isReceiverEligible(transfer)) {
      return `Quien recibe debe estar ligado al almacén destino (${this.stockName(transfer.destinationStockId)}). Se liga en Stocks → esa sucursal → "Empleados vinculados".`;
    }
    return '';
  }

  motivoProductoDelMes(product: AdminProduct): string {
    if (this.isSettingProductOfMonth) return 'Guardando…';
    if (!product.active) return 'Reactiva el producto para poder destacarlo como producto del mes.';
    return '';
  }

  get motivoCrearClientePos(): string {
    if (!this.hasPermission('customer_add')) return 'No tienes el permiso "Agregar clientes": pídeselo a tu gerente.';
    if (this.isSavingPosCustomer) return 'Guardando…';
    if (!this.posCustomerForm.firstName.trim()) return 'Escribe el nombre.';
    if (!this.posCustomerForm.apellidoPaterno.trim()) return 'Escribe el apellido paterno.';
    return '';
  }

  // Tabla única de descuento en el POS (construida por B, montada por I1)

  get posTablaTiers(): Array<{ min: number; max: number | null; rate: number }> {
    const tiers = this.businessConfig?.rewards?.discountTiers ?? [];
    return tiers.map((t) => ({ min: Number(t.min) || 0, max: t.max == null ? null : Number(t.max), rate: Number(t.rate) || 0 }));
  }

  get posMxnPerVp(): number {
    return Number(this.businessConfig?.bonuses?.vpConfig?.mxnPerVp ?? 50) || 50;
  }

  get posActivationVp(): number {
    return Number(this.businessConfig?.rewards?.activationNetMin ?? 20) || 20;
  }

  /** VP netos del mes según el servidor; sin dato, se estiman desde el neto. */
  get posCustomerMonthVp(): number {
    const vp = this.posSelectedCustomerMonth?.vp;
    if (vp != null && Number.isFinite(Number(vp))) {
      return Number(vp);
    }
    return Math.round((this.posCustomerMonthNet / this.posMxnPerVp) * 10) / 10;
  }

  /** PC de lista de la venta en curso: puntos del producto si los tiene, o precio ÷ pesos por VP. */
  get posCartPc(): number {
    const total = this.availablePosProducts
      .filter((product) => this.posItems.has(product.id))
      .reduce((acc, product) => {
        const qty = this.posItems.get(product.id) ?? 1;
        const pcUnidad = product.vpPoints != null ? Number(product.vpPoints) : Number(product.price) / this.posMxnPerVp;
        return acc + pcUnidad * qty;
      }, 0);
    return Math.round(total * 10) / 10;
  }

  /** Resumen del envío tal como quedó guardado en el servidor. */
  private resumenEnvioGuardado(guardado: AdminOrder | null | undefined, orderId: string): string {
    if (!guardado) {
      return 'Envío registrado.';
    }
    const guia = guardado.trackingNumber ? ` · guía ${guardado.trackingNumber}` : '';
    const paqueteria = guardado.shippingCarrier ? ` (${guardado.shippingCarrier})` : '';
    return `Pedido ${guardado.id || orderId}: el servidor lo dejó ${this.orderStatusLabel(guardado.status)}${guia}${paqueteria}.`;
  }
}




