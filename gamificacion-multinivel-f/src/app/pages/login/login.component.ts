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
  username = '';
  password = '';
  errorMessage = '';
  recoveryMessage = '';
  recoveryErrorMessage = '';
  recoveryEmail = '';
  isSubmitting = false;
  isRecovering = false;
  showPassword = false;
  showRecoveryForm = false;

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
      return;
    }

    this.errorMessage = '';
    this.isSubmitting = true;
    this.authService
      .login(this.username, this.password)
      .pipe(finalize(() => (this.isSubmitting = false)))
      .subscribe({
        next: (user) => {
          const target = this.authService.defaultRoute(user);
          void this.router.navigate([target]);
        },
        error: () => {
          this.errorMessage = 'Credenciales invalidas. Verifica tu correo electronico y contrasena.';
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
}
