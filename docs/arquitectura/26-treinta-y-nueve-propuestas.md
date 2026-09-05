# 26 · Arquitectura de la ronda 7: las 39 propuestas repartidas en siete paquetes

**Fecha:** 4 de septiembre de 2026. **Rama:** `claude/ultimos-cambios-integrados-fylhiw` (árbol principal, sin worktree).
**Base:** [25](../qa/25-ronda-experiencia-medida.md) §2–§7 (las 39 propuestas y su evidencia medida), el dictamen de las tres validadoras (lectura sobre esta misma rama, con el backend de simulación vivo en `:4400` y el reloj del mundo en 2027-04-10) y el método de la ronda anterior, [23](23-propuestas.md) §0 y §13.

Este documento es el contrato de la ronda. Siete agentes trabajan **a la vez** sobre la misma base; para que no se pisen, cada archivo tiene **un solo dueño**, y los cuatro monolitos compartidos (`admin.component.{ts,html}`, `order_lambda.py`, `customer_lambda.py`, `real-api.service.ts`) se reparten **por regiones con ancla nombrada**, como en la ronda 23 §0.6.

Los ids y nombres de los paquetes son fijos:

| Paquete | Nombre | Propuestas |
|---|---|---|
| **A** | `clabe-comisiones-pagos` | 1, 2, 17, 18, 32, 34, 35 |
| **B** | `plan-simulador-iva` | 14, 23, 36, 37, 38 |
| **C** | `checkout-y-tienda` | 3, 7, 10, 13, 22, 31 |
| **D** | `devoluciones-y-ayuda` | 8, 24, 39 |
| **E** | `navegacion-y-roles` | 4, 15, 27, 33 |
| **F** | `caja-almacen-stocks` | 5, 6, 21, 28, 30 |
| **G** | `coherencia-y-datos` | 9, 11, 12, 16, 19, 20, 25, 26, 29 |

Suma: 7 + 5 + 6 + 3 + 4 + 5 + 9 = **39**.

---

## 0. Reglas de la ronda

### 0.1 Hechos del código que condicionan el diseño

Se repiten aquí los que esta ronda toca; el resto sigue en [23](23-propuestas.md) §0.1.

- **Tabla única DynamoDB** (`core/db.py`), patrón bucket + REF. Esta ronda **no crea índices secundarios** ni entidades nuevas de peso: todo lo nuevo son atributos sobre entidades existentes (§2.4) y dos buckets pequeños.
- **Configuración** en `core/config.py` (`_default_app_config`, fusionada con `CONFIG/app-v1` y cacheada con TTL). Toda clave nueva se declara ahí con su valor por omisión y su comentario; **nadie repite un valor por omisión en el punto de lectura**. Bloques de esta ronda: `taxes` (nuevo, B), `returns` (ampliado, D), `contacto` (nuevo, D), `rewards` (ampliado, A), `pos` y `stocks` (ampliados, F), `seguimiento` (ampliado, G).
- **Ruteo**: `commissions_lambda` y `catalog_lambda` usan la tabla declarativa `RUTAS` de `core/routing.py`; `order_lambda`, `inventory_lambda`, `customer_lambda`, `auth_utils`, `dashboard_lambda` y `shipping_lambda` usan cascadas de `if` con la lista `_EXTENSIONES` ya introducida en la ronda 23. Las ocho lambdas comparten `CodeUri: python/`, así que un módulo puede importar a otro.
- **Tareas programadas**: el mecanismo **ya existe y funciona** — cada módulo declara `TAREAS_PROGRAMADAS = [("POST", "/ruta")]`, `sim/servidor.py:188 ejecutar_tareas_programadas()` las recorre al mover el reloj y `POST /__sim/tareas` las dispara a mano. La propuesta 34 **no construye un programador**: declara una tarea más. EventBridge sigue documentado y sin desplegar (`template.yaml` no se toca).
- **Presupuesto de consultas**: `python3 tools/check_query_budget.py` (vive en `Micro-lambda-GMF/python/tools/`, no en la raíz) vigila `GET /user-dashboard`, `GET /customers/dashboard`, `GET /dashboard/honor-board` y `ORDER_PAID`. Hoy pasa, con **ORDER_PAID en 37 de 40 GetItem a N=800: tres de holgura**. Es el número que manda en esta ronda.
- **Suite**: `python3 -m pytest tests -q` en `Micro-lambda-GMF/python` da **392 passed** de base. Verde al empezar y verde al terminar, por paquete.
- **Frontend** Angular 21 standalone y **zoneless** (no hay `zone.js` ni en `package.json` ni en `angular.json`): cada escucha de plantilla agenda una pasada de detección, así que un `*ngFor` sobre un literal escrito en la plantilla recrea sus nodos en cada pasada (causa (d) del botón "Ver", §1.E). Ruteo por hash (`withHashLocation`, `app.config.ts`).

### 0.2 Propiedad de archivos: la regla dura

1. **Cada archivo tiene un dueño y solo uno** (§2.1). El dueño crea, edita y borra con libertad dentro de él.
2. **Los cuatro monolitos compartidos se reparten por región** (§2.2). Una región se identifica por **el nombre de la función o el ancla de plantilla**, nunca por el número de línea (las líneas se mueven con cada edit). Dos paquetes nunca comparten ancla. Si un paquete necesita tocar una región ajena, **no la toca**: pide el cambio al dueño de la región y queda escrito aquí como delegación (hay exactamente una, la de la propuesta 20 → E).
3. **Archivos de configuración diminutos y compartidos por naturaleza** (`core/config.py`, `app.routes.ts`, `openapi-aws.yaml`, `app.config.ts`, `models/privileges.model.ts`): cada paquete añade **su bloque al final**, con el comentario `// paquete X · ronda 26` o `# ── Paquete X · ronda 26 ──`. Los conflictos que eso produce son de líneas adyacentes y los resuelve el integrador. `app.config.ts` es la excepción: lo edita **solo E**, e incluye en su commit las dos líneas que B y G necesitan (§3.5).
4. **Un módulo por paquete en el backend**: la lógica nueva vive en un `*_handlers.py` (o en un módulo auxiliar puro) junto a los lambdas, nunca en `core/`. Los módulos auxiliares que otros importan (`impuestos.py`, `vocabulario.py`) son de **lectura** para el resto: quien no es su dueño importa, no edita.
5. **Un servicio por tema en el frontend**. Los métodos nuevos de `real-api.service.ts` se añaden **al final del archivo**, en un bloque con el comentario del paquete (§2.2).
6. **`gamificacion-multinivel-f/src/environments/environment.ts` no entra en ningún commit.** Durante la simulación apunta a `http://localhost:4400`; si aparece modificado, se deja como está.

### 0.3 Rutas nuevas: cómo se registran

- **Backend**: la ruta se declara en el módulo del paquete (`RUTAS` declarativa o `atender()` en cascada), se añade a `openapi-aws.yaml` bajo `paths:` en un bloque final con el comentario `# ── Paquete X · ronda 26 ──` (con `summary` y el privilegio en `description`) y se regenera **solo** la instantánea del lambda propio: `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py -k <anfitrión>`, revisando que el diff traiga únicamente las rutas del paquete. Cada ruta reutiliza el privilegio de la pantalla que la usa: **esta ronda crea un solo privilegio nuevo**, `access_screen_campaigns` (§4.14).
- **Frontend**: entrada al final del arreglo de `app.routes.ts`, en el bloque comentado del paquete. Las rutas del back office siguen el patrón único de §3.5 (ruta explícita + `data: { view }` + `adminGuard` + `adminViewGuard`). Ninguna ruta nueva se inventa un privilegio: se declara el de su pantalla.
- **Tareas programadas**: `TAREAS_PROGRAMADAS` en el módulo, reexportada por el lambda anfitrión. Idempotente por día y por sujeto, con su marca guardada.

### 0.4 Dónde viven las pruebas

- Backend: `Micro-lambda-GMF/python/tests/test_<tema>_*.py`, con el **síntoma medido en la docstring** ("Fabiola pulsó Guardar cinco veces y el navegador nunca mandó el POST"). **Todo cambio de backend va con su prueba**; la suite completa queda verde en cada paquete.
- Las pruebas que esta ronda pone en rojo a propósito y hay que actualizar **en el mismo commit** que las rompe: `test_contacto_plantillas.py:42` (conjunto exacto de plantillas, G/11), `test_plan_publico.py:39` (`pesosAprox == 1000`, B/14), `test_correos_pedido.py` (asuntos y cuerpos, C/7 y D/39), las cuatro suites de devoluciones (D/39) y `test_pagos_mes.py` (A/18 y A/35).
- Frontend: sin framework de pruebas en el repositorio. La validación obligatoria es `npx tsc -p tsconfig.app.json --noEmit` y, si se tocan plantillas, la compilación de plantillas (`ngc`). **No se ejecuta `ng build` ni `ng serve` dentro de un worktree** (memoria); el build lo hace la integración.
- Presupuesto: `python3 tools/check_query_budget.py` debe pasar. Lo vuelven a correr obligatoriamente **A** (17, 32, 34), **G** (16) y **F** (21, 28).

### 0.5 Qué NO se toca

- **El motor de comisiones y el ledger.** En concreto: `commissions_lambda._distribute_commissions`, `_commissionable_net`, `_resolve_discount_rate`, el paso 2 de `handle_apply_rewards`, los importes ya escritos y los estados del mes contable. Tres excepciones, y solo esas:
  - **A/32** reescribe `_write_row` para **conservar** `createdAt` (no cambia importes) y el orden de `core/ledger.py:273`.
  - **G/16** invoca el **paso 1** de `handle_apply_rewards` (volumen, VP, activación, reevaluación de bloqueadas) al ligar un pedido de invitado, **nunca el paso 2** (repartir comisión), guardado por `rewardsAppliedAt`.
  - **B/38** añade campos de IVA en `order_lambda._calculate_totals`. El IVA es **desglose de un total que no cambia**: ningún importe cobrado, ninguna comisión y ninguna fila del ledger se mueven un centavo.
- **La base de cálculo de la comisión.** Sigue siendo el neto pagado sin envío, que es lo que el motor hace hoy (§37, §4.3). Esta ronda **lo escribe**, no lo cambia.
- **`template.yaml`**, índices secundarios, nombres de `role` (`admin`/`employee`/`cliente`: son la llave de `_require_admin` y de una docena de comprobaciones), y el formato del CSV que se sube al portal bancario.
- **`environment.ts`** (§0.2.6).

### 0.6 Lo que el dictamen dice que "ya existe": se hace visible, no se reconstruye

Ocho piezas de las 39 propuestas ya están construidas, total o parcialmente. **Ningún paquete las vuelve a escribir**; las expone y lo dice en su commit:

| Propuesta | Ya existe | Lo único que falta |
|---|---|---|
| 2 | Los dos textos separados, en el **correo** (`pagos_handlers._correo_clabe:314-318`) | Pasarle el motivo al aviso del **portal** (`_aviso_panel_clabe`) |
| 14 | El rango honesto, calculado y pintado con canastas reales ($1,120 activa / $1,170 no) | Borrar el titular `pesosAprox` de $1,000 |
| 20 | El filtro del servidor (`GET /orders?invoiceStatus=solicitada`), la insignia en la fila y el bloque para marcar emitida | La pestaña, el contador y que el botón "Ver" funcione |
| 22 | El enlace profundo `#/tienda?p=<id>` y el `scrollIntoView` de "Ver producto" | El buscador, la ruta bonita y el botón que da el enlace |
| 23 | El enlace del correo de bienvenida y el `routerLink` a `/modo-socio` (que **sí navega**) | El ancla a la sección, el enlace desde la tarjeta y desde las metas |
| 30 | `GET /inventory/turno/resumen` devuelve el texto ya armado; la pantalla lo copia | El canal: un `POST .../enviar` calcado de `handle_enviar_corte` |
| 35 | El CSV ya salta a las socias sin CLABE y exporta al resto (`pagos_handlers.py:186`) | El anexo de pendientes y el motivo con el número |
| 39 | Plazos, responsable del envío y evidencia por motivo, aplicados y escritos en el asistente y en los correos | Que sean configurables y que se publiquen **antes** de comprar |

Y dos correcciones al informe que cambian el trabajo antes de empezarlo:

- **La CLABE (1)**: el formulario, el servicio y el backend funcionan; el backend además **verifica identidad** (403 "solo puedes actualizar tu propia CLABE"). El defecto es que "Guardar" solo abre una confirmación y el `POST` vive detrás de "Confirmar", que nadie pulsó; el modal se cierra con clic al fondo y con Escape, descartando la CLABE en silencio.
- **El envío (31)**: el backend **no necesita "CP + estado"**, necesita **solo el CP** — `POST /shipping/quote {"zipTo":"03100"}` devuelve 200 con tarifas y añadirle `state` devuelve 400. Implementar la propuesta como está redactada rompería la cotización.

---

## 1. Los siete paquetes

### 1.A · `clabe-comisiones-pagos` (1, 2, 17, 18, 32, 34, 35)

**Objetivo.** Que el dinero llegue: que la CLABE se guarde al primer intento y lo diga en el propio campo, que ninguna ventana prometa comisiones que no existen, que el mes contable lo elija el servidor, que administración vea las tres cifras del mismo dinero (confirmado, por confirmar, bloqueado) y que el día 10 salga un correo pase lo que pase.

**1 · Que "Guardar CLABE" guarde.** Se elimina el paso de confirmación en las dos pantallas: `Guardar` hace el `POST` directo (la CLABE de 18 dígitos ya está validada) y el estado se pinta **en el propio campo** — *guardando… / guardada, termina en 6789 / no se pudo guardar: <motivo>* — nunca en un aviso al fondo de la página. Los dos formularios (panel y Mi perfil) se sustituyen por un componente único `components/ui-clabe-form/` (selector `ui-clabe-form`, inputs `[customerId]`, `[clabeLast4]`, `[bankInstitution]`, `[modo]='propio'|'admin'`, output `saved`), que incluye el banco (opcional, como acepta el backend) y un enlace **"Quitar CLABE"** con confirmación en línea. Backend: `customer_lambda.handle_update_clabe` acepta cadena vacía para borrar (hoy responde 400) y conserva el apagado de avisos (`_apagar_avisos_clabe`) y el refresco del panel. La verificación de identidad **ya existe y se conserva**; la validación del panel corrige "18 digitos" → "18 dígitos".

**2 · Que el aviso diga la verdad.** `_aviso_panel_clabe(customer_id, month_key, motivo)` recibe el motivo y escribe el texto que corresponde, igual que ya hace el correo: `activacion` → *"Acabas de activarte este mes: desde hoy las compras de tu red te generan comisiones. Registra tu CLABE para cobrarlas."*; `comision` → *"Ya tienes $X en comisiones confirmadas. Para depositártelas el día 10 necesitamos tu CLABE."* El id del aviso pasa a `NTF-CLABE-<cliente>-<mes>-<motivo>` (§4.7) para que quien ya recibió el de activación reciba después el de comisión. Se corrige además la contradicción con `#/modo-socio` dejando el interruptor `clabeReminderOnActivation` encendido y **cambiando el texto del plan** (`modo_handlers.py:468`): la CLABE se pide al activarse, y el plan lo dice.

**17 · El mes lo manda el servidor.** Endpoint nuevo `GET /commissions/periodos` (§3.6 de contratos): devuelve los meses contables **con datos**, el mes por omisión y la hora del servidor. Lo consumen Pagos del mes (`pagos-mes.component.ts` `buildMonthOptions`/`previousMonthKey`), el selector de Estadísticas (`availableReportMonths`/`activeReportMonth`) y el exportador (`getPrevMonthKey`, que hoy **ignora el mes seleccionado y baja los datos de otro mes**: se le pasa el mes activo). Ninguna pantalla vuelve a construir meses con `new Date()`. El recorrido del índice de meses vive **en su propio endpoint**, nunca dentro de `/commissions/pagos` ni del dashboard.

**18 · Las tres cifras del mes.** `pagos_handlers.estado_pagos()` deja de descartar a quien tiene `totalConfirmed == 0` y devuelve por fila `confirmado`, `porConfirmar`, `bloqueado`, el pedido que frena cada importe y sus días; los totales suman las tres columnas más `reconocido = confirmado + porConfirmar + bloqueado`. **El filtro se conserva donde importa**: `handle_dispersion_csv` y `handle_pago_lote` siguen operando solo sobre `status == "listo"`, y la casilla de pago solo se pinta en esas filas.

**32 · La fecha de la comisión no se reescribe.** `_write_row` conserva el `createdAt` de la fila anterior y añade `recalculatedAt` y `recalculatedReason`; la fila muestra la fecha del pedido (`order.createdAt`, que ya viaja) y, si hubo recálculo, *"recalculada el 20 de marzo porque tu patrocinadora se activó"*. `core/ledger.py:273` ordena por la fecha del pedido y desempata por `rowId`, no por `createdAt`. La comparación de "fila nueva" que decide si se manda el aviso de comisión se hace por `rowId`, no por fecha.

**34 · El día de pago existe.** Tarea programada `POST /commissions/pagos/dia-de-pago` declarada en `TAREAS_PROGRAMADAS` (el hook del reloj ya la recorrerá). El día `rewards.payoutDay` recorre por lotes los meses contables del mes anterior y manda, **una sola vez por beneficiaria y mes** (marca `payoutNoticeSentAt` en el mes contable, respetando `doNotContact`): *"Te depositamos $135 a tu CLABE terminación 6789"* si el mes está `PAID`; *"No te pudimos depositar porque nos falta tu CLABE"* con enlace directo al formulario si está `sin_clabe`; nada si el mes no tiene nada. Se añade además el correo *"tu comisión bloqueada se desbloqueó"* cuando `_reevaluate_blocked_rows` libera filas. **Nunca se avisa un depósito sin recibo**: el correo de "te depositamos" sale del recibo existente, no de la fecha.

**35 · Ya existe: se hace visible.** El CSV ya exporta a las que sí tienen CLABE. Falta el anexo `pendientes-YYYY-MM.csv` (nombre, monto, contacto, motivo) como **segundo archivo** — nunca filas más en el layout del banco — y que el motivo del botón apagado diga el número: *"No hay socias listas para depositar este mes · 1 espera CLABE ($135.00)"*.

**Rutas nuevas**: `GET /commissions/periodos` (`commissions_register_payment`), `POST /commissions/pagos/dia-de-pago` (mismo privilegio o superadmin, programable), `GET /commissions/pagos/pendientes.csv` (`commissions_register_payment`).

**Archivos propios**: `Micro-lambda-GMF/python/pagos_handlers.py`, `commissions_lambda.py`, `tests/test_pagos_mes.py`, `tests/test_avisos_clabe.py`, `tests/test_dia_de_pago.py`, `tests/test_comision_fecha.py`, `tests/rutas/commissions_lambda.json`, `pages/admin/pagos-mes/**`, `components/ui-clabe-form/**`, `services/pagos.service.ts`, `models/pagos.model.ts`.

---

### 1.B · `plan-simulador-iva` (14, 23, 36, 37, 38)

**Objetivo.** Que el plan se pueda calcular: sin números inventados, con un simulador que use la configuración real, diciendo sobre qué base se paga la comisión y desglosando el IVA en todas las pantallas donde se explica dinero. B es el paquete que **publica contratos** para los demás (§3.1, §3.2, §3.3): su primer commit son los contratos, y sale el primer día.

**14 · Borrar el número falso.** Desaparece `activacion.pesosAprox` del contrato de `GET /catalog/plan` y del titular de la página (§4.9). En su lugar, `activacion.rango = {min, max, notaProducto}` calculado de las canastas reales que ya se computan (`$933` a `$1,605` con el catálogo sembrado), y las dos tarjetas de ejemplo que ya existen se quedan como están. `_generaciones()` deja de recibir `pesos_aprox` y recibe `compraEjemplo` = **el neto de la canasta más barata que activa**, de modo que "si compra $1,120 netos ganas $112" sea aritmética verdadera y coherente con §37. Lo mismo en `indicadores_cliente().exampleEarnings`.

**23 · Enlazar donde nace la duda.** El enlace "Cómo se calculan" recibe `fragment: 'generaciones'` (y el router activa el desplazamiento por fragmento, §3.5); se añade el enlace desde la tarjeta de producto (hoy el "13 PC" es solo un `title`) y desde el bloque de metas del panel. `#/modo-socio` gana anclas `id` en sus secciones (`unidades`, `activacion`, `descuento`, `generaciones`, `pago`, `datos`, `simulador`, `iva`). El correo de bienvenida **ya enlaza**: no se toca.

**36 · Simulador de ganancias reales.** Componente `pages/modo-socio/simulador/` (selector `plan-simulador`, §3.3) y endpoint público `POST /catalog/plan/simular`. La persona mete **cuántos directos tiene, cuánto compra cada uno y cuánto compra ella**; la respuesta sale entera de la configuración (mismos `discountTiers`, `commissionLevels` y requisitos que el motor) y trae: su tramo de descuento, sus VP y si activa, la comisión por generación con el requisito cumplido o no y **por qué**, el gasto propio —**lo que de verdad paga**, ya con su descuento de socia, no el precio de lista— y la **ganancia neta** (`comisiones − gasto propio`), con la frase honesta calculada: *"Con 2 directas que compran $1,000 ganas $200 al mes, y tú pagaste $1,008 para activarte: tu resultado del mes es −$808."* Sin promesas: el texto fijo *"Esto es una calculadora con las reglas del plan, no una promesa de ingresos"* y sin extrapolar rangos.

**37 · Decir sobre qué base se paga.** Una sola frase, escrita una vez (§3.2) y usada en cinco sitios: la página del plan, el simulador, **la fila de cada comisión del panel de la socia**, el correo de comisión y la pantalla de pagos del back office. Formato de fila: *"10 % de $1,350.00 netos, sin envío = $135.00"*. B publica el texto y la función que lo arma (`impuestos.texto_base_comision` y su gemela en el frontend); **A y G lo colocan en sus regiones**.

**38 · IVA 16 %, configurable y desglosado.** Bloque de configuración `taxes` nuevo, helper `impuestos.py` y componente `ui-desglose-iva` (§3.1). B implementa el contrato, los campos del pedido (`vatRate`, `taxBase`, `taxAmount` en `_calculate_totals`) y el desglose en la página del plan y en el simulador; **cada dueño de pantalla lo monta en la suya**: C en carrito, recibo y correo de pago; E en el detalle del pedido del back office; F en el POS y en el corte de caja; G en el bloque de facturación. Los precios de lista siguen siendo con IVA incluido: **el IVA es un desglose, jamás un cargo nuevo** (§4.1).

**Rutas nuevas**: `POST /catalog/plan/simular` (pública).

**Archivos propios**: `Micro-lambda-GMF/python/modo_handlers.py`, `impuestos.py` (nuevo, auxiliar puro), `tests/test_plan_publico.py`, `tests/test_simulador_plan.py`, `tests/test_iva.py`, `tests/rutas/catalog_lambda.json`, `pages/modo-socio/**`, `components/ui-desglose-iva/**`, `services/plan-socio.service.ts`, `models/plan-socio.model.ts`, `components/ui-product-card/ui-product-card.component.html` (solo el enlace del PC, §2.2).

---

### 1.C · `checkout-y-tienda` (3, 7, 10, 13, 22, 31)

**Objetivo.** Que comprar no tenga callejones y que el comprobante compruebe. Es el paquete con más impacto por línea tocada: casi todo es plantilla y front, sin backend nuevo.

**3 · Contacto fuera del bloque de envío.** Nombre, Teléfono y Correo salen del `*ngIf="deliveryType === 'delivery'"` y se piden siempre; el error apunta al campo (no un aviso global). El payload de `pickup` manda `recipientName` y `phone`, que **el backend ya acepta en cualquier modo de entrega** (`order_lambda.py:617-620`). `onDeliveryFieldChange()` sigue disparando la cotización solo en modo domicilio.

**7 · El recibo repite lo elegido.** Cambio de plantilla: **todos los datos ya viajan normalizados** en el objeto que el componente tiene en memoria (`real-api.service.ts:1400-1444`). `#/orden/:id` gana: lista de productos con precios y desglose (con IVA, §3.1), *"Recoges en Sucursal Guadalajara, Av. Chapultepec 480"* (la dirección sale de `POST /orders/checkout/sucursales-recoger`, que ya la devuelve), *"Factura solicitada a nombre de… RFC…"*, y la tarjeta de dirección deja de depender de `shippingType` (que solo se escribe al despachar) para depender de `deliveryType`. La línea de tiempo (`ui-order-timeline`) mira `deliveryType`: en recolección los pasos son *Pago · Preparando · Listo para recoger · Entregado*. En el correo: la **versión de texto plano** deja de omitir el detalle (`core/order_emails.py:242` no llama a `_lineas`), y las dos versiones ganan sucursal y detalle fiscal. Se tolera la vista pública enmascarada del invitado (`_vista_publica_invitado`).

**10 · La cantidad que se teclea.** Se aplica en `ui-product-card` el patrón ya escrito y comentado para el producto destacado (`user-dashboard.component.ts:1896-1919`): borrador local, el carrito solo se toca al pulsar "Agregar". Alcance exacto: el campo solo se pinta en modo `detailed` y para productos sin variantes; los que tienen variantes usan `ui-qty-stepper`, que opera por deltas y **no tiene el defecto**.

**13 · "Estamos confirmando tu pago".** El mensaje **ya está escrito y nunca se enciende** porque `payments.mercadoLibre.successUrl` está vacío y el front no manda `successUrl`. Se manda desde `payWithMercadoPago` (respetando la precedencia cuerpo > configuración del servidor, `order_lambda.py:1011-1013`), se pinta el estado "confirmando" mientras no haya respuesta —sin la tarjeta de resumen en $0— y el sondeo pasa de 60 s fijos a decreciente (5 s, 10 s, 20 s, 30 s) con corte al llegar a `paid`. De paso se acentúan los textos: "Operación", "está siendo procesada".

**22 · Buscador y dirección por producto.** Filtro en cliente sobre nombre + etiquetas + descripción, con normalización de acentos ("colageno"/"colágeno"); el término que Ernesto no encontró ya vive en `tags` (`['omega 3','epa','dha','corazon','capsulas']`). Ruta `tienda/producto/:id` que reutiliza el `pickFromQuery` **que ya funciona**, más un botón "Copiar enlace del producto". Cuidado obligatorio: la ruta `tienda/:refToken` escribe `localStorage['leaderId']`; la ruta nueva tiene distinto número de segmentos y **no debe perder la atribución de la patrocinadora**.

**31 · Cotizar con el CP, y llamar Subtotal al subtotal.** Se corrige la premisa del informe (§0.6): se quita la guardia `hasValidShippingQuoteFormData` y se cotiza con **`zipTo` + items y nada más**, con `debounce` de 600 ms al teclear el CP; el texto pasa a *"Envío desde $129 · escribe tu CP y lo calculamos"* y, en cuanto hay tarifa, el número real. El rótulo "Total" se llama **"Subtotal"** hasta que hay envío elegido, y entonces "Total". **No se toca `shipping_lambda`** (no tiene ni una prueba: cualquier cambio ahí iría sin red). Se deja anotado que la cotización devuelve cada paquetería duplicada y el front la deduplica.

**Rutas nuevas**: `tienda/producto/:id` (frontend). Backend: ninguna.

**Archivos propios**: `pages/carrito/**`, `pages/order-status/**`, `pages/tienda/**`, `components/ui-product-card/**` (salvo el enlace del PC, de B), `components/ui-order-timeline/**`, `Micro-lambda-GMF/python/core/order_emails.py` (salvo las ramas de devolución, de D), `tests/test_correos_pedido.py`, `tests/test_pedidos_creacion.py`.

---

### 1.D · `devoluciones-y-ayuda` (8, 24, 39)

**Objetivo.** Que quien ya pagó tenga a quién escribirle y sepa, **antes de comprar**, qué pasa si algo sale mal. Es el paquete de la decisión de negocio 39.

**8 · Pie de página, ayuda y sucursales.** Bloque de configuración `contacto` nuevo (`email`, `whatsapp`, `horario`, `direccion`) y endpoint público `GET /catalog/ayuda` que devuelve contacto, sucursales (nombre, ubicación, ciudad, estado — **nunca inventario ni `isMainWarehouse`**) y la política de devolución (§3.4). Páginas públicas `#/ayuda`, `#/contacto`, `#/devoluciones`, `#/sucursales`, `#/facturacion` (una sola pantalla con secciones ancladas, salvo `#/devoluciones`, que es propia). El pie (`ui-footer`) lleva correo, WhatsApp, horario y los enlaces, **calcula el año** (hoy "© 2026" está quemado) y **se monta en las pantallas donde falta**: `order-status`, `carrito`, `order-devolucion`, `order-cancelacion`, `perfil`, `verificar-email`. Ruta comodín `**` → `#/ayuda` con el mensaje *"Esa página no existe; aquí están todas las formas de contactarnos"* (§4.15).

**24 · La devolución que se ve.** El botón "Devolver / Llegó dañado" se pinta **siempre** en `#/orden/:id`, apagado con su motivo, con el patrón de botón apagado que el personal ya elogió. El motivo y el plazo no se recalculan en el cliente: `GET /orders/{id}` devuelve `devolucion: {puedeSolicitar, motivo, horasRestantes, plazoTexto}` desde `_resumen_devolucion`, que es **la misma fuente que valida el servidor** (`RETURN_MOTIVOS`), para no crear una quinta versión de la regla. La pantalla "Cancelar orden" menciona la devolución parcial también cuando la cancelación **sí** es posible (hoy solo la ofrece cuando ya está bloqueada).

**39 · La política, decidida y publicada.** La decisión del dueño coincide con lo que el código ya hace, y **eso es la noticia**: paga el envío de regreso quien devuelve, salvo producto dañado o error de la empresa. El trabajo es (a) mover `order_lambda.RETURN_MOTIVOS` a configuración con **valores por omisión idénticos a los de hoy** y validación al guardar (§4.5), añadiendo `returns.direccionDevolucion` y `returns.inspeccionDiasHabiles`; (b) escribir el **proceso completo** —qué se puede devolver y en qué plazo, qué evidencia según el motivo, quién paga el envío en cada caso, a dónde se manda el paquete, cuánto tarda la inspección y cuándo y por qué medio llega el reembolso— en **una sola fuente** (§3.4) que se lee en `#/devoluciones`, en el asistente, en el correo de entrega y en el correo de solicitud recibida. La solicitud ya creada conserva la política con la que nació (`RETURN_REQUEST.refundPolicy`): la configuración **nunca es retroactiva**.

**Rutas nuevas**: `GET /catalog/ayuda` (pública). Frontend: `ayuda`, `contacto`, `devoluciones`, `sucursales`, `facturacion`, `**`.

**Archivos propios**: `Micro-lambda-GMF/python/ayuda_handlers.py` (nuevo), `devoluciones_handlers.py`, la región `RETURN_*` de `order_lambda.py` (§2.2), las ramas de devolución de `core/order_emails.py`, `tests/test_devoluciones*.py` (las cuatro), `tests/test_ayuda_publica.py`, `pages/ayuda/**`, `pages/devoluciones/**`, `pages/order-devolucion/**`, `pages/order-cancelacion/**`, `components/ui-footer/**`, `services/ayuda.service.ts`, `models/ayuda.model.ts`.

---

### 1.E · `navegacion-y-roles` (4, 15, 27, 33)

**Objetivo.** Que cada persona del personal encuentre su trabajo en el primer minuto y pueda mandar un enlace. Es el cambio más barato de la ronda y el que más minutos devuelve. E es **el dueño del caparazón del back office**: `admin.component.{ts,html}` es suyo salvo las regiones nombradas de F y G (§2.2).

**4 · Menú y URL por pantalla.** Inventario real: con URL propia hay 4 pantallas (`#/admin` y las tres de la ronda 5); sin URL, 12 vistas internas por el campo `currentView` y 8 sub-pantallas embebidas. El componente **no inyecta `ActivatedRoute`**: por eso recargar siempre vuelve a la vista por omisión. Se crea una ruta explícita por vista (§3.5), el componente lee `data.view` y `setView()` **navega** en vez de asignar; el menú gana el grupo **FINANZAS → Comisiones y pagos** (`#/admin/comisiones`, hoy al fondo de la ficha de un cliente) y las entradas de **Seguimiento de hoy**, **Despacho en bloque** y **Resumen de turno**, que ya tienen ruta y no están en el menú. La lista de enlaces se escribe **una sola vez** y la barra inferior móvil la reusa (hoy son dos copias de doce enlaces).

**15 · El botón "Ver" de Pedidos.** Reproducido 8 veces entre dos empleados; `toggleOrderDetail()` es correcto, el clic no llega. Cuatro causas, las cuatro se arreglan: (a) el botón de la columna Detalle recibe `[ariaLabel]="'Ver el pedido de ' + o.customer"` — en el mismo archivo, Clientes y Empleados **ya lo llevan**; (b) la pestaña **"Por devolver"** contiene la subcadena "ver" y es el primer elemento de la pantalla cuyo texto la contiene: se renombra a **"Devoluciones en curso"** (§3.7); (c) `setOrderStatus()` **deja de borrar** `orderSearch`; (d) la tira de pestañas sale de la plantilla a un campo `readonly orderTabs` del componente con `trackBy` por clave, para que sus nodos no se recreen en cada pasada de detección (la aplicación es zoneless). Además, el pedido gana URL propia `#/admin/pedido/:id`, con `access_screen_orders` exigido en la ruta porque por ahí pasan los datos fiscales.

**27 · Rol real y recorte honesto.** Tres cosas concretas, ni más ni menos: (a) `campaigns` deja de mapear a `access_screen_stocks` y estrena `access_screen_campaigns` (§4.14) — ese mapeo es literalmente el *"llenar el formulario para crear una campaña de publicidad. Yo. El de las cajas"* de Toño; (b) el formulario de alta de bodega deja de pintarse para quien no tiene `stock_create` (hoy solo el botón está condicionado, y ver el formulario es lo que hizo escribir a la cajera *"puedo dar de alta una bodega"*); (c) la insignia deja de decir ADMIN: se añade el campo **`jobTitle` (puesto)** a `EMPLOYEE`, al alta y a la respuesta de login, y la pantalla pinta "Caja", "Almacén", "Coach". **`role` no cambia** (§0.5). De paso, "Logout" pasa a "Cerrar sesión".

**33 · Aterrizar donde está el trabajo.** `getFirstAllowedView()` recorre una lista fija y los cinco empleados tienen `access_screen_orders`: los cinco caen en Pedidos. Se sustituye por una **tabla explícita de aterrizaje por privilegio** (§3.5) que devuelve una **ruta**, no una vista: caja → `#/admin/pos`, almacén → `#/admin/despacho`, coach → `#/admin/seguimiento`, finanzas → `#/admin/comisiones`, gerencia y superadmin → `#/admin/pedidos`. Pedidos abre en la **primera pestaña con trabajo**, que `nextActions()` ya calcula (hoy abre en "Pendiente" vacía mientras arriba dice "Pagados 3"). El buscador cruza estados: filtra sobre todos los pedidos cargados y la fila muestra su estado; los textos "en este estado" desaparecen.

**Delegación recibida**: la **propuesta 20** (pestaña "Factura solicitada", su contador y el filtro) la construye E dentro de su región de Pedidos, en el mismo commit que la 15, porque el botón "Ver" es lo que hoy corta el camino. El contrato lo escribe G (§1.G).

**Rutas nuevas**: las 15 del back office (§3.5).

**Archivos propios**: `pages/admin/admin.component.{ts,html,css}` (salvo regiones de F y G), `app.routes.ts` (bloque del back office y arbitraje del archivo), `app.config.ts`, `guards/auth.guard.ts`, `models/privileges.model.ts`, `Micro-lambda-GMF/python/core/settings.py` (solo `_ALL_PRIVILEGES`), las regiones de alta de empleado y login de `auth_utils.py`, `tests/test_seguridad.py`, `tests/test_roles_puesto.py`.

---

### 1.F · `caja-almacen-stocks` (5, 6, 21, 28, 30)

**Objetivo.** Que la caja no nazca descuadrada, que el almacén vea sus existencias antes que un formulario para fundar una bodega, y que el turno se pueda entregar sin WhatsApp.

**5 · Abrir turno.** No existe ninguna forma de declarar el fondo inicial: `calcular_arqueo()` lo hereda del `cashToKeep` del último corte y, si no hay corte, es cero — y **tampoco se puede sembrar con un corte en cero**, porque `handle_cash_cut` responde 400 *"No hay ventas ni retiros desde el último corte"*. Se crea `POST /inventory/pos/turno/abrir` (`pos_register_sale`), que escribe un movimiento de apertura con el fondo declarado, quién lo declaró y a qué hora; `calcular_arqueo()` **prefiere la apertura del turno vigente** sobre el corte anterior (§4.11) y la pantalla, cuando no hay ninguno de los dos, dice *"Esta caja nunca ha cerrado un corte: captura el fondo con el que arrancas"* en un campo editable, no un $0.00 de solo lectura. El movimiento de apertura aparece en "Ver movimientos" y en el comprobante.

**6 · El código de autorización, al salir del paso 3.** La tubería **ya existe**: `POST /inventory/pos/validate-auth` responde 200/403 y el front ya la expone (`validatePosAuth`), pero el arqueo solo comprueba que el campo no esté vacío y manda el código con el corte, por eso el 403 llega en "Cerrar el corte". Se valida al avanzar de paso, y con **tres estados distintos**, porque el dato decisivo del dictamen es que en este mundo `GET /inventory/pos/auth-config` responde `{"configured": false}`: *no hay código configurado* → se explica y se ofrece la salida honesta *"deja todo como fondo y avisa a tu gerente"* (que sigue permitiendo cerrar, porque el corte solo exige código con retiro > 0); *código incorrecto* → el botón se apaga con su motivo; *correcto* → avanza. Nunca se muestra la clave de configuración en pantalla.

**21 · Antigüedad y pickup.** `dashboard_lambda.get_admin_warnings` separa los pedidos de recolección del contador de envíos (`paid_no_ship` mete hoy tres recolecciones en el saco de "4 pedidos pagados sin envío") y dice los días del más viejo. La tabla de Pedidos gana **columna de antigüedad**, ordenable y en rojo desde `orders.aviso.diasRojo`; la antigüedad se calcula contra la **hora del servidor** (`serverNow`, §3.6), nunca con `Date.now()`, o se repite el defecto de "todos llevan 0 días". La ordenación se aplica **antes** de cortar la página.

**28 · Stocks: primero el inventario.** (a) La bitácora que la propia pantalla promete **ya existe** al final de la vista ("Registro de entradas y salidas"): se enlaza desde la tarjeta que la anuncia y se corrige "bitacora" → "bitácora". (b) Tabla **producto × sucursal con totales**: los datos ya vienen completos en el estado del front (`stocks[].inventory`), así que es front puro y cero consultas nuevas. (c) **Mínimo por producto** (`stocks.minStockDefault` en configuración y `minStock` por producto), foco rojo en la tabla y su entrada en Acciones urgentes; el aviso se resuelve con **un solo recorrido o `BatchGetItem`**, nunca con un `_get_by_id` por producto dentro del bucle (§0.1). (d) La vista abre con el inventario; "Alta de stock" queda detrás de un botón, en commit aparte del cambio de datos.

**30 · Entregar el turno.** `POST /inventory/turno/resumen/enviar`, calcado de `caja_handlers.handle_enviar_corte`: reutiliza `_texto_resumen` (el `GET` **ya devuelve el texto armado**), manda por `correo._send_ses_email` a un destinatario configurable (`pos.shiftSummaryNotifyEmail`, junto al `cashCutNotifyEmail` que ya existe) y **sella `notifiedTo`/`notifiedAt`** para que no se mande dos veces sin rastro. La autorización repite la del `GET`: el propio turno siempre; el de otra persona exige `access_screen_stats`. No recalcula el resumen dos veces ni amplía las ventanas de fecha del `GET` (es de los endpoints más llamados de la simulación: 337 veces).

**Rutas nuevas**: `POST /inventory/pos/turno/abrir` (`pos_register_sale`), `POST /inventory/turno/resumen/enviar` (`access_screen_stocks` propio / `access_screen_stats` ajeno).

**Archivos propios**: `Micro-lambda-GMF/python/caja_handlers.py`, `despacho_handlers.py`, `inventory_lambda.py`, `dashboard_lambda.py` (salvo la región de G, §2.2), `tests/test_caja_arqueo.py`, `tests/test_pos.py`, `tests/test_turno_resumen.py`, `tests/test_stocks_minimos.py`, `tests/rutas/inventory_lambda.json`, `pages/admin/arqueo/**`, `pages/admin/resumen-turno/**`, `pages/admin/despacho/**`, las regiones **Stocks** y **POS** de `admin.component.{ts,html}`, `services/caja.service.ts`, `services/despacho.service.ts`.

---

### 1.G · `coherencia-y-datos` (9, 11, 12, 16, 19, 20, 25, 26, 29)

**Objetivo.** Que dos partes del sistema no digan cosas distintas del mismo dato: el mismo estado con el mismo nombre, la misma cuenta regresiva, la misma fecha, la misma dirección guardada y el mismo mes. Es el paquete de la coherencia que sacó 3.8 de 10.

**9 · El aviso de privacidad.** La mitad ya está construida y nadie la vio: el aviso **ya habla distinto a cliente y a socio** por su `Input mode`. Dos cosas: (a) el párrafo de modo cliente **miente** —dice "No te pedimos datos bancarios ni fiscales" mientras el mismo carrito pide RFC, razón social, régimen, CP fiscal y uso de CFDI—, y se reescribe por etapas: *"Al comprar te pedimos nombre, contacto y dirección; si pides factura, tus datos fiscales; si activas el modo socio, tu CLABE."*; (b) deja de ser un modal bloqueante a pantalla completa sobre todas las rutas y pasa a **banner inferior no bloqueante** con "Entendido" y "Leer el aviso", **conservando la clave `privacy-notice-accepted-v1`** para no volver a preguntarle a quien ya aceptó. Los derechos ARCO apuntan a `#/contacto` (D).

**11 · La plantilla que dice lo contrario.** Se escribe la plantilla `activa` (hoy la situación existe y tiene etiqueta pero **no tiene plantilla**, y el front rellena con `'fria'` de forma explícita), y mientras una situación no tenga plantilla **no se propone ninguna**: se elimina el respaldo a `'fria'`. Se corrige el texto de `clabe_pendiente`, que manda a "Mi cuenta → Datos bancarios", ruta que no existe: es **Mi perfil** (`#/perfil`), y ahora con enlace directo al formulario de A.

**12 · La bitácora firmada con nombre.** El resolvedor **ya existe** (`noteAuthor`) y se usa en las notas del pedido, pero la bitácora del cliente pinta `{{ n.by }}` crudo. El arreglo va en el backend, no en la plantilla, porque la vista Clientes no carga empleados y la coach no tiene privilegio para verlos: la nota guarda `byName` junto a `by` usando `_nombre_actor()`, que ya vive en el mismo archivo. Aditivo: `by` se conserva. Se resuelve **al escribir**, nunca al leer (leer resolvería N nombres por ficha: un N+1 de manual).

**16 · Lo que se compró como invitado suma.** Al ligar un pedido de invitado a una ficha se invoca **solo el paso 1** de `handle_apply_rewards` (volumen, VP, tramo, activación y reevaluación de bloqueadas), guardado por `rewardsAppliedAt`; **nunca el paso 2**, que repartiría comisión otra vez a toda la línea ascendente. Corre en el camino de ligado, **no colgado de `ORDER_PAID`** (que está en 37 de 40 GetItem). `_es_comprador_registrado` ya reconoce retroactivamente un pedido `guest` con `customerId` y ficha. Prueba obligatoria de idempotencia: ligar dos veces no suma dos veces.

**19 · La casilla que guarda la dirección.** `handle_create_order` lee `body['saveShippingAddress']` (hoy no lo lee **nunca**: el pedido guarda `shippingAddressLabel: 'Casa'` y las 7 fichas siguen con `addresses = 0`) y escribe la dirección en la ficha con **un solo `_update_by_id`**, deduplicando por calle+número+CP y respetando `shippingAddressId` si viene. Se corrige de paso la condición anidada de `customer_lambda.py:686`, que obliga a mandar una llave que no se usa y es hoy **el único camino de escritura de direcciones que existe**. Con eso, la suscripción deja de mandar a la persona a una casilla que no hacía nada.

**20 · La bandeja de facturas.** **No hace falta backend**: el filtro `GET /orders?invoiceStatus=solicitada` ya existe (devuelve las dos facturas del 4 de marzo), la insignia ya se pinta y el bloque para marcar emitida ya está. G escribe el contrato y la prueba de extremo a extremo (`test_checkout_factura.py`); **la pestaña y el contador los pinta E** en su región de Pedidos (delegación de §1.E), filtrando **en memoria** sobre los 500 pedidos ya cargados — nunca con el filtro del servidor, que rompería la lógica de `loadedSections` de `admin-control.service.ts:86-95`.

**25 · Un solo vocabulario.** Los cuatro nombres del mismo estado son cuatro sitios distintos, no una traducción incompleta. Se publica la tabla única estado → texto (§3.7) en `models/vocabulario.model.ts` y `Micro-lambda-GMF/python/vocabulario.py`, y **cada dueño de región sustituye en la suya**: G en la ficha de cliente, la conciliación y Estadísticas; E en Pedidos y la cabecera; F en el POS y el corte; C en el recibo y los correos. Incluye: `mixed` → **"Mixto (efectivo + tarjeta)"** con el desglose que `caja_handlers.py:145-146` **ya calcula**; fechas con `DatePipe` y locale `es-MX`; "Mínimo requerido" completado con su sujeto y su número; género neutro también en los correos.

**26 · Conciliación con rango.** `conciliarPagos()` manda `{}` siempre; el servidor **ya acepta `hours` entre 1 y 2160** y cae a `reconciliationHours` cuando no le mandan nada. Se expone el selector (72 h · 7 días · este mes · desde-hasta) verificando que el nombre del campo coincida (`hours`), con tope y paginación porque cada pedido candidato dispara una consulta a MercadoPago, y **se deja de pisar `finishedAt`** con el reloj del navegador (hoy la corrida queda fechada en 2026-09 con el mundo en 2027-04).

**29 · Un solo corte de mes.** Hay **cuatro** orígenes: el servicio del panel, una copia calcada dentro del propio componente del panel, el carrito (que sin sesión cae al **último día del mes**: 26 d contra 21 d en el mismo minuto) y el del pedido, que sí viene del servidor. El servidor publica `cutoffAt` (instante absoluto ISO) y `serverNow` en el panel y en la configuración pública (sale de configuración ya cargada: **no cuesta consultas**); el servicio es el **único** origen, la copia del componente y el respaldo del carrito se borran, y el texto dice de qué es el corte: *"Cierre del mes de comisiones y de tu descuento por volumen · lunes 25 de marzo, 23:59"*, con la fecha en letras junto al reloj.

**Rutas nuevas**: ninguna. `GET /customers/dashboard`, `GET /user-dashboard` y `GET /commissions/config/app` ganan `cutoffAt`/`serverNow`.

**Archivos propios**: `Micro-lambda-GMF/python/seguimiento_handlers.py`, `vocabulario.py` (nuevo, auxiliar puro), las regiones de `order_lambda.py` (dirección guardada), `customer_lambda.py` (direcciones y corte) y `auth_utils.py` (`_vincular_pedidos_de_invitado`), `tests/test_contacto_plantillas.py`, `tests/test_direcciones_guardadas.py`, `tests/test_invitado_reacreditacion.py`, `tests/test_vocabulario.py`, `tests/test_corte_mes.py`, `components/privacy-notice/**`, `components/ui-status-badge/**`, `models/vocabulario.model.ts`, `services/conciliacion.service.ts`, `services/user-dashboard-control.service.ts`, `pages/admin/seguimiento/**`.

---

## 2. Contrato de archivos

### 2.1 Archivo → paquete dueño

**Backend** (`Micro-lambda-GMF/python/`):

| Archivo | Dueño | Nota |
|---|---|---|
| `pagos_handlers.py` | **A** | Pagos del mes, avisos de CLABE, día de pago, dispersión |
| `commissions_lambda.py` | **A** | Incluye `_write_row` (32) y el interruptor de aviso (2) |
| `core/ledger.py` | **A** | Solo el orden de `filas.sort` (32); importes intocados |
| `modo_handlers.py` | **B** | Plan, ejemplos, simulador, indicadores |
| `impuestos.py` *(nuevo)* | **B** | Auxiliar puro; A, C, F y G lo **importan**, no lo editan |
| `catalog_lambda.py` | **B** | `RUTAS.extend` del simulador y de `ayuda_handlers` (una línea de D) |
| `core/order_emails.py` | **C** | Salvo las ramas de devolución (§2.2) |
| `shipping_lambda.py` | — | **No se toca** esta ronda (§1.C/31) |
| `ayuda_handlers.py` *(nuevo)* | **D** | Contacto, sucursales públicas, política de devolución |
| `devoluciones_handlers.py` | **D** | Reembolso, líneas, evidencia |
| `core/settings.py` | **E** | Solo `_ALL_PRIVILEGES` (`access_screen_campaigns`) |
| `caja_handlers.py`, `despacho_handlers.py`, `inventory_lambda.py` | **F** | Turno, arqueo, POS, stocks |
| `dashboard_lambda.py` | **F** | Salvo la región de G (§2.2) |
| `seguimiento_handlers.py` | **G** | Plantillas, situaciones, bitácora |
| `vocabulario.py` *(nuevo)* | **G** | Auxiliar puro; C, E y F lo **importan** |
| `conciliacion_handlers.py` | **G** | Ventana y `finishedAt` |
| `order_lambda.py`, `customer_lambda.py`, `auth_utils.py` | **por regiones** | §2.2 |
| `core/config.py`, `openapi-aws.yaml` | **por bloques** | §2.3 y §0.3 |
| `core/db.py`, `core/values.py`, `core/security.py`, `core/routing.py`, `core/network.py`, `core_utils.py`, `template.yaml` | — | **No se tocan** |
| `tests/**` | quien crea la prueba | Un archivo de prueba tiene un solo dueño (§0.4) |

**Frontend** (`gamificacion-multinivel-f/src/app/`):

| Archivo o carpeta | Dueño |
|---|---|
| `components/ui-clabe-form/**`, `pages/admin/pagos-mes/**`, `services/pagos.service.ts`, `models/pagos.model.ts` | **A** |
| `pages/modo-socio/**`, `components/ui-desglose-iva/**`, `services/plan-socio.service.ts`, `models/plan-socio.model.ts`, `components/ui-tabla-descuento/**` | **B** |
| `pages/carrito/**`, `pages/order-status/**`, `pages/tienda/**`, `components/ui-product-card/**`, `components/ui-order-timeline/**`, `services/checkout.service.ts`, `services/cart-control.service.ts` | **C** |
| `pages/ayuda/**`, `pages/devoluciones/**`, `pages/order-devolucion/**`, `pages/order-cancelacion/**`, `components/ui-footer/**`, `services/ayuda.service.ts`, `services/devoluciones.service.ts`, `models/ayuda.model.ts` | **D** |
| `pages/admin/admin.component.{ts,html,css}`, `app.routes.ts`, `app.config.ts`, `guards/auth.guard.ts`, `models/privileges.model.ts`, `components/ui-sidebar-nav/**`, `services/admin-control.service.ts` | **E** |
| `pages/admin/arqueo/**`, `pages/admin/resumen-turno/**`, `pages/admin/despacho/**`, `services/caja.service.ts`, `services/despacho.service.ts` | **F** |
| `components/privacy-notice/**`, `components/ui-status-badge/**`, `models/vocabulario.model.ts`, `services/conciliacion.service.ts`, `services/user-dashboard-control.service.ts`, `services/seguimiento.service.ts`, `pages/admin/seguimiento/**`, `pages/user-profile/**` *(salvo el bloque CLABE, de A)* | **G** |
| `pages/user-dashboard/**` | **por regiones** (§2.2) |
| `services/real-api.service.ts`, `models/admin.model.ts`, `models/user-dashboard.model.ts` | **solo por añadido** (§2.2) |
| `services/api.service.ts`, `services/mock-api.service.ts` | **nadie**: no se tocan (el modo mock queda sin lo nuevo, como en la ronda 23) |
| `environments/environment.ts` | **nadie**: nunca entra en un commit |

### 2.2 Regiones de los archivos compartidos

Cada región se nombra por su función o su ancla de plantilla. **Ninguna aparece dos veces.**

**`admin.component.ts` / `admin.component.html`** (dueño base **E**):

| Región (ancla) | Paquete |
|---|---|
| Cabecera (insignia de rol, "Cerrar sesión"), `ui-sidebar-nav`, barra inferior móvil, `adminNavLinksStable`, `setView`, `getFirstAllowedView`, `ensureCurrentViewAllowed`, lectura de `ActivatedRoute` | **E** |
| Vista Pedidos completa: tira de pestañas (`orderTabs`), `setOrderStatus`, `filteredOrdersStable`, `toggleOrderDetail`, botón "Ver", columna de antigüedad, pestaña "Factura solicitada" (delegación de G) | **E** |
| Vista Stocks completa (`currentView === 'stocks'`) y vista POS completa (`currentView === 'pos'`), incluidos `stockInventoryRows`, `inventoryMovementRowsStable` y los métodos de POS y arqueo | **F** |
| Ficha de cliente: bitácora de contactos (`{{ n.by }}`) | **G** |
| `conciliarPagos()` y el modal de conciliación | **G** |
| Vista Estadísticas: selector de mes (`availableReportMonths`, `activeReportMonth`, `getPrevMonthKey`, exportadores) | **A** |
| Vista Estadísticas: los tres textos crudos (`{{ row.status }}`, `{{ o.status }}`, `{{ row.method }}`) | **G** |
| Detalle del pedido: bloque de importes (montaje de `ui-desglose-iva`) | **E** |

**`order_lambda.py`**:

| Región | Paquete |
|---|---|
| `_calculate_totals` (campos de IVA) | **B** |
| `handle_create_order` → bloque de dirección guardada (`saveShippingAddress`) | **G** |
| `RETURN_MOTIVOS` → `_motivos_devolucion(cfg)`, `_evidencia_faltante`, `_validar_solicitud_devolucion`, `_resumen_devolucion` | **D** |
| Todo lo demás | — (no se toca) |

**`customer_lambda.py`**:

| Región | Paquete |
|---|---|
| `handle_update_clabe`, `_resolve_clabe_customer_id`, `_apagar_avisos_clabe` | **A** |
| `handle_update_customer` → bloque `addresses`/`shippingAddress` (condición anidada) y `handle_update_profile` | **G** |
| `handle_customer_dashboard` → campos `cutoffAt`/`serverNow` | **G** |

**`auth_utils.py`**: alta de empleado y respuesta de `handle_login` (campo `jobTitle`) → **E**; `_vincular_pedidos_de_invitado` → **G**. Nada más.

**`dashboard_lambda.py`**: `get_admin_warnings` → **F** (envíos, pickup, mínimos de stock); `handle_user_dashboard` → **G** (`cutoffAt`/`serverNow`).

**`pages/user-dashboard/user-dashboard.component.{ts,html}`**:

| Región | Paquete |
|---|---|
| Bloque de Comisiones: CLABE (`openClabeConfirm`, `saveCustomerClabe`, `isClabeConfirmOpen` y su modal) y la fila de cada comisión (texto §37) | **A** |
| Bloque de metas: enlace a `#/modo-socio` con fragmento | **B** |
| Rejillas de producto: `(qtyChange)`, `updateCart`, `addQuick`, `heroQtyDraft` | **C** |
| Cuenta regresiva del corte: `getNextCutoffDate`, `cutoffRemainingSeconds`, `cutoffTotalSeconds` | **G** |
| Pie de página: la línea `<ui-footer />` al final de la plantilla | **D** |

La misma regla del pie vale para `order-status`, `carrito`, `order-devolucion`, `order-cancelacion`, `perfil` y `verificar-email`: **la última línea de la plantilla es de D**, y es lo único que D toca en archivos ajenos.

**`services/real-api.service.ts`, `models/admin.model.ts`, `models/user-dashboard.model.ts`**: **solo por añadido**. Métodos y campos nuevos al final, en un bloque `// ── Paquete X · ronda 26 ──`; los campos de interfaz van **opcionales y al final**. Nadie edita un método o un campo existente; si hiciera falta, el cambio lo hace el integrador.

### 2.3 Claves de configuración por paquete (`core/config.py`)

| Bloque | Paquete | Claves |
|---|---|---|
| `taxes` *(nuevo)* | **B** | `vatRate: 0.16`, `pricesIncludeVat: True`, `appliesToShipping: True`, `label: "IVA"` |
| `rewards` | **A** | `payoutNoticeEnabled: True`, `blockedUnlockNotice: True`, `commissionBase: "neto_con_iva"` (§4.3) |
| `returns` | **D** | `motivos: [...]` (§3.4), `direccionDevolucion`, `inspeccionDiasHabiles: "2"`; se conservan `refundMethod` y `refundBusinessDays` |
| `contacto` *(nuevo)* | **D** | `email`, `whatsapp`, `horario`, `direccion`, `avisoPrivacidadUrl` |
| `pos` | **F** | `shiftSummaryNotifyEmail: ""`, `requireOpeningCash: True` |
| `stocks` | **F** | `minStockDefault: 0` |
| `seguimiento` | **G** | (sin claves nuevas: la plantilla `activa` vive en `PLANTILLAS` con override ya existente) |
| `orders` | **F** | `agingRedDays: 7` (antigüedad en rojo) |

### 2.4 Atributos nuevos (tabla única, sin índices nuevos)

| Entidad | Paquete | Atributos |
|---|---|---|
| `COMMISSION_MONTH` | **A** | `payoutNoticeSentAt`, `payoutNoticeKind` |
| Fila del ledger | **A** | `recalculatedAt`, `recalculatedReason` (el `createdAt` deja de reescribirse) |
| `ORDER` | **B**, **G** | `vatRate`, `taxBase`, `taxAmount`; `savedShippingAddressId` |
| `CUSTOMER` | **G** | `addresses[]` se escribe de verdad (ya declarado) |
| `EMPLOYEE` | **E** | `jobTitle` (puesto, solo presentación; `role` no cambia) |
| `POS_SHIFT_OPENING` *(bucket nuevo)* | **F** | `stockId`, `attendantUserId`, `openingCash`, `declaredBy`, `createdAt` |
| `POS_SHIFT_SUMMARY` (registro del envío) | **F** | `notifiedTo`, `notifiedAt` |
| `PRODUCT` | **F** | `minStock` |
| Nota de contacto (`CUSTOMER.notes`, `GUEST_CONTACT`) | **G** | `byName` (aditivo; `by` se conserva) |
| `RETURN_REQUEST` | **D** | `refundPolicy` congelada al crear (ya existe; se documenta como no retroactiva) |

---

## 3. Contratos técnicos compartidos

### 3.1 El IVA (§38): forma, dónde se desglosa y quién lo monta

**Supuesto exacto, escrito una vez.** Los precios de lista se manejan **con IVA incluido**. El IVA no se suma nunca: se **desglosa** de un total que no cambia. La base gravable es **todo lo que se cobra** —producto después de descuento y cupón, **más el envío**, que es un servicio gravado— y el desglose se calcula sobre ese total:

```
base = redondear(total / (1 + tasa), 2, mitad_arriba)
iva  = total − base            # así base + iva == total, siempre, al centavo
```

Se redondea **una sola vez, al final, a dos decimales**, sobre el total del pedido: nunca por línea (redondear por línea y sumar produce el descuadre de un centavo que ya se vio en el Cuadro de Honor, [25] §3.15).

**Configuración** (bloque `taxes`, dueño B): `vatRate = Decimal("0.16")`, `pricesIncludeVat = True`, `appliesToShipping = True`, `label = "IVA"`.

**Helper backend** `Micro-lambda-GMF/python/impuestos.py` (dueño B, importable por todos):

```python
def desglose_iva(total_cobrado, cfg=None) -> dict:
    """{"total", "base", "iva", "rate", "label"}  ·  base + iva == total."""
```

**Componente frontend** `components/ui-desglose-iva` (selector `ui-desglose-iva`, dueño B):

```ts
@Input() total = 0;          // lo que se cobra
@Input() shipping = 0;       // informativo: se dice si el envío va dentro de la base
@Input() rate = 0.16;        // de GET /catalog/plan o /commissions/config/app
@Input() variant: 'inline' | 'card' = 'inline';
```

Pinta siempre las **tres líneas en este orden y con estas palabras**: `Subtotal sin IVA · $1,163.79` · `IVA 16 % · $186.21` · `Total · $1,350.00`, y una nota de una línea: *"Los precios ya incluyen IVA; el envío también."*

**Dónde se desglosa y quién lo monta** (el pedido guarda `vatRate`, `taxBase` y `taxAmount` al crearse, así que un pedido viejo no cambia de números cuando cambie la tasa):

| Pantalla | Monta |
|---|---|
| Carrito (resumen y cajón móvil) | **C** |
| Recibo `#/orden/:id` | **C** |
| Correo de pago (HTML y texto plano) | **C** |
| Detalle del pedido en el back office | **E** |
| POS: resumen de venta y comprobante del corte de caja | **F** |
| Bloque de facturación del pedido | **G** |
| Página del plan y simulador | **B** |

### 3.2 El texto único de "la comisión es sobre el neto sin envío" (§37)

Una sola redacción, escrita en `impuestos.py` (backend) y en `models/plan-socio.model.ts` (frontend), ambas de **B**:

- **Frase larga** (página del plan, simulador, correo de comisión):
  *"Tu comisión se calcula sobre el neto que pagó tu referida por producto —el precio ya con su descuento, con IVA incluido— y **sin contar el envío**."*
- **Frase por fila** (`texto_base_comision(neto, tasa, importe)` / `textoBaseComision(...)`):
  *"10 % de $1,350.00 netos, sin envío = $135.00"*.

Se coloca en cinco sitios: página del plan (**B**), simulador (**B**), fila de comisión del panel de la socia (**A**), correo de comisión (**A**) y pantalla de Pagos del mes (**A**). Ningún paquete escribe su propia versión del texto.

### 3.3 El simulador (§36): entradas, salida y componente

`POST /catalog/plan/simular` (pública, dueño B). **Cuerpo**:

```json
{"directos": 2, "compraPorDirecto": 1000, "compraPropia": 1120, "nivelesProfundidad": 1}
```

Topes de entrada: `directos` 0–100, importes 0–100,000, `nivelesProfundidad` 1–`maxLevels`. Fuera de rango → 400 con el tope escrito.

**Respuesta** (todo calculado con `discountTiers`, `commissionLevels`, `activationNetMin` y `mxnPerVp` de la configuración; ningún número escrito a mano):

```json
{"simulacion": {
  "tuCompra": {"bruto": 1120, "tramo": 0.10, "descuento": 112, "netoPagado": 1008,
               "vp": 20.16, "activa": true, "iva": {"base": 868.97, "iva": 139.03}},
  "generaciones": [{"gen": 1, "rate": 0.10, "personas": 2, "compraNetaPorPersona": 1000,
                    "requisitoTexto": "sin requisito", "cumple": true, "comision": 200}],
  "comisionTotal": 200, "gastoPropio": 1008, "gananciaNeta": -808,
  "baseComision": "neto pagado por producto, sin envío",
  "explicacion": ["Con 2 directas que compran $1,000 ganas $200 al mes.",
                  "Tú pagaste $1,008.00 para activarte: tu resultado del mes es -$808.00."],
  "aviso": "Esto es una calculadora con las reglas del plan, no una promesa de ingresos."}}
```

**Componente** `pages/modo-socio/simulador/simulador-plan.component.ts`, selector **`plan-simulador`**, standalone (dueño B):

```ts
@Input() plan!: PlanSocio;              // el plan ya cargado, para no volver a pedirlo
@Input() compraPropiaInicial = 0;       // lo que la persona ya lleva comprado en el mes
@Output() activateRequested = new EventEmitter<void>();
```

Reglas fijas: la ganancia neta se muestra **siempre**, también cuando es negativa; nunca se extrapolan rangos ni bonos; el desglose de IVA (§3.1) y la base de comisión (§3.2) van dentro del resultado, para que **ningún número quede sin explicación**.

### 3.4 La política de devolución (§39): una sola fuente, tres salidas

**Configuración** (bloque `returns`, dueño D), con valores por omisión **idénticos a los `RETURN_MOTIVOS` de hoy**:

```python
"returns": {
  "refundMethod": "mismo medio de pago", "refundBusinessDays": "3 a 5",
  "inspeccionDiasHabiles": "2",
  "direccionDevolucion": "",            # vacío = se toma la sucursal principal
  "motivos": [
    {"key": "DANADO_DEFECTUOSO", "label": "Llegó dañado o defectuoso",
     "limiteHoras": 48, "responsableEnvio": "empresa", "evidencia": "completa"},
    {"key": "ERROR_ENVIO", "label": "Me llegó algo distinto a lo que pedí",
     "limiteHoras": 48, "responsableEnvio": "empresa", "evidencia": "completa"},
    {"key": "DESISTIMIENTO", "label": "Cambié de opinión",
     "limiteHoras": 168, "responsableEnvio": "cliente", "evidencia": "paquete_cerrado"}]}
```

Validación al guardar: `limiteHoras` entero 1–8760, `responsableEnvio ∈ {empresa, cliente}`, `evidencia ∈ {completa, paquete_cerrado}`; una clave inválida se rechaza y **no se guarda nada**. `order_lambda` lee `_motivos_devolucion(cfg)` en vez de la constante, con la misma forma.

**El texto del proceso, en seis puntos**, generado por `ayuda_handlers.texto_politica(cfg)` a partir de esa configuración y usado **sin reescribir** en `#/devoluciones`, en el asistente `#/orden/:id/devolucion`, en el correo de entrega y en el de solicitud recibida:

1. **Qué se puede devolver**: producto completo o solo algunas líneas, con la cantidad que se elija.
2. **En qué plazo**: 48 horas desde la entrega si llegó dañado o equivocado; 7 días si cambiaste de opinión.
3. **Qué evidencia se pide**: dañado o error → fotos del producto, del empaque y de la guía; arrepentimiento → una foto del paquete cerrado con la guía visible.
4. **Quién paga el envío de regreso**: **lo paga quien devuelve**, salvo producto dañado o error nuestro, donde **lo pagamos nosotros** (guarda tu ticket).
5. **A dónde se manda**: la dirección de devolución configurada.
6. **Cuánto tarda y cómo llega el reembolso**: inspección en 2 días hábiles y reembolso al mismo medio de pago en 3 a 5 días hábiles; si la devolución es completa y el motivo es nuestro, se reembolsa también el envío original.

### 3.5 Las rutas del back office (§4, §15, §33)

**Patrón único.** Una ruta explícita por vista (nada de comodín `admin/:vista`, que dejaría entrar cualquier cadena), apuntando al mismo `AdminComponent`, con la vista en `data` y **dos guardas**:

```ts
{ path: 'admin/comisiones', component: AdminComponent,
  data: { view: 'customers', panel: 'pagos-mes', titulo: 'Comisiones y pagos' },
  canActivate: [adminGuard, adminViewGuard] },
```

| Ruta | Vista | Privilegio |
|---|---|---|
| `admin` | redirige al aterrizaje por rol | `hasAdminPanelAccess` |
| `admin/pedidos`, `admin/pedido/:id` | `orders` | `access_screen_orders` |
| `admin/clientes` | `customers` | `access_screen_customers` |
| `admin/comisiones` | `customers` + panel `pagos-mes` | `commissions_register_payment` |
| `admin/empleados` | `employees` | `access_screen_employees` |
| `admin/productos` | `products` | `access_screen_products` |
| `admin/stocks` | `stocks` | `access_screen_stocks` |
| `admin/campanas` | `campaigns` | `access_screen_campaigns` *(nuevo)* |
| `admin/pos` | `pos` | `access_screen_pos` |
| `admin/estadisticas` | `stats` | `access_screen_stats` |
| `admin/cuadro-de-honor` | `honor_board` | `access_screen_honor_board` |
| `admin/avisos` | `notifications` | `config_manage` |
| `admin/cupones` | `coupons` | `config_manage` |
| `admin/configuracion` | `settings` | `access_screen_settings` |
| `admin/despacho`, `admin/resumen-turno`, `admin/seguimiento` | ya existen | sus privilegios de pantalla |

`adminViewGuard` (nuevo, dueño E) lee `route.data.view` y comprueba `SCREEN_PRIVILEGE_BY_VIEW`: sin él, cualquiera con panel escribiría `#/admin/configuracion` a mano. **Aterrizaje por rol** (`landingRouteFor(privileges)`), en este orden: `pos_register_sale` sin `access_screen_stats` → `admin/pos`; `stock_receive_transfer` o `stock_add_inventory` → `admin/despacho`; `access_screen_customers` sin `commissions_register_payment` → `admin/seguimiento`; `commissions_register_payment` → `admin/comisiones`; resto → `admin/pedidos`. Si la ruta calculada no está permitida, se cae a la primera permitida de la tabla y **se dice en pantalla**, nunca se deja el contenedor vacío.

`app.config.ts` (dueño E) recibe en el mismo commit las dos líneas que otros necesitan: `withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' })` para los fragmentos de B (§23) y el registro del locale **`es-MX`** para las fechas de G (§25).

### 3.6 Periodos y reloj del servidor (§17, §21, §26, §29)

Ninguna pantalla de dinero vuelve a usar `new Date()`. Dos contratos:

`GET /commissions/periodos` (dueño A):

```json
{"serverNow": "2027-04-10T13:15:37Z", "mesContableVigente": "2027-03",
 "defaultMonth": "2027-03",
 "periodos": [{"monthKey": "2027-03", "label": "marzo de 2027",
               "beneficiarias": 1, "confirmado": 135.00, "porConfirmar": 124.20,
               "bloqueado": 0, "estado": "IN_PROGRESS"}]}
```

`serverNow` y `cutoffAt` (instante absoluto del corte, calculado con `cutoffDay/cutoffHour/cutoffMinute` que el servidor ya tiene) se añaden además a `GET /customers/dashboard`, `GET /user-dashboard` y `GET /commissions/config/app` (dueño G). **No cuestan consultas**: salen de configuración ya cargada. El frontend calcula la cuenta regresiva como `cutoffAt − (serverNow + tiempo transcurrido en el cliente)`, y la antigüedad de un pedido como `serverNow − order.createdAt` (F, §21).

### 3.7 Vocabulario único de estados (§25)

Tabla única, **en español de México y sin género** (hoy conviven "Pagada" del badge, "Pago registrado" del seguimiento y `paid` crudo en tres pantallas). Vive en `models/vocabulario.model.ts` y en `Micro-lambda-GMF/python/vocabulario.py`, ambos de **G**; cada dueño de región sustituye en la suya.

| Estado guardado | Texto en pantalla | Matiz de recolección |
|---|---|---|
| `pending` | **Pendiente de pago** | — |
| `paid` | **Pagado** | con `deliveryType = pickup`: **Listo para recoger** |
| `shipped` | **Enviado** | — |
| `delivered` | **Entregado** | con `pickup`: **Entregado en sucursal** |
| `cancelled` | **Cancelado** | — |
| `returned` | **Devuelto** | — |
| `refunded` | **Reembolsado** | — |
| `rejected` | **Rechazado** | — |
| `en_devolucion` | **Devolución en curso** | (también el nombre de la pestaña, §15) |
| `devuelto_validado` | **Devolución validada** | — |
| `devolucion_rechazada` | **Devolución rechazada** | — |

Métodos de pago: `cash` → **Efectivo**, `card` → **Tarjeta**, `transfer` → **Transferencia**, `mercadopago` → **MercadoPago**, `branch` → **Pago en sucursal**, `mixed` → **Mixto (efectivo + tarjeta)** seguido del desglose que `caja_handlers` ya calcula: *"Mixto · $500.00 en efectivo · $260.00 con tarjeta"*.

Fechas: `DatePipe` con locale `es-MX`, formato `d 'de' MMMM 'de' y, HH:mm` en pantalla y `dd/MM/yyyy` en tablas. Nunca un ISO crudo.

---

## 4. Decisiones sobre lo ambiguo

Cada una con su porqué. Se toman aquí para que nadie las vuelva a decidir dentro de un paquete.

1. **Base gravable del IVA: todo lo que se cobra, envío incluido.** El desglose se calcula sobre el total del pedido (producto tras descuento y cupón + envío), no sobre el subtotal de producto. *Porqué:* el envío es un servicio gravado y el importe que la persona compara con su estado de cuenta es el total; si el envío quedara fuera, `base + IVA` no daría el total y volveríamos a tener dos cifras del mismo dinero, que es justo la queja de coherencia (3.8 / 10) de esta ronda. La clave `taxes.appliesToShipping` existe por si el negocio necesita lo contrario, con valor por omisión `True`.
2. **Redondeo: dos decimales, mitad arriba, una sola vez y al final.** `base = redondear(total / 1.16)` e `iva = total − base`, nunca al revés y **nunca por línea**. *Porqué:* garantiza al centavo que `base + IVA == total` en pantalla, en el correo y en la factura; redondear por línea y sumar es exactamente el error que produjo el "50 de VG arriba contra 25 + 24 abajo" del Cuadro de Honor.
3. **La comisión se calcula sobre el neto pagado por producto, con IVA incluido y sin envío.** Es lo que el motor hace hoy (`_commissionable_net` devuelve `netTotal` sin envío, y el `rate` se aplica sobre eso: $135 sobre $1,350). *Porqué:* cambiar la base a "neto sin IVA" reduciría **toda** comisión un 13.79 %, afectaría a importes ya confirmados y pagados y obligaría a recalcular el ledger histórico; y el número que la socia ve en su pedido es el que paga, no una base fiscal que nadie le enseña. Queda el interruptor `rewards.commissionBase = "neto_con_iva" | "neto_sin_iva"` (por omisión `neto_con_iva`, el comportamiento actual) para que la decisión se pueda revisar en un solo sitio, **nunca de forma retroactiva**. La base elegida se dice con las palabras de §3.2 en la página del plan, en el simulador, en la fila de la comisión, en el correo y en pagos del mes.
4. **El IVA no cambia ni un importe cobrado.** Es desglose de un total que ya incluía impuesto, no un cargo nuevo. Los pedidos anteriores a la ronda **no se migran**: no traen `taxBase`/`taxAmount` y su recibo los calcula al vuelo con `taxes.vatRate`; los pedidos nuevos los guardan al crearse, de modo que un cambio futuro de tasa no reescribe la historia. *Porqué:* no hay script de migración que valga el riesgo sobre dinero ya cobrado, y los mundos sembrados (`sim/semilla.py`) deben seguir cuadrando peso a peso.
5. **La política de devolución se muda a configuración con valores idénticos a los de hoy y no es retroactiva.** `RETURN_MOTIVOS` deja de ser constante, pero los valores por omisión son los mismos (48 h / 48 h / 7 días; empresa, empresa, cliente); la solicitud ya creada conserva su `refundPolicy`. Se valida al guardar (§3.4). *Porqué:* el plazo y el responsable entran directo en el importe reembolsado y, río abajo, en la anulación de comisiones: un plazo vacío abriría devoluciones eternas y un cambio retroactivo movería reembolsos ya calculados.
6. **La CLABE se guarda directo, sin modal, y se puede borrar.** El paso de confirmación desaparece (dieciocho dígitos validados no lo necesitan) y `handle_update_clabe` acepta cadena vacía para quitarla, con confirmación en línea en el propio campo. *Porqué:* el `POST` vivía únicamente detrás de "Confirmar" y el modal se cerraba con un clic al fondo o con Escape, descartando la CLABE en silencio: diez intentos, dos pantallas, cero peticiones al servidor. **No se cambia `ui-modal`**: tocar `closeOnBackdrop` afectaría a todos los modales del producto (arqueo, avisos, lote de pagos).
7. **El aviso de CLABE es idempotente por motivo, no solo por mes.** El id pasa a `NTF-CLABE-<cliente>-<mes>-<motivo>`; el de activación caduca a los 30 días y el de comisión a los 45. *Porqué:* con el id actual, quien recibió el aviso de activación no vería nunca el correcto al tener comisión de verdad, que es el defecto que más credibilidad cuesta por línea de código.
8. **La ventana "Ya tienes comisiones a tu favor" no se apaga: se corrige.** Se mantiene `clabeReminderOnActivation = True` y se cambia **el texto y el texto del plan**. *Porqué:* pedir la CLABE al activarse es operativamente correcto (el día 10 no da tiempo de conseguirla); lo que no se puede es prometer un dinero que no existe ni contradecir la página del plan. La contradicción se resuelve por el lado del plan, no apagando el recordatorio.
9. **`activacion.pesosAprox` se borra del contrato, no se deja "deprecado".** En su lugar `activacion.rango = {min, max, notaProducto}` y, en los ejemplos de generación, la compra de referencia pasa a ser el **neto de la canasta más barata que activa**. Se actualizan `test_plan_publico.py` y `PlanSocio` en el mismo commit. *Porqué:* un campo que miente y sigue publicado se vuelve a pintar en la siguiente pantalla; y era el número más importante del plan, en la página que se llama "con los números reales".
10. **El simulador nunca promete.** Muestra siempre la ganancia **neta** (comisiones − gasto propio), también cuando es negativa, con el aviso fijo de que es una calculadora y no una promesa de ingresos, y sin extrapolar rangos ni bonos. *Porqué:* publicar cifras de ganancia es materia regulatoria en México y la persona que vino a decidir si esto es un negocio (10 de 16 tareas sin un solo clic) necesita el número honesto, no el ejemplo bonito.
11. **El fondo de caja: gana la apertura del turno vigente sobre el corte anterior.** Si existe una apertura posterior al último corte para ese par (sucursal, cajera), `calcular_arqueo()` usa su `openingCash`; si no, hereda `cashToKeep` como hoy; si no hay ninguno de los dos, el campo es editable y la pantalla lo explica. *Porqué:* la apertura es el dato más reciente y declarado por quien tiene el dinero en la mano; heredar en ese caso es lo que produjo el sobrante falso de $540 y $1,040 en el cajón toda la noche.
12. **El código de autorización del POS distingue tres estados.** *No hay código configurado* (hoy `GET /inventory/pos/auth-config` responde `{"configured": false}`) se dice con esas palabras y ofrece cerrar dejando todo como fondo; *incorrecto* apaga el botón con su motivo; *correcto* avanza. *Porqué:* validar antes sin distinguir el primer caso solo adelanta el 403 y deja igual de atorada a la cajera.
13. **La propuesta 35 no fuerza exportar con cero filas.** Un archivo con solo la cabecera es peor que no exportar; las pendientes salen en un **segundo archivo**, nunca como filas más en el layout que se sube al portal bancario. *Porqué:* el bloqueo actual está bien hecho y el personal lo elogió; lo que faltaba era decir cuántas esperan y llevarse la lista.
14. **Se crea un único privilegio nuevo, `access_screen_campaigns`, y se siembra con cuidado.** Se enciende para superadmin, para `role = admin` y para quien tenga `config_manage`; se apaga para el resto, aunque hoy vean Campañas por el mapeo a `access_screen_stocks`. El cambio de semilla se documenta y lleva prueba. *Porqué:* sembrarlo en `true` para todo el que tiene inventario reproduciría exactamente el defecto que la propuesta 27 viene a quitar; y dejarlo apagado para gerencia le quitaría una pantalla en silencio, así que se nombra a quién se le enciende.
15. **La ruta comodín `**` va a `#/ayuda`, no a la tienda ni a `''`.** *Porqué:* `''` monta el panel del cliente sin guarda y una URL mal escrita dejaría hoy el contenedor vacío; y quien escribe `#/devoluciones` o `#/soporte` viene buscando ayuda, no productos.
16. **El corte de mes tiene un solo origen y se explica.** El servidor publica `cutoffAt` y `serverNow`; se borran la copia calcada dentro del componente del panel y el respaldo del carrito que calculaba el **último día del mes** (origen de los "26 d y 21 d en el mismo minuto"). El rótulo dice de qué es el corte y la fecha en letras. *Porqué:* un reloj en cuenta regresiva sin explicación no apura, asusta: ninguna de las siete personas que lo vieron entendió qué se acababa.
17. **El género: neutro en pantalla y en los correos.** "Entregado", "Pagado", "Hola, {nombre}". Se conserva "socia/socio" solo donde el texto habla del rol y la persona ya declaró el suyo. *Porqué:* al señor de 63 años el sistema le dijo "socia" cinco veces, incluso por correo; y mantener dos géneros en la misma tabla de estados obligaría a elegir uno por pantalla, que es como nacieron los cuatro nombres del mismo estado.
18. **El ticket del POS para el cliente queda fuera de esta ronda.** Ninguna de las 39 propuestas lo pide; el IVA del mostrador se desglosa donde el POS ya muestra dinero (resumen de venta y comprobante del corte). *Porqué:* construir un ticket es una pantalla nueva con su propio diseño e impresión, y meterla de contrabando dentro de la propuesta 38 pondría en riesgo el corte de caja, que hoy es de lo mejor calificado del producto.
19. **La propuesta 20 la ejecuta E, no G.** La pestaña, el contador y el filtro viven en la vista Pedidos, cuyo dueño es E, y dependen de que el botón "Ver" funcione (propuesta 15). G escribe el contrato y la prueba. *Porqué:* dos paquetes editando la tira de pestañas y `filteredOrdersStable` a la vez es el conflicto más caro de la ronda, y arreglar 20 sin 15 deja una bandeja que lleva a un acordeón que no abre.
20. **Nada nuevo cuelga de `ORDER_PAID`.** La reacreditación del invitado (16) corre en el camino de ligado; los meses contables (17) se recorren en su propio endpoint; el correo del día 10 (34) es una tarea programada por lotes. *Porqué:* `ORDER_PAID` está en 37 de 40 GetItem con 800 clientes: tres de holgura. Cualquier trabajo extra ahí revienta el presupuesto y lo caza `tools/check_query_budget.py`.

---

## 5. Orden de trabajo y dependencias

**Día 1 — los contratos, antes que el código.** Tres commits pequeños que desbloquean a los demás:

1. **B** publica `taxes` en `core/config.py`, `impuestos.py` (con `desglose_iva` y `texto_base_comision`) y el componente `ui-desglose-iva` vacío pero con su API fija (§3.1, §3.2).
2. **G** publica `vocabulario.py` y `models/vocabulario.model.ts` con la tabla de §3.7.
3. **E** publica `app.routes.ts` con las rutas del back office, `adminViewGuard`, `app.config.ts` (fragmentos + `es-MX`) y `access_screen_campaigns` en `_ALL_PRIVILEGES` y en `privileges.model.ts` (§3.5).

**Ola 1 — en paralelo, sin dependencias entre sí:** **A**, **C**, **D**, **F**. A y C son los de mayor rendimiento medido por línea tocada; D es el único que necesita decisión de negocio ya tomada (39).

**Ola 2 — sobre lo anterior:** **E** (15, 27, 33 y la delegación de 20; necesita el vocabulario de G y las rutas del día 1) y **B** (14, 23, 36, 37; necesita `GET /commissions/periodos` de A solo para el ejemplo de comisión, no para el simulador).

**Ola 3 — el que cose:** **G** (9, 11, 12, 16, 19, 25, 26, 29). Su parte de vocabulario ya está publicada; lo que hace al final es sustituir en las regiones ajenas **que ya han dejado de moverse**.

Dependencias explícitas:

| Depende | De | Qué |
|---|---|---|
| C, E, F, G (montaje del IVA) | **B** | `impuestos.py` y `ui-desglose-iva` (§3.1) |
| A (texto de la comisión) | **B** | `texto_base_comision` (§3.2) |
| C, E, F (textos de estado) | **G** | `vocabulario` (§3.7) |
| E (menú y aterrizaje) | **día 1** | rutas y `adminViewGuard` (§3.5) |
| **20** | **15** y **4** | el botón "Ver" y la URL del pedido |
| F (antigüedad, 21) y G (corte, 29) | **A/G** | `serverNow` (§3.6) |
| A (Pagos del mes, 17/18) | — | independiente; es la ruta crítica del día 10 |
| D (pie en seis pantallas) | dueños de esas pantallas | una sola línea al final de cada plantilla (§2.2) |

**Checklist por paquete antes de dar por terminado:** `pytest` verde en `Micro-lambda-GMF/python`; `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py -k <anfitrión>` con diff que solo contenga rutas propias; `python3 tools/check_query_budget.py` en verde; `npx tsc -p tsconfig.app.json --noEmit` sin errores (y compilación de plantillas si se tocaron); `openapi-aws.yaml` con las rutas nuevas; `git status` sin `environment.ts`.

---

## 6. Cómo se verifica cada propuesta

Una línea por propuesta: la pantalla o el comando que lo demuestra. Con el harness vivo (`bash sim/comprobar.sh`, backend en `:4400`).

| # | Verificación |
|---|---|
| 1 | En `#/dashboard#comisiones`, escribir 18 dígitos y pulsar **Guardar**: el propio campo pasa a "guardada, termina en 6789" y `sim/servidor.log` muestra un `POST /customers/clabe` 200. "Quitar CLABE" la borra. |
| 2 | Activar una cuenta sin comisiones: el aviso del portal dice "desde hoy las compras de tu red te generan comisiones" y **no** "Ya tienes comisiones a tu favor"; al confirmarse la primera comisión aparece el segundo aviso, con monto (`pytest tests/test_avisos_clabe.py`). |
| 3 | Como invitado, elegir "Recoger en sucursal": los campos Nombre, Teléfono y Correo se ven y el pedido creado trae `recipientName` y `phone` no nulos (`GET /orders/{id}`). |
| 4 | `#/admin/comisiones` abre Pagos del mes al recargar; el menú lateral muestra FINANZAS → Comisiones y pagos, Seguimiento de hoy, Despacho en bloque y Resumen de turno. |
| 5 | Caja sin corte previo: la pantalla pide el fondo, se declaran $500 y el arqueo del día muestra "Fondo inicial $500.00" y diferencia $0 con $540 contados (`pytest tests/test_caja_arqueo.py`). |
| 6 | En el paso 3 del arqueo, con `auth-config` sin código: el botón se apaga diciendo "no hay código configurado" y ofrece "dejar todo como fondo"; con código incorrecto, el motivo cambia; nunca llega un 403 en "Cerrar el corte". |
| 7 | `#/orden/ORD-351342D9`: lista de productos, desglose con IVA, "Recoges en Sucursal Guadalajara, Av. Chapultepec 480" y "Factura solicitada · RFC…"; el correo de `sim/buzon/` (texto plano) trae el detalle. |
| 8 | `#/ayuda`, `#/contacto`, `#/devoluciones`, `#/sucursales` y `#/facturacion` cargan; el pie muestra correo, WhatsApp, horario y el año en curso en las trece pantallas. |
| 9 | El aviso de privacidad es un banner inferior que no tapa "Ver cómo funciona"; su texto de modo cliente menciona los datos fiscales de la factura; quien ya aceptó no lo vuelve a ver (clave `privacy-notice-accepted-v1`). |
| 10 | En la tarjeta del catálogo, teclear 2 y pulsar "Agregar a carrito": el carrito queda en **2**, no en 3. |
| 11 | `GET /customers/seguimiento/plantillas` incluye `activa`; un cliente que compró ayer propone la plantilla de activo y **nunca** "hace tiempo que no te vemos"; `clabe_pendiente` enlaza a `#/perfil` (`pytest tests/test_contacto_plantillas.py`). |
| 12 | La bitácora del cliente muestra "Gaby Ledesma", no `1803978000111`; la nota guardada trae `byName` y conserva `by`. |
| 13 | Al volver de la pasarela, la pantalla dice "Estamos confirmando tu pago" con el botón deshabilitado y refresca a los 5 s; nunca pinta un resumen en $0. |
| 14 | `GET /catalog/plan` no trae `pesosAprox`; `#/modo-socio` muestra el rango ($933–$1,605) y las dos canastas reales, sin "más o menos $1,000" (`pytest tests/test_plan_publico.py`). |
| 15 | En Pedidos, "Ver" abre el detalle **de esa fila** (tiene `aria-label` con el nombre), la pestaña se llama "Devolución en curso", el buscador sobrevive al cambio de pestaña y `#/admin/pedido/:id` abre solo. |
| 16 | Ligar un pedido de invitado y consultar `GET /commissions/associates/<id>/month/2027-03`: `vp` y `netVolume` dejan de ser 0; ligar dos veces no duplica (`pytest tests/test_invitado_reacreditacion.py`). |
| 17 | `GET /commissions/periodos` devuelve marzo 2027 y `defaultMonth`; recargar `#/admin/comisiones` mantiene el mes; el archivo exportado se llama con el mes **seleccionado** y trae sus datos. |
| 18 | Pagos del mes muestra la fila de Paulina con Confirmado $135.00, Por confirmar $124.20 y Bloqueado, con el pedido que las frena y sus días; el CSV del banco sigue trayendo solo las `listo` (`pytest tests/test_pagos_mes.py`). |
| 19 | Comprar palomeando "Guardar esta dirección" con alias "Casa" y consultar `GET /customers/getall`: la ficha trae `addresses` con esa entrada; repetir la compra no la duplica. |
| 20 | Pedidos muestra la pestaña "Factura solicitada" con contador 2 y las dos órdenes del 4 de marzo; desde la fila se abre el bloque para marcar emitida con folio. |
| 21 | El aviso dice "1 pedido pagado sin envío · 37 días" y aparte "3 pedidos por recoger en mostrador"; la tabla tiene columna de antigüedad ordenable, en rojo desde 7 días. |
| 22 | Buscar "omega 3" en `#/tienda` encuentra el Klinhart; `#/tienda/producto/<id>` lo abre destacado y el botón copia ese enlace; llegar por `#/tienda/<refToken>` sigue guardando `leaderId`. |
| 23 | "Cómo se calculan" cae en la sección de generaciones (`#/modo-socio#generaciones`); la tarjeta de producto y el bloque de metas enlazan al plan. |
| 24 | En un pedido `paid`, el botón "Devolver / Llegó dañado" se ve apagado con su motivo y su plazo; en "Cancelar orden" se menciona la devolución parcial. |
| 25 | El mismo pedido se llama **Pagado** en las cuatro pantallas y en el correo; el corte muestra "Mixto (efectivo + tarjeta) · $500.00 · $260.00"; las fechas se leen "2 de marzo de 2027, 11:18". |
| 26 | Conciliar con "este mes" manda `hours` acorde y devuelve revisados > 0; la tarjeta "última corrida" muestra la hora **del servidor** (2027-04), no la del navegador. |
| 27 | Con la sesión de la cajera: el menú no muestra Campañas, la vista Stocks no pinta el formulario de alta y la insignia dice "Caja"; el botón dice "Cerrar sesión". |
| 28 | Stocks abre con la tabla producto × sucursal y totales; un producto bajo su mínimo sale en rojo y en Acciones urgentes; la tarjeta enlaza a la bitácora; `python3 tools/check_query_budget.py` sigue en verde. |
| 29 | Sin sesión en `#/carrito` y con sesión en `#/dashboard`, en el mismo minuto: el mismo número de días y la misma fecha en letras, con el rótulo que dice de qué es el corte. |
| 30 | Desde `#/admin/resumen-turno`, "Enviar a mi gerente" deja el correo en `sim/buzon/` con los tres pedidos y sus guías, y el registro queda sellado con `notifiedTo`/`notifiedAt`; enviar dos veces no duplica. |
| 31 | Escribir solo el CP 03100 en el carrito: aparecen Estafeta $129 y DHL $219 sin pedir nada más; el rótulo dice "Subtotal" hasta elegir envío y luego "Total $829". |
| 32 | Activar a una patrocinadora y releer el ledger: las comisiones del 2 y del 4 de marzo conservan su fecha, el historial no se reordena y la fila dice "recalculada el 20 de marzo" (`pytest tests/test_comision_fecha.py`). |
| 33 | Cada credencial de `sim/credenciales.json` aterriza en su pantalla (caja → POS, almacén → Despacho, coach → Seguimiento, finanzas → Comisiones); Pedidos abre en la pestaña con trabajo y el buscador encuentra "Ximena" esté donde esté. |
| 34 | Mover el reloj al día 10 (`POST /__sim/reloj`) y revisar `sim/buzon/`: sale "Te depositamos $135…" o "No te pudimos depositar porque nos falta tu CLABE"; disparar la tarea dos veces no manda dos correos (`pytest tests/test_dia_de_pago.py`). |
| 35 | Con una socia sin CLABE y otra lista: el CSV del banco trae solo la lista, se descarga aparte `pendientes-2027-03.csv` y el botón apagado dice "1 espera CLABE ($135.00)". |
| 36 | En `#/modo-socio#simulador`, con 2 directos × $1,000 y compra propia $1,120: muestra comisión $200, gasto $1,008 —lo que paga de verdad, con su 10 % de descuento; el campo se captura a precio de lista— y ganancia neta −$808, con el aviso de que no es una promesa de ingresos. |
| 37 | La misma frase aparece en `#/modo-socio`, en el simulador, en la fila de la comisión del panel, en el correo de comisión y en Pagos del mes: "10 % de $1,350.00 netos, sin envío = $135.00". |
| 38 | Carrito, recibo, correo de pago, detalle del pedido, POS, corte y facturación muestran "Subtotal sin IVA / IVA 16 % / Total" con `base + IVA == total` al centavo; cambiar `taxes.vatRate` a 0.08 cambia el desglose y **no** el total (`pytest tests/test_iva.py`). |
| 39 | `#/devoluciones` publica los seis puntos del proceso; el asistente y los dos correos dicen lo mismo, leído de la misma fuente; cambiar `returns.motivos[].limiteHoras` cambia el plazo en las tres salidas (`pytest tests/test_devoluciones*.py`). |
