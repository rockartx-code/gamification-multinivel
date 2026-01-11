import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { MetricCardComponent } from '../../core/components/metric-card.component';
import { MetricsService } from '../../services/metrics.service';

@Component({
  selector: 'app-key-metrics',
  imports: [MetricCardComponent],
  template: `
    <section class="space-y-4">
      <div>
        <p class="app-eyebrow">
          Métricas clave
        </p>
        <h2 class="text-xl font-semibold text-white">
          Tu impacto esta semana
        </h2>
      </div>
      <div class="grid gap-4 md:grid-cols-2">
        <app-metric-card
          title="Impacto"
          [value]="impactPoints()"
          helper="Puntos logrados"
          tone="success"
        />
        <app-metric-card
          title="Avance"
          [value]="progressPoints()"
          helper="Puntos de progreso"
          tone="warning"
        />
        <app-metric-card
          title="Nuevos miembros"
          [value]="newMembers()"
          helper="Incorporaciones"
          tone="success"
        />
        <app-metric-card
          title="Conversión"
          [value]="conversionRate()"
          helper="Eficiencia del embudo"
          tone="warning"
        />
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KeyMetricsComponent {
  private readonly metricsService = inject(MetricsService);

  private readonly metrics = toSignal(this.metricsService.getMetrics(), {
    initialValue: null,
  });

  private readonly pointsFormatter = new Intl.NumberFormat('es-CO', {
    maximumFractionDigits: 0,
  });

  protected readonly impactPoints = computed(() =>
    this.metrics()
      ? `${this.pointsFormatter.format(this.metrics()!.impactPoints)} pts`
      : '0 pts'
  );

  protected readonly progressPoints = computed(() =>
    this.metrics()
      ? `${this.pointsFormatter.format(this.metrics()!.progressPoints)} pts`
      : '0 pts'
  );

  protected readonly newMembers = computed(() =>
    this.metrics() ? `${this.metrics()!.newMembers}` : '0'
  );

  protected readonly conversionRate = computed(() =>
    this.metrics() ? `${this.metrics()!.conversionRate}%` : '0%'
  );
}
