import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { ProgressBarComponent } from '../../core/components/progress-bar.component';
import { StatusBadgeComponent } from '../../core/components/status-badge.component';
import { Mission } from '../../domain/models';
import { MissionsService } from '../../services/missions.service';

@Component({
  selector: 'app-missions',
  imports: [ProgressBarComponent, StatusBadgeComponent],
  template: `
    <section class="app-card app-card--soft p-6">
      <div>
        <p class="app-eyebrow">
          Misiones
        </p>
        <h2 class="text-xl font-semibold text-white">Objetivos en curso</h2>
      </div>
      <div class="mt-5 space-y-4">
        @for (mission of missions(); track mission.id) {
          <article class="app-card app-card--soft p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-sm font-semibold text-white">
                  {{ mission.title }}
                </h3>
                <p class="mt-1 text-sm text-slate-300">
                  {{ mission.description }}
                </p>
                <p class="mt-2 text-xs font-medium text-slate-400">
                  Recompensa: {{ mission.rewardPoints }} puntos
                </p>
              </div>
              <app-status-badge
                [label]="statusLabel(mission)"
                [tone]="statusTone(mission)"
              />
            </div>
            <div class="mt-4">
              <app-progress-bar
                label="Progreso"
                [value]="mission.progressPercent"
                [max]="100"
                [tone]="statusTone(mission)"
              />
            </div>
          </article>
        }
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MissionsComponent {
  private readonly missionsService = inject(MissionsService);

  protected readonly missions = toSignal(this.missionsService.getMissions(), {
    initialValue: [],
  });

  protected statusLabel(mission: Mission): string {
    if (mission.status === 'completed') {
      return 'Completada';
    }
    if (mission.status === 'active') {
      return 'Activa';
    }
    return 'Pendiente';
  }

  protected statusTone(mission: Mission): 'success' | 'warning' | 'danger' {
    if (mission.status === 'completed') {
      return 'success';
    }
    if (mission.status === 'active') {
      return 'warning';
    }
    return 'danger';
  }
}
