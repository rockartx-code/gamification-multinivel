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
