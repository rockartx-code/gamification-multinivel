# 22 · Lo que dicen los diarios: inquietudes, fricción y tareas que se pueden automatizar

Lectura completa de los **89 diarios** de `sim/diarios/` (unas 715 KB; 30 personas entre clientes, prospectos, socias y empleados; septiembre de 2026 a enero de 2027), cruzada con las 172 filas de `sim/helpdesk.md` y con el estado real de cada corrección en las rondas [18](18-simulacion-multinivel.md) a [21](21-cuarta-ronda-escenarios-restantes.md).

Método: cinco lectores independientes extrajeron de cada grupo de diarios (clientes de la primera ronda en dos bloques, almacén y caja, gerencia y coach, socios de noviembre y diciembre) las inquietudes, los atorones, las tareas repetidas, lo que sí funcionó y frases textuales con archivo. Este documento agrupa esas extracciones, cuenta cuántas personas distintas dicen lo mismo, y marca para cada punto si **ya se corrigió**, si está **parcial** o si sigue **abierto**. Las propuestas del §7 salen de ahí: no de lo que un diario pide, sino de lo que varios diarios repiten.

## 1. Resumen ejecutivo

| | |
|---|---|
| **Inquietud número uno de los clientes** | Llegaron a comprar un producto y aterrizaron en un panel de distribuidor (red, comisiones, VP, CLABE, datos fiscales). 9 de 17 compradores o prospectos lo dicen con esas palabras; 5 de ellos se fueron sin comprar por eso. |
| **Inquietud número uno de las socias** | No pueden calcular el negocio: el plan no está publicado dentro de la plataforma, hay tres monedas (PC, VP, VG) con reglas distintas, y el descuento recorta los VP sin avisar. 8 personas; 3 lo pidieron por escrito más de cinco veces. |
| **Inquietud número uno de los empleados** | Miedo a disparar algo irreversible con un botón que no explica su efecto ("Marcar entregado", "Pagar comisiones", "Cobrar"), y desconfianza de un toast que dice "guardado" cuando no se guardó. Los cinco empleados lo expresan. |
| **Mayor fricción de clientes** | El checkout: registro obligatorio según por dónde entres, pasarela que fallaba, envío "gratis" que se vuelve $129 al poner el código postal, canasta de 20 VP que hay que sumar a mano y contraseña que se recupera en casi cada visita. |
| **Mayor fricción de empleados** | Cruzar pantallas a mano: 3 pestañas para detectar clientes fríos (más de 40 clics por turno), 13 productos por 10 pedidos para saber si alcanza el inventario, 16 fichas abiertas una a una el día de pago. |
| **Tareas más repetitivas y automatizables** | (1) despacho pedido por pedido con guías que llegan por WhatsApp; (2) marcar entregados a mano y pedidos que quedan meses en "Enviada"; (3) el día de pago: transferir fuera, generar comprobante y subirlo por cada beneficiario; (4) detectar y contactar clientes fríos; (5) explicar el plan por WhatsApp uno a uno; (6) armar la canasta de activación a mano y recomprar lo mismo cada mes. |
| **Lo que ya se corrigió gracias a los diarios** | Más de 70 bugs en cuatro rondas (documentos 18 a 21), entre ellos los que más aparecen aquí: pasarela, cantidades del carrito, cupón en móvil, correos del ciclo del pedido, notas y "no contactar", saldos pendientes del POS, CLABE obligatoria para pagar. Este documento marca cada uno. |
| **Lo que sigue abierto y más pesa** | Modo "solo cliente", plan publicado con calculadora, pago de comisiones por lote con archivo bancario, despacho masivo con lista de surtido, rastreo y cierre automático de envíos, suscripción mensual, sesión persistente, y una política para las comisiones bloqueadas que se pierden al cierre de mes. |

## 2. Quiénes hablan

| Grupo | Personas | Diarios | Resultado |
|---|---|---|---|
| Compradores de producto (anuncio, buscador, TikTok) | Karla, Tomás, Iván, Héctor, Andrés, Lucía, Patricia, Rosa Elena, Lupe | 22 | 5 se fueron sin comprar (Karla, Tomás, Iván, Héctor, Andrés). Lucía, Patricia, Rosa y Lupe compraron; tres recompran por el producto, no por el modelo. |
| Socias con red (y sus invitadas) | Verónica, Claudia, Bety, Lupita, Marcela, Rodrigo, Memo | 33 | Marcela se fue perdiendo $166 bloqueados. Rodrigo se quedó como cliente sin compartir link. Verónica se queda "chiquito". Las demás activas en diciembre. |
| Almacén y caja | Beto, Nadia, Paco | 22 | Beto pasó de "inventar guías" a "preguntar primero". Nadia perdió tres ventas por bloqueos del sistema. Paco cargó $1,000 de cambio en el bolsillo. |
| Gerencia y coach | Sofía, Ivonne | 20 | Sofía pidió tres veces el mismo hueco (notas de cliente) hasta que llegó. Ivonne dedicó "tres cuartos del turno" a cruzar pantallas. |

## 3. Inquietudes de clientes y socias

Ordenadas por cuántas personas distintas las expresan.

### 3.1 "Me metieron a un MLM sin decírmelo" (9 personas)

Karla, Tomás, Iván, Héctor, Andrés, Lucía, Patricia, Rosa Elena y Rodrigo llegaron por un producto y descubrieron red, comisiones y "Meta mensual: 20 VP" después de registrarse o incluso sin registrarse.

- "Yo quería un bote de proteína y salí dado de alta como vendedor" (ivan-dia5).
- "Ni siquiera me registré y ya me están sumando puntos de comisión" (lucia-dia1).
- "A mí solo me interesa mi paquete perdido, no entré a vender nada" (rosa-nov14).
- "Marcela no estaba recomendando un producto. Estaba reclutando distribuidores" (tomas-dia5).
- Soporte lo reconoce: "hoy no tenemos un modo 'solo cliente' que oculte esas secciones" (Daniel, en ivan-dia5).

Agravante: el aviso de privacidad y el perfil piden constancia fiscal, INE, CURP y cuenta bancaria. "Pedí la tabla nutrimental y me pidieron mi cuenta bancaria" (ivan-dia5); "¿para qué necesitan mis datos bancarios de entrada?" (patricia-dia5). La landing dice "Gratis · Sin riesgo" (andres-dia5).

**Estado: abierto.** Es la causa directa de 5 de las 5 pérdidas de prospectos y del rechazo de Rosa, Patricia y Lucía al panel. Ninguna corrección de las cuatro rondas lo toca.

### 3.2 No se puede calcular el negocio (8 personas)

Rodrigo, Andrés, Marcela, Verónica, Bety, Claudia, Lupita y Memo preguntan porcentajes, requisitos y reglas que la plataforma no muestra.

- "En ningún lugar de esta plataforma dice cuánto gano cuando alguien de mi nivel 1 compra" (rodrigo-dia1). Pidió el PDF del plan cinco veces en un mes; Marcela "lleva tres meses pidiéndolo".
- "El problema de esta empresa no es que mienta. Es que no publica" (andres-dia5). Andrés y Verónica, por separado, calculan que BRONCE exige unas 225 personas activas para $500 al mes.
- Tres monedas: "PC en la tienda, VP en las comisiones, VG en los rangos, y nadie las presenta" (veronica-dia1). El descuento recorta los VP: "Parece que el descuento también recorta los VP, aunque el catálogo no lo avisa" (bety-dic12); "el 'PC' que aparece junto a cada producto en el catálogo no es lo mismo que los VP reales del pedido" (claudia-dic20).
- Reglas de suma: "¿Los VP de dos compras distintas en el mismo mes se suman o cada compra se evalúa aparte?" (claudia-nov13); "¿El % de descuento se calcula por cada pedido por separado o se acumula en el mes?" (veronica-dic12). Las metas del panel y el nivel del carrito "parecen dos reglas distintas con los mismos nombres" (veronica-dic12).
- Un dato contradictorio: Lucía sí vio en la página de registro una tabla de generaciones y rangos con pagos de $500 a $10,000 (lucia-dia1), mientras Rodrigo reporta "cero números" en la landing. La tabla existe en un lugar y no en los que los socios consultan (panel, carrito, comisiones).

**Estado: parcial.** El carrito ya dice "Con este pedido llegas a X de 20 VP" y por qué (ronda 4). Los porcentajes por generación, la tabla de descuento y las reglas de activación siguen fuera de la plataforma; se explican por WhatsApp caso por caso.

### 3.3 Comisiones que se bloquean, se pierden o desaparecen (6 personas)

- Marcela perdió $96 que subieron a $166 bloqueados y al cierre del mes "el contador se reinició. Como si esos $166 nunca existieran" (marcela-oct1). Soporte le dijo primero "en cuanto los tengas se libera" y después "comprar $960 ahora no las desbloquea". "Para cobrar $96 de comisión, necesito GASTAR $960 de MI DINERO. ¿Esto es un negocio o un esquema?" (marcela-dia3b).
- Bety: "¿A dónde se fue esa comisión?" al ver "Sin movimientos" donde había tres correos de $138.60 (bety-dic12).
- Verónica y Claudia: "si yo no compro, no me pagan las comisiones de mi red, aunque ellos sí compren" (veronica-nov13).
- Rodrigo: "El plan no está amarrado a cuánto producto consumes, está amarrado al calendario" (rodrigo-dia15).

**Estado: parcial.** Ya existe la reevaluación al activarse dentro del mes (Claudia recuperó $195.20 el 20 de diciembre), las filas anuladas quedan visibles con motivo y hay correo de anulación (rondas 3 y 4). Lo abierto es de política, no de código: qué pasa con lo bloqueado al cerrar el mes, y cuándo se avisa a la socia que está por perderlo.

### 3.4 Silencio y lentitud después de pagar (6 personas)

Patricia (13 días, "armando el paquete"), Rosa (10 días y luego seis semanas), Verónica (pedidos despachados a los 42 días), Lucía (sin correo de compra), Rodrigo ("mi bandeja sigue teniendo un solo correo"). "Si yo no me meto a picarle, no me entero de nada" (veronica-dia1). "Yo le compré a Finding'U, no a Marcela" (patricia-dia15): la queja va al patrocinador porque no hay otro canal visible.

**Estado: parcial.** Los correos del ciclo del pedido existen desde la ronda 2 y en diciembre "el correo llegó el mismo minuto" (claudia-dic20). Sigue abierto el rastreo: no hay estado del carrier, y cuatro pedidos de octubre y noviembre llevaban meses en "Enviada" (beto-dic18).

### 3.5 Miedo a que cobren distinto de lo mostrado (5 personas)

Verónica pagó $112 de más en la pasarela; Bety heredó el miedo ("no quiero sorpresas en el estado de cuenta"); Héctor desconfió de una llamada con un monto que no cuadraba; Rodrigo vio carrito $1,089 y orden $960; todos vieron el envío "Gratis" convertirse en $129 al capturar la dirección: "Eso no se hace. Es lo mismo que un precio de gancho" (veronica-dia1).

**Estado: parcial.** La pasarela y los totales cuadran desde la ronda 1. El envío gratis condicionado al total con descuento sigue igual (hallazgo 5 de la ronda 4).

### 3.6 Devoluciones: quién paga, qué se devuelve, cuánto tarda (4 personas)

"¿Tengo que regresar todo el pedido o nada más el bote dañado?" (lupita-nov14). "La pantalla y el correo dicen cosas distintas" sobre el envío de regreso (patricia-dic16). Lucía pagó $165 de envío de retorno que no le reembolsaron. Memo: "¿Cuánto tiempo tarda y a dónde regresa el dinero?" (memo-dic12).

**Estado: parcial.** Correo alineado con la pantalla, cupón de cortesía real, sugerencia de reembolso por motivo (ronda 4). Abierto: devolución parcial por producto, y plazo y medio de reembolso en pantalla.

### 3.7 Reputación con los amigos (3 personas)

"Si mando mi link hoy y a la persona le pasa lo mismo, el que queda como tonto soy yo" (rodrigo-dia2). "Le vendí esto como una 'oportunidad' sin entender cómo funcionaba" (marcela-dia3b). Verónica: "La gamificación está afinada para que yo compre, no para que yo construya" (veronica-dia1). Es la razón por la que ninguna socia compartió su link en cuatro meses de simulación.

## 4. Inquietudes de los empleados

1. **Botones sin explicar su efecto.** "El sistema me da un botón para clickear, pero no me dice si debo hacerlo" (beto-turno1). Sofía: "'siguiente paso sugerido' no es lo mismo que 'ya pasó'" (sofia-turno1). Paco: "una vez que clickeé Cobrar, la venta se registró ya" (paco-turno1). El caso extremo es el 10 de enero: "Pagar comisiones" aceptó un comprobante sin CLABE ni transferencia y no había reversa (sofia-ene10). **Corregido** ese caso; el patrón general sigue.
2. **El toast dice guardado y no se guardó.** Botón pegado en "Guardando…" (sofia-turno5), archivo que queda en "0 archivo(s)" (sofia-turno13), PATCH que responde lo contrario de lo que se marcó (sofia-dic10), dato de "$340 pendiente" que desaparece tras registrar (nadia-dic13b). Sofía verifica por red o recargando en casi todos sus turnos. **Abierto** como patrón.
3. **No saber si el error es propio o del sistema.** Beto registró 2 frascos dañados y el inventario bajó 1; Sofía lo corrigió por una etiqueta equivocada de la bitácora: "dudé de Beto sin tener toda la información, y no me gustó esa sensación" (sofia-turno3). **Corregido** el caso.
4. **Bloqueos sin explicación que dejan al cliente sin atender.** Nadia perdió tres ventas: sin stock ligado el primer día, código 7412 rechazado cuatro veces, y "le dije que sí le fiaba el resto y a la hora de cobrar no pude" (nadia-dic13). "Me dieron acceso a un sistema pero no me capacitaron y el sistema mismo me bloquea sin explicar qué hacer" (nadia-turno1). Corte deshabilitado "sin ningún tooltip o mensaje" (nadia-turno3). **Parcial**: saldos pendientes y código quedaron; los botones deshabilitados siguen mudos.
5. **Qué hacer con el efectivo físico.** "La pantalla sólo registra el número" (nadia-turno2); "¿Debo guardarme los $440 de cambio en mi bolsillo?" (paco-turno1). **Parcial**: ya se captura efectivo recibido y cambio; no hay arqueo (efectivo esperado contra contado) en el corte.
6. **Dos sistemas de clientes que no se hablan.** Ivonne no sabe a quién le toca dar seguimiento: compradores invitados sin ficha de red (ivonne-turno1). **Parcial**: los pedidos de invitados ya se ligan al correo; no hay ficha unificada.
7. **Contactar a quien no quiere.** "El sistema mide actividad de compra, no preferencia de contacto" (ivonne-turno2). Karla: "preferiría que no me contacten sin haber pedido nada". **Corregido**: "No contactar", notas y bitácora de contactos (ronda 2).
8. **Datos que el sistema no captura.** Quién firmó la entrega, estado del paquete devuelto, paquetería, nota de la entrada de inventario. **Parcial**: paquetería y notas internas existen; la nota de entrada se sigue perdiendo ("manual").

## 5. Puntos de fricción, por costo

| # | Dónde | Quién y evidencia | Estado |
|---|---|---|---|
| 1 | **Checkout que exige registro según la puerta de entrada** | Karla (7 campos + correo + login a las 11:30 pm), Tomás ("no hubo opción de solo comprar como cliente"); Héctor y Rosa sí compraron como invitados | Abierto: el flujo depende de si entras por landing o por tienda |
| 2 | **Pasarela que fallaba** | Lucía: 3 intentos en 3 días; Rodrigo: 3 intentos; Claudia: pago "Pendiente" sin correo | Corregido (ronda 1 y 3) |
| 3 | **Canasta de 20 VP a mano** | Verónica, Bety, Lupita, Claudia, Patricia quedaron en 18–19 VP con "20 PC" de catálogo; todas hicieron un segundo pedido chico | Parcial: aviso en carrito; falta sugerir qué agregar |
| 4 | **Envío "Gratis" que se vuelve $129 al poner CP** | Verónica, Patricia, Rosa, Rodrigo, Lucía | Abierto |
| 5 | **Contraseña y códigos** | Memo, Lupita, Claudia, Patricia piden dos códigos porque el primero se invalida; Rosa esperó uno que no llegó; re-login casi cada sesión (Verónica, Claudia, Rosa "como tres veces", Beto turnos 6 y 7) | Abierto |
| 6 | **Cantidades duplicadas en el carrito** | Bety, Karla, Verónica ("si escribes 1 y le picas, pide 2"), Memo, Lupita ("Quitar a todo") | Corregido (ronda 4) |
| 7 | **Cupón sin campo en móvil** | Patricia buscó dos pedidos seguidos | Corregido (ronda 4) |
| 8 | **Recoger en sucursal** | Claudia: "No se pudo crear la orden" sin motivo; Patricia desde Mérida: única sucursal en CDMX | Parcial: ya muestra el motivo; la opción aparece aunque no aplique a tu ciudad |
| 9 | **Devolución** | Lucía: candado por "En tránsito" cuando ya lo tenía; 3 pasos y 3 fotos que se perdieron con "No autenticado"; Lupita: sin elegir producto; Patricia: 3 fotos para un paquete cerrado | Parcial: autenticación corregida; parcial por producto y fotos según motivo abiertos |
| 10 | **Rutas y sesión del back office** | `#/login` con sesión no redirige; `#/` es la tienda: "pensé que había perdido el acceso admin" (sofia-turno14); Verónica socia con acceso cayó en 403 | Parcial: 403 corregido; rutas abiertas |
| 11 | **Botones "Ver" duplicados (fila escritorio + móvil en el mismo DOM)** y dos campos de archivo en la misma pantalla | Ivonne, Sofía ×4: clics al elemento equivocado; el comprobante de Bety se subió al campo equivocado | Abierto |
| 12 | **Stock activo por defecto en la sucursal equivocada** | Beto "casi anoto mal el inventario" en tres turnos; dropdown de stock vacío hasta visitar Stocks | Parcial: dropdown corregido; el stock por defecto sigue |
| 13 | **Prompts y confirms del navegador** para cantidades, motivos y montos | Beto (transferencias: "el clic en Recibir no hizo nada visible"), Sofía (cancelar, reembolso, deshacer pago) | Abierto (la ronda 4 añadió tres más) |
| 14 | **Cobrar un saldo pendiente** | Nadia buscó en 5 pantallas | Corregido (ronda 4) |
| 15 | **Folio no visible / categoría que no se puede renombrar** | Sofía: 8 pestañas buscando un folio; 3 intentos con la categoría | Parcial: folio corregido; categoría abierta |
| 16 | **Tres módulos, tres cifras del mismo mes** | Rodrigo: "VP 19.2" y "VG 20" en la misma tarjeta; "Tu Red $0" con $960 comprados; reloj de corte clavado 30 días | Corregido en su mayoría (rondas 1 a 3); "Tu Red" propio abierto |
| 17 | **Orden fantasma desde caja** | Rodrigo: venta POS ligada a su cuenta sin confirmación, 9.6 VP, link del correo en blanco | Parcial: anulación con aviso existe; ligar cliente sin confirmar sigue |

## 6. Tareas repetitivas y automatizables

Frecuencias tomadas de los diarios; los pasos son los que la persona describe, no una estimación.

| # | Tarea | Quién | Frecuencia observada | Costo por vez | Automatización propuesta |
|---|---|---|---|---|---|
| 1 | **Registrar envío pedido por pedido** copiando la guía que Sofía manda por WhatsApp | Beto | 2, 1, 6, 1, 10 por turno | Ver → Registrar envío → stock → tipo → paquetería → guía → Marcar (7 pasos) | Generar la guía desde el pedido (API de la paquetería) o importar el CSV de guías del portal; despacho en bloque: seleccionar pedidos pagados y "Despachar N" |
| 2 | **Revisar existencias antes de despachar** transcribiendo una tabla de 13 productos y sumando pedido por pedido | Beto | 13 × 6 y 13 × 10 en dos turnos | Media hora de aritmética por turno | Lista de surtido consolidada por producto con semáforo contra el stock de la bodega; bloqueo del despacho si falta, con el producto y la sucursal que sí lo tiene |
| 3 | **Marcar entregados uno a uno** con el reporte de Estafeta recibido por WhatsApp; guardar "firmó X a las Y" en nota interna | Beto, Sofía | 1–2 por turno; 4 pedidos quedaron meses en "Enviada" | 3 pasos + nota | Rastreo del carrier por webhook o consulta diaria; cierre automático a N días con correo "¿te llegó?" (hallazgo 11 de la ronda 4); firma y hora guardadas en el pedido |
| 4 | **Día de pago: abrir cada ficha, transferir fuera, generar comprobante, subirlo, recargar para verificar** | Sofía | 9, 11, 16 y 16 fichas en cuatro días de pago (≈50 fichas) | 5–6 pasos por beneficiario | Pantalla "Pagos del mes": tabla con listos para depositar, sin CLABE y ya pagados; exportar archivo de dispersión para el banco; subir un comprobante por lote y marcar pagados en bloque; aviso automático de "registra tu CLABE" a la socia desde que tiene comisión confirmada (hallazgo 13) |
| 5 | **Detectar clientes fríos cruzando Clientes, Pedidos y Estadísticas** y abrir ficha por ficha para ver el patrocinador | Ivonne | 5 turnos; 36 fichas abiertas; en el último turno 16 fichas + 9 pestañas + 13 bitácoras (más de 40 clics) | "Tres cuartos del turno" | Ya parcial (filtro "Solo fríos", última compra, CSV). Falta: lista diaria "Seguimiento de hoy" ordenada por días sin compra y sin contacto, con teléfono, patrocinador y último pedido en la misma fila |
| 6 | **Redactar el mismo WhatsApp y después anotar la nota a mano** | Ivonne, Sofía | ≈7 mensajes de Ivonne; 2 de Sofía a Claudia y Bety por la CLABE | Verificar ficha + redactar + anotar | Plantillas por situación (bienvenida, fría, CLABE pendiente, pedido tardío) con enlace `wa.me` prellenado y la nota de contacto creada al pulsarlo |
| 7 | **Explicar el plan por WhatsApp uno a uno** | Daniel (soporte), Verónica a Bety por videollamada, Marcela | Rodrigo 8 intercambios en 15 días; Andrés, Iván, Marcela, Bety, Claudia | Cada respuesta individual | Publicar el plan dentro de la plataforma: porcentajes por generación, requisitos de activación y de cada generación, tabla de descuento, PDF descargable; calculadora "si mi red compra X, gano Y" |
| 8 | **Armar la canasta de activación a mano** y hacer un segundo pedido chico | Verónica, Bety, Lupita, Claudia, Patricia | 5 personas, 5 segundos pedidos | Sumar PC, descontar 10 %, volver a comprar | Botón "Completa tu activación" que sugiera el producto más barato que cierra los VP que faltan; y **suscripción mensual** (autoenvío) para quienes recompran lo mismo (Bety, Rosa, Patricia) |
| 9 | **Recuperar contraseña en cada visita** | Memo, Lupita, Claudia, Patricia, Rosa, Verónica, Bety | Casi cada sesión de la primera ronda | 2 códigos cuando el primero se invalida | Sesión persistente ("recordarme"), enlace de acceso por correo o WhatsApp, aceptar el último código emitido |
| 10 | **Cuadrar caja a mano y decidir qué hacer con el efectivo** | Nadia, Paco | 1 corte y 1 retiro por turno; Paco guardó $1,000 en el bolsillo | Suma mental + nota en el diario | Corte con arqueo: efectivo esperado, contado, diferencia y a dónde va (retiro con código o fondo del día siguiente) |
| 11 | **Facturar a mano** | Soporte para Rodrigo | Prometida 4 veces en 15 días; los datos fiscales se recapturaron | Días de espera | Factura automática al pagar cuando el perfil tiene datos fiscales; opción "quiero factura" en el checkout |
| 12 | **Mensaje de cierre de turno con folios, guías y contadores** | Beto (9 turnos), Nadia (6) | 1 por turno | Redactado a mano | Resumen automático del turno desde la bitácora (qué despachó, qué recibió, caja) visible para la gerente |
| 13 | **Verificar cada toast recargando o mirando la red** | Sofía | Casi todos sus turnos | 1–3 pasos extra por acción | Confirmaciones que muestran el dato guardado (folio, monto, estado nuevo) leído del servidor, no del formulario |
| 14 | **Subir la misma imagen en 3–4 formatos** | Sofía | 4 ocasiones | 3–4 cargas | Generar los derivados en el servidor desde una sola imagen |
| 15 | **Corregir a mano lo que el sistema no capturó**: patrocinio perdido, pago no acreditado, VP recalculados | Soporte | Rodrigo: "tres fallas críticas, las tres detectadas por el cliente, las tres corregidas a mano" | Horas de soporte por caso | Código de referido visible en carrito y checkout, no solo al final del registro; conciliación automática con la pasarela por webhook y reintento |

## 7. Propuestas, por impacto y esfuerzo

### 7.1 Rápidas (días o semanas, cambios acotados)

1. **Modo "solo cliente".** Todo comprador nace cliente: tienda, pedidos, rastreo, perfil. Red, VP, comisiones, CLABE y datos fiscales aparecen solo cuando pulsa "Quiero ser socia" (o cuando alguien se registra con su código). El aviso de privacidad se divide en dos. Resuelve la inquietud número uno de los clientes; es la única propuesta de esta lista que habría retenido a 5 prospectos.
2. **Plan publicado.** Una página "Cómo funciona" dentro del panel con porcentajes por generación, requisitos de activación y por generación, tabla de descuento por tramo, y PDF descargable. Quita la tarea 7 completa y la mitad de las consultas a soporte del helpdesk (48 filas mencionan activación, 35 los VP).
3. **Una sola tabla de descuento y VP** visible en panel, carrito y POS con el mismo vocabulario: tramo actual, siguiente tramo, cuánto falta, y "tus VP se cuentan sobre el precio con descuento" (hallazgos 1 y 4 de la ronda 4).
4. **CLABE al activarse.** Pedirla en el momento en que la socia cumple 20 VP la primera vez, y recordatorio automático en el panel y por correo desde que tiene comisión confirmada. "Acciones urgentes" separa "listas para depositar" de "sin CLABE".
5. **Completa tu activación.** Junto al aviso "llegas a 18.9 de 20 VP", el producto más barato que cierra la diferencia, con un botón para agregarlo.
6. **Envío visible desde la tienda.** Costo de envío y umbral de envío gratis medidos sobre el subtotal, o dicho en el carrito: "te faltan $19 después del descuento".
7. **Sesión persistente y último código válido.** "Recordarme" por 30 días en dispositivos propios; el correo de recuperación dice "usa el código más reciente" y el sistema lo acepta.
8. **Botones deshabilitados que explican por qué** (corte, retiro, pago parcial, devolución con candado), y un solo DOM para las tablas: una fila por registro, adaptada por CSS, para que "Ver" y los campos de archivo no se dupliquen.
9. **Sucursal por defecto del usuario.** El stock activo de Beto es Bodega Central; el de Nadia, Del Valle. Se guarda en el perfil del empleado.
10. **Sin `prompt()` ni `confirm()`.** Cantidades de transferencia, motivo de cancelación, monto de reembolso y motivo de reversa en modales con validación y el efecto escrito ("esto anula el comprobante y devuelve el mes a pendiente").
11. **Recoger en sucursal solo si hay sucursal en tu ciudad**, y con la existencia del producto comprobada antes de ofrecerla.

### 7.2 Medias (uno o dos meses)

12. **Pantalla "Pagos del mes"** (tarea 4): tabla de beneficiarios con monto, CLABE, estado; exportar archivo de dispersión bancaria; comprobante por lote; marcar pagados en bloque; deshacer por fila. Reduce el día de pago de 16 fichas a una pantalla.
13. **Despacho en bloque con lista de surtido** (tareas 1 y 2): seleccionar pedidos pagados, ver la suma por producto contra el stock, imprimir lista, capturar o importar guías, marcar todos como enviados.
14. **Suscripción mensual** (tarea 8): "recibe esto cada mes" con fecha, pausa y cancelación en un clic; la activación deja de depender de que la socia recuerde comprar el día 20.
15. **Seguimiento de hoy** para la coach (tareas 5 y 6): lista priorizada de clientes por días sin compra y sin contacto, con teléfono, patrocinador, último pedido y plantilla de WhatsApp que registra la nota al enviarse; excluye "No contactar" y compradores de otra ejecutiva.
16. **Arqueo de caja** (tarea 10): efectivo esperado contra contado en el corte, diferencia y destino del efectivo; retiro guiado con código.
17. **Factura automática** (tarea 11) al pagar cuando hay datos fiscales; "quiero factura" en el checkout para invitados.
18. **Devolución por producto y con evidencia según motivo**: elegir qué líneas se devuelven; una foto del paquete cerrado en desistimiento; plazo y medio de reembolso en pantalla y correo.
19. **Ficha unificada de cliente**: invitados y registrados con la misma ficha, origen (anuncio, código, tienda), preferencia de contacto y ejecutiva asignada; el patrocinador "FindingU" muestra nombre y WhatsApp de la coach.

### 7.3 Estructurales (un trimestre)

20. **Integración con la paquetería** (tarea 3): generación de guía desde el pedido, rastreo por webhook, entrega automática con firma y hora, correo "¿te llegó?" y cierre a N días. Elimina la tarea manual más frecuente de Beto y el silencio postcompra de §3.4.
21. **Conciliación automática con la pasarela**: webhook de pago con reintento y alerta cuando un pago aprobado no acreditó; adiós a "el dinero salió, los puntos no llegaron" (rodrigo-dia3).
22. **Política para las comisiones bloqueadas al cierre de mes.** Tres opciones para decidir en negocio, no en código: (a) periodo de gracia hasta el día 5 del mes siguiente para activarse y liberar lo bloqueado; (b) aviso el día 20 y el 27 con el monto que se perderá y el producto que lo salva; (c) las comisiones bloqueadas se pagan como saldo en tienda en lugar de perderse. Cualquiera de las tres evita otro caso Marcela; la (b) es la más barata y la (c) la que más retiene.
23. **Resumen automático de turno** (tarea 12) y **confirmaciones desde el servidor** (tarea 13): la bitácora ya tiene los datos; falta presentarlos.

## 8. Lo que no es software

Tres cosas se repiten en los diarios y no las arregla ninguna pantalla:

- **El plan exige gastar para cobrar.** "Marcela tiene que gastar $960 para poder cobrar $96" (rodrigo-dia5). Mientras la activación cueste diez veces la comisión típica de una socia nueva, la reputación de quien invita está en juego y nadie comparte su link.
- **La promesa "Gratis · Sin riesgo" contra la realidad de INE, CURP, constancia y CLABE.** Publicar la lista de lo que se pide y cuándo, y pedirlo solo cuando toca (propuesta 1), es tan importante como el modo cliente.
- **Soporte humano es lo que retiene.** Los tres clientes que se quedaron pese a los fallos lo atribuyen a Daniel y a Sofía: "lo que me hizo quedarme fue la manera en que soporte manejó los fallos" (lucia-dia3); "la gente de Finding'U responde rápido, admite el error y corrige. Su plataforma es la que va atrás de ellos" (veronica-dia1). Las automatizaciones del §6 deben liberar ese tiempo, no sustituir el contacto.

## 9. Contradicciones entre diarios

Sirven para no tomar un diario aislado como verdad:

- Registro obligatorio para pagar (Karla, Tomás) contra compra como invitado (Héctor, Rosa): depende de la puerta de entrada, no de la persona.
- Envío gratis por promoción aplicado a Lupita y cobrado a Bety en la misma semana.
- Precio de Klinhart anotado en $800 por Lucía y $480 por Rodrigo el mismo día.
- Rodrigo se corrigió a sí mismo sobre "la tienda redondea los puntos" (era el panel dividiendo entre 50), pero el diario de Marcela conserva la versión errónea que él le mandó.
- Beto narra dos veces la misma recepción del 3 de octubre con mecánica, hora y tipo de bitácora distintos.
- Sofía llama "el dueño" a Ricardo el 2 de octubre y el 7 dice que "nunca antes me habían escrito mencionando a un Ricardo".
- Beto cree que un pedido "se pagó y se entregó solo" el 13 de noviembre; ese día Nadia lo cobró y entregó en Del Valle.
- Patricia afirma el 12 de diciembre que "Ver resumen" no tenía campo de cupón y esa tarde lo usa ahí: entre ambas entradas se corrigió el bug.

## 10. Estado de las propuestas

La tercera columna se añadió después de la ronda de implementación ([23](23-implementacion-23-propuestas.md), rama `claude/ultimos-cambios-integrados-fylhiw` hasta `acca507`): 20 implementadas, 3 parciales.

| Propuesta | Estado al escribir este documento | Estado tras [23](23-implementacion-23-propuestas.md) | Origen en diarios |
|---|---|---|---|
| 1 Modo solo cliente | Sin empezar | **Implementado** (B; `fa1a386`, `72fedc3`) | 9 personas (§3.1) |
| 2 Plan publicado | Sin empezar (tabla de generaciones solo en registro) | **Implementado** sin PDF (B; `/#/modo-socio`, `GET /catalog/plan`) | 8 personas (§3.2) |
| 3 Tabla única descuento/VP | Parcial (aviso de VP en carrito) | **Implementado** (B, I1, I2; `ui-tabla-descuento` en panel, carrito y POS) | 6 personas |
| 4 CLABE al activarse | Parcial (CLABE obligatoria para pagar) | **Implementado** (A; aviso al activarse y con la primera comisión; CLABE desde la ficha en `acca507`) | Sofía, Claudia, Bety, Memo, Lupita |
| 5 Completa tu activación | Parcial (aviso sin sugerencia) | **Implementado** (C, I2; una sola fórmula para el carrito y el correo del día 20) | 5 socias |
| 6 Envío visible | Sin empezar | **Implementado** (C; envío gratis sobre el subtotal bruto) | 5 personas |
| 7 Sesión y último código | Sin empezar | **Implementado** (C, I2; Recordarme 30 días, enlace por correo, tres códigos vigentes, 401 → login con `?next=`) | 7 personas |
| 8 Botones mudos y DOM duplicado | Sin empezar | **Implementado** (E en el POS, I1 en el resto; `disabledReason`, un solo DOM) | Nadia, Ivonne, Sofía |
| 9 Sucursal por defecto | Sin empezar | **Implementado** (D; `defaultStockId` del empleado; sin bodega no se propone ninguna) | Beto ×3 turnos |
| 10 Modales en lugar de prompt | Sin empezar | **Implementado** (I1; `ui-confirm`, 0 `prompt/confirm` en `pages/admin`) | Beto, Sofía |
| 11 Recoger en sucursal condicionado | Parcial (motivo visible) | **Implementado** (C; falta capturar ciudad/estado en los almacenes existentes) | Claudia, Patricia |
| 12 Pagos del mes | Sin empezar | **Implementado** (A; Pagos del mes, CSV de dispersión, lote, deshacer, Pedir CLABE) | Sofía ×4 días de pago |
| 13 Despacho en bloque | Sin empezar | **Implementado** (D; `/#/admin/despacho`, lote `DSP-…`) | Beto ×9 turnos |
| 14 Suscripción | Sin empezar | **Implementado** sin cobro automático (H, I2; pedido + enlace de pago el día indicado) | Bety, Rosa, Patricia |
| 15 Seguimiento de hoy | Parcial (filtro fríos, CSV, notas) | **Implementado** (F; `/#/admin/seguimiento`, plantillas de WhatsApp con nota) | Ivonne ×5 turnos |
| 16 Arqueo de caja | Parcial (cambio en efectivo) | **Implementado** (E; arqueo en 4 pasos, retiro guiado, pago mixto) | Nadia, Paco |
| 17 Factura automática | Sin empezar | **Parcial** (C; datos fiscales y estado solicitada → emitida a mano; sin timbrado CFDI) | Rodrigo ×4 |
| 18 Devolución por producto | Parcial (cortesía, correo, sugerencia) | **Implementado** (G; líneas, evidencia por motivo, reembolso sugerido, plazo y medio) | Lupita, Patricia, Lucía |
| 19 Ficha unificada | Parcial (notas, no contactar, origen) | **Implementado** (F; campos en Seguimiento → Ficha, coach en el panel) | Ivonne, Sofía |
| 20 Paquetería integrada | Sin empezar | **Parcial** (D; adaptador Envia + simulada, rastreo por consulta, apagado por omisión; sin webhook ni tarea desplegada) | Beto, Sofía, 6 clientes |
| 21 Conciliación con pasarela | Sin empezar | **Implementado** (H; webhook con secreto e idempotencia, conciliación de 72 h) | Rodrigo, Lucía, Claudia |
| 22 Política de bloqueadas | Decisión de negocio pendiente | **Implementado** opción b (A; avisos días 20 y 27; opción a como `rewards.blockedGraceDays = 0`; tarea diaria sin desplegar) | Marcela, Verónica, Claudia, Bety |
| 23 Resumen de turno y confirmaciones | Sin empezar | **Implementado** (D, I1, I2; resumen de turno y confirmaciones desde el servidor) | Beto, Nadia, Sofía |
