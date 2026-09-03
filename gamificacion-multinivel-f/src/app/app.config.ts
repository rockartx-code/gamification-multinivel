import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withHashLocation } from '@angular/router';

import { routes } from './app.routes';
import { sesionCaducadaInterceptor } from './interceptors/sesion-caducada.interceptor'; // WP-I2

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withInterceptors([sesionCaducadaInterceptor])), // WP-I2: 401 → login sin perder el carrito
    provideRouter(routes, withHashLocation())
  ]
};
