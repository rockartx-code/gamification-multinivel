import { Routes } from '@angular/router';

import { AuthPage } from './auth/auth.page';
import { LandingPage } from './landing/landing.page';

export const publicRoutes: Routes = [
  {
    path: 'r/:refCode/:landingSlug',
    component: LandingPage,
  },
  {
    path: 'auth',
    component: AuthPage,
  },
];
