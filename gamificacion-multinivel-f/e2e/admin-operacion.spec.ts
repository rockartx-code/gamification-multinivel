import { test, expect, seedSession, USERS, blockUnmockedApi, mockApi, E2EAuthUser } from './support/fixtures';
import { mockAdminBaseline, defaultBusinessConfig } from './support/admin-mocks';

// POS, comisiones, configuración, notificaciones, cupones, campañas y reportes — prioridad #6/#7.
// HU-ADM-16/17 (Alta/Media, POS venta+corte), HU-ADM-18 (Alta, comisiones comprobante),
// HU-ADM-19 (Media, cupones), HU-ADM-20 (Media, campañas), HU-ADM-21 (Media, notificaciones),
// HU-ADM-22 (Alta, config de negocio), HU-ADM-23 (Alta, reportes XLSX).
// Fuente: docs/hu/04-hu-admin.md.

// IMPORTANTE (hallazgo): AdminControlComponent.currentOperatorId = Number(currentUser.userId)
// (admin.component.ts:1306-1309). USERS.admin tiene userId:'admin-001' -> Number('admin-001')
// es NaN -> currentOperatorId=null -> linkedPosStocks=[] SIEMPRE, aunque sea superusuario.
// Con el usuario admin-001 por defecto, la vista POS queda permanentemente sin stock vinculado
// (no es un bug de esta suite: refleja que POS requiere un operador con userId numérico
// vinculado a un stock). Para las pruebas de POS usamos un superusuario con userId numérico.
function posOperator(): E2EAuthUser {
  return {
    userId: '1',
    name: 'Operador POS',
    role: 'admin',
    token: 'e2e-fake-jwt-pos',
    canAccessAdmin: true,
    isSuperUser: true
  };
}

test.describe('Panel Admin — POS', () => {
  test('HU-ADM-16 / E2E-ADM-09: registrar venta de mostrador (pos_register_sale)', async ({ page }) => {
    await seedSession(page, posOperator());
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 41, name: 'ProductoPOS', price: 200, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [{ stockId: 'stk-pos', name: 'Sucursal POS', location: 'CDMX', linkedUserIds: [1], inventory: { 41: 10 } }]
    });
    await mockApi(
      page,
      '/inventory/pos/sales',
      { sale: { saleId: 'sale-1', orderId: 'ord-pos-1', stockId: 'stk-pos', customerName: 'Publico en General', paymentStatus: 'paid_branch', deliveryStatus: 'delivered_branch', total: 200, lines: [] } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Punto de Venta' }).click();

    await page.getByRole('button', { name: 'Publico en General' }).first().click();
    await page.getByRole('button', { name: /ProductoPOS/ }).click();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/pos/sales') && req.method() === 'POST'),
      page.getByRole('button', { name: /^Cobrar/ }).click()
    ]);
    const body = request.postDataJSON();
    expect(body.stockId).toBe('stk-pos');
    expect(body.items).toEqual([{ productId: 41, name: 'ProductoPOS', price: 200, quantity: 1 }]);
    await expect(page.getByText('Venta registrada en caja.').first()).toBeVisible();
  });

  test('HU-ADM-16 / E2E-ADM-11 (borde): descuento de cajero + pago parcial con código de autorización', async ({ page }) => {
    await seedSession(page, posOperator());
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 42, name: 'ProductoParcial', price: 1000, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [{ stockId: 'stk-pos', name: 'Sucursal POS', location: 'CDMX', linkedUserIds: [1], inventory: { 42: 10 } }]
    });
    await mockApi(page, '/inventory/pos/validate-auth', { ok: true }, { method: 'POST' });
    await mockApi(
      page,
      '/inventory/pos/sales',
      { sale: { saleId: 'sale-2', orderId: 'ord-pos-2', stockId: 'stk-pos', customerName: 'Publico en General', paymentStatus: 'partial_branch', deliveryStatus: 'delivered_branch', total: 900, lines: [] } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Punto de Venta' }).click();
    await page.getByRole('button', { name: 'Publico en General' }).first().click();
    await page.getByRole('button', { name: /ProductoParcial/ }).click();

    // Descuento de cajero: 10% (requiere autorización).
    await page.getByRole('button', { name: 'Aplicar descuento' }).click();
    await page.getByLabel('Codigo de autorizacion').fill('1234');
    await page.getByRole('button', { name: 'Confirmar' }).click();
    await page.getByLabel(/Porcentaje de descuento|Monto a descontar/).fill('10');
    await page.getByRole('button', { name: 'Aplicar descuento' }).last().click();

    // Pago parcial: también requiere autorización.
    await page.getByRole('button', { name: 'Pago parcial' }).click();
    await page.getByLabel('Codigo de autorizacion').fill('1234');
    await page.getByRole('button', { name: 'Confirmar' }).click();
    await page.getByLabel('Monto pagado ahora').fill('500');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/pos/sales') && req.method() === 'POST'),
      page.getByRole('button', { name: /^Cobrar/ }).click()
    ]);
    const body = request.postDataJSON();
    expect(body.cashierDiscountMode).toBe('percent');
    expect(body.cashierDiscountValue).toBe(10);
    expect(body.paymentType).toBe('partial');
    expect(body.amountPaid).toBe(500);
    expect(body.authCode).toBe('1234');
  });

  test('HU-ADM-17 / E2E-ADM-10: corte de caja + ticket del corte', async ({ page }) => {
    await seedSession(page, posOperator());
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      stocks: [{ stockId: 'stk-pos', name: 'Sucursal POS', location: 'CDMX', linkedUserIds: [1], inventory: {} }],
      posCashControl: { stockId: 'stk-pos', attendantUserId: 1, currentTotal: 500, salesCount: 2, cashToKeepSuggested: 0 }
    });
    await mockApi(
      page,
      '/inventory/pos/cash-cut',
      { cut: { cashCutId: 'cut-1', stockId: 'stk-pos', total: 500, salesCount: 2, cashToKeep: 200, withdrawnAmount: 300, createdAt: '2026-08-01T20:00:00.000Z' } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Punto de Venta' }).click();
    await page.getByRole('button', { name: 'Hacer corte de caja' }).click();

    const modal = page.locator('ui-modal', { hasText: 'Corte de caja' });
    await expect(modal.getByLabel('Monto a dejar en caja')).toBeVisible();

    // Borde: monto mayor al disponible ($500) se bloquea antes de llamar al backend.
    await modal.getByLabel('Monto a dejar en caja').fill('9999');
    await modal.getByRole('button', { name: 'Registrar corte' }).click();
    await expect(modal.getByText('El monto a dejar en caja no puede ser mayor al disponible.')).toBeVisible();

    await modal.getByLabel('Monto a dejar en caja').fill('200');
    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/pos/cash-cut')),
      modal.getByRole('button', { name: 'Registrar corte' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ stockId: 'stk-pos', cashToKeep: 200 });
    // El modal de corte se cierra solo al confirmar (confirmPosCashCut -> closePosCashCutModal).
    await expect(modal.getByLabel('Monto a dejar en caja')).toHaveCount(0);

    // Feature: ticket imprimible del corte, con folio, operador y totales — accesible desde la
    // tarjeta "Ultimo corte" que queda visible tras cerrarse el modal.
    await page.getByRole('button', { name: 'Ver ticket' }).click();
    // Nota: <ui-modal> (host, display:inline) puede reportarse "hidden" aunque su contenido sí
    // sea visible; se valida sobre el subtítulo, no sobre el wrapper.
    await expect(page.getByText('Vista imprimible del corte de caja.')).toBeVisible();
    const ticket = page.locator('ui-modal', { hasText: 'Ticket del corte' });
    await expect(ticket.getByText('cut-1')).toBeVisible();
    await expect(ticket.getByText('Operador POS')).toBeVisible();
    await expect(ticket.getByText(/Ventas \(2\)/)).toBeVisible();
    await expect(ticket.getByText('$500', { exact: false })).toBeVisible();
    await expect(ticket.getByText('$200', { exact: false })).toBeVisible();
    await expect(ticket.getByRole('button', { name: 'Imprimir' })).toBeVisible();
  });

  test('Histórico POS agrupado por cortes: corte en curso + cortes anteriores con drill-down', async ({ page }) => {
    await seedSession(page, posOperator());
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      stocks: [{ stockId: 'stk-pos', name: 'Sucursal POS', location: 'CDMX', linkedUserIds: [1], inventory: {} }],
      posCashControl: { stockId: 'stk-pos', attendantUserId: 1, currentTotal: 300, salesCount: 1, cashToKeepSuggested: 0 },
      posSales: [
        {
          saleId: 'sale-cur-1',
          orderId: 'ord-cur-1',
          stockId: 'stk-pos',
          attendantUserId: 1,
          customerName: 'Cliente Actual',
          total: 300,
          paymentStatus: 'paid_branch',
          deliveryStatus: 'delivered_branch',
          paymentMethod: 'cash',
          createdAt: '2026-08-01T12:00:00.000Z',
          lines: []
          // Sin cashCutId: pertenece al "corte en curso".
        }
      ],
      posCashCuts: [
        {
          cashCutId: 'cut-hist-1',
          stockId: 'stk-pos',
          attendantUserId: 1,
          total: 500,
          salesCount: 2,
          cashToKeep: 100,
          withdrawnAmount: 0,
          createdAt: '2026-07-30T18:00:00.000Z',
          sales: [
            { saleId: 'sale-1', orderId: 'ord-hist-1', stockId: 'stk-pos', customerName: 'Cliente A', total: 250, createdAt: '2026-07-30T15:00:00.000Z' },
            { saleId: 'sale-2', orderId: 'ord-hist-2', stockId: 'stk-pos', customerName: 'Cliente B', total: 250, createdAt: '2026-07-30T17:00:00.000Z' }
          ],
          withdrawals: []
        },
        {
          cashCutId: 'cut-hist-2',
          stockId: 'stk-pos',
          attendantUserId: 1,
          total: 400,
          salesCount: 1,
          cashToKeep: 50,
          withdrawnAmount: 20,
          createdAt: '2026-07-31T18:00:00.000Z',
          sales: [
            { saleId: 'sale-3', orderId: 'ord-hist-3', stockId: 'stk-pos', customerName: 'Cliente C', total: 400, createdAt: '2026-07-31T16:00:00.000Z' }
          ],
          withdrawals: [{ id: 'wdr-1', stockId: 'stk-pos', amount: 20, reason: 'Compra insumos', createdAt: '2026-07-31T17:00:00.000Z' }]
        }
      ]
    });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Punto de Venta' }).click();

    // El corte en curso agrupa solo la venta sin cortar (ord-cur-1); las ventas históricas
    // (ord-hist-*) no aparecen como lista plana en esta tarjeta.
    await expect(page.getByText('Corte en curso', { exact: true })).toBeVisible();
    await expect(page.getByText('EN CURSO', { exact: true })).toBeVisible();
    await expect(page.getByText('ord-cur-1')).toHaveCount(0);

    // Sin haber cargado el histórico todavía, los cortes anteriores no aparecen.
    await expect(page.getByText('cut-hist-1')).toHaveCount(0);

    await page.getByRole('button', { name: 'Cargar cortes anteriores' }).click();
    await expect(page.getByText('cut-hist-1')).toBeVisible();
    await expect(page.getByText('cut-hist-2')).toBeVisible();

    // [0] corte en curso, [1] cut-hist-1, [2] cut-hist-2, todos con botón "Ver detalles".
    await expect(page.getByRole('button', { name: /Ver detalles/ })).toHaveCount(3);

    // Cada tarjeta de corte anterior comparte la misma clase; se escopea por su folio para no
    // depender de índices (que cambian cuando un botón pasa de "Ver detalles" a "Ocultar").
    const cutCard = (cutId: string) =>
      page.locator('div.rounded-2xl.border.border-olive-30.bg-ivory-70.p-3', { hasText: cutId });

    // Drill-down del primer corte anterior: muestra sus 2 ventas, no las del otro corte.
    await cutCard('cut-hist-1').getByRole('button', { name: /Ver detalles/ }).click();
    await expect(page.getByText('ord-hist-1')).toBeVisible();
    await expect(page.getByText('ord-hist-2')).toBeVisible();
    await expect(page.getByText('ord-hist-3')).toHaveCount(0);

    // Drill-down del segundo corte anterior: muestra su venta y su retiro.
    await cutCard('cut-hist-2').getByRole('button', { name: /Ver detalles/ }).click();
    await expect(page.getByText('ord-hist-3')).toBeVisible();
    await expect(page.getByText('Compra insumos')).toBeVisible();
  });
});

test.describe('Panel Admin — Comisiones', () => {
  test('HU-ADM-18: registrar comprobante de pago de comisiones', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      customers: [
        {
          customerId: 801,
          name: 'Cliente Comision',
          email: 'comision@findingu.mx',
          commissionsPrevStatus: 'pending',
          commissionsPrevMonth: 1200,
          commissionsPrevMonthKey: '2026-07',
          commissionsCurrentPending: 0,
          commissionsCurrentConfirmed: 0
        }
      ]
    });
    await mockApi(page, '/customers/801', { customer: { customerId: 801, name: 'Cliente Comision', email: 'comision@findingu.mx', documents: [] } });
    await mockApi(page, '/commissions/admin/receipt', { receipt: { ok: true } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();
    await page.getByRole('button', { name: 'Ver' }).last().click();

    await page.getByRole('button', { name: 'Pagar comisiones' }).click();
    const modal = page.locator('ui-modal', { hasText: 'Cargar comprobante' });
    await expect(modal.getByLabel('Comprobante (PDF o imagen)')).toBeVisible();

    await modal.getByLabel('Comprobante (PDF o imagen)').setInputFiles({
      name: 'comprobante-comisiones.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fake')
    });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/commissions/admin/receipt')),
      modal.getByRole('button', { name: 'Subir comprobante' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ customerId: 801, monthKey: '2026-07' });
    await expect(page.getByText('Comprobante cargado.')).toBeVisible();
  });
});

test.describe('Panel Admin — Cupones', () => {
  test('HU-ADM-19: crear cupón', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(page, '/coupons', { coupon: { code: 'BIENVENIDA10', type: 'percent', value: 10, active: true } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Cupones' }).click();

    await page.getByLabel('Código').fill('bienvenida10');
    await page.getByLabel('Valor (%)').fill('10');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/coupons') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Guardar cupón' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ code: 'BIENVENIDA10', type: 'percent', value: 10 });
  });

  test('HU-ADM-19 (borde): valor <= 0 bloquea el guardado sin llamar al backend', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Cupones' }).click();

    await page.getByLabel('Código').fill('SINVALOR');
    await page.getByRole('button', { name: 'Guardar cupón' }).click();

    await expect(page.getByText('El valor debe ser mayor a 0.')).toBeVisible();
  });

  test('HU-ADM-19: desactivar cupón ("Eliminar" = active=false, con confirmación previa)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      coupons: [{ code: 'PROMO20', type: 'percent', value: 20, active: true, redemptions: 0 }]
    });
    await mockApi(page, '/coupons/PROMO20', { message: 'ok', code: 'PROMO20' }, { method: 'DELETE' });

    page.once('dialog', (dialog) => dialog.accept());

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Cupones' }).click();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/coupons/PROMO20') && req.method() === 'DELETE'),
      page.getByTitle('Desactivar').click()
    ]);
    expect(request.url()).toContain('/coupons/PROMO20');
    await expect(page.getByText('Cupón PROMO20 desactivado.')).toBeVisible();
  });
});

test.describe('Panel Admin — Campañas', () => {
  test('HU-ADM-20: crear campaña con assets por formato (story/feed/banner)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(page, '/dashboard/campaigns/assets', { asset: { assetId: 'asset-1', url: 'https://cdn.findingu.mx/asset-1.jpg' } }, { method: 'POST' });
    await mockApi(page, '/dashboard/campaigns', { campaign: { campaignId: 'camp-1', name: 'Campana Verano', active: true, hook: 'Impulsa tu red', story: 'https://x/s.jpg', feed: 'https://x/f.jpg', banner: 'https://x/b.jpg' } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Campanas' }).click();

    await page.getByRole('textbox', { name: 'Nombre', exact: true }).fill('Campana Verano');
    await page.getByRole('textbox', { name: 'Hook corto' }).fill('Impulsa tu red');

    const fileInputs = page.locator('input[type=file]');
    const imageBuffer = Buffer.from('fake-image-bytes');
    await fileInputs.nth(0).setInputFiles({ name: 'story.jpg', mimeType: 'image/jpeg', buffer: imageBuffer });
    await fileInputs.nth(1).setInputFiles({ name: 'feed.jpg', mimeType: 'image/jpeg', buffer: imageBuffer });
    await fileInputs.nth(2).setInputFiles({ name: 'banner.jpg', mimeType: 'image/jpeg', buffer: imageBuffer });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/dashboard/campaigns') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Guardar campana' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ name: 'Campana Verano', hook: 'Impulsa tu red' });
    await expect(page.getByText('Campana guardada: Campana Verano.')).toBeVisible();
  });
});

test.describe('Panel Admin — Notificaciones', () => {
  test('HU-ADM-21 / E2E-ADM-13: crear notificación con vigencia y link', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(
      page,
      '/dashboard/notifications',
      { notification: { id: 'noti-1', title: 'Nuevo catálogo', description: 'Revisa los productos nuevos.', startAt: '2026-08-01T00:00:00.000Z', endAt: '2026-08-31T00:00:00.000Z', active: true } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Notificaciones' }).click();

    await page.getByRole('textbox', { name: 'Titulo' }).fill('Nuevo catálogo');
    await page.getByRole('textbox', { name: 'Descripcion' }).fill('Revisa los productos nuevos.');
    await page.getByLabel('Mostrar desde').fill('2026-08-01T00:00');
    await page.getByLabel('Mostrar hasta').fill('2026-08-31T00:00');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/dashboard/notifications') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Guardar', exact: true }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ title: 'Nuevo catálogo', description: 'Revisa los productos nuevos.' });
    await expect(page.getByText('Notificacion creada: Nuevo catálogo.').first()).toBeVisible();
  });

  test('HU-ADM-21 (borde): "Mostrar hasta" anterior a "Mostrar desde" deja "Guardar" deshabilitado', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Notificaciones' }).click();

    await page.getByRole('textbox', { name: 'Titulo' }).fill('Aviso inválido');
    await page.getByRole('textbox', { name: 'Descripcion' }).fill('Vigencia invertida.');
    await page.getByLabel('Mostrar desde').fill('2026-08-31T00:00');
    await page.getByLabel('Mostrar hasta').fill('2026-08-01T00:00');

    await expect(page.getByRole('button', { name: 'Guardar', exact: true })).toBeDisabled();
  });
});

test.describe('Panel Admin — Configuración de negocio', () => {
  test('HU-ADM-22 / E2E-ADM-14: editar y guardar configuración (config_manage)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { businessConfig: defaultBusinessConfig() });
    await mockApi(page, '/commissions/config/app', { config: { ...defaultBusinessConfig(), rewards: { ...(defaultBusinessConfig() as any).rewards, cutRule: 'dynamic_compression' } } }, { method: 'PUT' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Configuracion' }).click();

    await page.getByLabel('Regla de corte').selectOption({ label: 'Compresión dinámica' });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/commissions/config/app') && req.method() === 'PUT'),
      page.getByRole('button', { name: 'Guardar configuracion' }).click()
    ]);
    expect(request.postDataJSON().config.rewards.cutRule).toBe('dynamic_compression');
    await expect(page.getByText('Configuracion guardada.').first()).toBeVisible();
  });

  test('HU-ADM-22: editar "Referidos directos requeridos" de un rango y guardarlo (bonuses.rankThresholds[].requiredDirects)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { businessConfig: defaultBusinessConfig() });
    await mockApi(page, '/commissions/config/app', { config: defaultBusinessConfig() }, { method: 'PUT' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Configuracion' }).click();

    const requiredDirectsInput = page.getByLabel('Referidos directos requeridos');
    await expect(requiredDirectsInput).toBeVisible();
    await requiredDirectsInput.fill('3');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/commissions/config/app') && req.method() === 'PUT'),
      page.getByRole('button', { name: 'Guardar configuracion' }).click()
    ]);
    expect(request.postDataJSON().config.bonuses.rankThresholds[0].requiredDirects).toBe(3);
    await expect(page.getByText('Configuracion guardada.').first()).toBeVisible();
  });

  test('HU-ADM-22 (borde): "Restaurar defaults" solo actualiza el borrador local (no llama al backend)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { businessConfig: defaultBusinessConfig() });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Configuracion' }).click();

    await page.getByRole('button', { name: 'Restaurar defaults' }).click();
    await expect(page.getByText('Se cargaron valores por defecto locales. Guarda para aplicar.')).toBeVisible();
  });
});

test.describe('Panel Admin — Reportes XLSX', () => {
  test('HU-ADM-23 / E2E-REP-01, E2E-REP-05: descargar reporte de Pedidos y reporte mensual consolidado', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Estadisticas' }).click();

    const content = page.locator('section').first();

    const [fullReportDownload] = await Promise.all([
      page.waitForEvent('download'),
      content.getByRole('button', { name: 'Reporte completo Excel' }).click()
    ]);
    expect(fullReportDownload.suggestedFilename()).toMatch(/\.xlsx$/);

    // El botón "Pedidos" del tab de reportes coincide en texto con el botón "Pedidos" del
    // bottom-nav móvil (misma sección <section>, clase distinta: navbtn); se excluye por clase.
    await content.locator('button:not(.navbtn):not(.mobbtn)', { hasText: 'Pedidos' }).click();
    const [ordersDownload] = await Promise.all([
      page.waitForEvent('download'),
      content.getByRole('button', { name: 'Exportar pedidos' }).click()
    ]);
    expect(ordersDownload.suggestedFilename()).toMatch(/\.xlsx$/);
  });

  test('HU-ADM-23 / E2E-REP-02..04: descargar reportes de Clientes, Productos y Stocks', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Estadisticas' }).click();
    const content = page.locator('section').first();

    for (const [tab, button] of [
      ['Clientes', 'Exportar clientes'],
      ['Productos', 'Exportar productos'],
      ['Stocks', 'Exportar stocks']
    ] as const) {
      // Excluye el botón homónimo del bottom-nav móvil (clase navbtn) dentro de la misma <section>.
      await content.locator('button:not(.navbtn):not(.mobbtn)', { hasText: tab }).click();
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        content.getByRole('button', { name: button }).click()
      ]);
      expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
    }
  });

  test('HU-ADM-23 / E2E-REP-09: descargar reporte de comisiones (buildSheet ya resuelve encabezados vacíos)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      customers: [{ customerId: 901, name: 'Cliente Reporte', email: 'reporte@findingu.mx' }]
    });
    await mockApi(page, /\/commissions\/summary/, { summary: {} }, { method: 'GET' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Exportar' }).click()
    ]);
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  });
});
