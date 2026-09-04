import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';

import { AdminOrder } from '../../models/admin.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiOrderTimelineComponent } from '../../components/ui-order-timeline/ui-order-timeline.component';
import { UiAhorroSocioComponent } from '../../components/ui-ahorro-socio/ui-ahorro-socio.component';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-order-status',
  standalone: true,
  imports: [CommonModule, RouterModule, UiButtonComponent, UiOrderTimelineComponent, UiAhorroSocioComponent],
  templateUrl: './order-status.component.html',
  styleUrl: './order-status.component.css'
})
export class OrderStatusComponent implements OnInit, OnDestroy {
  private readonly allowedStatuses = ['pending', 'paid', 'shipped', 'delivered', 'cancelled', 'en_devolucion', 'devuelto_validado', 'devolucion_rechazada', 'refunded'] as const;
  private pollingTimer: ReturnType<typeof setTimeout> | null = null;
  // ── Paquete C · ronda 26 · propuesta 13 ──
  /** Se pregunta pronto y luego cada vez menos: 5 s, 10 s, 20 s y 30 s. Antes era un minuto fijo,
   *  y Ernesto y Mariana se quedaron mirando una pantalla en blanco con $609 y $829 en juego. */
  private readonly pollingDelaysMs = [5000, 10000, 20000, 30000];
  private pollingIndex = 0;
  /** Se agotaron los reintentos y el pago sigue sin confirmarse: se dice qué hacer. */
  paymentConfirmTimedOut = false;
  orderId = '';
  orderReference = '';
  paymentId = '';
  redirectStatus: 'success' | 'failure' | 'pending' | '' = '';
  redirectMessage = '';
  cutoffCountdownMessage = '';
  checkoutError = '';
  isCheckoutLoading = false;
  isLoading = false;
  order: AdminOrder | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) { }

  copyToClipboard(txt?: string) { if (txt) navigator.clipboard.writeText(txt); }

  // ── Paquete B: ahorro como socia guardado en el pedido ───────────────────
  get partnerSavingsVisible(): boolean {
    const modo = this.order?.partnerMode;
    return modo === 'cliente' || modo === 'invitado';
  }

  get partnerSavingsMode(): 'cliente' | 'invitado' {
    return this.order?.partnerMode === 'invitado' ? 'invitado' : 'cliente';
  }

  goToModoSocio(): void {
    void this.router.navigate(['/modo-socio'], { queryParams: { desde: 'orden', id: this.order?.id ?? this.orderId } });
  }

  ngOnInit(): void {
    const routeOrderId = this.normalizeLookupValue(this.route.snapshot.paramMap.get('idOrden'));
    const query = this.route.snapshot.queryParamMap;
    this.paymentId = this.firstValidLookup(
      query.get('payment_id'),
      query.get('collection_id')
    );
    this.orderReference = this.firstValidLookup(
      query.get('external_reference'),
      query.get('orderId')
    );
    this.redirectStatus = this.normalizeRedirectStatusFromList(
      ...query.getAll('status'),
      query.get('collection_status')
    );

    if (this.redirectStatus === 'failure') {
      this.redirectMessage = 'Tu operación fue rechazada. No se te cobró nada: puedes volver a intentarlo.';
    } else if (this.redirectStatus === 'pending' || this.redirectStatus === 'success') {
      this.redirectMessage = 'Tu operación está siendo procesada y validándose con tu banco.';
    }

    this.orderId = this.orderReference || routeOrderId || this.paymentId;
    if (!this.paymentId && this.orderReference) {
      this.orderId = this.orderReference;
    }
    if (!this.orderId && !this.paymentId) {
      return;
    }

    if (this.orderId) {
      this.loadOrder(this.orderReference || this.paymentId || this.orderId);
    }

    if (this.redirectStatus === 'success' || this.redirectStatus === 'pending') {
      this.startSuccessPolling();
    }
  }

  ngOnDestroy(): void {
    this.stopSuccessPolling();
  }

  private loadOrder(id: string): void {
    this.isLoading = true;
    this.api.getOrder(id).subscribe({
      next: (order) => {
        this.order = order ?? null;
        if (order?.id) {
          this.orderId = order.id;
        }
        this.syncOrderStatusState(order);
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  private startSuccessPolling(): void {
    const lookupId = this.orderReference || this.paymentId || this.orderId;
    if (!lookupId) {
      return;
    }
    this.pollingIndex = 0;
    this.paymentConfirmTimedOut = false;
    this.scheduleNextPoll(lookupId);
  }

  private scheduleNextPoll(lookupId: string): void {
    const espera = this.pollingDelaysMs[this.pollingIndex];
    if (espera === undefined) {
      // Se acabaron los reintentos: en vez de callar, se dice qué hacer.
      this.paymentConfirmTimedOut = true;
      this.cdr.markForCheck();
      return;
    }
    this.pollingIndex += 1;
    this.pollingTimer = setTimeout(() => {
      this.pollingTimer = null;
      this.loadOrder(lookupId);
      if (this.isConfirmingPayment) {
        this.scheduleNextPoll(lookupId);
      }
    }, espera);
  }

  private stopSuccessPolling(): void {
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  /** Volvimos de la pasarela y el pedido todavía no está pagado: no hay nada que cobrar otra vez. */
  get isConfirmingPayment(): boolean {
    if (this.redirectStatus !== 'success' && this.redirectStatus !== 'pending') {
      return false;
    }
    if (this.order?.markedByWebhook) {
      return false;
    }
    return this.normalizeStatus(this.order?.status) === 'pending';
  }

  /** Mientras se confirma no se pinta el resumen: un total en $0 al volver de pagar asusta. */
  get isSummaryVisible(): boolean {
    return Boolean(this.order) && !this.isLoading;
  }

  private syncOrderStatusState(order: AdminOrder | null | undefined): void {
    const backendStatus = this.normalizeStatus(order?.status);
    const markedByWebhook = Boolean(order?.markedByWebhook);
    const shouldStop = markedByWebhook || ['paid', 'shipped', 'delivered'].includes(backendStatus);
    if (shouldStop) {
      this.redirectMessage = '';
      this.paymentConfirmTimedOut = false;
    }

    const cutoffWindow = Boolean(order?.discountCutoffWindow);
    const cutoffCountdown = String(order?.discountCutoffCountdown ?? '').trim();
    if (cutoffWindow && cutoffCountdown) {
      this.cutoffCountdownMessage = `Tu descuento solo aplicara hasta el corte de mes. Tiempo restante: ${cutoffCountdown}`;
    } else {
      this.cutoffCountdownMessage = '';
    }

    if (shouldStop) {
      this.stopSuccessPolling();
    }
  }

  get statusLabel(): string {
    if (this.redirectStatus === 'failure') {
      return 'Operación rechazada';
    }
    if (this.isConfirmingPayment) {
      return 'Estamos confirmando tu pago';
    }
    const status = this.normalizeStatus(this.order?.status);
    if (status === 'paid') {
      return 'Pago registrado';
    }
    if (status === 'shipped') {
      return 'Pedido enviado';
    }
    if (status === 'delivered') {
      return 'Pedido entregado';
    }
    if (status === 'cancelled') {
      return 'Cancelado';
    }
    if (status === 'en_devolucion') {
      return 'En devolución';
    }
    if (status === 'devuelto_validado') {
      return 'Devolución aprobada';
    }
    if (status === 'devolucion_rechazada') {
      return 'Devolución rechazada';
    }
    if (status === 'refunded') {
      // Un pedido reembolsado se mostraba como "Pago pendiente".
      return 'Reembolsado';
    }
    return 'Pago pendiente';
  }

  get statusClass(): string {
    if (this.redirectStatus === 'failure') {
      return 'border-red-400/30 bg-red-500/10 text-main';
    }
    const status = this.normalizeStatus(this.order?.status);
    if (status === 'paid') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-main';
    }
    if (status === 'shipped') {
      return 'border-blue-400/30 bg-blue-500/10 text-main';
    }
    if (status === 'delivered') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-main';
    }
    if (status === 'cancelled') {
      return 'border-red-400/30 bg-red-500/10 text-main';
    }
    if (status === 'en_devolucion') {
      return 'border-amber-400/30 bg-amber-400/10 text-main';
    }
    if (status === 'devuelto_validado') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-main';
    }
    if (status === 'devolucion_rechazada') {
      return 'border-red-400/30 bg-red-500/10 text-main';
    }
    if (status === 'refunded') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-main';
    }
    return 'border-yellow-400/30 bg-yellow-400/10 text-main';
  }

  get statusValue(): (typeof this.allowedStatuses)[number] {
    return this.normalizeStatus(this.order?.status);
  }

  get orderSubtotal(): number {
    if (!this.order) {
      return 0;
    }
    const gross = Number(this.order.grossSubtotal ?? 0);
    if (Number.isFinite(gross) && gross > 0) {
      return gross;
    }
    const net = Number(this.order.netTotal ?? 0);
    const discount = Number(this.order.discountAmount ?? 0);
    if (Number.isFinite(net) && net > 0) {
      return Math.max(0, net + discount);
    }
    return Number(this.order.total ?? 0);
  }

  get orderDiscount(): number {
    if (!this.order) {
      return 0;
    }
    const discount = Number(this.order.discountAmount ?? 0);
    return Number.isFinite(discount) ? discount : 0;
  }

  get orderDiscountPercent(): number {
    if (!this.order) {
      return 0;
    }
    const rate = Number(this.order.discountRate ?? 0);
    if (Number.isFinite(rate) && rate > 0) {
      return Math.round(rate * 100);
    }
    const subtotal = this.orderSubtotal;
    if (subtotal <= 0 || this.orderDiscount <= 0) {
      return 0;
    }
    return Math.round((this.orderDiscount / subtotal) * 100);
  }

  /** Costo de envío cobrado en el pedido (0 si no aplica). */
  get orderShipping(): number {
    const raw = Number((this.order as { shippingCost?: number } | null)?.shippingCost ?? 0);
    return Number.isFinite(raw) && raw > 0 ? raw : 0;
  }

  get orderShippingCarrier(): string {
    return String((this.order as { shippingCarrier?: string } | null)?.shippingCarrier ?? '');
  }

  get orderTotal(): number {
    if (!this.order) {
      return 0;
    }
    // La lista decía "$829" y este detalle "$700": aquí faltaba sumar el envío.
    const total = Number(this.order.total ?? 0);
    if (Number.isFinite(total) && total > 0) {
      return total;
    }
    const net = Number(this.order.netTotal ?? 0);
    if (Number.isFinite(net) && net > 0) {
      return net + this.orderShipping;
    }
    return 0;
  }

  formatMoney(value: number): string {
    const amount = Number.isFinite(value) ? value : 0;
    // Sin centavos cuando el importe es entero; con dos cuando no lo es
    // ("$1,376.40", no "$1,376.4" ni "$1,376").
    const cents = Number.isInteger(Math.round(amount * 100) / 100) ? 0 : 2;
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: cents,
      maximumFractionDigits: cents
    }).format(amount);
  }

  get displayOrderRef(): string {
    return this.orderReference || this.orderId || this.paymentId || '';
  }

  get canCancel(): boolean {
    const s = this.normalizeStatus(this.order?.status);
    return s === 'paid' || s === 'pending';
  }

  /** Ya hay una devolución en curso o resuelta: no tiene sentido pedir "solicita una devolución". */
  get inReturnFlow(): boolean {
    const s = this.order?.status;
    return ['en_devolucion', 'devuelto_validado', 'devolucion_rechazada', 'refunded'].includes(s as string);
  }

  get cancelBlocked(): boolean {
    const s = this.normalizeStatus(this.order?.status);
    return ['shipped', 'delivered', 'en_devolucion', 'devuelto_validado', 'devolucion_rechazada', 'refunded', 'cancelled'].includes(s as string);
  }

  get canRequestReturn(): boolean {
    return this.normalizeStatus(this.order?.status) === 'delivered';
  }

  navigateToCancel(): void {
    if (this.orderId) {
      void this.router.navigate(['/orden', this.orderId, 'cancelar']);
    }
  }

  navigateToReturn(): void {
    if (this.orderId) {
      void this.router.navigate(['/orden', this.orderId, 'devolucion']);
    }
  }

  payWithMercadoPago(): void {
    const targetOrderId = String(this.order?.id || this.orderId || this.displayOrderRef || '').trim();
    if (!targetOrderId || this.isCheckoutLoading) {
      return;
    }

    this.checkoutError = '';
    this.isCheckoutLoading = true;
    // Sin `successUrl` la pasarela no sabía a dónde regresar y el mensaje "estamos confirmando tu
    // pago", que ya estaba escrito, no se encendía nunca. El cuerpo manda mano sobre la
    // configuración del servidor, así que aquí se le dice a dónde volver.
    const regreso = this.buildReturnUrl(targetOrderId);
    this.api.createOrderCheckout(targetOrderId, regreso ? {
      successUrl: regreso,
      pendingUrl: regreso,
      failureUrl: regreso
    } : {}).subscribe({
      next: (response) => {
        const checkout = response?.checkout;
        const initPoint = String(checkout?.initPoint || checkout?.sandboxInitPoint || '').trim();
        if (!initPoint) {
          this.checkoutError = 'No se pudo iniciar el pago en MercadoPago.';
          this.isCheckoutLoading = false;
          this.cdr.markForCheck();
          return;
        }
        window.location.href = initPoint;
      },
      error: () => {
        this.checkoutError = 'No se pudo iniciar el pago en MercadoPago.';
        this.isCheckoutLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /** URL de esta misma pantalla, para que la pasarela devuelva a la persona a su pedido. */
  private buildReturnUrl(orderId: string): string {
    if (typeof window === 'undefined') {
      return '';
    }
    const { origin, pathname } = window.location;
    if (!origin) {
      return '';
    }
    return `${origin}${pathname}#/orden/${encodeURIComponent(orderId)}`;
  }

  private normalizeRedirectStatusFromList(...candidates: Array<string | null>): 'success' | 'failure' | 'pending' | '' {
    for (const value of candidates) {
      const normalized = this.normalizeLookupValue(value).toLowerCase();
      if (normalized === 'success' || normalized === 'failure' || normalized === 'pending') {
        return normalized;
      }
    }
    return '';
  }

  private firstValidLookup(...candidates: Array<string | null>): string {
    for (const value of candidates) {
      const normalized = this.normalizeLookupValue(value);
      if (normalized) {
        return normalized;
      }
    }
    return '';
  }

  private normalizeLookupValue(value: string | null): string {
    const normalized = String(value ?? '').trim();
    if (!normalized) {
      return '';
    }
    const lowered = normalized.toLowerCase();
    if (lowered === 'null' || lowered === 'undefined') {
      return '';
    }
    if (/^\{.+\}$/.test(normalized)) {
      return '';
    }
    return normalized;
  }

  private normalizeStatus(status?: AdminOrder['status'] | string | null): (typeof this.allowedStatuses)[number] {
    const normalized = typeof status === 'string' ? status.trim().toLowerCase() : '';
    if (normalized && this.allowedStatuses.includes(normalized as (typeof this.allowedStatuses)[number])) {
      return normalized as (typeof this.allowedStatuses)[number];
    }
    return 'pending';
  }
}

