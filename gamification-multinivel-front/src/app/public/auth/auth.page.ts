import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { SessionService } from '../../core/session.service';
import { Router } from '@angular/router';

import { AuthService } from '../../services/auth.service';
import { UserRole } from '../../domain/models';
import { getCoachCopy } from '../../shared/coach/coach-copy';
import { AuthFormComponent, AuthFormPayload } from './components/auth-form.component';
import { CoachMessageInlineComponent } from './components/coach-message-inline.component';

@Component({
  selector: 'app-auth-page',
  imports: [AuthFormComponent, CoachMessageInlineComponent],
  template: `
    <section class="app-page auth-page">
      <header class="auth-page__header">
        <p class="app-eyebrow">Acceso seguro</p>
        <h1 class="app-title">{{ authContext()?.title }}</h1>
        <p class="app-subtitle">{{ authContext()?.subtitle }}</p>
      </header>

      <div class="auth-page__content">
        <div class="app-card auth-card">
          @if (authContext(); as context) {
            <app-auth-form
              [primaryActionLabel]="context.primaryActionLabel"
              [secondaryActionLabel]="context.secondaryActionLabel"
              [helperText]="context.helperText"
              (submittedAction)="handleAuthAction($event)"
            />
          }
        </div>

        <aside class="auth-coach" aria-label="Mensajes del coach">
          <h2 class="auth-coach__title">{{ coachTitle() }}</h2>
          <div class="auth-coach__list">
            @for (message of coachMessages(); track message.id) {
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

      .auth-page__content {
        display: grid;
        gap: 20px;
      }

      .auth-card {
        padding: 20px;
      }

      .auth-coach {
        display: grid;
        gap: 12px;
      }

      .auth-coach__title {
        margin: 0;
        font-size: 16px;
        color: var(--ritual-text-strong);
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
  private readonly router = inject(Router);
  private readonly sessionService = inject(SessionService);
  private readonly coachCopy = getCoachCopy();
  private readonly authAction = signal<'login' | 'register' | null>(null);

  private readonly baseAuthContext = toSignal(this.authService.getAuthContext(), { initialValue: null });
  readonly authContext = computed(() => {
    const context = this.baseAuthContext();
    if (!context) {
      return null;
    }

    const referralContext = this.sessionService.landingContext();
    if (!referralContext) {
      return context;
    }

    return {
      ...context,
      subtitle: `${context.subtitle} Tu registro quedará asociado a la campaña ${referralContext.landingSlug}.`,
    };
  });
  protected readonly coachTitle = computed(() => {
    if (this.authAction() === 'register') {
      return this.coachCopy.auth.registrationSuccess.title;
    }
    return this.coachCopy.auth.default.title;
  });
  protected readonly coachMessages = computed(() => {
    if (this.authAction() === 'register') {
      return this.coachCopy.auth.registrationSuccess.messages;
    }
    return this.authContext()?.coachMessages ?? [];
  });

  handleAuthAction(payload: AuthFormPayload): void {
    this.authAction.set(payload.action);
    if (payload.action === 'login') {
      this.authService.login(payload.email, payload.password).subscribe({
        next: (session) => this.redirectToPanel(session.role),
        error: () => null,
      });
    }
  }

  private redirectToPanel(role: UserRole): void {
    const target = role === 'admin' ? '/admin' : '/dashboard';
    this.router.navigate([target]);
  }
}
