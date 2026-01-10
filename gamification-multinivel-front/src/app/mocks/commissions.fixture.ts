import { Commission } from '../domain/models';

export const commissionsFixture: Commission[] = [
  {
    id: 'commission-001',
    amount: 120,
    ratePercent: 12,
    orderId: 'order-001',
    earnedAt: '2025-03-18T10:00:00Z',
    status: 'paid',
  },
  {
    id: 'commission-002',
    amount: 150,
    ratePercent: 12,
    orderId: 'order-002',
    earnedAt: '2025-03-19T15:00:00Z',
    status: 'pending',
  },
];
