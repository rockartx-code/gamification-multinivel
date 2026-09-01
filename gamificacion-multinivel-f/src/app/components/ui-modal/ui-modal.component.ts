import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostListener, Input, Output } from '@angular/core';

@Component({
  selector: 'ui-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-modal.component.html'
})
export class UiModalComponent {
  @Input() isOpen = false;
  @Input() maxWidthClass = 'max-w-lg';
  @Input() contentClass = 'p-6';
  @Input() containerClass = 'fixed inset-0 z-50 flex items-center justify-center modal-backdrop px-4';
  @Input() panelClass = 'modal-card w-full max-h-[90vh] overflow-hidden';
  @Input() closeOnBackdrop = true;
  /** Etiqueta accesible del diálogo (cuando el contenido no tiene encabezado propio). */
  @Input() ariaLabel = '';

  @Output() closed = new EventEmitter<void>();

  close(): void {
    this.closed.emit();
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop) {
      this.close();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen && this.closeOnBackdrop) {
      this.close();
    }
  }
}
