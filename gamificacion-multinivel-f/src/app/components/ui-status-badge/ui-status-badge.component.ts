import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { UiBadgeComponent } from '../ui-badge/ui-badge.component';

@Component({
  selector: 'ui-status-badge',
  standalone: true,
  imports: [CommonModule, UiBadgeComponent],
  templateUrl: './ui-status-badge.component.html'
})
export class UiStatusBadgeComponent {
  @Input() status = '';
  @Input() context: 'order' | 'network' = 'order';
  @Input() showIcon = true;

  get tone(): 'active' | 'inactive' | 'pending' | 'delivered' {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('activa') || value.includes('active')) {
        return 'active';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'pending';
      }
      return 'inactive';
    }

    if (value === 'pending') {
      return 'pending';
    }
    if (value === 'paid') {
      return 'active';
    }
    if (value === 'shipped' || value === 'delivered') {
      return 'delivered';
    }
    return 'inactive';
  }

  get iconClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('activa') || value.includes('active')) {
        return 'fa-user-check';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'fa-hourglass-half';
      }
      return 'fa-user-xmark';
    }

    if (value === 'pending') {
      return 'fa-hourglass-half';
    }
    if (value === 'delivered') {
      return 'fa-circle-check';
    }
    if (value === 'shipped') {
      return 'fa-truck-fast';
    }
    if (value === 'paid') {
      return 'fa-receipt';
    }
    return 'fa-circle';
  }

  private get normalized(): string {
    return String(this.status || '').toLowerCase();
  }
}
