import type { Page } from '@playwright/test';
import { test, expect, seedSession, acceptPrivacyNotice, USERS, mockApi, blockUnmockedApi } from './support/fixtures';
import { mockDashboardEndpoints, buildDashboardData, buildCatalogData, networkMemberFixture } from './support/dashboard-mocks';

// Dominio: Dashboard del Asociado — Red multinivel, enlace de referido y patrocinador.
// Fuente de verdad: docs/hu/03-hu-dashboard-red-comisiones.md (HU-DASH-05, HU-DASH-06, HU-DASH-13)
//                    docs/qa/02-matriz-pruebas-e2e.md (E2E-DASH-05, E2E-REF-01/13, E2E-DASH-15/16)
//
// Quirks aplicados:
// - Orden de mocks: blockUnmockedApi(page) se registra SIEMPRE antes que los mocks específicos
//   (mockDashboardEndpoints/mockApi). Playwright evalúa los handlers de page.route() en orden
//   INVERSO de registro (el último registrado se evalúa primero); como blockUnmockedApi() nunca
//   hace route.fallback(), si se registrara después de los mocks específicos los taparía a
//   TODOS con 500.
// - La tabla de red (ui-data-table) renderiza SIEMPRE ambos templates (mobile y desktop) en el
//   DOM; el que no aplica queda oculto por CSS (`md:hidden` / `hidden md:block`), no removido.
//   Con el viewport de escritorio por defecto (proyecto "chromium" ~1280px) el visible es el
//   desktop (`div.hidden.md\\:block`) — se escopea la búsqueda de texto a ese contenedor para
//   evitar violaciones de "strict mode" por coincidencias duplicadas.
// - El enlace de referido usa literalmente `settings.userCode` (== customerId real en backend,
//   no un alias amigable): `{origin}/#/landing/{userCode}`.
// - El correo del patrocinador dispara mailto: Y copia el correo al portapapeles en el MISMO
//   evento de click (para que igual quede copiado si el cliente de correo no abre).
// - `ui-button` con [routerLink] SIEMPRE renderiza un <button> (nunca un <a>): usar
//   getByRole('button', ...), no getByRole('link', ...).

function desktopNetworkTable(page: Page) {
  return page.locator('#red div.hidden.md\\:block');
}

test.describe('HU-DASH-05: Árbol de red multinivel y estado de miembros', () => {
  test('HU-DASH-05 / E2E-DASH-05: muestra miembros por nivel con su consumo, estado y advertencia de bloqueo', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        networkMembers: [
          networkMemberFixture({ id: 'c1', name: 'María González', level: 'L1', spend: 800, status: 'Activa' }),
          networkMemberFixture({ id: 'c2', name: 'Luis Ramírez', level: 'L1', spend: 0, status: 'Inactiva' }),
          networkMemberFixture({
            id: 'c3',
            name: 'Ana Torres',
            level: 'L2',
            spend: 150,
            status: 'En progreso',
            leaderId: 'c1'
          })
        ]
      })
    });

    await page.goto('/#/dashboard');

    // Contadores: Nivel 1 = 2 (María + Luis), Nivel 2 = 1 (Ana), Activos = 1 (solo María).
    const networkSection = page.locator('#red');
    await expect(networkSection.locator('.progress-card', { hasText: 'Nivel 1' })).toContainText('2');
    await expect(networkSection.locator('.progress-card', { hasText: 'Nivel 2' })).toContainText('1');
    await expect(networkSection.locator('.progress-card', { hasText: 'Activos' })).toContainText('1');

    const table = desktopNetworkTable(page);
    await expect(table.getByText('María González', { exact: true })).toBeVisible();
    await expect(table.getByText('Luis Ramírez', { exact: true })).toBeVisible();
    await expect(table.getByText('Ana Torres', { exact: true })).toBeVisible();

    // FIX verificado: ui-status-badge.component.ts comprueba 'inact'/'inactive' ANTES que
    // 'activa'/'active' en displayStatus()/tone()/iconClass()/levelClass() del contexto
    // 'network' (antes 'inactiva'.includes('activa') === true hacía que un miembro "Inactiva"
    // se pintara como "Activa" en texto y tono). Se valida tanto por texto/tono visibles como
    // por la clase CSS de activityClass(), que ya acertaba antes del fix.
    const mariaRow = table.locator('div.grid', { hasText: 'María González' });
    const luisRow = table.locator('div.grid', { hasText: 'Luis Ramírez' });
    const anaRow = table.locator('div.grid', { hasText: 'Ana Torres' });
    await expect(mariaRow.getByText('Activa', { exact: true })).toBeVisible();
    await expect(mariaRow.locator('.status-active')).toBeVisible();
    await expect(luisRow.getByText('Inactiva', { exact: true })).toBeVisible();
    await expect(luisRow.locator('.status-inactive')).toBeVisible();
    await expect(anaRow.getByText('En progreso', { exact: true })).toBeVisible();
    await expect(anaRow.locator('.badge-pending')).toBeVisible();

    // Luis (L1) está inactivo -> se advierte que los beneficios de su L2 no llegan al usuario.
    await expect(page.getByText(/cuando hay inactivos en niveles L1/)).toBeVisible();
  });

  test('HU-DASH-05: sin miembros L1 inactivos, no se muestra la advertencia de bloqueo por inactividad', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        networkMembers: [networkMemberFixture({ id: 'c1', name: 'María González', level: 'L1', spend: 800, status: 'Activa' })]
      })
    });

    await page.goto('/#/dashboard');

    await expect(desktopNetworkTable(page).getByText('María González', { exact: true })).toBeVisible();
    await expect(page.getByText(/cuando hay inactivos en niveles L1/)).toBeHidden();
  });

  test('HU-DASH-05: con la red vacía, se muestra el estado vacío con CTA para compartir el enlace', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({ networkMembers: [] })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Aún no tienes miembros en tu red')).toBeVisible();
    await expect(page.getByText('Misión de red')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Compartir mi enlace' }).first()).toBeVisible();
  });

  test('HU-DASH-15: como invitado, la sección Red no se renderiza y el menú solo ofrece Tienda', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/catalog/catalog', buildCatalogData());

    await page.goto('/#/');

    await expect(page.locator('#red')).toHaveCount(0);
    await expect(page.locator('#links')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Red', exact: true })).toHaveCount(0);
  });
});

test.describe('HU-DASH-06: Enlace de referido propio', () => {
  test('HU-DASH-06 / E2E-REF-01 / E2E-REF-13: el enlace tiene el formato {origin}/#/landing/{userCode} y se copia al portapapeles', async ({
    page,
    context
  }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({ settings: { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: 'CUST-E2E-777', networkGoal: 300 } })
    });

    await page.goto('/#/dashboard');

    const linksSection = page.locator('#links');
    const linkField = linksSection.getByRole('textbox').first();
    await expect(linkField).toHaveValue(/\/#\/landing\/CUST-E2E-777$/);

    await linksSection.getByRole('button', { name: 'Copiar' }).first().click();

    // FIX verificado: copyToClipboard() (user-dashboard.component.ts) fuerza this.cdr.detectChanges()
    // dentro del .then() de navigator.clipboard.writeText() (app Angular 21 zoneless, mismo patrón
    // que tienda.component.ts#createAccount), así que el toast aparece de inmediato sin esperar a
    // que el usuario interactúe con otro control.
    await expect(page.getByText('Link y copy copiados. Pega en WhatsApp/Instagram.')).toBeVisible();

    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toMatch(/\/#\/landing\/CUST-E2E-777$/);
  });

  test('HU-DASH-06: como invitado, el enlace de referido es una cadena vacía (sección oculta)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/catalog/catalog', buildCatalogData());

    await page.goto('/#/');

    // Como invitado la sección #links completa está oculta (*ngIf="!isGuest") — el enlace vacío
    // nunca llega a renderizarse; se valida indirectamente por la ausencia de la sección.
    await expect(page.locator('#links')).toHaveCount(0);
  });
});

test.describe('HU-DASH-13: Contacto del patrocinador', () => {
  test('HU-DASH-13 / E2E-DASH-15 / E2E-DASH-16: con patrocinador asignado, el clic en su correo lo copia al portapapeles', async ({
    page,
    context
  }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        sponsor: { name: 'Carla Méndez', email: 'carla.mendez@example.com', phone: '+52 55 1234 5678', isDefault: false }
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Carla Méndez')).toBeVisible();
    await expect(page.getByText('Tu contacto directo en la red')).toBeVisible();

    // El (click) dispara copyText() en el MISMO evento que el mailto:, así que aunque el
    // navegador no tenga cliente de correo configurado, el valor ya quedó copiado.
    await page.getByRole('link', { name: 'carla.mendez@example.com' }).click();

    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBe('carla.mendez@example.com');
  });

  test('HU-DASH-13: sin patrocinador asignado, se usa el patrocinador por defecto de soporte FindingU', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        sponsor: { name: 'Soporte FindingU', email: 'contacto@findingu.com.mx', phone: '+52 1 55 1498 2351', isDefault: true }
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Soporte FindingU asignado')).toBeVisible();
    await expect(page.getByRole('link', { name: 'contacto@findingu.com.mx' })).toBeVisible();
  });
});

test.describe('HU-DASH-14: Historial de órdenes paginado y expandible', () => {
  test('HU-DASH-14 / E2E-DASH-17: cada orden se puede expandir para ver el detalle de productos', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      orders: [
        {
          id: 'ORD-E2E-100',
          orderId: 'ORD-E2E-100',
          createdAt: '2026-07-01T10:00:00.000Z',
          total: 1200,
          status: 'delivered',
          items: [
            { name: 'Producto A', quantity: 2, price: 300 },
            { name: 'Producto B', quantity: 1, price: 600 }
          ]
        }
      ]
    });

    await page.goto('/#/dashboard');

    const ordersSection = page.locator('#ordenes');
    const desktopOrdersTable = ordersSection.locator('div.hidden.md\\:block');
    await expect(desktopOrdersTable.getByText('ORD-E2E-100')).toBeVisible();
    await expect(desktopOrdersTable.getByText('Entregada')).toBeVisible();

    await expect(desktopOrdersTable.getByText('Producto A')).toBeHidden();
    await desktopOrdersTable.getByRole('button', { name: 'Productos' }).click();
    await expect(desktopOrdersTable.getByText('Producto A')).toBeVisible();
    await expect(desktopOrdersTable.getByText(/x2/)).toBeVisible();

    await desktopOrdersTable.getByRole('button', { name: 'Ocultar' }).click();
    await expect(desktopOrdersTable.getByText('Producto A')).toBeHidden();
  });

  test('HU-DASH-14: sin órdenes registradas, se muestra el estado vacío', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, { orders: [] });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Aun no tienes ordenes registradas.')).toBeVisible();
  });
});
