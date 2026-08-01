/**
 * Script standalone (Node + Playwright API directa, sin test-runner) para capturar screenshots
 * de las pantallas principales de Finding'U con datos mockeados, como insumo del análisis de
 * UI/UX en docs/ux/analisis-ui-ux-2026-08.md.
 *
 * NO modifica nada de e2e/ ni de la app: solo lee sus contratos (fixtures.ts, dashboard-mocks.ts,
 * admin-mocks.ts) para replicar shapes de datos localmente.
 *
 * Uso: node docs/ux/capture-screens.js
 * Requiere: app ya corriendo en http://localhost:4300 (no la levanta).
 */
const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:4300';
const API_BASE = 'https://ge2omdgk33.execute-api.us-east-1.amazonaws.com/Prod';
const OUT_DIR = path.join(__dirname, 'img');

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const USERS = {
  cliente: {
    userId: 'cust-e2e-001',
    name: 'Cliente E2E',
    role: 'cliente',
    token: 'e2e-fake-jwt-cliente',
    discountPercent: 30,
    discountActive: true,
    level: 1
  },
  admin: {
    userId: 'admin-001',
    name: 'Admin',
    role: 'admin',
    token: 'e2e-fake-jwt-admin',
    canAccessAdmin: true,
    isSuperUser: true
  }
};

async function acceptPrivacyNotice(page) {
  await page.addInitScript(() => window.localStorage.setItem('privacy-notice-accepted-v1', 'true'));
}

async function seedSession(page, user) {
  await acceptPrivacyNotice(page);
  await page.addInitScript((value) => window.localStorage.setItem('auth-user', value), JSON.stringify(user));
}

async function mockApi(page, urlPattern, body, opts = {}) {
  const matcher = typeof urlPattern === 'string' ? `${API_BASE}${urlPattern}` : urlPattern;
  await page.route(matcher, async (route) => {
    if (opts.method && route.request().method() !== opts.method) return route.fallback();
    await route.fulfill({
      status: opts.status ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(body)
    });
  });
}

async function blockUnmockedApi(page) {
  await page.route(`${API_BASE}/**`, (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ message: 'no mockeado' }) })
  );
}

function apiPath(suffix) {
  return new RegExp(`^${API_BASE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}${suffix}`);
}

// ---------- Fixtures de catálogo / productos ----------
const PRODUCTS = [
  {
    id: 'prod-colageno', productId: 'prod-colageno', name: 'Colágeno Hidrolizado', price: 590,
    badge: 'Bienestar', img: 'images/colageno.png', images: [{ section: 'miniatura', url: 'images/colageno.png' }],
    vpPoints: 10, tags: ['energia', 'recuperacion'], categoryIds: ['cat-suplementos'], inOnlineStore: true, variants: []
  },
  {
    id: 'prod-magnesio', productId: 'prod-magnesio', name: 'Magnesio Quelado', price: 420,
    badge: 'Energía', img: 'images/magnesio.png', images: [{ section: 'miniatura', url: 'images/magnesio.png' }],
    vpPoints: 6, tags: ['energia'], categoryIds: ['cat-minerales'], inOnlineStore: true, variants: []
  },
  {
    id: 'prod-te-relax', productId: 'prod-te-relax', name: 'Té Relax', price: 150,
    badge: 'Nuevo', img: 'images/te.png', images: [{ section: 'miniatura', url: 'images/te.png' }],
    vpPoints: 3, tags: ['relajacion'], categoryIds: ['cat-suplementos'], inOnlineStore: true, variants: []
  },
  {
    id: 'prod-vitamina-c', productId: 'prod-vitamina-c', name: 'Vitamina C', price: 280,
    badge: '', img: 'images/vitamina.png', images: [{ section: 'miniatura', url: 'images/vitamina.png' }],
    vpPoints: 5, tags: ['inmunidad'], categoryIds: ['cat-minerales'], inOnlineStore: true, variants: []
  },
  {
    id: 'prod-omega-3', productId: 'prod-omega-3', name: 'Omega 3', price: 350,
    badge: '', img: 'images/omega.png', images: [{ section: 'miniatura', url: 'images/omega.png' }],
    vpPoints: 4, tags: ['cardiovascular'], categoryIds: ['cat-suplementos'], inOnlineStore: true, variants: []
  }
];

const CATEGORIES = [
  { id: 'cat-suplementos', name: 'Suplementos', active: true },
  { id: 'cat-minerales', name: 'Minerales', active: true }
];

const SAVED_ADDRESS = {
  id: 'addr-1', label: 'Casa', recipientName: 'Cliente E2E', phone: '5555555555',
  street: 'Av Reforma', number: '100', address: 'Av Reforma 100, CDMX', city: 'CDMX',
  postalCode: '06600', state: 'CMX', country: 'MX', isDefault: true
};

const PICKUP_STOCKS = [
  { id: 'stock-centro', name: 'Sucursal Centro', location: 'CDMX Centro' },
  { id: 'stock-norte', name: 'Sucursal Norte', location: 'CDMX Norte' }
];

function dashboardSettings(overrides = {}) {
  return { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: 'CUST-E2E-001', networkGoal: 300, ...overrides };
}

function richDashboardData() {
  return {
    isGuest: false,
    settings: dashboardSettings(),
    customer: {
      id: 'cust-e2e-001', name: 'Cliente E2E', phone: '5555555555',
      addresses: [SAVED_ADDRESS], defaultAddressId: 'addr-1',
      shippingAddresses: [SAVED_ADDRESS], defaultShippingAddressId: 'addr-1'
    },
    user: { level: '2', discountPercent: 30, discountActive: true },
    sponsor: { name: 'Laura Méndez', userCode: 'SP-001' },
    goals: [
      { key: 'active', title: 'Actívate este mes', subtitle: 'Alcanza tu consumo neto mínimo mensual', target: 2500, base: 1800, cart: 0, ctaText: 'Ir a tienda', ctaFragment: 'merchant', unit: 'mxn', achieved: false, locked: false },
      { key: 'network', title: 'Meta de red', subtitle: 'Ayuda a 3 personas de tu red a activarse', target: 3, base: 1, cart: 0, ctaText: 'Ver mi red', ctaFragment: 'red', unit: 'personas', achieved: false, locked: false }
    ],
    featured: [PRODUCTS[0], PRODUCTS[1]],
    campaigns: [],
    networkMembers: [
      { id: 'member-1', name: 'María González', level: 'L1', spend: 1200, status: 'Activa', leaderId: 'cust-e2e-001' },
      { id: 'member-2', name: 'Carlos Ruiz', level: 'L1', spend: 0, status: 'Inactiva', leaderId: 'cust-e2e-001' },
      { id: 'member-3', name: 'Ana Torres', level: 'L2', spend: 800, status: 'Activa', leaderId: 'member-1' }
    ],
    buyAgainIds: ['prod-colageno'],
    commissions: {
      monthKey: '2026-07', monthTotal: 1800, pendingTotal: 600, blockedTotal: 0, paidTotal: 1200,
      hasPending: true, hasConfirmed: true, clabeOnFile: true, clabeLast4: '4321',
      prevStatus: 'paid', payoutDay: 10,
      ledger: [
        { orderId: 'ORD-C1', level: 1, amount: 400, status: 'confirmed', createdAt: '2026-07-15T10:00:00.000Z' },
        { orderId: 'ORD-C2', level: 2, amount: 200, status: 'pending', createdAt: '2026-07-20T10:00:00.000Z' }
      ]
    },
    notifications: [
      { id: 'notif-1', title: 'Aviso del portal', description: 'Nuevo bono disponible este mes.', active: true, startAt: '2026-07-01T00:00:00.000Z', endAt: '2026-12-31T23:59:59.000Z', createdAt: '2026-07-01T00:00:00.000Z', isRead: true }
    ],
    bonuses: []
  };
}

function tiendaDashboardData() {
  return {
    settings: dashboardSettings({ userCode: '' }),
    goals: [],
    products: PRODUCTS,
    featured: [PRODUCTS[0]],
    campaigns: [],
    categories: CATEGORIES,
    networkMembers: [],
    buyAgainIds: [],
    productOfMonth: null
  };
}

function clienteDashboardDataForCart() {
  return {
    isGuest: false,
    settings: dashboardSettings({ userCode: '' }),
    customer: {
      id: 'cust-e2e-001', name: 'Cliente E2E', phone: '5555555555',
      addresses: [SAVED_ADDRESS], defaultAddressId: 'addr-1',
      shippingAddresses: [SAVED_ADDRESS], defaultShippingAddressId: 'addr-1'
    },
    user: { discountPercent: 30, discountActive: true },
    sponsor: null, goals: [], featured: [], campaigns: [], networkMembers: [], buyAgainIds: [],
    commissions: null, notifications: []
  };
}

function baseOrder(overrides = {}) {
  return {
    id: 'ORD-9001', createdAt: '2026-07-15T10:00:00Z', customer: 'Cliente E2E',
    grossSubtotal: 590, discountRate: 0.1, discountAmount: 59, netTotal: 531, total: 531,
    status: 'paid', items: [{ productId: 1, name: 'Colágeno Hidrolizado', price: 590, quantity: 1 }],
    deliveryType: 'delivery',
    ...overrides
  };
}

function defaultBusinessConfig() {
  return {
    version: 'app-v1',
    rewards: {
      version: 'v1', activationNetMin: 20,
      discountTiers: [
        { min: 0, max: 999, rate: 0 }, { min: 1000, max: 1999, rate: 0.1 }, { min: 2000, max: 2999, rate: 0.2 },
        { min: 3000, max: 5999, rate: 0.3 }, { min: 6000, max: null, rate: 0.4 }
      ],
      commissionLevels: [
        { gen: 1, rate: 0.1, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
        { gen: 2, rate: 0.05, reqActiveDirects: 2, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
        { gen: 3, rate: 0.04, reqActiveDirects: 3, reqPersonalPC: 80, reqLines: 2, reqPCPerLine: 300 },
        { gen: 4, rate: 0.03, reqActiveDirects: 4, reqPersonalPC: 120, reqLines: 3, reqPCPerLine: 450 },
        { gen: 5, rate: 0.02, reqActiveDirects: 5, reqPersonalPC: 160, reqLines: 3, reqPCPerLine: 750 }
      ],
      payoutDay: 10, cutRule: 'hard_cut_no_pass'
    },
    orders: { requireStockOnShipped: true, requireDispatchLinesOnShipped: true },
    pos: {
      defaultCustomerName: 'Publico en General', defaultPaymentStatus: 'paid_branch', defaultDeliveryStatus: 'delivered_branch',
      orderStatusByDeliveryStatus: { delivered_branch: 'delivered', paid_branch: 'paid' }
    },
    stocks: { requireLinkedUserForTransferReceive: true },
    adminWarnings: { showCommissions: true, showShipping: true, showPendingPayments: true, showPendingTransfers: true, showPosSalesToday: true },
    shipping: { enabled: true, markup: 0, carriers: ['dhl', 'fedex'] },
    customerDocumentTypes: [
      { key: 'constancia', label: 'Constancia de situación fiscal', required: true },
      { key: 'ine', label: 'INE (frente y reverso)', required: true },
      { key: 'curp', label: 'CURP', required: true }
    ],
    bonuses: {
      vpConfig: { mxnPerVp: 50, maxNetworkLevels: 5 },
      rankThresholds: [{ rank: 'BRONCE', vpMin: 60, vgMin: 4500, minLines: 3, pcMinPerLine: 900, requiredLeaders: 0, requiredLeaderRank: '', monthlyBonus: 500, annualBonus: 6000 }],
      rules: [{ id: 'inicio_rapido', name: 'Bono de Inicio Rápido', active: true, conditions: [{ type: 'first_30_days' }, { type: 'vg_min', value: 600 }], rewards: [{ type: 'cash_mxn', amount: 5000 }], cooldown: 'once', notes: 'Primeros 30 días.' }]
    }
  };
}

const ADMIN_CUSTOMERS = [
  { id: 1, name: 'Ana Pérez', email: 'ana.perez@e2e.test', phone: '5551112222', level: 1, discountPercent: 10, discountActive: true, orderCount: 4, netTotal: 3200, status: 'active' },
  { id: 2, name: 'Bruno Silva', email: 'bruno.silva@e2e.test', phone: '5553334444', level: 2, discountPercent: 20, discountActive: true, orderCount: 9, netTotal: 8100, status: 'active' },
  { id: 3, name: 'Carla Díaz', email: 'carla.diaz@e2e.test', phone: '5555556666', level: 1, discountPercent: 0, discountActive: false, orderCount: 0, netTotal: 0, status: 'inactive' }
];

const ADMIN_ORDERS = [
  { id: 'ORD-9001', createdAt: '2026-07-15T10:00:00Z', customer: 'Ana Pérez', total: 531, netTotal: 531, status: 'paid', deliveryType: 'delivery', items: [{ productId: 1, name: 'Colágeno Hidrolizado', price: 590, quantity: 1 }] },
  { id: 'ORD-9002', createdAt: '2026-07-16T10:00:00Z', customer: 'Bruno Silva', total: 990, netTotal: 990, status: 'shipped', deliveryType: 'carrier', trackingNumber: 'GUIA-123', items: [{ productId: 2, name: 'Magnesio Quelado', price: 420, quantity: 2 }] },
  { id: 'ORD-9003', createdAt: '2026-07-17T10:00:00Z', customer: 'Carla Díaz', total: 150, netTotal: 150, status: 'pending', deliveryType: 'pickup', items: [{ productId: 3, name: 'Té Relax', price: 150, quantity: 1 }] },
  { id: 'ORD-9004', createdAt: '2026-07-10T10:00:00Z', customer: 'Ana Pérez', total: 280, netTotal: 280, status: 'delivered', deliveryType: 'delivery', items: [{ productId: 4, name: 'Vitamina C', price: 280, quantity: 1 }] },
  { id: 'ORD-9005', createdAt: '2026-07-05T10:00:00Z', customer: 'Bruno Silva', total: 350, netTotal: 350, status: 'cancelled', deliveryType: 'delivery', items: [{ productId: 5, name: 'Omega 3', price: 350, quantity: 1 }] }
];

const ADMIN_PRODUCTS = PRODUCTS.map((p) => ({ ...p, id: p.id, stockQty: 40, active: true }));

const ADMIN_STOCKS = [
  { id: 'stock-centro', name: 'Stock A', location: 'CDMX', active: true },
  { id: 'stock-norte', name: 'Stock B', location: 'GDL', active: true }
];

async function mockAdminBaseline(page, overrides = {}) {
  await mockApi(page, '/dashboard/admin/warnings', { warnings: overrides.warnings ?? [
    { id: 'w1', type: 'pending_payments', message: '3 pedidos con pago pendiente.' },
    { id: 'w2', type: 'pending_transfers', message: '1 transferencia de stock por confirmar.' }
  ] }, { method: 'GET' });
  await mockApi(page, apiPath('/orders/find'), { orders: overrides.orders ?? ADMIN_ORDERS, total: (overrides.orders ?? ADMIN_ORDERS).length }, { method: 'GET' });
  await mockApi(page, apiPath('/customers/getall'), { customers: overrides.customers ?? ADMIN_CUSTOMERS }, { method: 'GET' });
  await mockApi(page, '/catalog/product', { products: overrides.products ?? ADMIN_PRODUCTS, productOfMonth: overrides.productOfMonth ?? null }, { method: 'GET' });
  await mockApi(page, '/catalog/categories', { categories: overrides.categories ?? CATEGORIES }, { method: 'GET' });
  await mockApi(page, '/auth/employees', { employees: overrides.employees ?? [] }, { method: 'GET' });
  await mockApi(page, '/dashboard/campaigns', { campaigns: overrides.campaigns ?? [] }, { method: 'GET' });
  await mockApi(page, '/dashboard/notifications', { notifications: overrides.notifications ?? [] }, { method: 'GET' });
  await mockApi(page, '/inventory/stocks', { stocks: overrides.stocks ?? ADMIN_STOCKS }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/stocks/transfers'), { transfers: overrides.transfers ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/stocks/movements'), { movements: overrides.movements ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/pos/sales'), { sales: overrides.posSales ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/pos/cash-cuts'), { cuts: overrides.posCashCuts ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/pos/cash-control'), { control: overrides.posCashControl ?? { stockId: 'stock-centro', attendantUserId: null, currentTotal: 0, salesCount: 0, cashToKeepSuggested: 0 } }, { method: 'GET' });
  await mockApi(page, '/commissions/config/app', { config: overrides.businessConfig ?? defaultBusinessConfig() }, { method: 'GET' });
  await mockApi(page, '/coupons', { coupons: overrides.coupons ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/commissions/monthly-stats'), overrides.monthlyStats ?? {
    month: '2026-07',
    orders: { count: 12, total: 8400, avgTicket: 700, byStatus: { paid: 5, shipped: 3, pending: 2, delivered: 1, cancelled: 1 }, byPaymentMethod: {}, activeCustomers: [], activeCustomerCount: 6, topCustomers: [] },
    products: { sales: [], totalUnitsSold: 24 },
    customers: { newCount: 3, activeCount: 6, repurchaseRate: 0.4 },
    pos: { count: 4, total: 1200 },
    stocks: { summary: [], movements: [], movementsByType: {} }
  }, { method: 'GET' });
}

// ---------- Runner ----------
const VIEWPORTS = {
  desktop: { width: 1366, height: 768 },
  mobile: { width: 390, height: 844 }
};

// Prefijo opcional (p. ej. SHOT_PREFIX=after- node docs/ux/capture-screens.js) para regenerar
// capturas "después" de un cambio sin sobrescribir las originales usadas como referencia "antes".
const SHOT_PREFIX = process.env.SHOT_PREFIX || '';

async function shoot(page, name, viewportKey, fullPage = true) {
  const file = path.join(OUT_DIR, `${SHOT_PREFIX}${name}-${viewportKey}.png`);
  await page.screenshot({ path: file, fullPage });
  console.log('captured', file);
}

async function withPage(browser, viewportKey, fn) {
  const context = await browser.newContext({ viewport: VIEWPORTS[viewportKey] });
  const page = await context.newPage();
  try {
    await fn(page);
  } catch (err) {
    console.error('ERROR in scenario for viewport', viewportKey, err);
  } finally {
    await context.close();
  }
}

async function captureLanding(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, apiPath('/auth/sponsor'), { name: 'Laura Méndez', userCode: 'SP-001' }, { method: 'GET' });
    await page.goto(`${BASE_URL}/#/landing/1`);
    await page.waitForTimeout(800);
    await shoot(page, '01-landing', viewportKey);
  });
}

async function captureLogin(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await page.goto(`${BASE_URL}/#/login`);
    await page.waitForTimeout(500);
    await shoot(page, '02-login', viewportKey);
  });
}

async function captureTienda(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, apiPath('/user-dashboard'), tiendaDashboardData(), { method: 'GET' });
    await page.goto(`${BASE_URL}/#/tienda`);
    await page.waitForTimeout(800);
    await shoot(page, '03-tienda', viewportKey);
  });
}

async function captureCarrito(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await blockUnmockedApi(page);
    await seedSession(page, USERS.cliente);
    const cartItems = [
      { id: 'prod-colageno', name: 'Colágeno Hidrolizado', price: 590, qty: 1, note: '', img: 'images/colageno.png' },
      { id: 'prod-magnesio', name: 'Magnesio Quelado', price: 420, qty: 2, note: '', img: 'images/magnesio.png' }
    ];
    await page.addInitScript((items) => window.localStorage.setItem('cart-items', JSON.stringify(items)), cartItems);
    await mockApi(page, '/catalog/catalog', { products: PRODUCTS, productOfMonth: null }, { method: 'GET' });
    await mockApi(page, /\/inventory\/pickup-stocks/, { stocks: PICKUP_STOCKS }, { method: 'GET' });
    await mockApi(page, /\/customers\/dashboard/, clienteDashboardDataForCart(), { method: 'GET' });
    await mockApi(page, '/shipping/quote', { rates: [
      { carrier: 'Estafeta', service: 'Terrestre', price: 120, displayPrice: 120, currency: 'MXN', transitDays: 3, deliveryEstimate: '3-5 días' },
      { carrier: 'DHL', service: 'Express', price: 220, displayPrice: 220, currency: 'MXN', transitDays: 1, deliveryEstimate: '1-2 días' }
    ] }, { method: 'POST' });
    await page.goto(`${BASE_URL}/#/carrito`);
    await page.waitForTimeout(800);
    // Llenar el formulario de entrega para capturar el estado "con items y formulario".
    try {
      await page.getByLabel('Nombre', { exact: true }).fill('Ana Pérez');
      await page.getByLabel('Teléfono', { exact: true }).fill('5512345678');
      await page.getByLabel('Calle', { exact: true }).fill('Av. Reforma');
      await page.getByLabel('Número', { exact: true }).fill('123');
      await page.getByLabel('Ciudad', { exact: true }).fill('Ciudad de México');
      await page.getByLabel('CP', { exact: true }).fill('06600');
      await page.getByLabel('Estado').selectOption({ label: 'Ciudad de Mexico' });
      await page.getByLabel('Pais').selectOption({ label: 'Mexico' });
      await page.waitForTimeout(600);
    } catch (err) {
      console.error('cart form fill failed', err.message);
    }
    await shoot(page, '04-carrito', viewportKey);
  });
}

async function captureDashboard(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, '/catalog/catalog', { products: PRODUCTS, productOfMonth: null }, { method: 'GET' });
    await mockApi(page, '/customers/dashboard', richDashboardData(), { method: 'GET' });
    await mockApi(page, apiPath('/orders/find'), { orders: [
      { id: 'ORD-8001', createdAt: '2026-07-20T10:00:00Z', customer: 'Cliente E2E', total: 590, netTotal: 590, status: 'delivered', deliveryType: 'delivery', items: [{ productId: 1, name: 'Colágeno Hidrolizado', price: 590, quantity: 1 }] }
    ], count: 1, hasMore: false, nextToken: null }, { method: 'GET' });
    await page.goto(`${BASE_URL}/#/dashboard`);
    await page.waitForTimeout(1000);
    await shoot(page, '05-dashboard', viewportKey);
  });
}

async function capturePerfil(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, '/catalog/catalog', { products: PRODUCTS, productOfMonth: null }, { method: 'GET' });
    await mockApi(page, '/customers/dashboard', richDashboardData(), { method: 'GET' });
    await mockApi(page, apiPath('/orders/find'), { orders: [], count: 0, hasMore: false, nextToken: null }, { method: 'GET' });
    await page.goto(`${BASE_URL}/#/perfil`);
    await page.waitForTimeout(800);
    await shoot(page, '06-perfil', viewportKey);
  });
}

async function captureOrderStatus(browser, viewportKey) {
  await withPage(browser, viewportKey, async (page) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/orders/ORD-9001', { order: baseOrder({ status: 'paid' }) }, { method: 'GET' });
    await page.goto(`${BASE_URL}/#/orden/ORD-9001`);
    await page.waitForTimeout(800);
    await shoot(page, '07-order-status', viewportKey);
  });
}

async function captureAdminView(browser, viewportKey, viewLabel, screenName, extra, mobileLabel) {
  await withPage(browser, viewportKey, async (page) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);
    if (extra) await extra(page);
    await page.goto(`${BASE_URL}/#/admin`);
    await page.waitForTimeout(1000);
    if (viewLabel !== 'Pedidos') {
      const isDesktop = viewportKey === 'desktop';
      // 2026-08-01: la navegación admin en móvil ya no es #bottomBar (barra fija de 11-12
      // botones, ~41% del viewport) sino un hamburguesa + ui-sidebar-nav flotante, igual que en
      // user-dashboard.component.html — ambos ahora comparten las mismas etiquetas completas
      // (ya no hay abreviaturas tipo "PV"/"Config" solo para móvil).
      const label = isDesktop ? viewLabel : (mobileLabel ?? viewLabel);
      if (!isDesktop) {
        await page.getByRole('button', { name: 'Navegación' }).click();
        await page.waitForTimeout(200);
      }
      const btn = isDesktop
        ? page.locator('aside').first().getByRole('button', { name: label, exact: true })
        : page.locator('div.lg\\:hidden ui-sidebar-nav').getByRole('button', { name: label, exact: true });
      try {
        await btn.click({ timeout: 5000 });
        await page.waitForTimeout(800);
      } catch (err) {
        console.error(`admin nav click failed for ${viewLabel}`, err.message);
      }
    }
    await shoot(page, screenName, viewportKey);
  });
}

async function main() {
  const browser = await chromium.launch();
  const scenarios = [
    ['landing', captureLanding],
    ['login', captureLogin],
    ['tienda', captureTienda],
    ['carrito', captureCarrito],
    ['dashboard', captureDashboard],
    ['perfil', capturePerfil],
    ['order-status', captureOrderStatus]
  ];

  for (const viewportKey of Object.keys(VIEWPORTS)) {
    for (const [label, fn] of scenarios) {
      console.log(`--- ${label} (${viewportKey}) ---`);
      await fn(browser, viewportKey);
    }
    await captureAdminView(browser, viewportKey, 'Pedidos', '08-admin-pedidos');
    await captureAdminView(browser, viewportKey, 'Clientes', '09-admin-clientes');
    await captureAdminView(browser, viewportKey, 'Productos', '10-admin-catalogo');
    await captureAdminView(browser, viewportKey, 'Punto de Venta', '11-admin-pos');
    await captureAdminView(browser, viewportKey, 'Configuracion', '12-admin-configuracion');
  }

  await browser.close();
  console.log('DONE');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
