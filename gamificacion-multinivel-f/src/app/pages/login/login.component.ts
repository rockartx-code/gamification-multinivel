import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService, UserRole } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  selectedRole: UserRole = 'cliente';

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  setRole(role: UserRole): void {
    this.selectedRole = role;
  }

  login(): void {
    const user = this.authService.loginAs(this.selectedRole);
    const target = user.role === 'admin' ? '/admin' : '/dashboard';
    this.router.navigate([target]);
  }
}
