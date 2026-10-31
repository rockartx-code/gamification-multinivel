import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, EventEmitter, Input, Output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import { AdminCustomer } from '../../../models/admin.model';
import { ActivacionModoSocioRespuesta, ModoCuenta } from '../../../models/plan-socio.model';
import { PlanSocioService } from '../../../services/plan-socio.service';

/**
 * Etiqueta de modo (cliente/socio) en la ficha del back office, con el cambio
 * de modo en un modal que explica el efecto antes de guardar (paquete B).
 */
@Component({
  selector: 'app-admin-modo-cliente',
  standalone: true,
  imports: [CommonModule, UiButtonComponent, UiModalComponent],
  templateUrl: './admin-modo-cliente.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminModoClienteComponent {
  @Input() customer: AdminCustomer | null = null;
  /** Se emite con la respuesta del servidor cuando el modo cambió. */
  @Output() cambiado = new EventEmitter<ActivacionModoSocioRespuesta>();

  isModalOpen = false;
  isSaving = false;
  error = '';
  guardado: ActivacionModoSocioRespuesta | null = null;

  constructor(
    private readonly planSocio: PlanSocioService,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef
  ) {}

  get modo(): ModoCuenta {
    return this.customer?.mode === 'cliente' ? 'cliente' : 'socio';
  }

  get etiqueta(): string {
    return this.modo === 'cliente' ? 'Modo cliente' : 'Modo socio';
  }

  get claseEtiqueta(): string {
    return this.modo === 'cliente'
      ? 'inline-flex items-center gap-1 rounded-full border border-olive-30 bg-ivory-80 px-2 py-0.5 text-mini font-semibold text-gray-700'
      : 'inline-flex items-center gap-1 rounded-full border border-gold-35 bg-gold-12 px-2 py-0.5 text-mini font-semibold text-main';
  }

  get modoDestino(): ModoCuenta {
    return this.modo === 'cliente' ? 'socio' : 'cliente';
  }

  get textoBoton(): string {
    return this.modo === 'cliente' ? 'Pasar a modo socio' : 'Regresar a modo cliente';
  }

  get efecto(): string {
    if (this.modo === 'cliente') {
      return 'Desde su siguiente compra aplica la escalera de descuento y en su panel aparecen red, VP, comisiones, código de referido y CLABE. No se le manda correo (el cambio lo hace un administrador).';
    }
    return 'Sus próximas compras se cobran a precio de lista y su panel deja de mostrar red, VP y comisiones. Si alguien se registra con su código o el motor le genera una comisión, vuelve a modo socio automáticamente.';
  }

  abrir(): void {
    this.error = '';
    this.guardado = null;
    this.isModalOpen = true;
  }

  cerrar(): void {
    if (this.isSaving) {
      return;
    }
    this.isModalOpen = false;
  }

  confirmar(): void {
    if (!this.customer || this.isSaving) {
      return;
    }
    this.isSaving = true;
    this.error = '';
    this.cdr.markForCheck();
    this.planSocio
      .activarModoSocio({ customerId: this.customer.id, mode: this.modoDestino })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (respuesta) => {
          this.isSaving = false;
          this.guardado = respuesta;
          if (this.customer) {
            // La lista y la ficha comparten el objeto: se refleja sin recargar todo.
            this.customer.mode = respuesta.mode;
            this.customer.modeActivatedAt = respuesta.modeActivatedAt ?? undefined;
          }
          this.cambiado.emit(respuesta);
          this.cdr.markForCheck();
        },
        error: (err: { error?: { message?: string } }) => {
          this.isSaving = false;
          this.error = err?.error?.message || 'No se pudo guardar el cambio de modo.';
          this.cdr.markForCheck();
        }
      });
  }
}
