import { isPlatformBrowser } from '@angular/common';
import { inject, PLATFORM_ID } from '@angular/core';
import { CanMatchFn } from '@angular/router';

export type Role = 'public' | 'user' | 'admin';

const resolveRole = (): Role => {
  const platformId = inject(PLATFORM_ID);

  if (!isPlatformBrowser(platformId)) {
    return 'public';
  }

  const storedRole = window.localStorage.getItem('role');

  if (storedRole === 'admin' || storedRole === 'user' || storedRole === 'public') {
    return storedRole;
  }

  return 'public';
};

export const publicGuard: CanMatchFn = () => true;

export const userGuard: CanMatchFn = () => {
  const role = resolveRole();
  return role === 'user' || role === 'admin';
};

export const adminGuard: CanMatchFn = () => {
  const role = resolveRole();
  return role === 'admin';
};
