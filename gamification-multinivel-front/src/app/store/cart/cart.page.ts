import { ChangeDetectionStrategy, Component } from '@angular/core';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { getCoachCopy } from '../../shared/coach/coach-copy';

@Component({
  selector: 'app-store-cart-page',
  imports: [CTAButtonComponent],
  template: `
    <section class="app-page store-page">
      <header class="store-page__header">
        <p class="app-eyebrow">Carrito activo</p>
        <h1 class="app-title">Revisa tu selección antes de avanzar</h1>
        <p class="app-subtitle">
          Ajusta cantidades, confirma disponibilidad y protege tu margen antes de crear la
          cotización.
        </p>
      </header>

      <div class="store-page__content">
        <div class="app-card store-card">
          <h2 class="store-card__title">Resumen del pedido</h2>
          <ul class="store-card__list">
            <li>Productos top con alto margen</li>
            <li>Bonos por volumen aplicados automáticamente</li>
            <li>Entrega estimada en 48 horas</li>
          </ul>
          <app-cta-button label="Generar cotización" tone="success" [fullWidth]="true" />
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
export class CartPage {
  protected readonly coachCopy = getCoachCopy().store.cart;
}
