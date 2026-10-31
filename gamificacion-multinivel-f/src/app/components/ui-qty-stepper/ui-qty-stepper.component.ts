import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Stepper de cantidad −/n/+ del sistema (antes duplicado a mano en la
 * tarjeta de producto y el carrito). Emite la nueva cantidad, nunca < min.
 */
@Component({
  selector: 'ui-qty-stepper',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="inline-flex items-center gap-1">
      <button
        type="button"
        [attr.aria-label]="'Quitar una unidad' + (itemLabel ? ' de ' + itemLabel : '')"
        class="qty-btn"
        [disabled]="disabled || qty <= min"
        (click)="change(-1)">
        <i class="fa-solid fa-minus text-[10px]" aria-hidden="true"></i>
      </button>
      <span class="w-6 text-center text-sm font-semibold tabular-nums">{{ qty }}</span>
      <button
        type="button"
        [attr.aria-label]="'Agregar una unidad' + (itemLabel ? ' de ' + itemLabel : '')"
        class="qty-btn"
        [disabled]="disabled || (max !== null && qty >= max)"
        (click)="change(1)">
        <i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i>
      </button>
    </div>
  `
})
export class UiQtyStepperComponent {
  @Input() qty = 0;
  @Input() min = 0;
  @Input() max: number | null = null;
  @Input() disabled = false;
  /** Nombre del artículo para los aria-labels. */
  @Input() itemLabel = '';

  @Output() qtyChange = new EventEmitter<number>();

  change(delta: number): void {
    const next = Math.max(this.min, this.qty + delta);
    if (this.max !== null && next > this.max) {
      return;
    }
    if (next !== this.qty) {
      this.qtyChange.emit(next);
    }
  }
}
