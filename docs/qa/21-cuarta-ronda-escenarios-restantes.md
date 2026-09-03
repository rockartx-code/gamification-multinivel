# 21 · Cuarta ronda: los escenarios que faltaban

Continuación de [20](20-tercera-ronda-escenarios-inducidos.md). Mismo mundo simulado y mismas personas. Mes vivo: **diciembre de 2026** (noviembre ya cerró y se pagó el día 10). Objetivo: cubrir con desencadenantes inducidos todo lo que las tres rondas anteriores no habían tocado (lista al final de la ronda 3).

Reglas de esta ronda, iguales a la anterior: máximo dos navegadores a la vez, ninguna instrucción de uso, y nada cuenta hasta verificarlo en la API.

## 1. Resumen ejecutivo

_(Se completa al cerrar la ronda.)_

## 2. Escenarios y resultados

### 2.1 Compra grande, descuento por tramo y acceso al back office (Verónica, 12-dic)

Verónica compra para ocho clientas y quiere ver cuánto le descuentan; después entra al back office con el acceso que Sofía le dio el 14-nov (Ver Clientes, Ver Cuadro de Honor).

- Pedido 1: subtotal $3,140, **30%** (−$942), envío gratis, total $2,198. Pedido 2 (2 Biotina, $800): **20%**, envío $129, total $769. Verificado: la regla es "acumulado del mes más el pedido en curso" ($2,198 + $800 no llega a $3,000). Correcta, pero mal explicada: el carrito llamaba "Nivel base" al 20% y "Nivel 1" al 30%, mientras las metas del panel hablan de "nivel 1 (10%) / nivel 2 (20%)". Corregido: los niveles del carrito siguen los tramos del plan (1 = 10% … 4 = 40%).
- **Bug de producción**: en el back office, "Clientes" salía vacío con 403 en `/customers/getall` y `/dashboard/admin/warnings`. `_require_admin` solo aceptaba rol admin o empleado; una socia con `canAccessAdmin` y privilegios era rechazada en todo (el Cuadro de Honor abrió porque no exige privilegio). Corregido: la sesión guarda la marca y el actor se trata como empleado con sus privilegios. Regresión en pruebas.
- Cuadro de Honor con el selector nuevo: diciembre (Verónica 91 VG / 54 VP, Memo, Claudia) y noviembre (Verónica 98 / 23, Bety, Claudia). Verificado.
- Recibió dos correos idénticos "Guillermo Ibarra Ponce compró: comisión de $195.20 en camino" a la misma hora. **Bug**: la compra de Memo lo activó a él mismo y la reevaluación volvió a repartir el mismo pedido; la fila del ledger era una sola, el aviso salió dos veces. Corregido: el aviso solo sale cuando la fila es nueva.

### 2.2 Compra bajo patrocinadora inactiva y cancelación de un pedido pagado (Memo, 12-dic)

- Pedido 1 (2 Boom + 2 Finding Pro): $2,440 con 20% → $1,952, envío gratis, 36.8 VP. Verificado en el motor: **Claudia (inactiva) $195.20 bloqueados con `no_califica_gen`; Verónica (activa) $195.20 pendientes** por compresión dinámica. La reversión se prueba cuando Claudia se active (§2.x).
- Pedido 2 (Keto, $729 con envío) pagado y **cancelado por Memo desde el seguimiento**: "Orden cancelada … El reembolso está siendo procesado por nuestro equipo", correo "te reembolsaremos el importe completo". Verificado: `cancelled` con `pendingRefund`, volumen restado (2,552 → 1,952), `rewardsVoidedAt`. Hueco: ni pantalla ni correo dicen plazo ni medio del reembolso.
- **Bug**: la cantidad tecleada junto a "Agregar a carrito" en el panel escribía directo en el carrito y el botón sumaba una unidad más (2 → 3, 1 → 2), dos veces en el mismo turno. Corregido: el campo es un borrador y el botón agrega esa cantidad.
- Su panel muestra a Claudia como patrocinadora con WhatsApp, su link `GUILLERMO-GIP`, y subió al #2 del Cuadro de Honor.

### 2.3 Gestión de catálogo, cupón con tope, reembolso y código del POS (Sofía, 12-dic)

El primer intento se perdió con un reinicio del contenedor (dos navegadores abiertos); persistieron el reembolso, el cupón y el código del POS, y el resto se repitió en un segundo turno. Desde aquí, un solo navegador a la vez.

- Reembolso del pedido cancelado de Memo: `refunded`, correo "Reembolso realizado". Cupón `DIC50` creado con compra mínima $1,000 y un solo uso (verificado). Código de autorización del POS configurado (7412) y enviado a Nadia.
- Catálogo: categoría "Descanso" nueva, producto "Magnesio Glicinato 120 caps" ($520, 10 PC) con tres imágenes, marcado como producto del mes; campaña "Navidad 2026" activa. Verificado en la API. Hueco: la campaña no tiene fechas de vigencia; las escribió en el texto.
- Buscó "evaluar bonos / rangos" y no existe pantalla: los bonos se evalúan solos en cada compra pagada; la ruta manual del cliente es código muerto. Nadie tiene rango (BRONCE exige 4,500 VG; la red completa suma 91).
- El tablero ya avisa "4 pedidos pagados sin envío (Importante)"; falta la antigüedad de cada uno (propuesta 5.1 de la ronda 3, parcialmente cubierta).
- Recibió "comisión de $60 en camino" por el pedido que Memo canceló minutos después y ningún aviso de que se anuló. Corregido: correo "Comisión anulada" con el motivo al anular filas pendientes o confirmadas.

### 2.4 Activarse "comprando lo que usas" y la comisión que desapareció (Bety, 12-dic)

Verónica le pide a Bety que se active en diciembre; Bety además quiere saber por qué su comisión de noviembre por la compra de Lupita ya no aparece.

- Noviembre en su panel: "Sin movimientos este mes" y tres correos idénticos "Guadalupe compró: comisión de $138.60 en camino" (el duplicado ya corregido) sin ningún aviso posterior. **Hueco**: la validación de la devolución de Lupita borró la fila del ledger; al rechazarse después la devolución, la comisión ya no existía. Corregido en dos partes: las filas anuladas se conservan como "Anulada" (estado previo, fecha y motivo, fuera de los totales) y el patrocinador recibe "Comisión anulada" con el motivo (§2.3).
- Compró Colágeno + Longevit: $1,090, 10% de descuento, envío $129, total $1,110 (verificado). El catálogo anuncia 13 + 7 = 20 PC, pero la activación cuenta VP netos: 18. **No quedó activa por 2 VP** comprando justo lo recomendado. El carrito ya mostraba "18 VP" pero sin relacionarlo con la meta. Corregido: aviso "con este pedido llegas a 18 de 20 VP" también sin cupón. Hallazgo de negocio en §4.
- El envío se cobró porque el mínimo de envío gratis ($1,000) se mide sobre el total con descuento ($981). Regla válida, pero nadie la explica (§4).
- El endpoint mensual devolvía 19.6 VP (pesos ÷ 50) mientras la activación usa 18 (PC netos). Corregido: un solo valor.
- Su panel muestra a Lupita "Inactiva" y el aviso de compresión dinámica ya existente.

### 2.5 Cupón con mínimo y tope, y compra bajo la patrocinadora reasignada (Patricia, 12-dic, móvil)

Patricia fue reasignada de Marcela a Verónica en noviembre. Quiere usar `DIC50` (mínimo $1,000, un solo uso) y compra colágeno y un Naplus para su sobrina.

- **Bug**: desde el celular no existía dónde escribir el cupón: el bloque solo estaba en el resumen de escritorio y el cajón "Ver resumen" no lo tenía. Pagó dos pedidos sin cupón ($700 y $280). Corregido: cupón, VP del pedido y aviso de activación también en el resumen móvil.
- Comisiones tras el cambio de patrocinador, verificadas: Verónica recibe $70 y $28 pendientes (G1) y Marcela no aparece en ningún lado. El panel muestra a Verónica como patrocinadora con su WhatsApp.
- Quedó a 1 VP de activarse (19 PC sin descuento). El "Recoger en sucursal" le mostró Bodega Central (CDMX); la API devuelve también Tienda Del Valle, así que probablemente no desplazó la lista en el móvil; anotado sin confirmar.
- El primer código de recuperación de contraseña "inválido": pidió dos y el segundo invalida al primero (diseño; Claudia vivió lo mismo). Propuesta en §4.

### 2.6 Activación de las directas y 2ª generación (Bety, Patricia y Lupita, 12 y 13-dic)

- Bety y Patricia compraron un Naplus cada una tras el aviso de que les faltaban 2 y 1 VP. Verificado: 23.4 y 24.4 VP, activas; el carrito ya dice "Puntos de este pedido 5.4 VP · Te faltan 0 VP". Patricia probó `DIC50` desde el celular: "Requiere subtotal mínimo de $1000" (correcto y claro). Detalle: Patricia vio el modal "¡Buen trabajo! Meta cumplida" y Bety no; el modal depende de que la meta estuviera marcada como leída.
- **2ª generación cubierta.** Con Bety y Patricia activas, Verónica cumple el requisito de dos directas activas: la compra de Lupita (bajo Bety, $990 netos) dejó **$99 pendientes a Bety (G1) y $49.50 pendientes a Verónica (G2)**, verificado en el ledger. Es la primera comisión de segunda generación de todo el ejercicio.
- Lupita vio el aviso nuevo del carrito ("Con este pedido llegas a 18.9 de 20 VP: te faltarían 1.1 VP") y compró igual; queda inactiva por 1.1 VP.
- **Hueco de proceso**: en noviembre se le prometió "20% en tu próximo bote" en el correo de rechazo; nadie emitió nada y el carrito no tenía cómo aplicarlo. Corregido: al rechazar una devolución la gerente puede indicar una cortesía en %, que se convierte en un cupón personal de un solo uso (60 días) y viaja en el correo; los cupones admiten ahora `customerId` y rechazan a otro cliente ("Este cupón es personal"). A Lupita se le emitió el suyo por sistemas y soporte se lo mandó.

### 2.7 Punto de venta: pago parcial, código de autorización, retiro y saldo (Nadia, 13-dic)

- Primer intento: el código 7412 fue rechazado en pago parcial y en retiro ("Codigo de autorizacion incorrecto", cinco veces). Causa: el turno de Sofía que lo fijaba se perdió con el reinicio del contenedor y quedó el código anterior; se fijó por API como acción de Sofía. Mientras tanto vendió un Klinhart de mostrador con cambio calculado ("Cambio: $520 sobre un total de $480") e hizo el corte dejando $500 de fondo ("Se retirará $820"). El Magnesio nuevo no tenía existencia en Del Valle: hueco operativo (nadie lo transfirió), no de plataforma.
- Segundo intento, con el código correcto: **pago parcial** de Roberto (2 Boom, $500 en efectivo, "Saldo pendiente $340", folio POS-D7F97B91), **retiro** "entrega a gerencia" ("Retiro registrado") y **corte** ("Corte de caja registrado"). Verificado en la API.
- **Hueco de producto**: cuando Roberto volvió a liquidar, no existía ninguna acción para cobrar el saldo de una venta con pago parcial; el "$340 pendiente" solo se veía al cobrar. Corregido: nueva ruta de abonos; la tarjeta de la venta muestra "Saldo pendiente" y "Cobrar saldo"; el abono entra a caja como cobro (efectivo al corte, tarjeta no) y cierra la venta al llegar a cero. En el siguiente turno Nadia no encontró el botón: la venta ya estaba dentro de un corte cerrado y ahí las filas son texto. Se agregó la sección "Saldos pendientes" (todas las ventas con saldo de la sucursal, estén o no en un corte) y en el cuarto turno liquidó los $340 con tarjeta: "Abono registrado. Venta liquidada.", efectivo intacto, abono visible en Tarjeta. Verificado en la API (venta `paid`, abono aparte con `source=settlement`).

### 2.8 Clientes fríos desde la plataforma (Ivonne, 14-dic)

Ivonne revisó las 16 fichas cruzando ficha, las siete pestañas de Pedidos y Estadísticas. Fríos: Rosa Elena (2-oct), Rodrigo (3-sep), Tomás (nunca) y Guadalupe R. (pedido de sucursal sin pagar). Karla ya estaba en "No contactar" y no se le escribió. Dejó nota en cada ficha y avisó a Verónica de sus dos referidos fríos; verificado en la API.

- Le faltó lo mismo que en octubre: "última compra" a simple vista, un filtro "sin compra en X días" y exportar la lista. Corregido: la lista trae "Última compra · N días" (último pedido pagado del historial por cliente), filtro "Solo fríos (30+ días)" y "Exportar CSV".
- Dos fichas sin teléfono (Guadalupe R., Tomás): el registro no lo exige. Propuesta en §4.
- La columna "Mes anterior" de la lista se refiere a comisiones, no a compras; con "Última compra" al lado deja de confundir.

### 2.9 Reactivación por WhatsApp (Rosa Elena, 14-dic, móvil)

Tras el mensaje de Ivonne, Rosa Elena entra, ve por fin sus dos compras de invitada ligadas a su cuenta y compra otro Colágeno ($829 con envío) pidiendo que se lo lleven en persona. Verificado: pedido pagado y las tres órdenes en su panel.

- La "entrega personal" existe solo del lado del almacén; el cliente no puede pedirla al comprar (Ivonne lo resuelve avisando a bodega). Propuesta en §4.
- Su panel no dice quién es su coach: muestra "Patrocinador: FindingU" y el WhatsApp genérico de soporte, no a Ivonne. Propuesta en §4.

### 2.10 Despacho de diciembre con entrega personal (Beto, 14-dic) y entregas (16-dic)

- Beto despachó los diez pedidos pagados de diciembre: nueve con guía Estafeta y el de Rosa Elena como **entrega personal** (lugar, fecha y nota "la lleva Beto en persona"), primera vez que se usa esa modalidad. Verificado en la API. Bodega Central quedó holgada; el Magnesio nuevo tiene 0 en ambos almacenes: tras el alta nadie registró la entrada de inventario (hueco operativo).
- Encontró el pickup de Claudia de noviembre todavía "Pagada": la entrega del 15-nov y la transferencia de Biotina se habían perdido con un reinicio del contenedor (el simulador guardaba el estado solo al cambiar el reloj). Se repitieron por API y el simulador ahora guarda tras cada escritura.
- 16-dic: Estafeta entrega los nueve y Beto la personal. Las comisiones de diciembre pasaron a confirmadas en vivo: Verónica $491.20 (con los $49.50 de 2ª generación), Bety $99; Claudia sigue con $195.20 bloqueados a la espera de activarse.

### 2.11 Devolución por arrepentimiento (Patricia, 16-dic, móvil)

Patricia devuelve un Naplus cerrado dentro de los 7 días. Eligió "Desistimiento (arrepentimiento)" con el aviso "el costo de envío de la devolución corre a tu cargo"; folio RET-9A996299; verificado en la API (PENDIENTE, envío a cargo del cliente, VP intactos hasta la inspección).

- **Bug**: el correo "Recibimos tu solicitud" decía "guarda tu ticket de envío: te lo reembolsamos" para todos los motivos, contradiciendo la pantalla. Corregido: el correo distingue quién paga según el motivo.
- Las tres fotos (producto, empaque, guía) son obligatorias aunque el paquete esté cerrado. Es la regla 3.3 del plan; queda como hallazgo (§4).
- No encontró a quién escribir por un pedido: su panel solo mostraba el WhatsApp de su patrocinadora "para temas de red". Corregido: el bloque de patrocinador muestra también el WhatsApp y el correo de soporte para pedidos, pagos y devoluciones.

### 2.12 Recepción con checklist y entrada de inventario (Beto, 18-dic)

- Beto recibió el Naplus de Patricia con el formulario nuevo: seis casillas, "Resultado: devolución validada (procede el reembolso)" antes de confirmar, una foto y notas; "Paquete recibido. Devolución validada." Verificado en la API: checklist, notas y foto en la solicitud, pedido `devuelto_validado`, y la comisión de $25.20 de Verónica por ese pedido quedó "Anulada" (tachada, no borrada).
- **Bug**: esa anulación venía por un camino propio del servicio de pedidos (inspección, cancelación, reembolso) sin motivo ni correo; el aviso "Comisión anulada" solo existía en la acción de Step Functions. Corregido: ese camino guarda el motivo y avisa.
- Registró la entrada de 30 Magnesio en Bodega Central ("Entrada de inventario registrada.", bitácora con +30). Verificado.
- Encontró cuatro pedidos de octubre y noviembre "Enviada" que nunca se marcaron entregados aunque Estafeta los entregó: nadie cierra el ciclo de los envíos por paquetería. Se cerraron por API; propuesta en §4.

### 2.13 Reembolso con checklist y pickup que nadie recoge (Sofía, 18-dic)

- Abrió el detalle de la devolución de Patricia (motivo del cliente, tres fotos, notas y foto de Beto, checklist) y reembolsó. **Hueco**: el modal sugería $381 (producto más envío) aunque era arrepentimiento; lo corrigió a mano a $252. Verificado: `refunded` con $252, motivo y comprobante. Corregido: en desistimiento se sugiere solo el producto, y el detalle del pedido muestra cuánto se reembolsó y por qué.
- Canceló el pedido de recoger y pagar en sucursal que Guadalupe R. dejó cinco días sin recoger. **Hueco**: un `confirm` sin motivo, sin decir que no estaba pagado, y el registro quedaba como "admin_request". Corregido: pide motivo y avisa si no había pago. El tablero solo decía "1 pedidos pendientes de pago — Informativo", sin nombre ni días (§4).
- Acciones urgentes quedó con "2 comisiones pendientes por depositar — Urgente" a mitad de mes: las de diciembre se pagan el 10 de enero; el aviso debería ser informativo hasta entonces (§4).

### 2.14 Activación el día 20 y reversión de la compresión (Claudia, 20-dic)

Claudia, con "Bloqueadas $195.20" por la compra de Memo, compra $1,458 (27.9 VP) y se activa. Su panel pasó en el acto a "Confirmadas $195.20 · Bloqueadas $0". **Verificado en el ledger**: la fila G1 de Verónica por ese pedido quedó anulada ("recalculada: alguien de la línea se activó"), Claudia recibió G1 $195.20 confirmada y Verónica una G2 de $97.60 confirmada, más $145.80 pendientes por la compra de Claudia. Verónica recibió "comisión de $97.60 en camino" y "$145.80 en camino". Es el último escenario del motor que solo protegían las pruebas unitarias.

- Con 1 Colágeno + 1 Biotina (21 PC de lista) el carrito avisó "18.9 de 20 VP"; agregó el Magnesio del mes para llegar a 27.9. El aviso nuevo cumplió su función.
- **Bug**: eligió "Recoger en sucursal" y vio "No se pudo crear la orden." sin motivo (Del Valle no tiene Magnesio; la validación nueva funcionó pero el carrito tapó el mensaje). Corregido: el toast muestra el motivo del backend.

### 2.15 Ola en curso

_(10 de enero: Sofía paga las comisiones de diciembre a Verónica, Claudia y Bety.)_

## 3. Bugs de producción corregidos en esta ronda

| # | Gravedad | Dónde | Qué pasaba | Corrección |
|---|---|---|---|---|
| 1 | Grave | Seguridad | Una socia con acceso al back office recibía 403 en todas las pantallas con privilegio | Sesión con `canAccessAdmin`; actor tratado como empleado |
| 2 | Media | Correos | Aviso de comisión duplicado cuando la compra activa al propio comprador | Aviso solo con fila nueva |
| 3 | Media | Panel del socio | "Agregar a carrito" sumaba una unidad de más a la cantidad tecleada | Cantidad como borrador |
| 4 | Baja | Carrito | Niveles de descuento con nombres que no cuadran con el plan ("Nivel base" = 20%) | Niveles 1–4 = 10/20/30/40% |
| 5 | Media | Correos | Una comisión anunciada se anulaba sin aviso al patrocinador | Correo "Comisión anulada" con motivo |
| 6 | Media | Ledger | Las comisiones anuladas se borraban del mes: "Sin movimientos" donde hubo una comisión avisada | Filas "Anulada" con estado previo, fecha y motivo; fuera de los totales |
| 7 | Baja | Comisiones | El endpoint mensual derivaba VP de pesos ÷ tarifa; la activación usa PC netos | Un solo cálculo |
| 8 | Baja | Carrito | Nadie avisaba que los VP netos de la compra no alcanzan la activación | Aviso "llegas a X de 20 VP" sin cupón |
| 9 | Media | Carrito móvil | No había dónde escribir el cupón desde el celular | Cupón, VP y aviso de activación en el resumen móvil |
| 10 | Media | Devoluciones | La cortesía prometida al rechazar no existía como descuento | Cupón personal de un uso emitido desde el rechazo y enviado en el correo |
| 11 | Media | POS | Una venta con pago parcial no se podía liquidar después | Ruta de abonos, "Cobrar saldo" en la venta, abono al corte |
| 12 | Media | Clientes | Sin "última compra", sin filtro de fríos y sin exportar: la recuperación de cuentas se hacía cruzando siete pestañas | `lastPurchaseAt`, filtro "Solo fríos", CSV |
| 13 | Baja | Correos | El correo de devolución prometía reembolsar el envío también en arrepentimiento (la pantalla decía lo contrario) | Texto según quién paga el envío |
| 14 | Baja | Panel del socio | Con patrocinadora, el panel no mostraba ningún contacto de soporte para pedidos | WhatsApp y correo de soporte en el bloque de patrocinador |
| 15 | Media | Pedidos | La anulación de comisiones desde inspección, cancelación o reembolso no llevaba motivo ni avisaba al patrocinador | Motivo y correo también en ese camino |
| 16 | Baja | Reembolsos | El monto sugerido incluía el envío en devoluciones por arrepentimiento | Sugerencia según el motivo |
| 17 | Baja | Pedidos | El detalle no mostraba cuánto se reembolsó ni el motivo | "Reembolsado: $X · motivo" |
| 18 | Baja | Pedidos | Cancelar desde el panel no pedía motivo (quedaba "admin_request") ni avisaba si no estaba pagado | Motivo obligatorio y aviso |
| 19 | Baja | Carrito | Un pedido rechazado por el backend mostraba "No se pudo crear la orden." sin el motivo | Toast con el mensaje del backend |

## 4. Hallazgos de negocio

1. El descuento por tramo se explica en tres lugares con tres vocabularios (metas del panel, carrito, POS). Propuesta: una sola tabla "Tu descuento este mes" visible en panel y carrito, con el tramo actual, el siguiente y cuánto falta.
2. La cancelación de un pedido pagado promete reembolso sin plazo ni medio. Propuesta: "al mismo medio de pago, en 3 a 5 días hábiles" en pantalla y correo, y correo al salir.
3. Las campañas no tienen vigencia. Propuesta: fecha de inicio y fin, activación automática y aviso al vencer.
4. El catálogo anuncia PC brutos y la activación cuenta VP netos (con descuento): comprar "20 PC" deja 18 VP. Propuesta: o la activación cuenta PC brutos (más simple de explicar) o el catálogo muestra "VP con tu descuento actual".
5. El mínimo de envío gratis se mide sobre el total con descuento: $1,090 de catálogo pagan envío. Propuesta: medirlo sobre el subtotal, o decirlo en el carrito ("te faltan $19 después del descuento").
6. Los rangos son inalcanzables a la escala de esta red (BRONCE pide 4,500 VG; la red suma 91). No es un defecto, pero conviene un rango de entrada (por ejemplo 300 VG y 2 líneas) para que el Cuadro de Honor muestre algo más que "—".
7. Los códigos de recuperación se invalidan entre sí: quien pide dos (por impaciencia) ve "inválido o expirado" con el primero. Propuesta: aceptar el último código y decir en el correo "usa el código más reciente".
8. El teléfono es opcional al registrarse y la recuperación de cuentas es por WhatsApp: dos de cuatro fríos no tenían número. Propuesta: pedir celular en el registro (con explicación) y en el primer pedido.
9. La entrega personal no se puede elegir al comprar (solo el almacén la registra) y la cartera "FindingU" no muestra a la ejecutiva como coach en el panel del cliente. Propuestas: opción "entrega en persona" por zona en el checkout, y que el patrocinador por defecto muestre nombre y WhatsApp de la ejecutiva asignada.
10. Devolver un paquete cerrado por arrepentimiento exige tres fotos (producto, empaque y guía). Propuesta: para desistimiento con paquete sin abrir, una sola foto del paquete cerrado con la guía.
11. Los envíos por paquetería nunca se cierran: cuatro pedidos llevaban semanas "Enviada" con el paquete entregado. Propuesta: aviso "enviados hace más de 7 días sin entrega" en Acciones urgentes, o cierre automático con el rastreo de la paquetería (y el correo "¿te llegó?" al cliente).
12. Los avisos del tablero son genéricos: "1 pedidos pendientes de pago" sin nombre ni antigüedad, y "comisiones pendientes por depositar — Urgente" desde el día 1 aunque se pagan el 10 del mes siguiente. Propuesta: cada aviso con folio, cliente y días, y la urgencia de comisiones solo a partir del día 8.

## 5. Pendiente

_(Se completa al cerrar la ronda.)_
