import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { NextAction } from '../../domain/models';
import { NextActionsService } from '../../services/next-actions.service';

@Component({
  selector: 'app-next-action',
  imports: [StatusBadgeComponent],
  host: {
    id: 'next-action',
    class: 'scroll-mt-24',
  },
  template: `
    <section class="app-card app-card--soft p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="app-eyebrow">
            Siguiente acción
          </p>
          <h2 class="text-xl font-semibold text-white">
            {{ headline() }}
          </h2>
        </div>
        <span class="text-sm font-medium text-slate-300">
          {{ pendingCount() }} pendientes
        </span>
      </div>
      <ul class="mt-5 space-y-4">
        @for (action of nextActions(); track action.id) {
          <li
            class="app-card app-card--soft p-4"
            [class.opacity-70]="action.completed"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-white">
                  {{ action.label }}
                </p>
                <p class="mt-1 text-sm text-slate-300">
                  {{ action.description }}
                </p>
                <p class="mt-2 text-xs font-medium text-slate-400">
                  Recompensa: {{ action.rewardPoints }} puntos
                </p>
              </div>
              <app-status-badge
                [label]="statusLabel(action)"
                [tone]="statusTone(action)"
              />
            </div>
          </li>
        }
      </ul>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NextActionComponent {
  private readonly nextActionsService = inject(NextActionsService);

  protected readonly nextActions = toSignal(
    this.nextActionsService.getNextActions(),
    { initialValue: [] }
  );

  protected readonly pendingCount = computed(
    () => this.nextActions().filter((action) => !action.completed).length
  );

  protected readonly headline = computed(() => {
    const pendingAction = this.nextActions().find((action) => !action.completed);
    return pendingAction?.label ?? 'No hay acciones pendientes';
  });

  protected statusLabel(action: NextAction): string {
    return action.completed ? 'Completada' : 'Pendiente';
  }

  protected statusTone(action: NextAction): 'success' | 'warning' {
    return action.completed ? 'success' : 'warning';
  }
}
