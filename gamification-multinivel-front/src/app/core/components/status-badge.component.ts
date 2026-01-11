import { ChangeDetectionStrategy, Component, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-status-badge',
  template: `
    <span
      class="app-badge"
      role="status"
      [class.app-badge--success]="tone() === 'success'"
      [class.app-badge--warning]="tone() === 'warning'"
      [class.app-badge--danger]="tone() === 'danger'"
    >
      {{ label() }}
    </span>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusBadgeComponent {
  label = input<string>('Activo');
  tone = input<StatusTone>('success');
}
