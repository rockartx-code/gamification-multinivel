# Auditoría de consultas a base de datos (DynamoDB)

> **Alcance:** los 9 módulos Python de `Micro-lambda-GMF/python` (9,166 líneas).
> **Objetivo:** validar que toda consulta sea correcta y óptima.
> **Fecha:** septiembre 2026 · **Rama:** `claude/ultimos-cambios-integrados-fylhiw`

---

## 1. Método

1. **Inventario estático (AST).** Se recorrió el árbol sintáctico de los 9 módulos y se
   clasificaron los **286 puntos de acceso a datos**: 6 `query`, 18 `get_item`, 13 `put_item`,
   6 `update_item`, 3 `delete_item`, 1 `batch_get_item` y 239 llamadas a los helpers de
   `core_utils` (`_get_by_id`, `_query_bucket`, `_put_entity`, `_update_by_id`,
   `_batch_get_entities`).
2. **Medición dinámica.** Se sustituyó la tabla por una implementación en memoria que cuenta
   cada operación y se ejecutaron los handlers reales contra datasets sintéticos de 100 / 200 /
   400 / 800 clientes. La herramienta queda versionada y es reproducible:

   ```bash
   pip install boto3
   python3 Micro-lambda-GMF/python/tools/ddb_query_probe.py 400
   TRACE=1 python3 Micro-lambda-GMF/python/tools/ddb_query_probe.py 400   # atribuye cada GetItem
   ```

### Resultados medidos (operaciones por **una sola** invocación)

**Antes de las correcciones** — todas las cifras son **GetItem secuenciales** (salvo la última
fila): no hay paralelismo ni `BatchGetItem` en esas rutas, así que el tiempo de pared es
`nº operaciones × RTT` (≈ 2–5 ms en VPC). 481,200 GetItems ≈ **25–40 minutos**; el límite duro
de Lambda son 15 minutos.

| Endpoint | N=100 | N=200 | N=400 | N=800 | Crecimiento |
|---|---:|---:|---:|---:|---|
| `GET /dashboard/honor-board` | **30,300** | **120,600** | **481,200** | **1,922,400** | **O(N²)** (=3N²) |
| `GET /user-dashboard` | 110 | 210 | 410 | 810 | **O(N)** (=N+10) |
| `ORDER_PAID` (`handle_apply_rewards`) | 119 | 103 | 143 | 129 | O(profundidad · ancho) |
| `GET /customers/dashboard` (caliente) | 8 GetItem + 3 BatchGet | 8 + 3 | 8 + 6 | 8 + 12 | **O(1) viajes** ✅ |

**Después de las correcciones** (§7). Ya no quedan GetItem por cliente: lo que crece es el
número de `BatchGetItem`, que agrupa 100 claves por viaje.

| Endpoint | N=100 | N=400 | N=800 | Viajes a DynamoDB |
|---|---|---|---|---|
| `GET /dashboard/honor-board` | 3 BatchGet + 1 Query | 12 + 1 | 24 + 1 | **1,922,400 → 25** (N=800) |
| `GET /user-dashboard` | 11 GetItem + 3 BatchGet + 8 Query | 11 + 6 + 8 | 11 + 12 + 8 | **810 → 31** (N=800) |
| `ORDER_PAID` | 19 GetItem + 3 BatchGet | 30 + 3 | 31 + 3 | **129 → 34** (N=800) |
| `GET /customers/dashboard` | 8 GetItem + 3 BatchGet | 8 + 6 | 8 + 12 | sin cambios (ya era correcto) |

---

## 2. Resumen ejecutivo

| | |
|---|---|
| ✅ **No hay ni un solo `scan()`** en el código | El diseño de clave única evita el antipatrón más caro |
| ✅ `_query_bucket` **pagina correctamente** (`LastEvaluatedKey`) | `core_utils.py:161-174` |
| ✅ El historial de pedidos por cliente **está bien resuelto** | Partición dedicada + `nextToken` opaco (`order_lambda.py:273-284`) |
| ✅ `costumer_lambda` **ya implementa el patrón correcto** | Árbol persistido + `BatchGetItem` — sirve de plantilla para el resto |
| ❌ **Sin GSI, sin `ProjectionExpression`, sin `ConditionExpression`, sin `transact_write_items`, sin TTL** | 0 ocurrencias en todo el repo |
| ❌ **1 consulta cuadrática**, **1 lineal en ruta caliente**, **~55 tablas completas leídas en memoria** | Ver §4 |
| ❌ **4 de 6 `query` crudas leen una sola página** → truncado silencioso a 1 MB | Ver P1-1 |

**Veredicto: las consultas son correctas en su forma (no hay scans, la paginación del helper
principal es correcta) pero NO son óptimas.** El modelo "una partición por tipo de entidad"
obliga a leer la colección entera para cualquier filtro, y sobre eso se apilan varios N+1.
Hoy funciona porque el dataset es pequeño; **`/dashboard/honor-board` deja de funcionar
alrededor de los 300–400 clientes** y el resto se degrada linealmente.

---

## 3. Modelo de datos actual

Tabla única `multinivel`, clave `PK` + `SK`, **sin índices secundarios**.

```
Patrón "bucket + REF"  (core_utils.py:113-131)
  Item principal :  PK = "<ENTIDAD>"            SK = "<createdAt ISO>#<id>"
  Puntero        :  PK = "<ENTIDAD>#<id>"       SK = "REF"           → {refPK, refSK}

Excepciones (clave directa, sin puntero):
  ASSOCIATE_MONTH:  PK = "ASSOCIATE_MONTH"      SK = "<customerId>#<YYYY-MM>"
  COMMISSION_MONTH: PK = "COMMISSION_MONTH"     SK = "#BENEFICIARY#<id>#MONTH#<YYYY-MM>"
  Historial pedido: PK = "ORDER_BY_CUSTOMER#<id>" SK = "<createdAt>#<orderId>"
  Árbol de red    : PK = "NETWORK_TREE#customers" SK = "TREE"        (singleton)
  Índice nombre   : PK = "REF#NOMBRE#<letra>"   SK = "<createdAt>#<customerId>"
```

Consecuencias directas del diseño:

- **Toda lectura por id cuesta 2 GetItem** (puntero + principal). `_get_by_id` se invoca en
  98 sitios; en bucles esto duplica el coste.
- **Filtrar = leer la colección completa.** No existe forma de pedir "pedidos de junio" o
  "ventas POS del almacén 3"; se lee la partición entera y se filtra en Python.
- **Partición caliente.** Todos los `ORDER` del histórico viven en `PK="ORDER"`. DynamoDB
  limita una partición a **3,000 RCU / 1,000 WCU y 10 GB**. Con volumen real, escrituras de
  pedidos y lecturas de reportes compiten por el mismo tope.
- **`SK` empieza por `createdAt`** → `begins_with(SK, "2026-06")` ya sería una key condition
  válida para filtrar por mes **sin cambiar el modelo**. Es la optimización de mayor
  relación beneficio/riesgo del informe y hoy no se usa en ningún sitio.

---

## 4. Hallazgos

### P0 — Rompe en producción

#### P0-1 · `GET /dashboard/honor-board` es O(N²) — 1.9 M GetItem con 800 clientes
`dashboard_lambda.py:1043-1101` · `_compute_ranking` → `_build_network_tree_with_month`

```python
# dashboard_lambda.py:1062  — bucle sobre TODOS los clientes
for c in customers_raw:
    ...
    tree = _build_network_tree_with_month(cid, mk, customers_raw, cfg_rewards, max_depth=5)
```
y dentro (`dashboard_lambda.py:226-230`):
```python
for cid, n in nodes.items():          # nodes = TODOS los clientes, otra vez
    st = _get_month_state(cid, month_key)   # 1 GetItem por cliente, secuencial
```

Se construye el árbol **completo del sistema** una vez por cada cliente, y además para dos
meses (actual y anterior). Coste exacto medido: **3N² GetItem**. El comentario del código
dice *"Para eficiencia usamos suma de sub-árbol directo en lugar de árbol completo (evita N^2
queries)"* — el comentario describe una optimización que no está implementada.

**Impacto:** con ~350 clientes el endpoint supera los 15 min de Lambda y devuelve 502. También
consume RCU equivalente a millones de lecturas por request.

**Corrección:** cargar `_load_month_states()` **una vez** (BatchGetItem, ya existe en
`costumer_lambda.py:406-423`), construir el mapa `hijos por líder` **una vez**, y calcular el
VG de cada cliente con un solo recorrido post-orden del árbol global. Coste resultante:
`O(N)` items leídos en `⌈N/100⌉` BatchGetItem — de 1,922,400 operaciones a **8**.

---

#### P0-2 · `GET /user-dashboard` hace 1 GetItem por cada cliente del sistema
`dashboard_lambda.py:845-1000` → `_build_network_tree_with_month` (`dashboard_lambda.py:205-250`)

Medido: **N+10 GetItem secuenciales** (810 con 800 clientes) para pintar el dashboard de **un**
usuario, cuyo árbol se recorta después a 5 niveles. Además lee íntegras las colecciones
`PRODUCT`, `CAMPAIGN`, `CUSTOMER`, `NOTIFICATION`, `BONUS_AWARD` y `COMMISSION_RECEIPT`.

**Esta ruta está viva.** Aunque `real-api.service.ts:443` la marca `@deprecated`,
`gamificacion-multinivel-f/src/app/pages/tienda/tienda.component.ts:251` sigue llamando
`getUserDashboardData()`; es decir, **la tienda —la pantalla más visitada— paga el coste
completo en cada carga**.

**Corrección (dos opciones, no excluyentes):**
1. *Inmediata, 1 línea de front:* migrar `tienda.component.ts` a
   `getCatalogData()` + `getDashboardData()`, que ya existen y usan la ruta optimizada.
   La tienda solo consume `products` y `categories`: `GET /catalog` basta.
2. *De fondo:* portar a `dashboard_lambda` el patrón ya implementado en
   `costumer_lambda._load_customer_network_scope` (`costumer_lambda.py:176-217`) — árbol
   persistido + `_batch_get_entities` — y borrar la versión duplicada.

> La misma lógica de red está **triplicada** en `costumer_lambda` (optimizada),
> `dashboard_lambda` (O(N)) y `commissions_lambda` (`_load_network_customers`, N+1).
> Unificarla en `core_utils` elimina la clase entera de defectos.

---

### P1 — Correctitud

#### P1-1 · Cuatro `query` leen una sola página → truncado silencioso a 1 MB
DynamoDB corta cualquier `Query` en 1 MB y devuelve `LastEvaluatedKey`. Estos cuatro sitios lo
ignoran y **devuelven resultados incompletos sin error**:

| Sitio | Partición | Efecto del truncado |
|---|---|---|
| `dashboard_lambda.py:656` | `COMMISSION_MONTH` (todos los beneficiarios × todos los meses) | El aviso "N comisiones pendientes por depositar" queda **corto**; se dejan de pagar comisiones sin ninguna señal |
| `costumer_lambda.py:1563` | `REF#NOMBRE#<letra>` | La búsqueda de clientes en admin omite coincidencias |
| `costumer_lambda.py:783` | `NOTIFICATION_READ#<id>` | Notificaciones ya leídas reaparecen como no leídas |
| `dashboard_lambda.py:511` | `NOTIFICATION_READ#<id>` | Ídem |

Los dos primeros son fallos de negocio reales; los dos últimos son cosméticos hoy pero crecen
sin límite. **Corrección:** usar `utils._query_bucket` o replicar su bucle
`while LastEvaluatedKey` (`core_utils.py:161-174`).

---

#### P1-2 · El ledger de comisiones se pierde bajo concurrencia (lost update)
`commissions_lambda.py:24-51`

```python
item = _get_ledger_month(b_id, month_key)   # GetItem
item['ledger'].append(new_row)              # modificación en memoria
_save_ledger_month(item)                    # PutItem del item COMPLETO
```

Dos órdenes pagadas simultáneamente para el mismo beneficiario (escenario normal en un
multinivel) producen dos lecturas del mismo estado y la segunda escritura **borra la comisión
de la primera**. No hay `ConditionExpression` ni número de versión.

Riesgo relacionado: `ledger` es una lista dentro de un único item; DynamoDB limita el item a
**400 KB**. Un líder con mucho volumen mensual alcanza ese techo y las escrituras empiezan a
fallar con `ValidationException`.

**Corrección:** una fila de ledger = un item propio
(`PK="COMMISSION_MONTH#<benef>#<mes>"`, `SK="ROW#<orderId>#G<gen>"`) y los totales mantenidos
con `UpdateItem ... ADD` atómico. Elimina de raíz la carrera y el techo de 400 KB, y de paso
hace que `_void_commissions_for_order` (`order_lambda.py:401-470`, hoy también read-modify-write)
sea un `DeleteItem` + `ADD` negativo.

---

#### P1-3 · `_put_entity` escribe 2 items sin transacción
`core_utils.py:132-133`

```python
_table.put_item(Item=main_item)   # si esto pasa…
_table.put_item(Item=ref_item)    # …y esto falla, el item queda invisible
```

Si el segundo `put_item` falla (throttling, timeout), el item principal existe pero
`_get_by_id` nunca lo encuentra: registro huérfano permanente. Aplica a los 43 sitios que usan
`_put_entity`, incluidos `ORDER` y `CUSTOMER`.

**Corrección:** `_ddb_client.transact_write_items([...])` con ambos `Put`.

---

#### P1-4 · El índice de nombres solo se escribe en el auto-registro
`auth_utils.py:278-290` escribe `REF#NOMBRE#<letra>`. Pero:
- `costumer_lambda.py:1073` (alta de cliente por admin) **no lo escribe**.
- Ningún `PATCH /customers/{id}` lo actualiza al cambiar el nombre.

La búsqueda (`costumer_lambda.py:1560-1586`) solo cae al barrido completo cuando el índice
devuelve **cero** coincidencias; si devuelve alguna, entrega un resultado parcial y silencioso.

**Corrección:** centralizar el mantenimiento del índice en un helper de `core_utils` invocado
desde todas las altas y actualizaciones de `CUSTOMER`, y borrar la entrada antigua al cambiar
de inicial.

---

#### P1-5 · Reintento sin tope en `_batch_get_items`
`core_utils.py:271-303` — el bucle de `UnprocessedKeys` es `while True` con `sleep` acotado a
1 s y **sin número máximo de reintentos**. Bajo throttling sostenido el Lambda gira hasta
agotar su timeout en lugar de fallar rápido. **Corrección:** máximo 5–8 reintentos y luego
propagar el error.

---

#### P1-6 · La config global queda cacheada indefinidamente
`core_utils.py:1045` — `@functools.lru_cache(maxsize=1)` sobre `_load_app_config()`, y
`cache_clear()` no se llama en ningún punto del repo. Tras guardar la configuración
(`commissions_lambda._save_app_config`), **los contenedores tibios de los demás lambdas siguen
calculando comisiones, descuentos y rangos con la configuración vieja** hasta que AWS los
recicla (minutos u horas), de forma no determinista entre invocaciones.

**Corrección:** cachear con TTL corto (30–60 s) comparando `time.time()`, en vez de para
siempre.

---

### P2 — Rendimiento y coste

#### P2-1 · ~55 lecturas de colección completa filtradas en memoria
Se leen íntegras `ORDER`, `CUSTOMER`, `POS_SALE`, `INVENTORY_MOVEMENT`, `BONUS_AWARD`,
`COMMISSION_RECEIPT`, `POS_WITHDRAWAL`, `POS_CASH_CUT`… para después filtrar con un `if` en
Python. Los peores casos:

| Sitio | Qué lee | Para qué |
|---|---|---|
| `commissions_lambda.py:1044-1140` | ORDER + CUSTOMER + POS_SALE + INVENTORY_MOVEMENT + STOCK **completos** | Estadísticas de **un** mes |
| `dashboard_lambda.py:644-672` | ORDER (×2) + STOCK_TRANSFER + POS_SALE completos | Contar 5 alertas |
| `inventory_lambda.py:285-330` | POS_SALE + POS_WITHDRAWAL + POS_CASH_CUT completos | Caja del turno actual de **un** operador |
| `inventory_lambda.py:333-360` | POS_SALE + POS_WITHDRAWAL completos | Cerrar un corte de caja |
| `costumer_lambda.py:1456` / `dashboard_lambda.py:967` | COMMISSION_RECEIPT completo | Buscar **1** comprobante |
| `costumer_lambda.py:1041` | CUSTOMER completo | Comprobar si un email ya existe |
| `auth_utils.py:466` | AUTH completo | Buscar el registro del usuario que cambia su contraseña |
| `auth_utils.py:198` | CUSTOMER completo | Fallback de login |
| `commissions_lambda.py:1214-1215` | COMMISSION_MONTH + COMMISSION_RECEIPT completos | Reporte de comisiones de **un** mes |

Dos correcciones, ambas sin migración de datos:

1. **Filtro por fecha en la key condition.** Como `SK = "<createdAt>#<id>"`, basta añadir un
   parámetro a `_query_bucket`:
   ```python
   def _query_bucket(entity, limit=None, forward=False, sk_prefix=None):
       cond = Key("PK").eq(pk)
       if sk_prefix:
           cond = cond & Key("SK").begins_with(sk_prefix)
   ```
   `_query_bucket("POS_SALE", sk_prefix="2026-09")` deja de leer el histórico. Aplica
   directamente a `handle_monthly_stats`, alertas admin, movimientos de inventario y cortes
   de caja.
2. **Búsquedas puntuales por clave.** El email ya existente, el registro `AUTH` por
   `customerId` y el comprobante del mes se resuelven con un item puntero
   (`PK="AUTH_BY_CUSTOMER#<id>"`, `PK="COMMISSION_RECEIPT#<cid>#<mes>"`) en 1 GetItem en vez de
   una colección entera.

---

#### P2-2 · `GET /user-dashboard` y `/customers/dashboard` **escriben** en cada lectura
`dashboard_lambda.py:942-950` y `costumer_lambda.py:1433-1441` hacen `_update_by_id("CUSTOMER", …)`
guardando `goals`, `networkMembers` (hasta 30 filas) y `buyAgainIds` en cada GET.

Tres efectos: (a) un `GET` idempotente consume WCU y puede fallar; (b) el item `CUSTOMER` se
infla con blobs, **encareciendo todas las lecturas completas de la colección** —efecto
compuesto con P2-1—; (c) `_update_by_id` cuesta además 1 GetItem del puntero
(`core_utils.py:146`).

**Corrección:** no persistir un cache derivado en la ruta de lectura; si se quiere conservar,
llevarlo a un item aparte (`PK="CUSTOMER_DASH#<id>"`) para no engordar `CUSTOMER`.

---

#### P2-3 · Paginación de clientes en memoria
`costumer_lambda.py:1546-1600` — `GET /customers/getall?limit=50&nextToken=N` lee **todos** los
clientes y luego hace `items[offset:offset+limit]`. Cada página cuesta lo mismo que la
colección completa. Además, cuando la búsqueda acierta en el índice, resuelve los ids con
`_get_by_id` en bucle (**2 GetItem por resultado**) en vez de `_batch_get_entities`, que ya
existe.

**Corrección:** paginar con `ExclusiveStartKey`/`LastEvaluatedKey` reales (como hace
`_query_customer_order_history`) y sustituir el bucle por `_batch_get_entities("CUSTOMER", ids)`.

---

#### P2-4 · Sin memoización en el motor de comisiones
`commissions_lambda.py:144-165, 247-290` — en un solo `handle_apply_rewards` se invoca
`_calc_vp(cid)` para el mismo cliente hasta una decena de veces (desde `_is_active`,
`_count_active_directs`, `_generation_qualified`), y cada invocación es un `_get_by_id`
(1–3 GetItem). `_load_network_customers` (`commissions_lambda.py:122-142`) resuelve la
descendencia con `_get_by_id` **uno a uno**, y si el cliente no tiene `networkDescendantIds`
persistido cae a leer la colección `CUSTOMER` entera — **una vez por cada `_calc_vg`**.

Medido: **103–143 GetItem secuenciales por orden pagada**, todos evitables.

**Corrección:** un `dict` de memoización por invocación para `_calc_vp`/`_calc_vg`/
`_get_direct_reports`, y sustituir el bucle de `_load_network_customers` por
`_batch_get_entities` sobre el árbol persistido.

`_compute_rank` (`commissions_lambda.py:195-245`) sí memoiza —correcto— pero cada `rank_at`
sobre un descendiente dispara un `_calc_vg` completo, así que el gating de `requiredLeaders`
sigue siendo cuadrático sobre la subred. La nota de rendimiento del documento `04` lo
anticipa; esta auditoría lo confirma y lo cuantifica.

---

#### P2-5 · Sesiones y tokens sin expiración física
`SESSION`, `EMAIL_CONFIRMATION` y `PASSWORD_RESET` se guardan con `_put_entity` (2 items cada
uno). `expiresAt` es una cadena ISO comprobada en código: **no es un atributo TTL de DynamoDB**,
así que nada se borra nunca. La partición `SESSION` crece sin techo y el almacenamiento con
ella. Además, validar un Bearer cuesta 2 GetItem (`_get_by_id("SESSION", token)`) en **cada**
petición autenticada.

**Corrección:** atributo numérico `ttl` (epoch) + TTL habilitado en la tabla; y clave directa
`PK="SESSION#<token>", SK="SESSION"` para validar el token con 1 GetItem.

---

### P3 — Higiene

- **Sin `ProjectionExpression` en ningún sitio (0 ocurrencias).** Cada lectura de colección
  trae el item completo, incluidos `items[]` de pedidos, `images[]` de productos y los blobs
  de dashboard de P2-2. En listados donde solo se usan 4 campos, proyectar reduce los RCU
  consumidos de forma proporcional.
- **`get_admin_orders` (`dashboard_lambda.py:631-640`) y el listado admin de pedidos
  (`order_lambda.py:323-330`)** leen todos los pedidos y luego cortan a `limit`: el `limit` no
  ahorra ninguna lectura.
- **`_backfill_customer_order_history` (`order_lambda.py:287-303`)** recorre la colección
  `ORDER` completa; aceptable como migración puntual, pero conviene que no sea alcanzable
  desde una ruta de usuario.
- **`_query_bucket(entity, limit=N)`** funciona, pero `Limit` en DynamoDB se aplica *antes*
  del filtrado; documentarlo para que nadie lo confunda con "N resultados tras filtrar".

---

## 5. Verificación

La herramienta `Micro-lambda-GMF/python/tools/ddb_query_probe.py` debe reejecutarse tras cada
cambio: el criterio de aceptación es que el **número de viajes a DynamoDB** no crezca de forma
lineal ni cuadrática al pasar de 100 a 800 clientes.

---

## 6. Estado de las correcciones

Todos los hallazgos anteriores están corregidos salvo los dos anotados como pendientes.

| Hallazgo | Estado | Cómo se resolvió |
|---|---|---|
| **P0-1** honor-board O(N²) | ✅ | `_aggregate_vg_by_node`: los estados del mes se cargan en bloque y el VG de todos los nodos sale de un recorrido post-orden iterativo, O(N × niveles). Verificado contra el algoritmo anterior en 120 árboles aleatorios × 3 profundidades: **0 diferencias**; tolera ciclos y cadenas de 2,000 niveles sin `RecursionError` |
| **P0-2** `/user-dashboard` O(N) | ✅ | Usa `utils._load_network_scope` (árbol persistido + `BatchGetItem`). `tienda.component.ts` migrado a `getCatalogData()`; `/catalog/catalog` ahora incluye `categories` y `campaigns`, que era lo único que ataba la tienda al endpoint monolítico |
| **P1-1** 4 `query` truncadas | ✅ | Nuevo `utils._query_all_pages`; aplicado a `COMMISSION_MONTH` (alertas admin), índice de nombres y las dos de `NOTIFICATION_READ` |
| **P1-2** ledger sin bloqueo | ✅ | Atributo `version` + `ConditionExpression` con reintentos (`utils._mutate_ledger_month`), compartido por comisiones y anulaciones. **Prueba de concurrencia:** con 12 escritores simultáneos la implementación anterior persistía 2 de 12 filas; la nueva persiste 12/12 con totales correctos |
| **P1-3** `_put_entity` no transaccional | ✅ | `transact_write_items` con respaldo secuencial si el endpoint no lo soporta; serialización verificada idéntica a la del recurso boto3 |
| **P1-4** índice de nombres parcial | ✅ | `utils._upsert_customer_name_index`, invocado desde el auto-registro, el alta por admin y el renombrado (con borrado de la entrada vieja al cambiar de inicial) |
| **P1-5** reintento sin tope | ✅ | `MAX_BATCH_GET_RETRIES = 8` y error explícito |
| **P1-6** config cacheada para siempre | ✅ | Caché con TTL (`APP_CONFIG_TTL_SECONDS`, 60 s) + `_invalidate_app_config_cache()` |
| **P2-1** lecturas de colección completa | ✅ | `sk_prefix`/`sk_from`/`sk_to` en `_query_bucket` y `_iter_bucket` (con corte anticipado), aplicados a estadísticas mensuales, alertas admin, control y corte de caja POS, bonos y comprobantes. Nuevo índice `REF#EMAIL#<email>` para la comprobación de correo duplicado y `_find_auth_for_customer` para el cambio de contraseña |
| **P2-3** paginación en memoria | ✅ | `/customers/getall` pagina con `ExclusiveStartKey` y `nextToken` opaco; la búsqueda resuelve los ids con `BatchGetItem` |
| **P2-4** sin memoización en comisiones | ✅ | Caché por invocación de clientes, estados y VG; la descendencia sale del árbol persistido. Se limpia al inicio de cada invocación |
| **P2-5** sesiones sin expiración | ⚠️ Parcial | Se escribe el atributo `ttl` (epoch). **Falta habilitar TTL sobre el atributo `ttl` en la tabla** — es configuración de infraestructura, no de código |
| **P1-2 (techo de 400 KB)** | ⏳ Pendiente | El bloqueo optimista cierra la carrera, pero `ledger` sigue siendo una lista dentro de un item. Pasar a un item por fila requiere migrar datos y no se hizo aquí |

### Notas sobre decisiones tomadas

- **`sk_to` es un tope crudo, no un prefijo.** Como el SK lleva la hora,
  `sk_to="2026-08"` deja fuera todo agosto. Para incluir un periodo completo hace falta el
  centinela `"2026-08\uffff"`. Documentado en el docstring y cubierto por pruebas.
- **Filtros por mes de negocio usan `sk_from`, no `sk_prefix`.** Un bono o un comprobante de
  un mes puede emitirse al cierre, es decir el mes siguiente; `begins_with` los habría
  perdido. Solo se usa `sk_prefix` donde el filtro es sobre la propia fecha de creación.
- **`GET /inventory/pos/sales` mantiene el histórico completo por defecto.** Acepta `from`/`to`
  para acotar, pero cambiar el rango por defecto habría roto en silencio los reportes de meses
  anteriores del panel — justo el tipo de truncado que corrige P1-1.
- **`_find_customer_id_by_email` cae al barrido cuando el índice no acierta**, porque los
  clientes anteriores al índice no tienen entrada. Rellena el índice sobre la marcha, así que
  se acelera solo conforme se usa, sin necesidad de una migración previa.
- **`COMMISSION_MONTH` sigue leyéndose entera** en el reporte admin de comisiones: su SK ordena
  por beneficiario, no por fecha, así que no admite recorte por clave sin rediseñar la clave.
