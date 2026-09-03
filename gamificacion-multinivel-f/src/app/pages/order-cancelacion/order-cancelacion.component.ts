import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AdminOrder, OrderCancelResponse } from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';

@Component({
  selector: 'app-order-cancelacion',
  standalone: true,
  imports: [CommonModule, RouterLink, UiButtonComponent],
  templateUrl: './order-cancelacion.component.html'
})
export class OrderCancelacionComponent implements OnInit {
  orderId = '';
  order: AdminOrder | null = null;
  isLoading = true;
  isCancelling = false;
  cancelled = false;
  /** Lo que el servidor guardó al cancelar (folio, estado nuevo, si queda reembolso pendiente). */
  cancelResult: OrderCancelResponse | null = null;
  error = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.orderId = this.route.snapshot.paramMap.get('idOrden') ?? '';
    if (!this.orderId) {
      void this.router.navigate(['/dashboard']);
      return;
    }
    this.api.getOrder(this.orderId)
      .pipe(finalize(() => { this.isLoading = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (order) => { this.order = order; },
        error: () => { this.error = 'No se pudo cargar la orden.'; }
      });
  }

  get canCancel(): boolean {
    const s = this.order?.status ?? '';
    return s === 'paid' || s === 'pending';
  }

  get isPendingOrder(): boolean {
    return (this.order?.status ?? '') === 'pending';
  }

  /** Reembolso pendiente según el servidor (pedido que ya estaba pagado). */
  get refundPending(): boolean {
    if (this.cancelResult) {
      return Boolean(this.cancelResult.pendingRefund);
    }
    return !this.isPendingOrder;
  }

  get cancelledStatusLabel(): string {
    const estado = this.cancelResult?.status || this.order?.status || '';
    return estado === 'cancelled' || !estado ? 'Cancelada' : estado;
  }

  get blockReason(): string {
    const s = this.order?.status ?? '';
    if (['shipped', 'delivered', 'en_devolucion'].includes(s)) {
      return 'Pedido en proceso logístico, solicitar devolución';
    }
    if (s === 'cancelled') return 'Esta orden ya fue cancelada.';
    return `No se puede cancelar un pedido en estado "${s}".`;
  }

  confirmCancel(): void {
    if (!this.canCancel || this.isCancelling) return;
    this.isCancelling = true;
    this.error = '';
    this.api.cancelOrder(this.orderId, 'customer_request')
      .pipe(finalize(() => { this.isCancelling = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (respuesta) => {
          // La pantalla de éxito muestra el estado que devolvió el servidor, no el que suponía el formulario.
          this.cancelResult = respuesta;
          this.cancelled = true;
          if (this.order && respuesta?.status) {
            this.order = { ...this.order, status: respuesta.status as AdminOrder['status'] };
          }
        },
        error: (err: any) => {
          this.error = err?.error?.message || 'No se pudo cancelar la orden.';
        }
      });
  }

  formatMoney(v?: number | null): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v ?? 0);
  }
}
