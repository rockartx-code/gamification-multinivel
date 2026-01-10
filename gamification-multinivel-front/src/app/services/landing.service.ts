import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Landing } from '../domain/models';
import { landingFixture } from '../mocks/landing.fixture';

@Injectable({ providedIn: 'root' })
export class LandingService {
  private readonly apiClient = inject(ApiClient);

  getLanding(): Observable<Landing> {
    return this.apiClient.get(landingFixture);
  }
}
