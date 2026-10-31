import { Component, Input } from '@angular/core';

@Component({
  selector: 'feature-badge',
  standalone: true,
  host: {
    class: 'block min-w-0'
  },
  template: `
    <div class="flex min-w-0 items-center gap-2 rounded-xl border border-olive-30 bg-ivory-80 p-4">
      <i [class]="iconClasses" aria-hidden="true"></i>
      <span [class]="labelClasses">{{ label }}</span>
    </div>
  `
})
export class FeatureBadgeComponent {
  @Input() icon = 'fa-solid fa-circle';
  @Input() label = '';
  @Input() truncate = false;

  get iconClasses(): string {
    return `${this.icon} shrink-0`.trim();
  }

  get labelClasses(): string {
    return this.truncate ? 'min-w-0 truncate' : 'min-w-0 break-words';
  }
}
