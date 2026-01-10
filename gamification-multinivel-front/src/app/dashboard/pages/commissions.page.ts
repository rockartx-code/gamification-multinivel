import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { MetricCardComponent } from '../../core/components/metric-card.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { CommissionsService } from '../../services/commissions.service';

type StatusTone = 'success' | 'warning' | 'danger';

interface CommissionViewModel {
  id: string;
  amountLabel: string;
  rateLabel: string;
  orderId: string;
  earnedAtLabel: string;
  statusLabel: string;
  statusTone: StatusTone;
}

@Component({
  selector: 'app-commissions-page',
  imports: [MetricCardComponent, RouterLink, StatusBadgeComponent],
  template: `
    <main class="min-h-screen bg-slate-50 px-4 py-6 md:px-8">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Finanzas
          </p>
          <h1 class="text-2xl font-semibold text-slate-900">Comisiones</h1>
          <p class="text-sm text-slate-600">
            Visibilidad clara de los pagos generados por la red.
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
        <app-metric-card title="Entradas" [value]="totalCommissions()" helper="Registros" />
        <app-metric-card
          title="Monto"
          [value]="totalAmount()"
          helper="Total consolidado"
          tone="success"
        />
        <app-metric-card
          title="Pendientes"
          [value]="pendingCommissions()"
          helper="Por liquidar"
          tone="warning"
        />
      </section>

      <section class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-800">Detalle de comisiones</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3" scope="col">Comisión</th>
                <th class="px-4 py-3" scope="col">Orden</th>
                <th class="px-4 py-3" scope="col">Fecha</th>
                <th class="px-4 py-3" scope="col">Tasa</th>
                <th class="px-4 py-3" scope="col">Monto</th>
                <th class="px-4 py-3" scope="col">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (commission of commissionsView(); track commission.id) {
                <tr class="text-slate-700">
                  <td class="px-4 py-3 font-semibold text-slate-900">{{ commission.id }}</td>
                  <td class="px-4 py-3">{{ commission.orderId }}</td>
                  <td class="px-4 py-3">{{ commission.earnedAtLabel }}</td>
                  <td class="px-4 py-3">{{ commission.rateLabel }}</td>
                  <td class="px-4 py-3">{{ commission.amountLabel }}</td>
                  <td class="px-4 py-3">
                    <app-status-badge
                      [label]="commission.statusLabel"
                      [tone]="commission.statusTone"
                    />
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td class="px-4 py-6 text-center text-sm text-slate-500" colspan="6">
                    Sin comisiones registradas.
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
export class CommissionsPage {
  private readonly commissionsService = inject(CommissionsService);

  private readonly commissions = toSignal(this.commissionsService.getCommissions(), {
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

  protected readonly totalCommissions = computed(() => `${this.commissions().length}`);

  protected readonly totalAmount = computed(() =>
    this.currencyFormatter.format(
      this.commissions().reduce((total, commission) => total + commission.amount, 0)
    )
  );

  protected readonly pendingCommissions = computed(() =>
    `${this.commissions().filter((commission) => commission.status === 'pending').length}`
  );

  protected readonly commissionsView = computed<CommissionViewModel[]>(() =>
    this.commissions().map((commission) => ({
      id: commission.id,
      amountLabel: this.currencyFormatter.format(commission.amount),
      rateLabel: `${commission.ratePercent}%`,
      orderId: commission.orderId,
      earnedAtLabel: this.dateFormatter.format(new Date(commission.earnedAt)),
      statusLabel: this.getStatusLabel(commission.status),
      statusTone: this.getStatusTone(commission.status),
    }))
  );

  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      paid: 'Pagada',
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
