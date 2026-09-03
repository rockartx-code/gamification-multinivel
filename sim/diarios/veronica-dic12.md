# Diario de Verónica Sandoval Ruiz — 12 de diciembre de 2026

## 10:00 — Entrando a la tienda
Abrí http://localhost:4321/#/tienda. Sin sesión iniciada se ve la tienda pública: el catálogo completo (11 productos, cada uno con su precio y sus "PC"), el formulario de registro y el botón "Entrar". Precios que vi en el catálogo: Creatina Monohidratada $650 (9 PC), Colageno Hidrolizado $700 (13 PC), CRT-1200 $550 (10 PC), Keto Elektrolyte Fusion $750 (15 PC), Biotina $400 (8 PC), BHB Acido $630 (13 PC), Naplus $280 (6 PC), Boom $420 (8 PC), Longevit $390 (7 PC), Klinhart $480 (10 PC), Finding Pro 500g $800 (15 PC).

## 10:02 — Entrar
Clic en "Entrar", puse `veronica.sandoval@gmail.com` / `Veronica2026!` y "Ingresar al panel". Me sorprendió que me mandó directo a `http://localhost:4321/#/admin` (no a la tienda). Ahí vi mi nombre "Verónica Sandoval Ruiz" con la etiqueta "CLIENTE", un menú "Navegación" con solo dos opciones: PERSONAS → Clientes, SEGUIMIENTO → Cuadro de Honor. En la pantalla de "Clientes" decía "Clientes totales 0", "Comisiones por depositar $0", "0 clientes", "Sin resultados para ''." En la consola de la página salieron dos errores: `HTTP 403 GET /dashboard/admin/warnings` y `HTTP 403 GET /customers/getall?limit=200`. Es decir, el menú "Clientes" existe pero no me deja ver la lista — me la bloquea.

## 10:05 — Volviendo a la tienda para comprar
Regresé a `#/tienda` (recargando la página) y ahí, curiosamente, ya NO se veía como si tuviera sesión — otra vez apareció el botón "Entrar" arriba. Pero al ir al carrito, el formulario de entrega ya traía mi nombre "Verónica Sandoval Ruiz" como valor. Confuso: por fuera parecía que no había entrado, pero el carrito sí me reconocía.

## 10:08 — Armando el pedido grande para mis 8 clientas
Fui producto por producto ("Ver producto" cambia el destacado de arriba, luego "Agregar al carrito"). Armé: **Finding Pro 500g x2, Boom x2, Colageno Hidrolizado x1**. El contador de abajo mostró: "5 artículos" y "Total en carrito $3,140" — justo en el rango que quería ($3,000–$3,300).

## 10:09 — Carrito y descuento
Al abrir "Ver carrito" vi el resumen:
- Subtotal $3,140
- Descuento -$942 • **Dto 30%**
- Nivel de descuento: **Nivel 1**
- "Con esta compra subes a Nivel 1 (30%)."
- Envío: "Gratis (pedido de $1,000 o más)"
- Puntos de este pedido (VP): 41.3 VP
- **Total $2,198**

Sí me dieron buen descuento por comprar junto, como decía Sofía. Llené la dirección (Av. Vallarta 2100, Guadalajara, Jalisco, CP 44140) y di "Pagar y finalizar".

## 10:10 — Pedido #1 creado y pagado
Se creó la orden **ORD-158A01E6** ("Pago pendiente"). El detalle mostraba: Subtotal $3,140, Descuento -$942 - 30%, Total $2,198. Entré a "Pagar con MercadoPago"; salió una pantalla de pago simulado ("Pago simulado · Finding'U · Pedido ORD-158A01E6 · $2,198.00 · Estás fuera de la tienda. Este es el checkout de la pasarela."). Le di "Pagar $2,198.00" y regresó a la orden con estatus **"Pago registrado"**.

## 10:12 — Segundo pedido: 2 Biotina para la clienta que llegó tarde
Agregué Biotina x2 en un carrito nuevo (aparte, como pidió la clienta). Aquí me llevé una sorpresa: el resumen decía:
- Subtotal $800
- Descuento -$160 • **Dto 20%**
- Nivel de descuento: **"Nivel base"**
- "Con esta compra subes a Nivel base (20%)."
- Meta principal de consumo: "Alcanzar nivel 3 de descuento (30%)" — "Te faltan $2 para Alcanzar nivel 3 de descuento (30%)"
- Envío: ya NO fue gratis, esta vez cobró $129 (Estafeta) porque el pedido no llegó a $1,000.
- **Total $769**

O sea: el descuento del 30% del primer pedido NO se me quedó — cada pedido calcula su propio % según lo que traigo en ESE carrito, no según lo que llevo comprado en el mes. Con el pedido grande subí a "Nivel 1" (30%), pero al abrir un carrito nuevo con solo $800 me regresó a "Nivel base" (20%). Eso no lo tenía claro y me generó duda (ver abajo, mensaje a Soporte).

Pagué igual: orden **ORD-DA7CF4FA**, "Pago pendiente" → "Pago con MercadoPago" ($769.00) → **"Pago registrado"**.

📱 A Soporte: Hola, hice dos pedidos hoy: uno de $3,140 me dio 30% de descuento (Nivel 1) y minutos después uno de $800 (2 Biotina) solo me dio 20% ("Nivel base"), como si el primer pedido no contara. ¿El % de descuento se calcula por cada pedido por separado o se acumula en el mes? Quiero entender bien para cotizarles bien a mis clientas. Gracias.

## 10:15 — Revisando el panel completo (lo encontré en /dashboard, no en /admin)
Probé el enlace "Ve tu red" de un correo viejo (`http://localhost:4321/dashboard`) y ahí sí apareció mi panel completo de socia, con menú arriba: Tienda, Red, Links, Órdenes, Comisiones, Cuadro de Honor, Mi perfil (y arriba a la izquierda un ícono "1 · Top 1"). Cosas que vi:

- **Progreso mensual — Objetivo principal del mes**: "Agregar un nuevo miembro a la red este mes — Invita a 1 persona y actívala — Te faltan 1 para lograrlo." (Esta es mi "siguiente meta" ahora, no la de descuento — la de descuento ya la cumplí este mes según el cuadro de metas.)
- Al entrar salió un cuadro "¡Buen trabajo! Estas son tus metas alcanzadas en el mes": "Consumo objetivo desde $2,000 MXN → Alcanzar nivel 2 de descuento (20%)" (marcada "Nueva"), "Meta mensual: 20 VP → Alcanzar VP mínimo (usuario activo)" (Leída), "Consumo objetivo desde $1,000 MXN → Alcanzar nivel 1 de descuento (10%)" (Leída). Esto me confundió porque son "niveles de descuento" con otros porcentajes (10%/20%) y no coinciden con el 30%/20% que vi en mis dos carritos — parecen dos sistemas distintos (metas del mes vs. descuento del carrito) y no lo tengo claro.
- **Volumen & Rangos**: VP (Volumen Personal) **54.1**, VG (Volumen de Grupo) **90.9**. RANGO ACTUAL: **"Sin rango aún — Cada compra te acerca al primero."**
- **Comisiones — Resumen del mes 2026-12**: Total del mes **$195.20**, Confirmadas (se depositan el día de pago) **$0**, Por confirmar (pedidos aún no entregados) **$195.20**, Bloqueadas $0. O sea diciembre NO está en $0 como yo esperaba — ya aparece $195.20 "por confirmar". Mes anterior: Total **$393.60**, Estatus: **Pagada** (esto coincide con el correo que me llegó el 10 de diciembre).
- **Órdenes**: aparecen mis 6 pedidos, incluidos los dos de hoy: ORD-DA7CF4FA ($769, Pagada), ORD-158A01E6 ($2,198, Pagada), y de antes ORD-E056804D ($1,220, Enviada), ORD-4C638888 ($1,952, Cancelada), ORD-30280A83 ($381, Enviada), ORD-9BADDCB6 ($1,137, Enviada).
- **Red**: Nivel 1: 5 personas, Nivel 2: 2, Activos: 1. Meta de red (este mes): "$1,952 / $300 — Te faltan $0 para cumplir la meta de red" (ya la cumplí). Lista de mi red con estado: Guillermo Ibarra Ponce (L2, $1,952, **Activa**) y el resto (Rodrigo, Tomás, Patricia, Claudia, Beatriz, Guadalupe Ochoa) en **"Inactiva"**, consumo $0.
- **Links**: mi código de referido es **VERONICA-VSR** y mi link `http://localhost:4321/#/landing/VERONICA-VSR`.
- **"Mi perfil"** en este menú de arriba, al darle clic, me manda otra vez a `#/admin` (la pantalla de "Clientes" con los mismos 403 de antes). O sea "Mi perfil" y el back office que mencionó Sofía son la misma pantalla.

## 10:20 — Revisando el Cuadro de Honor (back office)
Desde `#/admin` → botón "Cuadro de Honor". Elegí el mes con el campo tipo "month":
- **Diciembre 2026**: #1 soy yo — "Verónica Sandoval Ruiz — VG 91 — VP 54". #2 Guillermo Ibarra Ponce (VG 37, VP 37, ▲2). #3 Claudia Ibarra Soto (VG 37, VP 0). Del 4 al 10 casi todos en 0.
- **Noviembre 2026**: también soy #1 — "Verónica Sandoval Ruiz — VG 98 — VP 23". #2 Beatriz Ochoa Lara (VG 38, VP 38). #3 Claudia Ibarra Soto (VG 37, VP 7).

También revisé "Acciones" (el botón de la campanita, "0 urgentes"): se abrió un panel que decía "Todo en orden — No hay acciones urgentes pendientes."

## 10:25 — Revisando el correo
En mi buzón encontré, entre otros:
- 10 dic: "Depositamos tus comisiones de 2026-11: $393.60" (con comprobante).
- Hoy 12 dic, 10:11: "Recibimos tu pago · pedido ORD-158A01E6".
- Hoy 12 dic, 10:12 (x2, llegó **duplicado**, dos correos con la misma hora exacta): "Guillermo Ibarra Ponce compró: comisión de $195.20 en camino". No entiendo por qué me llegó dos veces igual, ni por qué la compra de Guillermo generó comisión justo cuando yo estaba comprando — lo anoto como algo raro que no pude explicarme.
- Hoy 12 dic, 10:13: "Recibimos tu pago · pedido ORD-DA7CF4FA".

## Lo que no pude hacer
- No pude ver la lista de mis "Clientes" en el back office — el menú existe pero la tabla siempre sale vacía y en la consola hay dos errores 403 (`/dashboard/admin/warnings` y `/customers/getall`). No sé si es que no tengo permiso o si es un candado que Sofía todavía no me quita.
- No encontré un solo lugar que diga "tu descuento actual es X%" de forma fija — cada carrito calcula su propio % según lo que llevo en ESE pedido. No sé si eso es lo normal o un error.
- No entendí bien la diferencia entre el "Nivel de descuento" que sale en el carrito (10%/20%/30% según el subtotal de cada pedido) y los "niveles de descuento" de las metas del mes (10%/20%/30% pero por VP y consumo acumulado). Parecen dos reglas distintas con los mismos nombres.
- No até cabos con la comisión de "Guillermo Ibarra Ponce" que me llegó dos veces justo cuando yo pagaba mis propios pedidos.

## Lo que preguntaría
- ¿El % de descuento se calcula pedido por pedido, o hay manera de que se acumule en el mes para no perder el 30% si compro varias veces?
- ¿Por qué en el back office (Clientes) me sale todo en 0 y con error 403? ¿Ya tengo el acceso completo o falta algo por activar?
- ¿Por qué me llegó dos veces el mismo correo de la comisión de Guillermo?
- ¿Cuándo se van a depositar los $195.20 que ya aparecen "por confirmar" de diciembre?
