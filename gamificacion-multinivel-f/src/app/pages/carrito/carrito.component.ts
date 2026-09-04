import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, Subscription } from 'rxjs';
import { Router, RouterLink } from '@angular/router';

import { ESTADOS_MX_CODES, ESTADOS_MX_OPTIONS } from '../../constants/states-mx';
import { CartItem } from '../../models/cart.model';
import { DashboardGoal, DashboardProduct } from '../../models/user-dashboard.model';
import { AdminOrderItem, CustomerShippingAddress, ShippingRate, ShippingQuoteItem, CouponValidation } from '../../models/admin.model';
import { DatosFiscales, EnvioInfo, SucursalRecoger, SugerenciaActivacion } from '../../models/checkout.model';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CartControlService } from '../../services/cart-control.service';
import { CheckoutService } from '../../services/checkout.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { GoalControlService } from '../../services/goal-control.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';
import { UiProductCardComponent } from '../../components/ui-product-card/ui-product-card.component';
import { UiGoalProgressComponent } from '../../components/ui-goal-progress/ui-goal-progress.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';
import { UiChoiceCardComponent } from '../../components/ui-choice-card/ui-choice-card.component';
import { UiCheckboxComponent } from '../../components/ui-checkbox/ui-checkbox.component';
import { UiQtyStepperComponent } from '../../components/ui-qty-stepper/ui-qty-stepper.component';
// Ola B · I2: tabla única de descuento (B) y "Como socia habrías ahorrado" (B) en el carrito.
import { UiTablaDescuentoComponent } from '../../components/ui-tabla-descuento/ui-tabla-descuento.component';
import { UiAhorroSocioComponent } from '../../components/ui-ahorro-socio/ui-ahorro-socio.component';
import { PlanSocio } from '../../models/plan-socio.model';
import { ModoVisible, PlanSocioService } from '../../services/plan-socio.service';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiDesgloseIvaComponent } from '../../components/ui-desglose-iva/ui-desglose-iva.component';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, UiButtonComponent, UiFormFieldComponent, UiProductCardComponent, UiGoalProgressComponent, UiModalComponent, UiChoiceCardComponent, UiQtyStepperComponent, UiCheckboxComponent, UiTablaDescuentoComponent, UiAhorroSocioComponent, UiFooterComponent, UiDesgloseIvaComponent],
  templateUrl: './carrito.component.html',
  styleUrl: './carrito.component.css'
})
export class CarritoComponent implements OnInit, OnDestroy {
  readonly dashboardLink = ['/dashboard'];
  readonly stateOptions = ESTADOS_MX_OPTIONS;
  readonly countryOptions = [{ value: 'MX', label: 'Mexico' }];

  constructor(
    private readonly cartControl: CartControlService,
    private readonly cdr: ChangeDetectorRef,
    private readonly goalControl: GoalControlService,
    private readonly dashboardControl: UserDashboardControlService,
    private readonly api: ApiService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly checkout: CheckoutService,
    private readonly planSocio: PlanSocioService
  ) {}

  // ── Ola B · I2: tabla única de descuento y ahorro como socia ──
  /** Plan publicado (tramos, activación); la tabla del carrito usa los mismos números que el panel. */
  plan: PlanSocio | null = null;
  private planSub?: Subscription;

  // ── Paquete C · envío visible, completa tu activación, sucursales y factura ──
  envioInfo: EnvioInfo | null = null;
  sugerencia: SugerenciaActivacion | null = null;
  isLoadingSugerencia = false;
  /** Sucursales devueltas por el servidor para la ciudad/estado capturados y el carrito actual. */
  pickupOptions: SucursalRecoger[] = [];
  pickupAvailable = false;
  pickupCities: string[] = [];
  pickupLocationGiven = false;
  invoiceRequested = false;
  invoiceForm: DatosFiscales = { rfc: '', razonSocial: '', regimenFiscal: '', cpFiscal: '', usoCfdi: '', email: '' };
  invoiceErrors: Partial<Record<keyof DatosFiscales, string>> = {};
  private checkoutRefreshTimeout?: number;
  private lastPickupQueryKey = '';

  isToastVisible = false;
  toastMessage = 'Actualizado.';
  isSummaryOpen = false;
  isPlacingOrder = false;
  // Cupón / código de descuento (H7)
  couponCode = '';
  appliedCoupon: CouponValidation | null = null;
  couponMessage = '';
  couponChecking = false;
  deliveryType: 'delivery' | 'pickup' = 'delivery';
  pickupPaymentMethod: 'online' | 'at_store' = 'online';
  pickupStocks: Array<{ id: string; name: string; location: string }> = [];
  selectedPickupStockId = '';
  isLoadingPickupStocks = false;
  shippingRates: ShippingRate[] = [];
  isLoadingShippingRates = false;
  selectedShippingRate: ShippingRate | null = null;
  shippingQuoteError = '';
  deliveryName = '';
  deliveryPhone = '';
  /** Correo del comprador sin cuenta: sin él, ningún invitado recibía aviso de pago, envío ni entrega. */
  deliveryEmail = '';
  deliveryStreet = '';
  deliveryNumber = '';
  deliveryAddress = '';
  deliveryCity = '';
  deliveryPostalCode = '';
  deliveryState = '';
  deliveryCountry = 'MX';
  deliveryBetweenStreets = '';
  deliveryReferences = '';
  deliveryNotes = '';
  shippingAddresses: CustomerShippingAddress[] = [];
  selectedShippingAddressId = '';
  shippingAddressLabel = '';
  saveShippingAddress = false;
  deliveryFieldErrors: Record<'deliveryStreet' | 'deliveryNumber' | 'deliveryCity' | 'deliveryPostalCode' | 'deliveryState' | 'deliveryCountry', boolean> = {
    deliveryStreet: false,
    deliveryNumber: false,
    deliveryCity: false,
    deliveryPostalCode: false,
    deliveryState: false,
    deliveryCountry: false
  };
  // ── Paquete C · ronda 26 · propuesta 3 ──
  /** Nombre, teléfono y correo son datos de contacto del pedido: se piden siempre y el error se pinta en el campo.
   *  Antes vivían dentro del bloque de envío a domicilio: quien elegía "Recoger en sucursal" no tenía dónde
   *  escribir su correo y el botón de pagar se lo exigía igual (dos pedidos de mostrador sin nombre ni teléfono). */
  contactFieldErrors: Record<'deliveryName' | 'deliveryPhone' | 'deliveryEmail', string> = {
    deliveryName: '',
    deliveryPhone: '',
    deliveryEmail: ''
  };
  isProductDetailsOpen = false;
  selectedProduct: DashboardProduct | null = null;
  lastAddedItemId = '';
  showGuestRegisterModal = false;
  guestRegisterForm = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };
  isGuestRegisterSubmitting = false;
  guestRegisterFeedback = '';
  guestRegisterFeedbackType: 'error' | 'success' | '' = '';
  private toastTimeout?: number;
  private countdownInterval?: number;
  private dataSub?: Subscription;
  private goalsSub?: Subscription;
  private dashboardSub?: Subscription;
  private shippingQuoteSub?: Subscription;
  /** Espera antes de cotizar mientras se teclea el CP (propuesta 31). */
  private shippingQuoteTimeout?: number;
  private addFadeTimeout?: number;
  private addFadeRestartTimeout?: number;
  private hasPrefilledDashboardAddress = false;
  suggestedProducts: DashboardProduct[] = [];

  ngOnInit(): void {
    this.restoreDeliveryState();
    this.planSub = this.planSocio.plan$.subscribe({
      next: (plan) => {
        this.plan = plan;
        this.cdr.markForCheck();
      },
      error: () => this.cdr.markForCheck()
    });
    this.cartControl.load().subscribe(() => {
      this.cdr.detectChanges();
    });
    this.refreshSuggestedProducts();
    this.dataSub = this.cartControl.data$.subscribe(() => {
      this.refreshSuggestedProducts();
      this.scheduleCheckoutRefresh();
      this.cdr.markForCheck();
    });
    this.goalControl.load().subscribe();
    this.goalsSub = this.goalControl.goals$.subscribe(() => this.cdr.markForCheck());
    this.dashboardSub = this.dashboardControl.data$.subscribe((data) => {
      this.refreshSuggestedProducts();
      if (!data || this.hasPrefilledDashboardAddress) {
        return;
      }
      this.prefillCustomerAddressFromDashboard();
    });
    this.updateCountdown();
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 60000);
    this.loadPickupStocks();
    this.scheduleCheckoutRefresh();
  }

  private restoreDeliveryState(): void {
    const saved = this.cartControl.getDeliveryState();
    if (saved.deliveryType) {
      this.deliveryType = saved.deliveryType;
    }
    if (saved.selectedShippingAddressId) {
      this.selectedShippingAddressId = saved.selectedShippingAddressId;
      this.hasPrefilledDashboardAddress = true;
    }
    if (saved.shippingAddressLabel) { this.shippingAddressLabel = saved.shippingAddressLabel; }
    if (saved.deliveryName) { this.deliveryName = saved.deliveryName; }
    if (saved.deliveryPhone) { this.deliveryPhone = saved.deliveryPhone; }
    if (saved.deliveryEmail) { this.deliveryEmail = saved.deliveryEmail; }
    if (saved.deliveryStreet) { this.deliveryStreet = saved.deliveryStreet; }
    if (saved.deliveryNumber) { this.deliveryNumber = saved.deliveryNumber; }
    if (saved.deliveryCity) { this.deliveryCity = saved.deliveryCity; }
    if (saved.deliveryPostalCode) { this.deliveryPostalCode = saved.deliveryPostalCode; }
    if (saved.deliveryState) { this.deliveryState = saved.deliveryState; }
    if (saved.deliveryCountry) { this.deliveryCountry = saved.deliveryCountry; }
    if (saved.deliveryBetweenStreets) { this.deliveryBetweenStreets = saved.deliveryBetweenStreets; }
    if (saved.deliveryReferences) { this.deliveryReferences = saved.deliveryReferences; }
    if (saved.deliveryNotes) { this.deliveryNotes = saved.deliveryNotes; }

    if (this.deliveryType === 'delivery' && this.cpParaCotizar) {
      this.fetchShippingRates();
    }
  }

  ngOnDestroy(): void {
    this.dataSub?.unsubscribe();
    this.goalsSub?.unsubscribe();
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    if (this.addFadeTimeout) {
      window.clearTimeout(this.addFadeTimeout);
    }
    if (this.addFadeRestartTimeout) {
      window.clearTimeout(this.addFadeRestartTimeout);
    }
    if (this.checkoutRefreshTimeout) {
      window.clearTimeout(this.checkoutRefreshTimeout);
    }
    if (this.shippingQuoteTimeout) {
      window.clearTimeout(this.shippingQuoteTimeout);
    }
    this.dashboardSub?.unsubscribe();
    this.shippingQuoteSub?.unsubscribe();
    this.planSub?.unsubscribe();
    this.cartControl.saveDeliveryState({
      deliveryType: this.deliveryType,
      selectedShippingAddressId: this.selectedShippingAddressId,
      shippingAddressLabel: this.shippingAddressLabel,
      selectedShippingCarrier: this.selectedShippingRate?.carrier ?? '',
      selectedShippingRateId: this.selectedShippingRate?.service ?? '',
      deliveryName: this.deliveryName,
      deliveryPhone: this.deliveryPhone,
      deliveryEmail: this.deliveryEmail,
      deliveryStreet: this.deliveryStreet,
      deliveryNumber: this.deliveryNumber,
      deliveryCity: this.deliveryCity,
      deliveryPostalCode: this.deliveryPostalCode,
      deliveryState: this.deliveryState,
      deliveryCountry: this.deliveryCountry,
      deliveryBetweenStreets: this.deliveryBetweenStreets,
      deliveryReferences: this.deliveryReferences,
      deliveryNotes: this.deliveryNotes
    });
  }

  get countdownLabel(): string {
    return this.cartControl.countdownLabel;
  }

  get cartItems(): CartItem[] {
    return this.cartControl.cartItems;
  }

  private computeSuggestedProducts(): DashboardProduct[] {
    const products = this.dashboardControl.products ?? [];
    if (!products.length) {
      return [];
    }

    const cartIds = new Set(this.cartItems.map((item) => this.extractProductId(item.id)));
    const cartTags = this.collectCartTags(products);

    const scored = products.map((product, index) => {
      const tags = this.normalizeTags(product.tags?.length ? product.tags : product.badge ? [product.badge] : []);
      const score = tags.reduce((acc, tag) => acc + (cartTags.has(tag) ? 1 : 0), 0);
      return { product, score, index };
    });

    const notInCart = scored.filter((item) => !cartIds.has(item.product.id));
    const primary = notInCart
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.index - b.index);
    const fallback = notInCart.filter((item) => item.score === 0).sort((a, b) => a.index - b.index);
    const ordered = [...primary, ...fallback].map((item) => item.product);

    if (ordered.length >= 3) {
      return ordered.slice(0, 3);
    }

    const fill = scored
      .filter((item) => !ordered.some((entry) => entry.id === item.product.id))
      .sort((a, b) => a.index - b.index)
      .map((item) => item.product);

    return [...ordered, ...fill].slice(0, 3);
  }

  private refreshSuggestedProducts(): void {
    this.suggestedProducts = this.computeSuggestedProducts();
  }

  get shipping(): number {
    return this.cartControl.shipping;
  }

  get discountPct(): number {
    return this.cartControl.discountPct;
  }

  get isGuest(): boolean {
    return !this.authService.currentUser;
  }

  /** Modo con el que se pinta el carrito: invitado sin sesión; cliente o socio según el panel (paquete B). */
  get modoCuenta(): ModoVisible {
    if (this.isGuest) {
      return 'invitado';
    }
    const delPanel = this.dashboardControl.data?.mode;
    if (delPanel === 'cliente' || delPanel === 'socio') {
      return delPanel;
    }
    const delServicio = this.planSocio.modoActual;
    return delServicio === 'cliente' ? 'cliente' : 'socio';
  }

  /** Neto acumulado del mes (MPN): en modo cliente el indicador del panel, si no el consumo propio. */
  get monthNetSocio(): number {
    const data = this.dashboardControl.data;
    const indicador = data?.clientIndicators?.monthSpend;
    if (this.modoCuenta === 'cliente' && indicador != null) {
      return Number(indicador) || 0;
    }
    return Number(data?.myNetSpend ?? 0) || 0;
  }

  /** VP netos acumulados del mes según el panel (en modo cliente el panel vacía `vp`: se usa el indicador). */
  get monthVpSocio(): number {
    const data = this.dashboardControl.data;
    const indicador = data?.clientIndicators?.monthVp;
    if (this.modoCuenta === 'cliente' && indicador != null) {
      return Number(indicador) || 0;
    }
    return Number(data?.vp ?? 0) || 0;
  }

  /** PC de lista del carrito (sin descuento): la tabla los convierte a VP netos con la tasa del tramo. */
  get cartPc(): number {
    const products = this.dashboardControl.products ?? [];
    return this.cartItems.reduce((sum, item) => {
      const product = products.find((p) => p.id === this.extractProductId(item.id));
      return sum + Number(product?.vpPoints ?? 0) * item.qty;
    }, 0);
  }

  /** La tabla única se muestra con sesión y plan cargado (socio o cliente); los invitados ven solo el ahorro. */
  get tablaDescuentoVisible(): boolean {
    return !this.isGuest && this.plan != null && this.cartItems.length > 0;
  }

  get modoTabla(): 'cliente' | 'socio' {
    return this.modoCuenta === 'cliente' ? 'cliente' : 'socio';
  }

  /** "Activar modo socio" desde la tabla (solo en modo cliente): lleva a la landing del plan. */
  goToModoSocio(): void {
    void this.router.navigate(['/modo-socio'], { queryParams: { desde: 'carrito' } });
  }

  get hasSavedShippingAddresses(): boolean {
    return this.shippingAddresses.length > 0;
  }

  // ── Paquete C · ronda 26 · propuesta 31 ──
  /** CP de cinco dígitos: es lo único que el cotizador necesita. */
  get cpParaCotizar(): string {
    const cp = this.deliveryPostalCode.trim();
    return /^\d{5}$/.test(cp) ? cp : '';
  }

  get isShippingQuoteReady(): boolean {
    return Boolean(this.cpParaCotizar);
  }

  get goalTitle(): string {
    return this.activeGoal?.title || 'Meta de beneficios';
  }

  get goalSubtitle(): string {
    return this.activeGoal?.subtitle || 'Acumula consumo para activar beneficios.';
  }

  get basePercent(): number {
    const goal = this.activeGoal;
    if (!goal) {
      return 0;
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    if (!target) {
      return 0;
    }
    return Math.min(100, (base / target) * 100);
  }

  get cartPercent(): number {
    const goal = this.activeGoal;
    if (!goal || goal.isCountGoal) {
      return 0;
    }
    const target = Number(goal.target ?? 0);
    if (!target) {
      return 0;
    }
    const cart = Number(goal.cart ?? 0);
    const cartPercent = (cart / target) * 100;
    return Math.min(100 - this.basePercent, Math.max(0, cartPercent));
  }

  private get discountPercentValue(): number {
    if (!this.authService.currentUser || this.authService.currentUser.role !== 'cliente') {
      const raw = this.authService.currentUser?.discountPercent;
      const value = typeof raw === 'string' ? Number(raw) : Number(raw ?? 0);
      return Number.isFinite(value) ? value : 0;
    }

    const current = this.currentDiscountPercentValue;
    const projected = this.projectedDiscountPercentValue;
    return Math.max(current, projected);
  }

  private get currentDiscountPercentValue(): number {
    const raw = this.dashboardControl.data?.user?.discountPercent ?? this.authService.currentUser?.discountPercent;
    const value = typeof raw === 'string' ? Number(raw) : Number(raw ?? 0);
    return Number.isFinite(value) ? value : 0;
  }

  private get discountActiveValue(): boolean {
    return Boolean(this.dashboardControl.data?.user?.discountActive ?? this.authService.currentUser?.discountActive) || this.discountPercentValue > 0;
  }

  get discountLevelLabel(): string {
    if (!this.discountActiveValue) {
      return 'Inactivo';
    }
    const pct = this.discountPercentValue;
    if (!pct) {
      return 'Sin descuento';
    }
    // Los niveles van con los tramos del plan (10/20/30/40%); antes el 20% se llamaba "Nivel base".
    if (pct >= 40) {
      return 'Nivel 4';
    }
    if (pct >= 30) {
      return 'Nivel 3';
    }
    if (pct >= 20) {
      return 'Nivel 2';
    }
    if (pct >= 10) {
      return 'Nivel 1';
    }
    return 'Sin descuento';
  }

  get hasDiscount(): boolean {
    return this.discountActiveValue && this.discountPercentValue > 0;
  }

  get discountPercent(): number {
    return this.hasDiscount ? this.discountPercentValue : 0;
  }

  get discountLabel(): string {
    if (!this.discountActiveValue) {
      return 'Sin descuento';
    }
    const pct = this.discountPercentValue;
    if (!pct) {
      return 'Sin descuento';
    }
    return `Dto ${pct}%`;
  }

  get discountUpgradeMessage(): string {
    const current = Math.max(0, this.currentDiscountPercentValue);
    const projected = Math.max(0, this.projectedDiscountPercentValue);
    if (projected <= current || projected <= 0) {
      return '';
    }
    return `Con esta compra subes a ${this.discountLevelLabelByPercent(projected)} (${projected}%).`;
  }

  discountedPrice(value: number): number {
    if (!this.hasDiscount) {
      return value;
    }
    const pct = this.discountPercentValue / 100;
    return Math.max(0, Math.round(value * (1 - pct)));
  }

  get subtotal(): number {
    return this.cartControl.subtotal;
  }

  get discount(): number {
    if (!this.hasDiscount) {
      return 0;
    }
    return Math.round(this.subtotal * (this.discountPercentValue / 100));
  }

  /** Descuento por cupón aplicado (sobre el neto tras descuento por volumen). */
  get couponDiscount(): number {
    return this.appliedCoupon?.valid ? Math.round(this.appliedCoupon.discount) : 0;
  }

  /** Base sobre la que aplica el cupón: neto tras descuento por volumen. */
  private get netAfterVolumeDiscount(): number {
    return Math.max(0, this.subtotal - this.discount);
  }

  applyCoupon(): void {
    const code = this.couponCode.trim().toUpperCase();
    if (!code) {
      this.couponMessage = 'Ingresa un código.';
      return;
    }
    this.couponChecking = true;
    this.couponMessage = '';
    this.api.validateCoupon(code, this.netAfterVolumeDiscount, this.resolveOrderCustomerId()).subscribe({
      next: (res) => {
        this.couponChecking = false;
        this.appliedCoupon = res;
        this.couponMessage = res.message;
        this.scheduleCheckoutRefresh();
        this.cdr.markForCheck();
      },
      error: () => {
        this.couponChecking = false;
        this.appliedCoupon = null;
        this.couponMessage = 'No se pudo validar el cupón.';
        this.cdr.markForCheck();
      }
    });
  }

  removeCoupon(): void {
    this.appliedCoupon = null;
    this.couponCode = '';
    this.couponMessage = '';
    this.scheduleCheckoutRefresh();
  }

  get total(): number {
    if (this.deliveryType === 'pickup') {
      return Math.max(0, this.subtotal - this.discount - this.couponDiscount);
    }
    const shippingCost = this.isShippingFree ? 0 : (this.selectedShippingRate !== null ? this.selectedShippingRate.displayPrice : this.shipping);
    return Math.max(0, this.subtotal + shippingCost - this.discount - this.couponDiscount);
  }

  /** Regla de envío gratis por importe (misma que aplica el backend al crear el pedido). */
  get freeShippingMin(): number {
    if (this.envioInfo) {
      return Number(this.envioInfo.freeShippingMin) || 0;
    }
    return Number(this.dashboardControl.data?.settings?.freeShippingMin ?? 0) || 0;
  }

  get isShippingFree(): boolean {
    if (this.deliveryType === 'pickup' || !this.freeShippingMin) {
      return false;
    }
    // El servidor mide la regla sobre el subtotal bruto (config shipping.freeShippingBasis);
    // "Envío gratis" dejaba de serlo al poner el CP porque aquí se medía sobre el neto.
    if (this.envioInfo) {
      return this.envioInfo.freeNow;
    }
    return Math.max(0, this.subtotal - this.discount - this.couponDiscount) >= this.freeShippingMin;
  }

  /** Tarifa base de envío anunciada antes de cotizar. */
  get baseShippingRate(): number {
    return Number(this.envioInfo?.baseRateMxn ?? 0) || 0;
  }

  /** "Envío desde $129 · Gratis en compras de $1,000 o más" (números de config). */
  get envioAnuncio(): string {
    const partes: string[] = [];
    if (this.baseShippingRate > 0) {
      partes.push(`Envío desde ${this.formatMoney(this.baseShippingRate)}`);
    }
    if (this.freeShippingMin > 0) {
      partes.push(`Gratis en compras de ${this.formatMoney(this.freeShippingMin)} o más`);
    }
    return partes.length ? partes.join(' · ') : 'Recibe en tu dirección';
  }

  /** Cuánto falta de compra (bruto) para el envío gratis; 0 si ya aplica o no hay regla. */
  get faltanteEnvioGratis(): number {
    if (this.deliveryType === 'pickup' || !this.envioInfo || this.envioInfo.freeNow) {
      return 0;
    }
    return Math.max(0, Number(this.envioInfo.missingForFree) || 0);
  }

  get shippingLabel(): string {
    if (this.deliveryType === 'pickup') {
      return 'Gratis (recoger en sucursal)';
    }
    if (this.isShippingFree) {
      return `Gratis (compra de ${this.formatMoney(this.freeShippingMin)} o más)`;
    }
    if (this.selectedShippingRate) {
      return this.formatMoney(this.selectedShippingRate.displayPrice);
    }
    if (this.isLoadingShippingRates) {
      return 'Calculando con tu CP...';
    }
    // "Envío desde $129 · se calcula con tu CP" era mentira: la cotización solo salía con la
    // dirección completa. Ahora basta el CP, y el rótulo dice exactamente qué hay que escribir.
    if (this.baseShippingRate > 0) {
      return `Desde ${this.formatMoney(this.baseShippingRate)} · escribe tu CP y lo calculamos`;
    }
    return this.shipping === 0 ? 'Escribe tu CP y lo calculamos' : this.formatMoney(this.shipping);
  }

  /** El rótulo del resumen se llama "Subtotal" mientras falte el envío, y "Total" cuando ya está todo.
   *  Mariana leyó "$700" arriba y pagó "$829": el número no mentía, el nombre sí. */
  get totalLabel(): string {
    return this.deliveryType === 'delivery' && !this.selectedShippingRate && !this.isShippingFree
      ? 'Subtotal'
      : 'Total';
  }

  /** Aclaración de una línea junto al rótulo, para que "Subtotal" no quede sin explicación. */
  get totalNote(): string {
    return this.totalLabel === 'Subtotal' ? 'Falta el envío: escribe tu CP para verlo completo.' : '';
  }

  // ── Completa tu activación ──
  get activationSuggestionVisible(): boolean {
    return Boolean(!this.isGuest && this.sugerencia?.applies && this.sugerencia?.suggestion);
  }

  /** "Agrega 1 Naplus ($280, +5.4 VP) y llegas a 24.3 VP". */
  get activationSuggestionText(): string {
    const s = this.sugerencia?.suggestion;
    if (!s) {
      return '';
    }
    const piezas = s.units === 1 ? `1 ${s.name}` : `${s.units} ${s.name}`;
    const vp = Math.round(s.netVpPerUnit * s.units * 10) / 10;
    return `Agrega ${piezas} (${this.formatMoney(s.cost)}, +${vp} VP) y llegas a ${s.vpAfter} VP.`;
  }

  addSuggestedActivation(): void {
    const s = this.sugerencia?.suggestion;
    if (!s) {
      return;
    }
    const id = String(s.productId);
    const product = (this.dashboardControl.products ?? []).find((p) => String(p.id) === id);
    const item: CartItem = product
      ? this.buildCartItem(product)
      : { id, name: s.name, price: s.price, qty: 1, note: '', img: '' };
    this.cartControl.addItem(item, s.units);
    this.cdr.markForCheck();
    const vp = Math.round(s.netVpPerUnit * s.units * 10) / 10;
    this.showToast(`Agregado: ${s.units} ${s.name} (+${vp} VP). Con esto llegas a ${s.vpAfter} VP.`);
    this.triggerAddedFade(id);
  }

  // ── Recoger en sucursal ──
  /** La opción solo se ofrece si hay sucursal en la zona con existencia, o si aún no sabemos la zona. */
  get pickupChoiceVisible(): boolean {
    if (this.pickupAvailable) {
      return true;
    }
    return !this.pickupLocationGiven && this.pickupOptions.length > 0;
  }

  get pickupCitiesLabel(): string {
    return this.pickupCities.join(', ');
  }

  /** Motivo por el que no se ofrece recoger en sucursal (vacío si sí se ofrece). */
  get pickupUnavailableNote(): string {
    if (this.isLoadingPickupStocks || this.pickupChoiceVisible) {
      return '';
    }
    if (!this.pickupOptions.length) {
      return 'Por ahora no hay sucursales para recoger: te lo enviamos a domicilio.';
    }
    const enZona = this.pickupOptions.filter((s) => s.inArea);
    if (!enZona.length) {
      // Sin ciudad en el almacén se nombra la sucursal, no su dirección.
      const donde = this.pickupCitiesLabel || this.pickupOptions.map((s) => s.name).filter(Boolean).join(', ');
      return `Recoger en sucursal no está disponible en tu zona. Hay sucursal en: ${donde}. Te lo enviamos a domicilio.`;
    }
    const faltantes = new Set<string>();
    enZona.forEach((s) => s.missing.forEach((m) => faltantes.add(m)));
    return `La sucursal de tu zona no tiene ${[...faltantes].join(', ')} en existencia: te lo enviamos a domicilio.`;
  }

  pickupReason(branch: SucursalRecoger): string {
    if (branch.canPickup) {
      return 'Tiene todo tu pedido';
    }
    if (!branch.inArea) {
      return 'Fuera de tu ciudad/estado';
    }
    return branch.missing.length ? `No tiene ${branch.missing.join(', ')}` : 'No disponible';
  }

  selectPickupStock(branch: SucursalRecoger): void {
    if (!branch.canPickup) {
      this.showToast(`${branch.name}: ${this.pickupReason(branch)}.`);
      return;
    }
    this.selectedPickupStockId = branch.id;
  }

  // ── Quiero factura ──
  get invoiceEnabled(): boolean {
    return Boolean(this.envioInfo?.checkout?.invoiceEnabled);
  }

  get regimenOptions(): Array<{ value: string; label: string }> {
    return (this.envioInfo?.checkout?.regimenesFiscales ?? []).map((o) => ({ value: o.key, label: o.label }));
  }

  get usoCfdiOptions(): Array<{ value: string; label: string }> {
    return (this.envioInfo?.checkout?.usosCfdi ?? []).map((o) => ({ value: o.key, label: o.label }));
  }

  toggleInvoice(checked: boolean): void {
    this.invoiceRequested = checked;
    this.invoiceErrors = {};
    if (checked) {
      // Prellenado desde el perfil: a Rodrigo le recapturaron los datos fiscales cuatro veces.
      const customer = this.dashboardControl.customer;
      this.invoiceForm.razonSocial = this.invoiceForm.razonSocial || customer?.name || this.authService.currentUser?.name || '';
      this.invoiceForm.email = this.invoiceForm.email || this.deliveryEmail.trim();
      if (!this.invoiceForm.usoCfdi && this.usoCfdiOptions.length) {
        const general = this.usoCfdiOptions.find((o) => o.value === 'G03');
        this.invoiceForm.usoCfdi = (general ?? this.usoCfdiOptions[0]).value;
      }
    }
    this.cdr.markForCheck();
  }

  onInvoiceField(field: keyof DatosFiscales, value: string): void {
    let limpio = String(value ?? '');
    if (field === 'rfc') {
      limpio = limpio.toUpperCase().replace(/[^A-ZÑ&0-9]/g, '').slice(0, 13);
    }
    if (field === 'cpFiscal') {
      limpio = limpio.replace(/\D/g, '').slice(0, 5);
    }
    this.invoiceForm = { ...this.invoiceForm, [field]: limpio };
    if (this.invoiceErrors[field]) {
      this.validateInvoiceForm();
    }
  }

  validateInvoiceForm(): boolean {
    const f = this.invoiceForm;
    const errores: Partial<Record<keyof DatosFiscales, string>> = {};
    if (!/^([A-ZÑ&]{3}|[A-ZÑ&]{4})\d{6}[A-Z0-9]{3}$/.test(f.rfc.trim().toUpperCase())) {
      errores.rfc = 'Escribe el RFC como aparece en tu constancia (12 o 13 caracteres).';
    }
    if (!f.razonSocial.trim()) {
      errores.razonSocial = 'Nombre o razón social tal como está en el SAT.';
    }
    if (!f.regimenFiscal) {
      errores.regimenFiscal = 'Elige tu régimen fiscal.';
    }
    if (!/^\d{5}$/.test(f.cpFiscal.trim())) {
      errores.cpFiscal = 'Cinco dígitos.';
    }
    if (!f.usoCfdi) {
      errores.usoCfdi = 'Elige el uso del CFDI.';
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) {
      errores.email = 'Correo al que te mandaremos la factura.';
    }
    this.invoiceErrors = errores;
    return Object.keys(errores).length === 0;
  }

  private invoicePayload(): DatosFiscales {
    const f = this.invoiceForm;
    return {
      rfc: f.rfc.trim().toUpperCase(),
      razonSocial: f.razonSocial.trim(),
      regimenFiscal: f.regimenFiscal,
      cpFiscal: f.cpFiscal.trim(),
      usoCfdi: f.usoCfdi,
      email: f.email.trim().toLowerCase()
    };
  }

  // ── Consultas al servidor (con pequeña espera para no disparar una por tecla) ──
  private scheduleCheckoutRefresh(): void {
    if (this.checkoutRefreshTimeout) {
      window.clearTimeout(this.checkoutRefreshTimeout);
    }
    this.checkoutRefreshTimeout = window.setTimeout(() => this.refreshCheckoutInfo(), 250);
  }

  private refreshCheckoutInfo(): void {
    this.checkout.envioInfo(this.subtotal).subscribe({
      next: (info) => {
        this.envioInfo = info;
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    });
    this.refreshActivationSuggestion();
    this.loadPickupStocks();
  }

  private refreshActivationSuggestion(): void {
    const user = this.authService.currentUser;
    if (!user?.userId || user.role !== 'cliente' || !this.cartItems.length && !this.activeGoal) {
      this.sugerencia = null;
      return;
    }
    this.isLoadingSugerencia = true;
    this.checkout
      .sugerenciaActivacion({
        customerId: this.resolveOrderCustomerId(),
        items: this.cartItems.map((item) => ({ productId: this.extractProductId(item.id), quantity: item.qty, price: item.price })),
        couponCode: this.appliedCoupon?.valid ? this.couponCode.trim().toUpperCase() : undefined
      })
      .pipe(finalize(() => {
        this.isLoadingSugerencia = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (respuesta) => {
          this.sugerencia = respuesta;
          this.cdr.markForCheck();
        },
        error: () => {
          this.sugerencia = null;
          this.cdr.markForCheck();
        }
      });
  }

  get itemsCount(): number {
    return this.cartControl.itemsCount;
  }

  get totalDiscount(): number {
    return this.discount;
  }

  get gapToGoal(): number {
    const goal = this.activeGoal;
    if (!goal) {
      return this.cartControl.gapToGoal;
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    const remaining = Math.max(0, target - base);
    // Una meta en VP se descuenta con los puntos del carrito, no con los pesos:
    // antes "Te faltan $0" con $280 en el carrito y 20 VP de meta.
    const progress = goal.unit === 'vp' ? this.cartVp : this.subtotal;
    return Math.max(0, remaining - progress);
  }

  /** Puntos (PC) que suma el carrito según el catálogo. */
  get cartVp(): number {
    const products = this.dashboardControl.products ?? [];
    const bruto = this.cartItems.reduce((sum, item) => {
      const product = products.find((p) => p.id === this.extractProductId(item.id));
      return sum + (Number(product?.vpPoints ?? 0) * item.qty);
    }, 0);
    // El motor acredita VP netos: PC × (neto ÷ bruto), y "neto" incluye el
    // cupón. El carrito decía "Te faltan 0 VP" con 21 PC y el tablero "18.9 de
    // 20" tras pagar; con cupón la diferencia es mayor y nadie la veía.
    const bruto$ = this.subtotal || 0;
    const neto$ = Math.max(0, bruto$ - (this.discount || 0) - (this.couponDiscount || 0));
    const factor = bruto$ > 0 ? neto$ / bruto$ : 1 - (this.discountPercent || 0) / 100;
    return Math.round(bruto * factor * 10) / 10;
  }

  /** Solo hay algo que decir cuando existe una meta y todavía falta algo ("Te faltan $0" contradecía "Inactivo"). */
  get hasGoalGap(): boolean {
    return !!this.activeGoal && this.gapToGoal > 0;
  }

  /** "Te faltan …" con la unidad de la meta activa. */
  get gapToGoalLabel(): string {
    if (this.activeGoal?.unit === 'vp') {
      const gap = this.gapToGoal;
      return `${Number.isInteger(gap) ? gap : gap.toFixed(1)} VP`;
    }
    return this.formatMoney(this.gapToGoal);
  }

  get benefitPercent(): number {
    const goal = this.activeGoal;
    if (!goal) {
      return this.cartControl.benefitPercent;
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    const remaining = Math.max(0, target - base);
    if (remaining === 0) {
      return 100;
    }
    const progress = goal.unit === 'vp' ? this.cartVp : this.subtotal;
    return Math.min(100, (progress / remaining) * 100);
  }

  /** Meta de activación en VP (si la hay): objetivo y hueco con el carrito actual. */
  get vpGoalTarget(): number {
    const goal = this.activeGoal;
    return goal && goal.unit === 'vp' ? Number(goal.target || 0) : 0;
  }

  get vpGoalGap(): number {
    const goal = this.activeGoal;
    if (!goal || goal.unit !== 'vp') {
      return 0;
    }
    return Math.max(0, Math.round((Number(goal.target || 0) - Number(goal.base || 0) - this.cartVp) * 10) / 10);
  }

  /** El cupón recorta VP: avisa cuando con cupón no se llega a la meta y sin cupón sí. */
  /** Sin cupón también: Bety compró "20 PC" y quedó en 18 VP netos por el descuento, dos abajo de la activación. */
  get orderLeavesBelowVpGoal(): boolean {
    const goal = this.activeGoal;
    if (this.isGuest || !goal || goal.unit !== 'vp' || this.cartVp <= 0) {
      return false;
    }
    const base = Number(goal.base || 0);
    return base + this.cartVp < Number(goal.target || 0) && !this.couponLeavesBelowVpGoal;
  }

  get vpAfterOrder(): number {
    const goal = this.activeGoal;
    return Math.round((Number(goal?.base || 0) + this.cartVp) * 10) / 10;
  }

  get couponLeavesBelowVpGoal(): boolean {
    if (!(this.couponDiscount > 0) || !this.vpGoalTarget) {
      return false;
    }
    const goal = this.activeGoal;
    const base = Number(goal?.base || 0);
    const bruto$ = this.subtotal || 0;
    const sinCupon = bruto$ > 0 ? (bruto$ - (this.discount || 0)) / bruto$ : 1;
    const products = this.dashboardControl.products ?? [];
    const pcBrutos = this.cartItems.reduce((sum, item) => sum + Number(products.find((p) => p.id === this.extractProductId(item.id))?.vpPoints ?? 0) * item.qty, 0);
    const vpSinCupon = Math.round(pcBrutos * sinCupon * 10) / 10;
    return base + this.cartVp < this.vpGoalTarget && base + vpSinCupon >= this.vpGoalTarget;
  }

  private get activeGoal(): DashboardGoal | null {
    return (
      this.goalControl.goals.find(
        (goal) => goal?.ctaFragment === 'merchant' && !goal?.achieved && !goal?.locked
      ) ??
      this.goalControl.goals.find((goal) => goal?.ctaFragment === 'merchant') ??
      null
    );
  }

  formatMoney(value: number): string {
    return this.cartControl.formatMoney(value);
  }

  setQty(itemId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    this.cartControl.setQty(itemId, normalized);
    this.cdr.markForCheck();
    if (normalized === 0) {
      this.showToast('Producto removido.');
      return;
    }
    this.showToast('Cantidad actualizada.');
  }

  removeItem(itemId: string): void {
    this.cartControl.removeItem(itemId);
    this.cdr.markForCheck();
    this.showToast('Producto removido.');
  }

  addSuggested(): void {
    const suggestedId = this.cartControl.suggestedItem?.id;
    this.cartControl.addSuggested();
    this.cdr.markForCheck();
    this.showToast('Agregado sugerido.');
    if (suggestedId) {
      this.triggerAddedFade(suggestedId);
    }
  }

  addSuggestedProduct(product: DashboardProduct): void {
    const item = this.buildCartItem(product);
    this.cartControl.addItem(item, 1);
    this.cdr.markForCheck();
    this.showToast('Agregado al carrito.');
    if (this.isProductDetailsOpen) {
      this.closeProductDetails();
    }
    this.triggerAddedFade(product.id);
  }

  openProductDetails(product: DashboardProduct): void {
    this.selectedProduct = product;
    this.isProductDetailsOpen = true;
  }

  closeProductDetails(): void {
    this.isProductDetailsOpen = false;
    this.selectedProduct = null;
  }

  getCartQty(productId: string): number {
    return this.cartControl.getProductQty(productId);
  }

  private extractProductId(itemId: string): string {
    return itemId.includes('::') ? itemId.split('::')[0] : itemId;
  }

  placeOrder(): void {
    if (!this.cartItems.length) {
      this.showToast('Agrega productos para continuar.');
      return;
    }
    if (this.isPlacingOrder) {
      return;
    }
    const pickupStockId = this.resolveSelectedPickupStockId(this.pickupStocks, this.selectedPickupStockId);
    // El contacto del pedido se pide siempre, y lo que falte se marca en su propio campo.
    if (!this.validarContacto()) {
      this.scrollToSection('contacto-pedido');
      this.focusFirstMissingContactField();
      this.showToast('Revisa tus datos de contacto: hay un campo marcado en rojo.');
      return;
    }
    if (this.deliveryType === 'pickup') {
      if (!pickupStockId) {
        this.selectedPickupStockId = '';
        this.showToast('Selecciona una sucursal para recoger tu pedido.');
        return;
      }
      const sucursal = this.pickupOptions.find((branch) => branch.id === pickupStockId);
      if (sucursal && !sucursal.canPickup) {
        this.showToast(`${sucursal.name}: ${this.pickupReason(sucursal)}. Elige otra sucursal o envío a domicilio.`);
        return;
      }
      if (!this.pickupPaymentMethod) {
        this.showToast('Selecciona un método de pago para continuar.');
        return;
      }
    }
    if (this.invoiceRequested && !this.validateInvoiceForm()) {
      this.showToast('Revisa los datos de tu factura: hay un campo marcado en rojo.');
      this.scrollToSection('factura-checkout');
      return;
    }
    const user = this.authService.currentUser;
    const items: AdminOrderItem[] = this.cartItems.map((item) => ({
      productId: Number(this.extractProductId(item.id)),
      name: item.name,
      price: item.price,
      quantity: item.qty
    }));
    let payload: Record<string, unknown>;
    if (this.deliveryType === 'pickup') {
      // El backend acepta recipientName y phone en cualquier modo de entrega; el carrito no se los
      // mandaba y los pedidos de mostrador quedaban sin nombre ni teléfono de quien los va a recoger.
      payload = {
        customerId: this.resolveOrderCustomerId(),
        customerName: user?.name || this.resolveDeliveryName() || 'Cliente',
        email: this.isGuest ? this.deliveryEmail.trim() || undefined : undefined,
        status: 'pending' as const,
        items,
        recipientName: this.resolveDeliveryName() || user?.name,
        phone: this.resolveDeliveryPhone() || undefined,
        deliveryType: 'pickup',
        pickupStockId,
        pickupPaymentMethod: this.pickupPaymentMethod
      };
    } else {
      const recipientName = this.resolveDeliveryName();
      const phone = this.resolveDeliveryPhone();
      const street = this.deliveryStreet.trim();
      const number = this.deliveryNumber.trim();
      const city = this.deliveryCity.trim();
      const postalCode = this.deliveryPostalCode.trim();
      const state = this.deliveryState.trim();
      const country = this.deliveryCountry.trim().toUpperCase();
      const address = this.buildDeliveryAddressLine();
      if (
        !this.setDeliveryFieldErrors({
          deliveryStreet: street,
          deliveryNumber: number,
          deliveryCity: city,
          deliveryPostalCode: postalCode,
          deliveryState: state,
          deliveryCountry: country
        })
      ) {
        this.showToast('Completa calle, numero, ciudad, CP, estado y pais para continuar.');
        this.scrollToSection('detalle-carrito');
        this.focusFirstMissingDeliveryField();
        return;
      }
      const shippingAddress = {
        id: this.selectedShippingAddressId || undefined,
        addressId: this.selectedShippingAddressId || undefined,
        label: this.resolveShippingAddressLabel() || undefined,
        recipientName: recipientName || user?.name || undefined,
        phone: phone || undefined,
        street: street || undefined,
        number: number || undefined,
        address: address || undefined,
        city: city || undefined,
        postalCode: postalCode || undefined,
        state: state || undefined,
        country: country || undefined,
        betweenStreets: this.deliveryBetweenStreets.trim() || undefined,
        references: this.deliveryReferences.trim() || undefined
      };
      payload = {
        customerId: this.resolveOrderCustomerId(),
        customerName: user?.name || recipientName || 'Cliente',
        email: this.isGuest ? this.deliveryEmail.trim() || undefined : undefined,
        status: 'pending' as const,
        items,
        shippingAddress,
        recipientName: recipientName || user?.name,
        phone: phone || undefined,
        street,
        number,
        address,
        city,
        postalCode,
        state,
        country,
        betweenStreets: this.deliveryBetweenStreets.trim() || undefined,
        references: this.deliveryReferences.trim() || undefined,
        deliveryNotes: this.deliveryNotes.trim() || undefined,
        shippingAddressId: this.selectedShippingAddressId || undefined,
        shippingAddressLabel: this.resolveShippingAddressLabel() || undefined,
        saveShippingAddress: Boolean(user?.userId && this.saveShippingAddress),
        shippingCarrier: this.selectedShippingRate?.carrier || undefined,
        shippingService: this.selectedShippingRate?.service || undefined,
        shippingCost: this.isShippingFree ? 0 : (this.selectedShippingRate?.displayPrice ?? undefined),
        deliveryType: 'delivery'
      };
    }
    if (this.appliedCoupon?.valid) {
      payload['couponCode'] = this.couponCode.trim().toUpperCase();
    }
    if (this.invoiceRequested) {
      payload['invoiceRequested'] = true;
      payload['invoiceData'] = this.invoicePayload();
    }
    this.isPlacingOrder = true;
    this.api
      .createOrder(payload as any)
      .pipe(
        finalize(() => {
          this.isPlacingOrder = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (order) => {
          const resolvedId = (order as { id?: string | number; orderId?: string | number } | null)?.id ??
            (order as { orderId?: string | number } | null)?.orderId ??
            '';
          if (!resolvedId) {
            this.showToast('Orden creada, pero no se recibió el ID.');
            return;
          }
          const orderId = String(resolvedId);
          this.cartControl.clearCart();
          // La confirmación dice lo que el servidor guardó (folio, total, entrega y factura), no lo que se tecleó.
          const guardado = order as {
            total?: number; shippingCost?: number; deliveryType?: string; pickupPaymentMethod?: string;
            invoiceStatus?: string; invoiceData?: { rfc?: string };
          } | null;
          const totalGuardado = Number(guardado?.total ?? 0);
          const totalTexto = Number.isFinite(totalGuardado) && totalGuardado > 0 ? ` por ${this.formatMoney(totalGuardado)}` : '';
          const entregaTexto = guardado?.deliveryType === 'pickup'
            ? (guardado?.pickupPaymentMethod === 'at_store' ? ', para recoger y pagar en sucursal' : ', para recoger en sucursal')
            : (Number(guardado?.shippingCost ?? 0) > 0 ? ` (envío ${this.formatMoney(Number(guardado?.shippingCost))} incluido)` : ', con envío gratis');
          const facturaTexto = guardado?.invoiceStatus === 'solicitada'
            ? ` Factura solicitada para el RFC ${guardado?.invoiceData?.rfc ?? ''}: te llegará por correo en los próximos días hábiles.`
            : '';
          const siguiente = guardado?.deliveryType === 'pickup' && guardado?.pickupPaymentMethod === 'at_store'
            ? 'Te mostramos tu pedido...'
            : 'Te llevamos al pago...';
          this.showToast(`Pedido ${orderId} creado${totalTexto}${entregaTexto}.${facturaTexto} ${siguiente}`);
          this.router.navigate(['/orden', orderId]);
        },
        error: (err: { error?: { message?: string }; message?: string }) => {
          // El backend explica por qué (p. ej. la sucursal no tiene existencia); el toast lo tapaba.
          const motivo = err?.error?.message;
          this.showToast(motivo ? `No se pudo crear la orden: ${motivo}` : 'No se pudo crear la orden.');
        }
      });
  }

  /** Cotiza tras una pequeña espera, para no lanzar una consulta por cada tecla del CP. */
  private scheduleShippingQuote(): void {
    if (this.shippingQuoteTimeout) {
      window.clearTimeout(this.shippingQuoteTimeout);
    }
    this.shippingQuoteTimeout = window.setTimeout(() => this.fetchShippingRates(), 600);
  }

  fetchShippingRates(): void {
    const zipTo = this.cpParaCotizar;
    if (!zipTo) {
      this.shippingRates = [];
      this.selectedShippingRate = null;
      this.shippingQuoteError = '';
      return;
    }
    const items = this.buildShippingItems();
    this.isLoadingShippingRates = true;
    this.shippingQuoteError = '';
    this.shippingQuoteSub?.unsubscribe();
    // Solo CP y bultos: el cotizador exige *todos* los campos de dirección o ninguno, así que
    // mandarle el estado a medias devolvía 400 y el precio "aparecía al elegir el estado".
    this.shippingQuoteSub = this.api
      .getShippingQuote({
        zipTo,
        postalCode: zipTo,
        items
      })
      .pipe(finalize(() => {
        this.isLoadingShippingRates = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (rates) => {
          // La cotización podía traer la misma paquetería dos veces ("Estafeta" duplicada).
          const vistas = new Set<string>();
          this.shippingRates = rates.filter((r) => {
            const clave = `${r.carrier}|${r.service}|${r.displayPrice}`;
            if (vistas.has(clave)) { return false; }
            vistas.add(clave); return true;
          });
          rates = this.shippingRates;
          this.selectedShippingRate = rates.length > 0 ? rates[0] : null;
          this.cdr.markForCheck();
        },
        error: () => {
          this.shippingRates = [];
          this.shippingQuoteError = 'No se pudo calcular el envío.';
          this.cdr.markForCheck();
        }
      });
  }

  private buildShippingItems(): ShippingQuoteItem[] {
    const products = this.dashboardControl.products ?? [];
    const items: ShippingQuoteItem[] = [];
    for (const item of this.cartItems) {
      const product = products.find((p) => p.id === this.extractProductId(item.id));
      items.push({
        weightKg: product ? (Number(product.weightKg) || 0.5) : 0.5,
        lengthCm: product ? (Number(product.lengthCm) || 20) : 20,
        widthCm: product ? (Number(product.widthCm) || 15) : 15,
        heightCm: product ? (Number(product.heightCm) || 10) : 10,
        quantity: item.qty,
      });
    }
    return items.length ? items : [{ weightKg: 0.5, lengthCm: 20, widthCm: 15, heightCm: 10, quantity: 1 }];
  }

  showSummary(): void {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      this.scrollToSection('resumen-carrito');
      return;
    }
    this.isSummaryOpen = true;
  }

  closeSummary(): void {
    this.isSummaryOpen = false;
  }

  showDetails(): void {
    this.isSummaryOpen = false;
    this.scrollToSection('detalle-carrito');
  }

  private updateCountdown(): void {
    // Paquete G · ronda 26 (propuesta 29), montado en la integración.
    // Un solo origen del corte: el del servidor. El respaldo local caía al
    // último día del mes y por eso el carrito decía 26 días donde el panel
    // decía 21, en el mismo minuto. `getCountdownLabel()` nunca devuelve
    // cadena vacía: sin sesión usa los mismos ajustes publicados.
    this.cartControl.updateCountdown(this.dashboardControl.getCountdownLabel());
  }

  /** "Corte del mes para comisiones y descuento": Ernesto preguntó de qué era. */
  get cutoffLabel(): string {
    return this.dashboardControl.getCutoffLabel();
  }

  /** La fecha en letras junto al reloj: "lunes 25 de marzo de 2027, 23:59". */
  get cutoffDateText(): string {
    return this.dashboardControl.getCutoffDateText();
  }

  /** Tasa vigente para el desglose de IVA del resumen (§3.1). */
  get vatRate(): number {
    return this.plan?.iva?.tasa ?? 0.16;
  }

  get vatLabel(): string {
    return this.plan?.iva?.etiqueta || 'IVA';
  }

  /** El envío que ya está dentro del total; 0 mientras no se haya elegido.
   *
   *  Tiene que ser **el mismo** que suma `total`: con la tarifa de la cotización
   *  elegida, `this.shipping` vale 0 y el desglose recibía envío 0, así que la
   *  nota decía "Los precios ya incluyen IVA." y se callaba que el envío va
   *  dentro de la base, justo lo contrario de lo que dice el recibo del pedido. */
  get shippingInTotal(): number {
    if (this.deliveryType === 'pickup' || this.isShippingFree || this.totalLabel !== 'Total') {
      return 0;
    }
    const cotizado = this.selectedShippingRate !== null ? this.selectedShippingRate.displayPrice : this.shipping;
    return Number(cotizado) || 0;
  }

  private get projectedDiscountPercentValue(): number {
    return this.dashboardControl.getProjectedDiscountPercent(this.subtotal);
  }

  private discountLevelLabelByPercent(pct: number): string {
    // Los niveles van con los tramos del plan (10/20/30/40%); antes el 20% se llamaba "Nivel base".
    if (pct >= 40) {
      return 'Nivel 4';
    }
    if (pct >= 30) {
      return 'Nivel 3';
    }
    if (pct >= 20) {
      return 'Nivel 2';
    }
    if (pct >= 10) {
      return 'Nivel 1';
    }
    return 'Sin descuento';
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    this.toastTimeout = window.setTimeout(() => {
      this.isToastVisible = false;
    }, 2200);
  }

  private triggerAddedFade(itemId: string): void {
    if (!itemId) {
      return;
    }
    if (this.addFadeRestartTimeout) {
      window.clearTimeout(this.addFadeRestartTimeout);
    }
    if (this.addFadeTimeout) {
      window.clearTimeout(this.addFadeTimeout);
    }
    this.lastAddedItemId = '';
    this.addFadeRestartTimeout = window.setTimeout(() => {
      this.lastAddedItemId = itemId;
      this.cdr.markForCheck();
      this.addFadeTimeout = window.setTimeout(() => {
        if (this.lastAddedItemId === itemId) {
          this.lastAddedItemId = '';
          this.cdr.markForCheck();
        }
      }, 600);
    }, 0);
  }

  private scrollToSection(id: string): void {
    const section = document.getElementById(id);
    if (!section) {
      return;
    }
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  private focusFirstMissingDeliveryField(): void {
    const requiredFields: Array<{ hasError: boolean; name: string }> = [
      { hasError: this.deliveryFieldErrors.deliveryStreet, name: 'deliveryStreet' },
      { hasError: this.deliveryFieldErrors.deliveryNumber, name: 'deliveryNumber' },
      { hasError: this.deliveryFieldErrors.deliveryCity, name: 'deliveryCity' },
      { hasError: this.deliveryFieldErrors.deliveryPostalCode, name: 'deliveryPostalCode' },
      { hasError: this.deliveryFieldErrors.deliveryState, name: 'deliveryState' },
      { hasError: this.deliveryFieldErrors.deliveryCountry, name: 'deliveryCountry' }
    ];

    const missingField = requiredFields.find((field) => field.hasError);
    if (!missingField) {
      return;
    }

    window.setTimeout(() => {
      const selector = `[name="${missingField.name}"]`;
      const field = document.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(selector);
      if (!field) {
        return;
      }
      field.scrollIntoView({ behavior: 'smooth', block: 'center' });
      field.focus();
    }, 180);
  }

  onDeliveryFieldChange(
    field: 'deliveryStreet' | 'deliveryNumber' | 'deliveryCity' | 'deliveryPostalCode' | 'deliveryState' | 'deliveryCountry',
    value: string
  ): void {
    const normalizedIncomingValue = String(value ?? '');

    if (field === 'deliveryPostalCode') {
      const sanitizedPostalCode = normalizedIncomingValue.replace(/\D/g, '').slice(0, 5);
      this.deliveryPostalCode = sanitizedPostalCode;
      value = sanitizedPostalCode;
    } else {
      this.assignDeliveryFieldValue(field, normalizedIncomingValue);
      value = normalizedIncomingValue;
    }

    if (field === 'deliveryStreet' || field === 'deliveryNumber' || field === 'deliveryCity') {
      this.deliveryAddress = this.buildDeliveryAddressLine();
    }

    const normalizedValue = String(value ?? '').trim();
    if (field === 'deliveryPostalCode') {
      this.deliveryFieldErrors[field] = !/^\d{5}$/.test(normalizedValue);
    } else if (field === 'deliveryState') {
      this.deliveryFieldErrors[field] = !ESTADOS_MX_CODES.has(normalizedValue);
    } else {
      this.deliveryFieldErrors[field] = !normalizedValue;
    }
    // El envío se cotiza solo con el CP (propuesta 31): los demás campos ya no disparan consultas.
    if (field === 'deliveryPostalCode') {
      this.scheduleShippingQuote();
    }
    if (field === 'deliveryCity' || field === 'deliveryState') {
      this.scheduleCheckoutRefresh();
    }
  }

  // ── Paquete C · ronda 26 · propuesta 3: contacto del pedido ──
  onContactFieldChange(field: 'deliveryName' | 'deliveryPhone' | 'deliveryEmail', value: string): void {
    const limpio = String(value ?? '');
    if (field === 'deliveryName') {
      this.deliveryName = limpio;
    } else if (field === 'deliveryPhone') {
      this.deliveryPhone = limpio;
    } else {
      this.deliveryEmail = limpio;
    }
    if (this.contactFieldErrors[field]) {
      this.validarContacto();
    }
  }

  /** Marca en cada campo lo que falta y devuelve si el contacto del pedido está completo. */
  private validarContacto(): boolean {
    const errores: Record<'deliveryName' | 'deliveryPhone' | 'deliveryEmail', string> = {
      deliveryName: '',
      deliveryPhone: '',
      deliveryEmail: ''
    };
    if (!this.resolveDeliveryName()) {
      errores.deliveryName = 'Escribe el nombre de quien recibe el pedido.';
    }
    const telefono = this.resolveDeliveryPhone().replace(/[^\d]/g, '');
    if (telefono.length < 10) {
      errores.deliveryPhone = 'Escribe un teléfono de 10 dígitos: ahí te avisamos si algo pasa con tu pedido.';
    }
    if (this.isGuest && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.deliveryEmail.trim())) {
      errores.deliveryEmail = 'Escribe tu correo: ahí te avisamos del pago, el envío y la entrega.';
    }
    this.contactFieldErrors = errores;
    return !errores.deliveryName && !errores.deliveryPhone && !errores.deliveryEmail;
  }

  /** Lleva el foco al primer campo de contacto con error (el aviso al fondo de la página no se veía). */
  private focusFirstMissingContactField(): void {
    const orden: Array<'deliveryName' | 'deliveryPhone' | 'deliveryEmail'> = ['deliveryName', 'deliveryPhone', 'deliveryEmail'];
    const pendiente = orden.find((campo) => this.contactFieldErrors[campo]);
    if (!pendiente) {
      return;
    }
    window.setTimeout(() => {
      const campo = document.querySelector<HTMLInputElement>(`[name="${pendiente}"]`);
      if (!campo) {
        return;
      }
      campo.scrollIntoView({ behavior: 'smooth', block: 'center' });
      campo.focus();
    }, 180);
  }

  private assignDeliveryFieldValue(
    field: 'deliveryStreet' | 'deliveryNumber' | 'deliveryCity' | 'deliveryPostalCode' | 'deliveryState' | 'deliveryCountry',
    value: string
  ): void {
    switch (field) {
      case 'deliveryStreet':
        this.deliveryStreet = value;
        return;
      case 'deliveryNumber':
        this.deliveryNumber = value;
        return;
      case 'deliveryCity':
        this.deliveryCity = value;
        return;
      case 'deliveryPostalCode':
        this.deliveryPostalCode = value;
        return;
      case 'deliveryState':
        this.deliveryState = value;
        return;
      case 'deliveryCountry':
        this.deliveryCountry = value;
        return;
    }
  }

  selectShippingAddress(addressId: string): void {
    const selected = this.shippingAddresses.find((entry) => entry.id === addressId);
    if (!selected) {
      return;
    }
    this.selectedShippingAddressId = selected.id;
    this.shippingAddressLabel = selected.label || '';
    this.saveShippingAddress = false;
    this.applyShippingAddress(selected);
  }

  startNewShippingAddress(): void {
    this.selectedShippingAddressId = '';
    this.shippingAddressLabel = '';
    this.saveShippingAddress = true;
    this.deliveryStreet = '';
    this.deliveryNumber = '';
    this.deliveryAddress = '';
    this.deliveryCity = '';
    this.deliveryPostalCode = '';
    this.deliveryState = '';
    this.deliveryCountry = 'MX';
    this.deliveryBetweenStreets = '';
    this.deliveryReferences = '';
    this.deliveryFieldErrors = {
      deliveryStreet: false,
      deliveryNumber: false,
      deliveryCity: false,
      deliveryPostalCode: false,
      deliveryState: false,
      deliveryCountry: false
    };
    this.shippingRates = [];
    this.selectedShippingRate = null;
    this.shippingQuoteError = '';
  }

  private setDeliveryFieldErrors(
    values: Record<'deliveryStreet' | 'deliveryNumber' | 'deliveryCity' | 'deliveryPostalCode' | 'deliveryState' | 'deliveryCountry', string>
  ): boolean {
    let valid = true;
    (Object.keys(values) as Array<'deliveryStreet' | 'deliveryNumber' | 'deliveryCity' | 'deliveryPostalCode' | 'deliveryState' | 'deliveryCountry'>).forEach((field) => {
      const normalizedValue = values[field].trim();
      const hasError = field === 'deliveryPostalCode'
        ? !/^\d{5}$/.test(normalizedValue)
        : field === 'deliveryState'
          ? !ESTADOS_MX_CODES.has(normalizedValue)
          : !normalizedValue;
      this.deliveryFieldErrors[field] = hasError;
      if (hasError) {
        valid = false;
      }
    });
    return valid;
  }

  private collectCartTags(products: DashboardProduct[]): Set<string> {
    const tags = new Set<string>();
    for (const item of this.cartItems) {
      const match = products.find((product) => product.id === this.extractProductId(item.id));
      const rawTags = match?.tags?.length ? match.tags : match?.badge ? [match.badge] : item.note ? [item.note] : [];
      this.normalizeTags(rawTags).forEach((tag) => tags.add(tag));
    }
    return tags;
  }

  private normalizeTags(tags: string[]): string[] {
    return tags
      .map((tag) => tag.trim().toLowerCase())
      .filter((tag) => Boolean(tag));
  }

  private buildCartItem(product: DashboardProduct): CartItem {
    return {
      id: product.id,
      name: product.name,
      price: product.price,
      qty: 1,
      note: product.badge || '',
      img: product.img || ''
    };
  }

  setDeliveryType(type: 'delivery' | 'pickup'): void {
    this.deliveryType = type;
    if (type === 'delivery') {
      this.fetchShippingRates();
    } else {
      this.loadPickupStocks();
    }
    this.cdr.markForCheck();
  }

  /**
   * Sucursales para recoger: solo las de la ciudad/estado capturados y con existencia
   * de todo el carrito (Patricia veía "Recoger en sucursal" desde Mérida cuando la única
   * sucursal está en CDMX; Claudia pagó y el mostrador no tenía el producto).
   */
  private loadPickupStocks(): void {
    const city = this.deliveryCity.trim();
    const state = this.deliveryState.trim();
    const items = this.cartItems.map((item) => ({ productId: this.extractProductId(item.id), quantity: item.qty }));
    const key = JSON.stringify({ city, state, items });
    if (key === this.lastPickupQueryKey && !this.isLoadingPickupStocks) {
      return;
    }
    this.lastPickupQueryKey = key;
    this.isLoadingPickupStocks = true;
    this.checkout.sucursalesRecoger({ city: city || undefined, state: state || undefined, items }).subscribe({
      next: (respuesta) => {
        this.pickupOptions = respuesta.stocks ?? [];
        this.pickupAvailable = Boolean(respuesta.available);
        this.pickupCities = respuesta.cities ?? [];
        this.pickupLocationGiven = Boolean(respuesta.locationGiven);
        this.pickupStocks = this.normalizePickupStocks(
          this.pickupOptions.filter((s) => s.canPickup).map((s) => ({ id: s.id, name: s.name, location: s.location || s.city || '' }))
        );
        this.selectedPickupStockId = this.resolveSelectedPickupStockId(this.pickupStocks, this.selectedPickupStockId);
        if (!this.selectedPickupStockId && this.pickupStocks.length === 1) {
          this.selectedPickupStockId = this.pickupStocks[0].id;
        }
        if (this.deliveryType === 'pickup' && !this.pickupChoiceVisible) {
          // La opción dejó de aplicar (cambió la ciudad o el carrito): se vuelve a envío sin perder nada.
          this.deliveryType = 'delivery';
          this.showToast(this.pickupUnavailableNote || 'Recoger en sucursal ya no está disponible: te lo enviamos a domicilio.');
        }
        this.isLoadingPickupStocks = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingPickupStocks = false;
        this.lastPickupQueryKey = '';
        this.cdr.markForCheck();
      }
    });
  }

  private resolveSelectedPickupStockId(stocks: Array<{ id: string; name: string; location: string }>, selectedId: unknown): string {
    const normalizedId = this.normalizePickupStockId(selectedId);
    const matchedStock = stocks.find((stock) => this.normalizePickupStockId(stock.id) === normalizedId);
    return matchedStock ? this.normalizePickupStockId(matchedStock.id) : '';
  }

  private normalizePickupStocks(stocks: Array<{ id: string; name: string; location: string }>): Array<{ id: string; name: string; location: string }> {
    return stocks.reduce<Array<{ id: string; name: string; location: string }>>((acc, stock) => {
      const id = this.normalizePickupStockId(stock?.id);
      const name = typeof stock?.name === 'string' ? stock.name.trim() : '';
      const location = typeof stock?.location === 'string' ? stock.location.trim() : '';

      if (!id || !name || !location) {
        return acc;
      }

      acc.push({ id, name, location });
      return acc;
    }, []);
  }

  private normalizePickupStockId(value: unknown): string {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return String(value);
    }

    if (typeof value !== 'string') {
      return '';
    }

    return value.trim();
  }

  private prefillCustomerAddressFromDashboard(): void {
    const user = this.authService.currentUser;
    if (!user?.userId || user.role !== 'cliente') {
      return;
    }
    const customer = this.dashboardControl.customer;
    if (!customer) {
      return;
    }

    this.deliveryName = this.deliveryName || customer.name || this.authService.currentUser?.name || '';
    this.deliveryPhone = this.deliveryPhone || customer.phone || '';
    this.shippingAddresses = [...this.dashboardControl.shippingAddresses];

    const defaultShippingAddress =
      this.shippingAddresses.find((entry) => entry.id === this.dashboardControl.defaultShippingAddressId) ||
      this.shippingAddresses.find((entry) => entry.isDefault) ||
      this.shippingAddresses[0];

    if (defaultShippingAddress) {
      this.selectedShippingAddressId = defaultShippingAddress.id;
      this.shippingAddressLabel = defaultShippingAddress.label || '';
      this.saveShippingAddress = false;
      this.applyShippingAddress(defaultShippingAddress);
    } else {
      this.deliveryStreet = this.deliveryStreet || customer.address || '';
      this.deliveryCity = this.deliveryCity || customer.city || '';
      this.deliveryAddress = this.deliveryAddress || this.buildDeliveryAddressLine() || customer.address || '';
      const resolvedState = customer.state || '';
      this.deliveryState = this.deliveryState || resolvedState;
      this.deliveryPostalCode = this.deliveryPostalCode || customer.postalCode || '';
      this.deliveryCountry = this.deliveryCountry || 'MX';
      this.saveShippingAddress = true;
      // Los errores se marcan al escribir o al pagar; antes salían en rojo sin tocar nada.
    }

    this.hasPrefilledDashboardAddress = true;
    this.cdr.markForCheck();
  }

  openGuestRegisterModal(): void {
    this.showGuestRegisterModal = true;
    this.guestRegisterFeedback = '';
    this.guestRegisterFeedbackType = '';
  }

  closeGuestRegisterModal(): void {
    this.showGuestRegisterModal = false;
    this.guestRegisterFeedback = '';
    this.guestRegisterFeedbackType = '';
  }

  submitGuestRegister(): void {
    if (this.isGuestRegisterSubmitting) {
      return;
    }
    if (!this.guestRegisterForm.firstName.trim() || !this.guestRegisterForm.apellidoPaterno.trim() || !this.guestRegisterForm.email || !this.guestRegisterForm.password) {
      this.guestRegisterFeedback = 'Completa los campos obligatorios.';
      this.guestRegisterFeedbackType = 'error';
      return;
    }
    if (this.guestRegisterForm.password !== this.guestRegisterForm.confirmPassword) {
      this.guestRegisterFeedback = 'Las contraseñas no coinciden.';
      this.guestRegisterFeedbackType = 'error';
      return;
    }

    const fullName = `${this.guestRegisterForm.firstName.trim()} ${this.guestRegisterForm.apellidoPaterno.trim()} ${this.guestRegisterForm.apellidoMaterno.trim()}`.trim();
    const payload = {
      name: fullName,
      email: this.guestRegisterForm.email.trim(),
      phone: this.guestRegisterForm.phone.trim() || undefined,
      password: this.guestRegisterForm.password,
      confirmPassword: this.guestRegisterForm.confirmPassword,
      referralToken: localStorage.getItem('leaderId') || undefined
    };

    this.isGuestRegisterSubmitting = true;
    this.api
      .createAccount(payload)
      .pipe(
        finalize(() => {
          this.isGuestRegisterSubmitting = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (response?.requiresEmailVerification) {
            this.guestRegisterForm = {
              firstName: '',
              apellidoPaterno: '',
              apellidoMaterno: '',
              email: '',
              phone: '',
              password: '',
              confirmPassword: ''
            };
            this.guestRegisterFeedback = '';
            this.guestRegisterFeedbackType = '';
            this.showGuestRegisterModal = false;
            this.showToast('Solo falta un paso, confirma tu cuenta desde tu correo electrónico.');
            return;
          }
          if (response?.customer) {
            this.authService.setUserFromCreateAccount(response.customer);
          }
          this.guestRegisterForm = {
            firstName: '',
            apellidoPaterno: '',
            apellidoMaterno: '',
            email: '',
            phone: '',
            password: '',
            confirmPassword: ''
          };
          this.showGuestRegisterModal = false;
          this.showToast('Cuenta creada. Bienvenido.');
          window.location.reload();
        },
        error: (error: any) => {
          const apiMessage =
            error?.error?.message || error?.error?.Error || error?.message || 'No se pudo crear la cuenta.';
          this.guestRegisterFeedback = apiMessage;
          this.guestRegisterFeedbackType = 'error';
        }
      });
  }

  private applyShippingAddress(address: CustomerShippingAddress): void {
    this.deliveryName = address.recipientName?.trim() || this.deliveryName || this.authService.currentUser?.name || '';
    this.deliveryPhone = address.phone?.trim() || this.deliveryPhone;
    this.deliveryStreet = address.street?.trim() || address.address?.trim() || '';
    this.deliveryNumber = address.number?.trim() || '';
    this.deliveryCity = address.city?.trim() || '';
    this.deliveryAddress = address.address?.trim() || this.buildDeliveryAddressLine();
    this.deliveryPostalCode = address.postalCode?.trim() || '';
    this.deliveryState = address.state?.trim() || '';
    this.deliveryCountry = address.country?.trim() || 'MX';
    this.deliveryBetweenStreets = address.betweenStreets?.trim() || '';
    this.deliveryReferences = address.references?.trim() || '';
    this.setDeliveryFieldErrors({
      deliveryStreet: this.deliveryStreet,
      deliveryNumber: this.deliveryNumber,
      deliveryCity: this.deliveryCity,
      deliveryPostalCode: this.deliveryPostalCode,
      deliveryState: this.deliveryState,
      deliveryCountry: this.deliveryCountry
    });
    this.fetchShippingRates();
    this.scheduleCheckoutRefresh();
  }

  private buildDeliveryAddressLine(): string {
    return [this.deliveryStreet.trim(), this.deliveryNumber.trim(), this.deliveryCity.trim()].filter(Boolean).join(', ');
  }

  private resolveDeliveryName(): string {
    return this.deliveryName.trim() || this.dashboardControl.customer?.name?.trim() || this.authService.currentUser?.name?.trim() || '';
  }

  private resolveDeliveryPhone(): string {
    return this.deliveryPhone.trim() || this.dashboardControl.customer?.phone?.trim() || '';
  }

  private resolveShippingAddressLabel(): string {
    const explicitLabel = this.shippingAddressLabel.trim();
    if (explicitLabel) {
      return explicitLabel;
    }
    const selected = this.shippingAddresses.find((entry) => entry.id === this.selectedShippingAddressId);
    return selected?.label?.trim() || '';
  }

  private resolveOrderCustomerId(): number | string {
    const rawUserId = String(this.authService.currentUser?.userId ?? '').trim();
    if (!rawUserId) {
      return 0;
    }
    const numericId = Number(rawUserId);
    return Number.isFinite(numericId) ? numericId : rawUserId;
  }
}
