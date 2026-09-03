# Diario de Beto Salinas — Turno 7

**Fecha simulada:** 14 de noviembre de 2026
**Hora de inicio:** aprox. 3:00 pm (reloj del sistema marcó `2026-11-14T10:42:48Z` al entrar)

---

## 15:00 — Entro al sistema

Fui a `http://localhost:4321/#/login`. La sesión guardada del navegador `beto` no sirvió (me mandó de nuevo a la pantalla de LOGIN aunque ya había cerrado sesión con éxito antes), así que metí otra vez `beto@findingu.mx` / `U4Z3GEUEGP` y le di "Ingresar al panel". Entré bien: arriba dice "Beto Salinas · ADMIN" y "Acciones · 3 urgentes".

El tablero de Pedidos mostraba: Preparar envíos 2, Confirmar entregas 3, Recibir devoluciones 1. Pestañas: Pendiente 0, Pagado 2, Enviado 3, Entregado 11, Cancelado 6, Reembolsado 1, Por devolver 1, Devuelto (vacío), Dev. rechazada.

## Tarea 1 — Devolución de Guadalupe Ochoa Lara (ORD-B4D33503 / RET-671AA6F5)

Entré a la pestaña "Por devolver 1" y ahí estaba el pedido: `ORD-B4D33503`, Guadalupe Ochoa Lara, $1,386, estado "En Devolución", guía "Estafeta EST-MX-88120041 · Bodega Central". Botón "Recibir paquete".

Al hacer clic salió un modal: "Recibir paquete de devolución — Pedido: ORD-B4D33503. Adjunta fotos del estado del paquete recibido. Esto marcará la devolución como validada." Solo había un campo de "Fotos del paquete *" (tipo archivo). **No hay ningún campo de texto para anotar el motivo o el estado** (tapa rota, sello abierto, falta polvo) — solo puedo subir fotos, no escribir nada. Esto me dejó dudando si bastaba con las fotos.

Como me pidió Sofía, no me invento fotos reales: yo mismo generé dos PNG pequeños con Node (`foto-tapa-rota.png` y `foto-sello-abierto.png`, 1x1 píxel cada uno, hechos a propósito para esta prueba, no son fotos reales del bote) y los subí con `setInputFiles`. El sistema los aceptó y mostró "2 imagen(es) adjunta(s)".

Le di "Confirmar recepción" y la pantalla dijo: **"Paquete recibido. Devolución validada."** El contador de la barra "SIGUIENTE" cambió de "Recibir devoluciones 1" a "Resolver devoluciones validadas 1". La pestaña "Por devolver" bajó a 0 y "Devuelto" subió a 1.

Volví a entrar a la pestaña "Devuelto 1" para comprobar: ahí está `ORD-B4D33503`, Guadalupe Ochoa Lara, $1,386, **Estado: "Devuelta"**, con botones "Reembolsar" y "Rechazar" disponibles. No toqué esos botones porque Sofía dijo que la inspección (decidir si se rechaza o se reembolsa) la hace ella.

## Tarea 2 — Transferencia TRF-7C36CB3B (10 Boom, Bodega Central → Tienda Del Valle)

Entré a "Stocks". Con "Stock activo" en Tienda Del Valle vi el inventario: Boom en 0 piezas todavía. En la sección "Transferencias" apareció una fila: "14/11/2026 10:38 · Bodega Central → Tienda Del Valle · Boom x10 · Pendiente · Recibir".

El texto de ayuda dice: "Elige primero quién recibe (debe estar vinculado al almacén destino); sin eso el botón 'Recibir' no responde." Elegí "Beto Salinas · beto@findingu.mx" en el selector "Usuario que recibe" (comprobé que sí estoy vinculado a Tienda Del Valle: en "Empleados vinculados" aparece marcado junto con Nadia Ruiz).

Al hacer clic en "Recibir" salió un **cuadro de diálogo del navegador (prompt)**, algo que no esperaba en un formulario normal: *"Boom: enviados 10. ¿Cuántos llegaron?"*. Sofía me dijo que llegaron las 10, así que contesté **10**.

La pantalla respondió: **"Transferencia recibida."** El contador "Pendientes recibir" bajó de 1 a 0. En el inventario de Tienda Del Valle, la fila de "Boom" ahora muestra **existencia: 10**. La transferencia en la tabla pasó de "Pendiente" a "Recibida".

## Tarea 3 — Envío de ORD-E056804D (Verónica Sandoval Ruiz, guía EST-MX-88120047)

En "Pedidos" → pestaña "Pagado 2" encontré `ORD-E056804D`, Verónica Sandoval Ruiz, $1,220. Tenía dos pedidos pagados en pantalla (el otro era de Claudia Ibarra Soto, que tenía además el botón "Sucursal" porque es pickup); confirmé por el texto de la tarjeta que el botón "Registrar envío" que toqué era el de la fila de Verónica antes de darle clic.

Se abrió el modal "Enviar pedido — Ingresa la guía o los datos de entrega personal." Con el texto: "El cliente eligió Estafeta al pagar." Llené:
- Stock origen: **Bodega Central**
- Tipo de entrega: Paquetería (Guía) — ya venía así
- Paquetería: **Estafeta**
- Número de guía: **EST-MX-88120047**

Le di "Marcar como enviado" y la pantalla contestó: **"Envio registrado."** Los contadores cambiaron: Pagados bajó de 2 a 1, Enviados subió de 3 a 4.

Entré a la pestaña "Enviado 4" para comprobar: ahí está `ORD-E056804D`, Verónica Sandoval Ruiz, $1,220, **Estado: "Enviada"**, con "Guia: EST-MX-88120047 · Bodega Central".

Una cosa que me llamó la atención: en los otros tres pedidos enviados de la lista, la guía se muestra como "Guia: Estafeta EST-MX-88120044" (con la palabra "Estafeta" antes del número), pero en el mío quedó "Guia: EST-MX-88120047" sin la palabra "Estafeta" delante. El número de guía es el correcto de todos modos.

## Lo que no pude hacer

- No pude anotar por escrito en el sistema el detalle de "tapa rota + sello de seguridad abierto + falta un tercio del polvo" del bote de Colágeno devuelto: el formulario de "Recibir paquete de devolución" solo tiene campo de fotos, no hay cuadro de texto ni de comentarios. Documenté solo con las dos fotos que subí.
- Las "fotos" que subí son PNG de 1x1 píxel generados por mí con Node, no fotos reales del bote — lo dejo claro porque así me lo pidieron.

## Lo que me confundió

- Al inicio la sesión guardada no me mantuvo dentro; tuve que loguearme de nuevo cada vez que abría un script nuevo.
- El formulario de "Recibir paquete de devolución" no deja escribir nada, solo subir fotos, aunque el mensaje de Sofía pedía documentar detalles específicos (tapa rota, sello abierto, falta de producto).
- Al recibir la transferencia salió un cuadro de diálogo del navegador (tipo prompt), no un campo dentro de la página — la primera vez que probé sin manejarlo, el clic en "Recibir" no hizo nada visible.
- La guía del pedido ORD-E056804D se ve sin la palabra "Estafeta" antes del número, distinto a como se ven las guías de otros pedidos ya enviados.

## Lo que preguntaría

- 📱 A Sofía: mandé este mensaje: "Sofía, ya recibí el bote de Guadalupe (ORD-B4D33503) y subí 2 fotos, pero el formulario de recepción de devoluciones no tiene dónde escribir texto — solo fotos. No pude anotar ahí lo de la tapa rota, el sello abierto y que falta como un tercio del polvo. ¿Cómo le hago llegar esa descripción, o te la paso por aquí para que la tengas al inspeccionar?"
- ¿Por qué la guía de ORD-E056804D no muestra "Estafeta" antes del número como los demás pedidos enviados? ¿Está bien registrada o hay que corregir algo?
