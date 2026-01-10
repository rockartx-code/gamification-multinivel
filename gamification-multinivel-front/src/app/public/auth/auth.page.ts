import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { AuthService } from '../../services/auth.service';
import { getCoachCopy } from '../../shared/coach/coach-copy';
import { AuthFormComponent } from './components/auth-form.component';
import { CoachMessageInlineComponent } from './components/coach-message-inline.component';

@Component({
  selector: 'app-auth-page',
  imports: [AuthFormComponent, CoachMessageInlineComponent],
  template: `
    <section class="auth-page">
      <header class="auth-page__header">
        <p class="auth-page__eyebrow">Acceso seguro</p>
        <h1 class="auth-page__title">{{ authContext()?.title }}</h1>
        <p class="auth-page__subtitle">{{ authContext()?.subtitle }}</p>
      </header>

      <div class="auth-page__content">
        <div class="auth-card">
          @if (authContext(); as context) {
            <app-auth-form
              [primaryActionLabel]="context.primaryActionLabel"
              [secondaryActionLabel]="context.secondaryActionLabel"
              [helperText]="context.helperText"
            />
          }
        </div>

        <aside class="auth-coach" aria-label="Mensajes del coach">
          <h2 class="auth-coach__title">{{ coachTitle }}</h2>
          <div class="auth-coach__list">
            @for (message of authContext()?.coachMessages ?? []; track message.id) {
              <app-coach-message-inline [message]="message" />
            }
          </div>
        </aside>
      </div>
    </section>
  `,
  styles: [
    `
      .auth-page {
        display: grid;
        gap: 24px;
        padding: 32px 20px 48px;
        max-width: 980px;
        margin: 0 auto;
      }

      .auth-page__header {
        display: grid;
        gap: 8px;
      }

      .auth-page__eyebrow {
        margin: 0;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
      }

      .auth-page__title {
        margin: 0;
        font-size: 32px;
        color: #111827;
      }

      .auth-page__subtitle {
        margin: 0;
        font-size: 16px;
        color: #4b5563;
      }

      .auth-page__content {
        display: grid;
        gap: 20px;
      }

      .auth-card {
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
        background: #ffffff;
      }

      .auth-coach {
        display: grid;
        gap: 12px;
      }

      .auth-coach__title {
        margin: 0;
        font-size: 16px;
        color: #111827;
      }

      .auth-coach__list {
        display: grid;
        gap: 12px;
      }

      @media (min-width: 900px) {
        .auth-page__content {
          grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
          align-items: start;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthPage {
  private readonly authService = inject(AuthService);
  private readonly coachCopy = getCoachCopy();

  readonly authContext = toSignal(this.authService.getAuthContext(), { initialValue: null });
  protected readonly coachTitle = this.coachCopy.auth.default.title;
}
