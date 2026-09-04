import { ApplicationConfig, LOCALE_ID, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withHashLocation, withInMemoryScrolling } from '@angular/router';
import { registerLocaleData } from '@angular/common';
import localeEsMx from '@angular/common/locales/es-MX';

// Sin locale registrado el pipe date escribía "13 Jan" en pantallas en español.
registerLocaleData(localeEsMx, 'es-MX');

import { routes } from './app.routes';
import { sesionCaducadaInterceptor } from './interceptors/sesion-caducada.interceptor'; // WP-I2

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withInterceptors([sesionCaducadaInterceptor])), // WP-I2: 401 → login sin perder el carrito
    // Paquete E · ronda 26 · Los enlaces con fragmento (#/modo-socio#simulador,
    // #/dashboard#comisiones) caían al inicio de la página: sin anchorScrolling,
    // "Cómo se calculan" devolvía a la misma pantalla. Y al volver de una vista
    // del back office se recupera la posición en vez de saltar arriba.
    provideRouter(
      routes,
      withHashLocation(),
      withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' })
    ),
    { provide: LOCALE_ID, useValue: 'es-MX' }
  ]
};
