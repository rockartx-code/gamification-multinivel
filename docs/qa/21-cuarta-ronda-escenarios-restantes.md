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

### 2.3 Ola B en curso

_(Sofía: reembolso de Memo, cupón `DIC50` con mínimo y tope, producto nuevo con imagen y producto del mes, categoría, campaña, código de autorización del POS, evaluación de bonos. Bety: compra para activarse y busca su comisión de noviembre desaparecida.)_

## 3. Bugs de producción corregidos en esta ronda

| # | Gravedad | Dónde | Qué pasaba | Corrección |
|---|---|---|---|---|
| 1 | Grave | Seguridad | Una socia con acceso al back office recibía 403 en todas las pantallas con privilegio | Sesión con `canAccessAdmin`; actor tratado como empleado |
| 2 | Media | Correos | Aviso de comisión duplicado cuando la compra activa al propio comprador | Aviso solo con fila nueva |
| 3 | Media | Panel del socio | "Agregar a carrito" sumaba una unidad de más a la cantidad tecleada | Cantidad como borrador |
| 4 | Baja | Carrito | Niveles de descuento con nombres que no cuadran con el plan ("Nivel base" = 20%) | Niveles 1–4 = 10/20/30/40% |

## 4. Hallazgos de negocio

1. El descuento por tramo se explica en tres lugares con tres vocabularios (metas del panel, carrito, POS). Propuesta: una sola tabla "Tu descuento este mes" visible en panel y carrito, con el tramo actual, el siguiente y cuánto falta.
2. La cancelación de un pedido pagado promete reembolso sin plazo ni medio. Propuesta: "al mismo medio de pago, en 3 a 5 días hábiles" en pantalla y correo, y correo al salir.

## 5. Pendiente

_(Se completa al cerrar la ronda.)_
