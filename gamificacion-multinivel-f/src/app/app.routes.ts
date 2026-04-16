import { Routes } from '@angular/router';

import { adminGuard, dashboardGuard, loginGuard } from './guards/auth.guard';
import { AdminComponent } from './pages/admin/admin.component';
import { CarritoComponent } from './pages/carrito/carrito.component';
import { LandingComponent } from './pages/landing/landing.component';
import { LoginComponent } from './pages/login/login.component';
import { OrderCancelacionComponent } from './pages/order-cancelacion/order-cancelacion.component';
import { OrderDevolucionComponent } from './pages/order-devolucion/order-devolucion.component';
import { OrderStatusComponent } from './pages/order-status/order-status.component';
import { ResetPasswordComponent } from './pages/reset-password/reset-password.component';
import { UserDashboardComponent } from './pages/user-dashboard/user-dashboard.component';
import { UserProfileComponent } from './pages/user-profile/user-profile.component';
import { TiendaComponent } from './pages/tienda/tienda.component';
import { VerifyEmailComponent } from './pages/verify-email/verify-email.component';

export const routes: Routes = [
  {
    path: '',
    component: UserDashboardComponent
  },
  {
    path: 'login',
    component: LoginComponent,
    //canActivate: [loginGuard]
  },
  {
    path: 'recuperar-contrasena',
    component: ResetPasswordComponent
  },
  {
    path: 'verificar-email',
    component: VerifyEmailComponent
  },
  {
    path: 'verify-email',
    component: VerifyEmailComponent
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
    path: 'perfil',
    component: UserProfileComponent,
    canActivate: [dashboardGuard]
  },
  {
    path: 'orden/:idOrden',
    component: OrderStatusComponent
  },
  {
    path: 'orden/:idOrden/cancelar',
    component: OrderCancelacionComponent
  },
  {
    path: 'orden/:idOrden/devolucion',
    component: OrderDevolucionComponent
  },
  {
    path: 'tienda',
    component: TiendaComponent
  },
  {
    path: 'tienda/:refToken',
    component: TiendaComponent
  },
  {
    path: 'landing/:idSponsor',
    component: LandingComponent
  },
  {
    path: 'landing',
    component: LandingComponent
  }
];
