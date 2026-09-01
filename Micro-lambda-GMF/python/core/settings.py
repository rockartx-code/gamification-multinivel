"""Constantes y variables de entorno. No importa nada del paquete."""

import os
from decimal import Decimal


TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")

# Constantes de Negocio
D_ZERO = Decimal("0")

D_ONE = Decimal("1")

D_CENT = Decimal("0.01")

MAX_NETWORK_DEPTH = 3

MAX_BATCH_GET_RETRIES = 8

APP_CONFIG_TTL_SECONDS = int(os.getenv("APP_CONFIG_TTL_SECONDS", "60"))

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))

NETWORK_TREE_ID = "customers"

NETWORK_TREE_ROOT_KEY = "__ROOT__"

NETWORK_TREE_SK = "TREE"

COMMISSION_MONTH_PK = "COMMISSION_MONTH"

LEDGER_MAX_ATTEMPTS = 6

#: Esquema de almacenamiento del mes contable de comisiones.
#:   "off"  — item único con la lista `ledger` dentro (esquema original)
#:   "dual" — escribe en ambos, lee del original (transición)
#:   "rows" — un item por fila, totales con ADD atómico
#: Ver core/ledger.py para el porqué y tools/migrate_ledger_rows.py para poblar.
LEDGER_ROW_SCHEME = os.getenv("LEDGER_ROW_SCHEME", "off").strip().lower()

PASSWORD_HASH_SCHEME = "pbkdf2_sha256"

PASSWORD_HASH_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "210000"))

_ALL_PRIVILEGES = [
    "access_screen_orders",
    "access_screen_customers",
    "access_screen_products",
    "access_screen_stocks",
    "access_screen_pos",
    "access_screen_stats",
    "access_screen_settings",
    "order_mark_paid",
    "order_mark_shipped",
    "order_mark_delivered",
    "order_create",
    "customer_add",
    "commissions_register_payment",
    "product_add",
    "product_update",
    "product_set_month",
    "stock_create",
    "stock_create_transfer",
    "stock_add_inventory",
    "stock_mark_damaged",
    "stock_receive_transfer",
    "pos_register_sale",
    "user_mark_admin",
    "user_manage_privileges",
    "employee_add",
    "employee_manage_privileges",
    "access_screen_employees",
    "config_manage",
    "access_screen_honor_board",
]

# El token de superadmin se toma del entorno. Si la variable no está definida,
# NO existe ningún token maestro: antes había uno fijo en el código fuente, es
# decir una puerta trasera de rol admin válida en producción para cualquiera
# que pudiera leer el repositorio.
_SUPERADMIN_TOKEN = os.getenv("SUPERADMIN_TOKEN", "").strip()

SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "info@findingu.com.mx")
