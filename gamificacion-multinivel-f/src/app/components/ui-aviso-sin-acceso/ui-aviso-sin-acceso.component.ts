import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { AccesoPantallaService } from '../../services/acceso-pantalla.service';
import { UiButtonComponent } from '../ui-button/ui-button.component';

/**
 * «Configuración no está entre tus pantallas. Te dejamos en Punto de Venta.»
 *
 * Una pantalla que no te toca no se quita en silencio ni deja el contenedor
 * vacío (§3.5). El aviso lo anota `adminViewGuard` en `AccesoPantallaService`,
 * así que se pinta igual navegando dentro del panel o aterrizando en Despacho o
 * en Seguimiento, que son componentes aparte.
 */
@Component({
  selector: 'ui-aviso-sin-acceso',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  template: `
    <div *ngIf="(acceso.pantallaSinAcceso$ | async) as pantalla"
      class="flex items-start justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="status" aria-live="polite">
      <div>
        <span class="font-semibold">{{ pantalla }} no está entre tus pantallas.</span>
        {{ dondeQuedaste }} Si necesitas entrar, pídeselo a quien administra los permisos.
      </div>
      <ui-button size="sm" variant="ghost" ariaLabel="Cerrar el aviso" (pressed)="acceso.limpiar()">
        <i class="fa-solid fa-xmark" aria-hidden="true"></i>
      </ui-button>
    </div>
  `
})
export class UiAvisoSinAccesoComponent {
  /** Nombre de la pantalla en la que se quedó la persona. */
  @Input() pantallaActual = '';

  constructor(readonly acceso: AccesoPantallaService) {}

  get dondeQuedaste(): string {
    return this.pantallaActual ? `Te dejamos en ${this.pantallaActual}.` : '';
  }
}
