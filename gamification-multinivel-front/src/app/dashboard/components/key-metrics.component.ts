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
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Métricas clave
        </p>
        <h2 class="text-xl font-semibold text-slate-900">
          Tu impacto esta semana
        </h2>
      </div>
      <div class="grid gap-4 md:grid-cols-2">
        <app-metric-card
          title="Ingresos"
          [value]="revenue()"
          helper="Total generado"
          tone="success"
        />
        <app-metric-card
          title="Comisiones"
          [value]="commissions()"
          helper="Ganancia acumulada"
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

  private readonly currencyFormatter = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });

  protected readonly revenue = computed(() =>
    this.metrics() ? this.currencyFormatter.format(this.metrics()!.revenue) : '$0'
  );

  protected readonly commissions = computed(() =>
    this.metrics()
      ? this.currencyFormatter.format(this.metrics()!.commissions)
      : '$0'
  );

  protected readonly newMembers = computed(() =>
    this.metrics() ? `${this.metrics()!.newMembers}` : '0'
  );

  protected readonly conversionRate = computed(() =>
    this.metrics() ? `${this.metrics()!.conversionRate}%` : '0%'
  );
}
