import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { StatusBadgeComponent } from './status-badge.component';

type StatusTone = 'success' | 'warning' | 'danger';

const STATUS_LABELS: Record<StatusTone, string> = {
  success: 'En ritmo',
  warning: 'Requiere atención',
  danger: 'Fuera de foco',
};

@Component({
  selector: 'app-current-status',
  imports: [StatusBadgeComponent],
  template: `
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Estado actual
      </p>
      <div class="mt-3 flex flex-wrap items-start gap-3">
        <app-status-badge [label]="badgeLabel()" [tone]="tone()" />
        <p class="text-sm text-slate-600">{{ description() }}</p>
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CurrentStatusComponent {
  tone = input<StatusTone>('success');
  label = input<string>('');
  description = input<string>('Mantén el ritmo con los próximos pasos recomendados.');

  protected readonly badgeLabel = computed(() => this.label() || STATUS_LABELS[this.tone()]);
}
