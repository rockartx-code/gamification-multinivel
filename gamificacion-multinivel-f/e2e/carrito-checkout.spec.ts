import { test, expect, seedSession, acceptPrivacyNotice, mockApi, blockUnmockedApi, USERS } from './support/fixtures';
import type { Page } from '@playwright/test';

// Dominio: Carrito y checkout (/#/carrito). Fuente de verdad:
// docs/hu/02-hu-tienda-carrito-ordenes.md (HU-SHOP-07..23) y docs/qa/02-matriz-pruebas-e2e.md
// (E2E-CART-xx, E2E-SHIP-xx).
//
// OJO orden de mocks (ver tienda.spec.ts): page.route es LIFO, blockUnmockedApi() se registra
// PRIMERO y los mocks específicos DESPUÉS para que tengan prioridad.
//
// OJO bug de andamiaje confirmado navegando la app real: <ui-form-field [(ngModel)] name="x">
// nunca propaga "x" al atributo `name` del <input> interno (choque con el @Input('name') propio
// de NgModel). Por eso para todos los campos que usan ui-form-field (Nombre, Teléfono, Calle,
// Número, Ciudad, CP, Estado, Pais, Entre calles, Referencias, y los del modal de invitado) se usa
// getByLabel()/getByRole en vez de locators por [name=...]. Los campos NATIVOS que no pasan por
// ui-form-field (textarea "Detalles en la entrega", checkbox "Guardar direccion", input de cupón)
// sí conservan su atributo name/placeholder normalmente.

const CATALOG_COLAGENO = {
  productId: 'prod-colageno',
  name: 'Colágeno Hidrolizado',
  price: 590,
  tags: ['energia', 'recuperacion'],
  images: [{ section: 'miniatura', url: 'images/colageno.png' }],
  inOnlineStore: true,
  weightKg: 0.5,
  lengthCm: 20,
  widthCm: 15,
  heightCm: 10,
  variants: []
};

const CATALOG_MAGNESIO = {
  productId: 'prod-magnesio',
  name: 'Magnesio Quelado',
  price: 420,
  tags: ['energia'],
  images: [{ section: 'miniatura', url: 'images/magnesio.png' }],
  inOnlineStore: true,
  variants: []
};

const CATALOG_TE = {
  productId: 'prod-te-relax',
  name: 'Té Relax',
  price: 150,
  tags: ['relajacion'],
  images: [{ section: 'miniatura', url: 'images/te.png' }],
  inOnlineStore: true,
  variants: []
};

const CATALOG_VITAMINA = {
  productId: 'prod-vitamina-c',
  name: 'Vitamina C',
  price: 280,
  tags: ['inmunidad'],
  images: [{ section: 'miniatura', url: 'images/vitamina.png' }],
  inOnlineStore: true,
  variants: []
};

const CATALOG_OMEGA = {
  productId: 'prod-omega-3',
  name: 'Omega 3',
  price: 350,
  tags: ['cardiovascular'],
  images: [{ section: 'miniatura', url: 'images/omega.png' }],
  inOnlineStore: true,
  variants: []
};

const DEFAULT_CATALOG_PRODUCTS = [CATALOG_COLAGENO, CATALOG_MAGNESIO, CATALOG_TE, CATALOG_VITAMINA, CATALOG_OMEGA];

const CART_ITEM_COLAGENO = { id: 'prod-colageno', name: 'Colágeno Hidrolizado', price: 590, qty: 1, note: '', img: 'images/colageno.png' };

// inventory: mapa productId -> qty tal cual lo devuelve GET /inventory/pickup-stocks (items STOCK
// completos, ver inventory_lambda.py). Ambas sucursales cubren de sobra CART_ITEM_COLAGENO (qty:1)
// para no romper los tests preexistentes que no ejercitan el filtrado por stock.
const PICKUP_STOCKS = [
  { id: 'stock-centro', name: 'Sucursal Centro', location: 'CDMX Centro', inventory: { 'prod-colageno': 5, 'prod-magnesio': 5 } },
  { id: 'stock-norte', name: 'Sucursal Norte', location: 'CDMX Norte', inventory: { 'prod-colageno': 5, 'prod-magnesio': 5 } }
];

const SHIPPING_RATE_ESTAFETA = {
  carrier: 'Estafeta', service: 'Terrestre', price: 120, displayPrice: 120,
  currency: 'MXN', transitDays: 3, deliveryEstimate: '3-5 días'
};
const SHIPPING_RATE_DHL = {
  carrier: 'DHL', service: 'Express', price: 220, displayPrice: 220,
  currency: 'MXN', transitDays: 1, deliveryEstimate: '1-2 días'
};

const SAVED_ADDRESS = {
  id: 'addr-1',
  label: 'Casa',
  recipientName: 'Cliente E2E',
  phone: '5555555555',
  street: 'Av Reforma',
  number: '100',
  address: 'Av Reforma 100, CDMX',
  city: 'CDMX',
  postalCode: '06600',
  state: 'CMX',
  country: 'MX',
  isDefault: true
};

function dashboardSettings() {
  return { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: '', networkGoal: 300 };
}

function clienteDashboardData(overrides: Record<string, unknown> = {}) {
  return {
    isGuest: false,
    settings: dashboardSettings(),
    customer: {
      id: 'cust-e2e-001',
      name: 'Cliente E2E',
      phone: '5555555555',
      addresses: [SAVED_ADDRESS],
      defaultAddressId: 'addr-1',
      shippingAddresses: [SAVED_ADDRESS],
      defaultShippingAddressId: 'addr-1'
    },
    user: { discountPercent: 30, discountActive: true },
    sponsor: null,
    goals: [],
    featured: [],
    campaigns: [],
    networkMembers: [],
    buyAgainIds: [],
    commissions: null,
    notifications: [],
    ...overrides
  };
}

interface SetupOpts {
  cartItems?: unknown[];
  catalogProducts?: unknown[];
  session?: typeof USERS.cliente;
  dashboard?: Record<string, unknown>;
  pickupStocks?: unknown[];
}

/** Registra el bloqueo de red y los mocks base del carrito. Llamar antes de page.goto(). */
async function setupCarrito(page: Page, opts: SetupOpts = {}) {
  await blockUnmockedApi(page);
  if (opts.session) {
    await seedSession(page, opts.session);
  } else {
    await acceptPrivacyNotice(page);
  }
  if (opts.cartItems) {
    await page.addInitScript((items) => window.localStorage.setItem('cart-items', JSON.stringify(items)), opts.cartItems);
  }
  await mockApi(page, '/catalog/catalog', { products: opts.catalogProducts ?? DEFAULT_CATALOG_PRODUCTS, productOfMonth: null }, { method: 'GET' });
  await mockApi(page, /\/inventory\/pickup-stocks/, { stocks: opts.pickupStocks ?? PICKUP_STOCKS }, { method: 'GET' });
  if (opts.session) {
    await mockApi(page, /\/customers\/dashboard/, opts.dashboard ?? clienteDashboardData(), { method: 'GET' });
  }
}

const guestModal = (page: Page) => page.locator('ui-modal').filter({ hasText: 'Crea tu cuenta y desbloquea beneficios' });

/** Botón de confirmar pedido en el resumen: su texto cambia según pickup/at_store/loading. */
const confirmOrderButton = (page: Page) =>
  page.locator('#resumen-carrito').getByRole('button', { name: /Pagar y finalizar|Reservar y pagar en sucursal|Creando orden/ });

/**
 * Botón de una tarifa de envío en la lista de opciones. getByText(carrier) es ambiguo: el mismo
 * texto del carrier también aparece repetido como resumen ("Estafeta · Terrestre") una vez que hay
 * una tarifa seleccionada, así que hay que acotar por rol de botón.
 */
const shippingRateButton = (page: Page, carrier: string) => page.getByRole('button', { name: new RegExp(carrier) });

async function fillValidDeliveryForm(page: Page) {
  // exact:true evita colisiones de substring (p.ej. "Calle" también matchea "Entre calles").
  await page.getByLabel('Nombre', { exact: true }).fill('Ana Pérez');
  await page.getByLabel('Teléfono', { exact: true }).fill('5512345678');
  await page.getByLabel('Calle', { exact: true }).fill('Av. Reforma');
  await page.getByLabel('Número', { exact: true }).fill('123');
  await page.getByLabel('Ciudad', { exact: true }).fill('Ciudad de México');
  await page.getByLabel('CP', { exact: true }).fill('06600');
  // OJO 1: en un <select kind="select"> de ui-form-field, el <label> envuelve también las
  // <option>, así que su nombre accesible completo incluye el texto de TODAS las opciones
  // (" Estado Selecciona un estadoAguascalientes...Zacatecas"). exact:true nunca matchea aquí;
  // hace falta match parcial (comportamiento por defecto de getByLabel sin exact).
  // OJO 2: <option [ngValue]="option.value"> hace que Angular escriba el atributo `value` real
  // como "<índice>: <valor>" (p.ej. "6: CMX"), no el valor limpio — selectOption('CMX') nunca
  // encuentra la opción. Hay que seleccionar por label visible en su lugar.
  await page.getByLabel('Estado').selectOption({ label: 'Ciudad de Mexico' });
  await page.getByLabel('Pais').selectOption({ label: 'Mexico' });
}

test.describe('Carrito (/#/carrito) — edición y sugeridos', () => {
  test('HU-SHOP-07 / E2E-CART-01: cambiar la cantidad de un ítem actualiza el subtotal y muestra el toast', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');

    const item = page.locator('#cart-item-prod-colageno');
    await expect(item).toBeVisible();
    await item.locator('input[type="number"]').fill('3');
    await item.locator('input[type="number"]').blur();

    await expect(page.getByText('Cantidad actualizada.')).toBeVisible();
    await expect(item.getByText('Parcial:')).toBeVisible();
  });

  test('HU-SHOP-07 / E2E-CART-02: bajar la cantidad a 0 remueve el ítem del carrito', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');

    const item = page.locator('#cart-item-prod-colageno');
    // fill() ya dispara (ngModelChange); no hacer blur() después: setQty(0) remueve el ítem del
    // DOM de inmediato y un blur() sobre un elemento ya desmontado cuelga el test.
    await item.locator('input[type="number"]').fill('0');

    await expect(page.getByText('Producto removido.')).toBeVisible();
    await expect(page.locator('#cart-item-prod-colageno')).toHaveCount(0);
  });

  test('HU-SHOP-07 / E2E-CART-02: el botón "Quitar" elimina el ítem', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');

    await page.locator('#cart-item-prod-colageno').getByRole('button', { name: 'Quitar' }).click();

    await expect(page.getByText('Producto removido.')).toBeVisible();
    await expect(page.locator('#cart-item-prod-colageno')).toHaveCount(0);
  });

  test('HU-SHOP-10 / E2E-CART-08 y E2E-CART-09: los sugeridos excluyen ítems ya en el carrito', async ({ page }) => {
    // Catálogo con suficientes productos fuera del carrito (4) para llenar las 3 tarjetas
    // sugeridas sin recurrir al "relleno" de computeSuggestedProducts() (ver bug documentado
    // más abajo cuando el catálogo es pequeño).
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');

    // Los sugeridos se renderizan como <ui-product-card mode="compact"> — el carrito ya tiene
    // Colágeno, así que no debe aparecer entre las tarjetas sugeridas (aunque su nombre siga
    // visible arriba, en la fila del propio ítem del carrito).
    await expect(page.getByText('Sugeridos')).toBeVisible();
    const suggestedNames = await page.locator('ui-product-card').allTextContents();
    expect(suggestedNames.some((t) => t.includes('Colágeno Hidrolizado'))).toBe(false);
    expect(suggestedNames.some((t) => t.includes('Magnesio Quelado'))).toBe(true);
  });

  test(
    'HU-SHOP-10 / regresión: con catálogo pequeño, el relleno de sugeridos no reintroduce ítems del carrito',
    async ({ page }) => {
      // carrito.component.ts, computeSuggestedProducts(): el paso de "relleno" (cuando `ordered`
      // tiene menos de 3 elementos) ahora también excluye `cartIds`, no solo lo ya incluido en
      // `ordered`. Con un catálogo de 3 productos y 1 ya en el carrito, el relleno ya no reintroduce
      // ese producto como "sugerido".
      await setupCarrito(page, {
        cartItems: [CART_ITEM_COLAGENO],
        catalogProducts: [CATALOG_COLAGENO, CATALOG_MAGNESIO, CATALOG_TE]
      });

      await page.goto('/#/carrito');
      await expect(page.getByText('Sugeridos')).toBeVisible();

      const suggestedNames = await page.locator('ui-product-card').allTextContents();
      expect(suggestedNames.some((t) => t.includes('Colágeno Hidrolizado'))).toBe(false);
    }
  );

  test('HU-SHOP-08 / E2E-CART-07: el estado de entrega sobrevive a navegar y volver al carrito (SPA)', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });
    await mockApi(page, /\/user-dashboard/, {
      settings: dashboardSettings(), goals: [], products: [], featured: [], campaigns: [],
      categories: [], networkMembers: [], buyAgainIds: [], productOfMonth: null
    }, { method: 'GET' });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);
    await expect(page.getByLabel('Calle', { exact: true })).toHaveValue('Av. Reforma');

    // Navegación SPA (hash-only) a /tienda y de vuelta: CartControlService.deliveryState vive en
    // memoria del singleton, no en localStorage, así que solo sobrevive sin recarga completa.
    await page.goto('/#/tienda');
    await page.goto('/#/carrito');

    await expect(page.getByLabel('Calle', { exact: true })).toHaveValue('Av. Reforma');
    await expect(page.getByLabel('Número')).toHaveValue('123');
    await expect(page.getByLabel('CP', { exact: true })).toHaveValue('06600');
  });
});

test.describe('Carrito — cupón de descuento (HU-SHOP-11)', () => {
  test('E2E-CART-14 / happy: cupón válido aplica el descuento', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/coupons/validate', {
      valid: true, message: 'Cupón aplicado: 10% de descuento.', discount: 59, code: 'BIENVENIDO10', type: 'percent', value: 10
    }, { method: 'POST' });

    await page.goto('/#/carrito');
    await page.getByPlaceholder('Código de descuento').fill('bienvenido10');
    await page.getByRole('button', { name: 'Aplicar' }).click();

    await expect(page.getByText('Cupón aplicado: 10% de descuento.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Quitar' }).last()).toBeVisible();
  });

  test('E2E-CART-14 / error: cupón inválido muestra el mensaje del backend sin aplicar descuento', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/coupons/validate', {
      valid: false, message: 'Cupón no encontrado.', discount: 0, code: 'NOEXISTE'
    }, { method: 'POST' });

    await page.goto('/#/carrito');
    await page.getByPlaceholder('Código de descuento').fill('noexiste');
    await page.getByRole('button', { name: 'Aplicar' }).click();

    await expect(page.getByText('Cupón no encontrado.')).toBeVisible();
  });

  test('E2E-CART-14 / error: si /coupons/validate no existe en el backend (404) se muestra "No se pudo validar el cupón."', async ({ page }) => {
    // Observación #4 del doc HU: el backend no implementa /coupons* pese a que el frontend ya
    // tiene la UI completa. Este test documenta cómo se degrada la UI ante ese 404 real.
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/coupons/validate', { message: 'Ruta no encontrada' }, { method: 'POST', status: 404 });

    await page.goto('/#/carrito');
    await page.getByPlaceholder('Código de descuento').fill('BIENVENIDO10');
    await page.getByRole('button', { name: 'Aplicar' }).click();

    await expect(page.getByText('No se pudo validar el cupón.')).toBeVisible();
  });
});

test.describe('Carrito — tipo de entrega y envío (HU-SHOP-12, HU-SHOP-15, HU-SHOP-16)', () => {
  test('E2E-SHIP-01 / E2E-SHIP-02: cotiza el envío automáticamente y permite elegir tarifa', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA, SHIPPING_RATE_DHL] }, { method: 'POST' });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);

    await expect(shippingRateButton(page, 'Estafeta')).toBeVisible();
    await expect(shippingRateButton(page, 'DHL')).toBeVisible();

    await shippingRateButton(page, 'DHL').click();
    // El resumen refleja la tarifa seleccionada.
    await expect(page.locator('#resumen-carrito').getByText('DHL · Express')).toBeVisible();
  });

  test('E2E-SHIP-03: sin tarifas disponibles muestra el mensaje correspondiente', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [] }, { method: 'POST' });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);

    await expect(page.getByText('No se encontraron opciones de envío para este código postal.')).toBeVisible();
  });

  test('E2E-SHIP-03 / borde: sin ENVIA_API_KEY el backend responde 200 con rates:[] y error informativo', async ({ page }) => {
    // HU-SHOP-15: si el backend no tiene ENVIA_API_KEY configurado responde
    // {rates:[], error:"Servicio de envío no configurado."} con status 200 (no es un error HTTP).
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [], error: 'Servicio de envío no configurado.' }, { method: 'POST' });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);

    // El frontend solo lee `rates`; sin tarifas cae al mismo mensaje genérico de "sin opciones".
    await expect(page.getByText('No se encontraron opciones de envío para este código postal.')).toBeVisible();
  });

  test('E2E-SHIP-03 / error: fallo de red al cotizar muestra "No se pudo calcular el envío."', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { message: 'Internal error' }, { method: 'POST', status: 500 });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);

    await expect(page.getByText('No se pudo calcular el envío.')).toBeVisible();
  });

  test('HU-SHOP-13 / E2E-CART-11: un CP con menos de 5 dígitos muestra el error de validación', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    await page.getByLabel('CP', { exact: true }).fill('066');

    await expect(page.getByText('Debe tener 5 digitos.')).toBeVisible();
  });

  test('HU-SHOP-13 / E2E-CART-12: intentar pagar con la dirección incompleta bloquea y muestra el toast', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    // No se llena ningún campo de dirección; deliveryType es 'delivery' por defecto.
    await confirmOrderButton(page).click();

    await expect(page.getByText('Completa calle, numero, ciudad, CP, estado y pais para continuar.')).toBeVisible();
  });

  test(
    'HU-SHOP-13 / regresión: focusFirstMissingDeliveryField() enfoca el <input> real',
    async ({ page }) => {
      // carrito.component.ts: por el bug de ui-form-field (ver cabecera del archivo),
      // document.querySelector('[name="..."]') solo matchea el <ui-form-field> (custom element sin
      // tabindex, no enfocable). focusFirstMissingDeliveryField() ahora ubica el contenedor por
      // `id="delivery-field-<campo>"` (agregado en el template) y busca el <input>/<textarea>/
      // <select> real dentro de él para enfocarlo.
      // OJO: no se usa getByLabel('Calle') aquí porque, una vez que el campo muestra su error
      // ("Campo obligatorio."), ese texto queda dentro del mismo <label> y pasa a formar parte del
      // nombre accesible del input ("Calle Campo obligatorio."), rompiendo el match con exact:true.
      await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
      await page.goto('/#/carrito');
      await confirmOrderButton(page).click();

      await expect(page.locator('#delivery-field-deliveryStreet input')).toBeFocused();
    }
  );

  test('HU-SHOP-14 / E2E-CART-10: cliente autenticado ve su dirección guardada prellenada', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO], session: USERS.cliente });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });

    await page.goto('/#/carrito');

    await expect(page.getByText('Casa')).toBeVisible();
    await expect(page.getByLabel('Calle', { exact: true })).toHaveValue('Av Reforma');
    await expect(page.getByLabel('CP', { exact: true })).toHaveValue('06600');
  });

  test('HU-SHOP-16 / E2E-SHIP-05: pickup carga y lista las sucursales disponibles', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('Sucursal Centro')).toBeVisible();
    await expect(page.getByText('Sucursal Norte')).toBeVisible();
    // Sin costo de envío en el resumen para pickup.
    await expect(page.getByText('Gratis (recoger en sucursal)')).toBeVisible();
  });

  test('HU-SHOP-16 / stock por sucursal: con stock completo en todas no se muestra ningún aviso', async ({ page }) => {
    // PICKUP_STOCKS por defecto ya trae inventory suficiente para CART_ITEM_COLAGENO (qty:1)
    // en ambas sucursales, así que el filtrado por stock no debe ocultar ninguna ni mostrar aviso.
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('Sucursal Centro')).toBeVisible();
    await expect(page.getByText('Sucursal Norte')).toBeVisible();
    await expect(page.getByText(/Ninguna sucursal tiene stock completo/)).not.toBeVisible();
    await expect(page.getByText(/No pudimos verificar el stock/)).not.toBeVisible();
  });

  test('HU-SHOP-16 / stock por sucursal: caso parcial, solo lista las sucursales con stock suficiente', async ({ page }) => {
    // Sucursal Norte solo tiene 1 unidad de prod-colageno; el carrito pide 3, así que debe
    // quedar fuera del selector y solo debe listarse Sucursal Centro (5 unidades).
    await setupCarrito(page, {
      cartItems: [{ ...CART_ITEM_COLAGENO, qty: 3 }],
      pickupStocks: [
        { id: 'stock-centro', name: 'Sucursal Centro', location: 'CDMX Centro', inventory: { 'prod-colageno': 5 } },
        { id: 'stock-norte', name: 'Sucursal Norte', location: 'CDMX Norte', inventory: { 'prod-colageno': 1 } }
      ]
    });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('Sucursal Centro')).toBeVisible();
    await expect(page.getByText('Sucursal Norte')).not.toBeVisible();
    await expect(page.getByText(/Ninguna sucursal tiene stock completo/)).not.toBeVisible();
  });

  test('HU-SHOP-16 / stock por sucursal: ninguna cubre el carrito, se muestran todas con aviso y no bloquea la orden', async ({ page }) => {
    // Ninguna sucursal cubre las 10 unidades pedidas: en vez de dejar el selector vacío (lo que
    // bloquearía la compra en pickup), se muestran todas con un aviso y se puede completar la orden.
    await setupCarrito(page, {
      cartItems: [{ ...CART_ITEM_COLAGENO, qty: 10 }],
      pickupStocks: [
        { id: 'stock-centro', name: 'Sucursal Centro', location: 'CDMX Centro', inventory: { 'prod-colageno': 2 } },
        { id: 'stock-norte', name: 'Sucursal Norte', location: 'CDMX Norte', inventory: { 'prod-colageno': 1 } }
      ]
    });

    let capturedBody: Record<string, unknown> | null = null;
    await page.route(`**/orders/create`, async (route) => {
      capturedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ order: { id: 'ORD-3001', status: 'pending', customer: 'Cliente', total: 5900, items: [] } })
      });
    });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('Sucursal Centro')).toBeVisible();
    await expect(page.getByText('Sucursal Norte')).toBeVisible();
    await expect(page.getByText(/Ninguna sucursal tiene stock completo/)).toBeVisible();

    await page.getByText('Sucursal Centro').click();
    await confirmOrderButton(page).click();

    await expect(page).toHaveURL(/#\/orden\/ORD-3001$/);
    expect((capturedBody as any).pickupStockId).toBe('stock-centro');
  });

  test('HU-SHOP-16 / stock por sucursal: si el endpoint de sucursales falla no bloquea el resto del carrito', async ({ page }) => {
    // GET /inventory/pickup-stocks responde 500: sin datos de sucursales el selector de pickup
    // no puede listar nada (mismo comportamiento que antes de esta mejora), pero el resto del
    // carrito (incluido el checkout por envío a domicilio) sigue funcionando con normalidad.
    await blockUnmockedApi(page);
    await acceptPrivacyNotice(page);
    await page.addInitScript((items) => window.localStorage.setItem('cart-items', JSON.stringify(items)), [CART_ITEM_COLAGENO]);
    await mockApi(page, '/catalog/catalog', { products: DEFAULT_CATALOG_PRODUCTS, productOfMonth: null }, { method: 'GET' });
    await mockApi(page, /\/inventory\/pickup-stocks/, { message: 'boom' }, { method: 'GET', status: 500 });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('No hay sucursales disponibles para recoger en este momento.')).toBeVisible();

    // El carrito no queda bloqueado: se puede volver a "Envío a domicilio" y seguir el checkout.
    await page.getByRole('button', { name: 'Envío a domicilio' }).click();
    await expect(page.getByLabel('Nombre', { exact: true })).toBeVisible();
  });

  test('HU-SHOP-16 / borde: sin sucursales disponibles muestra el mensaje correspondiente', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO], pickupStocks: [] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();

    await expect(page.getByText('No hay sucursales disponibles para recoger en este momento.')).toBeVisible();
  });

  test('HU-SHOP-16 / error: intentar pagar en pickup sin elegir sucursal bloquea con toast', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO], pickupStocks: [] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();
    await confirmOrderButton(page).click();

    await expect(page.getByText('Selecciona una sucursal para recoger tu pedido.')).toBeVisible();
  });
});

test.describe('Carrito — checkout / crear orden (HU-SHOP-18, HU-SHOP-20)', () => {
  test('HU-SHOP-18 / E2E-CART-13: invitado confirma una orden a domicilio sin registrarse (customerId=0)', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });

    let capturedBody: Record<string, unknown> | null = null;
    await page.route(`**/orders/create`, async (route) => {
      capturedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ order: { id: 'ORD-2001', status: 'pending', customer: 'Cliente', total: 710, items: [] } })
      });
    });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);
    await shippingRateButton(page, 'Estafeta').click();
    await confirmOrderButton(page).click();

    await expect(page).toHaveURL(/#\/orden\/ORD-2001$/);
    expect(capturedBody).not.toBeNull();
    expect((capturedBody as any).customerId).toBe(0);
  });

  test(
    'HU-SHOP-31 / HU-SHOP-18: la orden de un invitado con leaderId en localStorage incluye referrerAssociateId',
    async ({ page }) => {
      // carrito.component.ts: placeOrder() ahora lee localStorage['leaderId'] (guardado por
      // HU-SHOP-05 al visitar /tienda/:refToken) y lo envía como `referrerAssociateId` en el
      // payload de createOrder — mismo nombre de campo que lee el backend en
      // lambda/handler.py (_create_order/_apply_rewards_on_paid_order) y en
      // Micro-lambda-GMF/python/order_lambda.py, así que la comisión one-shot de invitado
      // (HU-SHOP-31) ya es alcanzable end-to-end.
      await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
      await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });
      await page.addInitScript(() => window.localStorage.setItem('leaderId', 'AFILIADO-XYZ'));

      let capturedBody: Record<string, unknown> | null = null;
      await page.route(`**/orders/create`, async (route) => {
        capturedBody = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ order: { id: 'ORD-2002', status: 'pending', customer: 'Cliente', total: 710, items: [] } })
        });
      });

      await page.goto('/#/carrito');
      await fillValidDeliveryForm(page);
      await shippingRateButton(page, 'Estafeta').click();
      await confirmOrderButton(page).click();
      await expect(page).toHaveURL(/#\/orden\/ORD-2002$/);

      expect((capturedBody as any)?.referrerAssociateId).toBe('AFILIADO-XYZ');
    }
  );

  test('HU-SHOP-20 / borde: carrito vacío bloquea la confirmación con un toast', async ({ page }) => {
    await setupCarrito(page, { cartItems: [] });

    await page.goto('/#/carrito');
    await confirmOrderButton(page).click();

    await expect(page.getByText('Agrega productos para continuar.')).toBeVisible();
  });

  test('HU-SHOP-20 / error: fallo de red al crear la orden no limpia el carrito', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });
    await mockApi(page, '/orders/create', { message: 'Internal error' }, { method: 'POST', status: 500 });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);
    await shippingRateButton(page, 'Estafeta').click();
    await confirmOrderButton(page).click();

    await expect(page.getByText('No se pudo crear la orden.')).toBeVisible();
    // El carrito no debió vaciarse: el ítem sigue visible.
    await expect(page.locator('#cart-item-prod-colageno')).toBeVisible();
  });

  test('HU-SHOP-20 / borde: si la orden se crea sin ID en la respuesta, no navega y avisa', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/shipping/quote', { rates: [SHIPPING_RATE_ESTAFETA] }, { method: 'POST' });
    await mockApi(page, '/orders/create', { order: { status: 'pending', customer: 'Cliente', total: 710, items: [] } }, { method: 'POST' });

    await page.goto('/#/carrito');
    await fillValidDeliveryForm(page);
    await shippingRateButton(page, 'Estafeta').click();
    await confirmOrderButton(page).click();

    await expect(page.getByText('Orden creada, pero no se recibió el ID.')).toBeVisible();
    await expect(page).toHaveURL(/#\/carrito/);
  });

  test('HU-SHOP-12 / E2E-CART-13: pickup con pago en sucursal crea la orden con el payload correcto', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    let capturedBody: Record<string, unknown> | null = null;
    await page.route(`**/orders/create`, async (route) => {
      capturedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ order: { id: 'ORD-2003', status: 'pending', customer: 'Cliente', total: 590, items: [] } })
      });
    });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Recoger en sucursal' }).click();
    await page.getByText('Sucursal Centro').click();
    await page.getByRole('button', { name: 'Pagar en sucursal' }).click();
    await confirmOrderButton(page).click();

    await expect(page).toHaveURL(/#\/orden\/ORD-2003$/);
    expect((capturedBody as any).deliveryType).toBe('pickup');
    expect((capturedBody as any).pickupStockId).toBe('stock-centro');
    expect((capturedBody as any).pickupPaymentMethod).toBe('at_store');
  });
});

test.describe('Carrito — registro de invitado (HU-SHOP-19)', () => {
  test('E2E-SHOP-06 / borde: campos obligatorios incompletos bloquea el registro de invitado', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Registrate' }).click();
    const modal = guestModal(page);
    await modal.getByLabel('Nombre(s) *').fill('Ana');
    await modal.getByRole('button', { name: 'Regístrate' }).click();

    await expect(modal.getByText('Completa los campos obligatorios.')).toBeVisible();
  });

  test('E2E-SHOP-06 / error: contraseñas distintas bloquea el registro de invitado', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Registrate' }).click();
    const modal = guestModal(page);
    await modal.getByLabel('Nombre(s) *').fill('Ana');
    await modal.getByLabel('Apellido paterno *').fill('Pérez');
    await modal.getByLabel('Apellido materno *').fill('López');
    await modal.getByLabel('Correo').fill('ana@example.com');
    await modal.getByLabel('Contraseña', { exact: true }).fill('Password123');
    await modal.getByLabel('Confirmar contraseña').fill('Distinta123');
    await modal.getByRole('button', { name: 'Regístrate' }).click();

    await expect(modal.getByText('Las contraseñas no coinciden.')).toBeVisible();
  });

  test('E2E-SHOP-06 / happy: registro de invitado con verificación pendiente cierra el modal', async ({ page }) => {
    await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 777, requiresEmailVerification: true }, { method: 'POST' });

    await page.goto('/#/carrito');
    await page.getByRole('button', { name: 'Registrate' }).click();
    const modal = guestModal(page);
    await modal.getByLabel('Nombre(s) *').fill('Ana');
    await modal.getByLabel('Apellido paterno *').fill('Pérez');
    await modal.getByLabel('Apellido materno *').fill('López');
    await modal.getByLabel('Correo').fill('ana@example.com');
    await modal.getByLabel('Contraseña', { exact: true }).fill('Password123');
    await modal.getByLabel('Confirmar contraseña').fill('Password123');
    await modal.getByRole('button', { name: 'Regístrate' }).click();

    await expect(modal).toBeHidden();
  });

  test(
    'HU-SHOP-19 / regresión: el toast de confirmación se renderiza tras el registro de invitado',
    async ({ page }) => {
      // Este repo NO tiene zone.js como polyfill, así que las devoluciones asíncronas de
      // HttpClient no disparan detección de cambios automática salvo que el propio código llame
      // ChangeDetectorRef.markForCheck()/detectChanges() — mismo patrón que
      // tienda.component.ts.createAccount(). carrito.component.ts.submitGuestRegister() ahora
      // llama `this.cdr.detectChanges()` tras fijar el toast en su subscribe, así que el mensaje
      // "Solo falta un paso..." se pinta de inmediato.
      await setupCarrito(page, { cartItems: [CART_ITEM_COLAGENO] });
      await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 777, requiresEmailVerification: true }, { method: 'POST' });

      await page.goto('/#/carrito');
      await page.getByRole('button', { name: 'Registrate' }).click();
      const modal = guestModal(page);
      await modal.getByLabel('Nombre(s) *').fill('Ana');
      await modal.getByLabel('Apellido paterno *').fill('Pérez');
      await modal.getByLabel('Apellido materno *').fill('López');
      await modal.getByLabel('Correo').fill('ana@example.com');
      await modal.getByLabel('Contraseña', { exact: true }).fill('Password123');
      await modal.getByLabel('Confirmar contraseña').fill('Password123');
      await modal.getByRole('button', { name: 'Regístrate' }).click();

      await expect(page.getByText('Solo falta un paso, confirma tu cuenta desde tu correo electrónico.')).toBeVisible();
    }
  );
});

// NO AUTOMATIZADAS:
// - HU-SHOP-09 (subtotal del carrito inyectado en metas de consumo distintas de "active"/
//   "discount*"): requiere mockear GoalControlService con múltiples metas y no aporta cobertura
//   de UI adicional a lo ya cubierto por el resumen de carrito (subtotal/descuento visibles).
// - HU-SHOP-16 "aviso de stock en la sucursal elegida": YA CUBIERTA. GET /inventory/pickup-stocks
//   devuelve los items STOCK completos (incluye `inventory`, ver inventory_lambda.py root ==
//   "pickup-stocks"); real-api.service.ts la descartaba al normalizar la respuesta de
//   listPickupStocks(). Se agregó listPickupStocksWithInventory() (real/mock/api.service.ts) que
//   conserva ese campo y carrito.component.ts la usa para filtrar el selector de sucursales por
//   stock del carrito — ver los 4 tests "HU-SHOP-16 / stock por sucursal: ..." arriba (caso
//   completo, parcial, ninguna sucursal con stock y falla del endpoint).
// - Bloqueo de "selecciona un método de pago" en pickup: pickupPaymentMethod tiene un valor por
//   defecto ('online') fijado en el componente y la UI siempre deja uno de los dos botones
//   seleccionado, así que ese toast es código muerto inalcanzable desde la interfaz real.
