# Diario de Nadia — 13 de diciembre de 2026 — Tienda Del Valle

## 10:34 a.m. — Entro a mi turno
Entré con `nadia@findingu.mx`. La pantalla de inicio (`#/admin`) me muestra "Nadia Ruiz · ADMIN", "2 urgentes" en Acciones, y el resumen de Pedidos ($28,858.40 cobrado, 37 pedidos, +$560 por cobrar). Ya había un pedido pendiente de hoy mismo: Guadalupe Ramírez Torres, ORD-531EF896, $560, Naplus×2, 13 dic 2026 10:34 a.m. — no es mío, no lo toco.

Entré a Punto de Venta: el stock ligado ya es **Tienda Del Valle · Av. Coyoacán 1200**, así que no tuve que cambiar de sucursal como me advirtieron que podría pasar. Caja actual: $840 (fondo dejado en el corte del 13 nov). Solo 4 productos con existencia aquí: Colageno Hidrolizado, Naplus, Boom, Klinhart.

## 11:10 a.m. — Roberto Chávez Mena, 2 Boom, pago parcial ($500 efectivo)
Lo busco en el selector de cliente y aparece de inmediato: "Roberto Chávez Mena · roberto.chavez.m@gmail.com". Agrego 2× Boom ($420 c/u) → Subtotal $840. Elijo "Pago parcial".

Aquí me salió un modal que no esperaba: **"Autorizacion requerida — Ingresa el codigo de autorizacion para registrar pago parcial."** con un campo de 4 dígitos y el texto "Lo tiene la gerencia (Configuración → Código de autorización POS); pídeselo a tu gerente." Metí el código que me dio Sofía, **7412**, y me lo rechazó: **"Codigo de autorizacion incorrecto"**. La respuesta del servidor (la vi en la consola de red) fue `403 {"message": "Codigo de autorizacion incorrecto"}`.

Lo intenté cuatro veces distintas, con calma, revisando que el campo realmente tuviera "7412" escrito (lo confirmé) — siempre el mismo rechazo, siempre el mismo 403. No es un error mío de captura ni de la pantalla trabada: el sistema, de plano, no acepta ese código para pago parcial.

Le mandé un WhatsApp a Sofía explicándolo. No tengo forma de conseguir el código correcto yo sola — el propio sistema dice que solo "Configuración → Código de autorización POS" lo tiene la gerencia, y yo no tengo esa sección en mi menú (solo veo Pedidos, Punto de Venta, Stocks, Campañas).

Sin el código no pude cobrar el pago parcial. No se generó ningún folio de venta para Roberto. Se lo tuve que dejar pendiente — nada quedó registrado en el sistema para él hoy.

## 11:40 a.m. — Roberto regresa a liquidar
Como la venta original nunca se registró (por lo del código), no había nada que liquidar. Revisé "Pedidos" y el único pendiente de hoy sigue siendo el de Guadalupe Ramírez Torres ($560, Naplus×2) — nada de Roberto. Tampoco aparece nada suyo en "Ventas registradas" de mi caja de hoy. No pude hacer el cobro de saldo porque el saldo mismo nunca llegó a existir.

## 12:10 p.m. — Clienta de mostrador, Magnesio Glicinato 120 caps
Revisé el stock de Del Valle (en Punto de Venta y también en Stocks → Inventario por producto): "Magnesio Glicinato 120 caps" figura con **existencia 0** en esta sucursal (en Stocks aparece como catálogo, precio $520, pero 0 piezas aquí). No puedo vendérselo.

Le ofrecí Klinhart ($480, el más cercano a $500 de lo que sí tengo). Con Público en General (default), agregué 1 Klinhart, capturé "Efectivo recibido: 1000" y el sistema calculó solo: **"Cambio: $520 — Sobre un total de $480"**. Cobré y me confirmó en pantalla: **"Venta registrada en caja."** — folio **POS-268B0286**, Publico en General, $480, 13 dic 2026 10:53 a.m., Tienda Del Valle. La caja subió de $840 a $1,320 y el stock de Klinhart bajó de Disp. 4 a Disp. 3.

## 1:00 p.m. — Sofía pasa por el efectivo
Caja actual: $1,320. Debía retirar todo menos $500 de fondo → $820, motivo "entrega a gerencia", con el código 7412.

Probé "Retirar efectivo": mismo problema. El formulario también pide el código de autorización, y con 7412 me volvió a rechazar: **"Codigo de autorizacion incorrecto"** (esta vez el endpoint fue `/inventory/pos/withdrawal`, también 403). Le avisé a Sofía por WhatsApp que tampoco me sirvió ahí.

Como no pude autorizar el retiro por separado, hice el **corte de caja** directamente (ese botón no pide código): puse "Monto a dejar en caja: 500" y la pantalla me mostró antes de confirmar "Se retirará $820 del efectivo acumulado." Al registrar, me confirmó: **"Corte de caja registrado."** El resumen quedó así: Último corte 13 dic 2026 10:54 a.m., Monto: $480, Ventas: 1, En caja: $500, Retirado: $820. Esto logra el mismo resultado que pedía Sofía (dejar $500, que se lleven el resto), pero no quedó registrado con el motivo "entrega a gerencia" porque ese campo solo existe en el flujo de "Retirar efectivo", que no pude usar.

Volví a probar el código 7412 una vez más por si acaso, después de todo esto — sigue rechazado.

## Lo que sentí / lo que me confundió
- Me dio harta pena con Roberto: le dije que sí le fiaba el resto y a la hora de cobrar no pude. Se quedó sin sus Boom.
- No entendí por qué el código que me pasó Sofía "ayer" no sirve hoy — ¿cambia diario? ¿me equivoqué de dígitos? Lo revisé letra por letra en la pantalla y estaba bien escrito.
- Me tranquilizó ver que el corte de caja SÍ se pudo hacer sin código, y que dejó exactamente $500 como se pedía — al menos el efectivo quedó cuadrado aunque el retiro formal no se pudo registrar como tal.
- La pantalla de "Configuración → Código de autorización POS" que menciona el modal no aparece en mi menú — solo la ve gerencia, según entiendo.

## Lo que no pude hacer
- Cobrar el pago parcial de Roberto Chávez Mena (2 Boom, $840, $500 en efectivo). Bloqueado por "Codigo de autorizacion incorrecto" con el código 7412, probado 4 veces.
- Liquidar el saldo de Roberto a las 11:40 — no existía saldo que liquidar porque la venta original no se registró.
- Vender Magnesio Glicinato 120 caps — no hay existencia en Tienda Del Valle (0 piezas). Vendí Klinhart ($480) como sustituto.
- Registrar el retiro de efectivo formal de Sofía con motivo "entrega a gerencia" — mismo código rechazado (403 en `/inventory/pos/withdrawal`). Sí completé el corte de caja dejando $500 de fondo, que retiró los $820 restantes, pero sin el campo de motivo.

## Lo que preguntaría
- A Sofía: ¿el código de autorización cambia todos los días? ¿Cuál es el correcto para hoy 13 de diciembre?
- ¿Hay manera de que yo vea el código sin pasar por gerencia, o siempre tengo que pedirlo por WhatsApp cuando lo necesite?
- Si el pago parcial se queda bloqueado, ¿qué le digo al cliente? ¿Lo mando a Pedidos en línea, o simplemente le pido que junte todo el efectivo?
- ¿Puedo pedir traspaso de Magnesio Glicinato 120 caps a Del Valle, ya que el catálogo lo tiene a $520 pero aquí no hay ni una pieza?
