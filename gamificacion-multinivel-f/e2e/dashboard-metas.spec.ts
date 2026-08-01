import { test, expect, seedSession, acceptPrivacyNotice, USERS, mockApi, blockUnmockedApi } from './support/fixtures';
import { mockDashboardEndpoints, buildDashboardData, buildCatalogData, goalFixture } from './support/dashboard-mocks';

// Dominio: Dashboard del Asociado — Metas gamificadas (activación, niveles de descuento,
// vista previa del carrito, metas de invitar/activar red).
// Fuente de verdad: docs/hu/03-hu-dashboard-red-comisiones.md (HU-DASH-01 a HU-DASH-04, HU-DASH-15)
//                    docs/qa/02-matriz-pruebas-e2e.md (E2E-DASH-02/04/18, E2E-REF-01)
//
// Quirks aplicados:
// - Orden de mocks: blockUnmockedApi(page) se registra SIEMPRE antes que los mocks específicos
//   (mockDashboardEndpoints/mockApi). Playwright evalúa los handlers de page.route() en orden
//   INVERSO de registro (el último registrado se evalúa primero); como blockUnmockedApi() nunca
//   hace route.fallback(), si se registrara después de los mocks específicos los taparía a
//   TODOS con 500.
// - El dashboard autenticado carga vía forkJoin de GET /catalog/catalog + GET /customers/dashboard
//   (UserDashboardControlService.load) — /user-dashboard es un endpoint LEGACY que el
//   componente actual NO llama.
// - processGoals() en user-dashboard.component.ts calcula la meta "principal" en el FRONTEND,
//   ignorando cualquier flag primary/secondary que pudiera enviar el servidor: toma
//   `goals.filter(g => !g.achieved && !g.locked)[0]` como activeGoal, el resto como secondaryGoals.
//   Las metas con locked=true quedan EXCLUIDAS por completo de la UI (no se muestran ni su
//   subtítulo) — no solo deshabilitadas.
// - El "vista previa del carrito" (HU-DASH-03) usa el subtotal del carrito GLOBAL
//   (CartControlService, basado en localStorage['cart-items']), combinado en GoalControlService,
//   y solo se inyecta en metas de consumo (`active`/`discount`/`discount_*`) que no sean de
//   conteo ni de unidad 'vp'.
// - ui-form-field replica el label como <span> dentro de <label> que envuelve el <input>: usar
//   getByRole('textbox', { name }) en vez de getByPlaceholder cuando hay label.

test.describe('HU-DASH-01: Metas gamificadas del mes', () => {
  test('HU-DASH-01 / E2E-DASH-04: muestra la meta principal y revela las metas secundarias al expandir', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      catalog: buildCatalogData(),
      dashboard: buildDashboardData({
        goals: [
          // NOTA: no se incluye ninguna meta con achieved:true aquí a propósito — al detectar una
          // meta recién lograda (loadAchievedGoals), el componente abre automáticamente el modal
          // de "meta lograda" (isGoalsModalOpen), lo que bloquearía el resto de esta prueba.
          goalFixture({
            key: 'invite',
            title: 'Invita a un nuevo miembro',
            subtitle: 'Suma 1 persona nueva a tu red este mes',
            target: 1,
            base: 0,
            isCountGoal: true,
            unit: 'count',
            ctaText: 'Invitar ahora',
            ctaFragment: 'links'
          }),
          goalFixture({
            key: 'discount_1',
            title: 'Nivel de descuento 30%',
            subtitle: 'Consumo neto entre $3,600 y $8,000',
            target: 3600,
            base: 1200,
            unit: 'mxn'
          })
        ]
      })
    });

    await page.goto('/#/dashboard');

    // La meta principal es la primera NO lograda y NO bloqueada: 'invite'.
    await expect(page.getByText('Objetivo principal del mes')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Invita a un nuevo miembro' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Invitar ahora' })).toBeVisible();

    // Las secundarias están ocultas hasta expandir.
    await expect(page.getByText('Nivel de descuento 30%')).toBeHidden();
    await page.getByRole('button', { name: 'Mostrar metas secundarias' }).click();

    const secondaryCard = page.locator('[data-goal="discount_1"]');
    await expect(secondaryCard).toBeVisible();
    await expect(secondaryCard.getByText('Consumo neto entre $3,600 y $8,000')).toBeVisible();
    await expect(secondaryCard).toContainText(/\$1,200/);
    await expect(secondaryCard).toContainText(/\$3,600/);

    await expect(page.getByRole('button', { name: 'Ocultar metas secundarias' })).toBeVisible();
  });

  test('HU-DASH-01 / E2E-DASH-04: con todas las metas logradas, no se muestra tarjeta de meta principal', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        goals: [
          goalFixture({ key: 'active', title: 'Actívate este mes', target: 2500, base: 2500, achieved: true }),
          goalFixture({ key: 'invite', title: 'Invita a un nuevo miembro', target: 1, base: 1, achieved: true })
        ]
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Objetivo principal del mes')).toBeHidden();
    await expect(page.getByRole('button', { name: 'Mostrar metas secundarias' })).toBeHidden();
  });

  test('HU-DASH-02 / E2E-DASH-02: la meta de nivel de descuento muestra el faltante en pesos (MXN), no en puntos', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        goals: [
          goalFixture({
            key: 'discount_1',
            title: 'Nivel de descuento 30%',
            subtitle: 'Consumo neto entre $3,600 y $8,000',
            target: 3600,
            base: 1200,
            unit: 'mxn',
            ctaText: 'Ir a tienda',
            ctaFragment: 'merchant'
          })
        ]
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByRole('heading', { name: 'Nivel de descuento 30%' })).toBeVisible();
    // remainingForGoal() usa formatMoney (MXN) para metas que no son de conteo: faltan 3600-1200=2400.
    await expect(page.getByText(/Te faltan \$2,400 para lograrlo/)).toBeVisible();
  });

  test('HU-DASH-04: la meta de invitar (conteo) muestra el avance como número, sin formato de moneda', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      dashboard: buildDashboardData({
        goals: [
          goalFixture({
            key: 'invite',
            title: 'Invita a un nuevo miembro',
            target: 1,
            base: 0,
            isCountGoal: true,
            unit: 'count',
            ctaText: 'Invitar ahora',
            ctaFragment: 'links'
          })
        ]
      })
    });

    await page.goto('/#/dashboard');

    await expect(page.getByText('Te faltan 1 para lograrlo')).toBeVisible();
    // No debe existir un "Te faltan $... para lograrlo" (con signo de moneda) para esta meta.
    // Ojo: no se puede usar un getByText(/Te faltan \$/) global — la tarjeta "Meta de red" (otra
    // sección) también usa la frase "Te faltan $... para cumplir la meta de red".
    await expect(page.getByText(/Te faltan \$[\d,]+ para lograrlo/)).toHaveCount(0);
  });

  test('HU-DASH-03: el subtotal del carrito se refleja como avance adicional en una meta de consumo secundaria', async ({
    page
  }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, {
      catalog: buildCatalogData({
        productOfMonth: {
          id: 'prod-hero-1',
          name: 'Producto Estrella',
          price: 500,
          badge: 'Destacado',
          img: '',
          hook: 'Ideal para avanzar tus metas.'
        }
      }),
      dashboard: buildDashboardData({
        goals: [
          goalFixture({
            key: 'invite',
            title: 'Invita a un nuevo miembro',
            target: 1,
            base: 0,
            isCountGoal: true,
            unit: 'count',
            ctaText: 'Invitar ahora',
            ctaFragment: 'links'
          }),
          goalFixture({
            key: 'discount_1',
            title: 'Nivel de descuento 30%',
            subtitle: 'Consumo neto entre $3,600 y $8,000',
            target: 3600,
            base: 0,
            unit: 'mxn'
          })
        ]
      })
    });

    await page.goto('/#/dashboard');
    await page.getByRole('button', { name: 'Mostrar metas secundarias' }).click();

    const secondaryCard = page.locator('[data-goal="discount_1"]');
    await expect(secondaryCard).toBeVisible();
    await expect(secondaryCard.getByText(/en carrito/)).toHaveCount(0);

    await page.getByRole('button', { name: 'Agregar a carrito' }).click();

    // goal.cart se recalcula 100% en frontend (GoalControlService) a partir del subtotal del
    // carrito global — nunca se persiste ni se envía hasta pagar la orden.
    await expect(secondaryCard.getByText(/\+\$500 en carrito/)).toBeVisible();
  });

  test('HU-DASH-01: si el API de comisiones/metas responde 500, el dashboard no truena y no muestra metas', async ({
    page
  }) => {
    const pageErrors: Error[] = [];
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockDashboardEndpoints(page, { dashboardStatus: 500 });
    page.on('pageerror', (err) => pageErrors.push(err));

    await page.goto('/#/dashboard');

    // El forkJoin(catalog, dashboard) falla completo si /customers/dashboard falla: sin datos
    // de metas/red/comisiones, pero el layout base (Tienda) sigue en pie sin excepción visible.
    await expect(page.getByRole('heading', { name: 'Tienda' })).toBeVisible();
    await expect(page.getByText('Objetivo principal del mes')).toBeHidden();
    expect(pageErrors).toHaveLength(0);
  });
});

test.describe('HU-DASH-15: Vista de invitado sin sesión', () => {
  test('HU-DASH-15 / E2E-DASH-18: como invitado, se muestra el CTA de registro en lugar de las metas', async ({
    page
  }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/catalog/catalog', buildCatalogData());

    await page.goto('/#/');

    await expect(page.getByRole('heading', { name: 'Regístrate para obtener beneficios' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Registrate' })).toBeVisible();
    await expect(page.getByText('Objetivo principal del mes')).toBeHidden();

    await page.getByRole('button', { name: 'Registrate' }).click();
    await expect(page).toHaveURL(/#\/landing/);
  });
});
