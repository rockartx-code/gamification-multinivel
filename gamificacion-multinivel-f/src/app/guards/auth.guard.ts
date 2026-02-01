import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../services/auth.service';

const roleHome = (role: 'admin' | 'cliente'): string => (role === 'admin' ? '/admin' : '/dashboard');

export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  return router.parseUrl(roleHome(auth.currentUser.role));
};

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return router.parseUrl('/login');
  }

  if (auth.currentUser.role !== 'admin') {
    return router.parseUrl(roleHome(auth.currentUser.role));
  }

  return true;
};

export const dashboardGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  if (auth.currentUser.role !== 'cliente') {
    return router.parseUrl(roleHome(auth.currentUser.role));
  }

  return true;
};
