import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Tarjeta seleccionable del sistema (tipo de entrega, sucursal, método de
 * pago, dirección, paquetería…). Antes duplicada a mano en 5+ bloques del
 * carrito con las mismas clases. Proyecta su contenido y pinta el estado
 * seleccionado + indicador de check de forma consistente.
 */
@Component({
  selector: 'ui-choice-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      type="button"
      role="radio"
      [attr.aria-checked]="selected"
      [disabled]="disabled"
      class="choice-card w-full rounded-2xl border p-3 transition"
      [ngClass]="[
        layout === 'stack' ? 'flex flex-col items-center gap-2 text-center' : 'block text-left',
        selected ? 'choice-card-selected border-gold bg-ivory-80' : 'border-olive-30 surface-soft hover:bg-ivory-80'
      ]"
      (click)="onSelect()">
      <ng-content></ng-content>
      <i *ngIf="layout === 'stack'" class="fa-solid text-sm"
        [ngClass]="selected ? 'fa-circle-check text-gold' : 'fa-circle text-gray-300'"
        aria-hidden="true"></i>
    </button>
  `
})
export class UiChoiceCardComponent {
  @Input() selected = false;
  @Input() disabled = false;
  /** 'stack': contenido centrado en columna con check abajo. 'row': contenido libre a la izquierda. */
  @Input() layout: 'stack' | 'row' = 'row';

  @Output() pressed = new EventEmitter<void>();

  onSelect(): void {
    if (!this.disabled) {
      this.pressed.emit();
    }
  }
}
