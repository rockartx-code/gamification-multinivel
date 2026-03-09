export type AdminViewId = 'orders' | 'customers' | 'products' | 'stocks' | 'pos' | 'stats' | 'notifications' | 'settings';

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
  | 'product_set_month'
  | 'stock_create'
  | 'stock_create_transfer'
  | 'stock_add_inventory'
  | 'stock_mark_damaged'
  | 'stock_receive_transfer'
  | 'pos_register_sale'
  | 'user_mark_admin'
  | 'user_manage_privileges'
  | 'config_manage';

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
  'product_set_month',
  'stock_create',
  'stock_create_transfer',
  'stock_add_inventory',
  'stock_mark_damaged',
  'stock_receive_transfer',
  'pos_register_sale',
  'user_mark_admin',
  'user_manage_privileges',
  'config_manage'
];

export const SCREEN_PRIVILEGE_BY_VIEW: Record<AdminViewId, AppPrivilege> = {
  orders: 'access_screen_orders',
  customers: 'access_screen_customers',
  products: 'access_screen_products',
  stocks: 'access_screen_stocks',
  pos: 'access_screen_pos',
  stats: 'access_screen_stats',
  notifications: 'config_manage',
  settings: 'access_screen_settings'
};

export function normalizePrivileges(raw: unknown): UserPrivileges {
  const source = (raw ?? {}) as Record<string, unknown>;
  const normalized: UserPrivileges = {};
  for (const privilege of ALL_PRIVILEGES) {
    normalized[privilege] = source[privilege] === true;
  }
  return normalized;
}
