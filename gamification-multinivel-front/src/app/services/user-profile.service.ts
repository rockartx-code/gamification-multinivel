import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { UserProfile } from '../domain/models';
import { userProfileFixture } from '../mocks/user-profile.fixture';

@Injectable({ providedIn: 'root' })
export class UserProfileService {
  private readonly apiClient = inject(ApiClient);

  getUserProfile(): Observable<UserProfile> {
    return this.apiClient.get(userProfileFixture);
  }
}
