import { Page } from '@playwright/test';
import { API_BASE, mockApi } from './fixtures';

/**
 * Mocks y fixtures compartidos para el dominio Dashboard del Asociado
 * (e2e/dashboard-*.spec.ts). NO modifica e2e/support/fixtures.ts (protegido) — este es un
 * módulo adicional, siguiendo el mismo patrón que e2e/support/admin-mocks.ts.
 *
 * Fuente de verdad de shapes: src/app/models/user-dashboard.model.ts,
 * src/app/services/real-api.service.ts (getCatalogData/getDashboardData/getOrders),
 * src/app/services/user-dashboard-control.service.ts (normalización de `commissions`).
 *
 * Rutas reales que consume el dashboard autenticado (UserDashboardControlService.load):
 *   - GET {API_BASE}/catalog/catalog          -> CatalogData { products, productOfMonth }
 *   - GET {API_BASE}/customers/dashboard      -> DashboardData (goals/red/comisiones/avisos/...)
 *   - GET {API_BASE}/orders/find?customerId=&limit=&nextToken=  -> historial de órdenes
 * (GET /user-dashboard es el endpoint combinado LEGACY/@deprecated — el componente actual NO lo
 * llama; no se usa en estos tests.)
 *
 * IMPORTANTE — orden de registro de rutas: cada spec debe llamar a `blockUnmockedApi(page)`
 * ANTES de `mockDashboardEndpoints(...)`/`mockApi(...)`. Playwright evalúa los handlers de
 * page.route() en orden INVERSO de registro (el último registrado se evalúa primero); como
 * blockUnmockedApi() nunca hace route.fallback(), registrarlo DESPUÉS de los mocks específicos
 * haría que le gane a todos y siempre responda 500.
 */

/** Escapa un string para usarlo dentro de un RegExp. */
function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Regex que matchea la ruta del API sin importar el querystring (?customerId=...&limit=...). */
export function apiPath(pathSuffix: string): RegExp {
  return new RegExp(`^${escapeRegex(API_BASE)}${pathSuffix}`);
}

export function goalFixture(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    key: 'active',
    title: 'Actívate este mes',
    subtitle: 'Alcanza tu consumo neto mínimo mensual',
    target: 2500,
    base: 0,
    cart: 0,
    ctaText: 'Ir a tienda',
    ctaFragment: 'merchant',
    unit: 'mxn',
    achieved: false,
    locked: false,
    ...overrides
  };
}

export function networkMemberFixture(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'member-1',
    name: 'María González',
    level: 'L1',
    spend: 0,
    status: 'Inactiva',
    leaderId: 'cust-e2e-001',
    ...overrides
  };
}

export function notificationFixture(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'notif-1',
    title: 'Aviso del portal',
    description: 'Contenido del aviso.',
    active: true,
    startAt: '2026-07-01T00:00:00.000Z',
    endAt: '2026-12-31T23:59:59.000Z',
    createdAt: '2026-07-01T00:00:00.000Z',
    isRead: false,
    ...overrides
  };
}

export function ledgerRowFixture(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    orderId: 'ORD-0001',
    level: 1,
    amount: 100,
    status: 'confirmed',
    createdAt: '2026-07-15T10:00:00.000Z',
    ...overrides
  };
}

/** Respuesta base de GET /customers/dashboard (DashboardData). */
export function buildDashboardData(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    isGuest: false,
    settings: { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: 'CUST-E2E-001', networkGoal: 300 },
    customer: null,
    user: { level: '1', discountPercent: 30, discountActive: true },
    sponsor: null,
    goals: [],
    featured: [],
    campaigns: [],
    networkMembers: [],
    buyAgainIds: [],
    commissions: null,
    notifications: [],
    bonuses: [],
    ...overrides
  };
}

/** Respuesta base de GET /catalog/catalog (CatalogData). */
export function buildCatalogData(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    products: [],
    productOfMonth: null,
    ...overrides
  };
}

/** Respuesta base de GET /orders/find (CustomerOrdersPage cruda). */
export function buildOrdersPage(
  orders: Record<string, unknown>[] = [],
  overrides: Record<string, unknown> = {}
): Record<string, unknown> {
  return {
    orders,
    count: orders.length,
    hasMore: false,
    nextToken: null,
    ...overrides
  };
}

/**
 * Registra los 3 GET que dispara la carga del dashboard autenticado. Cada spec debe llamar
 * a esto primero y luego registrar mocks puntuales (POST clabe, POST notifications/:id/read,
 * etc.) antes de `blockUnmockedApi(page)`.
 */
export async function mockDashboardEndpoints(
  page: Page,
  opts: {
    dashboard?: Record<string, unknown>;
    catalog?: Record<string, unknown>;
    orders?: Record<string, unknown>[];
    dashboardStatus?: number;
  } = {}
): Promise<void> {
  await mockApi(page, '/catalog/catalog', opts.catalog ?? buildCatalogData());
  await mockApi(page, '/customers/dashboard', opts.dashboard ?? buildDashboardData(), {
    status: opts.dashboardStatus ?? 200
  });
  await mockApi(page, apiPath('/orders/find'), buildOrdersPage(opts.orders ?? []));
}
