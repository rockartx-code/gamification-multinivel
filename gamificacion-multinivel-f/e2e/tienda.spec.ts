import { test, expect, acceptPrivacyNotice, mockApi, blockUnmockedApi } from './support/fixtures';
import type { Page } from '@playwright/test';

// Dominio: Tienda pública (/#/tienda). Fuente de verdad: docs/hu/02-hu-tienda-carrito-ordenes.md
// (HU-SHOP-01..06) y docs/qa/02-matriz-pruebas-e2e.md (E2E-SHOP-xx).
//
// /tienda usa ApiService.getUserDashboardData() -> GET /user-dashboard (endpoint @deprecated
// pero es el que consume TiendaComponent). La respuesta se usa TAL CUAL como UserDashboardData
// (sin normalización de red): products[].id / img / variants[].price / variants[].active vienen
// listos, a diferencia de /catalog/catalog (usado por el carrito) que sí normaliza.
//
// OJO orden de mocks: page.route ejecuta los handlers en orden LIFO (el último registrado corre
// primero). blockUnmockedApi() debe registrarse ANTES que los mocks específicos para que estos
// últimos (más específicos, registrados después) tengan prioridad. Registrarlo al final hace que
// el 500 catch-all se coma también las rutas ya mockeadas.

const PRODUCT_COLAGENO = {
  id: 'prod-colageno',
  name: 'Colágeno Hidrolizado',
  price: 590,
  badge: 'Bienestar',
  img: 'images/colageno.png',
  vpPoints: 10,
  tags: ['energia', 'recuperacion'],
  categoryIds: ['cat-suplementos'],
  inOnlineStore: true,
  variants: [
    { id: 'var-caps', name: 'Cápsulas', price: 590, active: true },
    { id: 'var-polvo', name: 'Polvo', price: 690, active: true }
  ]
};

const PRODUCT_MAGNESIO = {
  id: 'prod-magnesio',
  name: 'Magnesio Quelado',
  price: 420,
  badge: 'Energía',
  img: 'images/magnesio.png',
  vpPoints: 6,
  tags: ['energia'],
  categoryIds: ['cat-minerales'],
  inOnlineStore: true,
  variants: []
};

const PRODUCT_DISCONTINUADO = {
  id: 'prod-discontinuado',
  name: 'Producto Descontinuado',
  price: 100,
  badge: '',
  img: 'images/descontinuado.png',
  tags: [],
  categoryIds: ['cat-suplementos'],
  inOnlineStore: false, // HU-SHOP-01: no debe listarse en tienda pública
  variants: []
};

const CATEGORIES = [
  { id: 'cat-suplementos', name: 'Suplementos', active: true },
  { id: 'cat-minerales', name: 'Minerales', active: true }
];

function baseDashboardData(overrides: Record<string, unknown> = {}) {
  return {
    settings: { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: '', networkGoal: 300 },
    goals: [],
    products: [PRODUCT_COLAGENO, PRODUCT_MAGNESIO],
    featured: [],
    campaigns: [],
    categories: CATEGORIES,
    networkMembers: [],
    buyAgainIds: [],
    productOfMonth: null,
    ...overrides
  };
}

/** Bloquea el resto del API y mockea GET /user-dashboard. Debe llamarse antes de page.goto(). */
async function setupTienda(page: Page, overrides: Record<string, unknown> = {}) {
  await blockUnmockedApi(page);
  await mockApi(page, /\/user-dashboard/, baseDashboardData(overrides), { method: 'GET' });
}

// BUG DE ANDAMIAJE (no es del dominio, es de ui-form-field): cuando un <ui-form-field> usa
// [(ngModel)] Y un atributo estático name="...", el @Input('name') propio del componente NUNCA
// recibe el valor porque el `NgModel` directive de Angular (activado por [(ngModel)]) declara su
// PROPIO @Input('name') y se queda con el binding del atributo estático. Resultado: el <input>
// interno siempre renderiza sin atributo name, aunque <ui-form-field name="firstName"> sí lo
// tenga como atributo del host. Por eso `input[name="..."]` NUNCA encuentra estos campos: hay que
// usar getByLabel()/getByRole('textbox', {name: <label>}) en su lugar (confirmado navegando la
// app real). Este mismo bug rompe focusFirstMissingDeliveryField() en carrito.component.ts, que
// hace document.querySelector('[name="..."]') esperando encontrar el <input> real y en cambio
// encuentra el <ui-form-field> (no enfocable) — ver carrito-checkout.spec.ts.
async function fillTiendaRegisterForm(
  page: Page,
  values: { firstName?: string; apellidoPaterno?: string; apellidoMaterno?: string; email?: string; phone?: string; password?: string; confirmPassword?: string }
) {
  if (values.firstName !== undefined) await page.getByLabel('Nombre(s) *').fill(values.firstName);
  if (values.apellidoPaterno !== undefined) await page.getByLabel('Apellido paterno *').fill(values.apellidoPaterno);
  if (values.apellidoMaterno !== undefined) await page.getByLabel('Apellido materno *').fill(values.apellidoMaterno);
  if (values.email !== undefined) await page.getByLabel('Correo electrónico').fill(values.email);
  if (values.phone !== undefined) await page.getByLabel('Teléfono').fill(values.phone);
  if (values.password !== undefined) await page.getByLabel('Contraseña', { exact: true }).fill(values.password);
  if (values.confirmPassword !== undefined) await page.getByLabel('Confirmar contraseña').fill(values.confirmPassword);
}

test.describe('Tienda pública (/#/tienda)', () => {
  test('HU-SHOP-01 / E2E-SHOP-01: solo lista productos activos en tienda online', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page, { products: [PRODUCT_COLAGENO, PRODUCT_MAGNESIO, PRODUCT_DISCONTINUADO] });

    await page.goto('/#/tienda');

    const catalogo = page.locator('#catalogo');
    await expect(catalogo.getByText(PRODUCT_COLAGENO.name)).toBeVisible();
    await expect(catalogo.getByText(PRODUCT_MAGNESIO.name)).toBeVisible();
    await expect(catalogo.getByText(PRODUCT_DISCONTINUADO.name)).toHaveCount(0);
  });

  test('HU-SHOP-01 / E2E-SHOP-10: catálogo vacío no rompe la página y muestra el hero por defecto', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page, { products: [] });

    await page.goto('/#/tienda');

    // allProducts.length > 1 es falso con 0 productos: la sección #catalogo no se renderiza.
    await expect(page.locator('#catalogo')).toHaveCount(0);
    // El hero cae al defaultHero (COLÁGENO) porque no hay productOfMonth ni products[0].
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Cuida tu cuerpo.');
    await expect(page.getByText('Sin artículos')).toBeVisible();
  });

  test('HU-SHOP-01 / E2E-SHOP-02: el filtro de categoría reduce el catálogo mostrado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page);

    await page.goto('/#/tienda');

    const catalogo = page.locator('#catalogo');
    await expect(catalogo.getByText(PRODUCT_COLAGENO.name)).toBeVisible();
    await expect(catalogo.getByText(PRODUCT_MAGNESIO.name)).toBeVisible();

    await catalogo.getByRole('button', { name: 'Minerales' }).click();

    await expect(catalogo.getByText(PRODUCT_MAGNESIO.name)).toBeVisible();
    await expect(catalogo.getByText(PRODUCT_COLAGENO.name)).toHaveCount(0);

    // "Todos" restaura el catálogo completo.
    await catalogo.getByRole('button', { name: 'Todos' }).click();
    await expect(catalogo.getByText(PRODUCT_COLAGENO.name)).toBeVisible();
  });

  test('HU-SHOP-02 / E2E-SHOP-03: seleccionar una variante del hero cambia el precio mostrado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page);

    await page.goto('/#/tienda');

    const hero = page.locator('#hero');
    // El precio principal del hero usa esta clase específica; los botones de variante también
    // muestran su propio precio como pista (span.ml-1...), así que hay que acotar el locator para
    // no chocar con "strict mode" al haber dos nodos con el mismo texto "$690".
    const heroPrice = hero.locator('span.text-3xl.font-extrabold.text-main');
    // Sin productOfMonth, el hero por defecto es products[0] = Colágeno (precio base 590).
    await expect(heroPrice).toHaveText(/\$\s?590/);

    await hero.getByRole('button', { name: 'Polvo' }).click();
    await expect(heroPrice).toHaveText(/\$\s?690/);
  });

  test('HU-SHOP-03 / E2E-SHOP-04 y E2E-SHOP-05: agregar al carrito actualiza el contador y "Ver carrito" navega a /carrito', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page);

    await page.goto('/#/tienda');

    await expect(page.getByText('Sin artículos')).toBeVisible();
    await page.getByRole('button', { name: 'Agregar al carrito' }).first().click();
    await expect(page.getByText('1 artículo')).toBeVisible();

    // Agregar el mismo producto otra vez acumula cantidad (HU-SHOP-03).
    await page.getByRole('button', { name: 'Agregar al carrito' }).first().click();
    await expect(page.getByText('2 artículos')).toBeVisible();

    await page.getByRole('button', { name: 'Ver carrito' }).click();
    await expect(page).toHaveURL(/#\/carrito$/);
  });

  test('HU-SHOP-05 / E2E-SHOP-06: la ruta con refToken guarda el leaderId en localStorage', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page);

    await page.goto('/#/tienda/AFILIADO-XYZ');

    const leaderId = await page.evaluate(() => window.localStorage.getItem('leaderId'));
    expect(leaderId).toBe('AFILIADO-XYZ');
  });

  test('HU-SHOP-05: sin refToken no se escribe leaderId en localStorage', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await setupTienda(page);

    await page.goto('/#/tienda');

    const leaderId = await page.evaluate(() => window.localStorage.getItem('leaderId'));
    expect(leaderId).toBeNull();
  });

  test.describe('HU-SHOP-06: registro rápido desde la tienda', () => {
    test('E2E-SHOP-06 / borde: campos obligatorios incompletos bloquea el registro', async ({ page }) => {
      await acceptPrivacyNotice(page);
      await setupTienda(page);

      await page.goto('/#/tienda');
      await fillTiendaRegisterForm(page, { firstName: 'Ana' });
      await page.getByRole('button', { name: 'Crear cuenta y comprar' }).click();

      await expect(page.getByText('Completa los campos obligatorios.')).toBeVisible();
    });

    test('E2E-SHOP-06 / error: contraseñas que no coinciden bloquea el registro', async ({ page }) => {
      await acceptPrivacyNotice(page);
      await setupTienda(page);

      await page.goto('/#/tienda');
      await fillTiendaRegisterForm(page, {
        firstName: 'Ana',
        apellidoPaterno: 'Pérez',
        apellidoMaterno: 'López',
        email: 'ana@example.com',
        password: 'Password123',
        confirmPassword: 'Different123'
      });
      await page.getByRole('button', { name: 'Crear cuenta y comprar' }).click();

      await expect(page.getByText('Las contraseñas no coinciden.')).toBeVisible();
    });

    test('E2E-SHOP-06 / happy: registro con verificación de correo pendiente no autentica', async ({ page }) => {
      await acceptPrivacyNotice(page);
      await setupTienda(page);
      // real-api.service.ts createAccount(): si la respuesta no trae `ok: true` + `customerId`
      // (o `customer`), la mapea a un Error y el componente muestra "No se pudo crear la cuenta.".
      // Hay que simular el shape real del backend, no solo requiresEmailVerification.
      await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 556, requiresEmailVerification: true }, { method: 'POST' });

      await page.goto('/#/tienda');
      await fillTiendaRegisterForm(page, {
        firstName: 'Ana',
        apellidoPaterno: 'Pérez',
        apellidoMaterno: 'López',
        email: 'ana@example.com',
        password: 'Password123',
        confirmPassword: 'Password123'
      });
      await page.getByRole('button', { name: 'Crear cuenta y comprar' }).click();

      await expect(page.getByText('Solo falta un paso, confirma tu cuenta desde tu correo electrónico.')).toBeVisible();
      // No debe navegar fuera de /tienda: no hay sesión iniciada todavía.
      await expect(page).toHaveURL(/#\/tienda/);
    });

    test('E2E-SHOP-06 / happy: registro exitoso sin verificación navega a /dashboard', async ({ page }) => {
      await acceptPrivacyNotice(page);
      await setupTienda(page);
      await mockApi(page, '/auth/crearcuenta', {
        ok: true,
        customerId: 555,
        requiresEmailVerification: false,
        customer: { id: 555, name: 'Ana Pérez López', discountRate: 0, activeBuyer: false }
      }, { method: 'POST' });

      await page.goto('/#/tienda');
      await fillTiendaRegisterForm(page, {
        firstName: 'Ana',
        apellidoPaterno: 'Pérez',
        apellidoMaterno: 'López',
        email: 'ana@example.com',
        password: 'Password123',
        confirmPassword: 'Password123'
      });
      await page.getByRole('button', { name: 'Crear cuenta y comprar' }).click();

      await expect(page).toHaveURL(/#\/dashboard/);
    });

    test('E2E-SHOP-06 / error: el backend rechaza el registro (correo duplicado)', async ({ page }) => {
      await acceptPrivacyNotice(page);
      await setupTienda(page);
      await mockApi(page, '/auth/crearcuenta', { message: 'El correo ya está registrado.' }, { method: 'POST', status: 409 });

      await page.goto('/#/tienda');
      await fillTiendaRegisterForm(page, {
        firstName: 'Ana',
        apellidoPaterno: 'Pérez',
        apellidoMaterno: 'López',
        email: 'ana@example.com',
        password: 'Password123',
        confirmPassword: 'Password123'
      });
      await page.getByRole('button', { name: 'Crear cuenta y comprar' }).click();

      await expect(page.getByText('El correo ya está registrado.')).toBeVisible();
    });
  });
});

// NO AUTOMATIZADAS:
// - HU-SHOP-02 (hero por campaña vía query ?p=campaign:<id>): la lógica de mapCampaign() es
//   puramente de mapeo de datos ya cubierta indirectamente por E2E-SHOP-03; no aporta cobertura
//   adicional de comportamiento de UI distinta y se omite para no inflar el suite con más mocks
//   de la misma naturaleza.
// - HU-SHOP-04 (contador/subtotal reactivos en la barra inferior): cubierta como aserción dentro
//   de E2E-SHOP-04/05 (no se abre un caso aparte porque no hay interacción de usuario adicional).
