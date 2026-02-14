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
    const base = this.size === 'mini' ? 'badge-mini' : 'badge';
    if (this.size === 'mini') {
      const miniTone = {
        active: 'badge-mini-active',
        inactive: 'badge-mini-off',
        pending: 'badge-mini-gold',
        delivered: 'badge-mini-silver'
      };
      return `${base} ${miniTone[this.tone]}`;
    }

    const toneClass = {
      active: 'badge-active',
      inactive: 'badge-inactive',
      pending: 'badge-pending',
      delivered: 'badge-delivered'
    };
    return `${base} ${toneClass[this.tone]}`;
  }
}
