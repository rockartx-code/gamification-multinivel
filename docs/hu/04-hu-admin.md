# Historias de Usuario — Panel de Administración

> **Propósito:** HU de ingeniería inversa del **Panel Admin** de Finding'U, derivadas de
> comportamiento **real** verificado en código. Base para priorizar/diseñar pruebas E2E y
> negociar alcance con el cliente.
> **Fecha:** 2026-08-01
> **Método:** lectura directa de `admin.component.ts` (6,638 líneas — usado como mapa vía
> `docs/qa/01`, con lectura puntual por línea), `admin-campaigns.component.ts`,
> `privileges.model.ts`, `auth.service.ts` y `handler.py` (backend monolito), contrastado contra
> `docs/qa/01`, `docs/qa/02-matriz-pruebas-e2e.md` y `docs/backend-architecture.md`. Donde el
> código difiere de `qa/01`/`02` (mayo 2026) se documenta el comportamiento **actual** y se anota
> la discrepancia.

## Resumen

| # | Título | Prioridad | Cobertura E2E |
|---|---|---|---|
| HU-ADM-01 | Transiciones de estado de pedido con RBAC granular | Crítica | E2E-ADM-01, E2E-ORD-06 |
| HU-ADM-02 | Registro de envío con descuento de stock | Alta | SIN COBERTURA EN MATRIZ |
| HU-ADM-03 | Cancelación con reembolso y comprobante | Alta | E2E-ORD-04, E2E-RET-11 |
| HU-ADM-04 | Inspección de devolución (recibir/rechazar) | Alta | E2E-RET-09, E2E-RET-10 |
| HU-ADM-05 | Alta de orden manual / POS admin | Alta | E2E-ADM-02 |
| HU-ADM-06 | Búsqueda y perfil 360° de cliente | Media | E2E-ADM-03 |
| HU-ADM-07 | Cambio de patrocinador de un cliente | Media | E2E-ADM-04 |
| HU-ADM-08 | Gestión de privilegios de cliente | Media | SIN COBERTURA EN MATRIZ |
| HU-ADM-09 | Carga de documentos de cliente | Media | SIN COBERTURA EN MATRIZ |
| HU-ADM-10 | Alta de empleados con contraseña temporal | Media | SIN COBERTURA EN MATRIZ |
| HU-ADM-11 | Asignación de privilegios a empleado | Media | E2E-ADM-05 |
| HU-ADM-12 | CRUD de productos del catálogo | Alta | E2E-ADM-06 |
| HU-ADM-13 | Producto del mes | Media | E2E-ADM-07 |
| HU-ADM-14 | Gestión de stocks y transferencias | Media | E2E-ADM-08 |
| HU-ADM-15 | Merma de inventario | Media | E2E-ADM-08 |
| HU-ADM-16 | POS: venta de mostrador | Alta | E2E-ADM-09, E2E-ADM-11 |
| HU-ADM-17 | POS: corte de caja | Media | E2E-ADM-10 |
| HU-ADM-18 | Comisiones: registrar comprobante de pago | Alta | SIN COBERTURA EN MATRIZ |
| HU-ADM-19 | Cupones (CRUD) | Media | SIN COBERTURA EN MATRIZ |
| HU-ADM-20 | Campañas: CRUD con assets | Media | SIN COBERTURA EN MATRIZ |
| HU-ADM-21 | Notificaciones: crear/editar con vigencia | Media | E2E-ADM-13 |
| HU-ADM-22 | Configuración de negocio (descuentos/comisiones/rangos/bonos) | Alta | E2E-ADM-14 |
| HU-ADM-23 | Reportes XLSX (5 reportes + comisiones) | Alta | E2E-REP-01..05, E2E-REP-06, E2E-REP-09 |
| HU-ADM-24 | Control de acceso a vistas admin (30 privilegios) | Crítica | E2E-ADM-16, E2E-AUTH-20 |
| HU-ADM-25 | Aviso interno de pedido pendiente en sucursal | Media | E2E-ADM-12 |

Total: **25 HU** · **8 sin cobertura en matriz** · **0 MOCK-ONLY** (el panel admin no usa
`rank`/`vp`/`vg`/`honorBoard`/`bonuses`; sí tiene 1 caso de "backend solo en el split", ver
HU-ADM-19 y Observaciones #2).

---

### HU-ADM-01 — Transiciones de estado de pedido con RBAC granular
**Como** operador admin **quiero** avanzar el estado de un pedido solo si tengo el privilegio
correspondiente **para** que cada cambio quede auditado por rol.
**Prioridad:** Crítica
**Criterios de aceptación:**
- `pending→paid` requiere `order_mark_paid`; `paid→shipped` requiere `order_mark_shipped`;
  `shipped→delivered` requiere `order_mark_delivered`. Sin el privilegio, no se ejecuta llamada.
- Al pasar de `paid`, se abre el modal de envío en vez de avanzar directo (no hay transición sin
  capturar datos de despacho).
**Fuente (código):** `admin.component.ts:3068-3103` (`advanceOrder`)
**Cobertura E2E:** E2E-ADM-01, E2E-ORD-06.

---

### HU-ADM-02 — Registro de envío con descuento de stock
**Como** operador admin **quiero** registrar la guía o entrega personal de un pedido y descontar
el inventario **para** mantener el stock sincronizado con los envíos.
**Prioridad:** Alta
**Criterios de aceptación:**
- Tipo `carrier` exige número de guía; tipo `personal` exige lugar y fecha de entrega.
- Stock de origen obligatorio; sin líneas de despacho (producto+cantidad), se bloquea con
  "Agrega producto y cantidad para descontar stock."
- Requiere `order_mark_shipped`; al confirmar, envía `dispatchLines` junto al cambio a `shipped`.
**Fuente (código):** `admin.component.ts:3105-3182`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-03 — Cancelación con reembolso y comprobante
**Como** operador admin **quiero** subir el comprobante de depósito al reembolsar un pedido
**para** dejar evidencia del pago devuelto.
**Prioridad:** Alta
**Criterios de aceptación:**
- Aplica a pedidos `cancelled` (con `pendingRefund`) o `devuelto_validado`.
- Sin comprobante adjunto, se bloquea con "Adjunta el comprobante de depósito."
- El tipo de contenido se infiere por extensión (`.pdf`→`application/pdf`, si no `image/jpeg`).
**Fuente (código):** `admin.component.ts:3373-3428`
**Cobertura E2E:** E2E-ORD-04, E2E-RET-11.

---

### HU-ADM-04 — Inspección de devolución (recibir/rechazar)
**Como** operador admin **quiero** aprobar o rechazar el paquete recibido de una devolución
**para** decidir si procede el reembolso.
**Prioridad:** Alta
**Criterios de aceptación:**
- **Recibir** (`en_devolucion→devuelto_validado`): exige ≥1 imagen del paquete; envía un
  checklist **fijo con los 7 puntos en `true`** — no hay UI para marcar cada punto
  individualmente pese a que `docs/qa/01` (9.10) describe un checklist granular.
- **Rechazar** (`devuelto_validado→devolucion_rechazada`): exige motivo de texto; envía un
  checklist con puntos ajustados a rechazo.
**Fuente (código):** `admin.component.ts:3432-3540`
**Cobertura E2E:** E2E-RET-09, E2E-RET-10 (agregar borde: UI no permite checklist parcial).

---

### HU-ADM-05 — Alta de orden manual / POS admin
**Como** operador admin **quiero** crear una orden manualmente **para** registrar ventas que no
pasaron por la tienda en línea.
**Prioridad:** Alta
**Criterios de aceptación:**
- Requiere `order_create`.
- El formulario captura cliente (o "Público en general"), líneas de producto/cantidad, método de
  pago y estado inicial de entrega/pago.
**Fuente (código):** `admin.component.ts:3605` (`saveNewOrder`), `2941` (guard)
**Cobertura E2E:** E2E-ADM-02.

---

### HU-ADM-06 — Búsqueda y perfil 360° de cliente
**Como** operador admin **quiero** buscar un cliente y ver su perfil completo (red, comisiones,
documentos) **para** dar soporte y resolver casos.
**Prioridad:** Media
**Criterios de aceptación:**
- Búsqueda por nombre/email; lista paginada (`PAGE_SIZE=15`).
- Al seleccionar, se cargan de forma diferida perfil, comisiones del mes anterior, CLABE y
  documentos.
- Requiere `access_screen_customers`.
**Fuente (código):** `admin.component.ts:397-453`, `421-439`
**Cobertura E2E:** E2E-ADM-03.

---

### HU-ADM-07 — Cambio de patrocinador de un cliente
**Como** operador admin **quiero** reasignar el `leaderId` de un cliente **para** corregir
errores de vinculación en la red.
**Prioridad:** Media
**Criterios de aceptación:**
- El buscador de patrocinador recomienda por nombre/email; se valida el id antes de habilitar
  guardar (`canSaveSelectedCustomerPosition`).
- Al guardar se llama `updateCustomer(id, {leaderId})`; el backend detecta y bloquea ciclos de
  patrocinio antes de persistir.
**Fuente (código):** `admin.component.ts:3920-3943`
**Cobertura E2E:** E2E-ADM-04.

---

### HU-ADM-08 — Gestión de privilegios de cliente
**Como** operador admin **quiero** habilitar acceso admin y privilegios a un cliente **para**
convertirlo en operador sin crear un empleado nuevo.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `user_manage_privileges` para guardar cualquier cambio.
- Otorgar `canAccessAdmin=true` sin tener yo mismo `user_mark_admin` se bloquea silenciosamente
  (no se ejecuta la llamada) — RBAC de dos privilegios cruzados.
- Los privilegios se normalizan (`normalizePrivileges`) a las 30 claves conocidas antes de
  enviarse.
**Fuente (código):** `admin.component.ts:3945-3973`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-09 — Carga de documentos de cliente
**Como** operador admin **quiero** subir documentos (constancia/INE/CURP) de un cliente **para**
completar su expediente.
**Prioridad:** Media
**Criterios de aceptación:**
- Solo se aceptan `application/pdf`, `image/png` o `image/jpeg`; otro tipo se rechaza antes de
  subir.
- Tras subir, la lista de documentos se recarga con confirmación o error específico.
**Fuente (código):** `admin.component.ts:3821`, `4105-4108`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-10 — Alta de empleados con contraseña temporal
**Como** operador admin **quiero** crear un empleado y recibir su contraseña temporal **para**
comunicársela de forma segura.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `employee_add`; nombre y email obligatorios.
- Al crear, el backend genera y devuelve `tempPassword`, mostrada una sola vez.
- Existe además `generateEmployeePassword` para regenerar la contraseña de un empleado existente.
**Fuente (código):** `admin.component.ts:4014-4049`, `4118-4133`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-11 — Asignación de privilegios a empleado
**Como** operador admin **quiero** definir qué pantallas y acciones puede usar cada empleado
**para** limitar el panel según su rol operativo.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `employee_manage_privileges` para guardar.
- Los 30 privilegios (`ALL_PRIVILEGES`) se ofrecen como checklist; el toggle actualiza un
  borrador que solo se persiste al confirmar.
**Fuente (código):** `admin.component.ts:3991-4012`; `privileges.model.ts:49-80`
**Cobertura E2E:** E2E-ADM-05.

---

### HU-ADM-12 — CRUD de productos del catálogo
**Como** operador admin **quiero** crear/editar productos con `vpPoints`, imágenes por sección y
variantes **para** mantener el catálogo actualizado.
**Prioridad:** Alta
**Criterios de aceptación:**
- Crear requiere `product_add`; editar `product_update`; eliminar `product_delete` — gateados
  independientemente según exista `productForm.id`.
- El guardado sube primero imágenes de producto/variantes antes de enviar el payload final
  (`sku`, `tags`, `commissionable`, `inOnlineStore`, `inPOS`).
- Eliminar pide confirmación previa antes de ejecutar.
**Fuente (código):** `admin.component.ts:4372-4507`
**Cobertura E2E:** E2E-ADM-06.

---

### HU-ADM-13 — Producto del mes
**Como** operador admin **quiero** marcar un producto como "producto del mes" **para** que se
destaque en dashboard/landing.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `product_set_month`.
- Solo hay un producto del mes activo a la vez (se reemplaza al confirmar uno nuevo).
- El cambio es visible de inmediato en el dashboard del asociado vía `_get_user_dashboard`.
**Fuente (código):** `admin.component.ts:4346-4369`; `handler.py:6092-6097`
**Cobertura E2E:** E2E-ADM-07.

---

### HU-ADM-14 — Gestión de stocks y transferencias
**Como** operador admin **quiero** crear almacenes/sucursales, vincular usuarios y transferir
inventario entre ellos **para** operar la logística multi-sucursal.
**Prioridad:** Media
**Criterios de aceptación:**
- Crear stock requiere `stock_create` (nombre y ubicación obligatorios).
- Registrar entrada requiere `stock_add_inventory`, cantidad entera > 0.
- Crear transferencia requiere `stock_create_transfer`: origen ≠ destino, ≥1 línea válida, y
  valida stock suficiente en origen **antes** de enviar al backend.
- Recibir transferencia requiere `stock_receive_transfer` y que el receptor esté vinculado
  (`linkedUserIds`) al stock destino.
**Fuente (código):** `admin.component.ts:4880-4900`, `4960-4979`, `5109-5187`
**Cobertura E2E:** E2E-ADM-08.

---

### HU-ADM-15 — Merma de inventario
**Como** operador admin **quiero** registrar productos dañados/perdidos **para** mantener el
stock real actualizado.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `stock_mark_damaged`; cantidad entera > 0 y motivo obligatorios.
- Se valida que la cantidad dañada no exceda el stock disponible antes de enviar.
**Fuente (código):** `admin.component.ts:5206-5230`
**Cobertura E2E:** E2E-ADM-08 (ampliar con caso dedicado a merma).

---

### HU-ADM-16 — POS: venta de mostrador
**Como** cajero/operador admin **quiero** registrar una venta de mostrador con su método de pago
**para** cerrar ventas físicas en sucursal.
**Prioridad:** Alta
**Criterios de aceptación:**
- Requiere `pos_register_sale` y un stock POS con líneas de producto.
- Antes de registrar, valida disponibilidad de stock; si falla, no llama al backend.
- Soporta descuento de cajero, pago parcial/crédito (`paymentType!=='full'` con `amountPaid`) y
  código de autorización de tarjeta; se registra con `paymentStatus:'paid_branch'` y
  `deliveryStatus:'delivered_branch'` fijos.
**Fuente (código):** `admin.component.ts:5568-5620`
**Cobertura E2E:** E2E-ADM-09, E2E-ADM-11.

---

### HU-ADM-17 — POS: corte de caja
**Como** operador admin **quiero** hacer corte de caja indicando cuánto efectivo dejo **para**
cuadrar el turno de ventas en sucursal.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere permiso de corte y un stock POS activo.
- El monto a dejar debe ser numérico ≥0 y no superar el total disponible en caja — ambas
  validaciones bloquean en frontend.
**Fuente (código):** `admin.component.ts:5622-5670`
**Cobertura E2E:** E2E-ADM-10.

---

### HU-ADM-18 — Comisiones: registrar comprobante de pago
**Como** operador admin **quiero** subir el comprobante de depósito de comisiones de un asociado
**para** dejar constancia de que se le pagó.
**Prioridad:** Alta
**Criterios de aceptación:**
- Requiere `commissions_register_payment` tanto para abrir el modal como para confirmar.
- El mes asociado es `commissionsPrevMonthKey` del cliente o el mes anterior calculado en
  frontend.
- Sin archivo seleccionado, se bloquea con "Selecciona un comprobante."
**Fuente (código):** `admin.component.ts:2984-3056`; `handler.py:5457`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-19 — Cupones (CRUD)
**Como** operador admin **quiero** crear, editar y desactivar cupones de descuento **para**
ofrecer promociones controladas en el checkout.
**Prioridad:** Media
**Criterios de aceptación:**
- Código, valor > 0, tipo, vigencia, subtotal mínimo y máximo de redenciones son campos del
  formulario; el código se normaliza a mayúsculas.
- "Eliminar" en realidad **desactiva** el cupón (`active=false`), con confirmación previa.
- El carrito ya tiene un campo de cupón conectado a `POST /coupons/validate`; este panel
  gestiona el catálogo de cupones consumido ahí.
- **Discrepancia crítica de backend:** `docs/qa/01` (6.12, 13.13) documenta cupones como
  ausentes; hoy el frontend (admin y carrito) implementa la funcionalidad completa, pero
  `/coupons`, `/coupons/{code}` y `/coupons/validate` **no existen en el monolito `handler.py`**
  (0 ocurrencias de "coupon") — sí están en `Micro-lambda-GMF/python/order_lambda.py`. Si el
  monolito es el backend desplegado (`docs/backend-architecture.md` §2), este módulo falla con
  404 en producción.
**Fuente (código):** `admin.component.ts:5958-6041`; `order_lambda.py:1214-1348`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ — confirmar backend desplegado antes de diseñar E2E.

---

### HU-ADM-20 — Campañas: CRUD con assets
**Como** operador admin **quiero** crear campañas con imágenes por formato (story/feed/banner)
**para** alimentar el carrusel de destacados del dashboard.
**Prioridad:** Media
**Criterios de aceptación:**
- Exige al menos una imagen o URL para story/feed/banner antes de habilitar guardar.
- Cada asset puede subirse como archivo (con preview) o capturarse como URL directa.
- Campos hero (badge/título/acento/cola/descripción) tienen valores por defecto si se dejan
  vacíos.
**Fuente (código):** `admin-campaigns.component.ts:94-177`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-ADM-21 — Notificaciones: crear/editar con vigencia
**Como** operador admin **quiero** publicar avisos con fecha de inicio/fin y link opcional
**para** comunicarme con los asociados desde el portal.
**Prioridad:** Media
**Criterios de aceptación:**
- Requiere `config_manage`. Título y descripción obligatorios; descripción tiene un límite
  máximo validado también en backend.
- `startAt`/`endAt` obligatorios y `endAt` debe ser ≥ `startAt`, o el backend rechaza.
- Con `linkUrl` sin `linkText`, el backend asigna texto por defecto ("Ver"); sin `linkUrl`, se
  limpia cualquier `linkText`.
**Fuente (código):** `admin.component.ts:4507-4542`; `handler.py:5599-5687`
**Cobertura E2E:** E2E-ADM-13.

---

### HU-ADM-22 — Configuración de negocio (descuentos/comisiones/rangos/bonos)
**Como** operador admin **quiero** editar tramos de descuento, niveles de comisión, rangos y
reglas de bonos **para** ajustar el plan de compensación sin desplegar código.
**Prioridad:** Alta
**Criterios de aceptación:**
- Requiere `config_manage` para guardar y para restaurar valores por defecto.
- Antes de guardar, se normalizan tramos/niveles y se validan selects contra listas permitidas,
  cayendo a un default seguro si el valor no es válido (p. ej. `cutRule`→`hard_cut_no_pass`).
- "Restaurar valores por defecto" solo actualiza el borrador local; no persiste hasta guardar de
  nuevo.
**Fuente (código):** `admin.component.ts:6197-6270`
**Cobertura E2E:** E2E-ADM-14.

---

### HU-ADM-23 — Reportes XLSX (5 reportes + comisiones)
**Como** operador admin **quiero** exportar reportes de pedidos, clientes, productos, stocks,
mensual consolidado y comisiones **para** analizar el negocio fuera del panel.
**Prioridad:** Alta
**Criterios de aceptación:**
- Cada reporte usa `buildSheet(rows, headers)`: si `rows` está vacío, genera encabezados vía
  `aoa_to_sheet([headers])` en vez de una hoja vacía — corrige el comportamiento nativo de
  `json_to_sheet([])`.
- **Discrepancia con matriz:** `docs/qa/02` da por no resuelto el problema de encabezados
  vacíos (E2E-REP-06) y por inexistente el reporte de comisiones (E2E-REP-09). Ambos ya están
  implementados: `buildSheet` (comentario "H11" en el código) y `downloadCommissionsReport`
  (hojas "Resumen" y "Desglose por árbol", `comisiones-{mes}.xlsx`).
- El reporte de comisiones desglosa por líder: comisión ganada vs perdida por miembro del árbol,
  con motivo de pérdida.
- Reportes de red (E2E-REP-10) y de rangos (E2E-REP-11) **siguen sin existir** — confirmado, no
  hay función `download*Report` para ninguno de los dos.
**Fuente (código):** `admin.component.ts:1806-1814`, `1816-2017`, `2472-2736`
**Cobertura E2E:** E2E-REP-01..05, más E2E-REP-06 y E2E-REP-09 **deben actualizarse en la
matriz** (ya no son hallazgos abiertos).

---

### HU-ADM-24 — Control de acceso a vistas admin (30 privilegios)
**Como** administrador del sistema **quiero** que cada usuario admin solo vea las pantallas para
las que tiene privilegio **para** aplicar mínimo privilegio.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Existen exactamente **30 privilegios** (`ALL_PRIVILEGES`) y 12 vistas (`AdminViewId`); las
  vistas `campaigns`/`stocks` comparten `access_screen_stocks`, y `notifications`/`coupons`
  comparten `config_manage`.
- Un "superusuario" (`isSuperUser`) tiene todos los privilegios, ignorando el mapa individual.
- La vista inicial es la primera de una lista ordenada fija a la que el usuario tenga acceso; si
  pierde acceso a la vista actual, se reubica automáticamente.
- **Nota:** la vista `coupons` no figura en esa lista ordenada, por lo que nunca se selecciona
  automáticamente aunque el usuario tenga `config_manage` — solo alcanzable navegando manual.
**Fuente (código):** `privileges.model.ts:1-96`; `auth.service.ts:157-172`;
`admin.component.ts:2044-2061`
**Cobertura E2E:** E2E-ADM-16, E2E-AUTH-20 (agregar borde para `coupons` excluida del fallback).

---

### HU-ADM-25 — Aviso interno de pedido pendiente en sucursal
**Como** operador admin **quiero** ver una alerta cuando un pedido de recolección en sucursal
está pendiente de pago/entrega **para** no dejar clientes esperando.
**Prioridad:** Media
**Criterios de aceptación:**
- El backend arma `adminWarnings` combinando configuración con el estado real de pedidos
  `pickup`/`at_store` pendientes.
- El admin consume `GET /dashboard/admin/warnings` y muestra la lista, cacheada por referencia
  para evitar recomputar en cada ciclo de detección de cambios.
**Fuente (código):** `admin.component.ts:917-1006`; `handler.py:1372`, `1462`, `1501`, `5750`
**Cobertura E2E:** E2E-ADM-12.

---

## Observaciones para QA

1. **Matriz desactualizada en reportes:** `docs/qa/02` marca E2E-REP-06 y E2E-REP-09 como
   hallazgos abiertos; el código ya los resuelve (`buildSheet`, `downloadCommissionsReport`).
   Actualizar la matriz antes de planear regresión, para no re-reportar bugs ya corregidos.
2. **Cupones: backend solo en el split.** El frontend tiene la funcionalidad de cupones completa
   conectada a `/coupons*`, pero esas rutas no existen en el monolito `handler.py` (probable
   backend de producción). Confirmar en AWS qué Lambda está detrás de producción antes de
   escribir E2E para HU-ADM-19 — si es el monolito, el módulo está roto en producción pese a
   verse completo en frontend.
3. **RBAC anidado en clientes:** un admin sin `user_mark_admin` no puede otorgar acceso admin a
   un cliente aunque tenga `user_manage_privileges` — regla de dos privilegios cruzados que vale
   la pena cubrir explícitamente (HU-ADM-08), no solo probar cada privilegio aislado.
4. **Gaps de UI, no solo de pruebas:** el checklist de devolución (7 puntos según `docs/qa/01`
   9.10) solo ofrece "aprobar todo" o "rechazar con motivo" en la UI admin, sin granularidad; y
   la vista `coupons` queda fuera de la lista ordenada de `getFirstAllowedView`, por lo que nunca
   se selecciona automáticamente aunque el usuario tenga `config_manage`. Confirmar con negocio
   si ambos son intencionales.
5. **Reportes de red y de rangos siguen ausentes:** confirmado que no existe función de descarga
   para ninguno (E2E-REP-10/11 siguen vigentes como ausentes, a diferencia de comisiones). Si el
   negocio los requiere, es desarrollo pendiente real, no solo prueba.
