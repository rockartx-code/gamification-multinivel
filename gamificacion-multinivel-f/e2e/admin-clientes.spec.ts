import { test, expect, seedSession, USERS, blockUnmockedApi, mockApi } from './support/fixtures';
import { mockAdminBaseline } from './support/admin-mocks';

// Clientes y empleados — prioridad #3.
// HU-ADM-06 (Media, búsqueda+perfil 360), HU-ADM-07 (Media, cambio de patrocinador),
// HU-ADM-08 (Media, privilegios de cliente — SIN UI, ver comentario abajo),
// HU-ADM-09 (Media, documentos de cliente), HU-ADM-10 (Media, alta de empleado),
// HU-ADM-11 (Media, privilegios de empleado). Fuente: docs/hu/04-hu-admin.md.

const CUSTOMERS = [
  { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', leaderId: null, level: '1', discount: '0%', commissions: 0 },
  { customerId: 602, name: 'Beto Sponsor', email: 'beto@findingu.mx', leaderId: null, level: '1', discount: '0%', commissions: 0 }
];

test.describe('Panel Admin — Clientes', () => {
  test('HU-ADM-06 / E2E-ADM-03: buscar cliente y ver su perfil 360°', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { customers: CUSTOMERS });
    await mockApi(page, '/customers/601', { customer: { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', documents: [] } });
    await mockApi(page, '/customers/602', { customer: { customerId: 602, name: 'Beto Sponsor', email: 'beto@findingu.mx', documents: [] } });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();

    await page.getByPlaceholder('Buscar por nombre o correo...').fill('Beto');
    await page.getByRole('button', { name: 'Ver' }).last().click();

    await expect(page.getByText('Documentos del cliente').first()).toBeVisible();
    await expect(page.locator('text=beto@findingu.mx').first()).toBeVisible();
  });

  test('HU-ADM-07 / E2E-ADM-04: cambiar patrocinador de un cliente', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { customers: CUSTOMERS });
    await mockApi(page, '/customers/601', { customer: { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', documents: [] } });
    await mockApi(page, '/customers/601', { customer: { customerId: 601, name: 'Ana Cliente', leaderId: 602 } }, { method: 'PATCH' });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();
    // Filtra a Ana (customerId 601): sin filtro, .last() en una lista de 2 clientes
    // (con doble render mobile/desktop) apuntaría al último cliente (Beto), no al primero.
    await page.getByPlaceholder('Buscar por nombre o correo...').fill('Ana');
    await page.getByRole('button', { name: 'Ver' }).last().click();

    await page.getByRole('button', { name: 'Cambiar patrocinador' }).click();
    await page.getByRole('button', { name: /Beto Sponsor/ }).click();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/customers/601') && req.method() === 'PATCH'),
      page.getByRole('button', { name: 'Guardar posicion' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ leaderId: 602 });
  });

  // NO AUTOMATIZADAS: HU-ADM-08 (Gestión de privilegios de cliente). El código en
  // admin.component.ts:3945-3973 (saveSelectedCustomerAccess, con la regla RBAC cruzada
  // user_manage_privileges/user_mark_admin) NO tiene ningún template asociado en
  // admin.component.html: no existe checkbox/toggle de canAccessAdmin ni de privilegios en el
  // panel del cliente seleccionado (verificado por búsqueda exhaustiva de
  // selectedCustomerAdminAccess/selectedCustomerPrivilegeDraft/saveSelectedCustomerAccess en el
  // HTML — 0 resultados). Es funcionalidad muerta o un bloque de UI pendiente de implementar;
  // no se puede accionar desde la interfaz y por lo tanto no es automatizable como E2E hasta que
  // exista el template. Reportar a negocio/desarrollo como gap real, no solo de pruebas.

  test('HU-ADM-09: subir documento de cliente (PDF válido)', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { customers: CUSTOMERS });
    await mockApi(page, '/customers/601', { customer: { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', documents: [] } });
    await mockApi(
      page,
      '/customers/601/documents',
      { customer: { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', documents: [{ id: 'doc-1', name: 'INE Ana', type: 'application/pdf' }] } },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();
    await page.getByPlaceholder('Buscar por nombre o correo...').fill('Ana');
    await page.getByRole('button', { name: 'Ver' }).last().click();

    await page.getByRole('textbox', { name: 'Nombre del documento' }).fill('INE Ana');
    await page.locator('input[type=file]').first().setInputFiles({
      name: 'ine.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fake')
    });

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/customers/601/documents')),
      page.getByRole('button', { name: 'Subir documento' }).click()
    ]);
    expect(request.postDataJSON().contentType).toBe('application/pdf');
    await expect(page.getByText('Documento asociado correctamente al cliente.')).toBeVisible();
  });

  test('HU-ADM-09 (borde): tipo de archivo no soportado se rechaza antes de subir', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, { customers: CUSTOMERS });
    await mockApi(page, '/customers/601', { customer: { customerId: 601, name: 'Ana Cliente', email: 'ana@findingu.mx', documents: [] } });

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Clientes' }).click();
    await page.getByPlaceholder('Buscar por nombre o correo...').fill('Ana');
    await page.getByRole('button', { name: 'Ver' }).last().click();

    await page.locator('input[type=file]').first().setInputFiles({
      name: 'nota.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('texto plano')
    });

    await expect(page.getByText('Solo se permiten PDF, PNG o JPG.')).toBeVisible();
  });
});

test.describe('Panel Admin — Empleados', () => {
  test('HU-ADM-10: alta de empleado con contraseña temporal', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    await mockApi(
      page,
      '/auth/employees',
      { employee: { employeeId: 701, name: 'Nuevo Empleado', email: 'nuevo@findingu.mx', canAccessAdmin: false, privileges: {}, active: true }, tempPassword: 'Xy9zAbc1' },
      { method: 'POST' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Empleados' }).click();

    await page.getByRole('textbox', { name: 'Nombre', exact: true }).fill('Nuevo Empleado');
    await page.getByRole('textbox', { name: 'Correo', exact: true }).fill('nuevo@findingu.mx');

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().endsWith('/auth/employees') && req.method() === 'POST'),
      page.getByRole('button', { name: 'Crear empleado' }).click()
    ]);
    expect(request.postDataJSON()).toMatchObject({ name: 'Nuevo Empleado', email: 'nuevo@findingu.mx' });
    await expect(page.getByText('Xy9zAbc1').first()).toBeVisible();
  });

  test('HU-ADM-11 / E2E-ADM-05: asignar privilegios a un empleado', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      employees: [{ employeeId: 701, name: 'Empleado Uno', email: 'uno@findingu.mx', canAccessAdmin: true, privileges: {}, active: true }]
    });
    await mockApi(
      page,
      '/auth/employees/701/privileges',
      { employee: { employeeId: 701, name: 'Empleado Uno', email: 'uno@findingu.mx', canAccessAdmin: true, privileges: { order_create: true }, active: true } },
      { method: 'PATCH' }
    );

    await page.goto('/#/admin');
    await page.locator('aside').first().getByRole('button', { name: 'Empleados' }).click();
    await page.getByRole('button', { name: 'Ver' }).click();

    await expect(page.getByText('Acceso y privilegios', { exact: true })).toBeVisible();
    // Checkbox sin accessible name propio: ubicarlo por el <span> hermano con el label.
    await page.getByText('Registrar nueva orden', { exact: true }).locator('xpath=..').locator('input[type=checkbox]').check();

    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url().includes('/auth/employees/701/privileges')),
      page.getByRole('button', { name: 'Guardar privilegios' }).click()
    ]);
    expect(request.postDataJSON().privileges).toMatchObject({ order_create: true });
    await expect(page.getByText('Permisos del empleado guardados.')).toBeVisible();
  });
});
