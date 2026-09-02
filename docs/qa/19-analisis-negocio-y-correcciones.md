# 19 · Análisis a fondo del ejercicio, correcciones y propuestas de negocio

**Fecha:** 2 de septiembre de 2026. **Base:** `docs/qa/18-simulacion-multinivel.md`, `sim/helpdesk.md`, `sim/diarios/`.
**Rama:** `claude/ultimos-cambios-integrados-fylhiw`.

Este documento hace tres cosas: explica con el código en la mano lo que pasó con los $166 de Marcela (§1), analiza el ejercicio como negocio y no solo como software (§2–§4), y deja constancia de lo que se corrigió en esta segunda ronda y de lo que se ejerció con desencadenantes inducidos (§5–§6).

## 1. Los $166 de Marcela: qué pasó exactamente

Marcela no podía "desbloquear comprando" por cómo estaba escrito el motor, no por el plan. Paso a paso:

1. El 4 de septiembre Rodrigo (su referido) pagó $960. En ese instante el motor (`commissions_lambda.handle_apply_rewards`, acción `ORDER_PAID`) recorrió la línea ascendente de Rodrigo y, para cada ancestro, preguntó **"¿está activo ahora mismo?"** (`_generation_qualified` → `_is_active` → `_calc_vp(mes) >= 20`). Marcela llevaba 0 VP ese día. Resultado: fila `{orderId: ORD-B49F8F4D, amount: 96, status: "blocked", reason: "no_califica_gen"}` en su ledger de septiembre. Con compresión dinámica, la generación pasa al siguiente ancestro calificado; Marcela no tiene patrocinador, así que nadie la cobró.
2. El 6 de septiembre Patricia pagó $700 → segunda fila bloqueada de $70. Total bloqueado: $166, exactamente lo que su panel mostraba.
3. **Nada volvía a leer una fila bloqueada.** Los únicos cambios de estado que existían eran `pending → confirmed` al entregarse el pedido (`handle_confirm_commissions`) y el borrado por cancelación o devolución (`_void_ledger_rows_for_order`). El cierre de mes no evaluaba nada; el pago del día 10 solo toma `totalConfirmed`.
4. Por tanto, si Marcela hubiera comprado sus 20 VP el 20 de septiembre, habría quedado activa **para los pedidos que sus referidos pagaran a partir del 20**, y las dos filas de $96 y $70 habrían seguido `blocked` hasta desaparecer del panel el 1 de octubre. Eso es lo que soporte le dijo, y era verdad para el código de ese momento.

Lo que dice el plan (abril 2026 §4) es que la comisión exige "estar activo en el mes". El código implementaba "estar activo en el segundo en que paga el referido", que es otra regla, más dura, y que además nadie explica en pantalla. El efecto de negocio se vio en vivo: Marcela se fue al leerlo ("mecanismo de retención que no es ético"), y Andrés lo usó como argumento decisivo para no entrar.

**Corrección aplicada (commit `958dcda`).** Al activarse un socio dentro del mes, el motor recalcula todas las órdenes del mes que dejaron filas bloqueadas en su ledger y en el de su línea ascendente (cuyos requisitos de "directos activos" pudieron cambiar con esa activación): borra las filas de cada orden en toda la cadena, vuelve a repartir con la situación actual y, si el pedido ya se entregó, deja las nuevas filas como `confirmed`. Es configurable (`rewards.reevaluateBlockedOnActivation`, por omisión encendido) porque es una decisión de negocio: con ella, "compra tus 20 PC para cobrar lo que tu red ya generó este mes" vuelve a ser cierto. Cuatro pruebas de regresión lo cubren (`tests/test_reevaluacion_bloqueadas.py`).

Lo que sigue siendo cierto y hay que decir en pantalla: al cerrar el mes, lo bloqueado se pierde. Es la regla del plan; lo inaceptable era que no existiera en ningún texto.

## 2. El embudo, con las personas del ejercicio

| Etapa | Personas | Qué pasó |
|---|---|---|
| Llegan | 9 prospectos + 1 socia existente | 7 venían por un producto, 2 por el negocio |
| Se registran | 7 de 9 | Karla, Tomás, Patricia, Andrés, Rosa Elena, Iván, Rodrigo. Lucía y Héctor compran o intentan como invitados |
| Compran | 5 (+2 en mostrador) | Lucía $800, Rodrigo $960, Patricia $829, Rosa Elena $829, Guadalupe $560; Rodrigo otros $480 en tienda física |
| Se activan (20 VP) | 1 | Rodrigo. Nadie más llega a $960 de compra personal |
| Recompran | 0 | Rodrigo "tengo omega para dos meses"; Patricia buscaría en farmacia; Rosa Elena sí, pero olvidó la contraseña |
| Construyen red | 0 | Marcela cierra; Rodrigo no invita; Andrés e Iván piden borrar sus datos |
| Cobran comisión | 0 | $0 depositados en septiembre |
| Piden no ser contactados o baja | 4 + 3 | Karla, Iván, Andrés, Héctor / Andrés, Iván, Marcela |

Tres lecturas:

- **La tienda vende; la red ahuyenta.** Los que compraron lo hicieron a pesar del panel de distribuidor, no gracias a él. Los que se fueron sin comprar (Karla, Tomás, Iván, Héctor) se fueron en el momento en que la plataforma les habló de red, puntos o comisiones.
- **Nadie recompra porque nadie se lo pide.** Sin correos, sin recordatorio de consumo, sin suscripción, la segunda compra depende de que el cliente recuerde la URL y su contraseña. Rosa Elena quiso recomprar y la contraseña la detuvo.
- **El negocio no se puede evaluar desde dentro.** Los dos perfiles con intención de construir tuvieron que obtener el plan por WhatsApp. Cuando lo tuvieron, hicieron cuentas y no les salió.

## 3. La economía del plan, con los números de la configuración

Datos de `core/config.py`: activación 20 PC ≈ $960–1,000; descuentos 10/20/30/40% a partir de $1,000/2,000/3,000/6,000; comisiones 10/5/4/3/2% por generación con requisitos crecientes; comisiones bloqueadas si el patrocinador no está activo; corte mensual sin arrastre.

**Punto de equilibrio del socio (la cuenta de Andrés, verificada).** Para cobrar necesita poner $918–1,000 al mes. La comisión de primera generación es 10% del neto de sus directos. Para recuperar $918 necesita $9,180 de compra mensual en sus directos: unos 10 Rodrigos activos, cada mes. Con la conversión observada (4 reclutados → 1 activo), unas 40 personas reclutadas. Eso, solo para no perder dinero; la segunda generación paga la mitad y exige más.

**El hoyo de precio.** Los 20 PC más baratos cuestan $960 (2 Klinhart) y no alcanzan el escalón de $1,000 del 10%. El carrito de $1,020 con 10% sale en $918. Quien optimiza al mínimo paga más y se lleva menos; el que descubre el truco desconfía del resto (Andrés).

**Qué gana el comprador de producto al registrarse: nada.** Iván lo comprobó: el "descuento en tu primera compra" del formulario fue $0, porque el descuento empieza en $1,000 acumulados. El registro le costó su correo, su teléfono y una llamada de una coach.

**Qué gana la empresa por cada activación de $960:** una venta que probablemente no se repetiría (Rodrigo compró dos meses de omega para cumplir 20 PC) y, con la regla vieja, una comisión que no pagó a nadie. Con la regla nueva paga $96 a Marcela y conserva a Marcela.

## 4. Propuestas de negocio, en orden de impacto

1. **Separar los dos productos.** Un modo "cliente" por defecto para quien llega por un producto: tienda, pedidos, perfil, recompra y, si quiere, un código de amigo que le da crédito en tienda. El modo "socio" se activa a petición, con el plan leído y aceptado. Nueve de cada diez llegadas del ejercicio eran clientes; hoy todos aterrizan en el panel de socio.
2. **Publicar el plan completo** en la landing y dentro del panel: niveles, porcentajes, requisitos, escalones, activación, y una frase honesta sobre bloqueo y cierre de mes. Hoy vive en `core/config.py`. Es texto; cuesta una tarde.
3. **Activación por consumo, no por calendario.** Alternativas que respetan el espíritu del plan y no obligan a comprar dos meses de omega: activación con 20 PC en una ventana móvil de 60 días, o autoenvío mensual de 10 PC que cuenta doble. Rodrigo lo dijo: "el plan está amarrado al calendario, no a lo que consumes".
4. **Regla de bloqueo explícita y humana.** Ya se recalcula al activarse en el mes (§1). Falta decidir y publicar si lo bloqueado al cierre se pierde (como hoy) o se paga si el socio se activa en los primeros N días del mes siguiente.
5. **Arreglar el escalón de $1,000.** Bajar el primer escalón a $950 o subir la activación a $1,000 exactos, para que "20 PC" y "10%" coincidan. Y que el carrito diga "te faltan $40 para el 10%" cuando el cliente esté a $40.
6. **Ficha de producto real.** Tabla nutrimental, porciones, ingredientes, sabor, certificaciones, comparativa. Iván y Héctor se fueron a la farmacia por esto; la coach no pudo ayudar porque tampoco lo tenía.
7. **Correos y avisos del pedido** (ya implementados en esta ronda) y un aviso de retraso a los 3 días sin envío. Trece días de silencio se convirtieron en "me metieron en un MLM".
8. **Recompra fácil.** Botón "volver a pedir" en el correo de entrega, recordatorio a los 25 días según la duración del producto, y suscripción con descuento. Cero recompras en un mes no es un problema de producto: el colágeno "sí funcionó" (Patricia, Rosa Elena).
9. **Seguimiento humano con registro.** Lo que retuvo a Lucía y a Rosa Elena fue una persona; lo que espantó a Karla e Iván fue una persona sin contexto. La ficha tiene ahora origen, no contactar y bitácora (esta ronda); falta que la coach vea una lista de "fríos" y no abra siete fichas a mano.
10. **Cumplimiento.** Baja de datos (implementada esta ronda), aviso de privacidad para clientes que no habla de "red de afiliados", y opt-in explícito para contacto de coach.
11. **Logística visible.** Quién genera la guía y desde dónde; guía de retorno; reembolso con envío de regreso (implementado); alerta de devolución parada; estado "reembolso en trámite".
12. **Una sola regla de descuento** en tienda y mostrador (corregido esta ronda) y un POS que calcule el cambio (corregido).
13. **La siguiente meta no debe ser reclutar.** A una compradora recién activada el sistema le pone "Agregar un nuevo miembro a la red"; a una socia con dos directas inactivas le pide "Completar consumo" en vez de activarlas. Las metas deben seguir al perfil: consumo y recompra para el cliente; activar a sus directas para la socia. Lo dijo la socia con más experiencia del ejercicio: "una persona que de verdad se tome el producto vale más que tres de compromiso".
14. **Decir el tamaño real.** "9 cuentas, 3 activas" retuvo a la única líder del ejercicio precisamente porque nadie se lo había dicho en seis años de venta directa. Un Top 10 con siete ceros lo dice solo, y peor.
15. **Cupones y puntos, con regla explícita.** El VP se calcula sobre el neto, así que un cupón recorta puntos y puede dejar a alguien "activa por un cuarto de punto". Ya se muestra en el carrito; falta decidir si los cupones de marketing deben contar como neto (hoy sí) o excluirse del cálculo de VP.
16. **Costo por punto visible** (ya en cada tarjeta): activarse con creatina cuesta 55% más que con Naplus para el mismo objetivo; quien no lo ve se siente estafado después.

## 5. Corregido en esta ronda

| Síntoma | Corrección | Commit |
|---|---|---|
| Comisiones bloqueadas que nunca se reevaluaban (§1) | Recalcular al activarse en el mes; configurable | `958dcda` |
| El POS mostraba "alcanzó meta 10%" y cobraba 0% | Se envía el descuento del escalón; misma regla que la web | `958dcda` |
| El POS no pedía dinero recibido ni calculaba cambio | Campo "Efectivo recibido", cambio o faltante | `958dcda` |
| Ningún correo de pedido; el pedido de invitado ni guardaba el correo | Correos de pago, envío (con guía), entrega, devolución recibida/aprobada/rechazada, reembolso y cancelación | `b07c264` |
| Sin "no contactar", notas ni origen; sin baja de datos | Ficha con seguimiento y bitácora; `DELETE /customers/{id}` anonimiza, cierra acceso y confirma por correo | `2f77b77` |
| Reembolso sin envío de regreso ni importe editable | El cliente declara el costo; el reembolso lo suma; la gerente ajusta | `a2599cd` |
| Septiembre desaparecía del panel el 1 de octubre | Selector de mes en Comisiones | `a2599cd` |
| Tooltip de "Bloqueadas" explicaba otra cosa | Texto correcto | `a2599cd` |
| Cupones inalcanzables en producción (`/coupons` sin ruta en API Gateway) | Enrutar bajo `/orders/coupons` | `9f53324` |

**Encontrado y corregido durante el ejercicio inducido (§6–§7):**

| Síntoma vivido | Corrección | Commit |
|---|---|---|
| La pasarela cobraba precio de lista sin el descuento del socio ($1,137 en pantalla, $1,249 cobrados) | Precios unitarios con el descuento del pedido, residuo ajustado al centavo | `3cc4474` |
| Cupones inalcanzables en producción (`/coupons` sin ruta en API Gateway) | Enrutar bajo `/orders/coupons` | `9f53324` |
| Recibir una transferencia estaba roto de raíz (nunca pasaba el id) y solo admitía confirmar todo tal cual | Recepción con cantidades reales; faltante como merma en el origen | `37f5225` |
| El comprador sin cuenta nunca dejaba correo | Campo obligatorio para invitados | `693a675` |
| Una venta de mostrador ligada a una cuenta que no la reconocía; sin forma de anular; cancelar no restaba volumen | Anulación con motivo, aviso al titular, volumen restado una sola vez | `533379a` |
| El icono de carrito del encabezado agregaba otra unidad (dos personas pagaron dos frascos) | Abre el carrito | `ea0aa3c`, `235077b` |
| El carrito proyectaba VP brutos; el motor acredita netos (cupón incluido) | VP del pedido visibles, con aviso si el cupón deja abajo de la meta | `3cc4474`, `89c59a4`, `51778c7` |
| Corte de caja y retiro de efectivo con "Internal Inventory Error" | Importes en Decimal | `13ce46f`, `b2066b0` |
| Diálogos del POS que no refrescaban (tres ventas fantasma) | Refresco de vista tras validar y aplicar | `44cf759`, `04131dc` |
| Ningún empleado podía cambiar su contraseña; el POS bloqueaba sin decir quién resuelve | Botón "Contraseña"; mensaje con el camino | `5655e78` |
| El Cuadro de Honor del cliente siempre vacío; el del socio con nombres completos ajenos y bajas | Carga desde su endpoint; nombre e inicial; sin bajas | `738bdbf`, `51778c7` |
| Renombrar categoría duplicaba; eliminar borraba la equivocada | Actualizar el registro existente | `c44a8e6` |
| El día de pago la gerente veía $0 en todas las fichas con $250.74 confirmados | La lista trae las comisiones del mes y del anterior; "por depositar" correcto | `acd0aba`, `6d51479` |
| Requisitos por generación y regla de corte fuera del plan público | Configuración pública completa y texto en la landing | `6289bc9`, `89c59a4` |
| Importes con centavos ocultos ($1,376 vs $1,376.40 en la pasarela) | Centavos cuando existen | `83bff5d`, `d3cf590` |
| Sin correo al cambiar contraseña, al comprar alguien de tu red, ni al depositar | Los tres correos | `533379a`, `51778c7`, `6ba72b1` |
| Pedido cerrado sin dónde anotar; apellido materno obligatorio | Notas internas en cualquier pedido; apellido materno opcional | `976d964` |
| Reembolso ciego al envío de regreso; septiembre desaparecía del panel | Importe editable con envío de regreso; selector de mes | `a2599cd` |

Suite: de 109 a **133 casos**, todos en verde. Cada corrección lleva su regresión con el síntoma en la docstring.

## 6. Rutas nunca tocadas: clasificación y ejercicio inducido

De las 36 rutas que ningún journey orgánico alcanzó:

**Muertas (el frontend las declara pero ningún componente las llama, y API Gateway no las enruta):** `GET /admin/dashboard`, `GET /cart`, `GET /user-dashboard`, `POST /assets`, `POST /verify-email` (solo como respaldo del `/auth/verify-email`). Candidatas a borrarse del cliente.

**Vivas sin desencadenante en un mes de vida real:** alta y privilegios de empleados, restablecer contraseña de empleado, transferencias entre almacenes y su recepción, retiros y código de autorización POS, cupones, campañas y activos, categorías, activos y baja de productos, alta manual de cliente, documentos y perfil del cliente, recuperación y cambio de contraseña, notificaciones leídas, solicitud y comprobantes de pago de comisiones.

Para ejercerlas se indujeron desencadenantes realistas, no acciones: el dueño manda a la gerente una lista de encargos (contratar cajera, abrir segundo almacén, cupón de octubre, campaña, categoría, baja de producto, código de caja, altas y bajas de clientes); una socia con experiencia en venta directa evalúa el plan y, si le convence, trae a dos amigas; una clienta quiere recomprar y no recuerda su contraseña; un cliente recibe la petición de subir su constancia fiscal para facturar; el cajero hace un retiro de efectivo y aplica un descuento autorizado; el almacén recibe la transferencia. Los resultados y la cobertura final están en §7.

## 7. Resultado del ejercicio inducido

Segunda fase (2 de octubre → 10 de noviembre simulados): 8 personas más en turno (Verónica, Claudia, Bety, Nadia, más los turnos nuevos de Sofía, Beto, Paco, Ivonne y Rodrigo), 37 turnos, 12,267 peticiones acumuladas, 106 filas en la bitácora de soporte, 54 diarios.

**Lo que se ejerció y qué salió:**

- **Empleados:** alta de cajera con permisos limitados, reseteo de contraseña, cambio de contraseña propio (no existía), vínculo a almacén (el POS bloqueaba sin decir cómo resolverlo).
- **Inventario:** segundo almacén, transferencia y recepción con faltante (la recepción estaba rota de raíz), retiro de efectivo con código, descuento autorizado, ventas anuladas, corte semanal.
- **Catálogo:** categoría (editar duplicaba), foto de producto, producto retirado, producto del mes, campaña con imagen, cupón creado, usado por una clienta (recortaba VP sin avisar) y desactivado.
- **Clientes:** alta manual, no contactar, origen, bitácora, dos bajas ARCO, documento fiscal subido por el cliente, notas en pedidos cerrados.
- **Comisiones:** una socia con dos directas activas: pendiente → confirmada al entregar → pagada el 10 del mes siguiente con comprobante y correo. Nadie había cobrado en el primer mes; la gerente no pudo pagar el 10 de octubre porque su ficha decía $0.
- **Recuperación de acceso:** una clienta recuperó su contraseña por correo con código; otra descubrió que nunca tuvo cuenta.

**Cobertura final:** 62 de 82 rutas según `sim/cobertura.py`, más 7 que el cruce literal no empareja por la query string (`customers/getall`, `cash-control`, `cash-cuts`, `pos/sales`, `stocks/movements`, `stocks/transfers`, `orders/find`): **69 de 82 ejercidas**. De las 13 restantes, 5 están muertas (`/admin/dashboard`, `/cart`, `/user-dashboard`, `/assets`, `/verify-email`: ningún componente las llama y API Gateway no las enruta) y 8 siguen vivas sin uso: editar empleado, reenviar confirmación de correo, borrar producto definitivamente (existe dentro de "Editar producto", nadie lo encontró), privilegios y documentos de cliente desde el back office (ídem), marcar aviso leído (se marca al abrir el centro), y las dos rutas de comisiones que el panel no expone (`/commissions/request`, `/commissions/receipt`): el depósito es automático con CLABE, así que sobran o falta el flujo que las use.

**Método, lo que se aprendió:** tres reportes de agentes de bajo costo en sesiones largas resultaron inventados o erróneos (una recepción "hecha", un descuento "que no aplica", un botón "que no responde"); los tres se contrastaron con la API o se reprodujeron con el arnés antes de contarse, y se repitieron los turnos con otro agente. Toda afirmación de "quedó" en este documento está verificada contra el backend.

VEREDICTO_PENDIENTE
