# 18 · Simulación multinivel: un mes de clientes y empleados sobre el backend real

**Fecha:** 2 de septiembre de 2026 (reloj simulado: del 2 de septiembre al 2 de octubre de 2026).
**Rama:** `claude/ultimos-cambios-integrados-fylhiw`.
**Artefactos:** `sim/` (arnés, protocolo, bitácora de soporte `helpdesk.md`), `sim/diarios/` (41 diarios en primera persona), `sim/capturas/` (394 capturas), `sim/servidor.log` (4,060 peticiones HTTP reales).

## 1. Qué se hizo

Se levantó el backend real (las ocho Lambdas de `Micro-lambda-GMF/python`) en local con una DynamoDB en memoria, un reloj congelable, un buzón de correo simulado, una pasarela MercadoPago falsa, un stub de Envia y una cola de Step Functions que se drena tras cada petición. El frontend Angular se sirvió con `ng serve` apuntando a ese backend. Nada de mocks: cada clic de cada persona llegó al código que corre en producción.

Sobre ese mundo se soltaron **14 agentes-persona** con distintos modelos (haiku, sonnet, opus), sin metas ni instrucciones de uso, solo con su historia y su punto de entrada:

| Persona | Modelo | Cómo llegó | Desenlace a un mes |
|---|---|---|---|
| Lucía, 38 | sonnet | Búsqueda orgánica, compra suplementos habitualmente | Compró $800 como invitada; el bote llegó dañado; devolvió; reembolso $800 el 1-oct; reclama $165 del envío de regreso. Volvería "porque siempre hubo alguien real". |
| Rodrigo, 29 | opus | Link de su amiga Marcela; ya está en otra red | Se registró, compró $960 (20 VP, activo), pidió el plan en PDF seis veces. Cierra como cliente: sin recompra ("el plan está amarrado al calendario, no a lo que consumes") y sin red. |
| Karla, 24, móvil | haiku | Anuncio de Instagram de un producto | Registró, vio "invita a 1 persona", se fue. La coach le escribió; pidió no ser contactada. |
| Marcela | sonnet | Socia con tres meses, una referida | Descubrió al intentar cobrar que necesita 20 VP propios. Llegó a 4 directos y $166 bloqueados. El 1-oct cierra su cuenta: "comisiones bloqueadas que nunca se revisan". |
| Tomás, 21, móvil | haiku | TikTok de Marcela, link en bio | Registró, verificó y se fue al leer "Te faltan $20" y "red/comisiones": "me metieron en un MLM". |
| Patricia, 47, móvil | sonnet | Instagram de Marcela, solo el código | Tardó 9 pantallas en encontrar dónde va el código; compró $829; 13 días sin paquete ni correo; producto entregado y funcionando. Recompraría "en farmacia o Amazon, sin patrocinador ni código". |
| Andrés, 35 | opus | YouTube de Marcela, link y código | Ingeniero: hizo el punto de equilibrio con los números que soporte le dio (10 directos activos cada mes para quedar en ceros). No entra ni como cliente; pide baja de datos (ARCO). |
| Héctor, 52 | sonnet | Anuncio de búsqueda en Google (omega 3) | La ficha decía lo mismo que el anuncio y nada más; no compró; 25 días después una llamada de la gerente le pareció cobranza. Pide cancelar y no ser contactado. |
| Rosa Elena, 58, móvil | haiku | Anuncio de Facebook | Se atoró en el formulario; con tres WhatsApp de un humano dictándole casilla por casilla, compró $829. Diez días de silencio hasta el envío. Volvería "si avisan". |
| Iván, 28 | opus | Pre-roll de YouTube (proteína) | Pidió gramos de proteína por porción: nadie los tenía. Se registró por un descuento que resultó $0. Le escribió una coach antes que una etiqueta. Pide baja de datos. |
| Sofía | sonnet | Gerente con todos los permisos, sin capacitación | Cuatro turnos. Resolvió lo que el sistema le dejó y documentó lo que no: baja de datos, cancelar pedidos, guías de retorno, notas por cliente. |
| Beto | haiku | Almacén y pedidos, sin capacitación | Cuatro turnos. Del "inventé las guías" del día 1 a "el sistema es una bitácora de lo que ya pasó; no hay que inventar, solo validar". |
| Ivonne | sonnet | Ejecutiva de recuperación (coach FindingU), añadida a petición | Cuatro turnos. Detectó a los fríos cruzando fichas una por una; dos de sus tres contactos pidieron no ser contactados. |
| Paco | haiku | Cajero de la tienda física | Cobró dos ventas a la primera (público en general y un socio); el corte de caja falló con un error interno; al día siguiente, corregido, cerró a la primera. Sacó el cambio de cabeza. |
| Diego | haiku | Amigo de Rodrigo | Nunca apareció: Rodrigo no compartió su link. |

Las conversaciones entre personas (socia ↔ referido, gerente ↔ almacén, coach ↔ cliente) se relevaron literalmente de un agente a otro. Toda duda a "Soporte Finding'U" la contestó el orquestador como lo haría un soporte real ("Daniel"), con un solo mensaje estilo WhatsApp y sin datos internos; cada duda quedó en `sim/helpdesk.md` como fricción (74 filas).

## 2. Aviso metodológico: qué NO cuenta como hallazgo

Se descartaron antes de escribir una sola línea de código:

- **El reloj "Corte de mes: 23d"** que Rodrigo e Iván reportaron congelado quince días: el contador usa la fecha real del navegador, no la simulada. En producción es correcto. Su razonamiento sobre el daño de un reloj equivocado sí quedó registrado.
- **Las imágenes rotas del catálogo** (Iván): mi semilla mandó `images` como diccionario; el backend espera una lista `{section, url}`. Corregida la semilla y reescritos los productos.
- **"Selecciona un estado válido"** (Rosa Elena): fijó el texto "Michoacán" dentro del `select` en lugar de elegir la opción. No es bug.
- **"Registré 2 frascos dañados y bajó 1"** (Beto): no reproducido mecánicamente; lo más probable es que el formulario reiniciara la cantidad al elegir el producto.
- **Fallos de MercadoPago del día 2**: colisión de mi propio stub de `urlopen`, no del backend.

Todo lo demás se verificó contra la API o el código antes de contarse.

## 3. Bugs de producción encontrados y corregidos (32 commits)

La simulación empezó sin poder crear un solo pedido. En orden de aparición:

| Síntoma vivido | Causa | Commit |
|---|---|---|
| Ningún pedido se podía crear | `vpPoints` se guardaba como `float` y DynamoDB lo rechaza | `7d35569` |
| Todo referido por link quedaba bajo "FindingU", no bajo su patrocinador | El código de referido no resolvía ids numéricos ni acentos | `4627f29`, `b058a3d` |
| El invitado no podía ver, pagar, devolver ni cancelar su pedido ("No autenticado") | Cuatro rutas exigían sesión de dueño a un pedido sin dueño | `61d1344`, `6955194`, `87c0a2f` |
| El envío se cotizaba pero nunca se cobraba | El pedido no guardaba `shippingCost` ni lo sumaba al total | `fd5e241` |
| El socio compraba y no se activaba | El pedido se creaba como `guest` aunque hubiera sesión | `6e00776` |
| El panel decía 19.2 VP y el motor pagaba 20 | Dos rutas de cálculo (pesos ÷ tarifa vs puntos del catálogo) | `2b29a3f`, `aa04e5d` |
| Las metas decían "nivel 1 (30%)" y "50%" | Metas numeradas con su propio índice, no con la configuración | `aa04e5d` |
| "Tu Red $0" para el propio socio activo | El frontend fijaba el consumo propio en 0 | `6f340d1`…`67dbc67` |
| Top clientes con ids en vez de nombres; "Ventas del periodo $0" | El resumen mensual no emitía nombre ni sumaba `netTotal` | `c5af6bc`, `50041b7` |
| Mermas etiquetadas "Salida por venta POS", "Daños registrados 0" | Backend guarda `damage`, admin solo conocía `damaged` | `4aba1b9` |
| "Te faltan $20" para una meta de 20 VP (panel y carrito) | Metas en VP formateadas como dinero; el carrito restaba pesos a puntos | `4aba1b9`, `c1d8ea5` |
| Cuadro de Honor "19" vs panel "20" | Tercera ruta de cálculo de VP | `7e574b1` |
| Seguimiento del pedido: "Total $700" cuando se cobraron $829 | El detalle ignoraba el envío | `240c947` |
| "Solicita una devolución" junto a "devolución en inspección" | El aviso no conocía los estados de devolución | `777aaf4` |
| Pedido reembolsado mostrado como "Pago pendiente" | El seguimiento no conocía `refunded` | `8a8ab5a` |
| La gerente no podía cancelar un pedido pendiente ni explicar "$480 → $609" | Sin botón de cancelar; detalle sin línea de envío | `8a8ab5a` |
| El corte de caja respondía "Internal Inventory Error" | Importes guardados como `float` | `13ce46f` |
| La compra de un socio en mostrador no le acreditaba puntos ni comisionaba a su patrocinadora | El POS solo disparaba `ORDER_DELIVERED`, nunca `ORDER_PAID` | `13ce46f` |

Suite de pruebas: de 52 a 75 funciones de prueba (**109 casos**), todas en verde; cada corrección lleva su regresión con el síntoma que la motivó en la docstring.

## 4. El hallazgo principal: dos productos en una sola pantalla

Siete de las nueve personas que llegaron venían a **comprar un producto** (Lucía, Karla, Tomás, Patricia, Héctor, Rosa Elena, Iván); solo dos venían por el negocio (Rodrigo, Andrés). Todas aterrizaron en el panel de un **distribuidor**: "Misión de red: Invita a 1 persona y actívala este mes", "Meta de red $0 / $300", "Patrocinador: FindingU", "Comisiones", "Cuadro de Honor", campo de CLABE con "Depósitos programados para el día 10". Tres se fueron en ese momento exacto (Karla, Tomás, Iván) y dos más lo nombraron como lo que más desconfianza les dio (Héctor, Patricia). Iván lo resumió: "Me mandaron una coach antes que una etiqueta: eso me dice qué están vendiendo, y no es proteína."

El aviso de privacidad ("calcular tus comisiones y mantener la relación con tu red de afiliados"), el "PC" en cada tarjeta, "Corte en 28d", "Nivel de descuento: Inactivo" y "Completa tus datos para activar descuentos y red" refuerzan lo mismo desde la primera pantalla de la tienda.

Al mismo tiempo, las dos personas que sí querían el negocio (Rodrigo, Andrés) no encontraron **un solo porcentaje ni un solo requisito en toda la aplicación**. Los obtuvieron por WhatsApp de soporte, y con ellos hicieron cuentas que los sacaron. Marcela, con tres meses adentro, descubrió cómo funciona su plan al intentar cobrar su primera comisión.

## 5. Lo que sintieron, por tema

**Miedo a que le vean la cara.** Rodrigo no compró el día 1 "para no dejar a Marcela sin comisión" (el sponsor se perdía por un bug). Andrés e Iván verificaron cada cifra de soporte antes de creerla; todo cuadró, y aun así se fueron: "su problema no es que mientan, es que no publican".

**Frustración con lo que falta, no con lo que hay.** Ninguna de las 13 fichas trae tabla nutrimental, gramos, sabor ni ingredientes; "Ver beneficios" muestra dos etiquetas sueltas. Iván (proteína) y Héctor (omega 3) compararon con la farmacia y ganó la farmacia. Ningún correo de pedido existe: solo hay tres tipos de correo y ninguno es de compra, envío, retraso o entrega. Rosa Elena vivió diez días de silencio; Patricia trece; Rodrigo esperó una factura que soporte prometió y el sistema no puede emitir.

**Alivio con las personas.** Lo que retuvo a quienes se quedaron fue siempre un humano: Daniel dictándole el formulario a Rosa Elena, Sofía escribiéndole a Lucía once días después. Ninguna de esas dos intervenciones deja rastro en la plataforma.

**Culpa y amistad.** Marcela: "no voy a arriesgar amistades con una plataforma a medio terminar". Rodrigo a Marcela: "entendiste tu plan mejor que quienes te lo vendieron". Andrés a Marcela: "me diste números que te costaban un prospecto y los diste igual".

**Del lado de los empleados.** Beto inventó guías el día 1 porque el sistema se las pidió sin decir de dónde salen; el día 15 se detuvo. Sofía descubrió que la guía la genera administración, no el almacén, y que el sistema no lo dice. Ivonne detecta a los fríos abriendo ficha por ficha (siete clientes; "con 300 no"). Paco sacó el cambio de cabeza porque el POS no pide "dinero recibido".

## 6. Huecos de producto (no de pantalla), en orden de daño

1. **Plan de compensación en ninguna parte.** Porcentajes, requisitos por nivel, escalones de descuento, qué es activarse, qué pasa con una comisión bloqueada. Hoy viven en `core/config.py` y en el WhatsApp de soporte.
2. **Comisiones bloqueadas que nunca se reevalúan.** Se escriben `blocked` al pagar cada pedido si el patrocinador no estaba activo en ese instante y no se vuelven a mirar. "Compra $960 para desbloquear tus $166" es falso: comprar después no las libera. Marcela cerró la cuenta al saberlo. Es una decisión de negocio, pero hoy ni el panel ni nadie la explica.
3. **Un solo panel para comprador y distribuidor.** Sin modo "solo cliente", sin ocultar red, CLABE, misión ni Cuadro de Honor a quien solo compró un bote.
4. **Sin correos de pedido** (pago, preparación, retraso, envío con guía, entrega, devolución, reembolso).
5. **Sin baja de cuenta ni borrado de datos.** Tres solicitudes ARCO en un mes (Andrés, Iván, Marcela) y ningún botón ni permiso entre los 30.
6. **Sin "no contactar", notas ni historial de contactos por cliente.** Cuatro personas pidieron no ser contactadas (Karla, Iván, Andrés, Héctor); la lista vive fuera del sistema. Los invitados (Lucía, Héctor, Rosa Elena) ni siquiera tienen ficha.
7. **Ficha de producto sin datos** (ni para el cliente ni para la coach que quiso ayudar).
8. **Logística a ciegas.** El sistema cotiza el envío pero no genera la guía ni dice quién la genera; no hay guía de retorno capturable; "Recibir paquete" acepta cualquier imagen; el reembolso no conoce el envío de regreso ($165 de Lucía) ni tiene estado "en trámite"; una devolución puede quedar once días parada sin alerta.
9. **Dos reglas de descuento.** La tienda aplica el 10% a todo el carrito al cruzar $1,000; el POS le dijo a Rodrigo "alcanzó meta 10%" y aplicó 0%.
10. **Hoyo de precio** (Andrés): los 20 PC más baratos ($960) no alcanzan el escalón de $1,000; $1,020 con 10% cuesta $918. El que busca el mínimo paga más y se lleva menos.
11. **Código de referido escondido** al final del registro; envío visible solo en el último paso ($480 → $609 sorprendió a Héctor 25 días después).
12. **Sin teléfono ni "hablar con alguien"** en toda la tienda (Rosa Elena, Patricia).
13. **Historial mensual inexistente** en el panel del socio: el 1 de octubre septiembre desapareció (VG 33 → 0, bloqueadas $166 → $0).
14. **POS sin cambio** (no pide dinero recibido) y con corte que fallaba.

## 7. Cobertura de rutas

`sim/cobertura.py` cruza `servidor.log` con las 79 rutas que declara el frontend. Ver §10 para la cifra final. Lo que ningún journey orgánico alcanzó en un mes: transferencias entre almacenes, retiros de caja, autorización POS, búsqueda avanzada de pedidos, campañas y cupones desde el cliente. Son rutas sin desencadenante en la vida de estas 16 personas, lo que también es un dato: o sobran, o falta el proceso que las usa.

## 8. Mejoras recomendadas, en orden

1. **Publicar el plan** en la landing y en el panel: tabla de niveles con porcentaje y requisito, escalones de descuento, regla de activación, y una frase honesta sobre las comisiones bloqueadas. Es texto; está en la configuración.
2. **Decidir la regla de bloqueo** (reevaluar al cierre del mes si el socio se activó, o no) y mostrarla. Hoy retiene dinero sin decirlo.
3. **Modo cliente** por defecto para quien llega por producto: tienda, pedidos, perfil. La red se opta.
4. **Correos de ciclo de vida del pedido** y un aviso automático de retraso a los 3–4 días sin envío.
5. **Ficha de producto real** (tabla nutrimental, porciones, ingredientes, sabor) y fotos por producto; quitar el hero fijo de colágeno.
6. **Baja de cuenta y anonimización** con confirmación por correo; "no contactar", notas e historial de contactos en la ficha, también para invitados.
7. **Logística explícita**: quién genera la guía y desde dónde; campo de guía de retorno; reembolso con envío de retorno y estado "en trámite"; alerta de devolución parada.
8. **Una sola regla de descuento** entre tienda y POS; cerrar el hoyo $960–$1,000 (escalón a $950 o mínimo a $1,000).
9. **Código de referido en carrito y checkout**; envío visible desde el carrito.
10. **Historial de meses** en el panel del socio.
11. **POS**: "dinero recibido" y cambio; ocultar "Registrar envío" a quien no puede generar guías.

## 9. Verificación

- Backend: `python3 -m pytest -q tests` → **109 passed**.
- Frontend: `npx tsc --noEmit -p tsconfig.app.json` sin errores tras cada parche; el `ng serve` en vivo recompiló cada cambio y las personas lo vieron en su siguiente turno ("Te faltan 20 VP", "Total $829", "Dano").
- Cada corrección se comprobó en la sesión viva de la persona que la reportó antes de avisarle (Rodrigo lo exigió el día 3: "verifiquen antes de avisar").
- `environment.ts` se devolvió a la URL de producción al cerrar; el arnés (`sim/`) queda en el repositorio con `estado.pkl`, buzón, capturas, perfiles y diarios ignorados por git.

## 10. Cifras finales

| Cifra | Valor |
|---|---|
| Peticiones HTTP reales al backend | 4,060 |
| Rutas que declara el frontend | 79 |
| Alcanzadas según `sim/cobertura.py` | 37 |
| Alcanzadas además con query string, que el cruce literal no empareja (`cash-control`, `cash-cuts`, `pos/sales`, `customers/getall`, `stocks/movements`, `orders/find`) | 6 |
| **Rutas ejercidas por personas reales** | **43 / 79** |
| Nunca tocadas en un mes | 36: transferencias entre almacenes y su recepción, retiros y autorización POS, cambio y recuperación de contraseña, documentos y privilegios de cliente, categorías y activos del catálogo, campañas, cupones desde el cliente, comprobantes y solicitud de pago de comisiones (nadie llegó a cobrar), notificaciones leídas, `GET /cart` y `GET /user-dashboard` (el frontend usa otras rutas) |
| Personas | 14 (10 clientes o prospectos, 4 empleados) |
| Mensajes de WhatsApp relevados o contestados | 75 filas en `sim/helpdesk.md` |
| Diarios en primera persona | 41 |
| Capturas | 394 |
| Commits de corrección durante la simulación | 32 (18 síntomas de producción distintos) |
| Pruebas | 109 casos, 0 fallos |
| Compras cerradas | 5 (Lucía $800, Rodrigo $960, Patricia $829, Rosa Elena $829, Guadalupe $560 en mostrador; más Rodrigo $480 en mostrador) |
| Clientes que piden no ser contactados o baja de datos | 4 + 3 |
| Socios activos al cierre de septiembre | 1 (Rodrigo). Comisiones pagadas: $0 |
