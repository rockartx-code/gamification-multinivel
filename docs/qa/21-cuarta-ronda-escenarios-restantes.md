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

### 2.5 Ola en curso

_(Patricia: cupón `DIC50` con mínimo y tope, compra bajo la patrocinadora reasignada.)_

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

## 4. Hallazgos de negocio

1. El descuento por tramo se explica en tres lugares con tres vocabularios (metas del panel, carrito, POS). Propuesta: una sola tabla "Tu descuento este mes" visible en panel y carrito, con el tramo actual, el siguiente y cuánto falta.
2. La cancelación de un pedido pagado promete reembolso sin plazo ni medio. Propuesta: "al mismo medio de pago, en 3 a 5 días hábiles" en pantalla y correo, y correo al salir.
3. Las campañas no tienen vigencia. Propuesta: fecha de inicio y fin, activación automática y aviso al vencer.
5. El catálogo anuncia PC brutos y la activación cuenta VP netos (con descuento): comprar "20 PC" deja 18 VP. Propuesta: o la activación cuenta PC brutos (más simple de explicar) o el catálogo muestra "VP con tu descuento actual".
6. El mínimo de envío gratis se mide sobre el total con descuento: $1,090 de catálogo pagan envío. Propuesta: medirlo sobre el subtotal, o decirlo en el carrito ("te faltan $19 después del descuento").
4. Los rangos son inalcanzables a la escala de esta red (BRONCE pide 4,500 VG; la red suma 91). No es un defecto, pero conviene un rango de entrada (por ejemplo 300 VG y 2 líneas) para que el Cuadro de Honor muestre algo más que "—".

## 5. Pendiente

_(Se completa al cerrar la ronda.)_
