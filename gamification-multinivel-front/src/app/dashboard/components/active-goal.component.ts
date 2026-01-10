import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { ProgressBarComponent } from '../../core/components/progress-bar.component';
import { GoalsService } from '../../services/goals.service';

@Component({
  selector: 'app-active-goal',
  imports: [CTAButtonComponent, ProgressBarComponent],
  template: `
    <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Meta activa
          </p>
          <h2 class="text-2xl font-semibold text-slate-900">
            {{ title() }}
          </h2>
          <p class="text-sm text-slate-600">{{ remainingMessage() }}</p>
          @if (dueDate()) {
            <p class="text-xs text-slate-500">Fecha límite: {{ dueDate() }}</p>
          }
        </div>
        <div class="min-w-[220px]">
          <app-cta-button [label]="ctaLabel()" tone="success" />
        </div>
      </div>
      <div class="mt-6">
        <app-progress-bar
          label="Avance de la meta"
          [value]="progressValue()"
          [max]="targetAmount()"
          tone="success"
        />
        <p class="mt-3 text-sm font-medium text-slate-700">
          {{ progressSummary() }}
        </p>
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActiveGoalComponent {
  private readonly goalsService = inject(GoalsService);

  private readonly goals = toSignal(this.goalsService.getGoals(), {
    initialValue: [],
  });

  protected readonly activeGoal = computed(() => this.goals()[0] ?? null);
  protected readonly title = computed(() => this.activeGoal()?.title ?? 'Sin meta activa');
  protected readonly remainingMessage = computed(
    () => this.activeGoal()?.remainingMessage ?? 'Define tu próxima meta.'
  );
  protected readonly dueDate = computed(() => this.activeGoal()?.dueDate ?? '');
  protected readonly targetAmount = computed(() => this.activeGoal()?.targetAmount ?? 0);
  protected readonly progressValue = computed(() => this.activeGoal()?.currentAmount ?? 0);
  protected readonly progressSummary = computed(() => {
    if (!this.activeGoal()) {
      return 'Aún no tienes una meta activa asignada.';
    }
    return `${this.progressValue()} de ${this.targetAmount()} completado.`;
  });
  protected readonly ctaLabel = computed(() =>
    this.activeGoal() ? 'Continuar con la meta' : 'Crear nueva meta'
  );
}
