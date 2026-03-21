import { AppBusinessConfig } from '../models/admin.model';

export const DEFAULT_BUSINESS_CONFIG: AppBusinessConfig = {
  version: 'app-v1',
  rewards: {
    version: 'v1',
    activationNetMin: 2500,
    discountTiers: [
      { min: 3600, max: 8000, rate: 0.3 },
      { min: 8001, max: 12000, rate: 0.4 },
      { min: 12001, max: null, rate: 0.5 }
    ],
    commissionByDepth: { '1': 0.1, '2': 0.05, '3': 0.03 },
    payoutDay: 10,
    cutRule: 'hard_cut_no_pass'
  },
  orders: {
    requireStockOnShipped: true,
    requireDispatchLinesOnShipped: true
  },
  pos: {
    defaultCustomerName: 'Publico en General',
    defaultPaymentStatus: 'paid_branch',
    defaultDeliveryStatus: 'delivered_branch',
    orderStatusByDeliveryStatus: {
      delivered_branch: 'delivered',
      paid_branch: 'paid'
    }
  },
  stocks: {
    requireLinkedUserForTransferReceive: true
  },
  payments: {
    mercadoLibre: {
      enabled: false,
      accessToken: '',
      checkoutPreferencesUrl: 'https://api.mercadopago.com/checkout/preferences',
      paymentInfoUrlTemplate: 'https://api.mercadopago.com/v1/payments/{payment_id}',
      notificationUrl: 'https://m85v7secp8.execute-api.us-east-1.amazonaws.com/default/Multinivel/webhooks/mercadolibre',
      successUrl: 'https://www.findingu.com.mx/#/orden/{payment_id}?status=success',
      failureUrl: 'https://www.findingu.com.mx/#/orden/{payment_id}?status=failure',
      pendingUrl: 'https://www.findingu.com.mx/#/orden/{payment_id}?status=pending',
      currencyId: 'MXN',
      webhookSecret: ''
    }
  },
  adminWarnings: {
    showCommissions: true,
    showShipping: true,
    showPendingPayments: true,
    showPendingTransfers: true,
    showPosSalesToday: true
  }
};
