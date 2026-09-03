# Diario — Sofía Herrera — Turno 14 nov 2026

## 10:01 — Entro al back office
Inicié sesión con sofia@findingu.mx en http://localhost:4321/#/login. El sistema me mandó a la URL `#/admin`, que es donde vive todo el panel (Pedidos, Punto de Venta, Stocks, Clientes, Empleados, Productos, etc.). Ojo: cuando entro por `#/login` con la sesión ya guardada, NO me redirige sola — me vuelve a mostrar el formulario de login. Tengo que ir directo a `#/admin`.

Nota rara: la URL raíz `#/` no es el back office, es la tienda del cliente/socio (ahí Sofía también aparece como "socia" con su propio carrito, su red, etc.). Son dos apps distintas colgadas del mismo dominio. Al principio me confundí y pensé que había perdido el acceso admin.

Pantalla de inicio: Pedidos cargados $17,661.40 · 24 pedidos. Pendientes: 0, Pagados: 2, Pendientes envío: 2.

## 10:05 — Nadia (Empleados)
Fui a Empleados → Ver permisos de Nadia Ruiz. Encontré:
- Su celular YA aparecía como 5551000005 en el campo. Comprobé que Ivonne, Paco y Beto tienen 5551000004, 5551000003, 5551000002 — es una secuencia de datos de prueba, así que el número que pidió Nadia ya estaba cargado desde antes. El botón "Guardar datos" salió deshabilitado porque no había ningún cambio pendiente (confirma que no hay nada sin guardar).
- Permisos: tenía 4 de 30. Marqué "Dar de alta clientes" y le di "Guardar permisos". Mensaje en pantalla: "Permisos del empleado guardados." Confirmé recargando su ficha: ahora dice "5 de 30 permisos concedidos" y el checkbox de "Dar de alta clientes" quedó marcado.

Lo que me costó: los botones "Ver" de cada fila de empleado no tienen la palabra "Ver" como texto plano legible por mi lector de pantallas simple — tuve que ir al aria-label ("Ver permisos de Nadia Ruiz") para dar con el correcto. La primera vez casi marco el permiso equivocado (el de "Acceso a panel admin", que ya estaba en on) por un error mío al mapear los checkboxes — me di cuenta a tiempo y lo corregí antes de guardar nada malo.

## 10:15 — Gel Reductivo (Productos)
Fui a Productos. Gel Reductivo ya figuraba "Retirado". Al abrir su ficha (clic en el renglón de la tabla, no en la versión móvil oculta) aparecieron dos botones que antes no estaban, según me dijo Sistemas ayer: "Reactivar producto" y "Eliminar producto definitivamente". Antes del 12 de noviembre solo había "Reactivar" sin opción de borrar en definitiva.

Le di clic a "Eliminar producto definitivamente". Salió un modal de confirmación ("¿Estás seguro que deseas eliminar Gel Reductivo? Esta acción lo retirará de la tienda y del POS. Cancelar / Eliminar"). Confirmé con "Eliminar".

Resultado en pantalla: mensaje "Producto eliminado: Gel Reductivo." El catálogo pasó de 13 a 12 productos y Gel Reductivo ya no aparece en la lista. Listo, sí se arregló.

## 10:25 — Verónica Sandoval (Clientes) — acceso mínimo
Ojo importante: hay DOS "Verónica" en el sistema — una es cliente/socia ("Verónica Sandoval Ruiz", la que me pidió el encargo) y otra es una cuenta de EMPLEADO de prueba ("Veronica Sandoval Ruiz TEST"). Fui a Clientes, no a Empleados, y abrí la ficha de la cliente real (botón con aria-label "Ver ficha de Verónica Sandoval Ruiz").

Dentro de su ficha hay una sección "Acceso al back office de Verónica Sandoval Ruiz — Solo para socios que además operan la empresa (líderes, promotores). 0 de 30 permisos." con botón "Editar". La abrí y vi el mismo checklist de 30 permisos que en Empleados, más un interruptor aparte arriba: "Acceso a panel admin — Habilitado" (este no cuenta dentro del "de 30").

Marqué exactamente:
- **Acceso a panel admin** (el interruptor maestro — sin esto no puede entrar al panel aunque tenga permisos marcados)
- **Ver Clientes**
- **Ver Cuadro de Honor**

Le di "Guardar permisos". Volví a abrir su ficha desde cero (nuevo script, nueva carga de página) para comprobar que quedó: "2 de 30 permisos" + el interruptor "Acceso a panel admin: Habilitado" marcado, y los checkboxes de Ver Clientes y Ver Cuadro de Honor en `true`. Sí quedó guardado.

No le di "Ver Productos" ni nada de precios/márgenes ni nada operativo — solo lo mínimo que pidió Sofía (perdón, que pedí yo): ver clientes y ver el Cuadro de Honor.

## 10:32 — Pedidos pagados sin enviar / nota para Verónica
Fui a Pedidos → pestaña "Pagado" (2). Ahí apareció:
- ORD-AD9456FF — Claudia Ibarra Soto — $350 — Pagada — sin guía
- **ORD-E056804D — Verónica Sandoval Ruiz — $1,220 — Pagada — sin guía**, fecha 13/11/2026.

O sea que SÍ hay un pedido de Verónica pagado y todavía sin enviar hoy, justo lo que ella se estaba quejando de patrones de retraso (sus dos pedidos de octubre tardaron 42 días).

Fui a su ficha de cliente, sección "Bitácora de contactos" → "Nueva nota", y dejé escrito:

> "Sofía 14/11: Verónica se quejó de que sus 2 pedidos de octubre tardaron 42 días en salir. Hoy además hay un pedido pagado sin enviar (ORD-E056804D, $1,220, pagado 13/11, aun sin guía). Compensación acordada: envío gratis en su próxima compra. Pendiente: avisarle por WhatsApp y registrar el envío de ORD-E056804D cuanto antes."

Verifiqué que quedó guardada recargando su ficha: aparece con fecha "14/11/2026 10:33" bajo mi usuario.

No marqué el envío de ORD-E056804D como enviado porque la tarea no me pedía despachar el pedido, solo dejar la nota de compensación — pero lo anoté como pendiente para no perderlo de vista.

## 10:37 — Boom en Tienda Del Valle (Stocks)
Fui a Stocks. Con "Stock activo" = Tienda Del Valle, el inventario por producto mostró **Boom: 0** unidades. Confirmado, no hay Boom ahí — coincide con la queja del cliente de ayer.

Cambié "Stock activo" a Bodega Central para revisar disponibilidad: Boom mostraba 37 unidades ahí, suficiente para mover 10.

En "Nueva transferencia" puse: Stock origen = Bodega Central, Stock destino = Tienda Del Valle, Solicitado por = Sofía Herrera, Producto = Boom, Cantidad = 10. Clic en "Crear transferencia".

Mensaje en pantalla: "Transferencia creada." Apareció una fila nueva en la tabla de Transferencias: "14/11/2026 10:38 · Bodega Central · Tienda Del Valle · Boom x10 · Pendiente · Recibir".

El folio no se ve como texto en la fila de la tabla (solo dice "Boom x10", sin número de folio visible a simple vista). Lo obtuve revisando la respuesta que la propia pantalla trae al cargar la lista de transferencias (no es texto legible normal, pero sí es la respuesta que la app usa para pintar la tabla): **TRF-7C36CB3B**, estatus "pending". El inventario de Bodega Central bajó de 37 a 27 unidades de Boom, consistente con la salida de 10.

Como quedó "Pendiente" (no "Recibida"), todavía falta que alguien en Tienda Del Valle la reciba — no me tocaba hacer eso hoy, la tarea era solo crearla.

## Lo que no pude hacer
- No registré el envío del pedido ORD-E056804D de Verónica (no estaba en el encargo de hoy, solo dejar la nota; lo dejé anotado como pendiente en la bitácora).
- No recibí la transferencia TRF-7C36CB3B en Tienda Del Valle (quedó "Pendiente"); eso le toca a alguien de esa sucursal.

## Lo que preguntaría
- ¿El interruptor "Acceso a panel admin" (arriba del listado de 30 permisos) es realmente indispensable para que un cliente entre al panel, o basta con los permisos de pantalla? Lo marqué por precaución para Verónica, pero nadie me lo explicó en pantalla — solo lo infiero por analogía con la ficha de empleado.
- ¿Por qué la fila de una transferencia no muestra su folio (TRF-...) en la tabla? Sería útil para dar seguimiento sin tener que buscarlo por otro lado.
- Los renglones "Cliente eliminado" en la lista de Clientes (3 de ellos) — ¿son bajas ARCO ya procesadas? No lo toqué, solo lo dejo anotado porque llama la atención.
