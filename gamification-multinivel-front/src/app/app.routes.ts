import { Routes } from '@angular/router';

import { adminGuard, publicGuard, userGuard } from './core/guards/role.guard';

export const routes: Routes = [
  {
    path: 'dashboard',
    canMatch: [userGuard],
    loadChildren: () => import('./dashboard/dashboard.routes').then((m) => m.dashboardRoutes),
  },
  {
    path: 'admin',
    canMatch: [adminGuard],
    loadChildren: () => import('./admin/admin.routes').then((m) => m.adminRoutes),
  },
  {
    path: '',
    canMatch: [publicGuard],
    loadChildren: () => import('./public/public.routes').then((m) => m.publicRoutes),
  },
];
