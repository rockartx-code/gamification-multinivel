import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username = '';
  password = '';
  errorMessage = '';
  isSubmitting = false;

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  login(): void {
    if (!this.username || !this.password) {
      this.errorMessage = 'Ingresa tu usuario y contraseña.';
      return;
    }

    this.errorMessage = '';
    this.isSubmitting = true;
    this.authService
      .login(this.username, this.password)
      .pipe(finalize(() => (this.isSubmitting = false)))
      .subscribe({
        next: (user) => {
          const target = user.role === 'admin' ? '/admin' : '/dashboard';
          this.router.navigate([target]);
        },
        error: () => {
          this.errorMessage = 'Credenciales inválidas. Verifica tu usuario y contraseña.';
        }
      });
  }
}
