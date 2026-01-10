import { ChangeDetectionStrategy, Component } from '@angular/core';

import { AchievementsComponent } from './components/achievements.component';
import { ActiveGoalComponent } from './components/active-goal.component';
import { CoachHeaderComponent } from './components/coach-header.component';
import { KeyMetricsComponent } from './components/key-metrics.component';
import { MissionsComponent } from './components/missions.component';
import { NextActionComponent } from './components/next-action.component';
import { CurrentStatusComponent } from '../core/components/current-status.component';

@Component({
  selector: 'app-dashboard-page',
  imports: [
    CoachHeaderComponent,
    CurrentStatusComponent,
    ActiveGoalComponent,
    NextActionComponent,
    KeyMetricsComponent,
    AchievementsComponent,
    MissionsComponent,
  ],
  template: `
    <main class="space-y-6 bg-slate-50 px-4 py-6 md:px-8">
      <app-coach-header actionLabel="Revisar siguiente acción" />
      <section class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div class="space-y-6">
          <app-current-status
            label="En ritmo"
            description="Mantén la constancia y revisa las prioridades del día."
            tone="success"
          />
          <app-active-goal />
          <app-next-action />
          <app-key-metrics />
        </div>
        <div class="space-y-6">
          <app-achievements />
          <app-missions />
        </div>
      </section>
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardPage {}
