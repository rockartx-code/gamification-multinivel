import { Routes } from '@angular/router';

export const storeRoutes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'catalogo',
  },
  {
    path: 'catalogo',
    loadComponent: () => import('./catalog/catalog.page').then((m) => m.CatalogPage),
  },
  {
    path: 'carrito',
    loadComponent: () => import('./cart/cart.page').then((m) => m.CartPage),
  },
  {
    path: 'cotizacion',
    loadComponent: () => import('./quote/quote.page').then((m) => m.QuotePage),
  },
  {
    path: 'checkout',
    loadComponent: () => import('./checkout/checkout.page').then((m) => m.CheckoutPage),
  },
];
