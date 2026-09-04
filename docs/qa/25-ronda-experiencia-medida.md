# 25 · Sexta ronda (corrida buena): cuánto cuesta usarlo y cómo se siente

> **Dos líneas de contexto.** Una primera corrida de esta misma ronda ([24](24-ronda-experiencia-y-esfuerzo.md)) se ejecutó por error con el frontend apuntando a la API de producción en AWS y sin backend detrás: sus cifras de esfuerzo, facilidad, confianza y emoción **no son atribuibles al producto** y quedó marcada como anulada.
> Esta corrida es la buena: el mundo se verificó con `sim/comprobar.sh` antes de empezar (backend local en `:4400`, bundle sin AWS, catálogo sembrado) y las doce personas trabajaron contra el producto de verdad. Donde un hallazgo del [24] se confirma aquí, se dice; donde desaparece, también, porque era del entorno.

Las rondas 18 a 21 preguntaron *¿funciona?*. La [22](22-diarios-inquietudes-friccion-automatizacion.md) preguntó *¿qué les preocupa?* y la [23](23-implementacion-23-propuestas.md) construyó 23 propuestas. Esta ronda pregunta otra cosa: **cuánto le cuesta a una persona sacar adelante lo que vino a hacer, y cómo se siente mientras lo hace.**

Doce personas trabajaron con la plataforma entre el 2 de marzo y el 10 de abril de 2027 del mundo simulado: siete de fuera (clientas, prospectas y socias) y cinco del personal. Ninguna había visto el producto antes, ninguna leyó código, y cada una escribió su diario al terminar (`sim/diarios/`, 12 archivos). El arnés contó por su lado clics, teclas, pantallas, recargas y milisegundos de lectura antes del primer clic; la persona registró a mano lo que pensaba, lo que dudaba, dónde se atoró, qué sintió y con qué intensidad (`sim/metricas/*.json`). Las 27 preguntas que no pudo contestar la pantalla quedaron en `sim/helpdesk.md` con la respuesta de soporte, de la gerente o de la patrocinadora. Una verificación posterior revisó cada síntoma contra el código y contra la API, y clasificó los 49 hallazgos en **confirmada** (38), **percepción** (7) y **dato o arnés** (4).

Todo lo que aquí se afirma se puede reproducir: `bash sim/comprobar.sh`, `python3 sim/metricas.py --markdown` y `python3 sim/cobertura.py`.

---

## 1. Resumen ejecutivo

| | |
|---|---|
| **Personas** | 12 · 7 de fuera (Mariana, Ernesto, Ximena, Julio, Aurora, Fabiola, Paulina) y 5 del personal (Mireya, Toño, Gaby, Renata, Alma) |
| **Tiempo** | 212 minutos de sesión sumados; 188 min de tarea cronometrada |
| **Tareas** | **126 intentadas, 82 logradas (65 %)**. Clientes: 60 intentadas, 34 logradas (**57 %**). Personal: 66 intentadas, 48 logradas (**73 %**) |
| **Clics por tarea lograda** | **Mediana 3.** 411 clics en toda la ronda. El producto no cuesta clics: cuesta lectura |
| **Segundos de reflexión antes de actuar** | **11,897 s = 3 h 18 min**, más que los 188 min de tarea cronometrada. La gente pasa más tiempo entendiendo la pantalla que operándola |
| **Lectura antes del primer clic** | 22.2 min repartidos en 48 llegadas a pantalla. Mediana por pantalla: `#/landing/PAULINA-PR` 43 s, `#/tienda` 33 s, `#/login` 25 s, `#/admin` 16 s, `#/dashboard` 14 s, `#/orden/:id` 3 s |
| **Tareas sin un solo clic** | **35 de 126**; 19 terminaron en fracaso. La persona leyó, no encontró por dónde, y se fue |
| **Preguntas que la plataforma debió responder sola** | **27** (14 a soporte, 8 a un superior, 3 a la patrocinadora, 2 a un familiar) · 27 filas en `sim/helpdesk.md`. **11 de las 27 ya tenían respuesta en pantalla**; 6 son decisiones de negocio; las otras 10 destaparon huecos reales |
| **Facilidad media** | **3.6 / 7** (1 difícil – 7 fácil) · clientes 3.5, personal 4.0. Por persona: Gaby 4.6 y Toño 4.4 arriba; Paulina 2.4 y Mireya 3.2 abajo |
| **Confianza en que quedó guardado** | **3.9 / 5** · Alma 3.2, Renata 3.3, Aurora 3.0 abajo; Gaby 4.5, Toño 4.5 arriba |
| **Estética** | primera impresión **6.2 / 10**, legibilidad **6.3**, confianza que transmite **4.8**, **coherencia 3.8** (la nota más baja de todas), recomendaría **5.2 / 10**, sensación en celular **5.0** (3 personas) |
| **Emociones registradas** | 140. **Desconfianza 31, alivio 26, frustración 24, enojo 14, orgullo 6, vergüenza 4.** 15 registros de intensidad 5 (la máxima); 7 de esos 15 son de la CLABE |
| **Atorones / reintentos / recargas** | 92 / 47 / 8 |
| **Verificación** | 49 hallazgos: **38 confirmadas** (7 críticas, 14 altas, 13 medias, 4 bajas), 7 percepciones (existía y no se halló), 4 datos o arnés |
| **Cobertura** | `sim/cobertura.py`: 79 rutas declaradas, **42 alcanzadas, 37 nunca tocadas**; además 20 rutas de los servicios por paquete que el script no reconoce (`/inventory/turno/resumen` 337 veces, `/orders/checkout/envio-info` 63, `/catalog/plan` 61, `/orders/checkout/sucursales-recoger` 37, `/commissions/pagos` 30, `/inventory/pos/arqueo` 27, `/customers/seguimiento/hoy` 21) |

### Las tres conclusiones que cambiarían el producto

**1. El costo no está en los clics, está en la lectura.** La mediana de una tarea lograda son tres clics, y aun así la gente gastó 3 h 18 min pensando antes de mover el dedo: más que el tiempo cronometrado de tarea. Y 35 de 126 tareas no tuvieron ni un clic —19 de ellas fracasaron— porque la persona leyó la pantalla y no encontró por dónde. El impuesto se paga en vocabulario que nadie tradujo (PC, VP, VG, "Corte en 26d 19h", "Mínimo requerido" sin número, "Estado: paid", "mixed", "2027-03-02T11:18:04Z") y en pantallas que no repiten lo que la persona acaba de elegir. Ernesto Vidal, contador jubilado de 63 años: *"Yo fui contador toda mi vida y no le entiendo a los VP ni a los PC"* (`ernesto-2027-03-02.md`).

**2. Lo que la ronda 5 construyó funciona, y casi nadie lo encuentra.** De las funciones nuevas de la [23], las que se alcanzaron esta ronda fueron las mejor calificadas de todo el producto —Despacho en bloque, el arqueo por pasos, Seguimiento de hoy, la sugerencia de activación del carrito, la página del plan— y **cinco de ellas están fuera del menú**. Comisiones y pagos vive al fondo de la ficha de un cliente que no tiene comisiones (Alma la buscó siete veces en el menú antes de caer ahí de rebote por una alerta); "Recibe esto cada mes" está en el último renglón del panel, debajo de trece productos; Seguimiento de hoy se alcanza por un botón encima de una tabla dentro de Clientes; Despacho en bloque, por un botón entre las pestañas de estado de Pedidos; y `#/modo-socio` —la mejor pantalla de la ronda para cuatro personas y elogiada por seis— cuelga de *"un renglón chiquito y gris"* (`paulina-rios-2027-03-20.md`). Toño Vera lo dijo en una línea: *"es la mejor pantalla del sistema y está escondida atrás de un botón entre las pestañas de estado"* (`tono-2027-03-03.md`). La ronda 6 no encontró que falte producto: encontró que **falta arquitectura de información**.

**3. Un solo defecto silencioso vació el mes de dinero.** La CLABE no se guarda: entre Paulina y Fabiola hubo **diez intentos en dos pantallas distintas y en tres días distintos**, sin un mensaje de éxito ni de error, y la verificación comprobó que **el navegador nunca mandó nada al servidor** (el backend sí funciona: un POST directo devolvió `200 {ok:true, clabeLast4:6789}`). Río abajo, ese defecto produjo el cierre de marzo: Renata y Alma no pudieron exportar el archivo del banco, marzo se cerró con **$0.00 depositados**, y las dos personas que más dinero mueven en la empresa terminaron el día 10 mandando WhatsApps. Siete de los quince registros de emoción de intensidad máxima de toda la ronda son de esto. Paulina: *"Tres intentos, dos pantallas, cero mensajes"* (`paulina-rios-2027-03-20.md`).

---

## 2. El costo de cada cosa

### 2.1 Las tareas más caras

Ordenadas por segundos de reloj. "Reflexión" es lo que la persona pasó pensando antes de actuar, medido sobre su propia línea de tiempo (puede desbordar el reloj de la tarea cuando el pensamiento arranca antes de que la tarea empiece).

| Persona | Qué quería | Clics | Seg | Reflexión (s) | Atorones | Reintentos | ¿Logró? | Facilidad |
|---|---|---|---|---|---|---|---|---|
| Renata Bustos | ver qué hay que pagar de marzo 2027 y a quién | 8 | 501 | 501 | 4 | 3 | sí | 2 |
| Ernesto Vidal | volver a buscar dónde repetir el pedido cada mes | 7 | 398 | 398 | 5 | 1 | **no** | 2 |
| Fabiola Cantú | mandarle mi link a mis clientas del salón | 0 | 348 | 403 | 0 | 0 | sí | 3 |
| Julio Herrera | devolver **solo** la proteína, que llegó estrellada | 17 | 341 | 369 | 8 | 5 | **no** | 1 |
| Ernesto Vidal | comprar mi frasco de omega 3 y pagarlo | 11 | 312 | 333 | 0 | 0 | sí | 4 |
| Mireya Solano | entregar el pedido de internet a la señora que vino por él | 13 | 293 | 295 | 3 | 1 | sí | 2 |
| Mireya Solano | cerrar mi caja y entregar el dinero del día | 19 | 281 | 303 | 2 | 1 | sí | 3 |
| Fabiola Cantú | volver a intentar guardar mi CLABE desde el correo | 8 | 261 | 206 | 3 | 2 | **no** | 1 |
| Paulina Ríos | comprar lo necesario para activarme y no perder $259.20 | 13 | 246 | 268 | 1 | 0 | sí | 4 |
| Paulina Ríos | registrar mi CLABE para que me puedan depositar | 6 | 244 | 253 | 4 | 3 | **no** | 1 |
| Paulina Ríos | ver cuánto tengo por cobrar y por qué está bloqueado | 5 | 233 | 238 | 1 | 0 | sí | 2 |
| Ximena Paredes | saber si el 10 % se calcula sobre lista o sobre lo pagado | 2 | 218 | 218 | 3 | 1 | **no** | 2 |
| Fabiola Cantú | armar una compra que me deje activa y me dé descuento | 7 | 208 | 230 | 0 | 0 | sí | 6 |
| Ernesto Vidal | agregar el omega 3 al carrito | 2 | 205 | 161 | 4 | 2 | sí | 3 |
| Alma Rentería | sacar cuánto entró en marzo y por qué vía | 0 | 184 | 179 | 1 | 1 | **no** | — |
| Aurora Vega | entrar a la tienda y ver si puedo comprar dos suplementos | 0 | 177 | 194 | 1 | 1 | **no** | — |
| Renata Bustos | reconstruir a mano cómo cerró marzo | 9 | 177 | 177 | 1 | 1 | sí | 3 |
| Mariana Robles | saber cuánto cuesta con envío antes de dar mis datos | 8 | 154 | 137 | 3 | 1 | **no** | 2 |

Lo que se lee en esta tabla: **las tareas caras no son las complicadas, son las que no tienen pantalla**. Renata tardó 501 segundos en contestar "¿a quién le pagamos de marzo?" no porque la tabla de pagos sea difícil, sino porque no está en el menú y, al recargar, pierde el mes. Ernesto gastó casi siete minutos buscando por segunda vez una función que ya había encontrado. Julio hizo 17 clics y visitó nueve pantallas para no devolver una proteína rota, mientras la pantalla que necesitaba existía y estaba a un estado de distancia.

Y hay el reverso: cuando la pantalla está pensada, el costo se desploma. Fabiola armó su compra de activación en 208 s con **cero atorones y cero reintentos**, y le puso facilidad 6 de 7: *"Compré $1,100 pensando que con eso me activaba, y el carrito me dijo: 'llegas a 18.9 de 20 VP, te faltarían 1.1'. Si no me lo dice, pago y me quedo sin activar el mes sin enterarme"* (`fabiola-2027-03-04.md`). Toño despachó tres pedidos en 82 s con facilidad 6.

### 2.2 El impuesto de comprensión: dónde se fue el tiempo de lectura

El arnés cronometra los milisegundos entre que una pantalla carga y el primer clic de la persona. En 48 llegadas se acumularon **22.2 minutos de puro leer sin tocar nada**.

| Pantalla | Llegadas | Mediana antes del primer clic | Máximo | Qué estaban leyendo |
|---|---|---|---|---|
| `#/` (portada) | 2 | **50 s** | 63 s | Qué venden, y si esto es una tienda o un negocio |
| `#/dashboard#comisiones` | 2 | **47 s** | 63 s | Por qué dice $0 si el correo dice $259.20 |
| `#/landing/PAULINA-PR` | 4 | **43 s** | 72 s | Cuatro promesas sin un solo porcentaje |
| `#/admin/seguimiento` | 1 | 37 s | 37 s | La única pantalla que Gaby leyó entera y con gusto |
| `#/tienda` | 4 | **33 s** | 39 s | Trece nombres de marca sin decir qué es cada cosa |
| `#/login` | 5 | 25 s | 31 s | "LOGIN — Accede a tu panel": *"¿qué es un panel?"* |
| `#/verificar-email` | 2 | 25 s | 25 s | — |
| `#/admin` | 9 | 16 s | 65 s | Nueve pestañas y un menú donde no está su trabajo |
| `#/carrito` | 2 | 16 s | 16 s | El bloque de descuento y activación |
| `#/dashboard` | 14 | **14 s** | 96 s | Metas, VP, reloj de corte, tienda y red apilados |
| `#/orden/:id` | 2 | **3 s** | 3 s | No hay nada que leer: un folio y un total |

Tres lecturas de esta tabla:

1. **Las pantallas públicas son las más caras de leer.** Portada, landing y tienda están entre las cuatro medianas más altas. Es lo primero que ve una persona que no conoce el producto, y es donde el vocabulario no está traducido. Ernesto tuvo que leerse los trece nombres uno por uno buscando "omega 3": *"Ninguno se llama omega 3… para hallar mi omega 3 tengo que leerme los trece, y yo veo poco de cerca"* (`ernesto-2027-03-02.md`).
2. **`#/orden/:id` cuesta 3 segundos porque no dice nada.** Es la mediana más baja de la ronda y no es una virtud: el recibo de una compra de $1,500 no lista productos, ni la sucursal elegida, ni la factura pedida. Aurora: *"No dice «sucursal». No dice «Guadalajara». No dice «factura». No dice ni qué compré. Es un recibo de un número."* (`aurora-vega-2027-03-04.md`).
3. **El impuesto se paga aunque la información esté.** En 11 de las 27 preguntas la respuesta estaba en pantalla (§4.1). Lo que falla no es la existencia del dato: es el orden en que aparece y el nombre que lleva.

Un cuarto dato, que no es lectura de pantalla sino aritmética a mano: **Ximena Paredes hizo 16 tareas y 10 de ellas sin un solo clic**. Se pasó la sesión con lápiz y papel calculando el $/PC de cada producto para decidir si el negocio le convenía, porque la plataforma publica el plan pero no publica ganancias reales. Sacó que el PC va de $46.67 a $72.22 —55 % de diferencia— y que el *"más o menos $1,000"* que promete la página de activación en realidad va de $933 a $1,605.

### 2.3 Costo por persona

| Persona | Rol | Disp. | Min | Tareas | Logradas | Clics | Refl. (s) | Sin clic | Atorones | Reint. | Facilidad | Confianza |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Toño Vera, 31 | almacén | escritorio | 15 | 17 | **14 (82 %)** | 31 | 783 | 2 | 3 | 2 | 4.4 | 4.5 |
| Gaby Ledesma, 33 | coach | escritorio | 15 | 14 | **11 (79 %)** | 39 | 914 | 1 | 4 | 3 | **4.6** | 4.5 |
| Renata Bustos, 38 | gerencia | escritorio | 26 | 13 | 10 (77 %) | 37 | 1,462 | 1 | 7 | 6 | 3.4 | 3.3 |
| Fabiola Cantú, 41 | socia nueva | escritorio | 22 | 9 | 7 (78 %) | 28 | 1,286 | 2 | 8 | 4 | 4.1 | 4.4 |
| Ernesto Vidal, 63 | cliente | **celular** | 28 | 8 | 6 (75 %) | 42 | **1,535** | 1 | **14** | 4 | 3.0 | 3.7 |
| Mariana Robles, 29 | clienta | celular | 9 | 6 | 4 (67 %) | 13 | 465 | 3 | 4 | 2 | 4.0 | 3.5 |
| Mireya Solano, 24 | caja | escritorio | 17 | 6 | 4 (67 %) | **48** | 1,013 | 0 | 8 | 4 | 3.2 | 4.0 |
| Julio Herrera, 26 | cliente | celular | 14 | 5 | 3 (60 %) | 33 | 760 | 1 | 8 | 5 | 4.0 | 3.7 |
| Alma Rentería | finanzas | escritorio | 17 | 16 | 9 (56 %) | 60 | 822 | 7 | 3 | 2 | 3.5 | **3.2** |
| Paulina Ríos, 44 | socia | escritorio | 20 | 9 | 5 (56 %) | 32 | 1,162 | 3 | 11 | **6** | **2.4** | 4.2 |
| Aurora Vega, 45 | clienta | escritorio | 10 | 7 | 3 (43 %) | 23 | 577 | 4 | 7 | 3 | 3.0 | **3.0** |
| Ximena Paredes, 34 | prospecta | escritorio | 19 | 16 | **6 (38 %)** | 25 | 1,118 | **10** | **15** | **6** | 4.1 | 4.3 |

- **Ximena es el caso más importante de la tabla.** Es la que menos logró (38 %) y la que más atorones acumuló (15), y no porque el producto le fallara: falló porque vino a decidir si esto es un negocio y **el producto no publica la información con la que se decide eso**. Diez de sus dieciséis tareas no llevaron un clic. Su conclusión fue *"No recluto porque saqué la cuenta… No doy mi CLABE, y no por el negocio: por la ventana que me dijo que ya tenía comisiones que no tengo"* (`ximena-paredes-2027-03-02.md`).
- **Ernesto, 63 años y celular, es el techo de dificultad del producto**: 14 atorones, 1,535 s de reflexión, 28 minutos para comprar un frasco y no lograr lo único que vino a hacer. *"Le piqué a «Mi cuenta» → me dejó en la misma pantalla. Le piqué otra vez pensando que fue mi dedo. Lo mismo."* (`ernesto-2027-03-02.md`).
- **Los dos mejores números de la ronda son de las dos pantallas nuevas que hacen un oficio completo**: Toño con Despacho en bloque y Gaby con Seguimiento de hoy. Las dos están fuera del menú.
- **Mireya hizo 48 clics en seis tareas**: es el precio de un turno de caja donde el fondo inicial no se puede capturar y la lista de pedidos se reinicia sola.

---

## 3. Dónde se atoran y por qué

Agrupado por causa, no por persona. Cada bloque marca el **veredicto de la verificación** y si lo que hay que arreglar es **código** o **diseño**.

### 3.1 El dinero que no se puede cobrar: la CLABE (código · CONFIRMADA · crítica)

El defecto más caro de la ronda, y el más silencioso.

| Quién | Intentos | Pantallas | Mensaje que recibió |
|---|---|---|---|
| Fabiola Cantú | 5 | Comisiones del panel · Mi perfil | ninguno |
| Paulina Ríos | 5 (en dos días distintos) | Comisiones del panel · Mi perfil · ventana del portal | ninguno |

La verificación es concluyente: el backend funciona (`POST /customers/clabe` con el token de Paulina devolvió `200 {ok:true, clabeLast4:6789}` y quedó persistido), pero **en todo `sim/servidor.log` de esta ronda no hay ni un solo `POST /customers/clabe`** desde el navegador. Las dos pantallas comparten el mismo patrón: "Guardar" no guarda, solo abre un modal de confirmación pintado al final de una página kilométrica; ninguna de las dos personas describe ese modal porque estaban con el scroll abajo, en Comisiones. Además hay **dos formularios de CLABE distintos** (uno pide banco, el otro no) que no se enteran uno del otro.

Las consecuencias, todas medidas:

- Marzo cerró con **$0.00 depositados**. Renata: *"Listas para depositar 0 · $0.00 — Sin CLABE 1 · $135.00 — Pagadas 0 · $0.00"* (`renata-2027-04-10.md`).
- Alma no pudo exportar el archivo del banco. El bloqueo, dicho sea, **está bien hecho**: *"No hay socias listas para depositar este mes"*, y sin CLABE ni siquiera aparece la casilla para marcar pagado. Renata lo anotó como lo único que la tranquilizó: *"sin CLABE no hay ni casilla que palomear, así que por ahí no se cuela un pago fantasma"*.
- El día 10 no hubo depósito **ni aviso de ningún tipo**. Paulina: *"Abrí el correo esperando un «te depositamos». Mi último correo es del 20 de marzo. Nada"* (`paulina-rios-2027-03-20.md`).
- Siete de los quince registros de emoción de intensidad máxima de la ronda salen de aquí, incluida la única *impotencia* registrada: *"tres intentos, cero mensajes de error y cero resultado: no hay nada más que yo pueda hacer"*.

Dos agravantes de la misma pantalla, también confirmados: una CLABE guardada **no se puede borrar ni vaciar**, solo sustituir por otra de 18 dígitos; y se puede escribir con solo el id de la socia, **sin verificar identidad**.

### 3.2 El sistema promete comisiones que no existen (código y diseño · CONFIRMADA · crítica)

El aviso *"Ya tienes comisiones a tu favor"* no se dispara por saldo: se dispara al activarse el modo socio o al primer pedido (`clabeReminderOnActivation`). Ximena y Fabiola lo recibieron **el mismo minuto en que pagaron, con sus registros en $0.00**, y la página del plan promete literalmente lo contrario: *"la CLABE se pide solo cuando ya tengas una comisión que cobrar"*.

Ximena, que perdió dinero en una red hace ocho años, lo detectó sola y fue **lo único que le tiró la confianza en todos los números buenos del sitio**:

> *"La ventana «Ya tienes comisiones a tu favor» con $0 y red vacía. Que no salga hasta que de verdad haya un peso confirmado. Es lo único que me tiró la confianza en todo lo demás."* (`ximena-paredes-2027-03-02.md`)
> *"Un solo número falso en la pantalla del dinero le tira la credibilidad a todos los números buenos, y aquí son muchos."*

Fabiola escribió lo mismo desde el otro lado: *"El aviso «Ya tienes comisiones a tu favor» cuando tengo $0 y la red vacía: eso es mentirle a la gente"* (`fabiola-2027-03-04.md`). Y Renata, desde administración: *"Le estamos prometiendo dinero a dos socias que según el sistema no tienen nada"* (`renata-2027-04-10.md`). Es el mismo defecto visto por tres puestos distintos.

Pegado a esto, un hueco de la misma familia: **el ledger distingue confirmada y pendiente ($135.00 + $124.20 = $259.20) y ninguna pantalla de administración lo muestra**. Paulina vio $259.20 todo marzo y le pagan $135; Alma acabó con tres cifras distintas del mismo concepto y ninguna pantalla que explique el paso de una a otra: *"cada vez que dos partes del sistema hablan del mismo dinero, dicen cosas distintas — $10,088 contra $0, $135 contra $0.00 listas, «Activas 0» contra tres avisos activos, $135 contra $259.20, $760 de venta contra $500 de corte"* (`alma-renteria-2027-04-10.md`).

### 3.3 Lo que compras antes de tener cuenta nunca suma (código · CONFIRMADA · crítica)

`GET /commissions/associates/<id>/month/2027-03` devuelve `vp=0.0, netVolume=0.0` para Julio (que pagó $1,209), Mariana ($829) y Aurora ($3,000 en dos pedidos). Ernesto, que se registró **antes** de comprar, sí tiene `vp=10.0`. Los pedidos de Aurora traen `linkedToAccountAt` —Gaby les creó ficha— y aun así su mes sigue en cero.

De ese solo defecto salen, todas a la vez, cinco cosas que cinco personas distintas reportaron sin saber que era lo mismo:

- Julio: *"«Este mes has comprado $0» arriba de «$1,209 Pagada»"* (`julio-2027-03-02.md`).
- Julio, Mariana y Aurora no aparecen en el Cuadro de Honor de marzo.
- Alma leyó "0 % recompra" pese a las dos compras de Aurora.
- **La mejor clienta del mes sale como inactiva.**
- Y es dinero: quien compra como invitado pierde su tramo de descuento por volumen y su activación del mes aunque después se registre.

### 3.4 El mes del dinero lo elige el reloj del navegador (código · CONFIRMADA · crítica y media)

Cuatro pantallas de dinero fechan el negocio con el reloj del cliente:

| Pantalla | Qué hace | Quién lo sufrió |
|---|---|---|
| Pagos del mes | el selector arma 12 meses desde `new Date()`; al recargar, marzo 2027 desaparece y se planta en agosto 2026 | Renata lo reprodujo tres veces: *"Recargué la página para asegurarme de que el recordatorio había quedado guardado de verdad… Marzo 2027 ya no estaba en el selector"* |
| Exportador de comisiones | el nombre del archivo sale del reloj, no del mes seleccionado: `comisiones-2026-08.xlsx` con el selector en marzo 2027 | Renata: *"El archivo que iba a mandar como constancia del cierre de marzo se llama agosto de 2026 y se contradice a sí mismo entre sus dos hojas"* |
| Estadísticas | abre en el mes del navegador sin avisar; Alma vio *"Ventas del periodo $0 · 0 pedidos"* junto a *"$10,088 cobrado · 9 pedidos"* en la misma pantalla | Alma estuvo media hora creyendo que marzo había cerrado en ceros y se bajó un `reporte-mensual-2026-09.xlsx` |
| Clientes | `daysSinceLastPurchase` con `Date.now()` y `Math.max(0, …)`: todos llevan "0 días" y el filtro de fríos no encuentra a nadie nunca | Renata, Alma y Gaby, por separado |

**Nota honesta sobre el arnés**: el navegador de la ronda iba en 2026-09-04 y el mundo en 2027-04-10, así que el arnés *agranda* el efecto. Pero el defecto es del producto y en producción deja el día de pago dependiendo del reloj del cliente; y hay una parte que no tiene excusa de reloj: la contradicción entre las dos mitades de la pantalla de Estadísticas, los importes en cero por estado, el Top de clientes sin ordenar y la hoja Inventario del Excel vacía.

Un caso emparentado y **sin ninguna excusa de reloj**: al recalcular una comisión se le **reescribe la fecha de creación**. Las de Ximena (2 de marzo) y Fabiola (4 de marzo) aparecen las dos con `createdAt 2027-03-20T09:14:39Z`, el instante en que Paulina se activó. Paulina, que sí sabe cuándo compraron sus alumnas, lo leyó como *"Le movieron la fecha a mis comisiones"*.

### 3.5 Casillas y botones que dicen que hacen algo, y no lo hacen (código · CONFIRMADA)

| Control | Qué promete | Qué hace | Quién |
|---|---|---|---|
| "Guardar esta dirección para futuras compras" | guardar la dirección en el perfil | el carrito manda `saveShippingAddress` y `POST /orders/create` no lo lee nunca; las 7 fichas de clientes tienen `addresses=0` | Ernesto (palomeó y le puso alias "Casa") |
| "Activar modo socio" (panel y pedido) | activar | solo navega a otra página, donde hay un segundo botón con el mismo nombre | Ximena, Fabiola, Aurora |
| "Ver" (columna Detalle de Pedidos) | abrir el pedido | reproducido **8 veces entre dos empleados**: brinca de pestaña, abre el detalle de otra clienta, o vacía la lista entera | Toño (4), Mireya (4, con la clienta enfrente) |
| Campo Qty de la tarjeta de producto | poner la cantidad tecleada | escribe directo en el carrito y "Agregar" suma una pieza más: escribes 2 y quedan 3 | Paulina (le metió 3 Klinhart, $1,440, y casi le tumba la activación) |
| "Mostrar metas secundarias" | mostrarlas | cuando no hay ninguna, cambia su propio texto y no muestra nada | Ximena, que lo anotó como botón roto |
| "Compartir mi enlace" | compartir | no abre nada visible en laptop | Fabiola |
| Guardar CLABE | guardar | §3.1 | Paulina, Fabiola |

Encadenado: **sin dirección guardada la suscripción no se puede crear**, y en todo marzo no se dio de alta ni una. Ernesto llenó todo —Klinhart, día 5, envío a su domicilio— y le salió *"Aún no tienes direcciones guardadas"*, en un mensaje que además lo mandaba a guardarla con la casilla que acababa de usar.

> *"Pero si yo SÍ palomeé esa casilla al pagar. Hasta le puse de nombre «Casa»."* (`ernesto-2027-03-02.md`)

El del bug de cantidad tiene una particularidad que conviene decir: **ya estaba corregido para el producto destacado** y la tarjeta del catálogo quedó igual. Paulina: *"La cantidad no respeta lo que tecleo: puse 2 y metió 3."* (`paulina-rios-2027-03-20.md`).

### 3.6 El recibo que no comprueba nada (diseño · CONFIRMADA · alta)

Los datos **sí están guardados**: `GET /orders/ORD-351342D9` devuelve `deliveryType "pickup"`, `pickupStockId`, `invoiceRequested true`, el `invoiceData` completo (RFC, razón social, régimen 612, CP fiscal, uso G03), los items y el desglose. La pantalla del cliente no muestra ninguno de esos campos, y la barra de progreso dice *"Envío — Ruta de entrega"* aun en recolección. El correo repite lo mismo a tres personas que eligieron recoger: *"Estamos preparando tu paquete y te avisaremos cuando salga"*.

Cinco personas lo reportaron:

- Aurora abandonó buscando dónde releer su RFC: *"No hay ninguna pantalla donde vuelva a ver ni corrija mis datos fiscales."* (`aurora-vega-2027-03-04.md`).
- Paulina lleva **21 días** sin saber en qué tienda está su pedido: *"Pagué $960 hace tres semanas y no sé dónde está mi producto"*.
- Mariana compró sin cuenta y su único comprobante es un correo que no dice qué compró: *"El correo de pago no trae el detalle de la compra: sin cuenta, me quedé sin comprobante."* (`mariana-2027-03-02.md`).

Del lado de administración, el mismo hueco desde arriba: **no existe módulo de facturación** —ni bandeja, ni marcar emitida, ni folio, ni PDF—, y **dos facturas del 4 de marzo llevan 37 días sin atender**. Alma buscó las palabras "factura", "CFDI", "RFC" y "fiscal" en toda la Configuración y concluyó que la pantalla no existe. La verificación matiza: **sí existe** el bloque para marcar una factura como emitida, con folio y correo al cliente… escondido dentro del detalle del pedido, detrás del mismo botón "Ver" que está roto (§3.5). Es una **percepción** con una causa muy real.

### 3.7 El checkout: dos callejones (código · CONFIRMADA · crítica y alta)

**a) Comprando como invitado no se puede elegir "Recoger en sucursal".** El botón de pagar exige correo válido a todo invitado, sin mirar el tipo de entrega, pero Nombre, Teléfono y Correo viven dentro del bloque que solo se pinta cuando la entrega es a domicilio. Aurora solo pudo pagar con un rodeo: volver a "Envío a domicilio", escribir el correo, y regresar a "Recoger". El daño quedó grabado: sus dos pedidos tienen `recipientName: null` y `phone: null`, es decir, **dos pedidos de mostrador sin nombre ni teléfono de quien los va a recoger**.

> *"«Escribe tu correo: ahí te avisamos del pago, el envío y la entrega.» (respuesta de «Pagar y finalizar» cuando no había ningún campo de correo en la pantalla)"* (`aurora-vega-2027-03-04.md`)

**b) "Envío desde $129 · se calcula con tu CP" es mentira.** La cotización solo se dispara con nombre, teléfono, calle, número, ciudad, CP, estado y país completos. El CP por sí solo no hace nada, y como el estado suele ser el último campo, el precio *"aparece al elegir el estado"* — que es exactamente lo que reportaron Mariana, Ximena y Julio. Mientras tanto el Total de arriba sigue diciendo $700 cuando se van a cobrar $829.

> *"Como dice «se calcula con tu CP», escribo solo mi código postal, 03100, a propósito… Exactamente lo mismo: «Desde $129». No calculó nada."* · *"El Total del carrito miente hasta el final: dice $700 cuando vas a pagar $829."* (`mariana-2027-03-02.md`)
> *"El envío que nunca se calcula. Puse mi CP y me dejó sin saber cuánto iba a pagar."* (`ximena-paredes-2027-03-02.md`)

Mariana escribió su CP a propósito para no dar su dirección, se quedó sin número, abandonó la tarea con facilidad 2 y le escribió a soporte a las 21:46 preguntando cuánto costaba el envío.

**c) Y una tercera, heredada del [24] y confirmada aquí sin el entorno roto:** al volver de la pasarela la pantalla se queda en blanco unos segundos, sin un "estamos confirmando tu pago". Esta vez **nadie pagó dos veces** —los dos pedidos gemelos de Aurora resultaron ser dos compras completas, con su propio paso por la pasarela y su propio `paymentId`—, pero el susto quedó registrado dos veces con intensidad máxima:

> *"Pagué $609 y la pantalla se quedó en blanco. Se me fue el alma a los pies."* (`ernesto-2027-03-02.md`)
> *"La pantalla se quedó unos segundos como en blanco justo después de pagar. Susto feo con $829 en juego."* (`mariana-2027-03-02.md`)

### 3.8 La caja que nace descuadrada (código · CONFIRMADA · alta)

El fondo inicial solo puede heredarse del corte anterior: no existe endpoint ni campo para declararlo. Mireya, cajera de tercer día, llegó con $500 en el cajón, la pantalla le dijo *"Fondo inicial $0.00"* en un campo de solo lectura, vendió todo el día con la caja descuadrada y su corte le salió con un **sobrante falso de $540** ($500 de fondo + $40 reales). Ese sobrante la empujó a "Retirar", que exige el código de la gerente.

Y el código **se valida hasta el paso 4**: Mireya escribió 1234 a ver qué pasaba, la pantalla la dejó pasar, le hizo leer todo el resumen del arqueo y hasta "Cerrar el corte" le rebotó con `HTTP 403`. Resultado real: **los $1,040 del día se quedaron toda la noche en el cajón de la tienda**.

Lo notable es que el arqueo en sí es de lo mejor del producto, y ella misma lo dice:

> *"«Queda escrito en el comprobante para que la gerente lo vea. No es una falta: es lo que pasó», que me quitó el miedo de reportar una diferencia."* (`mireya-2027-03-03.md`)

El mejor arqueo de la ronda arrojó $540 de sobrante donde había $40, porque le falta el movimiento anterior.

Dos huecos más del mostrador, del mismo turno: **no hay ticket para el cliente** (el corte de caja sí se puede mandar por correo, la venta no), y **entregar un pedido reservado en otra sucursal descuenta el inventario de la sucursal equivocada, en silencio**. Mireya escribió *"le di dos botes de mi anaquel y el inventario no bajó en ningún lado"*; la verificación la corrige —sí bajó, en Guadalajara— y confirma el problema de fondo: la única salida disponible es cambiar la caja de sucursal y fingir que estás en otra tienda. Su emoción más intensa de la ronda fue *preocupación*, intensidad 5: *"el faltante va a aparecer en mi tienda"*.

### 3.9 Trabajo enterrado: la arquitectura de información (diseño · CONFIRMADA y PERCEPCIÓN)

Cuatro de los cinco empleados perdieron su primer cuarto de hora buscando dónde vive su trabajo.

| Lo que buscaban | Dónde estaba | Cómo llegaron |
|---|---|---|
| Comisiones y pagos (Renata, Alma) | al fondo de la vista Clientes, debajo de la bitácora y los documentos de un cliente sin comisiones | por la alerta de "Acciones urgentes". Alma buscó "Comisiones" en el menú **siete veces** |
| Seguimiento de hoy (Gaby) | botón encima de la tabla dentro de Clientes | de casualidad, tras cruzar cuatro pantallas |
| Despacho en bloque (Toño) | botón entre las pestañas de estado de Pedidos | picándole a lo que había, después de rendirse con el botón "Ver" |
| "Recibe esto cada mes" (Ernesto) | último renglón del panel, debajo de trece productos | bajando hasta el final después de comprar; antes preguntó a soporte y a su sobrino |
| `#/modo-socio` (6 personas) | enlace gris al pie de un bloque del panel | por un correo, después de pagar (Mariana, Julio); de coraje el último día (Paulina) |

Las frases:

> *"No existe la palabra Comisiones en ninguna parte del menú, y yo vengo justamente el día 10, que es el día de pago."* · *"Si alguien me pregunta dónde se pagan las comisiones tendría que contestarle: en Clientes, hasta abajo, después de los documentos."* (`renata-2027-04-10.md`)
> *"si no me sale ese aviso urgente, no lo encuentro hoy"* (`alma-renteria-2027-04-10.md`)
> *"Me costó cruzar cuatro (login → panel de pedidos → clientes → seguimiento) para llegar a la única pantalla que es mía. Y llegué de casualidad, porque el botón está escondido arriba de una tabla dentro de Clientes. En el menú de navegación no existe."* (`gaby-2027-03-08.md`)
> *"Lo que más coraje me da no es que falte algo: es que sí estaba y estaba escondido."* (`ernesto-2027-03-02.md`)
> *"Si me la hubieran mandado el día que me hice socia me habría ahorrado dos mañanas."* (`paulina-rios-2027-03-20.md`)

Agravante estructural: **todo el back office vive en una sola ruta, `#/admin`**. Renata no puede mandarle un enlace al dueño ni volver a la misma pantalla tras recargar (y al recargar pierde el mes, §3.4). Le puso 2 de 7 a la facilidad de encontrar su propio trabajo. Del lado del cliente, el panel es una página infinita cuyo menú no navega sino que hace scroll: por eso Ernesto reportó *"«Mi cuenta» y «Órdenes» del menú no me llevan a ningún lado"* y Fabiola *"todo el panel es UNA sola página kilométrica… Le picas a «Links» y no cambia de pantalla, sólo te baja… pasando por la tienda entera con los 13 productos en medio"*.

### 3.10 El vocabulario: tres monedas y ningún glosario (diseño · CONFIRMADA)

Es el impuesto de comprensión hecho texto. Cinco personas reportaron lo mismo desde ángulos distintos:

- **PC, VP, VG** (y PV, PG en los globitos): trece apariciones de "PC" en la tienda y **la única definición está en `#/modo-socio`**. Paulina: *"Cinco siglas para tres cosas. Yo doy clases de yoga, no de álgebra"*.
- **Cuatro nombres para el mismo estado**: Julio contó "Pago registrado", "Pagada", "Pendiente/Pagada/Enviada/Entregada" y `paid`. *"«Estado: paid», así, en inglés, es el cuarto nombre distinto que le veo al mismo estado en cuatro pantallas"* (`julio-2027-03-02.md`).
- **`mixed`**, en inglés y sin desglose, es literalmente el número que Alma iba a cuadrar en el corte de caja. Su emoción de intensidad 5: *"es exactamente el número que vine a cuadrar y la pantalla me lo esconde detrás de una palabra en inglés"*.
- **Fechas ISO**: *"«Creada: 2027-03-02T11:18:04Z»: ¿qué es esa T y esa Z?"* (`ernesto-2027-03-02.md`).
- **"Mínimo requerido"**, etiqueta fija sin sujeto en la cabecera del bloque Entrega: el arnés la recogió como error en pantalla **tres veces** (Ernesto, Julio, Ximena) y los tres preguntaron "¿mínimo de qué?".
- **Género**: al señor de 63 años el sistema le dijo "socia" cinco veces, incluso en el correo. Julio: *"Dice «socia». En femenino. Yo entré por Google buscando un bote de proteína"*.
- Y **el año**: el pie dice "© 2026 finding U" en todas y cada una de las pantallas, con el mundo en 2027. Nueve de doce personas lo anotaron.

Al vocabulario se le suma un número mal publicado, que es el más importante del plan: **"20 VP netos (más o menos $1,000 de compra a precio de lista)"** es falso, y la misma página lo desmiente tres renglones abajo (*"Ojo: 20 PC de lista con 10 % de descuento = 18 VP: no activa"*). Ximena lo detectó sola y midió el hoyo: con $980 de Naplus activa, con $1,000 no; el rango real va de $933 a $1,605 según el producto.

> *"La misma pantalla me dice que $1,000 activa y que $1,000 no activa. Es el número más importante del plan."* (`ximena-paredes-2027-03-02.md`)

### 3.11 Sin puerta de salida: quien ya pagó no tiene a quién escribirle (diseño · CONFIRMADA)

`#/ayuda`, `#/contacto`, `#/devoluciones`, `#/soporte`, `#/sucursales` y `#/facturacion` rebotan a la tienda. El pie de la tienda no tiene un solo enlace.

Julio compró como invitado —como la propia página permite—, le llegó el bote estrellado, y **para encontrar el teléfono de la tienda a la que ya le había pagado $1,209 tuvo que crear una cuenta y verificar su correo**. Aurora probó cuatro rutas con el mismo resultado, ya habiendo pagado $1,500 sin saber a qué hora abre la sucursal donde va a recoger.

> *"Comprarles me costó cinco minutos. Reclamarles no lo logré en veinte."* · *"El pie de página dice, completo: «© 2026 finding U». Ni un enlace. Ni ayuda, ni contacto, ni devoluciones, ni un teléfono."* (`julio-2027-03-02.md`)

Encima, el aviso de privacidad remite los derechos ARCO a *"los canales de contacto oficiales"* que en ninguna parte del sitio se nombran. Y ese mismo aviso —modal a pantalla completa, sin cerrar y sin "no acepto", anclado abajo en móvil— **le costó tiempo a 11 de las 12 personas**: Ximena y Fabiola le picaron dos y tres veces a "Ver cómo funciona" creyendo que el botón estaba roto; Paulina creyó que "Iniciar sesión" no servía.

Y una contradicción de una línea que casi cuesta una venta: el aviso jura *"No te pedimos datos bancarios ni fiscales"* mientras el carrito pide RFC, régimen y CP fiscal, y el modo socio pide CLABE, INE, CURP y constancia. Aurora, que entró justamente por la factura: *"se me cae el estómago… si no piden datos fiscales, no hay RFC"* (`aurora-vega-2027-03-04.md`). Alma, que viene a pedir CLABEs y RFCs, se rió del aviso el día de su primer cierre.

### 3.12 La devolución que sí existe y no se ve (diseño · PERCEPCIÓN · media)

La pantalla que Julio necesitaba existe y hace exactamente lo que pedía: cantidades por producto con tope por línea, motivos, reembolso calculado sobre el neto de cada línea y envío de solo esas líneas. **No la vio porque el botón solo se pinta cuando el pedido está "entregado"**, y en su turno el pedido estaba en `paid`.

Julio pasó veinte minutos adivinando direcciones y se quedó con la proteína rota, porque la única salida visible era "Cancelar orden", que le devolvía los $1,209 completos y lo obligaba a pagar otro envío.

> *"El sistema sabe perfectamente que son dos cosas separadas y cuánto vale cada una. Puede devolverme $800 sin tocar el resto. Simplemente no hay botón."* (`julio-2027-03-02.md`)

Este producto **hace muy bien los botones apagados que explican su motivo** (Renata elogió el patrón, Mireya también). Aquí el botón simplemente no está.

### 3.13 Permisos: cuatro empleados entran como ADMIN (diseño · CONFIRMADA · media)

Los tres empleados que no son gerencia lo reportaron por su cuenta y con incomodidad:

> Mireya, cajera de tercer día: *"puedo dar de alta una bodega o sucursal nueva; ¿por qué me deja hacer eso a mí?"* (`mireya-2027-03-03.md`)
> Toño: *"llenar el formulario para crear una campaña de publicidad. Yo. El de las cajas."* (`tono-2027-03-03.md`)
> Gaby: *"debajo de mi nombre dice ADMIN, igual que le diría a Renata"* (`gaby-2027-03-08.md`)

La etiqueta ADMIN sobre el nombre de una cajera es, además, lo primero que ve el cliente que se asoma al mostrador. Y el costo no es solo de seguridad: la pantalla de Stocks abre con el formulario de crear bodega y deja el inventario al fondo, tras dos formularios largos que a Toño no le tocan.

### 3.14 Lo que le pasa al coach: plantillas que dicen lo contrario (código · CONFIRMADA · alta)

La situación 'activa' existe en el backend pero **no tiene plantilla**, y la pantalla rellena con `'fria'`. Gaby estuvo a un clic de mandarle *"Hace tiempo que no te vemos por la tienda"* a Julio, cuyo pedido se había entregado el viernes — mientras el mismo cuadro, arriba, le decía *"Compró hace poco; no necesita contacto hoy"*.

> *"La plantilla no me ahorró trabajo, me puso una trampa."* (`gaby-2027-03-08.md`)

Escribió los cuatro mensajes a mano. Y aun así hizo su jornada en quince minutos, con la mejor facilidad de la ronda: la pantalla es buena, el contenido no está terminado. Dos detalles más del mismo turno: la bitácora de contactos **firma con un número de trece dígitos** en vez del nombre (*"Las dos notas quedaron guardadas, pero Si mañana Mireya lee «1803978000111», no sabe si fui yo o Alma, y le vuelve a escribir a Julio. Para eso, me sigo yendo con mi libreta."*), y *"«Mi cartera» no es mi cartera: es mi cartera más las huérfanas"*.

### 3.15 Lo pequeño que duele

| Qué | Veredicto | Quién |
|---|---|---|
| El Cuadro de Honor no cuadra: 50 de VG arriba frente a 25 + 24 abajo (redondeo por separado), y la columna FALTA sale en negativo | CONFIRMADA · baja | Gaby, Fabiola |
| Fabiola aparece con nombre y dos apellidos completos y las demás como "Paulina R."; ella escribió que no quiere su nombre completo en una lista que ve toda la red | CONFIRMADA · baja | Fabiola |
| Los contadores de Notificaciones marcan siempre "Activas 0" con tres avisos activos abajo | CONFIRMADA · media | Alma |
| Pedidos abre en la pestaña Pendiente (vacía) mientras el resumen de al lado dice que hay tres pagados; el buscador contesta "sin resultados **en este estado**" | CONFIRMADA · baja | Toño, Mireya |
| La conciliación acepta hasta 90 días; la pantalla la deja clavada en 72 horas y le encargaron revisar todo marzo | CONFIRMADA · media | Renata |
| El "4 pedidos pagados sin envío" mezcla tres recolecciones en mostrador con un solo envío pendiente; y 37 días se ven igual que 1 día | CONFIRMADA · media | Renata |
| Stocks sin mínimos, sin alertas, sin vista de las tres sucursales juntas y sin la bitácora que la propia pantalla anuncia | CONFIRMADA · media | Toño, Alma |
| La tienda no tiene buscador ni una dirección por producto; "Ver producto" solo cambia un encabezado fuera de la vista | CONFIRMADA · media | Ernesto, Mariana, Aurora, Ximena, Julio |
| La suscripción solo puede ser mensual y viene marcada de fábrica en "Recoger en Sucursal Guadalajara, día 20" — a un señor de Monterrey | CONFIRMADA · media | Ernesto |
| El objetivo del mes cambia solo, de comprar a reclutar, en el minuto en que pagas | CONFIRMADA · media | Ximena |
| El perfil del cliente llama a un endpoint de administración y recibe 403 en cada carga; el catch tapa el error y pinta "Constancia fiscal: Requerido · INE · CURP" desde un fallback cableado en el front | CONFIRMADA · alta | Paulina (6 veces), Fabiola (2), Ernesto (1) |
| El "Corte de mes" cuenta cinco días distintos según tengas sesión o no (26d sin cuenta, 21d con cuenta, medido en el mismo minuto) y nunca dice de qué es el corte | CONFIRMADA · media | 7 de 12 personas |

Sobre el último: **ninguna de las siete personas entendió qué es el corte**. *"¿se me vence el carrito? ¿se acaba una oferta?"*. Un reloj en cuenta regresiva sin explicación no apura: asusta.

### 3.16 Lo que fue del arnés, no del producto (DATO O ARNÉS · 4 hallazgos)

Se separa aquí para que no contamine las cuentas:

1. **Julio vio su pedido en "Pago registrado" cuatro días después.** Su turno corrió antes que el de Toño, que es quien despacha: en el momento en que miró, el pedido de verdad estaba en `paid`. El sistema no se equivocó. Lo que sí queda del reporte —y está anotado en §3.12— es que desde un pedido pagado no hay ninguna puerta visible hacia una devolución.
2. **Los dos pedidos idénticos de Aurora no son un cobro duplicado**: son dos compras completas separadas por seis horas de reloj simulado, cada una con su propio `paymentId`. Alma hizo bien en levantar la mano; lo que sí falta es que el panel avise "posible duplicado, revisar", porque desde la pantalla es imposible distinguirlos.
3. **La paquetería se llama "Simulada"** y así le sale al cliente en el correo. Es el transportista de mentira del mundo simulado. La lectura de Toño es correcta (*"«Lo enviamos por Simulada» en un correo a un cliente se ve pésimo"*) pero no hay defecto detrás.
4. **Ocho de las trece fichas de producto están vacías** ("Presentación y modo de uso en la etiqueta del producto"). Es un hueco de la semilla, no de la plataforma: la ficha del Finding Pro demuestra que el campo existe y se pinta bien, y fue lo que convenció a Julio y a Mariana. Aurora, nutrióloga, estuvo a punto de no comprar por eso. Sí es del producto lo que va pegado: el bloque *"Por qué elegir X — Resultados reales"* rellena con las etiquetas del producto, por eso el colágeno mostraba dos tarjetas que decían "colageno" y "colágeno".

---

## 4. Lo que preguntaron

**27 preguntas** que la plataforma debió responder sola: 14 a soporte, 8 a un superior, 3 a la patrocinadora y 2 a un familiar. Las 27 quedaron escritas en `sim/helpdesk.md` con su respuesta.

| Reparto | Cuántas |
|---|---|
| **Ya tenían respuesta en pantalla** (la persona no la encontró) | **11** |
| Destaparon huecos reales de producto | 10 |
| Son decisiones de negocio que ningún sistema resuelve | 6 |

### 4.1 Las once que ya estaban respondidas, y dónde estaba la respuesta

| Quién preguntó | Qué preguntó | Dónde estaba la respuesta |
|---|---|---|
| Mariana | costo exacto del envío | tarifa plana ($129 Estafeta / $219 DHL); el checkout la muestra **al elegir el estado**, un campo debajo del CP, en la misma pantalla donde ella preguntó |
| Ximena | costo del envío a CP 44100 | $129, misma tarifa plana, visible al elegir Estado |
| Ernesto (a soporte) | dónde se programa la compra mensual | "Recibe esto cada mes", al fondo del panel `#/dashboard` |
| Ernesto (a su sobrino) | la misma función | la buscó en carrito, Mi cuenta, Órdenes y Mi perfil: **cuatro pantallas que no la mencionan** |
| Julio | devolución parcial | existe por líneas y por motivo; aparece cuando el pedido pasa a "Entregado", plazo de 2 días, reembolso al mismo medio en 3 a 5 días hábiles |
| Julio | si tenemos registrada la entrega | sí: salió el 3-mar 12:07 con guía SIM-682C1E22 y el correo se le mandó ese mismo minuto; su ficha de pedido seguía diciendo "Pago registrado" |
| Mireya | fondo inicial de caja | no hay "abrir turno": el fondo se captura en el paso 3 del corte, y los botones están grises porque no hay movimientos que cortar |
| Mireya | código de autorización POS | la pantalla sí dice dónde vive (Configuración → Código de autorización POS), aunque **nadie lo ha dado de alta** |
| Toño | dónde dejar el reporte de turno | Almacén → "Resumen de turno" lo arma solo, y con su usuario del 3-mar dice literalmente los 3 pedidos con sus guías |
| Renata → Paulina | los $124.20 que faltaban | están en el registro de comisiones como "pendiente" por ORD-9CD8BD3D, con pedido, generación, monto y estado |
| Alma | por qué no exporta el archivo del banco | el bloqueo es correcto y está explicado ("No hay socias listas para depositar"); sin CLABE la socia queda en "sin CLABE" |

**Lo que dice esta tabla no es que la gente no busque.** Toño buscó su reporte de turno y no lo halló porque no está en el menú; Ernesto buscó su suscripción en cuatro pantallas, incluida la que la contiene, y no la halló porque está debajo de trece productos; Mireya encontró la instrucción del código de autorización y el código **no existe en la configuración**; Julio buscó su devolución en nueve pantallas y el botón se pinta según un estado que él no controlaba. En once de veintisiete casos **el producto tenía la respuesta y la escondió**. Ese es el mismo hallazgo del §1.2, medido desde el otro lado.

### 4.2 Las seis de negocio

Ninguna de estas se arregla con código; se decide y se escribe:

1. **Ximena → Paulina:** *"¿cuánto llevas ganado y con cuántas personas? Necesito diez personas comprando lo mismo que yo cada mes para recuperar mis $1,350, ¿así es?"* — su aritmética es exacta (al 10 % de generación 1 hacen falta ~$13,500 netos de red al mes). Ningún sistema resuelve si eso es un buen negocio; publicar ganancias reales, sí.
2. **Ximena:** *"¿me retienen impuestos de las comisiones y hay monto mínimo para depositar?"* — hoy no hay retención ni mínimo configurados, se paga el bruto el día 10.
3. **Julio:** *"¿quién paga el envío de regreso de una devolución?"* — no está configurado ni decidido en ninguna parte del sistema.
4. **Gaby → Renata:** *"¿los clientes que tienen patrocinadora me tocan a mí o a Paulina?"* — la plataforma muestra la patrocinadora pero no define de quién es la responsabilidad del contacto. Gaby **dejó a dos clientas sin contactar** por no saberlo.
5. **Alma → Renata:** *"¿dejamos a Paulina para el pago del 10 de mayo o le hablo por teléfono?"* — decisión de cobranza.
6. **Renata → dueño:** qué hacer con los dos cargos idénticos de Aurora Vega (reembolsar uno y facturar el otro).

---

## 5. Cómo se ve y cómo se siente

### 5.1 Calificaciones

| Persona | 1.ª impresión | Confianza que transmite | Legibilidad | **Coherencia** | Móvil | Recomendaría |
|---|---|---|---|---|---|---|
| Mariana Robles, 29 | 7 | 5 | 6 | 4 | 5 | 5 |
| Ernesto Vidal, 63 | 6 | 5 | **4** | 4 | 4 | 5 |
| Ximena Paredes, 34 | 6 | 5 | **8** | 4 | — | 5 |
| Julio Herrera, 26 | 7 | 4 | 7 | **3** | 6 | **4** |
| Aurora Vega, 45 | 7 | 4 | 7 | **3** | — | 5 |
| Fabiola Cantú, 41 | 7 | 5 | 6 | 5 | — | 6 |
| Paulina Ríos, 44 | **5** | **3** | 6 | **3** | — | **4** |
| Mireya Solano, 24 | 6 | 6 | 6 | 5 | — | 6 |
| Toño Vera, 31 | 6 | 6 | 7 | 4 | — | 6 |
| Gaby Ledesma, 33 | 6 | **7** | 6 | 4 | — | **7** |
| Renata Bustos, 38 | 6 | 4 | 6 | **3** | — | **4** |
| Alma Rentería | 6 | 4 | 7 | **3** | — | 5 |
| **Media** | **6.2** | **4.8** | **6.3** | **3.8** | 5.0 | **5.2** |
| Media clientes | 6.4 | 4.4 | 6.3 | 3.7 | 5.0 | 4.9 |
| Media personal | 6.0 | 5.4 | 6.4 | 3.8 | — | 5.6 |

**El perfil de estas notas es el diagnóstico entero del producto**: se ve bien (6.2), se lee bien (6.3) y **no cuadra consigo mismo (3.8)**. La coherencia es la nota más baja de todas y la única donde clientes y personal coinciden. Las cinco personas que le pusieron 3 son las cinco que trabajaron con dinero: Julio (cuatro nombres para un estado), Aurora (el aviso contra el carrito), Paulina (cinco siglas y tres cifras), Renata (dos hojas del mismo Excel) y Alma (*"cada vez que dos partes del sistema hablan del mismo dinero dicen cosas distintas"*).

Nótese también que **el personal confía más que los clientes** (5.4 contra 4.4) y recomendaría más (5.6 contra 4.9): el back office está mejor terminado que la tienda.

### 5.2 Los adjetivos

| Persona | Tres adjetivos |
|---|---|
| Mariana | bonita, **ambigua**, insistente |
| Ernesto | larga, joven, **insistente** |
| Ximena | clara, **insistente**, **contradictoria** |
| Julio | limpia, **insistente**, **incompleta** |
| Aurora | bonita, **incompleta**, olvidadiza |
| Fabiola | ordenada, larguísima, **desconfiada** |
| Paulina | abarrotada, ruidosa, **desconfiada** |
| Mireya | seria, apretada, para alguien que ya sabe |
| Toño | ordenada, **incompleta**, despareja |
| Gaby | ordenada, apretada, de contadora |
| Renata | ordenada por fuera, desordenada por dentro, **sin memoria** |
| Alma | ordenada, operativa, **incompleta** |

Se repiten: **"ordenada" 5 veces**, **"insistente" 4**, **"incompleta" 4**, **"desconfiada" 2**, **"apretada" 2**. Nadie dijo "fea"; cuatro dijeron "bonita" o "limpia". El producto no tiene un problema estético: tiene un problema de **terminación** y de **insistencia**. "Insistente" es siempre lo mismo: el modo socio ofrecido cuatro o cinco veces a quien vino por un frasco.

> *"terminé con la sensación rara de haber comprado en una tienda bonita que en realidad quiere reclutarme"* (`mariana-2027-03-02.md`)
> *"Le di al botón azul «Registrate» y no me llevó a un registro: me llevó a una página larguísima que empieza con «Bono de Inicio Rápido disponible»… y premios: «ORO — 15,000 puntos VG — $3,000 MXN/mes», «DIAMANTE — Viaje internacional elite». A mi edad eso me huele mal. Casi cierro todo. Yo venía por un frasco."* (`ernesto-2027-03-02.md`)

### 5.3 Mejor y peor pantalla

| Persona | Mejor | Peor |
|---|---|---|
| Mariana | `#/modo-socio` | el carrito en el celular |
| Ernesto | el "Resumen" antes de pagar y "¡Correo verificado!" | el panel después de entrar |
| Ximena | la caja "Tu descuento este mes" del carrito | la ventana "Ya tienes comisiones a tu favor" sobre un panel en $0 |
| Julio | `#/modo-socio` | `#/orden/ORD-682C1E22` |
| Aurora | `#/modo-socio` | la orden ya pagada |
| Fabiola | el carrito (la sugerencia de activación) | Comisiones del panel (la CLABE) |
| Paulina | `#/modo-socio` | el panel principal |
| Mireya | el corte de caja por pasos | la lista de Pedidos |
| Toño | Despacho en bloque | la lista de Pedidos |
| Gaby | Seguimiento de hoy | la tabla de Clientes |
| Renata | Acciones urgentes y los modales que explican antes de apretar | Pagos del mes, escondida y sin memoria del mes |
| Alma | el detalle de pedido con los datos fiscales | Estadísticas |

**Cuatro personas eligieron `#/modo-socio` como la mejor pantalla del producto, y seis la elogiaron.** Todas llegaron tarde. Es la pantalla que la ronda 5 construyó y la que nadie enlaza desde donde nacen las dudas.

**Las peores se reparten en dos familias:** las que no repiten lo que la persona eligió (la orden pagada, el carrito móvil, Estadísticas) y las que se contradicen con su propio contenido (el aviso de comisiones sobre un panel en $0, Pagos del mes que pierde el mes, la tabla de Clientes que dice "0 días" de gente que compró esta semana).

### 5.4 Las emociones y su disparador

140 registros. La distribución dice bastante sola:

| Emoción | Veces | Intensidad media | Personas |
|---|---|---|---|
| **Desconfianza** | 31 | 3.8 | 12 de 12 |
| **Alivio** | 26 | 3.6 | 12 de 12 |
| **Frustración** | 24 | 4.0 | 12 de 12 |
| Enojo | 14 | 3.6 | 9 |
| Orgullo | 6 | 3.2 | 6 |
| Vergüenza | 4 | 3.0 | 4 |
| Otras (resignación, miedo, impotencia, susto, desconcierto…) | 35 | — | — |

Las tres primeras las sintieron **las doce personas**. La desconfianza es la emoción dominante y su disparador es siempre el mismo: **dos partes del producto diciendo cosas distintas del mismo dinero**. El alivio en segundo lugar no es cortesía: es lo que sienten cuando una pantalla bien hecha les resuelve el día (el arqueo, la sugerencia de activación, la lista de surtido, Seguimiento de hoy).

Los quince registros de **intensidad máxima (5)**, con su disparador textual:

| Persona | Emoción | Disparador |
|---|---|---|
| Paulina | resignación | *"cinco intentos en dos días distintos; ya no es que yo no sepa, es que no funciona"* |
| Paulina | impotencia | *"tres intentos, cero mensajes de error y cero resultado: no hay nada más que yo pueda hacer"* |
| Paulina | frustración | *"cuatro intentos de guardar mi cuenta de banco y ni un solo mensaje del sistema"* |
| Paulina | desconfianza | *"si ni siquiera puedo guardar mi cuenta de banco, no sé cómo me van a pagar el 10 de abril"* |
| Paulina | desconfianza | *"el consejo de la pantalla y la regla de puntos se contradicen entre sí"* |
| Paulina | enojo | *"faltan $124.20 de los $259.20 que la pantalla me prometió en marzo y nadie me explicó nada"* |
| Fabiola | frustración | *"cuatro veces guardé mi CLABE, el sistema mismo me manda correos y avisos diciendo que la registre, y no se guarda ni me dice por qué"* |
| Ximena | enojo | *"me dijeron «ya tienes comisiones a tu favor» con cero pesos y cero personas en mi red, para pedirme mi CLABE"* |
| Ernesto | miedo | *"pagué $609 y la pantalla se quedó en blanco; no sé si me cobraron o no"* |
| Ernesto | frustración | *"hice exactamente lo que la página me pidió, palomeé «Guardar esta dirección» y de todos modos no la guardó"* |
| Mireya | preocupación | *"entregué mercancía física y el inventario no se movió en ninguna sucursal; el faltante va a aparecer en mi tienda"* |
| Alma | desconfianza | *"la pantalla que se llama Estadísticas me da cero ventas en un mes donde sí hubo nueve pedidos"* |
| Alma | frustración | *"es exactamente el número que vine a cuadrar y la pantalla me lo esconde detrás de una palabra en inglés"* |
| Renata | desconfianza | *"el archivo que iba a mandar como constancia del cierre de marzo se llama agosto 2026 y se contradice a sí mismo"* |
| Renata | frustración | *"la pantalla de configuración mide 12 mil caracteres y los niveles de comisión están hasta el último renglón"* |

**Siete de los quince son la CLABE.** Los otros ocho son, sin excepción, alguna pantalla de dinero contradiciéndose a sí misma.

### 5.5 A qué se les parece

No hay que maquillarlo: las metáforas que escogieron son duras y consistentes.

> *"a una tienda de suplementos bien hecha con un negocio de multinivel encima; como si dos apps distintas compartieran la misma pantalla"* (Mariana)
> *"a un catálogo de farmacia bien hecho al que le injertaron encima el discurso de una junta de red de ventas de las de antes"* (Ximena)
> *"a la página bonita de una marca de suplementos que todavía no ha abierto: el escaparate está terminado y la trastienda no"* (Aurora)
> *"a una tienda bonita montada por alguien que nunca pensó qué pasa cuando algo sale mal"* (Julio)
> *"a un tianguis con confeti: bonito de lejos, pero con tres letreros distintos para la misma cosa (PC, VP, VG, PV, PG) y felicitaciones que brincan encima cuando lo que quiero es una cifra"* (Paulina)
> *"a un ERP heredado al que le fueron colgando pantallas: cada pieza por separado está bien escrita, pero nadie se sentó a pensar cómo es el día 10 de quien cierra el mes"* (Renata)
> *"a un sistema de almacén al que le colgaron la parte del dinero al final: se nota clarísimo quién lo pensó (el que despacha) y quién no (el que los cobra)"* (Alma)
> *"al sistema de la farmacia donde trabajé, pero sin el manual pegado en la pared"* (Mireya)
> *"a un sistema de bodega hecho por alguien que sí ha empacado cajas, pero al que le faltó una semana para terminarlo"* (Toño)

Dos de ellas son elogios encubiertos y conviene leerlos así: Toño y Alma están diciendo que **se nota cuando alguien que hace el oficio diseñó la pantalla**. Fabiola lo dice en positivo: *"los colores olivo y el tipo de letra me dan cosa de spa, no de multinivel gritón, eso me gustó"*.

### 5.6 ¿Volverían?

Doce sí, y ninguno sin condición.

| Persona | Volvería… |
|---|---|
| Mariana | *"sí, si el bote sirve, pero comprando rápido y sin leerles nada del modo socio"* |
| Ernesto | *"sí… pero no sin que alguien me ayude"* |
| Ximena | *"sí, cada mes, pero solo a comprar mi colágeno y mi proteína con el 10 %; a invitar gente no"* |
| Julio | *"para volver a comprar sí… pero ya no gastaría $800 en un solo artículo sabiendo que si llega roto no hay a quién reclamarle"* |
| Aurora | *"sí, pero solo si me llega bien la factura; si no me llega, no vuelvo y tampoco se la paso a mis pacientes"* |
| Fabiola | *"sí, por el producto… pero no le voy a decir a mis clientas que se metan hasta que sepa que sí pagan"* |
| Paulina | *"sí, porque ahí está mi dinero y mi red, no porque me guste entrar"* · *"Si en mayo tampoco me depositan, dejo de invitar"* |
| Mireya | *"pues sí, es mi trabajo, pero mañana llego con una libreta para apuntar lo que el sistema no guarda"* |
| Toño | *"sí… pero solo entro por Despacho en bloque, lo demás lo esquivo"* |
| Gaby | *"sí, todos los días… pero voy a seguir con mi libreta para saber quién dijo qué"* |
| Renata | *"la tengo que usar, no es cuestión de querer; pero no cierro un mes con ella sin sacar cuentas en papel aparte"* |
| Alma | *"sí, es mi trabajo, pero el cierre lo voy a seguir armando en Excel aparte"* |

**Cinco de las doce dijeron que van a llevar una libreta, un Excel o un papel aparte.** Los cinco son el personal completo salvo Toño, que directamente dijo que esquiva el resto del sistema. Y el riesgo de negocio está dicho con todas sus letras por las dos socias con red: Fabiola no invita hasta saber que pagan, Paulina deja de invitar si mayo tampoco deposita.

---

## 6. Qué mejoró de verdad desde las rondas 1 a 5

Comparación contra [22](22-diarios-inquietudes-friccion-automatizacion.md) §5 (los 17 puntos de fricción por costo) y [23](23-implementacion-23-propuestas.md) §1 (las 23 propuestas).

### 6.1 Lo que se construyó y esta ronda confirma que funciona

| Propuesta de [22] §7 | Evidencia de esta ronda | Veredicto |
|---|---|---|
| **13 · Despacho en bloque** | Toño despachó 3 pedidos en **82 s y 3 clics**, con lista de surtido, semáforo, "Todo alcanza: puedes despachar 3 pedido(s)" y lote DSP-89056D5E94; verificó que el inventario bajó exacto y sin duplicar, y que a los tres clientes les llegó su correo con guía. Facilidad 6 | **Cumple.** Su queja es que está escondida: *"es la mejor pantalla del sistema"* |
| **5 · Completa tu activación** | Fabiola: *"Activación: 20 VP netos · llevas 0 · este pedido suma 18.9. Te faltan 1.1 VP para activar el mes"*. Lo llamó **lo mejor que tiene la plataforma** y es lo que la hizo comprar. Ximena elogió el mismo bloque | **Cumple.** El único cambio pedido: avisar también cuando el descuento *tumba* la activación |
| **2 · Plan publicado** (`#/modo-socio`) | **Mejor pantalla de la ronda para cuatro personas y elogiada por seis.** `/catalog/plan` se pidió 61 veces. Julio: *"la única que explica con números y sin trampa"*; incluye una advertencia contra la propia empresa | **Cumple cuando se llega.** No está enlazada desde la tienda, el carrito ni el correo de bienvenida, y publica un equivalente en pesos falso (§3.10) |
| **16 · Arqueo de caja** | Mireya cerró CUT-8D11C495 contando por denominaciones, con motivo escrito, y mandó el comprobante por correo desde la misma pantalla. *"«No es una falta: es lo que pasó», que me quitó el miedo de reportar una diferencia"* | **Cumple el arqueo, falta el paso anterior**: sin "abrir turno" arrojó $540 de sobrante donde había $40 (§3.8) |
| **15 · Seguimiento de hoy** | Gaby hizo su jornada completa —4 contactos, 4 notas, una ficha de invitada con 2 pedidos ligados, 4 asignaciones— **en quince minutos**, con la facilidad más alta de la ronda (4.6) y confianza 4.5 | **Cumple.** Dos huecos: no está en el menú y falta la plantilla 'activa' (§3.14) |
| **8 · Botones que explican por qué** | Renata dedicó medio párrafo de su diario a elogiarlo: *"Cada botón apagado te dice por qué está apagado"*. Alma igual. Mireya entendió por un texto de ayuda por qué la tarjeta no entra al cajón | **Cumple**, y es de lo más citado en positivo por el personal |
| **23 · Resumen de turno** | Existe y se pidió 337 veces; con el usuario de Toño del 3-mar dice literalmente los 3 pedidos con sus guías | **Cumple para armarlo, no para entregarlo**: no tiene botón para mandárselo al gerente (el corte de caja sí lo tiene), así que Toño se lo mandó a Renata por WhatsApp |
| **12 · Pagos del mes** | La tabla, el CSV, el lote y "Pedir CLABE" existen y el servidor responde bien; el bloqueo sin CLABE está correctamente explicado y **no deja colar un pago fantasma** (Renata lo verificó a propósito) | **No sirvió el día 10**: no está en el menú, pierde el mes al recargar y no muestra lo pendiente (§3.1, §3.4, §3.9) |
| **9 · Sucursal por defecto** | Toño la fijó y la verificó: *"Listo: tu bodega por defecto ahora es Bodega Central. Stocks, Caja y Despacho abrirán con ella"* | **Cumple para almacén.** Para caja, Mireya tuvo que descubrir sola que su POS venía puesto en otra sucursal |
| **18 · Devolución por producto** | Existe, con líneas, motivos y reembolso por neto de línea | **No se alcanzó desde el cliente** (§3.12): el botón solo aparece en estado "entregado" y no se explica |
| **14 · Suscripción mensual** | Completa y con un texto que Ernesto calificó de perfecto: *"Nada se cobra solo. Puedes pausar o cancelar cuando quieras"* | **No se pudo usar**: depende de una libreta de direcciones que el sistema no sabe llenar. **Cero suscripciones en todo marzo** |
| **17 · Factura** | Datos fiscales completos y correctos en el checkout; Aurora capturó RFC, régimen 612 y uso G03 sin un tropiezo, y Alma llamó a esa pantalla la mejor del sistema | **Se queda en "solicitada" para siempre**: sin bandeja, sin folio, sin acuse al cliente. Dos facturas del 4-mar llevan 37 días |
| **21 · Conciliación** | Existe, con texto de ayuda que Renata calificó de claro | **Insuficiente**: 72 h fijas cuando el endpoint acepta 90 días, y no se puede cargar el estado de cuenta |
| **1 · Modo "solo cliente"** | Existe por dentro | **Sigue siendo la queja número uno de los clientes**: la tienda habla de PC, el carrito de metas, el comprobante ofrece "Activar modo socio" y el modo socio se ofrece 4-5 veces por sesión |

### 6.2 Lo que sigue igual desde [22] §5

| Fricción de [22] §5 | Estado en [22] | Estado hoy |
|---|---|---|
| #3 Canasta de 20 VP a mano | Parcial | **Corregido de verdad.** El aviso del carrito con producto sugerido salvó a Fabiola de pagar $990 sin activarse |
| #4 Envío "Gratis" que se vuelve $129 al poner el CP | Abierto | **Sigue abierto y ahora con un texto que promete lo que no hace** (§3.7b). Tres personas |
| #6 Cantidades duplicadas en el carrito | "Corregido (ronda 4)" | **Reabierto en la tarjeta del catálogo**: corregido para el producto destacado, intacto en el resto (§3.5) |
| #9 Devolución | Parcial → "Implementado" | **Abierto desde el lado del cliente** (§3.12) |
| #10 Rutas y sesión del back office | Parcial | **Abierto y es de los que más minutos cuesta**: todo el admin vive en `#/admin`, sin URL por pantalla (§3.9) |
| #11 Botones "Ver" duplicados / clics al elemento equivocado | Abierto | **Vivo y reproducido 8 veces** entre dos empleados, uno de ellos con una clienta enfrente (§3.5) |
| #12 Stock por defecto en la sucursal equivocada | Parcial | **Corregido para almacén, abierto para caja** |
| #16 Tres módulos, tres cifras del mismo mes | "Corregido en su mayoría" | **Reabierto**: $10,088 contra $0 en la misma pantalla, $259.20 contra $135, "Activas 0" con tres avisos activos, 50 de VG contra 25+24 |
| §3.1 "Me metieron a un MLM sin decírmelo" (9 personas en [22]) | Abierto → "Implementado" en [23] | **Sigue siendo la queja número uno**: Mariana, Ernesto, Ximena, Julio y Aurora lo dicen otra vez |
| §3.2 No se puede calcular el negocio | Parcial → "Implementado" | **Corregido para quien llega a `#/modo-socio`, intacto para quien no** — y con un número falso en el dato más importante |
| §3.3 Comisiones bloqueadas | Parcial | **Cumple la mecánica y falla la comunicación**: Paulina recuperó sus $259.20 activándose, pero tardó ~20 min en entender por qué estaban bloqueadas y nadie le avisó cuando se desbloquearon |
| §3.4 Silencio después de pagar | Parcial | **Los correos transaccionales funcionan y llegan al minuto** (verificado por Mariana, Ernesto, Julio, Toño). Lo que falta es el contenido: no dicen qué compraste ni a dónde va |
| §4.7 Contactar a quien no quiere | "Corregido" | **Se sostiene.** Gaby no reportó ni un problema de "no contactar", notas ni bitácora — salvo la firma con número |

### 6.3 Qué cambió respecto de la corrida anulada del [24]

Esta es la comparación que da sentido a repetir la ronda. Las cifras del [24] miden una aplicación sin backend; las de aquí, el producto.

| Métrica | [24] (anulada, sin backend) | **25 (esta corrida)** | Lectura |
|---|---|---|---|
| Tareas logradas | 65 de 129 (**50 %**) | **82 de 126 (65 %)** | 15 puntos eran el entorno |
| Facilidad media | 2.9 / 7 | **3.6 / 7** | |
| Estética / recomendaría | 4.9 / 3.7 | **5.3 / 5.2** | |
| Coherencia | 3.5 | 3.8 | **prácticamente igual: es del producto** |
| Legibilidad | 6.7 | 6.3 | igual |
| Emociones | 148 (desconfianza 42, frustración 31) | **140 (desconfianza 31, frustración 24)** | menos, pero el ranking no cambia |
| Atorones / reintentos / recargas | 139 / 62 / **27** | **92 / 47 / 8** | las recargas eran el error de red |
| Reflexión antes de actuar | 14,060 s | **11,897 s** | sigue superando al tiempo de tarea |
| Rutas alcanzadas | 39 de 79 | **42 de 79** | |

**Hallazgos del [24] que desaparecieron aquí** (eran del entorno, no del producto):

- El mensaje de error crudo `Http failure response … 0 Unknown Error` que frenó en la puerta a 11 de 12 personas: **no apareció ni una vez**.
- **Las cuatro clientas que pagaron dos veces**: no ocurrió. Los únicos dos pedidos gemelos de esta ronda son dos compras reales de Aurora, verificadas con dos `paymentId` distintos.
- Las "pantallas que inventan datos cuando el servidor no responde", incluidos rangos comerciales veinte veces más bajos: no se reprodujeron.
- El "tablero que sube cuando reembolsas".

**Hallazgos del [24] que se confirman aquí, ya sin excusa de entorno:**

- **Las cinco funciones nuevas fuera del menú** (§3.9, §1.2). Confirmado por cinco personas distintas.
- **La falta de un estado "confirmando tu pago"** después de la pasarela (§3.7c). Sin cobros dobles esta vez, pero con dos registros de miedo de intensidad máxima.
- **Los dos relojes del panel** (corte con y sin sesión: 26d contra 21d) y, más grave, **el reloj del navegador decidiendo el mes contable** (§3.4).
- **El día de pago sin día de pago** (§3.1): aquí quedó medido hasta el final, con marzo cerrado en $0.00.
- **La caja que no se puede abrir** (§3.8), **los permisos que dan ADMIN a todos** (§3.13) y **el panel del cliente como página infinita con menú de anclas** (§3.9).
- **El vocabulario sin glosario** (§3.10) y **la ausencia de canal interno**: el reporte de Toño y la autorización de Mireya salieron por WhatsApp, igual que en [22] §6.

### 6.4 Lo que esta ronda encontró y ninguna anterior había visto

1. **La CLABE no llega al servidor** (§3.1). Diez intentos, dos pantallas, cero peticiones. Ninguna ronda anterior había puesto a dos socias distintas a capturarla el mismo mes.
2. **Lo que se compra como invitado nunca suma** (§3.3). Nunca se había simulado a tres clientes comprando sin cuenta y a una coach creándoles ficha después.
3. **El aviso "Ya tienes comisiones a tu favor" con $0** (§3.2) — el defecto que más credibilidad cuesta por línea de código.
4. **El recibo que no repite nada de lo elegido** (§3.6): sucursal, productos, factura, RFC. Nunca se había medido una compra con recolección **y** factura en la misma orden.
5. **La cantidad de la tarjeta que suma una pieza de más**, un bug ya corregido en otro componente y no propagado (§3.5).
6. **La comisión a la que se le reescribe la fecha al recalcular** (§3.4).
7. **El coach al que el sistema le propone el mensaje contrario** (§3.14).
8. **Entregar en mostrador un pedido reservado en otra sucursal descuenta la sucursal equivocada, en silencio** (§3.8).

---

## 7. Propuestas priorizadas

Cada una con la evidencia que la sostiene. Se marca **[P]** cambio de pantalla, **[F]** cambio de flujo, **[N]** decisión de negocio.

### 7.1 Esta semana — alto impacto, esfuerzo bajo

| # | Qué | Tipo | Evidencia |
|---|---|---|---|
| 1 | **Que "Guardar CLABE" guarde.** Quitar el paso de confirmación (una CLABE de 18 dígitos ya validada no lo necesita), guardar directo y poner el estado **en el propio campo** (*guardando… / guardada, termina en 6789 / no se pudo*), no en un toast global al fondo de la página. Unificar los dos formularios en uno | **[F]** | Paulina 5 intentos, Fabiola 5, marzo cerrado en $0.00; 7 de las 15 emociones de intensidad máxima. *"El único dato que sirve para que YO cobre es justo el que no se guarda"* (`fabiola-2027-03-04.md`) |
| 2 | **Separar los dos textos del aviso de CLABE**, como ya se separan en el correo: al activarse, *"desde hoy las compras de tu red te generan comisiones"*; "Ya tienes comisiones a tu favor" **solo con monto confirmado**. O apagar `clabeReminderOnActivation` y cumplir lo que promete `#/modo-socio` | **[P]** | Ximena y Fabiola con $0; Renata desde el otro lado. *"Un solo número falso en la pantalla del dinero le tira la credibilidad a todos los números buenos"* |
| 3 | **Sacar Nombre, Teléfono y Correo del bloque de envío**: son datos de contacto del pedido, no de la dirección. Que se pidan siempre. Y que el error apunte al campo | **[F]** | Aurora, 2 intentos y un rodeo; sus dos pedidos de mostrador quedaron con `recipientName: null` y `phone: null` |
| 4 | **Poner Comisiones y pagos en el menú** (FINANZAS → Comisiones y pagos) y **dar URL propia a cada pantalla del admin** (`#/admin/comisiones`, `#/admin/pedidos`…). Lo mismo con Seguimiento de hoy, Despacho en bloque y Resumen de turno, con el nombre del oficio | **[P]** | Alma buscó "Comisiones" 7 veces en el menú; Renata calificó la facilidad con 2/7; 4 de 5 empleados perdieron su primer cuarto de hora. **Es el cambio más barato de la lista y el que más minutos devuelve** |
| 5 | **Un paso de "abrir turno"** que escriba el fondo inicial cuando no hay corte previo, y decir en la pantalla *"esta caja nunca ha cerrado un corte: captura el fondo con el que arrancas"* en vez de $0.00 sin explicación | **[F]** | Mireya: sobrante falso de $540 y **$1,040 toda la noche en el cajón** |
| 6 | **Validar el código de autorización al salir del paso 3**, no en el paso 4, con el estilo de los demás botones apagados; y ofrecer ahí la salida honesta (*"si no tienes el código, deja todo como fondo y avisa a tu gerente"*) | **[P]** | Mireya: HTTP 403 con el dinero contado en la mano y el turno terminado |
| 7 | **Que el recibo repita lo elegido**, palabra por palabra: productos con precios, desglose, *"Recoges en Sucursal Guadalajara, Av. Chapultepec 480"* con horario, y *"Factura solicitada a nombre de… RFC…"* con enlace para corregirla. Que el estado diga "Listo para recoger" y no "Ruta de entrega". Lo mismo en el correo | **[P]** | 5 personas. Aurora abandonó buscando su RFC; Paulina lleva 21 días sin saber en qué tienda está su pedido |
| 8 | **Pie de página con correo, WhatsApp y horario en todas las pantallas**, y una página de sucursales; que `#/ayuda` y `#/contacto` lleven a algún lado. Y corregir el año | **[P]** | Julio tuvo que crear cuenta para hallar el teléfono de la tienda a la que ya le había pagado $1,209; Aurora probó cuatro rutas |
| 9 | **Que el aviso de privacidad no tape la primera pantalla** (banner inferior no bloqueante, o modal centrado también en móvil con una X) y **que diga la verdad por etapas**, copiando el cuadro que ya hace bien `#/modo-socio` | **[P]** | 11 de 12 personas perdieron tiempo con él; Aurora estuvo a punto de irse por la frase "No te pedimos datos bancarios ni fiscales" |
| 10 | **Aplicar en la tarjeta del catálogo el patrón de cantidad del producto destacado** (borrador local que solo entra al carrito al pulsar Agregar) | **[P]** | Paulina: 3 Klinhart en vez de 2, $1,440, casi le tumba la activación por la que había gastado el dinero |
| 11 | **Escribir la plantilla 'activa'** del seguimiento y, mientras no exista, no proponer ninguna en vez de proponer la contraria. Corregir la ruta "Mi cuenta → Datos bancarios" de la plantilla `clabe_pendiente` (no existe: es Mi perfil) | **[P]** | Gaby, a un clic de mandarle "hace tiempo que no te vemos" a un cliente con el pedido entregado el viernes |
| 12 | **Resolver el id a nombre en la bitácora de contactos** | **[P]** | *"Si mañana Mireya lee «1803978000111», no sabe si fui yo o Alma, y le vuelve a escribir a Julio. Para eso, me sigo yendo con mi libreta."* (`gaby-2027-03-08.md`) |
| 13 | **Un "estamos confirmando tu pago"** al volver de la pasarela, con el botón deshabilitado | **[P]** | Dos registros de miedo/susto de intensidad máxima; es además el seguro contra el cobro doble que el [24] destapó |
| 14 | **Borrar el "(más o menos $1,000 de compra a precio de lista)"** de la activación y del cálculo de generaciones; poner el rango honesto o la calculadora del carrito, que ya existe y funciona bien | **[P]** | Ximena midió el hoyo: de $933 a $1,605. *"Es el número más importante del plan, en la página que se llama «con los números reales»"* |

### 7.2 Este mes — alto impacto, esfuerzo medio

| # | Qué | Tipo | Evidencia |
|---|---|---|---|
| 15 | **Reproducir y arreglar el botón "Ver" de Pedidos**, y de paso dar al pedido una URL propia (`#/admin/pedido/:id`) en vez de un acordeón dentro de una pantalla sin dirección. Primer sitio donde mirar: la tira de pestañas se recrea en cada ciclo de detección de cambios | **[F]** | 8 reproducciones entre dos empleados. Por ahí pasan el detalle, los datos fiscales y el bloque de facturación |
| 16 | **Recalcular el mes contable al ligar una ficha de invitado** (o al registrarse alguien con un correo que ya tiene pedidos pagados): VP, volumen neto, tramo y activación | **[F]** | Julio, Mariana y Aurora en cero con $5,038 pagados entre los tres; "0 % recompra"; la mejor clienta del mes como inactiva |
| 17 | **Que el servidor mande la lista de periodos y el mes por omisión** (los meses que de verdad tienen comisiones, con el mes contable vigente marcado) a Pagos del mes, Estadísticas y el exportador. Y que ninguna pantalla se plante sola en un mes sin datos sin decirlo | **[F]** | Renata reprodujo tres veces la pérdida de marzo; Alma casi reporta que marzo cerró en ceros |
| 18 | **Añadir a Pagos del mes "Por confirmar" y "Bloqueadas"** con el pedido que las frena y sus días, y un total de comisión reconocida del mes | **[P]** | El ledger ya tiene los números ($135 + $124.20); Alma acabó con tres cifras del mismo concepto |
| 19 | **Que `order_lambda` guarde la dirección cuando venga `saveShippingAddress`** (con su etiqueta), y que la suscripción deje capturar una dirección ahí mismo | **[F]** | Ernesto; cero suscripciones en marzo; 7 de 7 clientes con `addresses=0` |
| 20 | **Un filtro/pestaña "Factura solicitada" en Pedidos y su contador en Acciones urgentes.** No hace falta módulo nuevo: `invoiceStatus` ya está en la fila y el bloque para marcarla emitida ya existe | **[P]** | Dos facturas del 4-mar con 37 días; Alma las armó abriendo pedido por pedido |
| 21 | **Columna de antigüedad en pedidos pagados sin envío**, ordenable y en rojo, y que la alerta diga los días. Separar los pickup del contador de envíos | **[P]** | *"Ninguna columna dice cuántos días llevan parados. 37 días se ven igual que 1 día."* (`renata-2027-04-10.md`); de ese pedido colgaba la comisión de una socia |
| 22 | **Buscador en la tienda** (nombre, etiquetas y descripción: "omega 3" ya vive en el producto) y **ruta propia por producto** `#/tienda/producto/:id` | **[F]** | Ernesto leyó 13 nombres uno por uno con vista cansada; Julio no tiene enlace que mandarle a un cliente; Mariana y Aurora creyeron que "Ver producto" no servía |
| 23 | **Enlazar `#/modo-socio` desde donde nacen las dudas**: el "13 PC · $53.85/PC" de cada tarjeta, el bloque de metas del panel y el correo de bienvenida de socio. Y arreglar el enlace "Cómo se calculan", que hoy devuelve a la misma página | **[P]** | 4 personas la eligieron como mejor pantalla y **todas llegaron tarde** |
| 24 | **Botón "Devolver / Llegó dañado" siempre visible** con su condición explicada, y mención de la devolución parcial en el texto de "Cancelar orden" | **[P]** | Julio: 17 clics, 9 pantallas, 341 s, facilidad 1, y se quedó con la proteína rota |
| 25 | **Vocabulario único en español para los estados del pedido**, en las cuatro pantallas y en el correo; fechas escritas como las escribe la gente; desglosar `mixed` en efectivo y tarjeta; quitar o completar "Mínimo requerido"; neutralizar el género | **[P]** | Julio contó 4 nombres del mismo estado; Alma: emoción de intensidad 5 por la palabra `mixed`; "Mínimo requerido" recogido 3 veces como error en pantalla |
| 26 | **Exponer el rango de fechas en la conciliación** (72 h / 7 días / este mes / desde-hasta) y dejar de pisar el `finishedAt` del servidor con el reloj del navegador | **[P]** | El endpoint acepta 90 días; a Renata le encargaron revisar todo marzo y obtuvo "Revisados 0" |
| 27 | **Recortar de verdad el menú y las acciones por rol**, y mostrar el rol real ("Caja", "Almacén", "Coach") en vez de ADMIN | **[F]** | Los tres empleados no gerenciales lo pidieron por su cuenta |
| 28 | **Stocks: tabla producto × sucursal con totales, mínimo por producto, foco rojo y su entrada en Acciones urgentes**, más el enlace a la bitácora que la propia pantalla promete. Inventario arriba, alta de bodega detrás de un botón | **[P]** | Toño: *"el día que Guadalajara se quede en 1 pieza, nadie se va a enterar hasta que un cliente pague y no haya"* |
| 29 | **Un solo origen del corte de mes, del servidor**, igual con y sin sesión, con la fecha en letras junto al reloj | **[P]** | 7 de 12 personas; Ximena midió 26d y 21d en el mismo minuto |
| 30 | **Botón para mandar el resumen de turno al gerente**, como ya lo tiene el corte de caja | **[P]** | Toño se lo mandó a Renata por WhatsApp; Mireya no tuvo dónde reportar el sobrante |
| 31 | **Cotizar el envío con CP + estado** (que es lo que el backend necesita) y cambiar el texto; o publicar la tabla de tarifas por estado antes de pedir datos. Y que el Total del carrito incluya el envío o se llame Subtotal | **[F]** | 3 personas; Mariana abandonó con facilidad 2 y escribió a soporte a las 21:46 |
| 32 | **Conservar el `createdAt` de la comisión al recalcular** (o mostrar la fecha del pedido y guardar aparte un `recalculatedAt`), y decir en la fila por qué cambió | **[P]** | Paulina: *"Le movieron la fecha a mis comisiones"* |
| 33 | **Que el panel de cada rol abra en la pantalla de esa persona** (cajera en POS con su sucursal, almacén en Despacho, coach en su lista) y que Pedidos abra en la primera pestaña con trabajo; que el buscador busque en todos los estados | **[F]** | Toño leyó a la vez "Pagados 3" y "0 pedidos — No hay pedidos en este estado": *"si yo fuera menos necio me voy a la bodega a barrer"* |
| 34 | **Correo el día 10, siempre**: *"Te depositamos $135 a tu CLABE terminación 6789"* o *"No te pudimos depositar porque nos falta tu CLABE — haz esto"*. Y correo cuando una comisión bloqueada se desbloquea | **[F]** | Paulina: *"Abrí el correo esperando un «te depositamos». Mi último correo es del 20 de marzo. Nada"* |
| 35 | **Que el exportador de dispersión no se bloquee del todo**: exportar a quienes sí tienen CLABE y listar aparte a las que faltan | **[P]** | Alma perdió el mes entero por una sola socia |

### 7.3 Decisiones de negocio, antes de escribir código

| # | Qué hay que decidir | Quién lo pidió |
|---|---|---|
| 36 | **Publicar ganancias reales y un simulador del plan.** Hoy la única referencia es "$1,000 → $100", que no se parece a lo que gana una socia real. Ximena calculó sola que BRONCE ($500/mes) requiere unos 180-225 socios activos | Ximena: *"para recuperar los ~$1,350 que tengo que gastar cada mes necesito diez personas comprando $1,350 cada una, todos los meses"*. Y: *"Ese número contesta solo. No voy a poner a mis amigas ahí."* |
| 37 | **Sobre qué base se calcula la comisión**: precio de lista o neto pagado. Hoy es el neto sin envío ($135 sobre $1,350, no sobre $1,500) y **no está escrito en ningún lado** | Ximena lo buscó en 3 pantallas; el enlace "Cómo se calculan" la devolvía a la misma página |
| 38 | **Retención de impuestos y monto mínimo de depósito.** Hoy no hay ninguno de los dos configurados y se paga el bruto el día 10 | Ximena |
| 39 | **Quién paga el envío de regreso de una devolución**, cuántos días hay y si se piden fotos. Nada de eso está configurado | Julio, que además preguntó las cuatro cosas por WhatsApp |
| 40 | **De quién es la responsabilidad de contactar a un cliente con patrocinadora**: de la coach o de la patrocinadora. Y qué es un "ejecutivo por omisión" — hoy las siete personas del sistema tienen ejecutivo vacío | Gaby **dejó a dos clientas sin contactar** por no saberlo |
| 41 | **Qué se hace con los documentos marcados "Requerido"** (constancia fiscal, INE, CURP): para qué son, con qué fecha, con qué consecuencia y quién los revisa. Hoy no bloquean nada y **la socia creyó que sí** | Paulina: *"«CARGA DE DOCUMENTACIÓN — Constancia de situación fiscal: Requerido · INE: Requerido · CURP: Requerido». Requeridos. Nadie me lo dijo nunca tampoco"* |
| 42 | **Si el objetivo del mes debe cambiar solo de comprar a reclutar** en el minuto del pago. Es una decisión de diseño de producto, no un bug | Ximena: *"Pagué mi proteína y la pantalla ya me está empujando a reclutar. Así empieza exactamente lo que me pasó hace ocho años"* |
| 43 | **Publicar el nombre completo en el Cuadro de Honor**, y si debe haber casilla para no aparecer. El aviso de privacidad no lo menciona | Fabiola, que sale con nombre y dos apellidos mientras las demás salen con inicial |
| 44 | **Periodicidad de la suscripción** (cada 1, 2 o 3 meses) y qué hacer cuando el cliente no tiene sucursal en su ciudad | Ernesto: frasco para dos meses, envío solo mensual, y Guadalajara preseleccionada a 900 km de su casa |

---

## 8. Cómo se midió

### 8.1 El arnés

- **Mundo verificado antes de empezar.** `bash sim/comprobar.sh` comprobó, en este orden: `environment.ts` apuntando al backend local, backend en `:4400` respondiendo con el reloj del mundo (`2027-04-10`), frontend en `:4321`, **el bundle servido sin URLs de AWS**, catálogo sembrado (14 productos) y credenciales presentes. Esta comprobación es exactamente la que faltó en el [24] y es la razón de que esta corrida sea la válida.
- **Una persona, un navegador, un turno.** Cada agente abrió un solo navegador, siguió su ficha de `sim/agentes/`, no leyó código y averiguó todo desde la pantalla. Los empleados usaron `sim/credenciales.json`.
- **Lo que cuenta el arnés solo**: clics, teclas, envíos de formulario, campos tocados, cambios de pantalla, recargas, retrocesos, **milisegundos entre la carga de cada pantalla y el primer clic** (el "impuesto de comprensión"), errores visibles en pantalla y mensajes de consola con su código HTTP.
- **Lo que registra la persona a mano**: qué quería en cada tarea y si lo logró, sus pensamientos con el tiempo transcurrido entre uno y otro (de ahí salen los segundos de reflexión), dudas con la pantalla donde nacieron, atorones, reintentos, preguntas a soporte o a un superior, facilidad (1-7) y confianza en que quedó guardado (1-5) por tarea, y al cerrar: emoción con intensidad y disparador, calificaciones estéticas, mejor y peor pantalla, tres adjetivos, a qué se le parece y si volvería.
- **Fuentes cruzadas**: `sim/diarios/*.md` (12 diarios), `sim/metricas/*.json` (bitácoras crudas), `sim/helpdesk.md` (27 filas), `sim/servidor.log` (peticiones reales), y la API consultada directamente por la verificación.
- **Las frases textuales** de este informe se citan con el archivo de diario de la persona entre paréntesis (`sim/diarios/*.md`); son literales de ese diario. Las que no llevan archivo salen de la bitácora cruda del turno (`sim/metricas/*.json`), de `sim/helpdesk.md` o son texto de la propia pantalla.
- **La verificación** revisó cada síntoma contra el código y contra la API y emitió tres veredictos: **confirmada** (38), **percepción** —existía y no se halló— (7) y **dato o arnés** (4). Los cuatro últimos están aislados en §3.16 y no cuentan en ninguna cifra de esfuerzo.

### 8.2 Lo que el arnés metió de su cosecha

Se dice para que nadie lo lea como defecto del producto — y para señalar qué parte **sí** lo es:

1. **El reloj del navegador iba en 2026-09-04 y el mundo en 2027-04-10.** Eso agranda tres hallazgos: el hueco de meses del selector de comisiones, los "0 días sin comprar" de todos los clientes y el mes por omisión de Estadísticas. **El defecto de producto es real** —fechar el negocio con el reloj del cliente y disfrazar un negativo con `Math.max(0, …)`— pero su tamaño en esta ronda está inflado por el arnés.
2. **Los turnos no corrieron en el orden del calendario de la historia.** Julio reclamó su devolución antes de que Toño despachara, así que vio su pedido en "Pago registrado" con razón. Para la próxima conviene ordenar los turnos según el calendario o mover el reloj con `sim/dia.sh` entre personas.
3. **La paquetería se llama "Simulada"** y así sale en los correos.
4. **Ocho de trece fichas de producto están vacías**: es la semilla, no la plataforma.
5. **Dos pedidos gemelos de Aurora**: su guion recorrió el checkout dos veces y su diario solo narra el primero.

### 8.3 Métricas que conviene añadir la próxima

1. **Tiempo hasta el primer resultado útil** por tarea (no solo si la logró): cuántos segundos pasan entre "quiero X" y el primer dato en pantalla que sirve para X. Distinguiría el "no lo encontré" del "lo encontré y no me sirvió".
2. **Peticiones por tarea**, cruzando `sim/servidor.log` con la línea de tiempo de la persona. Habría delatado la CLABE en el primer intento en vez de en el décimo.
3. **Camino recorrido**: la secuencia de rutas por tarea, para medir cuántas pantallas se visitan **de más**. Julio tocó nueve para no devolver una proteína.
4. **Scroll antes del primer clic**, no solo tiempo. Media docena de hallazgos de esta ronda ("Recibe esto cada mes", el modal de CLABE, el inventario debajo de dos formularios) son problemas de profundidad de página, y hoy no se miden.
5. **Contradicciones detectadas**: un contador de "dos pantallas del sistema me dieron cifras distintas del mismo dato", que es el disparador número uno de la desconfianza (§5.4) y hoy solo aparece en prosa.
6. **Reintentos ciegos**: veces que la persona repite exactamente la misma acción porque el sistema no le dijo nada. Diez de esos, todos de la CLABE, valen más que cualquier promedio.
7. **Emoción al cerrar cada tarea**, no solo cuando la persona lo anota. Serviría para saber si el alivio de una pantalla bien hecha compensa la desconfianza de la anterior — hoy sabemos que las doce personas sintieron las dos.
8. **Un turno de retorno**: la misma persona, dos semanas después. Cinco de doce dijeron que volverían con libreta o Excel aparte; medir si esa libreta se queda es medir si el producto se adopta o se tolera.
