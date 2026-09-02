# Diario — Claudia Ibarra Soto
**13 de noviembre de 2026, tarde (desde las 5:00 pm)**

## 5:00 pm — Entrando a la plataforma
Abrí la tienda en `http://localhost:4321/#/tienda`. No tenía la sesión guardada en este navegador (salió la pantalla de "Entrar" normal, con el catálogo de fondo). Toqué "Entrar" y de ahí "Recuperar contraseña" porque de plano no me acordaba de mi clave.

Puse mi correo `claudia.ibarra.salon@gmail.com`, le di "Enviar Correo de recuperación" y salió el mensaje "Código enviado". Fui a mi correo (con `leerCorreo`) y ahí estaba: *"Tu código de recuperación Finding'U es: 849782. Expira en 15 minutos."* Se me fueron varios códigos porque cada vez que reintentaba el formulario mandaba uno nuevo y el anterior quedaba inválido ("Código inválido o expirado" me marcó una vez). Al final usé el código correcto (el último que llegó, 727920) junto con mi correo y mi contraseña nueva: **`Salon2026Claudia!`**. Le piqué a "Guardar nueva contraseña" y me regresó sola a la pantalla de Login. Entré con mi correo y la contraseña nueva y ¡ahí estaba mi panel!

Anoto mi contraseña nueva aquí para no volver a perderla: **Salon2026Claudia!**

## 5:10 pm — Lo primero que vi: modales
Apenas entré me saltaron varios avisos encimados (tuve que cerrarlos uno por uno: "Metas cumplidas del mes", "aviso del portal", etc.). El de metas decía "¡Buen trabajo! Estas son tus metas alcanzadas en el mes": *"Agregar un nuevo miembro a la red este mes"*, *"Lograr que un miembro de la red alcance su meta"* (Meta por miembro: 20 VP) y *"Todos los directos logran su meta"* (Directos: 1) — las tres marcadas como "Nueva". Se siente raro festejar una meta que en realidad cumplió Memo, no yo.

## 5:15 pm — Lo de los $172 de Memo
Fui a la sección "Comisiones". Decía textual:
- **"Total del mes $0"**
- **"Confirmadas (se depositan el día de pago) $0"**
- **"Por confirmar (pedidos aún no entregados) $0"**
- **"Bloqueadas $172"**

Le di clic al iconito de información junto a "Bloqueadas" y salió este tooltip, que es la explicación que andaba buscando:

> **"Comisiones de tus referidos generadas mientras no estabas activa/o (20 VP en el mes). Si te activas dentro del mismo mes, se recalculan."**

O sea: sí existen los $172 de Memo, pero están "bloqueados" porque yo no tengo los 20 VP de actividad de este mes. Si compro y me activo ESTE mes, según ese texto "se recalculan" (entiendo que se desbloquean).

Le di "Ver detalles" y salió una tabla:
| Orden | Nivel | Monto | Estado | Fecha |
|---|---|---|---|---|
| ORD-9074F79E | L1 | $172 | **blocked** | 12 nov 2026 |

Arriba también vi el objetivo del mes bien claro: *"Objetivo principal del mes — Alcanzar VP mínimo (usuario activo) — Meta mensual: 20 VP — Te faltan 20 VP para lograrlo."* Osea parto de cero VP.

En "Volumen & Rangos": **VP (Volumen Personal): 0**, **VG (Volumen de Grupo): 29.6**, **RANGO ACTUAL: Sin rango aún — "Cada compra te acerca al primero."**

En "Red" confirmé lo de Memo: *"Guillermo Ibarra Ponce · L1 · Consumo mes $1,720 · Estado: Activa"*. Y abajo: *"Meta de red (este mes) $1,720 / $300 — Te faltan $0 para cumplir la meta de red."* Esa meta de red sí la cumplí gracias a la compra de mi hermano, pero mi comisión personal sigue bloqueada porque YO no estoy activa.

No vi a Tomás por ningún lado en mi tabla de Red (solo aparece Guillermo). Sí lo vi más abajo, en el "Cuadro de Honor" del mes, con 0 VG y 0 VP, separado de mí — así que se confirma que él cuenta para la red de Verónica y no para la mía.

## 5:25 pm — Explorando la tienda y probando cupones
Fui a "Tienda". El Colágeno Hidrolizado está en $700 (13 PC) y la Biotina en $400 (8 PC) — con $600 no me alcanza para el colágeno, así que me fui por la Biotina.

La agregué al carrito (por accidente quedaron 2 unidades porque el carrito ya traía una de un intento anterior — la ajusté a 1 con el botón de "Quitar una unidad de Biotina"). Con 1 Biotina: Total $400, "Puntos de este pedido (VP): 8 VP", y abajo decía *"Te faltan 12 VP para Alcanzar VP mínimo (usuario activo)"* — o sea ni comprando la Biotina llego a los 20 VP que pide la meta. Con mi presupuesto de $600 no me alcanza para completar la activación completa este mes; lo más barato por VP (Klinhart, CRT-1200) igual se pasa de mi presupuesto si lo combino con algo más.

Probé los cupones en el carrito:
- **GRACIAS50**: lo puse y apliqué. Salió: *"Cupón aplicado — Cupón GRACIAS50 -$50"*. El total bajó de $400 a **$350**, pero los VP del pedido bajaron de 8 a **7 VP** (el descuento también resta puntos).
- **NAVIDAD100**: lo probé después (quitando primero el GRACIAS50). El sistema me contestó de volada: **"Cupón expirado."** Ni siquiera lo aplicó. Ese cupón de la historia de Instagram ya no sirve.

Volví a aplicar GRACIAS50 para la compra final.

## 5:35 pm — La compra
Elegí "Recoger en sucursal" (sin costo de envío) porque ya estaba pesado el flujo de dirección con tantos campos obligatorios. Elegí la sucursal "Tienda Del Valle · Av. Coyoacán 1200" y método de pago "Pagar en línea (Tarjeta / transferencia)".

Resumen final antes de pagar:
- **Subtotal: $400**
- **Descuento: -$50 (GRACIAS50)**
- **Total: $350**
- **Puntos de este pedido (VP): 7 VP**

Le di "Pagar y finalizar" y se creó la orden:
> **Orden ORD-AD9456FF** — Creada: 2026-11-13T17:29:08Z — Estatus: **Pago pendiente** — Subtotal $400, Descuento "Sin descuento" (raro, en el detalle de la orden ya no menciona el cupón aunque sí descontó el monto), **Total $350**.

Me mandó a la pasarela simulada (Mercado Pago simulado): *"Pago simulado · Finding'U · Pedido ORD-AD9456FF — $350.00 — Estás fuera de la tienda. Este es el checkout de la pasarela."* Le di "Pagar $350.00".

Me regresó a la pantalla de seguimiento de mi orden, pero se quedó marcando **"Pago pendiente"** todo el rato — until intenté de nuevo un par de veces y hasta recargué la página completa, y seguía igual: "Pago pendiente". Me acordé de que la vez pasada (mi compra de octubre) el correo de "Recibimos tu pago" me llegó AL DÍA SIGUIENTE de haber comprado, no al instante. Entonces creo que aquí es lo mismo: mi pago quedó registrado pero la confirmación tarda, no es que se haya caído.

## 5:45 pm — Revisando el panel después de comprar
Volví a entrar a mi cuenta (se había cerrado la sesión sola en algún momento, tuve que volver a poner correo y contraseña) y revisé todo de nuevo:

- **Comisiones — igual que antes:** "Total del mes $0", "Confirmadas $0", "Por confirmar $0", **"Bloqueadas $172"** — no cambió nada.
- **Volumen & Rangos — igual:** VP 0, VG 29.6, "Sin rango aún".
- **Órdenes** ahora sí me aparece mi compra: *"ORD-AD9456FF — 2026-11-13T17:29:08Z — $350 — Pendiente"*, junto con la vieja de octubre que dice "Entregada".
- Revisé mi correo otra vez y **no me ha llegado ningún correo de la compra de hoy** (ni de "pago recibido" ni nada), solo siguen ahí los correos viejos y los códigos de recuperación.

O sea: mientras mi orden diga "Pendiente" en vez de "Entregada" o pagada-confirmada, entiendo que mis $172 bloqueados de Memo van a seguir bloqueados, y mis 7-8 VP de esta compra tampoco se han sumado a mi VP (sigue en 0). Tiene sentido con lo que decía el tooltip: activarme "recalcula" las comisiones, pero primero mi pago se tiene que confirmar.

## 5:50 pm — Links / referidos
Fui a la pestaña "Links". Ahí está:
- **Mi link:** `http://localhost:4321/#/landing/CLAUDIA-CIS`
- **Mi código de referido:** `CLAUDIA-CIS`
- Dice: *"Tus referidos pueden escribirlo al registrarse si no tienen tu link."* y un tip: *"fija el link en tu bio y repítelo en 3 historias."*

Es el mismo código que ya le compartí a Memo, todo cuadra.

## Mensajes que mandé

📱 A Soporte: Hola, hice una compra hoy (orden ORD-AD9456FF) de $350 con la Biotina, pagué en la pasarela pero mi orden se quedó en "Pago pendiente" y no me llegó ningún correo de confirmación. ¿Es normal que tarde o hay algún problema con mi pago?

📱 A Soporte: Vi que tengo $172 bloqueados de la compra de mi hermano Guillermo (12 nov) porque no estoy activa este mes (me piden 20 VP y voy en 0). Compré Biotina hoy por $350 con cupón pero solo suma 7 VP, no me alcanza para los 20. ¿Con mi próxima compra ya se suman los VP de ambos pedidos, o tengo que hacerlo todo en una sola compra?

## Lo que no pude hacer
- No pude activarme este mes: con mi presupuesto de $600 no alcanzo los 20 VP que pide la meta (la Biotina sola da 7-8 VP; ni combinándola con otro producto barato me daba el presupuesto para llegar a 20).
- No pude confirmar si mis $172 bloqueados de Memo ya se desbloquearon, porque mi pago de hoy quedó en "Pago pendiente" y el panel de Comisiones no se movió (sigue en $0 confirmadas / $172 bloqueadas).
- No me llegó ningún correo de confirmación de esta compra (ni de "orden creada" ni de "pago recibido") en todo lo que estuve esperando.
- No pude usar el cupón NAVIDAD100 — salió "Cupón expirado" apenas lo metí.
- No encontré manera de ver a mi hijo Tomás dentro de mi tabla de "Red" (solo sale en el Cuadro de Honor general, separado, con 0 VG/0 VP) — sigue confirmado que está bajo Verónica y no bajo mí.

## Lo que preguntaría
- ¿Cuánto tarda realmente en confirmarse un pago simulado? ¿Hay que esperar horas, un día, como pasó con mi compra de octubre?
- Si me activo a la mitad del mes (después del día 12, que es cuando compró Memo), ¿se desbloquean completos los $172 o se prorratea algo?
- ¿Los VP de dos compras distintas en el mismo mes se suman para la meta de 20 VP, o cada compra se evalúa aparte?
- ¿Hay manera de "pasar" a Tomás de la red de Verónica a la mía, o eso ya no se puede cambiar una vez que se registró con otro código?
- ¿Por qué el descuento del cupón GRACIAS50 también me quita puntos VP (de 8 a 7)? ¿Me conviene entonces no usar cupones si mi meta es activarme?

## Capturas de pantalla (todas en `/home/user/gamification-multinivel/sim/capturas/`)
- claudia-nov13-01-tienda.png — tienda sin sesión
- claudia-nov13-02-login.png — pantalla de login
- claudia-nov13-03-recuperar.png — recuperar contraseña
- claudia-nov13-04-envio.png — código enviado
- claudia-nov13-06-codigo.png — pantalla para poner el código
- claudia-nov13-07/08-* — cambio de contraseña
- claudia-nov13-09-panel.png — panel recién logueada
- claudia-nov13-11-modal-check.png — modal "Metas cumplidas del mes"
- claudia-nov13-13-info-bloqueadas.png — tooltip de comisiones bloqueadas
- claudia-nov13-14-verdetalles.png — tabla detalle $172 blocked
- claudia-nov13-15-detalle-biotina.png — ficha de producto Biotina
- claudia-nov13-19-gracias50.png — cupón GRACIAS50 aplicado
- claudia-nov13-20-navidad100.png — cupón NAVIDAD100 expirado
- claudia-nov13-24-pickup.png — recoger en sucursal
- claudia-nov13-26-tras-pagar.png — orden creada, pago pendiente
- claudia-nov13-27-gateway.png — pasarela Mercado Pago simulada
- claudia-nov13-33-pasarela-2s.png — orden sigue pendiente tras pagar
- claudia-nov13-38-panel-relogin.png — panel completo después de la compra
- claudia-nov13-40-links.png — pestaña de Links/referidos
