import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { EstadoDevolucionPedido } from '../../models/ayuda.model';

/**
 * Paquete D · propuesta 24 — el botón "Devolver / Llegó dañado", siempre visible.
 *
 * La pantalla de devolución existía y hacía exactamente lo que Julio pedía
 * —cantidades por producto, motivos, reembolso por línea—, pero **el botón solo
 * se pintaba con el pedido "entregado"** y el suyo estaba en `paid`: 17 clics,
 * 9 pantallas, 341 segundos, facilidad 1 de 7, y se quedó con la proteína rota.
 *
 * Este producto hace muy bien los botones apagados que explican su motivo
 * (Renata y Mireya lo elogiaron). Aquí faltaba el botón. Ahora está siempre, y
 * el motivo y el plazo vienen del servidor (`GET /orders/{id}` → `devolucion`),
 * que es la misma fuente con la que valida la solicitud: no hay una quinta
 * versión de la regla.
 */
@Component({
  selector: 'ui-devolucion-boton',
  standalone: true,
  imports: [CommonModule, RouterLink, UiButtonComponent],
  templateUrl: './ui-devolucion-boton.component.html'
})
export class UiDevolucionBotonComponent {
  /** Lo que dice el servidor. Sin él, el botón no se pinta (aún no carga el pedido). */
  @Input() devolucion: EstadoDevolucionPedido | null = null;
  /** Para armar el enlace al asistente. */
  @Input() orderId = '';
  /** El pedido ya tiene una solicitud: se ofrece "Ver mi devolución" en su lugar. */
  @Input() enCurso = false;

  @Output() solicitar = new EventEmitter<void>();

  get puede(): boolean {
    return Boolean(this.devolucion?.puedeSolicitar);
  }

  get motivo(): string {
    return this.devolucion?.motivo ?? '';
  }

  /** "Te quedan 2 días" / "Te quedan 6 horas", para que el plazo se sienta. */
  get restanteTexto(): string {
    const horas = this.devolucion?.horasRestantes;
    if (!this.puede || horas == null || horas <= 0) {
      return '';
    }
    if (horas >= 48) {
      const dias = Math.floor(horas / 24);
      return `Te quedan ${dias} días para pedirla.`;
    }
    const enteras = Math.max(1, Math.floor(horas));
    return `Te queda${enteras === 1 ? '' : 'n'} ${enteras} hora${enteras === 1 ? '' : 's'} para pedirla.`;
  }
}
