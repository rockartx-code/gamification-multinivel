import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFooterComponent, UiFormFieldComponent, UiHeaderComponent],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.css'
})
export class ResetPasswordComponent implements OnInit {
  email = '';
  otp = '';
  password = '';
  confirmPassword = '';
  errorMessage = '';
  successMessage = '';
  isSubmitting = false;
  showPassword = false;
  showConfirmPassword = false;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.email = (this.route.snapshot.queryParamMap.get('email') ?? '').trim();
    this.otp = (this.route.snapshot.queryParamMap.get('otp') ?? '').trim();
  }

  submit(): void {
    if (!this.email || !this.otp || !this.password || !this.confirmPassword) {
      this.errorMessage = 'Completa correo, OTP, nueva contrasena y confirmacion.';
      this.successMessage = '';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.authService
      .resetPassword({
        email: this.email.trim(),
        otp: this.otp.trim(),
        password: this.password,
        confirmPassword: this.confirmPassword
      })
      .pipe(finalize(() => (this.isSubmitting = false)))
      .subscribe({
        next: (response) => {
          this.successMessage = response.message;
          this.errorMessage = '';
          this.cdr.detectChanges();
          setTimeout(() => {
            void this.router.navigate(['/login']);
          }, 1200);
        },
        error: (error: { error?: { message?: string }; message?: string }) => {
          this.errorMessage =
            error?.error?.message || error?.message || 'No se pudo actualizar la contrasena.';
          this.successMessage = '';
          this.cdr.detectChanges();
        }
      });
  }

  togglePasswordVisibility(field: 'password' | 'confirm'): void {
    if (field === 'password') {
      this.showPassword = !this.showPassword;
      return;
    }
    this.showConfirmPassword = !this.showConfirmPassword;
  }
}
