# Diario — Sofía Herrera — Turno 15/11/2026

## 10:00 — Entrada
Entré con `sofia@findingu.mx` en http://localhost:4321/#/login. Quedé directo en Pedidos (rol admin). El panel mostraba: "Pedidos cargados $17,661.40 · cobrado · 24 pedidos", con badges "Preparar envíos 1", "Confirmar entregas 4", "Resolver devoluciones validadas 1".

## 10:05 — Tarea 1: devolución de Guadalupe Ochoa Lara (ORD-B4D33503)
Fui a la pestaña "Devuelto 1". Ahí apareció:
> 12/11/2026 · ORD-B4D33503 · Guadalupe Ochoa Lara · $1,386 · Devuelta · Guia: Estafeta EST-MX-88120041 · Bodega Central

Abrí "Ver" para revisar antes de decidir. En el detalle solo vi productos ($700 Colágeno Hidrolizado, $840 Naplus — nota: el pedido trae 2 productos, no solo el colágeno que mencionó Beto), dirección, guía, un campo "Notas internas" vacío, y al final una franja: "Solicitud devolución: RET-671AA6F5 — Aprobada". Probé hacer clic sobre ese texto por si abría las fotos que subió Beto: no pasó nada, no es clicable. No encontré en ningún lado las 2 fotos ni ninguna nota de inspección. Esto confirma lo que dijo Beto: el formulario viejo no tenía dónde escribir, y el sistema solo guardó "Aprobada" sin más detalle.

Le di clic a "Rechazar". Se abrió un modal: "Rechazar devolución — Pedido: ORD-B4D33503 — Esta acción marcará la devolución como rechazada y notificará al cliente." con un campo obligatorio "Motivo del rechazo *".

Escribí como motivo:
> "El sello de seguridad del bote ya estaba abierto y falta aproximadamente un tercio del polvo (producto consumido), aunque la tapa haya llegado rota en el transporte. Por política, un producto abierto y consumido no es procedente para devolución. Como cortesía, se le ofrece a la clienta un 20% de descuento en su próximo bote."

Confirmé. La pantalla mostró el mensaje "Devolución rechazada." y el pedido desapareció de "Devuelto" (quedó en 0) y apareció en "Dev. rechazada 1". Volví a abrir "Ver" en esa pestaña y confirmé el estado final:
> Estado: "Dev. Rechazada" · "Solicitud devolución: RET-671AA6F5 — Rechazada"

**Duda sobre el aviso a la clienta:** el modal dijo que "notificará al cliente" (antes de confirmar), pero después de confirmar no vi en pantalla ningún texto tipo "aviso enviado" ni bitácora de notificación. Revisé también la sección "Notificaciones" del menú, pero es para avisos internos/marketing (banners de inicio de sesión), no un historial de notificaciones a clientes. No tengo forma de ver el correo de Guadalupe, así que no puedo confirmar si le llegó el aviso — solo lo que la pantalla me mostró.

📱 A Sistemas: Oye, rechacé la devolución RET-671AA6F5 de Guadalupe Ochoa (ORD-B4D33503) y el sistema dijo que "notificará al cliente", pero no veo en ningún lado una confirmación de que el aviso salió. ¿Hay una bitácora de notificaciones a clientes que pueda consultar, o eso solo se ve del lado de ustedes?

## 10:20 — Tarea 2: nuevo formulario "Recibir paquete de devolución"
Fui a la pestaña "Por devolver" en Pedidos. Estaba vacía: "0 pedidos" / "No hay pedidos en este estado." No encontré manera de abrir el formulario nuevo sin un pedido real en ese estado, así que no pude probarlo ni describir el checklist que mencionó Sistemas.

📱 A Sistemas: Fui a revisar el formulario nuevo de "Recibir paquete de devolución" que me dijeron que cambiaron (con checklist y notas), pero ahora mismo no hay ningún pedido en "Por devolver" para abrirlo. ¿Me avisan cuando haya uno, o hay forma de verlo sin un pedido real?

## 10:30 — Tarea 3: acceso de Verónica Sandoval
Primero busqué en "Empleados" y encontré una fila "Veronica Sandoval Ruiz Ruiz TEST" (veronica.sandoval.coach@findingu.mx) con acceso a panel Habilitado pero solo "Ver Cuadro de Honor" marcado (Ver Clientes NO estaba marcado ahí) — parece un registro de prueba distinto, con "TEST" en el nombre.

La socia real la encontré en "Clientes": **Verónica Sandoval Ruiz** (veronica.sandoval@gmail.com), estatus "Activa". En su ficha, la sección "Acceso al back office de Verónica Sandoval Ruiz" decía: "Solo para socios que además operan la empresa (líderes, promotores). 2 de 30 permisos." Entré a "Editar" y confirmé los checkboxes marcados:
- "Acceso a panel admin" → Habilitado (true)
- "Ver Clientes" → true
- "Ver Cuadro de Honor" → true
- todo lo demás sin marcar

Es decir, su acceso sigue activo con exactamente los 2 permisos que se esperaban.

También noté en su bitácora una nota mía de ayer (14/11 10:33) donde ya se había acordado la compensación de envío gratis por el retraso de sus pedidos de octubre, y que mencionaba un pedido pagado sin enviar: ORD-E056804D ($1,220, pagado 13/11, sin guía).

Agregué la nota pedida en "Nueva nota" → "Agregar nota". El campo aceptó el texto:
> "15/11: acceso al back office activo; compensación envío gratis próxima compra confirmada"

La pantalla mostró "Nota agregada." y la nota quedó visible en la bitácora con el sello "1788339615521 · 15/11/2026 10:15".

## 10:40 — Tarea 4: pedidos pagados sin enviar y ORD-AD9456FF
Fui a Pedidos → "Pagado". El contador del header decía "Pagados: 1". La lista mostró un solo pedido:
> 13/11/2026 · ORD-AD9456FF · Claudia Ibarra Soto · $350 · Pagada · Sucursal: Tienda Del Valle

Antes de eso, quise verificar si ORD-E056804D (el que mencionaba mi nota de ayer sobre Verónica) seguía pagado sin enviar. Lo busqué en la pestaña "Enviado" y sí apareció ahí:
> ORD-E056804D · Verónica Sandoval Ruiz · $1,220 · Enviada · Guia: EST-MX-88120047 · Bodega Central

O sea, ya se registró su envío entre ayer y hoy — ya no está pendiente.

Abrí el detalle de ORD-AD9456FF (sin marcarlo como enviado ni tocar nada más). Los botones de acción disponibles eran "Registrar envío" y "Cancelar pedido" — no había opción de "Marcar como entregado", y el estado seguía mostrando "Pagada". Con eso concluyo que el pedido **NO ha sido entregado en la sucursal** todavía; solo está pagado, con recolección en Tienda Del Valle pendiente.

## Lo que no pude hacer
- No pude ver las 2 fotos que Beto subió de la devolución de Guadalupe, ni ninguna nota de inspección — el detalle del pedido no las muestra en ningún lugar visible ni son clicables.
- No pude confirmar en pantalla si a Guadalupe le llegó efectivamente el aviso del rechazo (solo vi la advertencia previa "notificará al cliente" y el mensaje "Devolución rechazada."); no tengo acceso a su correo.
- No pude abrir ni describir el nuevo formulario "Recibir paquete de devolución" con checklist porque no había ningún pedido en "Por devolver".

## Lo que preguntaría
- ¿Dónde quedan guardadas las fotos que sube el personal de bodega al recibir una devolución? No las vi en el detalle del pedido.
- ¿Hay una bitácora de notificaciones enviadas a clientes (correo/WhatsApp) que se pueda consultar desde el back office?
- ¿Por qué existe un registro de empleado "Veronica Sandoval Ruiz TEST" con correo distinto (veronica.sandoval.coach@findingu.mx) y permisos distintos a los de la ficha de cliente real de Verónica? ¿Es un duplicado de prueba que se pueda dar de baja?
