import { Injectable } from '@angular/core';

import { AppBusinessConfig } from '../models/admin.model';
import { BusinessConfigDiscountTier } from '../models/business-config.model';
import { DEFAULT_BUSINESS_CONFIG } from './business-config.defaults';

@Injectable({
  providedIn: 'root'
})
export class BusinessConfigService {
  private readonly rewardCutRuleValues: AppBusinessConfig['rewards']['cutRule'][] = ['hard_cut_no_pass', 'carry_over'];
  private readonly paymentStatusValues: AppBusinessConfig['pos']['defaultPaymentStatus'][] = ['paid_branch'];
  private readonly deliveryStatusValues: AppBusinessConfig['pos']['defaultDeliveryStatus'][] = ['delivered_branch'];
  private readonly orderStatusValues: AppBusinessConfig['pos']['orderStatusByDeliveryStatus']['delivered_branch'][] = ['delivered', 'paid'];

  createDefaultConfig(): AppBusinessConfig {
    return structuredClone(DEFAULT_BUSINESS_CONFIG);
  }

  normalizeForDraft(config: AppBusinessConfig | null | undefined): AppBusinessConfig {
    return this.normalizeConfig(config, false);
  }

  normalizeForSave(config: AppBusinessConfig | null | undefined): AppBusinessConfig {
    return this.normalizeConfig(config, true);
  }

  private normalizeConfig(config: AppBusinessConfig | null | undefined, sortDiscountTiers: boolean): AppBusinessConfig {
    const next = structuredClone(config ?? DEFAULT_BUSINESS_CONFIG);
    next.rewards.discountTiers = this.normalizeDiscountTiers(next.rewards.discountTiers, sortDiscountTiers);
    this.normalizeSelectValues(next);
    return next;
  }

  private normalizeSelectValues(config: AppBusinessConfig): void {
    config.rewards.cutRule = this.ensureAllowedValue(config.rewards.cutRule, this.rewardCutRuleValues, 'hard_cut_no_pass');
    config.pos.defaultPaymentStatus = this.ensureAllowedValue(config.pos.defaultPaymentStatus, this.paymentStatusValues, 'paid_branch');
    config.pos.defaultDeliveryStatus = this.ensureAllowedValue(config.pos.defaultDeliveryStatus, this.deliveryStatusValues, 'delivered_branch');
    config.pos.orderStatusByDeliveryStatus.delivered_branch = this.ensureAllowedValue(
      config.pos.orderStatusByDeliveryStatus.delivered_branch,
      this.orderStatusValues,
      'delivered'
    );
    config.pos.orderStatusByDeliveryStatus.paid_branch = this.ensureAllowedValue(
      config.pos.orderStatusByDeliveryStatus.paid_branch,
      this.orderStatusValues,
      'paid'
    );
  }

  private normalizeDiscountTiers(
    tiers: BusinessConfigDiscountTier[] | null | undefined,
    sortByMin: boolean
  ): BusinessConfigDiscountTier[] {
    const fallback = DEFAULT_BUSINESS_CONFIG.rewards.discountTiers;
    const source = Array.isArray(tiers) && tiers.length ? tiers : fallback;
    const normalized = source.map((tier) => ({
      min: this.parseNonNegativeNumber(tier?.min),
      max: null,
      rate: this.normalizeDiscountRateValue(tier?.rate)
    }));
    const ordered = sortByMin ? [...normalized].sort((left, right) => left.min - right.min) : normalized;
    return ordered.map((tier, index) => {
      const nextMin = ordered[index + 1]?.min;
      return {
        ...tier,
        max: Number.isFinite(nextMin) && nextMin > tier.min ? nextMin - 1 : null
      };
    });
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

  private ensureAllowedValue<T extends string>(value: unknown, options: readonly T[], fallback: T): T {
    return options.find((option) => String(option) === String(value)) ?? fallback;
  }

  private roundMoney(value: number): number {
    return Math.round(value * 100) / 100;
  }
}
