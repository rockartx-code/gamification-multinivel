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
  @Input() steps: TimelineStep[] = [
    { key: 'created', label: 'Orden creada', description: 'Tu pedido fue registrado.' },
    { key: 'paid', label: 'Pago', description: 'Conciliación y confirmación.' },
    { key: 'packing', label: 'Preparación', description: 'Armando paquete.' },
    { key: 'shipped', label: 'Envío', description: 'Ruta de entrega.' },
    { key: 'delivered', label: 'Entregada', description: 'Pedido finalizado.' }
  ];

  get currentIndex(): number {
    const s = String(this.status || '').toLowerCase();
    if (s === 'delivered') return 4;
    if (s === 'shipped') return 3;
    if (s === 'paid') return 2;
    return 1;
  }

  stepClass(index: number): string {
    if (index < this.currentIndex) return 'border-emerald-400/40 bg-emerald-400/20 text-main';
    if (index === this.currentIndex) return 'border-sky-400/40 bg-sky-400/15 text-main';
    return 'border-olive-20 bg-ivory-80 text-muted';
  }

  stepIcon(index: number, stepKey: string): string {
    if (index < this.currentIndex) return 'fa-check text-[10px]';
    if (index === this.currentIndex) {
      if (stepKey === 'paid') return 'fa-credit-card text-[11px]';
      if (stepKey === 'packing') return 'fa-box-open text-[11px]';
      if (stepKey === 'shipped') return 'fa-truck-fast text-[11px]';
      if (stepKey === 'delivered') return 'fa-circle-check text-[11px]';
      return 'fa-check text-[10px]';
    }
    return 'fa-circle text-[6px] opacity-60';
  }
}

