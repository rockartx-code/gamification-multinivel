# Diario de Beto Salinas — 12 de enero de 2027 (turno de mañana)

> Nota antes de empezar: el sistema me fecha todo "13/01/2027" (bitácora, notas, "Pagado hace 1 día(s)"). Hoy es 12. Sofía ya lo había notado ayer. Lo escribo con la hora que me muestra la pantalla.

## 10:16 — Entrada
Abrí la computadora de la bodega y el navegador todavía tenía mi sesión. Pero en vez del panel me abrió **la tienda de socios**: "Beto Salinas · Tienda · Red · Links · Órdenes · Cuadro de Honor · Mi perfil · Progreso mensual", con carrito, productos y un "Producto recomendado para avanzar en tus metas" (Magnesio Glicinato, con textos "10g por porci?n", "Alta absorci?n" con signos de interrogación). Yo no tengo metas ni red, soy almacén. Piqué mi nombre arriba y el cuadro dice "Usuario Beto Salinas · Rol **admin**" y solo tiene WhatsApp de soporte, correo y "Cerrar sesión". Ningún botón que diga "panel", "almacén" o "pedidos". De rol admin nada: yo solo veo Pedidos, Stocks y Campañas.

Me acordé de que otras veces entré por `#/login`. Ahí sí: "Accede a tu panel", correo, contraseña, "Ingresar al panel". Lo piqué sin llenar nada por costumbre y me marcó bien los dos campos ("Ingresa tu correo electrónico" / "Ingresa tu contraseña"). Llené `beto@findingu.mx` y la contraseña y entré al panel `#/admin`.

Capturas: `beto-ene12-01-inicio.png`, `beto-ene12-02-menu-usuario.png`, `beto-ene12-03-login.png`, `beto-ene12-04-tras-login.png`.

## 10:18 — Lo que me esperaba
Panel: "Pedidos cargados $36,254.40 cobrado · 47 pedidos · Pendientes: 0 · Pagados: 4 · Pendientes envío: 4". Acciones "2 urgentes": *"2 socias con comisión y sin CLABE · $294.20 — Urgente"* (eso no es mío) y *"4 pedidos pagados sin envío — Importante"* (eso sí). Al lado de las pestañas de siempre hay dos botones que no había visto: **"Despacho en bloque"** y "Conciliar pagos".

Pestaña Pagado (4):
- 12/01/2027 · ORD-FA8E7601 · Nadia Prueba · $1,320
- 12/01/2027 · ORD-73A2FDB9 · Diana Robles Castillo · $829
- 12/01/2027 · ORD-66407B13 · **Cliente** · $800
- 20/12/2026 · ORD-B17FBDD2 · Claudia Ibarra Soto · $1,458

El de Claudia lleva 24 días pagado. Sofía me lo había dicho ayer por WhatsApp, y también que el de $800 a nombre de "Cliente" **no** lo despache porque está raro y ya lo reportó.

Captura: `beto-ene12-05-acciones.png`, `beto-ene12-06-tab-pagado.png`.

## 10:19 — "Despacho en bloque"
Como Sofía dijo "todo lo pagado de una vez", probé el botón nuevo. Es una pantalla aparte, "ALMACÉN · Despacho en bloque", con cuatro pasos numerados. Me gustó que va en orden: 1 Bodega de salida, 2 Lista de surtido, 3 Guías, 4 Despachar.

**Paso 1, bodega.** El selector venía en **"Tienda Del Valle · Av. Coyoacán 1200"** y abajo decía textual: *"Aún no tienes bodega por defecto."* con un botón *"Usar Tienda Del Valle como mi bodega por defecto"*. O sea que el sistema me ofrecía de entrada la tienda de Paco, no mi bodega. Si le doy clic sin fijarme, todo se descuenta de Del Valle. Cambié el selector a "Bodega Central · Av. Insurgentes Sur 1234" y el botón cambió a *"Usar Bodega Central como mi bodega por defecto"*. Lo piqué y salió: *"Listo: tu bodega por defecto ahora es Bodega Central. Stocks, Caja y Despacho abrirán con ella."* y en el paso 1 ahora dice *"Mi bodega por defecto: Bodega Central — Es la que tienes guardada"*. Después comprobé en Stocks que "Stock activo" ya abre en Bodega Central. Antes de hoy Stocks siempre me abría en Tienda Del Valle (lo anoté en diciembre), así que esto sí lo arregla, pero tuve que arreglarlo yo.

Captura: `beto-ene12-07-despacho-bloque.png`, `beto-ene12-08-bodega-default.png`.

**La lista.** "Pagados por despachar 4". Tabla con folio, cliente, destino, productos, "Pagado hace", paquetería y guía:
- ORD-B17FBDD2 · Claudia Ibarra Soto · Puebla, PUE · 1 × Colageno Hidrolizado, 1 × Biotina, 1 × Magnesio Glicinato 120 caps (3 pzas) · 24 día(s) · Estafeta
- ORD-66407B13 · Cliente · (destino vacío) · 1 × Finding Pro 500g · 1 día(s) · paquetería "—"
- ORD-73A2FDB9 · Diana Robles Castillo · Puebla, PUE · 1 × Colageno Hidrolizado · 1 día(s) · Estafeta
- ORD-FA8E7601 · Nadia Prueba · Ciudad de Mexico, CMX · 1 × Magnesio Glicinato 120 caps, 1 × Finding Pro 500g (2 pzas) · 1 día(s) · Estafeta

Marqué los tres que sí se pueden (Claudia, Diana, Nadia). El de "Cliente" no, por lo que dijo Sofía y porque no tiene destino. Detalle chico: al marcar un pedido, la columna "Paquetería" que decía "Estafeta" se convierte en un campo vacío ("Estafeta, DHL…") y hay que volver a escribir Estafeta a mano en cada uno; el sistema ya sabía la paquetería y la borra.

**Paso 2, surtido.** "Calcular surtido" → *"Suma por producto de los pedidos seleccionados contra la existencia de Bodega Central"*:

| Producto | Necesario | En Bodega Central | Semáforo |
|---|---|---|---|
| Biotina | 1 | 32 | Alcanza |
| Colageno Hidrolizado | 2 | 19 | Alcanza |
| Finding Pro 500g | 1 | 33 | Alcanza |
| Magnesio Glicinato 120 caps | 2 | 30 | Alcanza |

*"Todo alcanza: puedes despachar 3 pedido(s)."* Esto es justo lo que Sofía me pidió saber ("dime si nos falta producto para algo"): **no falta nada**. Hay hasta una columna "Quién sí lo tiene" para cuando no alcance; hoy quedó en "—".

Captura: `beto-ene12-09-surtido.png`.

**Paso 3, guías.** Dice textual: *"La integración con la paquetería está apagada: las guías se capturan a mano o por CSV. Para encenderla, la gerencia activa la integración con la paquetería (Configuración → Envíos)."* Así que el sistema no genera guías. Las capturé a mano en la tabla, siguiendo la numeración que traemos:
- Claudia ORD-B17FBDD2 → Estafeta · **EST-MX-88120091**
- Diana ORD-73A2FDB9 → Estafeta · **EST-MX-88120092**
- Nadia ORD-FA8E7601 → Estafeta · **EST-MX-88120093**

**Paso 4, despachar.** "Despachar 3 pedido(s)" abrió una ventana de confirmación: *"Despachar 3 pedido(s) desde Bodega Central — Cada pedido pasará a Enviado, se descontará su mercancía de Bodega Central y el cliente recibirá un correo con su guía. Esto no se puede deshacer desde aquí."* con la tabla de los tres folios y sus guías, y botones "Cancelar" / "Sí, despachar 3". Me gustó que me repita lo que va a pasar y a quién antes de hacerlo. Piqué "Sí, despachar 3".

Respuesta: *"Se despacharon 3 pedido(s) desde Bodega Central: ORD-B17FBDD2 (Estafeta EST-MX-88120091), ORD-73A2FDB9 (Estafeta EST-MX-88120092), ORD-FA8E7601 (Estafeta EST-MX-88120093)."* Y abajo un cuadro *"Último despacho · lote DSP-9F7663254C desde Bodega Central"* con los tres "quedó enviado". "Pagados por despachar" bajó a 1 (el de "Cliente").

Capturas: `beto-ene12-10-guias-capturadas.png`, `beto-ene12-11-confirmacion.png`, `beto-ene12-12-tras-despachar.png`.

## 10:24 — Susto: "Volver a Pedidos" me mostró todo como si no hubiera hecho nada
Piqué "Volver a Pedidos" y la pantalla de Pedidos seguía diciendo **"Pagados: 4 · Pendientes envío: 4 · Enviados 0"**, la pestaña Pagado seguía con los cuatro pedidos, guía "-", y "Enviado" con 0 pedidos. Por un momento pensé que el despacho no se había guardado y que iba a tener que repetirlo (y si lo repito, ¿descuenta doble?). Cerré y volví a abrir el panel: ahí sí, **"Pagados: 1 · Enviados: 3"**, y en SIGUIENTE apareció "Confirmar entregas 3". La pantalla de Pedidos no se refresca al regresar del despacho en bloque; hay que recargar. Eso puede hacer que alguien despache dos veces.

Pestaña Enviado (3), ya recargado:
- ORD-FA8E7601 · Nadia Prueba · $1,320 · Enviada · Guia: EST-MX-88120093 · Bodega Central · "Marcar como entregado"
- ORD-73A2FDB9 · Diana Robles Castillo · $829 · Enviada · Guia: EST-MX-88120092 · Bodega Central
- ORD-B17FBDD2 · Claudia Ibarra Soto · $1,458 · Enviada · Guia: EST-MX-88120091 · Bodega Central

Detalle de Claudia: productos correctos, dirección "Av. Juárez, 45, Puebla, CP 72000 · PUE, Tel: 3319876543", "Envío — Guía: EST-MX-88120091 · Stock origen: Bodega Central". Todo cuadra.

Capturas: `beto-ene12-13-tab-enviado.png`, `beto-ene12-14-detalle-claudia.png`.

## 10:25 — Stocks
Stocks abrió directo en Bodega Central (gracias a lo de la bodega por defecto). Existencias después del despacho: Magnesio Glicinato 30→**28**, Colageno Hidrolizado 19→**17**, Biotina 32→**31**, Finding Pro 33→**32**. Coincide con lo que salió (2 magnesios, 2 colágenos, 1 biotina, 1 Finding Pro).

Bitácora: `13/01/2027 10:23 · Bodega Central · Colageno Hidrolizado · Salida por envio · -1 · Despacho orden ORD-B17FBDD2 · **Empleado 1788339615539**`. En vez de mi nombre sale un número. Cuando registré la entrada de magnesio en diciembre sí decía "Beto Salinas". Soy yo, pero nadie que lea la bitácora lo sabe.

Captura: `beto-ene12-15-stocks.png`.

## 10:27 — El pedido de $800 de "Cliente"
Abrí el detalle: *"ORD-66407B13 · Cliente · $800 · Pagada — Productos del pedido: Producto x1 · $800 — Dirección de envío: Sin dirección de envío registrada."* y "Notas internas" **vacío**, solo el campo "Agregar nota" y "Guardar". Sofía me dijo que le había dejado nota ayer; yo no veía ninguna.

Le puse mi nota: *"13/01 Beto: NO despachado. Sofía me dijo que este pedido está raro (sin cliente, sin producto real, sin dirección) y que ya lo reportó a Sistemas. Lo dejo en Pagado hasta que aclaren."* Al guardar, salió *"Nota guardada: el pedido ORD-66407B13 tiene 2 notas internas."* y **entonces sí** aparecieron las dos: la de Sofía ("12/01 Sofía: pedido pagado $800 sin cliente identificable… · 1788339615521 · 13/01 10:13") y la mía (· 1788339615539 · 13/01 10:27). Recargué y volví a abrir el detalle: otra vez "Notas internas" vacío. Las notas existen, pero no se ven al abrir el pedido; solo aparecen después de guardar una nueva. Si Sofía deja una nota para que yo no despache algo, yo no la veo. Y el autor sale como número, no como nombre.

Capturas: `beto-ene12-16-detalle-cliente-800.png`, `beto-ene12-17-nota-cliente-800.png`.

## 10:28 — Correo
Mi buzón (`beto@findingu.mx`) sigue vacío, como siempre. El sistema no me avisa de nada por correo; me entero por la pantalla o por Sofía.

## Cómo me sentí
Contento con la pantalla nueva: en diciembre despachaba pedido por pedido con "Registrar envío" y sin saber si había existencia; hoy en una sola pantalla vi qué necesito, si alcanza y despaché tres de un jalón con confirmación. Lo del "Volver a Pedidos" me dio un susto real de haber perdido el trabajo. Y me molesta que la bodega por defecto fuera la tienda de Paco: si no me fijo, vacío el inventario equivocado.

## Lo que me confundió
- Al abrir el navegador caí en la tienda de socios con metas y carrito, con rol "admin", y sin ningún botón para ir a mi panel. Tuve que escribir `#/login` de memoria.
- "Aún no tienes bodega por defecto" pero el selector ya traía Tienda Del Valle elegida, que no es mi bodega.
- Al marcar un pedido se borra la paquetería que ya traía (Estafeta) y hay que reescribirla.
- "Volver a Pedidos" muestra los contadores y la lista viejos; parece que el despacho no ocurrió.
- Las notas internas no se ven al abrir el pedido; solo aparecen tras guardar una nueva.
- En bitácora y en notas salgo como "Empleado 1788339615539" en vez de Beto Salinas.
- Todo fechado 13/01 cuando es 12/01.

## Lo que no pude hacer
- Despachar ORD-66407B13 ($800, "Cliente"): sin dirección, sin producto real, y Sofía dijo que no. Queda en Pagado con nota.
- Generar guías desde el sistema: la integración con la paquetería está apagada ("la gerencia la activa en Configuración → Envíos"). Las capturé a mano.
- Mandar el cierre de turno desde el sistema: no hay mensajería entre empleados. Se lo mando por WhatsApp (abajo) y lo dejo en `beto-reporte-ene12.txt`.

## Lo que reportaría a Sistemas
1. Empleado de almacén con sesión guardada entra a `#/` y cae en la tienda de socios (metas, carrito, red), rol "admin", sin acceso al panel desde ahí.
2. Despacho en bloque: bodega preseleccionada Tienda Del Valle para un empleado de Bodega Central, con el aviso "Aún no tienes bodega por defecto". Debería proponer la bodega del empleado o no proponer ninguna.
3. Al seleccionar un pedido en Despacho en bloque se pierde la paquetería que ya traía el pedido (Estafeta).
4. "Volver a Pedidos" después de despachar no refresca: Pagados 4 / Enviados 0 hasta recargar. Riesgo de doble despacho.
5. Notas internas del pedido no se muestran al abrir el detalle; solo tras guardar una nota nueva. La nota de la gerente para no despachar era invisible.
6. Bitácora de inventario y notas muestran "Empleado 1788339615539" / "1788339615521" en lugar de nombres.
7. Fecha del sistema un día adelantada (13/01 en vez de 12/01).
8. Textos con "?" en la tienda ("porci?n", "absorci?n").

## 📱 A Sofía — cierre de turno
"Sofía, cierre de turno 12/01 (el sistema lo fecha 13/01), 10:30. Despaché lo pagado desde Bodega Central con la pantalla nueva 'Despacho en bloque', lote DSP-9F7663254C: Claudia Ibarra Soto ORD-B17FBDD2 ($1,458, Puebla) guía EST-MX-88120091; Diana Robles Castillo ORD-73A2FDB9 ($829, Puebla) guía EST-MX-88120092; Nadia Prueba ORD-FA8E7601 ($1,320, CDMX) guía EST-MX-88120093. Todo Estafeta, guías capturadas a mano porque la integración con la paquetería está apagada (dice que la gerencia la enciende en Configuración → Envíos). El sistema avisa que a cada cliente le mandó su correo con guía. NO falta producto: el surtido dio 'todo alcanza' (magnesio 2 de 30, colágeno 2 de 19, biotina 1 de 32, Finding Pro 1 de 33); quedan 28 / 17 / 31 / 32. El único pagado sin despachar es ORD-66407B13 ($800, 'Cliente', sin dirección ni producto), como me dijiste; le dejé nota. Ojo: tu nota de ayer en ese pedido no se ve al abrirlo, solo apareció cuando guardé la mía. Mi bodega por defecto NO era Bodega Central: el sistema me proponía Tienda Del Valle; ya la dejé fijada en Bodega Central. Y al regresar a Pedidos después de despachar seguía mostrando 4 pagados hasta que recargué, casi lo vuelvo a hacer. Pedidos: Pagados 1, Enviados 3, Entregados 32."
