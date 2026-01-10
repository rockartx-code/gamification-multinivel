import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Goal } from '../domain/models';
import { goalsFixture } from '../mocks/goals.fixture';

@Injectable({ providedIn: 'root' })
export class GoalsService {
  private readonly apiClient = inject(ApiClient);

  getGoals(): Observable<Goal[]> {
    return this.apiClient.get(goalsFixture);
  }
}
