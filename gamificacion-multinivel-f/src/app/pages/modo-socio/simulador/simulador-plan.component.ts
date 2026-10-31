import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiDesgloseIvaComponent } from '../../../components/ui-desglose-iva/ui-desglose-iva.component';
import {
  PlanSocio,
  SimuladorResultado,
  formatoPesosExactos,
  formatoPorcentaje,
  formatoPuntos
} from '../../../models/plan-socio.model';
import { PlanSocioService } from '../../../services/plan-socio.service';

/**
 * El simulador del plan (paquete B, propuesta 36).
 *
 * Ximena Paredes se pasó la sesión con lápiz y papel calculando si el negocio
 * le convenía —diez de sus dieciséis tareas sin un solo clic—, porque la
 * plataforma publicaba el plan pero no publicaba ganancias. Aquí mete cuántas
 * personas directas tiene, cuánto compra cada una y cuánto compra ella, y ve
 * el resultado con los porcentajes y requisitos reales de la configuración,
 * incluida la ganancia **neta**, también cuando sale en rojo.
 *
 * Todo lo que se pinta viene de `POST /catalog/plan/simular`: ningún
 * porcentaje, ningún requisito y ningún importe se calcula aquí.
 */
@Component({
  selector: 'plan-simulador',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiDesgloseIvaComponent],
  templateUrl: './simulador-plan.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SimuladorPlanComponent implements OnInit {
  /** El plan ya cargado, para no volver a pedirlo. */
  @Input() plan!: PlanSocio;
  /** Lo que la persona ya lleva comprado en el mes, si lo sabemos. */
  @Input() compraPropiaInicial = 0;
  @Output() activateRequested = new EventEmitter<void>();

  readonly pesos = formatoPesosExactos;
  readonly porcentaje = formatoPorcentaje;
  readonly puntos = formatoPuntos;

  directos = 2;
  compraPorDirecto = 1000;
  compraPropia = 0;
  niveles = 1;

  resultado: SimuladorResultado | null = null;
  isLoading = false;
  errorMensaje = '';

  constructor(
    private readonly planSocio: PlanSocioService,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef
  ) {}

  ngOnInit(): void {
    // Se arranca con la compra que la persona ya lleva; si no sabemos nada,
    // con lo más barato que de verdad activa, que es un número del catálogo.
    this.compraPropia = this.compraPropiaInicial > 0
      ? Math.round(this.compraPropiaInicial)
      : Math.round(this.plan?.activacion?.rango?.min ?? 0);
    this.calcular();
  }

  get maxNiveles(): number {
    return Math.max(1, this.plan?.unidades?.maxLevels ?? 1);
  }

  get nivelesDisponibles(): number[] {
    return Array.from({ length: this.maxNiveles }, (_, i) => i + 1);
  }

  get ganaODebe(): 'gana' | 'pierde' | 'empata' {
    const neta = this.resultado?.gananciaNeta ?? 0;
    return neta > 0 ? 'gana' : neta < 0 ? 'pierde' : 'empata';
  }

  /**
   * Ronda 7 · Gerardo: «el resultado no se actualiza mientras se escribe: solo
   * al salir del campo». En un celular uno teclea y mira el resultado sin salir
   * del campo, y concluye que la calculadora está muerta. Se recalcula al
   * escribir, con una pausa corta para no disparar una petición por tecla.
   */
  alEscribir(): void {
    if (this.reboteId !== null) {
      clearTimeout(this.reboteId);
    }
    this.reboteId = setTimeout(() => {
      this.reboteId = null;
      this.calcular();
    }, 350) as unknown as number;
  }

  private reboteId: number | null = null;

  calcular(): void {
    if (this.reboteId !== null) {
      clearTimeout(this.reboteId);
      this.reboteId = null;
    }
    this.isLoading = true;
    this.errorMensaje = '';
    this.cdr.markForCheck();
    this.planSocio
      .simular({
        directos: Math.max(0, Math.trunc(Number(this.directos) || 0)),
        compraPorDirecto: Math.max(0, Number(this.compraPorDirecto) || 0),
        compraPropia: Math.max(0, Number(this.compraPropia) || 0),
        nivelesProfundidad: Math.max(1, Math.trunc(Number(this.niveles) || 1))
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (resultado) => {
          this.resultado = resultado;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (error: { error?: { message?: string } }) => {
          this.isLoading = false;
          this.errorMensaje =
            error?.error?.message || 'No pudimos hacer la cuenta en este momento. Intenta de nuevo en unos minutos.';
          this.cdr.markForCheck();
        }
      });
  }

  activar(): void {
    this.activateRequested.emit();
  }
}
