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
    path: 'store',
    canMatch: [userGuard],
    loadChildren: () => import('./store/store.routes').then((m) => m.storeRoutes),
  },
  {
    path: '',
    canMatch: [publicGuard],
    loadChildren: () => import('./public/public.routes').then((m) => m.publicRoutes),
  },
];
