# Diario — Claudia Ibarra Soto — 20 de diciembre 2026

## 10:03 am — Antes de comprar, con el aguinaldo en la bolsa
Ya cobré el aguinaldo. Traigo $1,500 y hoy sí me voy a activar antes de que cierre diciembre. Entré a la tienda (`http://localhost:4321/#/tienda`) con mi correo y contraseña. El reloj del mundo simulado marca **2026-12-20T10:03:03Z**.

Inicié sesión y anoté tal cual lo que decía mi panel, ANTES de tocar nada:

- **Corte de mes:** "22d 14h 17m 11s"
- **Objetivo principal del mes:** "Alcanzar VP mínimo (usuario activo)" — **"Meta mensual: 20 VP"** — **"Te faltan 20 VP para lograrlo"**
- **Comisiones (resumen del mes 2026-12):**
  - Total del mes: **$0**
  - Confirmadas (se depositan el día de pago): **$0**
  - Por confirmar (pedidos aún no entregados): **$0**
  - **Bloqueadas: $195.20**
- **Volumen & Rangos:** VP (Volumen Personal) **0**, VG (Volumen de Grupo) **36.8**, "Sin rango aún"
- **Mi Red:** "Guillermo Ibarra Ponce | L1 | Consumo mes $1,952 | Estado: Activa". Meta de red: "$1,952 / $300 — Te faltan $0 para cumplir la meta de red" (o sea la meta de RED sí la cumplo, es la meta de MI VP la que me falta).

Le di "Ver detalles" en Bloqueadas y salió la fila exacta:
> **ORD-384BE04A | L1 | $195.20 | Bloqueada | 12 dic 2026**

Ahí está, tal cual como en noviembre: el dinero de la compra de Memo ($1,952 el 12 de diciembre) se ve pero "Bloqueada" porque yo no llegué a mis 20 VP.

## 10:07 am — Armando el carrito para llegar a 20 VP
Según los "PC" que muestra el catálogo, Colágeno da 13 y Biotina 8 (13+8=21), así que puse 1 de cada uno pensando que ya la hacía. Pero cuando entré al carrito con Colágeno + Biotina el aviso decía:

> **"Con este pedido llegas a 18.9 de 20 VP del mes: te faltarían 1.1 VP para activarte. Los VP se cuentan sobre el precio ya con descuento; agrega algo más si quieres activarte con esta compra."**

Esto me sorprendió: el "PC" que aparece junto a cada producto en el catálogo (13 PC, 8 PC) **no es lo mismo que los VP reales del pedido**, porque el sistema calcula los VP sobre el precio CON el descuento por volumen ya aplicado (a $1,100 de subtotal me tocaba "Dto 10%"), no sobre el precio de lista. Con el descuento, 1 Colágeno + 1 Biotina solo sumó **18.9 VP**, no 21.

Agregué un tercer producto (Magnesio Glicinato, el que la propia tienda me recomendaba: "Este producto te acerca a: Alcanzar VP mínimo (usuario activo)"). Con los tres el resumen cambió:

> **Puntos de este pedido (VP): 27.9 VP**
> **"Te faltan 0 VP para Alcanzar VP mínimo (usuario activo)"**

Carrito final: Colágeno Hidrolizado $630 (con Dto 10%, antes $700) + Biotina $360 (antes $400) + Magnesio Glicinato $468 (antes $520). **Subtotal $1,620, Descuento -$162 (10%), Total $1,458.** Me alcanzaba de sobra con mis $1,500.

## 10:10 am — Intento fallido con "Recoger en sucursal"
Elegí "Recoger en sucursal" → "Tienda Del Valle" → "Pagar en línea" (todo se veía bien marcado, con sus paloma verdes) y le di "Pagar y finalizar". Me salió un mensaje de error abajo a la derecha:

> **"No se pudo crear la orden."**

Lo intenté una segunda vez y en vez de crear la orden me salió otro aviso distinto:

> **"Completa calle, numero, ciudad, CP, estado y pais para continuar."**

O sea que, aunque en pantalla se veía "Recoger en sucursal" seleccionado, algo se resetea o no se guarda bien y me sigue pidiendo dirección de envío como si hubiera elegido "Envío a domicilio". Me dio desconfianza — no entendí por qué fallaba si todo se veía correcto en el formulario.

## 10:16 am — La compra (por fin), con envío a domicilio
Cambié de táctica: llené el formulario de "Envío a domicilio" (nombre, teléfono, calle, número, ciudad, CP, estado Puebla, país México) y dejé "Pagar en línea". Le di "Pagar y finalizar" y esta vez sí se creó la orden:

> **Orden ORD-B17FBDD2** — Creada: 2026-12-20T10:16:12Z — Estatus: **Pago pendiente** — Subtotal $1,620, Descuento -$162 (10%), **Total $1,458**.

Me mandó a la pasarela simulada: *"Mercado Pago · Pago simulado · Finding'U · Pedido ORD-B17FBDD2 — $1,458.00 — Estás fuera de la tienda. Este es el checkout de la pasarela."* Le di "Pagar $1,458.00".

Regresé al seguimiento de mi orden y ahora sí decía de inmediato:

> **Estatus: Pago registrado**

Esta vez no se quedó pegada en "Pago pendiente" como me pasó en noviembre.

## 10:16 am — El correo, casi al instante (distinto a noviembre)
Revisé mi buzón y, a diferencia de mi compra de octubre (que tardó hasta el día siguiente en llegar la confirmación), esta vez el correo llegó **el mismo minuto**:

> **"Recibimos tu pago · pedido ORD-B17FBDD2"** (2026-12-20T10:16:45Z): *"¡Gracias por tu compra! Hola Claudia Ibarra Soto. Tu pago quedó confirmado. Estamos preparando tu paquete y te avisaremos por este medio cuando salga."*

Y junto a ese, con la misma fecha y hora exacta (2026-12-20T10:16:45Z), me llegó otro correo que no esperaba:

> **"Guillermo Ibarra Ponce compró: comisión de $195.20 en camino"**: *"Hola Claudia. Guillermo Ibarra Ponce compró; te genera una comisión de $195.20 (generación 1), pendiente hasta la entrega."*

Me pareció raro que este correo de "Memo compró" llegara justo AHORA, con fecha de hoy, cuando la compra de Memo fue el 12 de diciembre — como si el aviso se hubiera disparado hasta que yo me activé, no cuando él compró.

## 10:20 am — El panel después de pagar: los $195.20 ya no están bloqueados
Volví a entrar (tuve que loguearme de nuevo, la sesión no se quedó abierta) y revisé todo con calma:

- **Objetivo principal del mes cambió:** ya no pide VP, ahora dice **"Agregar un nuevo miembro a la red este mes — Invita a 1 persona y actívala — Te faltan 1 para lograrlo"**. O sea que la meta de VP ya la cumplí y el panel me puso la siguiente meta.
- **Comisiones (resumen del mes 2026-12):**
  - Total del mes: **$195.20**
  - Confirmadas (se depositan el día de pago): **$195.20**
  - Por confirmar: **$0**
  - **Bloqueadas: $0**
  - Detalle (Ver detalles): **ORD-384BE04A | L1 | $195.20 | Confirmada | 20 dic 2026** — la fecha del detalle cambió de "12 dic 2026" a "20 dic 2026" (el día que yo me activé), y el estado pasó de "Bloqueada" a **"Confirmada"**.
  - Sigue diciendo: *"Las comisiones confirmadas de un mes se depositan el día 10 del mes siguiente (las de 2026-12 se depositan el 10 del mes que viene)."*
- **Volumen & Rangos:** VP subió de 0 a **27.9**, VG subió de 36.8 a **64.7**. Sigue "Sin rango aún".
- **Mi Red:** la fila de Memo sigue igual — "Guillermo Ibarra Ponce | L1 | Consumo mes $1,952 | Estado: Activa" — lo que cambió fue MI columna arriba: "Claud I. S. | $1K" (antes decía "$0").
- **Órdenes:** ahora aparece **ORD-B17FBDD2 | 2026-12-20T10:16:12Z | $1,458 | Pagada**, junto con mis dos órdenes viejas ("Entregada").
- **Cuadro de Honor:** subí de la posición #4 a **#2 en Red (VG) con 65 VG** y de fuera del top 10 a **#3 en Personal (VP) con 28 VP**.

Osea: en cuanto mi pago quedó "Pago registrado" (no tuve que esperar a que la orden diga "Entregada"), mis $195.20 bloqueados de Memo se desbloquearon solitos y pasaron a "Confirmadas". Esta vez sí lo logré.

## Mensajes que mandé

📱 A Soporte: Hola, hoy quise pagar mi pedido eligiendo "Recoger en sucursal" (Tienda Del Valle, pagar en línea) y me salió "No se pudo crear la orden." Lo intenté otra vez y ahí sí me pidió llenar la dirección de envío a domicilio, como si "Recoger en sucursal" no se hubiera guardado. Tuve que cambiar a envío a domicilio para que sí me dejara pagar. ¿Está fallando la opción de recoger en sucursal?

## Lo que no pude hacer
- No pude completar la compra con "Recoger en sucursal": me dio error "No se pudo crear la orden" y, al reintentar, me pidió los datos de envío a domicilio como si mi elección de sucursal no se hubiera guardado. Tuve que cambiar a envío a domicilio para poder pagar.
- No entendí bien por qué el correo de "Guillermo Ibarra Ponce compró: comisión de $195.20 en camino" me llegó hasta hoy (20 de diciembre), con la misma marca de tiempo que mi propio pago, si la compra de Memo fue el 12 de diciembre.
- No pude confiar de entrada en los "PC" que muestra el catálogo junto a cada producto (Colágeno 13, Biotina 8) para calcular cuánto me faltaba: el carrito me dijo que con esos dos productos solo llegaba a 18.9 VP, no a 21, porque los VP se cuentan sobre el precio ya con el descuento por volumen aplicado.

## Lo que preguntaría
- ¿Por qué "Recoger en sucursal" me tronó la orden ("No se pudo crear la orden") y luego me pidió llenar dirección de envío a domicilio como si no hubiera elegido sucursal? ¿Es un problema conocido?
- ¿El correo de "comisión en camino" de Memo se manda hasta que YO me activo, o se supone que debió llegarme desde el 12 de diciembre cuando él compró?
- ¿El "PC" que se ve junto a cada producto en el catálogo es el mismo VP que voy a recibir, o siempre hay que fijarse nada más en el aviso del carrito porque cambia con el descuento por volumen?
- Ya que mi orden dice "Pago registrado" (no "Entregada"), ¿mis $195.20 ya están garantizados o podrían volver a bloquearse si algo pasa con la entrega?
- Con mi nueva meta ("Agregar un nuevo miembro a la red este mes"), si no invito a nadie más este mes, ¿pierdo algo o nada más se queda esa meta sin cumplir?

## Capturas de pantalla (todas en `/home/user/gamification-multinivel/sim/capturas/`)
- claudia-dic20-01-tienda.png — tienda sin sesión
- claudia-dic20-03-post-login.png — panel completo ANTES de comprar (comisiones bloqueadas $195.20, meta 20 VP)
- claudia-dic20-04-detalle-bloqueadas.png — detalle de la fila ORD-384BE04A bloqueada
- claudia-dic20-07-carrito.png — carrito con Colágeno+Biotina duplicados (ajuste de sesión, ver script)
- claudia-dic20-08-carrito-ajustado.png — carrito correcto 1 Colágeno + 1 Biotina: "18.9 de 20 VP"
- claudia-dic20-09-carrito-3productos.png — carrito con Magnesio agregado: "27.9 VP", "Te faltan 0 VP"
- claudia-dic20-11-antes-pagar.png — resumen final antes de pagar, "Recoger en sucursal" seleccionado
- claudia-dic20-12-tras-pagar-finalizar.png — error "No se pudo crear la orden."
- claudia-dic20-14-form-domicilio.png — formulario de envío a domicilio lleno
- claudia-dic20-16-pasarela.png — pasarela Mercado Pago simulada, $1,458.00
- claudia-dic20-18-orden-tras-pago.png — orden ORD-B17FBDD2, "Pago registrado"
- claudia-dic20-20-panel-final.png — panel completo DESPUÉS: comisiones confirmadas $195.20, bloqueadas $0, VP 27.9
