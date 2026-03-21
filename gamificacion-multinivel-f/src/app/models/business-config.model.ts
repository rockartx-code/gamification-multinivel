import { AppBusinessConfig } from './admin.model';

export type BusinessConfigDiscountTier = AppBusinessConfig['rewards']['discountTiers'][number];
export type BusinessConfigNotificationTone = 'info' | 'success' | 'error';
