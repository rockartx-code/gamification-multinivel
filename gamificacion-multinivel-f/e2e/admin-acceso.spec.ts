import { test, expect, seedSession, USERS, blockUnmockedApi, E2EAuthUser } from './support/fixtures';
import { mockAdminBaseline } from './support/admin-mocks';

// HU-ADM-24 (Crítica): control de acceso a las 12 vistas admin vía los 30 privilegios de
// privileges.model.ts. Fuente: docs/hu/04-hu-admin.md HU-ADM-24, docs/qa/02 E2E-ADM-16/E2E-AUTH-20.
// También cubre el "borde" de HU-ADM-01 (gating de un botón de acción concreto sin privilegio).

function operatorUser(privileges: Record<string, boolean>): E2EAuthUser {
  return {
    userId: 'emp-e2e-rbac',
    name: 'Empleado RBAC',
    role: 'admin',
    token: 'e2e-fake-jwt-empleado-rbac',
    canAccessAdmin: true,
    privileges
  };
}

test.describe('Panel Admin — Control de acceso (RBAC)', () => {
  test('HU-ADM-24 / E2E-ADM-16: superusuario ve las 12 vistas del nav y aterriza en Pedidos', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    const nav = page.locator('aside').first();
    for (const label of [
      'Pedidos',
      'Clientes',
      'Empleados',
      'Productos',
      'Stocks',
      'Campanas',
      'Punto de Venta',
      'Estadisticas',
      'Cuadro de Honor',
      'Notificaciones',
      'Cupones',
      'Configuracion'
    ]) {
      await expect(nav.getByRole('button', { name: label })).toBeVisible();
    }

    // Vista inicial: Pedidos (currentView por defecto y primera de getFirstAllowedView()).
    await expect(page.getByRole('button', { name: 'Pendiente' })).toBeVisible();
  });

  test('HU-ADM-24 / E2E-AUTH-20: sesión de cliente no accede al panel admin', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await page.goto('/#/admin');

    await expect(page).not.toHaveURL(/#\/admin$/);
  });

  test('HU-ADM-24: empleado con un solo privilegio de pantalla solo ve esa vista en el nav', async ({ page }) => {
    await seedSession(page, operatorUser({ access_screen_products: true }));
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    const nav = page.locator('aside').first();
    await expect(nav.getByRole('button', { name: 'Productos' })).toBeVisible();
    await expect(nav.getByRole('button', { name: 'Pedidos' })).toHaveCount(0);
    await expect(nav.getByRole('button', { name: 'Clientes' })).toHaveCount(0);
    await expect(nav.getByRole('button', { name: 'Configuracion' })).toHaveCount(0);

    // getFirstAllowedView() debe aterrizar directo en 'products' (única vista permitida).
    await expect(page.getByPlaceholder('Buscar por nombre, SKU, estado...')).toBeVisible();
  });

  test('HU-ADM-24 (borde): un privilegio no reconocido no otorga acceso a ninguna vista', async ({ page }) => {
    // USERS.adminLimitado trae privileges={order_view:true}; 'order_view' NO es un AppPrivilege
    // válido (privileges.model.ts) por lo que normalizePrivileges lo descarta: el usuario queda
    // sin ningún privilegio real y no puede ver ninguna vista del nav.
    await seedSession(page, USERS.adminLimitado);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    const nav = page.locator('aside').first();
    await expect(nav.getByRole('button', { name: 'Pedidos' })).toHaveCount(0);
    await expect(nav.getByRole('button', { name: 'Clientes' })).toHaveCount(0);
    await expect(nav.getByRole('button', { name: 'Configuracion' })).toHaveCount(0);
  });

  test('HU-ADM-24 (borde): "coupons" no se autoselecciona aunque el usuario tenga config_manage', async ({ page }) => {
    // getFirstAllowedView() (admin.component.ts:2052-2055) excluye 'coupons' de la lista
    // ordenada de fallback aunque comparta el mismo privilegio (config_manage) que 'notifications'.
    await seedSession(page, operatorUser({ config_manage: true }));
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    const nav = page.locator('aside').first();
    // Ambas vistas comparten el privilegio y deben aparecer en el nav...
    await expect(nav.getByRole('button', { name: 'Notificaciones' })).toBeVisible();
    await expect(nav.getByRole('button', { name: 'Cupones' })).toBeVisible();
    // ...pero la vista inicial resuelta es 'notifications', no 'coupons'.
    await expect(page.getByRole('button', { name: 'Guardar', exact: true })).toBeVisible();

    // Navegar manualmente a Cupones sí funciona (solo no se autoselecciona).
    await nav.getByRole('button', { name: 'Cupones' }).click();
    await expect(page.getByRole('button', { name: 'Guardar cupón' })).toBeVisible();
  });

  test('HU-ADM-01 (borde): sin order_mark_paid, "Cambiar estado" no aparece para un pedido pendiente', async ({ page }) => {
    await seedSession(page, operatorUser({ access_screen_orders: true }));
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      orders: [
        {
          orderId: 'ord-rbac-1',
          customer: 'Cliente RBAC',
          total: 500,
          status: 'pending',
          createdAt: '2026-07-01T10:00:00.000Z'
        }
      ]
    });

    await page.goto('/#/admin');

    await expect(page.getByText('Cliente RBAC').last()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cambiar estado' })).toHaveCount(0);
  });

  test('Acciones pendientes: un operador limitado solo ve las acciones que puede atender', async ({ page }) => {
    // order_mark_shipped -> puede atender warning.type 'shipping'; NO tiene
    // commissions_register_payment ni order_mark_paid, así que 'commissions' y 'payments' deben
    // quedar ocultos para este usuario (a diferencia de un superusuario, que ve las 3).
    await seedSession(page, operatorUser({ access_screen_orders: true, order_mark_shipped: true }));
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      warnings: [
        { type: 'shipping', text: 'Hay pedidos pagados sin enviar.', severity: 'high' },
        { type: 'commissions', text: 'Comisiones pendientes por depositar.', severity: 'high' },
        { type: 'payments', text: 'Pedidos pendientes de pago.', severity: 'medium' }
      ]
    });

    await page.goto('/#/admin');
    await expect(page.getByText('1 urgentes')).toBeVisible();

    await page.getByRole('button', { name: 'Acciones' }).click();
    await expect(page.getByText('Acciones urgentes')).toBeVisible();
    await expect(page.getByText('Hay pedidos pagados sin enviar.')).toBeVisible();
    await expect(page.getByText('Comisiones pendientes por depositar.')).toHaveCount(0);
    await expect(page.getByText('Pedidos pendientes de pago.')).toHaveCount(0);
  });

  test('Acciones pendientes: un superusuario ve todas las acciones sin filtrar', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page, {
      warnings: [
        { type: 'shipping', text: 'Hay pedidos pagados sin enviar.', severity: 'high' },
        { type: 'commissions', text: 'Comisiones pendientes por depositar.', severity: 'high' },
        { type: 'payments', text: 'Pedidos pendientes de pago.', severity: 'medium' }
      ]
    });

    await page.goto('/#/admin');
    await expect(page.getByText('3 urgentes')).toBeVisible();
  });
});
