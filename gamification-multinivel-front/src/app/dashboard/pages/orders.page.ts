import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { CurrentStatusComponent } from '../../core/components/current-status.component';
import { MetricCardComponent } from '../../core/components/metric-card.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { ActiveGoalComponent } from '../components/active-goal.component';
import { CoachHeaderComponent } from '../components/coach-header.component';
import { NextActionComponent } from '../components/next-action.component';
import { OrdersService } from '../../services/orders.service';

type StatusTone = 'success' | 'warning' | 'danger';

interface OrderViewModel {
  id: string;
  customerId: string;
  pointsLabel: string;
  createdAtLabel: string;
  statusLabel: string;
  statusTone: StatusTone;
}

@Component({
  selector: 'app-orders-page',
  imports: [
    ActiveGoalComponent,
    CoachHeaderComponent,
    CurrentStatusComponent,
    MetricCardComponent,
    NextActionComponent,
    RouterLink,
    StatusBadgeComponent,
  ],
  template: `
    <main class="app-page">
      <div class="app-shell space-y-6">
        <app-coach-header
          [messageTitle]="coachMessage.title"
          [messageBody]="coachMessage.message"
          [messageTone]="coachMessage.tone"
          actionLabel="Revisar pedidos pendientes"
          actionHref="#next-action"
        />
        <header class="flex flex-wrap items-start justify-between gap-4">
          <div class="space-y-2">
            <p class="app-eyebrow">Operación diaria</p>
            <h1 class="text-2xl font-semibold text-white">Pedidos</h1>
            <p class="text-sm text-slate-300">
              Estado claro de las activaciones y su impacto en tu progreso.
            </p>
          </div>
          <a class="app-button app-button--ghost text-sm" routerLink="/dashboard">
            Volver al tablero
          </a>
        </header>

        <section class="space-y-4">
          <app-current-status
            label="En marcha"
            description="Monitorea las activaciones clave y mantén el ritmo."
            tone="success"
          />
          <app-active-goal />
          <app-next-action />
        </section>

        <section class="grid gap-4 md:grid-cols-3">
          <app-metric-card
            title="Órdenes"
            [value]="totalOrders()"
            helper="Activas"
          />
          <app-metric-card
            title="Impacto"
            [value]="totalPoints()"
            helper="Puntos consolidados"
            tone="success"
          />
          <app-metric-card
            title="Completadas"
            [value]="completedOrders()"
            helper="Listas hoy"
            tone="warning"
          />
        </section>

        <section class="app-card app-card--soft overflow-hidden">
          <div class="border-b border-slate-700/60 px-4 py-3">
            <h2 class="text-sm font-semibold text-slate-200">Detalle de órdenes</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full text-sm text-slate-200">
              <caption class="sr-only">
                Estado y puntos asociados a cada orden activa.
              </caption>
              <thead class="bg-slate-900/70 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <tr>
                  <th class="px-4 py-3" scope="col">Orden</th>
                  <th class="px-4 py-3" scope="col">Cliente</th>
                  <th class="px-4 py-3" scope="col">Fecha</th>
                  <th class="px-4 py-3" scope="col">Puntos</th>
                  <th class="px-4 py-3" scope="col">Estado</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800">
                @for (order of ordersView(); track order.id) {
                  <tr class="text-slate-200">
                    <td class="px-4 py-3 font-semibold text-white">{{ order.id }}</td>
                    <td class="px-4 py-3">{{ order.customerId }}</td>
                    <td class="px-4 py-3">{{ order.createdAtLabel }}</td>
                    <td class="px-4 py-3">{{ order.pointsLabel }}</td>
                    <td class="px-4 py-3">
                      <app-status-badge
                        [label]="order.statusLabel"
                        [tone]="order.statusTone"
                      />
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td class="px-4 py-6 text-center text-sm text-slate-400" colspan="5">
                      Sin órdenes registradas.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OrdersPage {
  private readonly ordersService = inject(OrdersService);

  private readonly orders = toSignal(this.ordersService.getOrders(), {
    initialValue: [],
  });

  private readonly pointsFormatter = new Intl.NumberFormat('es-CO', {
    maximumFractionDigits: 0,
  });

  private readonly dateFormatter = new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  protected readonly coachMessage = {
    title: 'Coach: Prioriza y confirma',
    message: 'Valida hoy las órdenes pendientes que liberan más puntos.',
    tone: 'success' as const,
  };

  protected readonly totalOrders = computed(() => `${this.orders().length}`);

  protected readonly totalPoints = computed(() => {
    const points = this.orders().reduce((total, order) => total + order.impactPoints, 0);
    return `${this.pointsFormatter.format(points)} pts`;
  });

  protected readonly completedOrders = computed(() =>
    `${this.orders().filter((order) => order.status === 'fulfilled').length}`
  );

  protected readonly ordersView = computed<OrderViewModel[]>(() =>
    this.orders().map((order) => ({
      id: order.id,
      customerId: order.customerId,
      pointsLabel: `${this.pointsFormatter.format(order.impactPoints)} pts`,
      createdAtLabel: this.dateFormatter.format(new Date(order.createdAt)),
      statusLabel: this.getStatusLabel(order.status),
      statusTone: this.getStatusTone(order.status),
    }))
  );

  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      paid: 'Validada',
      fulfilled: 'Completada',
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
