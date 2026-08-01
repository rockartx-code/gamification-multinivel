import { test as base, expect, Page } from '@playwright/test';

/** Base del API real (environment.ts). Las rutas de mock se cuelgan de aquí. */
export const API_BASE = 'https://ge2omdgk33.execute-api.us-east-1.amazonaws.com/Prod';

/** Réplica del contrato AuthUser persistido por AuthService en localStorage['auth-user']. */
export interface E2EAuthUser {
  userId: string;
  name: string;
  role: 'cliente' | 'admin' | string;
  token?: string;
  canAccessAdmin?: boolean;
  isSuperUser?: boolean;
  privileges?: Record<string, boolean>;
  discountPercent?: number;
  discountActive?: boolean;
  level?: number;
}

/** Usuarios canónicos para sembrar sesión. La sesión es válida si token es no vacío. */
export const USERS: Record<'cliente' | 'admin' | 'adminLimitado', E2EAuthUser> = {
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
    // admin-001 es superusuario (AuthService.isSuperUser): pasa todos los privilegios.
    userId: 'admin-001',
    name: 'Admin',
    role: 'admin',
    token: 'e2e-fake-jwt-admin',
    canAccessAdmin: true,
    isSuperUser: true
  },
  adminLimitado: {
    userId: 'emp-e2e-002',
    name: 'Empleado Limitado',
    role: 'admin',
    token: 'e2e-fake-jwt-empleado',
    canAccessAdmin: true,
    privileges: { order_view: true }
  }
};

/**
 * Acepta de antemano el Aviso de Privacidad (modal que bloquea la app en la
 * primera visita; clave de PrivacyNoticeComponent).
 */
export async function acceptPrivacyNotice(page: Page): Promise<void> {
  await page.addInitScript(() =>
    window.localStorage.setItem('privacy-notice-accepted-v1', 'true')
  );
}

/**
 * Siembra la sesión ANTES de cargar la app (addInitScript corre antes que Angular).
 * También acepta el aviso de privacidad, salvo opts.keepPrivacyNotice.
 */
export async function seedSession(
  page: Page,
  user: E2EAuthUser,
  opts: { keepPrivacyNotice?: boolean } = {}
): Promise<void> {
  if (!opts.keepPrivacyNotice) {
    await acceptPrivacyNotice(page);
  }
  await page.addInitScript(
    (value: string) => window.localStorage.setItem('auth-user', value),
    JSON.stringify(user)
  );
}

export async function clearSession(page: Page): Promise<void> {
  await page.addInitScript(() => window.localStorage.removeItem('auth-user'));
}

export interface MockOptions {
  status?: number;
  method?: string;
  contentType?: string;
}

/**
 * Intercepta una ruta del API real y responde con `body`.
 * `path` es relativo al API (ej. '/auth/login', '/orders/*', /\/catalog.*$/).
 */
export async function mockApi(
  page: Page,
  path: string | RegExp,
  body: unknown,
  opts: MockOptions = {}
): Promise<void> {
  const matcher =
    typeof path === 'string' ? `${API_BASE}${path}` : path;
  await page.route(matcher, async (route) => {
    if (opts.method && route.request().method() !== opts.method) {
      return route.fallback();
    }
    await route.fulfill({
      status: opts.status ?? 200,
      contentType: opts.contentType ?? 'application/json',
      body: typeof body === 'string' ? body : JSON.stringify(body)
    });
  });
}

/**
 * Bloquea todo el API con 500 salvo lo mockeado explícitamente.
 * OJO: page.route evalúa handlers en orden LIFO — registra esto ANTES
 * de los mockApi específicos para que ellos tengan prioridad.
 */
export async function blockUnmockedApi(page: Page): Promise<void> {
  await page.route(`${API_BASE}/**`, (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'E2E: endpoint no mockeado', path: route.request().url() })
    })
  );
}

export const test = base;
export { expect };
