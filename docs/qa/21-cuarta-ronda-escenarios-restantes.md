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

### 2.8 Ola en curso

_(Nadia liquida el saldo; después Beto despacha diciembre con una entrega personal y recibe una devolución con el checklist; Ivonne detecta clientes fríos; Claudia se activa el 20; cierre y pago de enero.)_

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

## 4. Hallazgos de negocio

1. El descuento por tramo se explica en tres lugares con tres vocabularios (metas del panel, carrito, POS). Propuesta: una sola tabla "Tu descuento este mes" visible en panel y carrito, con el tramo actual, el siguiente y cuánto falta.
2. La cancelación de un pedido pagado promete reembolso sin plazo ni medio. Propuesta: "al mismo medio de pago, en 3 a 5 días hábiles" en pantalla y correo, y correo al salir.
3. Las campañas no tienen vigencia. Propuesta: fecha de inicio y fin, activación automática y aviso al vencer.
4. El catálogo anuncia PC brutos y la activación cuenta VP netos (con descuento): comprar "20 PC" deja 18 VP. Propuesta: o la activación cuenta PC brutos (más simple de explicar) o el catálogo muestra "VP con tu descuento actual".
5. El mínimo de envío gratis se mide sobre el total con descuento: $1,090 de catálogo pagan envío. Propuesta: medirlo sobre el subtotal, o decirlo en el carrito ("te faltan $19 después del descuento").
6. Los rangos son inalcanzables a la escala de esta red (BRONCE pide 4,500 VG; la red suma 91). No es un defecto, pero conviene un rango de entrada (por ejemplo 300 VG y 2 líneas) para que el Cuadro de Honor muestre algo más que "—".
7. Los códigos de recuperación se invalidan entre sí: quien pide dos (por impaciencia) ve "inválido o expirado" con el primero. Propuesta: aceptar el último código y decir en el correo "usa el código más reciente".

## 5. Pendiente

_(Se completa al cerrar la ronda.)_
