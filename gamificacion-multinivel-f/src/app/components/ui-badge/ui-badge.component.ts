import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-badge',
  standalone: true,
  template: `<span [class]="classes"><ng-content></ng-content></span>`
})
export class UiBadgeComponent {
  @Input() tone: 'active' | 'inactive' | 'pending' | 'delivered' = 'inactive';
  @Input() size: 'default' | 'mini' = 'default';

  get classes(): string {
    const toneClass = {
      active: 'badge-active',
      inactive: 'badge-inactive',
      pending: 'badge-pending',
      delivered: 'badge-active'
    };
    const sizeClass = this.size === 'mini' ? 'badge badge-compact' : 'badge';
    return `${sizeClass} ${toneClass[this.tone]}`;
  }
}
