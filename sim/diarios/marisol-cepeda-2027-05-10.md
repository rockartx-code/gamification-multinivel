# Marisol Cepeda — lunes 10 de mayo de 2027

Gerente de operaciones. Entro con el usuario de Renata Bustos, que es el que me dieron.
Escritorio, pantalla grande. Día 10: día de pago.

---

## 9:00 — Entrar

Abro `localhost:4321` y lo primero que veo es la tienda: "Regístrate para obtener beneficios",
"Crea tu cuenta para desbloquear descuentos y seguimiento de tu red". Nada de administración.
Cierro el aviso de privacidad con "Entendido", le doy a **"Iniciar sesión"** y ahí sí:
"LOGIN — Accede a tu panel". Pongo mi correo y mi contraseña y entro de un jalón.

Caigo en **Pedidos**. El menú de la izquierda está bien puesto y agrupado:
OPERACIÓN DIARIA, PERSONAS, **FINANZAS → Comisiones y pagos**, CATÁLOGO Y OFERTA,
REPORTES Y AVISOS, SISTEMA. En la esquina, "Acciones — 2 urgentes". Y una tarjeta lateral
que me gusta mucho: "Pedidos cargados · **$5,676** cobrado · 12 pedidos · **+ $2,916 por cobrar** ·
Pendientes: 4 · Pagados: 2 · Pendientes envío: 2".

Eso sí: en la lista, en la columna Cliente, los cuatro pendientes dicen **"Cliente"**. Sin nombre.

*Fácil: 7. Confianza: 5.*

---

## 9:03 — "Comisiones y pagos" (que se llama "Clientes")

Le doy al único renglón del menú que dice FINANZAS. La pantalla que abre se titula
**"Clientes — Niveles, estructura y comisiones"**, y de una vez me abre la ficha completa de
**Gerardo Lomelí Cantú**: su correo, su teléfono, "No contactar", "Origen", "Bitácora de contactos",
"Documentos del cliente", "Dar de baja sus datos (ARCO)", "Cambiar patrocinador",
"Acceso al back office… 0 de 30 permisos". Yo no vine a ver a Gerardo. Vine a pagar.

Bajo, bajo, bajo. Hasta el fondo está lo mío:

> **Pagos del mes · comisiones por depositar**
> Quién cobra cuánto, con su CLABE. Exporta el archivo para el banco, sube un comprobante por lote
> y marca pagadas en bloque.
> Mes de las comisiones: **abril 2027**. *Se paga el mes anterior el día 10. Solo se listan los meses con comisiones.*
> **Comisión reconocida de abril 2027: $0.00**
> $0.00 confirmadas · $0.00 por confirmar · $0.00 bloqueadas.
> **Nadie tiene comisiones en abril 2027: ni confirmadas, ni por confirmar, ni bloqueadas.**

Y los tres botones que necesitaría, apagados, cada uno con su razón escrita —eso me gustó,
no me dejaron adivinando—: "Exportar archivo de dispersión (CSV) — *No hay socias listas para
depositar este mes*", "Descargar pendientes (0)", "Registrar pago por lote — *Marca las filas que
vas a pagar*".

Me quedo con una espina: el selector dice **"Solo se listan los meses con comisiones"** y el único
mes que ofrece es abril… en $0.00. ¿Entonces abril tiene comisiones o no?

**No hay a quién pagarle.** Bueno. Pero antes de decírselo al patrón necesito estar segura.

*Fácil: 4. Confianza: 4.* (La frase final es clarísima. Llegar a ella me costó bajar la ficha
completa de una persona que no me interesaba.)

---

## 9:08 — "Conciliar pagos": la parte que me quitó el sueño

Regreso a Pedidos y le doy a **"Conciliar pagos"**. La ventana explica bonito:

> **Conciliar pagos con MercadoPago.** Para cuando alguien ya pagó y su pedido sigue en "Pendiente".
> Se consultará a MercadoPago por los pedidos pendientes de pago… y se acreditarán los aprobados;
> los ya pagados no se tocan.

Viene en "Últimas 72 horas". Mis pendientes son del **04/05/2027, "5 días"** de antigüedad: con 72
horas no alcanza. Le muevo a **"Últimos 7 días"** y le doy a "Revisar pagos ahora":

> **Resultado: Revisados 0 · Acreditados 0 · Sin pago 0**
> No hay pedidos pendientes de pago en el periodo que elegiste (últimos 7 días): no había nada que
> revisar. **Prueba con un periodo más largo.**

Y atrás de la ventana, en la misma pantalla, los cuatro pedidos ahí: ORD-A4CCC53F, ORD-B2E4A95F,
ORD-BD349B9F, ORD-D8B1CD8B. **Pendiente De Pago. 04/05/2027. 5 días.**

Le hago caso y pruebo **30 días**: lo mismo. **90 días (lo máximo)**: lo mismo, y me vuelve a decir
*"Prueba con un periodo más largo"* estando yo en el más largo que existe.

Ahí sentí feo. No es que me diga "no hay pagos perdidos": es que **no está viendo**. Y a mí me
toca firmarle al dueño que no hay pagos sin registrar.

Abro una ficha a mano, la de ORD-A4CCC53F: "Gel x3 · $1,200", "Envío $129", "Subtotal sin IVA
$1,230.56", "IVA 8 % $98.44", "Total $1,329.00", "Sin dirección de envío registrada", "Notas internas".
**Ni el nombre del cliente, ni su teléfono, ni una referencia de pago.** Aunque abriera las cuatro
fichas una por una —justo lo que quería evitar— no sabría si esa gente ya pagó.

*Abandonada. Fácil: 2. Confianza: 1.*

---

## 9:20 — El clic que no debí dar (y que doy a propósito)

Quería saber si el sistema me pregunta antes de mover dinero. Escojo el pedido más chico,
ORD-BD349B9F, **$129**, y le doy a **"Marcar como pagado"** esperando el clásico "¿Estás seguro?"
para cancelarlo.

No hubo nada. Ni ventana, ni pregunta, ni un campo para la referencia del depósito, ni la fecha,
ni quién lo cobró. El pedido brincó a **Pagado** y la tarjeta de arriba pasó de **$5,676 a $5,805
cobrado**, "Pendientes: 3 · Pagados: 3". Hasta abajo, debajo del pie de página, un rengloncito:

> Pedido ORD-BD349B9F de **Cliente**: el servidor lo dejó Pagado.

"El servidor lo dejó Pagado". Así, como si el servidor fuera el responsable y no yo.

Me voy a la pestaña **Pagado** a buscar cómo regresarlo. Las únicas acciones son **"Registrar envío"**
y **"Cancelar pedido"**. **No hay deshacer.** Recargo para comprobar que no fue un espejismo:
sigue Pagado. (Y ahora ese pedido dice "**6 días**" de antigüedad mientras sus vecinos, de la misma
fecha 04/05/2027, siguen diciendo "5 días".)

Un clic movió dinero, no me pidió comprobante y no me deja regresarlo. En cambio, para borrar los
datos de un cliente sí hay una explicación de tres renglones. Está al revés.

*Abandonada. Fácil: 1. Confianza: 2.* Y sí, sentí susto.

---

## 9:30 — Cómo cerró el mes (armado a mano)

Voy a **Estadísticas** creyendo que ahí está el cierre. Sale: "Ventas del periodo **$9,921** · 12
pedidos", "Ticket promedio $826.75", "Clientes activos 1", "Productos vendidos 32". Dos problemas:

1. El selector de "Periodo analizado" **solo tiene "Mayo de 2027"**. Abril, el mes que tengo que
   reportar hoy, no se puede elegir.
2. Los $9,921 no cuadran con los $5,805 + $2,787 del tablero. Y "Pedidos por estado" lista
   "Entregado 4 — **$0**", "Pendiente de pago 4 — **$0**", "Pagado 2 — **$0**": la columna del dinero
   viene en ceros en todos los renglones.

En "Top clientes del periodo" cuatro de los diez son "**Cliente**" y uno, Aurora Vega, aparece con $0.

Bajo el Excel de abril desde el botón **"Exportar abril de 2027"** (`comisiones-2027-04.xlsx`).
La primera hoja está vacía, solo encabezados. La segunda trae una línea:

> Paulina Ríos | paulina.rios@gmail.com | 012345678901236789 | 0 | Sin movimientos |
> Gerardo Lomelí Cantú | **L1** | 0 | **0** | 0 | 0 | **Nivel no configurado**

"Nivel no configurado". Me voy a **Configuración** y ahí están los **"Niveles de comision"**:
"Generación 1 — Comisión (%) **10**", luego 5, 4, 3 y 2, con la regla de corte en "Compresión
dinámica (Plan abril 2026)". O sea que **sí están configurados** y el reporte dice que no.

Al final abro las cinco pestañas de pedidos una por una y me cae el veinte: **todos los pedidos son
del 4 y del 5 de mayo**. En abril no hubo una sola venta. El cero de abril es de verdad. Pero para
saberlo tuve que leer fecha por fecha, que es justo lo que no quería hacer.

*Fácil: 3. Confianza: 3.*

---

## 9:40 — Lo que le mandé al patrón

Le escribí por WhatsApp: que abril cerró en ceros y es real porque no hubo ventas; que **no le puedo
firmar** que no haya pagos sin registrar porque la conciliación no ve nada; que **yo misma** moví
$129 con un clic y se lo reporto para que quede asentado, porque el sistema no me dejó asentarlo ni
deshacerlo; cómo quedó la operación (12 pedidos, $5,805 cobrado, $2,787 por cobrar, 3 pendientes,
3 pagados sin enviar —el más viejo de 6 días—, 4 entregados, 1 cancelado, 1 devolución en curso);
y lo de la caja.

Porque además, en mi correo, el único mensaje que tengo es el comprobante del corte
**CUT-2B3D81B9** del 5 de mayo: "Diferencia: **$40.00** · Motivo: *Sobran $40 y no sé de dónde
salieron. Es mi tercer día y estuve cobrando con el usuario de la gerente porque el mío no abre la
caja*". Encabezado con "Sucursal: **STK-46603B** · Operador: **1809421204348**". Claves y números
internos en un comprobante que sirve de respaldo de dinero. Yo no sé de memoria cuál sucursal es
STK-46603B.

---

## Lo que reportaría, en orden

1. **"Conciliar pagos" no ve los pedidos pendientes** en ningún periodo, ni en los 90 días que son
   su máximo, y remata sugiriendo "un periodo más largo" que no existe. Es la única herramienta que
   contesta "¿falta algún pago?" y contesta que no revisó nada.
2. **"Marcar como pagado" mueve dinero de un clic**: sin confirmación, sin referencia, sin fecha,
   sin monto y sin deshacer. El aviso llega abajo del pie de página y dice "el servidor lo dejó Pagado".
3. **El reporte de comisiones dice "Nivel no configurado"** con los cinco niveles capturados en
   Configuración (10 %, 5 %, 4 %, 3 %, 2 %).
4. **Estadísticas no deja elegir abril** el día que hay que reportar abril; y sus totales
   ($9,921) no cuadran con el tablero ($5,805 + $2,787), con la columna de dinero por estado en $0.
5. **"Comisiones y pagos" abre en "Clientes"** con la ficha de una persona desplegada; los pagos del
   mes están hasta el fondo. El nombre del menú y el título de la pantalla no coinciden.
6. **La columna "Cliente" viene vacía** ("Cliente") en la mayoría de los pedidos y en el Top de
   Estadísticas: no hay a quién cobrarle ni a quién llamarle.
7. **"Antigüedad" no es confiable**: dos pedidos del mismo 04/05/2027 marcan 5 y 6 días.
8. Detalles de redacción en pantallas de gerencia: "**Guardar configuracion**", "**Nuevo codigo**",
   "**Niveles de comision**", "Pedidos pagados sin **envio**", "Tope **automatico**", "Monto **minimo**".
   Y en Configuración, decenas de casillas numéricas sin etiqueta que se lea sola (VP, VG, PC).

## Lo que sí está bien y quiero que quede escrito

- Cada botón apagado dice **por qué** está apagado. Eso vale oro.
- La frase "**Nadie tiene comisiones en abril 2027: ni confirmadas, ni por confirmar, ni bloqueadas**"
  es exactamente lo que uno necesita leer el día 10.
- "Se paga el mes anterior el día 10" y la explicación de sobre qué se calcula la comisión
  ("el neto que pagó tu referida… sin contar el envío") están donde deben estar.
- El Excel de abril salió al primer clic, con nombre correcto y con una hoja de detalle que explica
  por qué no se pagó cada peso. Si el motivo fuera cierto, sería un reporte ejemplar.
