# Diario de Patricia Solís Ek — 16 de diciembre de 2026

## 11:00 (hora del celular) — Entro a la tienda

Entré a `http://localhost:4321/#/tienda` desde el celular. No tenía sesión guardada, así que le di clic a "Entrar" y metí mi correo `patricia.solis@yahoo.com` y mi contraseña. Me mandó directo al panel (`#/dashboard`).

Lo primero que vi arriba: "Objetivo principal del mes: Agregar un nuevo miembro a la red este mes" y "Invita a 1 persona y actívala — Te faltan 1 para lograrlo". Ya me puse nerviosa pensando en mi devolución, pero seguí bajando.

## Busco mi pedido

En la sección "Órdenes" del panel vi los cuatro pedidos:
- **ORD-C7345274** — Entregada — Fecha: 2026-12-12T12:18:43Z — Total: $381
- ORD-E3335EC5 — Entregada — Fecha: 2026-12-12T11:46:47Z — Total: $409
- ORD-016AAED1 — Entregada — Fecha: 2026-12-12T11:37:56Z — Total: $829
- ORD-5B31500B — Entregada — Fecha: 2026-09-06T10:42:13Z — Total: $829 (esta es vieja, de septiembre, no la toqué)

También vi mis números: **VP (Volumen Personal) 24.4** y **VG (Volumen de Grupo) 24.4**. "RANGO ACTUAL: Sin rango aún — Cada compra te acerca al primero". Los anoto porque quiero comparar después de la devolución.

Le di clic a "Ver orden" del primer pedido de la lista (era el ORD-C7345274, lo confirmé en la pantalla de detalle) y entré a `#/orden/ORD-C7345274`.

## El detalle del pedido

Vi: "Pedido entregado", Subtotal $280, Descuento -$28 (10%), Envío (Estafeta) $129, Total $381. Abajo había un botón "Solicitar devolución". Le di clic.

## El formulario de devolución (paso 1 de 3)

Me preguntó "¿Cuál es el motivo de la devolución?" con tres opciones:
1. **Producto dañado o defectuoso** — "El producto llegó roto, dañado o no funciona."
2. **Error en el envío** — "Recibiste un producto diferente al pedido."
3. **Desistimiento (arrepentimiento)** — "Decidiste no quedarte con el producto."

Elegí la tercera, que es mi caso (ya no lo quiero, fue un impulso). En cuanto la elegí apareció un aviso: **"Aplica dentro de los 7 días posteriores a la entrega. El costo de envío de la devolución corre a tu cargo."** Ahí ya me quedó claro que el envío de vuelta lo pago yo. Escribí en la descripción: "Fue una compra por impulso, ya no lo quiero. El producto está cerrado, sin abrir." Y le di "Siguiente".

## Paso 2: las fotos — esto sí me sorprendió

Me pidió: **"Se requieren los tres tipos de fotos para continuar. Acepta JPG, PNG o PDF."**
- Fotos del producto *
- Fotos del empaque *
- Fotos de la guía de envío *

Me extrañó que pidiera fotos aunque elegí "arrepentimiento" y el paquete nunca se abrió — pensé que solo pedirían fotos si el producto llegó dañado. Pero no, las tres son obligatorias sin importar el motivo. No tengo cámara aquí a la mano en este ejercicio, así que usé unas fotos de prueba (un PNG chiquito hecho con Node) para las tres casillas: `foto-producto.png`, `foto-empaque.png`, `foto-guia.png`. Las subí una por una y la pantalla mostró los tres nombres de archivo cargados.

## Paso 3: confirmar

Me mostró el resumen:
- Motivo: Desistimiento (arrepentimiento)
- Evidencia: 3 archivo(s)
- **Costo de envío devolución: A cargo del cliente**

No vi ninguna dirección de devolución en esta pantalla, solo hasta el correo (ver abajo). Le di "Enviar solicitud".

## Confirmación en pantalla

Me salió: **"Solicitud de devolución registrada. Te notificaremos el resultado de la inspección. El costo de envío de la devolución corre a tu cargo."**
**ID de solicitud: RET-9A996299**
**Costo de envío de devolución: A cargo del cliente**

## Reviso mi correo

Encontré el correo "Recibimos tu solicitud de devolución · RET-9A996299" (2026-12-16T10:06:44Z) que dice, textual:

> "Hola Patricia Solís Ek. Folio RET-9A996299. Envía el producto que reportaste, en su empaque, a Bodega Central, Av. Insurgentes Sur 1234, Col. Del Valle, CDMX con el folio escrito en el paquete, y guarda tu ticket de envío: te lo reembolsamos junto con el producto una vez que lo revisemos (1 a 3 días hábiles tras recibirlo)."

Esto me dejó un poco confundida: en la pantalla decía clarísimo que el envío de regreso "corre a mi cargo", pero el correo dice "guarda tu ticket de envío: te lo reembolsamos junto con el producto una vez que lo revisemos". ¿Entonces sí me lo reembolsan o no? No sé si "te lo reembolsamos" se refiere al ticket de envío (el costo) o nada más al producto. No lo tengo claro.

También encontré el correo anterior "Tu pedido ORD-C7345274 fue entregado" (2026-12-16T10:00:00Z) que decía: "Si algo llegó dañado tienes 48 horas para pedir la devolución desde tu seguimiento; si simplemente te arrepentiste, 7 días." — esto confirma que sí estoy dentro de plazo (pedido entregado hoy mismo, 16 de diciembre).

## Reviso el estado del pedido y mi panel después

Volví a `#/orden/ORD-C7345274` y ahora el estatus cambió: **"En devolución"** y en el progreso apareció **"Devolución en proceso de inspección"**.

Fui al panel (`#/dashboard`) otra vez y en "Volumen & Rangos" seguía viendo: **VP 24.4, VG 24.4**. O sea que todavía NO me bajaron los VP del pedido — supongo que es porque la devolución sigue "en proceso de inspección" y todavía no me han hecho válida la devolución. No vi ningún aviso en pantalla que dijera explícitamente "tus VP bajarán cuando..." — eso lo estoy suponiendo, no lo leí en ningún texto.

## Busco cómo mandar un mensaje a Soporte

Quería preguntar por la contradicción del envío (pantalla dice "a mi cargo", correo dice "te lo reembolsamos"). Revisé el menú de navegación (Tienda, Red, Links, Órdenes, Comisiones, Cuadro de Honor, Mi perfil) y la página de "Mi perfil" completa. **No encontré ningún botón ni ícono de "Mensaje a Soporte" ni chat de soporte en ninguna pantalla.** Lo único parecido que hay es un enlace de WhatsApp, pero es hacia mi patrocinadora Verónica Sandoval Ruiz (mi contacto de red), con un mensaje prellenado de "Hola, necesito ayuda con mi red de FindingU" — es decir, es para dudas de red/patrocinio, no un canal de soporte de pedidos. No lo usé porque no aplica a mi duda y es un enlace que abre una app externa (whatsapp://) que no puedo completar desde aquí.

## Lo que no pude hacer
- No pude mandar un mensaje real a Soporte porque no encontré esa función en la app; solo hay un link de WhatsApp a mi patrocinadora, para temas de red, no de pedidos/devoluciones.
- No pude tomar fotos reales del producto/empaque/guía (usé PNGs de prueba hechos con Node, como indicaba el ejercicio).
- No pude confirmar si al final sí me reembolsan el envío de vuelta o no — la pantalla y el correo dicen cosas distintas.
- No pude ver una fecha exacta de cuándo bajarán mis VP ni un texto que lo explique.

## Lo que preguntaría (si hubiera Soporte)
- "En la pantalla de la devolución dice que el envío de regreso corre por mi cuenta, pero el correo dice que me reembolsan el ticket de envío junto con el producto. ¿Al final sí me devuelven ese costo o no?"
- "¿Cuándo se van a reflejar los cambios en mi VP de este mes por esta devolución, ahora que quedó 'en proceso de inspección'?"
- "¿Por qué piden fotos del producto y del empaque si elegí arrepentimiento y el paquete nunca se abrió?"
