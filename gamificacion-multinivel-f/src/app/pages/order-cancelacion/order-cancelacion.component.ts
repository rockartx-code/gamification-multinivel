import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AdminOrder } from '../../models/admin.model';
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
    return (this.order?.status ?? '') === 'paid';
  }

  get blockReason(): string {
    const s = this.order?.status ?? '';
    if (['shipped', 'delivered', 'en_devolucion'].includes(s)) {
      return 'Pedido en proceso logístico, solicitar devolución';
    }
    if (s === 'cancelled') return 'Esta orden ya fue cancelada.';
    if (s === 'pending') return 'Solo se pueden cancelar órdenes con pago confirmado.';
    return `No se puede cancelar un pedido en estado "${s}".`;
  }

  confirmCancel(): void {
    if (!this.canCancel || this.isCancelling) return;
    this.isCancelling = true;
    this.error = '';
    this.api.cancelOrder(this.orderId, 'customer_request')
      .pipe(finalize(() => { this.isCancelling = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: () => { this.cancelled = true; },
        error: (err: any) => {
          this.error = err?.error?.message || 'No se pudo cancelar la orden.';
        }
      });
  }

  formatMoney(v?: number | null): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v ?? 0);
  }
}
