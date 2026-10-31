# 23 · Implementación de las 23 propuestas: ocho paquetes, dos transversales, revisión y validación

Continuación de [22](22-diarios-inquietudes-friccion-automatizacion.md). Aquella lectura de 89 diarios terminó en 23 propuestas (§7) y una tabla de estado (§10) en la que 13 estaban "sin empezar", 9 "parciales" y una era decisión de negocio. Este documento cuenta qué se hizo con cada una en la rama `claude/ultimos-cambios-integrados-fylhiw` entre `99879bc` (el commit de [22]) y `acca507`: el diseño ([arquitectura/23](../arquitectura/23-propuestas.md)), los ocho paquetes en paralelo, las dos transversales, lo que encontraron las revisoras, lo que vivieron cinco personas el 12 de enero de 2027 en el mundo simulado y lo que se corrigió después.

Todo lo que aquí se afirma se puede comprobar con `git log --oneline 99879bc..HEAD` (41 commits antes de este informe) y con los diarios nuevos `sim/diarios/{diana,sofia,beto,nadia,claudia}-ene12.md`.

## 1. Resumen ejecutivo

| | |
|---|---|
| Propuestas de [22] §7 | 23; **20 implementadas**, **3 parciales** (17 factura sin timbrado, 20 paquetería sin webhook ni endpoint real, 22 opción b con la tarea diaria sin desplegar), ninguna sin empezar |
| Cómo se hizo | Un contrato de propiedad de archivos ([arquitectura/23](../arquitectura/23-propuestas.md)); ocho agentes en worktrees a la vez sobre `afc604a` (ola A); dos transversales sobre el árbol integrado (ola B); dos revisoras de código y de navegador; cinco personas en el harness; dos commits de corrección por fase |
| Tamaño del cambio | `git diff --shortstat 99879bc..HEAD`: 145 archivos, +24,051 / −1,382 líneas; 79 archivos nuevos; 41 rutas nuevas de API y 8 ampliadas; 4 pantallas nuevas del back office (`/#/admin/despacho`, `/#/admin/resumen-turno`, `/#/admin/seguimiento`, Pagos del mes dentro de Clientes) y 2 del socio (`/#/modo-socio`, `/#/orden/:id/devolucion` reescrita) |
| Pruebas del backend | 147 → **392 en verde** (27 archivos de prueba nuevos); `tools/check_query_budget.py` en verde (ORDER_PAID 37 GetItem, tope 40, después de haber subido a 47 en la integración) |
| Frontend | `tsc`, `ngc --strictTemplates` y `ng build` de producción en verde; el bundle inicial subió a 2.25 MB y el tope de error de `angular.json` se movió de 2 a 3 MB (§6) |
| Hallazgos de las revisoras | 22 (2 graves, 10 medias, 10 bajas); 18 corregidos, 3 parciales, 1 descartado con justificación (§3) |
| Validación con personas | 5 diarios del 12-ene (Diana, Sofía, Beto, Nadia, Claudia), 54 fallas reportadas; 31 corregidas en `b0712e6` + `acca507`, 12 son datos o reloj de la simulación, 11 quedan como decisión de producto (§4, §5) |
| Cobertura de rutas | `sim/cobertura.py`: 79 rutas declaradas en `real-api.service.ts`, 73 alcanzadas, 6 nunca tocadas (las mismas de [21] §5); además 11 rutas nuevas alcanzadas que el script no reconoce porque viven en los servicios por paquete (§7) |
| Estado del mundo | Reloj de la simulación en 13 de enero de 2027, 10:00 (a las personas se les dijo "12"); diciembre pagado a Verónica; Claudia con CLABE capturada y $195.20 pendientes; tres pedidos despachados en el lote `DSP-9F7663254C` |

### 1.1 Las 23 propuestas, una por una

Columna "Commit": el primero es el commit del paquete en su worktree; entre paréntesis, el merge en la rama. Las correcciones posteriores (`89b2b50`, `72fedc3`, `b0712e6`, `acca507`) se citan cuando tocan esa propuesta.

| # | Propuesta ([22] §7) | Paquete | Estado | Commit | Qué se implementó |
|---|---|---|---|---|---|
| 1 | Modo "solo cliente" | B | **Implementado** | `141bc18`, `1f759d7` (`fa1a386`); `72fedc3` | Atributo `mode` cliente/socio: todo registro nuevo nace cliente, las fichas existentes quedan socio; en modo cliente el panel oculta red, VP, comisiones, CLABE y datos fiscales y muestra "Tu cuenta en modo cliente" (compra del mes, ahorro como socia); pasa a socio por solicitud (`POST /customers/modo-socio`), por referido o por comisión; aviso de privacidad por modo; el Cuadro de Honor y su modal también se ocultan (corrección) |
| 2 | Plan publicado | B | **Implementado** (sin PDF, decisión 3) | `141bc18`, `1f759d7`; `acca507` | `GET /catalog/plan` con todos los números desde `config` y ejemplos calculados; landing pública `/#/modo-socio` con nueve secciones (PC/VP/VG, generaciones y requisitos, tabla de descuento, qué se pide y cuándo) y botón "Activar modo socio"; enlace "cómo se calculan" desde Comisiones del panel (corrección tras Claudia) |
| 3 | Tabla única de descuento y VP | B, I1, I2 | **Implementado** | `1f759d7`; `8c49e49` (`b4bffe4`); `2e52f73` (`9905159`); `72fedc3` | Componente `ui-tabla-descuento` con contexto panel/carrito/pos/plan y el mismo vocabulario (tramo actual, siguiente tramo, cuánto falta, "los VP se cuentan sobre el precio con descuento"); montado en el panel (B), el POS (I1) y el carrito (I2). La revisora encontró el POS sin tramos (no se cargaba la config) y el carrito con el bloque viejo de "Nivel"; ambos corregidos. Queda la meta "Alcanzar nivel 2" del backend con el vocabulario antiguo |
| 4 | CLABE al activarse | A | **Implementado** | `8d20323`, `2aa3d37` (`717a640`); `b0712e6`, `acca507` | Aviso "registra tu CLABE" por correo y aviso dirigido en el panel al activarse por primera vez y al confirmarse la primera comisión del mes (uno por motivo y mes, respeta "no contactar"); "Acciones urgentes" separa `commissions_ready` de `commissions_no_clabe` con monto; el aviso se apaga al capturar la CLABE y administración puede capturarla desde la ficha (correcciones tras Claudia y Sofía) |
| 5 | Completa tu activación | C, I2 | **Implementado** | `587ccc4`, `be71ad9` (`d01fcf1`); `1763752` | `POST /orders/checkout/sugerencia-activacion`: el producto más barato que cierra los VP, con botón "Agregar" junto al aviso "llegas a X de 20 VP"; la misma fórmula (`checkout_handlers.sugerir_producto_activacion`) alimenta el correo de bloqueadas del día 20 (I2 unificó la copia de A) |
| 6 | Envío visible | C | **Implementado** | `587ccc4`, `be71ad9` | `GET /orders/checkout/envio-info`: tarifa base y faltante para envío gratis medidos sobre el subtotal bruto (`shipping.freeShippingBasis = "gross"`; `"net"` conserva la regla anterior); visible en el carrito antes de la dirección |
| 7 | Sesión persistente y último código | C, I2 | **Implementado** | `587ccc4`, `be71ad9`; `255303b` | "Recordarme en este dispositivo" (30 días en `localStorage`) o 24 h en `sessionStorage`; enlace de acceso por correo (`POST /auth/enlace-acceso`, un uso, 15 min); la recuperación acepta los tres últimos códigos vigentes y comprueba caducidad; un 401 con sesión vuelve al login con `?next=` sin perder el carrito |
| 8 | Botones que explican por qué y un solo DOM | E, I1 | **Implementado** | `a08c0d6` (`95c6823`); `3cd2c73`, `8c49e49` | `ui-button.disabledReason` en los 61 `[disabled]` del monolito y en las pantallas nuevas; `ui-data-table` pinta solo la plantilla del ancho actual; Clientes y Productos con una sola fila adaptada por CSS. Nadia: "esta vez casi cada botón gris me dijo qué le faltaba" (nadia-ene12) |
| 9 | Sucursal por defecto del empleado | D | **Implementado** | `9a9ae69`, `1d8a57d` (`7070bba`); `acca507` | `GET/PUT /inventory/despacho/preferencias` (`defaultStockId` en el empleado), aplicada en Stocks, Despacho y POS. Beto encontró que sin bodega guardada se proponía la de otra sucursal; corregido: sin bodega por defecto no se propone ninguna |
| 10 | Sin `prompt()` ni `confirm()` | I1 | **Implementado** | `3cd2c73`, `8c49e49`, `657f769` | Componente `ui-confirm` (título, efecto escrito, motivo obligatorio, resultado del servidor); los 7 `prompt/confirm` que quedaban (cancelar pedido, deshacer pago, baja ARCO, desactivar empleado, recibir traspaso, cupón) sustituidos; `grep` en `pages/admin`: 0 |
| 11 | Recoger en sucursal condicionado | C | **Implementado** (datos por capturar) | `587ccc4`, `be71ad9`; `89b2b50`, `72fedc3` | `POST /orders/checkout/sucursales-recoger`: solo sucursales con `allowPickup` en la ciudad/estado del cliente y con existencia; los almacenes ganan `city`/`state` (formulario en Stocks). Los almacenes del harness no tenían ciudad y el carrito mostraba direcciones como ciudades; corregido para nombrar la sucursal. Falta capturar ciudad/estado en los almacenes existentes |
| 12 | Pantalla "Pagos del mes" | A | **Implementado** | `8d20323`, `2aa3d37`; `89b2b50`, `acca507` | `GET /commissions/pagos` (listas / sin CLABE / pagadas, CLABE enmascarada), CSV de dispersión con CLABE completa, pago por lote con un comprobante (`COMMISSION_PAYMENT_BATCH`, saltos por fila), deshacer por fila, "Pedir CLABE" (correo + aviso dirigido + bitácora). Sofía: "Esto es justo lo que Ricardo quería: pagar por lote sin abrir ficha por ficha" (sofia-ene12); lo que faltaba (capturar la CLABE que le mandaron por WhatsApp) se añadió a la ficha en `acca507` |
| 13 | Despacho en bloque con lista de surtido | D | **Implementado** | `9a9ae69`, `1d8a57d`; `72fedc3`, `89b2b50`, `acca507` | `/#/admin/despacho`: pendientes pagados a domicilio, surtido consolidado con semáforo y qué bodega sí tiene el faltante, guías a mano / CSV / paquetería, "Despachar" con confirmación y lote `DISPATCH_BATCH`; cada pedido pasa por `handle_update_status` (inventario y correo una sola vez). Beto despachó tres pedidos "de un jalón" (beto-ene12) |
| 14 | Suscripción mensual | H, I2 | **Implementado** (sin cobro automático, decisión 12) | `bb30715`, `4b9495f` (`e792b2b`); `e4a352f`; `acca507` | Entidad `SUBSCRIPTION` con día 1–28, pausa de un mes y cancelación; `POST /orders/suscripciones/generar` (programable) crea el pedido con el tramo real, genera el enlace de MercadoPago y lo manda por correo; `app-suscripcion` montado en Órdenes del panel. Claudia la guardó (`SUS-7F3F1BD1`) pero con "Recoger en sucursal" porque no tenía dirección guardada; el texto ahora manda a guardarla al pagar. Falta mostrar VP y avisar que el mes en curso queda sin activar |
| 15 | Seguimiento de hoy | F | **Implementado** | `096077f`, `5347ee7` (`bc1d397`); `89b2b50`, `b0712e6` | `/#/admin/seguimiento`: lista priorizada por días sin compra y sin contacto con teléfono (wa.me), patrocinadora, ejecutiva, origen y último pedido; situaciones bienvenida / fría / CLABE pendiente / pedido tardío / activa; plantillas de WhatsApp que registran la nota al pulsarse (`POST /customers/{id}/contacto`); excluye "no contactar" y otras carteras. Sofía la usó para mandarle la lista a Ivonne. "Pedido tardío 0" con cuatro pagados sin envío se corrigió en `b0712e6` |
| 16 | Arqueo de caja | E | **Implementado** | `ae1b0c1`, `a08c0d6`; `b0712e6`, `acca507` | Efectivo esperado = fondo + ventas y abonos en efectivo + parte en efectivo de mixtas − retiros; conteo por denominación; diferencia con motivo obligatorio; destino fondo/retiro con código y receptor; comprobante con folio y montos del servidor (imprimir o correo); retiro guiado con tope; pago mixto. Nadia cerró `CUT-5DB5A173` con $50 de sobrante y motivo. Correcciones: ventas huérfanas entran al corte, "Retirar una parte" propone dejar el fondo, "Efectivo del turno" en lugar de "Total" |
| 17 | Factura automática | C | **Parcial** (sin timbrado, decisión 4) | `587ccc4`, `be71ad9` | Casilla "Quiero factura" en el checkout con datos fiscales (`POST /orders/{id}/factura`), estado `solicitada` → `emitida` a mano con folio y archivo desde el back office (`app-factura-pedido`), insignia en Pedidos, frase en el correo de pago. No hay timbrado CFDI ni emisión automática al pagar |
| 18 | Devolución por producto y evidencia según motivo | G | **Implementado** | `7b05347`, `8e9f7e4` (`f0f48de`); `89b2b50` | `POST /orders/{id}/return` con `lines[]`, evidencia por motivo (una foto del paquete cerrado en desistimiento; producto + empaque + guía en daño), reembolso sugerido por líneas con desglose, "te devolvemos $X al mismo medio de pago en 3 a 5 días hábiles" en pantalla y correos (también al cancelar un pedido pagado); inspección por línea y ajuste con motivo en el back office; `GET /orders/{id}/devolucion`. La devolución parcial anula la comisión completa (decisión 14) |
| 19 | Ficha unificada | F, B | **Implementado** | `096077f`, `5347ee7` | Invitados con ficha (`POST /customers/seguimiento/ficha-invitado` liga sus pedidos), preferencia de contacto y ejecutiva asignada (`PATCH /customers/{id}`, editables desde el modal "Ficha" de Seguimiento), origen visible; sin patrocinadora, el panel muestra a la ejecutiva como "Tu coach en Finding'U" con WhatsApp (`_find_effective_sponsor`). Los dos campos no están en la ficha del monolito de Clientes, solo en Seguimiento |
| 20 | Integración con la paquetería | D | **Parcial** | `9a9ae69`, `598ebc8`; `89b2b50` | Adaptador `carriers.py` (Envia + simulada), guía desde Despacho, rastreo por consulta programable (`POST /inventory/envios/rastrear`) que marca entregado con fecha y firma, correo "¿te llegó?" a los 7 días con botón que confirma (`confirmar-entrega`, ahora solo por POST) y cierre a 10 días. Apagado por omisión (`shipping.carrierIntegration.enabled = False`); sin webhook; los endpoints de Envia no se validaron contra la API real; la tarea diaria no está desplegada (EventBridge documentado) |
| 21 | Conciliación con la pasarela | H | **Implementado** | `bb30715`, `ae1b1d4`; `89b2b50` | Webhook de MercadoPago con `webhookSecret` (401 si no coincide o, con la pasarela encendida, si falta), idempotencia (`paid` → `paid` no repite SFN ni correo), `paymentId`/`paidVia` en el pedido; `POST /orders/conciliacion` (72 h por `payments/search`) con botón "Conciliar pagos" en Pedidos; un pago aprobado sobre un pedido cancelado ya no lo reactiva (`approved_after_cancel` con reembolso pendiente). La firma `x-signature` queda como mejora posterior |
| 22 | Política de comisiones bloqueadas | A | **Implementado** (opción b; tarea programada sin desplegar) | `8d20323`; `1763752` | Decisión 1 de arquitectura/23: avisos los días 20 y 27 (`rewards.blockedNoticeDays`) con el monto bloqueado y el producto que lo salva (`POST /commissions/avisos/bloqueadas`, idempotente por día, `dryRun`/`force`); la opción a queda como `rewards.blockedGraceDays = 0`; la c no se implementa. En el harness corre con el reloj (`POST /__sim/tareas`); en AWS falta el cableado EventBridge → API Gateway |
| 23 | Resumen de turno y confirmaciones desde el servidor | D, I1, I2 | **Implementado** | `9a9ae69`, `598ebc8`, `1d8a57d`; `8c49e49`, `657f769`; `2e52f73`, `e4a352f` | `GET /inventory/turno/resumen` y `/#/admin/resumen-turno` (despachados, entregados, transferencias, entradas, mermas, ventas y cortes, texto para WhatsApp); toda confirmación del back office y del panel del socio repite el dato guardado leído de la respuesta (folio, monto, estado nuevo, existencia resultante) |

## 2. Arquitectura: cómo se repartió el trabajo

[arquitectura/23](../arquitectura/23-propuestas.md) (`afc604a`, 756 líneas) es el contrato de la ronda. Su idea central: ocho agentes trabajan **a la vez** sobre la misma base, así que cada paquete tiene una lista cerrada de archivos **propios** y una lista de archivos **compartidos** donde solo cabe un *edit mínimo* descrito por función o bloque (una línea de montaje, un `import`, una entrada en una lista). Los componentes que un paquete construye y otro monta tienen selector e *inputs* fijados de antemano.

### 2.1 Convenciones que sostuvieron la ronda

- **Extensiones en cascada en el backend**: cada paquete nuevo es un módulo `*_handlers.py` con `atender(method, path, body, actor)`; los lambdas recorren una lista `_EXTENSIONES` antes de sus rutas propias (`order_lambda`: checkout, devoluciones, suscripciones, conciliación; `inventory_lambda`: despacho, caja; `customer_lambda`: seguimiento, modo). Los lambdas declarativos (`commissions`, `catalog`) usan `RUTAS.extend`. Las tareas programables se descubren por atributo `TAREAS_PROGRAMADAS` desde el hook del reloj del harness.
- **Frontend sin tocar `api.service.ts`**: cada paquete trae su servicio (`pagos.service.ts`, `plan-socio.service.ts`, `checkout.service.ts`, `despacho.service.ts`, `caja.service.ts`, `seguimiento.service.ts`, `devoluciones.service.ts`, `suscripcion.service.ts`, `conciliacion.service.ts`) con `HttpClient` y `RealApiService.actorHeaders()` hecho público; el modo mock queda sin estas funciones (aceptado en §0.5).
- **Mapa de regiones de `admin.component.{ts,html}`** (§0.6): el monolito de 8,000 líneas se repartió por bloques (Pedidos a C y G, Clientes a A, B y F, POS a E, Stocks a D…) y cada pantalla nueva es un componente *standalone* `OnPush` montado con una línea.
- **Sin privilegios, índices ni `template.yaml` nuevos**; EventBridge documentado, no desplegado; `openapi-aws.yaml` con un bloque `# ── Paquete X` por paquete y las instantáneas de ruteo `tests/rutas/*.json` regeneradas.

### 2.2 Los paquetes

| Paquete | Propuestas | Rutas nuevas (ampliadas) | Pruebas nuevas | Pantallas |
|---|---|---|---|---|
| A `pagos-comisiones` | 4, 12, 22 | 5 | 26 | Pagos del mes (dentro de Clientes), avisos en Acciones urgentes |
| B `modo-cliente-y-plan` | 1, 2, 3 | 4 (+ `/#/modo-socio`) | 29 | Landing del plan, panel en modo cliente, `ui-tabla-descuento`, `ui-ahorro-socio`, columna Modo en Clientes |
| C `checkout-y-sesion` | 5, 6, 7, 11, 17 | 7 | 29 | Carrito (activación, envío, sucursales, factura), login con "Recordarme" y enlace por correo, factura en Pedidos, ciudad/estado en Stocks |
| D `almacen-despacho-paqueteria` | 9, 13, 20, 23a | 9 (+ 2 rutas del front) | 27 | `/#/admin/despacho`, `/#/admin/resumen-turno`, bodega por defecto |
| E `caja-arqueo` | 16, 8 (POS) | 3 (3) | 14 | Arqueo en 4 pasos, retiro guiado, pago mixto, botones con motivo en el POS |
| F `coach-seguimiento` | 15, 19 | 4 (1) | 27 | `/#/admin/seguimiento`, ficha de invitado, coach en el panel |
| G `devoluciones` | 18 | 1 (3) | 28 | Asistente de devolución en 4 pasos, modales de inspección y reembolso |
| H `pasarela-y-suscripcion` | 14, 21 | 8 (1) + 3 del harness | 38 | `app-suscripcion`, "Conciliar pagos" en Pedidos, pasarela con estado en `sim/servidor.py` |
| I1 `transversal-admin` | 8, 10, 23b | 0 (1) | 3 | `ui-confirm`, `disabledReason`, un solo DOM, tabla en el POS |
| I2 `transversal-socio` | 3, 5, 7, 14, 23 | 0 | 3 | Tabla y ahorro en el carrito, suscripción en Órdenes, interceptor 401, `?next=` |

### 2.3 Decisiones tomadas sobre lo ambiguo (arquitectura/23 §13)

Las que cambian lo que ve la gente: **política 22 = opción b**, con la a como parámetro apagado y sin la c; **todo registro nuevo nace cliente**, en modo cliente no aplica la escalera de descuento (paga lista y el pedido guarda `partnerSavings`) para que "como socia habrías ahorrado $X" sea verdad, y el volumen sí se acredita; **plan sin PDF** (la landing es imprimible); **factura sin timbrado**; **envío gratis sobre el subtotal bruto**; **recoger en sucursal solo con sucursal en la ciudad y con existencia**; **"Recordarme" marcado por omisión**; **paquetería apagada por omisión**, rastreo por consulta y no por webhook, cierre a 10 días con correo a los 7; **despacho parcial permitido** tras validar el surtido y sin pedidos pickup; **pago por lote con un comprobante** y deshacer por fila; **suscripción sin cobro automático** (el día indicado se crea el pedido y se manda el enlace de pago); **secreto del webhook en la query** con `x-signature` como mejora posterior; **devolución parcial anula la comisión completa**; **el WhatsApp lo manda la persona** (`wa.me`), el sistema prellena y anota.

### 2.4 Integración

- **Ola A** (`717a640` … `e792b2b`, en el orden A→B→C→D→E→F→G→H): 13 conflictos, todos en archivos compartidos previstos por §0.7 (`openapi-aws.yaml`, `admin.component.ts`, `order_lambda._EXTENSIONES`, `inventory_lambda._EXTENSIONES`, `customer_lambda._EXTENSIONES`, `core/config.py`, `core/order_emails.py`, `auth.service.ts`, `app.routes.ts`, `admin.model.ts`, `user-dashboard.model.ts`, las instantáneas de ruteo). Los ocho worktrees nacieron en `main` (`22085de`, 169 commits atrás) y cada agente hizo *fast-forward* a `afc604a` antes de trabajar; ninguno tocó archivos ajenos salvo tres casos declarados (`.env.example` en D por `test_infraestructura`; `_serialize_order_list_item` y `normalizeAdminOrder` en C; un bloque de Devolución en el detalle de pedido en G).
- **Correcciones de integración** (`0d5ac92`): `SesionAbierta.user.mode` tipado como `'cliente' | 'socio' | null` (C y B se cruzaban); la prueba de suscripción espera envío de $129 porque C añadió `shipping.baseRateMxn`; el tope de error del bundle inicial subió de 2 a 3 MB (2.19 MB por ocho pantallas *eager* en el monolito). 365 pruebas en verde.
- **Ola B** (`b4bffe4`, `9905159`): sin conflictos, I1 e I2 no compartieron archivos. 371 pruebas. Humo por API con el reloj en 2027-01-12: ninguna respuesta 500; las tareas programadas respondieron 200.

## 3. Lo que encontraron las revisoras y qué se corrigió

Dos revisiones sobre `9905159`: una de código (backend, con pruebas de reproducción) y una en el navegador (Sofía, Beto, Nadia y una clienta nueva en el harness). 22 hallazgos; las correcciones están en `89b2b50` (backend) y `72fedc3` (frontend), con 14 pruebas de regresión nuevas (385 en verde).

| # | Gravedad | Dónde | Qué pasaba | Corrección | Estado |
|---|---|---|---|---|---|
| 1 | Grave | `order_lambda.py` | Un webhook aprobado (o la conciliación) sobre un pedido **cancelado** lo pasaba a `paid`, disparaba `ORDER_PAID` (VP, activación, comisiones) y mandaba "Recibimos tu pago" después de "Pedido cancelado" | `cancelled`/`canceled` son terminales: el webhook responde idempotente, anota `approved_after_cancel` con reembolso pendiente y la gerente lo ve en Acciones urgentes | Corregido |
| 2 | Media | `commissions_lambda.py` | `asegurar_socio` por beneficiario (B) hacía 2 GetItem por generación: ORDER_PAID pasó de 37 a 47 GetItem y `check_query_budget.py` (gate de CI) fallaba | Se decide el modo con la ficha ya cacheada; 37 GetItem otra vez | Corregido |
| 3 | Media | `order_lambda.py`, `carriers.py` | `deliveredAt` se guardaba sin validar ("ayer por la tarde"); `_horas_desde_entrega` devolvía 0 y la ventana de devolución quedaba abierta para siempre | ISO 8601 obligatorio (400 si no); la paquetería normaliza su fecha | Corregido |
| 4 | Media | `core/ledger.py` | Con `LEDGER_ROW_SCHEME=rows` se perdían `blockedNoticeSentDays`, `clabeReminderAt` y `paidAt`, y Pagos del mes, avisos y acciones urgentes recorrían un bucket que en ese esquema no existe | La cabecera conserva las marcas del mes; índice por mes que sirve a ambos esquemas; pruebas en `test_ledger_esquemas.py` | Corregido |
| 5 | Media | `despacho_handlers.py` | "Sí, ya llegó" era un **GET con efectos**: un escáner de enlaces de correo marcaba el pedido entregado, confirmaba comisiones y abría el plazo de devolución | El GET solo muestra la página con el botón; la entrega la hace el POST del formulario; token de un solo uso | Corregido |
| 6 | Baja | `suscripciones_handlers.py` | Cualquier empleado sin privilegios podía listar, editar y cancelar la suscripción de cualquier clienta | Privilegio exigido para empleados | Corregido |
| 7 | Baja | `pagos_handlers.py` | CSV de dispersión con el nombre de la socia sin neutralizar (`=HYPERLINK(...)` se evalúa en Excel) | Celdas que empiezan por `=`, `+`, `-`, `@` neutralizadas | Corregido |
| 8 | Baja | `pagos_handlers.py` | El lote subía el comprobante a S3 antes de validar las filas (doble clic = asset huérfano y 409) | Valida primero, sube solo si hay al menos una fila pagable | Corregido (sin `idempotencyKey`) |
| 9 | Baja | `seguimiento_handlers.py` | `_pedidos_de_invitados` recorría todo el bucket ORDER sin fecha y `_fila_cliente` lanzaba una Query por ficha | Acotado con `sk_from` (coldDays × 2 en "hoy", 365 días en ficha/contacto) | Parcial: la Query por ficha se mantiene (Limit 8) |
| 10 | Media | `devoluciones_handlers.py` | `GET /orders/{id}/devolucion` y `GET /orders/{id}` de un pedido de invitado sin sesión exponían teléfono, dirección, descripción, fotos de evidencia e inspección a quien conociera el folio | Teléfono, correo y calle enmascarados; la devolución no expone descripción, evidencia ni inspección | Parcial: sin token de seguimiento (implica cambiar correos y `/#/orden/{id}`) |
| 11 | Baja | `order_lambda.py` | Con `webhookSecret` vacío (valor por omisión) el webhook acreditaba pedidos con un WARN | Con la pasarela encendida y sin secreto responde 401 | Corregido |
| 12 | Grave | `admin.component.ts` (POS) | La tabla única salía **sin tramos** y decía "Ya está en el tramo más alto"; `businessConfig` nunca se cargaba en el POS y la venta de Beatriz ($1,080) se cobraba sin el 10 % | El POS carga la configuración al entrar; sin tramos la tabla no afirma nada | Corregido |
| 13 | Media | `user-dashboard`, POS | En modo cliente la tabla decía "llevas 0 VP" con $1,320 comprados; el POS decía "$0 · 0 VP" | Panel y carrito leen `clientIndicators.monthVp`/`monthSpend` | Parcial: el POS lee la misma fuente que el panel (`ASSOCIATE_MONTH`); la diferencia del harness venía del reloj del navegador (2026-09) contra el del servidor (2027-01) |
| 14 | Media | `landing.component.html` | "Te registras como cliente" solo salía en la landing con código; en `/#/landing` el registro seguía junto a "Comisiones de Red · Gen 1 10 %" | El párrafo vive en `#formBlock` y sale en ambas ramas | Corregido |
| 15 | Media | `carrito.component.html` | En modo socio convivían "Nivel de descuento: Nivel 1 · Con esta compra subes a Nivel 1" y la tabla única con "Tramo actual: 10 %" | El bloque viejo se retira cuando se monta la tabla | Parcial: la meta "Alcanzar nivel 2 de descuento" viene de `goals` del backend y no se renombró |
| 16 | Media | `despacho.component.ts` | Cargar guías por CSV borraba el surtido calculado y "Despachar" volvía a "Primero pulsa Calcular surtido" | Solo se anula si la selección cambió | Corregido |
| 17 | Media | `user-dashboard.component.html` | En modo cliente seguían el Cuadro de Honor por Red (VG) y VP y el modal "¡Estás en el Cuadro de Honor! Red (VG): #2" | Ocultos con `isClientMode` | Corregido |
| 18 | Baja | `despacho.component.html` | Texto técnico para Beto: "activa `shipping.carrierIntegration.enabled`", "Enciende `trackingEnabled`" | Español de almacén y motivo por `disabledReason` | Corregido |
| 19 | Baja | `despacho_handlers.py` | "Producto 1788339615574" cuando la línea del pedido no trae nombre | Nombre desde el catálogo (mismo mapa que el resumen de turno) | Corregido |
| 20 | Baja | `pagos-mes.component.ts` | "Ir a resolver" del aviso de socias sin CLABE aterrizaba en el mes del navegador (agosto 2026) y no en el del aviso (diciembre 2026) | El aviso trae `monthKey`, `app-pagos-mes` lo recibe por `[month]` y lo añade al selector | Corregido |
| 21 | Baja | `admin-seguimiento.component.ts` | Un byte NUL literal dentro de una cadena: git trataba el archivo como binario (sin diff ni revisión) | Lógica explícita; el archivo vuelve a ser texto (los diffs son legibles desde `72fedc3`) | Corregido |
| 22 | Baja | `checkout_handlers.py`, carrito | Sin `city` en el almacén se usaba `location`: "Disponible en: Av. Coyoacán 1200…" y "no está disponible en tu zona" aun capturando CDMX | Sin ciudad se nombra la sucursal, no su dirección | Corregido |

## 4. Validación con personas (12 de enero de 2027)

Cinco personas, un navegador cada una, sin instrucciones de uso y con el reloj de la simulación en 2027-01-13 10:00 (a todas se les dijo "12 de enero", de ahí el "sistema un día adelantado" que las cuatro empleadas y socias anotan: no es defecto de la aplicación). Diarios en `sim/diarios/*-ene12.md`; capturas en `sim/capturas/` (fuera de git por `sim/.gitignore`).

### 4.1 Diana Robles, clienta nueva desde un anuncio (`diana-ene12.md`, móvil, 22:05 a 23:40 y 13-ene 10:00)

Diseñadora en Puebla, quería un solo bote de colágeno, no conoce a nadie de la empresa y no quiere vender. Es la persona para la que se hizo la propuesta 1.

- **Logró**: encontrar el Colágeno ($700) y agregarlo; leer en el carrito "Como socia, con $300 más de compra este mes tendrías 10 % de descuento · Conoce el modo socio" y seguir el enlace a `/#/modo-socio`; entender en menos de cinco minutos cuánto ahorraría (nada con $700), qué le piden (nada al activar; CLABE solo con comisiones) y **decidir no activarse**; registrarse, confirmar el correo, capturar la dirección, pagar $829 ($700 + $129 Estafeta) y ver `ORD-73A2FDB9` en "Pago registrado" con el correo "Recibimos tu pago"; ver en el panel "Este mes has comprado $700 · Como socia habrías ahorrado este mes $0"; volver al día siguiente con la sesión guardada.
- **Falló** (13 reportes): un recuadro negro con `TS2540 … pagos-mes.component.ts:91` encima del aviso de privacidad (overlay de `ng serve` mientras se editaba ese archivo; no reproducible con `tsc` en verde); la tienda prometía "descuento en la primera compra" y no existe (se quitó la promesa en `acca507`); "Corte en 27d 3h" en el carrito contra "22d 3h 45m" en el panel y congelado al día siguiente (el carrito usaba fin de mes y el panel `cutoffDay`, unificado; el congelamiento es el reloj real del navegador); "Te faltan $0 para Meta de beneficios" (no se muestra sin meta); acentos rotos "porci?n"; errores en rojo antes de escribir; "Seguir como cliente" no regresaba al carrito; la tarjeta de estados se salía del móvil; el cuadro de cuenta tapaba el menú; "Cancelar orden" sin decir qué pasa con el dinero; entrega "24–72h" contra "3 a 5 días hábiles"; dobles espacios en el correo. Todo lo anterior corregido en `b0712e6`/`acca507` salvo la ficha de producto vacía (datos del catálogo) y el paso "Pago" sin palomita (no reproducible: con `status=paid` el timeline marca dos pasos).
- **Confusiones**: qué es "PC" bajo cada precio, qué es "corte", "Nivel de descuento: Inactivo" ("suena a que hice algo mal"), y una meta que nadie le pidió.
- **Frases**: "mi primera impresión fue 'esto está a medio hacer'" · "Con mi bote de $700 ahorraría cero. Para ahorrar $100 tendría que gastar $300 más; eso no es ahorrar, es gastar $200 más." · "Lo entendí (cero ahorro para mí, nada que dar hoy), la explicación es honesta, y justo por eso no lo activé" · "Yo no me puse ninguna meta; me la pusieron." · "'Este mes has comprado $700 · Como socia habrías ahorrado este mes $0'. Correcto y honesto." · "doce horas después sigue en 22 días y 3 horas. Ese reloj no cuenta nada real."

Lectura: la propuesta 1 hizo lo que prometía (Diana compró como cliente, entendió el plan y eligió no entrar sin sentirse engañada); lo que la molestó fueron promesas viejas de la tienda y ruido del panel que no era de esta ronda.

### 4.2 Sofía Herrera, gerente de operaciones (`sofia-ene12.md`, 10:05 a 12:30)

Tres encargos de Ricardo: liquidar diciembre, mandarle a Ivonne la lista de a quién escribir, y revisar pagos de MercadoPago no acreditados.

- **Logró**: verificar en "Pagos del mes" que Verónica ($368.40) está pagada el 10-ene con comprobante; enviar "Pedir CLABE" (correo + aviso dirigido + bitácora) a Beatriz y a Claudia; generar "Seguimiento de hoy" (11 personas: 2 CLABE pendiente, 9 frías, 1 oculta por "no contactar") y pasársela a Ivonne con motivo por persona; correr "Conciliar pagos" (Revisados 0 · Acreditados 0 · Sin pago 0, no había pendientes de 72 h); detectar y anotar el pedido `ORD-66407B13` pagado por $800 a nombre de "Cliente" con producto "Producto" y sin dirección.
- **Falló** (10 reportes): **no había dónde capturar la CLABE** que las socias le mandaron por WhatsApp, aunque el texto de la ficha decía "Pídesela y guárdala en su ficha" (corregido en `acca507`: campo de CLABE en la ficha del cliente); el pedido fantasma (lo creó el orquestador por API sin nombres; `b0712e6` hace que los pedidos por API tomen el nombre de la ficha y del catálogo); "Pedido tardío 0" contra "4 pedidos pagados sin envío" (corregido: el pedido tardío pesa más que la CLABE pendiente); "Última revisión: 13 Jan" en inglés (locale `es-MX`); cuenta "Prueba Reenvio" y teléfono repetido de Guillermo y Claudia (datos); columna Ejecutiva siempre "—" (la asignación existe en Seguimiento → Ficha; nadie tenía ejecutiva); avisos "Registra tu CLABE" en Notificaciones sin saber quién los ve (ahora la lista dice "Solo la ve …"); botón "Perfil" sin acción (retirado); buscador de Pedidos por folio (no reproducible: el filtro compara el id en minúsculas).
- **Frases**: "'Guárdala en su ficha'… ¿dónde?" · "Esto es justo lo que Ricardo quería: pagar por lote sin abrir ficha por ficha. Me gustó. El problema vino después." · "Me da pena con ellas: es pedirles dos veces lo mismo." · "Una pantalla dice cero y la otra cuatro." · "La pantalla nueva de pagos por lote está muy bien pensada para el día 10, pero se quedó sin la mitad del flujo."

### 4.3 Beto Salinas, almacén de Bodega Central (`beto-ene12.md`, 10:16 a 12:05; cierre en `beto-reporte-ene12.txt`)

- **Logró**: despachar en bloque desde Bodega Central el lote `DSP-9F7663254C` (Claudia `ORD-B17FBDD2` $1,458 → `EST-MX-88120091`, Diana `ORD-73A2FDB9` $829 → `EST-MX-88120092`, Nadia Prueba `ORD-FA8E7601` $1,320 → `EST-MX-88120093`), con surtido "Todo alcanza" (Biotina 1/32, Colágeno 2/19, Finding Pro 1/33, Magnesio 2/30) y existencias descontadas una sola vez; fijar Bodega Central como su bodega por defecto; dejar `ORD-66407B13` sin despachar con nota; mandar a Sofía el cierre de turno con guías, existencias y pendientes.
- **Falló** (9 reportes): la pantalla proponía **Tienda Del Valle** con "Aún no tienes bodega por defecto" (corregido: sin bodega guardada no se propone ninguna); "Volver a Pedidos" mostraba Pagados 4 / Enviados 0 hasta recargar (corregido: se recargan los pedidos tras despachar); **las notas internas de Sofía no se veían al abrir el pedido**, solo tras guardar otra (corregido: la lista de pedidos lleva `adminNotes` y `byName`); con sesión guardada caía en la tienda de socios con "Rol admin" y sin camino al panel (corregido: el empleado va a `/admin`); al marcar un pedido se borraba "Estafeta" (corregido); bitácora con "Empleado 1788339615539" en vez de su nombre (corregido: `userName` en movimientos); "porci?n" (corregido); el pedido fantasma y la fecha (datos y reloj).
- **Frases**: "Por un momento pensé que el despacho no se había guardado y que iba a tener que repetirlo (y si lo repito, ¿descuenta doble?)." · "si no me fijo, vacío el inventario equivocado" · "Las notas existen, pero no se ven al abrir el pedido; solo aparecen después de guardar una nueva." · "en diciembre despachaba pedido por pedido con 'Registrar envío' y sin saber si había existencia; hoy en una sola pantalla vi qué necesito, si alcanza y despaché tres de un jalón con confirmación" · "Soy yo, pero nadie que lea la bitácora lo sabe."

### 4.4 Nadia Ruiz, cajera de Tienda Del Valle (`nadia-ene12.md`, 10:31 a 11:30)

- **Logró**: venta de mostrador `POS-C7ACD530` (Boom $420 + Naplus $280 = $700, recibió $1,000, "Cambio a entregar: $300" leído del servidor); corte `CUT-5DB5A173` con el asistente de cuatro pasos (esperado $1,200, contado $1,250, "Diferencia $50.00 (sobra)" con motivo obligatorio, todo como fondo de mañana); leer el motivo de cada botón deshabilitado ("Elige al menos un producto", "Escribe cuánto efectivo contaste (puede ser $0)", "Escribe quién recibe el efectivo retirado", "No hay ventas ni retiros desde el último corte"); ver la tabla de descuento del POS con Roberto Chávez (0/10/20/30/40 % por tramo, activación 20 VP).
- **Falló** (12 reportes): las ventas con tarjeta de noviembre nunca entraban a ningún corte y "Ventas en caja" contaba 4 y luego 2 (corregido en `b0712e6`: las ventas sin corte anteriores al último entran al siguiente); "2 ventas por $1,040" en el paso 4 contra "Total: $700" en el historial (el historial mostraba el efectivo generado; reetiquetado "Efectivo del turno"); "Retirar una parte" proponía retirar todo, fondo incluido (corregido: propone dejar el fondo con el que abrió); "1 ventas POS registradas hoy — Ir a resolver" y avisos de CLABE ajenos a su rol (plural corregido; Acciones urgentes solo lista lo que la persona puede abrir); "Resolvé" (corregido); la caída en la tienda de socios (corregida). Sin cambio: qué hacer físicamente con los $50 sobrantes (política de tienda), el correo del corte sin configurar (Configuración), la caja que no pide abrir turno (diseño actual: el turno va de corte a corte), y las cuentas de prueba en la lista de clientes (datos).
- **Frases**: "Yo soy cajera, no tengo red ni metas." · "esta vez casi cada botón gris me dijo qué le faltaba y el corte me llevó de la mano (contar, motivo, destino, revisar)" · "Lo del 'No es una falta: es lo que pasó' me quitó el nervio de escribir que sobraban $50." · "de los $50 extra no me dice nada (quedaron dentro del fondo de mañana como si fueran de la empresa)" · "el paso 4 dijo '2 ventas por $1,040' y el historial dice 'Total $700': ¿cuál es el total del corte?" · "me da cosa que un cliente vea, si se asoma, 'Nadia Prueba' y 'Prueba Reenvio' en la lista"

### 4.5 Claudia Ibarra Soto, socia con comisión pendiente (`claudia-ene12.md`, 10:47 a 12:10)

- **Logró**: confirmar que diciembre sigue "Pendiente de pago" ($195.20 por la compra de Memo, confirmada el 20-dic); **capturar su CLABE** en Comisiones (`**** 9719`); guardar la suscripción `SUS-7F3F1BD1` (Colágeno + Biotina + Magnesio, $1,620 de lista, día 5, primer pedido 5 de febrero) y recibir "Tu suscripción mensual quedó guardada"; entender en `/#/modo-socio` que gana 10 % de Memo y que el 5 % de la gente de Memo exige dos directas activas; ver que su pedido del 20 de diciembre por fin salió (`EST-MX-88120091`, correo "Tu paquete ya salió").
- **Falló** (10 reportes): la suscripción la mandaba a guardar una dirección en el perfil, y el perfil no tiene direcciones (el texto ahora manda a guardarla al pagar; terminó eligiendo "Recoger en Tienda Del Valle" viviendo en Puebla); el aviso "Registra tu CLABE" seguía vigente después de capturarla (corregido: registrar la CLABE apaga los avisos `NTF-CLABE`); guardar la CLABE no daba confirmación (el toast ya se pinta) ni cambiaba "Pendiente de pago" (lo cambia el registro del depósito por administración); "¡Estás en el Cuadro de Honor! #10" con 0 VG/0 VP y "Bajaste en el ranking" (corregido: quien lleva 0 y 0 no entra al top 10); el panel no enlazaba la explicación de porcentajes (enlace añadido en Comisiones); "Av. Reforma 123, Monterrey" prellenado en el carrito (datos de su ficha de registro); voseo en el perfil (corregido); "Beneficios" (hace scroll, no reproducible). Sin cambio: VP de la suscripción y aviso de que enero queda sin activar (producto); lo que `/#/modo-socio` dice de "confirmada al entregar", avisos del 20 y 27 y pago el día 10 depende del calendario y de las tareas programadas de la simulación.
- **Frases**: "Ah, entonces la CLABE que le mandé a Sofía por WhatsApp no sirvió de nada: la tengo que capturar yo." · "Pues ya es 12 y sigue 'Pendiente de pago'." · "¿Cómo que no tengo direcciones guardadas? Ya me han mandado dos pedidos a mi casa." · "Me mandó a un lugar donde no existe lo que me pidió. Me quedé dando vueltas." · "Con una sola persona directa, lo que compre la gente de Memo no me deja NADA." · "estoy 'en el cuadro de honor' con cero, y además 'bajé'. Es 12 de enero, obvio que traigo cero." · "enero se me va otra vez. Mi VP de enero va en 0, la suscripción arranca hasta el 5 de febrero, y nadie me lo avisó al guardarla."

### 4.6 Lo que se repite entre los cinco

- Cuatro de cinco anotaron la **fecha "13 de enero"**: es el reloj de la simulación (`/__sim/reloj`), no la aplicación. Lo único real ahí era "13 Jan" en inglés, corregido.
- Tres empleados con sesión guardada **cayeron en la tienda de socios** sin camino al panel: corregido en `acca507`.
- Tres personas vieron **"porci?n" / "absorci?n"**: corregido.
- Sofía y Beto chocaron con el **pedido fantasma** `ORD-66407B13`: dato creado por API durante la revisión; los pedidos por API ya toman nombres de ficha y catálogo.
- Las **cuentas de prueba** ("Nadia Prueba", "Prueba Reenvio") las vieron Sofía, Nadia y Beto: datos de la simulación.

## 5. Bugs corregidos en la ronda

Además de los 18 hallazgos de las revisoras cerrados en §3, estos salieron de los diarios del 12-ene y se corrigieron en `b0712e6` (backend, 7 pruebas en `tests/test_correcciones_ene12.py`) y `acca507` (frontend). 392 pruebas en verde.

| # | Gravedad | Dónde | Qué pasaba | Corrección | Quién lo vio |
|---|---|---|---|---|---|
| 1 | Alta | Clientes | La ficha decía "Pídesela y guárdala en su ficha" y no había campo de CLABE | Campo para capturar la CLABE de la socia desde la ficha | Sofía |
| 2 | Alta | Pedidos | Las notas internas no se veían al abrir el pedido, solo tras guardar otra | La lista de pedidos lleva `adminNotes`; cada nota guarda `byName` | Beto |
| 3 | Alta | Despacho | Sin bodega por defecto se proponía la primera del catálogo (la de otra sucursal) | Sin bodega guardada no se propone ninguna | Beto |
| 4 | Alta | Despacho | "Volver a Pedidos" mostraba contadores viejos (Pagados 4 / Enviados 0) | Se recargan los pedidos del back office tras despachar | Beto |
| 5 | Alta | Tienda | Prometía "descuento en la primera compra" que no existe en el backend | Se retira la promesa (no se implementó un descuento nuevo) | Diana |
| 6 | Media | Panel del socio | El aviso "Registra tu CLABE" seguía vigente tras capturarla | Registrar la CLABE desactiva los `NTF-CLABE` de esa socia | Claudia |
| 7 | Media | Cuadro de Honor | Siete socias con 0 VP y 0 VG salían en el top 10 y recibían "Bajaste en el ranking" | Quien lleva 0 y 0 no entra al top 10 | Claudia, Diana |
| 8 | Media | Pedidos por API | Un pedido creado sin `customerName` quedaba como "Cliente" / "Producto x1" | Nombre desde la ficha y del catálogo | Sofía, Beto |
| 9 | Media | POS | Las ventas con tarjeta de noviembre nunca entraban a un corte; "Ventas en caja" contaba 4 y luego 2 | Las ventas sin corte anteriores al último entran al siguiente | Nadia |
| 10 | Media | Seguimiento | "Pedido tardío 0" con cuatro pedidos pagados sin envío | El pedido tardío pesa más que la CLABE pendiente al clasificar | Sofía |
| 11 | Media | Stocks, Pedidos | Bitácora y notas con "Empleado 1788339615539" | `userName` en movimientos; nombre de la sesión en notas | Beto |
| 12 | Media | Panel, Pedidos | Empleado con sesión guardada caía en la tienda de socios (y un 404 en `/customers/dashboard`) | El empleado va a `/admin` | Beto, Nadia |
| 13 | Media | Back office | "Última revisión: 13 Jan" en inglés | Locale `es-MX` registrado | Sofía |
| 14 | Media | Acciones urgentes | La cajera veía CLABEs y comisiones ajenas a su rol; "1 ventas"; "Resolvé" | Solo lo que la persona puede abrir; plural; "Resuelve" | Nadia |
| 15 | Media | POS | "Total: $700" en el historial contra "2 ventas por $1,040" en el corte | Reetiquetado "Efectivo del turno" (expectedCash − fondo) | Nadia |
| 16 | Media | Corte de caja | "Retirar una parte" proponía retirar todo, fondo incluido | Propone dejar el fondo con el que abrió la caja | Nadia |
| 17 | Media | Carrito, panel | "Corte en 27d 3h" (fin de mes) contra "22d 3h" (`cutoffDay`) | Ambos usan la misma fecha de corte | Diana |
| 18 | Media | Carrito | Entrega "24–72h" contra "3 a 5 días hábiles" de la paquetería | "3 a 5 días hábiles" | Diana |
| 19 | Baja | Despacho | Al marcar un pedido se borraba la paquetería que traía | Se conserva | Beto |
| 20 | Baja | Notificaciones | No se sabía quién ve un aviso dirigido | "Solo la ve …" en la lista del admin | Sofía |
| 21 | Baja | Clientes | Botón "Perfil" sin acción | Retirado | Sofía |
| 22 | Baja | Panel del socio | El cuadro de cuenta no cerraba con Escape y tapaba el menú móvil; la ayuda de estados se salía del móvil | Escape cierra ambos; el menú queda encima; la ayuda cabe | Diana |
| 23 | Baja | Panel del socio | El toast de CLABE guardada no se pintaba | Se pinta | Claudia |
| 24 | Baja | Panel, Comisiones | Nada enlazaba la explicación de porcentajes y requisitos | Enlace "cómo se calculan" a `/#/modo-socio` | Claudia |
| 25 | Baja | Tienda, panel | "10g por porci?n", "Alta absorci?n" | Etiquetas sin acentos rotos | Diana, Beto, Nadia, Claudia |
| 26 | Baja | Carrito | Errores en rojo antes de escribir; "Te faltan $0" sin meta | Sin validación previa; no se muestra sin meta | Diana, Nadia |
| 27 | Baja | Modo socio | "Seguir como cliente" iba a la portada, no al carrito | Regresa al carrito cuando se llegó desde ahí | Diana |
| 28 | Baja | Orden | "Cancelar orden" tras pagar sin decir qué pasa con el dinero | Aviso de reembolso junto al botón | Diana |
| 29 | Baja | Suscripción | "Guarda una dirección en tu perfil" y el perfil no tiene direcciones | El texto manda a guardarla al pagar | Claudia |
| 30 | Baja | Correos | Dobles espacios y enlace pegado en el texto plano | Texto plano limpio | Diana |
| 31 | Baja | Perfil | "Acá podés ver…" (voseo) | Español neutro | Claudia |

**No eran defectos** (o no se reprodujeron): el `TS2540` de Diana (overlay de `ng serve` en edición; `tsc` en verde y `push` sobre un arreglo `readonly` es válido); la fecha "13 de enero" (reloj de la simulación); el contador "Corte de mes" congelado (el navegador usa la fecha real, 2026-09-03); el paso "Pago" sin palomita; la ficha de producto vacía y las etiquetas `colageno`/`colágeno` (catálogo); "Prueba Reenvio", "Nadia Prueba" y el teléfono compartido de Guillermo y Claudia (datos); la columna Ejecutiva vacía (nadie asignado); el buscador de Pedidos por folio; "Beneficios" y el botón "3" del encabezado (hacen scroll a secciones que existen); "Mostrar desde 2026-09-03" (fecha real del navegador).

## 6. Pendiente y siguientes pasos

**Decisiones de producto que los diarios dejaron sobre la mesa**

1. Qué hacer con el **sobrante del corte** (Nadia: "de los $50 extra no me dice nada"): hoy queda dentro del fondo con motivo; falta una regla (separar, entregar a la gerente, registrar como ingreso).
2. **Apertura de caja**: el turno va de corte a corte y Nadia llegó a una caja "abierta" desde el 13 de diciembre; pedir abrir turno y confirmar el fondo es una definición de producto.
3. **Suscripción**: mostrar los VP que da cada mes y avisar al guardarla que el mes en curso queda sin activar (Claudia); permitir capturar una dirección desde el perfil o desde la propia suscripción sin pasar por una compra.
4. **Descuento de primera compra**: se quitó la promesa; si el negocio lo quiere, hay que implementarlo (cupón de bienvenida).
5. **PC bajo cada precio y metas asignadas** a quien compra un bote: Diana no entendió "13 PC · $53.85/PC" ni por qué tenía un "Objetivo principal del mes". En modo cliente conviene ocultar PC y metas.
6. **Teléfonos duplicados** entre fichas (Guillermo y Claudia): aviso al capturar.
7. `POST /commissions/request` **ignora el campo `clabe`** del modal de solicitud de pago del panel (solo se guarda con `saveCustomerClabe`); es de A/B y no se tocó.
8. La meta **"Alcanzar nivel 2 de descuento"** de `goals` conserva el vocabulario viejo junto a la tabla única ("Siguiente tramo").

**Deuda técnica de la ronda**

9. **Bundle inicial de 2.25 MB**: `angular.json` subió el tope de error a 3 MB; hay que cargar `admin.component` de forma perezosa o dividirlo por regiones (§0.6 ya da el mapa).
10. **Tareas programadas en AWS**: `POST /commissions/avisos/bloqueadas`, `POST /inventory/envios/rastrear`, `POST /inventory/envios/cerrar`, `POST /orders/suscripciones/generar` y `POST /orders/conciliacion` corren con el reloj del harness; el cableado EventBridge → API Gateway está documentado en `openapi-aws.yaml` y no desplegado. Sin él, la política 22 y la suscripción no ocurren solas en producción.
11. **Paquetería**: `ENVIA_GENERATE_URL`/`ENVIA_TRACK_URL` y el formato de respuesta sin validar contra la API real; `API_BASE_URL` debe definirse en el despliegue para que el botón del correo "¿te llegó?" apunte al API; verificar que API Gateway resuelva los paths explícitos nuevos de D al lambda de `/inventory/{proxy+}`.
12. **Pedido de invitado sin sesión**: se enmascaró PII y se quitó la evidencia de la devolución pública, pero la autorización sigue basada en conocer el folio; un token de seguimiento en correos y en `/#/orden/{id}` es el cierre real (hallazgo 10).
13. **Webhook de MercadoPago**: verificación de `x-signature` (hoy el secreto va en la query).
14. **Seguimiento de hoy**: una Query de historial por ficha (Limit 8); acotar a la cartera filtrada y cachear por invocación cuando crezca.
15. **`sim/cobertura.py`** solo lee `real-api.service.ts`; las rutas de los servicios por paquete salen como "no declaradas". Hay que enseñarle a leer `services/*.service.ts`.
16. Un `POST /inventory/pos/cash-cuts//enviar` (id vacío) aparece en `servidor.log`: el frontend llamó a enviar el comprobante por correo con un `cashCutId` vacío; falta deshabilitar ese botón con motivo mientras no haya corte cargado.
17. Los dos campos de la ficha unificada (preferencia de contacto, ejecutiva) viven solo en Seguimiento; si se quieren en la ficha de Clientes hay que añadir dos `ui-form-field` y mapearlos en `normalizeAdminCustomer`.
18. **Datos del harness**: capturar ciudad/estado en los almacenes existentes, borrar o marcar las cuentas de prueba, asignar ejecutiva a las carteras, configurar `pos.cashCutNotifyEmail` y `webhookSecret`.

**Siguiente ronda de validación**: Ivonne con "Seguimiento de hoy" y las plantillas de WhatsApp; el día 20 y 27 de enero con el aviso de bloqueadas y el producto que salva; el 5 de febrero con la generación del pedido de suscripción de Claudia; el 10 de febrero con el pago por lote (ahora que Claudia tiene CLABE); una devolución parcial por líneas con evidencia; un pago de MercadoPago sin webhook conciliado a las 72 h; un empleado con la paquetería encendida (`carrierIntegration.enabled`) rastreando y cerrando envíos.

## 7. Cómo verificarlo

**Código y pruebas**

```bash
git log --oneline 99879bc..HEAD                       # 41 commits: afc604a (diseño) … acca507 (correcciones del 12-ene)
git diff --shortstat 99879bc..HEAD                    # 145 archivos, +24,051 / −1,382
cd Micro-lambda-GMF/python && python3 -m pytest -q tests   # 392 passed
python3 tools/check_query_budget.py                   # ORDER_PAID 37 GetItem (tope 40): "Presupuesto de consultas respetado"
grep -rn "prompt(\|confirm(\|alert(" ../../gamificacion-multinivel-f/src/app/pages/admin | wc -l   # 0
cd ../../gamificacion-multinivel-f && npx tsc -p tsconfig.app.json --noEmit && npx ng build   # sin errores; aviso de presupuesto del bundle
```

**Harness** (`sim/servidor.py` en 4400 con `environment.ts` apuntando a `http://localhost:4400`; `ng serve` en 4321; reloj en 2027-01-13):

```bash
python3 sim/cobertura.py | head -1                    # 79 rutas declaradas · 73 alcanzadas · 6 nunca tocadas
curl -s localhost:4400/__sim/reloj
curl -s -X POST localhost:4400/__sim/tareas           # ejecuta las cinco tareas programadas con el reloj
H='-H x-user-role:admin -H x-user-privileges:{}' ; T='Authorization: Bearer sim-superadmin-token'
curl -s -H "$T" 'localhost:4400/commissions/pagos?month=2026-12'                # filas listo / sin_clabe / pagado
curl -s -H "$T" 'localhost:4400/commissions/pagos/dispersion.csv?month=2026-12' # CSV del banco
curl -s -H "$T" -X POST localhost:4400/commissions/avisos/bloqueadas -d '{"dryRun":true,"force":true}'
curl -s localhost:4400/catalog/plan                                              # plan público con los números de config
curl -s -H "$T" localhost:4400/inventory/despacho/pendientes
curl -s -H "$T" localhost:4400/inventory/pos/arqueo
curl -s -H "$T" 'localhost:4400/customers/seguimiento/hoy?scope=all'
curl -s -H "$T" localhost:4400/inventory/turno/resumen
curl -s -H "$T" -X POST localhost:4400/orders/conciliacion -d '{"dryRun":true}'
```

Rutas nuevas alcanzadas por las personas según `servidor.log` (el script las lista como "no declaradas", §6.15): `/catalog/plan`, `/customers/modo`, `/customers/modo-socio`, `/orders/checkout/envio-info`, `/orders/checkout/sucursales-recoger`, `/orders/checkout/sugerencia-activacion`, `/commissions/pagos`, `/commissions/pagos/pedir-clabe`, `/inventory/despacho/{pendientes,surtido,enviar,preferencias}`, `/inventory/pos/{arqueo,cash-cut,cash-cuts,withdrawal}`, `/customers/seguimiento/hoy`, `/orders/{id}/devolucion`, `/orders/{id}/return`, `/orders/{id}/return/inspect`, `/orders/suscripciones`, `/orders/conciliacion`, `/orders/conciliacion/ultima`.

**Pantallas, por persona**

| Quién | Dónde | Qué mirar |
|---|---|---|
| Clienta nueva (registro en `/#/landing`) | `/#/tienda`, `/#/carrito`, `/#/modo-socio`, `/#/dashboard` | "Te registras como cliente" bajo el formulario; en el carrito la barra "Como socia, con $X más tendrías 10 %" y la tabla única; en el panel "Tu cuenta en modo cliente" sin red, VP, comisiones, CLABE ni Cuadro de Honor; "Activar modo socio" con confirmación del servidor |
| Socia (Claudia) | `/#/dashboard` → Comisiones, Órdenes | Tabla única en Volumen; CLABE con toast y aviso apagado; enlace "cómo se calculan"; "Recibe esto cada mes" con día, pausa y cancelación; devolución en `/#/orden/{id}/devolucion` en cuatro pasos |
| Sofía (`sofia@findingu.mx`) | Clientes → Pagos del mes; ficha → CLABE; barra de Clientes → Seguimiento de hoy; Pedidos → Conciliar pagos; Acciones urgentes | Filas listo / sin CLABE / pagado, CSV, lote con un comprobante, deshacer por fila; captura de CLABE en la ficha; "Ir a resolver" abre el mes del aviso; `ui-confirm` con efecto escrito y resultado del servidor en cancelar, deshacer pago, cupones |
| Beto (`beto@findingu.mx`) | `/#/admin/despacho`, Stocks, `/#/admin/resumen-turno` | Sin bodega por defecto no se propone ninguna; surtido con semáforo y qué bodega sí tiene; guías a mano / CSV; "Despachar" con motivo cuando está deshabilitado; al volver, Pedidos ya recargado; notas internas visibles con nombre; bitácora con nombre |
| Nadia (`nadia@findingu.mx`) | Punto de Venta → Hacer corte, Retirar | Pago mixto; motivo bajo cada botón gris; corte en cuatro pasos con denominaciones, diferencia con motivo y "Efectivo del turno"; "Retirar una parte" con el fondo propuesto; tabla única al elegir un socio; ventas viejas sin corte incluidas |
| Correos (`sim/buzon/`, un JSON por destinatario) | — | "Registra tu CLABE", "Recibimos tu pago" con el ahorro como socia, "Tu paquete ya salió", "¿Te llegó tu pedido?" con botón que hace POST, "Tu suscripción mensual quedó guardada", "Comisión bloqueada: te faltan $X" los días 20 y 27 |
