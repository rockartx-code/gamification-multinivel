import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Achievement } from '../domain/models';
import { achievementsFixture } from '../mocks/achievements.fixture';

@Injectable({ providedIn: 'root' })
export class AchievementsService {
  private readonly apiClient = inject(ApiClient);

  getAchievements(): Observable<Achievement[]> {
    return this.apiClient.get(achievementsFixture);
  }
}
