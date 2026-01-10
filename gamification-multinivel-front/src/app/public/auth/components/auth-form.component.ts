import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'app-auth-form',
  imports: [ReactiveFormsModule],
  template: `
    <form class="auth-form" [formGroup]="form" (ngSubmit)="handleSubmit()">
      <label class="field">
        <span class="field__label">Correo</span>
        <input
          class="field__input"
          type="email"
          autocomplete="email"
          formControlName="email"
          aria-describedby="email-help"
        />
      </label>
      <p id="email-help" class="field__hint">Usa el correo con el que te registraste.</p>

      <label class="field">
        <span class="field__label">Contraseña</span>
        <input
          class="field__input"
          type="password"
          autocomplete="current-password"
          formControlName="password"
          aria-describedby="password-help"
        />
      </label>
      <p id="password-help" class="field__hint">Mínimo 6 caracteres.</p>

      <p class="helper" aria-live="polite">{{ helperText() }}</p>

      <div class="actions">
        <button class="button button--primary" type="submit" [disabled]="form.invalid">
          {{ primaryActionLabel() }}
        </button>
        <button class="button button--ghost" type="button" (click)="handleSecondary()">
          {{ secondaryActionLabel() }}
        </button>
      </div>

      @if (submitted()) {
        <p class="status" role="status">Gracias, revisa tus datos para continuar.</p>
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

      .field__label {
        font-weight: 600;
      }

      .field__input {
        border: 1px solid #cdd5df;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 15px;
      }

      .field__input:focus-visible {
        outline: 3px solid #1f6feb;
        outline-offset: 2px;
      }

      .field__hint {
        margin: 0;
        font-size: 13px;
        color: #4b5563;
      }

      .helper {
        margin: 0;
        font-size: 14px;
        color: #374151;
      }

      .actions {
        display: grid;
        gap: 8px;
      }

      .button {
        border-radius: 999px;
        padding: 10px 16px;
        font-weight: 600;
        border: 1px solid transparent;
        cursor: pointer;
      }

      .button:focus-visible {
        outline: 3px solid #1f6feb;
        outline-offset: 2px;
      }

      .button--primary {
        background: #111827;
        color: #ffffff;
      }

      .button--primary:disabled {
        background: #9ca3af;
        cursor: not-allowed;
      }

      .button--ghost {
        background: #f9fafb;
        border-color: #d1d5db;
        color: #111827;
      }

      .status {
        margin: 0;
        font-size: 14px;
        color: #065f46;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthFormComponent {
  readonly primaryActionLabel = input.required<string>();
  readonly secondaryActionLabel = input.required<string>();
  readonly helperText = input.required<string>();

  private readonly formBuilder = inject(FormBuilder);
  readonly form = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  private readonly submitState = signal<'idle' | 'submitted'>('idle');
  readonly submitted = computed(() => this.submitState() === 'submitted');

  handleSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitState.set('submitted');
  }

  handleSecondary(): void {
    this.submitState.set('submitted');
  }
}
