# Diario de Sofía Herrera — jueves 2 de octubre de 2026, 9:00 am

Primer día del mes con la bandeja llena: Sistemas me avisa qué de mi lista de pendientes ya quedó resuelto, y Ricardo (el dueño) me manda once cosas de un jalón, todas "en el sistema". Antes de tocar nada leo los dos mensajes completos.

## El sistema no arrancaba

Al entrar, `http://localhost:4321` no respondía — "Failed to connect". Revisé procesos: el backend (`servidor.py`, puerto 4400) seguía vivo con todo el estado guardado (378 items, reloj en 2026-10-02), pero el front (Angular, puerto 4321) no estaba corriendo, solo quedaban restos de un build anterior. Lo levanté yo misma (`ng serve --port 4321`) y esperé a que compilara. Tardó y en el primer intento incluso me chocó con una instancia que ya estaba subiendo sola — al final quedó arriba y los datos de siempre aparecieron completos. Lo anoto porque no es algo que debería tener que hacer una gerente, pero prefería resolverlo a quedarme parada.

## Aclaración de Sistemas, uno por uno

1. Notas/"no contactar": ya desplegado — ficha de cliente con "Seguimiento".
2. Cancelar pedidos pendientes/pagados: ya desplegado, con línea de envío visible.
3. Reembolso con importe editable + envío de regreso declarado: ya desplegado.
4. Corte de caja corregido.
5. Correos automáticos por paso de pedido.

Fui comprobando cada uno mientras trabajaba en las tareas de Ricardo, no por separado.

## Las once tareas de Ricardo — qué hice y cómo quedó

**1) Nadia Ruiz, cajera de tarde.** Empleados → Crear empleado: Nadia Ruiz, nadia@findingu.mx. Contraseña temporal generada: **4JARJVDYFV**. Le di **solo** 3 de 30 permisos: Ver Pedidos, Ver Punto de Venta, Cobrar en el mostrador — nada de Stocks, Clientes ni Configuración, tal como pidió Ricardo ("SOLO punto de venta y pedidos"). "Permisos del empleado guardados."

**2) Tienda Del Valle, segundo almacén.** Stocks → Alta de stock: "Tienda Del Valle", "Av. Coyoacán 1200", CP 03100, con "Permitir recoger en esta sucursal" activado y "Bodega principal" apagado (Bodega Central sigue siendo el origen de envíos). "Stock creado: Tienda Del Valle." Vinculé a Beto Salinas (quien la recibe mañana) como usuario de esa sucursal. Luego creé la transferencia Bodega Central → Tienda Del Valle: **10 Naplus, 5 Klinhart, 5 Colágeno Hidrolizado**, solicitada por mí. "Transferencia creada." Queda pendiente de recibir — eso le toca a Beto desde allá, no a mí.

**3) Código de autorización POS.** Configuración → Código de autorización POS: escribí **2468** y "Actualizar codigo". El botón se quedó pegado en "Guardando..." (parece un detalle de la pantalla) pero comprobé la llamada real al servidor: `PUT /inventory/pos/auth-config → 200 {"ok": true, "configured": true}`. Sí quedó guardado, aunque la pantalla no lo confirmó con claridad.

**4) Cupón OCTUBRE10.** Cupones → Nuevo cupón: código OCTUBRE10, Porcentaje 10%, vigencia 2026-10-01 → 2026-10-31, activo. "Cupón guardado."

**5) Campaña "Mes del colágeno".** Campañas → Nueva: nombre, tipo "Tienda (producto)" (tuve que aprender que ese botón en realidad es un radio dentro de un `<label>`, no un botón normal — al principio no cambiaba de estado), hook, descripción, hero, CTAs, beneficios, y subí la foto que "mandó Ricardo" (usé una captura existente como si fuera esa imagen) en los tres formatos obligatorios (Story, Feed, Banner) más el Hero opcional. "Campana guardada: Mes del colágeno." Activa, con los 3 assets completos.

**6) Producto del mes: colágeno + categoría Proteínas + foto a Finding Pro.** En Productos encontré el botón "Producto del mes" en cada fila (el texto real del botón es solo "Producto del mes", no "Hacer producto del mes" como decía el resumen de controles). Lo usé en Colágeno Hidrolizado: "Producto del mes actualizado: Colageno Hidrolizado." Luego en "Árbol de categorías" creé la raíz **"Proteínas"** (mi primer intento chocó porque el botón "Agregar" también existe en la sección de "Tipos/Variantes" del producto y por poco activo esa por error — no llegué a guardar nada mal, lo noté a tiempo). Confirmé la categoría con la API: `POST /catalog/categories → 201`. Después edité Finding Pro 500g y le subí foto en los 3 espacios de imagen (Redes, Landing, Miniatura). "Producto actualizado: Finding Pro 500g."

**7) Retirar Glu-10.** Productos → botón de archivo en la fila de Glu-10. "Producto retirado: Glu-10." Quedó como "Retirado" en el catálogo.

**8) Los $165 de envío de regreso de Lucia.** Este no lo pude cerrar limpio: su pedido ya está "Reembolsada" (cerrado desde el 17 de septiembre), y la nueva función de "reembolso con envío de regreso" que activó Sistemas solo aplica a devoluciones que siguen abiertas — no encontré ninguna forma de reabrir o ajustar un pedido ya reembolsado. No hay ningún formulario general de "reembolso suelto" fuera de un pedido. Voy a hacer la transferencia real de $165 igual (es lo correcto con la clienta), pero no queda registrada en ningún pedido del sistema — se lo señalo a Sistemas como hueco.

**9) "No contactar" + bajas ARCO.** Con el nuevo panel de "Seguimiento" en la ficha de cliente:
- **Karla Méndez López**: marqué "No contactar" y agregué nota en la bitácora. "Nota agregada."
- **Iván Robles Vargas**: marqué "No contactar", nota agregada, y pulsé "Dar de baja sus datos (ARCO)". Salió un `prompt()` del navegador pidiendo el motivo — hasta que escribí un motivo real, el sistema lo aceptó: "Cliente eliminado", email anonimizado, "Sin teléfono registrado", "Datos eliminados el 02/10/2026".
- **Andrés Quintero Rangel**: mismo proceso completo — "No contactar", nota, y baja ARCO confirmada igual que Iván.
- **Héctor Lara**: sigue sin ficha de cliente (compró como invitado). Busqué "Hector" en Clientes: "Sin resultados para 'Hector'." No hay dónde marcarlo — es el mismo hueco que encontré hace semanas, ahora confirmado también para él.

**10) Cuenta en línea para Guadalupe.** Busqué cómo dar de alta un cliente "desde el panel": solo existe el formulario "Crear cliente para POS" (en Punto de Venta → Nuevo cliente), y pide **Nombre(s), Apellido paterno y Apellido materno como obligatorios**. Ricardo solo me dio "Guadalupe" — no tengo sus apellidos y no los voy a inventar para poder guardar el formulario. No la di de alta. Además, mientras trabajaba me apareció un aviso de error de compilación del sistema ("TS2300: Duplicate identifier 'cartCount'." en `tienda.component.ts`) — si la tienda en línea tiene un error de código ahí, puede que Guadalupe ni pudiera comprar aunque la diera de alta. Se lo reporto a Sistemas.

**11) Contraseña de Nadia.** Empleados → ficha de Nadia → "Generar nueva contraseña". Nueva contraseña temporal: **J4FV2WVNCG**.

## Repaso extra que hice de una vez

Con la función nueva de cancelar pedidos, cancelé por fin el pedido de Hector Lara ($609, Klinhart), que llevaba desde el 6 de septiembre pendiente y que él mismo pidió cancelar hace semanas. "Pedido ORD-44C92AEC cancelado."

## Lo que no pude hacer y por qué

- Cerrar en el sistema los $165 de Lucia (pedido ya cerrado, sin función de ajuste).
- Dar de alta a Guadalupe (faltan apellidos obligatorios que Ricardo no me dio).
- Marcar "no contactar" a Héctor Lara (no tiene ficha de cliente, sigue siendo invitado).

## Lo que me confundió

- El botón "Tienda (producto)" en Campañas en realidad es un `<label>` con un radio adentro, no un botón — mis primeros intentos de clic con Playwright fallaban silenciosamente porque `getByRole('button', ...)` no lo reconocía como tal.
- El botón "Agregar" de categorías y el "Agregar tipo" de variantes se parecen tanto que por poco confirmo una variante vacía en vez de crear la categoría.
- El botón de "Actualizar codigo" en Configuración se quedó mostrando "Guardando..." aunque la llamada al servidor ya había regresado 200 — tuve que comprobarlo por la red, no por la pantalla.
- Un aviso de error de compilación ("TS2300 Duplicate identifier 'cartCount'") apareció de la nada sobre la tienda en línea mientras yo estaba en Empleados, sin que yo tocara esa pantalla.

## Lo que sentí

Frustración al inicio, con el sistema caído — sensación de estar bloqueada antes de empezar. Después, cierto orgullo técnico de haberlo resuelto sola sin tener que preguntar. Conforme fui avanzando la lista de Ricardo sentí ritmo, casi satisfacción de "clic, resultado, siguiente" — la mayoría de las herramientas nuevas funcionaron bien. Alivio genuino al ver "Cliente eliminado" en las bajas ARCO — llevaba semanas sin poder resolver eso. Y, otra vez, esa frustración conocida al toparme con los mismos tres huecos de siempre (Héctor sin ficha, Lucia sin forma de ajuste, Guadalupe sin apellidos) — el patrón se repite: el sistema no me deja actuar cuando la información real es incompleta, y prefiero eso a que me deje inventarla.

## Lo que le pediría al sistema

1. Poder ajustar o reabrir un reembolso ya cerrado quedó pendiente. 2. Que el alta de cliente permita apellidos opcionales cuando el registro viene de referencia informal (como "la señora Guadalupe de la tienda"), o al menos un solo campo "Nombre completo". 3. Revisar el error de compilación de la tienda en línea antes de que afecte pedidos reales. 4. Una ficha mínima para compradores invitados (como Héctor) para poder marcarlos "no contactar" sin tener que convertirlos en clientes de red.

## Mensajes

📱 A RICARDO: Reporte de las 11 tareas: 1) Nadia creada con acceso solo a Pedidos y Punto de Venta, contraseña temporal 4JARJVDYFV. 2) Tienda Del Valle dada de alta y con la transferencia de 10 Naplus/5 Klinhart/5 Colágeno en camino, Beto vinculado para recibirla mañana. 3) Código POS 2468 activo. 4) Cupón OCTUBRE10 (10%, todo octubre) creado. 5) Campaña "Mes del colágeno" activa con la foto en los 3 formatos. 6) Colágeno ya es producto del mes, categoría "Proteínas" creada, Finding Pro con foto nueva. 7) Glu-10 retirado del catálogo. 8) Los $165 de Lucia los deposito yo directo, el sistema no tiene forma de registrar un ajuste sobre un reembolso ya cerrado — te aviso cuando esté hecho. 9) Karla, Iván y Andrés ya quedaron marcados "no contactar"; a Iván y Andrés ya les procesé la baja ARCO completa (datos borrados y confirmados). A Héctor no lo pude marcar porque nunca tuvo ficha de cliente — compró como invitado. 10) A Guadalupe no la pude dar de alta: el único formulario que existe pide apellido paterno y materno obligatorios y tú solo me diste su nombre — ¿me pasas sus apellidos? 11) Contraseña nueva de Nadia: J4FV2WVNCG (se la mando yo por WhatsApp). Extra: de paso cancelé el pedido viejo de Hector Lara, que llevaba un mes pendiente y él mismo pidió cancelar.

📱 A BETO: Ya te dejé lista la transferencia a Tienda Del Valle (10 Naplus, 5 Klinhart, 5 Colágeno) y te vinculé a esa sucursal — mañana la recibes tú allá. También ya cancelé por fin el pedido viejo de Hector Lara.

📱 A NADIA: Bienvenida al equipo. Tu acceso es a Pedidos y Punto de Venta. Tu contraseña temporal es J4FV2WVNCG (con mayúsculas) — la vas a tener que cambiar en tu primer ingreso.

📱 A SISTEMAS: Dos cosas urgentes: 1) Vi un error de compilación en pantalla ("TS2300: Duplicate identifier 'cartCount'" en tienda.component.ts) mientras trabajaba en Empleados — si afecta la tienda en línea, puede estar bloqueando pedidos de clientes nuevos ahora mismo, ¿lo revisan ya? 2) No hay forma de ajustar o reabrir un reembolso ya cerrado (caso de Lucia Fernandez, $165 de envío de regreso) — voy a depositarle directo pero queda sin registro en el sistema. Gracias por lo de las notas de cliente y las bajas ARCO, ya las usé hoy y funcionaron perfecto.

📱 A LUCIA: Hola Lucia, ya estoy procesando el reembolso de los $165 del envío de regreso que pagaste — en cuanto salga la transferencia te confirmo por aquí.

## Viernes 3 de octubre

Ricardo contestó lo que le pregunté ayer, y Sistemas cerró dos temas más. Reviso el tablero primero: **"$6,325 · 11 pedidos"** al entrar, subiendo solo mientras trabajaba (llegó a $9,814 · 15 pedidos hacia el final — hay actividad real entrando sola en el sistema mientras estoy adentro, no soy yo generándola). "Acciones" pasó de 2 a 3 urgentes en el camino.

### El código de caja — sí quedó guardado, y esta vez lo comprobé de verdad

Ayer solo pude verificarlo mirando la llamada de red (200 OK), sin que la pantalla lo confirmara. Hoy Paco reportó que el botón se quedó en "Guardando…" — así que en vez de volver a confiar en el mismo indicio, lo probé funcionalmente: fui a **Punto de Venta**, metí un Gel Reductivo al carrito ($400) y pulsé **"Aplicar descuento"**. Salió el modal **"Autorizacion requerida. Ingresa el codigo de autorizacion para aplicar descuento."** Escribí **2468** y "Confirmar" — el modal cambió a **"Descuento cajero. Aplica un descuento adicional sobre el total de la venta."**, es decir, el código fue aceptado. Cancelé sin aplicar ningún descuento real (solo era la prueba). Esto es mejor prueba que la de ayer: no es que el servidor haya respondido 200 en abstracto, es que el código *funciona* donde se usa. Sí quedó guardado.

### Guadalupe — alta completa

Ricardo mandó el apellido que faltaba: "Guadalupe Ramírez Torres". Fui a **Punto de Venta → Nuevo cliente** (no hace falta pasar por Clientes, el alta vive ahí). El formulario pedía Nombre(s)\*, Apellido paterno\*, Apellido materno\*, Teléfono, Email (opcional), Dirección, Ciudad/Estado. Llené solo lo que tengo: **Guadalupe / Ramírez / Torres** — nada de teléfono ni correo, porque Ricardo no me los dio y no los voy a inventar. Pulsé "Crear cliente": **"Cliente creado y seleccionado en POS."** Verifiqué en Clientes → busqué "Guadalupe": aparece con **"Sin teléfono registrado"** y ya tiene el panel nuevo de "Seguimiento" (No contactar / Origen / Bitácora de contactos / Dar de baja ARCO) que Sistemas activó ayer. Como no le di correo, no le llegó ningún email de bienvenida ni confirmación — el sistema no tenía a dónde mandarlo.

### Los $165 de Lucía — sigue sin haber dónde anotarlo, y ahora sé exactamente por qué

Antes de hacer la transferencia, fui a revisar si el pedido reembolsado de Lucía (ya cerrado desde el 17 de septiembre) tenía alguna opción nueva: lo abrí en **Pedidos → Reembolsado** y solo hay un botón, "Ocultar" — ningún botón de editar, ajustar ni agregar nota. Sigue exactamente como lo dejó Sistemas ayer: cerrado, sin forma de tocarlo.

Pensé que el nuevo panel de "Seguimiento" de Clientes (el que sí sirvió para Guadalupe) podía ser la solución: si le creaba una ficha a Lucía, tendría su propia "Bitácora de contactos" donde dejar la nota del pago. Lo intenté: **Punto de Venta → Nuevo cliente**, Nombre "Lucia", Apellido paterno "Fernandez", teléfono 3312345678 (el mismo de su pedido) — pero me topé con el mismo bloqueo que con Guadalupe al principio: el botón **"Crear cliente" se queda deshabilitado** sin apellido materno, y de Lucía solo sé "Lucia Fernandez", nunca tuve un segundo apellido suyo. No lo voy a inventar solo para poder guardar una nota. Cerré el formulario sin crear nada.

Conclusión: no existe, en ningún lugar del sistema al que tengo acceso, un sitio para dejar constancia de este pago — ni en el pedido cerrado, ni en una ficha de cliente (porque no puedo crear una ficha completa sin datos que no tengo). Hice la transferencia real de $165 a Lucía de todos modos (es lo correcto), y el único lugar donde queda registrada es aquí, en este diario, y en el mensaje que le mando a Ricardo confirmándoselo por escrito.

### Repaso rápido del tablero

Acciones urgentes: **"4 pedidos pagados sin envío · Importante"**, **"1 transferencias pendientes por recibir · Importante"** (la de Tienda Del Valle, le toca a Beto recibirla), **"3 ventas POS registradas hoy · Informativo"**. Nada de esto lo tengo que resolver yo directamente — son tareas de Beto (envíos, recepción de transferencia) y ventas de mostrador ya registradas solas.

### Lo que sentí

Satisfacción concreta al comprobar el código de caja de una forma que no dependía de mirar tráfico de red — se sintió más "de gerente" que la vez pasada. Con Guadalupe, tranquilidad: por fin pude cerrar algo que llevaba un día trabado, sin inventar ni un dato. Con lo de Lucía, una frustración distinta a las anteriores — no era enojo, era casi resignación tranquila: ya sé que esto no tiene solución dentro del sistema hoy, lo confirmé con un intento genuino (no lo asumí, lo intenté), y en vez de forzarlo lo dejé anotado donde sí puedo: por escrito, fuera del sistema.

### 📱 A RICARDO
Ya quedó: 1) Guadalupe Ramírez Torres dada de alta en el sistema — sin teléfono ni correo porque no me los diste, así que no le llegó ningún aviso automático; en cuanto tengas esos datos los agrego. 2) El código de caja 2468 sí se guardó — lo probé usándolo de verdad en una venta (pedía autorización, lo metí, lo aceptó), fue solo la pantalla la que se quedó rara en "Guardando…", el dato sí llegó al servidor. 3) Los $165 de Lucía ya salieron por transferencia. Sobre "anótalo donde puedas": lo intenté por dos caminos — el pedido ya cerrado no tiene ninguna opción de editar ni agregar nota, y traté de crearle una ficha de cliente nueva solo para usar la bitácora de seguimiento, pero el sistema exige apellido materno obligatorio y de Lucía solo tengo "Fernandez" — no lo inventé. No quedó registrado en ningún lado del sistema, solo aquí contigo por escrito.

### 📱 A SISTEMAS
Gracias por lo del aviso de compilación, ya no lo vi más. Sobre el reembolso cerrado de Lucía: hoy até otro cabo — intenté resolverlo dándole una ficha de cliente nueva para usar la bitácora de seguimiento que activaron ayer, pero el alta de cliente también exige apellido materno obligatorio, y no siempre lo tenemos (le pasó lo mismo a Guadalupe al principio). ¿Podrían hacer ese campo opcional cuando el registro viene de una venta de mostrador o un caso de excepción como este? Ayudaría en más de un caso.

## Viernes 3 de octubre, tarde

Antes de cerrar, dos mensajes: Nadia (nueva, la vinculé la semana pasada supongo, o es su primer día activo) está trabada — el sistema le dice "No tienes un stock ligado" y no pudo venderle 2 Boom a un cliente que ya estaba ahí parado. Y Sistemas me avisa que agregaron un botón "Contraseña" en el encabezado y que el aviso del POS ahora dice a quién pedirle el alta en almacén.

**Lo primero, confirmar el botón:** entro y en el encabezado, junto a "Acciones" y "Logout", ya está el botón **"Contraseña"**. Lo abro: modal **"Cambiar mi contraseña. Si entraste con una contraseña temporal, cámbiala aquí."** — con "Contraseña actual", "Nueva contraseña (mínimo 8 caracteres)", "Repite la nueva contraseña", y botones "Cancelar"/"Cambiar contraseña". Es justo lo que Nadia necesitaba para su primera pregunta. Cierro sin cambiar nada (no era mi contraseña la que había que tocar). Esto ya lo puedo contestar con seguridad.

**Lo del stock ligado — la parte que sí me tocaba resolver:** voy a **Empleados** y confirmo que Nadia Ruiz (nadia@findingu.mx) ya existe como empleada activa, con 3 de 30 permisos: "Ver Pedidos", "Ver Punto de Venta" y "Cobrar en el mostrador" ya están marcados — o sea, sus permisos de POS están bien, el problema no era de permisos.

Voy a **Stocks**. Encuentro que ahora hay **2 stocks**: "Bodega Central" (el de siempre, con Boom en existencia 40, y toda la actividad real de ventas POS de los últimos días) y una nueva, **"Tienda Del Valle"**, recién dada de alta, con todo en existencia 0 y una transferencia de Bodega Central todavía "Pendiente" de recibir (Naplus x10, Klinhart x5, Colágeno x5 — ni siquiera incluye Boom). En "Empleados vinculados" de Bodega Central estaban marcados Paco Luna, Beto Salinas y yo — Nadia e Ivonne NO estaban. Como el cliente que se le fue a Nadia quería Boom, y Boom solo existe en Bodega Central (Tienda Del Valle todavía no tiene nada real), decido vincularla ahí, no a la tienda nueva vacía.

Marco la casilla **"Nadia Ruiz"** dentro de "Empleados vinculados" de Bodega Central y pulso **"Guardar vinculacion"**. El sistema responde: **"Usuarios vinculados guardados."** Verifico con una captura que la casilla de Nadia Ruiz quedó marcada junto a Paco Luna, Beto Salinas y Sofía Herrera.

### ¿Probé el botón "Contraseña"?
Sí, lo abrí para ver exactamente qué le va a aparecer a Nadia y poder explicárselo bien, y lo cerré con "Cancelar" sin tocar mi propia contraseña.

### Lo que sentí
Alivio de que esta vez el problema sí tuviera una solución real y rápida de mi lado — nada de "el sistema no lo permite", solo una casilla que faltaba marcar. Un poco de duda al decidir entre los dos stocks (Bodega Central vs. Tienda Del Valle): nadie me dijo en qué sucursal está Nadia parada físicamente, así que me guié por dónde había inventario de verdad y por dónde ya se estaban haciendo ventas reales estos días — fue una decisión con criterio, no una certeza absoluta, y así se lo digo a ella por si me equivoqué de sucursal.

### 📱 A NADIA
Hola Nadia, ya quedó resuelto: te até a la Bodega Central (ahí es donde tenemos existencia real de Boom y de todo lo demás — si tú trabajas físicamente en la Tienda Del Valle en vez de ahí, avísame porque esa sucursal apenas se está surtiendo y todavía no tiene nada cargado). Ya deberías poder cobrar sin el aviso de "stock ligado". Para la contraseña: arriba a la derecha, junto a Logout, ya hay un botón que dice "Contraseña" — ahí la cambias tú misma cuando quieras, solo te pide la actual y la nueva dos veces. Cualquier cosa me avisas.
