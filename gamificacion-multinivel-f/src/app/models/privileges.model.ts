export type AdminViewId =
  | 'orders'
  | 'customers'
  | 'products'
  | 'stocks'
  | 'campaigns'
  | 'pos'
  | 'stats'
  | 'honor_board'
  | 'notifications'
  | 'settings'
  | 'employees'
  | 'coupons';

export type AppPrivilege =
  | 'access_screen_orders'
  | 'access_screen_customers'
  | 'access_screen_products'
  | 'access_screen_stocks'
  | 'access_screen_pos'
  | 'access_screen_stats'
  | 'access_screen_settings'
  | 'order_mark_paid'
  | 'order_mark_shipped'
  | 'order_mark_delivered'
  | 'order_create'
  | 'customer_add'
  | 'commissions_register_payment'
  | 'product_add'
  | 'product_update'
  | 'product_delete'
  | 'product_set_month'
  | 'stock_create'
  | 'stock_create_transfer'
  | 'stock_add_inventory'
  | 'stock_mark_damaged'
  | 'stock_receive_transfer'
  | 'pos_register_sale'
  | 'user_mark_admin'
  | 'user_manage_privileges'
  | 'employee_add'
  | 'employee_manage_privileges'
  | 'access_screen_employees'
  | 'config_manage'
  | 'access_screen_honor_board'
  // paquete E · ronda 26: Campañas deja de colgar del privilegio de Stocks.
  | 'access_screen_campaigns';

export type UserPrivileges = Partial<Record<AppPrivilege, boolean>>;

export const ALL_PRIVILEGES: AppPrivilege[] = [
  'access_screen_orders',
  'access_screen_customers',
  'access_screen_products',
  'access_screen_stocks',
  'access_screen_pos',
  'access_screen_stats',
  'access_screen_settings',
  'order_mark_paid',
  'order_mark_shipped',
  'order_mark_delivered',
  'order_create',
  'customer_add',
  'commissions_register_payment',
  'product_add',
  'product_update',
  'product_delete',
  'product_set_month',
  'stock_create',
  'stock_create_transfer',
  'stock_add_inventory',
  'stock_mark_damaged',
  'stock_receive_transfer',
  'pos_register_sale',
  'user_mark_admin',
  'user_manage_privileges',
  'employee_add',
  'employee_manage_privileges',
  'access_screen_employees',
  'config_manage',
  'access_screen_honor_board',
  'access_screen_campaigns' // paquete E · ronda 26
];

export const SCREEN_PRIVILEGE_BY_VIEW: Record<AdminViewId, AppPrivilege> = {
  orders: 'access_screen_orders',
  customers: 'access_screen_customers',
  products: 'access_screen_products',
  stocks: 'access_screen_stocks',
  campaigns: 'access_screen_campaigns',
  pos: 'access_screen_pos',
  stats: 'access_screen_stats',
  honor_board: 'access_screen_honor_board',
  notifications: 'config_manage',
  settings: 'access_screen_settings',
  employees: 'access_screen_employees',
  coupons: 'config_manage'
};

export function normalizePrivileges(raw: unknown): UserPrivileges {
  const source = (raw ?? {}) as Record<string, unknown>;
  const normalized: UserPrivileges = {};
  for (const privilege of ALL_PRIVILEGES) {
    normalized[privilege] = source[privilege] === true;
  }
  return normalized;
}

// ── Paquete E · ronda 26 ──
// Todo el back office vivía en una sola ruta, `#/admin`: nadie podía mandar un
// enlace ("tendría que contestarle: en Clientes, hasta abajo, después de los
// documentos") ni volver a su pantalla al recargar. Cada vista estrena URL.

/** Ruta explícita de cada vista del back office. Una sola tabla: el menú lateral,
 *  la barra inferior móvil y el aterrizaje por puesto leen de aquí. */
export const ADMIN_ROUTE_BY_VIEW: Record<AdminViewId, string> = {
  orders: '/admin/pedidos',
  customers: '/admin/clientes',
  products: '/admin/productos',
  stocks: '/admin/stocks',
  campaigns: '/admin/campanas',
  pos: '/admin/pos',
  stats: '/admin/estadisticas',
  honor_board: '/admin/cuadro-de-honor',
  notifications: '/admin/avisos',
  settings: '/admin/configuracion',
  employees: '/admin/empleados',
  coupons: '/admin/cupones'
};

/** Pantallas del back office que son componentes aparte, con su privilegio. */
export const ADMIN_EXTRA_ROUTE_PRIVILEGE: Record<string, AppPrivilege> = {
  '/admin/comisiones': 'commissions_register_payment',
  '/admin/despacho': 'access_screen_orders',
  '/admin/resumen-turno': 'access_screen_stocks',
  '/admin/seguimiento': 'access_screen_customers'
};

function tiene(privileges: UserPrivileges | undefined, privilege: AppPrivilege): boolean {
  return privileges?.[privilege] === true;
}

/**
 * Dónde abre el panel según lo que la persona hace de verdad.
 *
 * `getFirstAllowedView()` recorría una lista fija que empezaba en Pedidos, y los
 * cinco empleados tienen `access_screen_orders`: los cinco caían en Pedidos.
 * Toño leyó a la vez "Pagados 3" y "0 pedidos — No hay pedidos en este estado".
 *
 * El orden lo fija §3.5 del contrato de la ronda, con una precisión: gerencia y
 * superadmin (quien administra privilegios) abren en Pedidos aunque tengan los
 * privilegios de almacén, porque los tienen todos.
 */
export function landingRouteFor(privileges: UserPrivileges | undefined, isSuperUser = false): string {
  if (isSuperUser || tiene(privileges, 'user_manage_privileges') || tiene(privileges, 'employee_manage_privileges')) {
    return ADMIN_ROUTE_BY_VIEW.orders;
  }
  if (tiene(privileges, 'pos_register_sale') && !tiene(privileges, 'access_screen_stats')) {
    return ADMIN_ROUTE_BY_VIEW.pos;
  }
  if (tiene(privileges, 'stock_receive_transfer') || tiene(privileges, 'stock_add_inventory')) {
    return '/admin/despacho';
  }
  if (tiene(privileges, 'access_screen_customers') && !tiene(privileges, 'commissions_register_payment')) {
    return '/admin/seguimiento';
  }
  if (tiene(privileges, 'commissions_register_payment')) {
    return '/admin/comisiones';
  }
  return ADMIN_ROUTE_BY_VIEW.orders;
}

/** Privilegio que exige una ruta del back office, sea vista o pantalla aparte. */
export function privilegeForAdminRoute(route: string): AppPrivilege | null {
  const extra = ADMIN_EXTRA_ROUTE_PRIVILEGE[route];
  if (extra) {
    return extra;
  }
  const view = (Object.keys(ADMIN_ROUTE_BY_VIEW) as AdminViewId[]).find((v) => ADMIN_ROUTE_BY_VIEW[v] === route);
  return view ? SCREEN_PRIVILEGE_BY_VIEW[view] : null;
}

// ── Paquete E · ronda 26 · El menú del back office, escrito UNA sola vez ─────
// Vivía dentro de `AdminComponent`, así que las dos pantallas que son
// componentes aparte (Despacho en bloque y Seguimiento de hoy) no tenían menú
// —y son justo donde empiezan su día el de almacén y la coach—. Aquí es una
// tabla pura que cualquiera puede montar.

/**
 * Una entrada del menú: su URL, la vista que monta (si vive dentro del
 * caparazón) y el privilegio que exige.
 */
export type AdminMenuEntry = {
  id: string;
  icon: string;
  label: string;
  /** Nombre corto para la barra inferior del móvil, donde no cabe el largo. */
  short: string;
  route: string;
  view?: AdminViewId;
};

export const ADMIN_MENU_GROUPS: ReadonlyArray<{ label: string; links: AdminMenuEntry[] }> = [
  {
    label: 'Operación diaria',
    links: [
      { id: 'orders', view: 'orders', route: ADMIN_ROUTE_BY_VIEW.orders, icon: 'fa-receipt', label: 'Pedidos', short: 'Pedidos' },
      { id: 'despacho', route: '/admin/despacho', icon: 'fa-boxes-packing', label: 'Despacho en bloque', short: 'Despacho' },
      { id: 'pos', view: 'pos', route: ADMIN_ROUTE_BY_VIEW.pos, icon: 'fa-cash-register', label: 'Punto de Venta', short: 'PV' },
      { id: 'stocks', view: 'stocks', route: ADMIN_ROUTE_BY_VIEW.stocks, icon: 'fa-warehouse', label: 'Stocks', short: 'Stocks' },
      { id: 'resumen-turno', route: '/admin/resumen-turno', icon: 'fa-clipboard-check', label: 'Resumen de turno', short: 'Turno' }
    ]
  },
  {
    label: 'Personas',
    links: [
      { id: 'customers', view: 'customers', route: ADMIN_ROUTE_BY_VIEW.customers, icon: 'fa-users', label: 'Clientes', short: 'Clientes' },
      { id: 'seguimiento', route: '/admin/seguimiento', icon: 'fa-headset', label: 'Seguimiento de hoy', short: 'Seguimiento' },
      { id: 'employees', view: 'employees', route: ADMIN_ROUTE_BY_VIEW.employees, icon: 'fa-id-badge', label: 'Empleados', short: 'Empleados' }
    ]
  },
  {
    label: 'Finanzas',
    links: [
      { id: 'comisiones', route: '/admin/comisiones', icon: 'fa-hand-holding-dollar', label: 'Comisiones y pagos', short: 'Comisiones' }
    ]
  },
  {
    label: 'Catálogo y oferta',
    links: [
      { id: 'products', view: 'products', route: ADMIN_ROUTE_BY_VIEW.products, icon: 'fa-boxes-stacked', label: 'Productos', short: 'Productos' },
      { id: 'campaigns', view: 'campaigns', route: ADMIN_ROUTE_BY_VIEW.campaigns, icon: 'fa-bullhorn', label: 'Campañas', short: 'Campañas' },
      { id: 'coupons', view: 'coupons', route: ADMIN_ROUTE_BY_VIEW.coupons, icon: 'fa-ticket', label: 'Cupones', short: 'Cupones' }
    ]
  },
  {
    label: 'Reportes y avisos',
    links: [
      { id: 'stats', view: 'stats', route: ADMIN_ROUTE_BY_VIEW.stats, icon: 'fa-chart-line', label: 'Estadísticas', short: 'Estadísticas' },
      { id: 'honor_board', view: 'honor_board', route: ADMIN_ROUTE_BY_VIEW.honor_board, icon: 'fa-ranking-star', label: 'Cuadro de Honor', short: 'Honor' },
      { id: 'notifications', view: 'notifications', route: ADMIN_ROUTE_BY_VIEW.notifications, icon: 'fa-bell', label: 'Notificaciones', short: 'Avisos' }
    ]
  },
  {
    label: 'Sistema',
    links: [
      { id: 'settings', view: 'settings', route: ADMIN_ROUTE_BY_VIEW.settings, icon: 'fa-sliders', label: 'Configuración', short: 'Configuración' }
    ]
  }
];

/**
 * Los grupos del menú con solo las entradas que esta persona puede abrir.
 *
 * El privilegio sale SIEMPRE de `privilegeForAdminRoute`, la misma tabla que
 * usa la guarda de la URL (§3.5): el menú pedía `order_mark_shipped` para
 * "Despacho en bloque" y la guarda `access_screen_orders`, así que la cajera no
 * veía la entrada y la pantalla se le abría escribiendo la dirección.
 */
export function adminMenuVisible(
  privileges: UserPrivileges | undefined,
  isSuperUser = false
): Array<{ label: string; entries: AdminMenuEntry[] }> {
  const grupos: Array<{ label: string; entries: AdminMenuEntry[] }> = [];
  for (const grupo of ADMIN_MENU_GROUPS) {
    const entries = grupo.links.filter((entrada) => {
      const privilegio = privilegeForAdminRoute(entrada.route);
      return isSuperUser || !privilegio || tiene(privileges, privilegio);
    });
    if (entries.length > 0) {
      grupos.push({ label: grupo.label, entries });
    }
  }
  return grupos;
}
