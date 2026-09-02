# Diario de Sofía Herrera — jueves 4 de septiembre de 2026, 6:00 pm

Llego a la oficina después de juntas todo el día. Tengo dos WhatsApp sin contestar (Beto de almacén, Ivonne de recuperación de cuentas) y quiero, además, hacer lo que haría cualquier gerente al cierre del día: ver qué se vendió, qué falta y si algo depende de mí. Llevo dos semanas en el puesto y todavía no conozco bien el sistema, así que voy a comprobar todo antes de contestarle a mi gente — no quiero decirles algo que luego no sea cierto.

## Entrando al sistema

Abro `http://localhost:4321/#/login`. Antes de nada me sale un Aviso de Privacidad que tengo que aceptar ("Entendido y acepto"). Pongo mis credenciales (sofia@findingu.mx) y entro. Aterrizo directo en **Pedidos**, dentro del panel ADMIN.

Lo primero que veo es la tarjeta "Pedidos cargados: $1,760 cobrado · 3 pedidos" y un contador "SIGUIENTE: Confirmar entregas (2)". También veo las pestañas: Pendiente 0, Pagado 0, **Enviado 2**, Entregado 0, **Cancelado 1**. Eso ya me dice algo: hay 3 pedidos en total, pero solo 2 en "Enviado" y 1 en "Cancelado" — ahí puede estar el pedido que a Beto le faltó ver.

## Revisando los pedidos de Beto

Entro a la pestaña **Enviado** (2 pedidos): ahí están Rodrigo Aguilar Ramírez ($960, guía FDU-2026-0001) y Lucia Fernandez ($800, guía FDU-2026-0002), exactamente los dos que Beto dice haber registrado. Abro el detalle de Rodrigo con "Ver": el pedido dice "Guía: FDU-2026-0001 · Stock origen: Sin stock", producto Klinhart x2, dirección en Querétaro.

Esa frase "Sin stock" me preocupa un momento — pensé que podía significar que el envío salió sin descontar inventario. Voy a **Stocks** para comprobarlo. Ahí veo la "Bitácora de inventario": el 04/09/2026 10:19 hay una salida de "Finding Pro 500g -1, Despacho orden ORD-8E2E57C2" y el 04/09 10:17 una salida de "Klinhart -2, Despacho orden ORD-B49F8F4D". El inventario de Klinhart quedó en 38 (de 40) y Finding Pro 500g en 39 (de 40) — exactamente las cantidades vendidas. Es decir: **el stock sí se descontó correctamente al marcar como enviado**. También veo en Configuración, sección "Pedidos", que el switch "Exigir stock al marcar enviado" está activado — el sistema no habría dejado marcar el envío si no hubiera existencia. Así que la etiqueta "Sin stock" en el detalle del pedido no cuadra con lo que muestra la bitácora; no tengo forma de saber, solo mirando la pantalla, qué significa exactamente ese campo "Stock origen: Sin stock" — puede ser una etiqueta de una bodega no asignada, no un problema real de inventario. Lo dejo anotado como duda, no como certeza.

Sobre el pedido que "falta": entro a la pestaña **Cancelado** (1 pedido) y veo: "Prueba Interna · $0 · Cancelada · Motivo cancelación: pedido de prueba interna · 03/09/2026 09:00". Ese es el tercer pedido que contaba el sistema — no es un pedido real de cliente, es una prueba interna cancelada con motivo explícito en pantalla. No hay nada que Beto tenga que atender ahí.

Sobre si puede marcar "Entregado" ya: en **Empleados → permisos**, el sistema describe el permiso así: *"Marcar pedido como Entregado. Cierra el pedido. A partir de aquí cuenta para comisiones."* Eso me confirma que marcar Entregado no es un trámite cualquiera: cierra el pedido y dispara comisiones. El propio flujo que describe la pantalla de Pedidos dice "Pendiente → Pagado → Enviado → Entregado" y hay un botón "Marcar como entregado" en cada fila de Enviado — pero el sistema no me dice en ningún lado si el paquete YA llegó físicamente al cliente. Eso lo sabe el mensajero o el cliente, no la pantalla. No lo voy a marcar yo ni le voy a decir a Beto que lo haga hasta que haya confirmación real de entrega (firma, aviso del cliente o de la paquetería), aunque el sistema lo señale como "siguiente paso" — decido que "siguiente paso sugerido" no es lo mismo que "ya pasó".

Sobre si las guías son válidas o hay que poner guías reales: entro a **Configuración → Envío (Envia.com)**. La integración está activada, con paqueterías "dhl" y "fedex" cargadas y Markup 0%. Pero el sistema no me dice en ningún lado si las guías FDU-2026-0001 y FDU-2026-0002 fueron generadas por esa integración o si Beto las escribió a mano. El formato (FDU-2026-000X) no se parece a un número de guía real de DHL o FedEx, se parece más a un folio interno. No puedo comprobar esto con certeza desde la pantalla — es una pregunta que le tengo que devolver a Beto y, si hace falta, a sistemas.

## Revisando lo de Ivonne

Voy a **Clientes**. Veo 3 clientes en total: Karla Méndez López, Rodrigo Aguilar Ramírez y Marcela Ortiz. Ivonne me dijo que el sistema "no da el teléfono en ningún lado, solo el correo" — busco a Karla y abro su ficha con "Ver": en el panel derecho "Detalle del cliente" aparece:
- Karla Méndez López — karla.mendez@outlook.com — **+52 8115551234** (con enlace directo a WhatsApp).

Busco a Marcela Ortiz (con el buscador "Marcela") y abro su ficha:
- Marcela Ortiz — marcela.ortiz@gmail.com — **5552000001**.

O sea: el teléfono **sí está en el sistema**, pero no en la lista general de clientes (ahí solo salen nombre, estatus, descuento) — hay que entrar a la ficha individual de cada cliente ("Ver") para verlo, en la columna de contacto junto al correo. Entiendo por qué a Ivonne se le fue: en la lista no se ve, solo en el detalle.

## Revisión de gerente — cierre del día

- **Acciones urgentes** (icono de rayo, arriba): dice "0 urgentes" y al abrirlo, "Todo en orden. No hay acciones urgentes pendientes."
- **Notificaciones**: 0 registradas, "Aún no hay notificaciones programadas." Nada que avisar a mi equipo desde ahí.
- **Estadísticas** (septiembre 2026): "Ventas del periodo: $0 · 3 pedidos", "Ticket promedio: $0 · 0% entregados", "Clientes activos: 1 · 0% recompra", "Productos vendidos: 4 · 2 SKUs distintos". Entiendo que "Ventas del periodo" solo cuenta lo que ya está en Entregado (0% entregados = $0), aunque hay $1,760 cobrados. "Advertencias operativas: Sin advertencias activas." En "Pedidos por estado" aparece shipped 2 / cancelled 1. En "Top clientes del periodo" los nombres salen mal: "1788340136546", "0", "None" en vez de nombres de cliente — esto me parece un defecto de la pantalla, no algo que yo tenga que resolver operativamente, pero lo anoto para avisar a sistemas.
- **Cuadro de Honor** (septiembre 2026): Rodrigo Aguilar Ramírez #1 (VG 19, VP 19), Marcela Ortiz #2 (VG 19, VP 0), Karla Méndez López #3 (VG 0, VP 0). Nada que requiera acción mía hoy.
- **Clientes → Comisiones por depositar: $0**. Coherente con que nada está Entregado todavía — no hay nada pendiente de pagar en comisiones hoy.
- **Configuración**: repasé rápido, sin tocar nada (me daba miedo cambiar una regla de negocio sin saber su efecto real — comisiones, rangos, bonos). Vi que "Exigir stock al marcar enviado" y "Exigir líneas de salida al marcar enviado" están activados, que hay 5 niveles de descuento y 5 generaciones de comisión configuradas, y que la sección de bonos tiene reglas cargadas. No modifiqué nada: no es algo que el sistema me señale como pendiente, y prefiero no tocar configuración de comisiones sin entender bien el impacto.
- **Empleados**: 4 empleados activos (Ivonne, Paco, Beto, yo). Vi el detalle de permisos de Ivonne: tiene 4 de 30 permisos concedidos. No cambié nada ahí tampoco.

## Lo que sentí

Al entrar, alivio de ver "0 urgentes" y "Todo en orden" — pensé que iba a encontrar algo roto. Cuando vi "Sin stock" en el pedido de Rodrigo sentí un pico de alarma (¿envié algo que no había en bodega?) que se calmó al cruzarlo con la bitácora de Stocks y ver que sí se descontó bien — ahí sentí que "sé buscar la prueba", que es algo. Cuando no pude confirmar si las guías son reales me sentí genuinamente insegura: el sistema simplemente no contesta esa pregunta, y no quiero inventarle una respuesta a Beto. Con Ivonne sentí más control: encontrar los teléfonos fue rápido en cuanto entendí que había que entrar al detalle del cliente, no quedarme en la lista.

## Dónde me sentí sin control

En el detalle del pedido de Rodrigo, frente a la frase exacta **"Stock origen: Sin stock"**, no supe interpretarla con seguridad — significa cosas distintas según cómo se lea, y el sistema no la explica. Tampoco supe, mirando la pantalla de Configuración → Envío (Envia.com), si las guías FDU-2026-0001/0002 salieron de esa integración o si Beto las tecleó él mismo; el sistema no distingue eso en ningún lado visible para mí.

## Lo que me faltó

Me faltó un lugar donde el sistema me diga explícitamente "esta guía es de la paquetería" vs "esta guía es un folio interno". Me faltó también, en la lista general de Clientes, poder ver el teléfono sin tener que abrir cada ficha — le puedo ahorrar tiempo a Ivonne si eso se agrega a la vista de lista. Y me faltó una fuente donde confirmar entregas físicas reales (no solo el estado del sistema) — hoy decidí no marcar nada como "Entregado" solo por prudencia, sabiendo que ese clic dispara comisiones y cierra el pedido.
