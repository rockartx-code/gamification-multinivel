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
    <main class="app-page">
      <div class="app-shell space-y-6">
        <app-coach-header
          [messageTitle]="coachMessage.title"
          [messageBody]="coachMessage.message"
          [messageTone]="coachMessage.tone"
          actionLabel="Actualizar CTA clave"
          actionHref="#next-action"
        />
        <header class="flex flex-wrap items-start justify-between gap-4">
          <div class="space-y-2">
            <p class="app-eyebrow">Marketing</p>
            <h1 class="text-2xl font-semibold text-white">Landings</h1>
            <p class="text-sm text-slate-300">
              Resumen directo de las páginas activas y su enfoque comercial.
            </p>
          </div>
          <a class="app-button app-button--ghost text-sm" routerLink="/dashboard">
            Volver al tablero
          </a>
        </header>

        <section class="space-y-4">
          <app-current-status
            label="Contenido activo"
            description="Alinea mensajes y CTA para mantener el impulso."
            tone="success"
          />
          <app-active-goal />
          <app-next-action />
        </section>

        <section class="grid gap-4 md:grid-cols-3">
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

        <section class="app-card app-card--soft overflow-hidden">
          <div class="border-b border-slate-700/60 px-4 py-3">
            <h2 class="text-sm font-semibold text-slate-200">Detalle de landings</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full text-sm text-slate-200">
              <caption class="sr-only">
                Landings activas con CTA, highlights y URL.
              </caption>
              <thead class="bg-slate-900/70 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <tr>
                  <th class="px-4 py-3" scope="col">Landing</th>
                  <th class="px-4 py-3" scope="col">CTA</th>
                  <th class="px-4 py-3" scope="col">Highlights</th>
                  <th class="px-4 py-3" scope="col">URL</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800">
                @for (landing of landingsView(); track landing.heroTitle) {
                  <tr class="text-slate-200">
                    <td class="px-4 py-3 font-semibold text-white">{{ landing.heroTitle }}</td>
                    <td class="px-4 py-3">{{ landing.ctaLabel }}</td>
                    <td class="px-4 py-3">{{ landing.highlightsCount }}</td>
                    <td class="px-4 py-3">
                      <span class="text-slate-400">{{ landing.ctaUrl }}</span>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td class="px-4 py-6 text-center text-sm text-slate-400" colspan="4">
                      Sin landings registradas.
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
