import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  private readonly confirmationRequiredMessage = 'Confirma tu cuenta desde tu correo electronico para iniciar sesion.';

  username = '';
  password = '';
  errorMessage = '';
  resendMessage = '';
  resendErrorMessage = '';
  recoveryMessage = '';
  recoveryErrorMessage = '';
  recoveryEmail = '';
  isSubmitting = false;
  isResendingConfirmation = false;
  isRecovering = false;
  showPassword = false;
  showRecoveryForm = false;

  get shouldShowResendConfirmation(): boolean {
    return this.errorMessage === this.confirmationRequiredMessage;
  }

  get usernameError(): string {
    if (this.errorMessage && !this.username) {
      return 'Ingresa tu correo electronico.';
    }
    return '';
  }

  get passwordError(): string {
    if (this.errorMessage && !this.password) {
      return 'Ingresa tu contrasena.';
    }
    return '';
  }

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  login(): void {
    if (!this.username || !this.password) {
      this.errorMessage = 'Ingresa tu correo electronico y contrasena.';
      this.resendMessage = '';
      this.resendErrorMessage = '';
      return;
    }

    this.errorMessage = '';
    this.resendMessage = '';
    this.resendErrorMessage = '';
    this.isSubmitting = true;
    this.authService
      .login(this.username, this.password)
      .pipe(finalize(() => (this.isSubmitting = false)))
      .subscribe({
        next: (user) => {
          const target = this.authService.defaultRoute(user);
          void this.router.navigate([target]);
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.errorMessage =
            error?.error?.message || error?.message || 'Credenciales invalidas. Verifica tu correo electronico y contrasena.';
          this.cdr.detectChanges();
        }
      });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  openRecoveryForm(): void {
    this.showRecoveryForm = true;
    this.errorMessage = '';
    this.resendMessage = '';
    this.resendErrorMessage = '';
  }

  openLoginForm(): void {
    this.showRecoveryForm = false;
    this.recoveryErrorMessage = '';
    this.recoveryMessage = '';
  }

  requestPasswordRecovery(): void {
    if (!this.recoveryEmail.trim()) {
      this.recoveryErrorMessage = 'Ingresa tu correo electronico para recuperar la contrasena.';
      this.recoveryMessage = '';
      return;
    }

    this.isRecovering = true;
    this.recoveryErrorMessage = '';
    this.recoveryMessage = '';

    this.authService
      .requestPasswordRecovery(this.recoveryEmail.trim())
      .pipe(finalize(() => (this.isRecovering = false)))
      .subscribe({
        next: (response) => {
          this.recoveryMessage = response.message;
          this.recoveryErrorMessage = '';
          this.cdr.detectChanges();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.recoveryErrorMessage =
            error?.error?.message || error?.message || 'No se pudo enviar el codigo OTP.';
          this.recoveryMessage = '';
          this.cdr.detectChanges();
        }
      });
  }

  resendConfirmationEmail(): void {
    const email = this.username.trim();
    if (!email) {
      this.resendErrorMessage = 'Ingresa tu correo electronico para reenviar la confirmacion.';
      this.resendMessage = '';
      return;
    }

    this.isResendingConfirmation = true;
    this.resendErrorMessage = '';
    this.resendMessage = '';

    this.authService
      .resendEmailConfirmation(email)
      .pipe(finalize(() => (this.isResendingConfirmation = false)))
      .subscribe({
        next: (response) => {
          this.resendMessage = response.message;
          this.resendErrorMessage = '';
          this.cdr.detectChanges();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.resendErrorMessage =
            error?.error?.message || error?.message || 'No se pudo reenviar el correo de confirmacion.';
          this.resendMessage = '';
          this.cdr.detectChanges();
        }
      });
  }
}
