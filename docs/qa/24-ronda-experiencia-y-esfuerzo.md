# 24 · Sexta ronda: cuánto cuesta usarlo y cómo se siente

Las rondas 18 a 21 preguntaron *¿funciona?*. La [22](22-diarios-inquietudes-friccion-automatizacion.md) preguntó *¿qué les preocupa?* y la [23](23-implementacion-23-propuestas.md) construyó 23 propuestas. Esta ronda pregunta otra cosa: **cuánto le cuesta a una persona sacar adelante lo que vino a hacer, y cómo se siente mientras lo hace.**

Doce personas trabajaron con la plataforma entre el 2 de marzo y el 10 de abril de 2027 del mundo simulado: siete de fuera (clientas, prospectas y socias) y cinco del personal. Ninguna había visto el producto antes, ninguna leyó código, y cada una escribió su diario al terminar (`sim/diarios/`, 14 archivos contando los dos días de Paulina y el cierre de soporte). El arnés contó por su lado clics, teclas, pantallas, recargas y segundos; la persona registró a mano lo que pensaba, lo que dudaba, dónde se atoró y qué sintió (`sim/metricas/*.json`). Las 31 preguntas que no pudo contestar la pantalla quedaron en `sim/helpdesk.md` con la respuesta de Daniel (soporte) o de la gerente. Una verificación posterior revisó cada síntoma contra el código y contra la API, y clasificó los 40 hallazgos en **confirmada**, **percepción** y **dato o arnés**.

Todo lo que aquí se afirma se puede reproducir: `python3 sim/metricas.py --markdown` y `python3 sim/cobertura.py`.

---

## 1. Resumen ejecutivo

| | |
|---|---|
| **Personas** | 12 · 7 de fuera (Mariana, Ernesto, Ximena, Julio, Aurora, Fabiola, Paulina) y 5 del personal (Mireya, Toño, Gaby, Renata, Alma) |
| **Tiempo** | 252 minutos de sesión sumados; 3 h 51 min de tarea cronometrada |
| **Tareas** | **129 intentadas, 65 logradas (50 %)**. Clientes: 68 intentadas, 24 logradas (**35 %**). Personal: 61 intentadas, 41 logradas (**67 %**) |
| **Clics por tarea lograda** | **Mediana 4.** El producto no cuesta clics: cuesta lectura |
| **Segundos de reflexión antes de actuar** | **14,060 s = 3 h 54 min**, más que el tiempo de tarea. En 24 de las 129 tareas la reflexión se comió prácticamente todo el reloj |
| **Lectura antes del primer clic** | 26.9 min repartidos en 65 llegadas a pantalla. Mediana por pantalla: `#/dashboard` 36 s, `#/landing/PAULINA-PR` 49 s, `#/admin` 18 s, `#/login` 16 s |
| **Tareas sin un solo clic** | **34 de 129**; 28 de ellas terminaron en fracaso. La persona leyó, no encontró por dónde, y se fue |
| **Preguntas que la plataforma debió responder sola** | **31** (14 a soporte, 17 a un superior o conocido) · 30 filas en `sim/helpdesk.md`. **21 de las 31 ya tenían respuesta en pantalla**; 24 destaparon huecos reales de producto y 8 son decisiones de negocio |
| **Facilidad media** | **2.9 / 7** (1 difícil – 7 fácil). Ximena 1.0, Ernesto 1.2, Mariana 1.4; Gaby 4.8 y Toño 4.5 en el otro extremo |
| **Confianza en que quedó guardado** | **3.6 / 5** · Alma 3.0, Aurora 3.3, Julio 3.3; Gaby 4.6, Fabiola 4.5 |
| **Estética media** | **4.9 / 10** · recomendaría **3.7 / 10** · confianza que transmite **3.5 / 10** · coherencia **3.5 / 10** frente a legibilidad **6.7 / 10** |
| **Emociones registradas** | 148. **Desconfianza 42, frustración 31, alivio 21, enojo 18, vergüenza 11.** 29 registros de intensidad 5 (la máxima) |
| **Atorones / reintentos / recargas** | 139 / 62 / 27 |
| **Cobertura** | `sim/cobertura.py`: 79 rutas declaradas, **39 alcanzadas, 40 nunca tocadas**; además 20 rutas de los servicios por paquete que el script no reconoce (`/catalog/plan` 25 veces, `/commissions/pagos` 17, `/inventory/pos/arqueo` 13, `/customers/seguimiento/hoy` 10) |

### Las tres conclusiones que cambiarían el producto

**1. El costo no está en los clics, está en la lectura.** La mediana de una tarea lograda son cuatro clics, y aun así la gente gastó 3 h 54 min pensando antes de mover el dedo: más que el tiempo total de tarea. El impuesto se paga en vocabulario que nadie tradujo (PC, VP, VG, "Corte en 27d 1h", "Mínimo requerido" sin número, "Nivel de descuento: Inactivo", "Estado: paid") y en pantallas que no dicen en qué estado están. Ximena Paredes lo resumió después de once cargas en cinco pantallas: *"el problema no fue que yo no encontrara la información. Fue que la información no está"* (`ximena-paredes-2027-03-02.md`). No lo es siempre: en 21 de 31 preguntas la información **sí** estaba.

**2. Lo que la ronda 5 construyó, nadie lo encontró.** Las siete funciones nuevas de la [23](23-implementacion-23-propuestas.md) que se usaron esta ronda funcionaron bien cuando la persona llegó a ellas — y cinco de las siete están fuera del menú. Pagos del mes vive al fondo de la ficha de un cliente ("*la nómina de comisiones de toda la empresa estaba enterrada al fondo del expediente de un cliente cualquiera*", `alma-2027-04-10.md`); Seguimiento de hoy se alcanza por un botón chiquito arriba de la tabla de Clientes; el arqueo está dentro de Punto de Venta; la suscripción, debajo de trece productos; el plan publicado, en una ruta que nadie enlaza desde la tienda. La ronda 6 no encontró que faltara producto: encontró que falta **arquitectura de información**.

**3. Dos defectos de una tarde costaron la mitad de la ronda.** El mensaje de error crudo (`Http failure response for https://ge2omdgk33…: 0 Unknown Error`) frenó en la puerta a **11 de 12 personas**, se llevó media hora de la jornada de Gaby y provocó los cuatro abandonos de prospectos; se arregla con un mapeador de errores compartido que toca ~18 sitios. La falta de un estado intermedio después de pagar ("confirmando tu pago", botón deshabilitado) hizo que **cuatro clientas pagaran dos veces** — $960, $1,180 y $1,308 × 2 — y no depende de por qué falló la pasarela: cualquier retraso normal produce el mismo cobro doble. Ninguno de los dos es una función nueva: son dos correcciones acotadas con el mayor retorno de toda la lista.

---

## 2. El costo de cada cosa

### 2.1 Las tareas más caras

Ordenadas por segundos. "Reflexión" es lo que la persona pasó pensando antes de actuar, medido sobre su propia línea de tiempo (puede desbordar el reloj de la tarea cuando el pensamiento arranca antes de que la tarea empiece).

| Persona | Qué quería | Clics | Seg | Reflexión (s) | Atorones | Reintentos | ¿Logró? | Facilidad |
|---|---|---|---|---|---|---|---|---|
| Paulina Ríos | activarme comprando los 20 VP para rescatar mis $117.90 | 12 | 746 | 747 | 9 | 5 | **no** | 1 |
| Gaby Ledesma | entrar al sistema para ver a quién le toca que le escriba hoy | 9 | 470 | 58 | 2 | 2 | sí | 3 |
| Paulina Ríos | entrar a mi panel a ver cómo va mi mes de marzo | 6 | 453 | 441 | 4 | 2 | sí | 2 |
| Fabiola Cantú | armar una compra que me deje activa este mes sin gastar de más | 11 | 430 | 430 | 4 | 2 | **no** | 2 |
| Toño Vera | entrar al sistema con mi correo de trabajo para ver los pedidos de ayer | 7 | 428 | 424 | 4 | 3 | sí | 2 |
| Mireya Solano | entregarle su pedido de internet a una señora que vino a recogerlo | 23 | 401 | 399 | 5 | 2 | sí | 2 |
| Mireya Solano | cerrar mi turno: contar el efectivo, cuadrar el sobrante de $40 y entregar el dinero | 30 | 383 | 349 | 2 | 1 | sí | 3 |
| Fabiola Cantú | registrarme como socia con el código de Paulina | 0 | 336 | 374 | 2 | 1 | **no** | — |
| Paulina Ríos | ver si tengo algo por cobrar este mes | 5 | 318 | 345 | 1 | 0 | sí | 3 |
| Ximena Paredes | registrarme como clienta desde el link de Paulina, para ver si adentro sí están los números | 3 | 267 | 256 | 4 | 2 | **no** | 1 |
| Julio Herrera | crear mi cuenta para poder ver los productos y comprar | 0 | 250 | 213 | 3 | 2 | **no** | — |
| Julio Herrera | pagar los dos productos y que me lleguen a mi casa | 5 | 240 | 252 | 2 | 2 | sí | 4 |
| Fabiola Cantú | dejar registrada mi CLABE para que me puedan pagar las comisiones | 4 | 230 | 255 | 2 | 1 | sí | 3 |
| Alma Rentería | sacar la lista de comisiones del mes con nombre y CLABE para subirla al banco | 3 | 218 | 219 | 4 | 2 | **no** | 1 |
| Renata Bustos | entrar al panel para pagar las comisiones de marzo | 5 | 217 | 26 | 0 | 0 | sí | 3 |
| Paulina Ríos | registrar mi CLABE para que me puedan depositar | 4 | 216 | 184 | 4 | 2 | sí | 3 |
| Aurora Vega | comprar los dos productos SIN cuenta, como invitada | 0 | 213 | 224 | 2 | 1 | **no** | — |
| Ernesto Vidal | encontrar el omega 3 que me recetó la doctora | 5 | 209 | 147 | 4 | 2 | **no** | 1 |
| Alma Rentería | entrar al sistema con mi usuario para poder cerrar marzo | 4 | 203 | 199 | 1 | 1 | sí | 3 |
| Ernesto Vidal | crear mi cuenta para ver si así aparecen los productos | 2 | 198 | 61 | 3 | 2 | **no** | 1 |
| Gaby Ledesma | escribirle por WhatsApp a Julio Herrera, que compró solo hace unos días | 4 | 197 | 198 | 0 | 0 | sí | **6** |
| Mireya Solano | cobrar de mostrador: parte con un billete de $500 y el resto con tarjeta | 6 | 194 | 189 | 1 | 0 | sí | 4 |
| Aurora Vega | pagar el pedido | 2 | 186 | 75 | 4 | 3 | **no** | 1 |
| Alma Rentería | encontrar dónde se ven los ingresos del mes, los cortes de caja y las comisiones | 0 | 184 | 204 | 2 | 1 | **no** | — |

Dos lecturas de esta tabla.

**La tarea más cara de la ronda no fue de trabajo, fue de una clienta tratando de darle dinero a la empresa.** Paulina gastó 746 segundos, 12 clics, 9 atorones y 5 reintentos en *comprar* los 20 VP que le rescataban $117.90 — y no lo logró: pagó dos veces $960 y el pedido nunca salió de "Pago pendiente". Facilidad declarada: 1 de 7.

**Las tareas de cero clics son el fracaso más barato y el más grave.** 34 de 129 tareas terminaron sin que la persona tocara nada; 28 fracasaron. Fabiola pasó 336 segundos intentando registrarse como socia sin dar un solo clic útil; Aurora, 213 segundos buscando comprar como invitada; Alma, 184 segundos recorriendo el menú buscando la palabra "dinero". Son las tareas donde el producto no ofreció ni siquiera una superficie donde equivocarse.

### 2.2 El impuesto de comprensión: dónde se fue el tiempo de lectura

Segundos entre llegar a una pantalla y dar el primer clic, sumados sobre todas las visitas.

| Pantalla | Llegadas con clic | Mediana (s) | Máximo (s) | Total (s) |
|---|---|---|---|---|
| `#/dashboard` (panel del cliente/socia) | 13 | **36.1** | 63.3 | 448.8 |
| `#/login` | 14 | 15.7 | 32.1 | 244.3 |
| `#/landing/PAULINA-PR` (landing con código de patrocinio) | 5 | **48.6** | 86.3 | 239.1 |
| `#/tienda` | 13 | 10.0 | 48.6 | 220.9 |
| `#/admin` (panel del personal) | 5 | 17.8 | 67.2 | 140.4 |
| `/` y `#/` (portada) | 2 | 64.5 | 69.7 | 129.0 |
| `#/orden/…` (comprobante del pedido) | 3 | 31.6 | 43.2 | 95.3 |
| `#/carrito` | 2 | 17.2 | 17.2 | 34.4 |
| `#/admin/seguimiento` | 1 | 23.7 | 23.7 | 23.7 |
| `#/admin/despacho` | 2 | **3.0** | 3.0 | 6.0 |
| | | | | **1,614.9 s = 26.9 min** |

El impuesto se concentra en **cuatro pantallas de entrada**: dashboard, landing, portada y tienda se llevan 1,038 de los 1,615 segundos. Son exactamente las pantallas donde una persona tiene que decidir *qué es esto y por dónde empiezo*, y son las que mezclan tres vocabularios (tienda, plan de compensación, panel de socia) sin glosario.

En el extremo opuesto está **Despacho en bloque: 3 segundos de mediana antes del primer clic**. Es la pantalla con los pasos numerados y los botones apagados que dicen por qué. Toño lo escribió tal cual: *"Copiar el estilo de 'Despacho en bloque' al resto del sistema: pasos numerados y botones apagados que digan por qué. Esa pantalla la entendí sin que nadie me enseñara; las demás no"* (`tono-vera-2027-03-03.md`). El producto ya sabe cómo bajar su propio impuesto de comprensión; lo hizo en una pantalla.

El `#/dashboard` del cliente es el caso contrario y el más caro: 36 segundos de mediana en 13 llegadas. Paulina llegó a él el día de pago y tardó 63 segundos en encontrar dónde mirar, porque *"el panel me recibe con trece productos y el dinero mío está al final, en un número seco que dice 'Bloqueadas $117.90' sin explicación"* (`paulina-2027-04-10.md`).

### 2.3 Costo por persona

| Persona | Rol | Disp. | Min | Tareas | Logradas | Clics | Pantallas | Reflexión (s) | Dudas | Atorones | Reint. | Facilidad | Confianza |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ximena Paredes, 34 | prospecta | escritorio | 18 | 9 | **0** | 13 | 9 | 1,082 | 9 | 14 | 7 | **1.0** | — |
| Ernesto Vidal, 63 | cliente | celular | 15 | 10 | **0** | 17 | 4 | 846 | 9 | 12 | 5 | **1.2** | — |
| Mariana Robles, 29 | clienta | celular | 9 | 10 | 1 | 17 | 8 | 498 | 14 | 12 | 5 | **1.4** | 2.0 |
| Mireya Solano, 24 | cajera | escritorio | 22 | 5 | 4 | **68** | 5 | 1,158 | 16 | 10 | 4 | 2.6 | 3.8 |
| Aurora Vega, 45 | clienta | escritorio | 20 | 13 | 6 | 34 | **22** | 1,185 | 19 | **20** | 8 | 2.7 | 3.3 |
| Julio Herrera, 26 | cliente | celular | 18 | 6 | 3 | 34 | **27** | 1,001 | 14 | 14 | 7 | 2.8 | 3.3 |
| Paulina Ríos, 44 | socia | escritorio | **40** | 11 | 8 | 33 | 19 | **2,248** | 22 | 19 | **9** | 3.1 | 3.9 |
| Renata Bustos, 41 | gerente | escritorio | 20 | 14 | 9 | 42 | 6 | 1,174 | 11 | 5 | **0** | 3.1 | 3.7 |
| Alma Rentería, 41 | finanzas | escritorio | 20 | 14 | 7 | **208** | 12 | 1,205 | **28** | 12 | 5 | 3.2 | **3.0** |
| Fabiola Cantú, 41 | socia nueva | escritorio | 30 | 9 | 6 | 27 | 20 | 1,701 | 19 | 13 | 6 | 3.8 | 4.5 |
| Toño Vera, 33 | almacén | escritorio | 17 | 12 | **11** | 31 | 11 | 992 | 12 | 6 | 4 | 4.5 | 4.2 |
| Gaby Ledesma, 34 | coach | escritorio | 23 | 16 | 10 | 43 | 6 | 1,345 | 18 | **2** | 2 | **4.8** | **4.6** |

Los **208 clics de Alma** no son de trabajo productivo: 159 de ellos se fueron en una sola tarea, "encontrar los cortes de caja de mostrador de marzo", porque *"Resumen de turno"* acepta un día y una persona por consulta y ella tenía que revisar 31 días × 5 empleados. Los **68 de Mireya** son en su mayoría el conteo del corte por denominación, que es trabajo legítimo. La diferencia entre las dos cifras es la diferencia entre un producto que te hace trabajar y uno que te hace repetirte.

Toño y Gaby son las dos personas que salieron mejor de la ronda (11 de 12 y 10 de 16 tareas, facilidad 4.5 y 4.8) y las dos usan pantallas construidas en la ronda 5: Despacho en bloque y Seguimiento de hoy. Ximena y Ernesto salieron con **cero tareas logradas**.

---

## 3. Dónde se atoran y por qué

Agrupado por causa. El veredicto es el de la verificación posterior: **confirmada** (defecto reproducible en el código), **percepción** (la función existe y la persona no la encontró o la leyó al revés) y **dato o arnés** (falla del entorno de simulación, no del producto — pero se documenta lo que destapa). De los 40 hallazgos: **29 confirmadas** (5 críticas, 9 altas, 12 medias, 3 bajas), **8 de percepción** (4 altas de diseño) y **3 de arnés**.

### 3.1 La puerta: un mensaje de error que le habla al servidor, no a la persona

**Veredicto: confirmada · crítica · 11 de 12 personas.**

`login.component.ts:166-167` y el mismo patrón en unos 18 sitios: `error?.error?.message || error?.message || 'Credenciales invalidas...'`. En un fallo de transporte (status 0, CORS, servidor caído) `error.error.message` no existe pero `error.message` **siempre** existe y vale la cadena en inglés con la URL interna, así que el texto humano que sí escribieron nunca se alcanza. De paso, filtra el host del API Gateway a cualquier visitante.

- Mireya, tercer día de trabajo: *"Yo pensé que había escrito mal mi contraseña"* (`mireya-2027-03-03.md`). Dos intentos creyendo que la culpa era suya.
- Toño necesitó cuatro intentos y el enlace por correo nunca llegó: *"Si no puedo entrar, no hay envíos"* (`tono-vera-2027-03-03.md`).
- Gaby: seis intentos, media hora de su jornada antes del primer cliente. No entró por sí sola.
- Renata entró al tercero; Alma y Paulina al tercero; Aurora, Ximena, Mariana, Ernesto y Julio nunca llegaron a crear cuenta.
- Mariana: *"parece una página abandonada o una copia pirata"* (`mariana-robles-2027-03-02.md`). Ernesto: *"Un error debe decir qué pasó y qué hago yo, y traer un teléfono"* (`ernesto-vidal-2027-03-02.md`).

Un solo *helper* que mapee `status===0` → "no pudimos conectar" y `status>=500` → "problema de nuestro lado", y que **nunca** use `error.message` como último recurso, arregla los 18 sitios.

### 3.2 El dinero que sale y no llega: cuatro clientas pagaron dos veces

**Veredicto: confirmada · crítica · Aurora, Fabiola, Julio, Paulina.**

`order-status.component.html:270-300` pinta el bloque de pago con `*ngIf="statusValue === 'pending'"` y ofrece "Pagar con MercadoPago" sin ningún estado intermedio. Al volver de la pasarela no hay "estamos confirmando tu pago", ni marca de intento previo, ni bloqueo temporal del botón.

- Fabiola: *"Pagué DOS VECES ($1,308 cada vez) y el pedido sigue en Pago pendiente. Ni correo, ni cambio de estatus"* (`fabiola-2027-03-04.md`).
- Julio: *"Pagué $1,209 y la pantalla seguía diciendo 'Pago pendiente'. Ese es el momento en que la gente paga dos veces"* (`julio-herrera-2027-03-02.md`). Recargó tres veces.
- Paulina, $960 dos veces, y después la pantalla en blanco (`paulina-2027-03-20.md`).
- Aurora: *"puede que me hayan cobrado dos veces $1,180 y la tienda no se entera"* — emoción registrada: miedo, intensidad 5.

**Lo que es del arnés y lo que no.** Que *ningún* pago se acreditara sí fue del arnés: la semilla dejó `notificationUrl` vacío junto al `webhookSecret`, la pasarela llamó sin secreto y el lambda contestó 401 catorce veces (`sim/servidor.log`). Pero eso destapó dos defectos reales: (1) `handle_mercadopago_checkout` acepta esa media configuración sin negarse ni alertar — un comercio real cobraría a todos sus clientes sin marcar pagado ni un pedido y sin señal en pantalla; (2) el cobro doble **no depende del webhook**: cualquier retraso normal de la pasarela produce exactamente el mismo resultado.

Encima, **no existe correo de "recibimos tu pedido"** (`core/order_emails.py`: los eventos son paid, shipped, delivered, cancelled, refunded). Los cinco buzones de `sim/buzon/` lo confirman. Paulina lo anotó: *"Me llega correo por cancelar un pedido pero no por hacerlo ni por pagarlo"* (`paulina-2027-04-10.md`). Sin ese acuse, cuando la pasarela falla el cliente se queda sin ninguna constancia de que su compra existe.

### 3.3 Pantallas que inventan datos cuando el servidor no responde

**Veredicto: dos confirmadas críticas.**

- **La tienda inventa un producto.** `tienda.component.ts:30-42`: `defaultHero` es un objeto fijo en código — `name:'COLÁGENO', price:0, tags:['Energía diaria','Recuperación','Salud integral']` — que se pinta con su botón de compra aunque el catálogo esté vacío. `addToCart()` empieza con `if (!product) return;`: un retorno mudo, sin aviso. Cinco personas describieron lo mismo. Aurora: *"Le piqué dos veces y el carrito quedó en $0"*. Ernesto: *"'Agregar al carrito' no agrega nada"* (`ernesto-vidal-2027-03-02.md`). Los tres "beneficios" que vieron son literalmente los tres *tags* del objeto inventado. Y un catálogo que no cargó se presenta como **"Todos los productos · 0 productos"**: seis de las siete personas de fuera lo citaron, y ninguna entendió que era una falla de red. Aurora: *"pensé que la tienda estaba sin inventario, no que estuviera caída"*.
- **El landing inventa los rangos del plan.** `landing.component.ts:150-156`: `rankThresholds` cae a un literal `[ORO 700, PLATINO 2000, DIAMANTE 6000]` cuando `businessConfig` es null. La configuración real es BRONCE 4,500 / PLATA 9,000 / ORO 15,000 / PLATINO 21,000 / DIAMANTE 25,000: **los números publicados son unas 20 veces más bajos que los verdaderos**. Fabiola detectó la contradicción entre el landing y `#/modo-socio` y preguntó *"¿a cuál le creo?"*. En la misma pantalla, el `*ngFor` de "Comisiones de Red" no tiene estado vacío ni de error: quedan los cinco encabezados sobre cero filas. Ximena, gerente de compras, decidió no comprar por eso: *"Vine a leer la única tabla que importa y tiene cinco títulos y ninguna fila"*; *"cuando llegas a la parte de los números, la hoja está en blanco"* (`ximena-paredes-2027-03-02.md`).

Una promesa comercial no puede salir de un valor por omisión escrito en el código. Es el hallazgo con más consecuencia legal de la ronda.

### 3.4 El comprobante que no comprueba nada

**Veredicto: confirmada · crítica · Aurora, Julio, Mireya, Paulina.**

`#/orden/:id` muestra folio, subtotal, envío y total, y **nunca recorre `order.items`** (grep de `order.items`, `invoiceStatus` y `pickupStockId`: cero coincidencias). La API sí los trae: ORD-AC9B846C devuelve partidas, `pickupStockId STK-72339D` (Sucursal Guadalajara) e `invoiceStatus 'solicitada'`.

- Aurora: *"El comprobante no menciona los productos, ni la sucursal donde voy a recoger, ni que pedí factura. ¿Sí se guardó todo eso?"* (`aurora-2027-03-04.md`).
- Julio no pudo señalar cuál bote llegó roto: *"La pantalla del pedido no dice qué compré"* (`julio-herrera-2027-03-02.md`).
- Mireya, desde el mostrador, no supo qué entregarle a la señora que vino por su pedido: *"Yo necesito saber QUÉ le entrego a la señora y aquí no viene"* (`mireya-2027-03-03.md`).
- Y la línea de tiempo del pedido (`ui-order-timeline.component.ts:17-23`) tiene los cinco pasos escritos a mano, sin saber nada de `deliveryType`: a quien eligió recoger en sucursal le dice **"Envío · Ruta de entrega"**. Paulina: *"Elegí recoger en tienda y la orden me habla de Ruta de entrega. No dice en ningún lado a qué sucursal debo ir"* (`paulina-2027-03-20.md`).

### 3.5 Callejones sin salida del checkout

**Veredicto: confirmada · alta.** Como invitada, elegir "Recoger en sucursal" oculta el campo de correo que el propio botón de pagar exige: todo el bloque de contacto vive dentro de `<div *ngIf="deliveryType === 'delivery'">` (`carrito.component.html:271`), mientras `placeOrder()` valida el correo **antes** de mirar `deliveryType` y saca el aviso *"Escribe tu correo: ahí te avisamos del pago, el envío y la entrega"*. Aurora: *"Me pide un dato que la pantalla no me deja capturar"*; tuvo que cambiar a envío a domicilio, escribir el correo y volver. En recolección el contacto es **más** necesario, no menos: es con lo que el cliente se identifica en el mostrador — que es justamente lo que le faltó a Paulina: *"¿Con qué me presento en la Tienda Del Valle?"*.

Del mismo tipo, aunque más barato: el carrito pide trece campos de dirección con cero artículos y avisa "Agrega productos para continuar" **al final**. Mariana: *"Me está pidiendo mi dirección completa para un carrito vacío y con total $0"*. Ernesto, que escribe con un dedo: *"me hizo escribir toda mi dirección con un dedo para al final decirme 'Agrega productos para continuar'"* (`ernesto-vidal-2027-03-02.md`).

### 3.6 Números del panel que no cuadran con sus propias partidas

**Veredicto: confirmada · alta · Renata, Alma.**

- **Devolver dinero sube las ventas.** `admin.component.ts:1959-1963`: el filtro de `ordersCollectedTotal` es `status !== 'pending' && status !== 'cancelled'`, así que `refunded` cuenta como cobrado. Verificado contra la API: los cinco pedidos suman exactamente 5,417 y ORD-391358BF está en `refunded` con `refundAmount 960`. Antes del reembolso estaba `cancelled` y quedaba fuera: de ahí el 4,457. Renata: *"Devolví $960 y el panel me sumó $960 de ingreso"* (`renata-bustos-2027-04-10.md`). Alma iba a reportar ese número al contador. Y la clienta reembolsada quedó como Top cliente #1.
- **El detalle del pedido nunca imprime el descuento.** `admin.component.html:392-404` pinta partidas, Envío y Total, sin subtotal ni descuento. ORD-A42EFB51 guarda `grossSubtotal 1310, discountAmount 131, total 1308`: en pantalla se lee partidas por 1,310 + envío 129 y un total de 1,308. Alma: *"Cinco pedidos, dos que no cuadran consigo mismos, y en direcciones contrarias"*; *"un total que no cuadra con sus partidas es lo peor que me puede pasar en un cierre"* (`alma-2027-04-10.md`). Emoción registrada: frustración 5, desconfianza 5.
- **Una venta de mostrador dice dos cosas a la vez.** La lista usa `stockId` y acierta ("Tienda Del Valle"); el detalle usa `pickupStockId`, que las ventas POS no llenan, y `stockName('')` devuelve el literal **"Sin stock"** como si fuera el nombre de un lugar. Alma: *"'Sin stock' no es una sucursal. Es el mismo pedido diciendo dos cosas"*.
- **Estados y motivos internos a la vista.** `customer_request`, `mixed`, `paid 2, delivered 2, cancelled 1` impresos tal cual. Alma: *"¿Eso se lo enseño así a mi jefa?"*. Y `mixed` sin desdoblar es exactamente el dato que a ella y a Mireya les faltaba para cuadrar los $260 de diferencia entre la venta ($760) y el corte ($500).

### 3.7 La caja que nace descuadrada

**Veredicto: confirmada · alta · Mireya.**

`caja_handlers.py:126`: `openingCash` se deriva **únicamente** del `cashToKeep` del corte anterior. En una caja nueva no hay corte anterior, así que el fondo queda clavado en $0.00, y el "Fondo inicial" de la pantalla de arqueo es un letrero, no un campo. Mireya arrancó con $500 de su cajón, cerró contando $1,040 y el sistema le reclamó $540 de diferencia. Ella lo describió redondo: *"Si le pongo lo que de veras conté me va a parecer que metí dinero; si pongo $540 estoy mintiendo del conteo"* (`mireya-2027-03-03.md`). Sin una acción "Abrir caja", **ninguna caja nueva puede cuadrar nunca**.

El segundo muro del mismo turno: el código de autorización del retiro se comprueba **al confirmar**, después de llenar los cuatro pasos. *"Si me lo hubiera dicho en el paso 3, no me habría hecho llenar todo"*. Su gerente no contestó el WhatsApp y **los $1,040 del día se quedaron en el cajón toda la noche**: *"Me voy a mi casa dejando $1,040 en el cajón de una tienda, porque no tengo un código de cuatro números"*.

### 3.8 El día de pago sin pantalla de pago

**Veredicto: confirmada (alta y media) + percepción alta · Renata, Alma, Paulina.**

El 10 de abril, que la propia configuración define como día de pago (`Dia de pago = 10`), ni la gerente ni finanzas pudieron depositar una sola comisión:

- **No hay entrada "Comisiones" en el menú.** Renata leyó el menú completo dos veces. Alma: *"Me contrataron para cuadrar el dinero y el menú del sistema no tiene ni una palabra de dinero"* (`alma-2027-04-10.md`). Estuvo dos horas convencida de que se le escapaba algo.
- **La nómina vive dentro de la ficha de un cliente.** "Pagos del mes · comisiones por depositar" está al fondo del expediente de Julio Herrera, después de documentos, notas de WhatsApp y árbol de red. Alma llegó de casualidad. Es la peor pantalla de la ronda para dos personas distintas.
- **El selector de mes se arma con el reloj del equipo, no con el periodo del negocio.** Ofrece de octubre 2025 a septiembre 2026. Alma: *"El mes más nuevo que me ofrece es de hace año y medio"*. El servidor **sí** conoce marzo de 2027 y contesta (0 listas, 0 sin CLABE, 0 pagadas). El origen es de arnés — el mundo simulado está en 2027 y el navegador en 2026 — pero destapa un defecto real: **dos pantallas del mismo panel calculan "días desde la última compra" con dos relojes distintos** (Clientes con el del navegador, Seguimiento con el del servidor) y muestran cifras diferentes de la misma persona. Gaby lo cazó: *"El mismo Julio: 'Inactiva, 0 días' en una pantalla, 'Activa, 5 días' en otra, y en el calendario son 6"* (`gaby-ledesma-2027-03-08.md`).
- **"Exportar" no dice de qué mes exporta ni deja elegirlo** (`downloadCommissionsReport()` usa `getPrevMonthKey()` sin parámetros). Renata: *"me bajó un archivo que se llama comisiones-2026-08.xlsx. Y en ningún lado de la tarjeta dice de qué mes es lo que exporta"*.
- **"Conciliar pagos" solo mira 72 horas fijas.** El backend acepta `body.hours` entre 1 y 2160 (90 días); el front manda `{}`. Los dos pedidos cobrados del 4 de marzo tenían 37 días el 10 de abril: ninguna corrida manual podía encontrarlos. Renata: *"Clarísimo el mensaje, pero solo mira 3 días atrás y yo venía a revisar marzo entero"*. Por ahí se perdió el pago de Paulina del 20 de marzo.
- **Del otro lado, la socia no recibe nada.** El 10 de abril el panel de Paulina seguía diciendo *"marzo de 2027 (actual)"*, el aviso del día 27 nunca salió, no hubo depósito ni explicación. *"El silencio es lo que rompe la confianza"* (`paulina-2027-04-10.md`).

Nota importante para no culpar a la pantalla de lo que no es suyo: **el $0 era correcto**. Verificado contra la API, `GET /commissions/pagos?month=2027-03` devuelve cero filas porque las comisiones se confirman al entregar y los dos pedidos pagados del 4 de marzo llevaban 37 días sin salir del almacén, y porque Paulina cerró marzo con 0 VP de los 20 de activación. **Lo que falla no es el número, es que ninguna pantalla lo explica.** Alma llegó a creer que estaba mal porque el Cuadro de Honor mostraba VG 24.

### 3.9 Permisos que esconden el trabajo de quien lo tiene que hacer

**Veredicto: percepción alta (de diseño de permisos) + confirmada alta.**

- **A Alma le esconden su propio trabajo.** `app-factura-pedido` tiene folio, PDF y el botón "Marcar factura emitida", envuelto en `*ngIf="… && canMark"` con `[canMark]="hasPermission('order_mark_paid')"`. El login de Alma devuelve `order_mark_paid:false`, así que el bloque **desaparece sin sustituto ni explicación**. Ella concluyó *"no hay NINGÚN botón para marcarla como emitida"* y *"mañana el pedido va a seguir diciendo Factura Solicitada"*. Es la persona de administración y finanzas. "Marcar un pago" y "emitir una factura" no son la misma responsabilidad, y esconder un control por permiso sin dejar rastro contradice el patrón `disabledReason` que el propio producto ya usa y que Renata elogió en otra pantalla.
- **A Toño le abren el trabajo de otro.** `privileges.model.ts:87-88` autoriza Campañas con `access_screen_stocks`, con un comentario que lo reconoce. El login real de Toño devuelve ese privilegio, así que puede publicar campañas de publicidad con imágenes y botones para toda la red, y el backend valida el mismo privilegio. *"Con mi usuario de almacén puedo crear campañas de publicidad… Si le muevo por curiosidad, rompo algo de otro"* (`tono-vera-2027-03-03.md`).
- **El panel llama "ADMIN" a los cinco empleados.** `POST /auth/login` devuelve `role:'admin'` para Renata, Toño, Mireya, Gaby y Alma por igual; lo único que los distingue es el mapa de privilegios, y nada nombra el puesto. Consecuencias: Mireya entra a Pedidos, que no es lo suyo, porque es la primera vista permitida; Toño abre su pantalla de trabajo y lo primero que ve es el formulario completo de "Alta de stock" con los 32 estados de la República — renderizado sin condición, solo el botón de guardar lleva el permiso que él no tiene — con las existencias empujadas hasta abajo. Gaby: *"Arriba de mi nombre dice 'ADMIN'. Yo no soy admin, soy coach, y las 'Acciones urgentes' que me enseña son pedidos sin despachar, que no me tocan"*.

### 3.10 Botones que no responden y sí eran botones (o no lo eran)

**Veredicto: percepción alta de diseño · seis personas.**

Julio, Paulina, Aurora, Mariana, Ernesto y Ximena reportaron "botones que no hacen nada": "Ver beneficios", "Ver productos", "Órdenes", "Mi cuenta", "Tienda" del menú. **Ninguno estaba roto.** El menú del panel del cliente no navega: llama `scrollToSection(id)`, que hace `getElementById` y, si no encuentra el nodo, hace `return` sin ningún aviso. Las secciones tienen `*ngIf`: `#modo-cliente` solo existe en modo cliente, así que "Mi cuenta" es un botón permanentemente muerto para un socio como Julio; `#ordenes` está debajo de los 13 productos, las tablas de descuento, la red y los enlaces — *"enterrado como diez pantallazos abajo en el celular"*, escribió él mismo al encontrarlo. "Tienda" apunta a `#merchant`, que está arriba del todo: el scroll no se mueve.

Julio: *"Tres botones seguidos que no hacen nada. Yo ahí ya pensé: esto está caído o es pirata"*; *"Me hice una cuenta a propósito para encontrar mis pedidos y el botón 'Órdenes' está muerto"*; y su remedio, en una línea: *"Prefiero un botón gris que uno que me ignora"* (`julio-herrera-2027-03-02.md`). Mariana no llegó tan lejos: cerró la pestaña.

Esto no es código roto: es arquitectura de información. Un panel del cliente que es una sola página infinita con un menú de anclas.

### 3.11 Lo que existe y nadie halló

**Veredicto: percepción.** Cuatro casos donde la función está completa y bien hecha:

| Qué | Dónde está | Quién no lo encontró |
|---|---|---|
| **"Recibe esto cada mes"** (suscripción: crear, pausar, cancelar, día del cargo, dirección o sucursal) | `suscripcion.component.html`, montado **después** de la tabla de órdenes, al fondo de la página infinita, y envuelto en `*ngIf="currentUser?.userId"` — invisible para invitados | Ernesto, que nunca pudo crear cuenta y buscó exactamente la palabra "suscripción": *"ni la palabra suscripción aparece"*. Concluyó *"No existe en ninguna pantalla"*. Era **lo único** que venía a hacer |
| **El importe reembolsado** ($960 y su motivo, en el detalle del pedido) | `admin.component.html:462-463`, justo **debajo** del recuadro rojo "Motivo cancelación: customer_request" | Alma reportó "en el detalle no aparece cuánto se reembolsó": lo tenía a la vista, pero el motivo en clave se llevó toda su atención |
| **El motivo del botón "Recibir" apagado** ("Elige arriba quién recibe") | `ui-button` lo pinta debajo del botón por omisión | Toño, porque llega como una línea más de una tabla densa — y porque cinco líneas antes la pantalla ya le había anunciado *"sin eso el botón Recibir no responde"*: *"el sistema ya sabe que hay un botón que no responde y en vez de arreglarlo me lo avisan con un letrero. Eso me deja nervioso"* |
| **La asignación de ejecutiva** | Dentro del modal de ficha de Seguimiento, no como botón en la fila | Gaby, que primero anotó "no encontré ningún botón para asignármelos" y veinte minutos después se asignó las cuatro |

### 3.12 El vocabulario: tres monedas y ningún glosario

**Veredicto: percepción alta de diseño · 9 de 12 personas.**

La API sí trae las definiciones: `/catalog/plan` devuelve `unidades.pc`, `unidades.vp` y `unidades.vg` explicadas en castellano llano, y `mxnPerVp 50`. **Ninguna pantalla las usa.** La tienda habla de PC, el carrito y el panel de VP, el Cuadro de Honor y los rangos de VG, y el pago va en pesos.

- Fabiola: *"Son tres monedas distintas en la misma pantalla y nadie me explica cómo se convierten"* (`fabiola-2027-03-04.md`).
- Ximena: *"Tres siglas —PC, VP, VG— y ningún glosario. ¿Cuál de las tres me pagan?"* (`ximena-paredes-2027-03-02.md`).
- Ernesto: *"¿Qué es 'PC'? Yo sólo conozco PC de computadora"* (`ernesto-vidal-2027-03-02.md`).
- Mariana: *"Palabras como 'tu red', 'metas' y 'PC' son justo lo que me hace cerrar una app"* (`mariana-robles-2027-03-02.md`).
- Y la vuelta de tuerca que Fabiola encontró sola: el descuento **recorta** los VP ("20 PC con 10 % = 18 VP"), *"lo contrario de lo que uno espera de un descuento"*.

En el mismo saco: "Corte en 27d 1h" sin explicación (cinco personas creyeron cosas distintas, Ernesto pensó que le iban a cobrar en 27 días), "Mínimo requerido" sin número (cuatro personas), "Te faltan $0 para Meta de beneficios" (tres), "Nivel de descuento: Inactivo" + "Descuento aplicado: Sin descuento" (dos frases para lo mismo).

### 3.13 Lo pequeño que duele

**Veredicto: confirmada, gravedad baja, consecuencia alta.**

- **Fabiola se llama Fabio.** `compactNodeName` hace `parts[0].slice(0,5)`: "Fabiola Cantú Ríos" → **"Fabio C. R."**. *"Me llamo Fabiola. Me cortaron el nombre y encima quedó de hombre. Si mis clientas del salón ven eso, ¿qué van a pensar?"* (`fabiola-2027-03-04.md`). Es la pantalla que las socias enseñan a sus invitadas.
- **"−0".** La columna "Falta" del Cuadro de Honor imprime `'−' + gap` sin caso para cero, y Fabiola y Paulina están empatadas en 24.3 VG. Alma: *"¿Menos cero?"* (`alma-2027-04-10.md`).
- **Números donde va un nombre.** El CSV de clientes escribe el `leaderId` crudo en la columna Patrocinador pudiendo usar `customerName()`, que existe en el mismo componente; `customerName()` devuelve `Usuario ${id}` cuando el id no está entre los clientes, y los empleados nunca lo están. Mireya: *"¿Ese numerote soy yo? Debería decir mi nombre"*. Gaby: *"Mi nota quedó firmada por '1803978000183'"*. Alma tuvo que adivinar que 1803978000305 era Paulina.
- **"© 2026 finding U"** en marzo de 2027, escrito a mano en la plantilla — será falso cada enero. Lo citaron seis personas. Pero lo grave es lo que hay alrededor: **el pie completo es esa sola línea**. Aurora buscó teléfono, correo o WhatsApp en el pie, en el catálogo y en la pantalla del pedido: *"el carrito me hizo aceptar términos y políticas que no están en ningún lado"* (`aurora-2027-03-04.md`). Julio, con un bote roto, no encontró ni política de devoluciones ni un correo. Ximena leyó que puede *"ejercer derechos ARCO por los canales de contacto oficiales"* y no hay ni uno.
- **Acentos.** "danos", "Marcar danado", "Ubicacion", "vinculacion", "campanas", "Confirmacion", "Pais", "Queretaro". Toño y Paulina los reportaron por separado; Paulina, sobre la ventana que guarda su CLABE: *"'Confirmacion' en la pantalla del banco se ve mal"*.

### 3.14 Sin canal interno: el trabajo sale por WhatsApp

**Veredicto: confirmada · media · Toño, Renata, Mireya, Gaby.**

No hay bandeja, bitácora ni notas entre empleados; Notificaciones es difusión hacia clientes. Toño dejó un traspaso de 40 botes colgado en "Pendiente" y no tuvo dónde avisarlo: *"No hay ninguna manera de dejarle un aviso a mi jefa dentro del sistema. Ni un cuadrito de notas en el traspaso"*. Renata, del otro lado, no encontró dónde dejarle el cierre de marzo al dueño y se lo mandó por WhatsApp. Y el tablero de "Acciones urgentes" le dijo a Toño **"Todo en orden"** con su traspaso sin recibir: solo cuenta estados de pedido, no traspasos pendientes ni cortes sin retiro autorizado.

---

## 4. Lo que preguntaron

**31 preguntas** en 39 días: 14 a soporte y 17 a un superior, a una patrocinadora o a un familiar. Quedaron en `sim/helpdesk.md` (30 filas; dos preguntas de Alma viajaron en la misma fila). El reparto, según la clasificación que hizo el propio soporte al contestar:

| | Cuántas | Qué significa |
|---|---|---|
| **Ya estaban respondidas en pantalla** | **21** | La información existía y era correcta; la persona no la alcanzó, o la alcanzó y no la creyó |
| Destaparon un hueco real de producto | 24 | Muchas preguntas caen en las dos columnas: la respuesta existía **y** faltaba algo alrededor |
| Son decisión de negocio, no de software | 8 | Nadie las puede contestar desde una pantalla |

### 4.1 Las que ya tenían respuesta, y dónde estaba

| Lo que preguntaron | Quién | Dónde estaba la respuesta |
|---|---|---|
| ¿Cuánto cuesta el colágeno? ¿Y los demás productos? | Mariana, Ximena, Ernesto, Julio | `#/tienda`: 13 productos con precio ($280 a $800) y ficha. Público, sin cuenta |
| ¿Tienen omega 3 con la dosis de EPA y DHA? | Ernesto | Klinhart $480, 60 cápsulas, 660 mg de EPA y 440 mg de DHA por cápsula, en `#/tienda`. Exactamente lo que le apuntó su doctora |
| ¿Tienen proteína? | Julio | Finding Pro 500 g, $800, 21 g por porción, en `#/tienda` |
| ¿Cuánto cuesta el envío? ¿Llega a mi CP? | Mariana, Ernesto | Tarifa única $129 Estafeta (3-5 días) o $219 DHL (1-2 días); el cotizador del carrito responde y cubre el 06100 y el 64000 |
| ¿Cuánto gano por generación? ¿Qué me exigen? ¿Qué descuento me toca? | Ximena, Fabiola | `#/modo-socio`: 10/5/4/3/2 %, requisitos, descuentos 10/20/30/40 %, activación de 20 VP ≈ $1,000. **Público, sin cuenta** |
| ¿Qué son PC, VP y VG? | Ximena (y otras 8 personas) | El mismo plan los define: 1 PC ≈ $50 de lista; VP = PC de lo pagado en el mes ya con descuento; VG = VP propios más los de la red hasta 5 niveles |
| ¿Puedo recoger en sucursal y pedir factura? | Aurora | Las dos cosas existen en el carrito… pero **solo aparecen con el carrito lleno**. Creyó 40 minutos que no se podía |
| ¿Se guardaron mis datos de recolección y factura? | Aurora | Sí: ORD-AC9B846C guarda Sucursal Guadalajara, RFC VEGA850312AB1, régimen 612, uso G03. La pantalla del pedido no los muestra (§3.4) |
| ¿Por qué mi comisión está "Bloqueada"? | Paulina, Alma, Renata | La pantalla de comisiones lo dice literalmente: *"las comisiones se confirman cuando el pedido se entrega"* — en el panel de administración, no en el de la socia |
| ¿Existe marzo de 2027 para el sistema? | Alma, Renata | Sí: el servidor contesta ese mes (0 listas, 0 sin CLABE, 0 pagadas). Solo el selector de la pantalla no lo ofrece |
| ¿De verdad no hay nada que despachar? | Toño | Sí, era correcto: los dos pedidos de internet ya estaban entregados |
| ¿Quién está vinculado a cada almacén? | Toño | En la ficha del almacén, en Stocks: hoy los cinco empleados en las tres bodegas |
| ¿Cómo le mando el resumen del día a mi jefa? | Toño | "Resumen de turno" existe, lo arma el sistema solo y trae la lista del equipo para enviárselo. No está en el menú de tres entradas de almacén |
| ¿De dónde sale el fondo de caja? ¿Quién autoriza el retiro? | Mireya | Las dos cosas las dice la propia pantalla ("Fondo que dejó el corte anterior"; "lo autoriza la gerente con su código") — la segunda hasta el paso 4 de 4 |
| ¿Por qué $5,417 y $4,457 para el mismo marzo? | Alma, Renata | Se verifica cruzando Pedidos con Estadísticas: el pedido de más es el reembolsado de $960 |
| ¿Dónde están arqueo y comisiones? | Alma | Existen, escondidos dentro de otras pantallas: el arqueo en Punto de Venta, las comisiones al fondo de Clientes |
| Si me asigno un cliente, ¿sale de la lista de mis compañeras? | Gaby | Sí, "Seguimiento de hoy" ya lo aplica |
| ¿Qué plantilla le mando a quien acaba de comprar? | Gaby | "Pedido tardío", disponible en la misma ventana junto a Bienvenida, Cliente fría y CLABE pendiente |
| ¿Hay que registrarse para ver productos y precios? | Ernesto, Ximena | No. El catálogo y el plan son públicos |

**Veintiuna de treinta y una.** La lectura no es "la gente no busca": Ximena recorrió cinco pantallas y once cargas antes de escribir; Alma probó los doce meses del selector uno por uno y escribió a mano cuatro direcciones; Ernesto le picó dos veces a cada uno de los tres botones que había, recargó y volvió por la noche. La lectura es que **el producto tiene la respuesta y no tiene el camino**.

### 4.2 Las ocho de negocio

Nadie las puede contestar desde una pantalla y siguen abiertas:

1. Si se le devuelven los $129 de envío al cliente que acabó recogiendo su pedido en el mostrador (Mireya).
2. Quién paga el envío de regreso de un producto que llegó roto y en cuántos días se devuelve el dinero — la política configurada solo dice "mismo medio de pago, 3 a 5 días hábiles" (Julio).
3. Si la casa repone los $117.90 que Paulina perdió por un pago que sí hizo y que el sistema nunca acreditó, y si se da por buena su activación de marzo (Paulina).
4. Si se atiende por teléfono a quien no puede con la web: Ernesto dejó su número y hoy no existe ese canal.
5. Si se rescata por teléfono a un cliente que abandonó, y con qué criterio: no hay nada en el sistema que lo dispare.
6. Corregir el texto del aviso de privacidad frente a los datos fiscales que el checkout sí pide y a los documentos que se exigen a las socias (Aurora).
7. Cuál es el mínimo de existencias de cada producto por bodega: nadie lo ha definido, y sin ese número el "Guadalajara anda bajo" es a ojo (Toño).
8. Si se depositan las comisiones por fuera del sistema o se espera a que la pantalla lo permita (Renata, Alma).

---

## 5. Cómo se ve y cómo se siente

### 5.1 Calificaciones

| Persona | 1ª impresión | Confianza | Legibilidad | Coherencia | Móvil | Recomendaría | Tres adjetivos |
|---|---|---|---|---|---|---|---|
| Mariana Robles | **7** | **2** | 7 | 3 | 5 | **1** | bonita, **hueca**, sospechosa |
| Ernesto Vidal | 5 | **2** | **4** | 3 | 3 | **1** | vacía, presumida, complicada |
| Ximena Paredes | 6 | **2** | 6 | 3 | — | 2 | bonita, **hueca**, vaga |
| Julio Herrera | **4** | 3 | 6 | 3 | 4 | 3 | femenina, insistente, incompleta |
| Aurora Vega | 6 | 3 | 7 | 4 | — | 3 | bonita, incompleta, insistente |
| Paulina Ríos | 5 | 3 | 7 | 3 | — | 3 | vendedora, desordenada, poco confiable |
| Fabiola Cantú | 6 | 4 | **8** | 4 | — | 5 | cuidada, contradictoria, lenta |
| Alma Rentería | 6 | 3 | 7 | 3 | — | 4 | ordenada, incompleta, poco confiable |
| Renata Bustos | **7** | 4 | 7 | 3 | — | 4 | ordenada, incoherente, **fría** |
| Mireya Solano | 6 | **6** | 7 | 5 | — | 5 | largona, explicadita, de oficina |
| Toño Vera | 5 | 5 | 7 | 5 | — | 6 | ordenada, **fría**, inconstante |
| Gaby Ledesma | 6 | 5 | 7 | 4 | — | **7** | ordenada, **gris**, desconfiada |
| **Media** | **5.8** | **3.5** | **6.7** | **3.5** | 4.0 | **3.7** | |

**El patrón es una tijera: legibilidad 6.7 contra coherencia 3.5 y confianza 3.5.** Nadie dijo que fuera fea ni ilegible; ocho de doce dijeron alguna variante de "bonita por fuera, hueca por dentro". Y no se maquilla: los adjetivos que más se repiten son **hueca** (Mariana, Ximena), **fría** (Renata, Toño), **incompleta** (Aurora, Alma, Julio), **poco confiable** (Paulina, Alma), **gris** (Gaby), **cara** en el sentido de aparentar más de lo que entrega (Fabiola: "cuidada"; Mariana: "los colores tierra y la tipografía se ven caros").

### 5.2 Mejor y peor pantalla

| Persona | Mejor | Peor |
|---|---|---|
| Mariana | la portada de la tienda: colores tierra y tipografía que "se ven caros" | el carrito en el celular: trece campos para un total de $0 y "0 artículos" |
| Ernesto | la tienda del colágeno con el fondo grande | el carrito: escribir toda la dirección con un dedo para leer al final "Agrega productos para continuar" |
| Ximena | la portada del landing: seria, ordenada, bien escrita | la tabla "Comisiones de Red" con encabezados y cero filas, empatada con `#/modo-socio`, que promete "los números reales" y nunca carga |
| Julio | el carrito con la dirección puesta: Estafeta $129 y DHL $219 y el total actualizado solo | la pantalla del pedido: no dice qué compró, no avanzó de "Preparación" y solo ofrece "Cancelar orden" |
| Aurora | el carrito al elegir "Recoger en sucursal": envío en Gratis, tres sucursales con dirección y "Tiene todo tu pedido" | `#/orden`: no dice qué compró, ni dónde recoge, ni que pidió factura; lo único grande es "Activar modo socio" |
| Fabiola | **"Modo socio · Cómo funciona, con los números reales"**: la única que explica PC, VP y VG con ejemplos y dice cuándo pagan | la pantalla del pedido después de pagar: en blanco, luego "Pago pendiente" y otra vez el botón de pagar |
| Paulina | **"Modo Socio"**: sobria, con tablas y ejemplos; ahí entendió qué es una comisión bloqueada | la orden después de pagar: "Pago pendiente" con el botón de pagar otra vez ahí |
| Mireya | **el corte de caja paso a paso**, el conteo por billetes y la frase "No es una falta: es lo que pasó" | la lista de Pedidos: columna "Acción" vacía y un "Ver" que no abre nada |
| Toño | **Despacho en bloque**: los cuatro pasos numerados y los botones apagados que dicen por qué | Stocks: una pantalla larguísima que abre con "Alta de stock" y los 32 estados, y las existencias hasta el final |
| Gaby | **Seguimiento de hoy**: arma la lista sola, con el motivo de cada persona y el mensaje ya escrito | Estadísticas: todo en ceros contradiciendo al mismo panel que dice $4,457 |
| Renata | Pedidos: pestañas con contadores y el modal de reembolso, que pide comprobante y sugiere el importe | **"Pagos del mes · comisiones por depositar"** dentro de Clientes |
| Alma | el detalle del pedido: los datos fiscales de la factura vienen completitos | **"Pagos del mes · comisiones por depositar"**, escondida al fondo de la ficha de un cliente |

Las mejores pantallas de la ronda son **todas** de la ronda 5: Modo socio (×2), corte de caja, Despacho en bloque, Seguimiento de hoy, y el carrito con recolección y cotizador. Las peores son **todas** de antes: la orden después de pagar (×3), el comprobante del pedido (×2), el carrito de un carrito vacío (×2), la tabla de comisiones del landing, Pedidos, Stocks, Estadísticas, y Pagos del mes por estar donde está.

### 5.3 Las emociones y su disparador

148 registros. **Desconfianza 42, frustración 31, alivio 21, enojo 18, vergüenza 11**, y luego orgullo 5, gusto 4, miedo 3. Veintinueve de intensidad máxima.

**Desconfianza (42) — disparador principal: el error crudo de AWS y las pantallas que enseñan datos que no cuadran.**
- Mariana: *"una tienda seria no me enseña la dirección de su servidor de Amazon con un 'Unknown Error'; parece página pirata o a medio hacer"* (intensidad 5).
- Aurora: *"me enseñan un error técnico con una URL de Amazon; parece página a medio hacer y yo iba a poner mi tarjeta aquí"* (5).
- Alma: *"si los totales de los pedidos no cuadran solos, ningún número de arriba me sirve"* (5).
- Renata: *"dos pantallas del mismo panel me dan dos totales distintos del mismo mes"* (5).
- Ximena: *"Una tienda sin precios. En mi trabajo eso se llama cotización opaca y es motivo de descalificar al proveedor"* (5).
- Paulina: *"para cobrar $117.90 me piden gastar $960; me huele a que el premio es el anzuelo"* (5).

**Frustración (31) — disparador: el trabajo hecho que no sirve de nada.**
- Ernesto: *"Llené nombre, teléfono, correo, calle, número, ciudad, CP y estado para que al final me diga que no hay productos. Perdí como diez minutos escribiendo con un dedo"* (5).
- Fabiola: *"pagué $1,308 y la pantalla se quedó en blanco y luego me dice que no he pagado; no sé si me cobraron"* (5).
- Alma: *"de las cuatro cosas que me pidieron, entregué dos a medias y una no la pude ni empezar"* (5).
- Renata: *"es día de pago, el dueño me pidió dejar marzo liquidado y la única pantalla que existe para depositar no me deja ni seleccionar marzo de 2027"* (5).

**Miedo (3), pero el más caro de la ronda.** Mireya: *"recargué la página y la caja apareció en $0 y 'No hay ventas registradas para esta caja': pensé que se me había borrado el cobro de $760 del señor"* (5). No se había borrado: el almacén se había regresado solo a Bodega Central.

**Vergüenza (11) — la emoción que más habla del diseño, porque la persona se culpa a sí misma.** Ernesto: *"uno a esta edad siempre piensa 'ha de ser que yo le estoy picando mal'. Pero no"* (`ernesto-vidal-2027-03-02.md`). Mireya pasó dos intentos creyendo que había escrito mal su contraseña. Paulina registró vergüenza al ser felicitada por ser *"#2"* de dos personas con cero puntos: *"me premian por un segundo lugar entre dos; parece que me están endulzando el oído"*.

**Alivio (21) y orgullo (5) — y son informativos, porque señalan lo que sí está bien hecho.** Fabiola, al ver "Te faltan 1.1 VP para activar el mes · Agrega 1 Naplus ($252, +5.4 VP) y llegas a 24.3": *"Copiar el estilo del carrito al resto de la plataforma: ese aviso es lo mejor que tienen y es lo que a mí me hizo comprar"*. Mireya, ante *"No es una falta: es lo que pasó"*: *"esa frase me quitó un peso de encima"*. Toño, ante *"Listo: tu bodega por defecto ahora es Bodega Central. Stocks, Caja y Despacho abrirán con ella"*: *"me dijo exactamente qué cambió y dónde"*. Paulina, en `#/modo-socio`: *"por fin una pantalla en español claro que me explica el negocio"*.

### 5.4 A qué se les parece

Sin maquillar, en sus palabras:

- *"a una plantilla de tienda bonita a la que nunca le conectaron los productos; por fuera marca de bienestar gringa, por dentro nada"* — Mariana.
- *"a un folleto de esos que te dan en una junta donde te quieren meter a vender, no a una farmacia"* — Ernesto.
- *"a un folleto de junta de reclutamiento: puro 'propósito', 'comunidad' e 'ingresos reales', y cuando llegas a la parte de los números, la hoja está en blanco"* — Ximena.
- *"a un catálogo de multinivel de los que te pasa una tía por WhatsApp, con una tienda medio decente escondida adentro"* — Julio.
- *"a una página de gimnasio bien diseñada por fuera, con un negocio de multinivel encima; no a una tienda de suplementos donde yo compraría para mi consultorio"* — Aurora.
- *"a una tienda bien hecha con un backoffice de los noventa pegado atrás; por fuera parece un spa, por dentro parece un Excel de mi contador"* — Fabiola.
- *"a un catálogo de multinivel con un panel de banco encima: la tienda está pulida y bonita, pero la parte de mi dinero parece hecha por alguien que nunca ha esperado un depósito"* — Paulina.
- *"a un ERP hecho por alguien que entiende de almacén pero nunca cerró una nómina de comisiones"* — Renata.
- *"a un sistema de almacén al que le colgaron una parte de finanzas al final, casi de favor"* — Alma.
- *"a un sistema de contador, no a una caja de tienda; parece hecho para la oficina y no para el mostrador con gente esperando"* — Mireya.
- *"al sistema de la empresa donde trabajaba antes, hecho por alguien que sabe de contabilidad pero nunca ha cargado una caja"* — Toño.
- *"a un sistema de oficina de los que te enseña tu compañera de al lado, no a una app; útil pero sin cariño"* — Gaby.

Siete de doce nombran solos el mismo diagnóstico: **una tienda y un backoffice de operación bien hechos, con la parte del dinero (comisiones, pagos, finanzas) pegada al final por otra mano**. Y cuatro de siete personas de fuera dicen la palabra que más caro cuesta: *multinivel*, *reclutamiento*, *pirámide*.

### 5.5 ¿Volverían?

- **No:** Mariana (*"el colágeno se lo voy a comprar a otra marca esta misma noche"*), Ernesto (*"mejor voy a la farmacia de la esquina"*), Ximena (*"no como está"*).
- **Condicionado:** Julio (*"si esta devolución no se resuelve, no"*), Aurora (*"a la sucursal de Chapultepec sí, en persona; a la página no hasta que me confirmen el pago"*), Paulina (*"sólo por Fabiola y porque me deben $117.90"*), Fabiola (*"sí, pero no voy a meter a mis clientas del salón hasta que el pago se vea al momento"*).
- **Sí, porque es su trabajo:** Renata, Alma (*"mañana voy a llegar con mi cuaderno y mi calculadora igual que hoy"*), Mireya (*"pediría que me capaciten un día antes de dejarme sola"*), Toño (*"mañana voy a entrar con miedo de que otra vez no me deje"*).
- **Sí, con ganas:** Gaby (*"la de Seguimiento la abriría todos los días en cuanto llego"*). Es la única.

---

## 6. Qué mejoró de verdad desde las rondas 1 a 5

Comparación contra [22](22-diarios-inquietudes-friccion-automatizacion.md) §5 (los 17 puntos de fricción por costo) y [23](23-implementacion-23-propuestas.md) §1 (las 23 propuestas implementadas).

### 6.1 Lo que se construyó y esta ronda confirma que funciona

| Propuesta de [22] §7 | Evidencia de esta ronda | Veredicto |
|---|---|---|
| **2 · Plan publicado** (`#/modo-socio`) | **Mejor pantalla de la ronda para dos personas.** Fabiola: *"la única que me explicó PC, VP y VG con ejemplos y me dijo que me pagan el día 10"*. Paulina: *"por fin una pantalla en español claro"* — ahí entendió qué es una comisión bloqueada. `/catalog/plan` se pidió 25 veces | **Cumple**, cuando se llega. No está enlazada desde la tienda ni desde el carrito, y contradice al landing en los rangos (§3.3) |
| **5 · Completa tu activación** | Fabiola: *"Te faltan 1.1 VP para activar el mes · Agrega 1 Naplus ($252, +5.4 VP) y llegas a 24.3"*. Lo señaló como **lo mejor que tiene la plataforma** y lo que la hizo comprar | **Cumple** |
| **13 · Despacho en bloque** | La pantalla con **menor impuesto de comprensión de toda la ronda**: 3 s de mediana antes del primer clic. Toño la entendió sin que nadie le enseñara y pidió que copien su estilo | **Cumple** |
| **16 · Arqueo de caja** | Mireya lo llamó *"lo más bonito y lo mejor hecho de todo el sistema"*: conteo por denominación, motivo obligatorio, comprobante por correo, y la frase *"No es una falta: es lo que pasó"* | **Cumple el arqueo**, pero le falta el paso anterior: no hay "abrir caja" (§3.7), así que el arqueo mejor diseñado de la ronda arrojó $540 de sobrante donde había $40 |
| **15 · Seguimiento de hoy** | Gaby: *"lo mejor que me han dado para mi trabajo"*. Cuatro contactos, cuatro notas con hora, una ficha de invitada creada y cuatro asignaciones **en veinte minutos**; *"eso antes me llevaba la mañana"* (compárese con los 40+ clics por turno de Ivonne en [22] §6). Facilidad 4.8, la más alta de la ronda | **Cumple**, con dos huecos: no está en el menú y no hay "ya la atendí" (§6.3) |
| **9 · Sucursal por defecto** | Toño la fijó y verificó recargando: *"Listo: tu bodega por defecto ahora es Bodega Central"* | **Cumple** para almacén. **No para caja**: la de Mireya se regresa sola a Bodega Central al recargar |
| **8 · Botones que explican por qué** | `disabledReason` está y funciona: el "Recibir" de Toño sí traía *"Elige arriba quién recibe"*. Renata elogió el mismo patrón en el modal de reembolso | **Cumple parcialmente**: el motivo se pierde dentro de una fila de tabla densa, y no se dispara al hacer clic (§3.11) |
| **12 · Pagos del mes** | La tabla, el CSV de dispersión, el lote y "Pedir CLABE" existen y el servidor responde correctamente | **No sirvió**: nadie pudo usarla el día de pago (§3.8). El selector se arma con el reloj del equipo y la pantalla vive dentro de la ficha de un cliente |
| **18 · Devolución por producto** | Existe con líneas, evidencia por motivo y reembolso sugerido | **No se alcanzó desde el cliente**: Julio, con un bote estrellado, solo vio "Cancelar orden" del pedido completo. La entrada al flujo no está en `#/orden/:id` |
| **14 · Suscripción mensual** | Completa: crear, pausar, cancelar, día del cargo, dirección o sucursal | **No se alcanzó**: montada al fondo de la página infinita y oculta para invitados. Ernesto, cuyo único objetivo era recibir su frasco cada mes, concluyó *"No existe en ninguna pantalla"* (§3.11). Cero suscripciones dadas de alta |
| **17 · Factura** | Datos fiscales completos y correctos en el checkout (Aurora capturó RFC, régimen 612, uso G03 sin un solo tropiezo) | **Se queda a medias**: la factura vive en "solicitada" para siempre. No hay emisión, folio, PDF ni pantalla de facturas, y el botón de marcar emitida está escondido tras un permiso que finanzas no tiene (§3.9) |
| **21 · Conciliación con la pasarela** | Existe, con texto de ayuda que Renata calificó de *"clarísimo"* | **Insuficiente**: 72 horas fijas sin rango de fechas, y ninguna alerta de "pagado en la pasarela y sin acreditar" (§3.8) |
| **23 · Resumen de turno** | Existe y se pidió 323 veces | **Cumple para un turno, no para un mes**: acepta un día y una persona por consulta. Alma lo consultó 155 veces (31 días × 5 personas) para cerrar marzo |

### 6.2 Lo que sigue igual desde [22] §5

| Fricción de [22] §5 | Estado en [22] | Estado hoy |
|---|---|---|
| #1 Checkout que exige registro según la puerta de entrada | Abierto | **Peor documentado**: se puede comprar como invitada (Aurora lo hizo) pero elegir recolección esconde el correo que el pago exige (§3.5) |
| #2 Pasarela | "Corregido (ronda 1 y 3)" | **Reabierto y agravado**: cuatro clientas pagaron dos veces. Lo que falta ya no es la pasarela, es el estado intermedio en pantalla (§3.2) |
| #4 Envío "Gratis" que se vuelve $129 | Abierto | **Corregido en el flujo** (el cotizador por CP funciona y Julio y Aurora lo elogiaron). Sigue mordiendo en el negocio: el descuento de $131 de Fabiola se lo comió el envío de $129 |
| #5 Contraseña y códigos | Abierto | **Sustituido por otro muro**: nadie perdió la contraseña; once de doce se estrellaron con el error crudo (§3.1) |
| #11 Botones "Ver" duplicados | Abierto | **Distinto pero vivo**: el "Ver" de Pedidos vacía la lista sin avisar porque el contador de la pestaña no respeta el filtro de almacén, y el selector aparece tarde y desplaza la barra bajo el cursor. Mireya lo intentó 3 veces con una clienta enfrente; Alma: *"mi clic en Ver me abrió un desplegable de sucursales"* |
| #12 Stock por defecto en la sucursal equivocada | Parcial | **Corregido para almacén, abierto para caja** (§6.1) |
| #16 Tres módulos, tres cifras del mismo mes | "Corregido en su mayoría" | **Reabierto con fuerza**: cuatro pantallas con cuatro meses distintos y dos totales de marzo ($4,457 y $5,417). Renata: *"no sé en qué mes vive el sistema"* |
| §3.1 "Me metieron a un MLM sin decírmelo" (9 personas en [22]) | Abierto → "Implementado" en [23] | **Sigue siendo la queja número uno de los clientes**: Mariana, Ernesto, Ximena, Julio y Aurora lo dicen otra vez. El modo cliente existe por dentro, pero la tienda sigue hablando de PC, el carrito de metas y el comprobante ofrece "Activar modo socio" como su elemento más grande |
| §3.2 No se puede calcular el negocio | Parcial → "Implementado" | **Corregido para quien llega a `#/modo-socio`, intacto para quien no.** Ximena recorrió las cinco pantallas públicas y se fue sin un número del lado del ingreso |
| §3.6 Devoluciones | Parcial → "Implementado" | **Abierto desde el lado del cliente** (§6.1) |
| §4.7 Contactar a quien no quiere | "Corregido" | **Se sostiene**: "No contactar", notas y bitácora siguen funcionando. Gaby no reportó ni un problema ahí |

### 6.3 Lo que la ronda 6 encontró y ninguna ronda anterior había visto

1. **El día de pago no tiene día de pago** (§3.8). Las rondas anteriores nunca simularon un cierre de mes con una persona de finanzas.
2. **La caja no se puede abrir** (§3.7). La ronda 5 construyó el arqueo sin el movimiento de apertura.
3. **Un tablero que sube cuando reembolsas** (§3.6). Renata lo encontró por casualidad al recargar.
4. **El panel del cliente es una página infinita con un menú de anclas** (§3.10). Seis personas creyeron que había botones rotos.
5. **Los permisos esconden trabajo y abren trabajo ajeno** (§3.9).
6. **Pantallas que inventan datos cuando el servidor no responde** (§3.3), incluidos rangos comerciales veinte veces más bajos que los reales.
7. **No hay canal interno entre empleados** (§3.14): el resumen de turno, las incidencias y las autorizaciones salen por WhatsApp, exactamente como en [22] §6, aunque el resumen de turno automático ya existe.

---

## 7. Propuestas priorizadas

Cada una con su evidencia. **[P]** = cambio de pantalla (acotado, una o pocas plantillas). **[F]** = cambio de flujo (toca varias pantallas y el orden en que ocurren las cosas). **[N]** = decisión de negocio.

### 7.1 Esta semana — alto impacto, esfuerzo bajo

| # | Propuesta | Evidencia |
|---|---|---|
| 1 | **[P] Un mapeador de errores compartido.** `status===0` → "No pudimos conectar con el servidor; revisa tu conexión e inténtalo de nuevo". `status>=500` → "Tuvimos un problema de nuestro lado". **Nunca** `error.message` como último recurso. Un solo *helper* arregla los ~18 sitios | 11 de 12 personas, 4 abandonos, media hora de la jornada de Gaby. Mireya: *"Yo pensé que había escrito mal mi contraseña"*. Mariana: *"parece página pirata"* (desconfianza 5) |
| 2 | **[P] Estado "Confirmando tu pago…" al volver de la pasarela**, con el botón de pagar deshabilitado N minutos y el aviso "ya registramos un intento de pago de este pedido; no vuelvas a pagar" cuando existe `paymentPreferenceId` reciente | 4 clientas, 4 cobros dobles ($960, $1,180, $1,308 × 2). Julio: *"Ese es el momento en que la gente paga dos veces"*. Fabiola: frustración 5 dos veces |
| 3 | **[P] Que el comprobante del pedido liste las partidas**, el desglose subtotal/descuento/envío/total, la sucursal con nombre y dirección cuando `deliveryType==='pickup'`, y "Factura solicitada · datos registrados". Y que el paso 4 de la línea de tiempo diga "Listo para recoger · Sucursal X" en los pedidos de recolección | Aurora, Julio, Mireya, Paulina. La API ya trae los tres datos. Mireya: *"Yo necesito saber QUÉ le entrego a la señora y aquí no viene"* |
| 4 | **[P] Borrar los valores por omisión que inventan datos:** el `defaultHero` de la tienda, el `rankThresholds` literal del landing, y el `return` mudo de `addToCart()`. Si el catálogo o la config no cargan, estado de error con reintento — nunca "0 productos" ni una promesa comercial | Ximena decidió no comprar por la tabla vacía; Fabiola preguntó "¿a cuál le creo?" con rangos 20 veces menores que los reales. Ernesto, Mariana, Aurora, Julio se fueron por "0 productos" |
| 5 | **[P] Excluir `refunded` del total cobrado** (o restarlo y mostrar "Reembolsado en el periodo: −$960" en línea aparte), y aplicar el mismo criterio en Estadísticas | Renata: *"Devolví $960 y el panel me sumó $960 de ingreso"* (enojo 5). Alma iba a reportarlo al contador |
| 6 | **[P] Imprimir subtotal, descuento y envío en el detalle del pedido.** La API ya devuelve `grossSubtotal`, `discountRate`, `discountAmount`, `netTotal`, `shippingCost` | Alma: *"Cinco pedidos, dos que no cuadran consigo mismos"* (frustración 5, desconfianza 5) |
| 7 | **[P] Un diccionario de etiquetas** para `status`, `paymentMethod` y `cancelReason`, y desdoblar `mixed` en su composición ("Mixto: $500 efectivo + $260 tarjeta") | Alma: *"¿Eso se lo enseño así a mi jefa?"*. Los $260 sin desglosar son lo único que le faltó a ella y a Mireya para cuadrar el corte |
| 8 | **[P] Sacar Nombre/Teléfono/Correo del bloque condicionado a "delivery"** y ponerlos en un bloque de contacto común a los dos modos de entrega | Aurora: *"Me pide un dato que la pantalla no me deja capturar"*. Paulina: *"¿Con qué me presento en la Tienda Del Valle?"* |
| 9 | **[P] Resolver identificadores a nombres**: `customerName(c.leaderId)` en el CSV, un `userName()` que mire clientes **y** empleados, y `stockId`/`attendantUserId` a nombre en el comprobante del corte. Y no truncar nombres propios por número de caracteres | Mireya: *"¿Ese numerote soy yo?"*. Gaby: *"Mi nota quedó firmada por '1803978000183'"*. Fabiola: *"Me cortaron el nombre y encima quedó de hombre"* |
| 10 | **[P] Un pie de página real:** año calculado, WhatsApp, correo, teléfono, términos, política de devoluciones y aviso de privacidad enlazados — sobre todo porque el carrito ya obliga a aceptar unos términos que no se pueden leer | Aurora, Julio, Ximena, Paulina. Ximena: el aviso manda a "canales de contacto oficiales" que no existen |
| 11 | **[P] "Empatadas" en lugar de "−0"**, y un pie en el Cuadro de Honor cuando nadie alcanza el primer rango: "Aún nadie llega a BRONCE (4,500 VG)" | Alma: *"¿Menos cero?"* |
| 12 | **[P] Cuando el servidor no manda `templateKey`, dejar "Sin plantilla (escribo yo)" seleccionado**, y añadir una plantilla de posventa para la situación "activa" | Gaby tuvo que borrar el texto dos veces; a Fabiola le iba a preguntar por un producto que aún no recibía. Cambio de una línea en el front más una entrada en `PLANTILLAS` |

### 7.2 Este mes — alto impacto, esfuerzo medio

| # | Propuesta | Evidencia |
|---|---|---|
| 13 | **[F] "Comisiones" como entrada propia del menú**, al mismo nivel que Pedidos, con la pantalla de Pagos del mes fuera de la ficha del cliente; el mes lo pone el servidor con la fecha del negocio; el día 10 abre en el mes que toca pagar, con el mes escrito grande | Renata y Alma, las dos, la señalaron como **peor pantalla de la ronda**. Alma: *"Me contrataron para cuadrar el dinero y el menú del sistema no tiene ni una palabra de dinero"*; dos horas buscándola |
| 14 | **[F] Una sola fuente de la fecha de negocio en todo el panel.** Ningún periodo, selector ni nombre de archivo se arma con `new Date()` del navegador | Cuatro pantallas con cuatro meses distintos; Clientes y Seguimiento dan días distintos de la misma persona. Renata: *"no sé en qué mes vive el sistema"* |
| 15 | **[F] "Abrir caja" con fondo declarado**, contado por denominación igual que el corte; o permitir editar `openingCash` en el primer corte de una caja | Mireya: *"Si le pongo lo que de veras conté me va a parecer que metí dinero; si pongo $540 estoy mintiendo del conteo"*. Sin esto ninguna caja nueva puede cuadrar nunca |
| 16 | **[F] Validar el código de autorización al salir del paso 3** y ofrecer salida cuando no se tiene: cerrar el corte dejando el efectivo marcado "pendiente de retiro autorizado" | Los $1,040 del día se quedaron en el cajón toda la noche. *"Si me lo hubiera dicho en el paso 3, no me habría hecho llenar todo"* |
| 17 | **[F] Un glosario de una línea junto a cada sigla**, alimentado por `unidades` de `/catalog/plan` (el texto ya existe, solo hay que pintarlo), con la equivalencia en pesos al lado de cada cifra en puntos; y un "¿por qué?" junto a cada comisión "Bloqueada" que abra la explicación del cierre y de la activación | 9 de 12 personas preguntaron qué es PC. Fabiola: *"Son tres monedas distintas en la misma pantalla"*. Paulina tardó media hora y una casualidad en entender "Bloqueada" |
| 18 | **[F] Partir el panel del cliente en rutas de verdad** (`#/mis-pedidos`, `#/comisiones`) o, como mínimo, que `scrollToSection` nunca falle en silencio: si la sección no existe, el enlace no está en el menú. "Ver beneficios" debe abrir la ficha del producto | Seis personas reportaron botones rotos y ninguno lo era. Julio: *"Prefiero un botón gris que uno que me ignora"*. Es el hallazgo de diseño más importante de la ronda |
| 19 | **[F] Anunciar la recompra recurrente donde se decide la compra:** casilla "recibirlo cada mes" en la ficha del producto y en el carrito, visible también para invitados; y subir la sección por encima del catálogo en el panel | Ernesto, cuyo **único** objetivo era ese, concluyó "No existe en ninguna pantalla". Cero suscripciones dadas de alta en toda la ronda |
| 20 | **[F] Entrada a la devolución desde `#/orden/:id`:** "Tengo un problema con este pedido", con las partidas y una casilla por línea, foto, motivo, y en la misma pantalla quién paga el regreso, cuánto se devuelve y en cuántos días hábiles | Julio, con un bote estrellado y $800: *"la única salida que me dan es cancelar TODO, incluidos los electrolitos que sí sirven"*. El flujo completo ya existe en el backoffice |
| 21 | **[F] Correo inmediato al crear el pedido**, con folio, partidas, total, modo de entrega y enlace de seguimiento. Es la red de seguridad de todo lo demás | Paulina: *"Me llega correo por cancelar un pedido pero no por hacerlo ni por pagarlo"*. Mariana, Ernesto y Aurora se quedaron sin ninguna constancia de haber existido |
| 22 | **[F] Rango de fechas en "Conciliar pagos"** (el backend ya acepta `hours` hasta 90 días) y una alerta de "pagado en la pasarela y sin acreditar" | Renata: *"solo mira 3 días atrás y yo venía a revisar marzo entero"*. Por ahí se perdió el pago de Paulina del 20 de marzo |
| 23 | **[F] Privilegio propio para facturación** (`invoice_mark_issued`) otorgado a finanzas, y **nunca esconder un control por permiso sin dejar rastro**: pintarlo deshabilitado con `disabledReason`, el patrón que el producto ya usa | Alma, persona de finanzas: *"no hay NINGÚN botón para marcarla como emitida"*. Y un filtro transversal "Factura: solicitada / emitida / no aplica" que atraviese las nueve pestañas de estado |
| 24 | **[F] Privilegio propio para Campañas** (`access_screen_campaigns`), puesto real en la cabecera en lugar de "ADMIN", y vista inicial por puesto (Caja para Mireya, Almacenes para Toño) | Toño: *"Con mi usuario de almacén puedo crear campañas de publicidad… Si le muevo por curiosidad, rompo algo de otro"*. Gaby: *"Yo no soy admin, soy coach"* |
| 25 | **[F] "Ya la atendí" / "Recordarme en X días" en Seguimiento**, un "asignarme" directo en la fila, y **"Seguimiento de hoy" en el menú de la izquierda, bajo SEGUIMIENTO** | Gaby: *"Si mañana entra otra compañera va a ver el mismo renglón y le va a volver a escribir"*. Es la pantalla mejor calificada de la ronda y la única que no está en el menú |
| 26 | **[F] Que "Acciones urgentes" incluya traspasos pendientes de recibir y cortes sin retiro autorizado**, y se refresque sin recargar; más **notas internas por documento** (traspaso, corte, pedido) visibles para el equipo | Toño tenía 40 botes colgados y el tablero decía "Todo en orden". Él y Renata acabaron los dos en WhatsApp |
| 27 | **[P] Que "Exportar" diga y deje elegir el mes** ("Comisiones por depositar · marzo 2027"), con el mismo selector que ya tiene Pagos del mes | Renata: *"me bajó comisiones-2026-08.xlsx. Y en ningún lado de la tarjeta dice de qué mes es"* |
| 28 | **[F] Mínimos por producto y bodega, semáforo, y vista consolidada de las tres bodegas** (producto en filas, bodegas en columnas), más "En camino: 20 Finding Pro (TRF-…)" en el destino | Toño: *"es literalmente lo que mi jefa me pide todos los días y lo tengo que sacar a ojo abriendo bodega por bodega"*. **Requiere antes la decisión de negocio 7 del §4.2** |
| 29 | **[P] Que "Resumen de turno" acepte un rango de fechas y "todas las personas"** | Alma lo consultó **155 veces** (31 días × 5 personas) para cerrar un mes; 159 de sus 208 clics se fueron ahí |
| 30 | **[F] "Entregado en mostrador" en la fila del pedido pagado**, sin guía inventada ni correo de "va en camino"; y que el folio del panel abra la vista de operación, no la del comprador | Mireya despachó con guía inventada y le mandó a la clienta un correo falso. *"Yo pensé que era la pantalla del cliente… me ofrece 'Cancelar orden'"* |

### 7.3 Decisiones de negocio, antes de escribir código

| # | Decisión | Por qué no espera |
|---|---|---|
| N1 | **Un canal de soporte publicado** (teléfono, WhatsApp y correo en el pie y en todos los correos) y si se atiende por teléfono a quien no puede con la web | Aurora, Paulina, Julio y Ernesto lo buscaron y no existe. Ernesto dejó su número (8181002002) en un mensaje que nadie recibió. En [22] §8 ya estaba escrito que *"soporte humano es lo que retiene"* |
| N2 | **Qué se hace con el dinero de Paulina:** $960 cobrados dos veces sin registro de pago por pedido, $117.90 de comisión perdida por una falla propia, y si se da por buena su activación de marzo | Es el caso completo: pagó, no recibió producto, ni comisión, ni comprobante, ni explicación el día de pago |
| N3 | **Política de devolución escrita:** quién paga el envío de regreso, en cuántos días llega el dinero, y si hay devolución parcial | Julio tiene un bote roto en la mesa y $800 en el aire. La política configurada solo dice "mismo medio de pago, 3 a 5 días hábiles" |
| N4 | **Corregir el aviso de privacidad.** Hoy jura *"No te pedimos datos bancarios ni fiscales"* mientras el checkout pide RFC y régimen y a las socias se les exige constancia fiscal, INE, CURP y CLABE | Mariana lo citó como *"lo único que me dio confianza"* — y es falso. Decir "si pides factura te pediremos tus datos fiscales" da más confianza que jurar que no |
| N5 | **Los $129 de envío de quien recogió en mostrador** | Mireya no supo qué hacer y no hay flujo para reembolsar solo el envío |
| N6 | **Mínimo de existencias por producto y bodega** | Sin ese número, la propuesta 28 no se puede construir |
| N7 | **Si se depositan comisiones fuera del sistema** mientras la pantalla no lo permita | Renata hizo lo correcto: *"No voy a mover dinero sin que el sistema me deje dejar constancia"*. Y por eso nadie cobró |
| N8 | **Separar la tienda del programa de socias en la copia visible.** Cinco de siete personas de fuera dijeron "multinivel", "reclutamiento" o "pirámide" | Es la misma inquietud número uno de [22] §3.1, con nueve personas entonces y cinco ahora. El modo cliente existe por dentro; la copia sigue empujando "Activar modo socio" en el comprobante del pedido |

---

## 8. Cómo se midió

### 8.1 El arnés

- **Un solo navegador por persona**, contra el front en `http://localhost:4321` y la API en `http://localhost:4400`, con el reloj del mundo simulado en marzo–abril de 2027. Ninguna persona leyó código: todo lo que sabe lo averiguó desde la pantalla.
- **Lo que cuenta el arnés solo:** clics, teclas, envíos de formulario, campos tocados, pantallas visitadas, recargas, "atrás", ruta de cada pantalla y cómo se llegó a ella (carga, navegación, atrás), y **milisegundos entre llegar a una pantalla y el primer clic** — la medida del §2.2.
- **Lo que registra la persona:** el enunciado de cada tarea ("quiero…"), si la logró, sus pensamientos con el tiempo transcurrido desde el anterior, dudas con la pantalla donde surgieron, atorones, reintentos, preguntas (a quién y con qué texto), emociones con intensidad 1–5 y su disparador, errores vistos en pantalla, y al final la ficha de estética (primera impresión, confianza, legibilidad, coherencia, sensación en móvil, tres adjetivos, mejor y peor pantalla, "a qué se parece", recomendaría y volvería).
- **Derivadas:** facilidad (1–7) y confianza en que quedó guardado (1–5) por tarea; `sim/metricas.py` agrega por persona y por tarea; `sim/cobertura.py` lee el registro del servidor y lo cruza con las rutas que declara el frontend.
- **Verificación posterior:** una revisión independiente reprodujo cada síntoma contra el código y contra la API antes de clasificarlo. De ahí salen los tres veredictos del §3, y de ahí sale que tres de los 40 hallazgos son del arnés, no del producto.

### 8.2 Lo que el arnés metió de su cosecha (y qué destapó)

Se documenta para que nadie lo lea como defecto del producto — y para no perder lo que cada uno dejó ver:

1. **El front apuntaba a la API de producción en AWS, no al servidor local.** Ambos `environment.ts` traen `apiBaseUrl` del API Gateway; el de desarrollo no apunta a `localhost:4400`. Contra el servidor local todo responde: `GET /catalog` devuelve 13 productos con precio, `/catalog/config/public` los cinco niveles de comisión y las cinco franjas de descuento, `/catalog/plan` el plan completo. **Destapó tres defectos reales**: el mensaje de error crudo, el producto inventado en la tienda y los rangos inventados en el landing.
2. **La semilla puso `webhookSecret` sin `notificationUrl`**, así que el webhook de MercadoPago se rechazó con 401 catorce veces y ningún pago se acreditó. **Destapó dos defectos reales**: que el checkout acepta esa media configuración sin alerta, y que el cobro doble es independiente del webhook.
3. **El reloj del navegador (septiembre de 2026) contra el del mundo simulado (marzo–abril de 2027).** En producción los dos coinciden. **Destapó el defecto real**: dos pantallas del mismo panel calculan la misma cifra con dos relojes distintos, y el origen de la fecha de negocio debe ser siempre el servidor.

Ninguno de los tres se arregló durante la ronda: las doce personas trabajaron con ellos encima, que es también parte de por qué la tasa de logro fue del 50 %.

### 8.3 Métricas que conviene añadir la próxima

1. **Tiempo hasta el primer dato útil** por pantalla: no solo cuánto tarda en dar el primer clic, sino cuántos segundos pasan hasta que la persona lee el número que vino a buscar. Es la métrica que habría puesto un número al *"estuve dos horas convencida de que se me estaba escapando algo"* de Alma.
2. **Distancia de scroll** (píxeles y pantallazos) hasta el elemento que resuelve la tarea. Julio describió sus órdenes como *"enterrado como diez pantallazos abajo en el celular"* y hoy eso solo existe como frase.
3. **Retrocesos por pantalla**: cuántas veces la persona entra a una vista y sale sin actuar. Distinguiría "no lo encontró" de "lo encontró y no le sirvió", que hoy se confunden en el conteo de pantallas.
4. **Clics sobre elementos que no responden** (controles deshabilitados, anclas muertas, botones con `return` mudo), con el selector. Habría cuantificado en segundos el §3.10 en lugar de contarlo por testimonios.
5. **Reintentos idénticos**: repetir exactamente la misma acción es la firma de "no sé si funcionó". Aurora, Julio, Fabiola y Paulina pagaron dos veces; el arnés lo supo por sus diarios, no por el contador.
6. **Preguntas resolubles en pantalla, medido en vivo**: hoy la clasificación (21 de 31) la hizo soporte al contestar. Si al registrar la pregunta se anota la pantalla donde estaba la persona, sale solo el mapa de "la respuesta estaba a un scroll de distancia".
7. **Un contador de correos esperados y no recibidos** por persona: cinco personas se quedaron sin ningún acuse y eso solo aparece en frases ("cero correos", "ni un correo"), no en una cifra.
8. **Cobertura por pantalla, no solo por ruta de API.** `sim/cobertura.py` dice que 40 de 79 rutas nunca se tocaron, pero no dice qué pantallas nadie abrió — y las pantallas que nadie abre son, esta ronda lo demuestra, el problema principal del producto.
