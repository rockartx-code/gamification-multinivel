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
import { ModoSocioComponent } from './pages/modo-socio/modo-socio.component'; // paquete B

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
    // Galería interna de componentes (styleguide); sin enlaces de navegación.
    path: 'galeria',
    loadComponent: () => import('./pages/galeria/galeria.component').then((m) => m.GaleriaComponent)
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
  },
  {
    // Paquete B: landing pública "Modo socio" (el plan completo y el botón para activarlo).
    path: 'modo-socio',
    component: ModoSocioComponent
  },
  {
    // Paquete D · despacho en bloque con lista de surtido
    path: 'admin/despacho',
    loadComponent: () => import('./pages/admin/despacho/despacho.component').then((m) => m.DespachoComponent),
    canActivate: [adminGuard]
  },
  {
    // Paquete D · resumen automático de turno
    path: 'admin/resumen-turno',
    loadComponent: () => import('./pages/admin/resumen-turno/resumen-turno.component').then((m) => m.ResumenTurnoComponent),
    canActivate: [adminGuard]
  },
  {
    // Paquete F · coach-seguimiento: "Seguimiento de hoy" (lista priorizada + WhatsApp con nota).
    path: 'admin/seguimiento',
    loadComponent: () => import('./pages/admin/seguimiento/admin-seguimiento.component').then((m) => m.AdminSeguimientoComponent),
    canActivate: [adminGuard]
  },

  // ── Paquete D · ronda 26 · ayuda, contacto, sucursales, facturación y devoluciones ──
  // Julio tuvo que crear una cuenta y verificar su correo para hallar el teléfono
  // de la tienda a la que ya le había pagado $1,209; Aurora probó cuatro rutas y
  // las cuatro rebotaban a la tienda. Todas son públicas: quien ya pagó no
  // debería necesitar sesión para reclamar.
  {
    path: 'ayuda',
    loadComponent: () => import('./pages/ayuda/ayuda.component').then((m) => m.AyudaComponent),
    data: { seccion: 'ayuda' }
  },
  {
    path: 'contacto',
    loadComponent: () => import('./pages/ayuda/ayuda.component').then((m) => m.AyudaComponent),
    data: { seccion: 'contacto' }
  },
  {
    path: 'sucursales',
    loadComponent: () => import('./pages/ayuda/ayuda.component').then((m) => m.AyudaComponent),
    data: { seccion: 'sucursales' }
  },
  {
    path: 'facturacion',
    loadComponent: () => import('./pages/ayuda/ayuda.component').then((m) => m.AyudaComponent),
    data: { seccion: 'facturacion' }
  },
  {
    // Pantalla propia: es la más larga y la que enlazan los correos.
    path: 'devoluciones',
    loadComponent: () => import('./pages/devoluciones/devoluciones.component').then((m) => m.DevolucionesComponent)
  },
  {
    // Alias que la gente escribió a mano y rebotaba a la tienda.
    path: 'soporte',
    redirectTo: 'ayuda'
  },
  {
    // Comodín: una URL mal escrita cae en Ayuda con el aviso, nunca en un
    // contenedor vacío ni en la tienda. Va al final del arreglo a propósito.
    path: '**',
    loadComponent: () => import('./pages/ayuda/ayuda.component').then((m) => m.AyudaComponent),
    data: { seccion: 'ayuda', noEncontrada: true }
  }
];
