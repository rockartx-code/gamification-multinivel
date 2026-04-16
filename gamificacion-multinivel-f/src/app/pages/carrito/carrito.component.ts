import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, Subscription } from 'rxjs';
import { Router, RouterLink } from '@angular/router';

import { ESTADOS_MX_CODES, ESTADOS_MX_OPTIONS } from '../../constants/states-mx';
import { CartItem } from '../../models/cart.model';
import { DashboardGoal, DashboardProduct } from '../../models/user-dashboard.model';
import { AdminOrderItem, CustomerShippingAddress, ShippingRate, ShippingQuoteItem } from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CartControlService } from '../../services/cart-control.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { GoalControlService } from '../../services/goal-control.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';
import { UiProductCardComponent } from '../../components/ui-product-card/ui-product-card.component';
import { UiGoalProgressComponent } from '../../components/ui-goal-progress/ui-goal-progress.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, UiButtonComponent, UiFormFieldComponent, UiProductCardComponent, UiGoalProgressComponent, UiModalComponent],
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
    private readonly router: Router
  ) {}

  isToastVisible = false;
  toastMessage = 'Actualizado.';
  isSummaryOpen = false;
  isPlacingOrder = false;
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
  private addFadeTimeout?: number;
  private addFadeRestartTimeout?: number;
  private hasPrefilledDashboardAddress = false;
  suggestedProducts: DashboardProduct[] = [];

  ngOnInit(): void {
    this.cartControl.load().subscribe();
    this.refreshSuggestedProducts();
    this.dataSub = this.cartControl.data$.subscribe(() => {
      this.refreshSuggestedProducts();
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
    this.dashboardSub?.unsubscribe();
    this.shippingQuoteSub?.unsubscribe();
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

    const cartIds = new Set(this.cartItems.map((item) => item.id));
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

  get hasSavedShippingAddresses(): boolean {
    return this.shippingAddresses.length > 0;
  }

  get isShippingQuoteReady(): boolean {
    return this.hasValidShippingQuoteFormData();
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
    if (pct >= 50) {
      return 'Nivel 3';
    }
    if (pct >= 40) {
      return 'Nivel 2';
    }
    if (pct >= 30) {
      return 'Nivel 1';
    }
    return 'Nivel base';
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

  get total(): number {
    if (this.deliveryType === 'pickup') {
      return Math.max(0, this.subtotal - this.discount);
    }
    const shippingCost = this.selectedShippingRate !== null ? this.selectedShippingRate.displayPrice : this.shipping;
    return Math.max(0, this.subtotal + shippingCost - this.discount);
  }

  get shippingLabel(): string {
    if (this.deliveryType === 'pickup') {
      return 'Gratis (recoger en sucursal)';
    }
    if (this.selectedShippingRate) {
      return this.formatMoney(this.selectedShippingRate.displayPrice);
    }
    return this.shipping === 0 ? 'Gratis' : this.formatMoney(this.shipping);
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
    return Math.max(0, remaining - this.subtotal);
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
    return Math.min(100, (this.subtotal / remaining) * 100);
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
    return this.cartControl.getQty(productId);
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
    if (this.deliveryType === 'pickup') {
      if (!pickupStockId) {
        this.selectedPickupStockId = '';
        this.showToast('Selecciona una sucursal para recoger tu pedido.');
        return;
      }
      if (!this.pickupPaymentMethod) {
        this.showToast('Selecciona un método de pago para continuar.');
        return;
      }
    }
    const user = this.authService.currentUser;
    const items: AdminOrderItem[] = this.cartItems.map((item) => ({
      productId: Number(item.id),
      name: item.name,
      price: item.price,
      quantity: item.qty
    }));
    let payload: Record<string, unknown>;
    if (this.deliveryType === 'pickup') {
      payload = {
        customerId: this.resolveOrderCustomerId(),
        customerName: user?.name || this.deliveryName.trim() || 'Cliente',
        status: 'pending' as const,
        items,
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
        shippingCost: this.selectedShippingRate?.displayPrice ?? undefined,
        deliveryType: 'delivery'
      };
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
          this.showToast('Orden creada. Redirigiendo...');
          this.router.navigate(['/orden', orderId]);
        },
        error: () => {
          this.showToast('No se pudo crear la orden.');
        }
      });
  }

  fetchShippingRates(): void {
    if (!this.hasValidShippingQuoteFormData()) {
      this.shippingRates = [];
      this.selectedShippingRate = null;
      this.shippingQuoteError = '';
      return;
    }
    const zipTo = this.deliveryPostalCode.trim();
    const items = this.buildShippingItems();
    this.isLoadingShippingRates = true;
    this.shippingQuoteError = '';
    this.shippingQuoteSub?.unsubscribe();
    this.shippingQuoteSub = this.api
      .getShippingQuote({
        zipTo,
        postalCode: zipTo,
        name: this.resolveDeliveryName(),
        recipientName: this.resolveDeliveryName(),
        phone: this.resolveDeliveryPhone(),
        street: this.deliveryStreet.trim(),
        number: this.deliveryNumber.trim(),
        address: this.buildDeliveryAddressLine(),
        city: this.deliveryCity.trim(),
        state: this.deliveryState.trim(),
        country: this.deliveryCountry.trim().toUpperCase(),
        items
      })
      .pipe(finalize(() => {
        this.isLoadingShippingRates = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (rates) => {
          console.log('Shipping rates received:', rates);
          this.shippingRates = rates;
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
      const product = products.find((p) => p.id === item.id);
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
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    lastDay.setHours(23, 59, 59, 999);
    const diff = Math.max(0, lastDay.getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    this.cartControl.updateCountdown(`${d}d ${h}h`);
  }

  private get projectedDiscountPercentValue(): number {
    return this.dashboardControl.getProjectedDiscountPercent(this.subtotal);
  }

  private discountLevelLabelByPercent(pct: number): string {
    if (pct >= 50) {
      return 'Nivel 3';
    }
    if (pct >= 40) {
      return 'Nivel 2';
    }
    if (pct >= 30) {
      return 'Nivel 1';
    }
    return 'Nivel base';
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
    this.fetchShippingRates();
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
      const match = products.find((product) => product.id === item.id);
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
    }
    this.cdr.markForCheck();
  }

  private loadPickupStocks(): void {
    this.isLoadingPickupStocks = true;
    this.api.listPickupStocks().subscribe({
      next: (stocks) => {
        const normalizedStocks = this.normalizePickupStocks(stocks);
        this.pickupStocks = normalizedStocks;
        this.selectedPickupStockId = this.resolveSelectedPickupStockId(normalizedStocks, this.selectedPickupStockId);
        if (!this.selectedPickupStockId && normalizedStocks.length === 1) {
          this.selectedPickupStockId = normalizedStocks[0].id;
        }
        this.isLoadingPickupStocks = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingPickupStocks = false;
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
      this.setDeliveryFieldErrors({
        deliveryStreet: this.deliveryStreet,
        deliveryNumber: this.deliveryNumber,
        deliveryCity: this.deliveryCity,
        deliveryPostalCode: this.deliveryPostalCode,
        deliveryState: this.deliveryState,
        deliveryCountry: this.deliveryCountry
      });
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
    if (!this.guestRegisterForm.firstName.trim() || !this.guestRegisterForm.apellidoPaterno.trim() || !this.guestRegisterForm.apellidoMaterno.trim() || !this.guestRegisterForm.email || !this.guestRegisterForm.password) {
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
  }

  private buildDeliveryAddressLine(): string {
    return [this.deliveryStreet.trim(), this.deliveryNumber.trim(), this.deliveryCity.trim()].filter(Boolean).join(', ');
  }

  private hasValidShippingQuoteFormData(): boolean {
    return Boolean(
      this.resolveDeliveryName() &&
      this.resolveDeliveryPhone() &&
      this.deliveryStreet.trim() &&
      this.deliveryNumber.trim() &&
      this.deliveryCity.trim() &&
      /^\d{5}$/.test(this.deliveryPostalCode.trim()) &&
      ESTADOS_MX_CODES.has(this.deliveryState.trim()) &&
      this.deliveryCountry.trim()
    );
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
