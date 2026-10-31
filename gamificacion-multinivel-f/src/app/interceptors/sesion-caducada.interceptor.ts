import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';

/**
 * Ola B · I2: sesión de punta a punta.
 *
 * Cuando el servidor responde 401 a una petición que llevaba la sesión
 * (`Authorization: Bearer …`), la sesión guardada ya no sirve (caducó el TTL o
 * se cerró en otro lado). Antes el panel se quedaba "muerto" con toasts de
 * error; ahora se borra la sesión y se vuelve al login con `?next=` a la misma
 * pantalla y el aviso "tu carrito sigue guardado" (el carrito vive en
 * localStorage y no se toca).
 *
 * No actúa sobre las rutas de `/auth/` (un login con contraseña equivocada
 * también es 401 y debe mostrar su propio mensaje).
 */
export const sesionCaducadaInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  return next(req).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        req.headers.has('Authorization') &&
        !req.url.includes('/auth/') &&
        auth.currentUser
      ) {
        const actual = router.url || '/';
        auth.logout();
        const destino = actual.startsWith('/login') ? undefined : actual;
        void router.navigate(['/login'], { queryParams: { motivo: 'sesion', ...(destino ? { next: destino } : {}) } });
      }
      return throwError(() => error);
    })
  );
};
