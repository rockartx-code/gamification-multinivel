import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import {
  PlanTramo,
  formatoPesos,
  formatoPorcentaje,
  formatoPuntos,
  siguienteTramo,
  tasaDeTramos,
  tramoDe
} from '../../models/plan-socio.model';
import { UiButtonComponent } from '../ui-button/ui-button.component';

/**
 * La tabla única de descuento y VP (paquete B, propuesta 3).
 *
 * "Las metas del panel y el nivel del carrito parecen dos reglas distintas
 * con los mismos nombres" (veronica-dic12). Panel, carrito y POS montan este
 * mismo componente con el mismo vocabulario: tramo actual, con esta compra,
 * siguiente tramo, cuánto falta, y la nota de que los VP se cuentan sobre el
 * precio ya con descuento.
 */
@Component({
  selector: 'ui-tabla-descuento',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  templateUrl: './ui-tabla-descuento.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiTablaDescuentoComponent {
  @Input() tiers: Array<{ min: number; max: number | null; rate: number }> = [];
  @Input() mxnPerVp = 50;
  @Input() activationVp = 20;
  /** Neto acumulado del mes (MPN). */
  @Input() monthNet = 0;
  /** VP netos acumulados del mes. */
  @Input() monthVp = 0;
  /** Bruto del carrito o de la venta en curso (0 si no aplica). */
  @Input() cartGross = 0;
  /** PC de lista del carrito o venta. */
  @Input() cartPc = 0;
  @Input() mode: 'cliente' | 'socio' = 'socio';
  @Input() context: 'panel' | 'carrito' | 'pos' | 'plan' = 'panel';
  @Input() compact = false;
  /** Solo en modo cliente: la persona pulsó "Activar modo socio". */
  @Output() activateRequested = new EventEmitter<void>();

  readonly pesos = formatoPesos;
  readonly porcentaje = formatoPorcentaje;
  readonly puntos = formatoPuntos;

  get tramos(): PlanTramo[] {
    return [...(this.tiers ?? [])]
      .map((t) => ({ min: Number(t.min) || 0, max: t.max == null ? null : Number(t.max), rate: Number(t.rate) || 0 }))
      .sort((a, b) => a.min - b.min);
  }

  get hayCompra(): boolean {
    return (Number(this.cartGross) || 0) > 0;
  }

  get tercera(): boolean {
    return this.context === 'pos';
  }

  get titulo(): string {
    if (this.context === 'plan') {
      return 'Tu descuento por volumen';
    }
    return this.tercera ? 'Descuento del cliente este mes' : 'Tu descuento este mes';
  }

  get tramoActual(): PlanTramo | null {
    return tramoDe(this.tramos, this.monthNet);
  }

  get tasaActual(): number {
    return tasaDeTramos(this.tramos, this.monthNet);
  }

  get proyectado(): number {
    return (Number(this.monthNet) || 0) + (Number(this.cartGross) || 0);
  }

  get tramoConCompra(): PlanTramo | null {
    return tramoDe(this.tramos, this.proyectado);
  }

  get tasaConCompra(): number {
    return tasaDeTramos(this.tramos, this.proyectado);
  }

  get siguiente(): { rate: number; missing: number } | null {
    return siguienteTramo(this.tramos, this.proyectado);
  }

  /** VP netos que suma la compra en curso (PC × (1 − tasa)); en modo cliente la tasa es 0. */
  get vpDeLaCompra(): number {
    const pc = Number(this.cartPc) || 0;
    const tasa = this.mode === 'cliente' ? 0 : this.tasaConCompra;
    return Math.round(pc * (1 - tasa) * 10) / 10;
  }

  get vpTrasCompra(): number {
    return Math.round(((Number(this.monthVp) || 0) + this.vpDeLaCompra) * 10) / 10;
  }

  get vpFaltantes(): number {
    return Math.max(0, Math.round((this.activationVp - this.vpTrasCompra) * 10) / 10);
  }

  /** Lo que esta compra se ahorraría en modo socio (solo se muestra en modo cliente). */
  get ahorroHipotetico(): number {
    return Math.round((Number(this.cartGross) || 0) * this.tasaConCompra * 100) / 100;
  }

  get sujeto(): string {
    return this.tercera ? 'El cliente' : 'Tú';
  }

  rangoDe(tramo: PlanTramo): string {
    if (tramo.max == null) {
      return `desde ${this.pesos(tramo.min)}`;
    }
    if (tramo.min <= 0) {
      return `hasta ${this.pesos(tramo.max - 1)}`;
    }
    return `de ${this.pesos(tramo.min)} a ${this.pesos(tramo.max - 1)}`;
  }

  esActual(tramo: PlanTramo): boolean {
    return this.tramoActual?.min === tramo.min;
  }

  esConCompra(tramo: PlanTramo): boolean {
    return this.hayCompra && this.tramoConCompra?.min === tramo.min;
  }

  /** Ejemplo fijo de la nota: los PC de activación con el primer tramo con descuento. */
  get ejemploNota(): string {
    const primero = this.tramos.find((t) => t.rate > 0);
    if (!primero) {
      return '';
    }
    const vp = Math.round(this.activationVp * (1 - primero.rate) * 10) / 10;
    return `${this.puntos(this.activationVp)} PC con ${this.porcentaje(primero.rate)} = ${this.puntos(vp)} VP`;
  }

  get textoTramoActual(): string {
    const tramo = this.tramoActual;
    if (!tramo) {
      return '';
    }
    const quien = this.tercera ? 'El cliente está en el tramo' : 'Tramo actual';
    return `${quien}: ${this.porcentaje(tramo.rate)} (${this.rangoDe(tramo)})`;
  }

  get textoConCompra(): string {
    if (!this.hayCompra) {
      return '';
    }
    const llegas = this.tercera ? 'llega a' : 'llegas a';
    return `Con esta compra: ${this.porcentaje(this.tasaConCompra)} (${llegas} ${this.pesos(this.proyectado)})`;
  }

  get textoSiguiente(): string {
    const sig = this.siguiente;
    if (!sig) {
      return this.tercera ? 'Ya está en el tramo más alto.' : 'Ya estás en el tramo más alto.';
    }
    const faltan = this.tercera ? 'le faltan' : 'te faltan';
    return `Siguiente tramo: ${this.porcentaje(sig.rate)}, ${faltan} ${this.pesos(sig.missing)}`;
  }

  get textoActivacion(): string {
    const lleva = this.tercera ? 'lleva' : 'llevas';
    let texto = `Activación: ${this.puntos(this.activationVp)} VP netos · ${lleva} ${this.puntos(this.monthVp)}`;
    if (this.hayCompra && (Number(this.cartPc) || 0) > 0) {
      texto += ` · este pedido suma ${this.puntos(this.vpDeLaCompra)}`;
    }
    return texto;
  }

  get textoActivacionEstado(): string {
    if (this.vpFaltantes <= 0) {
      return this.hayCompra ? 'Con esta compra queda activo el mes.' : 'Este mes ya está activo.';
    }
    const faltan = this.tercera ? 'Le faltan' : 'Te faltan';
    return `${faltan} ${this.puntos(this.vpFaltantes)} VP para activar el mes.`;
  }

  pedirActivacion(): void {
    this.activateRequested.emit();
  }
}
