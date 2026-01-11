import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'app-auth-form',
  imports: [ReactiveFormsModule],
  template: `
    <form class="auth-form" [formGroup]="form" (ngSubmit)="handleSubmit()">
      <label class="field">
        <span class="app-label">Correo</span>
        <input
          class="app-input"
          type="email"
          autocomplete="email"
          formControlName="email"
          aria-describedby="email-help"
        />
      </label>
      <p id="email-help" class="app-hint">Usa el correo con el que te registraste.</p>

      <label class="field">
        <span class="app-label">Contraseña</span>
        <input
          class="app-input"
          type="password"
          autocomplete="current-password"
          formControlName="password"
          aria-describedby="password-help"
        />
      </label>
      <p id="password-help" class="app-hint">Mínimo 6 caracteres.</p>

      <p class="auth-helper" aria-live="polite">{{ helperText() }}</p>

      <div class="actions">
        <button class="app-button app-button--success" type="submit" [disabled]="form.invalid">
          {{ primaryActionLabel() }}
        </button>
        <button class="app-button app-button--ghost" type="button" (click)="handleSecondary()">
          {{ secondaryActionLabel() }}
        </button>
      </div>

      @if (submitted()) {
        <p class="auth-status" role="status">{{ statusMessage() }}</p>
      }
    </form>
  `,
  styles: [
    `
      .auth-form {
        display: grid;
        gap: 16px;
      }

      .field {
        display: grid;
        gap: 6px;
      }

      .auth-helper {
        margin: 0;
        font-size: 0.85rem;
        color: var(--ritual-text-soft);
      }

      .actions {
        display: grid;
        gap: 8px;
      }

      .auth-status {
        margin: 0;
        font-size: 0.85rem;
        color: #86efac;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthFormComponent {
  readonly primaryActionLabel = input.required<string>();
  readonly secondaryActionLabel = input.required<string>();
  readonly helperText = input.required<string>();
  readonly submittedAction = output<AuthFormPayload>();

  private readonly formBuilder = inject(FormBuilder);
  readonly form = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  private readonly submitState = signal<'idle' | 'login' | 'register'>('idle');
  readonly submitted = computed(() => this.submitState() !== 'idle');
  readonly statusMessage = computed(() => {
    switch (this.submitState()) {
      case 'register':
        return 'Registro exitoso. Te enviaremos un correo con los siguientes pasos.';
      case 'login':
        return 'Acceso confirmado. Estamos preparando tu panel.';
      default:
        return '';
    }
  });

  handleSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitState.set('login');
    this.submittedAction.emit({ action: 'login', ...this.form.getRawValue() });
  }

  handleSecondary(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitState.set('register');
    this.submittedAction.emit({ action: 'register', ...this.form.getRawValue() });
  }
}

export interface AuthFormPayload {
  action: 'login' | 'register';
  email: string;
  password: string;
}
