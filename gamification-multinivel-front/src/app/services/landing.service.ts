import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Landing } from '../domain/models';
import { landingFixture } from '../mocks/landing.fixture';

interface LandingReferralContext {
  referrerUserId: string;
  landingSlug: string;
}

@Injectable({ providedIn: 'root' })
export class LandingService {
  private readonly apiClient = inject(ApiClient);
  private readonly referralContext = signal<LandingReferralContext | null>(null);

  getLanding(): Observable<Landing> {
    return this.apiClient.get(landingFixture);
  }

  saveReferralContext(referrerUserId: string, landingSlug: string): void {
    this.referralContext.set({ referrerUserId, landingSlug });
  }
}
