import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'border-green-500',
  warning: 'border-yellow-500',
  danger: 'border-red-500',
};

@Component({
  selector: 'app-metric-card',
  template: `
    <div
      class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      role="group"
      [attr.aria-label]="title()"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-sm font-medium text-slate-600">{{ title() }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ value() }}</p>
          <p class="mt-1 text-sm text-slate-500">{{ helper() }}</p>
        </div>
        <span
          class="h-10 w-1 rounded-full"
          aria-hidden="true"
          [class]="toneClasses()"
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

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
