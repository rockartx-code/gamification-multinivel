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
    const source = config ?? DEFAULT_BUSINESS_CONFIG;
    const next: AppBusinessConfig = {
      version: this.normalizeRequiredString(source.version, DEFAULT_BUSINESS_CONFIG.version),
      rewards: {
        version: this.normalizeRequiredString(source.rewards?.version, DEFAULT_BUSINESS_CONFIG.rewards.version),
        activationNetMin: this.parseNonNegativeNumber(source.rewards?.activationNetMin),
        discountTiers: this.normalizeDiscountTiers(source.rewards?.discountTiers, sortDiscountTiers),
        commissionByDepth: {
          '1': this.normalizeDiscountRateValue(source.rewards?.commissionByDepth?.['1']),
          '2': this.normalizeDiscountRateValue(source.rewards?.commissionByDepth?.['2']),
          '3': this.normalizeDiscountRateValue(source.rewards?.commissionByDepth?.['3'])
        },
        payoutDay: this.normalizePositiveInteger(source.rewards?.payoutDay, DEFAULT_BUSINESS_CONFIG.rewards.payoutDay),
        cutRule: this.normalizeRequiredString(source.rewards?.cutRule, DEFAULT_BUSINESS_CONFIG.rewards.cutRule)
      },
      orders: {
        requireStockOnShipped: this.normalizeBoolean(
          source.orders?.requireStockOnShipped,
          DEFAULT_BUSINESS_CONFIG.orders.requireStockOnShipped
        ),
        requireDispatchLinesOnShipped: this.normalizeBoolean(
          source.orders?.requireDispatchLinesOnShipped,
          DEFAULT_BUSINESS_CONFIG.orders.requireDispatchLinesOnShipped
        )
      },
      pos: {
        defaultCustomerName: this.normalizeRequiredString(
          source.pos?.defaultCustomerName,
          DEFAULT_BUSINESS_CONFIG.pos.defaultCustomerName
        ),
        defaultPaymentStatus: this.normalizeRequiredString(
          source.pos?.defaultPaymentStatus,
          DEFAULT_BUSINESS_CONFIG.pos.defaultPaymentStatus
        ),
        defaultDeliveryStatus: this.normalizeRequiredString(
          source.pos?.defaultDeliveryStatus,
          DEFAULT_BUSINESS_CONFIG.pos.defaultDeliveryStatus
        ),
        orderStatusByDeliveryStatus: {
          delivered_branch: this.normalizeRequiredString(
            source.pos?.orderStatusByDeliveryStatus?.delivered_branch,
            DEFAULT_BUSINESS_CONFIG.pos.orderStatusByDeliveryStatus.delivered_branch
          ),
          paid_branch: this.normalizeRequiredString(
            source.pos?.orderStatusByDeliveryStatus?.paid_branch,
            DEFAULT_BUSINESS_CONFIG.pos.orderStatusByDeliveryStatus.paid_branch
          )
        }
      },
      stocks: {
        requireLinkedUserForTransferReceive: this.normalizeBoolean(
          source.stocks?.requireLinkedUserForTransferReceive,
          DEFAULT_BUSINESS_CONFIG.stocks.requireLinkedUserForTransferReceive
        )
      },
      payments: {
        mercadoLibre: {
          enabled: this.normalizeBoolean(
            source.payments?.mercadoLibre?.enabled,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.enabled
          ),
          accessToken: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.accessToken,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.accessToken
          ),
          checkoutPreferencesUrl: this.normalizeRequiredString(
            source.payments?.mercadoLibre?.checkoutPreferencesUrl,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.checkoutPreferencesUrl
          ),
          paymentInfoUrlTemplate: this.normalizeRequiredString(
            source.payments?.mercadoLibre?.paymentInfoUrlTemplate,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.paymentInfoUrlTemplate
          ),
          notificationUrl: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.notificationUrl,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.notificationUrl
          ),
          successUrl: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.successUrl,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.successUrl
          ),
          failureUrl: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.failureUrl,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.failureUrl
          ),
          pendingUrl: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.pendingUrl,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.pendingUrl
          ),
          currencyId: this.normalizeRequiredString(
            source.payments?.mercadoLibre?.currencyId,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.currencyId
          ),
          webhookSecret: this.normalizeOptionalString(
            source.payments?.mercadoLibre?.webhookSecret,
            DEFAULT_BUSINESS_CONFIG.payments.mercadoLibre.webhookSecret
          )
        }
      },
      adminWarnings: {
        showCommissions: this.normalizeBoolean(
          source.adminWarnings?.showCommissions,
          DEFAULT_BUSINESS_CONFIG.adminWarnings.showCommissions
        ),
        showShipping: this.normalizeBoolean(source.adminWarnings?.showShipping, DEFAULT_BUSINESS_CONFIG.adminWarnings.showShipping),
        showPendingPayments: this.normalizeBoolean(
          source.adminWarnings?.showPendingPayments,
          DEFAULT_BUSINESS_CONFIG.adminWarnings.showPendingPayments
        ),
        showPendingTransfers: this.normalizeBoolean(
          source.adminWarnings?.showPendingTransfers,
          DEFAULT_BUSINESS_CONFIG.adminWarnings.showPendingTransfers
        ),
        showPosSalesToday: this.normalizeBoolean(
          source.adminWarnings?.showPosSalesToday,
          DEFAULT_BUSINESS_CONFIG.adminWarnings.showPosSalesToday
        )
      }
    };

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

  private normalizePositiveInteger(value: unknown, fallback: number): number {
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      return fallback;
    }
    return parsed;
  }

  private normalizeBoolean(value: unknown, fallback: boolean): boolean {
    if (typeof value === 'boolean') {
      return value;
    }
    return fallback;
  }

  private normalizeRequiredString(value: unknown, fallback: string): string {
    return typeof value === 'string' && value.trim() ? value : fallback;
  }

  private normalizeOptionalString(value: unknown, fallback: string): string {
    return typeof value === 'string' ? value : fallback;
  }

  private ensureAllowedValue<T extends string>(value: unknown, options: readonly T[], fallback: T): T {
    return options.find((option) => String(option) === String(value)) ?? fallback;
  }

  private roundMoney(value: number): number {
    return Math.round(value * 100) / 100;
  }
}
