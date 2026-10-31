import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Paginación estándar del sistema (antes duplicada a mano en 6 templates).
 * Se oculta sola cuando hay una sola página. `page` es base cero.
 */
@Component({
  selector: 'ui-pagination',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="totalPages > 1"
      class="flex items-center justify-between border-t border-olive-20 bg-ivory-80 px-4 py-2 text-xs text-gray-600">
      <span>Pág. {{ page + 1 }} de {{ totalPages }}</span>
      <div class="flex gap-1">
        <button type="button" aria-label="Página anterior" [disabled]="page === 0 || disabled"
          class="pg-btn" (click)="go(page - 1)">‹</button>
        <button *ngFor="let p of range" type="button"
          class="pg-btn" [class.pg-btn-active]="p === page"
          [attr.aria-current]="p === page ? 'page' : null"
          (click)="go(p)">{{ p + 1 }}</button>
        <button type="button" aria-label="Página siguiente" [disabled]="page >= totalPages - 1 || disabled"
          class="pg-btn" (click)="go(page + 1)">›</button>
      </div>
    </div>
  `
})
export class UiPaginationComponent {
  @Input() page = 0;
  @Input() totalPages = 0;
  @Input() disabled = false;
  /** Máximo de números visibles alrededor de la página actual. */
  @Input() windowSize = 5;

  @Output() pageChange = new EventEmitter<number>();

  get range(): number[] {
    const total = Math.max(0, this.totalPages);
    const half = Math.floor(this.windowSize / 2);
    let start = Math.max(0, this.page - half);
    const end = Math.min(total, start + this.windowSize);
    start = Math.max(0, end - this.windowSize);
    const pages: number[] = [];
    for (let p = start; p < end; p++) {
      pages.push(p);
    }
    return pages;
  }

  go(page: number): void {
    if (this.disabled || page < 0 || page > this.totalPages - 1 || page === this.page) {
      return;
    }
    this.pageChange.emit(page);
  }
}
