import { Routes } from '@angular/router';

import { AdminPage } from './admin.page';

export const adminRoutes: Routes = [
  {
    path: '',
    component: AdminPage,
  },
  {
    path: 'landings',
    loadChildren: () => import('./landings/landings.routes').then((m) => m.landingsRoutes),
  },
];
