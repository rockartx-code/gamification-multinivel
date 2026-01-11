import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-progress-bar',
  template: `
    <div class="app-progress">
      <div class="app-progress__label">
        <span>{{ label() }}</span>
        <span aria-hidden="true">{{ percentage() }}%</span>
      </div>
      <div
        class="app-progress__track"
        role="progressbar"
        [attr.aria-label]="label()"
        [attr.aria-valuemin]="min()"
        [attr.aria-valuemax]="max()"
        [attr.aria-valuenow]="value()"
      >
        <div
          class="app-progress__fill"
          [class.app-progress__fill--success]="tone() === 'success'"
          [class.app-progress__fill--warning]="tone() === 'warning'"
          [class.app-progress__fill--danger]="tone() === 'danger'"
          [style.width.%]="percentage()"
        ></div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProgressBarComponent {
  label = input<string>('Progreso');
  value = input<number>(0);
  min = input<number>(0);
  max = input<number>(100);
  tone = input<StatusTone>('success');

  protected readonly percentage = computed(() => {
    const range = this.max() - this.min();
    if (range <= 0) {
      return 0;
    }
    const clampedValue = Math.min(Math.max(this.value(), this.min()), this.max());
    return Math.round(((clampedValue - this.min()) / range) * 100);
  });
}
