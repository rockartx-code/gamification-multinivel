import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { CoachMessageComponent } from '../../core/components/coach-message.component';
import { CurrentStatusComponent } from '../../core/components/current-status.component';
import { MetricCardComponent } from '../../core/components/metric-card.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { ActiveGoalComponent } from '../components/active-goal.component';
import { NextActionComponent } from '../components/next-action.component';
import { NetworkService } from '../../services/network.service';

type StatusTone = 'success' | 'warning';

interface NetworkMemberViewModel {
  id: string;
  name: string;
  levelLabel: string;
  joinedAtLabel: string;
  statusLabel: string;
  statusTone: StatusTone;
}

@Component({
  selector: 'app-network-page',
  imports: [
    ActiveGoalComponent,
    CoachMessageComponent,
    CurrentStatusComponent,
    MetricCardComponent,
    NextActionComponent,
    RouterLink,
    StatusBadgeComponent,
  ],
  template: `
    <main class="min-h-screen bg-slate-50 px-4 py-6 md:px-8">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Red comercial
          </p>
          <h1 class="text-2xl font-semibold text-slate-900">Mi red</h1>
          <p class="text-sm text-slate-600">
            Seguimiento directo del desempeño y actividad de los líderes.
          </p>
        </div>
        <a
          class="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          routerLink="/dashboard"
        >
          Volver al tablero
        </a>
      </header>

      <section class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div class="space-y-4">
          <app-current-status
            label="Equipo activo"
            description="Acompaña a los líderes con más potencial hoy."
            tone="success"
          />
          <app-active-goal />
          <app-next-action />
        </div>
        <div class="space-y-4">
          <app-coach-message
            [title]="coachMessage.title"
            [message]="coachMessage.message"
            [tone]="coachMessage.tone"
          />
        </div>
      </section>

      <section class="mt-6 grid gap-4 md:grid-cols-3">
        <app-metric-card title="Integrantes" [value]="totalMembers()" helper="Total en red" />
        <app-metric-card
          title="Activos"
          [value]="activeMembers()"
          helper="En actividad"
          tone="success"
        />
        <app-metric-card
          title="Nivel promedio"
          [value]="averageLevel()"
          helper="Promedio actual"
          tone="warning"
        />
      </section>

      <section class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-800">Detalle de integrantes</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <caption class="sr-only">
              Integrantes con nivel, fecha de alta y estado actual.
            </caption>
            <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3" scope="col">Integrante</th>
                <th class="px-4 py-3" scope="col">Nivel</th>
                <th class="px-4 py-3" scope="col">Alta</th>
                <th class="px-4 py-3" scope="col">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (member of membersView(); track member.id) {
                <tr class="text-slate-700">
                  <td class="px-4 py-3 font-semibold text-slate-900">{{ member.name }}</td>
                  <td class="px-4 py-3">{{ member.levelLabel }}</td>
                  <td class="px-4 py-3">{{ member.joinedAtLabel }}</td>
                  <td class="px-4 py-3">
                    <app-status-badge
                      [label]="member.statusLabel"
                      [tone]="member.statusTone"
                    />
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td class="px-4 py-6 text-center text-sm text-slate-500" colspan="4">
                    Sin integrantes registrados.
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
export class NetworkPage {
  private readonly networkService = inject(NetworkService);

  private readonly members = toSignal(this.networkService.getNetworkMembers(), {
    initialValue: [],
  });

  private readonly dateFormatter = new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  protected readonly coachMessage = {
    title: 'Coach: Lidera con claridad',
    message: 'Revisa quién necesita apoyo y celebra los avances visibles.',
    tone: 'success' as const,
  };

  protected readonly totalMembers = computed(() => `${this.members().length}`);

  protected readonly activeMembers = computed(() =>
    `${this.members().filter((member) => member.active).length}`
  );

  protected readonly averageLevel = computed(() => {
    if (this.members().length === 0) {
      return '0';
    }
    const totalLevel = this.members().reduce((sum, member) => sum + member.level, 0);
    return (totalLevel / this.members().length).toFixed(1);
  });

  protected readonly membersView = computed<NetworkMemberViewModel[]>(() =>
    this.members().map((member) => ({
      id: member.id,
      name: member.name,
      levelLabel: `Nivel ${member.level}`,
      joinedAtLabel: this.dateFormatter.format(new Date(member.joinedAt)),
      statusLabel: member.active ? 'Activo' : 'Inactivo',
      statusTone: member.active ? 'success' : 'warning',
    }))
  );
}
