import { test, expect, seedSession, USERS, mockApi, blockUnmockedApi } from './support/fixtures';
import {
  mockDashboardEndpoints,
  buildDashboardData,
  notificationFixture,
  ledgerRowFixture,
  apiPath
} from './support/dashboard-mocks';

// Dominio: Dashboard del Asociado — Comisiones, CLABE/retiro, notificaciones y KPIs MOCK-ONLY
// (VP/VG/rango, Cuadro de Honor, bonos).
// Fuente de verdad: docs/hu/03-hu-dashboard-red-comisiones.md (HU-DASH-07 a HU-DASH-11,
//   HU-DASH-16/17/18 [MOCK-ONLY]) · docs/qa/02-matriz-pruebas-e2e.md (E2E-DASH-12/13/14,
//   E2E-COMP-04, E2E-PROF-02/03, E2E-NOTI-01/02, E2E-DASH-06).
//
// Quirks aplicados:
// - Orden de mocks: blockUnmockedApi(page) se registra SIEMPRE antes que los mocks específicos.
//   Playwright evalúa los handlers de page.route() en orden INVERSO de registro (el último
//   registrado se evalúa primero); como blockUnmockedApi() nunca hace route.fallback(), si se
//   registrara después de los mocks específicos los taparía a TODOS con 500.
// - CLABE: el frontend exige /^\d{18}$/ ANTES de abrir el modal de confirmación; el guardado es
//   POST /customers/clabe (NO PATCH).
// - Al cargar el dashboard, si hay notificaciones NO leídas, prepareNotifications() abre
//   AUTOMÁTICAMENTE el modal de detalle de la primera (openNextNotification), y dispara
//   POST /dashboard/notifications/:id/read en el mismo load — hay que mockear esa ruta en
//   cualquier test con notificaciones sin leer, aunque el test no la ejercite explícitamente.
// - HU-DASH-10 (trigger de retiro) y HU-DASH-17 (Cuadro de Honor) tenían bugs de frontend que
//   los volvían inalcanzables/muertos (ver notas en sus describe blocks más abajo); ya están
//   corregidos y cubiertos con pruebas reales.

test.describe('HU-DASH-07: Ledger de comisiones del mes', () => {
  test('HU-DASH-07 / E2E-DASH-12: muestra los totales del mes y el ledger es expandible', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 1800,
          pendingTotal: 600,
          blockedTotal: 0,
          paidTotal: 1200,
          hasPending: true,
          hasConfirmed: true,
          clabeOnFile: true,
          clabeLast4: '4321',
          prevStatus: 'paid',
          payoutDay: 10,
          ledger: [
            ledgerRowFixture({ orderId: 'ORD-C1', level: 1, amount: 400, status: 'confirmed' }),
            ledgerRowFixture({ orderId: 'ORD-C2', level: 2, amount: 200, status: 'pending' })
          ]
        }
      })
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await expect(commissionsSection.getByText('Resumen del mes 2026-07.')).toBeVisible();
    await expect(commissionsSection).toContainText(/\$1,800/);
    await expect(commissionsSection).toContainText(/\$600/);
    await expect(commissionsSection.getByText('**** 4321')).toBeVisible();

    // ui-data-table renderiza SIEMPRE ambos templates (mobile/desktop) en el DOM; con el
    // viewport de escritorio por defecto el visible es `div.hidden.md:block` — se escopea ahí
    // para evitar violaciones de "strict mode" por coincidencias duplicadas.
    const desktopLedger = commissionsSection.locator('div.hidden.md\\:block');
    await expect(desktopLedger.getByText('ORD-C1')).toBeHidden();
    await commissionsSection.getByRole('button', { name: 'Ver detalles' }).click();

    await expect(desktopLedger.getByText('ORD-C1')).toBeVisible();
    await expect(desktopLedger.getByText('ORD-C2')).toBeVisible();
    await expect(desktopLedger.getByText('confirmed')).toBeVisible();
    await expect(desktopLedger.getByText('pending')).toBeVisible();

    await commissionsSection.getByRole('button', { name: 'Ocultar detalles' }).click();
    await expect(desktopLedger.getByText('ORD-C1')).toBeHidden();
  });

  test('HU-DASH-07: sin movimientos en el mes, el ledger muestra el estado vacío', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 0,
          pendingTotal: 0,
          blockedTotal: 0,
          paidTotal: 0,
          hasPending: false,
          ledger: []
        }
      })
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await commissionsSection.getByRole('button', { name: 'Ver detalles' }).click();
    await expect(commissionsSection.getByText('Sin movimientos este mes.')).toBeVisible();
  });

  test('HU-DASH-07: sin estructura de comisiones (commissions=null), la sección no se renderiza', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, { dashboard: buildDashboardData({ commissions: null }) });

    await page.goto('/#/dashboard');

    await expect(page.locator('#comisiones')).toHaveCount(0);
  });
});

test.describe('HU-DASH-08: Bloqueo de comisiones por ancestro inactivo', () => {
  test('HU-DASH-08 / E2E-COMP-04 (parcial): el tooltip de comisiones bloqueadas explica el motivo', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 500,
          pendingTotal: 500,
          blockedTotal: 350,
          paidTotal: 0,
          hasPending: true,
          ledger: [ledgerRowFixture({ orderId: 'ORD-BLK', status: 'blocked', amount: 350 })]
        }
      })
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await expect(commissionsSection).toContainText(/\$350/);

    // El aria-label vive en el host <ui-button>, no en el <button> nativo que renderiza dentro
    // (solo tiene un ícono aria-hidden, sin texto) — getByRole('button', {name}) no lo encuentra
    // porque el nombre accesible del <button> real queda vacío. Se ubica por el atributo CSS.
    await expect(page.getByText('Las comisiones que pasan por referidos inactivos no llegan a ti.')).toBeHidden();
    await page.locator('ui-button[aria-label="Info comisiones bloqueadas"]').click();
    await expect(page.getByText('Las comisiones que pasan por referidos inactivos no llegan a ti.')).toBeVisible();
  });
});

test.describe('HU-DASH-09: Registro/actualización de CLABE interbancaria', () => {
  test('HU-DASH-09 / E2E-PROF-02: una CLABE de 18 dígitos abre el modal de confirmación y dispara el guardado', async ({
    page
  }) => {
    let capturedBody: Record<string, unknown> | null = null;
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: { monthKey: '2026-07', monthTotal: 0, pendingTotal: 0, paidTotal: 0, hasPending: false, clabeOnFile: false }
      })
    });
    // El guardado es POST /customers/clabe (no PATCH, pese a lo que sugiere el nombre REST usual).
    // Capturamos el body para verificar que el frontend realmente llama al API con la CLABE
    // correcta (ver nota de BUG más abajo sobre por qué no se valida el toast/cierre del modal).
    await page.route('**/customers/clabe', async (route, request) => {
      if (request.method() === 'POST') {
        capturedBody = request.postDataJSON();
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await expect(commissionsSection.getByText('No registrada')).toBeVisible();

    await commissionsSection.getByRole('textbox', { name: 'CLABE interbancaria' }).fill('123456789012345678');
    await commissionsSection.getByRole('button', { name: 'Guardar' }).click();

    await expect(page.getByRole('heading', { name: 'Actualizar CLABE interbancaria' })).toBeVisible();
    await expect(page.getByText('123456789012345678')).toBeVisible();

    await page.getByRole('button', { name: 'Confirmar' }).click();
    await expect.poll(() => capturedBody).not.toBeNull();
    expect(capturedBody).toMatchObject({ clabe: '123456789012345678' });

    // FIX verificado: saveCustomerClabe() (user-dashboard.component.ts) fuerza this.cdr.detectChanges()
    // dentro del next() de subscribe() (app Angular 21 zoneless, mismo patrón que
    // tienda.component.ts#createAccount), así que el modal se cierra y el toast aparece de
    // inmediato sin esperar a que el usuario interactúe con otro control.
    await expect(page.getByRole('heading', { name: 'Actualizar CLABE interbancaria' })).toBeHidden();
    await expect(page.getByText('CLABE actualizada.')).toBeVisible();
  });

  test('HU-DASH-09 / E2E-PROF-03: una CLABE con longitud inválida es bloqueada por el frontend antes de llamar al API', async ({
    page
  }) => {
    let clabeCalled = false;
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: { monthKey: '2026-07', monthTotal: 0, pendingTotal: 0, paidTotal: 0, hasPending: false, clabeOnFile: false }
      })
    });
    // Mock instrumentado para detectar si el frontend llega a llamar al API (no debería): se
    // registra DESPUÉS de blockUnmockedApi para poder ganarle (Playwright evalúa page.route() en
    // orden INVERSO de registro — el último registrado se evalúa primero).
    await page.route('**/customers/clabe', async (route, request) => {
      if (request.method() === 'POST') {
        clabeCalled = true;
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await commissionsSection.getByRole('textbox', { name: 'CLABE interbancaria' }).fill('12345');
    await commissionsSection.getByRole('button', { name: 'Guardar' }).click();

    await expect(page.getByText('La CLABE debe tener 18 digitos.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Actualizar CLABE interbancaria' })).toBeHidden();
    expect(clabeCalled).toBe(false);
  });
});

test.describe('HU-DASH-10: Solicitud de retiro de comisiones', () => {
  // FIX verificado: user-dashboard.component.html ahora tiene un botón "Solicitar retiro" en
  // #comisiones (junto a "Ver detalles", cerca del total confirmado) que invoca
  // openCommissionModal(). Se habilita con comisiones confirmadas del mes > 0
  // (commissionSummary.hasConfirmed); la CLABE se sigue validando al enviar
  // (submitCommissionRequest() ya bloqueaba con "Ingresa tu CLABE interbancaria." si no hay CLABE
  // en archivo ni capturada) — por eso el trigger NO exige clabeOnFile para quedar habilitado.
  test('HU-DASH-10 / E2E-DASH-13: solicitar el retiro de comisiones confirmadas con CLABE registrada', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null;
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 1800,
          pendingTotal: 0,
          paidTotal: 0,
          hasPending: false,
          hasConfirmed: true,
          clabeOnFile: true,
          clabeLast4: '4321'
        }
      })
    });
    await page.route('**/commissions/request', async (route, request) => {
      if (request.method() === 'POST') {
        capturedBody = request.postDataJSON();
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ request: { status: 'requested' } })
      });
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await commissionsSection.getByRole('button', { name: 'Solicitar retiro' }).click();

    await expect(page.getByRole('heading', { name: 'CLABE interbancaria' })).toBeVisible();
    await page.getByRole('button', { name: 'Solicitar pago' }).click();

    await expect.poll(() => capturedBody).not.toBeNull();
    expect(capturedBody).toMatchObject({ clabe: '' });

    // FIX zoneless (mismo origen que HU-DASH-06/HU-DASH-09): submitCommissionRequest() fuerza
    // this.cdr.detectChanges() en su next(), así que el modal cierra y el toast aparece de inmediato.
    await expect(page.getByRole('heading', { name: 'CLABE interbancaria' })).toBeHidden();
    await expect(page.getByText('Solicitud enviada. Te contactaremos por el deposito.')).toBeVisible();
  });

  test('HU-DASH-10 / E2E-DASH-14: bloquear la solicitud de retiro cuando no hay CLABE capturada', async ({ page }) => {
    let requestCalled = false;
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 900,
          pendingTotal: 0,
          paidTotal: 0,
          hasPending: false,
          hasConfirmed: true,
          clabeOnFile: false
        }
      })
    });
    await page.route('**/commissions/request', async (route, request) => {
      if (request.method() === 'POST') {
        requestCalled = true;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ request: { status: 'requested' } })
      });
    });

    await page.goto('/#/dashboard');

    const commissionsSection = page.locator('#comisiones');
    await commissionsSection.getByRole('button', { name: 'Solicitar retiro' }).click();
    await expect(page.getByRole('heading', { name: 'CLABE interbancaria' })).toBeVisible();

    await page.getByRole('button', { name: 'Solicitar pago' }).click();

    await expect(page.getByText('Ingresa tu CLABE interbancaria.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'CLABE interbancaria' })).toBeVisible();
    expect(requestCalled).toBe(false);
  });

  test('HU-DASH-10: sin comisiones confirmadas del mes, el botón de solicitar retiro queda deshabilitado', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        commissions: {
          monthKey: '2026-07',
          monthTotal: 0,
          pendingTotal: 0,
          paidTotal: 0,
          hasPending: false,
          hasConfirmed: false,
          clabeOnFile: true,
          clabeLast4: '4321'
        }
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.locator('#comisiones').getByRole('button', { name: 'Solicitar retiro' })).toBeDisabled();
  });
});

test.describe('HU-DASH-11: Notificaciones del portal', () => {
  test('HU-DASH-11 / E2E-NOTI-01: el centro de avisos lista las notificaciones vigentes ya leídas', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        notifications: [
          notificationFixture({ id: 'n1', title: 'Nuevo catálogo disponible', description: 'Revisa los productos nuevos.', isRead: true }),
          notificationFixture({ id: 'n2', title: 'Mantenimiento programado', description: 'El domingo habrá mantenimiento.', isRead: true })
        ]
      })
    });

    await page.goto('/#/dashboard');

    await page.locator('ui-button[aria-label="Ver avisos del portal"]').click();

    await expect(page.getByRole('heading', { name: 'Notificaciones vigentes' })).toBeVisible();
    await expect(page.getByText('2 vigentes')).toBeVisible();
    await expect(page.getByText(/\d+ nuevas/)).toBeHidden();
    await expect(page.getByText('Nuevo catálogo disponible')).toBeVisible();
    await expect(page.getByText('Mantenimiento programado')).toBeVisible();
    await expect(page.getByText('Vista', { exact: true }).first()).toBeVisible();
  });

  test('HU-DASH-11 / E2E-NOTI-02: una notificación no leída se abre automáticamente y marcarla como leída actualiza su estado', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        notifications: [notificationFixture({ id: 'n1', title: 'Bono disponible', description: 'Revisa tu bono del mes.', isRead: false })]
      })
    });
    await mockApi(page, apiPath('/dashboard/notifications/n1/read'), { ok: true, notificationId: 'n1', readAt: '2026-08-01T00:00:00.000Z' }, {
      method: 'POST'
    });

    await page.goto('/#/dashboard');

    // prepareNotifications() abre automáticamente el detalle de la primera notificación no leída
    // y dispara markNotificationRead() en el mismo load.
    await expect(page.getByRole('heading', { name: 'Bono disponible' })).toBeVisible();
    await expect(page.getByText('Revisa tu bono del mes.')).toBeVisible();
    await page.getByRole('button', { name: 'Cerrar' }).click();

    await page.locator('ui-button[aria-label="Ver avisos del portal"]').click();
    const card = page.locator('.notification-modal-card', { hasText: 'Bono disponible' });
    await expect(card.getByText('Vista', { exact: true })).toBeVisible();
  });

  test('HU-DASH-11: sin notificaciones vigentes, la campanita de avisos no se muestra', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, { dashboard: buildDashboardData({ notifications: [] }) });

    await page.goto('/#/dashboard');

    await expect(page.locator('ui-button[aria-label="Ver avisos del portal"]')).toHaveCount(0);
  });
});

test.describe('HU-DASH-16/17/18 [MOCK-ONLY — sin backend real]', () => {
  // Confirmado en handler.py (backend real): 0 ocurrencias de rank/vp/vg/honorBoard/bonuses.
  // Estos campos solo existen hoy en MockApiService; contra la API real siempre llegan
  // undefined/[] y las secciones correspondientes no se muestran. Se cubren aquí en modo
  // mockeado (Playwright intercepta el API) para validar que la UI SÍ los renderiza cuando el
  // payload los trae, dejando constancia de que esto NO es una prueba de integración contra el
  // backend desplegado.

  test('HU-DASH-16 [MOCK-ONLY] @mock-only-backend / E2E-DASH-06 (parcial): VP, VG y rango se muestran cuando el payload los incluye', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({ vp: 180.5, vg: 2400, rank: 'ORO', bonuses: [] })
    });

    await page.goto('/#/dashboard');

    const volumenSection = page.locator('#volumen');
    await expect(volumenSection.getByText('VP (Volumen Personal)')).toBeVisible();
    await expect(volumenSection).toContainText('180.5');
    await expect(volumenSection.getByText('VG (Volumen de Grupo)')).toBeVisible();
    await expect(volumenSection).toContainText('2,400');
    await expect(volumenSection.getByText('Rango actual')).toBeVisible();
    await expect(volumenSection.getByText('ORO', { exact: true })).toBeVisible();
  });

  test('HU-DASH-18 [MOCK-ONLY] @mock-only-backend: los bonos del mes se muestran cuando el payload los incluye', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        vp: 0,
        vg: 0,
        bonuses: [
          {
            id: 'bonus-1',
            ruleId: 'oro-kit',
            ruleName: 'Bono ORO — Kit de bienvenida',
            customerId: 1,
            monthKey: '2026-07',
            rewardType: 'cash_mxn',
            rewardAmount: 5000,
            status: 'pending'
          }
        ]
      })
    });

    await page.goto('/#/dashboard');

    const volumenSection = page.locator('#volumen');
    await expect(volumenSection.getByText('Bonos del mes')).toBeVisible();
    await expect(volumenSection.getByText('Bono ORO — Kit de bienvenida')).toBeVisible();
    await expect(volumenSection).toContainText(/\$5,000/);
    await expect(volumenSection.getByText('Pendiente', { exact: true })).toBeVisible();
  });

  // FIX verificado: UserDashboardControlService.load() ahora copia `dashboard.honorBoard` al
  // armar UserDashboardData (y DashboardData declara el campo), así que
  // UserDashboardComponent.honorBoard deja de ser siempre null y la sección `#honor` sí se
  // renderiza cuando el payload lo incluye.
  test('HU-DASH-17 [MOCK-ONLY] @mock-only-backend: el Cuadro de Honor (Top 10) se muestra cuando el payload incluye honorBoard', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        honorBoard: {
          monthKey: '2026-07',
          // Ninguna entrada usa el customerId de USERS.cliente ('cust-e2e-001'): así isInTop10
          // queda en false y no se dispara el modal automático de Top 10 (checkHonorBoardOnLoad),
          // que duplicaría este mismo contenido y volvería la prueba no determinista por su delay.
          byVg: [{ customerId: 'cust-other-1', name: 'Beto Sponsor', vp: 300, vg: 5200, rank: 'DIAMANTE', position: 1 }],
          byVp: [{ customerId: 'cust-other-2', name: 'Ana Rivera', vp: 420, vg: 1800, rank: 'PLATINO', position: 1 }]
        }
      })
    });

    await page.goto('/#/dashboard');

    const honorSection = page.locator('#honor');
    await expect(honorSection.getByText('Cuadro de Honor')).toBeVisible();
    await expect(honorSection.getByText('Top 10 del mes 2026-07')).toBeVisible();
    await expect(honorSection.getByText('Beto Sponsor')).toBeVisible();
    await expect(honorSection.getByText('Ana Rivera')).toBeVisible();
  });
});
