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

  get levelClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('activa') || value.includes('active')) {
        return 'level-2';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'level-3';
      }
      return 'level-5';
    }
    if (value === 'delivered') {
      return 'level-1';
    }
    if (value === 'shipped') {
      return 'level-2';
    }
    if (value === 'paid') {
      return 'level-3';
    }
    if (value === 'pending') {
      return 'level-4';
    }
    return 'level-5';
  }

  get activityClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inactiv') || value.includes('inactive')) {
        return 'status-inactive';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'status-active';
      }
      return '';
    }
    if (value === 'delivered') {
      return 'status-active';
    }
    if (value === 'pending') {
      return 'status-inactive';
    }
    return '';
  }

  private get normalized(): string {
    return String(this.status || '').toLowerCase();
  }
}
