import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { CurrentStatusComponent } from '../../core/components/current-status.component';
import { MetricCardComponent } from '../../core/components/metric-card.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { ActiveGoalComponent } from '../components/active-goal.component';
import { CoachHeaderComponent } from '../components/coach-header.component';
import { NextActionComponent } from '../components/next-action.component';
import { CommissionsService } from '../../services/commissions.service';

type StatusTone = 'success' | 'warning' | 'danger';

interface CommissionViewModel {
  id: string;
  pointsLabel: string;
  contributionLabel: string;
  orderId: string;
  earnedAtLabel: string;
  statusLabel: string;
  statusTone: StatusTone;
}

@Component({
  selector: 'app-commissions-page',
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
          actionLabel="Validar comisiones pendientes"
          actionHref="#next-action"
        />
        <header class="flex flex-wrap items-start justify-between gap-4">
          <div class="space-y-2">
            <p class="app-eyebrow">Reconocimiento</p>
            <h1 class="text-2xl font-semibold text-white">Reconocimientos</h1>
            <p class="text-sm text-slate-300">
              Seguimiento claro de los puntos ganados por tu liderazgo.
            </p>
          </div>
          <a class="app-button app-button--ghost text-sm" routerLink="/dashboard">
            Volver al tablero
          </a>
        </header>

        <section class="space-y-4">
          <app-current-status
            label="En crecimiento"
            description="Suma puntos con cada reconocimiento consolidado."
            tone="success"
          />
          <app-active-goal />
          <app-next-action />
        </section>

        <section class="grid gap-4 md:grid-cols-3">
          <app-metric-card
            title="Entradas"
            [value]="totalCommissions()"
            helper="Registros"
          />
          <app-metric-card
            title="Puntos"
            [value]="totalPoints()"
            helper="Total consolidado"
            tone="success"
          />
          <app-metric-card
            title="Pendientes"
            [value]="pendingCommissions()"
            helper="Por validar"
            tone="warning"
          />
        </section>

        <section class="app-card app-card--soft overflow-hidden">
          <div class="border-b border-slate-700/60 px-4 py-3">
            <h2 class="text-sm font-semibold text-slate-200">Detalle de reconocimientos</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full text-sm text-slate-200">
              <caption class="sr-only">
                Reconocimientos con puntos, participación y estado actual.
              </caption>
              <thead class="bg-slate-900/70 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <tr>
                  <th class="px-4 py-3" scope="col">Reconocimiento</th>
                  <th class="px-4 py-3" scope="col">Orden</th>
                  <th class="px-4 py-3" scope="col">Fecha</th>
                  <th class="px-4 py-3" scope="col">Participación</th>
                  <th class="px-4 py-3" scope="col">Puntos</th>
                  <th class="px-4 py-3" scope="col">Estado</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800">
                @for (commission of commissionsView(); track commission.id) {
                  <tr class="text-slate-200">
                    <td class="px-4 py-3 font-semibold text-white">{{ commission.id }}</td>
                    <td class="px-4 py-3">{{ commission.orderId }}</td>
                    <td class="px-4 py-3">{{ commission.earnedAtLabel }}</td>
                    <td class="px-4 py-3">{{ commission.contributionLabel }}</td>
                    <td class="px-4 py-3">{{ commission.pointsLabel }}</td>
                    <td class="px-4 py-3">
                      <app-status-badge
                        [label]="commission.statusLabel"
                        [tone]="commission.statusTone"
                      />
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td class="px-4 py-6 text-center text-sm text-slate-400" colspan="6">
                      Sin comisiones registradas.
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
export class CommissionsPage {
  private readonly commissionsService = inject(CommissionsService);

  private readonly commissions = toSignal(this.commissionsService.getCommissions(), {
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
    title: 'Coach: Valida y cobra',
    message: 'Confirma las comisiones pendientes y registra el avance del equipo.',
    tone: 'success' as const,
  };

  protected readonly totalCommissions = computed(() => `${this.commissions().length}`);

  protected readonly totalPoints = computed(() => {
    const points = this.commissions().reduce(
      (total, commission) => total + commission.rewardPoints,
      0
    );
    return `${this.pointsFormatter.format(points)} pts`;
  });

  protected readonly pendingCommissions = computed(() =>
    `${this.commissions().filter((commission) => commission.status === 'pending').length}`
  );

  protected readonly commissionsView = computed<CommissionViewModel[]>(() =>
    this.commissions().map((commission) => ({
      id: commission.id,
      pointsLabel: `${this.pointsFormatter.format(commission.rewardPoints)} pts`,
      contributionLabel: `${commission.contributionPercent}%`,
      orderId: commission.orderId,
      earnedAtLabel: this.dateFormatter.format(new Date(commission.earnedAt)),
      statusLabel: this.getStatusLabel(commission.status),
      statusTone: this.getStatusTone(commission.status),
    }))
  );

  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      paid: 'Validada',
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
