# Diario de Nadia Ruiz — Tienda Del Valle, 12 de enero de 2027

> Igual que le pasó a Beto y a Sofía: hoy es 12 de enero pero el sistema fecha todo "13 ene 2027". Lo anoto con la hora que me muestra la pantalla.

## 10:31 — Entrada
Abrí el navegador de la caja y en vez del panel me apareció **la tienda de socios**: "Nadia Ruiz · Tienda · Red · Links · Órdenes · Cuadro de Honor · Mi perfil · Progreso mensual", con carrito, "Agrega tus básicos", un "Magnesio Glicinato 120 caps — Producto recomendado para avanzar en tus metas" con textos "10g por porci?n" / "Alta absorci?n" (así, con signos de interrogación) y abajo "Tu Red — Nadia R. | $0 — Compartir mi enlace — Nivel 1". Yo soy cajera, no tengo red ni metas. Me fui por costumbre a `#/login`, puse mi correo y contraseña, "Ingresar al panel", y ahí sí: `#/admin`, "Nadia Ruiz — ADMIN", menú Pedidos / Punto de Venta / Stocks / Campañas.

Arriba el botón "Acciones — 2 urgentes" dice: "2 socias con comisión y sin CLABE · $294.20 — Urgente — Ir a resolver" y "1 pedidos pagados sin envío — Importante". Yo no puedo hacer nada con eso; no es mío. (Y dice "Resolvé pendientes críticos", como argentino.)

Capturas: `nadia-ene12-01-inicio.png`, `02-login`, `03-tras-login`, `04-acciones`.

## 10:32 — Punto de Venta, antes de vender
"Ventas en caja 3 · Caja actual $500 · Stock actual Tienda Del Valle · Operador Nadia Ruiz". Abajo, "Control de caja actual": "Efectivo que debería haber en el cajón $500.00 — Fondo inicial $500.00 — Ventas en efectivo $0.00 — Tarjeta y transferencia $340.00 (no entran al cajón)". "Inicio de caja: 13 dic 2026, 11:31 a.m." — o sea la caja lleva abierta un mes; nadie me pidió abrir caja hoy ni contar el fondo al empezar.

Botones deshabilitados y su motivo, tal cual los vi:
- "Aplicar descuento" (gris) → debajo: **"Elige al menos un producto para aplicar un descuento."** ✔
- "Cobrar $0" (gris) → debajo: **"Elige al menos un producto."** ✔
- "Hacer corte de caja" hoy sí estaba activo (en noviembre estaba gris sin explicación).

En "Ventas registradas → Tarjeta" siguen apareciendo tres ventas: POS-D7F97B91 Roberto $340 (13 dic), POS-785DCAA4 Beatriz $480 (15 nov) y POS-6947D029 Roberto $840 (15 nov). Las de noviembre ya pasaron por tres cortes y siguen ahí.

Capturas: `05-pos`, `06-pos-medio`, `07-pos-abajo`.

## 10:33 — Venta de mostrador (Público en General)
Cliente de paso, sin cuenta. Dejé "Publico en General" ("Venta mostrador sin metas ni descuentos acumulados"). Un clic en **Boom** ($420, Disp. 6 · 8 PC) y uno en **Naplus** ($280, Disp. 6 · 6 PC); a cada uno le salió "Cantidad — Maximo disponible: 6", dejé 1 y 1. Subtotal $700, Total neto $700. Con productos elegidos, "Aplicar descuento" cambió a "Requiere el código de autorización de la gerente." (sigue sin servirme, pero al menos dice por qué).

Forma de pago Efectivo (ahora también existe "Efectivo + tarjeta/transferencia", lo que Bety pedía en noviembre). En "Efectivo recibido" escribí 1000 y en automático: **"Cambio: $300 — Sobre un total de $700"**. Botón "Cobrar $700".

Al cobrar: **"Venta POS-C7ACD530 registrada por $700. Pago: efectivo. Cambio a entregar: $300."** y una tarjeta "ÚLTIMA VENTA GUARDADA — POS-C7ACD530 — Total $700 — efectivo — Efectivo $700 — Cambio $300". Le di sus $300 al señor. Caja actual pasó a $1,200; Boom y Naplus bajaron a Disp. 5.

Cosas raras después de cobrar:
- Arriba el contador dice "Ventas en caja **4**", pero "Control de caja" dice "Ventas registradas **2**" y "Ver movimientos (2)". Tres números para lo mismo.
- Debajo de "Publico en General" apareció sola una lista de clientes sin que yo escribiera nada: "Diana Robles Castillo, **Nadia Prueba**, **Prueba Reenvio**, Roberto Chávez Mena, Rosa Elena Mendoza, Guadalupe Ochoa Lara, Guillermo Ibarra Ponce, Guadalupe Ramírez Torres". ¿"Nadia Prueba" y "Prueba Reenvio" son clientes? Se ven en la caja.
- "Acciones" subió a "3 urgentes": el nuevo es "1 ventas POS registradas hoy — Informativo — Ir a resolver". No hay nada que resolver en una venta que yo misma acabo de hacer.

Capturas: `08-dos-productos`, `09-efectivo-1000`, `10-tras-cobrar`, `11-acciones-3`, `12-movimientos`.

## 10:35 — La tabla de descuento del POS
Para verla tuve que seleccionar a un socio: Roberto Chávez Mena. Su ficha: "Descuento actual: 0% — Meta proyectada: 0%" y luego "Metas y descuento aplicable — Descuento del cliente este mes":

| Compra del mes | Descuento |
|---|---|
| hasta $999 | 0 % (está aquí) |
| de $1,000 a $1,999 | 10 % |
| de $2,000 a $2,999 | 20 % |
| de $3,000 a $5,999 | 30 % |
| desde $6,000 | 40 % |

"El cliente está en el tramo: 0 % (hasta $999). Siguiente tramo: 10 %, le faltan $1,000. Activación: 20 VP netos · lleva 0. Le faltan 20 VP para activar el mes. Los VP se cuentan sobre el precio ya con descuento: 20 PC con 10 % = 18 VP. Consumo del mes según el servidor $0 · 0 VP".

Luego quise comparar con lo que ve un socio en su panel. Yo no tengo panel de socio: en la tienda que me abre `/#/`, "Progreso mensual" es solo un texto (no se puede picar) y "Mi perfil" me regresó al panel de admin. En "Ver carrito" (`#/carrito`) el resumen dice "Nivel de descuento: Inactivo — Descuento aplicado: Sin descuento — Meta principal de consumo: Meta de beneficios — **Te faltan $0 para Meta de beneficios**" — sin ninguna tabla de tramos, y eso de "te faltan $0" pero "Inactivo" no lo entiendo. No pude ver el panel de un socio de verdad.

📱 A Sistemas: En el POS la tabla de descuento por compra del mes es 0% hasta $999, 10% de $1,000, 20% de $2,000, 30% de $3,000 y 40% desde $6,000. ¿Es la misma que ve un socio en su panel? No tengo forma de abrir el panel de un socio desde mi usuario (en `/#/` me sale una tienda con "Red" y "Links" a mi nombre, y "Mi perfil" me regresa al admin). ¿Me pasan una captura del panel de Roberto o de cualquier socio?

Capturas: `13-lista-clientes`, `14-roberto-tabla`, `14b-roberto-tabla-scroll`, `25-socio-menu`, `28-socio-carrito`.

## 10:36 — Corte del día
Conté el cajón: $1,250. El sistema decía $1,200. Sobran $50 y no sé de dónde salieron.

"Hacer corte de caja" abre un asistente **"Corte de caja · paso 1 de 4"**:

**Paso 1** — "Esto es lo que debería haber en el cajón según las ventas y retiros del turno": Fondo que dejó el corte anterior $500.00 · Ventas en efectivo $700.00 · Abonos en efectivo $0.00 · Parte en efectivo de pagos mixtos $0.00 · Retiros del turno -$0.00 · **Efectivo esperado $1,200.00** · "2 venta(s) en el turno · tarjeta y transferencia $340.00 (no entran al cajón)". "Atrás" gris sin texto (obvio, es el primer paso). Botón "Siguiente: contar el efectivo".

**Paso 2** — "Cuenta el efectivo del cajón y escribe cuánto hay. Si no cuadra, explica por qué." Dos modos: "Escribir el total contado — Ya lo sumaste tú" o "Contar por billetes y monedas — Escribe cuántos hay de cada uno y el sistema suma" (con casillas $1000, $500, $200, $100, $50, $20, $10, $5, $2, $1). "Siguiente: destino del efectivo" gris con el motivo **"Escribe cuánto efectivo contaste (puede ser $0)."** ✔. Escribí 1250: **"Efectivo contado $1,250.00 — Efectivo esperado $1,200.00 — Diferencia $50.00 (sobra)"**. "Motivo de la diferencia (obligatorio) — Queda escrito en el comprobante para que la gerente lo vea. No es una falta: es lo que pasó." Escribí: "Aparecieron $50 de más en el cajón; no sé de dónde salieron." Ese "No es una falta" se agradece.

**Paso 3** — "Decide cuánto se queda como fondo para mañana y cuánto se retira. Contaste $1,250.00. ¿A dónde va?" Opciones: "Dejar todo como fondo de mañana — Los $1,250.00 se quedan en el cajón. No hace falta código" o "Retirar una parte (o todo) — Se anota quién se lo lleva y se pide el código de la gerente". Probé "Retirar": "Fondo que se queda en caja" arranca en **0** y por eso "Se retira $1,250.00" (todo, incluido el fondo — si una va rápido se lleva hasta el fondo). Pide "Quién recibe el efectivo" y "Código de autorización — **Lo tiene la gerencia (Configuración → Código de autorización POS); pídeselo a tu gerente.**" "Siguiente: revisar" gris con motivo "Escribe quién recibe el efectivo retirado." ✔. Como no tengo el código de hoy y Sofía no está, regresé a "Dejar todo como fondo de mañana".

**Paso 4** — "Revisa lo que va a pasar antes de cerrar. Después del corte ya no se puede editar. Se cerrará el corte con 2 ventas por $1,040.00. Fondo para mañana: $1,250.00. No se retira efectivo. La diferencia de $50.00 queda registrada con motivo: ..." Botón "Cerrar el corte".

**Resultado**: **"Corte cerrado · CUT-5DB5A173 — Guardado en el servidor 13 ene 2027, 10:38 a.m."** — "Tienda Del Valle · Nadia Ruiz · 2 venta(s) · de 13 dic 2026, 11:31 a.m. a 13 ene 2027, 10:38 a.m." Fondo inicial $500 · Ventas en efectivo $700 · Efectivo esperado $1,200 · Efectivo contado $1,250 · Diferencia $50.00 · Motivo · "Se deja como fondo de mañana $1,250.00 · Se retira $0.00 · Tarjeta y transferencia (no entran a caja) $340.00". Abajo: "Enviar el comprobante a la gerente — Correo de la gerente — **No hay un correo configurado para los cortes; escribe uno o pide a la gerente que lo capture en Configuración.**" Botones Imprimir / Enviar por correo a la gerente / Listo. No mandé nada: no sé si Sofía quiere que le llegue a su correo personal y no lo tengo a la mano.

Tras el corte: "Ventas en caja 2 · Caja actual $1,250 · Inicio de caja 13 ene 2027, 10:38 a.m. · Ultimo corte 13 ene 2027, 10:38 a.m. · Monto: $700 · Ventas: 2 · En caja: $1,250 · Retirado: $0". "Hacer corte de caja" ahora dice "**No hay ventas ni retiros desde el último corte: no hay nada que cortar todavía.**" ✔. En "Ver historial de cortes": CUT-5DB5A173 "Total: $700 · Ventas: 2 · En caja: $1,250 · Retirado: $0 · CSV" (el paso 4 dijo "2 ventas por $1,040" y el historial dice "Total $700": ¿cuál es el total del corte?). Y las dos ventas con tarjeta de noviembre siguen en "Ventas registradas → Tarjeta 2 venta(s)" después de cuatro cortes.

Capturas: `15-corte-modal`, `16-corte-p1a`…`p4a`, `19-corte-billetes`, `20-corte-retirar`, `21-corte-revisar`, `22-corte-comprobante`, `22b-…-abajo`, `23-pos-tras-corte`, `27-historial-cortes`.

## Cómo me sentí
Mejor que en noviembre: esta vez casi cada botón gris me dijo qué le faltaba y el corte me llevó de la mano (contar, motivo, destino, revisar). Lo del "No es una falta: es lo que pasó" me quitó el nervio de escribir que sobraban $50. Lo que me sigue dejando con cara de "¿y ahora?" es el efectivo físico: el sistema me dice cuánto debería haber y me deja dejarlo todo de fondo, pero de los $50 extra no me dice nada (quedaron dentro del fondo de mañana como si fueran de la empresa) y el retiro sigue dependiendo de un código que hoy no tengo. Y me da cosa que un cliente vea, si se asoma, "Nadia Prueba" y "Prueba Reenvio" en la lista, o que a mí me salgan comisiones y CLABEs de socias en "urgentes".

## Lo que reportaría a Sistemas
1. La fecha del sistema va un día adelantada (12 → "13 ene 2027").
2. "Ventas en caja" (4) vs "Ventas registradas" (2) vs "Ver movimientos (2)" vs "2 venta(s) en el turno": números distintos para el mismo turno; tras el corte "Ventas en caja 2" con 0 ventas del turno.
3. Las ventas con tarjeta del 15 de noviembre (POS-785DCAA4, POS-6947D029) nunca entran a ningún corte y siguen listadas; en cambio el abono de $340 del 13 de diciembre sí entró al corte de hoy ("2 ventas por $1,040").
4. Historial: "Total: $700" para un corte que el paso 4 describió como "2 ventas por $1,040".
5. "Retirar una parte": el fondo arranca en $0 y propone retirar los $1,250 completos.
6. Los $50 sobrantes se registran con motivo pero se quedan dentro del "fondo de mañana"; no hay indicación de separarlos ni de a quién entregarlos.
7. No hay correo de la gerente configurado para el comprobante del corte.
8. La caja llevaba abierta desde el 13 de diciembre; nadie pide "abrir caja" ni contar el fondo al iniciar el día.
9. Lista de clientes con "Nadia Prueba" y "Prueba Reenvio", y aparece sola sin escribir nada.
10. "Acciones urgentes" me muestra CLABEs y comisiones de socias (no es mi trabajo) y "1 ventas POS registradas hoy — Ir a resolver" (nada que resolver).
11. Al entrar por `/#/` me abre la tienda de socios con "Red", "Links", "Compartir mi enlace" a mi nombre; "Mi perfil" regresa al admin; textos con "?" en el Magnesio.
12. No pude comprobar si la tabla de descuento del POS (0/10/20/30/40 %) es la misma del panel de un socio; en mi carrito dice "Nivel de descuento Inactivo · Te faltan $0 para Meta de beneficios", sin tabla.
