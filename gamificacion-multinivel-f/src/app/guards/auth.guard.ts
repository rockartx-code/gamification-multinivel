import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { ADMIN_EXTRA_ROUTE_PRIVILEGE, AdminViewId, SCREEN_PRIVILEGE_BY_VIEW } from '../models/privileges.model';
import { AccesoPantallaService } from '../services/acceso-pantalla.service';
import { AuthService, AuthUser } from '../services/auth.service';

const userHome = (auth: AuthService, user: AuthUser): string => auth.defaultRoute(user);

export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  return router.parseUrl(userHome(auth, auth.currentUser));
};

export const adminGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return router.parseUrl('/login');
  }

  if (!auth.hasAdminPanelAccess(auth.currentUser)) {
    return router.parseUrl(userHome(auth, auth.currentUser));
  }

  // Paquete E · ronda 26 · `#/admin` a secas no abre una pantalla fija: manda a
  // la de esta persona. Los cinco empleados tienen `access_screen_orders`, así
  // que los cinco caían en Pedidos —"si yo fuera menos necio me voy a la bodega
  // a barrer" (Toño)—, y la cajera empezaba su turno a tres clics de su caja.
  if (route.routeConfig?.path === 'admin') {
    return router.parseUrl(auth.adminLandingRoute(auth.currentUser));
  }

  return true;
};

/**
 * Paquete E · ronda 26 · Cada pantalla del back office tiene URL propia; sin
 * esta guarda, cualquiera con acceso al panel escribiría `#/admin/configuracion`
 * a mano. Lee `data.view` de la ruta (o su ruta literal, para las pantallas que
 * son componentes aparte) y comprueba el privilegio de esa pantalla.
 */
export const adminViewGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const user = auth.currentUser;

  if (!user) {
    return router.parseUrl('/login');
  }

  const view = route.data?.['view'] as AdminViewId | undefined;
  const ruta = '/' + (state.url.split('?')[0] || '').replace(/^\/+/, '');
  // Comisiones y pagos vive dentro de la vista Clientes pero exige su propio
  // privilegio: la tabla de rutas manda sobre el privilegio de la vista.
  const privilegio = ADMIN_EXTRA_ROUTE_PRIVILEGE[ruta] ?? (view ? SCREEN_PRIVILEGE_BY_VIEW[view] : null);

  if (privilegio && !auth.hasPrivilege(privilegio, user)) {
    // Nunca se deja el contenedor vacío: se cae a la pantalla que sí es suya y
    // se DICE en pantalla cuál se quiso abrir, en vez de quitarla en silencio.
    // El aviso se anota en el servicio —lo lee `ui-aviso-sin-acceso` monte donde
    // monte, también en Despacho y en Seguimiento— y además viaja en la URL,
    // para que sobreviva a una recarga completa.
    const destino = auth.adminLandingRoute(user);
    const titulo = (route.data?.['titulo'] as string | undefined) ?? '';
    inject(AccesoPantallaService).anotar(titulo);
    return router.createUrlTree([destino === ruta ? '/admin/pedidos' : destino],
                                titulo ? { queryParams: { sinAcceso: titulo } } : {});
  }

  inject(AccesoPantallaService).navegacionPermitida();
  return true;
};

export const dashboardGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.currentUser) {
    return true;
  }

  if (!auth.hasUserDashboardAccess(auth.currentUser) && auth.hasAdminPanelAccess(auth.currentUser)) {
    return router.parseUrl('/admin');
  }

  return true;
};
