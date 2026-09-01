import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Casilla del sistema. Sustituye a los <input type="checkbox"> nativos
 * (que se pintaban con el azul del navegador dentro de la paleta oro/bosque).
 * Mantiene un input real oculto para conservar teclado y lectores de pantalla.
 *
 *   layout 'inline': [casilla] Etiqueta        (por defecto)
 *   layout 'row'   : Etiqueta ............ [casilla]
 */
@Component({
  selector: 'ui-checkbox',
  standalone: true,
  imports: [CommonModule],
  template: `
    <label class="ui-check" [class.ui-check-row]="layout === 'row'" [class.ui-check-disabled]="disabled">
      <input
        type="checkbox"
        class="check-input"
        [checked]="checked"
        [disabled]="disabled"
        (change)="onToggle($event)" />
      <span class="check-box" aria-hidden="true">
        <i class="fa-solid fa-check text-[10px]"></i>
      </span>
      <span class="min-w-0">
        <span class="block" [class.text-sm]="!compact" [class.text-xs]="compact">
          <ng-content></ng-content>{{ label }}
        </span>
        <span *ngIf="description" class="mt-0.5 block text-xs text-gray-500">{{ description }}</span>
      </span>
    </label>
  `
})
export class UiCheckboxComponent {
  @Input() checked = false;
  @Input() label = '';
  @Input() description = '';
  @Input() disabled = false;
  @Input() compact = false;
  @Input() layout: 'inline' | 'row' = 'inline';

  @Output() checkedChange = new EventEmitter<boolean>();

  onToggle(event: Event): void {
    if (this.disabled) {
      return;
    }
    this.checkedChange.emit((event.target as HTMLInputElement).checked);
  }
}
