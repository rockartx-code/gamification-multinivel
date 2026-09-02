# Diario de Nadia Ruiz — Turno en Tienda Del Valle
**13 de noviembre de 2026**

## 9:31 a.m. — Entrando al sistema
Llegué a Tienda Del Valle y abrí `http://localhost:4321/#/login`. Metí mi correo `nadia@findingu.mx` y mi contraseña. Entré sin problema, me mandó directo a un panel que dice "ADMIN" arriba de mi nombre (no sé si eso significa que tengo permisos de administradora o solo es el nombre del rol que me dieron, no me quedó claro). Ya en el panel vi que el sistema ya me tenía como "Pendientes de por cobrar: $840" y abajo, en la lista de pedidos, salía justo el pedido de la señora que me dijo Sofía: **ORD-4852F102, Guadalupe Ramírez Torres, $840, Pendiente**. Qué bueno, ya estaba ligada a la sucursal como prometió Sofía.

## 9:36 a.m. — Llega Guadalupe Ramírez Torres
Me enseñó el folio en su celular: ORD-4852F102. Dijo que quería pagar en efectivo con un billete de $1,000, 3 Naplus.

Primero intenté desde "Pedidos" > "Ver" y ahí sólo pude ver el detalle (Naplus x3, $840, sucursal Tienda Del Valle) pero no encontré botón para cobrar ahí mismo — el texto "Paga aquí" que aparece junto al pedido no es un botón, lo confirmé mirando el HTML, es sólo una etiqueta descriptiva.

Me fui a "Punto de Venta" y ahí sí, arriba decía "1 pedido pendiente de pago en sucursal" con el nombre de Guadalupe y un botón **"Recibir pago"**. Le di clic. Se abrió un cuadro "Recibir pago en sucursal" con el pedido (ORD-4852F102 · $840) y una lista de "Forma de pago" (Efectivo / Tarjeta / Transferencia), ya venía en Efectivo por default. No pedía cuánto dinero me dio, solo la forma de pago. Le di "Confirmar pago".

La pantalla contestó: **"Pago recibido y registrado en caja."** El contador de "Pendientes" pasó de 1 a 0, y "Pagados" de 6 a 7. Mi caja pasó de $0 a "Caja actual $840".

Como el sistema no me pidió el monto recibido, calculé el cambio yo misma con lápiz mental: pagó con $1,000, el total era $840, así que **le regresé $160 de cambio**. Esto no lo dice la pantalla en ningún lado, es cuenta mía.

Después vi que el pedido pasó a la sección "1 pedido pendiente de entregar" (ya pagado, para retiro en sucursal) con un botón **"Entregar"**. Le di clic porque ella ya estaba ahí para llevarse sus productos. La pantalla dijo: **"Orden entregada en sucursal."** y el pedido desapareció de pendientes.

Fui a Pedidos > pestaña "Entregado" para confirmar: ahí sale ORD-4852F102, Guadalupe Ramírez Torres, $840, estado **"Entregada"**, Tienda Del Valle.

## 9:40 a.m. — Llega el señor preguntando por Boom
Me preguntó si tenía Boom, cuánto costaba, y si registrándose le daban puntos.

Busqué en el Punto de Venta, en "Productos disponibles en stock" — sólo salían 3 productos: Colageno Hidrolizado ($700, Disp. 4 · 13 PC), Naplus ($280, Disp. 7 · 6 PC) y Klinhart ($480, Disp. 5 · 10 PC). Boom no aparecía ahí para nada, ni como tarjeta clickeable ni en ningún listado del POS.

Fui a "Stocks" para revisar el inventario completo de Tienda Del Valle y ahí sí vi la fila "Boom — Existencia: 0". En otra parte de esa misma pantalla (donde se arma una transferencia entre bodegas) sale el precio de catálogo: **Boom · $420**.

Entonces le dije: no tenemos Boom en existencia en esta sucursal ahorita (la pantalla marca 0), pero en el catálogo cuesta $420. No lo pude vender porque no aparece como producto disponible para agregar a una venta — lo intenté buscar de nuevo por si se me pasaba y confirmé que el elemento "Boom" no existe en ningún botón/tarjeta visible del punto de venta.

Sobre lo de registrarse: en la pantalla del POS, en la sección de Cliente, dice "las ventas de clientes registrados aplican a metas y descuentos" (a diferencia de "Publico en General" que dice "no acumula consumo, metas ni descuentos personalizados"). O sea que sí parece haber algo de puntos/beneficios para clientes registrados, pero yo no encontré ningún botón de "Registrar cliente nuevo" en el Punto de Venta — sólo hay un buscador que autocompleta entre clientes que YA existen (probé escribir "Roberto Nuevo" y no salió ninguna opción de crear cliente, sólo se quedó filtrando la lista existente sin resultados). No encontré tampoco un módulo de "Clientes" en el menú (sólo tengo: Pedidos, Punto de Venta, Stocks, Campañas). Le dije que por ahora no le podía dar de alta ahí mismo, que tendría que preguntar si hay otra forma.

Como no tenían Boom en existencia, no hubo venta que cobrar — no llegó a comprar nada.

## 9:41–9:42 a.m. — Corte de caja
Al final del turno (simulado) fui a "Punto de Venta" y en "Control de caja actual" le di clic a **"Hacer corte de caja"**. Se abrió un cuadro que decía "Efectivo disponible $840" y me pedía "Monto a dejar en caja". Lo dejé como venía (vacío / $0 a retirar, según decía el texto "Se retirará $0 del efectivo acumulado") y le di "Registrar corte".

La pantalla contestó: **"Corte de caja registrado."** El resumen de "Ultimo corte" quedó así: Monto: $840, Ventas: 1, En caja: $840, Retirado: $0.

Luego entré a "Ver historial de cortes" y ahí apareció el folio: **CUT-F9BC18D6**, 13 nov 2026, 09:42 a.m., Total: $840, Ventas: 1, En caja: $840, Retirado: $0, con opción de descargar CSV.

Me quedé con la duda de si "dejar $840 en caja" era lo correcto o si debía haber retirado el efectivo para entregárselo a alguien — la pantalla no explica qué se supone que haga yo con ese dinero físicamente, sólo registra el número. Como no tenía forma de preguntarle a nadie en ese momento sin gastar mi único mensaje en algo más urgente, lo dejé así y lo anoto aquí como duda.

## Mensajes que mandé
No mandé ningún WhatsApp a Sofía ni a Soporte — todo lo que necesité (el pedido, el botón para cobrar, el corte de caja) lo fui encontrando en pantalla sin trabarme del todo. Si acaso, me hubiera gustado preguntar por lo del "Monto a dejar en caja" pero decidí seguir con lo que la pantalla ya traía por default en vez de gastar mi pregunta en eso.

## Lo que no pude hacer
- No pude vender el Boom al señor porque la sucursal Tienda Del Valle tiene 0 en existencia (lo vi en Stocks); el producto ni siquiera aparece como opción en el Punto de Venta.
- No pude registrar al señor como cliente nuevo — no encontré ningún botón de "crear cliente" ni un módulo de "Clientes" en el menú, sólo un buscador de clientes ya existentes.
- No pude confirmar cuántos "PC" (puntos) hubiera dado el Boom si lo hubiera tenido en stock, porque esa información sólo se muestra junto a los productos que sí están disponibles.
- No supe si "dejar $840 en caja" en el corte era lo correcto, o si debía retirar el efectivo — la pantalla no lo explica.

## Lo que preguntaría
- ¿El botón "Paga aquí" que sale junto al pedido en la pestaña Pedidos hace algo, o el cobro siempre se hace desde Punto de Venta con "Recibir pago"?
- ¿Cómo se registra a un cliente nuevo en el sistema? ¿Hay otro módulo al que yo no tengo acceso, o lo tiene que hacer alguien más (Sofía, o el mismo cliente desde la página)?
- Cuando hago el corte de caja, ¿debo retirar el efectivo físicamente o dejarlo todo en el cajón hasta que venga alguien de administración?
- ¿Cuándo va a haber Boom en existencia en Tienda Del Valle? El cliente se fue sin comprar nada.
