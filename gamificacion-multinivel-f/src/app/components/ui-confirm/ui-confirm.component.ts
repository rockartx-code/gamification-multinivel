import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { UiFormFieldComponent } from '../ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../ui-modal/ui-modal.component';

/**
 * Confirmación con el efecto escrito (I1, propuesta 10). Sustituye a los
 * `prompt()`/`confirm()` del navegador: "Recibir no hizo nada visible" (Beto),
 * "¿esto anula el comprobante?" (Sofía). Dice qué va a pasar, pide el motivo
 * cuando hace falta y, al terminar, muestra lo que el servidor guardó
 * (`result`) en lugar de lo que se escribió en el formulario.
 */
@Component({
  selector: 'ui-confirm',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent, UiModalComponent],
  templateUrl: './ui-confirm.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiConfirmComponent {
  @Input() isOpen = false;
  @Input() title = '¿Confirmar?';
  /** Qué va a pasar si se confirma, en una o dos frases. */
  @Input() effect = '';
  @Input() requireReason = false;
  @Input() reasonLabel = 'Motivo';
  @Input() reasonPlaceholder = 'Escribe por qué (queda guardado con la acción)';
  @Input() confirmLabel = 'Confirmar';
  @Input() cancelLabel = 'Cancelar';
  /** Acción irreversible o que quita algo: pinta el efecto en rojo. */
  @Input() danger = false;
  /** Mientras se guarda: bloquea botones y cierre. */
  @Input() busy = false;
  @Input() busyLabel = 'Guardando…';
  @Input() error = '';
  /** Lo que el servidor guardó; cuando existe, el diálogo pasa a "Listo". */
  @Input() result: string | null = null;
  @Input() resultTitle = 'Listo';
  /** Motivo por el que no se puede confirmar todavía (además del motivo vacío). */
  @Input() blockReason = '';

  @Output() confirmed = new EventEmitter<string>();
  @Output() cancelled = new EventEmitter<void>();

  reason = '';

  get reasonMissing(): boolean {
    return this.requireReason && !this.reason.trim();
  }

  get disabledReason(): string {
    if (this.busy) {
      return this.busyLabel;
    }
    if (this.blockReason) {
      return this.blockReason;
    }
    if (this.reasonMissing) {
      return 'Escribe el motivo para poder continuar.';
    }
    return '';
  }

  confirm(): void {
    if (this.disabledReason) {
      return;
    }
    this.confirmed.emit(this.reason.trim());
  }

  cancel(): void {
    if (this.busy) {
      return;
    }
    this.reason = '';
    this.cancelled.emit();
  }

  /** Cierre desde "Listo": el motivo se limpia para la siguiente vez. */
  finish(): void {
    this.reason = '';
    this.cancelled.emit();
  }
}
