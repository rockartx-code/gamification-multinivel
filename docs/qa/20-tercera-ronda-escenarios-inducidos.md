# 20 · Tercera ronda: correcciones pendientes y escenarios inducidos

Continuación de [18](18-simulacion-multinivel.md) y [19](19-analisis-negocio-y-correcciones.md). Mismo mundo simulado (backend real de 8 Lambdas sobre tabla en memoria, frontend real, correo interceptado, reloj propio), mismas personas. Fechas simuladas: 12 al 15 de noviembre de 2026, y cierre en diciembre.

Método de esta ronda:

- Primero se aplicaron las correcciones que habían quedado pendientes de la ronda anterior (§2).
- Después se lanzaron agentes-persona con **desencadenantes inducidos**: cada uno recibió una situación concreta (un pedido que llega dañado, una socia que no ha comprado en el mes, un cliente que quiere pagar en sucursal) pero ninguna instrucción de uso de la plataforma.
- Máximo dos navegadores a la vez (el contenedor se reinició dos veces por memoria en la ronda anterior).
- **Ninguna afirmación de un agente cuenta hasta verificarla en la API.** Cuando un agente dijo "quedó guardado", se leyó el registro; cuando dijo "no hay botón", se comprobó el bundle o se reprodujo a mano. En esta ronda los agentes no inventaron resultados; en dos casos (Sofía, 12-nov) lo que parecía error del agente resultó ser un defecto real.

## 1. Resumen ejecutivo

| | |
|---|---|
| Escenarios inducidos ejecutados | 13 turnos de agente (Nadia ×3, Beto ×2, Sofía ×4, Verónica, Claudia, Lupita, Rosa Elena) más acciones de operación por API (entregas de Estafeta, correcciones de datos por "sistemas") |
| Bugs de producción encontrados y corregidos en esta ronda | 18 (§4), tres de ellos graves: VP negativo al cancelar un pedido no pagado, pedidos de recoger en tienda pagados en línea que nunca pasaban a pagados, y recepción de devolución que aprobaba sin inspeccionar |
| Hallazgos de negocio nuevos | 10 (§5) |
| Cobertura de rutas del frontend | 71 de 77 alcanzadas; las 6 restantes son código muerto (no hay pantalla que las llame). La única ruta viva que faltaba (`/auth/resend-email-confirmation`) resultó inalcanzable por un bug y se corrigió (§3.8, §6) |
| Pruebas del backend | 142 en verde (eran 137 al empezar la ronda) |

## 2. Correcciones aplicadas antes de lanzar los agentes

Pendientes de la ronda anterior, todas verificadas con `tsc` y `pytest`:

| Pendiente | Qué se hizo |
|---|---|
| Folio del pedido no visible en las filas del back office | Folio en cada fila |
| Producto retirado sin forma de borrarlo | Botón rojo "Eliminar producto definitivamente" (gated por `product_delete`) |
| Recepción de transferencias sin explicación | Texto de ayuda en la pantalla |
| Corte de caja con copy confuso | Copy nuevo |
| Comprobante de depósito sin botón | Botón "Ver comprobante" en el panel del socio |
| `verifyEmail` con fallback a una ruta que no existe | Eliminado el fallback |
| Alta manual de cliente sin acceso | Crea el acceso con contraseña temporal y la manda por correo; correo editable en la ficha (409 si ya existe) |
| Envío gratis sin regla | `shipping.freeShippingMin` en configuración; el backend lo aplica (`shippingFreeApplied`) y el carrito lo muestra |
| Panel del socio sin cómo pedir ayuda | Bloque de ayuda con WhatsApp y correo |
| Pickup con pago en sucursal mostraba MercadoPago | Bloque propio en el seguimiento |
| Tarifas de envío duplicadas | Dedupe por paquetería, servicio y precio |
| Ficha de empleado sin nombre ni celular editables | Campos y guardado; el backend ignoraba `phone` (defecto real) |
| "Documento asociado correctamente" con la ficha vacía | Falso positivo del entorno: la tabla en memoria de las pruebas no entendía `list_append`. Corregida la tabla; el backend real estaba bien |

## 3. Escenarios inducidos y lo que pasó

Cada fila: qué se indujo, qué hizo la persona, qué se verificó en la API y qué salió.

### 3.1 Recoger en tienda con pago en sucursal (Nadia, 13-nov)

Guadalupe R. llega a Tienda Del Valle a pagar en efectivo su pedido de 3 Naplus ($840) con un billete de $1,000. Nadia estaba ligada a Bodega Central; Sofía la ligó también a Del Valle.

- Encontró sola el pedido en el POS ("1 pedido pendiente de pago en sucursal"), cobró en efectivo y entregó. Verificado: pedido `delivered`, venta `SALE-78BBDB57` ligada al pedido, Naplus 10→7 en Del Valle, $840 de volumen a la clienta, corte de caja registrado.
- **Hueco**: el modal "Recibir pago en sucursal" solo pedía la forma de pago; calculó los $160 de cambio de cabeza. Corregido: efectivo recibido, cambio en pantalla, rechazo si falta dinero, guardado en la venta.
- **Hueco**: un señor quiso registrarse para "que le cuenten los puntos" y el botón "Nuevo cliente" del POS estaba oculto porque Nadia no tenía `customer_add`, sin decirle qué le faltaba. Corregido: aviso con el nombre del permiso. Sofía se lo concedió al día siguiente.
- Boom con existencia 0 en Del Valle: correcto, nunca se había transferido. Sofía transfirió 10 y Beto los recibió.
- Duda operativa sin respuesta en pantalla: "¿qué hago físicamente con los $840 del corte?"

### 3.2 Despacho de seis pedidos pagados (Beto, 13-nov)

Tres pedidos del 12-nov y **tres de octubre que llevaban 42 días pagados sin enviar** (dos de Verónica, uno de Rosa Elena). Nadie los había notado: el back office no alerta pedidos pagados sin guía.

- Beto verificó existencias, registró los seis envíos con guía y todos quedaron `shipped` con correo "va en camino". Bodega descontada (Naplus 25→18, Colágeno 29→24).
- **Hueco**: el formulario de envío no tenía campo de paquetería; escribió "Estafeta EST-MX-…" dentro de la guía. Corregido: selector de paquetería precargado con la que eligió el cliente al pagar, guía limpia, `shippingCarrier` guardado al enviar.
- Notó que un pedido "cambió solo" de Pendiente a Entregada: era Nadia cobrándolo en Del Valle. El back office no dice quién movió cada pedido.

### 3.3 Activación tardía y reevaluación en vivo (Verónica, 13-nov)

Verónica no había comprado en noviembre y su panel mostraba **$379.90 bloqueadas** con el tooltip "si te activas dentro del mismo mes, se recalculan". Compró $1,220 (23 VP).

- Antes de comprar, por error duplicó cantidades y **canceló un carrito de $1,952 que nunca pagó**. Resultado: VP −13.8, "te faltan 33.8 VP", última en el Cuadro de Honor con −14 VP, comisiones sin recalcular.
- **Bug grave**: la corrección de la ronda 2 ("al cancelar se resta el volumen una sola vez") restaba aunque el pedido nunca se hubiera acreditado. Verificado en la API: `netVolume −732`, `VP −14.64` con un pedido pagado de $1,220. Corregido: `ORDER_PAID` marca `rewardsAppliedAt`; la anulación solo resta si hay esa marca o evidencia de pago; todo pedido pagado guarda `paidAt`. Regresión en pruebas.
- Datos de Verónica corregidos por "sistemas" (`/__sim/patch`) y reevaluación relanzada: en segundos sus $172 (Memo, comprimido) y $138.60 (Bety) pasaron de bloqueadas a pendientes; los $69.30 de Lupita (2ª generación) siguen bloqueados por requisito de generación. Al día siguiente, con las entregas, $310.60 pasaron a confirmadas en vivo.
- Se quejó (con razón) de los 42 días de sus pedidos de octubre. "Ver comprobante" del depósito de octubre abre el archivo en pestaña nueva; en la simulación la URL de S3 no existe, así que no se pudo validar aquí.

### 3.4 Activación con presupuesto corto y cupones (Claudia, 13-nov)

Claudia ve **$172 bloqueadas** por la compra de su hermano Memo y tiene $600. Probó `GRACIAS50` (aplicó, −$50, y bajó los VP del pedido de 8 a 7 como debe) y `NAVIDAD100` ("Cupón expirado", correcto). Compró 1 Biotina, $350, 7 VP, para recoger en Tienda Del Valle pagando en línea.

- **Bug grave**: pagó en la pasarela y el pedido se quedó "Pago pendiente" sin correo. El webhook de MercadoPago (sin usuario) recibía 403 "no vinculado a la sucursal de entrega": la regla de operador ligado a la sucursal se aplicaba también a la pasarela. **Todo pedido de recoger en tienda pagado en línea se quedaba pendiente para siempre.** Corregido (la regla queda solo para pago en sucursal y para la entrega), pago reprocesado, pedido pagado con correo.
- Con 7 VP sigue inactiva y sus $172 siguen bloqueados. Hallazgo de negocio en §5.

### 3.5 Producto dañado y devolución (Lupita 14-nov, Beto 14-nov, Sofía 15-nov)

Lupita recibe su pedido con el bote de Colágeno con la tapa rota. Quiere cambiar solo ese producto.

- Encontró "Solicitar devolución" en 3 pantallas, subió fotos, folio `RET-671AA6F5`, pedido `en_devolucion`, envío a cargo de la empresa (motivo daño). Verificado.
- **Hueco**: la devolución es del pedido completo, no hay selección por producto; lo explicó en "Descripción adicional".
- **Hueco**: el correo "Recibimos tu solicitud" decía "envía el paquete a nuestro almacén" sin dirección. Corregido: dirección de la bodega principal y qué mandar.
- Beto recibió el bote (tapa rota, **sello abierto, falta un tercio del polvo**) y el sistema respondió "Paquete recibido. Devolución validada". **Bug de proceso**: el modal "Recibir paquete" mandaba el checklist de inspección todo en verde; recibir era aprobar, y no había dónde escribir cómo llegó. Corregido: el modal muestra el checklist (coincide, trazabilidad, empaque, sello, sin uso, daño ajeno) con notas; el backend calcula el resultado y usa las notas como motivo si rechaza.
- Consecuencia inmediata verificada: la validación anuló en vivo la comisión de Bety ($138.60) y la fila de 2ª generación de Verónica, pero **no restó el volumen de Lupita** (27.72 VP con una devolución validada): la nueva guardia de `rewardsAppliedAt` no reconocía pedidos pagados antes de que existiera la marca. Corregido (reembolsos y devoluciones siempre restan; solo la cancelación de un pedido nunca pagado queda fuera), volumen reprocesado a 0.
- Sofía rechaza la devolución en su turno 15 (sello abierto y consumido) con cortesía del 20%: ver §3.8.

### 3.6 De invitada a cuenta (Rosa Elena, 14-nov)

Rosa Elena compró dos veces sin cuenta; su pedido de octubre llevaba seis semanas sin llegar y sin correos (los pedidos de invitado de septiembre no guardaban correo; eso ya se había corregido para los nuevos).

- No encontró ninguna forma de rastrear su pedido tecleando el folio. Corregido: bloque "¿Compraste sin cuenta? Rastrea tu pedido" en la pantalla de entrar.
- Creó su cuenta sin tropiezos (activación por correo al instante; "Reenviar confirmación" no hizo falta). Su panel: "Aún no tienes órdenes registradas". Corregido en el backend: al crear cuenta se ligan los pedidos de invitado con el mismo correo; los suyos se ligaron a mano porque no tenían correo.
- En móvil el modal de avisos tapó el botón "Explicar estados de orden".

### 3.7 Back office (Sofía, 12 y 14-nov)

- 12-nov: reasignó la red de Marcela a Verónica y dio de baja a Marcela (verificado). Reportó que no había botón para borrar el Gel ni bloque "Acceso a panel admin" en la ficha de Verónica. **No era error del agente**: `product_delete` no existía en el catálogo de privilegios del backend (`_normalize_privileges` lo descartaba al guardar, así que ningún empleado podía borrar productos aunque el panel tuviera el botón), y el bloque de privilegios de cliente existía en el componente pero nunca se pintaba (ruta `/customers/{id}/privileges` inalcanzable). Ambos corregidos.
- 14-nov: dio a Nadia `customer_add`; borró el Gel ("Producto eliminado", catálogo 13→12→11 con el retiro previo); dio a Verónica acceso al panel con "Ver Clientes" y "Ver Cuadro de Honor" (primera vez que se toca `/customers/{id}/privileges`); dejó la nota de compensación; creó la transferencia de 10 Boom. Dudas: si "Acceso a panel admin" es obligatorio (ahora la pantalla lo explica) y por qué las transferencias no mostraban folio (ahora lo muestran).

### 3.8 Turnos del 15-nov

- **Sofía rechaza la devolución** (RET-671AA6F5) con el motivo completo (sello abierto, producto consumido, cortesía del 20%). Verificado: pedido `devolucion_rechazada`, correo "Devolución no procedente" a Lupita a las 10:07 con ese motivo. Encontró que la ficha del pedido no mostraba las fotos ni las notas de la recepción (estaban en la solicitud, no en el pedido) y que no hay bitácora de avisos enviados al cliente. Corregido lo primero: la ficha muestra estado, motivo del cliente, sus fotos, las notas y fotos de la recepción, el checklist y el motivo del rechazo. Lo segundo queda en §5.
- **Nadia entrega, da de alta y cobra**: la entrega del pedido de Claudia (recoger en Del Valle, pagado en línea) falló con "Stock insuficiente para el producto Biotina": Del Valle tenía 0. **Bug**: el checkout deja elegir una sucursal sin existencia; la clienta paga y el mostrador no puede entregar. Corregido: el backend rechaza el pedido de pickup y dice qué producto falta. Para Claudia, transferencia de 5 Biotina, recepción y entrega (por API, como acciones de operación); los $35 de Verónica por esa compra pasaron a confirmados. Con su permiso nuevo dio de alta a Roberto desde el POS ("Cliente creado y seleccionado en POS", cliente 1794737118037) y le vendió 2 Boom (POS-6947D029); no pudo decirle cuántos VP ganó porque el POS no los muestra. Bety quiso pagar mitad efectivo y mitad tarjeta: no existe pago mixto; "Pago parcial" pide un código de autorización que la cajera no tiene y la pantalla no decía a quién pedírselo (ahora lo dice). El corte de caja apareció deshabilitado sin explicación (ahora explica que se habilita con ventas desde el último corte).
- **Reenviar confirmación**, la única ruta viva que ningún agente había tocado, se reprodujo a mano con una cuenta sin confirmar: el botón **nunca aparecía**. El frontend comparaba el texto del error con el del backend y difería en un acento ("sesion" / "sesión"). Corregido con un código de error (`EMAIL_NOT_VERIFIED`); verificado: botón visible, segundo correo de activación en el buzón, ruta registrada.
- Al crear una transferencia por API con el campo equivocado, el backend aceptó una transferencia vacía. Corregido: exige origen, destino distinto y al menos un producto.

### 3.9 Día de pago (Sofía, 10-dic)

- Encontró en Clientes (y en la advertencia de Estadísticas, "1 comisiones pendientes por depositar") a la única socia con comisión de noviembre: Verónica, $393.60, con CLABE. Subió el comprobante ("Comprobante cargado"). Verificado: noviembre `paid` con comprobante y correo "Depositamos tus comisiones de 2026-11: $393.60".
- Los $172 bloqueados de Claudia **desaparecen sin rastro** al cerrar el mes: su ficha dice "Mes anterior: $0 — Sin movimientos". Es el comportamiento del plan (no se activó en el mes) pero nadie se lo explica (§5.9).
- El Cuadro de Honor no tenía selector de mes: en diciembre ya no se podía ver el ranking de noviembre. Corregido (selector y parámetro `month`).
- Quiso desactivar a la empleada duplicada "Veronica Sandoval Ruiz TEST": no había botón, y al desmarcar "Acceso a panel admin" el servidor respondía `true` y no persistía. **Bug**: el PATCH de empleados ignoraba `canAccessAdmin`. Corregido, y la ficha tiene ahora "Desactivar / Reactivar empleado".
- No aparece folio del depósito en pantalla (solo "Comprobante cargado"); anotado.

## 4. Bugs de producción corregidos en esta ronda

| # | Gravedad | Dónde | Qué pasaba | Corrección |
|---|---|---|---|---|
| 1 | Grave | Motor de comisiones | Cancelar un pedido nunca pagado restaba su volumen: VP negativo, socia inactiva sin poder desbloquear | Solo se resta lo acreditado (`rewardsAppliedAt`/evidencia de pago); `paidAt` en todo pedido pagado |
| 2 | Grave | Pedidos | Pickup pagado en línea se quedaba pendiente: el webhook de la pasarela recibía 403 por la regla de operador ligado | La regla aplica solo a pago en sucursal y a la entrega |
| 3 | Grave | Devoluciones | "Recibir paquete" aprobaba la devolución con el checklist en verde y sin notas | Checklist real con notas; resultado calculado en el backend |
| 4 | Media | Motor | Devoluciones/reembolsos de pedidos anteriores a la marca no restaban volumen | Reembolso y devolución siempre restan; solo la cancelación no pagada queda fuera |
| 5 | Media | Privilegios | `product_delete` no existía en el backend: nadie podía borrar productos | Agregado al catálogo |
| 6 | Media | Ficha de cliente | Bloque de acceso al back office nunca se pintaba | Bloque plegado bajo `user_manage_privileges`; el backend expone `canAccessAdmin` y `privileges` |
| 7 | Media | Empleados | El backend ignoraba `phone`; la ficha no dejaba editar nombre ni celular | Campos y PATCH |
| 8 | Media | Cuentas | El historial de invitado se perdía al crear cuenta | Se ligan los pedidos por correo al crear la cuenta |
| 9 | Baja | POS | Cobro de pickup sin efectivo recibido ni cambio | Efectivo recibido, cambio, validación |
| 10 | Baja | Envíos | Sin campo de paquetería; la guía se contaminaba | Selector de paquetería y `shippingCarrier` |
| 11 | Baja | Correos | Correo de devolución sin dirección del almacén | Dirección de la bodega principal |
| 12 | Baja | Seguimiento | Sin cuenta no había dónde teclear el folio | Bloque de rastreo en la pantalla de entrar |
| 13 | Grave | Checkout | Se podía pagar un pedido para recoger en una sucursal sin existencia | Validación de existencia por sucursal al crear el pedido |
| 14 | Media | Login | "Reenviar correo de confirmación" nunca aparecía (comparación de textos con acento distinto) | Código `EMAIL_NOT_VERIFIED` del backend |
| 15 | Baja | Devoluciones | La ficha del pedido no mostraba fotos, notas ni checklist de la devolución | `returnInspection` en el detalle para admin/empleado |
| 16 | Baja | Transferencias | Se aceptaban transferencias sin productos | Validación |
| 17 | Media | Empleados | El PATCH ignoraba `canAccessAdmin`; no había forma de desactivar a un empleado | Campo guardado y botón "Desactivar / Reactivar" |
| 18 | Baja | Cuadro de Honor | Solo el mes en curso; el ranking de un mes cerrado no se podía consultar | Selector de mes y `?month=` |

Además, en el entorno de simulación: la tabla en memoria no entendía `list_append` (falso "documento no guardado") y el script de cobertura contaba como nunca tocadas rutas con query string.

## 5. Hallazgos de negocio

1. **Pedidos pagados sin enviar no se alertan.** Tres pedidos llevaban 42 días pagados y nadie lo vio hasta que la socia se quejó. Propuesta: en el tablero del back office, "pagados con más de 3 días sin guía", con contador y correo diario a la gerente.
2. **La activación de 20 VP (≈ $1,000/mes) deja fuera al socio pequeño.** Claudia tiene $600 al mes; su hermano compró $1,720 bajo ella y sus $172 se quedan bloqueados. Propuestas: activación escalonada (10 VP desbloquea 1ª generación al 50%, 20 VP el 100%), o contar la compra del mes anterior si fue mayor a 40 VP.
3. **Devolución parcial.** Lupita quería cambiar un bote de tres productos y la plataforma solo devuelve el pedido completo; con la validación se le anuló todo el volumen. Propuesta: devolución por línea (producto y cantidad), con reembolso y resta de volumen proporcionales.
4. **Custodia del efectivo.** El corte de caja registra un número y no dice a quién se entrega. Propuesta: el corte pida "efectivo entregado a" y genere el retiro en el mismo paso.
5. **Los puntos en el mostrador.** El POS muestra PC por producto pero no le dice al cliente de mostrador cuántos VP suma su compra; el argumento "regístrate para que te cuenten los puntos" lo hace la cajera de memoria. Propuesta: ticket con VP acumulados del mes y lo que falta para el siguiente descuento.
6. **Pago mixto en mostrador.** Bety quiso pagar mitad efectivo y mitad tarjeta; el POS solo admite una forma de pago (o "pago parcial" con saldo pendiente y código de gerente). Propuesta: dos formas de pago por venta, con el efectivo a caja y la tarjeta a terminal.
7. **Bitácora de avisos al cliente.** Sofía rechazó una devolución y no pudo confirmar que el aviso salió. Propuesta: guardar cada correo enviado (asunto, fecha, destino) y mostrarlo en la ficha del cliente y del pedido.
8. **Comisiones bloqueadas que se esfuman.** Al cerrar noviembre, los $172 de Claudia desaparecen de todas las pantallas. Propuesta: mostrarlos en el mes anterior como "no pagadas: no te activaste en noviembre" con el monto, en el panel de la socia y en su ficha, y un correo el día 25 a quien tenga comisiones bloqueadas y le falten VP ("te faltan 13 VP para cobrar $172").
9. **Folio del depósito.** El registro del pago solo dice "Comprobante cargado". Propuesta: folio y fecha visibles en la ficha y en el correo.
10. **Trazabilidad de quién movió qué.** Beto vio un pedido cambiar solo. Propuesta: bitácora por pedido (quién, cuándo, desde qué sucursal) visible en la ficha del pedido.

## 6. Cobertura de rutas

`python3 sim/cobertura.py` (ya corregido para ignorar query strings y aceptar `{x}` vacío) al cierre de la ronda:

- Rutas que expone el frontend: 77 · alcanzadas: 71 · nunca tocadas: 6.
- Código muerto (ninguna pantalla las llama, y el API Gateway no las enruta): `GET /admin/dashboard`, `POST /assets`, `GET /cart`, `GET /user-dashboard`, `POST /commissions/request`, `POST /commissions/receipt`. Las dos últimas son la solicitud de pago y el comprobante del socio, que la operación decidió hacer automáticos (depósito con CLABE en el día de pago); sus métodos en el frontend nunca se conectaron a un botón. Propuesta: borrarlas del cliente.
- `/auth/resend-email-confirmation`: la confirmación llegó al instante en todos los registros de la simulación, así que ninguna persona necesitó reenviarla. Al ejercitarla a mano resultó inalcanzable (§3.8, bug 14); ya corregida y alcanzada. Con eso, **71 de 77** rutas alcanzadas y las 6 restantes son código muerto.

## 7. Pendiente

- Devolución parcial (§5.3) y alerta de pagados sin enviar (§5.1) son cambios de producto, no correcciones; quedan como propuesta.
- "Ver comprobante" del depósito solo se puede validar en producción (S3 real).
- El modal de avisos en móvil tapa botones del panel del socio: revisar orden de capas en la siguiente ronda visual.
