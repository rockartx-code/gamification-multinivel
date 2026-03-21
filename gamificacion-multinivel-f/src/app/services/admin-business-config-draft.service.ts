import { Injectable } from '@angular/core';

import { AppBusinessConfig } from '../models/admin.model';
import { BusinessConfigDiscountTier } from '../models/business-config.model';
import { BusinessConfigService } from './business-config.service';

@Injectable({
  providedIn: 'root'
})
export class AdminBusinessConfigDraftService {
  constructor(private readonly businessConfigService: BusinessConfigService) {}

  createDefaultDraft(): AppBusinessConfig {
    return this.businessConfigService.createDefaultConfig();
  }

  normalizeDraft(config: AppBusinessConfig | null | undefined): AppBusinessConfig {
    return this.businessConfigService.normalizeForDraft(config);
  }

  prepareDraftForSave(config: AppBusinessConfig | null | undefined): AppBusinessConfig {
    return this.businessConfigService.normalizeForSave(config);
  }

  restoreDefaults(): AppBusinessConfig {
    return this.businessConfigService.createDefaultConfig();
  }

  discountTierPercentValue(tier: BusinessConfigDiscountTier): number {
    return this.roundMoney(this.normalizeDiscountRateValue(tier?.rate) * 100);
  }

  discountTierRangeLabel(tier: BusinessConfigDiscountTier, formatMoney: (value: number) => string): string {
    const min = this.parseNonNegativeNumber(tier?.min);
    const max = tier?.max == null ? null : this.parseNonNegativeNumber(tier.max);
    if (max == null || max < min) {
      return `Desde ${formatMoney(min)}`;
    }
    return `${formatMoney(min)} a ${formatMoney(max)}`;
  }

  updateDiscountTierMin(config: AppBusinessConfig, index: number, value: unknown): AppBusinessConfig {
    const next = structuredClone(config);
    const tiers = next.rewards.discountTiers ?? [];
    if (!tiers[index]) {
      return next;
    }
    tiers[index].min = this.parseNonNegativeNumber(value);
    return this.normalizeDraft(next);
  }

  updateDiscountTierRate(config: AppBusinessConfig, index: number, value: unknown): AppBusinessConfig {
    const next = structuredClone(config);
    const tiers = next.rewards.discountTiers ?? [];
    if (!tiers[index]) {
      return next;
    }
    const percent = Math.min(100, this.parseNonNegativeNumber(value));
    tiers[index].rate = this.roundMoney(percent / 100);
    return this.normalizeDraft(next);
  }

  private parseNonNegativeNumber(value: unknown): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return 0;
    }
    return this.roundMoney(parsed);
  }

  private normalizeDiscountRateValue(value: unknown): number {
    const parsed = this.parseNonNegativeNumber(value);
    const normalized = parsed > 1 ? parsed / 100 : parsed;
    return Math.min(1, this.roundMoney(normalized));
  }

  private roundMoney(value: number): number {
    return Math.round(value * 100) / 100;
  }
}
