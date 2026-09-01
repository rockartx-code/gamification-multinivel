import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { UiButtonComponent } from '../ui-button/ui-button.component';

export type SidebarLink = {
  id: string;
  icon: string;
  label: string;
  subtitle?: string;
  /** Cuando es true, el enlace se pinta como encabezado de grupo (no clicable). */
  heading?: boolean;
};

@Component({
  selector: 'ui-sidebar-nav',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  templateUrl: './ui-sidebar-nav.component.html'
})
export class UiSidebarNavComponent {
  @Input() links: SidebarLink[] = [];
  @Input() activeId = '';
  @Input() compact = false;
  @Output() linkSelect = new EventEmitter<string>();

  onSelect(id: string): void {
    this.linkSelect.emit(id);
  }
}
