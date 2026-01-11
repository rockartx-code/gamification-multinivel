import { ChangeDetectionStrategy, Component, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-metric-card',
  template: `
    <div
      class="app-metric"
      role="group"
      [attr.aria-label]="title()"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="app-metric__label">{{ title() }}</p>
          <p class="app-metric__value">{{ value() }}</p>
          <p class="app-metric__helper">{{ helper() }}</p>
        </div>
        <span
          class="app-metric__bar"
          aria-hidden="true"
          [class.app-metric__bar--success]="tone() === 'success'"
          [class.app-metric__bar--warning]="tone() === 'warning'"
          [class.app-metric__bar--danger]="tone() === 'danger'"
        ></span>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MetricCardComponent {
  title = input<string>('Meta semanal');
  value = input<string>('8/10');
  helper = input<string>('Tareas completadas');
  tone = input<StatusTone>('success');
}
