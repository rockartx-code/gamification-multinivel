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

  /**
   * "Te quedan 2 días" / "Te quedan 6 horas", para que el plazo se sienta.
   *
   * Ronda 7 · Nayeli: el botón anunciaba SIEMPRE el plazo más largo ("te quedan
   * 6 días", los 7 de "cambié de opinión") mientras tres renglones más abajo la
   * misma pantalla decía "llegó dañado o defectuoso: 48 horas". Quien se
   * confiaba de los 6 días perdía el plazo real de su caso. Ahora se dice a qué
   * motivo corresponde ese plazo, y cuál es el más corto que sigue vivo.
   */
  get restanteTexto(): string {
    const horas = this.devolucion?.horasRestantes;
    if (!this.puede || horas == null || horas <= 0) {
      return '';
    }
    return `${this.plazoLargoTexto(horas)} para ${this.motivoDelPlazoLargo}.`;
  }

  /** El motivo con la ventana más corta que todavía no se vence, si hay más de una. */
  get plazoCortoTexto(): string {
    const motivos = this.devolucion?.motivos ?? [];
    if (!this.puede || motivos.length < 2) {
      return '';
    }
    const largo = Math.max(...motivos.map((m) => m.limiteHoras || 0));
    const corto = motivos
      .filter((m) => (m.limiteHoras || 0) > 0 && m.limiteHoras < largo)
      .sort((a, b) => a.limiteHoras - b.limiteHoras)[0];
    if (!corto) {
      return '';
    }
    return `Ojo: "${corto.label}" solo se puede pedir dentro de ${corto.plazoTexto || corto.limiteHoras + ' horas'} desde la entrega.`;
  }

  private get motivoDelPlazoLargo(): string {
    const motivos = this.devolucion?.motivos ?? [];
    if (!motivos.length) {
      return 'pedirla';
    }
    const largo = motivos.reduce((a, b) => ((b.limiteHoras || 0) > (a.limiteHoras || 0) ? b : a));
    return `pedirla por "${largo.label}"`;
  }

  private plazoLargoTexto(horas: number): string {
    if (horas >= 48) {
      const dias = Math.floor(horas / 24);
      return `Te quedan ${dias} días`;
    }
    const enteras = Math.max(1, Math.floor(horas));
    return `Te queda${enteras === 1 ? '' : 'n'} ${enteras} hora${enteras === 1 ? '' : 's'}`;
  }
}
