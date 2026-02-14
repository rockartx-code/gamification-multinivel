import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

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
  @Input() closeOnBackdrop = true;

  @Output() closed = new EventEmitter<void>();

  close(): void {
    this.closed.emit();
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop) {
      this.close();
    }
  }
}
