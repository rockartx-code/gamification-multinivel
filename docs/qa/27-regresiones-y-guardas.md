# 27 · ¿Rompimos algo? Auditoría de regresiones de la ronda de las 23 propuestas

La sospecha era razonable: en las rondas 4 y 5 se pagaron comisiones (Verónica cobró $393.60 y $368.40 con su
CLABE en la ficha) y en la ronda 6 la CLABE aparece como que "no se guarda" y marzo cierra en $0.00. Si eso se
rompió con nuestros cambios, hay que saberlo y blindarlo.

Se auditaron los **42 commits de `99879bc` a `95d443a`** (la ronda que implementó las 23 propuestas de
[23](23-implementacion-23-propuestas.md)) contra los 49 hallazgos de [25](25-ronda-experiencia-medida.md),
comparando cada archivo implicado con su versión anterior (`git show 99879bc:<archivo>`), rastreando el origen
de cada síntoma (`git log -S`), decidiendo "antes o dentro de la ronda" con `git merge-base --is-ancestor`,
leyendo los diarios archivados de las rondas 1 a 5 y haciendo llamadas reales al backend.

## 1. El resultado, en una línea

**Ninguno de los 49 hallazgos es una regresión.** No rompimos nada que funcionara.

| Veredicto | Hallazgos | Qué significa |
|---|---|---|
| **Regresión** (funcionaba y lo rompimos) | **0** | — |
| **Preexistente** | 17 | Ya estaba roto o nunca existió; la ronda 6 lo encontró porque por fin alguien lo intentó |
| **Nuevo y nació incompleto** | 18 | Lo construimos en la ronda de las 23 propuestas y se entregó a medio terminar |
| **No es defecto de código** | 6 | La función existe y sirve: era diseño, percepción o el arnés |

El riesgo que se intuía existe, pero apunta al lado contrario: **lo que hay que blindar no es lo viejo, sino el
criterio de "hecho" de lo nuevo.** De los 18 hallazgos de "nació incompleto", catorce se habrían detectado con
una prueba de las del §4, y todas juntas cuestan menos de un segundo en una suite que corre en cinco.

## 2. La CLABE: el informe 25 se equivocó en la causa

Tres afirmaciones de la §3.1 del informe 25 no se sostienen:

| Lo que dice el informe 25 | Lo que muestra la evidencia |
|---|---|
| "En todo `sim/servidor.log` no hay ni un solo `POST /customers/clabe`" | Hay **10** (`grep -c "customers/clabe"`), con respuestas 200. Lo correcto es: *ninguno vino del navegador de una socia* |
| "Un modal de confirmación pintado al final de una página kilométrica" | `ui-modal.component.ts:37` usa `fixed inset-0 z-50 flex items-center justify-center`. La captura `fabiola-11-clabe-segundo-intento.png` lo muestra centrado y legible |
| "Guardar CLABE no guarda" | Guarda. Lo que no se completó fue el **segundo paso**: el diálogo se abrió y nadie pulsó "Confirmar" |

**El código de la CLABE no cambió en la ronda.** Los dos formularios, el modal, el campo y el servicio son
idénticos a como estaban antes de `99879bc` — y a como estaban en la ronda 1:

```
git diff 99879bc..HEAD -- .../components/ui-modal/        → 0 líneas
git diff 99879bc..HEAD -- .../components/ui-form-field/   → 0 líneas
git diff 99879bc..HEAD -- .../user-profile.component.ts   → solo el *ngIf de modo cliente y un texto
```

**Y el flujo del socio sí funcionó una vez, en la ronda 1**, con este mismo modal:

> "Registré mi CLABE. Puse 012180001234567890, salió un modal 'Actualizar CLABE interbancaria — Estás a punto de
> guardar la CLABE', confirmé y ahora dice 'CLABE registrada: **** 7890'. Ese flujo sí está bien hecho: pide
> confirmación y luego la enmascara." — `veronica-dia1.md`, en el archivo de las rondas 1 a 5

**Por qué parecía que se había roto.** En las rondas 4 y 5 nadie volvió a capturar una CLABE: Verónica ya la
traía de la ronda 1 (por eso cobró), y Claudia y Bety **nunca la tuvieron** — es literalmente el hallazgo 13 del
informe [21](21-cuarta-ronda-escenarios-restantes.md): *"dos de tres beneficiarias llegaron al día 10 sin ella"*.
Hasta esta ronda, el back office ni siquiera podía capturarla: la ficha solo la mostraba, y el campo lo añadió
`acca507`. Es decir: **el defecto de diseño llevaba ahí desde la ronda 1, sin testigos**, y la ronda 6 fue la
primera vez que dos socias distintas intentaron capturarla el mismo mes.

**Dónde se rompe la cadena, en concreto.** En la corrida buena no hay `POST` ni siquiera `OPTIONS
/customers/clabe` desde el navegador: sin preflight, la petición nunca se intentó, así que `saveCustomerClabe()`
salió por su guarda (`user-dashboard.component.ts:2089`) porque nunca se pulsó Confirmar. Las dos socias leyeron
el diálogo como "no pasó nada" —el rótulo de arriba seguía diciendo "No registrada" y el campo conservaba el
número— y recargaron. Diez intentos, cero confirmaciones.

La corrección de la propuesta 1 del informe 25 sigue siendo la correcta (quitar el paso de confirmación, guardar
directo y poner el estado en el propio campo), pero por la razón contraria a la que daba el informe.

## 3. Lo que sí conviene vigilar: tres estrechamientos

No rompen nada que antes funcionara, pero la ronda **estrechó caminos que estaban abiertos**, y merecen guarda:

| Qué | Commit | Dónde | Por qué importa |
|---|---|---|---|
| El bloque de CLABE y el de documentos del perfil se ocultan en "modo cliente" | `1f759d7` | `user-profile.component.html:105,147,289` | `isClientMode` arranca en `'invitado'` y solo se corrige cuando responde `GET /customers/modo`. Si esa llamada falla o tarda, la socia ve su perfil **sin** su CLABE |
| El panel del socio redirige a `/admin` a toda sesión con acceso admin | `acca507` | `user-dashboard.component.ts:1236` | Una socia con acceso al back office (el caso grave del informe 21) ya no puede ver su propio panel ni su CLABE |
| Dos botones más en la tira de pestañas de Pedidos, uno con `ml-auto` | `1d8a57d`, `4b9495f` | `admin.component.html:144,152` | Agrava el salto de layout de una tira que ya recreaba sus nueve botones en cada ciclo de detección de cambios (`*ngFor` sobre un literal, sin `trackBy`): es el sustrato del bug del botón "Ver" |

## 4. Guardas: quince pruebas que impiden que esto vuelva

Nueve de backend (`Micro-lambda-GMF/python/tests/`, estilo `test_avisos_clabe.py`), cinco de frontend
(el andamio ya existe: `@angular/build:unit-test` con vitest y jsdom, `npm test` configurado) y una del arnés.

| # | Prueba | Qué afirma | Cubre |
|---|---|---|---|
| 1 | `test_seguimiento_hoy.py::test_toda_situacion_tiene_plantilla` | `set(SITUACIONES) <= set(PLANTILLAS)`; y que la situación `activa` traiga su propia plantilla en vez de caer en `fria` | Coach a punto de mandar "hace tiempo que no te vemos" a quien compró el viernes |
| 2 | `test_caja_arqueo.py::test_fondo_inicial_declarable` | Sin corte anterior se puede declarar el fondo de $500; con $40 en efectivo el esperado es $540 y la diferencia 0. Y `openingCashDeclared: false` cuando nadie lo declaró | El sobrante falso de $540 y los $1,040 que se quedaron en el cajón |
| 3 | `test_ledger_fechas.py::test_recalculo_no_reescribe_createdAt` | Recalcular una comisión conserva su `createdAt`; solo cambian `status` y `updatedAt` | "Le movieron la fecha a mis comisiones" |
| 4 | `test_invitado_mes.py` (3 pruebas) | Ligar la ficha de un invitado (o registrarse con un correo que ya compró) recalcula VP, volumen y activación del mes, y el Cuadro de Honor lo incluye | $5,038 pagados por tres clientes y el mes en cero |
| 5 | `test_avisos_clabe.py::test_no_avisa_comisiones_inexistentes` | Sin comisiones confirmadas ni pendientes no sale "Ya tienes comisiones a tu favor"; con pendientes, el texto dice "pendientes" | El aviso que le llegó a dos socias con $0 |
| 6 | `test_direcciones.py::test_saveShippingAddress_persiste` | El pedido con `saveShippingAddress` guarda la dirección, y la suscripción la acepta después | Cero suscripciones en marzo; 7 de 7 clientes sin direcciones |
| 7 | `test_conciliacion.py::test_horas_viaja_desde_la_pantalla` | `hours` llega del cliente (1 a 2160) y se ecoa; fuera de rango, 400 | "Revisados 0" cuando se pidió revisar el mes |
| 8 | `test_pos_autorizacion.py` | El código se valida antes del retiro y con mensaje propio cuando no hay código dado de alta | 403 con el dinero contado en la mano |
| 9 | `test_despacho_bloque.py::test_entrega_en_mostrador_no_descuenta_otra_sucursal` | O se rechaza con motivo, o descuenta la correcta y la respuesta dice cuál | La entrega que movió inventario de otra ciudad |
| 10 | `user-dashboard.clabe.spec.ts` (3 pruebas) | Guardar llama al API **en un solo paso**; el estado se pinta en el propio campo ("termina en 6789"); 17 dígitos dan mensaje inline sin llamada | El caso que motivó esta auditoría |
| 11 | `user-profile.clabe.spec.ts` (2 pruebas) | El bloque de CLABE se pinta aunque el modo no se resuelva; y en toda la aplicación hay **un solo** formulario de CLABE | El estrechamiento 1 del §3 |
| 12 | `pagos-mes.component.spec.ts` | El selector de meses sale del servidor, no del reloj del navegador, y la selección sobrevive a recargar | Marzo perdido en el día de pago |
| 13 | `admin.component.reloj.spec.ts` | El mes contable y "días desde la última compra" salen del reloj del servidor | Dos pantallas con dos relojes distintos |
| 14 | `admin.tablas.spec.ts` | Ningún `*ngFor` itera sobre un literal de array; toda tabla dinámica declara `trackBy` | El botón "Ver" que no abre |
| 15 | `sim/lib/persona.mjs` + `sim/comprobar.sh` | El reloj del navegador se fija al del mundo simulado, y el comprobador lo verifica | Cuatro hallazgos de la ronda 6 que eran del arnés |

## 5. Lo que nunca se había ejercido

Ocho funciones que ninguna ronda anterior tocó, y que por eso parecían roturas nuevas:

1. **El alta de CLABE desde el panel del socio**, desde la ronda 1. Verónica la guardó una vez; después nadie
   más la capturó hasta la ronda 6.
2. **La captura de CLABE desde el back office**: no existía hasta `acca507`.
3. **La libreta de direcciones**: `saveShippingAddress` se envía desde antes de la ronda y **el backend nunca la
   ha leído**; solo el mock la implementa.
4. **La suscripción mensual**, que depende de la anterior: cero altas en todo marzo.
5. **Comprar como invitado y que un empleado te cree ficha después.**
6. **Un turno de caja de alguien que llega con dinero en el cajón**: el arqueo se probó como "cerrar", nunca
   como "abrir".
7. **La situación `activa` del coach**: solo se dispara con clientes que compraron hace poco, y no los había.
8. **La conciliación con un rango distinto de 72 h**, la devolución vista por el cliente en estado `paid`, la
   factura después de solicitada y la recolección en sucursal como invitado.

## 6. Qué se hace con esto

Las quince guardas del §4 se aplican **después** de la ronda que está implementando las 39 propuestas, para no
pisar su integración, y antes de darla por cerrada. Las que blindan lo que ya servía (10, 11, 3, 6 y 15) van
primero; las demás acompañan a la corrección que ya está en curso, porque describen exactamente lo que esas
propuestas tienen que dejar funcionando.

## 7. Estado de las guardas

Las quince guardas del §4 están escritas y aplicadas sobre
`claude/ultimos-cambios-integrados-fylhiw`, después de la ronda de las 39 propuestas. **Ninguna quedó en
`xfail` ni saltada**: las treinta y una pruebas pasan en verde. Diez de las quince pasaron a la primera contra
el código de hoy —la propuesta correspondiente de la ronda 26 ya estaba implementada— y quedan de candado; las
otras cinco (5, 11, 13, 14 y 15) destaparon función a medio terminar, y en las cinco se corrigió el producto (o
el arnés) con el cambio mínimo, nunca la afirmación de la prueba.

| # | Guarda | Archivo | Pruebas | Estado | Qué destapó |
|---|---|---|---|---|---|
| 1 | Toda situación del coach tiene plantilla | `Micro-lambda-GMF/python/tests/test_seguimiento_hoy.py::test_toda_situacion_tiene_plantilla` | 1 | **pasa** | Nada: `activa` ya trae plantilla propia. Candado. Comprueba además lo que sirve `/customers/seguimiento/plantillas` con el override de configuración, y que la bitácora acepte `templateKey: "activa"` |
| 2 | El fondo inicial de caja se declara | `Micro-lambda-GMF/python/tests/test_caja_arqueo.py::test_fondo_inicial_declarable` | 1 | **pasa** | Nada: la propuesta 5 de la ronda 26 ya está. El contrato que el §4 pedía como `openingCashDeclared: false` existe hoy con otro nombre —`openingSource: "sin_declarar"` + `needsOpening: true`— y es ese el que la prueba fija; queda escrito en el archivo para que no parezca una rebaja |
| 3 | Recalcular no reescribe `createdAt` | `Micro-lambda-GMF/python/tests/test_ledger_fechas.py` | 3 | **pasa** | Nada: la propuesta 32 ya lo corrigió. La guarda no mira solo `createdAt`: compara la fila campo por campo antes y después y exige que lo único que cambie sea `status` y las marcas `recalculatedAt`/`recalculatedReason`. El `updatedAt` que menciona el §4 vive en la cabecera del mes, no en la fila (`core/ledger.py::_write_ledger_rows`). Se corre también con `LEDGER_ROW_SCHEME="rows"` |
| 4 | Ligar la ficha de un invitado recalcula el mes | `Micro-lambda-GMF/python/tests/test_invitado_mes.py` | 3 | **pasa** | Nada. Fija las tres puertas de activación (VP, volumen, Cuadro de Honor) por los dos caminos: registrarse con un correo que ya compró, y ligar la ficha desde el back office |
| 5 | El aviso no promete comisiones inexistentes | `Micro-lambda-GMF/python/tests/test_avisos_clabe.py::test_no_avisa_comisiones_inexistentes` | 1 | **pasa (tras corregir el producto)** | La ronda 26 solo había arreglado la mitad. El panel no distinguía "cero" de "pendiente": con $96 en comisiones pendientes decía exactamente lo mismo que con $0. Y el correo de pedir CLABE (`handle_pedir_clabe` → `_correo_clabe`) seguía diciendo literalmente «Ya tienes $0.00 en comisiones confirmadas» — el texto que, según el informe 26, «es lo único que me tiró la confianza» (Ximena). Corregido en `pagos_handlers.py`: rama de pendientes en `_aviso_panel_clabe` y rama de monto 0 en `_correo_clabe`, sin consultas nuevas |
| 6 | `saveShippingAddress` persiste y la suscripción la acepta | `Micro-lambda-GMF/python/tests/test_direcciones.py` | 3 | **pasa** | Nada en la primera mitad. La segunda —que la suscripción acepte esa dirección después— no estaba cubierta y ahora lo está; se añadieron además el rechazo honesto (alta sin dirección → 400 con motivo y salida desde el perfil) y que la dirección de otra persona no se pueda usar |
| 7 | El rango de conciliación viaja desde la pantalla | `Micro-lambda-GMF/python/tests/test_conciliacion.py::test_horas_viaja_desde_la_pantalla` | 1 | **pasa** | Nada. Crece más allá del enunciado en la misma dirección: fija que el rango se guarda en la corrida (que es lo que lee la tarjeta después) y que sin `hours` manda la configuración, no un literal |
| 8 | El código del POS se valida antes del retiro | `Micro-lambda-GMF/python/tests/test_pos_autorizacion.py` | 3 | **pasa** | Nada. Fija que no se escribe nada si se rechaza, que sin código dado de alta se dice eso y no «incorrecto», y que el código nunca viaja de vuelta ni se valida sin privilegio |
| 9 | La entrega en mostrador no descuenta otra sucursal | `Micro-lambda-GMF/python/tests/test_despacho_bloque.py` | 2 | **pasa** | Nada. Añade que el `stockId` del cuerpo **no** elige de qué bodega se descuenta, y que entregar dos veces no descuenta dos veces |
| 10 | La CLABE del panel se guarda de un tirón | `gamificacion-multinivel-f/src/app/pages/user-dashboard/user-dashboard.clabe.spec.ts` | 3 | **pasa** | Nada: `ui-clabe-form` ya implementa la propuesta 1 (guarda en un paso, pinta «termina en 6789» en el propio campo, rechaza 17 dígitos sin llamar al API). Comprueba además que no hay ningún `ui-modal` en ese flujo |
| 11 | Un solo formulario de CLABE en toda la aplicación | `gamificacion-multinivel-f/src/app/pages/user-profile/user-profile.clabe.spec.ts` | 2 | **pasa (tras corregir el producto)** | Primera prueba (el bloque se pinta aunque `GET /customers/modo` falle) pasa: cierra el estrechamiento 1 del §3. La segunda destapó **dos** campos de captura de CLABE: el de `ui-clabe-form` y otro suelto en el modal «Solicitud de pago» del panel (`name="commissionClabe"`), inalcanzable —nada llamaba a `openCommissionModal()`— y que el backend (`handle_payout_request`) ignora por completo. El modal deja de capturar CLABE y dice a qué CLABE registrada va el depósito; `clabe` pasa a opcional en `CommissionRequestPayload` |
| 12 | Los meses de Pagos del mes salen del servidor | `gamificacion-multinivel-f/src/app/pages/admin/pagos-mes/pagos-mes.component.spec.ts` | 2 | **pasa** | Nada: los meses vienen de `GET /commissions/periodos` y el elegido sobrevive a la recarga aunque el servidor ya no lo liste (`ensureMonthOption`). La prueba fija el navegador en 2026-09 y el servidor en 2027, y comprueba que la fuente del componente no tiene `new Date()` ni `Date.now()` |
| 13 | El back office lee la hora del servidor | `gamificacion-multinivel-f/src/app/pages/admin/admin.component.reloj.spec.ts` | 2 | **pasa (tras corregir el producto)** | El mes contable ya venía del servidor, pero `daysSinceLastPurchase()` restaba contra `Date.now()` mientras `orderAgingDays()` ya usaba `relojDelServidorMs`. Con el navegador en 2026-09 y las compras en 2027-04 el `Math.max(0, …)` dejaba toda la lista de clientas en «0 días» y `isColdCustomer` en falso para todas: el síntoma que hizo creer a Alma que nadie compraba. Corregido con una línea |
| 14 | Ningún `*ngFor` sobre un literal; toda tabla con `trackBy` | `gamificacion-multinivel-f/src/app/pages/admin/admin.tablas.spec.ts` | 3 | **pasa (tras corregir el producto)** | La tira de pestañas de reportes iteraba un literal escrito en la plantilla (`admin.component.html:2842`): identidad nueva en cada ciclo de detección de cambios, cinco botones destruidos y recreados sin parar — el sustrato del botón «Ver» que no abre. Y doce tablas dinámicas no declaraban `trackBy` (`pagedCustomers`, `pagedEmployees`, `pagedProducts`, `pagedNotifications` y ocho `<tr *ngFor>` de reportes, Cuadro de Honor y cupones). La lista pasa a la constante `statsReportTabs` con `trackStatsReportTab`; las doce tablas usan `trackFila`. La tira de Pedidos del §3 ya estaba corregida con `orderTabs` |
| 15 | El navegador del arnés vive en la hora del mundo | `sim/lib/comprobar-reloj.mjs`, cableado en `sim/comprobar.sh`; corrección en `sim/lib/persona.mjs` | 1 | **pasa (tras corregir el arnés)** | `abrirNavegador()` nunca tocaba el reloj: medido contra el mundo en pie, el navegador reportaba 2026-09-04 y `GET /__sim/reloj` daba 2027-05-10 — **247.5 días de desvío**. Son los cuatro hallazgos de la ronda 6 que el §4 atribuye al arnés. Corregido con `fijarRelojDelMundo()` (`ctx.clock.setSystemTime`, antes de `ctx.newPage()`); se usa `setSystemTime` y no `setFixedTime` ni `install` porque esas dos congelan el reloj y matarían los temporizadores de la aplicación |

### Cómo se corre

| Suite | Comando | Hoy |
|---|---|---|
| Backend | `cd Micro-lambda-GMF/python && python3 -m pytest -q tests` | **631 pasan** (613 antes de las guardas; 18 nuevas), 0 fallos, 0 xfail |
| Presupuesto de consultas | `cd Micro-lambda-GMF/python && python3 tools/check_query_budget.py` | dentro de presupuesto en los cuatro endpoints vigilados, sin cambios (`GET /dashboard/honor-board` 4/25 viajes, `ORDER_PAID` 28/40) |
| Frontend | `cd gamificacion-multinivel-f && npx ng test --watch=false` | **14 pasan** (12 de guardas + 2 del andamio), ~3 s |
| Tipos | `npx tsc -p tsconfig.app.json --noEmit` y `npx tsc -p tsconfig.spec.json --noEmit` | limpios |
| Paquete | `npx ng build` | compila (solo los avisos `NG8107` y de presupuesto de tamaño, preexistentes) |
| Arnés | `sim/comprobar.sh` (corre `node sim/lib/comprobar-reloj.mjs`) | verde contra el mundo en pie: `2027-05-10T10:51:06Z` en el navegador vs `2027-05-10T10:51:07Z` en el mundo, y el reloj corre |

### Lo que hay que saber para mantenerlas

- **Las guardas muerden.** Se comprobó rompiendo el producto a propósito y restaurándolo: guarda 3
  (`createdAt = ahora` en `_write_row` → 2 fallos), guarda 4 (sin `_reacreditar_volumen_del_pedido` → 3 fallos),
  guarda 6 (sin leer `saveShippingAddress` → 3 fallos), guarda 9 (descontar `body.stockId` y quitar el 403 de
  sucursal → 2 fallos), guarda 15 (con `fijarRelojDelMundo` neutralizado, el comprobador sale con código 1 y
  247.5 días de desvío). No son pruebas que pasen por decorado.
- **Las guardas 11 y 14 son estructurales**: leen las plantillas del repositorio con `node:fs`. Como el proyecto
  no instala `@types/node` y `tsconfig.app.json` declara `types: []`, `src/testing/node-builtins.d.ts` aporta las
  firmas mínimas de `node:fs`/`node:path`. Son solo declaraciones: no entran al paquete de la aplicación.
- **Guarda 15 y el día del mundo**: el arnés toma la hora del mundo **al abrir** el navegador. Si una ronda mueve
  la fecha con `dia.sh` a mitad de sesión, hay que cerrar y volver a abrir el navegador para que la persona vea
  el día nuevo. Queda escrito en `sim/protocolo.md`.
- Las dos únicas pruebas del backend que pueden saltarse (`test_metas.py`, `test_infraestructura.py`) son
  condicionales preexistentes y no son guardas de este informe; hoy no se saltan.
