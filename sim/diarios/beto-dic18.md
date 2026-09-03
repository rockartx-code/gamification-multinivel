# Diario de Beto Salinas — 18 de diciembre de 2026

## 10:00 — Entrada
Inicié sesión en `beto@findingu.mx` sin problema (`Ingresar al panel`). El dashboard muestra "2 urgentes" en Acciones, y en Pedidos la pestaña "Por devolver" trae 1 pedido.

## 10:05 — Recibir paquete de Patricia Solís Ek (ORD-C7345274)
Fui a Pedidos → Por devolver. Ahí estaba el pedido de Patricia, $381, guía EST-MX-88120051, Bodega Central, con el botón "Recibir paquete". Le di clic y se abrió el formulario nuevo con el checklist que dijo Sofía:

Texto del formulario: *"Revisa el paquete y marca lo que veas. Con todo en orden la devolución queda validada; si algo falla, queda rechazada y se le avisa al cliente."*

Checklist (y lo que marqué según lo que traía el paquete):
- Lo recibido coincide con el pedido — MARCADA (es el Naplus del pedido)
- Trae folio o guía identificable — MARCADA (folio RET-9A996299 escrito en la caja)
- Empaque original — MARCADA (caja/bote original)
- Sello de seguridad intacto — MARCADA (sello intacto)
- Sin señales de uso — MARCADA (cerrado, sin consumo)
- El daño lo causó el cliente o la paquetería — SIN MARCAR (no hay ningún daño que reportar; el texto dice "márcalo solo si el daño no es de fábrica ni de nuestro empaque", y aquí no hay daño de ningún tipo)

Las casillas ya venían así por default al abrir el formulario (5 marcadas, la de daño sin marcar), coincidiendo exactamente con lo que yo hubiera marcado viendo el paquete real. No tuve que cambiar nada de los checkboxes.

En "Cómo llegó el paquete (notas)" escribí: *"Caja cerrada, sello intacto, empaque original. Folio RET-9A996299 escrito a mano en la caja. Cliente devuelve por arrepentimiento, no hay daño ni señales de uso."*

Antes de confirmar, la página ya mostraba: **"Resultado: devolución validada (procede el reembolso)"**.

Subí una foto (generé un PNG chiquito con Node, `paquete-patricia.png`, 68 bytes, 2x2 px). El formulario confirmó "1 imagen(es) adjunta(s)".

Le di clic a "Confirmar recepción". El sistema respondió con el texto: **"Paquete recibido. Devolución validada."**

Fui a la pestaña "Devuelto" para verificar: el pedido ORD-C7345274 ahora aparece con Estado **"Devuelta"**, y salieron dos acciones nuevas: "Reembolsar" y "Rechazar". No toqué ninguna de esas dos porque no me tocan a mí — soy almacén, no manejo el reembolso. Lo dejo anotado por si Sofía quiere que alguien más lo tome.

También noté que en la pestaña "SIGUIENTE" del panel apareció una tarjeta nueva: "Resolver devoluciones validadas · 1" — supongo que es justo este pedido esperando que alguien decida el reembolso.

## 10:20 — Entrada de Magnesio Glicinato 120 caps (30 pzas, Bodega Central)
Fui a Stocks. Por default el "Stock activo" estaba en Tienda Del Valle. Cambié el selector a "Bodega Central · Av. Insurgentes Sur 1234, Col. Del Valle, CDMX" y ahí en la tabla de Inventario por producto vi:

`Magnesio Glicinato 120 caps — Existencia: 0`

Le di clic a "Entrada" de esa fila. Se abrió el modal "Registrar entrada de inventario" (nota: dice "Solo permite agregar unidades al stock seleccionado"). Ya venía preseleccionado Stock = Bodega Central y Producto = Magnesio Glicinato 120 caps · $520 (correcto), pero "Registrado por" traía a Nadia Ruiz por default — lo cambié a **Beto Salinas · beto@findingu.mx**, que soy yo quien lo está registrando.

Puse Cantidad = **30**, y en la nota escribí: "Entrada de proveedor. Llegaron 30 piezas a Bodega Central, sin registrar hasta hoy."

Le di clic en "Registrar entrada". El sistema mostró: **"Entrada de inventario registrada."**

Verifiqué en la tabla de inventario: **Magnesio Glicinato 120 caps — Existencia: 30**.

También apareció en la Bitácora de entradas/salidas: `18/12/2026 10:10 · Bodega Central · Magnesio Glicinato 120 caps · Entrada · +30 · manual · Beto Salinas`. El campo Motivo/Ref solo dice "manual" (igual que otras entradas manuales previas de otros compañeros); no muestra el texto completo de mi nota en esa columna, aunque sí lo escribí en el formulario. No sé si la nota se guarda en otro lado que no vi en la lista.

## 10:30 — Revisión de "Enviado" en Pedidos
Fui a Pedidos → Enviado. Aparecen **4 pedidos**, todos con Estado "Enviada":
- ORD-E056804D — Verónica Sandoval Ruiz — creado 13/11/2026 — guía EST-MX-88120047
- ORD-30280A83 — Verónica Sandoval Ruiz — creado 02/10/2026 — guía EST-MX-88120044
- ORD-9BADDCB6 — Verónica Sandoval Ruiz — creado 02/10/2026 — guía EST-MX-88120045
- ORD-0CF9F0B2 — Rosa Elena Mendoza — creado 02/10/2026 — guía EST-MX-88120046

Ninguno de estos 4 tiene fecha de creación en diciembre — son de octubre y noviembre. Así que, tal como se esperaba, **no hay nada de diciembre atorado en "Enviado"** (Estafeta ya entregó todo el 16, según me dijo Sofía).

Lo que sí me llamó la atención: estos 4 pedidos llevan meses en "Enviada" sin marcarse como entregados, con guías de números más bajos (EST-MX-88120044 a 47) que la de Patricia (EST-MX-88120051, ya entregada y en devolución). Es raro que sigan ahí de octubre/noviembre. No lo toqué porque no es parte de lo que me pidió Sofía (que era específicamente diciembre), pero lo dejo anotado.

## Lo que me confundió
- El botón "Enviado" del listado de pedidos tiene el mismo texto que otros elementos de la página (el resumen "Enviados: 4"); mi primer clic por texto exacto agarró el elemento equivocado y no filtró la lista. Tuve que ser más específico con el botón de la pestaña.
- El campo de nota al registrar la entrada de stock no se refleja completo en la columna "Motivo/Ref" de la bitácora — solo dice "manual". No sé si se guarda en otro lugar.
- Los 4 pedidos "Enviada" de octubre/noviembre que nunca se marcaron como entregados — no sé si es algo pendiente de alguien más o un dato viejo que ya no importa.

## Lo que no pude hacer
- No decidí el reembolso del pedido de Patricia (ORD-C7345274) — quedó en "Devuelta" con acciones "Reembolsar"/"Rechazar" disponibles, pero eso no me toca a mí como almacén.
- No encontré una función real para mandar un mensaje 📱 a Sofía dentro de las herramientas que tengo (el arnés `persona.mjs` no trae ninguna función de mensajería, solo navegador y buzón de correo). No inventé un mensaje que no pude mandar de verdad; en su lugar dejo las dudas anotadas abajo.

## Lo que preguntaría (si pudiera mandarle el mensaje a Sofía)
1. Los 4 pedidos "Enviada" de octubre/noviembre (ORD-E056804D, ORD-30280A83, ORD-9BADDCB6, ORD-0CF9F0B2) que nunca se marcaron como entregados — ¿los dejo así o alguien tiene que revisarlos?
2. El pedido de Patricia (ORD-C7345274) quedó "Devuelta" con "Reembolsar"/"Rechazar" disponibles — ¿eso lo resuelve alguien de finanzas o me toca a mí también?
