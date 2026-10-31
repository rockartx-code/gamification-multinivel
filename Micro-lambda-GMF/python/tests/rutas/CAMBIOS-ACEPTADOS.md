# Cambios de ruteo aceptados al migrar `catalog_lambda` a tabla declarativa

Las cascadas de `if` despachaban **por prefijo**: cualquier sub-path caía en el
handler de la raíz. Cuando ese handler no atendía el método, devolvía `None`, y
API Gateway lo traduce a **502 Bad Gateway**. La tabla declarativa compara
segmento a segmento, así que esas rutas pasan a 404 (no existe) o 405 (el
método no aplica).

Se comprobó **caso por caso** qué respondía cada uno antes de aceptar el cambio:

| Antes | Ahora | Casos |
|---|---|---|
| 502 (el handler devolvía `None`) | **405** método no permitido | `PATCH/DELETE` sobre `/products`, `/product-categories`, `/notifications`, `/campaigns` |
| 405 (el propio handler lo devolvía) | **405** desde el ruteador | `POST/PATCH/DELETE /catalog` |
| 502 | **404** ruta inexistente | ~250 sub-paths inventados (`/campaigns/loquesea`, …) |
| **Escritura real** en una URL no declarada | **404** | `POST /notifications/{id}` creaba una notificación; `POST /product-categories/{id}` creaba una categoría |

Comportamiento **preservado a propósito** (devolvían 200 de verdad):

- `GET /product-categories/{id}` y `GET /notifications/{id}` ignoran el id y
  devuelven la colección completa. Es discutible como diseño de API, pero
  cambiarlo es una decisión de contrato, no de ruteo.

El contrato nuevo queda fijado en `tests/test_ruteo.py`
(`test_una_ruta_inexistente_responde_404_y_no_502`,
`test_un_metodo_no_permitido_responde_405`).

## Diff completo

```
DELETE /campaigns/123: handle_campaigns → <sin handler>
DELETE /campaigns/cash-control: handle_campaigns → <sin handler>
DELETE /campaigns/cash-cut: handle_campaigns → <sin handler>
DELETE /campaigns/cash-cuts: handle_campaigns → <sin handler>
DELETE /campaigns/categories: handle_campaigns → <sin handler>
DELETE /campaigns/config: handle_campaigns → <sin handler>
DELETE /campaigns/create: handle_campaigns → <sin handler>
DELETE /campaigns/dashboard: handle_campaigns → <sin handler>
DELETE /campaigns/employees: handle_campaigns → <sin handler>
DELETE /campaigns/evaluate: handle_campaigns → <sin handler>
DELETE /campaigns/find: handle_campaigns → <sin handler>
DELETE /campaigns/getall: handle_campaigns → <sin handler>
DELETE /campaigns/honor-board: handle_campaigns → <sin handler>
DELETE /campaigns/login: handle_campaigns → <sin handler>
DELETE /campaigns/movements: handle_campaigns → <sin handler>
DELETE /campaigns/product: handle_campaigns → <sin handler>
DELETE /campaigns/receipt: handle_campaigns → <sin handler>
DELETE /campaigns/referral-code: handle_campaigns → <sin handler>
DELETE /campaigns/request: handle_campaigns → <sin handler>
DELETE /campaigns/sales: handle_campaigns → <sin handler>
DELETE /campaigns/summary: handle_campaigns → <sin handler>
DELETE /campaigns/transfers: handle_campaigns → <sin handler>
DELETE /campaigns/warnings: handle_campaigns → <sin handler>
DELETE /campaigns/withdrawal: handle_campaigns → <sin handler>
DELETE /catalog/categories: handle_categories → <sin handler>
DELETE /catalog: handle_catalog → <sin handler>
DELETE /notifications: handle_notifications → <sin handler>
DELETE /product-categories: handle_categories → <sin handler>
DELETE /products: handle_products → <sin handler>
GET /campaigns/123: handle_campaigns → <sin handler>
GET /campaigns/cash-control: handle_campaigns → <sin handler>
GET /campaigns/cash-cut: handle_campaigns → <sin handler>
GET /campaigns/cash-cuts: handle_campaigns → <sin handler>
GET /campaigns/categories: handle_campaigns → <sin handler>
GET /campaigns/config: handle_campaigns → <sin handler>
GET /campaigns/create: handle_campaigns → <sin handler>
GET /campaigns/dashboard: handle_campaigns → <sin handler>
GET /campaigns/employees: handle_campaigns → <sin handler>
GET /campaigns/evaluate: handle_campaigns → <sin handler>
GET /campaigns/find: handle_campaigns → <sin handler>
GET /campaigns/getall: handle_campaigns → <sin handler>
GET /campaigns/honor-board: handle_campaigns → <sin handler>
GET /campaigns/login: handle_campaigns → <sin handler>
GET /campaigns/movements: handle_campaigns → <sin handler>
GET /campaigns/product: handle_campaigns → <sin handler>
GET /campaigns/receipt: handle_campaigns → <sin handler>
GET /campaigns/referral-code: handle_campaigns → <sin handler>
GET /campaigns/request: handle_campaigns → <sin handler>
GET /campaigns/sales: handle_campaigns → <sin handler>
GET /campaigns/summary: handle_campaigns → <sin handler>
GET /campaigns/transfers: handle_campaigns → <sin handler>
GET /campaigns/warnings: handle_campaigns → <sin handler>
GET /campaigns/withdrawal: handle_campaigns → <sin handler>
PATCH /campaigns/123: handle_campaigns → <sin handler>
PATCH /campaigns/cash-control: handle_campaigns → <sin handler>
PATCH /campaigns/cash-cut: handle_campaigns → <sin handler>
PATCH /campaigns/cash-cuts: handle_campaigns → <sin handler>
PATCH /campaigns/categories: handle_campaigns → <sin handler>
PATCH /campaigns/config: handle_campaigns → <sin handler>
PATCH /campaigns/create: handle_campaigns → <sin handler>
PATCH /campaigns/dashboard: handle_campaigns → <sin handler>
PATCH /campaigns/employees: handle_campaigns → <sin handler>
PATCH /campaigns/evaluate: handle_campaigns → <sin handler>
PATCH /campaigns/find: handle_campaigns → <sin handler>
PATCH /campaigns/getall: handle_campaigns → <sin handler>
PATCH /campaigns/honor-board: handle_campaigns → <sin handler>
PATCH /campaigns/login: handle_campaigns → <sin handler>
PATCH /campaigns/movements: handle_campaigns → <sin handler>
PATCH /campaigns/product: handle_campaigns → <sin handler>
PATCH /campaigns/receipt: handle_campaigns → <sin handler>
PATCH /campaigns/referral-code: handle_campaigns → <sin handler>
PATCH /campaigns/request: handle_campaigns → <sin handler>
PATCH /campaigns/sales: handle_campaigns → <sin handler>
PATCH /campaigns/summary: handle_campaigns → <sin handler>
PATCH /campaigns/transfers: handle_campaigns → <sin handler>
PATCH /campaigns/warnings: handle_campaigns → <sin handler>
PATCH /campaigns/withdrawal: handle_campaigns → <sin handler>
PATCH /campaigns: handle_campaigns → <sin handler>
PATCH /catalog/categories: handle_categories → <sin handler>
PATCH /catalog: handle_catalog → <sin handler>
PATCH /notifications/123: handle_notifications → <sin handler>
PATCH /notifications/cash-control: handle_notifications → <sin handler>
PATCH /notifications/cash-cut: handle_notifications → <sin handler>
PATCH /notifications/cash-cuts: handle_notifications → <sin handler>
PATCH /notifications/categories: handle_notifications → <sin handler>
PATCH /notifications/config: handle_notifications → <sin handler>
PATCH /notifications/create: handle_notifications → <sin handler>
PATCH /notifications/dashboard: handle_notifications → <sin handler>
PATCH /notifications/employees: handle_notifications → <sin handler>
PATCH /notifications/evaluate: handle_notifications → <sin handler>
PATCH /notifications/find: handle_notifications → <sin handler>
PATCH /notifications/getall: handle_notifications → <sin handler>
PATCH /notifications/honor-board: handle_notifications → <sin handler>
PATCH /notifications/login: handle_notifications → <sin handler>
PATCH /notifications/movements: handle_notifications → <sin handler>
PATCH /notifications/product: handle_notifications → <sin handler>
PATCH /notifications/receipt: handle_notifications → <sin handler>
PATCH /notifications/referral-code: handle_notifications → <sin handler>
PATCH /notifications/request: handle_notifications → <sin handler>
PATCH /notifications/sales: handle_notifications → <sin handler>
PATCH /notifications/summary: handle_notifications → <sin handler>
PATCH /notifications/transfers: handle_notifications → <sin handler>
PATCH /notifications/warnings: handle_notifications → <sin handler>
PATCH /notifications/withdrawal: handle_notifications → <sin handler>
PATCH /notifications: handle_notifications → <sin handler>
PATCH /product-categories/123: handle_categories → <sin handler>
PATCH /product-categories/cash-control: handle_categories → <sin handler>
PATCH /product-categories/cash-cut: handle_categories → <sin handler>
PATCH /product-categories/cash-cuts: handle_categories → <sin handler>
PATCH /product-categories/categories: handle_categories → <sin handler>
PATCH /product-categories/config: handle_categories → <sin handler>
PATCH /product-categories/create: handle_categories → <sin handler>
PATCH /product-categories/dashboard: handle_categories → <sin handler>
PATCH /product-categories/employees: handle_categories → <sin handler>
PATCH /product-categories/evaluate: handle_categories → <sin handler>
PATCH /product-categories/find: handle_categories → <sin handler>
PATCH /product-categories/getall: handle_categories → <sin handler>
PATCH /product-categories/honor-board: handle_categories → <sin handler>
PATCH /product-categories/login: handle_categories → <sin handler>
PATCH /product-categories/movements: handle_categories → <sin handler>
PATCH /product-categories/product: handle_categories → <sin handler>
PATCH /product-categories/receipt: handle_categories → <sin handler>
PATCH /product-categories/referral-code: handle_categories → <sin handler>
PATCH /product-categories/request: handle_categories → <sin handler>
PATCH /product-categories/sales: handle_categories → <sin handler>
PATCH /product-categories/summary: handle_categories → <sin handler>
PATCH /product-categories/transfers: handle_categories → <sin handler>
PATCH /product-categories/warnings: handle_categories → <sin handler>
PATCH /product-categories/withdrawal: handle_categories → <sin handler>
PATCH /product-categories: handle_categories → <sin handler>
PATCH /products/123: handle_products → <sin handler>
PATCH /products/cash-control: handle_products → <sin handler>
PATCH /products/cash-cut: handle_products → <sin handler>
PATCH /products/cash-cuts: handle_products → <sin handler>
PATCH /products/categories: handle_products → <sin handler>
PATCH /products/config: handle_products → <sin handler>
PATCH /products/create: handle_products → <sin handler>
PATCH /products/dashboard: handle_products → <sin handler>
PATCH /products/employees: handle_products → <sin handler>
PATCH /products/evaluate: handle_products → <sin handler>
PATCH /products/find: handle_products → <sin handler>
PATCH /products/getall: handle_products → <sin handler>
PATCH /products/honor-board: handle_products → <sin handler>
PATCH /products/login: handle_products → <sin handler>
PATCH /products/movements: handle_products → <sin handler>
PATCH /products/product: handle_products → <sin handler>
PATCH /products/receipt: handle_products → <sin handler>
PATCH /products/referral-code: handle_products → <sin handler>
PATCH /products/request: handle_products → <sin handler>
PATCH /products/sales: handle_products → <sin handler>
PATCH /products/summary: handle_products → <sin handler>
PATCH /products/transfers: handle_products → <sin handler>
PATCH /products/warnings: handle_products → <sin handler>
PATCH /products/withdrawal: handle_products → <sin handler>
PATCH /products: handle_products → <sin handler>
POST /campaigns/123: handle_campaigns → <sin handler>
POST /campaigns/cash-control: handle_campaigns → <sin handler>
POST /campaigns/cash-cut: handle_campaigns → <sin handler>
POST /campaigns/cash-cuts: handle_campaigns → <sin handler>
POST /campaigns/categories: handle_campaigns → <sin handler>
POST /campaigns/config: handle_campaigns → <sin handler>
POST /campaigns/create: handle_campaigns → <sin handler>
POST /campaigns/dashboard: handle_campaigns → <sin handler>
POST /campaigns/employees: handle_campaigns → <sin handler>
POST /campaigns/evaluate: handle_campaigns → <sin handler>
POST /campaigns/find: handle_campaigns → <sin handler>
POST /campaigns/getall: handle_campaigns → <sin handler>
POST /campaigns/honor-board: handle_campaigns → <sin handler>
POST /campaigns/login: handle_campaigns → <sin handler>
POST /campaigns/movements: handle_campaigns → <sin handler>
POST /campaigns/product: handle_campaigns → <sin handler>
POST /campaigns/receipt: handle_campaigns → <sin handler>
POST /campaigns/referral-code: handle_campaigns → <sin handler>
POST /campaigns/request: handle_campaigns → <sin handler>
POST /campaigns/sales: handle_campaigns → <sin handler>
POST /campaigns/summary: handle_campaigns → <sin handler>
POST /campaigns/transfers: handle_campaigns → <sin handler>
POST /campaigns/warnings: handle_campaigns → <sin handler>
POST /campaigns/withdrawal: handle_campaigns → <sin handler>
POST /catalog: handle_catalog → <sin handler>
POST /notifications/123: handle_notifications → <sin handler>
POST /notifications/cash-control: handle_notifications → <sin handler>
POST /notifications/cash-cut: handle_notifications → <sin handler>
POST /notifications/cash-cuts: handle_notifications → <sin handler>
POST /notifications/categories: handle_notifications → <sin handler>
POST /notifications/config: handle_notifications → <sin handler>
POST /notifications/create: handle_notifications → <sin handler>
POST /notifications/dashboard: handle_notifications → <sin handler>
POST /notifications/employees: handle_notifications → <sin handler>
POST /notifications/evaluate: handle_notifications → <sin handler>
POST /notifications/find: handle_notifications → <sin handler>
POST /notifications/getall: handle_notifications → <sin handler>
POST /notifications/honor-board: handle_notifications → <sin handler>
POST /notifications/login: handle_notifications → <sin handler>
POST /notifications/movements: handle_notifications → <sin handler>
POST /notifications/product: handle_notifications → <sin handler>
POST /notifications/receipt: handle_notifications → <sin handler>
POST /notifications/referral-code: handle_notifications → <sin handler>
POST /notifications/request: handle_notifications → <sin handler>
POST /notifications/sales: handle_notifications → <sin handler>
POST /notifications/summary: handle_notifications → <sin handler>
POST /notifications/transfers: handle_notifications → <sin handler>
POST /notifications/warnings: handle_notifications → <sin handler>
POST /notifications/withdrawal: handle_notifications → <sin handler>
POST /product-categories/123: handle_categories → <sin handler>
POST /product-categories/cash-control: handle_categories → <sin handler>
POST /product-categories/cash-cut: handle_categories → <sin handler>
POST /product-categories/cash-cuts: handle_categories → <sin handler>
POST /product-categories/categories: handle_categories → <sin handler>
POST /product-categories/config: handle_categories → <sin handler>
POST /product-categories/create: handle_categories → <sin handler>
POST /product-categories/dashboard: handle_categories → <sin handler>
POST /product-categories/employees: handle_categories → <sin handler>
POST /product-categories/evaluate: handle_categories → <sin handler>
POST /product-categories/find: handle_categories → <sin handler>
POST /product-categories/getall: handle_categories → <sin handler>
POST /product-categories/honor-board: handle_categories → <sin handler>
POST /product-categories/login: handle_categories → <sin handler>
POST /product-categories/movements: handle_categories → <sin handler>
POST /product-categories/product: handle_categories → <sin handler>
POST /product-categories/receipt: handle_categories → <sin handler>
POST /product-categories/referral-code: handle_categories → <sin handler>
POST /product-categories/request: handle_categories → <sin handler>
POST /product-categories/sales: handle_categories → <sin handler>
POST /product-categories/summary: handle_categories → <sin handler>
POST /product-categories/transfers: handle_categories → <sin handler>
POST /product-categories/warnings: handle_categories → <sin handler>
POST /product-categories/withdrawal: handle_categories → <sin handler>
```
