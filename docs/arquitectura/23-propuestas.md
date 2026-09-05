# 23 · Arquitectura de la ronda de propuestas: ocho paquetes en paralelo y dos transversales

**Fecha:** 3 de septiembre de 2026. **Rama:** `claude/ultimos-cambios-integrados-fylhiw`.
**Base:** [22](../qa/22-diarios-inquietudes-friccion-automatizacion.md) (§6 tareas, §7 propuestas, §10 estado), [21](../qa/21-cuarta-ronda-escenarios-restantes.md) §3–§4, [19](../qa/19-analisis-negocio-y-correcciones.md) §3, `core/config.py`, los siete lambdas, `sim/servidor.py` y el frontend.

Este documento es el contrato de la ronda. Ocho agentes trabajan **a la vez** en worktrees sobre la misma base; para que no se pisen, cada paquete tiene una lista cerrada de archivos **propios** (crea y edita con libertad) y una lista de archivos **compartidos** donde solo puede hacer el *edit mínimo* que aquí se describe (una línea de montaje, un `import`, una entrada en una lista). Cuando dos paquetes tocan el mismo archivo compartido, el documento dice en qué función o bloque toca cada uno. Los componentes que un paquete construye y otro monta tienen nombre de archivo, selector e *inputs* fijados aquí.

Los ids y nombres de los paquetes son fijos: A `pagos-comisiones`, B `modo-cliente-y-plan`, C `checkout-y-sesion`, D `almacen-despacho-paqueteria`, E `caja-arqueo`, F `coach-seguimiento`, G `devoluciones`, H `pasarela-y-suscripcion`. Después de integrar la ola A, dos agentes transversales (I1 `transversal-admin`, I2 `transversal-socio`) trabajan sobre el árbol integrado (§11).

---

## 0. Convenciones comunes a todos los paquetes

### 0.1 Hechos del código que condicionan el diseño

- **Tabla única DynamoDB** con patrón bucket + REF (`core/db.py`): `PK = ENTIDAD`, `SK = "{createdAt}#{id}"`, puntero `ENTIDAD#{id}/REF`. Se lee con `utils._get_by_id`, `utils._query_bucket(entidad, sk_prefix=, sk_from=, sk_to=)`, se escribe con `utils._put_entity` y `utils._update_by_id`. Las entidades nuevas de esta ronda siguen ese patrón; **no se crean índices secundarios**: el volumen (decenas de clientes, cientos de pedidos) no lo exige y `sk_prefix` por fecha basta para acotar.
- **Configuración del negocio** en `core/config.py` (`_default_app_config`, fusionada con el item `CONFIG/app-v1`). Números que usan todos los paquetes: activación **20 VP netos** (`rewards.activationNetMin`, `mxnPerVp = 50` → ≈ $1,000), descuento por tramo **0 / 10 / 20 / 30 / 40 %** desde **$0 / $1,000 / $2,000 / $3,000 / $6,000** de MPN acumulado en el mes (`discountTiers`; el tramo se decide con acumulado previo + compra actual y aplica a toda la compra), comisiones por generación **10 / 5 / 4 / 3 / 2 %** con requisitos `reqActiveDirects 0/2/3/4/5`, `reqPersonalPC 0/0/80/120/160`, `reqLines 0/0/2/3/3`, `reqPCPerLine 0/0/300/450/750` (`commissionLevels`), compresión dinámica, reevaluación de bloqueadas al activarse (`reevaluateBlockedOnActivation`), día de pago **10** (`payoutDay`), envío gratis desde `shipping.freeShippingMin` (0 = sin regla; en el mundo simulado vale 1000), documentos `customerDocumentTypes` (constancia, INE, CURP). Toda clave nueva de config se añade a `_default_app_config` con su valor por omisión y un comentario; nadie repite defaults en el punto de lectura.
- **Privilegios** en `core/settings._ALL_PRIVILEGES` y `models/privileges.model.ts`. Esta ronda **no crea privilegios nuevos**: cada ruta reutiliza el que corresponde a la pantalla que la usa (tabla en cada paquete). El superadmin (`SUPERADMIN_TOKEN`) tiene todos.
- **Ruteo.** `commissions_lambda` y `catalog_lambda` usan la tabla declarativa `RUTAS = [Ruta(...)]` de `core/routing.py`; `order_lambda`, `inventory_lambda`, `customer_lambda`, `auth_utils`, `dashboard_lambda` y `shipping_lambda` usan cascadas de `if`. Las ocho lambdas comparten el mismo `CodeUri: python/` (`template.yaml`), así que un módulo puede importar a otro (`despacho_handlers` puede llamar a `order_lambda.handle_update_status`); en el harness `sim/servidor.py` ya se importan todos.
- **Sesiones**: `SESSION#{token}` con TTL de 30 días (`SESSION_TTL_SECONDS`); el actor sale de `utils._extract_actor(headers)` (rol, privilegios, `canAccessAdmin`). Auto-servicio con `utils._require_self_or_admin(_from_bearer)`.
- **Correo**: `utils._send_ses_email(para, asunto, texto, html)` con `core.email._email_shell(cuerpo)`; en el harness se intercepta al buzón. Los correos del pedido viven en `core/order_emails._plantillas`.
- **Motor de comisiones**: `ORDER_PAID` → `handle_apply_rewards` (VP, filas `pending`/`blocked`), `ORDER_DELIVERED` → `handle_confirm_commissions` (`confirmed`), anulaciones → filas `voided`. El mes contable es `COMMISSION_MONTH` / `#BENEFICIARY#{id}#MONTH#{YYYY-MM}` con `ledger[]`, `totalPending/Confirmed/Blocked`, `status IN_PROGRESS|PAID`, `version` (bloqueo optimista; se muta con `utils._mutate_ledger_month`).
- **Pasarela**: `handle_mercadopago_checkout` crea la preferencia y anexa `webhookSecret` a `notification_url`; `POST /orders/webhooks/mercadolibre` → `handle_mp_webhook` consulta `/v1/payments/{id}` y llama a `handle_update_status(paid)`. Falta validar el secreto, idempotencia y conciliación (paquete H).
- **Pruebas**: `Micro-lambda-GMF/python/tests/` con DynamoDB en memoria (`conftest.py`: fixtures `store`, `utils`, `snapshot_ruteo`). `test_ruteo.py` fija una instantánea del ruteo por módulo en `tests/rutas/<modulo>.json` (se regenera con `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py`) y toma las rutas del `openapi-aws.yaml`. `test_arquitectura.py` exige que `core/` no invierta capas y que `core_utils` solo reexporte.
- **Frontend** Angular standalone. `app.routes.ts` (hash routing: `/#/ruta`), servicios `api.service.ts` → `real-api.service.ts` (`environment.apiBaseUrl`, cabeceras en `actorHeaders()`), `auth.service.ts` (sesión en `localStorage['auth-user']`). `admin.component.{ts,html}` es un monolito (7,479 + 4,772 líneas) con vistas por `currentView` (§0.6 mapa de regiones). `user-dashboard.component` decide `isClient` por `role === 'cliente'` e `isGuest` por el `dashboardControl.data.isGuest`.

### 0.2 Módulos backend nuevos y cómo se enganchan

Cada paquete pone su lógica nueva en **un módulo `*_handlers.py`** en `Micro-lambda-GMF/python/` (junto a los lambdas), que importa `core_utils as utils` y, si lo necesita, el lambda anfitrión (`import order_lambda`), nunca `core/*` directamente salvo `core.email` y `core.routing`.

**Anfitrión con tabla declarativa** (`commissions_lambda` para A; `catalog_lambda` para B): el módulo expone `RUTAS: list[Ruta]` con patrones relativos al prefijo del lambda y el anfitrión añade, **al final del archivo**, dos líneas:

```python
import pagos_handlers                      # paquete A
RUTAS.extend(pagos_handlers.RUTAS)         # paquete A
```

**Anfitrión en cascada** (`order_lambda`, `inventory_lambda`, `customer_lambda`): el módulo expone

```python
def atender(peticion) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
```

y el anfitrión lleva, junto a sus imports, una lista `_EXTENSIONES = [...]` y, como **primer bloque dentro del `try:` de `lambda_handler`**, el recorrido:

```python
        for extension in _EXTENSIONES:
            respuesta = extension.atender(request)
            if respuesta is not None:
                return respuesta
```

El módulo compara `peticion.segments` **ya sin el prefijo** del lambda (en `order_lambda` los segmentos llegan con `orders` delante porque no usa `strip_prefix`; el módulo lo tolera: `seg = request.segments[1:] if request.segments[:1] == ["orders"] else request.segments`). Dentro de `atender` se comprueba el privilegio con `utils._require_admin(headers, "…")` o `utils._require_self_or_admin(_from_bearer)` exactamente como hace el anfitrión. El bloque `_EXTENSIONES` y su recorrido los introduce **el primer paquete que se integre** en cada anfitrión (§12); los demás solo añaden su `import` y su elemento a la lista. Los conflictos que eso produce son de líneas adyacentes y los resuelve el integrador.

Anfitriones y extensiones de esta ronda:

| Anfitrión | Extensiones (paquete) |
|---|---|
| `order_lambda.py` | `checkout_handlers` (C), `devoluciones_handlers` (G), `suscripciones_handlers` (H), `conciliacion_handlers` (H) |
| `inventory_lambda.py` | `despacho_handlers` (D), `caja_handlers` (E) |
| `customer_lambda.py` | `modo_handlers` (B), `seguimiento_handlers` (F) |
| `commissions_lambda.py` (declarativo) | `pagos_handlers` (A) |
| `catalog_lambda.py` (declarativo) | `modo_handlers.RUTAS_CATALOGO` (B) |

`auth_utils.py`, `shipping_lambda.py` y `dashboard_lambda.py` no reciben extensiones: los cambios que necesitan son edits localizados de su dueño (§0.7).

### 0.3 Rutas programables y el reloj de la simulación

Varias propuestas necesitan una tarea periódica (avisos de bloqueadas los días 20 y 27, rastreo y cierre de envíos, generación de pedidos de suscripción, conciliación de pagos). El contrato es el mismo para todas:

- Es una ruta HTTP `POST` **idempotente por día**: se puede invocar varias veces el mismo día sin repetir efectos (cada tarea guarda su marca: `blockedNoticeSentDays` en el mes contable, `deliveryCheckEmailSentAt` en el pedido, `lastRunDate` en la suscripción, etc.).
- Acepta dos autorizaciones: el privilegio de la pantalla que la expone, o el token de superadmin (`SUPERADMIN_TOKEN`), que es como la invocará un programador externo (EventBridge → API Gateway; el cableado de EventBridge queda documentado en el paquete y **no se despliega en esta ronda**).
- El módulo que la expone declara `TAREAS_PROGRAMADAS = [("POST", "/commissions/avisos/bloqueadas"), ...]` (rutas completas, con prefijo del lambda). El lambda anfitrión reexporta la lista si la extensión la aporta (`order_lambda`: `TAREAS_PROGRAMADAS = suscripciones_handlers.TAREAS_PROGRAMADAS + conciliacion_handlers.TAREAS_PROGRAMADAS`, lo escribe H; `inventory_lambda`: la de `despacho_handlers`, lo escribe D; `commissions_lambda`: la propia, lo escribe A).
- **Hook del reloj** (lo implementa H en `sim/servidor.py`): al cambiar la fecha con `POST /__sim/reloj`, tras `fijar_reloj`, se llama `ejecutar_tareas_programadas()`, que recorre `set(LAMBDAS.values())`, lee `getattr(mod, "TAREAS_PROGRAMADAS", [])` e invoca cada ruta con `{"httpMethod": "POST", "path": ruta, "headers": {"authorization": "Bearer " + SUPERADMIN_TOKEN}, "body": "{}"}`, drena la cola SFN y guarda. También se expone `POST /__sim/tareas` para dispararlas a mano. Como la lista se descubre por atributo, A y D **no tocan** `sim/servidor.py`.

### 0.4 Pruebas y contratos que hay que mantener en verde

- Cada paquete crea sus pruebas en `tests/test_<paquete>_*.py` (por ejemplo `test_pagos_lote.py`, `test_modo_cliente.py`, `test_checkout_factura.py`). Cada regresión lleva el síntoma en la docstring, como el resto de la suite. La suite completa (`pytest`) debe seguir en verde en cada worktree.
- **Instantánea de ruteo**: cada paquete añade sus rutas nuevas al `openapi-aws.yaml` (bajo `paths:`, en un bloque al final con el comentario `# ── Paquete X ──`, con `summary` y el privilegio en `description`) y regenera **solo** el `tests/rutas/<anfitrión>.json` de su lambda con `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py -k <anfitrión>`, revisando que el diff contenga únicamente sus rutas. Al integrar, el integrador regenera los ocho.
- `test_arquitectura.py`: los módulos nuevos no van en `core/`; nada de lógica en `core_utils.py`.
- Frontend: `ng build` sin errores en cada worktree; los componentes nuevos son standalone y no se registran en ningún módulo.

### 0.5 Frontend: servicios, modelos, rutas

- **Un servicio por paquete** en `services/`: `pagos.service.ts` (A), `plan-socio.service.ts` (B), `checkout.service.ts` (C), `despacho.service.ts` (D), `caja.service.ts` (E), `seguimiento.service.ts` (F), `devoluciones.service.ts` (G), `suscripcion.service.ts` y `conciliacion.service.ts` (H). Usan `HttpClient` con `environment.apiBaseUrl` y las cabeceras de `RealApiService.actorHeaders()`. Ese método hoy es `private` (línea 1295): **el primer paquete que lo necesite lo cambia a `public actorHeaders(): HttpHeaders`**; esa línea idéntica en varias ramas se fusiona sin conflicto. No se tocan `api.service.ts` ni `mock-api.service.ts` (el modo mock queda sin estas funciones; es aceptable: la galería no las usa).
- **Modelos**: cada paquete crea `models/<paquete>.model.ts`. Si necesita un campo en una interfaz existente (`AdminCustomer`, `AdminOrder`, `DashboardData`…), lo añade **opcional, al final de la interfaz, con el comentario `// paquete X`**. Nada de renombrar o reordenar.
- **Rutas** (`app.routes.ts`): cada paquete añade su entrada **al final del arreglo** con su comentario. Rutas nuevas de esta ronda: `modo-socio` (B, pública), `admin/despacho` y `admin/resumen-turno` (D, `adminGuard`), `admin/seguimiento` (F, `adminGuard`), `admin/arqueo` (E, opcional, `adminGuard`).
- **Componentes compartidos** que un paquete construye y otro monta: `components/ui-tabla-descuento/` y `components/ui-ahorro-socio/` (B; §2.6), `pages/user-dashboard/suscripcion/` (H; §8.6). Sus selectores e inputs están fijados; el que monta no los cambia.
- **Textos**: español de México, sin anglicismos en pantalla, "socia/socio" según el contexto; los importes con `formatMoney` (centavos cuando existen).

### 0.6 Mapa de regiones de `admin.component.{ts,html}` (quién toca qué)

Referencias a la numeración actual de la rama base; se mueven con cada edit, así que se identifican por el ancla, no por la línea.

| Región (html) | Ancla | Paquete y edit permitido |
|---|---|---|
| Barra de Pedidos | `<div class="mt-4 flex flex-wrap gap-2" *ngIf="currentView === 'orders'` (≈122–153) | **D**: botón "Despacho en bloque" (routerLink `/admin/despacho`) antes de `<!-- Filtro por stock -->`. **H**: botón "Conciliar pagos" al final del div. |
| Lista y detalle de Pedidos | ≈154–434 | **C**: insignia "Factura solicitada" y bloque "Marcar factura emitida" dentro del detalle (`toggleOrderDetail`). Nadie más. |
| Sección Clientes | `*ngIf="currentView === 'customers'` (≈435–949) | **F**: botón "Seguimiento de hoy" en la barra superior de la sección (primer `div` de la sección). **B**: columna "Modo" en la lista y etiqueta de modo en la ficha. **A**: `<app-pagos-mes>` como último bloque de la sección (antes del cierre del `div`). |
| Sección Stocks | ≈1577–1820 | **C**: campos "Ciudad" y "Estado" en el formulario de almacén. |
| Sección POS | `*ngIf="currentView === 'pos'` (≈1824–2465) | **E** (solo E; edits localizados; se recomienda mover el corte a `<app-admin-arqueo>`). |
| Sección Estadísticas | ≈2466–2850 | **D**: botón "Resumen de turno" (routerLink) en el encabezado. |
| Modales de devolución y reembolso | `isReceiveReturnModalOpen`, `isRejectReturnModalOpen`, `isRefundModalOpen` | **G**. |
| Modal "Acciones urgentes" | ≈3840–3890 | Nadie (los textos vienen del backend). |

| Región (ts) | Ancla | Paquete |
|---|---|---|
| `imports: [...]` del `@Component` | línea ≈236 | **A** (`PagosMesComponent`), **E** (`AdminArqueoComponent`). |
| `resolveWarning()` | ≈3215 | **A**: entradas `commissions_ready` y `commissions_no_clabe` → `'customers'`. |
| `downloadOrdersReport()` | ≈2108 | **H**: añade `conciliarPagos()` justo después. |
| `openReceiveReturnModal` … `confirmRejectReturn`, `openRefundModal` … `confirmRefund` | ≈3858–4072 | **G**. |
| Métodos POS (`setPosStock` … `settlePosSale`, `canRegisterPosSale`, `canCreatePosCashCut`, retiros y cortes) | ≈6012–6400 | **E**. |
| Final de la clase | — | **C**: `markInvoiceIssued(order)`. **D**: `applyEmployeeDefaultStock()` y su llamada (una línea) al final de `loadStocksAndPosState()` (≈3079). |

I1 (ola B) es el único que puede hacer cambios transversales (botones deshabilitados, `prompt/confirm`, DOM duplicado) en todo el monolito.

### 0.7 Archivos compartidos con más de un dueño

| Archivo | Quién y dónde |
|---|---|
| `order_lambda.py` | **H**: `handle_mercadopago_checkout`, `handle_mp_webhook`, `_precios_cobrables`, `handle_update_status` (guarda de idempotencia en `paid`), lista `_EXTENSIONES` y su recorrido, `TAREAS_PROGRAMADAS`. **C**: `handle_create_order` (factura, regla de envío gratis, validación de sucursal), `handle_list_orders` (filtro `invoiceStatus`), import + entrada en `_EXTENSIONES`. **G**: `RETURN_*`, `_validar_solicitud_devolucion`, `_subir_evidencia_devolucion`, `handle_return_request`, `handle_return_inspection`, `handle_refund_order`, `_resumen_devolucion`, import + entrada. **D**: dentro de `handle_update_status`, solo el bloque `if new_status == "shipped":` (añade `shippedAt`, `shippedBy`) y el bloque `if new_status == "delivered":` (acepta `deliveredAt`, `deliverySignedBy`, `deliveredBy` del body). **B**: `_calculate_totals` (tasa 0 en modo cliente y campos `partnerSavings*`). |
| `inventory_lambda.py` | **E**: `handle_pos_sale`, `handle_settle_pos_sale`, `handle_void_pos_sale`, `_build_pos_cash_control`, `handle_cash_cut`, `handle_pos_withdrawal`, `handle_list_cash_cuts`, `_route_pos`. **D**: `handle_transfers`, `_apply_stock_delta`, `_log_movement`, `_route_stocks`. **C**: en `handle_stocks`, añadir `"city", "state"` a la lista de campos de POST y PATCH (dos líneas). Lista `_EXTENSIONES`: D la introduce, E añade su entrada. |
| `customer_lambda.py` | **F**: `_format_customer_output` (campos de seguimiento), `handle_update_customer` (campos `contactPreference`, `executiveId`), `_con_comisiones`, `_ultima_compra`, `handle_customer_dashboard` salvo la línea de B, `_EXTENSIONES`. **B**: en `_format_customer_output` una línea `out["mode"] = modo_handlers.modo_de(item)`; en `handle_customer_dashboard` una línea antes del `return`: `response = modo_handlers.ajustar_dashboard(customer, response)`; import + entrada en `_EXTENSIONES`. |
| `commissions_lambda.py` | **A**: todo (incluido refactor de `handle_admin_receipt`, `handle_apply_rewards` para gracia y aviso de CLABE, `handle_confirm_commissions` para aviso de CLABE, `handle_commissions_summary`, `import pagos_handlers` + `RUTAS.extend`). **B**: una línea en `_distribute_commissions`, justo después de crear una fila nueva para un beneficiario: `modo_handlers.asegurar_socio(beneficiary_id, "comision")`. |
| `auth_utils.py` | **C**: todo (login, recordarme, enlace de acceso, recuperación, ruteo). **B**: en `handle_create_account`, `"mode": "cliente"` en `customer_item` y, tras resolver `leader_id`, una línea `modo_handlers.asegurar_socio(leader_id, "referido")`; en `handle_login`, una línea `"mode": modo_handlers.modo_de(profile) if entity_type == "CUSTOMER" else None` en el dict `user`. |
| `dashboard_common.py` | **F**: `_find_effective_sponsor` (coach). **A**: `_active_notifications_for_customer` (filtro `targetCustomerId`). |
| `dashboard_lambda.py` | **A**: `get_admin_warnings` (avisos de comisiones separados y con urgencia por fecha). |
| `core/config.py` | Cada paquete añade sus claves en `_default_app_config` **dentro del bloque de su tema** (A en `rewards`, C en `shipping`/`checkout`, D en `shipping.carrierIntegration`, E en `pos`, F en `seguimiento`, H en `payments.mercadoLibre` y `subscriptions`). Bloques nuevos (`checkout`, `seguimiento`, `subscriptions`) van al final del dict, en orden alfabético por paquete. |
| `core/order_emails.py` (`_plantillas`) | **B**: solo la rama `evento == "paid"` (párrafo de ahorro). **G**: ramas `return_received`, `return_approved`, `return_rejected`, `refunded`, `cancelled`. **D**: nueva rama `elif evento == "delivery_check":` inmediatamente antes del `else` final. |
| `sim/servidor.py` | **H** únicamente (stub de MercadoPago y hook del reloj). |
| `app.routes.ts` | B, D, E, F: una entrada cada uno al final. |
| `admin.component.{ts,html}` | Ver §0.6. |
| `models/admin.model.ts`, `models/user-dashboard.model.ts` | Campos opcionales al final de la interfaz con comentario del paquete (§0.5). |
| `services/real-api.service.ts` | `actorHeaders()` pasa a `public` (cualquiera; línea idéntica). **C**: además cambia su lectura de `localStorage` por `sessionStorage ?? localStorage` (recordarme). |
| `openapi-aws.yaml`, `tests/rutas/*.json` | §0.4. |

---

## 1. Paquete A · `pagos-comisiones` (propuestas 4, 12 y 22)

### 1.1 Objetivo

Que el día de pago sea **una pantalla**, no dieciséis fichas: la gerente ve quién cobra cuánto, exporta el archivo para el banco, sube un comprobante por lote y marca pagados en bloque; el sistema pide la CLABE a la socia antes de que haga falta y avisa a tiempo lo que está por perderse por no activarse.

### 1.2 Diseño funcional

**Pantalla "Pagos del mes"** (`pages/admin/pagos-mes/`, selector `app-pagos-mes`, montada al final de la sección Clientes; también accesible desde "Acciones urgentes"). Selector de mes (por omisión el mes anterior al actual). Tres contadores arriba: "Listas para depositar · N · $X", "Sin CLABE · N · $Y", "Pagadas · N · $Z". Tabla con una fila por beneficiaria: nombre, correo/WhatsApp, monto confirmado, CLABE enmascarada (`••••••••••••••1234`) y banco, estado (`Lista` verde / `Sin CLABE` ámbar / `Pagada` con enlace "Ver comprobante" / `Pagada por lote L-…`), casilla de selección (solo filas `Lista`). Botones: "Exportar archivo de dispersión (CSV)" (solo listas), "Registrar pago por lote" (abre modal: archivo del comprobante, referencia bancaria opcional, lista de las N seleccionadas con montos y el total; texto del efecto: *"Se marcarán como pagadas N comisiones por $X. El comprobante queda ligado a cada una. Se avisará por correo a cada socia."*), y por fila "Deshacer pago" (modal con motivo; efecto: *"El mes vuelve a pendiente y el comprobante queda anulado"*). Las filas sin CLABE muestran el botón "Pedir CLABE" que envía el recordatorio (§1.5) y anota la bitácora. Tras registrar, la tabla se recarga **desde el servidor** y la confirmación muestra el folio del lote y el total leído de la respuesta.

**Acciones urgentes**: los avisos de comisiones se separan en `commissions_ready` ("N comisiones listas para depositar · $X") y `commissions_no_clabe` ("N socias con comisión y sin CLABE · $Y"); severidad `low` antes del día `payoutDay − 2` del mes siguiente, `high` desde entonces (hallazgo 12 de la ronda 4). Ambos llevan a Clientes → Pagos del mes.

**Panel de la socia**: al activarse por primera vez sin CLABE, y al tener su primera comisión confirmada del mes sin CLABE, recibe correo "Registra tu CLABE para cobrar" y un aviso en el panel (mecanismo de notificaciones existente, dirigido a ella) con enlace a la sección de Comisiones donde ya existe el formulario de CLABE.

**Avisos de bloqueadas (política 22, opción b)**: los días **20 y 27** de cada mes, cada socia con `totalBlocked > 0` e inactiva recibe correo "Tienes $X en comisiones bloqueadas que se pierden el {último día del mes}" con los VP que le faltan y **el producto más barato que los cierra** (con enlace al carrito) y la frase honesta: "Si te activas antes del cierre, se recalculan y pasan a pendientes/confirmadas; si no, se pierden al cerrar el mes".

### 1.3 Contratos de API (prefijo `/commissions`, todas con privilegio `commissions_register_payment` salvo indicación)

| Método y ruta | Cuerpo | Respuesta | Errores |
|---|---|---|---|
| `GET /commissions/pagos?month=YYYY-MM` | — | `{monthKey, rows:[{customerId, name, email, phone, amount, clabeMasked, bankInstitution, status:"listo"|"sin_clabe"|"pagado", receiptUrl, paidAt, batchId}], totals:{listo:{count,amount}, sinClabe:{…}, pagado:{…}}}`. Solo beneficiarias con `totalConfirmed > 0`. | 400 mes inválido |
| `GET /commissions/pagos/dispersion.csv?month=` | — | `text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="dispersion-YYYY-MM.csv"`; columnas `CLABE,Beneficiario,Monto,Concepto,Referencia,Email`; concepto `Comisiones YYYY-MM Finding'U`; referencia `customerId`. Solo filas `listo`. Respuesta construida con `utils._cors_headers("text/csv; charset=utf-8")`. | 400 mes inválido |
| `POST /commissions/pagos/lote` | `{monthKey, customerIds:[…], name, contentType, contentBase64, bankReference?}` | `201 {batchId:"LOTE-XXXXXXXX", assetUrl, paid:[{customerId, receiptId, amount}], skipped:[{customerId, code:"CLABE_REQUIRED"|"ALREADY_PAID"|"NO_CONFIRMED"}], totalPaid}`. Sube el archivo **una vez**, crea un `COMMISSION_RECEIPT` por beneficiaria con `batchId`, marca cada mes `PAID` y manda el correo de depósito existente. Por fila: las que fallan se saltan con código; nunca se marca sin CLABE. | 400 cuerpo incompleto o base64 inválido; 409 si `customerIds` vacío |
| `POST /commissions/admin/receipt/revert` (existente) | `{customerId, monthKey, reason}` | Sin cambios; además marca `batchId` en el recibo anulado. | 409 mes no pagado |
| `POST /commissions/pagos/pedir-clabe` | `{customerId}` | `200 {sent:true, channel:"email+panel"}`; reenvía el recordatorio y anota `clabeReminderAt`. | 404 |
| `POST /commissions/avisos/bloqueadas` (programable; privilegio o superadmin) | `{force?:bool, dryRun?:bool}` | `200 {day, notified:[{customerId, blocked, vpMissing, product:{id,name,units,cost}}], skipped:"not_notice_day"?}`. Solo actúa si el día del mes está en `rewards.blockedNoticeDays` o `force`. Idempotente: guarda el día en `blockedNoticeSentDays[]` del mes contable. | — |

`handle_commissions_summary` (existente) devuelve además `status:"sin_clabe"` cuando corresponde, para que la ficha y la lista de Clientes lo pinten.

### 1.4 Cambios de datos

- `COMMISSION_PAYMENT_BATCH` (bucket nuevo): `{batchId, monthKey, assetId, assetUrl, bankReference, customerIds[], totalPaid, createdBy, createdAt}`.
- `COMMISSION_RECEIPT`: `batchId` opcional.
- `COMMISSION_MONTH`: `clabeReminderAt` (ISO) y `blockedNoticeSentDays: [20, 27]` (se escriben dentro de `_mutate_ledger_month`, que preserva `version`).
- `CUSTOMER`: `clabeReminderFirstAt` (primer aviso, al activarse).
- `NOTIFICATION`: `targetCustomerId` opcional; `_active_notifications_for_customer` descarta las dirigidas a otro cliente.
- Config (`rewards`): `blockedNoticeDays: [20, 27]`, `blockedGraceDays: 0` (opción a, apagada), `clabeReminderOnActivation: True`.

### 1.5 Reglas de negocio

- Estado por beneficiaria del mes M: `pagado` si el mes contable está `PAID` con recibo no anulado; `sin_clabe` si `totalConfirmed > 0` y la ficha no tiene `clabeInterbancaria`; `listo` en el resto con `totalConfirmed > 0`. `totalConfirmed` es el mismo número que muestra la ficha (`_con_comisiones`).
- El lote reutiliza la validación de `handle_admin_receipt` refactorizada en `_registrar_pago(cid, month_key, asset, batch_id=None)`; las reglas `CLABE_REQUIRED` y `ALREADY_PAID` se aplican por fila.
- Aviso de CLABE: (1) en `handle_apply_rewards`, cuando `se_activo` y la ficha no tiene CLABE y `clabeReminderFirstAt` está vacío; (2) en `handle_confirm_commissions`, para cada beneficiaria de la cadena con filas recién confirmadas, sin CLABE y sin `clabeReminderAt` en ese mes. Nunca más de un correo por mes por motivo; respeta `doNotContact`.
- Producto que salva (fórmula compartida con C, §3.5): `faltan = 20 − netVP_mes`; para cada producto activo en tienda con `vpPoints > 0`: `tasa = _resolve_discount_rate(tiers, netVolume_mes + precio)`, `vpNeto = vpPoints × (1 − tasa)`, `unidades = ceil(faltan / vpNeto)`, `costo = precio × unidades × (1 − tasa)`; se elige el menor `costo`. A implementa `_producto_que_salva` en `pagos_handlers`; I2 unifica con `checkout_handlers.sugerir_producto_activacion` al integrar.
- Gracia (opción a, apagada): si `blockedGraceDays > 0` y una socia se activa en los primeros N días del mes, `handle_apply_rewards` reevalúa también las bloqueadas del mes anterior (`_reevaluate_blocked_rows(chain, mes_anterior)`). Con 0 no cambia nada.
- Avisos del tablero: `commissions_ready`/`commissions_no_clabe` sustituyen al aviso genérico `commissions`; `resolveWarning` los manda a Clientes.

### 1.6 Pruebas mínimas

`test_pagos_mes.py`: listado con los tres estados y totales cuadrados contra el ledger; CSV con solo las listas y CLABE completa; lote con una sin CLABE (queda en `skipped`, el resto pagado, un solo asset, correo por beneficiaria); deshacer una fila del lote vuelve el mes a pendiente y no toca las demás; `test_avisos_clabe.py`: correo al activarse sin CLABE una sola vez; correo al confirmar la primera comisión; sin correo con `doNotContact`; notificación dirigida solo la ve su cliente; `test_avisos_bloqueadas.py`: el día 20 avisa con el producto correcto (caso Bety: 18 VP, tasa 10 %, Naplus), el 21 no, el 27 sí, dos llamadas el mismo día un solo correo; gracia apagada no reevalúa el mes anterior y con `blockedGraceDays=5` sí; `test_ruteo` regenerado para `commissions_lambda`.

### 1.7 Archivos

**Propios**: `Micro-lambda-GMF/python/pagos_handlers.py`, `commissions_lambda.py`, `dashboard_lambda.py` (solo `get_admin_warnings`), `tests/test_pagos_*.py`, `tests/test_avisos_*.py`, `tests/rutas/commissions_lambda.json`, `gamificacion-multinivel-f/src/app/pages/admin/pagos-mes/**`, `services/pagos.service.ts`, `models/pagos.model.ts`.
**Compartidos (edit mínimo)**: `dashboard_common.py` (`_active_notifications_for_customer`: filtro `targetCustomerId`), `core/config.py` (claves en `rewards`), `admin.component.ts` (`imports`, `resolveWarning`), `admin.component.html` (montaje `<app-pagos-mes [month]="…">` al final de Clientes), `models/admin.model.ts` (`AdminCustomer.commissionsPrevStatus` admite `'sin_clabe'`), `openapi-aws.yaml`.

---

## 2. Paquete B · `modo-cliente-y-plan` (propuestas 1, 2 y 3)

### 2.1 Objetivo

Que quien llega por un producto compre como cliente sin ver red, VP, comisiones, CLABE ni datos fiscales; que cada compra le diga cuánto habría ahorrado como socia y la lleve a una página que explica el plan completo con ejemplos sencillos tomados de la configuración real; y que un botón cambie su cuenta a modo socio. Los socios existentes no cambian.

### 2.2 Diseño funcional

**Modo de la cuenta.** Todo cliente tiene `mode ∈ {cliente, socio}`. Nace `cliente` al registrarse (landing con o sin código, tienda, invitado que después crea cuenta, alta desde el POS). Pasa a `socio` por tres caminos: pulsa "Activar modo socio"; alguien se registra con su código (ya tiene red); o el motor le crea una fila de comisión. Las fichas anteriores a esta ronda (sin atributo) son `socio`. Un admin puede cambiar el modo desde la ficha (misma ruta con `customerId`).

**Tienda y carrito (modo cliente e invitados).** Bajo el total: *"Como socia habrías ahorrado **$X** en esta compra"* (o, si el proyectado del mes no alcanza el primer tramo: *"Como socia, con $Y más de compra este mes tendrías 10 % de descuento"*) y el enlace "Conoce el modo socio". Se pinta con `ui-ahorro-socio` (§2.6); en tienda lo monta B (barra inferior fija), en carrito lo monta C (resumen de escritorio y cajón móvil).

**Confirmación de pedido** (`pages/order-status`): misma frase con el ahorro **guardado en el pedido** (`partnerSavings`) y botón "Activar modo socio" que lleva a `/#/modo-socio?desde=orden&id=ORD-…`. **Correo de pago**: párrafo equivalente con enlace.

**Landing "Modo socio"** (`pages/modo-socio/`, ruta pública `modo-socio`): una sola página, orden fijo: (1) *"Qué cambia si activas el modo socio"* (tres frases: descuento por volumen, comisiones por tu red, tu propio código); (2) *"Las tres medidas, con una sola definición"*: **PC** = puntos de lista de cada producto (1 PC ≈ $50 de precio de lista), **VP** = los PC de lo que pagas en el mes, contados sobre el precio ya con descuento (`PC × neto ÷ bruto`), **VG** = tus VP más los de tu red hasta 5 niveles; (3) *"Activación"*: 20 VP netos al mes (≈ $1,000), ejemplo con dos productos reales del catálogo (los dos más baratos con PC), incluido el caso "20 PC de lista con 10 % de descuento = 18 VP: no activa"; (4) *"Tu descuento"*: la tabla única (`ui-tabla-descuento` en modo `context="plan"`) con un ejemplo por tramo calculado (compra $1,200 → 10 % → pagas $1,080; $2,500 → 20 %…); (5) *"Lo que ganas por tu red"*: tabla de generaciones con porcentaje, requisito en palabras ("2 directas activas", "80 PC personales y 2 líneas con 300 PC") y ejemplo numérico ("si una referida directa compra $1,000, ganas $100; si ella refiere a alguien que compra $1,000 y tú tienes 2 directas activas, ganas $50"); compresión dinámica en una frase; (6) *"Cómo y cuándo se paga"*: pendiente al pagar el pedido, confirmada al entregarse, bloqueada si ese mes no estás activa (se recalcula si te activas antes del cierre; se pierde al cerrar; avisos los días 20 y 27), depósito el día 10 del mes siguiente a tu CLABE; (7) *"Qué datos te pedimos y cuándo"*: registro → nombre, correo, teléfono; activar modo socio → nada más; primera comisión confirmada → CLABE; antes de facturar comisiones (si aplica) → constancia, INE, CURP (lista desde `customerDocumentTypes`); (8) rangos y bonos, en una tabla breve (`rankThresholds`, `rules` activas); (9) botón **"Activar modo socio"**: con sesión, llama la ruta y redirige al panel ya en modo socio con el mensaje "Tu cuenta ya está en modo socio"; sin sesión, lleva a registro/login con `?next=modo-socio`. Todos los números vienen de `GET /catalog/plan`; ningún porcentaje va escrito en el HTML.

**Panel del cliente** (`user-dashboard`, modo cliente): se ocultan `#red`, `#volumen`, `#comisiones`, `#links` (código y enlace de referido), el bloque de CLABE y el de documentos fiscales (`/perfil` también oculta CLABE y documentos). Se muestran: pedidos, recompra, campañas, patrocinadora/coach (contacto para pedidos), y un bloque **"Tu cuenta en modo cliente"** con tres indicadores: *"Este mes has comprado $X"*, *"Como socia habrías ahorrado $Y este mes"* (suma de `partnerSavings` de los pedidos pagados del mes), *"Qué ganarías"* (una línea: "si dos amigas compraran $1,000 cada una, ganarías $200 al mes") y el botón "Conoce el modo socio". En modo socio el panel es el actual, más `ui-tabla-descuento` en `#volumen` (B la monta ahí) y, si el `sponsor` trae `isCoach`, se pinta "Tu coach: {nombre} · WhatsApp" (F lo expone; §6).

**Back office**: columna "Modo" (Cliente/Socio) en la lista de Clientes y etiqueta en la ficha, con fecha de activación.

**Aviso de privacidad** (`components/privacy-notice`): input `mode`; en `cliente` no menciona red, comisiones ni datos bancarios.

### 2.3 Contratos de API

| Método y ruta | Privilegio | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `GET /catalog/plan` | pública | — | `{plan}` (§2.4) | — |
| `GET /customers/modo` | sesión propia | — | `{mode, modeSince, modeActivatedAt, indicators:{monthSpend, monthSavingsIfPartner, nextTier:{rate,missing}, exampleEarnings}}` | 401 |
| `POST /customers/modo-socio` | sesión propia; admin con `customer_add` puede pasar `customerId` | `{customerId?, acceptedPlanVersion}` | `200 {mode:"socio", modeActivatedAt, alreadyPartner:bool}`; idempotente | 401, 404 |
| `POST /customers/ahorro-socio` | pública | `{items:[{price, quantity}], customerId?}` | `{gross, monthNet, projected, rate, savings, nextTier:{rate, missing}}` | 400 |

`GET /customers/dashboard` (existente) añade `mode` y, en modo cliente, `clientIndicators` (mismo objeto que `indicators` arriba) y vacía `networkMembers`, `commissions`, `vp`, `vg`, `rank`, `bonuses`; `goals` se reduce a las de consumo (`_goal_activacion` se reetiqueta "Meta de compra del mes"). `GET /customers/getall` y `GET /customers/{id}` añaden `mode`. `POST /auth/login` añade `user.mode`.

### 2.4 `GET /catalog/plan` (forma fija)

```json
{"plan": {
  "version": "abril-2026",
  "unidades": {"mxnPerVp": 50, "maxLevels": 5,
    "pc": "…", "vp": "…", "vg": "…"},
  "activacion": {"vpNetos": 20, "pesosAprox": 1000,
    "ejemplos": [{"productos": [{"id": "…", "name": "…", "price": 480, "pc": 10, "qty": 2}], "bruto": 960, "rate": 0.0, "vp": 20, "activa": true},
                 {"productos": […], "bruto": 1090, "rate": 0.10, "vp": 18, "activa": false}]},
  "descuento": {"tramos": [{"min": 0, "max": 1000, "rate": 0.0}, …],
    "ejemplos": [{"compraMes": 1200, "rate": 0.10, "descuento": 120, "pagas": 1080}, …]},
  "generaciones": [{"gen": 1, "rate": 0.10, "requisitos": {"activeDirects": 0, "personalPC": 0, "lines": 0, "pcPerLine": 0},
    "requisitoTexto": "sin requisito", "ejemplo": {"compraReferido": 1000, "comision": 100}}, …],
  "compresionDinamica": true,
  "pago": {"dia": 10, "estados": ["pendiente", "confirmada", "bloqueada", "pagada"], "bloqueo": {"avisos": [20, 27], "graciaDias": 0}},
  "datos": [{"cuando": "registro", "que": ["nombre", "correo", "teléfono"]}, {"cuando": "modo socio", "que": []},
            {"cuando": "primera comisión confirmada", "que": ["CLABE"]}, {"cuando": "facturación", "que": ["Constancia de situación fiscal", "INE", "CURP"]}],
  "rangos": [{"rank": "BRONCE", "vgMin": 4500, "vpMin": 60, "minLines": 3, "monthlyBonus": 500}, …],
  "bonos": [{"id": "inicio_rapido", "name": "…", "notes": "…"}]
}}
```

Los ejemplos se **calculan** con `_resolve_discount_rate` y los productos activos más baratos con PC; los textos de requisito se generan de los números.

### 2.5 Cambios de datos y reglas

- `CUSTOMER`: `mode` ("cliente"|"socio"), `modeSince`, `modeActivatedAt`, `modeReason` ("registro"|"solicitud"|"referido"|"comision"|"admin"), `acceptedPlanVersion`.
- `ORDER`: `partnerSavings` (Decimal), `partnerSavingsRate`, `partnerSavingsProjected` (escritos por `_calculate_totals` cuando el comprador es cliente o invitado; en modo socio valen 0).
- `modo_de(customer)`: `mode` si es válido; si no, `"socio"`. `asegurar_socio(customer_id, motivo)`: si está en cliente, lo pasa a socio y anota motivo; no manda correo salvo motivo `solicitud` ("Bienvenida al modo socio", con enlace a la landing y al panel).
- **Descuento**: en modo cliente `_calculate_totals` devuelve `discountRate 0` (paga precio de lista) y calcula `partnerSavings = gross × _resolve_discount_rate(tiers, netVolume_mes + gross)`. En modo socio la escalera se aplica como hoy. El volumen del mes (`netVolume`, `netVP`) se sigue acreditando en modo cliente (así el proyectado es real y la activación es inmediata al cambiar de modo); las compras de un cliente **sí** pagan comisión a su línea ascendente (el motor no cambia).
- **Invitados**: mismo cálculo que un cliente con `monthNet = 0`.
- **POS**: E lee `customer.mode`; en modo cliente el descuento de socio es 0 (§5.5).
- **Indicador "qué ganarías"**: `2 × 1000 × commissionLevels[0].rate` con los números de config.

### 2.6 Componentes compartidos que B construye

`components/ui-tabla-descuento/ui-tabla-descuento.component.ts`, selector **`ui-tabla-descuento`**, standalone:

```ts
@Input() tiers: Array<{ min: number; max: number | null; rate: number }> = [];
@Input() mxnPerVp = 50;
@Input() activationVp = 20;
@Input() monthNet = 0;        // neto acumulado del mes (MPN)
@Input() monthVp = 0;         // VP netos acumulados del mes
@Input() cartGross = 0;       // bruto del carrito o de la venta en curso (0 si no aplica)
@Input() cartPc = 0;          // PC de lista del carrito o venta
@Input() mode: 'cliente' | 'socio' = 'socio';
@Input() context: 'panel' | 'carrito' | 'pos' | 'plan' = 'panel';
@Input() compact = false;
@Output() activateRequested = new EventEmitter<void>();  // solo en modo cliente
```

Vocabulario fijo: título "Tu descuento este mes"; "Tramo actual: 10 % (de $1,000 a $1,999)"; "Con esta compra: 20 % (llegas a $2,300)"; "Siguiente tramo: 30 %, te faltan $700"; "Activación: 20 VP netos · llevas 18 · este pedido suma 5.4"; nota permanente "Tus VP se cuentan sobre el precio ya con descuento: 20 PC con 10 % = 18 VP". En `context="pos"` el texto habla en tercera persona ("El cliente está en el tramo…"). En modo cliente muestra los tramos y el ahorro hipotético y el botón "Activar modo socio" (emite `activateRequested`).

`components/ui-ahorro-socio/ui-ahorro-socio.component.ts`, selector **`ui-ahorro-socio`**:

```ts
@Input() gross = 0;           // bruto de la compra
@Input() monthNet = 0;
@Input() mode: 'cliente' | 'socio' | 'invitado' = 'invitado';
@Input() variant: 'inline' | 'card' = 'inline';
@Input() orderId?: string;    // para el enlace ?desde=orden
```

Calcula con `PlanSocioService` (cachea `GET /catalog/plan`); en modo socio no pinta nada.

`services/plan-socio.service.ts`: `plan$`, `ahorroComoSocio(gross, monthNet)`, `activarModoSocio()`.

### 2.7 Pruebas mínimas

`test_modo_cliente.py`: registro nuevo nace cliente; ficha sin atributo es socio; registro con código convierte al líder; fila de comisión convierte al beneficiario; activación idempotente; admin cambia modo; `_calculate_totals` en modo cliente no descuenta y guarda `partnerSavings` correcto (casos $960 → 0 con texto de $40 faltantes; $1,200 → $120; con acumulado $900 + $300 → 10 % sobre $300); en modo socio `partnerSavings = 0`; dashboard en modo cliente sin red/comisiones y con `clientIndicators`; `test_plan_publico.py`: `GET /catalog/plan` refleja cambios en `discountTiers` y `commissionLevels`, ejemplos cuadran con `_resolve_discount_rate`, sin números literales en el handler; correo `paid` de un cliente lleva el párrafo y el de un socio no. Frontend: `ng build`; prueba manual en el harness: Karla compra en modo cliente y ve el ahorro en tienda, carrito, confirmación y correo; activa modo socio y aparecen las secciones.

### 2.8 Archivos

**Propios**: `modo_handlers.py`, `catalog_lambda.py`, `tests/test_modo_*.py`, `tests/test_plan_publico.py`, `tests/rutas/catalog_lambda.json`, `pages/user-dashboard/**` (excepto `pages/user-dashboard/suscripcion/**`, de H), `pages/user-profile/**` (ocultar CLABE/documentos en modo cliente), `pages/tienda/**`, `pages/landing/**`, `pages/modo-socio/**`, `pages/order-status/**`, `components/ui-tabla-descuento/**`, `components/ui-ahorro-socio/**`, `components/privacy-notice/**`, `services/plan-socio.service.ts`, `services/user-dashboard-control.service.ts`, `models/plan-socio.model.ts`, `models/user-dashboard.model.ts` (campos `mode`, `clientIndicators`).
**Compartidos (edit mínimo)**: `order_lambda.py` (`_calculate_totals`), `customer_lambda.py` (dos líneas + `_EXTENSIONES`), `auth_utils.py` (tres líneas), `commissions_lambda.py` (una línea en `_distribute_commissions`), `core/order_emails.py` (rama `paid`), `app.routes.ts`, `admin.component.html` (columna y etiqueta de modo), `models/admin.model.ts` (`AdminCustomer.mode?`, `AdminOrder.partnerSavings?`), `services/auth.service.ts` (`AuthUser.mode?`; C es dueño del archivo, B añade solo el campo), `openapi-aws.yaml`.

---

## 3. Paquete C · `checkout-y-sesion` (propuestas 5, 6, 7, 11 y 17)

### 3.1 Objetivo

Que el carrito diga lo que va a cobrar y lo que falta para activarse (y ofrezca el producto que lo cierra), que "Recoger en sucursal" solo aparezca cuando de verdad se puede, que pedir factura sea una casilla, y que nadie tenga que recuperar la contraseña en cada visita.

### 3.2 Diseño funcional

**Completa tu activación** (carrito): junto al aviso existente "Con este pedido llegas a 18.9 de 20 VP" aparece la tarjeta *"Completa tu activación: agrega 1 Naplus ($280, +5.4 VP) y llegas a 24.3 VP"* con botón "Agregar". Se recalcula al cambiar el carrito o el cupón. Solo en modo socio (en modo cliente no hay meta de activación).

**Envío visible**: en el carrito, antes de capturar dirección: *"Envío desde $129 · Gratis en compras de $1,000 o más"* (números de config) y, con la dirección, la cotización real. La regla de envío gratis se mide sobre el **subtotal bruto** (decisión §13) y el carrito lo dice: *"Te faltan $40 de compra para envío gratis"*. En la tienda, B usa el mismo endpoint para la barra inferior.

**Recoger en sucursal**: la opción solo se muestra si existe al menos una sucursal con `allowPickup` en la ciudad o estado capturados **y** con existencia de todo el carrito; si no hay dirección aún, se muestra con la lista de ciudades disponibles ("Disponible en: Ciudad de México"). Las sucursales sin existencia aparecen deshabilitadas con el motivo ("No tiene Magnesio").

**Quiero factura**: casilla en el checkout (socios, clientes e invitados). Al marcarla se piden RFC, razón social, régimen fiscal (lista SAT acotada), CP fiscal, uso de CFDI y correo; se prellenan desde el perfil (`rfc`, `curp`, nombre). El pedido queda con `invoiceStatus = "solicitada"`; en el back office el pedido lleva la insignia "Factura solicitada" con los datos y el botón "Marcar factura emitida" (sube el PDF, opcional). Sin timbrado CFDI en esta ronda; el correo de pago dice *"Solicitaste factura: la recibirás por correo en los próximos días hábiles"*.

**Sesión**: casilla "Recordarme en este dispositivo" en el login (marcada por omisión): con ella la sesión dura 30 días y se guarda en `localStorage`; sin ella dura 24 horas y va en `sessionStorage`. **Enlace de acceso por correo**: en el login, "Entrar con un enlace por correo" pide el correo y manda un enlace de un solo uso (15 minutos) que abre `/#/login?enlace=TOKEN` y crea la sesión. **Recuperación**: el correo dice *"Si pediste varios códigos, usa el más reciente; los anteriores dejan de valer"*, el código caduca a los 15 minutos (hoy no se comprobaba `expiresAt`: se corrige) y el sistema acepta cualquiera de los **tres últimos** emitidos dentro de su vigencia y no usados (así el primero no "se invalida" si el correo llega tarde).

### 3.3 Contratos de API

| Método y ruta | Privilegio | Cuerpo / query | Respuesta | Errores |
|---|---|---|---|---|
| `GET /orders/checkout/envio-info` | pública | `?subtotal=` | `{baseRateMxn, freeShippingMin, basis:"gross", missingForFree, freeNow:bool}` | — |
| `POST /orders/checkout/sugerencia-activacion` | sesión propia | `{customerId, items:[{productId, quantity, price}], couponCode?}` | `{applies:bool, vpNow, vpAfterCart, gap, suggestion:{productId, name, price, units, netVpPerUnit, cost, vpAfter}}` | 401 |
| `POST /orders/checkout/sucursales-recoger` | pública | `{city?, state?, postalCode?, items:[{productId, quantity}]}` | `{available:bool, cities:[…], stocks:[{id, name, location, city, state, canPickup:bool, missing:[nombre…]}]}` | — |
| `POST /orders/{id}/factura` | dueño, invitado por id, o admin | `{rfc, razonSocial, regimenFiscal, cpFiscal, usoCfdi, email}` | `200 {invoiceStatus:"solicitada", invoiceRequestedAt}` | 400 RFC inválido (regex SAT), 409 pedido cancelado o ya emitida |
| `POST /orders/{id}/factura/emitida` | `order_mark_paid` | `{folioFiscal?, name?, contentType?, contentBase64?}` | `200 {invoiceStatus:"emitida", invoiceIssuedAt, invoiceFileUrl?}` | 409 sin solicitud |
| `POST /auth/login` (existente) | — | + `rememberMe:bool` | + `user.mode` (B), `expiresAt` | — |
| `POST /auth/enlace-acceso` | pública | `{email, rememberMe?}` | `200 {ok, message:"Si el correo existe, enviamos un enlace"}` (nunca revela existencia) | — |
| `POST /auth/enlace-acceso/canjear` | pública | `{token, rememberMe?}` | igual que login | 401 token inválido/usado/caducado |
| `POST /auth/password/recovery`, `/reset` (existentes) | — | sin cambios de forma | — | 401 con mensaje "Código inválido o caducado: pide uno nuevo" |

`POST /orders/create` acepta `invoiceRequested`, `invoiceData`; `GET /orders/find` acepta `invoiceStatus=solicitada`. `GET /inventory/pickup-stocks` no cambia (queda para compatibilidad).

### 3.4 Cambios de datos

- `ORDER`: `invoiceRequested`, `invoiceStatus` ("no_aplica"|"solicitada"|"emitida"), `invoiceData{rfc, razonSocial, regimenFiscal, cpFiscal, usoCfdi, email}`, `invoiceRequestedAt`, `invoiceIssuedAt`, `invoiceFolio`, `invoiceFileUrl`.
- `STOCK`: `city`, `state` (formulario de almacén).
- `LOGIN_LINK` (bucket nuevo): `{tokenHash, email, expiresAt, used, rememberMe, createdAt}`; se busca por `_get_by_id("LOGIN_LINK", tokenHash)`.
- `PASSWORD_RESET`: `otpHashes: [{hash, expiresAt, used}]` (últimos tres); `otpHash` se conserva por compatibilidad.
- `SESSION`: `rememberMe`, `expiresAt` (informativo; el TTL manda).
- Config: `shipping.freeShippingBasis: "gross"` (`"net"` conserva la regla actual), `shipping.baseRateMxn: 129`; `checkout: {invoiceEnabled: True, regimenesFiscales: [...]}`; `auth: {sessionShortSeconds: 86400, loginLinkMinutes: 15, recoveryCodesKept: 3}`.

### 3.5 Reglas de negocio

- Sugerencia de activación: misma fórmula que §1.5 (`sugerir_producto_activacion(products, gap_vp, rate_fn)` en `checkout_handlers`, función pura y probada); el `rate` se calcula con `netVolume_mes + bruto del carrito + precio del producto`; con cupón, `vpNeto` usa el factor neto/bruto del carrito. Solo se sugiere si `0 < gap ≤ 20`.
- Envío gratis: `basis = grossSubtotal` cuando `freeShippingBasis == "gross"`; `handle_create_order` usa la misma regla que el carrito (hoy compara `netTotal`); `shippingFreeApplied` se conserva.
- Sucursales: coincidencia por `state` normalizado (sin acentos, mayúsculas) o `city`; existencia con `_faltantes_en_sucursal` (existente).
- Factura: RFC con la expresión del SAT (12/13 caracteres); un pedido cancelado o reembolsado pasa a `invoiceStatus = "no_aplica"`.
- Sesión: `rememberMe` → TTL `SESSION_TTL_SECONDS` (30 días); sin él → `auth.sessionShortSeconds`. El enlace de acceso solo se emite para cuentas verificadas (`emailVerified != False`); un token se canjea una vez.

### 3.6 Pruebas mínimas

`test_checkout_activacion.py` (Bety: 18 VP + Naplus 280/5.4 VP → sugerencia Naplus; sin hueco no sugiere; con cupón cambia el neto), `test_checkout_envio.py` (gratis sobre bruto $1,090 con 10 % → gratis; `basis="net"` → $129; `envio-info` con faltante), `test_checkout_sucursales.py` (Mérida sin sucursal → `available false` con ciudades; CDMX con Magnesio faltante → `canPickup false` y `missing`), `test_checkout_factura.py` (solicitud, RFC inválido, emitida con archivo, cancelación → `no_aplica`, filtro en `find`), `test_sesion.py` (TTL corto/largo, enlace de acceso emitido/canjeado/reusado/caducado, no revela correos, recuperación con dos códigos: ambos válidos, caducidad, mensaje). Frontend: login recuerda, `sessionStorage` sin recordarme, carrito muestra sugerencia y envío, pickup condicionado, factura visible en el back office.

### 3.7 Archivos

**Propios**: `checkout_handlers.py`, `auth_utils.py`, `tests/test_checkout_*.py`, `tests/test_sesion.py`, `tests/rutas/auth_utils.json`, `pages/carrito/**`, `pages/login/**`, `pages/reset-password/**`, `services/auth.service.ts`, `services/checkout.service.ts`, `models/checkout.model.ts`, `guards/auth.guard.ts`.
**Compartidos (edit mínimo)**: `order_lambda.py` (`handle_create_order`, `handle_list_orders`, import + `_EXTENSIONES`), `inventory_lambda.py` (`handle_stocks`: campos `city`, `state`), `core/config.py`, `core/order_emails.py` (**no**: la frase de factura en el correo `paid` la añade B en su párrafo leyendo `order.invoiceRequested`; C se lo comunica), `admin.component.html` (detalle de pedido: insignia y bloque de factura; formulario de almacén: dos campos), `admin.component.ts` (`markInvoiceIssued` al final), `services/real-api.service.ts` (`actorHeaders` público y lectura `sessionStorage ?? localStorage`), `models/admin.model.ts` (`AdminOrder.invoice*`, `AdminStock.city/state`), `tests/rutas/order_lambda.json`, `openapi-aws.yaml`. Montaje de `ui-ahorro-socio` en el carrito (dos líneas, resumen y cajón móvil) cuando B esté integrado; si C se integra antes, lo monta I2.

---

## 4. Paquete D · `almacen-despacho-paqueteria` (propuestas 9, 13, 20 y 23a)

### 4.1 Objetivo

Que Beto despache diez pedidos en una operación con la lista de surtido calculada, que la guía se genere o importe en vez de copiarse de WhatsApp, que los envíos se cierren solos con el rastreo o a los N días, que su sucursal por defecto sea la suya y que el resumen de turno se escriba solo.

### 4.2 Diseño funcional

**Despacho en bloque** (`pages/admin/despacho/`, ruta `admin/despacho`, privilegio `order_mark_shipped`): (1) selector de bodega (por defecto la del empleado); lista de pedidos **pagados** con envío a domicilio (casillas, "Seleccionar todos"); (2) botón "Calcular surtido" → tabla consolidada por producto: necesario, existencia en la bodega, semáforo (verde alcanza / rojo falta N) y, en rojo, "Del Valle tiene 4"; botón "Imprimir lista"; si falta algo, "Despachar" queda deshabilitado con el motivo escrito ("Faltan 2 Magnesio en Bodega Central; Del Valle tiene 4: transfiere o quita el pedido ORD-…"); (3) guías: por fila, paquetería y guía capturadas a mano, o "Importar CSV" (`orderId,carrier,tracking`), o "Generar guías con Envia" cuando `carrierIntegration.enabled`; (4) "Despachar N pedidos" con modal que enumera folios, guías y bodega; al terminar, confirmación con los folios que quedaron `shipped` **leídos de la respuesta** y los que fallaron con motivo.

**Sucursal por defecto**: en Stocks y en Despacho, "Mi bodega por defecto: Bodega Central · Cambiar" (se guarda en el perfil del empleado); el POS también arranca con ella.

**Rastreo y cierre**: tarea `rastrear` (diaria) consulta la paquetería para pedidos `shipped` con guía y marca `delivered` con fecha y quién firmó cuando el carrier lo reporta; tarea `cerrar`: a los `askDays` (7) sin entrega manda "¿Te llegó tu pedido?" (con botón "Sí, llegó" que marca entregado por el cliente, y "Aún no" que abre soporte); a los `autoCloseDays` (10) marca entregado con `deliveredBy = "auto"` y nota interna. Acciones urgentes ya cuenta "pagados sin envío"; D añade "enviados hace más de 7 días sin entrega" en su propia pantalla (no en `get_admin_warnings`, que es de A).

**Resumen de turno** (`pages/admin/resumen-turno/`, ruta `admin/resumen-turno`, privilegio `access_screen_stats`; un empleado ve el suyo): por empleado y fecha: pedidos despachados (folios, guías), entregados, transferencias creadas/recibidas (con faltantes), entradas y mermas, ventas y cortes del POS, con enlace a cada folio, y botón "Copiar resumen" (texto plano para WhatsApp).

### 4.3 Contratos de API (prefijo `/inventory`)

| Método y ruta | Privilegio | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `GET /inventory/despacho/pendientes?stockId=` | `order_mark_shipped` | — | `{orders:[{id, customer, createdAt, paidAt, daysSincePaid, items:[…], city, state, hasInvoiceRequest}]}` (pagados, `deliveryType = delivery`) | — |
| `POST /inventory/despacho/surtido` | `order_mark_shipped` | `{stockId, orderIds:[…]}` | `{stockId, canDispatch:bool, lines:[{productId, name, needed, available, status:"ok"|"short", short:N, elsewhere:[{stockId, name, available}]}], blockedOrders:[{orderId, reason}]}` | 400 sin pedidos; 404 bodega |
| `POST /inventory/despacho/enviar` | `order_mark_shipped` | `{stockId, shipments:[{orderId, carrier, trackingNumber}], csv?:"orderId,carrier,tracking\n…", generateLabels?:bool}` | `{shipped:[{orderId, trackingNumber, carrier, labelUrl?}], failed:[{orderId, reason}]}`; cada pedido pasa por `order_lambda.handle_update_status(oid, {status:"shipped", stockId, shippingType:"carrier", shippingCarrier, trackingNumber, dispatchLines: items}, headers)` (misma salida de inventario y correo que hoy). Todo o nada **no**: se despacha lo que se puede y se informa el resto; el surtido ya se validó antes. | 409 si el surtido no alcanza (`code: "STOCK_SHORT"`, mismas líneas que `surtido`) |
| `GET /inventory/despacho/preferencias` | sesión de empleado | — | `{defaultStockId}` | 401 |
| `PUT /inventory/despacho/preferencias` | sesión de empleado | `{defaultStockId}` | `{defaultStockId}` | 404 bodega |
| `POST /inventory/envios/rastrear` (programable) | `order_mark_delivered` o superadmin | `{orderIds?, dryRun?}` | `{checked, delivered:[{orderId, deliveredAt, signedBy}], inTransit, errors}` | — |
| `POST /inventory/envios/cerrar` (programable) | `order_mark_delivered` o superadmin | `{dryRun?}` | `{asked:[orderId…], closed:[orderId…]}` | — |
| `POST /inventory/envios/{orderId}/confirmar-entrega` | pública con `?token=` firmado (enlace del correo) | — | `{status:"delivered"}` | 401 token |
| `GET /inventory/turno/resumen?userId=&date=YYYY-MM-DD` | `access_screen_stats` o el propio usuario | — | `{user, date, dispatched:[…], delivered:[…], transfers:{created, received}, entries, damages, pos:{sales, cuts}, counters, text}` (fuente: `ADMIN_EVENT` con `actorUserId`, `INVENTORY_MOVEMENT`, `POS_SALE`, `POS_CASH_CUT`, `ORDER.shippedBy/deliveredBy`) | — |

`carriers.py` (no expone rutas): `class Paqueteria` con `generar_guia(order) -> {carrier, trackingNumber, labelUrl}` y `rastrear(carrier, trackingNumber) -> {status:"in_transit"|"delivered"|"exception", deliveredAt?, signedBy?, events[]}`; implementaciones `EnviaPaqueteria` (endpoints en `ENVIA_GENERATE_URL`, `ENVIA_TRACK_URL`, clave `ENVIA_API_KEY`; nombres de endpoint a confirmar con la documentación vigente de Envia) y `PaqueteriaSimulada` (entrega a los `simDeliveryDays` con firma "Recibió: {recipientName}") usada por pruebas y por el harness cuando `provider = "simulada"`.

### 4.4 Cambios de datos

- `ORDER`: `shippedAt`, `shippedBy`, `deliveredBy` ("empleado id"|"carrier"|"cliente"|"auto"), `deliverySignedBy`, `carrierDeliveredAt`, `trackingEvents[]`, `labelUrl`, `deliveryCheckEmailSentAt`, `autoClosedAt`, `dispatchBatchId`.
- `DISPATCH_BATCH` (bucket nuevo): `{batchId, stockId, orderIds, shipments, createdBy, createdAt, results}`.
- `EMPLOYEE`: `defaultStockId`.
- Config: `shipping.carrierIntegration: {enabled: False, provider: "envia", autoLabel: False, trackingEnabled: False, askDays: 7, autoCloseDays: 10, simDeliveryDays: 3}`.

### 4.5 Reglas de negocio

- Solo se despachan pedidos `paid` con `deliveryType = delivery`; un pedido pickup nunca entra al bloque.
- El surtido consolida por `productId` y compara contra `STOCK.inventory` de la bodega; `elsewhere` lista las demás bodegas con existencia ≥ faltante.
- `handle_update_status(shipped)` graba `shippedAt` y `shippedBy` (edit de D); `delivered` acepta `deliveredAt`, `deliverySignedBy`, `deliveredBy` del body (solo cuando el actor es admin/superadmin) y los guarda.
- Rastreo: solo pedidos con `trackingNumber` y `carrierIntegration.trackingEnabled`; excepciones se anotan en `trackingEvents` sin cambiar estado.
- Cierre: `askDays` y `autoCloseDays` cuentan desde `shippedAt` (si falta, `updatedAt` cuando pasó a shipped); un pedido con `deliveryCheckEmailSentAt` no vuelve a recibir el correo; el cierre automático dispara `ORDER_DELIVERED` (confirma comisiones) como una entrega normal.
- El resumen de turno se calcula al vuelo (sin persistir); el `text` es el mensaje que hoy Beto redacta a mano.

### 4.6 Pruebas mínimas

`test_despacho_bloque.py` (surtido con faltante y `elsewhere`; despacho de 3 pedidos con guías por CSV: los tres `shipped`, inventario descontado una sola vez, correo de envío por pedido; pedido pickup rechazado; bodega por defecto guardada y leída), `test_paqueteria.py` (`PaqueteriaSimulada` genera guía y entrega a los 3 días; `rastrear` marca entregado con firma y confirma comisiones; `cerrar` manda "¿te llegó?" al día 7 una sola vez y cierra al 10 con `deliveredBy = auto`; enlace de confirmación del cliente), `test_turno_resumen.py` (un turno con despacho, recepción con faltante y venta POS aparece completo y el `text` contiene los folios). Harness: con el reloj a +7 y +10 días se ven el correo y el cierre.

### 4.7 Archivos

**Propios**: `despacho_handlers.py`, `carriers.py`, `shipping_lambda.py`, `inventory_lambda.py` (funciones de envíos y transferencias, `_route_stocks`, `_EXTENSIONES`), `tests/test_despacho_*.py`, `tests/test_paqueteria.py`, `tests/test_turno_resumen.py`, `tests/rutas/inventory_lambda.json`, `pages/admin/despacho/**`, `pages/admin/resumen-turno/**`, `services/despacho.service.ts`, `models/despacho.model.ts`.
**Compartidos (edit mínimo)**: `order_lambda.py` (bloques `shipped` y `delivered` de `handle_update_status`), `core/order_emails.py` (rama `delivery_check`), `core/config.py` (`shipping.carrierIntegration`), `app.routes.ts` (dos entradas), `admin.component.html` (botón en barra de Pedidos y en Estadísticas), `admin.component.ts` (`applyEmployeeDefaultStock` + una llamada), `models/admin.model.ts` (`AdminOrder.shippedAt?`, `deliveredBy?`, `deliverySignedBy?`; `AdminEmployee.defaultStockId?`), `openapi-aws.yaml`.

---

## 5. Paquete E · `caja-arqueo` (propuestas 16 y 8, solo POS)

### 5.1 Objetivo

Que el corte de caja cuadre el efectivo físico contra el esperado y diga a dónde va el dinero; que el retiro sea guiado; que en el POS ningún botón esté mudo; y que se pueda cobrar mitad efectivo, mitad tarjeta.

### 5.2 Diseño funcional

**Corte con arqueo** (`pages/admin/arqueo/`, selector `app-admin-arqueo`, montado en la sección POS en lugar del bloque de corte actual): paso 1 "Efectivo esperado": fondo inicial (lo que dejó el corte anterior) + ventas en efectivo (incluidos abonos en efectivo y la parte en efectivo de pagos mixtos) − retiros = **esperado**, con la lista desplegable de movimientos; paso 2 "Efectivo contado": campo de conteo (opcional por denominaciones: 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1) → **diferencia** en verde/rojo y campo "Motivo de la diferencia" obligatorio si ≠ 0; paso 3 "Destino del efectivo": "Dejar $X como fondo de mañana" y "Retirar $Y" (con código de autorización cuando `Y > 0`, quién lo recibe); paso 4 confirmación con el efecto escrito (*"Se cerrará el corte con N ventas por $T. Fondo: $X. Retiro: $Y a nombre de …. La diferencia de $D queda registrada con motivo."*) → al confirmar, pantalla "Comprobante del corte" con folio `CUT-…`, todos los montos **leídos de la respuesta**, botón "Imprimir" y "Enviar por correo a la gerente" (si `pos.cashCutNotifyEmail`).

**Retiro guiado**: modal en tres pasos (monto con máximo = efectivo disponible, motivo y quién recibe, código) y confirmación con folio `WDR-…` y el efectivo restante leído del servidor.

**Botones que explican por qué**: en el POS, cada botón deshabilitado lleva bajo él el motivo en una línea (`posDisabledReason('cobrar' | 'corte' | 'retiro' | 'parcial' | 'descuento')`): "Sin sucursal vinculada: pide a la gerente que te ligue a una", "No hay ventas desde el último corte", "El pago parcial requiere el código de autorización de la gerente", "Elige al menos un producto", "El cliente no tiene existencia de X en esta sucursal", "En modo cliente no aplica descuento de socio". Las confirmaciones de venta, abono, corte y retiro muestran folio y montos devueltos por el backend, nunca los del formulario.

**Pago mixto**: en "Cobrar", opción "Efectivo + tarjeta/transferencia": dos importes que deben sumar el total (el segundo se autocompleta), cambio calculado sobre el efectivo recibido.

### 5.3 Contratos de API (prefijo `/inventory/pos`)

| Método y ruta | Privilegio | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `GET /inventory/pos/arqueo?stockId=` | `pos_register_sale` | — | `{stockId, attendantUserId, openingCash, cashSales, cashSettlements, cashFromMixed, withdrawals, expectedCash, movements:[{type, id, at, amount}], salesCount, since}` | 400 sin stock |
| `POST /inventory/pos/cash-cut` (existente, ampliado) | `pos_register_sale` | + `cashCounted`, `denominations?`, `differenceReason?`, `withdrawalAmount`, `withdrawalReceiver?`, `authCode?` (obligatorio si `withdrawalAmount > 0`) | `201 {cut:{cashCutId, cashExpected, cashCounted, difference, differenceReason, cashToKeep, withdrawnAmount, withdrawalReceiver, salesCount, …}, control}` | 400 diferencia sin motivo; 400 `cashToKeep + withdrawalAmount ≠ cashCounted`; 403 código |
| `GET /inventory/pos/cash-cuts/{id}` | `pos_register_sale` | — | `{cut}` (para el comprobante) | 404 |
| `POST /inventory/pos/cash-cuts/{id}/enviar` | `pos_register_sale` | `{email?}` | `{sent:true}` (correo con el comprobante en texto y tabla) | 400 sin correo configurado |
| `POST /inventory/pos/withdrawal` (existente) | `pos_register_sale` | + `receiver` | + `control` (ya lo devuelve) | 400 monto > disponible (nuevo) |
| `POST /inventory/pos/sales` (existente) | `pos_register_sale` | + `payments:[{method:"cash"|"card"|"transfer", amount}]` (si viene, sustituye a `paymentMethod`) | + `payments`, `cashPortion`, `change` | 400 si la suma ≠ total; 400 efectivo recibido < parte en efectivo |
| `POST /inventory/pos/sales/{id}/payments` (existente) | `pos_register_sale` | sin cambios (un abono, un método) | — | — |

Compatibilidad: el corte sin `cashCounted` (clientes viejos) sigue funcionando y guarda `cashCounted = cashExpected`, `difference = 0`.

### 5.4 Cambios de datos

- `POS_CASH_CUT`: `cashExpected`, `cashCounted`, `denominations{}`, `difference`, `differenceReason`, `withdrawalReceiver`, `openingCash`, `notifiedTo`.
- `POS_SALE`: `payments[]`, `cashPortion`, `paymentMethod = "mixed"` cuando aplica.
- `POS_WITHDRAWAL`: `receiver`.
- Config (`pos`): `cashCutNotifyEmail: ""`, `denominations: [1000,500,200,100,50,20,10,5,2,1]`, `requireDifferenceReason: True`.

### 5.5 Reglas de negocio

- `expectedCash = openingCash (cashToKeep del último corte) + Σ efectivo de ventas full + Σ amountPaid en efectivo de parciales + Σ abonos en efectivo + Σ cashPortion de mixtas − Σ retiros sin corte`. `_build_pos_cash_control.currentTotal` pasa a usar exactamente esta suma (hoy ignora la parte en efectivo de abonos registrados con `source = settlement` en tarjeta correctamente, pero no sabe de mixtas).
- En el corte: `cashCounted = cashToKeep + withdrawalAmount`; la diferencia es `cashCounted − expectedCash` y se guarda con motivo; el retiro del corte crea un `POS_WITHDRAWAL` ligado (`cashCutId`) con `receiver`.
- El retiro suelto no puede exceder `currentTotal`.
- Pago mixto: `Σ payments = total` (centavo a centavo); `cashPortion` entra a caja; el resto no; con `paymentType = partial` no se admite mixto (una cosa a la vez).
- Modo cliente (B): el POS no aplica descuento de socio si `customer.mode == "cliente"`; el motivo se muestra en el botón de descuento.

### 5.6 Pruebas mínimas

`test_caja_arqueo.py` (esperado con fondo + ventas + abono efectivo + mixta − retiro; corte con diferencia sin motivo → 400; corte con destino fondo/retiro y código; retiro que excede → 400; comprobante por id), `test_pos_mixto.py` (suma incorrecta → 400; venta mixta acredita VP igual que una normal; el corte solo cuenta la parte en efectivo), regresión: los cortes viejos (`test_pos.py`) siguen igual. Frontend: motivos visibles en los cinco botones, confirmaciones con folio del servidor.

### 5.7 Archivos

**Propios**: `caja_handlers.py`, `inventory_lambda.py` (funciones POS listadas en §0.7 y `_route_pos`), `tests/test_caja_*.py`, `tests/test_pos_mixto.py`, `pages/admin/arqueo/**`, `services/caja.service.ts`, `models/caja.model.ts`, sección POS de `admin.component.{ts,html}` (edits localizados).
**Compartidos (edit mínimo)**: `inventory_lambda.py` (entrada en `_EXTENSIONES`, que introduce D), `core/config.py` (`pos`), `admin.component.ts` (`imports`), `models/admin.model.ts` (`PosSale.payments?`, `PosCashCut.cashExpected?…`), `app.routes.ts` (solo si se opta por ruta propia), `tests/rutas/inventory_lambda.json` (compartido con D: cada uno regenera y el integrador vuelve a regenerar), `openapi-aws.yaml`.

---

## 6. Paquete F · `coach-seguimiento` (propuestas 15 y 19)

### 6.1 Objetivo

Que la coach abra una sola pantalla y sepa a quién escribir hoy, con qué mensaje, y que la nota quede sola; y que compradores invitados y registrados tengan la misma ficha, con la coach visible en el panel de quien no tiene patrocinadora.

### 6.2 Diseño funcional

**Seguimiento de hoy** (`pages/admin/seguimiento/`, ruta `admin/seguimiento`, privilegio `access_screen_customers`; botón en la barra de Clientes). Filtros: "Mi cartera" (por omisión) / "Todas"; situación (todas, bienvenida, fría, CLABE pendiente, pedido tardío). Tabla, una fila por persona: nombre y modo (cliente/socio), teléfono con icono de WhatsApp, patrocinadora, ejecutiva asignada, origen, último pedido (folio, fecha, total, estado), días sin compra, días sin contacto, situación (etiqueta), botón "Escribir". Excluye "No contactar", bajas y las de otra ejecutiva salvo en "Todas". Orden: prioridad descendente. "Escribir" abre el modal con la plantilla de la situación ya llena ({nombre}, {coach}, {producto}, {monto}), editable; el botón "Abrir WhatsApp" abre `wa.me/52{10 dígitos}?text=…` **y** registra la nota de contacto ("WhatsApp · plantilla fría") con la hora; si el navegador bloquea la ventana, se muestra el enlace para copiar. Fila sin teléfono: botón deshabilitado con "Sin teléfono en la ficha".

**Ficha unificada**: en la ficha de Clientes (bloque de seguimiento existente) se añaden "Preferencia de contacto" (WhatsApp / correo / ninguno) y "Ejecutiva asignada" (lista de empleados); los compradores invitados aparecen en Seguimiento como filas "Invitado (sin cuenta)" agrupadas por correo, con botón "Crear ficha" que crea el cliente (modo cliente, origen `invitado`, sin acceso) y le liga sus pedidos.

**Coach en el panel del cliente**: cuando el cliente no tiene patrocinadora, el bloque de patrocinador muestra "Tu coach en Finding'U: Ivonne Castro · WhatsApp" (la ejecutiva asignada o la de la cartera por defecto); B lo pinta si el `sponsor` trae `isCoach`.

### 6.3 Contratos de API (prefijo `/customers`, privilegio `access_screen_customers` salvo indicación)

| Método y ruta | Cuerpo / query | Respuesta | Errores |
|---|---|---|---|
| `GET /customers/seguimiento/hoy?scope=mine|all&situation=&limit=` | — | `{date, executiveId, rows:[{customerId, isGuest, email, name, mode, phone, whatsappUrl, sponsorName, executiveId, executiveName, origin, contactPreference, lastOrder:{id, createdAt, total, status}, daysSinceLastPurchase, daysSinceLastContact, situation:"bienvenida"|"fria"|"clabe_pendiente"|"pedido_tardio"|"activa", priority, templateKey}], excluded:{doNotContact:N, otherExecutive:N}}` | — |
| `GET /customers/seguimiento/plantillas` | — | `{templates:{bienvenida:{title, text}, fria:{…}, clabe_pendiente:{…}, pedido_tardio:{…}}, placeholders:["{nombre}","{coach}","{producto}","{monto}","{folio}"]}` (defaults en código, override en config `seguimiento.templates`) | — |
| `POST /customers/{id}/contacto` | `{channel:"whatsapp"|"email"|"call", templateKey?, message, guestEmail?}` | `201 {note:{text, by, at, channel, templateKey}, whatsappUrl}`; para invitados (`id = "invitado"`, con `guestEmail`) se guarda en `GUEST_CONTACT` | 404; 409 `doNotContact` |
| `POST /customers/seguimiento/ficha-invitado` | `{email}` | `201 {customer}` (modo cliente, origen `invitado`, pedidos ligados con `_vincular_pedidos_de_invitado`) | 409 ya existe |
| `PATCH /customers/{id}` (existente) | + `contactPreference`, `executiveId` | — | 400 ejecutiva inexistente |

### 6.4 Cambios de datos

- `CUSTOMER`: `contactPreference` ("whatsapp"|"email"|"none"), `executiveId` (EMPLOYEE), `lastContactAt` (se actualiza al añadir nota); `contactNotes[]` admite `channel`, `templateKey`.
- `GUEST_CONTACT` (bucket nuevo): `{email, notes[]}` para invitados sin ficha.
- Config (`seguimiento`): `defaultExecutiveId: ""`, `coldDays: 30`, `welcomeDays: 7`, `lateOrderDays: 5`, `templates: {}`.

### 6.5 Reglas de negocio

- Situación (la primera que aplique): `clabe_pendiente` si tiene `totalConfirmed > 0` en el mes anterior o actual y sin CLABE; `pedido_tardio` si tiene un pedido `paid` sin envío desde hace ≥ `lateOrderDays` o `shipped` ≥ 7 días sin entrega (para que la coach avise, no para que despache); `bienvenida` si se registró hace ≤ `welcomeDays` y no ha comprado; `fria` si `daysSinceLastPurchase ≥ coldDays` (o nunca compró y ya no es bienvenida); `activa` en el resto (no aparece salvo filtro).
- Prioridad: `daysSinceLastPurchase + daysSinceLastContact` (sin contacto nunca = 999), con `clabe_pendiente` y `pedido_tardio` +100.
- "Mi cartera": clientes con `executiveId == actor`, más los de `leaderId` vacío sin ejecutiva cuando el actor es la ejecutiva por defecto (`seguimiento.defaultExecutiveId`) o un admin.
- Teléfono: se normaliza a 10 dígitos; si no cuadra, `whatsappUrl` vacío.
- `_find_effective_sponsor`: sin `leaderId` → si `executiveId` o `defaultExecutiveId` resuelven a un empleado activo, `{name, phone, whatsapp, email, isDefault:true, isCoach:true, coachTitle:"Tu coach en Finding'U"}`; si no, el `DEFAULT_SPONSOR` actual.

### 6.6 Pruebas mínimas

`test_seguimiento_hoy.py` (lista con las cuatro situaciones sobre el mundo de la ronda 4: Rosa Elena fría, Tomás bienvenida vencida → fría, Claudia CLABE pendiente, Karla excluida por no contactar, cliente de otra ejecutiva excluido en `mine`; invitado Héctor como fila `isGuest`), `test_contacto_plantillas.py` (nota registrada con canal y plantilla, `lastContactAt` actualizado, `doNotContact` → 409, teléfono normalizado, placeholders sustituidos), `test_ficha_unificada.py` (ficha de invitado creada en modo cliente con pedidos ligados; `contactPreference`/`executiveId` guardados; dashboard con `isCoach` y datos de Ivonne).

### 6.7 Archivos

**Propios**: `seguimiento_handlers.py`, `customer_lambda.py` (funciones listadas en §0.7 y `_EXTENSIONES`), `dashboard_common.py` (solo `_find_effective_sponsor`), `tests/test_seguimiento_*.py`, `tests/test_contacto_*.py`, `tests/test_ficha_unificada.py`, `tests/rutas/customer_lambda.json` (compartido con B; el integrador regenera), `pages/admin/seguimiento/**`, `services/seguimiento.service.ts`, `models/seguimiento.model.ts`.
**Compartidos (edit mínimo)**: `core/config.py` (`seguimiento`), `app.routes.ts`, `admin.component.html` (botón en la barra de Clientes; dos campos en el bloque de seguimiento de la ficha), `models/admin.model.ts` (`AdminCustomer.contactPreference?`, `executiveId?`), `models/user-dashboard.model.ts` (`SponsorContact.isCoach?`, `coachTitle?`, `whatsapp?`), `openapi-aws.yaml`.

---

## 7. Paquete G · `devoluciones` (propuesta 18)

### 7.1 Objetivo

Que la clienta devuelva **el bote dañado, no todo el pedido**, con la evidencia que corresponde al motivo, sabiendo cuánto, cuándo y a dónde vuelve su dinero; y que la gerente vea las líneas devueltas y un reembolso sugerido por líneas.

### 7.2 Diseño funcional

**Asistente de devolución** (`pages/order-devolucion`): paso 1 "¿Qué devuelves?": lista de líneas del pedido con cantidad devuelta (stepper 0..qty), "Todo el pedido" como atajo; paso 2 "Motivo" (los actuales) con el plazo visible (48 h daño/defecto, 7 días desistimiento) y el texto de quién paga el envío; paso 3 "Evidencia": según el motivo: desistimiento con paquete cerrado → **una** foto del paquete cerrado con la guía visible; daño o defecto → producto, empaque y guía; paso 4 "Reembolso": *"Te devolvemos $X (los productos que regresas, con tu descuento) [+ envío $Y si el motivo es nuestro] al mismo medio con que pagaste, en 3 a 5 días hábiles después de validar el paquete"*; confirmación con folio `RET-…` leído de la respuesta y la dirección del almacén. Después, la misma página muestra el estado de la solicitud (pendiente / validada / rechazada / reembolsada) con las fechas.

**Back office** (modales existentes): "Recibir paquete" muestra las líneas devueltas con cantidades y las casillas por línea "coincide"; "Reembolsar" sugiere el importe por líneas (`refundSuggested`) desglosado (productos, envío de regreso, envío original si aplica) y deja editar con motivo del ajuste. El detalle del pedido muestra "Devuelto: 1 × Naplus · reembolso $252 · motivo".

**Correos** (G en `order_emails`): `return_received` con líneas, dirección, quién paga, plazo y medio; `return_approved` con importe y "3 a 5 días hábiles al mismo medio de pago"; `return_rejected` sin cambios de fondo; `refunded` con importe, medio y fecha; `cancelled` (pedido pagado) con "al mismo medio de pago, en 3 a 5 días hábiles" (hallazgo 2 de la ronda 4).

### 7.3 Contratos de API

| Método y ruta | Privilegio | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `POST /orders/{id}/return` (existente, ampliado) | dueño/invitado/admin | `{motivo, descripcion?, lines:[{productId, quantity}], evidence:{fotos_paquete_cerrado?|fotos_producto?, fotos_empaque?, fotos_guia_envio?}, returnShippingCost?}` | `201 {requestId, status:"PENDIENTE", lines, shippingResponsibility, refund:{suggested, products, returnShipping, originalShipping, method:"mismo medio de pago", businessDays:"3 a 5"}, warehouseAddress, message}` | 400 `INVALID_LINES` (producto no está en el pedido o cantidad > comprada); 400 `MISSING_EVIDENCE` con `missing` **según el motivo**; los existentes (`NOT_DELIVERED`, `TIME_EXPIRED`, `RETURN_ALREADY_EXISTS`) |
| `GET /orders/{id}/devolucion` | dueño/invitado/admin | — | `{request:{requestId, status, motivo, lines, evidence, refund, inspection?, refundedAt?, refundAmount?, createdAt}}` | 404 |
| `POST /orders/{id}/return/inspect` (existente) | `access_screen_orders` | + `lines:[{productId, quantity, matches:bool}]` | + `refundSuggested` | — |
| `POST /orders/{id}/refund` (existente) | `order_mark_paid` | + `adjustmentReason?` cuando `amount ≠ refundSuggested` | + `refundSuggested`, `breakdown` | 400 ajuste sin motivo |

### 7.4 Cambios de datos

- `RETURN_REQUEST`: `lines[]` (`productId, name, quantity, unitPrice, unitNet`), `partial:bool`, `refundSuggested`, `refundBreakdown{products, returnShipping, originalShipping}`, `refundPolicy{method, businessDays}`, `evidenceRule` ("paquete_cerrado"|"completa").
- `ORDER`: `returnedLines[]`, `refundBreakdown`, `refundAdjustmentReason`.
- `RETURN_MOTIVOS` gana `evidencia` por motivo; `RETURN_EVIDENCIA_REQUERIDA` deja de ser una constante global.

### 7.5 Reglas de negocio

- Líneas: subconjunto del pedido; sin `lines` → todas (compatibilidad).
- Evidencia: `DESISTIMIENTO` → `fotos_paquete_cerrado` (≥ 1); `DANIO`/`DEFECTO` → las tres categorías actuales.
- Reembolso sugerido: `Σ unitNet × quantity` de las líneas (`unitNet = price × (1 − discountRate)`; el cupón se prorratea) + `returnShippingCost` si el responsable es la empresa + envío original solo si se devuelve todo el pedido y el responsable es la empresa. Desistimiento: solo productos (regla de la ronda 4).
- El reembolso mayor que el total cobrado se rechaza (400).
- Plazo y medio en pantalla y correo: "al mismo medio de pago, en 3 a 5 días hábiles tras validar" (config `returns: {refundBusinessDays: "3 a 5"}`).
- Las comisiones se anulan como hoy (por pedido completo) cuando la devolución se valida; una devolución parcial anula la comisión completa del pedido y se reparte de nuevo solo lo no devuelto **no** en esta ronda (decisión §13): se anula todo y se deja anotado el motivo "devolución parcial" para revisar en la siguiente ronda.

### 7.6 Pruebas mínimas

`test_devoluciones_parciales.py` (Lupita devuelve 1 de 2 Naplus: líneas, sugerido = 1 × neto; producto ajeno → 400; cantidad de más → 400), `test_devoluciones_evidencia.py` (desistimiento con una foto pasa; daño con una foto falla con `missing` correcto), `test_devoluciones_reembolso.py` (desistimiento sin envío; daño con envío de regreso y original cuando es todo; ajuste sin motivo → 400; correo con importe, medio y plazo; cancelación de pedido pagado con plazo en el correo), regresiones de `test_devoluciones.py` en verde.

### 7.7 Archivos

**Propios**: `devoluciones_handlers.py`, funciones de devolución de `order_lambda.py` (§0.7), `tests/test_devoluciones_*.py` (nuevos), `pages/order-devolucion/**`, `services/devoluciones.service.ts`, `models/devoluciones.model.ts`, modales de devolución/reembolso de `admin.component.{ts,html}` (edits localizados).
**Compartidos (edit mínimo)**: `order_lambda.py` (import + `_EXTENSIONES`), `core/order_emails.py` (ramas de devolución, `refunded`, `cancelled`), `core/config.py` (`returns`), `models/admin.model.ts` (`OrderReturnRequestPayload.lines?`, `AdminOrder.returnedLines?`), `tests/rutas/order_lambda.json`, `openapi-aws.yaml`.

---

## 8. Paquete H · `pasarela-y-suscripcion` (propuestas 14 y 21)

### 8.1 Objetivo

Que un pago aprobado en MercadoPago **siempre** acabe acreditado (secreto validado, sin duplicados, con conciliación cuando el webhook se pierde) y que quien recompra lo mismo cada mes reciba su pedido sin acordarse del día 20.

### 8.2 Diseño funcional

**Pasarela**: sin pantalla nueva salvo el botón **"Conciliar pagos"** en la barra de Pedidos: modal con el efecto (*"Se consultará a MercadoPago por los pedidos pendientes de pago de las últimas 72 h y se acreditarán los aprobados; los ya pagados no se tocan"*), resultado leído de la respuesta (*"Revisados 4 · Acreditados 1 (ORD-…) · Sin pago 3"*) y enlace a cada pedido acreditado.

**Suscripción mensual** (`pages/user-dashboard/suscripcion/`, selector `app-suscripcion`, lo monta I2 en la sección "Órdenes" del panel): tarjeta "Recibe esto cada mes": productos con cantidad (desde el catálogo), día del mes (1–28), dirección (de las guardadas) o recoger en sucursal, resumen con precio de lista y nota *"El descuento de tu tramo se aplica al generar cada pedido"*; estados: Activa (próximo pedido: 20 de enero), Pausada (hasta …), Cancelada; botones "Pausar un mes", "Reanudar", "Cancelar", "Editar". El día indicado el sistema crea el pedido, genera el enlace de pago y manda el correo *"Tu pedido mensual está listo: paga aquí"*; el pedido aparece en Órdenes como cualquier otro. Correos: al crear, al pausar/reanudar, al generar cada pedido, al cancelar.

### 8.3 Contratos de API

| Método y ruta | Privilegio | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `POST /orders/webhooks/mercadolibre?topic=payment&id=…&webhookSecret=…` (existente) | pública | MP | `200 {ok:true, orderId, applied:bool, idempotent?:true}`; `200 {ok:true, ignored:"order_not_found"|"not_approved"}` | **401** `{message:"Secreto de webhook inválido"}` si `payments.mercadoLibre.webhookSecret` está configurado y no coincide; si no está configurado se acepta y se registra `mp_webhook_secret_missing` |
| `POST /orders/conciliacion` (programable) | `order_mark_paid` o superadmin | `{hours?:72, orderIds?, dryRun?}` | `{runId, checked, credited:[{orderId, paymentId}], unpaid:[orderId…], errors:[{orderId, error}]}` | 502 si MP no responde (parcial: se informa por pedido) |
| `GET /orders/conciliacion/ultima` | `access_screen_orders` | — | `{run}` (última corrida) | — |
| `GET /orders/suscripciones` | sesión propia | — | `{subscriptions:[…]}` | 401 |
| `POST /orders/suscripciones` | sesión propia | `{items:[{productId, quantity}], dayOfMonth, deliveryType, shippingAddressId?|shippingAddress?, pickupStockId?}` | `201 {subscription}` (+ correo) | 400 día fuera de 1–28, ítems vacíos, producto inactivo |
| `PATCH /orders/suscripciones/{id}` | dueño o admin | `{items?, dayOfMonth?, shippingAddress?, status?:"active"|"paused", pausedUntil?}` | `{subscription}` (+ correo si cambia el estado) | 404, 409 cancelada |
| `DELETE /orders/suscripciones/{id}` | dueño o admin | — | `{subscription:{status:"cancelled"}}` (+ correo) | 404 |
| `POST /orders/suscripciones/generar` (programable) | `order_create` o superadmin | `{date?, dryRun?}` | `{generated:[{subscriptionId, orderId, initPoint}], skipped:[{subscriptionId, reason}]}` | — |

`handle_update_status`: si `new_status == "paid"` y el pedido ya está `paid` (o en cualquier estado posterior), responde `200 {order, alreadyPaid:true}` sin SFN, sin `paidAt` nuevo y sin correo.

### 8.4 Cambios de datos

- `ORDER`: `paymentId`, `paymentStatusDetail`, `paidVia` ("mercadopago"|"branch"|"admin"|"reconciliation"), `webhookReceivedAt`, `reconciledAt`, `subscriptionId`.
- `RECONCILIATION_RUN` (bucket nuevo): `{runId, startedAt, hours, checked, credited, unpaid, errors, triggeredBy}`.
- `SUBSCRIPTION` (bucket nuevo): `{subscriptionId, customerId, items[], dayOfMonth, deliveryType, shippingAddress, pickupStockId, status:"active"|"paused"|"cancelled", pausedUntil, nextRunDate, lastRunDate, lastOrderId, createdAt, updatedAt}`; se lista filtrando por `customerId` en memoria (volumen pequeño).
- Config: `payments.mercadoLibre.paymentSearchUrlTemplate: "https://api.mercadopago.com/v1/payments/search?external_reference={order_id}&sort=date_created&criteria=desc"`, `payments.reconciliationHours: 72`; `subscriptions: {enabled: True, minDay: 1, maxDay: 28, reminderDaysBefore: 0}`.

### 8.5 Reglas de negocio

- Webhook: (1) secreto; (2) consulta `/v1/payments/{id}`; (3) busca el pedido por `external_reference`; (4) si `order.paymentId == id` o el estado ya no es `pending` → idempotente; (5) si `approved` → `handle_update_status(paid, {paymentId, paidVia:"mercadopago"})`. Un `pending`/`rejected` no cambia nada y se registra en `paymentStatusDetail`.
- Conciliación: pedidos `pending` con `paymentPreferenceId` creados en las últimas `hours`; por cada uno consulta `payments/search`; el primer `approved` acredita con `paidVia:"reconciliation"`; un pedido sin resultados queda `unpaid`. Idempotente por construcción (la guarda de `paid`).
- Suscripción: `nextRunDate` = próximo `dayOfMonth`; `generar` procesa las activas con `nextRunDate ≤ hoy` y `lastRunDate ≠ hoy`; el pedido se crea con `order_lambda.handle_create_order` a nombre del cliente (descuento del tramo real, envío cotizado con la tarifa base `shipping.baseRateMxn` cuando no hay cotización: se marca `shippingCost` y `shippingCarrier = "por confirmar"`), se genera la preferencia (`handle_mercadopago_checkout`) y se manda el correo con `initPoint`; no hay cobro automático (no se guardan tarjetas: decisión §13). Si el cliente está en modo cliente, el pedido sigue las reglas de modo cliente (B). Pausada con `pausedUntil` vencido vuelve a activa al generar.

### 8.6 Componente que H construye y otro monta

`pages/user-dashboard/suscripcion/suscripcion.component.ts`, selector **`app-suscripcion`**, standalone:

```ts
@Input() customerId = '';
@Input() products: DashboardProduct[] = [];          // catálogo activo (id, name, price, vpPoints, img)
@Input() addresses: CustomerShippingAddress[] = [];
@Input() defaultAddressId = '';
@Input() pickupStocks: Array<{ id: string; name: string; location: string }> = [];
@Input() mode: 'cliente' | 'socio' = 'socio';
@Output() changed = new EventEmitter<void>();         // tras crear/editar/pausar/cancelar
```

Servicio `services/suscripcion.service.ts`. I2 lo monta en `user-dashboard.component.html` dentro de `#ordenes` con una línea y pasa los inputs desde `dashboardControl.data`.

### 8.7 Harness (`sim/servidor.py`, solo H)

- `urlopen_mp`: (a) `checkout/preferences` guarda además `notification_url` y `estado:"pending"`; (b) `/v1/payments/sim-{oid}` devuelve `approved` solo si `PAGOS[oid]["estado"] == "approved"`; (c) `/v1/payments/search?external_reference={oid}` devuelve `{"results":[{id, status, external_reference}]}` según `estado`.
- `/__sim/pago/{oid}/confirmar` marca `estado = approved` y llama al webhook **con el `webhookSecret` que trae la `notification_url`** guardada (si la config lo tiene); `/__sim/pago/{oid}/pagar-sin-aviso` marca `approved` sin llamar al webhook (para probar la conciliación); `/__sim/pago/{oid}/reenviar-webhook` repite el webhook (para probar la idempotencia).
- Hook del reloj y `POST /__sim/tareas` (§0.3).
- `sim/protocolo.md`: H documenta las tres acciones nuevas (edit propio; nadie más lo toca esta ronda).

### 8.8 Pruebas mínimas

`test_pasarela_webhook.py` (secreto configurado y erróneo → 401 y el pedido sigue `pending`; correcto → `paid`; sin configurar → acepta con log; webhook repetido → `idempotent` y una sola fila de comisión, un solo correo; `rejected` no cambia estado), `test_conciliacion.py` (pedido pagado sin webhook se acredita; ya pagado no se toca; fuera de ventana no se consulta; `dryRun`), `test_suscripciones.py` (crear/pausar/reanudar/cancelar con correos; `generar` el día indicado crea pedido con el tramo real y manda enlace; no duplica el mismo día; pausada no genera; cliente en modo cliente sin descuento). Harness: `pagar-sin-aviso` + "Conciliar pagos" acredita; reloj a día 20 genera el pedido de Bety.

### 8.9 Archivos

**Propios**: `suscripciones_handlers.py`, `conciliacion_handlers.py`, en `order_lambda.py` las funciones de §0.7 más `_EXTENSIONES` (lo introduce H) y `TAREAS_PROGRAMADAS`, `sim/servidor.py`, `sim/protocolo.md`, `tests/test_pasarela_*.py`, `tests/test_conciliacion.py`, `tests/test_suscripciones.py`, `pages/user-dashboard/suscripcion/**`, `services/suscripcion.service.ts`, `services/conciliacion.service.ts`, `models/suscripcion.model.ts`.
**Compartidos (edit mínimo)**: `core/config.py` (`payments`, `subscriptions`), `admin.component.html` (botón "Conciliar pagos"), `admin.component.ts` (`conciliarPagos()`), `models/admin.model.ts` (`AdminOrder.paymentId?`, `paidVia?`, `subscriptionId?`), `tests/rutas/order_lambda.json`, `openapi-aws.yaml`.

---

## 9. Contratos cruzados entre paquetes (resumen)

| De → a | Qué | Cómo |
|---|---|---|
| B → C | `ui-ahorro-socio` en el carrito | C monta `<ui-ahorro-socio [gross]="subtotal" [monthNet]="monthNet" [mode]="mode" variant="inline">` en el resumen y en el cajón móvil (dos líneas); si C integra antes que B, lo hace I2. |
| B → E | Modo del cliente en el POS | E lee `AdminCustomer.mode`; en `cliente` el descuento de socio es 0 y el botón lo explica. |
| B → I1/I2 | `ui-tabla-descuento` | I1 la monta en el POS (`context="pos"`), I2 en el carrito (`context="carrito"`); B la monta en el panel. |
| B → todos | `partnerSavings` en el pedido | Lo escribe `_calculate_totals`; `order-status` y el correo lo leen. |
| F → B | Coach en el panel | `_find_effective_sponsor` devuelve `isCoach`, `coachTitle`, `whatsapp`; B pinta el bloque. |
| A ↔ C | Producto que cierra la activación | Misma fórmula (§1.5, §3.5); dos implementaciones en la ola A, unificadas por I2. |
| H → A, D | Tareas programadas y hook del reloj | H implementa el hook genérico; A y D solo declaran `TAREAS_PROGRAMADAS`. |
| H → C, G | `_EXTENSIONES` en `order_lambda` | H la introduce; C y G añaden su entrada. |
| D → E | `_EXTENSIONES` en `inventory_lambda` | D la introduce; E añade su entrada. |
| F → B | `_EXTENSIONES` en `customer_lambda` | F la introduce; B añade su entrada. |
| C → B | Texto de factura en el correo `paid` | B lee `order.invoiceRequested` en su párrafo. |
| D → H | `shippedAt` | H no lo usa; D lo escribe en `handle_update_status`. |
| E → D | Resumen de turno | D lee `POS_SALE`/`POS_CASH_CUT` con los campos nuevos de E si existen (todo opcional). |

---

## 10. Tabla de nuevas entidades y atributos (tabla única)

| Bucket / entidad | Nuevo o ampliado | Paquete | Atributos |
|---|---|---|---|
| `COMMISSION_PAYMENT_BATCH` | nuevo | A | batchId, monthKey, assetUrl, bankReference, customerIds, totalPaid, createdBy |
| `COMMISSION_RECEIPT` | ampliado | A | batchId |
| `COMMISSION_MONTH` | ampliado | A | clabeReminderAt, blockedNoticeSentDays |
| `NOTIFICATION` | ampliado | A | targetCustomerId |
| `CUSTOMER` | ampliado | A, B, F | clabeReminderFirstAt; mode, modeSince, modeActivatedAt, modeReason, acceptedPlanVersion; contactPreference, executiveId, lastContactAt |
| `ORDER` | ampliado | B, C, D, G, H | partnerSavings*, invoice*, shippedAt/shippedBy/deliveredBy/deliverySignedBy/carrierDeliveredAt/trackingEvents/labelUrl/deliveryCheckEmailSentAt/autoClosedAt/dispatchBatchId, returnedLines/refundBreakdown/refundAdjustmentReason, paymentId/paymentStatusDetail/paidVia/webhookReceivedAt/reconciledAt/subscriptionId |
| `STOCK` | ampliado | C | city, state |
| `EMPLOYEE` | ampliado | D | defaultStockId |
| `LOGIN_LINK` | nuevo | C | tokenHash, email, expiresAt, used, rememberMe |
| `PASSWORD_RESET` | ampliado | C | otpHashes[] |
| `SESSION` | ampliado | C | rememberMe, expiresAt |
| `DISPATCH_BATCH` | nuevo | D | batchId, stockId, orderIds, shipments, results |
| `POS_CASH_CUT` / `POS_SALE` / `POS_WITHDRAWAL` | ampliados | E | cashExpected, cashCounted, denominations, difference, differenceReason, withdrawalReceiver, openingCash; payments, cashPortion; receiver |
| `GUEST_CONTACT` | nuevo | F | email, notes |
| `RETURN_REQUEST` | ampliado | G | lines, partial, refundSuggested, refundBreakdown, refundPolicy, evidenceRule |
| `RECONCILIATION_RUN` | nuevo | H | runId, checked, credited, unpaid, errors |
| `SUBSCRIPTION` | nuevo | H | subscriptionId, customerId, items, dayOfMonth, deliveryType, shippingAddress, status, pausedUntil, nextRunDate, lastRunDate, lastOrderId |

Ningún índice secundario nuevo. Los nuevos buckets se consultan por `sk_prefix`/`sk_from` (fecha) o en memoria por su tamaño.

---

## 11. Ola B (sobre el árbol integrado)

### I1 · `transversal-admin` (propuestas 8, 10, 23b y montaje de la tabla en el POS)

- **Botones deshabilitados que explican por qué** en todo el back office: `ui-button` gana `@Input() disabledReason = ''` y pinta el motivo bajo el botón (o como `title`) cuando `disabled`; I1 recorre `admin.component.html` y cada `[disabled]` recibe su motivo (parte de la lista de E en el POS como referencia). `components/ui-button/**` es de I1.
- **Un solo DOM por tabla**: las tablas con fila de escritorio y fila móvil duplicadas (Pedidos, Clientes, Productos, Stocks, POS) pasan a una sola fila adaptada por CSS; los botones "Ver" y los `input type="file"` dejan de existir dos veces; se verifica con `document.querySelectorAll` en el harness que cada acción aparece una vez por registro.
- **Sin `prompt()` ni `confirm()`**: los 11 usos actuales (cancelar pedido, deshacer pago, baja de datos, desactivar empleado, recibir transferencia con cantidades, abono de saldo, anular venta, activar/desactivar cupón) se sustituyen por `ui-modal` con validación y el efecto escrito; se añade `components/ui-confirm/` (selector `ui-confirm`, inputs `title`, `effect`, `requireReason`, `confirmLabel`, `danger`; output `confirmed(reason)`).
- **Confirmaciones desde el servidor**: toda acción del back office muestra en el toast/modal el dato guardado leído de la respuesta (folio, monto, estado nuevo), nunca el del formulario; donde la respuesta no traiga el dato, I1 lo añade en el backend (edit localizado con prueba).
- **Tabla única en el POS**: monta `ui-tabla-descuento` (`context="pos"`) junto al cliente seleccionado con `monthNet`/`monthVp` de `GET /commissions/associates/{id}/month/{mes}` y `cartGross`/`cartPc` de la venta en curso.
- Archivos: `admin.component.{ts,html,css}`, `components/ui-button/**`, `components/ui-confirm/**`, `components/ui-data-table/**`, `components/ui-table/**`, y edits localizados de backend con prueba.

### I2 · `transversal-socio`

- Monta `ui-tabla-descuento` (`context="carrito"`) en el carrito (resumen y cajón móvil) y `app-suscripcion` en el panel (`#ordenes`), con los inputs de §2.6 y §8.6.
- Confirmaciones desde el servidor en carrito, seguimiento de pedido, devolución y panel (folio, total, estado leídos de la respuesta).
- Revisión de punta a punta de la sesión persistente (C): recordarme, `sessionStorage`, enlace de acceso, 401 → relogin sin perder el carrito, back office y panel.
- Unifica `_producto_que_salva` (A) con `checkout_handlers.sugerir_producto_activacion` (C).
- Archivos: `pages/carrito/**`, `pages/user-dashboard/user-dashboard.component.{ts,html}` (montaje), `pages/order-status/**`, `services/auth.service.ts` (revisión), `pagos_handlers.py` (solo la sustitución de la fórmula).

---

## 12. Orden de integración de la ola A y checklist

Orden sugerido (minimiza conflictos en los anfitriones): **H → C → G** (los tres de `order_lambda`; H introduce `_EXTENSIONES`), **D → E** (`inventory_lambda`; D introduce `_EXTENSIONES`), **F → B** (`customer_lambda`; F introduce `_EXTENSIONES`; B toca además `auth_utils` de C y `commissions_lambda` de A, ya integrados o pendientes: son líneas sueltas), **A** al final (o antes de B, indistinto).

Checklist por integración: `pytest` en verde; `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py` y revisión del diff de `tests/rutas/`; `ng build`; arranque del harness (`sim/servidor.py`) y `POST /__sim/tareas` sin errores; `openapi-aws.yaml` con las rutas nuevas.

---

## 13. Decisiones tomadas sobre lo ambiguo

1. **Política 22**: se implementa la **opción b** (avisos los días 20 y 27 con el monto bloqueado en riesgo y el producto que lo salva). La **opción a** (gracia hasta el día N del mes siguiente) queda como parámetro `rewards.blockedGraceDays`, **0 por omisión** (apagada); si el negocio la enciende, la reevaluación al activarse alcanza también el mes anterior. La opción c (saldo en tienda) no se implementa.
2. **Modo cliente**: nace cliente todo registro nuevo; las fichas existentes quedan socio; en modo cliente **no aplica la escalera de descuento** (paga precio de lista) para que "como socia habrías ahorrado $X" sea verdad; el volumen del mes se sigue acreditando y sus compras pagan comisión a su línea. Cambia a socio por solicitud, por referido o por comisión. Sin firma ni aceptación formal del plan más allá de `acceptedPlanVersion`.
3. **Plan publicado**: una sola definición de PC/VP/VG; todos los números salen de config; sin PDF en esta ronda (la landing es imprimible).
4. **Factura**: captura de datos fiscales y estado `solicitada` → `emitida` a mano con archivo opcional; **sin timbrado CFDI** en esta ronda.
5. **Envío gratis**: se mide sobre el **subtotal bruto** (`shipping.freeShippingBasis = "gross"`); el neto queda como opción de config; el carrito y la tienda dicen la tarifa base y el faltante.
6. **Recoger en sucursal**: solo si hay sucursal con `allowPickup` en la ciudad/estado del cliente y con existencia; los almacenes ganan `city`/`state`.
7. **Sesión**: "Recordarme" marcado por omisión (30 días en `localStorage`); sin marcar, 24 h en `sessionStorage`; enlace de acceso por correo (no por WhatsApp: no hay canal saliente de WhatsApp en el sistema); recuperación acepta los tres últimos códigos vigentes y comprueba caducidad.
8. **Paquetería**: adaptador `carriers.py` con la integración de **Envia** existente (generación de guía y rastreo por consulta programable, no por webhook) y una paquetería simulada; rastreo y cierre automático desactivados por omisión (`carrierIntegration.enabled = False`); cierre a `autoCloseDays = 10` con correo "¿te llegó?" a los 7.
9. **Despacho en bloque**: parcial permitido (se despacha lo que se puede y se informa el resto) **después** de validar el surtido; un pedido pickup nunca entra.
10. **Pago de comisiones por lote**: un solo archivo de comprobante para el lote; por fila se aplican `CLABE_REQUIRED` y `ALREADY_PAID` (se saltan, no fallan); deshacer sigue siendo por fila con la ruta existente. CSV con CLABE completa (es el archivo del banco); en pantalla siempre enmascarada.
11. **Aviso de CLABE**: al activarse por primera vez y al confirmarse la primera comisión del mes; uno por motivo y mes; respeta "no contactar".
12. **Suscripción**: sin cobro automático (no se guardan tarjetas): el día indicado se crea el pedido, se genera el enlace de MercadoPago y se manda por correo; el descuento es el del tramo real de ese día; día 1–28.
13. **Pasarela**: el secreto viaja en la query (`webhookSecret`) como ya lo anexa el checkout; la verificación de `x-signature` de MercadoPago queda documentada como mejora posterior; conciliación de 72 h por `payments/search`; el estado `paid` es idempotente en `handle_update_status`.
14. **Devolución parcial**: se anulan las comisiones del pedido completo (regla actual) y se anota "devolución parcial"; repartir de nuevo lo no devuelto queda para otra ronda.
15. **Arqueo**: la diferencia exige motivo (`pos.requireDifferenceReason`); el comprobante es el registro del corte impreso desde el frontend más un correo opcional; el retiro del corte requiere código como cualquier retiro.
16. **Seguimiento**: la cartera "FindingU" es la de la ejecutiva por defecto (`seguimiento.defaultExecutiveId`); las plantillas viven en código con override en config; el mensaje de WhatsApp lo manda la persona desde su teléfono (`wa.me`); el sistema solo prellena y anota.
17. **Sin privilegios nuevos**: cada ruta reutiliza el de su pantalla (tabla en cada paquete).
18. **Sin índices nuevos** ni cambios en `template.yaml`; la programación con EventBridge se documenta y no se despliega.
19. **Botones deshabilitados y modales**: E aplica el patrón solo en el POS; I1 lo generaliza (`ui-button.disabledReason`, `ui-confirm`) en todo el back office.
20. **Servicios de API por paquete** y `actorHeaders()` público: se evita que ocho agentes editen `api.service.ts`/`real-api.service.ts`; el modo mock queda sin estas funciones.
