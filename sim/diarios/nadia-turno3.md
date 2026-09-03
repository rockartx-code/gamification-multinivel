# Diario de Nadia — Turno 3, Tienda Del Valle
**15 de noviembre de 2026**

## 10:01 — Entrada
Entré a http://localhost:4321/#/login con `nadia@findingu.mx` / `Nadia2024!`. El login me llevó directo a `#/admin`. Arriba dice "Nadia Ruiz — ADMIN" (raro para una cajera, pero es lo que muestra la pantalla). El resumen inicial: "Pedidos cargados $17,661.40 · cobrado · 24 pedidos", "Pendientes: 0 / Pagados: 1 / Pendientes envío: 1".

Entré a Punto de Venta. Ya estaba en **Tienda Del Valle** (Stock actual: Tienda Del Valle, Operador: Nadia Ruiz), así que no tuve que cambiar de sucursal como me advirtieron que podría pasar. Caja actual: $840. Inicio de caja: "13 nov 2026, 09:42 a.m." — o sea la caja se abrió hace dos días, no hoy; el sistema no me dio opción de abrir una caja nueva.

## 11:10 — Claudia Ibarra Soto (ORD-AD9456FF)
La vi de inmediato en el panel: "1 pedido pendiente de entregar — Claudia Ibarra Soto, #ORD-AD9456FF, 13 nov 2026 05:29 p.m., $350, Biotina ×1" con botón "Entregar".

Le di clic a "Entregar" y me salió una alerta roja: **"Http failure response for http://localhost:4400/orders/ORD-AD9456FF: 400 Bad Request"**. Lo intenté una segunda vez y até la respuesta exacta del servidor: `{"message": "Stock insuficiente para el producto 1788339615590"}`.

Me metí a Stocks para ver qué pasaba. En "Inventario por producto" de Tienda Del Valle, **Biotina aparece con Existencia: 0**. En la bitácora vi que Biotina sí tuvo una entrada de +40 el 02/09/2026, pero fue en **Bodega Central**, no en Del Valle — nunca le transfirieron nada a mi tienda. El pedido de Claudia se pagó en línea pero el producto físicamente no está aquí.

No pude entregarlo. Me sentí muy mal, la señora venía con el folio en el celular y yo sin poder hacer nada porque el sistema no me deja "inventar" stock que no existe.

📱 A Sofía: Oye, el pedido de Claudia (ORD-AD9456FF, 1 Biotina, ya pagado) no lo pude entregar. El sistema me marca "Stock insuficiente para el producto 1788339615590" y en Stocks veo que Tienda Del Valle tiene 0 Biotina — la entrada de 40 piezas del 2 de septiembre se quedó en Bodega Central, nunca nos transfirieron nada acá. ¿Me autorizas pedir una transferencia urgente o qué le digo a la clienta?

**No pude marcar la entrega en el sistema.** Verifiqué después en Pedidos → pestaña "Pagado": el pedido sigue ahí, estado **"Pagada"**, Guía/Entrega "-". No avanzó a Entregado.

## 11:30 — Roberto Chávez Mena (alta + venta)
Sofía me había avisado por WhatsApp que ya tengo permiso para dar de alta clientes desde el POS. Probé el botón "Nuevo cliente" en Punto de Venta y sí me dejó. Llené el formulario: Nombre "Roberto", Apellido paterno "Chávez", Apellido materno "Mena", Teléfono "5559871234", Email "roberto.chavez.m@gmail.com".

Al dar clic en "Crear cliente" la pantalla dijo **"Cliente creado y seleccionado en POS."** y quedó seleccionado arriba: "Roberto Chávez Mena / roberto.chavez.m@gmail.com — Descuento actual: 0% / Meta proyectada: 0%".

Le agregué 2 Boom (aprendí que hay que dar un solo clic en el producto — dos clics lo marcan y desmarcan el checkbox — y luego aparece un campo "Cantidad" donde puse 2). Subtotal $840. Cambié "Forma de pago" a Tarjeta y di clic en "Cobrar $840".

La pantalla confirmó: **"Venta registrada en caja."** Apareció en "Ventas registradas → Tarjeta": folio **POS-6947D029**, Roberto Chávez Mena, $840, 15 nov 2026, 10:12 a.m., Tienda Del Valle.

Busqué en toda la pantalla la palabra "puntos" y no aparece en ningún lado del POS ni de Campañas (que es la única otra sección que tengo en el menú). Solo se muestran "Descuento actual / Descuento aplicable / Siguiente meta ($ para el próximo % de descuento)", nunca un número de puntos. No pude decirle a Roberto cuántos puntos ganó porque el sistema nunca me lo mostró.

📱 A Sofía: Ya di de alta a Roberto y le cobré sus 2 Boom con tarjeta ($840, folio POS-6947D029). Pero no encuentro en ninguna pantalla cuántos puntos le dio la compra — solo veo lo de descuentos por meta. ¿Eso se ve en otro lado que yo no tengo, o de plano no se muestra aquí?

## 12:00 — Bety (Beatriz) Ochoa
Busqué "bety.ochoa45@hotmail.com" en "Buscar cliente" del POS y sí apareció como **Beatriz Ochoa Lara**. La seleccioné y su ficha mostró: "Consumo acumulado del mes $0 / Descuento actual 0% / Descuento aplicable hoy 0% / Siguiente meta: Descuento 10% — **Faltan $1,000**". Con eso le contesté: le faltan $1,000 en compras del mes para llegar al 10% de descuento.

Para lo del pago mixto: agregué 1 Klinhart ($480) y probé el selector "Tipo de pago → Pago parcial", pensando que ahí podría dividir el monto. En vez de eso salió un modal **"Autorización requerida — Ingresa el código de autorización para registrar pago parcial"** con un campo "Código de autorización" que no tengo. Ese "Pago parcial" resultó ser para dejar un saldo pendiente con autorización de un supervisor, no para combinar efectivo y tarjeta en la misma venta. Revisé toda la pantalla: "Forma de pago" es un único selector (Efectivo / Tarjeta / Transferencia), no hay forma de marcar dos métodos a la vez.

Cancelé ese modal y, siguiendo el plan de respaldo, le cobré todo con Tarjeta: 1 Klinhart, $480. La pantalla confirmó **"Venta registrada en caja."**, folio **POS-785DCAA4**, Beatriz Ochoa Lara, $480, 15 nov 2026, 10:15 a.m., Tarjeta.

**No se pudo hacer el pago mixto que pidió Bety** ($200 efectivo + $280 tarjeta); el sistema no tiene esa opción visible para mí, o requiere un código de autorización que no tengo.

## Cierre de turno
Fui a "Control de caja actual". Probé **"Retirar efectivo"**: llené Monto $840 y Motivo "Entrega a Sofía - corte de turno", pero el botón **"Confirmar retiro"** permaneció deshabilitado — el modal también pide un "Código de autorización" vacío que no tengo.

Probé **"Hacer corte de caja"**: el botón aparece **deshabilitado desde el inicio del turno** (icono de tijeras en gris, atributo `disabled` en el HTML), sin ningún tooltip o mensaje en pantalla que explique por qué. No pude averiguar la causa solo mirando la pantalla.

📱 A Sofía: Para el retiro de efectivo me pide un "Código de autorización" que no tengo, y "Hacer corte de caja" me sale bloqueado (gris) sin que la pantalla diga por qué. ¿Me pasas el código o hay que hacerlo distinto? Al final del turno dejé los $840 en caja porque no logré registrar el retiro.

**No pude hacer el corte de caja ni el retiro de efectivo.** Caja quedó igual: $840, sin retiros registrados.

---

## Lo que no pude hacer
- Entregar el pedido ORD-AD9456FF de Claudia Ibarra Soto (Biotina) — el sistema rechaza la entrega por "Stock insuficiente para el producto 1788339615590"; Tienda Del Valle tiene 0 unidades de Biotina en Stocks. El pedido sigue en estado "Pagada", sin entregar.
- Decirle a Roberto cuántos puntos le dio su compra — el sistema (POS y Campañas, que son las únicas pantallas que tengo) nunca mostró un número de puntos en ningún momento.
- Cobrarle a Bety con pago mixto (efectivo + tarjeta) — no existe esa opción en "Forma de pago"; "Pago parcial" es otra cosa y pide un código de autorización que no tengo.
- Hacer el corte de caja — el botón está deshabilitado sin explicación visible.
- Registrar el retiro de efectivo para Sofía — el modal pide un código de autorización que no tengo; con el campo vacío "Confirmar retiro" no se activa.

## Lo que preguntaría
- ¿Cómo se supone que resuelva un pedido pagado cuyo producto no tiene stock en mi sucursal? ¿Pido transferencia yo misma desde Stocks, o eso lo hace alguien más?
- ¿Dónde se ven los puntos que gana un cliente por su compra? ¿Es una pantalla que yo no tengo como cajera?
- ¿Existe alguna forma real de cobrar mitad efectivo/mitad tarjeta, o simplemente no está pensado el sistema para eso y hay que elegir un solo método?
- ¿Cuál es el código de autorización para retiros de caja y para pagos parciales, y quién me lo debe dar?
- ¿Por qué "Hacer corte de caja" aparece bloqueado si mi caja lleva dos días abierta con ventas encima?
