import { test, expect, acceptPrivacyNotice, mockApi, blockUnmockedApi } from './support/fixtures';
import type { Page } from '@playwright/test';

// Dominio: Seguimiento, pago, cancelación y devolución de órdenes. Fuente de verdad:
// docs/hu/02-hu-tienda-carrito-ordenes.md (HU-SHOP-21..30) y docs/qa/02-matriz-pruebas-e2e.md
// (E2E-ORD-xx, E2E-PAY-xx, E2E-RET-xx).
//
// Rutas: /#/orden/:idOrden, /#/orden/:idOrden/cancelar, /#/orden/:idOrden/devolucion.
// GET /orders/:id (real-api.service.ts) normaliza la orden con `normalizeAdminOrder()`, que a su
// vez llama a `normalizeOrderStatus()` — esa función SÍ convierte "canceled" (backend, una L) a
// "cancelled" (frontend, doble L) ANTES de que la orden llegue a cualquier componente. Por eso el
// bug "canceled vs cancelled" que describe la Observación #2 de docs/hu/02 está en realidad
// mitigado a nivel de servicio (ver test de regresión más abajo, que documenta esto).
//
// OJO orden de mocks: page.route es LIFO — blockUnmockedApi() se registra PRIMERO y los mocks
// específicos DESPUÉS para que tengan prioridad (ver tienda.spec.ts para el detalle).

function baseOrder(overrides: Record<string, unknown> = {}) {
  return {
    id: 'ORD-9001',
    createdAt: '2026-07-15T10:00:00Z',
    customer: 'Cliente E2E',
    grossSubtotal: 590,
    discountRate: 0,
    discountAmount: 0,
    netTotal: 590,
    total: 590,
    status: 'pending',
    items: [{ productId: 1, name: 'Colágeno Hidrolizado', price: 590, quantity: 1 }],
    deliveryType: 'delivery',
    ...overrides
  };
}

async function mockOrder(page: Page, orderId: string, overrides: Record<string, unknown> = {}, opts: { status?: number } = {}) {
  await mockApi(page, `/orders/${orderId}`, opts.status && opts.status >= 400
    ? { message: 'No se pudo cargar la orden.' }
    : { order: baseOrder({ id: orderId, ...overrides }) }, { method: 'GET', status: opts.status ?? 200 });
}

test.describe('Seguimiento de orden (/#/orden/:id) — HU-SHOP-21, HU-SHOP-24', () => {
  test('HU-SHOP-24 / E2E-ORD-01: muestra el estado, el resumen y el timeline de una orden pagada', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9001', { status: 'paid', discountAmount: 59, discountRate: 0.1, netTotal: 531, total: 531 });

    await page.goto('/#/orden/ORD-9001');

    await expect(page.getByText('Pago registrado').first()).toBeVisible();
    await expect(page.getByText('ORD-9001').first()).toBeVisible();
  });

  test('HU-SHOP-24 / E2E-ORD-01: estados enviado y entregado muestran su etiqueta correspondiente', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9002', { status: 'shipped', shippingType: 'carrier', trackingNumber: 'GUIA-123' });

    await page.goto('/#/orden/ORD-9002');
    await expect(page.getByText('Pedido enviado').first()).toBeVisible();
    await expect(page.getByText('GUIA-123')).toBeVisible();
  });

  test('HU-SHOP-24 / borde: orden inexistente muestra "No se encontro la orden."', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/orders/ORD-NOPE', { message: 'not found' }, { method: 'GET', status: 404 });

    await page.goto('/#/orden/ORD-NOPE');

    await expect(page.getByText('No se encontro la orden.')).toBeVisible();
  });

  test('HU-SHOP-24 / borde: redirectStatus=failure desde MercadoPago muestra el mensaje de rechazo', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9003', { status: 'pending' });

    await page.goto('/#/orden/ORD-9003?status=failure');

    await expect(page.getByText('Operacion rechazada').first()).toBeVisible();
    await expect(page.getByText('Tu operacion fue rechazada.')).toBeVisible();
  });

  test('HU-SHOP-24 / E2E-PAY-02: hace polling cada 60s tras un regreso exitoso de MercadoPago hasta que la orden se marca pagada', async ({ page }) => {
    await page.clock.install();
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);

    let callCount = 0;
    await page.route('**/orders/ORD-9004', async (route) => {
      callCount += 1;
      const status = callCount === 1 ? 'pending' : 'paid';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ order: baseOrder({ id: 'ORD-9004', status }) })
      });
    });

    await page.goto('/#/orden/ORD-9004?status=success');
    await expect(page.getByText('Operacion en validacion').first()).toBeVisible();
    expect(callCount).toBe(1);

    // startSuccessPolling() usa setInterval(..., 60000). Avanzamos el reloj simulado 60s para
    // disparar el siguiente tick sin esperar un minuto real.
    await page.clock.fastForward('01:00');
    await expect(page.getByText('Pago registrado').first()).toBeVisible();
    expect(callCount).toBe(2);
  });
});

test.describe('Pago con MercadoPago desde el seguimiento — HU-SHOP-21', () => {
  test('E2E-PAY-01 / E2E-ORD-02: el botón de pago redirige al initPoint de MercadoPago', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9005', { status: 'pending' });
    // Se mockea con una URL dentro de la propia app (nunca se navega al checkout real de MP,
    // como exige el modo mockeado): confirma que payWithMercadoPago() efectivamente asigna
    // window.location.href al initPoint recibido.
    await mockApi(page, '/orders/ORD-9005/checkout', {
      orderId: 'ORD-9005',
      checkout: { provider: 'mercadopago', initPoint: '/#/orden/ORD-9005?status=success', sandboxInitPoint: '/#/orden/ORD-9005?status=success' }
    }, { method: 'POST' });

    await page.goto('/#/orden/ORD-9005');
    await page.getByRole('button', { name: 'Pagar con MercadoPago' }).click();

    await expect(page).toHaveURL(/#\/orden\/ORD-9005\?status=success/);
  });

  test('E2E-PAY-01 / error: sin initPoint en la respuesta muestra un mensaje controlado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9006', { status: 'pending' });
    await mockApi(page, '/orders/ORD-9006/checkout', { orderId: 'ORD-9006' }, { method: 'POST' });

    await page.goto('/#/orden/ORD-9006');
    await page.getByRole('button', { name: 'Pagar con MercadoPago' }).click();

    await expect(page.getByText('No se pudo iniciar el pago en MercadoPago.')).toBeVisible();
  });

  test('E2E-PAY-01 / error: fallo del backend al iniciar el checkout muestra el mismo mensaje controlado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9007', { status: 'pending' });
    await mockApi(page, '/orders/ORD-9007/checkout', { message: 'Internal error' }, { method: 'POST', status: 500 });

    await page.goto('/#/orden/ORD-9007');
    await page.getByRole('button', { name: 'Pagar con MercadoPago' }).click();

    await expect(page.getByText('No se pudo iniciar el pago en MercadoPago.')).toBeVisible();
  });

  test(
    'HU-SHOP-23 / regresión: el botón de MercadoPago se oculta para pickup con pago en sucursal',
    async ({ page }) => {
      // order-status.component.ts expone `canPayWithMercadoPago`, que además de
      // `statusValue === 'pending'` valida que la orden no sea pickup con pago "en sucursal"
      // (pickupPaymentMethod: 'at_store'). El template usa ese getter para mostrar la tarjeta de
      // pago en vez de condicionar solo por status.
      await acceptPrivacyNotice(page);
      await blockUnmockedApi(page);
      await mockOrder(page, 'ORD-9008', {
        status: 'pending',
        deliveryType: 'pickup',
        pickupPaymentMethod: 'at_store',
        pickupStockId: 'stock-centro'
      });

      await page.goto('/#/orden/ORD-9008');

      await expect(page.getByRole('button', { name: 'Pagar con MercadoPago' })).toHaveCount(0);
    }
  );

  test(
    'HU-SHOP-30 / regresión: una orden reembolsada (status "refunded") se muestra como "Reembolsado"',
    async ({ page }) => {
      // order-status.component.ts:18 incluye 'refunded' en `allowedStatuses`, en línea con
      // real-api.service.ts::normalizeOrderStatus(). Con eso, `statusLabel` resuelve "Reembolsado"
      // en vez de caer al default 'pending', y `canPayWithMercadoPago` oculta el botón de pago.
      await acceptPrivacyNotice(page);
      await blockUnmockedApi(page);
      await mockOrder(page, 'ORD-9009', { status: 'refunded' });

      await page.goto('/#/orden/ORD-9009');

      await expect(page.getByText('Pago pendiente')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Pagar con MercadoPago' })).toHaveCount(0);
    }
  );
});

test.describe('Regresión: normalización de estado cancelado (Observación #2 de docs/hu/02)', () => {
  test('el backend respondiendo "canceled" (una L) se normaliza correctamente a "Cancelado" en la UI', async ({ page }) => {
    // El doc HU afirma que el frontend compara contra "cancelled" mientras el backend escribe
    // "canceled", dejando el pago pendiente visible en una orden ya cancelada. Al leer
    // real-api.service.ts se confirmó que normalizeOrderStatus() SÍ traduce "canceled"->
    // "cancelled" antes de exponer la orden a los componentes. Este test simula la respuesta CRUDA
    // del backend (con una sola L, como realmente la devuelve _cancel_order/_refund_order) para
    // verificar el comportamiento real observado, no el documentado.
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/orders/ORD-9010', { order: baseOrder({ id: 'ORD-9010', status: 'canceled' }) }, { method: 'GET' });

    await page.goto('/#/orden/ORD-9010');

    await expect(page.getByText('Cancelado', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Orden cancelada — reembolso en proceso')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Pagar con MercadoPago' })).toHaveCount(0);
  });
});

test.describe('Cancelar orden (/#/orden/:id/cancelar) — HU-SHOP-26', () => {
  test('E2E-ORD-03: cancelar una orden pending confirma sin mencionar reembolso', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9101', { status: 'pending' });
    await mockApi(page, '/orders/ORD-9101/cancel', { ok: true, orderId: 'ORD-9101', status: 'cancelled', pendingRefund: false }, { method: 'POST' });

    await page.goto('/#/orden/ORD-9101/cancelar');
    await page.getByRole('button', { name: 'Cancelar orden' }).click();

    await expect(page.getByRole('heading', { name: 'Orden cancelada' })).toBeVisible();
    await expect(page.getByText('El pago no había sido confirmado')).toBeVisible();
  });

  test('E2E-ORD-04: cancelar una orden paid confirma e informa que el reembolso se procesará', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9102', { status: 'paid' });
    await mockApi(page, '/orders/ORD-9102/cancel', { ok: true, orderId: 'ORD-9102', status: 'cancelled', pendingRefund: true }, { method: 'POST' });

    await page.goto('/#/orden/ORD-9102/cancelar');
    await page.getByRole('button', { name: 'Cancelar orden' }).click();

    await expect(page.getByRole('heading', { name: 'Orden cancelada' })).toBeVisible();
    await expect(page.getByText('El reembolso está siendo procesado')).toBeVisible();
  });

  test('E2E-ORD-05: una orden shipped bloquea la cancelación y ofrece solicitar devolución', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9103', { status: 'shipped' });

    await page.goto('/#/orden/ORD-9103/cancelar');

    await expect(page.getByText('Pedido en proceso logístico, solicitar devolución')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancelar orden' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Solicitar devolución' })).toBeVisible();
  });

  test('E2E-ORD-05 / borde: una orden ya cancelada muestra el motivo de bloqueo correspondiente', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9104', { status: 'cancelled' });

    await page.goto('/#/orden/ORD-9104/cancelar');

    await expect(page.getByText('Esta orden ya fue cancelada.')).toBeVisible();
  });

  test('E2E-ORD-05 / error: el backend rechaza la cancelación (409, ya en tránsito)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9105', { status: 'paid' });
    await mockApi(page, '/orders/ORD-9105/cancel', { message: 'La orden ya no puede cancelarse.' }, { method: 'POST', status: 409 });

    await page.goto('/#/orden/ORD-9105/cancelar');
    await page.getByRole('button', { name: 'Cancelar orden' }).click();

    await expect(page.getByText('La orden ya no puede cancelarse.')).toBeVisible();
  });

  test(
    'regresión: si la orden no carga, la pantalla de cancelación muestra el mensaje de error',
    async ({ page }) => {
      // order-cancelacion.component.html agrega un bloque `*ngIf="!order && error"` que sí
      // renderiza `this.error` (fijado en el callback de error de ngOnInit) con una acción para
      // volver, en vez de depender de los bloques "Can cancel"/"Blocked" que exigen `order` truthy.
      await acceptPrivacyNotice(page);
      await blockUnmockedApi(page);
      await mockApi(page, '/orders/ORD-NOPE-2', { message: 'not found' }, { method: 'GET', status: 404 });

      await page.goto('/#/orden/ORD-NOPE-2/cancelar');

      await expect(page.getByText('No se pudo cargar la orden.')).toBeVisible();
    }
  );
});

test.describe('Solicitar devolución (/#/orden/:id/devolucion) — HU-SHOP-27', () => {
  test('borde: solo se puede solicitar devolución de pedidos entregados', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9201', { status: 'shipped' });

    await page.goto('/#/orden/ORD-9201/devolucion');

    await expect(page.getByText('Solo puedes solicitar devoluciones de pedidos entregados.')).toBeVisible();
  });

  test('E2E-RET-01 / happy: flujo completo de devolución (motivo, evidencia y confirmación)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9202', { status: 'delivered' });
    await mockApi(page, '/orders/ORD-9202/return', {
      ok: true, requestId: 'RET-001', status: 'EN_DEVOLUCION', shippingResponsibility: 'empresa',
      message: 'Tu solicitud fue registrada. Un asesor se pondrá en contacto contigo.'
    }, { method: 'POST' });

    await page.goto('/#/orden/ORD-9202/devolucion');

    // Paso 1: motivo.
    await page.getByText('Producto dañado o defectuoso').click();
    await page.getByRole('button', { name: 'Siguiente' }).click();

    // Paso 2: evidencia (las 3 categorías son obligatorias para avanzar).
    const nextBtn = page.getByRole('button', { name: 'Siguiente' });
    await expect(nextBtn).toBeDisabled();
    const fileInputs = page.locator('input[type="file"]');
    await fileInputs.nth(0).setInputFiles({ name: 'producto.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('fake-image-data') });
    await expect(nextBtn).toBeDisabled();
    await fileInputs.nth(1).setInputFiles({ name: 'empaque.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('fake-image-data') });
    await expect(nextBtn).toBeDisabled();
    await fileInputs.nth(2).setInputFiles({ name: 'guia.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('fake-image-data') });
    await expect(nextBtn).toBeEnabled();
    await nextBtn.click();

    // Paso 3: confirmar y enviar.
    await expect(page.getByText('Producto dañado o defectuoso')).toBeVisible();
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();

    await expect(page.getByRole('heading', { name: 'Solicitud registrada' })).toBeVisible();
    await expect(page.getByText('ID de solicitud:')).toBeVisible();
    await expect(page.getByText('RET-001')).toBeVisible();
  });

  test('E2E-RET-02 / borde: el paso de evidencia no avanza si falta alguna de las 3 categorías', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9203', { status: 'delivered' });

    await page.goto('/#/orden/ORD-9203/devolucion');
    await page.getByText('Error en el envío').click();
    await page.getByRole('button', { name: 'Siguiente' }).click();

    const fileInputs = page.locator('input[type="file"]');
    await fileInputs.nth(0).setInputFiles({ name: 'producto.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') });
    await fileInputs.nth(1).setInputFiles({ name: 'empaque.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') });
    // Falta la 3a categoría (guía de envío): "Siguiente" debe seguir deshabilitado.
    await expect(page.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
  });

  test('E2E-RET-03 / error: el backend no implementa /orders/:id/return (404) — la UI no revienta, pero expone el mensaje crudo del API Gateway', async ({ page }) => {
    // Observación #1 del doc HU: la ruta POST /orders/{id}/return no existe en el backend real
    // (handler.py no la implementa). AWS API Gateway responde a rutas no mapeadas con
    // {"message":"Not Found"} y status 404. order-devolucion.component.ts prioriza
    // `err?.error?.message` sobre su fallback genérico ("No se pudo enviar la solicitud."), así
    // que ese "Not Found" crudo del API Gateway es justo lo que el usuario final vería hoy si el
    // backend no cambia — no es amigable, pero al menos la UI no se rompe.
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockOrder(page, 'ORD-9204', { status: 'delivered' });
    await mockApi(page, '/orders/ORD-9204/return', { message: 'Not Found' }, { method: 'POST', status: 404 });

    await page.goto('/#/orden/ORD-9204/devolucion');
    await page.getByText('Desistimiento (arrepentimiento)').click();
    await page.getByRole('button', { name: 'Siguiente' }).click();

    const fileInputs = page.locator('input[type="file"]');
    await fileInputs.nth(0).setInputFiles({ name: 'a.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') });
    await fileInputs.nth(1).setInputFiles({ name: 'b.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') });
    await fileInputs.nth(2).setInputFiles({ name: 'c.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') });
    await page.getByRole('button', { name: 'Siguiente' }).click();
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();

    await expect(page.getByText('Not Found')).toBeVisible();
  });

  test(
    'regresión: si la orden no carga, la pantalla de devolución muestra el mensaje de error',
    async ({ page }) => {
      // order-devolucion.component.html agrega un bloque `*ngIf="!order && error"`, mismo patrón
      // que en order-cancelacion, que renderiza `this.error` con una acción para volver en vez de
      // depender de los bloques "Success result"/"Error if not delivered"/"Main form" (que exigen
      // `order` u `result` truthy).
      await acceptPrivacyNotice(page);
      await blockUnmockedApi(page);
      await mockApi(page, '/orders/ORD-NOPE-3', { message: 'not found' }, { method: 'GET', status: 404 });

      await page.goto('/#/orden/ORD-NOPE-3/devolucion');

      await expect(page.getByText('No se pudo cargar la orden.')).toBeVisible();
    }
  );
});

// NO AUTOMATIZADAS:
// - E2E-RET-04 a E2E-RET-12 (plazos de 48h/7 días, inspección de evidencia por admin, ajuste de
//   PC, reembolso tras validación, rechazo de devolución): dependen de estados
//   (en_devolucion/devuelto_validado/devolucion_rechazada) y endpoints
//   (POST /orders/:id/return/inspect) que son en su mayoría de panel admin o de backend puro;
//   fuera del alcance de "Tienda, Carrito, Checkout y Órdenes" desde la tienda pública/cliente.
// - HU-SHOP-22 (webhook de Mercado Pago mapea approved/pending/refunded/rejected a estados de
//   orden): es un endpoint server-to-server sin superficie de UI, no ejercitable desde el
//   navegador.
// - HU-SHOP-28 / HU-SHOP-29 / HU-SHOP-30 (generación, confirmación y reversión de comisiones al
//   pagar/entregar/cancelar una orden): lógica puramente de backend (ledger de comisiones), sin
//   ningún elemento de UI en el dominio tienda/carrito/checkout/órdenes que la exponga.
// - Botón "Copiar" del número de guía (usa navigator.clipboard.writeText): requiere permisos de
//   portapapeles del navegador y no aporta cobertura de negocio adicional a lo ya validado (que el
//   número de guía se muestra correctamente); se omite para no añadir fragilidad de permisos.
