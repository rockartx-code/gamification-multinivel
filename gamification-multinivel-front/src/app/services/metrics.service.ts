import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Metrics } from '../domain/models';
import { metricsFixture } from '../mocks/metrics.fixture';

@Injectable({ providedIn: 'root' })
export class MetricsService {
  private readonly apiClient = inject(ApiClient);

  getMetrics(): Observable<Metrics> {
    return this.apiClient.get(metricsFixture);
  }
}
