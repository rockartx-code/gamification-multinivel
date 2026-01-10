import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { CurrentStatusComponent } from '../../core/components/current-status.component';
import { MetricCardComponent } from '../../core/components/metric-card.component';
import { ActiveGoalComponent } from '../components/active-goal.component';
import { CoachHeaderComponent } from '../components/coach-header.component';
import { NextActionComponent } from '../components/next-action.component';
import { LandingsService } from '../../services/landings.service';

interface LandingViewModel {
  heroTitle: string;
  ctaLabel: string;
  ctaUrl: string;
  highlightsCount: string;
}

@Component({
  selector: 'app-landings-page',
  imports: [
    ActiveGoalComponent,
    CoachHeaderComponent,
    CurrentStatusComponent,
    MetricCardComponent,
    NextActionComponent,
    RouterLink,
  ],
  template: `
    <main class="min-h-screen bg-slate-50 px-4 py-6 md:px-8">
      <app-coach-header
        [messageTitle]="coachMessage.title"
        [messageBody]="coachMessage.message"
        [messageTone]="coachMessage.tone"
        actionLabel="Actualizar CTA clave"
        actionHref="#next-action"
      />
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Marketing
          </p>
          <h1 class="text-2xl font-semibold text-slate-900">Landings</h1>
          <p class="text-sm text-slate-600">
            Resumen directo de las páginas activas y su enfoque comercial.
          </p>
        </div>
        <a
          class="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          routerLink="/dashboard"
        >
          Volver al tablero
        </a>
      </header>

      <section class="mt-6 space-y-4">
        <app-current-status
          label="Contenido activo"
          description="Alinea mensajes y CTA para mantener el impulso."
          tone="success"
        />
        <app-active-goal />
        <app-next-action />
      </section>

      <section class="mt-6 grid gap-4 md:grid-cols-3">
        <app-metric-card title="Landings" [value]="totalLandings()" helper="Activas" />
        <app-metric-card
          title="CTA únicos"
          [value]="uniqueCtas()"
          helper="Variantes"
          tone="success"
        />
        <app-metric-card
          title="Highlights"
          [value]="totalHighlights()"
          helper="Mensajes clave"
          tone="warning"
        />
      </section>

      <section class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-800">Detalle de landings</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <caption class="sr-only">
              Landings activas con CTA, highlights y URL.
            </caption>
            <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3" scope="col">Landing</th>
                <th class="px-4 py-3" scope="col">CTA</th>
                <th class="px-4 py-3" scope="col">Highlights</th>
                <th class="px-4 py-3" scope="col">URL</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (landing of landingsView(); track landing.heroTitle) {
                <tr class="text-slate-700">
                  <td class="px-4 py-3 font-semibold text-slate-900">{{ landing.heroTitle }}</td>
                  <td class="px-4 py-3">{{ landing.ctaLabel }}</td>
                  <td class="px-4 py-3">{{ landing.highlightsCount }}</td>
                  <td class="px-4 py-3">
                    <span class="text-slate-600">{{ landing.ctaUrl }}</span>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td class="px-4 py-6 text-center text-sm text-slate-500" colspan="4">
                    Sin landings registradas.
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
export class LandingsPage {
  private readonly landingsService = inject(LandingsService);

  private readonly landings = toSignal(this.landingsService.getLandings(), {
    initialValue: [],
  });

  protected readonly coachMessage = {
    title: 'Coach: Ajusta el mensaje',
    message: 'Refuerza los highlights con más tracción y renueva el CTA clave.',
    tone: 'success' as const,
  };

  protected readonly totalLandings = computed(() => `${this.landings().length}`);

  protected readonly totalHighlights = computed(() =>
    `${this.landings().reduce((total, landing) => total + landing.highlights.length, 0)}`
  );

  protected readonly uniqueCtas = computed(() => {
    const uniqueLabels = new Set(this.landings().map((landing) => landing.ctaLabel));
    return `${uniqueLabels.size}`;
  });

  protected readonly landingsView = computed<LandingViewModel[]>(() =>
    this.landings().map((landing) => ({
      heroTitle: landing.heroTitle,
      ctaLabel: landing.ctaLabel,
      ctaUrl: landing.ctaUrl,
      highlightsCount: `${landing.highlights.length}`,
    }))
  );
}
