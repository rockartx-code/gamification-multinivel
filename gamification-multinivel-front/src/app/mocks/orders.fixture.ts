import { Order } from '../domain/models';

export const ordersFixture: Order[] = [
  {
    id: 'order-001',
    impactPoints: 980,
    createdAt: '2025-03-18T09:12:00Z',
    status: 'paid',
    customerId: 'customer-001',
  },
  {
    id: 'order-002',
    impactPoints: 1250,
    createdAt: '2025-03-19T14:05:00Z',
    status: 'fulfilled',
    customerId: 'customer-002',
  },
];
