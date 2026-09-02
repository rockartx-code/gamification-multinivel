# Diario — Ivonne Castro — Turno 1
**Jueves 4 de septiembre de 2026, 5:00 pm**

## Entrando

Abro `http://localhost:4321/#/login`. Antes de nada me sale un Aviso de Privacidad completo (qué datos guardan, que no los venden, cómo ejercer derechos ARCO). Le doy "Entendido y acepto" — normal, primer día, primera vez que toco el sistema.

Meto `ivonne@findingu.mx` / `99AUBETGGM`. Entro. Arriba a la derecha dice "Ivonne Castro — ADMIN" y "Acciones: 1 urgentes". Anoto que soy ADMIN, no un rol limitado — puedo ver todo el negocio, no solo "mi cartera".

El menú tiene: **Pedidos** (operación diaria), **Clientes** (Personas), **Estadísticas** y **Cuadro de Honor** (seguimiento). No hay ningún menú que diga "Recuperación", "Seguimiento de clientes fríos" ni nada parecido. Ya de entrada: si existe una vista pensada para mi trabajo (detectar quién se enfría), no la veo en la navegación. Tendré que armarla yo cruzando pantallas.

## Pedidos: la foto es muy chica

En Pedidos veo un resumen: "$1,760 cobrado · 3 pedidos". Solo tres pedidos existen en todo el sistema, nunca. Pestañas: Pendiente 0, Pagado 2, Cancelado 1 (el resto en cero). Esto ya me dice algo importante: es una operación diminuta, no miles de clientes — así que "ir viendo" persona por persona sí es viable hoy.

## Clientes: aquí está la pista del "colgado de FindingU"

Entro a Clientes. Arriba: "Clientes totales: 3". Es decir, en TODA la red de la empresa solo hay 3 clientes registrados: Karla Méndez López, Rodrigo Aguilar Ramírez y Marcela Ortiz. Los tres aparecen con Estatus "Inactiva", Descuento 0%, "Mes anterior $0".

Al hacer clic en cada uno aparece un panel "Detalle del cliente" con una sección clave: **"Posición en la red" → "Patrocinador actual"**. Esto es lo que Sofía me explicó: quien no fue invitado por nadie queda colgado de "FindingU".

Reviso los tres, uno por uno (cuesta trabajo — los botones "Ver" no tienen nombre único, tuve que ubicarlos por posición en pantalla, y "Perfil" no abre nada visible):

- **Karla Méndez López** (karla.mendez@outlook.com) → Patrocinador actual: **FindingU**. Comisiones mes actual $0, mes anterior $0 ("Sin movimientos"). Consumo de su red en el periodo: "Karla | $0".
- **Rodrigo Aguilar Ramírez** (rodrigo.aguilar@hotmail.com) → Patrocinador actual: **Marcela Ortiz**. O sea, a Rodrigo lo invitó Marcela — no es mío, es cliente de la red de Marcela. Consumo: "Rodri | $960".
- **Marcela Ortiz** (marcela.ortiz@gmail.com) → Patrocinador actual: **FindingU**. Comisiones $0, "Sin movimientos". Bajo ella cuelga Rodrigo (con $960 de consumo), pero ella misma "Marce | $0".

Con esto ya tengo claro: **mis dos clientes son Karla y Marcela**. Rodrigo no — a él lo tengo que dejar en paz porque tiene madrina (Marcela) y eso no es mi terreno.

## Pedidos por cliente: ¿alguna de las mías compró alguna vez?

Voy a Pedidos → pestaña Pagado: 2 pedidos, ambos del **03/09/2026**:
- Rodrigo Aguilar Ramírez — $960 — Pagada
- Lucia Fernandez — $800 — Pagada

Pestaña Cancelado: 1 pedido, "Prueba Interna" $0 — es una prueba interna del sistema, no un cliente real, lo descarto.

Ni Karla ni Marcela aparecen en ningún pedido, nunca. Confirmo cruzando con Estadísticas → pestaña "Clientes" (dentro del reporte del periodo, Septiembre 2026): la tabla "Clientes con compras en el periodo" solo lista a Rodrigo Aguilar Ramírez ($960), Lucia Fernandez ($800) y Prueba Interna ($0). "Total en base de datos: 3" confirma que no hay más clientes ocultos. Karla y Marcela no compraron nunca — ni este mes ni ningún mes, porque solo han existido 3 pedidos en la historia del sistema y ninguno es de ellas.

Esto es justo el primer caso que Sofía describió: **"quien se registró y no compró."**

## Un dato raro: Lucia Fernandez

Lucia Fernandez pagó $800 (Finding Pro 500g) el 03/09/2026, con domicilio en Guadalajara y teléfono 3312345678 (lo vi en el detalle del pedido). Pero cuando la busco en Clientes escribiendo "Lucia" en el buscador, el sistema responde **"Sin resultados para 'Lucia'."** No está en la red de 3 clientes. No puedo ver quién es su patrocinador, ni si está colgada de FindingU o de alguien más. Es una clienta que compró pero de la que no tengo ninguna ficha de red — no sé si me toca. La dejo fuera por falta de evidencia.

## Estadísticas: la tabla "Top clientes del periodo" está rota

En el resumen de Estadísticas, la tabla "Top clientes del periodo" muestra cosas como "1788340136546", "0", "None" en vez de nombres, todos con $0 de total — a pesar de que sí hay pedidos pagados reales. Es una tabla inservible tal cual está, no me sirve para nada; tuve que ir a la sub-pestaña "Clientes" dentro de Estadísticas para sacar información legible.

## Lo que busqué y no encontré

- **Teléfono / WhatsApp de Karla o Marcela**: no aparece en ningún lado del panel de administración. Solo tengo su correo. El botón "Perfil" en el detalle del cliente no abrió nada visible al hacer clic (ni modal ni navegación). El único teléfono que vi en todo el sistema fue el de Lucia, y fue porque venía en la dirección de envío de su pedido — dato que Karla y Marcela no tienen porque nunca compraron.
- **Fecha de registro**: no aparece en ninguna pantalla de Clientes ni en Estadísticas. No sé si Karla se registró hace 3 días o hace 3 meses.
- **Último acceso / última sesión**: tampoco existe ese dato en ninguna pantalla.
- **Carrito abandonado**: no vi ninguna sección de carritos ni de "checkout iniciado y no terminado".

## Lo que sentí

- Al entrar y ver el menú, alivio — la navegación es simple, pocas opciones.
- Al ver "Clientes totales: 3", sorpresa — esperaba tener que buscar entre cientos, y en cambio la operación es diminuta. Eso hace el trabajo manejable hoy, pero también me preocupa: si la empresa es tan chica, ¿por qué el sistema no tiene ni un campo de teléfono para sus tres clientes?
- Al encontrar "Patrocinador actual: FindingU" en Karla, satisfacción — ahí estaba la señal que Sofía describió, aunque nadie me dijo dónde buscarla.
- Frustración moderada con los selectores de botones ("Ver" resultó tener 3 coincidencias en el DOM por íconos duplicados) — nada del negocio, solo terquedad técnica de la pantalla.
- Al confirmar que ni Karla ni Marcela tienen un solo pedido en la historia del sistema, quedé segura del diagnóstico ("se registraron y no compraron") — pero inmediatamente frustrada al darme cuenta de que no tengo cómo escribirles, porque no hay número de teléfono para ninguna de las dos en ningún lado del sistema.
- Al buscar a Lucia Fernandez y ver "Sin resultados", desconcierto — hay una clienta real, con compra real, que el módulo de Clientes ni siquiera conoce. Da la sensación de que hay dos sistemas de clientes que no se hablan (el de la tienda/pedidos y el de la red MLM).
- Al final, algo de impotencia: identifiqué a mis dos personas con bastante seguridad, pero el sistema no me da el dato mínimo (teléfono) para hacer el trabajo que me pidieron. Voy a tener que pedírselo a Sofía directamente.

## Lo que me faltó

Una ficha de cliente con **teléfono/WhatsApp** y **fecha de registro** habría resuelto todo esto en un clic. Ahora mismo tuve que: (1) entrar a Clientes, (2) abrir cada uno de los 3 para ver su "Patrocinador actual" uno por uno porque no hay columna de patrocinador en la tabla general, (3) cruzar contra Pedidos y contra Estadísticas > Clientes para confirmar que nunca compraron, y aun así terminé sin un solo teléfono utilizable. Una columna "Patrocinador" en la tabla de Clientes, una columna "Teléfono" y una columna "Fecha de registro" me habrían ahorrado los 3/4 del turno.

## Decisión

Con lo que tengo, mis dos clientas de hoy son **Karla Méndez López** y **Marcela Ortiz** — ambas colgadas de FindingU, ambas "Inactiva", cero pedidos en toda la historia del sistema. Evidencia alta de que están frías desde el registro. Pero no tengo teléfono para ninguna de las dos, así que antes de mandar nada real le voy a preguntar a Sofía cómo consigo el WhatsApp de mis clientas — el sistema no lo tiene. Redacto ya los mensajes que les mandaría en cuanto tenga el número, para no perder el día.

A Rodrigo no le escribo — sí compró ($960) y además tiene madrina (Marcela), no es mi terreno.
A Lucia Fernandez no le escribo — compró, pero no aparece en el módulo de Clientes ni tengo forma de saber si es colgada de FindingU o de alguien más; escribirle sin saber eso es justo el error que quiero evitar.
