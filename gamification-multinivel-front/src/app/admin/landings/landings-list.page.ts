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
    <main class="space-y-6 bg-slate-50 px-4 py-6 md:px-8">
      <header class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-sm font-semibold uppercase text-slate-500">Admin</p>
          <h1 class="text-2xl font-semibold text-slate-900">Landings</h1>
          <p class="text-sm text-slate-600">
            Gestiona las landings activas y sus estados de publicación.
          </p>
        </div>
        <a
          class="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          routerLink="new"
        >
          Crear nueva landing
        </a>
      </header>

      <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div class="grid gap-4 sm:grid-cols-2">
          @for (landing of landings(); track landing.id) {
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h2 class="text-lg font-semibold text-slate-900">{{ landing.h1 }}</h2>
                  <p class="text-sm text-slate-600">Slug: /{{ landing.slug }}</p>
                </div>
                <span
                  class="rounded-full px-3 py-1 text-xs font-semibold"
                  [class]="
                    landing.status === 'Publicado'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-amber-100 text-amber-700'
                  "
                >
                  {{ landing.status }}
                </span>
              </div>
              <p class="mt-3 text-sm text-slate-600">
                Última actualización: {{ landing.updatedAt }}
              </p>
              <div class="mt-4 flex flex-wrap gap-3 text-sm font-semibold text-slate-700">
                <a class="text-sky-700" routerLink="new">Editar</a>
                <button class="text-slate-500" type="button">Duplicar</button>
              </div>
            </article>
          }
        </div>
      </section>
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
