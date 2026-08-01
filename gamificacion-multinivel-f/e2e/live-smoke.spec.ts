import { test, expect } from '@playwright/test';
import { API_BASE } from './support/fixtures';

// Smoke @live contra el API dev real (microlambdas). Solo corre con E2E_LIVE=1.
// Valida los fixes desplegados el 2026-08-01: floats en órdenes y config pública.

test('@live config pública expone activación en pesos y rangos con requiredDirects', async ({ request }) => {
  const res = await request.get(`${API_BASE}/catalog/config/public`);
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.config.rewards.activationNetMin).toBe(2500);
  expect(Array.isArray(body.config.bonuses.rankThresholds)).toBe(true);
});

test('@live crear orden con precio decimal ya no falla (fix float→Decimal) y se cancela', async ({ request }) => {
  const create = await request.post(`${API_BASE}/orders/create`, {
    data: {
      customerId: 0,
      customerName: 'E2E Live Smoke',
      items: [{ productId: 'TEST-LIVE-SMOKE', name: 'Smoke live', qty: 1, price: 149.99 }],
      deliveryType: 'pickup',
      pickupPaymentMethod: 'at_store',
      notes: 'ORDEN DE PRUEBA @live - se cancela automáticamente'
    }
  });
  expect([200, 201]).toContain(create.status());
  const { order } = await create.json();
  expect(order.orderId).toBeTruthy();
  expect(order.netTotal).toBeCloseTo(149.99, 2);

  const cancel = await request.patch(`${API_BASE}/orders/${order.orderId}`, {
    headers: { 'x-user-id': 'admin-001', 'x-user-name': 'Admin', 'x-user-role': 'admin' },
    data: { status: 'cancelled', cancelReason: 'Smoke @live automático' }
  });
  expect(cancel.status()).toBe(200);
});
