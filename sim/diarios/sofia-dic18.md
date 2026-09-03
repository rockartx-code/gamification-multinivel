# Diario de Sofía Herrera — 18 de diciembre de 2026

## 10:00 — Entrada
Entré con `sofia@findingu.mx` en `http://localhost:4321/#/login`. El campo de correo no es `type="email"` sino texto normal con placeholder `tu@correo.com`; mi primer intento de llenar `input[type="email"]` dio timeout, tuve que usar el placeholder. Tras "Ingresar al panel" caí en `#/admin`, que es directo la pantalla de **Pedidos** (no hay una portada "tablero" separada de Pedidos).

Arriba se ve el botón **"Acciones · 2 urgentes"**. Al abrirlo (antes de tocar nada) mostraba:
> "Acciones urgentes — Resolvé pendientes críticos desde aquí."
> - **2 comisiones pendientes por depositar** — Urgente — Ir a resolver
> - **1 pedidos pendientes de pago** — Informativo — Ir a resolver

Ese segundo aviso ("1 pedidos pendientes de pago", Informativo) sí apuntaba de forma genérica al pedido de Guadalupe (era el único Pendiente que había), pero no menciona su nombre ni los 5 días — solo el conteo. Lo confirmé después: en cuanto cancelé su pedido, ese aviso desapareció y "Acciones" bajó a "1 urgentes" (quedó solo la de comisiones).

En la pestaña "Pedidos", la sección "SIGUIENTE" mostraba **"Confirmar pagos · 1"** y **"Resolver devoluciones validadas · 1"** — esas dos sí eran, respectivamente, el pedido pendiente de Guadalupe y la devolución validada de Patricia que dejó Beto.

## 10:05 — Detalle de la devolución de Patricia (ORD-C7345274) antes de reembolsar
Fui a Pedidos → pestaña **"Devuelto · 1"**: ahí estaba ORD-C7345274, Patricia Solís Ek, $381, Estado "Devuelta", guía EST-MX-88120051 · Bodega Central, con acciones "Ver / Reembolsar / Rechazar".

Le di clic a "Ver" (mi primer intento con `button:has-text("Ver")` falló por *strict mode* al no ser único en la página; tuve que usar `getByRole` filtrando el texto exacto). El detalle mostró:

- **Productos del pedido:** Naplus x1 · $280 — **Total: $381**
- **Dirección de envío:** Patricia Solís Ek, Calle Flamboyanes 12, Mérida, CP 97000 YUC, Tel: 9991230000
- **Envío:** Guía EST-MX-88120051, Stock origen: Bodega Central
- **Notas internas (devolución):**
  > "Solicitud devolución: RET-9A996299 — Aprobada"
  > "Motivo del cliente: DESISTIMIENTO · Fue una compra por impulso, ya no lo quiero. El producto está cerrado, sin abrir."
  > "Fotos del cliente: foto 1, foto 2, foto 3"
  > "Recepción en bodega: Caja cerrada, sello intacto, empaque original. Folio RET-9A996299 escrito a mano en la caja. Cliente devuelve por arrepentimiento, no hay daño ni señales de uso."
  > "Fotos al recibir: foto 1"
  > "Checklist: sello intacto · sin uso · empaque original · coincide — 18/12/2026 10:06"

Coincide con lo que Beto anotó en su diario del turno de hoy. No había daño reportado.

**Confusión:** la línea de producto muestra "$280" (precio de catálogo) pero el Total del pedido es "$381". Sofía sabía que el producto se vendió en $252 con descuento y el envío fue $129 ($252+$129=$381 sí cuadra), pero la pantalla no desglosa esos $381 en producto+envío en ningún lado — solo el Total. Lo tuve que calcular yo con el dato que ya traía de antes.

## 10:10 — Registrar el reembolso
Le di clic a "Reembolsar". Se abrió un modal "Registrar reembolso" con este texto:
> "Pedido: ORD-C7345274. Importe a reembolsar. **Cobrado: $381. Sugerido: $381.**"

Es decir: **la pantalla propone reembolsar el total completo ($381), incluyendo el envío**, sin distinguir que fue una devolución por arrepentimiento. Como el envío de ida ($129) y el de regreso corren por cuenta de la clienta en estos casos, cambié el importe a mano a **$252** (solo el producto).

También llené:
- Motivo: *"Devolución por arrepentimiento (RET-9A996299). Se reembolsa solo el producto ($252); el envío de ida ($129) y el de regreso corren por cuenta de la clienta."*
- Comprobante de depósito (obligatorio, marcado con *): subí un PNG que generé para la prueba (`comprobante-reembolso-patricia.png`, 73 bytes).

Al confirmar, el sistema respondió: **"Reembolso registrado correctamente."**

Verifiqué: la pestaña "Devuelto" bajó a 0, "Reembolsado" subió de 2 a 3, y el pedido ORD-C7345274 ahora aparece con Estado **"Reembolsada"** en esa pestaña.

**Lo que no pude confirmar desde la pantalla:** al volver a abrir el detalle del pedido ya reembolsado, la vista solo muestra otra vez "Total: $381" — no hay ningún campo visible de "monto reembolsado" ni se ve el motivo ni el comprobante que subí. No tengo forma, solo mirando la pantalla, de comprobar si quedó registrado el $252 que puse o si el sistema guardó otra cosa. Tampoco vi el motivo que escribí reflejado en ningún lado del detalle del pedido.

## 10:20 — Pedido pendiente de Guadalupe (ORD-531EF896)
Fui a Pedidos → pestaña "Pendiente · 1": ahí estaba, 13/12/2026, Guadalupe Ramírez Torres, $560, Sucursal, "Paga aquí", con acciones "Ver / Marcar como pagado / Cancelar pedido".

Abrí "Ver" antes de cancelar. El detalle mostró:
- **Productos:** Naplus x2 · $560 — Total $560
- **Dirección de envío:** "Sucursal: Tienda Del Valle" (no hay teléfono en esta vista tampoco)
- Sin notas internas previas en el pedido.

Confirmé la fecha: creado 13/12/2026, hoy 18/12/2026 → 5 días exactos sin que se presente a pagar/recoger, tal como me dijeron.

Le di clic a "Cancelar pedido". Apareció un **diálogo nativo del navegador (confirm)**, no un formulario de la app:
> "¿Cancelar el pedido ORD-531EF896 de Guadalupe Ramírez Torres?"

Este cuadro **no ofrece ningún campo para escribir un motivo**, y **no menciona en ningún momento que el pedido no se ha pagado** — es un simple Sí/No genérico (lo probé primero cancelando con "Dismiss" para ver si aparecía algo más después, y no: no hay un segundo paso). Acepté.

El sistema respondió con el texto: **"Pedido ORD-531EF896 cancelado."**

Estado final: pestaña "Pendiente" bajó a 0, "Cancelado" subió de 6 a 7, y en esa pestaña el pedido aparece con Estado **"Cancelada"**. El detalle del pedido, después de cancelar, muestra automáticamente en Notas internas:
> "Motivo cancelación: admin_request · 18/12/2026 10:26"

Es decir, el sistema no guardó ningún motivo mío en texto — solo un código genérico `admin_request`, porque el diálogo nativo nunca me pidió escribir nada. Como el motivo "claro" que me pidieron no quedó registrado en ningún lado de la app, **agregué yo una nota interna en el pedido** (campo "Agregar nota" bajo Notas internas) con el detalle real:
> "18/12: cancelado por Sofía. Clienta no se presentó a pagar/recoger en sucursal (Tienda Del Valle) en 5 días desde la creación (13/12). Motivo del sistema quedó como 'admin_request' genérico."

El sistema la guardó y la mostró con mi usuario y fecha/hora: "· 1788339615521 · 18/12 10:28".

Nota: el pedido cancelado sigue mostrando un botón "Reembolsar" en la lista de "Cancelado" (igual que otros pedidos cancelados), aunque este nunca se pagó ("Paga aquí" sigue ahí). No le di clic porque no hay nada que reembolsar — no hubo cobro.

## 10:30 — Revisión de "Enviado" y "Acciones urgentes" tras los cambios
Pestaña **Enviado**: **"0 pedidos" — "No hay pedidos en este estado."**

**Acciones** bajó de "2 urgentes" a **"1 urgentes"**. Al abrirlo ahora solo queda:
> "2 comisiones pendientes por depositar" — Urgente — Ir a resolver

El aviso "1 pedidos pendientes de pago" (el de Guadalupe) ya no aparece — confirma que era justo ese pedido. No investigué ni toqué el tema de comisiones porque no me lo pidieron hoy.

## 10:35 — Nota en la ficha de Guadalupe Ramírez Torres
Fui a Clientes, busqué su fila (16 clientes en total, ella con "Última compra: 12/11/2026 · 0 días", Estatus "Inactiva") y abrí "Ver". Su ficha confirma: **correo guadalupe.r@gmail.com, "Sin teléfono registrado"**.

En "Bitácora de contactos" ya había dos notas previas:
- 12/11/2026 (Sofía): sobre acceso al panel y un pedido anterior reservado en Tienda Del Valle.
- 14/12/2026 (Ivonne): *"Correo (sin teléfono en ficha, no se pudo WhatsApp): le escribí para recordarle su pedido ORD-531EF896 ($560) que quedó pendiente de pago desde el 13/12... Pendiente: pedirle su celular para poder marcarle."* — o sea, ya había un intento previo de contacto documentado, y ya se sabía que no había teléfono.

Agregué la nota pedida en el campo "Nueva nota" → "Agregar nota":
> "18/12: pedido de sucursal cancelado por no recoger; sin teléfono en ficha"

Quedó guardada con mi usuario y hora: "· 1788339615521 · 18/12/2026 10:32".

## Lo que me confundió
- El botón "Ver" del detalle de pedido no es único en la página cuando hay elementos de navegación con el mismo texto; con selector genérico por texto falla por *strict mode*, hay que apuntar directo al botón dentro de la fila.
- El campo de correo del login es `type="text"`, no `type="email"`.
- El modal de reembolso "sugiere" el cobro completo ($381) sin distinguir envío/producto ni el motivo de la devolución (arrepentimiento) — tuve que saber de memoria que el envío no se reembolsa en estos casos y corregir el número a mano.
- Después de confirmar el reembolso, el detalle del pedido no vuelve a mostrar el monto que quedó registrado (solo el Total original del pedido) ni el motivo que escribí ni el comprobante subido — no tengo cómo verificar desde pantalla que se guardó $252 y no $381.
- El botón "Cancelar pedido" en Pendientes usa un `confirm()` nativo del navegador sin campo de motivo y sin avisar que el pedido no se había pagado; el "motivo claro" que pedían tuve que dejarlo yo aparte, en Notas internas del pedido, porque la cancelación en sí solo guarda el código genérico "admin_request".

## Lo que no pude hacer
- No pude verificar en pantalla el monto exacto que quedó registrado como reembolso ($252) porque esa vista no lo muestra en ningún lugar tras confirmar — solo infiero por el texto de éxito y el cambio de estado que el reembolso se procesó.
- No revisé el tema de "2 comisiones pendientes por depositar" (Urgente) que sigue en Acciones urgentes — no era parte de las tareas de hoy, lo dejo anotado por si alguien más lo necesita.

## Lo que preguntaría (mensaje 📱 a Sistemas)
No usé mi mensaje del día — no hizo falta, la información que necesitaba estaba en pantalla (Beto ya había dejado documentado el checklist de recepción, y las fichas de cliente ya traían contexto). Si tuviera que preguntar algo, sería: ¿el modal de reembolso puede calcular el "Sugerido" restando el envío cuando el motivo de la devolución es arrepentimiento, en vez de proponer siempre el total cobrado? Y ¿el botón "Cancelar pedido" de Pendientes podría pedir un motivo en un campo de texto (como ya hace el de rechazo de devolución), en vez de un simple confirm() del navegador?
