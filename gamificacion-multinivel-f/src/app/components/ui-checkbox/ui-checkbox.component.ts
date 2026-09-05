import { CommonModule } from '@angular/common';
import { booleanAttribute, Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Casilla del sistema. Sustituye a los <input type="checkbox"> nativos
 * (que se pintaban con el azul del navegador dentro de la paleta oro/bosque).
 * Mantiene un input real oculto para conservar teclado y lectores de pantalla.
 *
 *   layout 'inline': [casilla] Etiqueta        (por defecto)
 *   layout 'row'   : Etiqueta ............ [casilla]
 *
 * Los booleanos usan booleanAttribute, así que admiten tanto la forma
 * abreviada (<ui-checkbox compact>) como valores opcionales del modelo
 * (`boolean | undefined` llega como false en lugar de romper strictTemplates).
 */
@Component({
  selector: 'ui-checkbox',
  standalone: true,
  imports: [CommonModule],
  host: { class: 'ui-check-host' },
  template: `
    <label class="ui-check" [class.ui-check-row]="layout === 'row'" [class.ui-check-disabled]="disabled">
      <input
        type="checkbox"
        class="check-input"
        [checked]="checked"
        [disabled]="disabled"
        [attr.aria-label]="ariaLabel || null"
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
  @Input({ transform: booleanAttribute }) checked = false;
  @Input({ transform: booleanAttribute }) disabled = false;
  @Input({ transform: booleanAttribute }) compact = false;
  @Input() label = '';
  @Input() description = '';
  /** Nombre accesible cuando la etiqueta visible vive fuera del componente. */
  @Input() ariaLabel = '';
  @Input() layout: 'inline' | 'row' = 'inline';

  @Output() checkedChange = new EventEmitter<boolean>();

  onToggle(event: Event): void {
    if (this.disabled) {
      return;
    }
    this.checkedChange.emit((event.target as HTMLInputElement).checked);
  }
}
