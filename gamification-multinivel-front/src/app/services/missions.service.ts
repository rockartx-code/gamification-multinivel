import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Mission } from '../domain/models';
import { missionsFixture } from '../mocks/missions.fixture';

@Injectable({ providedIn: 'root' })
export class MissionsService {
  private readonly apiClient = inject(ApiClient);

  getMissions(): Observable<Mission[]> {
    return this.apiClient.get(missionsFixture);
  }
}
