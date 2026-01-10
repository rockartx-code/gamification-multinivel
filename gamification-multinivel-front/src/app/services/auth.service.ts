import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { AuthContext } from '../domain/models';
import { authFixture } from '../mocks/auth.fixture';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiClient = inject(ApiClient);

  getAuthContext(): Observable<AuthContext> {
    return this.apiClient.get(authFixture);
  }
}
