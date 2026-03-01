import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService, AuthUser } from '../services/auth.service';

const userHome = (auth: AuthService, user: AuthUser): string => (auth.hasAdminPanelAccess(user) ? '/admin' : '/dashboard');

export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  return router.parseUrl(userHome(auth, auth.currentUser));
};

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return router.parseUrl('/login');
  }

  if (!auth.hasAdminPanelAccess(auth.currentUser)) {
    return router.parseUrl(userHome(auth, auth.currentUser));
  }

  return true;
};

export const dashboardGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  if (auth.hasAdminPanelAccess(auth.currentUser)) {
    return router.parseUrl('/admin');
  }

  return true;
};
