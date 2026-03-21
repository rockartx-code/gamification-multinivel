import { Injectable } from '@angular/core';

export type UserDashboardProfileBadgeState = {
  iconClass: string;
  ringClass: string;
  miniBadgeClass: string;
};

type UserDashboardProfileBadgeInput = {
  isClient: boolean;
  discountActive: boolean;
  discountPercent: number;
};

@Injectable({
  providedIn: 'root'
})
export class UserDashboardProfileBadgeService {
  buildState(input: UserDashboardProfileBadgeInput): UserDashboardProfileBadgeState {
    if (!input.isClient || !input.discountActive) {
      return {
        iconClass: 'icon-status-inactive',
        ringClass: 'ring ring-status-inactive level-5',
        miniBadgeClass: 'badge badge-compact status-inactive'
      };
    }

    const levelClass = this.resolveLevelClass(input.discountPercent);
    return {
      iconClass: 'icon-status-active',
      ringClass: `ring ring-status-active ${levelClass}`,
      miniBadgeClass: `badge badge-compact status-active ${levelClass}`
    };
  }

  private resolveLevelClass(discountPercent: number): string {
    if (discountPercent >= 50) {
      return 'level-1';
    }
    if (discountPercent >= 40) {
      return 'level-2';
    }
    if (discountPercent >= 30) {
      return 'level-3';
    }
    if (discountPercent >= 20) {
      return 'level-4';
    }
    return 'level-5';
  }
}
