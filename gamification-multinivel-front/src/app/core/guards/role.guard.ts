import { inject } from '@angular/core';
import { CanMatchFn } from '@angular/router';

import { UserRole } from '../../domain/models';
import { AuthService } from '../../services/auth.service';

const resolveRole = (): UserRole => {
  const authService = inject(AuthService);
  return authService.getSession()?.role ?? 'public';
};

export const publicGuard: CanMatchFn = () => {
  const authService = inject(AuthService);
  authService.validateSession();
  return true;
};

export const userGuard: CanMatchFn = () => {
  const role = resolveRole();
  return role === 'user' || role === 'admin';
};

export const adminGuard: CanMatchFn = () => {
  const role = resolveRole();
  return role === 'admin';
};
