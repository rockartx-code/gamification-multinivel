import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Commission } from '../domain/models';
import { commissionsFixture } from '../mocks/commissions.fixture';

@Injectable({ providedIn: 'root' })
export class CommissionsService {
  private readonly apiClient = inject(ApiClient);

  getCommissions(): Observable<Commission[]> {
    return this.apiClient.get(commissionsFixture);
  }
}
