import { Routes } from '@angular/router';
import { AdminComponent } from './pages/admin/admin.component';
import { CarritoComponent } from './pages/carrito/carrito.component';
import { LandingComponent } from './pages/landing/landing.component';
import { UserDashboardComponent } from './pages/user-dashboard/user-dashboard.component';

export const routes: Routes = [
  {
    path: '',
    component: LandingComponent
  },
  {
    path: 'admin',
    component: AdminComponent
  },
  {
    path: 'carrito',
    component: CarritoComponent
  },
  {
    path: 'dashboard',
    component: UserDashboardComponent
  }
];
