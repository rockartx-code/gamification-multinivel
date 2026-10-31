# 26 · Séptima ronda: las 39 propuestas aplicadas, y qué pasó cuando cinco personas las usaron

Continuación de [25](25-ronda-experiencia-medida.md). Aquella ronda midió a doce personas y terminó en 44 propuestas (§7); las **39 primeras** —las que no eran preguntas abiertas de gobierno— se repartieron en siete paquetes, se validaron contra el código **antes** de escribir una línea, se implementaron a la vez en siete worktrees, se integraron, se revisaron y se pusieron delante de cinco personas nuevas del mundo simulado.

Este documento cuenta qué se hizo con cada una en la rama `claude/ultimos-cambios-integrados-fylhiw` entre `76165c5` (el commit de [25]) y `7fdacff`: el contrato ([arquitectura/26](../arquitectura/26-treinta-y-nueve-propuestas.md)), lo que la validación encontró antes de empezar, las cuatro decisiones de negocio del dueño, los 24 hallazgos de las revisoras, la sesión con Valeria, Gerardo, Nayeli, Rubén y Marisol, y los dos commits de corrección que la cerraron.

Todo lo que aquí se afirma se puede comprobar con `git log --oneline 76165c5..7fdacff` (64 commits), con los diarios nuevos `sim/diarios/{valeria-nunez,gerardo-lomeli,nayeli-ocampo,ruben-avila,marisol-cepeda}-2027-05-*.md` y con `python3 sim/metricas.py --markdown`.

---

## 1. Resumen ejecutivo

| | |
|---|---|
| Propuestas de [25] §7 | 39 tomadas (1–39); **38 implementadas**, **1 parcial** (38: el IVA se desglosó en todas partes, la retención de ISR y el monto mínimo de depósito siguen sin existir), **ninguna descartada** |
| Cómo se hizo | Un contrato de propiedad de archivos y regiones ([arquitectura/26](../arquitectura/26-treinta-y-nueve-propuestas.md), `76165c5`); **una validación en lectura** sobre la propia rama antes de codificar (§2); siete agentes en worktrees a la vez; una integración; tres revisoras; cinco personas en el arnés; dos commits de corrección |
| Tamaño del cambio | `git diff --shortstat 76165c5..7fdacff`: **160 archivos, +14,358 / −1,293 líneas**; 44 archivos nuevos; 8 rutas de API nuevas; 16 archivos de prueba nuevos; 5 pantallas públicas nuevas (`#/ayuda`, `#/contacto`, `#/sucursales`, `#/facturacion`, `#/devoluciones`) y 15 rutas explícitas del back office |
| Pruebas del backend | 392 → **613 en verde** (`python3 -m pytest tests -q`); `tools/check_query_budget.py` en verde con **ORDER_PAID en 37 de 40 GetItem**, exactamente igual que al empezar |
| Frontend | `npx tsc -p tsconfig.app.json --noEmit` y `ngc` sin errores; `ng build` de producción en verde (tres avisos de presupuesto de tamaño ya existentes) |
| Hallazgos de las revisoras | **24**, todos reproducidos y **todos corregidos**; ninguno descartado. 3 críticas de seguridad, 1 alta de integridad, el resto medias y bajas (§4) |
| Validación con personas | 5 diarios del 4, 5 y 10 de mayo de 2027 (Valeria, Gerardo, Nayeli, Rubén, Marisol), **29 tareas, 19 logradas (66 %)**, 63 fallas reportadas; 50 corregidas en `13a44ed` + `7fdacff`, 3 descartadas con su razón, 10 quedan pendientes (§5, §6) |
| Lo que mejoró en la medida | facilidad **3.6 → 4.0**, confianza **3.9 → 4.3**, confianza que transmite **4.8 → 5.8**, coherencia **3.8 → 4.4**, recomendaría **5.2 → 6.0** (§5.7). Cinco personas no son doce: qué comparación aguanta y cuál no, en §5.8 |
| Estado del mundo | Reloj de la simulación en mayo de 2027; pedidos reales creados y pagados por las personas (`ORD-AB0806B2`, `ORD-1818C2AF`), una devolución parcial (`RET-3C6E604F`), una venta de mostrador (`POS-C04B073D`) y un corte de caja (`CUT-2B3D81B9`) |

### Las tres conclusiones que cambiarían el producto

**1. Un tercio de la ronda ya estaba escrito y nadie podía verlo.** De las 39 propuestas, **12 ya estaban construidas —total o parcialmente— y solo faltaba enseñarlas o encender la última línea** (§2). El caso más caro: el mensaje *"estamos confirmando tu pago"* llevaba escrito desde la ronda 5 y nunca se encendía porque faltaba mandar una URL de retorno. El segundo: el correo de CLABE ya distinguía activación de comisión confirmada; el aviso del portal, que es el que la gente ve, escribía siempre el mismo texto falso. **Antes de construir, mirar.** La validación previa costó una sesión de lectura y ahorró rescribir ocho piezas que ya funcionaban.

**2. El informe se equivocó dos veces en el diagnóstico, y una de ellas habría roto el producto.** La [25] afirmaba que la CLABE fallaba porque *"el navegador nunca mandó nada al servidor"* —cierto— y deducía que el formulario estaba roto —falso—: el `POST` vivía detrás de un botón "Confirmar" de un modal que se cerraba con un clic al fondo, en silencio. Y la propuesta 31 pedía cotizar el envío **con CP + estado**, *"que es lo que el backend necesita"*; el backend devuelve **400 si le mandas el estado**. Implementar la propuesta como estaba redactada habría apagado la cotización de envíos de todo el producto. Un síntoma medido no es una causa (§2.2).

**3. Los permisos de la ronda eran decorativos, y no por culpa de la ronda.** El paquete E construyó un privilegio nuevo, guardas por pantalla y menús recortados por puesto. Las revisoras comprobaron que **cualquiera podía abrir el CSV del banco con la CLABE completa de cada socia mandando el encabezado `x-user-role: admin`, sin credencial ninguna**, porque todo empleado nacía con `role: admin` y `_extract_actor` confiaba en encabezados que el cliente escribe. El defecto era anterior a esta ronda; lo que la ronda hizo fue construir encima de él. Corregido en `13a44ed`, con `tests/test_encabezados_forjados.py` para que no vuelva.

### 1.1 Las 39 propuestas, una por una

Columna **Commits**: el primero es el commit del paquete en su worktree (el merge está en `git log --merges`); las correcciones posteriores (`bea2355` integración, `13a44ed` y `7fdacff` correcciones) se citan cuando tocan esa propuesta. Columna **Tamaño**: archivos y líneas de los commits citados; un commit que sirve a dos propuestas cuenta para las dos, así que la columna **no suma** el total de la ronda (160 archivos, +14,358 / −1,293).

| # | Propuesta ([25] §7) | Paq. | Estado | Commits | Tamaño | Qué quedó |
|---|---|---|---|---|---|---|
| 1 | Que "Guardar CLABE" guarde | A | **Implementada** | `6e9780b`, `bea2355` | 10 arch · +392/−218 | Desaparece el paso de confirmación; un solo `ui-clabe-form` para panel, Mi perfil y la ficha del back office; estado en el propio campo (*guardando… / guardada, termina en 6789 / no se pudo guardar: motivo*); `handle_update_clabe` acepta cadena vacía para borrar (antes 400). No se tocó `ui-modal` |
| 2 | Separar los dos textos del aviso de CLABE | A | **Implementada** | `7814f50`, `aa97bb0` | 5 arch · +121/−18 | `_aviso_panel_clabe(cliente, mes, motivo)` escribe el texto que corresponde, como ya hacía el correo; id `NTF-CLABE-<cliente>-<mes>-<motivo>` (activación caduca a 30 días, comisión a 45); el plan y el correo de bienvenida dejan de contradecirlo |
| 3 | Contacto fuera del bloque de envío | C | **Implementada** | `19d8a64`, `717c5b3` | 3 arch · +232/−62 | Bloque propio `#contacto-pedido` siempre visible, error pintado en el campo y foco al primero que falta; el `payload` de recolección también manda nombre y teléfono |
| 4 | Comisiones en el menú y URL por pantalla | E | **Implementada** | `22b9ec8`, `373ab27`, `f706094` | 8 arch · +521/−122 | 15 rutas explícitas del back office con `data.view`, `adminGuard` y `adminViewGuard`; menú escrito una sola vez con FINANZAS → Comisiones y pagos y las tres pantallas que tenían ruta y no menú; pestaña y mes en la URL |
| 5 | Abrir turno con fondo declarado | F | **Implementada** | `97cb26b`, `04b09e3` | 10 arch · +522/−9 | `POST /inventory/pos/turno/abrir` con movimiento de apertura; `calcular_arqueo` prefiere la apertura sobre el corte anterior y publica `openingSource`; sin ninguno de los dos, campo editable con su explicación |
| 6 | Validar el código de autorización al salir del paso 3 | F | **Implementada** | `c0b7293`, `04b09e3` | 9 arch · +384/−14 | Tres estados: *no hay código configurado* (409, con la salida honesta de dejar todo como fondo), *incorrecto* (403) y *correcto*; el arqueo publica `authCodeConfigured` sin enseñar la clave |
| 7 | Que el recibo repita lo elegido | C | **Implementada** | `bb2bf50`, `356e869`, `29107a9` | 8 arch · +425/−27 | Productos con precios, sucursal de recolección con dirección, datos fiscales, fecha legible y desglose de IVA, en pantalla y en las dos versiones del correo; la línea de tiempo mira `deliveryType` |
| 8 | Pie de página, ayuda, contacto y sucursales | D | **Implementada** | `6c9d324`, `3f7b26c`, `0491bf8` | 29 arch · +1,207/−29 | Bloque `contacto` en configuración y `GET /catalog/ayuda` público; `#/ayuda`, `#/contacto`, `#/sucursales`, `#/facturacion`, `#/devoluciones`; pie con correo, WhatsApp, horario y año calculado, montado en las seis pantallas donde faltaba; comodín `**` a `#/ayuda` |
| 9 | Aviso de privacidad honesto y sin bloquear | G | **Implementada** | `f39550c` | 5 arch · +127/−69 | De modal a pantalla completa a banner inferior con "Entendido", "Leer el aviso" y una X, conservando la clave de aceptación; el texto de modo cliente deja de negar que se pidan datos fiscales; ARCO apunta a `#/contacto` |
| 10 | Patrón de cantidad del producto destacado en la tarjeta | C | **Implementada** | `34e73a5`, `131e428` | 4 arch · +57/−48 | Borrador local en `ui-product-card`: el carrito solo se toca al pulsar "Agregar"; se elimina la salida `qtyChange` y su único consumidor |
| 11 | Plantilla "activa" y ruta falsa de la CLABE | G | **Implementada** | `6dd1acd` | 6 arch · +188/−7 | Plantilla `activa` escrita, respaldo a `'fria'` eliminado, ruta corregida a `#/perfil`; prueba de invariante: toda situación tiene plantilla |
| 12 | Resolver el id a nombre en la bitácora | G | **Implementada** | `6dd1acd`, `13a44ed` | 6 arch · +188/−7 | `firmar_nota()` guarda `byName` **al escribir**, nunca al leer, en las tres puertas; tras el hallazgo de las revisoras, el nombre sale de la sesión y no del encabezado `x-user-name` |
| 13 | "Estamos confirmando tu pago" | C | **Implementada** | `f70e24b` | 2 arch · +104/−20 | El mensaje ya existía y no se encendía por falta de `successUrl`: ahora se manda desde el cuerpo; sondeo 5 s → 10 s → 20 s → 30 s con corte al llegar a pagado |
| 14 | Borrar el "más o menos $1,000" de la activación | B | **Implementada** | `c47bcd7`, `c43f9b9` | 14 arch · +1,080/−34 | `activacion.pesosAprox` **borrado** del contrato (no deprecado) y sustituido por `rango = {min, max, notaProducto}`, resuelto por tramos: **$933.33 – $1,604.94** con la semilla real; los ejemplos de generación usan el neto de la canasta más barata que activa (2 × Klinhart, $960 → gen 1 = $96) |
| 15 | Arreglar el botón "Ver" y dar URL al pedido | E | **Implementada** | `81c4ba4`, `f706094` | 2 arch · +142/−23 | Las cuatro causas: `aria-label` por fila, la pestaña "Por devolver" (única cadena con "ver") pasa a "Devolución en curso", `setOrderStatus()` deja de borrar el buscador, y la tira de pestañas sale de la plantilla a un campo con `trackBy` (la app es zoneless); `#/admin/pedido/:id` con botón de copiar |
| 16 | Recalcular el mes contable al ligar un invitado | G | **Implementada** | `0eee4fd` | 2 arch · +211/−4 | El paso 1 de `handle_apply_rewards` (volumen, VP, activación, reevaluación de bloqueadas) corre al ligar, nunca el paso 2; idempotente por `rewardsAppliedAt`, escrito antes de sumar; cubre las dos puertas |
| 17 | Que el servidor mande la lista de periodos | A | **Implementada** | `507c2d0`, `58f60f9` | 16 arch · +1,111/−69 | `GET /commissions/periodos` (meses con datos, `defaultMonth`, `payoutDay`, `serverNow`) en su propio endpoint; lo consumen Pagos del mes, Estadísticas y el exportador, que bajaba los datos de otro mes |
| 18 | "Por confirmar" y "Bloqueadas" en Pagos del mes | A | **Implementada** | `507c2d0`, `58f60f9` | 16 arch · +1,111/−69 | `estado_pagos` deja de descartar a quien tiene 0 confirmados y publica `confirmado`, `porConfirmar`, `bloqueado`, `reconocido` y el pedido que frena cada importe con sus días; el CSV del banco y el lote siguen siendo solo de las `listo` |
| 19 | Guardar la dirección con `saveShippingAddress` | G | **Implementada** | `2d1f622`, `13a44ed` | 3 arch · +268/−6 | `handle_create_order` la escribe con **un solo** `_update_by_id`, deduplicando por calle+número+CP y sin guardar la sucursal en recolección; corregida la condición anidada que era el único camino de escritura; la suscripción deja capturar una dirección ahí mismo |
| 20 | Pestaña "Factura solicitada" en Pedidos | E (contrato G) | **Implementada** | `f783731`, `81c4ba4`, `13a44ed` | 3 arch · +158/−23 | Filtrando **en memoria** sobre los pedidos ya cargados (el filtro del servidor rompería `loadedSections`), con su contador en Acciones urgentes |
| 21 | Antigüedad de los pedidos pagados sin envío | F + E | **Implementada** | `d6d875d`, `bea2355` | 3 arch · +145/−7 | `get_admin_warnings` separa las recolecciones del contador de envíos, dice los días y publica `serverNow`/`agingRedDays`; la columna ordenable y en rojo vive en la vista Pedidos, que es de E, y se montó en la integración |
| 22 | Buscador en la tienda y ruta por producto | C | **Implementada** | `c2b5d51` | 3 arch · +125/−4 | Filtro sobre nombre + etiquetas + descripción con acentos normalizados ("colageno" encuentra "Colágeno"); ruta `tienda/producto/:id` declarada **antes** de `tienda/:refToken` para no perder la atribución; botón de copiar enlace |
| 23 | Enlazar `#/modo-socio` donde nacen las dudas | B | **Implementada** | `8caa198`, `c43f9b9` | 8 arch · +508/−17 | Anclas `id` en las ocho secciones y desplazamiento al fragmento dentro del componente (el plan llega después del GET); "Cómo se calculan" cae en `#generaciones`; el "13 PC" de la tarjeta pasa de `title` invisible a enlace |
| 24 | Botón "Devolver / Llegó dañado" siempre visible | D | **Implementada** | `8854871`, `461c853` | 13 arch · +534/−44 | `GET /orders/{id}` devuelve `devolucion: {puedeSolicitar, motivo, horasRestantes, plazoTexto, motivos}` desde el mismo `_motivos_devolucion()` con que el servidor valida; el invitado sin sesión también lo recibe; "Cancelar orden" menciona la devolución parcial |
| 25 | Vocabulario único de estados y métodos | G | **Implementada** | `f66ac1d`, `f39550c`, `0c0a522`, `bea2355` | 10 arch · +541/−75 | `vocabulario.py` y `models/vocabulario.model.ts` con los mismos textos palabra por palabra y una prueba que se cae si divergen; sin género, con el matiz de recolección y `mixed` desglosado; aplicado en insignias, pestañas, POS, corte y Estadísticas |
| 26 | Rango de fechas en la conciliación | G | **Implementada** | `62343e2`, `7fdacff` | 5 arch · +240/−24 | 72 h · 7 días · 30 días · 90 días · desde una fecha, traducida a horas por el servidor; `startedAt`/`finishedAt` del servidor dejan de pisarse con `new Date()`; corrida por lotes con `pending`/`hasMore` |
| 27 | Recortar menú y acciones por rol, y mostrar el puesto | E | **Implementada** | `9336c04`, `96b3d76` | 8 arch · +199/−15 | `access_screen_campaigns` (único privilegio nuevo de la ronda), `jobTitle` en alta, PATCH y login, la insignia dice "Caja"/"Almacén"/"Coach" y no ADMIN, el alta de bodega se oculta sin `stock_create`; `role` no cambia |
| 28 | Stocks: tabla producto × sucursal, mínimos y bitácora | F | **Implementada** | `caa2f79`, `00d3373`, `c3d5af0` | 9 arch · +562/−9 | Tabla calculada del estado que la pantalla ya tenía (cero consultas nuevas); `GET\|PUT /inventory/stocks/minimos` con `stocks.minStockDefault`, celda en rojo y aviso sin N+1; la bitácora que la tarjeta prometía por fin se enlaza; el alta de bodega, detrás de un botón |
| 29 | Un solo origen del corte de mes | G | **Implementada** | `0bf674b`, `bea2355`, `13a44ed` | 8 arch · +298/−70 | `corte_mes.py` es el único sitio donde vive el día del corte y publica `cutoffAt`, `serverNow` y `cutoffLabel`; se borran la copia del componente y el respaldo del carrito; con y sin sesión sale la misma fecha |
| 30 | Mandar el resumen de turno al gerente | F | **Implementada** | `f6aa095`, `21f5963` | 9 arch · +364/−8 | `POST /inventory/turno/resumen/enviar` calcado de `handle_enviar_corte`, reusando el texto que el GET ya arma, con sello `notifiedTo`/`notifiedAt` e idempotencia por persona y día |
| 31 | Cotizar el envío con el CP | C | **Implementada (premisa corregida)** | `19d8a64`, `717c5b3` | 3 arch · +232/−62 | Se quitó la guardia que exigía la dirección completa y se cotiza con `zipTo` + bultos y nada más, con 600 ms de espera al teclear. **La propuesta pedía CP + estado y el backend devuelve 400 si le mandas el estado** (§2.2); el rótulo se llama "Subtotal" hasta que hay envío |
| 32 | Conservar el `createdAt` de la comisión | A | **Implementada** | `1084906`, `58f60f9` | 12 arch · +698/−59 | `_write_row` conserva el `createdAt` anterior y añade `orderCreatedAt`, `recalculatedAt` y `recalculatedReason`; `core/ledger.py` ordena por la fecha del pedido y desempata por `rowId`. **Ni un importe se movió** |
| 33 | Aterrizar en la pantalla de cada rol | E | **Implementada** | `0ec66c5`, `1267809` | 4 arch · +80/−14 | `landingRouteFor()` devuelve una ruta por privilegio, con caída a la primera pantalla permitida y un aviso que dice cuál se quiso abrir; Pedidos abre en la primera pestaña con trabajo; el buscador cruza estados |
| 34 | Correo el día 10, siempre | A | **Implementada** (tarea programada; EventBridge sigue sin desplegar) | `507c2d0`, `1084906` | 10 arch · +955/−20 | `POST /commissions/pagos/dia-de-pago` en `TAREAS_PROGRAMADAS`, una sola vez por beneficiaria y mes, respetando `doNotContact`: *"Te depositamos $135.00 a tu CLABE terminación 6789"* o *"No te pudimos depositar: nos falta tu CLABE"*. Nunca se avisa un depósito sin comprobante. Más el correo de desbloqueo |
| 35 | Exportar a quienes sí tienen CLABE y listar aparte | A | **Implementada** | `507c2d0`, `58f60f9`, `13a44ed` | 16 arch · +1,111/−69 | `GET /commissions/pagos/pendientes.csv` como **segundo archivo** (nunca filas más en el layout del banco, §3.13) y el botón apagado dice el número: *"No hay socias listas para depositar este mes · 1 espera CLABE ($135.00)"* |
| 36 | Publicar ganancias reales y un simulador | B | **Implementada** (decisión de negocio del dueño) | `c47bcd7`, `c43f9b9`, `7fdacff` | 14 arch · +1,080/−34 | `POST /catalog/plan/simular` (pública, sin escritura) y `plan-simulador` en `#/modo-socio#simulador`: muestra siempre la ganancia **neta**, también negativa, con el aviso fijo de que es una calculadora y no una promesa de ingresos, y sin extrapolar |
| 37 | Sobre qué base se calcula la comisión | B | **Implementada** (decisión de negocio del dueño) | `1b0430d`, `58f60f9`, `bea2355` | 17 arch · +874/−54 | Un solo texto en `impuestos.py` y su gemelo de TypeScript: *"10 % de $1,350.00 netos, sin envío = $135.00"*, con `rewards.commissionBase` como interruptor nunca retroactivo; colocado en la página del plan, el simulador, la fila de la comisión, el correo y Pagos del mes |
| 38 | Retención de impuestos y monto mínimo de depósito | B | **Parcial** (decisión de negocio del dueño: IVA sí, retención no) | `1b0430d`, `d4977c7`, `bb2bf50`, `13a44ed` | 16 arch · +942/−19 | El dueño resolvió la mitad fiscal con **IVA 16 % configurable y desglosado**: bloque `taxes`, `impuestos.py`, `ui-desglose-iva`, `vatRate`/`taxBase`/`taxAmount` en el pedido y montaje en carrito, recibo, correo, back office, POS y corte. **La retención de ISR/IVA de la comisión y el monto mínimo de depósito siguen sin existir y sin publicarse**, y Gerardo Lomelí los fue a buscar y no los encontró (§5.2) |
| 39 | Quién paga el envío de regreso de una devolución | D | **Implementada** (decisión de negocio del dueño) | `6c9d324`, `461c853`, `da06eda`, `1cac96a` | 14 arch · +859/−25 | `RETURN_MOTIVOS` se muda a `returns.motivos` con valores por omisión idénticos (48 h / 48 h / 7 días) y validación al guardar; `ayuda_handlers.texto_politica()` es la **única** fuente del proceso en seis puntos, leída sin reescribir en `#/devoluciones`, en el asistente y en los dos correos; la solicitud ya creada conserva su `refundPolicy` |

---

## 2. Lo que la validación encontró antes de escribir código

Es el dato más útil de la ronda y el que cambia cómo conviene trabajar la siguiente.

Antes de abrir un solo worktree, tres validadoras leyeron las 39 propuestas **contra el código de esta misma rama**, con el backend de simulación vivo en `http://localhost:4400` (reloj del mundo en `2027-04-10T13:15:37Z`) y las capturas del arnés como evidencia de pantalla. No modificaron ningún archivo: solo leyeron, reprodujeron con `curl` y con las capturas, y dictaminaron. El resultado está en [arquitectura/26](../arquitectura/26-treinta-y-nueve-propuestas.md) §0.6.

### 2.1 Las tres categorías

| Categoría | Cuántas | Cuáles |
|---|---|---|
| **Ya existía, total o parcialmente: solo estaba escondida o apagada** | **12** | 2, 10, 13, 14, 20, 22, 23, 28 (la bitácora), 30, 35, 37, 39 |
| **Defecto: había código escrito que no hacía lo que decía** | **13** | 1, 6, 9, 11, 15, 16, 17, 19, 24, 26, 29, 31, 32 |
| **Por construir de cero** | **14** | 3, 4, 5, 7, 8, 12, 18, 21, 25, 27, 33, 34, 36, 38 |

**Casi dos terceras partes de la ronda (25 de 39) no eran producto nuevo.** Eran producto escrito que no se veía, o producto escrito que mentía.

### 2.2 Lo que ya existía y solo faltaba enseñar

| Prop. | Lo que ya estaba escrito | Lo único que faltaba |
|---|---|---|
| 2 | Los dos textos separados, en el **correo** (`pagos_handlers._correo_clabe`), y el interruptor `clabeReminderOnActivation` con su prueba | Pasarle el motivo al aviso del **portal**, que escribía siempre el mismo texto *hard-coded*. Es lo que Ximena y Fabiola vieron con $0.00 |
| 10 | El patrón de borrador local, escrito para el producto destacado (`heroQtyDraft`) | Aplicarlo a la tarjeta del catálogo |
| 13 | El mensaje *"estamos confirmando tu pago"*, completo | `payments.mercadoLibre.successUrl`. Sin URL de retorno, el mensaje **nunca se encendía** |
| 14 | El rango honesto con canastas reales ($1,120 activa / $1,170 no), calculado y pintado | Borrar el titular `pesosAprox` de $1,000 que lo contradecía en la misma página |
| 20 | El filtro del servidor, la insignia en la fila y el bloque para marcar la factura emitida | La pestaña, el contador, y que el botón "Ver" funcionara (propuesta 15) |
| 22 | El enlace profundo `#/tienda?p=<id>` y el `scrollIntoView` de "Ver producto" | El buscador, la ruta bonita y el botón que da el enlace |
| 23 | El enlace del correo de bienvenida y el `routerLink` a `/modo-socio`, que **sí navegaba** | Las anclas a la sección, y enlazar desde la tarjeta y desde las metas |
| 28 | La bitácora de movimientos que la propia tarjeta de Stocks anunciaba | Enlazarla desde la tarjeta que la anuncia (y corregir "bitacora" → "bitácora") |
| 30 | `GET /inventory/turno/resumen` devolvía el texto ya armado; la pantalla lo copiaba a mano | El canal: un `POST .../enviar` calcado de `handle_enviar_corte` |
| 35 | El CSV ya saltaba a las socias sin CLABE y exportaba al resto | El anexo de pendientes y que el motivo del botón apagado dijera el número |
| 37 | El motor **ya** calcula sobre el neto sin envío ($135 sobre $1,350) | Escribirlo. En ningún lado del producto estaba dicho |
| 39 | Plazos, responsable del envío de regreso y evidencia por motivo, aplicados y escritos en el asistente y en los correos | Que fueran configurables y que se publicaran **antes** de comprar |

### 2.3 Las dos veces que el informe se equivocó de causa

Esto es lo que justifica que la validación sea un paso obligatorio y no un lujo.

**Propuesta 1 · la CLABE.** [25] §3.1 concluía que el formulario estaba roto y que el modal aparecía *"pintado al final de una página kilométrica"*. La validación reprodujo el síntoma —en `sim/servidor.log`, desde la línea 2118 (primer `OPTIONS` de CORS) no hay **ni un** `OPTIONS` ni un `POST /customers/clabe`— y desmontó la causa:

- el `[(ngModel)]` funciona, `openClabeConfirm()` valida los 18 dígitos y abre el modal, y la captura `sim/capturas/fabiola-11-clabe-segundo-intento.png` muestra el diálogo **centrado y a pantalla completa** (`ui-modal` es `fixed inset-0 z-50`);
- el defecto real es el **segundo paso**: "Guardar" solo abre una confirmación, el `POST` vive detrás de "Confirmar" y ninguna de las dos personas lo pulsó nunca;
- el agravante que explica los "cero mensajes": el modal se cierra con clic al fondo y con Escape, **descartando la CLABE en silencio**, y detrás sigue leyéndose *"CLABE registrada: No registrada"* — que es exactamente lo que Fabiola reportó (*"Le di Guardar y sigue diciendo No registrada"*, `fabiola-2027-03-04.md`);
- y de paso corrigió dos agravantes del informe: **sí** hay verificación de identidad (con el token de Paulina, escribir la CLABE de Fabiola devuelve 403 *"solo puedes actualizar tu propia CLABE"*), pero **no** se podía borrar (400 con cadena vacía).

Si se hubiera implementado la propuesta como estaba redactada —"el formulario no manda nada, arréglalo"— se habría reescrito un formulario que funcionaba y el `POST` habría seguido detrás del mismo botón.

**Propuesta 31 · el envío.** El informe pedía cotizar **con CP + estado**, *"que es lo que el backend necesita"*. La validación probó el endpoint: `POST /shipping/quote {"zipTo":"03100"}` devuelve **200 con tarifas**, y añadirle `state` devuelve **400**. El cotizador exige todos los campos de dirección o ninguno. **Implementar la propuesta como estaba escrita habría apagado la cotización de envíos de todo el producto**; lo que había que quitar era la guardia que exigía la dirección completa antes de cotizar.

### 2.4 Qué se lleva la próxima ronda

1. **Una sesión de lectura antes de repartir el trabajo paga su costo dos veces**: evitó rescribir 12 piezas y evitó una regresión que habría dejado sin cotización de envíos a todo el producto.
2. **Un síntoma medido no es una causa.** Las doce personas de la [25] describieron lo que vieron con precisión; las causas que el informe dedujo de eso fallaron en 2 de 39. La medida sigue siendo buena; la deducción necesita el código delante.
3. **El producto tiene más funcionalidad de la que enseña.** La conclusión 2 de la [25] —*"lo que la ronda 5 construyó funciona y casi nadie lo encuentra"*— se confirmó en el código, no solo en los diarios: 12 de 39 propuestas eran arquitectura de información, no desarrollo.

---

## 3. Arquitectura y decisiones

Resumen de [arquitectura/26](../arquitectura/26-treinta-y-nueve-propuestas.md) (`76165c5`, 665 líneas). Idea central, heredada de la ronda 5 y endurecida: **siete agentes trabajan a la vez sobre la misma base, así que cada archivo tiene un dueño y solo uno**, y los cuatro monolitos compartidos (`admin.component.{ts,html}`, `order_lambda.py`, `customer_lambda.py`, `real-api.service.ts`) se reparten **por regiones con ancla nombrada** —el nombre de la función o del bloque de plantilla, nunca el número de línea, porque las líneas se mueven con cada edición—. Si un paquete necesita una región ajena, **no la toca**: la pide, y la delegación queda escrita (hubo exactamente una: la propuesta 20 → E).

### 3.1 Los siete paquetes

| Paquete | Propuestas | Rutas nuevas | Pruebas nuevas | Lo que estrena |
|---|---|---|---|---|
| **A** `clabe-comisiones-pagos` | 1, 2, 17, 18, 32, 34, 35 | 3 | 30 | `ui-clabe-form` único, `GET /commissions/periodos`, las tres cifras del mes, `pendientes.csv`, la tarea del día de pago |
| **B** `plan-simulador-iva` | 14, 23, 36, 37, 38 | 1 | 45 | `impuestos.py`, `ui-desglose-iva`, `POST /catalog/plan/simular`, `plan-simulador`, el rango honesto de activación |
| **C** `checkout-y-tienda` | 3, 7, 10, 13, 22, 31 | 0 | 7 | Bloque de contacto propio, cotización solo con CP, buscador y ruta por producto, recibo que repite lo elegido |
| **D** `devoluciones-y-ayuda` | 8, 24, 39 | 1 | 26 | `ayuda_handlers.py`, cinco pantallas públicas, `ui-footer` completo, `ui-devolucion-boton`, la política en configuración |
| **E** `navegacion-y-roles` | 4, 15, 27, 33 (+20 por delegación) | 0 | 7 | 15 rutas del back office, `adminViewGuard`, menú por puesto, `access_screen_campaigns`, aterrizaje por rol |
| **F** `caja-almacen-stocks` | 5, 6, 21, 28, 30 | 3 | 18 | Apertura de turno, tres estados del código de autorización, tabla producto × sucursal con mínimos, envío del resumen |
| **G** `coherencia-y-datos` | 9, 11, 12, 16, 19, 20, 25, 26, 29 | 0 | 49 | `vocabulario.py` + su gemelo de TypeScript, `corte_mes.py`, banner de privacidad, reacreditación del invitado, conciliación con rango |

Convenciones que sostuvieron la ronda: extensiones en cascada en el backend (`*_handlers.py` con `atender()`); un servicio por tema en el frontend; los archivos de configuración diminutos y compartidos (`core/config.py`, `app.routes.ts`, `openapi-aws.yaml`, `app.config.ts`) reciben **un bloque al final por paquete**, con el comentario `# ── Paquete X · ronda 26 ──`; los módulos auxiliares que otros importan (`impuestos.py`, `vocabulario.py`) son de **lectura** para el resto; **nada nuevo cuelga de `ORDER_PAID`**, que está en 37 de 40 GetItem con tres de holgura.

### 3.2 Las cuatro decisiones de negocio del dueño, ya aplicadas

Estas son las cuatro preguntas de [25] §7.3 que la ronda 6 dejó abiertas porque no eran de ingeniería. El dueño las contestó y así quedaron en el producto.

**36 · El simulador se publica, y nunca promete.** `POST /catalog/plan/simular` es una calculadora pública sin escritura. Se le capturan cuatro cosas —personas directas, cuánto paga cada una, cuánto compras tú, cuántas generaciones— y devuelve, con la configuración vigente y no con ejemplos: el tramo de descuento, el neto pagado, los VP, si activa o no, la comisión por generación **con el requisito cumplido o no y por qué, con el número que falta**, el gasto propio y la **ganancia neta**, que se muestra siempre, también en rojo. Lleva el aviso fijo *"Esto es una calculadora con las reglas del plan, no una promesa de ingresos"* y no extrapola. Con el caso honesto de Ximena (2 personas × $1,000, compra propia $1,120) da comisión $200, pago propio $1,008 y **resultado −$808**, dicho con esas palabras. *Porqué:* publicar cifras de ganancia es materia regulatoria en México, y la persona que vino a decidir si esto es un negocio necesita el número honesto, no el ejemplo bonito. La prueba de que funcionó está en el diario de Valeria, que ni siquiera quería vender: *"su propia calculadora me enseñó un resultado en rojo, «TU RESULTADO DEL MES: -$933.00». Eso me subió el respeto por la marca"* (`valeria-nunez-2027-05-04.md`).

**37 · La comisión se paga sobre el neto, y se dice en todas partes.** La base sigue siendo el **neto pagado por producto, con IVA incluido y sin envío** —que es lo que el motor hace hoy: $135 sobre $1,350—. No se cambió: pasar a "neto sin IVA" bajaría **toda** comisión un 13.79 % y tocaría importes ya confirmados y pagados. Queda el interruptor `rewards.commissionBase = "neto_con_iva" | "neto_sin_iva"`, por omisión el actual y **nunca retroactivo**. Lo nuevo es que ahora está **escrito**, con una sola función (`impuestos.texto_base_comision`) y su gemela de TypeScript, en cinco sitios: la página del plan, el simulador, la fila de cada comisión del panel, el correo de comisión y Pagos del mes. Ningún paquete escribe su propia versión del texto: `pagos_handlers` llevaba una copia de respaldo mientras B publicaba el contrato, y la integración la borró (`bea2355`).

**38 · IVA 16 %, configurable y desglosado.** Bloque `taxes` nuevo (`vatRate 0.16`, `pricesIncludeVat`, `appliesToShipping`, `label`) y helper puro `impuestos.py` con el supuesto escrito en su docstring. Cuatro decisiones dentro:

- **Base gravable: todo lo que se cobra, envío incluido** (`taxes.appliesToShipping = True`), no el subtotal de producto. Así `base + IVA == total`, que es el número que la persona compara con su estado de cuenta.
- **Redondeo: dos decimales, mitad arriba, una sola vez y al final del pedido.** `base = redondear(total / 1.16)`, `iva = total − base`, **nunca por línea**: redondear por línea y sumar es el error que ya produjo el descuadre del Cuadro de Honor. Hay prueba de ello.
- **El IVA no cambia ni un importe cobrado.** Es desglose de un total que ya lo incluía, jamás un cargo nuevo. Los pedidos anteriores **no se migran** (su recibo se desglosa al vuelo); los nuevos guardan `vatRate`/`taxBase`/`taxAmount` para que un cambio futuro de tasa no reescriba la historia.
- **La tasa viaja en `GET /config/public`** para que ninguna pantalla escriba `0.16`.

El componente `ui-desglose-iva` tiene API fija —*Subtotal sin IVA · IVA 16 % · Total*, en ese orden y con esas palabras— y quedó montado en el carrito, el recibo, el correo de pago, el detalle del back office, el bloque de facturación, el resumen de venta del POS y el comprobante del corte. **La otra mitad de la propuesta 38 —retención de ISR/IVA sobre la comisión y monto mínimo de depósito— el dueño la dejó sin resolver**, y por eso la propuesta figura como parcial en §1.1: hoy se paga el bruto el día 10 y no hay una sola pantalla que lo diga (§6).

**39 · El socio paga el envío de regreso, salvo cuando el problema es nuestro, y el proceso se publica.** `RETURN_MOTIVOS` se muda a `returns.motivos` en configuración con valores por omisión **idénticos a los de hoy** (48 h "llegó dañado", 48 h "me llegó algo distinto", 7 días "cambié de opinión"; empresa, empresa, cliente), más `returns.direccionDevolucion` e `inspeccionDiasHabiles`, con validación al guardar: `validar_returns` rechaza el bloque entero con 400 y su motivo si una sola clave está mal, y la lectura cae a los valores por omisión, así que **una configuración rota nunca deja al cliente sin regla**. `ayuda_handlers.texto_politica(cfg)` es la **única** fuente del proceso en seis puntos —qué se puede devolver, en qué plazo, qué evidencia, **quién paga el envío de regreso**, a dónde se manda y cuándo y por qué medio llega el reembolso— y se lee sin reescribir en `#/devoluciones`, en el asistente, en el correo de entrega y en el de solicitud recibida, en HTML y en texto plano. La configuración **nunca es retroactiva**: la solicitud ya creada conserva su `refundPolicy`.

### 3.3 Las otras decisiones que cambian lo que ve la gente

- **La CLABE se guarda directo y se puede borrar**; **no se toca `ui-modal`**, porque cambiar `closeOnBackdrop` afectaría a todos los modales del producto (arqueo, avisos, lote de pagos).
- **El recordatorio de CLABE al activarse no se apaga: se corrige su texto y el del plan.** Pedirla al activarse es operativamente correcto —el día 10 no da tiempo de conseguirla—; prometer dinero que no existe, no.
- **`activacion.pesosAprox` se borra, no se deja deprecado.** Un campo que miente y sigue publicado se vuelve a pintar en la siguiente pantalla.
- **El fondo de caja: gana la apertura del turno vigente** sobre el `cashToKeep` del corte anterior; si no hay ninguno, el campo es editable y la pantalla lo explica.
- **El código de autorización del POS distingue tres estados**, porque hoy `auth-config` responde `configured:false` y cualquier código habría dado 403.
- **La propuesta 35 no fuerza exportar con cero filas**: un archivo con solo cabecera es peor que no exportar; las pendientes salen en un segundo archivo.
- **Un solo privilegio nuevo**, `access_screen_campaigns`, sembrado para superadmin, `role admin` y quien tenga `config_manage`.
- **La ruta comodín `**` va a `#/ayuda`**, no a la tienda ni a `''` (que monta el panel del cliente sin guarda).
- **Género neutro en pantalla y en correos** ("Entregado", "Pagado", "Hola, {nombre}"); se conserva socia/socio solo donde el texto habla del rol declarado.
- **El ticket del POS para el cliente queda fuera de la ronda**: no lo pide ninguna de las 39, y meterlo de contrabando dentro de la 38 pondría en riesgo el corte de caja, que es de lo mejor calificado del producto. Reapareció en la sesión con personas (§6).

### 3.4 La integración

Los siete worktrees se juntaron en `bea2355`. Los conflictos reales fueron pocos y todos de líneas adyacentes o de orden:

- **`app.routes.ts`**: el bloque del back office de E tenía que quedar **antes** del comodín `**` de D, que es la última entrada del arreglo. Si no, ninguna ruta de E resolvía.
- **`core/order_emails.py`, rama `delivered`**: conviven las dos intenciones, el matiz de recolección de C (propuesta 7) y la política leída de configuración de D (propuesta 39), en una sola redacción.
- **`openapi-aws.yaml`**: los bloques de A, D y F conviven, cada uno con su integración y su `OPTIONS`; 91 rutas, YAML validado.
- **`admin.component.html`, bloque "Alta de stock"**: se conservan la guarda `*ngIf="hasPermission('stock_create')"` de E **y** el plegado detrás del botón de F.

Y la integración cerró **los pendientes que cada paquete había dejado atados por no invadir región ajena**: montar `ui-desglose-iva` en las seis pantallas de otros dueños, el vocabulario único en las pestañas y en el POS, la columna de antigüedad en Pedidos, el tercer formulario de CLABE de la ficha, el borrado del respaldo del corte en el carrito, y en el backend el privilegio real de Campañas, la conservación de `minStock` al guardar un producto y el `cutoffAt`/`serverNow` en los dos endpoints que faltaban. Diez pruebas nuevas en `tests/test_integracion_ronda26.py` fijan cada uno con su síntoma.

---

## 4. Lo que encontraron las revisoras y qué se corrigió

Sobre el árbol ya integrado (`bea2355`), tres revisoras leyeron el diff y probaron el producto en vivo contra `:4400`. Levantaron **24 hallazgos**. Los 24 se reprodujeron y los 24 se corrigieron en `13a44ed`; **ninguno se descartó**. La suite pasó de 584 a 601 pruebas, con `tests/test_encabezados_forjados.py` entre las nuevas.

### 4.1 Las tres críticas: los permisos de la ronda eran decorativos

Las tres son defectos **anteriores** a esta ronda, pero es lo que vuelve decorativo todo el trabajo de permisos que la ronda acababa de construir, así que no se podía dar por buena la revisión sin decirlo.

| # | Hallazgo | Cómo se reprodujo | Qué se hizo |
|---|---|---|---|
| 1 | **Las rutas nuevas se abren con el encabezado `x-user-role` forjado, sin credencial ninguna.** `core/security.py:98` `_extract_actor` caía a los encabezados legacy `x-user-id` / `x-user-role` / `x-user-privileges` cuando no había Bearer, y `openapi-aws.yaml` declaraba el esquema como un `apiKey` en `x-user-id`, sin autorizador. El cliente decidía su propio rol y sus propios privilegios | `curl -H 'x-user-role: admin' localhost:4400/commissions/pagos/dispersion.csv?month=2027-04` → **200 con el layout del banco y la CLABE COMPLETA de cada socia**, la que el propio código promete que *"en pantalla siempre va enmascarada"*. Y `POST /inventory/turno/resumen/enviar` con el mismo encabezado manda el correo del turno **al destinatario que se le indique**, las veces que se quiera | `_extract_actor` solo confía en esos encabezados si el despliegue lo declara con `TRUST_ACTOR_HEADERS`, que nadie define y que está documentada en `.env.example`. La suite los sigue usando como atajo de identidad, así que `conftest` la enciende en `pytest_configure` —**no al importar el módulo**, porque `sim/servidor.py` importa `conftest` y encenderlo ahí habría reabierto el agujero en el mundo simulado—. `test_encabezados_forjados.py` la apaga y mide lo que hace un despliegue de verdad. Verificado en vivo: los tres `curl` responden **403** |
| 2 | **Todo empleado iniciaba sesión con `role: "admin"`.** `auth_utils.handle_employees` creaba el registro AUTH de cualquier empleado como admin, y `_require_admin` da acceso total a `role == 'admin'` y solo aplica los privilegios cuando el rol es `employee`. Los cinco empleados sembrados pasaban cualquier guarda con sus casillas apagadas | Con la sesión real de Mireya (cajera, `commissions_register_payment=false`): `GET /commissions/periodos` → 200, `GET /commissions/pagos` → 200, `GET /commissions/pagos/pendientes.csv` → 200, `POST /commissions/pagos/dia-de-pago` → 200, y el turno de Renata leído por la cajera | El alta escribe `employee` y `_abrir_sesion` **normaliza el rol de toda ficha EMPLOYEE**, así que las credenciales ya guardadas también quedan migradas sin resembrar el mundo. Efecto de comportamiento deseado pero amplio: la cajera ahora recibe 403 en las rutas de comisiones; Alma y Renata conservan todo por sus privilegios |
| 3 | **La firma de la bitácora (propuesta 12) era falsificable.** `seguimiento_handlers.firmar_nota:431` devolvía, antes que nada, el valor del encabezado `x-user-name` tal cual llegaba, sin contrastarlo con la sesión; ese valor es el `byName` que la pantalla enseña en vez del id | Con el token de Mireya y `-H 'x-user-name: Alma Renteria'`, la nota de contacto queda `{"by": "…364", "byName": "Alma Renteria"}`: **firmada por Alma y escrita por Mireya** | El nombre sale de la sesión o de la ficha EMPLOYEE, nunca del encabezado. La propuesta 12 existe precisamente porque *"si mañana Mireya lee «1803978000111», no sabe si fui yo o Alma"* (`gaby-2027-03-08.md`); con esto la bitácora podía decir cualquier nombre |

### 4.2 Las que movían dinero o datos

| Hallazgo | Qué se hizo |
|---|---|
| **`taxes.appliesToShipping` se publicaba y no se aplicaba.** `desglose_iva` calculaba siempre `base = total/(1+tasa)` sobre el total completo; las funciones que leen la llave solo servían para **publicar** su valor. Si el negocio la apagaba, la página del plan y la tienda decían que el envío no lleva IVA y cada pedido seguía desglosándolo sobre el envío. Es la única de las cuatro llaves del IVA que mueve dinero en el desglose | `desglose_iva`/`campos_pedido` aceptan `envio` y lo sacan de la base cuando la llave está apagada. Comprobado en vivo: total 1,329 con envío 129 → base 1,163.48 / IVA 165.52 (antes 1,145.69 / 183.31). La configuración quedó restaurada en `true` |
| **`access_screen_campaigns` no se podía quitar a nadie que tuviera `config_manage`**: la siembra lo encendía siempre que el mapa entrante trajera esa llave, también en el PATCH, así que la casilla quedaba clavada | La siembra mira si la llave **viene**, no su valor. Un `false` explícito manda (la casilla ya no queda clavada) y una ficha guardada antes de la ronda lo recibe al leerla y al abrir sesión |
| **`pendientes.csv` ponía el *reconocido* donde el archivo del banco pone el *confirmado***: decía 259.20 donde el CSV decía 135.00 | Las filas `sin_clabe` llevan el confirmado |
| **Pagos del mes releía el mes contable una vez por beneficiaria** | Una sola lectura; `check_query_budget.py` sigue en verde |
| **El listado de pedidos no proyectaba `shippingCost`, `vatRate`, `taxBase` ni `taxAmount`**, así que el detalle del back office no podía pintar ni el envío ni el desglose que B acababa de publicar | Se proyectan; el detalle pinta envío, desglose y factura |

### 4.3 Las de pantalla

Las nueve restantes eran de coherencia y de acceso, y salieron de probar el producto con las sesiones reales de los cinco empleados sembrados:

- **El menú del back office y la guarda no leían la misma tabla.** Se movió a `models/privileges.model.ts` (`ADMIN_MENU_GROUPS` + `adminMenuVisible`) con el privilegio de cada entrada saliendo de `privilegeForAdminRoute`: **una sola tabla para el menú y para la guarda**. Con eso, "Despacho en bloque" aparece y se abre con el mismo privilegio.
- **El aviso "esta pantalla no está entre las tuyas" no se veía navegando dentro del panel** (0 nodos). Pasó a `AccesoPantallaService` + `ui-aviso-sin-acceso`, y se ve también en Despacho y en Seguimiento, que son componentes aparte. Verificado con Playwright para Mireya, Toño y Gaby.
- **«Comisiones y pagos» enseñaba «Exportar 2026-08» junto a «abril 2027»**: ahora pide los periodos al montarse y el botón dice el mes en letras.
- **Sin sesión, el corte de mes salía del reloj del navegador**: 26 días contra 21 en el mismo minuto. `GET /catalog/config/public` publica `cutoffAt`/`serverNow` y el pie usa el año del servidor.
- **Género** en el correo de compra, la tienda, el panel y las tablas de descuento; **el recibo del cliente** usa el vocabulario único y el formato de fecha del contrato; **Acciones urgentes** estrena el contador de facturas solicitadas (propuesta 20) y **la suscripción** deja capturar una dirección ahí mismo (propuesta 19).
- **El gasto del simulador** pasó a ser el neto pagado ($1,008, resultado −$808), que es lo que de verdad sale de la bolsa.

Un apunte de método que costó tiempo: **`ng serve` estaba sirviendo un bundle viejo**. Llevaba varios ciclos fallando por un archivo nuevo que su *watcher* no recogió, aunque `tsc` y `ng build` pasaban. Se reinició con `.angular/cache` limpia, matando por PID. Si una revisión en navegador contradice a `tsc`, el sospechoso es el bundle servido, no el código.

---

## 5. La sesión con personas

Cinco personas nuevas trabajaron con el producto los días 4, 5 y 10 de mayo de 2027 del mundo simulado. Ninguna había visto la plataforma antes, ninguna leyó código, todas escribieron su diario al terminar (`sim/diarios/`) y el arnés contó por su lado clics, teclas, pantallas, recargas y milisegundos de lectura antes del primer clic (`sim/metricas/*.json`). Las preguntas que la pantalla no contestó quedaron en `sim/helpdesk.md`.

Se eligieron a propósito para volver a pisar los cinco sitios donde la ronda 6 más había dolido: comprar sin cuenta desde el celular, decidir si el negocio conviene, devolver un producto roto, abrir una caja de mostrador y pagar comisiones el día 10.

| Persona | Rol | Disp. | Min | Tareas | Logradas | Clics | Refl. (s) | Dudas | Atorones | Reint. | Facilidad | Confianza | Estética |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nayeli Ocampo, 31 | clienta invitada | celular | 32 | 5 | **4 (80 %)** | 16 | 1,788 | 11 | 4 | 2 | **5.6** | **5.0** | **7.0** |
| Gerardo Lomelí, 38 | prospecto | celular | 17 | 5 | **4 (80 %)** | 66 | 938 | 16 | 11 | 6 | 4.4 | 4.0 | 6.8 |
| Valeria Núñez, 27 | clienta nueva | celular | 8 | 3 | 2 (67 %) | 13 | 361 | 21 | 6 | 1 | 3.7 | 4.5 | 5.5 |
| Rubén Ávila, 24 | caja, tercer día | escritorio | 23 | 10 | 6 (60 %) | 58 | 1,398 | **45** | **15** | 5 | **3.1** | 4.0 | 5.0 |
| Marisol Cepeda, 41 | gerencia | escritorio | 12 | 6 | 3 (50 %) | 25 | 701 | 6 | 3 | 1 | 3.4 | 4.0 | 5.2 |

### 5.1 Valeria Núñez, 27, ilustradora en Querétaro — vino por un bote de colágeno

Entró por un anuncio, desde el celular, sin ningún interés en vender. Ocho minutos, tres tareas.

**Qué logró.** Comprar: pedido `ORD-AB0806B2`, Colágeno $700 + Estafeta $129 = **$829.00**, pagado y verificado tras recargar. Y sobre todo, lo que la ronda 6 no le dio a Mariana Robles: **saber el total antes de dar sus datos**. Escribiendo **solo el CP 76000** —sin nombre, sin teléfono, sin calle— aparecieron *"Estafeta · Terrestre · 3 a 5 días hábiles · $129 MXN"*, *"DHL · Express · 1 a 2 días · $219"* y el Total fijo abajo. Vio el desglose completo (*"Subtotal sin IVA $714.66 · IVA 16 % $114.34 · Total $829.00 — Los precios ya incluyen IVA; el envío también"*) y recibió el correo con el mismo desglose y un enlace de seguimiento que funciona sin cuenta.

**Qué falló.** Tres cosas, y las tres son de la misma familia —el producto sabe hablar de sí mismo y no sabe hablar del pedido—:

1. **No supo qué día le llega.** El *"3 a 5 días hábiles"* aparece en el carrito y **desaparece** al crear la orden: no está en la pantalla del pedido, no está en el correo y el Centro de ayuda no tiene sección de envíos. *"Pagué $829 sin fecha de entrega."*
2. **No supo qué estaba comprando.** Ocho de los trece productos repetían, en la tarjeta y en el "Detalle del producto", la misma frase de relleno: *«Presentación y modo de uso en la etiqueta del producto.»* Lo delator es que los otros cinco sí traen gramajes y porciones: se sabe escribirlas, a estos no se les puso.
3. **El botón "Ver carrito" del aviso no se dejaba tocar** mientras el detalle del producto estaba abierto: el fondo del modal se tragaba el toque. Le picó cinco veces. *"En el celular esto se siente como una app trabada."*

**Qué mejoró respecto de la ronda 6.** La tarea que Mariana Robles abandonó con facilidad 2 —*"ver cuánto cuesta con envío antes de dar mis datos"*— Valeria la **logró**, con facilidad 4 y confianza 5, y la nombró como la razón de comprar: *"Con tu código postal ya calculamos el envío: no hace falta nada más." — y es cierto, funcionó.* El aviso de privacidad, que en la ronda 6 le costó tiempo a 11 de 12 personas, ahora *"explica en cristiano que los datos se piden por etapas"*. Y el desglose de IVA *"se entiende de una sola leída"*.

**Qué sigue igual.** El vocabulario. *"«Meta para invitados»"* en el encabezado (un chip que ni siquiera se puede tocar), *"+13 PC hacia tu meta"* al agregar, *"Te faltan $0 para Meta de beneficios"* en el resumen: **la palabra "Meta" no se define en ninguna pantalla**, ni siquiera en la página del plan, que es la única que traduce el vocabulario. Y el carrito de una invitada sigue abriendo con *"Corte de mes — 21d 3h 27m 12s — Cierre del mes de comisiones y de tu descuento por volumen"*: *"Yo no tengo comisiones ni descuento por volumen: es una cuenta regresiva que me apura con algo que no es mío."*

> *"lo que sobra es todo lo de puntos, metas, comisiones y «modo socio» metido en medio de mi compra, y lo que falta es lo básico: qué trae el bote y qué día llega."* — `valeria-nunez-2027-05-04.md`

### 5.2 Gerardo Lomelí, 38, dueño de un gimnasio en Monterrey — vino a hacer la cuenta con lápiz

Prospecto de Paulina, ya perdió dinero en otra red. Diecisiete minutos, cinco tareas, 66 clics: el que más trabajó de los cinco.

**Qué logró.** Lo que Ximena Paredes no pudo en la ronda 6: **sacar su número honesto**. Con 8 personas reales de su gimnasio: comisión $960, menos $1,035 de compra mínima para activarse, menos $129 de envío a Monterrey = **−$204**. Entendió sobre qué se paga (*"sobre el neto que pagó tu referida por producto —el precio ya con su descuento, con IVA incluido— y sin contar el envío"*), qué le exigen (20 VP netos cada mes desde cero, comisión bloqueada si no está activo, depósito el día 10), leyó la escalera de descuento completa y los cinco porcentajes por generación con sus requisitos, y comprobó que activar el modo socio **fue gratis, instantáneo y sin CLABE**: *"En la otra red me cobraron $4,500 de «kit»."*

**Qué falló.** Encontró **seis defectos altos**, cuatro de ellos en el simulador que la ronda acababa de publicar:

1. **El acantilado del 40 %.** Comprar $6,000 en vez de $5,999 salta de tramo, baja los VP netos de 84 a 72, lo saca del requisito de generación 3 y le cuesta **$1,200.70 al mes**. La página vende ese tramo como el premio (*"Entre más compras en el mes, menos pagas"*) y no había ni una advertencia.
2. **El simulador clonaba a sus 8 directas hacia la generación 2** —sumándole $480 que nadie capturó— mientras al pie juraba *"no suponemos que tu red crezca sola"*. Su resultado honesto (−$75) se volvía +$405: *"es la diferencia entre entrarle y no entrarle."*
3. **"llevas 72 PC personales de los 80 que pide"**, cuando 72 son sus **VP netos** y sus PC de lista son 120. O la etiqueta o el cálculo estaban mal.
4. **El veredicto verde "Con eso activas el mes"** usaba $50/PC fijos cuando el catálogo va de **$46.67 a $72.22 por PC**: comprando Creatina, esos $1,035 son 14.3 VP y **no activa**.
5. **El aviso de comisión bloqueada del día 27 llegaba dos días después del corte del 25**, y se presentaba como el recordatorio para alcanzar a activarse.
6. **El menú de socio no abría nada.** Red, Links, Órdenes, Comisiones, Cuadro de Honor: *"le pico y no pasa nada, sin error, sin mensaje"*. Y el correo de bienvenida prometía *"tienes tu propio código"* **sin traerlo**. *"Un socio recién activado, con 180 clientes potenciales, sin manera de ver su código el mismo día que se registró."*

**Todo eso está corregido en `7fdacff`**: las cuatro cosas del simulador se dicen ahora y el resultado se recalcula **al escribir**, no solo al salir del campo; el aviso pasó al día 24 con una prueba que fija que ningún aviso rebase el corte; el correo lleva el código y la liga (y lo crea si falta); y los enlaces del menú que llevaban a una sección inexistente ya no callan.

**Qué mejoró respecto de la ronda 6.** Todo lo que Ximena pidió y no tuvo. Ximena hizo 16 tareas y **10 sin un solo clic**, calculando con lápiz el $/PC de cada producto porque *"la plataforma publica el plan pero no publica ganancias reales"*; Gerardo abrió el simulador y **le salió en rojo**:

> *"La calculadora abre en NEGATIVO (−$933.00) y remata con «Esto es una calculadora con las reglas del plan, no una promesa de ingresos». Ninguna red que yo haya conocido te abre en rojo."*

Y lo que Ximena buscó en tres pantallas sin encontrarlo —la base de la comisión— él lo leyó en la primera. Su estética es la más alta de los tres clientes en confianza que transmite (7) y legibilidad (8).

**Qué sigue igual.** *"«Es gratis, no te pide datos extra»"* contra INE, CURP y constancia fiscal marcados **"Requerido"** en el perfil: es la misma contradicción que Paulina Ríos reportó el 20 de marzo, ahora además contradicha por escrito (corregida en `7fdacff`: esos papeles se piden al cobrar comisiones, y así se dice). La portada sigue sin un solo porcentaje y sus cuatro promesas son de modo socio, no de cliente. Y el Centro de ayuda, que la ronda estrenó, **no tiene una sola sección de socios**: ni ISR, ni quién factura a quién, ni qué pasa con la comisión de un pedido devuelto. *"Para un dueño de negocio con RFC, si el pago es bruto o retenido y quién factura a quién es el dato que decide."* Eso es exactamente la mitad no resuelta de la propuesta 38.

### 5.3 Nayeli Ocampo, 31, maestra de primaria en Puebla — le llegó la proteína rota

Es la persona mejor calificada de las dos rondas: **facilidad 5.6 / 7, confianza 5.0 / 5, estética 7.0 / 10, recomendaría 8 de 10**, y eso que le llegó el producto estrellado.

**Qué logró.** Comprar como invitada (`ORD-1818C2AF`, $1,209, con la cotización solo por CP y el aviso honesto *"Recoger en sucursal no está disponible en tu zona. Hay sucursal en: Ciudad de México, Guadalajara. Te lo enviamos a domicilio."*) y, sobre todo, **la devolución parcial**: folio `RET-3C6E604F`, solo la proteína, sin devolver el Naplus. Y sus tres preguntas contestadas **sin preguntarle a nadie**:

- *quién paga el regreso* — *"El envío de regreso lo pagamos nosotros: guarda tu ticket, te lo reembolsamos"*;
- *cuánto* — $800.00, solo el producto;
- *cuándo* — *"al mismo medio de pago con el que compraste, en 3 a 5 días hábiles después de que validemos el paquete"*.

La misma información le salió **cuatro veces**: antes de pagar, en el correo de entrega, en el paso del motivo y en el resumen final. Es la propuesta 39 funcionando exactamente como se diseñó: una sola fuente, leída en cuatro sitios.

**Qué falló.** Dos cosas, y una es grave:

1. **La pantalla de seguimiento no se actualizaba sola.** Con el correo *"tu pedido fue entregado"* en la mano y el backend en entregado, `#/orden/…` seguía diciendo *"Estatus: Pagado"* y **el botón de devolución apagado**. Solo cambió al recargar a mano. *"Es grave porque el motivo «Llegó dañado» tiene una ventana de 48 horas: quien no se le ocurra recargar cree que no puede devolver y se le vence el plazo."*
2. **No hay forma de entregar el ticket del flete de regreso ni de avisar "ya lo mandé".** La plataforma lo promete cuatro veces y `#/devoluciones` lo pide en su paso 5; pero el único campo para el flete está en el paso 4 del asistente **y en pasado** (*"Si ya pagaste el envío de regreso, ¿cuánto te costó?"*), justo cuando nadie lo ha pagado todavía, y después desaparece. *"El flujo mejor explicado de toda la app manda a la clienta a WhatsApp exactamente por el dinero que le prometió."*

Además: el botón anunciaba siempre **el plazo más largo** (*"Te quedan 6 días"*, los 7 de "cambié de opinión") mientras tres renglones abajo decía *"48 horas"*; la dirección de la bodega solo se revelaba **después** de confirmar; y las tres tarjetas de motivo eran `<p>` con `(click)`, sin `role`, sin `tabindex` y sin radio visible: *"con teclado o lector de pantalla no se pueden elegir"*. Lo tres corregidos en `7fdacff`; el ticket del flete, no (§6).

**Qué mejoró respecto de la ronda 6.** Es la comparación más limpia de toda la ronda, porque hizo **exactamente la misma tarea que Julio Herrera**:

| | Julio Herrera (ronda 6) | Nayeli Ocampo (ronda 7) |
|---|---|---|
| Tarea | *"devolver SOLO la proteína, que llegó con el bote estrellado"* | *"devolver SOLO la proteína, que llegó estrellada, y saber quién paga el regreso, cuánto me devuelven y cuándo"* |
| ¿Logró? | **No.** Se quedó con la proteína rota | **Sí.** Folio `RET-3C6E604F`, $800.00 |
| Clics / pantallas | 17 clics, 9 pantallas | 8 clics, 3 pantallas |
| Facilidad / confianza | **1 / 7** | **6 / 7 · 5 / 5** |
| Preguntas a soporte | 2 (las cuatro cosas, por WhatsApp) | 0 |

Y su frase sobre los botones apagados es la propuesta 24 medida: *"Los botones deshabilitados dicen por qué lo están: «Podrás pedir la devolución en cuanto marquemos el pedido como entregado. Ahora está pagado.» Nunca había visto eso."*

**Qué sigue igual.** El "PC" en cada producto y el reloj de "Corte de mes" *"con lo de comisiones en mi carrito de dos botes"*; el *"En modo socio habrías ahorrado $108"* repetido en el resumen, en la orden y en el correo (*"Se siente como reclamo, no como oferta"*); y el carrito en el celular, *"larguísimo"*, que sigue siendo su peor pantalla.

> *"Recomendaría 8/10. ¿Volvería? Sí, y eso que me llegó rota la proteína: justo por cómo me trataron después."* — `nayeli-ocampo-2027-05-04.md`

### 5.4 Rubén Ávila, 24, cajero de mostrador, tercer día, sin capacitación

La peor sesión de la ronda, y la más útil: 23 minutos, 10 tareas, 6 logradas — **cuatro de ellas solo con la sesión de la gerente**. Facilidad 3.1, coherencia 3 de 10, y la frase que resume el problema: *"mañana llego con el papelito de la contraseña de Renata y eso no está bien"*.

**Qué logró.** Con el usuario de la gerente: abrir turno con $500 de fondo, cobrar la venta mixta `POS-C04B073D` por $980 ($500 al cajón, $480 con tarjeta, *"separados solos y bien explicados en pantalla"*), entregar un pedido de internet y cerrar el corte `CUT-2B3D81B9` con $1,040 contra $1,000 esperados, con el motivo obligatorio del sobrante y el comprobante enviado por correo.

**Qué falló.** El rol de caja no podía usar la caja: *"Stock actual: Sin stock asignado"* y *"No tienes un almacén ligado a tu usuario, así que no puedes cobrar todavía"*, con "Retirar efectivo" y "Hacer corte" apagados. La gerente probó cuatro caminos —vincular en Stocks (los cinco empleados **ya salían palomeados** en las tres bodegas), conceder permisos, guardar la bodega por defecto desde Despacho, recargar— y ninguno sirvió. Todo el turno quedó registrado a nombre de Renata Bustos: **se destruye la trazabilidad de quién cobró**.

**La causa no era la vinculación.** Se encontró al reproducirlo: el arranque del back office pedía cinco listas en un solo `forkJoin` y **bastaba un 403 en una** —el cajero no tiene "Ver Productos"— para que fallara el combinado entero, el `next` nunca corriera y bodegas, ventas y movimientos se quedaran en la lista vacía inicial, **sin un error en consola**. La pantalla convertía un problema de permisos en un estado vacío falso: *"Todavía no hay ninguna bodega dada de alta"*. Corregido en `7fdacff`: cada petición se resuelve por su cuenta y la que no se puede leer se nombra — *"No tienes permiso para ver Productos"*.

Y el segundo crítico, del mismo turno: **el comprobante del corte declaraba $500 vendidos con una única venta de $980**. Pintaba `total`, que es el movimiento **neto** del cajón, no lo vendido. Se guarda `salesTotal` y va en pantalla, en el correo y en el asunto. Palabras de Rubén: *"si la gerente lee nada más ese renglón, va a pensar que me quedé con $480."*

**Qué mejoró respecto de la ronda 6.** Lo que la propuesta 5 vino a arreglar, funcionó: Mireya Solano abrió su turno con un sobrante falso de $540 y dejó **$1,040 toda la noche en el cajón**; Rubén encontró el campo, la explicación y el texto que la propuesta pedía casi palabra por palabra —*"Esta caja nunca ha cerrado un corte: captura el fondo con el que arrancas"*— y el fondo quedó escrito en los movimientos y en el comprobante. Su mejor pantalla es la misma que la de Mireya, el corte en cuatro pasos, y por la misma frase, que ahora tiene un lector nuevo:

> *"«Queda escrito en el comprobante para que la gerente lo vea. No es una falta: es lo que pasó.» Un cajero nuevo con $40 de sobrante deja de tener miedo de reportarlo."*

La propuesta 6 también se cumplió: *"Todavía no hay un código de autorización configurado: nadie puede autorizar un retiro. Deja todo como fondo y avisa a tu gerente."* Mireya recibió un 403 con el dinero contado en la mano; Rubén recibió una explicación y una salida.

**Qué sigue igual.** Que el mismo dato salga distinto según con qué usuario se entre (*"lo más grave para la confianza"*), que los mensajes manden a pantallas que no existen —*"Almacenes → tu sucursal"* cuando la pantalla se llama Stocks—, que no haya en ningún lado un lugar que diga **qué permisos necesita la caja para funcionar** (30 permisos con explicación bonita y ninguna combinación recomendada), y que los pedidos de recolección **no se entreguen desde Caja** aunque Despacho lo prometa por escrito. Y las claves internas: *"STK-46603B"*, *"Usuario 1809421204348"*, *"privilegio 'order_mark_shipped' requerido"*, *"gu?a"*. Todo eso está corregido en `7fdacff` salvo la entrega desde Caja y la persistencia del stock al navegar (§6).

### 5.5 Marisol Cepeda, 41, gerente de operaciones — el día 10, día de pago

Doce minutos, seis tareas, tres logradas. Es la sucesora de Renata y Alma, y su sesión mide lo que la ronda hizo por el día de pago.

**Qué logró.** Entrar y **caer en Pedidos** de un jalón (3 clics, facilidad 7); llegar al bloque de Pagos del mes y obtener **una respuesta inequívoca**: *"Comisión reconocida de abril 2027: $0.00"* y *"Nadie tiene comisiones en abril 2027: ni confirmadas, ni por confirmar, ni bloqueadas"*; descargar el reporte con un clic desde *"Exportar abril de 2027"*, con el nombre correcto y una hoja de detalle que explica peso por peso por qué no se pagó; y comprobar, recargando, que el movimiento de dinero que hizo quedó persistido.

**Qué falló.** Tres cosas, dos de ellas críticas:

1. **"Conciliar pagos" contestaba "Revisados 0 · Acreditados 0 · Sin pago 0" en los cuatro periodos** —72 h, 7 días, 30 días y 90 días, el máximo— con cuatro pedidos "Pendiente de pago" listados **en la misma pantalla**, y remataba aconsejando *"Prueba con un periodo más largo"* estando ya en el más largo. La causa: solo se puede consultar a la pasarela por un pedido que llegó a generar su preferencia de pago; los demás se contaban como inexistentes. *"La única herramienta que responde «¿falta algún pago por registrar?» es ciega, así que la gerencia no puede firmar el cierre del día 10."* Corregido: ahora se cuentan y se nombran aparte, el consejo imposible desaparece y el verde de éxito se reserva para lo que sí se acreditó.
2. **"Marcar como pagado" movía dinero de un clic**: sin confirmación, sin campo para la referencia del depósito, sin deshacer, y con el acuse escondido al fondo de la página y redactado en jerga (*"Pedido ORD-BD349B9F de Cliente: el servidor lo dejó Pagado"*). *"Para borrar los datos de un cliente sí hay tres renglones de advertencia. El acto irreversible que toca el dinero es el que no pregunta nada."* Corregido: pregunta con el efecto escrito y pide el folio del depósito, que el servidor guarda en `paymentReference`.
3. **El día 10 no se puede reportar el mes anterior**: el selector de Estadísticas solo ofrece el mes en curso. Para saber si abril cerró en ceros por falta de ventas o por un error de cálculo tuvo que abrir las cinco pestañas de pedidos y leer fecha por fecha. **Sigue pendiente** (§6).

**Qué mejoró respecto de la ronda 6.** Las propuestas 4, 17, 18 y 35 se ven en su bitácora y en su diario:

| | Renata Bustos (ronda 6) | Marisol Cepeda (ronda 7) |
|---|---|---|
| *"ver qué hay que pagar del mes y a quién"* | 8 clics, **501 s**, 4 atorones, 3 reintentos, facilidad **2** | 1 clic, **68 s**, 0 atorones, facilidad **4** |
| Encontrar la pantalla | *"Comisiones"* buscada 7 veces en el menú por Alma; se llegó de rebote por una alerta | FINANZAS → Comisiones y pagos, en el menú |
| El mes | Marzo desaparecía del selector al recargar; el exportador bajaba **agosto de 2026** | *"Exportar abril de 2027"*, con el mes en el propio botón |
| La respuesta | Tres cifras del mismo concepto, sin saber cuál | *"Nadie tiene comisiones en abril 2027: ni confirmadas, ni por confirmar, ni bloqueadas"* |

Y elogió sin que se le preguntara lo que la propuesta 35 vino a hacer: *"Los botones apagados dicen POR QUÉ están apagados, con la razón escrita al lado: «Exportar archivo de dispersión (CSV) — No hay socias listas para depositar este mes», «Descargar pendientes (0) — Este mes no hay comisiones pendientes». Nunca me quedé adivinando por qué no podía apretar algo."*

**Qué sigue igual.** Que **"Comisiones y pagos" abra una pantalla titulada "Clientes"** con la ficha completa de una persona desplegada —ARCO, documentos, permisos, patrocinador— y el bloque de tesorería hasta el fondo: *"El día de pago se entra a pagar, no a leer la ficha de alguien."* Que los pedidos digan *"Cliente"* en vez del nombre y no traigan referencia de pago: *"Si la conciliación no me dice quién pagó y la ficha no me dice quién es, no hay a quién llamarle."* (corregido en `7fdacff`: los pedidos de invitado ya llevan el nombre del destinatario). Y que el Excel diga *"Motivo de pérdida: Nivel no configurado"* con los cinco niveles cargados en Configuración: **sigue pendiente**, y es la diferencia entre *"el mes salió en ceros"* y *"llevamos meses sin pagarle a la gente"*.

> *"Transmite confianza hasta que uno toca el dinero: ahí el diseño se voltea, porque lo irreversible es lo que no pregunta y lo reversible es lo que advierte."* — `marisol-cepeda-2027-05-10.md`

### 5.6 Las siete tareas que se repitieron: la comparación que sí aguanta

Las cinco personas de esta ronda no repitieron la sesión de nadie, pero **siete de sus veintinueve tareas son la misma tarea que alguien intentó en la ronda 6**, con el mismo objetivo escrito con sus propias palabras. Esas siete son la evidencia sólida; el resto de la comparación es de medias entre cohortes distintas (§5.8).

| Tarea | Ronda 6 | Ronda 7 | Veredicto |
|---|---|---|---|
| Saber el total con envío **antes** de dar mis datos | Mariana Robles: **no**, 8 clics, 154 s, facilidad 2, escribió a soporte a las 21:46 | Valeria Núñez: **sí**, 9 clics, 204 s, facilidad 4, confianza 5, con solo el CP | **Mejoró** (prop. 31) |
| Devolver **solo** el producto que llegó roto | Julio Herrera: **no**, 17 clics, 341 s, 9 pantallas, facilidad 1 | Nayeli Ocampo: **sí**, 8 clics, 388 s, 3 pantallas, facilidad 6, confianza 5 | **Mejoró mucho** (prop. 24, 39) |
| Saber sobre qué se paga la comisión y cuánto se gana de verdad | Ximena Paredes: **no**, 218 s, facilidad 2, lo buscó en 3 pantallas | Gerardo Lomelí: **sí**, 218 s, facilidad 4; y su número honesto del mes, −$204 | **Mejoró** (prop. 36, 37) |
| Ver qué hay que pagar de comisiones y a quién | Renata Bustos: sí, 8 clics, **501 s**, 4 atorones, facilidad 2, confianza 2 | Marisol Cepeda: sí, 1 clic, **68 s**, 0 atorones, facilidad 4, confianza 4 | **Mejoró mucho** (prop. 4, 17, 18) |
| Abrir el turno de caja con $500 de fondo | Mireya Solano: **no**, 6 clics, 147 s, facilidad 1; sobrante falso de $540 | Rubén Ávila: **no** con su usuario (2 clics, 97 s, facilidad 1); **sí** con el de la gerente (1 clic, 23 s, facilidad 5) | **La pantalla mejoró; el rol sigue sin poder** (prop. 5 sí, 27/33 no) |
| Entregar en el mostrador un pedido que llegó por internet | Mireya Solano: sí, 13 clics, 293 s, facilidad 2 | Rubén Ávila: **no** por el camino que la app anuncia (10 clics, 243 s, facilidad 1); sí por el rodeo de Pedidos (5 clics, 187 s, facilidad 2) | **Igual de malo** |
| Conciliar: ¿falta algún pago por registrar? | Renata Bustos: **no**, 2 clics, 71 s, facilidad 2, "Revisados 0" | Marisol Cepeda: **no**, 8 clics, 240 s, facilidad 2, "Revisados 0" en los cuatro periodos | **Igual** — y esta ronda encontró por fin la causa (§5.5) |

**Cuatro mejoraron con claridad, dos siguen igual y una mejoró a medias.** Las cuatro que mejoraron son las cuatro donde la propuesta atacaba una pantalla; las tres que no, son donde el problema es de **rol, de camino entre pantallas o de un dato que el servidor no puede consultar**. Es la misma lección de la [25] §1, conclusión 2, vista desde el otro lado: arreglar la pantalla funciona; arreglar la arquitectura de información y los permisos, no se hizo del todo.

### 5.7 Las métricas, ronda 6 → ronda 7

Ambas columnas salen de `python3 sim/metricas.py --markdown`, filtrando por cohorte. La ronda 6 son las doce personas de [25] §1; la ronda 7, las cinco de esta.

| Medida | Ronda 6 (12 personas) | Ronda 7 (5 personas) | ¿Mejoró? |
|---|---|---|---|
| Minutos de sesión | 212 | 92 | — |
| **Tareas logradas** | 82 de 126 (**65 %**) | 19 de 29 (**66 %**) | Igual (§5.8) |
| **Clics por tarea lograda (mediana)** | **3** | **4** | Empeoró un clic |
| Clics totales | 411 | 178 | — |
| **Segundos de reflexión antes de actuar** | **11,897 s** (3 h 18) | **5,186 s** (1 h 26) | Igual en densidad: 56 s de reflexión por minuto de sesión en las dos rondas |
| Reflexión por tarea | 94 s | 179 s | Empeoró en apariencia (§5.8) |
| Lectura antes del primer clic | 22.2 min en 48 llegadas (27.8 s de media) | 6.4 min en 18 llegadas (**21.3 s**) | **Mejoró**: 6.5 s menos por pantalla |
| **Tareas sin un solo clic** | **35 de 126 (28 %)**, 19 en fracaso | **5 de 29 (17 %)**, 2 en fracaso | **Mejoró**: menos gente se queda leyendo sin encontrar por dónde |
| Preguntas que la plataforma debió contestar sola | 27 (2.3 por persona) | 13 (2.6 por persona) | Igual |
| Atorones / reintentos / recargas | 92 / 47 / 8 | 39 / 15 / 3 | Por tarea: atorones 0.73 → **1.34**, empeoró (§5.8) |
| Dudas registradas | 175 | 99 | No comparable (§5.8) |
| **Facilidad media** (1 difícil – 7 fácil) | **3.6** | **4.0** | **Mejoró** +0.4 |
| **Confianza en que quedó guardado** (1–5) | **3.9** | **4.3** | **Mejoró** +0.4 |
| Estética · primera impresión (0–10) | 6.2 | 6.6 | Mejoró |
| Estética · **confianza que transmite** | **4.8** | **5.8** | **Mejoró +1.0** — el salto más grande |
| Estética · legibilidad | 6.3 | 6.8 | Mejoró |
| Estética · **coherencia** | **3.8** (la nota más baja de la [25]) | **4.4** | Mejoró, y sigue siendo la más baja |
| Estética · sensación en el celular | 5.0 (3 personas) | 5.7 (3 personas) | Mejoró |
| **Recomendaría** (0–10) | **5.2** | **6.0** | **Mejoró** +0.8 |
| Emociones registradas | 140 · **desconfianza 31**, alivio 26, frustración 24, enojo 14 | 35 · **alivio 6**, desconfianza 5, frustración 3, enojo 2 | **Mejoró**: la emoción más frecuente pasó de desconfianza a alivio |

### 5.8 Con franqueza: qué comparación es sólida y cuál no

Cinco personas no son doce, y estas cinco además hicieron **tareas distintas** de las de la ronda 6. Conviene decir dónde está la línea.

**Lo que sí aguanta.**

1. **Las siete tareas repetidas de §5.6.** Es una comparación de la misma tarea contra el mismo producto en dos momentos, con el diario de las dos personas al lado. Cuatro mejoraron, dos siguen igual, una a medias. Es el resultado más creíble de toda la ronda.
2. **Las notas de estética y de recomendación.** Las seis subieron, y subieron **en las cinco personas a la vez**, incluidas las dos que peor lo pasaron: Rubén, que trabajó todo el turno con la contraseña de otra persona, califica la legibilidad con 7 y la primera impresión con 6; Marisol, que abandonó tres tareas, pone 7 de primera impresión. Que suban todas en todos, con perfiles tan distintos, no parece ruido.
3. **La emoción dominante.** Pasar de 31 registros de desconfianza (la primera de la [25], con 7 de intensidad máxima solo por la CLABE) a 5, con el alivio en primer lugar, es un cambio de naturaleza, no de magnitud. Y esta ronda **no tuvo ni un solo registro de intensidad 5 relacionado con dinero que no se guarda**: la CLABE, que se llevó siete de los quince máximos de la ronda 6, no apareció en ningún diario.
4. **Lectura antes del primer clic y tareas sin un solo clic.** Las dos son medidas del arnés, no del criterio de la persona, y las dos apuntan igual: la gente encuentra antes por dónde. Es el efecto directo de las propuestas 4, 22, 23 y 25.

**Lo que no aguanta, y por qué.**

1. **El 65 % → 66 % de tareas logradas no dice nada.** Con 29 tareas, una sola tarea vale 3.4 puntos porcentuales. Que las dos cifras coincidan es casualidad aritmética, no evidencia de estabilidad.
2. **La mediana de clics (3 → 4) tampoco.** Es una mediana sobre 19 valores, y las tareas de esta ronda eran más largas por diseño: cuatro pasos del asistente de devolución, un simulador con cuatro campos, un corte de caja completo.
3. **Los "segundos de reflexión por tarea" (94 → 179) parecen un empeoramiento y no lo son.** La reflexión por **minuto de sesión** es idéntica (56 s en las dos rondas): lo que cambió es el tamaño de la tarea. Y el mayor bloque individual de reflexión de toda la ronda —**1,568 s de Nayeli**— corresponde a una tarea **lograda, con facilidad 6 y confianza 5**: leyó de arriba abajo la política de devoluciones porque la política por fin estaba escrita. La reflexión no distingue "no entiendo" de "estoy leyendo con gusto".
4. **Los atorones por tarea (0.73 → 1.34) empeoraron, y hay que decirlo aunque incomode.** No se explica solo por Rubén: quitándolo, siguen en 1.26. Las cinco personas de esta ronda fueron a sitios más profundos —el plan entero desde un celular, un rol que no podía trabajar, el día de pago— y ahí se atoraron más. Esta medida dice que **el producto sigue costando** en las trayectorias largas.
5. **Las "dudas" registradas no son comparables entre rondas.** Es un conteo que cada persona lleva a mano; Rubén anotó 45 en 10 tareas y Valeria 21 en 3. Mide diligencia del anotador tanto como confusión del producto.
6. **Y la limitación de fondo: los cinco perfiles no son los doce.** Faltó por completo el perfil que más sufrió en la ronda 6 —**Ernesto Vidal, 63 años, celular, 14 atorones**— y faltó el almacén (Toño) y la coach (Gaby), que fueron los dos mejores números de la ronda 6. Una cohorte con Ernesto dentro habría bajado todas las medias. **La conclusión honesta es que el producto mejoró donde se midió, y que no se midió donde más costaba.**

---

## 6. Pendiente y siguientes pasos

### 6.1 Lo que la ronda dejó sin hacer, a propósito

| Qué | De quién salió | Por qué se dejó |
|---|---|---|
| **La otra mitad de la propuesta 38**: retención de ISR/IVA sobre la comisión, si se paga bruto o retenido, quién factura a quién, y monto mínimo de depósito | Ximena (ronda 6), Gerardo (ronda 7) | Es decisión de negocio y fiscal del dueño; hoy se paga el bruto el día 10 y **no hay una sola pantalla que lo diga**. Es lo que un socio con RFC necesita para decidir |
| **Ticket de la venta para el cliente en el POS** | Rubén | Decisión §3.18: ninguna de las 39 lo pide, y meterlo dentro de la 38 pondría en riesgo el corte de caja. Reapareció en la sesión: *"la clienta se fue sin comprobante de una venta de $980"* |
| **Entregar el ticket del flete de regreso y avisar "ya lo mandé"** | Nayeli | Es funcionalidad nueva, no un cambio mínimo. Es el hueco de la mejor pantalla del producto: *"la única acción que la app me pide («avísanos») es la única que no tiene botón"* |
| **Secciones de socio en el Centro de ayuda** (impuestos, comisión de un pedido devuelto, red) y **de tiempos de envío** | Gerardo, Valeria | Es contenido nuevo. El Centro de ayuda que la ronda estrenó es todo de comprador, y no tiene sección de envíos: *"la pregunta más obvia después de pagar no tiene respuesta en ningún lado"* |
| **Estadísticas**: selector con el mes anterior, totales que cuadren con el tablero y la columna de dinero por estado, hoy en $0 | Marisol | Toca el motor de reportes, fuera del alcance de las 39 |
| **"Nivel no configurado"** en el reporte de comisiones con los cinco niveles cargados | Marisol | Hay que distinguir *"no compró"* de *"no hay configuración"* en el motor de comisiones, que esta ronda **no toca** (§0.5) |
| **La persistencia del stock del POS al navegar**: salir de Caja y volver repone "Bodega Central" y el turno abierto parece perdido | Rubén | Riesgo alto de tocar el arqueo; se documentó para la ronda siguiente |
| **El selector "Stock origen" vacío** del diálogo "Registrar envío" de un pedido suelto, y el `NG0103` del despacho en bloque | Nayeli (incidental de almacén) | Encontrado montando el mundo, no como clienta |
| **Combinaciones de permisos inservibles** y el botón "Ver" de Empleados que abre la ficha de otra persona | Rubén | Es la continuación natural de la propuesta 27 |
| **Reacreditar los pedidos de invitado ligados ANTES de la ronda** | G/16 | El mundo se sembró de cero y no hay casos; escribir un script de migración sobre dinero ya contabilizado no vale el riesgo |
| **Deduplicar las etiquetas de "Por qué elegir X"** ("colageno" y "colágeno" pintaban dos tarjetas) | C, por su cuenta | No era ninguna de sus seis propuestas y prefirió no meterlo de contrabando. Queda anotado |

### 6.2 Lo que se descartó, con su razón

- **"Todos los productos — 13 productos" con 14 tarjetas.** El contador cuenta productos distintos (13 en el catálogo); la decimocuarta tarjeta es el producto del mes destacado arriba, que también vive en la lista. **No es un duplicado.**
- **"Textos pegados sin salto de línea"** en el correo de devolución y en el Centro de ayuda. En ambos casos los bloques son `<p>`/`<div>` separados: **el pegado es del extractor de texto del arnés**, no de lo que se renderiza.
- **"Envío desde $129 ahuyenta cuando la tarifa es plana."** "Desde" es exacto mientras el precio se cotiza por CP, y `shipping.baseRateMxn` no modela una tarifa plana que se pudiera anunciar sin mentir. Cambiarlo requiere que el negocio **declare** la tarifa plana.

### 6.3 Un cambio de comportamiento que conviene confirmar con el dueño

**El carrito ahora exige 10 dígitos de teléfono siempre**, también a un cliente con sesión cuyo perfil no lo tenga. Es lo que pide la propuesta 3 (*"que se pidan siempre"*) y sin teléfono no hay a quién avisarle, pero es un cambio de comportamiento para clientes ya registrados. Lo dejó anotado el paquete C y sigue sin confirmarse.

### 6.4 Las tres cosas que haría la ronda siguiente

1. **Terminar los permisos, no la pantalla.** Las tres tareas de §5.6 que no mejoraron son de rol y de camino entre pantallas: la caja que no abre con su propio usuario, la entrega de mostrador que la app anuncia por un sitio y ocurre por otro, y la conciliación que no puede consultar lo que no tiene preferencia de pago. Ninguna se arregla con una pantalla nueva. Y hay que publicar en algún lado **qué permisos necesita cada puesto para trabajar**: hoy son 30 casillas sin una sola combinación recomendada, y la gerente terminó palomeando a tanteo.
2. **Cerrar el ciclo del pedido después de pagar.** Valeria pagó $829 sin saber qué día le llega; Nayeli mandó un paquete sin poder decir que lo mandó ni entregar el ticket; Marisol no puede reportar el mes anterior el día 10. El producto sabe **empezar** cosas y no sabe **acabarlas**: fecha de entrega en el recibo y en el correo, un "ya lo mandé" con su ticket, y el mes anterior en Estadísticas.
3. **Traducir el vocabulario donde nace, no en la página del plan.** "PC", "Meta", "Corte de mes", "Nivel de descuento: Inactivo", "Conciliación": las tres clientas de esta ronda tropezaron con los mismos cinco términos, y las tres tuvieron que irse a la página de las comisiones para entender la etiqueta de un bote. La propuesta 25 unificó los **estados**; el vocabulario del plan sigue suelto en la tienda de quien no vino a vender nada.

---

## 7. Cómo verificarlo

### 7.1 Comandos

```bash
# El árbol y el tamaño de la ronda
git log --oneline 76165c5..7fdacff            # 64 commits
git diff --shortstat 76165c5 7fdacff          # 160 archivos, +14,358 / −1,293

# Backend: la suite completa y el presupuesto de consultas
cd Micro-lambda-GMF/python
python3 -m pytest tests -q                    # 613 passed
python3 tools/check_query_budget.py           # ORDER_PAID 37/40 · "Presupuesto de consultas respetado."

# Las pruebas que fijan lo más caro de la ronda
python3 -m pytest tests/test_encabezados_forjados.py -q   # el hallazgo crítico de las revisoras
python3 -m pytest tests/test_integracion_ronda26.py -q    # los diez pendientes que cerró la integración
python3 -m pytest tests/test_iva.py tests/test_simulador_plan.py tests/test_clabe_guardar.py -q

# Frontend (nunca 'ng build' ni 'ng serve' dentro de un worktree)
cd gamificacion-multinivel-f
npx tsc -p tsconfig.app.json --noEmit
npx ngc -p tsconfig.app.json --noEmit

# El mundo simulado, antes de mirar nada en el navegador
bash sim/comprobar.sh          # environment.ts a :4400, backend vivo, bundle sin AWS, catálogo sembrado
python3 sim/metricas.py --markdown
python3 sim/cobertura.py
```

Comprobación en vivo del hallazgo crítico (debe responder **403** en los tres casos):

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'x-user-role: admin' \
  'http://localhost:4400/commissions/pagos?month=2027-04'
curl -s -o /dev/null -w '%{http_code}\n' -H 'x-user-role: admin' \
  'http://localhost:4400/commissions/pagos/dispersion.csv?month=2027-04'
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'x-user-role: admin' \
  -H 'Content-Type: application/json' -d '{"userId":"1809421204364","date":"2027-01-15"}' \
  'http://localhost:4400/inventory/turno/resumen/enviar'
```

### 7.2 Pantallas

Credenciales del mundo sembrado en `sim/credenciales.json`; el frontend en `http://localhost:4321`.

| Qué mirar | Dónde | Qué tiene que verse |
|---|---|---|
| **1 · CLABE** | `#/dashboard` → Comisiones, `#/perfil`, y la ficha del cliente en `#/admin/clientes` | El mismo `ui-clabe-form` en los tres sitios, sin modal; al guardar, el estado aparece **en el propio campo**: *guardada, termina en 6789*. "Quitar CLABE" con confirmación en línea |
| **2 · Aviso de CLABE** | Panel de una socia recién activada | *"desde hoy las compras de tu red te generan comisiones"*, nunca *"Ya tienes $0.00 en comisiones confirmadas"* |
| **4, 15, 20, 33 · Back office** | `#/admin/comisiones`, `#/admin/pedidos`, `#/admin/pedido/:folio` | FINANZAS → Comisiones y pagos en el menú; recargar la URL no pierde la vista; el botón "Ver" abre el detalle; pestaña "Factura solicitada" con contador; entrar como Mireya aterriza en `#/admin/pos` |
| **5, 6, 30 · Caja** | `#/admin/pos` y `#/admin/resumen-turno` | *"Esta caja nunca ha cerrado un corte: captura el fondo con el que arrancas"*; en el paso 3 del corte, *"Todavía no hay un código de autorización configurado… deja todo como fondo y avisa a tu gerente"*; "Enviar a mi gerente" en el resumen |
| **7, 13, 31, 38 · Compra** | `#/tienda` → `#/carrito` → `#/orden/:id` | Escribir **solo el CP** y ver las dos tarifas con plazo; *"Subtotal sin IVA · IVA 16 % · Total"* y *"Los precios ya incluyen IVA; el envío también"*; el recibo repite productos, sucursal y datos fiscales |
| **8, 39 · Ayuda y devoluciones** | `#/ayuda`, `#/contacto`, `#/sucursales`, `#/facturacion`, `#/devoluciones`, y cualquier URL inventada | El comodín cae en `#/ayuda`; la tabla de los tres motivos con plazo, evidencia y **quién paga el envío de regreso**; el pie con correo, WhatsApp, horario y el año del servidor |
| **24 · Botón de devolución** | `#/orden/:id` de un pedido pagado | El botón se ve **siempre**; apagado, dice su motivo y su plazo, también al pasar por encima |
| **28 · Stocks** | `#/admin/stocks` | Abre con la tabla producto × sucursal, con totales y las celdas bajo el mínimo en rojo; la bitácora enlazada; el alta de bodega detrás de un botón |
| **29 · Corte de mes** | `#/carrito` con sesión y en una ventana privada sin sesión | **La misma fecha y los mismos días** en los dos casos, con la fecha en letras |
| **36, 37 · Plan y simulador** | `#/modo-socio`, `#/modo-socio#simulador`, `#/modo-socio#generaciones` | *"Activarte cuesta entre $933.33 y $1,604.94, según lo que compres"*; el simulador abre en negativo, avisa que no es una promesa de ingresos y dice el requisito que falta con su número; *"10 % de $960.00 netos, sin envío = $96.00"* |
| **Permisos (revisoras)** | Entrar como Mireya (`mireya@findingu.mx`) | Menú recortado, insignia "Caja"; abrir a mano `#/admin/comisiones` muestra el aviso de que esa pantalla no está entre las suyas, también navegando dentro del panel |

