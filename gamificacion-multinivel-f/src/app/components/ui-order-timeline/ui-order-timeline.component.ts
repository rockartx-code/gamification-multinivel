import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

type TimelineStep = {
  key: string;
  label: string;
  description: string;
};

@Component({
  selector: 'ui-order-timeline',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-order-timeline.component.html'
})
export class UiOrderTimelineComponent {
  @Input() status = 'pending';
  /** Cómo se entrega el pedido: en recolección la barra no habla de rutas ni de paquetes. */
  @Input() deliveryType: 'delivery' | 'pickup' = 'delivery';
  @Input() steps: TimelineStep[] = [
    { key: 'created', label: 'Orden creada', description: 'Tu pedido fue registrado.' },
    { key: 'paid', label: 'Pago', description: 'Conciliación y confirmación.' },
    { key: 'packing', label: 'Preparación', description: 'Armando paquete.' },
    { key: 'shipped', label: 'Envío', description: 'Ruta de entrega.' },
    { key: 'delivered', label: 'Entregada', description: 'Pedido finalizado.' }
  ];

  // ── Paquete C · ronda 26 · propuesta 7 ──
  /** A tres compradoras de mostrador la barra les decía "Envío — Ruta de entrega". */
  private readonly pasosRecoleccion: TimelineStep[] = [
    { key: 'created', label: 'Orden creada', description: 'Tu pedido quedó registrado.' },
    { key: 'paid', label: 'Pago', description: 'Confirmación del pago.' },
    { key: 'packing', label: 'Preparando', description: 'Lo estamos separando en la sucursal.' },
    { key: 'shipped', label: 'Listo para recoger', description: 'Puedes pasar por él.' },
    { key: 'delivered', label: 'Entregado', description: 'Lo recogiste en la sucursal.' }
  ];

  get pasos(): TimelineStep[] {
    return this.deliveryType === 'pickup' ? this.pasosRecoleccion : this.steps;
  }

  get currentIndex(): number {
    const s = String(this.status || '').toLowerCase();
    // Tras la entrega el pedido puede seguir a devolución o reembolso: la línea de tiempo queda completa.
    if (['delivered', 'en_devolucion', 'devuelto_validado', 'devolucion_rechazada', 'refunded'].includes(s)) return 4;
    if (s === 'shipped') return 3;
    if (s === 'paid') return 2;
    return 1;
  }

  stepClass(index: number): string {
    // Paleta del sistema: completado en verde del sistema, actual en oro.
    if (index < this.currentIndex) return 'border-forest-20 bg-forest-10 text-main';
    if (index === this.currentIndex) return 'border-gold-35 bg-gold-20 text-main';
    return 'border-olive-20 bg-ivory-80 text-muted';
  }

  stepIcon(index: number, stepKey: string): string {
    if (index < this.currentIndex) return 'fa-check text-[10px]';
    if (index === this.currentIndex) {
      if (stepKey === 'paid') return 'fa-credit-card text-[11px]';
      if (stepKey === 'packing') return 'fa-box-open text-[11px]';
      if (stepKey === 'shipped') return this.deliveryType === 'pickup' ? 'fa-store text-[11px]' : 'fa-truck-fast text-[11px]';
      if (stepKey === 'delivered') return 'fa-circle-check text-[11px]';
      return 'fa-check text-[10px]';
    }
    return 'fa-circle text-[6px] opacity-60';
  }
}

