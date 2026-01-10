import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

export interface LandingReferralContext {
  referrerUserId: string;
  landingSlug: string;
}

const REFERRAL_STORAGE_KEY = 'landing-referral-context';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly referralContext = signal<LandingReferralContext | null>(null);
  readonly landingContext = this.referralContext.asReadonly();

  constructor() {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const storedContext = window.localStorage.getItem(REFERRAL_STORAGE_KEY);
    if (!storedContext) {
      return;
    }

    try {
      const parsedContext = JSON.parse(storedContext) as LandingReferralContext;
      if (parsedContext?.referrerUserId && parsedContext?.landingSlug) {
        this.referralContext.set(parsedContext);
      }
    } catch {
      window.localStorage.removeItem(REFERRAL_STORAGE_KEY);
    }
  }

  saveLandingContext(referrerUserId: string, landingSlug: string): void {
    const context = { referrerUserId, landingSlug };
    this.referralContext.set(context);

    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    window.localStorage.setItem(REFERRAL_STORAGE_KEY, JSON.stringify(context));
  }

  clearLandingContext(): void {
    this.referralContext.set(null);

    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    window.localStorage.removeItem(REFERRAL_STORAGE_KEY);
  }
}
