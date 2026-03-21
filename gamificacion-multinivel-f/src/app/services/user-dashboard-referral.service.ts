import { Injectable } from '@angular/core';

import { SponsorContact } from '../models/user-dashboard.model';

@Injectable({ providedIn: 'root' })
export class UserDashboardReferralService {
  private readonly fallbackSponsorEmail = 'coach@findingu.com.mx';
  private readonly fallbackSponsorPhone = '+52 1 55 1498 2351';
  private readonly sponsorWhatsappMessage = 'Hola, necesito ayuda con mi red de FindingU.';

  buildReferralLink(params: {
    isGuest: boolean;
    userCode?: string | null;
    activeFeaturedId?: string | null;
    origin: string;
  }): string {
    if (params.isGuest) {
      return '';
    }
    const userCode = (params.userCode ?? '').trim();
    if (!userCode) {
      return '';
    }
    const productId = params.activeFeaturedId ?? '';
    const query = productId ? `?p=${productId}` : '';
    return `${params.origin}/#/${userCode}${query}`;
  }

  getSponsorEmailHref(sponsor?: SponsorContact | null): string {
    const email = (sponsor?.email ?? '').trim() || this.fallbackSponsorEmail;
    return `mailto:${encodeURIComponent(email)}`;
  }

  getSponsorWhatsappHref(sponsor?: SponsorContact | null): string {
    const digits = (sponsor?.phone ?? this.fallbackSponsorPhone).replace(/\D/g, '');
    const text = encodeURIComponent(this.sponsorWhatsappMessage);
    return `whatsapp://send?phone=${digits}&text=${text}`;
  }
}
