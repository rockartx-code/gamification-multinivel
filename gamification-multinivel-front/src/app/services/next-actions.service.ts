import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { NextAction } from '../domain/models';
import { nextActionsFixture } from '../mocks/next-actions.fixture';

@Injectable({ providedIn: 'root' })
export class NextActionsService {
  private readonly apiClient = inject(ApiClient);

  getNextActions(): Observable<NextAction[]> {
    return this.apiClient.get(nextActionsFixture);
  }
}
