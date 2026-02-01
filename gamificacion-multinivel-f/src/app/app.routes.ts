import { Routes } from '@angular/router';

import { adminGuard, dashboardGuard, loginGuard } from './guards/auth.guard';
import { AdminComponent } from './pages/admin/admin.component';
import { CarritoComponent } from './pages/carrito/carrito.component';
import { LandingComponent } from './pages/landing/landing.component';
import { LoginComponent } from './pages/login/login.component';
import { OrderStatusComponent } from './pages/order-status/order-status.component';
import { UserDashboardComponent } from './pages/user-dashboard/user-dashboard.component';

export const routes: Routes = [
  {
    path: '',
    component: LandingComponent
  },
  {
    path: 'login',
    component: LoginComponent,
    //canActivate: [loginGuard]
  },
  {
    path: 'admin',
    component: AdminComponent,
    canActivate: [adminGuard]
  },
  {
    path: 'carrito',
    component: CarritoComponent
  },
  {
    path: 'dashboard',
    component: UserDashboardComponent,
    canActivate: [dashboardGuard]
  },
  {
    path: 'orden/:idOrden',
    component: OrderStatusComponent
  },
  {
    path: ':refToken',
    component: LandingComponent
  }
];
