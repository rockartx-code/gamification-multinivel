import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiCheckboxComponent } from '../../components/ui-checkbox/ui-checkbox.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { AuthService } from '../../services/auth.service';

type LoginPanel = 'login' | 'recovery' | 'link';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiCheckboxComponent, UiFormFieldComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent implements OnInit {
  private readonly confirmationRequiredMessage = 'Confirma tu cuenta desde tu correo electrónico para iniciar sesion.';

  username = '';
  password = '';
  /** Marcada por omisión: 30 días sin volver a escribir la contraseña (docs/qa/22 §6 tarea 9). */
  rememberMe = true;
  errorMessage = '';
  resendMessage = '';
  resendErrorMessage = '';
  recoveryMessage = '';
  recoveryErrorMessage = '';
  recoveryEmail = '';
  linkEmail = '';
  linkMessage = '';
  linkErrorMessage = '';
  /** Estado del canje del enlace `?enlace=TOKEN`. */
  linkRedeemStatus: '' | 'redeeming' | 'error' = '';
  isSubmitting = false;
  isResendingConfirmation = false;
  isRecovering = false;
  isRequestingLink = false;
  panel: LoginPanel = 'login';

  /** El backend manda code EMAIL_NOT_VERIFIED; comparar textos fallaba por un acento ("sesion" vs "sesión"). */
  needsEmailConfirmation = false;

  get showRecoveryForm(): boolean {
    return this.panel === 'recovery';
  }

  get showLinkForm(): boolean {
    return this.panel === 'link';
  }

  get rememberMeDescription(): string {
    return this.rememberMe
      ? 'Tu sesión dura 30 días en este dispositivo. Desmárcala en una computadora compartida.'
      : 'Tu sesión dura 24 horas y se cierra al cerrar el navegador.';
  }

  get shouldShowResendConfirmation(): boolean {
    return this.needsEmailConfirmation || this.errorMessage === this.confirmationRequiredMessage;
  }

  get usernameError(): string {
    if (this.errorMessage && !this.username) {
      return 'Ingresa tu correo electrónico.';
    }
    return '';
  }

  get passwordError(): string {
    if (this.errorMessage && !this.password) {
      return 'Ingresa tu contraseña.';
    }
    return '';
  }

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly route: ActivatedRoute,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const enlace = (this.route.snapshot.queryParamMap.get('enlace') ?? '').trim();
    if (enlace) {
      this.redeemLink(enlace);
      return;
    }
    // Con sesión vigente, /#/login mandaba al login otra vez ("pensé que había perdido el acceso admin").
    // Solo se salta con sesiones que declaran su vencimiento (las abiertas con "Recordarme" o enlace).
    if (this.authService.hasSession && this.authService.currentUser?.expiresAt) {
      void this.router.navigate([this.authService.defaultRoute()]);
    }
  }

  trackingFolio = '';

  /** Seguimiento de un pedido hecho sin cuenta, por folio. */
  trackOrder(): void {
    const folio = this.trackingFolio.trim().toUpperCase();
    if (!folio) {
      return;
    }
    void this.router.navigate(['/orden', folio]);
  }

  login(): void {
    if (!this.username || !this.password) {
      this.errorMessage = 'Ingresa tu correo electrónico y contraseña.';
      this.resendMessage = '';
      this.resendErrorMessage = '';
      return;
    }

    this.errorMessage = '';
    this.resendMessage = '';
    this.resendErrorMessage = '';
    this.needsEmailConfirmation = false;
    this.isSubmitting = true;
    this.authService
      .login(this.username, this.password, this.rememberMe)
      .pipe(finalize(() => {
        this.isSubmitting = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (user) => {
          const target = this.authService.defaultRoute(user);
          void this.router.navigate([target]);
        },
        error: (error: { status?: number; error?: { message?: string; code?: string }; message?: string }) => {
          this.errorMessage =
            error?.error?.message || error?.message || 'Credenciales invalidas. Verifica tu correo electrónico y contraseña.';
          const mensaje = (error?.error?.message || '').toLowerCase();
          this.needsEmailConfirmation =
            error?.error?.code === 'EMAIL_NOT_VERIFIED' || (error?.status === 403 && mensaje.includes('confirma tu cuenta'));
          this.cdr.detectChanges();
        }
      });
  }

  openRecoveryForm(): void {
    this.panel = 'recovery';
    this.errorMessage = '';
    this.resendMessage = '';
    this.resendErrorMessage = '';
  }

  openLinkForm(): void {
    this.panel = 'link';
    this.linkEmail = this.linkEmail || this.username.trim();
    this.linkMessage = '';
    this.linkErrorMessage = '';
    this.errorMessage = '';
  }

  openLoginForm(): void {
    this.panel = 'login';
    this.recoveryErrorMessage = '';
    this.recoveryMessage = '';
    this.linkMessage = '';
    this.linkErrorMessage = '';
  }

  requestLoginLink(): void {
    const email = this.linkEmail.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this.linkErrorMessage = 'Escribe el correo con el que te registraste.';
      this.linkMessage = '';
      return;
    }
    this.isRequestingLink = true;
    this.linkErrorMessage = '';
    this.linkMessage = '';
    this.authService
      .requestLoginLink(email, this.rememberMe)
      .pipe(finalize(() => {
        this.isRequestingLink = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (response) => {
          this.linkMessage = `${response.message} El enlace sirve una sola vez y caduca en 15 minutos.`;
          this.cdr.detectChanges();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.linkErrorMessage = error?.error?.message || error?.message || 'No se pudo enviar el enlace. Intenta de nuevo.';
          this.cdr.detectChanges();
        }
      });
  }

  private redeemLink(token: string): void {
    this.linkRedeemStatus = 'redeeming';
    this.authService
      .loginWithLink(token, true)
      .pipe(finalize(() => this.cdr.markForCheck()))
      .subscribe({
        next: (user) => {
          void this.router.navigate([this.authService.defaultRoute(user)]);
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.linkRedeemStatus = 'error';
          this.panel = 'link';
          this.linkErrorMessage =
            error?.error?.message || 'El enlace ya no sirve (se usó o caducó). Pide uno nuevo con tu correo.';
          this.cdr.detectChanges();
        }
      });
  }

  requestPasswordRecovery(): void {
    if (!this.recoveryEmail.trim()) {
      this.recoveryErrorMessage = 'Ingresa tu correo electrónico para recuperar la contraseña.';
      this.recoveryMessage = '';
      return;
    }

    this.isRecovering = true;
    this.recoveryErrorMessage = '';
    this.recoveryMessage = '';

    this.authService
      .requestPasswordRecovery(this.recoveryEmail.trim())
      .pipe(finalize(() => {
        this.isRecovering = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (response) => {
          this.recoveryMessage = response.message;
          this.recoveryErrorMessage = '';
          this.cdr.detectChanges();
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.recoveryErrorMessage =
            error?.error?.message || error?.message || 'No se pudo enviar el código.';
          this.recoveryMessage = '';
          this.cdr.detectChanges();
        }
      });
  }

  resendConfirmationEmail(): void {
    const email = this.username.trim();
    if (!email) {
      this.resendErrorMessage = 'Ingresa tu correo electrónico para reenviar la confirmacion.';
      this.resendMessage = '';
      return;
    }

    this.isResendingConfirmation = true;
    this.resendErrorMessage = '';
    this.resendMessage = '';

    this.authService
      .resendEmailConfirmation(email)
      .pipe(finalize(() => {
        this.isResendingConfirmation = false;
        this.cdr.markForCheck();
      }))
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
