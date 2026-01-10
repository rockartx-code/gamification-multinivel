import { ChangeDetectionStrategy, Component } from '@angular/core';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { getCoachCopy } from '../../shared/coach/coach-copy';

@Component({
  selector: 'app-store-catalog-page',
  imports: [CTAButtonComponent],
  template: `
    <section class="store-page">
      <header class="store-page__header">
        <p class="store-page__eyebrow">Catálogo inteligente</p>
        <h1 class="store-page__title">Explora productos listos para impulsar tu red</h1>
        <p class="store-page__subtitle">
          Filtra por objetivos, tendencias y margen de ganancia para elegir lo mejor para tu
          siguiente avance.
        </p>
      </header>

      <div class="store-page__content">
        <div class="store-card">
          <h2 class="store-card__title">Selecciones destacadas</h2>
          <ul class="store-card__list">
            <li>Bundles de alto impacto para nuevos socios</li>
            <li>Productos estrella con reposición inmediata</li>
            <li>Materiales para activaciones rápidas</li>
          </ul>
          <app-cta-button label="Ir al catálogo" tone="success" [fullWidth]="true" />
        </div>

        <aside class="store-coach" aria-label="Consejo del coach">
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

      .store-page__eyebrow {
        margin: 0;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
      }

      .store-page__title {
        margin: 0;
        font-size: 32px;
        color: #0f172a;
      }

      .store-page__subtitle {
        margin: 0;
        font-size: 16px;
        color: #475569;
      }

      .store-page__content {
        display: grid;
        gap: 20px;
      }

      .store-card {
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 20px;
        background: #ffffff;
        display: grid;
        gap: 16px;
      }

      .store-card__title {
        margin: 0;
        font-size: 18px;
        color: #0f172a;
      }

      .store-card__list {
        margin: 0;
        padding-left: 18px;
        color: #475569;
        display: grid;
        gap: 8px;
      }

      .store-coach {
        border-radius: 16px;
        padding: 18px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        display: grid;
        gap: 8px;
      }

      .store-coach__title {
        margin: 0;
        font-size: 16px;
        color: #0f172a;
      }

      .store-coach__message {
        margin: 0;
        color: #475569;
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
