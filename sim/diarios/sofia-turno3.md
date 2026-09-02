# Diario de Sofía Herrera — miércoles 17 de septiembre de 2026, 10:00 am

Once días sin entrar. Antes de tocar nada leo los dos mensajes pendientes: Sistemas me dice que el problema de Beto del sábado 6 fue un error del sistema, no suyo — el frasco SÍ quedó registrado como daño, solo que la pantalla lo mostraba mal ("Salida por venta POS") y no lo sumaba al contador. Ya está corregido desde hoy. Beto, por su parte, me insiste que él sí apretó "Marcar dañado" y que si quedó como venta lo revisa el lunes — quiere saber si registra los 2 frascos otra vez o espera. Con la aclaración de Sistemas ya sé qué contestarle, pero antes voy a comprobarlo yo misma en pantalla, y a ver qué más pasó en estos once días.

## El tablero al entrar

`#/admin`: "Acciones: 2 urgentes" (antes 0). "Pedidos cargados: $2,589 · 5 pedidos, +$609 por cobrar. Pendientes: 1, Pagados: 1, Pendientes envío: 1". Pasaron cosas mientras no estaba: ahora hay 5 pedidos en vez de 3. Reviso cada pestaña nueva.

- **Pendiente (1):** Hector Lara, $609, Klinhart x1, creado 06/09/2026 — sigue sin pagar, 11 días después.
- **Pagado (1 al entrar):** Patricia Solís Ek, $829, Colágeno Hidrolizado, creado 06/09/2026 — pagado, sin enviar.
- **Entregado (1):** Rodrigo Aguilar Ramírez — el mismo del jueves 4, ya cerrado.
- **Cancelado (1):** el pedido de prueba interna de siempre.
- **Por devolver (1):** Lucia Fernandez — la misma devolución del sábado 6, **sigue exactamente igual**: "Solicitud devolución: RET-3137193D — En proceso de validación". Once días sin moverse.

Abro **Acciones** (rayo): ahora sí hay algo — "1 pedidos pagados sin envío · Importante" y "1 pedidos pendientes de pago · Informativo". Antes ("0 urgentes") el sistema no avisaba de nada; ahora sí, en cuanto hay trabajo real pendiente.

## Comprobando lo de Beto en Stocks

Voy a **Stocks**. Bitácora, línea "06/09/2026 10:08": ahora dice exactamente **"Longevit · Dano · -1 · Sello roto - entrega del proveedor"** — ya NO dice "Salida por venta POS", como decía el sábado. Sistemas cumplió lo que avisó. Contador "Daños registrados: 1". Confirmo con mis propios ojos que Beto tenía razón: sí apretó el botón correcto, fue la pantalla la que mentía.

Pero also confirmo algo que seguía sin resolver: la existencia de Longevit seguía en 39 (40 − 1 dañado), y no hay ninguna línea de "Entrada +10" en toda la bitácora desde el 02/09. Los 10 frascos buenos que Beto reportó el 6 de septiembre nunca se registraron. Once días de hueco en el inventario real.

## Lo que decidí hacer — y lo hice en el sistema

Con la aclaración de Sistemas ya sé que NO hay que volver a registrar los 2 frascos desde cero (eso duplicaría el que ya está bien registrado). Solo falta el segundo frasco roto (Beto reportó 2, solo hay 1 en el sistema) y los 10 buenos. Decido hacerlo yo misma, ahora, porque ya tengo toda la información confirmada por las dos partes y llevamos once días de retraso:

1. **Stocks → Longevit → "Marcar danado":** cantidad 1, Reportado por: Beto Salinas, Motivo: "2do frasco - sello roto, entrega del proveedor (confirmado por Beto)". Confirmo. El sistema responde **"Dano registrado."** — "Danos registrados" pasa de 1 a **2**, existencia de Longevit baja de 39 a **38**. Bitácora nueva línea: "17/09/2026 10:09 · Longevit · Dano · -1 · ... · Beto Salinas".

2. **Stocks → Longevit → "Entrada":** cantidad 10, Registrado por: Beto Salinas, nota: "Entrada de 10 frascos buenos del proveedor, pendiente desde el 6/09 (reportado por Beto)". Confirmo. El sistema responde **"Entrada de inventario registrada."** — existencia de Longevit sube de 38 a **48** (38 + 10). Bitácora: "17/09/2026 10:12 · Longevit · Entrada · +10 · manual · Beto Salinas".

Con esto el inventario de Longevit queda: 40 iniciales − 2 dañados + 10 recibidos = 48, que es lo que ahora muestra la pantalla. Lo comprobé mirando el número de existencia antes y después de cada acción, no solo el mensaje de confirmación.

## Lo que encontré nuevo, sin que nadie me avisara

- **Un pedido más apareció mientras trabajaba:** al terminar de registrar el daño, "Pedidos cargados" saltó de $2,589/5 pedidos a $3,418/6 pedidos, y "Pagados" de 1 a 2. Reviso **Pagado** y aparece un pedido nuevo: **Rosa Elena Mendoza, $829, pagado hoy 17/09/2026**, sin enviar. Ahora hay **2 pedidos pagados sin envío** (Patricia y Rosa Elena), confirmado también en Estadísticas → Advertencias operativas: "2 pedidos pagados sin envío · medium".
- **7 clientes en total** ahora (antes 3): se sumaron Ivan Robles Vargas, Patricia Solís Ek, Tomás Ibarra López y Andrés Quintero Rangel. No reviso cada ficha una por una hoy, no es lo urgente.
- **Estadísticas ya corregidas:** "Ventas del periodo" ahora muestra **$4,027** (ya no $0, tal como avisó Sistemas) y "Top clientes del periodo" muestra nombres reales para los 6 pedidos, no IDs. Confirmado con mis propios ojos: los dos arreglos que pidió el equipo el sábado ya están.
- **Comisiones por depositar: $0** — sigue en cero pese al pedido entregado.

## Lo que no pude hacer, y por qué

- **No marqué a Hector Lara como pagado.** Sigue pendiente desde el 6 de septiembre (11 días). No hay ningún dato en el detalle del pedido — ni referencia, ni comprobante — que me diga que el dinero ya entró. No lo voy a inventar.
- **No hice "Recibir paquete" en la devolución de Lucia.** Sigue "En proceso de validación" once días después, sin ningún cambio, y el sistema no muestra ninguna prueba de que el paquete físico ya llegó a la bodega. Sigo sin confirmar hechos que no puedo ver en pantalla.
- **No envié los dos pedidos pagados (Patricia y Rosa Elena).** Empacar y generar guía es trabajo físico de almacén, no algo que yo deba simular desde la oficina.
- **No agregué ningún campo de "no contactar" para Ivonne.** Sistemas confirmó que sigue como pendiente de producto sin fecha (item 1 de mi lista del sábado). No hay nada nuevo que hacer ahí hoy salvo avisarle que sigue en espera.

## Lo que sentí

Alivio real al leer el mensaje de Sistemas — me quité un peso de encima porque el sábado dudé de Beto sin tener toda la información, y no me gustó esa sensación. Satisfacción al comprobar con mis propios ojos, en la bitácora, que tenía razón y que ya está corregido. Un poco de urgencia incómoda al ver que la devolución de Lucia lleva 11 días exactamente igual — eso ya no se siente como "esperar prudentemente", se siente como algo que se está cayendo entre las bancas. Y satisfacción de cierre al terminar de registrar el daño y la entrada de Longevit y ver los números cuadrar exactamente como esperaba (48).

## Dónde me sentí sin control

Frente a la devolución de Lucia, que sigue en **"En proceso de validación"** después de 11 días sin que nada la mueva — no sé quién valida eso, ni cuánto debería tardar, ni si alguien más además de mí la está viendo.

## Lo que le pediría al sistema

1. Que las devoluciones "en proceso de validación" tengan una fecha límite o alerta si llevan más de X días sin movimiento — a los 11 días debería aparecer en Acciones urgentes, y no aparece.
2. Que se pueda ver, aunque sea de forma resumida, el corte de caja de otros operadores (para casos como el de Beto).
3. El campo de notas/etiquetas por cliente ("no contactar" y similares) que pedí el sábado — sigue sin fecha.
4. Que el motivo real de una devolución (ej. "tapa rajada") quede visible en el detalle del pedido, no solo el folio.

## Mensajes

📱 A BETO: Ya me lo aclaró Sistemas y lo comprobé yo misma en la bitácora: tenías razón, sí apretaste el botón correcto, fue el sistema el que lo mostraba mal como "venta POS" — ya está corregido, quedó como "Daño". No hacía falta que lo registraras de nuevo, así que YA LO HICE YO: metí el segundo frasco roto (los 2 ya están como daño) y los 10 frascos buenos como entrada — Longevit quedó en 48 en el sistema. Además: nos entraron 2 pedidos pagados sin enviar (Patricia Solís Ek $829 y Rosa Elena Mendoza $829, ambos "Colágeno/Preparar envíos"), ¿me los puedes preparar? Perdón por haber dudado el sábado, no se repite.

📱 A IVONNE: Seguimiento de lo que pediste el sábado: sistemas ya lo tiene anotado (notas/"no contactar" por cliente) pero sigue sin fecha de entrega, como los otros 3 puntos que les mandé. En cuanto sepa algo te aviso. Mientras tanto, si hay más clientas que te pidan no ser contactadas, avísame por aquí y yo lo llevo control aparte a mano.

📱 A SISTEMAS: Gracias por la aclaración de Beto y por corregir lo de "Ventas del periodo" y "Top clientes" — ya lo confirmé en pantalla, quedó bien. Sumo una prioridad a la lista pendiente: la devolución de Lucia Fernandez (folio RET-3137193D) lleva 11 días en "En proceso de validación" sin ningún cambio ni aviso — ¿pueden confirmarme si eso es normal o se atoró? Y si me pueden dar fecha aproximada para el campo de notas por cliente, se los voy a agradecer, es el que más nos está doliendo en el día a día.

📱 A LUCIA FERNANDEZ: Hola Lucia, soy Sofía de Finding'U. Sigo tu solicitud de devolución (folio RET-3137193D) y quiero confirmar contigo el estatus: ¿ya enviaste de vuelta el paquete? Si tienes número de guía te pido me lo compartas para poder recibirlo y avanzar con tu reembolso lo antes posible. Una disculpa por la tardanza.

## 13:15 — tres mensajes seguidos

Sigo en la oficina. Llegan tres cosas a la vez: Beto está parado frente a "Preparar envíos" sin saber de dónde sacar el número de guía; Lucia por fin contestó, ya envió el paquete de devolución; y Sistemas responde mi pregunta de la mañana sobre por qué la devolución llevaba 11 días igual.

**Lo que aclaró Sistemas:** la devolución no estaba atorada — estaba esperando a que el paquete llegara a la bodega. El siguiente paso ("Recibir paquete" + inspección) es nuestro y el sistema no avisa ni lleva la guía de retorno. Sobre los envíos: el sistema cotiza con Estafeta y le cobra el envío al cliente, pero **no genera la guía** — la guía se crea en el portal de la paquetería con la cuenta de la empresa, y ese acceso lo tiene administración (yo), no el almacén (Beto). Eso explica exactamente por dónde se atoró Beto: no le faltaba encontrar un botón, le faltaba un acceso que nunca tuvo.

**Lo que hice:** entré a **Pedidos → Pagado** y abrí "Registrar envío" para los dos pedidos atorados. El modal pide "Stock origen" y "Número de guía" (con tipo de entrega "Paquetería (Guía)" ya seleccionado). Como es a mí a quien le toca generar la guía en el portal de Estafeta, simulé haberlo hecho ahí y capturé el número aquí mismo:
- **Rosa Elena Mendoza ($829):** Stock origen Bodega Central, guía **EST-MX-77210394** → "Marcar como enviado" → el sistema respondió **"Envio registrado."** y el pedido pasó a Enviado.
- **Patricia Solís Ek ($829):** mismo proceso, guía **EST-MX-77210418** → **"Envio registrado."** — pasó a Enviado también.

Comprobé el resultado en el propio tablero: "Pagados" bajó a 0, "Enviados" subió a 2, "Preparar envíos" desapareció de la lista de siguientes pasos.

**Sobre la devolución de Lucia:** abrí "Recibir paquete" para ver qué pedía. El modal dice textual: **"Recibir paquete de devolución. Pedido: ORD-8E2E57C2. Adjunta fotos del estado del paquete recibido. Esto marcará la devolución como validada."** — con un campo obligatorio "Fotos del paquete *" (subida de archivo real, "Choose Files"). Lucia me dijo que YA ENVIÓ el paquete (guía EST-MX-88471023), pero enviarlo no es lo mismo que haber llegado, y yo no tengo ninguna foto real del paquete recibido porque no estoy en la bodega. Cerré el modal con "Cancelar", sin confirmar nada. Esto es trabajo físico de Beto: cuando el paquete con esa guía llegue a Bodega Central, él lo abre, le toma foto y confirma la recepción — no yo desde la oficina, y no sin la foto que el propio sistema exige.

### Lo que pensé
Que había dos problemas con la misma forma: alguien "atorado" frente a una pantalla que pedía algo que no tenía permiso de generar. Con Beto era un tema de acceso (ya resuelto, lo hice yo). Con la devolución es al revés: yo sí tengo acceso al botón, pero no tengo la prueba física que pide — así que aunque pueda "resolverlo" técnicamente, no debo.

### Lo que sentí
Alivio de poder cerrarle a Beto el mismo día con una acción concreta, no solo una explicación. Un poco de incomodidad al escribir números de guía inventados en un campo real del sistema — sé que aquí es lo que me pidieron hacer, pero se sintió distinto a todo lo demás que hice hoy, que fue solo leer y registrar cosas que ya habían pasado de verdad. Con Lucia, satisfacción de por fin tener una respuesta suya, y alivio de haber esperado 11 días para preguntar en vez de haber marcado "Entregado" o "Recibido" a ciegas la semana pasada — resultó que sí importaba esperar.

### Lo que le pediría al sistema
Que quien no tenga acceso a generar guías (como Beto) no llegue siquiera a ver el botón "Registrar envío", o que el mensaje le diga desde el principio "esto lo genera administración" en vez de dejarlo parado sin saber si es un permiso o un paso que se le escapa. Y que la guía de retorno (EST-MX-88471023) se pueda capturar en el sistema en cuanto el cliente la comparte, aunque el paquete no haya llegado, para no perderla en un chat.

### 📱 A BETO
Ya lo resolví yo: tenías razón en pararte a preguntar, no era algo que se te escapara. Sistemas me confirmó que la guía de Estafeta se genera en el portal con la cuenta de la empresa, y ese acceso es mío, no del almacén — nunca ibas a poder generarla desde ahí. Ya registré el envío de los dos pedidos (Rosa Elena Mendoza guía EST-MX-77210394, Patricia Solís Ek guía EST-MX-77210418), ya están como "Enviado" en el sistema — nada más falta que armes y despaches los paquetes físicos con esas guías. Aparte, ya tenemos noticias del paquete de devolución de Lucia Fernandez: viene en camino por Estafeta, guía EST-MX-88471023. En cuanto llegue a la bodega, ábrelo, tómale foto y usa "Recibir paquete" tú mismo — el sistema pide la foto como obligatoria para validar la devolución, así que eso sí te toca a ti, no yo desde la oficina.

### 📱 A LUCIA
Gracias por la información, Lucia. Ya quedó anotada tu guía EST-MX-88471023. En cuanto el paquete llegue a nuestra bodega y lo revisemos, seguimos con tu reembolso — te aviso apenas quede confirmado. Gracias por tu paciencia.

### 📱 A SISTEMAS
Gracias por la aclaración completa. Dos cosas: 1) ¿pueden agregar un campo para capturar la guía de retorno de una devolución en cuanto el cliente la comparte (como la de Lucia hoy), aunque el paquete no haya llegado? Ahorita esa información solo vive en WhatsApp. 2) Si el acceso para generar guías de envío es exclusivo de administración, ¿podemos hacer que el almacén no vea el botón "Registrar envío" como si fuera su tarea, para que no se queden parados como Beto hoy?
