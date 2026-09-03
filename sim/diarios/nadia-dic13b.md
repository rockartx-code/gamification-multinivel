# Diario de Nadia — 13 de diciembre de 2026 (tarde) — Tienda Del Valle

## 2:00 p.m. — Retomo con el código nuevo
Sofía me escribió: "Perdón, se quedó el código viejo cuando se fue la luz; ya lo puse en 7412, vuelve a intentar." Entré de nuevo con `nadia@findingu.mx`. La pantalla de Punto de Venta mostró: Caja actual **$500**, Ventas en caja **2**, Stock ligado Tienda Del Valle · Av. Coyoacán 1200. Todo seguía como lo dejé en la mañana (corte con $500 de fondo).

## 2:10 p.m. — Roberto Chávez Mena, 2 Boom, pago parcial ($500 efectivo)
Lo busqué en "Buscar cliente" escribiendo "Roberto" y salió de inmediato: **Roberto Chávez Mena · roberto.chavez.m@gmail.com**. Agregué Boom y puse cantidad **2** → Subtotal **$840**. Elegí "Pago parcial".

Salió el mismo modal de siempre: **"Autorizacion requerida — Ingresa el codigo de autorizacion para registrar pago parcial."** Escribí **7412** y esta vez, al dar "Confirmar", el modal se cerró sin ningún error — no vi ningún 403 en la consola de red. El formulario cambió a mostrar "Monto pagado ahora".

Puse **500** ahí (forma de pago ya estaba en "Efectivo"). La pantalla me mostró antes de cobrar:
- Subtotal: **$840**
- Total neto: **$840**
- Monto a pagar ahora: **$500**
- **Saldo pendiente: $340**

Di clic en "Cobrar $840" y me confirmó con un aviso verde: **"Venta registrada en caja."** Folio: **POS-D7F97B91**, Roberto Chávez Mena, $840, 13 dic 2026, 11:06 a.m., Tienda Del Valle / Usuario 1790935678727. La caja subió de $500 a **$1,000** (los $500 en efectivo que sí entraron), y el stock de Boom bajó de Disp. 8 a Disp. 6. El código 7412 **sí funcionó** esta vez para pago parcial.

Le mandé un WhatsApp a Sofía:
📱 A Sofía: "¡Ahora sí jaló el 7412! Ya le cobré a Roberto sus 2 Boom con $500 en efectivo, quedó un saldo pendiente de $340. Gracias."

## 2:40 p.m. — Roberto regresa a liquidar el saldo ($340) con tarjeta
Busqué cómo cobrar nada más el pendiente:
- En **Punto de Venta**, en el bloque "Ventas registradas → Efectivo" apareció la tarjeta de su venta: **POS-D7F97B91 · Roberto Chávez Mena · $840 · 13 dic 2026, 11:06 a.m.** Es solo una tarjeta informativa — no tiene ningún botón, no es clicable, no dice "$340 pendiente" en ningún lado, solo el total de $840.
- Volví a buscar a Roberto como cliente en el formulario de nueva venta: su ficha muestra "Consumo acumulado del mes: $0", "Descuento actual: 0%" — nada sobre saldo o adeudo.
- Revisé **Pedidos**: solo aparece el pedido de Guadalupe Ramírez Torres (ORD-531EF896, $560, en línea). La venta de mostrador de Roberto (POS-D7F97B91) no aparece ahí — Pedidos solo lista pedidos en línea (ORD-), no ventas de POS.
- Revisé el panel de **Acciones** (3 urgentes): "10 pedidos pagados sin envío", "1 pedidos pendientes de pago" (el de Guadalupe) y "2 ventas POS registradas hoy" (informativo) — ninguna menciona el saldo de $340 de Roberto.

No encontré ningún botón, pestaña ni opción para registrar un abono o liquidar el saldo de una venta de mostrador ya cobrada. El "Pago parcial" solo te deja definir cuánto se cobra AL MOMENTO de la venta; una vez que la venta queda registrada, el sistema no vuelve a mostrar ese folio para cobrarle el resto.

📱 A Sofía: "Roberto ya trae el dinero para liquidar sus $340 con tarjeta, pero no encuentro dónde cobrar el resto de una venta ya hecha — ni en Pedidos ni en el historial de POS hay opción de abono. ¿Cómo le hago?"

No pude completar el cobro del saldo — no existe la opción en pantalla.

## 3:00 p.m. — Retiro de efectivo, "entrega a gerencia"
Caja actual: **$1,000**. Tenía que dejar $500 de fondo y retirar el resto → **$500**. Di clic en "Retirar efectivo" y salió el modal "Retiro de efectivo — Registra un retiro parcial del efectivo acumulado en caja", con tres campos: Monto a retirar, Motivo, Código de autorización.

Llené: Monto a retirar **500**, Motivo **"entrega a gerencia"**, Código de autorización **7412**. Di clic en "Confirmar retiro" y esta vez el sistema respondió: **"Retiro registrado."** — no hubo ningún 403. La caja bajó de $1,000 a **$500**. El código funcionó también aquí (a diferencia de la mañana).

## 3:05 p.m. — Corte de caja
Con la caja ya en $500, hice clic en "Hacer corte de caja". El modal mostró **"Efectivo disponible: $500"**, con "Monto a dejar en caja" prellenado en 500 y el texto **"Se retirará $0 del efectivo acumulado."** (porque ya había retirado los $500 aparte). Di clic en "Registrar corte" y confirmó: **"Corte de caja registrado."**

El resumen quedó: Último corte **13 dic 2026, 11:11 a.m.**, Monto: $0, Ventas: 1, En caja: $500, Retirado: $0.

## Lo que sentí / lo que me confundió
- Alivio de que el código 7412 sí sirvió esta vez, tanto para el pago parcial como para el retiro de efectivo — ya no tuve que dejar a Roberto sin sus Boom.
- Me descolocó no encontrar cómo cobrarle el saldo pendiente a Roberto cuando regresó. El sistema deja muy claro el saldo pendiente ($340) ANTES de cobrar, pero después de que la venta queda registrada, ese dato desaparece de la vista — el folio solo muestra el total ($840), no lo que falta.
- El "Retirado: $0" del corte de las 3:05 me dejó dudando si el retiro de las 3:00 quedó bien contado en el resumen del corte, aunque la caja sí bajó correctamente de $1,000 a $500 en ambos pasos.

## Lo que no pude hacer
- Liquidar el saldo de $340 de la venta POS-D7F97B91 de Roberto Chávez Mena. Busqué en: la tarjeta de la venta en "Ventas registradas" (sin botón), la ficha del cliente en POS (sin indicador de saldo), Pedidos (esa venta no aparece ahí, solo pedidos en línea ORD-), y el panel de Acciones urgentes (no la menciona). No encontré ninguna opción de abono o liquidación de saldo para ventas de mostrador ya cerradas.

## Lo que preguntaría
- A Sofía / gerencia: ¿cómo se cobra el saldo pendiente de una venta de mostrador con pago parcial una vez que ya se registró? ¿Hay que hacer una "venta" nueva por $340 a nombre de Roberto, o existe alguna pantalla que no encontré?
- ¿El folio POS-D7F97B91 queda con algún estatus interno de "saldo pendiente" aunque en pantalla no se vea?
- ¿El código de autorización 7412 va a seguir funcionando mañana, o cambia otra vez?
