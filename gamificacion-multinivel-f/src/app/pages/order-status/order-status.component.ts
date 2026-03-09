import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { AdminOrder } from '../../models/admin.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiOrderTimelineComponent } from '../../components/ui-order-timeline/ui-order-timeline.component';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-order-status',
  standalone: true,
  imports: [CommonModule, UiButtonComponent, UiOrderTimelineComponent],
  templateUrl: './order-status.component.html',
  styleUrl: './order-status.component.css'
})
export class OrderStatusComponent implements OnInit, OnDestroy {
  private readonly allowedStatuses = ['pending', 'paid', 'shipped', 'delivered'] as const;
  private pollingTimer: ReturnType<typeof setInterval> | null = null;
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
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) { }

  copyToClipboard(txt?: string) { if (txt) navigator.clipboard.writeText(txt); }

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
      this.redirectMessage = 'Tu operacion fue rechazada.';
    } else if (this.redirectStatus === 'pending' || this.redirectStatus === 'success') {
      this.redirectMessage = 'Tu operacion esta siendo procesada y validando por tu banco.';
    }

    this.orderId = this.orderReference || routeOrderId || this.paymentId;
    if (!this.paymentId && this.orderReference) {
      this.orderId = this.orderReference;
    }
    if (!this.orderId && !this.paymentId) {
      return;
    }

    if (this.orderId) {
      this.loadOrder(this.orderId);
      this.pollStatus(this.orderReference || this.paymentId || this.orderId);
    }

    if (this.redirectStatus === 'success') {
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
    this.pollStatus(lookupId);
    this.pollingTimer = setInterval(() => this.pollStatus(lookupId), 60000);
  }

  private stopSuccessPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  private pollStatus(lookupId: string): void {
    this.api.getOrderStatus(lookupId).subscribe({
      next: (statusData) => {
        const backendStatus = this.normalizeStatus(statusData?.status as AdminOrder['status']);
        const markedByWebhook = Boolean(statusData?.markedByWebhook);
        const backendOrderId = String(statusData?.orderId ?? '').trim();
        const shouldStop = markedByWebhook || ['paid', 'shipped', 'delivered'].includes(backendStatus);
        if (markedByWebhook) {
          this.redirectMessage = '';
        }
        const cutoffWindow = Boolean(statusData?.discountCutoffWindow);
        const cutoffCountdown = String(statusData?.discountCutoffCountdown ?? '').trim();
        if (cutoffWindow && cutoffCountdown) {
          this.cutoffCountdownMessage = `Tu descuento solo aplicara hasta el corte de mes. Tiempo restante: ${cutoffCountdown}`;
        } else {
          this.cutoffCountdownMessage = '';
        }

        if (backendOrderId && backendOrderId !== this.orderId) {
          this.orderId = backendOrderId;
          this.loadOrder(backendOrderId);
        }

        if (shouldStop) {
          this.stopSuccessPolling();
          if (backendOrderId && (!this.order || this.order.id !== backendOrderId)) {
            this.loadOrder(backendOrderId);
          }
        }
      },
      error: () => {}
    });
  }

  get statusLabel(): string {
    if (this.redirectStatus === 'failure') {
      return 'Operacion rechazada';
    }
    if ((this.redirectStatus === 'success' || this.redirectStatus === 'pending') && this.normalizeStatus(this.order?.status) === 'pending') {
      return 'Operacion en validacion';
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

  get orderTotal(): number {
    if (!this.order) {
      return 0;
    }
    const net = Number(this.order.netTotal ?? 0);
    if (Number.isFinite(net) && net > 0) {
      return net;
    }
    return Number(this.order.total ?? 0);
  }

  formatMoney(value: number): string {
    const amount = Number.isFinite(value) ? value : 0;
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      maximumFractionDigits: 0
    }).format(amount);
  }

  get displayOrderRef(): string {
    return this.orderReference || this.orderId || this.paymentId || '';
  }

  payWithMercadoPago(): void {
    const targetOrderId = String(this.order?.id || this.orderId || this.displayOrderRef || '').trim();
    if (!targetOrderId || this.isCheckoutLoading) {
      return;
    }

    this.checkoutError = '';
    this.isCheckoutLoading = true;
    this.api.createOrderCheckout(targetOrderId).subscribe({
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

