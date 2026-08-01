import { Locator, Page } from '@playwright/test';
import { API_BASE, mockApi } from './fixtures';

/**
 * Selecciona una <option> de un <select> ui-form-field buscándola por texto parcial visible
 * (p. ej. el nombre de un stock/producto/empleado, sin depender del sufijo formateado —
 * "· CDMX", "· $100", "· correo@x.com" — que agregan los *OptionsStable getters de
 * admin.component.ts). Evita fallos por formato de moneda/Intl que `selectOption({label})`
 * exigiría como match exacto.
 */
export async function selectByVisibleText(select: Locator, partialText: string): Promise<void> {
  const value = await select.locator('option', { hasText: partialText }).first().getAttribute('value');
  if (value === null) {
    throw new Error(`selectByVisibleText: no se encontró ninguna <option> con texto "${partialText}".`);
  }
  await select.selectOption(value);
}

/**
 * Ubica el <select> de un `ui-form-field kind="select"` por el atributo `label` EXACTO,
 * evitando `getByLabel`: como el <label> interno envuelve al <select>, el nombre accesible es
 * la concatenación de "texto del label" + "texto de la opción actualmente seleccionada" (p. ej.
 * "Stock origen Stock A · CDMX"), lo que rompe tanto el match exacto (nunca es solo "Stock
 * origen") como el parcial (dos labels que empiezan igual, ej. "Stock" y "Stock origen",
 * matchean ambos con el mismo query). En cambio, `label="..."` en admin.component.html se pasa
 * siempre como string literal (no `[label]="expr"`), por lo que Angular lo deja también como
 * atributo HTML real en el custom element <ui-form-field> — se puede seleccionar por CSS attr.
 */
export function selectByExactLabel(scope: Page | Locator, label: string): Locator {
  const escaped = label.replace(/"/g, '\\"');
  return scope.locator(`ui-form-field[label="${escaped}"] select`);
}

/**
 * Mocks compartidos para el dominio Panel Admin (e2e/admin-*.spec.ts).
 * NO modifica e2e/support/fixtures.ts (protegido) — este es un módulo adicional.
 *
 * Estrategia: `mockAdminBaseline` registra respuestas vacías/neutras para TODOS los GET que el
 * panel admin puede disparar al cargar cualquier vista (evita 500 de `blockUnmockedApi` por
 * llamadas de secciones que no son el foco del test). Cada spec debe:
 *   1. await mockAdminBaseline(page, { orders: [...], ... })  // overrides puntuales
 *   2. mockApi(page, '/ruta/de/la/accion', respuesta, { method: 'POST'|'PATCH'|... })
 *   3. await blockUnmockedApi(page)  // AL FINAL, ver e2e/support/fixtures.ts
 */

/** Escapa un string para usarlo dentro de un RegExp. */
function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Regex que matchea la ruta del API sin importar el querystring (?status=...&limit=...). */
export function apiPath(pathSuffix: string): RegExp {
  return new RegExp(`^${escapeRegex(API_BASE)}${pathSuffix}`);
}

export interface AdminBaselineOverrides {
  warnings?: unknown[];
  orders?: unknown[];
  customers?: unknown[];
  products?: unknown[];
  productOfMonth?: unknown;
  categories?: unknown[];
  employees?: unknown[];
  campaigns?: unknown[];
  notifications?: unknown[];
  stocks?: unknown[];
  transfers?: unknown[];
  movements?: unknown[];
  posSales?: unknown[];
  posCashCuts?: unknown[];
  posCashControl?: Record<string, unknown>;
  businessConfig?: Record<string, unknown>;
  coupons?: unknown[];
  monthlyStats?: Record<string, unknown>;
}

/** AppBusinessConfig completo y válido (espejo de getDefaultBusinessConfig en admin.component.ts). */
export function defaultBusinessConfig(): Record<string, unknown> {
  return {
    version: 'app-v1',
    rewards: {
      version: 'v1',
      activationNetMin: 2500,
      discountTiers: [
        { min: 0, max: 999, rate: 0 },
        { min: 1000, max: 1999, rate: 0.1 },
        { min: 2000, max: 2999, rate: 0.2 },
        { min: 3000, max: 5999, rate: 0.3 },
        { min: 6000, max: null, rate: 0.4 }
      ],
      commissionLevels: [
        { gen: 1, rate: 0.1, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
        { gen: 2, rate: 0.05, reqActiveDirects: 2, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 },
        { gen: 3, rate: 0.04, reqActiveDirects: 3, reqPersonalPC: 80, reqLines: 2, reqPCPerLine: 300 },
        { gen: 4, rate: 0.03, reqActiveDirects: 4, reqPersonalPC: 120, reqLines: 3, reqPCPerLine: 450 },
        { gen: 5, rate: 0.02, reqActiveDirects: 5, reqPersonalPC: 160, reqLines: 3, reqPCPerLine: 750 }
      ],
      payoutDay: 10,
      cutRule: 'hard_cut_no_pass'
    },
    orders: { requireStockOnShipped: true, requireDispatchLinesOnShipped: true },
    pos: {
      defaultCustomerName: 'Publico en General',
      defaultPaymentStatus: 'paid_branch',
      defaultDeliveryStatus: 'delivered_branch',
      orderStatusByDeliveryStatus: { delivered_branch: 'delivered', paid_branch: 'paid' }
    },
    stocks: { requireLinkedUserForTransferReceive: true },
    adminWarnings: {
      showCommissions: true,
      showShipping: true,
      showPendingPayments: true,
      showPendingTransfers: true,
      showPosSalesToday: true
    },
    shipping: { enabled: true, markup: 0, carriers: ['dhl', 'fedex'] },
    customerDocumentTypes: [
      { key: 'constancia', label: 'Constancia de situación fiscal', required: true },
      { key: 'ine', label: 'INE (frente y reverso)', required: true },
      { key: 'curp', label: 'CURP', required: true }
    ],
    bonuses: {
      vpConfig: { mxnPerVp: 50, maxNetworkLevels: 5 },
      rankThresholds: [
        { rank: 'BRONCE', vpMin: 60, vgMin: 4500, minLines: 3, pcMinPerLine: 900, requiredLeaders: 0, requiredLeaderRank: '', monthlyBonus: 500, annualBonus: 6000 }
      ],
      rules: [
        {
          id: 'inicio_rapido',
          name: 'Bono de Inicio Rápido',
          active: true,
          conditions: [{ type: 'first_30_days' }, { type: 'vg_min', value: 600 }],
          rewards: [{ type: 'cash_mxn', amount: 5000 }],
          cooldown: 'once',
          notes: 'Primeros 30 días.'
        }
      ]
    }
  };
}

/** Registra respuestas neutras (vacías) para todos los GET del panel admin. Llamar primero. */
export async function mockAdminBaseline(page: Page, overrides: AdminBaselineOverrides = {}): Promise<void> {
  await mockApi(page, '/dashboard/admin/warnings', { warnings: overrides.warnings ?? [] }, { method: 'GET' });
  await mockApi(
    page,
    apiPath('/orders/find'),
    { orders: overrides.orders ?? [], total: (overrides.orders ?? []).length },
    { method: 'GET' }
  );
  await mockApi(
    page,
    apiPath('/customers/getall'),
    { customers: overrides.customers ?? [] },
    { method: 'GET' }
  );
  await mockApi(
    page,
    '/catalog/product',
    { products: overrides.products ?? [], productOfMonth: overrides.productOfMonth ?? null },
    { method: 'GET' }
  );
  await mockApi(page, '/catalog/categories', { categories: overrides.categories ?? [] }, { method: 'GET' });
  await mockApi(page, '/auth/employees', { employees: overrides.employees ?? [] }, { method: 'GET' });
  await mockApi(page, '/dashboard/campaigns', { campaigns: overrides.campaigns ?? [] }, { method: 'GET' });
  await mockApi(page, '/dashboard/notifications', { notifications: overrides.notifications ?? [] }, { method: 'GET' });
  await mockApi(page, '/inventory/stocks', { stocks: overrides.stocks ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/stocks/transfers'), { transfers: overrides.transfers ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/stocks/movements'), { movements: overrides.movements ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/pos/sales'), { sales: overrides.posSales ?? [] }, { method: 'GET' });
  await mockApi(page, apiPath('/inventory/pos/cash-cuts'), { cuts: overrides.posCashCuts ?? [] }, { method: 'GET' });
  await mockApi(
    page,
    apiPath('/inventory/pos/cash-control'),
    {
      control: overrides.posCashControl ?? {
        stockId: '',
        attendantUserId: null,
        currentTotal: 0,
        salesCount: 0,
        cashToKeepSuggested: 0
      }
    },
    { method: 'GET' }
  );
  await mockApi(page, '/commissions/config/app', { config: overrides.businessConfig ?? defaultBusinessConfig() }, { method: 'GET' });
  await mockApi(page, '/coupons', { coupons: overrides.coupons ?? [] }, { method: 'GET' });
  await mockApi(
    page,
    apiPath('/commissions/monthly-stats'),
    overrides.monthlyStats ?? {
      month: '2026-08',
      orders: { count: 0, total: 0, avgTicket: 0, byStatus: {}, byPaymentMethod: {}, activeCustomers: [], activeCustomerCount: 0, topCustomers: [] },
      products: { sales: [], totalUnitsSold: 0 },
      customers: { newCount: 0, activeCount: 0, repurchaseRate: 0 },
      pos: { count: 0, total: 0 },
      stocks: { summary: [], movements: [], movementsByType: {} }
    },
    { method: 'GET' }
  );
}
