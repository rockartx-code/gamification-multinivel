import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { UiFormFieldComponent } from '../ui-form-field/ui-form-field.component';
import { ApiService } from '../../services/api.service';

/** Lo que la persona ve mientras guarda, **en el propio campo**. */
export type EstadoClabe = 'inactivo' | 'guardando' | 'guardada' | 'quitada' | 'error';

/**
 * Paquete A · propuesta 1: el formulario único de CLABE.
 *
 * Paulina lo intentó cinco veces y Fabiola otras cinco, en dos pantallas
 * distintas, sin un solo mensaje; marzo cerró con $0.00 depositados. Aquí
 * "Guardar" **guarda**: manda el POST directo (dieciocho dígitos ya validados
 * no necesitan un segundo diálogo que se cierra con un clic al fondo) y el
 * estado se pinta junto al campo, no en un aviso al final de la página.
 *
 * Sustituye a los dos formularios que había (uno pedía banco y el otro no, y
 * no se enteraban uno del otro).
 */
@Component({
  selector: 'ui-clabe-form',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ui-clabe-form.component.html'
})
export class UiClabeFormComponent implements OnChanges {
  /** Ficha a la que se le guarda la CLABE. */
  @Input() customerId: string | number = '';
  /** Los cuatro últimos dígitos de la CLABE ya registrada, si hay. */
  @Input() clabeLast4 = '';
  /** Banco ya registrado (opcional, como lo acepta el backend). */
  @Input() bankInstitution = '';
  /** `propio`: la socia en su panel. `admin`: administración desde la ficha. */
  @Input() modo: 'propio' | 'admin' = 'propio';
  /** Título de la tarjeta; vacío lo deja sin encabezado. */
  @Input() titulo = '';

  /** Se emite con la terminación guardada (vacía si se quitó). */
  @Output() saved = new EventEmitter<{ clabeLast4: string; bankInstitution: string; removed: boolean }>();

  clabe = '';
  banco = '';
  estado: EstadoClabe = 'inactivo';
  mensaje = '';
  confirmandoQuitar = false;

  constructor(
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['bankInstitution']) {
      this.banco = this.bankInstitution || '';
    }
  }

  get tieneClabe(): boolean {
    return !!this.clabeLast4;
  }

  get guardando(): boolean {
    return this.estado === 'guardando';
  }

  /** Lo que se lee arriba del campo: nunca "No registrada" cuando ya la guardó. */
  get resumen(): string {
    if (this.tieneClabe) {
      const banco = this.bankInstitution ? ` · ${this.bankInstitution}` : '';
      return `Guardada, termina en ${this.clabeLast4}${banco}`;
    }
    return this.modo === 'admin' ? 'Esta socia no tiene CLABE registrada.' : 'Todavía no registras tu CLABE.';
  }

  get textoBoton(): string {
    if (this.guardando) {
      return 'Guardando…';
    }
    return this.tieneClabe ? 'Guardar la nueva CLABE' : 'Guardar CLABE';
  }

  onClabeChange(valor: string): void {
    this.clabe = (valor || '').replace(/\D/g, '').slice(0, 18);
    if (this.estado === 'error') {
      this.estado = 'inactivo';
      this.mensaje = '';
    }
    this.cdr.markForCheck();
  }

  guardar(): void {
    if (this.guardando) {
      return;
    }
    const clabe = this.clabe.trim();
    if (clabe.length !== 18) {
      this.estado = 'error';
      this.mensaje = clabe
        ? `No se pudo guardar: la CLABE debe tener 18 dígitos y escribiste ${clabe.length}.`
        : 'No se pudo guardar: escribe tu CLABE de 18 dígitos.';
      this.cdr.markForCheck();
      return;
    }
    this.enviar(clabe, this.banco.trim());
  }

  pedirQuitar(): void {
    this.confirmandoQuitar = true;
    this.cdr.markForCheck();
  }

  cancelarQuitar(): void {
    this.confirmandoQuitar = false;
    this.cdr.markForCheck();
  }

  confirmarQuitar(): void {
    if (this.guardando) {
      return;
    }
    this.enviar('', '');
  }

  private enviar(clabe: string, banco: string): void {
    const customerId = Number(this.customerId);
    if (!this.customerId || Number.isNaN(customerId)) {
      this.estado = 'error';
      this.mensaje = 'No se pudo guardar: no sabemos de quién es esta cuenta. Vuelve a entrar e inténtalo otra vez.';
      this.cdr.markForCheck();
      return;
    }
    this.estado = 'guardando';
    this.mensaje = clabe ? 'Guardando…' : 'Quitando la CLABE…';
    this.cdr.markForCheck();
    this.api
      .saveCustomerClabe({ customerId, clabe, ...(banco ? { bankInstitution: banco } : {}) })
      .pipe(finalize(() => this.cdr.markForCheck()))
      .subscribe({
        next: (respuesta) => {
          const last4 = respuesta?.clabeLast4 ?? (clabe ? clabe.slice(-4) : '');
          this.clabeLast4 = last4;
          this.bankInstitution = clabe ? banco : '';
          this.clabe = '';
          this.confirmandoQuitar = false;
          this.estado = clabe ? 'guardada' : 'quitada';
          this.mensaje = clabe
            ? `Guardada, termina en ${last4}. Ahí te depositamos tus comisiones.`
            : 'CLABE quitada. Sin CLABE no podemos depositarte: registra otra cuando quieras.';
          this.saved.emit({ clabeLast4: last4, bankInstitution: this.bankInstitution, removed: !clabe });
        },
        error: (error: unknown) => {
          this.estado = 'error';
          this.mensaje = `No se pudo guardar: ${this.motivo(error)}`;
        }
      });
  }

  private motivo(error: unknown): string {
    const err = error as { status?: number; error?: { message?: string } };
    const mensaje = err?.error?.message;
    if (typeof mensaje === 'string' && mensaje.trim()) {
      return mensaje.trim();
    }
    if (err?.status === 403) {
      return 'esta cuenta no puede cambiar esa CLABE.';
    }
    if (err?.status === 0) {
      return 'no hubo conexión. Revisa tu internet e inténtalo otra vez.';
    }
    return 'inténtalo otra vez en un momento.';
  }
}
