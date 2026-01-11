import { ChangeDetectionStrategy, Component } from '@angular/core';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { getCoachCopy } from '../../shared/coach/coach-copy';

@Component({
  selector: 'app-store-catalog-page',
  imports: [CTAButtonComponent],
  template: `
    <section class="app-page store-page">
      <header class="store-page__header">
        <p class="app-eyebrow">Catálogo inteligente</p>
        <h1 class="app-title">Explora productos listos para impulsar tu red</h1>
        <p class="app-subtitle">
          Filtra por objetivos, tendencias y margen de ganancia para elegir lo mejor para tu
          siguiente avance.
        </p>
      </header>

      <div class="store-page__content">
        <div class="app-card store-card">
          <h2 class="store-card__title">Selecciones destacadas</h2>
          <ul class="store-card__list">
            <li>Bundles de alto impacto para nuevos socios</li>
            <li>Productos estrella con reposición inmediata</li>
            <li>Materiales para activaciones rápidas</li>
          </ul>
          <app-cta-button label="Ir al catálogo" tone="success" [fullWidth]="true" />
        </div>

        <aside class="app-card app-card--soft store-coach" aria-label="Consejo del coach">
          <h2 class="store-coach__title">{{ coachCopy.title }}</h2>
          <p class="store-coach__message">{{ coachCopy.message }}</p>
        </aside>
      </div>
    </section>
  `,
  styles: [
    `
      .store-page {
        display: grid;
        gap: 24px;
        padding: 32px 20px 48px;
        max-width: 1040px;
        margin: 0 auto;
      }

      .store-page__header {
        display: grid;
        gap: 10px;
      }

      .store-page__content {
        display: grid;
        gap: 20px;
      }

      .store-card {
        padding: 20px;
        display: grid;
        gap: 16px;
      }

      .store-card__title {
        margin: 0;
        font-size: 18px;
        color: var(--ritual-text-strong);
      }

      .store-card__list {
        margin: 0;
        padding-left: 18px;
        color: var(--ritual-text-soft);
        display: grid;
        gap: 8px;
      }

      .store-coach {
        padding: 18px;
        display: grid;
        gap: 8px;
      }

      .store-coach__title {
        margin: 0;
        font-size: 16px;
        color: var(--ritual-text-strong);
      }

      .store-coach__message {
        margin: 0;
        color: var(--ritual-text-soft);
      }

      @media (min-width: 900px) {
        .store-page__content {
          grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
          align-items: start;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CatalogPage {
  protected readonly coachCopy = getCoachCopy().store.catalog;
}
