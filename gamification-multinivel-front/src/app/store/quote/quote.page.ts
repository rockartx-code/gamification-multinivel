import { ChangeDetectionStrategy, Component } from '@angular/core';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { getCoachCopy } from '../../shared/coach/coach-copy';

@Component({
  selector: 'app-store-quote-page',
  imports: [CTAButtonComponent],
  template: `
    <section class="app-page store-page">
      <header class="store-page__header">
        <p class="app-eyebrow">Cotización lista</p>
        <h1 class="app-title">Comparte una propuesta clara y convincente</h1>
        <p class="app-subtitle">
          Ajusta el mensaje para tu cliente y destaca el valor agregado que entregas con tu
          red.
        </p>
      </header>

      <div class="store-page__content">
        <div class="app-card store-card">
          <h2 class="store-card__title">Propuesta optimizada</h2>
          <ul class="store-card__list">
            <li>Desglose de precios con incentivos incluidos</li>
            <li>Notas clave para el seguimiento comercial</li>
            <li>Opción de compartir por WhatsApp o email</li>
          </ul>
          <app-cta-button label="Enviar cotización" tone="success" [fullWidth]="true" />
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
export class QuotePage {
  protected readonly coachCopy = getCoachCopy().store.quote;
}
