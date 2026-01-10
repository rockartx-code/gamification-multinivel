import { Routes } from '@angular/router';

import { DashboardPage } from './dashboard.page';

export const dashboardRoutes: Routes = [
  {
    path: '',
    component: DashboardPage,
  },
  {
    path: 'orders',
    loadComponent: () => import('./pages/orders.page').then((m) => m.OrdersPage),
  },
  {
    path: 'commissions',
    loadComponent: () =>
      import('./pages/commissions.page').then((m) => m.CommissionsPage),
  },
  {
    path: 'network',
    loadComponent: () => import('./pages/network.page').then((m) => m.NetworkPage),
  },
  {
    path: 'landings',
    loadComponent: () => import('./pages/landings.page').then((m) => m.LandingsPage),
  },
];
