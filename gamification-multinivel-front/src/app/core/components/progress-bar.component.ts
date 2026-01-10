import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger: 'bg-red-500',
};

@Component({
  selector: 'app-progress-bar',
  template: `
    <div class="space-y-2">
      <div class="flex items-center justify-between text-sm font-medium text-slate-700">
        <span>{{ label() }}</span>
        <span aria-hidden="true">{{ percentage() }}%</span>
      </div>
      <div
        class="h-3 w-full rounded-full bg-slate-200"
        role="progressbar"
        [attr.aria-label]="label()"
        [attr.aria-valuemin]="min()"
        [attr.aria-valuemax]="max()"
        [attr.aria-valuenow]="value()"
      >
        <div
          class="h-full rounded-full transition-all"
          [class]="toneClasses()"
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

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
