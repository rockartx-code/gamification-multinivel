import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
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
export class OrderStatusComponent implements OnInit {
  private readonly allowedStatuses = ['pending', 'paid', 'shipped', 'delivered'] as const;
  orderId = '';
  isLoading = false;
  order: AdminOrder | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) { }

  copyToClipboard(txt?: string) { if (txt) navigator.clipboard.writeText(txt); }

  ngOnInit(): void {
    this.orderId = this.route.snapshot.paramMap.get('idOrden') ?? '';
    if (!this.orderId) {
      return;
    }
    this.isLoading = true;
    this.api.getOrder(this.orderId).subscribe({
      next: (order) => {
        this.order = order ?? null;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  get statusLabel(): string {
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
    const status = this.normalizeStatus(this.order?.status);
    if (status === 'paid') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200';
    }
    if (status === 'shipped') {
      return 'border-blue-400/30 bg-blue-500/10 text-blue-200';
    }
    if (status === 'delivered') {
      return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200';
    }
    return 'border-yellow-400/30 bg-yellow-400/10 text-yellow-200';
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

  private normalizeStatus(status?: AdminOrder['status'] | string | null): (typeof this.allowedStatuses)[number] {
    const normalized = typeof status === 'string' ? status.trim().toLowerCase() : '';
    if (normalized && this.allowedStatuses.includes(normalized as (typeof this.allowedStatuses)[number])) {
      return normalized as (typeof this.allowedStatuses)[number];
    }
    return 'pending';
  }
}
