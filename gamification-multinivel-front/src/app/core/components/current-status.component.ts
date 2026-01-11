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
    <section class="app-card app-card--soft p-5">
      <p class="app-eyebrow">Estado actual</p>
      <div class="mt-3 flex flex-wrap items-start gap-3">
        <app-status-badge [label]="badgeLabel()" [tone]="tone()" />
        <p class="text-sm text-slate-300">{{ description() }}</p>
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
