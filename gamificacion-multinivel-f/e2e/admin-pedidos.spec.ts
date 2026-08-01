import { test, expect, seedSession, USERS, blockUnmockedApi, mockApi } from './support/fixtures';
import { mockAdminBaseline, selectByVisibleText, selectByExactLabel } from './support/admin-mocks';

// Pedidos y transiciones de estado — prioridad #2 tras RBAC.
// HU-ADM-01 (Crítica, transición con RBAC), HU-ADM-02 (Alta, envío + descuento stock),
// HU-ADM-03 (Alta, cancelación+reembolso), HU-ADM-04 (Alta, inspección devolución),
// HU-ADM-05 (Alta, alta manual de orden), HU-ADM-25 (Media, aviso interno pedido pendiente).
// Fuente: docs/hu/04-hu-admin.md.

test.describe('Panel Admin — Pedidos', () => {
  test('HU-ADM-01 / E2E-ORD-06: pending -> paid vía "Cambiar estado" (con order_mark_paid) pide forma de pago', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [
        { orderId: 'ord-100', customer: 'Cliente Pendiente', total: 750, status: 'pending', createdAt: '2026-07-01T10:00:00.000Z' }
      ]
    });
    await mockApi(page, '/orders/ord-100', { order: { orderId: 'ord-100', customer: 'Cliente Pendiente', total: 750, status: 'paid', paymentMethod: 'transfer' } }, { method: 'PATCH' });

    await page.goto('/#/admin');

    // Feature: al marcar como pagado, primero se solicita la forma de pago en un modal.
    // Nota: <ui-modal> es el host del componente (display:inline sin tamaño propio, ya que su
    // contenido usa position:fixed) — Playwright lo reporta "hidden" aunque el contenido SÍ sea
    // visible. Se valida visibilidad sobre el subtítulo del modal, no sobre el wrapper <ui-modal>.
    await page.getByRole('button', { name: 'Cambiar estado' }).last().click();
    await expect(page.getByText('Selecciona la forma de pago recibida antes de confirmar.')).toBeVisible();
    const modal = page.locator('ui-modal', { hasText: 'Marcar como pagado' });

    // ui-form-field usa [ngValue], que serializa el <option> como "<índice>: <valor>" en vez del
    // valor limpio (ver e2e/carrito-checkout.spec.ts) — se selecciona por label, no por value.
    await selectByExactLabel(modal, 'Forma de pago').selectOption({ label: 'Transferencia' });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/ord-100') && req.method() === 'PATCH'),
      modal.getByRole('button', { name: 'Confirmar pago' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ status: 'paid', paymentMethod: 'transfer' });
    await expect(modal).toHaveCount(0);

    // El pedido ya no aparece en la pestaña "Pendiente"; ahora vive en "Pagado", con la forma de pago visible.
    await page.getByRole('button', { name: 'Pagado', exact: true }).click();
    await expect(page.getByText('Cliente Pendiente').last()).toBeVisible();
    await expect(page.getByText('Pagada').last()).toBeVisible();
    await page.getByRole('button', { name: 'Ver' }).last().click();
    await expect(page.getByText('Transferencia').last()).toBeVisible();
  });

  test('HU-ADM-01 (borde): cancelar el modal de forma de pago no cambia el estado del pedido', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [
        { orderId: 'ord-101', customer: 'Cliente Pendiente 2', total: 500, status: 'pending' }
      ]
    });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Cambiar estado' }).last().click();
    await expect(page.getByText('Selecciona la forma de pago recibida antes de confirmar.')).toBeVisible();
    const modal = page.locator('ui-modal', { hasText: 'Marcar como pagado' });

    await modal.getByRole('button', { name: 'Cancelar' }).click();
    await expect(page.getByText('Selecciona la forma de pago recibida antes de confirmar.')).toHaveCount(0);

    // Sigue en "Pendiente": no se disparó ningún PATCH.
    await expect(page.getByText('Cliente Pendiente 2').last()).toBeVisible();
  });

  test('HU-ADM-02: paid -> shipped abre modal de envío y descuenta stock con dispatchLines', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [
        {
          orderId: 'ord-200',
          customer: 'Cliente Pagado',
          total: 900,
          status: 'paid',
          items: [{ productId: 1, name: 'Colageno', price: 900, quantity: 1 }]
        }
      ],
      stocks: [{ stockId: 'stk-1', name: 'Bodega Central', location: 'CDMX', linkedUserIds: [], inventory: { 1: 20 } }]
    });
    await mockApi(page, '/orders/ord-200', { order: { orderId: 'ord-200', customer: 'Cliente Pagado', total: 900, status: 'shipped' } }, { method: 'PATCH' });

    await page.goto('/#/admin');
    // El selector "Stock origen" del modal de envío depende de AdminControlService.stocks, que
    // solo se carga al visitar la vista Stocks/POS (loadViewData, admin.component.ts:741-749) —
    // no en la vista Pedidos. Se visita Stocks una vez para poblarlo antes de abrir el modal.
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();
    await page.locator('aside').first().getByRole('button', { name: 'Pedidos' }).click();

    await page.getByRole('button', { name: 'Pagado', exact: true }).click();
    await page.getByRole('button', { name: 'Cambiar estado' }).last().click();

    await expect(page.getByText('Enviar pedido')).toBeVisible();
    await selectByVisibleText(page.getByLabel('Stock origen'), 'Bodega Central');
    await page.getByRole('textbox', { name: 'Numero de guia' }).fill('GUIA-12345');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/ord-200') && req.method() === 'PATCH'),
      page.getByRole('button', { name: 'Marcar como enviado' }).click()
    ]);
    const body = request.postDataJSON();
    expect(body.status).toBe('shipped');
    expect(body.trackingNumber).toBe('GUIA-12345');
    expect(body.dispatchLines).toEqual([{ productId: 1, quantity: 1 }]);
    await expect(page.getByText('Enviar pedido')).toHaveCount(0);
  });

  test('HU-ADM-02 (borde): sin líneas de despacho, bloquea con mensaje de stock', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [{ orderId: 'ord-201', customer: 'Cliente Sin Items', total: 300, status: 'paid' }],
      stocks: [{ stockId: 'stk-1', name: 'Bodega Central', location: 'CDMX', linkedUserIds: [], inventory: {} }],
      products: [] // fuerza shippingFallbackProductId=null -> resolveDispatchLines() vacío
    });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();
    await page.locator('aside').first().getByRole('button', { name: 'Pedidos' }).click();

    await page.getByRole('button', { name: 'Pagado', exact: true }).click();
    await page.getByRole('button', { name: 'Cambiar estado' }).last().click();
    await selectByVisibleText(page.getByLabel('Stock origen'), 'Bodega Central');
    await page.getByRole('textbox', { name: 'Numero de guia' }).fill('GUIA-999');
    await page.getByRole('button', { name: 'Marcar como enviado' }).click();

    await expect(page.getByText('Agrega producto y cantidad para descontar stock.').first()).toBeVisible();
  });

  test('HU-ADM-03: reembolso de pedido cancelado con comprobante', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [{ orderId: 'ord-300', customer: 'Cliente Cancelado', total: 400, status: 'cancelled' }]
    });
    await mockApi(page, '/orders/ord-300/refund', { orderId: 'ord-300', status: 'refunded', refundReceiptUrl: 'https://x/comprobante.jpg' }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Cancelado', exact: true }).click();
    await page.getByRole('button', { name: 'Reembolsar' }).click();
    await expect(page.getByText('Registrar reembolso')).toBeVisible();

    await page.locator('input[type=file]').setInputFiles({
      name: 'comprobante.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-bytes')
    });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/ord-300/refund')),
      page.getByRole('button', { name: 'Confirmar reembolso' }).click()
    ]);
    expect(request.postDataJSON().receiptContentType).toBe('image/jpeg');
    await expect(page.getByText('Registrar reembolso')).toHaveCount(0);
  });

  test('HU-ADM-03 (borde): reembolso sin comprobante bloquea con mensaje explícito', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [{ orderId: 'ord-301', customer: 'Cliente Cancelado 2', total: 400, status: 'cancelled' }]
    });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Cancelado', exact: true }).click();
    await page.getByRole('button', { name: 'Reembolsar' }).click();
    await page.getByRole('button', { name: 'Confirmar reembolso' }).click();

    await expect(page.getByText('Adjunta el comprobante de depósito.')).toBeVisible();
  });

  test('HU-ADM-04: recibir devolución (en_devolucion -> devuelto_validado) con imagen', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [{ orderId: 'ord-400', customer: 'Cliente Devuelve', total: 600, status: 'en_devolucion' }]
    });
    await mockApi(page, '/orders/ord-400/return/inspect', { ok: true, requestId: 'ret-1', returnStatus: 'DEVUELTO_VALIDADO', orderStatus: 'devuelto_validado', approved: true }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Por devolver', exact: true }).click();
    await page.getByRole('button', { name: 'Recibir paquete' }).click();
    await expect(page.getByText('Recibir paquete de devolución')).toBeVisible();

    await page.locator('input[type=file]').setInputFiles({
      name: 'paquete.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-bytes')
    });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/ord-400/return/inspect')),
      page.getByRole('button', { name: 'Confirmar recepción' }).click()
    ]);
    expect(request.postDataJSON().inspection).toMatchObject({
      empaque_original: true,
      sellos_intactos: true,
      sin_uso: true,
      producto_abierto: false,
      coincide_con_pedido: true,
      trazabilidad_valida: true
    });
    await expect(page.getByText('Recibir paquete de devolución')).toHaveCount(0);
  });

  test('HU-ADM-04: rechazar devolución (devuelto_validado -> devolucion_rechazada) con motivo', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [{ orderId: 'ord-401', customer: 'Cliente Devuelve 2', total: 600, status: 'devuelto_validado' }]
    });
    await mockApi(page, '/orders/ord-401/return/inspect', { ok: true, requestId: 'ret-2', returnStatus: 'DEVOLUCION_RECHAZADA', orderStatus: 'devolucion_rechazada', approved: false }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Devuelto', exact: true }).click();
    await page.getByRole('button', { name: 'Rechazar' }).click();
    await expect(page.getByText('Rechazar devolución')).toBeVisible();

    // Borde: confirmar sin motivo bloquea antes de llamar al backend.
    await page.getByRole('button', { name: 'Confirmar rechazo' }).click();
    await expect(page.getByText('Ingresa el motivo del rechazo.')).toBeVisible();

    await page.getByPlaceholder('Ej. El producto presenta daños causados por el cliente...').fill('Producto usado, no corresponde a devolución.');
    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/ord-401/return/inspect')),
      page.getByRole('button', { name: 'Confirmar rechazo' }).click()
    ]);
    expect(request.postDataJSON().rejectionReason).toBe('Producto usado, no corresponde a devolución.');
  });

  test('HU-ADM-05: alta de orden manual (order_create)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      customers: [{ customerId: 501, name: 'Cliente Manual', email: 'manual@findingu.mx' }],
      products: [{ productId: 9, name: 'Colageno Manual', price: 350, active: true, inOnlineStore: true, inPOS: true, commissionable: true }]
    });
    await mockApi(page, '/orders/create', { order: { orderId: 'ord-new-1', customer: 'Cliente Manual', total: 350, status: 'pending' } }, { method: 'POST' });

    await page.goto('/#/admin');
    // El modal "Nuevo pedido" depende de AdminControlService.customers/products, que solo se
    // cargan al visitar esas vistas (loadViewData, admin.component.ts:707-719) — no en Pedidos.
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();
    await page.locator('aside').first().getByRole('button', { name: 'Productos' }).click();
    await page.locator('aside').first().getByRole('button', { name: 'Pedidos' }).click();

    await page.getByRole('button', { name: 'Nuevo pedido' }).click();
    // Nota: <ui-modal> es el host del componente (display:inline sin tamaño propio, ya que su
    // contenido usa position:fixed) — Playwright lo reporta "hidden" aunque el contenido SÍ sea
    // visible. Se valida visibilidad sobre el subtítulo del modal, no sobre el wrapper <ui-modal>.
    await expect(page.getByText('Registrá un pedido manual.')).toBeVisible();
    const modal = page.locator('ui-modal', { hasText: 'Nuevo pedido' });

    await modal.getByLabel('Cliente').selectOption({ label: 'Cliente Manual · manual@findingu.mx' });
    await modal.getByRole('button', { name: /Colageno Manual/ }).click();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/orders/create')),
      modal.getByRole('button', { name: 'Guardar pedido' }).click()
    ]);
    const body = request.postDataJSON();
    expect(body.customerId).toBe(501);
    expect(body.items).toEqual([{ productId: 9, name: 'Colageno Manual', price: 350, quantity: 1 }]);
    await expect(page.getByText('Registrá un pedido manual.')).toHaveCount(0);
  });

  test('HU-ADM-25 / E2E-ADM-12: aviso interno de pedido pendiente en sucursal y resolución', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      warnings: [{ type: 'assets', text: 'Hay productos sin imágenes cargadas.', severity: 'medium' }]
    });

    await page.goto('/#/admin');
    await page.getByRole('button', { name: 'Acciones' }).click();
    await expect(page.getByText('Acciones urgentes')).toBeVisible();
    await expect(page.getByText('Hay productos sin imágenes cargadas.')).toBeVisible();

    await page.getByRole('button', { name: 'Ir a resolver' }).click();
    // warning.type 'assets' -> target view 'products'.
    await expect(page.getByPlaceholder('Buscar por nombre, SKU, estado...')).toBeVisible();
  });

  test('estados negativos (Cancelado, Devuelto, Dev. rechazada) usan la variante badge-danger', async ({ page }) => {
    // Ver docs/ux/analisis-ui-ux-2026-08.md, hallazgo Alta "Badges de estado": antes todos los
    // estados de pedido (positivos, neutros y negativos) compartían la misma paleta
    // dorada/neutra; --color-danger estaba declarado pero sin ningún badge que lo usara.
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [
        { orderId: 'ord-500', customer: 'Cliente Cancelado', total: 400, status: 'cancelled' },
        { orderId: 'ord-501', customer: 'Cliente Devuelto', total: 500, status: 'devuelto_validado' },
        { orderId: 'ord-502', customer: 'Cliente Rechazado', total: 600, status: 'devolucion_rechazada' },
        { orderId: 'ord-503', customer: 'Cliente Pendiente', total: 300, status: 'pending' }
      ]
    });

    await page.goto('/#/admin');

    // La tabla filtra por el tab de estado activo (por defecto "Pendiente"): hay que cambiar de
    // tab para ver cada orden. Badge del estado negativo: clase badge-danger + etiqueta traducida
    // (antes se mostraba el valor crudo en inglés, p. ej. "cancelled", porque ui-status-badge no
    // reconocía estos estados de devolución/cancelación).
    // ui-data-table renderiza a la vez la fila mobileRow (oculta por CSS en viewport desktop) y
    // la desktopRow: se usa .last() para apuntar siempre a la copia visible, igual que el resto
    // de pruebas de este archivo (ver p. ej. "Cliente Pendiente" más abajo en el describe).
    await page.getByRole('button', { name: 'Cancelado', exact: true }).click();
    await expect(page.getByText('Cliente Cancelado').last()).toBeVisible();
    const cancelledBadge = page.locator('ui-status-badge .badge').last();
    await expect(cancelledBadge).toHaveClass(/badge-danger/);
    await expect(cancelledBadge).toHaveText(/Cancelado/);

    await page.getByRole('button', { name: 'Devuelto', exact: true }).click();
    await expect(page.getByText('Cliente Devuelto').last()).toBeVisible();
    await expect(page.locator('ui-status-badge .badge').last()).toHaveClass(/badge-danger/);

    await page.getByRole('button', { name: 'Dev. rechazada', exact: true }).click();
    await expect(page.getByText('Cliente Rechazado').last()).toBeVisible();
    await expect(page.locator('ui-status-badge .badge').last()).toHaveClass(/badge-danger/);

    // Un estado neutro (pending) NO debe llevar la variante danger.
    await page.getByRole('button', { name: 'Pendiente', exact: true }).click();
    await expect(page.getByText('Cliente Pendiente').last()).toBeVisible();
    await expect(page.locator('ui-status-badge .badge').last()).not.toHaveClass(/badge-danger/);
  });
});
