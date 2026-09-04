# Alma Rentería · administración y finanzas · sábado 10 de abril de 2027

Es mi primer cierre en Finding'U. Nadie me sentó a explicarme el sistema: me pasaron un correo, una
contraseña y la lista de lo que tengo que entregar. Escribo esto mientras trabajo para no perder de
vista dónde vi cada número.

---

## 12:00 · Entrar

`http://localhost:4321/#/login`. Lo primero que veo es un aviso de privacidad que tapa la pantalla:
"En Finding'U protegemos tus datos personales… No te pedimos datos bancarios ni fiscales." Me hizo
gracia, porque yo justamente vengo a pedir CLABEs y RFCs. Le doy "Entendido y acepto", pongo mi
correo y entro a la primera. Al pie dice **"© 2026 finding U"** y hoy es 10 de abril de 2027.

## 12:03 · El menú (aquí empieza mi problema)

Leo la navegación completa, palabra por palabra:

> OPERACIÓN DIARIA · **Pedidos** — PERSONAS · **Clientes** — CATÁLOGO Y OFERTA · **Cupones** —
> SEGUIMIENTO · **Estadísticas**, **Cuadro de Honor**, **Notificaciones** — SISTEMA · **Configuración**

Busco mis palabras: Comisiones, Caja, Cortes, Facturas, Bancos, Reportes, Ventas. **No está ninguna.**
Siete opciones y ni una que se llame como se llama mi trabajo. Me quedé un rato mirando la pantalla
pensando que se me había cargado a medias.

Lo único que promete algo es un botón arriba: **"Acciones · 2 urgentes"**. Lo abro:

> "1 socias con comisión y sin CLABE · $135.00" — Urgente — [Ir a resolver]
> "4 pedidos pagados sin envío" — Importante — [Ir a resolver]

Ahí sí aparece la palabra comisión. Le doy "Ir a resolver".

## 12:08 · Las comisiones estaban escondidas en Clientes

El botón me manda a **Clientes**, y hasta el fondo del todo, debajo de la ficha de un cliente
cualquiera, está el módulo que yo necesitaba:

> **"Pagos del mes · comisiones por depositar** — Quién cobra cuánto, con su CLABE. Exporta el archivo
> para el banco, sube un comprobante por lote y marca pagadas en bloque."

Es exactamente lo que pedí. Y está colgado del final de la pantalla de Clientes, sin nombre en el
menú. **Si no me sale ese aviso urgente, no lo encuentro hoy.** Sentí alivio y coraje al mismo tiempo.

El selector de mes me deja frío: **marzo 2027, septiembre 2026, agosto 2026, julio 2026…** Faltan
octubre, noviembre y diciembre de 2026 y enero y febrero de 2027. Si mañana me piden febrero, no lo
puedo sacar.

Los números de marzo:

| | |
|---|---|
| Listas para depositar | **0 · $0.00** |
| Sin CLABE | **1 · $135.00** |
| Pagadas | **0 · $0.00** |

Y arriba, en la misma pantalla, el recuadro grande dice **"Comisiones por depositar $135"**. Abajo dice
$0.00 listas. Dos cifras del mismo concepto separadas por dos dedos de pantalla.

La única fila: **Paulina Ríos · paulina.rios@gmail.com · $135.00 · CLABE "No registrada" · Sin CLABE ·
"Recordatorio enviado el 10 abr 2027"**.

El botón **"Exportar archivo de dispersión (CSV)" está apagado**, y al menos me dice por qué:
*"No hay socias listas para depositar este mes."* Eso sí lo agradezco: los botones apagados de este
sistema explican su motivo, no todos lo hacen.

Le doy **"Pedir CLABE"**. Sale una ventana honesta: *"Paulina Ríos tiene $135.00 confirmados de marzo
2027 y no ha registrado su CLABE… Ya se le pidió el 10 abr 2027."* Lo mando igual, quiero constancia
mía. **Y no pasó nada visible**: ni un aviso, ni un "enviado". Fui a revisar el correo de Paulina y sí
está, a las 12:04 de hoy: *"Registra tu CLABE para cobrar tus comisiones"*. O sea, funcionó, pero yo
me quedé sin saberlo.

En ese mismo buzón encontré algo que no me cuadra nada. El **20 de marzo** el sistema le escribió:
*"Tienes **$259.20** en comisiones bloqueadas que se pierden el 31 de marzo"*, y el mismo día otro
correo: *"Fabiola Cantú Robledo compró; te genera una comisión de **$124.20**"*. Y a mí el panel me
dice **$135.00**. Tres cifras. Ninguna pantalla me explica cómo se pasa de una a otra.

**Resultado: el pago de comisiones de marzo queda detenido.** Le escribí a Renata.

## 12:30 · Cuánto entró en marzo

Voy a Pedidos esperando un filtro de fechas. **No hay.** Hay pestañas por estado, un selector de
sucursal y una caja de "Buscar por cliente, guía, teléfono, dirección…". Nada más. Tampoco hay botón
de exportar. Así que copié los nueve renglones a mano:

| Folio | Fecha | Cliente | Suma de productos | Total en pantalla | Diferencia |
|---|---|---|---|---|---|
| POS-E26D95B4 | 03/03 | Publico en General | $760 | **$760** | – |
| ORD-1F950075 | 02/03 | Mariana Robles | $700 | **$829** | +$129 |
| ORD-7C55FDBD | 02/03 | Ximena Paredes | $1,500 | **$1,350** | **−$150** |
| ORD-682C1E22 | 02/03 | Julio Herrera | $1,080 | **$1,209** | +$129 |
| ORD-97E56995 | 02/03 | Ernesto Vidal | $480 | **$609** | +$129 |
| ORD-0F7B6112 | 20/03 | Paulina Ríos | $960 | **$960** | – |
| ORD-9CD8BD3D | 04/03 | Fabiola Cantú | $1,380 | **$1,371** | **−$9** |
| ORD-1A2D13F6 | 04/03 | Aurora Vega | $1,500 | **$1,500** | – |
| ORD-351342D9 | 04/03 | Aurora Vega | $1,500 | **$1,500** | – |
| | | | **$9,860** | **$10,088** | **+$228** |

El total ($10,088 / 9 pedidos) sí cuadra con el recuadro de arriba. Lo que **no** cuadra es el detalle:
**el detalle del pedido no tiene desglose**. No dice subtotal, no dice envío, no dice descuento, no
dice IVA. Solo los productos y un "Total" que no es la suma de los productos. Supongo que los $129 son
flete porque son justo los tres que llevan guía, pero **la palabra "envío" no aparece con importe en
ninguna parte**, y los −$150 de Ximena y los −$9 de Fabiola no los puedo explicar de ninguna manera.

De la vía de venta, mi respuesta honesta: **1 venta de mostrador ($760) y 8 por internet ($9,328)**,
y eso lo deduzco **yo** porque un folio empieza con `POS-`. **No hay ninguna columna que diga el canal
ni la forma de pago.** Ni en pantalla ni en el Excel.

Un detalle feo: el ticket de mostrador POS-E26D95B4 aparece en la lista como "Tienda Del Valle" y al
abrirlo dice **"Dirección de envío · Sucursal: Sin stock"**. La misma sucursal escrita de dos maneras
en la misma pantalla.

Y dos pedidos me dejaron pensando: **ORD-1A2D13F6 y ORD-351342D9, los dos de Aurora Vega, el mismo
04/03, los dos con Colageno Hidrolizado x1 $700 + Finding Pro 500g x1 $800 = $1,500, los dos a recoger
en Sucursal Guadalajara**, uno pedido a las 11:05 y el otro a las 17:02. O compró dos veces lo mismo el
mismo día, o le cobramos doble. **Desde aquí no lo puedo saber.**

## 12:55 · Estadísticas, y el susto del día

Entro a Estadísticas. Arriba dice el mes y abajo:

> Ventas del periodo **$0** · 0 pedidos · Ticket promedio **$0** · Productos vendidos **0**
> Pedidos por estado: **"Sin pedidos en el periodo."** · Top clientes: **"Sin datos."**

Y en la misma pantalla, en la esquina, **"$10,088 cobrado · 9 pedidos"**. Me quedé fría: estuve a
punto de reportar que marzo cerró en ceros.

Le di a **"Reporte completo Excel"** y el archivo se bajó llamándose **`reporte-mensual-2026-09.xlsx`**.
Ahí me cayó el veinte: **el selector estaba puesto en "Septiembre de 2026"**, aunque "Marzo de 2027" es
la primera opción de la lista. La pantalla abre en un mes de hace siete meses y **no te avisa**. Media
hora perdida y un reporte falso a punto de salir de mis manos.

Lo cambié a mano a "Marzo de 2027" y ahí sí: **$10,088 · 9 pedidos · ticket promedio $1,120.89 · 17
unidades · 5 SKUs**. Cuadra con mi conteo a mano, eso me tranquilizó.

Lo que sigue mal en esa pantalla:
- **"Pedidos por estado: delivered 5 — $0 / paid 4 — $0"**. Los estados en inglés y **los importes en
  cero**, cuando yo ya sumé $4,757 entregados y $5,331 pagados.
- **"Top clientes del periodo"** no está ordenado: #2 es Paulina con $960 y #3 es Fabiola con $1,371.
  Un top que no ordena de mayor a menor no es un top. (En el Excel sí viene bien ordenado.)
- Dice **"Clientes activos 7"** cuando en Clientes los siete salen como **"Inactiva"**, y **"0%
  recompra"** cuando Aurora compró dos veces.
- El mismo hueco de meses: de Marzo 2027 salta a Septiembre 2026.

El Excel (`reporte-mensual-2027-03.xlsx`) trae 5 hojas: Resumen, Pedidos, Clientes activos, Productos
e Inventario. La de Pedidos me sirve. Pero **la hoja Productos suma $9,860 de ingresos y el Resumen
dice $10,088**: los mismos $228 sin renglón que los explique. **La hoja Inventario viene vacía**, solo
el encabezado. Y no trae forma de pago, ni canal, ni cortes de caja, ni devoluciones, ni facturas, ni
comisiones. Justo las cinco cosas del cierre.

## 13:20 · Los cortes de caja

Encontré la caja por casualidad, en un botón que dice **"Resumen de turno"** dentro de Estadísticas.
Es una pantalla marcada **"EQUIPO"** que dice *"El mismo texto que antes se escribía a mano; listo para
pegar en WhatsApp"*. O sea, está pensada para el mensaje de cierre del turno, no para contabilidad.

Y el campo de fecha me llegó con **"2026-09-04"**, con el texto *"No hay movimientos de Alma Rentería
el 4 sep 2026"*. Hoy es 10 de abril de 2027.

Lo puse en Mireya Solano / 2027-03-03 y aquí está lo que vine a buscar:

> Ventas en caja **$760.00**
> Caja: **POS-E26D95B4 · Publico en General · $760.00 · mixed**
> **Corte CUT-8D11C495 · $500.00**

**Vendió $760 y el corte declara $500.** Faltan $260, o esos $260 se fueron en tarjeta. **La pantalla no
me deja saberlo**: escribe la palabra **"mixed"**, en inglés, sin decir cuánto fue efectivo y cuánto
tarjeta. Es literalmente el número que vine a cuadrar y me lo esconde detrás de una palabra.

Probé el 2, el 4, el 20 y el 31 de marzo: "Sin ventas ni cortes". Así que en todo marzo hubo un solo
corte. Pero para asegurarme tendría que hacer **5 personas × 31 días = 155 consultas**, porque solo se
puede pedir **una persona y un día** a la vez.

## 13:40 · Devoluciones y reembolsos

Recorrí las cinco pestañas: **Cancelado 0, Reembolsado 0, Por devolver 0, Devuelto 0, Dev. rechazada
0**. Mi respuesta para el cierre: **en marzo de 2027 no hubo devoluciones ni reembolsos.** Lo firmo,
pero con la incomodidad de que **no tengo un papel que lo respalde**: ni el Excel ni ningún reporte
traen devoluciones. Solo puedo decir "vi cinco pestañas vacías".

## 13:50 · Facturas

Aquí lo bueno y lo malo juntos. Al abrir el pedido, los datos fiscales **están completos y bien
puestos**:

> "Factura solicitada · pedida el 04/03/2027 17:02 — RFC: VEGA850312AB1 — Razón social: Aurora Vega
> Morales — Régimen: 612 — CP fiscal: 44160 — Uso CFDI: G03 — Enviar a: aurora.vega@gmail.com"

Lo malo: **no existe pantalla de facturación**. Busqué las palabras "factura", "CFDI", "RFC" y "fiscal"
en toda la Configuración: **ninguna aparece**. Lo único que sale es "1 VP = X MXN netos (sin IVA ni
envío)". No hay dónde poner el RFC de la empresa, ni el IVA, ni la serie de folios, ni **dónde marcar
una factura como emitida**. Y para encontrarlas tuve que abrir pedido por pedido.

Mi lista de marzo, hecha a mano:
**ORD-1A2D13F6 — Aurora Vega — $1,500 — pedida 04/03/2027 11:05**
**ORD-351342D9 — Aurora Vega — $1,500 — pedida 04/03/2027 17:02**
**Total facturas pedidas y sin emitir: $3,000.**

## 14:05 · Cosas sueltas que anoté

- **Notificaciones** dice arriba *"Total 3 · Activas 0 · Programadas 0 · Expiradas 0"* y abajo *"3
  registradas"*, las tres con la etiqueta **"Activa"** y con fechas que incluyen hoy.
- Ahí vi un aviso del 4 de marzo dirigido a **Fabiola Cantú**: *"Ya tienes comisiones a tu favor…"*.
  Fui a su ficha: **"Comisiones mes actual $0 · mes anterior $0 · Sin movimientos"**. O el aviso mintió
  o la comisión se perdió.
- En Clientes, la columna "Última compra" dice **"02/03/2027 · 0 días"** y **"04/03/2027 · 0 días"**.
  Son 39 y 37 días. Con esos ceros, el filtro **"Solo fríos (30+ días sin compra)"** no va a marcar
  nunca a nadie.
- En la ficha de Paulina, la gráfica "Consumo de la red del cliente en el periodo" muestra **"Pauli |
  $0", "Fabio | $0", "Ximen | $0"** — nombres cortados a cinco letras y todo en cero.
- "Conciliar pagos" corrió bien y me dijo claramente *"No hay pedidos pendientes de pago en las últimas
  72 horas"*, pero **la ventana se queda abierta tapando el menú** hasta que la cierras a mano; me
  atoré un rato pensando que la aplicación se había trabado.

## Qué entrego y qué no

**Entrego:** ventas de marzo $10,088 en 9 pedidos ($760 mostrador / $9,328 internet, deducido por mí);
cero devoluciones; 2 facturas pedidas sin emitir por $3,000; y el Excel de marzo.

**No entrego:** el archivo de dispersión para el banco (bloqueado por la CLABE de Paulina); la
explicación de los $228 de diferencia entre producto y total; y el cuadre del corte de caja del 3 de
marzo ($760 vendidos contra $500 declarados).

**Lo que le pedí a Renata por WhatsApp:** qué hacemos con la comisión de Paulina, cuál de las tres
cifras es la buena ($259.20 / $124.20 / $135.00), si los dos pedidos de Aurora son un cobro duplicado,
y dónde se marcan las facturas emitidas.

**Lo que me faltó desde mi usuario y para qué lo necesitaba:** un reporte de caja por mes y por
sucursal (para cuadrar contra el banco), el desglose de cada pedido en producto/envío/descuento (para
declarar bien el ingreso), y una lista de facturas por emitir (para no perseguirlas pedido por pedido).
No pido más permisos: pido que esas tres cosas existan.

## Cómo me sentí

Mal, la verdad. Es mi primer cierre y voy a entregarlo con tres huecos. Lo peor no fue que faltaran
pantallas: fue que **cada vez que dos partes del sistema hablan del mismo dinero, dicen cosas distintas**
— $10,088 contra $0, $135 contra $0.00 listas, "Activas 0" contra tres avisos activos, $135 contra
$259.20, $760 de venta contra $500 de corte. Un sistema de dinero que se contradice a sí mismo no me da
confianza aunque esté bien escrito y se vea limpio, que lo está. Se nota que lo pensó quien despacha
pedidos, no quien los cobra.
