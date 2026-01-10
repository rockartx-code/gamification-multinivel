import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Landing } from '../domain/models';
import { landingsFixture } from '../mocks/landings.fixture';

@Injectable({ providedIn: 'root' })
export class LandingsService {
  private readonly apiClient = inject(ApiClient);

  getLandings(): Observable<Landing[]> {
    return this.apiClient.get(landingsFixture);
  }
}
