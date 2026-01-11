import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

type LandingSummary = {
  id: string;
  h1: string;
  slug: string;
  status: 'Borrador' | 'Publicado';
  updatedAt: string;
};

@Component({
  selector: 'app-landings-list-page',
  imports: [RouterLink],
  template: `
    <main class="app-page">
      <div class="app-shell space-y-6">
        <header class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p class="app-eyebrow">Admin</p>
            <h1 class="text-2xl font-semibold text-white">Landings</h1>
            <p class="text-sm text-slate-300">
              Gestiona las landings activas y sus estados de publicación.
            </p>
          </div>
          <a class="app-button text-sm" routerLink="new">Crear nueva landing</a>
        </header>

        <section class="app-card app-card--soft p-4">
          <div class="grid gap-4 sm:grid-cols-2">
            @for (landing of landings(); track landing.id) {
              <article class="app-card app-card--soft p-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <h2 class="text-lg font-semibold text-white">{{ landing.h1 }}</h2>
                    <p class="text-sm text-slate-300">Slug: /{{ landing.slug }}</p>
                  </div>
                  <span
                    class="app-badge"
                    [class.app-badge--success]="landing.status === 'Publicado'"
                    [class.app-badge--warning]="landing.status === 'Borrador'"
                  >
                    {{ landing.status }}
                  </span>
                </div>
                <p class="mt-3 text-sm text-slate-300">
                  Última actualización: {{ landing.updatedAt }}
                </p>
                <div class="mt-4 flex flex-wrap gap-3 text-sm font-semibold text-slate-200">
                  <a class="app-link" routerLink="new">Editar</a>
                  <button class="text-slate-400" type="button">Duplicar</button>
                </div>
              </article>
            }
          </div>
        </section>
      </div>
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingsListPage {
  readonly landings = signal<LandingSummary[]>([
    {
      id: 'landing-001',
      h1: 'Impulsa tu red con retos y recompensas',
      slug: 'impulsa-tu-red',
      status: 'Publicado',
      updatedAt: 'hace 2 días',
    },
    {
      id: 'landing-002',
      h1: 'Nuevos objetivos para líderes de equipo',
      slug: 'objetivos-para-lideres',
      status: 'Borrador',
      updatedAt: 'hace 4 horas',
    },
  ]);
}
