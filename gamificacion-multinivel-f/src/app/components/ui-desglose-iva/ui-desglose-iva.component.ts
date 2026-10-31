import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { DesgloseIva, desgloseIva, formatoPesosExactos, formatoPorcentaje } from '../../models/plan-socio.model';

/**
 * El desglose del IVA, en tres líneas y siempre con las mismas palabras
 * (paquete B, propuesta 38).
 *
 * Los precios de lista ya incluyen IVA: aquí **no se suma nada**, se explica
 * un total que no cambia. Cada pantalla donde se explica dinero monta este
 * mismo componente —carrito, recibo, correo de pago, detalle del pedido, POS,
 * corte de caja, facturación, plan y simulador— para que el importe se lea
 * igual en todas y `Subtotal sin IVA + IVA = Total` cuadre al centavo.
 */
@Component({
  selector: 'ui-desglose-iva',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-desglose-iva.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiDesgloseIvaComponent {
  /** Lo que se cobra, con IVA ya incluido. */
  @Input() total = 0;
  /** Envío incluido en ese total; informativo, para decir si va en la base. */
  @Input() shipping = 0;
  /** Tasa vigente, de `GET /catalog/plan` o de la configuración pública. */
  @Input() rate = 0.16;
  /** Cómo se llama el impuesto en pantalla. */
  @Input() label = 'IVA';
  @Input() variant: 'inline' | 'card' = 'inline';
  /** La nota de una línea se puede callar donde ya se dijo arriba. */
  @Input() mostrarNota = true;

  readonly pesos = formatoPesosExactos;
  readonly porcentaje = formatoPorcentaje;

  get desglose(): DesgloseIva {
    return desgloseIva(this.total, this.rate, this.label);
  }

  get hayEnvio(): boolean {
    return (Number(this.shipping) || 0) > 0;
  }

  /** Se dice de dónde sale la base: es la duda que nadie pudo resolver en pantalla. */
  get nota(): string {
    if (!this.desglose.rate) {
      return 'Este total no lleva impuesto desglosado.';
    }
    return this.hayEnvio
      ? 'Los precios ya incluyen IVA; el envío también.'
      : 'Los precios ya incluyen IVA.';
  }
}
