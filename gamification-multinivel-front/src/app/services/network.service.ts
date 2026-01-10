import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { NetworkMember } from '../domain/models';
import { networkMembersFixture } from '../mocks/network-members.fixture';

@Injectable({ providedIn: 'root' })
export class NetworkService {
  private readonly apiClient = inject(ApiClient);

  getNetworkMembers(): Observable<NetworkMember[]> {
    return this.apiClient.get(networkMembersFixture);
  }
}
