import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { MetricCardComponent } from '../../core/components/metric-card.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { OrdersService } from '../../services/orders.service';

type StatusTone = 'success' | 'warning' | 'danger';

interface OrderViewModel {
  id: string;
  customerId: string;
  amountLabel: string;
  createdAtLabel: string;
  statusLabel: string;
  statusTone: StatusTone;
}

@Component({
  selector: 'app-orders-page',
  imports: [MetricCardComponent, RouterLink, StatusBadgeComponent],
  template: `
    <main class="min-h-screen bg-slate-50 px-4 py-6 md:px-8">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Operaciones
          </p>
          <h1 class="text-2xl font-semibold text-slate-900">Pedidos</h1>
          <p class="text-sm text-slate-600">
            Control directo del estado y volumen de las órdenes activas.
          </p>
        </div>
        <a
          class="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          routerLink="/dashboard"
        >
          Volver al tablero
        </a>
      </header>

      <section class="mt-6 grid gap-4 md:grid-cols-3">
        <app-metric-card title="Órdenes" [value]="totalOrders()" helper="Total activas" />
        <app-metric-card
          title="Volumen"
          [value]="totalAmount()"
          helper="Monto consolidado"
          tone="success"
        />
        <app-metric-card
          title="Pagadas"
          [value]="paidOrders()"
          helper="Con pago confirmado"
          tone="warning"
        />
      </section>

      <section class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-800">Detalle de órdenes</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3" scope="col">Orden</th>
                <th class="px-4 py-3" scope="col">Cliente</th>
                <th class="px-4 py-3" scope="col">Fecha</th>
                <th class="px-4 py-3" scope="col">Monto</th>
                <th class="px-4 py-3" scope="col">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (order of ordersView(); track order.id) {
                <tr class="text-slate-700">
                  <td class="px-4 py-3 font-semibold text-slate-900">{{ order.id }}</td>
                  <td class="px-4 py-3">{{ order.customerId }}</td>
                  <td class="px-4 py-3">{{ order.createdAtLabel }}</td>
                  <td class="px-4 py-3">{{ order.amountLabel }}</td>
                  <td class="px-4 py-3">
                    <app-status-badge
                      [label]="order.statusLabel"
                      [tone]="order.statusTone"
                    />
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td class="px-4 py-6 text-center text-sm text-slate-500" colspan="5">
                    Sin órdenes registradas.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OrdersPage {
  private readonly ordersService = inject(OrdersService);

  private readonly orders = toSignal(this.ordersService.getOrders(), {
    initialValue: [],
  });

  private readonly currencyFormatter = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });

  private readonly dateFormatter = new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  protected readonly totalOrders = computed(() => `${this.orders().length}`);

  protected readonly totalAmount = computed(() =>
    this.currencyFormatter.format(
      this.orders().reduce((total, order) => total + order.totalAmount, 0)
    )
  );

  protected readonly paidOrders = computed(() =>
    `${this.orders().filter((order) => order.status === 'paid').length}`
  );

  protected readonly ordersView = computed<OrderViewModel[]>(() =>
    this.orders().map((order) => ({
      id: order.id,
      customerId: order.customerId,
      amountLabel: this.currencyFormatter.format(order.totalAmount),
      createdAtLabel: this.dateFormatter.format(new Date(order.createdAt)),
      statusLabel: this.getStatusLabel(order.status),
      statusTone: this.getStatusTone(order.status),
    }))
  );

  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      paid: 'Pagada',
      fulfilled: 'Entregada',
      cancelled: 'Cancelada',
    };
    return labels[status] ?? 'Pendiente';
  }

  private getStatusTone(status: string): StatusTone {
    if (status === 'cancelled') {
      return 'danger';
    }
    if (status === 'pending') {
      return 'warning';
    }
    return 'success';
  }
}
