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
    <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Siguiente acción
          </p>
          <h2 class="text-xl font-semibold text-slate-900">
            {{ headline() }}
          </h2>
        </div>
        <span class="text-sm font-medium text-slate-600">
          {{ pendingCount() }} pendientes
        </span>
      </div>
      <ul class="mt-5 space-y-4">
        @for (action of nextActions(); track action.id) {
          <li
            class="rounded-xl border border-slate-100 bg-slate-50 p-4"
            [class.opacity-70]="action.completed"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  {{ action.label }}
                </p>
                <p class="mt-1 text-sm text-slate-600">
                  {{ action.description }}
                </p>
                <p class="mt-2 text-xs font-medium text-slate-500">
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
