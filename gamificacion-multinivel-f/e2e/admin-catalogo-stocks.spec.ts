import { test, expect, seedSession, USERS, blockUnmockedApi, mockApi } from './support/fixtures';
import { mockAdminBaseline, selectByVisibleText, selectByExactLabel } from './support/admin-mocks';

// Catálogo (productos) y stocks/inventario — prioridad #4/#5.
// HU-ADM-12 (Alta, CRUD productos), HU-ADM-13 (Media, producto del mes),
// HU-ADM-14 (Media, stocks/transferencias), HU-ADM-15 (Media, merma de inventario).
// Fuente: docs/hu/04-hu-admin.md.

test.describe('Panel Admin — Catálogo de productos', () => {
  test('HU-ADM-12 / E2E-ADM-06: crear producto (product_add)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(page, '/catalog/product', { product: { productId: 21, name: 'Colageno Nuevo', price: 499, active: true } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Productos' }).click();

    await page.getByRole('textbox', { name: 'Nombre', exact: true }).fill('Colageno Nuevo');
    await page.getByRole('spinbutton', { name: 'Precio' }).fill('499');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/catalog/product') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Guardar' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ name: 'Colageno Nuevo', price: 499 });
  });

  test('HU-ADM-12: eliminar producto pide confirmación previa', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 22, name: 'Colageno Retirable', price: 350, active: true, inOnlineStore: true, inPOS: true, commissionable: true }]
    });
    await mockApi(page, '/catalog/product/remove', { ok: true, productId: 22 }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Productos' }).click();

    await page.getByRole('button', { name: 'Eliminar' }).last().click();
    // <ui-modal> es el host del componente (sin tamaño propio, contenido en position:fixed);
    // se valida visibilidad sobre el texto de confirmación, no sobre el wrapper.
    await expect(page.getByText('¿Estás seguro que deseas eliminar')).toBeVisible();
    const modal = page.locator('ui-modal', { hasText: 'Eliminar producto' });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/catalog/product/remove')),
      modal.getByRole('button', { name: 'Eliminar' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ productId: 22 });
  });

  test('HU-ADM-13 / E2E-ADM-07: marcar producto del mes', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 23, name: 'Colageno Estrella', price: 550, active: true, inOnlineStore: true, inPOS: true, commissionable: true }]
    });
    await mockApi(page, '/catalog/product/product-of-month', { productOfMonth: { productId: 23 } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Productos' }).click();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/catalog/product/product-of-month')),
      page.getByRole('button', { name: 'Producto del mes' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ productId: 23 });
    await expect(page.getByText('Producto del mes actualizado: Colageno Estrella.')).toBeVisible();
  });
});

test.describe('Panel Admin — Stocks', () => {
  test('HU-ADM-14 / E2E-ADM-08: alta de stock (nombre + ubicación requeridos)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(page, '/inventory/stocks', { stock: { stockId: 'stk-new', name: 'Stock Norte', location: 'Monterrey Centro', linkedUserIds: [], inventory: {} } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();

    await page.getByRole('textbox', { name: 'Nombre' }).fill('Stock Norte');
    await page.getByRole('textbox', { name: 'Ubicacion' }).fill('Monterrey Centro');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/inventory/stocks') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Crear stock' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ name: 'Stock Norte', location: 'Monterrey Centro' });
  });

  test('HU-ADM-14: registrar entrada de inventario (stock_add_inventory)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 31, name: 'ProductoStock', price: 100, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [{ stockId: 'stk-A', name: 'Stock A', location: 'CDMX', linkedUserIds: [1], inventory: { 31: 10 } }],
      employees: [{ employeeId: 1, name: 'Operador Uno', email: 'op1@findingu.mx', canAccessAdmin: true, privileges: {}, active: true }]
    });
    await mockApi(page, '/inventory/stocks/stk-A/entries', { ok: true, stock: { stockId: 'stk-A', inventory: { 31: 15 } } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();
    await selectByVisibleText(selectByExactLabel(page, 'Stock'), 'Stock A');

    await page.getByRole('button', { name: 'Entrada' }).click();
    const modal = page.locator('ui-modal', { hasText: 'Registrar entrada de inventario' });
    await expect(modal.getByRole('button', { name: 'Registrar entrada' })).toBeVisible();
    await selectByVisibleText(selectByExactLabel(modal, 'Stock'), 'Stock A');
    await selectByVisibleText(selectByExactLabel(modal, 'Producto'), 'ProductoStock');
    await modal.getByLabel('Cantidad').fill('5');
    await selectByVisibleText(selectByExactLabel(modal, 'Registrado por'), 'Operador Uno');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/stocks/stk-A/entries')),
      modal.getByRole('button', { name: 'Registrar entrada' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ productId: 31, qty: 5 });
  });

  test('HU-ADM-14: crear transferencia y recibirla (usuario vinculado al destino)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 32, name: 'ProductoTransfer', price: 80, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [
        { stockId: 'stk-A', name: 'Stock A', location: 'CDMX', linkedUserIds: [1], inventory: { 32: 10 } },
        { stockId: 'stk-B', name: 'Stock B', location: 'GDL', linkedUserIds: [1], inventory: { 32: 0 } }
      ],
      employees: [{ employeeId: 1, name: 'Operador Uno', email: 'op1@findingu.mx', canAccessAdmin: true, privileges: {}, active: true }],
      transfers: [
        {
          transferId: 'trf-1',
          sourceStockId: 'stk-A',
          destinationStockId: 'stk-B',
          lines: [{ productId: 32, qty: 3 }],
          status: 'pending',
          createdAt: '2026-07-01T10:00:00.000Z'
        }
      ]
    });
    await mockApi(
      page,
      '/inventory/stocks/transfers',
      { transfer: { transferId: 'trf-2', sourceStockId: 'stk-A', destinationStockId: 'stk-B', lines: [{ productId: 32, qty: 3 }], status: 'pending' } },
      { method: 'POST' }
    );
    await mockApi(
      page,
      '/inventory/stocks/transfers/trf-1/receive',
      { transfer: { transferId: 'trf-1', sourceStockId: 'stk-A', destinationStockId: 'stk-B', lines: [{ productId: 32, qty: 3 }], status: 'received' } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();

    await selectByVisibleText(selectByExactLabel(page, 'Stock origen'), 'Stock A');
    await selectByVisibleText(selectByExactLabel(page, 'Stock destino'), 'Stock B');
    await selectByVisibleText(selectByExactLabel(page, 'Solicitado por'), 'Operador Uno');
    await selectByVisibleText(selectByExactLabel(page, 'Producto'), 'ProductoTransfer');
    await page.getByLabel('Cantidad').first().fill('3');

    const [createRequest] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/inventory/stocks/transfers') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Crear transferencia' }).click()
    ]);
    expect(createRequest.postDataJSON()).toMatchObject({ sourceStockId: 'stk-A', destinationStockId: 'stk-B' });

    // Recibir la transferencia pendiente ya existente (trf-1), requiere usuario vinculado al destino.
    await selectByVisibleText(selectByExactLabel(page, 'Usuario que recibe'), 'Operador Uno');
    const [receiveRequest] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/stocks/transfers/trf-1/receive')),
      page.getByRole('button', { name: 'Recibir' }).click()
    ]);
    expect(receiveRequest.postDataJSON()).toMatchObject({ receivedByUserId: 1 });
  });

  test('HU-ADM-14 (borde): transferencia bloqueada si el origen no tiene stock suficiente', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 33, name: 'ProductoEscaso', price: 60, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [
        { stockId: 'stk-A', name: 'Stock A', location: 'CDMX', linkedUserIds: [1], inventory: { 33: 2 } },
        { stockId: 'stk-B', name: 'Stock B', location: 'GDL', linkedUserIds: [1], inventory: { 33: 0 } }
      ]
    });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();

    await selectByVisibleText(selectByExactLabel(page, 'Stock origen'), 'Stock A');
    await selectByVisibleText(selectByExactLabel(page, 'Stock destino'), 'Stock B');
    await selectByVisibleText(selectByExactLabel(page, 'Producto'), 'ProductoEscaso');
    await page.getByLabel('Cantidad').first().fill('99');
    await page.getByRole('button', { name: 'Crear transferencia' }).click();

    await expect(page.getByText(/Stock insuficiente para ProductoEscaso/).first()).toBeVisible();
  });

  test('HU-ADM-15: registrar merma de inventario (stock_mark_damaged)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 34, name: 'ProductoDanado', price: 70, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [{ stockId: 'stk-A', name: 'Stock A', location: 'CDMX', linkedUserIds: [1], inventory: { 34: 8 } }],
      employees: [{ employeeId: 1, name: 'Operador Uno', email: 'op1@findingu.mx', canAccessAdmin: true, privileges: {}, active: true }]
    });
    await mockApi(page, '/inventory/stocks/stk-A/damages', { ok: true, stock: { stockId: 'stk-A', inventory: { 34: 6 } } }, { method: 'POST' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();
    await selectByVisibleText(selectByExactLabel(page, 'Stock'), 'Stock A');

    await page.getByRole('button', { name: 'Marcar danado' }).click();
    const modal = page.locator('ui-modal', { hasText: 'Marcar producto como danado' });
    await selectByVisibleText(selectByExactLabel(modal, 'Stock'), 'Stock A');
    await selectByVisibleText(selectByExactLabel(modal, 'Producto'), 'ProductoDanado');
    await modal.getByLabel('Cantidad').fill('2');
    await selectByVisibleText(selectByExactLabel(modal, 'Reportado por'), 'Operador Uno');
    await modal.getByLabel('Motivo').fill('Caja aplastada en traslado.');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/inventory/stocks/stk-A/damages')),
      modal.getByRole('button', { name: 'Confirmar dano' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ productId: 34, qty: 2, reason: 'Caja aplastada en traslado.' });
  });

  test('HU-ADM-15 (borde): merma bloqueada si excede el stock disponible', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      products: [{ productId: 35, name: 'ProductoLimitado', price: 40, active: true, inOnlineStore: true, inPOS: true, commissionable: true }],
      stocks: [{ stockId: 'stk-A', name: 'Stock A', location: 'CDMX', linkedUserIds: [1], inventory: { 35: 3 } }]
    });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Stocks' }).click();
    await selectByVisibleText(selectByExactLabel(page, 'Stock'), 'Stock A');

    await page.getByRole('button', { name: 'Marcar danado' }).click();
    const modal = page.locator('ui-modal', { hasText: 'Marcar producto como danado' });
    await selectByVisibleText(selectByExactLabel(modal, 'Stock'), 'Stock A');
    await selectByVisibleText(selectByExactLabel(modal, 'Producto'), 'ProductoLimitado');
    await modal.getByLabel('Cantidad').fill('50');
    await modal.getByLabel('Motivo').fill('Prueba de límite.');
    await modal.getByRole('button', { name: 'Confirmar dano' }).click();

    await expect(page.getByText(/Stock insuficiente para ProductoLimitado/).first()).toBeVisible();
  });
});
