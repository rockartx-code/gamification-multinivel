import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-green-50 text-green-700 ring-green-600/20',
  warning: 'bg-yellow-50 text-yellow-800 ring-yellow-600/30',
  danger: 'bg-red-50 text-red-700 ring-red-600/20',
};

@Component({
  selector: 'app-status-badge',
  template: `
    <span
      class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset"
      role="status"
      [class]="toneClasses()"
    >
      {{ label() }}
    </span>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusBadgeComponent {
  label = input<string>('Activo');
  tone = input<StatusTone>('success');

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
