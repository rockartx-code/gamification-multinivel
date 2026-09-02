# Diario de Beto — Turno 6
**Fecha simulada:** 13 de noviembre de 2026 (reloj del sistema marcaba `2026-11-13T09:32:17Z` al entrar)

## 09:30 — Entrando
Abrí el perfil `beto` y fui a `#/login`. No tenía sesión guardada de antes (me salió el formulario de correo/contraseña), así que entré con `beto@findingu.mx` / `U4Z3GEUEGP`. Me mandó directo a `#/admin`, panel de "Beto Salinas · ADMIN". Arriba a la derecha decía "Acciones · 2 urgentes" — no lo revisé porque Sofía no me pidió eso, aunque me quedó la curiosidad.

La pantalla de Pedidos ya mostraba justo lo que decía el WhatsApp de Sofía: **Pagados: 6**, **Pendientes envío: 6**. Entré a la pestaña "Pagado 6" y ahí estaban los 6 folios exactos que ella mandó, con el mismo cliente y las mismas fechas (3 del 12/11 y 3 del 02/10). Coincidieron uno a uno, sin sorpresas.

## Revisando existencia antes de sacar cada pedido
Antes de tocar nada fui a **Stocks**. La primera vez se me pasó que el desplegable "Stock activo" trae "Tienda Del Valle" seleccionado si no eliges nada, y casi anoto mal el inventario (ahí Naplus tenía 10 y Klinhart 5 — es la tienda, no la bodega). Cuando seleccioné explícitamente "Bodega Central · Av. Insurgentes Sur 1234" salió el inventario real:

| Producto | Existencia antes |
|---|---|
| Gel Reductivo | 40 |
| Creatina Monohidratada | 40 |
| Colageno Hidrolizado | 29 |
| CRT-1200 | 40 |
| Keto Elektrolyte Fusion | 40 |
| Biotina | 40 |
| BHB Acido | 40 |
| Glu-10 | 40 |
| Naplus | 25 |
| Boom | 38 |
| Longevit | 48 |
| Klinhart | 33 |
| Finding Pro 500g | 39 |

Fui a "Ver" cada uno de los 6 pedidos para anotar qué productos llevaban, y los comparé contra esta tabla: todo sobraba por mucho, ningún producto estaba en riesgo. Anoté qué llevaba cada uno:
- ORD-B4D33503: Colageno Hidrolizado x1, Naplus x3
- ORD-9074F79E: Creatina Monohidratada x1, Colageno Hidrolizado x1, Finding Pro 500g x1
- ORD-D138835A: Colageno Hidrolizado x1, Naplus x3
- ORD-30280A83: Naplus x1
- ORD-9BADDCB6: Colageno Hidrolizado x1, Boom x1
- ORD-0CF9F0B2: Colageno Hidrolizado x1

## Registrando los envíos
El botón dice "Registrar envío" y abre un modal "Enviar pedido". Ahí solo hay dos campos: "Stock origen" (elegí Bodega Central en los 6, como pidió Sofía) y un solo campo de texto llamado "Numero de guia" (placeholder "Guia de paqueteria"). **No hay campo separado para el nombre de la paquetería** — solo ese cuadro de texto. Como Sofía insistió en que fuera "con paquetería Estafeta", escribí en ese único campo `Estafeta EST-MX-88120041` (y así con cada guía) para que quedara registrada la paquetería junto con el número. No sé si hay otra forma de indicar "Estafeta" aparte de meterlo en ese texto; si hay un lugar dedicado para el nombre de paquetería no lo vi en pantalla.

Los 6 quedaron enviados. Cada vez que le di "Marcar como enviado" salió un mensaje verde "Envio registrado." y el pedido desapareció de "Pagado" y apareció en "Enviado". Al final entré a la pestaña "Enviado" y los 6 estaban ahí con su guía exacta:

- ORD-B4D33503 → "Guia: Estafeta EST-MX-88120041 · Bodega Central" — Estado: **Enviada**
- ORD-9074F79E → "Guia: Estafeta EST-MX-88120042 · Bodega Central" — Estado: **Enviada**
- ORD-D138835A → "Guia: Estafeta EST-MX-88120043 · Bodega Central" — Estado: **Enviada**
- ORD-30280A83 → "Guia: Estafeta EST-MX-88120044 · Bodega Central" — Estado: **Enviada**
- ORD-9BADDCB6 → "Guia: Estafeta EST-MX-88120045 · Bodega Central" — Estado: **Enviada**
- ORD-0CF9F0B2 → "Guia: Estafeta EST-MX-88120046 · Bodega Central" — Estado: **Enviada**

También abrí el detalle de ORD-D138835A para confirmar y ahí dentro, en la sección "Envío", quedó escrito: "Guía: Estafeta EST-MX-88120043 / Stock origen: Bodega Central" — así que sí se guarda bien.

## Cosa rara que me confundió
Mientras trabajaba, entre un script y otro (o sea, entre que recargaba la pantalla), noté que los contadores generales cambiaban solos sin que yo tocara nada: al principio había "1 pendiente" (ORD-4852F102, Guadalupe Ramírez Torres, pago en sucursal) y "Entregados: 8". En algún momento, sin que yo hiciera clic en nada de eso, pasó a "0 pendientes" y "Entregados: 9". Cuando después revisé la pestaña "Entregado" completa, ese mismo folio (ORD-4852F102) ya aparecía como "Entregada" con "Tienda Del Valle" y "Sucursal / Paga aquí" — o sea, se pagó y se entregó solo, como si otro empleado o el propio cliente lo hubiera resuelto en la sucursal mientras yo estaba en otra pantalla. No hice nada para causar eso, solo lo vi cambiar entre una lectura y otra.

## Sobre lo de Estafeta y los envíos de octubre ya entregados
Sofía dijo que revisara si había algo en "Enviado" pendiente de marcar como entregado. Fui a esa pestaña **antes** de registrar los 6 envíos nuevos y decía literal: **"No hay pedidos en este estado. Los contadores de las pestañas muestran dónde hay trabajo."** — 0 pedidos. O sea que no encontré nada pendiente de marcar como entregado en ese momento.

Después, ya con los 6 nuevos enviados, revisé la pestaña "Entregado" completa (9 pedidos) para ver si ahí estaban los envíos viejos de octubre que Estafeta dice que entregó. Encontré estos dos con guía de Estafeta y fecha de octubre, y ya decían "Entregada":
- ORD-4ED2C269 (Beatriz Ochoa Lara, 03/10/2026) — "Guia: EST-MX-88120099 · Bodega Central" — Entregada
- ORD-DC1D5D6F (Claudia Ibarra Soto, 03/10/2026) — "Guia: EST-MX-88120077 · Bodega Central" — Entregada

Como ya estaban en "Entregada" y no en "Enviado", no tuve nada que marcar manualmente — la pantalla no me dio ningún botón de "Marcar como entregado" para ellos porque ya no estaban en ese estado. No sé si alguien más los marcó antes que yo entrara, o si ya venían así desde ayer. Lo que sí puedo asegurar es que **el filtro "Enviado" estaba vacío cuando yo lo revisé**, así que no dejé nada pendiente de marcar.

⚠️ Importante: los 6 pedidos que YO acabo de mandar hoy siguen en "Enviada", NO los marqué como entregados — eso no me lo pidió Sofía, ella solo pidió registrar el envío.

## Inventario final de Bodega Central
Después de sacar los 6 pedidos, volví a Stocks → Bodega Central y la bitácora mostraba las 8 salidas de hoy (13/11/2026, hora 09:44 a 09:49) con la leyenda "Despacho orden ORD-XXXX", una línea por producto. El inventario quedó así:

| Producto | Existencia antes | Existencia después |
|---|---|---|
| Gel Reductivo | 40 | 40 |
| Creatina Monohidratada | 40 | **39** |
| Colageno Hidrolizado | 29 | **24** |
| CRT-1200 | 40 | 40 |
| Keto Elektrolyte Fusion | 40 | 40 |
| Biotina | 40 | 40 |
| BHB Acido | 40 | 40 |
| Glu-10 | 40 | 40 |
| Naplus | 25 | **18** |
| Boom | 38 | **37** |
| Longevit | 48 | 48 |
| Klinhart | 33 | 33 |
| Finding Pro 500g | 39 | **38** |

**Ningún producto quedó por debajo de 5 unidades.** El más bajo es Naplus con 18, que sigue siendo cómodo.

## Lo que no pude hacer
- No pude confirmar si hay una forma "oficial" en pantalla de indicar el nombre de la paquetería (Estafeta) separado del número de guía — solo existe el campo "Numero de guia", así que metí ahí "Estafeta EST-MX-88120041" (y equivalentes). Si existe otro lugar para eso no lo encontré.
- No investigué qué eran las "2 urgentes" (luego "1 urgentes") en Acciones, porque no venía en el encargo de Sofía.
- No marqué nada como "Entregado" porque no había nada en la pestaña "Enviado" cuando revisé, y los 6 que yo mandé hoy deben seguir como "Enviados" según lo que pidió Sofía.

## Lo que preguntaría
1. Los dos envíos de octubre (ORD-4ED2C269 y ORD-DC1D5D6F) ya aparecían como "Entregada" cuando los busqué — ¿alguien más ya los había marcado, o el sistema los marca solo cuando Estafeta actualiza? Quiero confirmar que son justo esos dos a los que se refería el reporte de Estafeta.
2. ¿Debo anotar la paquetería en algún otro lugar además del campo de guía? No vi un campo específico para "paquetería" en el formulario de "Registrar envío".
3. Vi que el pedido ORD-4852F102 (Guadalupe Ramírez Torres) pasó solo de "Pendiente" a "Entregada" (pago y recogida en Tienda Del Valle) sin que yo tocara nada — ¿eso lo hizo otro compañero en el mostrador mientras yo trabajaba en Pedidos/Stocks? Solo lo vi cambiar entre una pantalla y otra.

📱 A Sofía: No mandé ningún mensaje — no me trabé en nada que no pudiera resolver viendo la pantalla; los 6 pedidos y el inventario quedaron según lo que pediste. Sí me quedaron las 3 dudas de arriba para cuando tengas un momento.

## Capturas guardadas
- `sim/capturas/beto-01-login.png` — pantalla de login
- `sim/capturas/beto-02-tras-login.png` — panel admin recién logueado
- `sim/capturas/beto-04-tab-pagado.png` — pestaña Pagado con los 6 pedidos
- `sim/capturas/beto-07-bodega-central.png` — inventario Bodega Central ANTES
- `sim/capturas/beto-09-orden1-detalle.png` — detalle productos ORD-B4D33503
- `sim/capturas/beto-11-orden1-form-lleno.png` / `beto-11-orden1-despues.png` — envío ORD-B4D33503
- `sim/capturas/beto-13-orden2-form.png` / `beto-13-orden2-despues.png` — envío ORD-9074F79E
- `sim/capturas/beto-14-orden3-form.png` / `beto-14-orden3-despues.png` — envío ORD-D138835A
- `sim/capturas/beto-15-orden4-form.png` / `beto-15-orden4-despues.png` — envío ORD-30280A83
- `sim/capturas/beto-16-orden5-form.png` / `beto-16-orden5-despues.png` — envío ORD-9BADDCB6
- `sim/capturas/beto-17-orden6-form.png` / `beto-17-orden6-despues.png` — envío ORD-0CF9F0B2
- `sim/capturas/beto-18-todos-enviados.png` — los 6 con su guía confirmada
- `sim/capturas/beto-19-tab-entregado.png` — pestaña Entregado (9 pedidos, incluye los 2 de octubre de Estafeta)
- `sim/capturas/beto-20-orden3-detalle.png` — detalle ORD-D138835A con guía y stock origen guardados
- `sim/capturas/beto-21-stocks-final-bodega-central.png` — inventario Bodega Central DESPUÉS, con bitácora de las 8 salidas de hoy
