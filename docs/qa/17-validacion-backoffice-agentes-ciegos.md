# 17 · Validación del back office con agentes a ciegas

Doce agentes, uno por sección, **sin instrucciones de uso**: cada uno recibió
solo una meta de negocio ("Ana López dice que ya pagó, déjalo registrado"),
prohibición explícita de leer el código, y un límite de 25 acciones. Lo que se
midió no es si el back office funciona, sino si **se explica solo**.

Perfil usado: `admin / admin123` del mock, con los 30 privilegios y acceso a
las 12 secciones.

---

## 1. Aviso metodológico: qué NO cuenta como hallazgo

Para poblar el back office se activó `useMockApi: true`. El mock guarda el
estado en un servicio de Angular del navegador, así que **al recargar la página
se reinicia**. Ocho de los doce agentes reportaron, con razón desde su punto de
vista, que "el sistema dice «guardado» y al recargar no queda nada" y que
"al guardar no sale ninguna petición de red".

**Eso es el banco de pruebas, no el producto.** Se verificó en el código que
los mensajes de éxito solo se emiten en la rama `next:` de la suscripción y que
existe una rama `error:` con su mensaje ("No se pudo guardar la notificacion.").
Con la API real, un guardado fallido sí avisa.

Se descartaron por el mismo motivo:

- "`Guardar` de Notificaciones está habilitado con el formulario vacío" —
  comprobado en vivo: está **deshabilitado** (`[disabled]="… || !isNotificationFormValid"`).
- "La papelera de Cupones no hace nada" — sí llama a `confirm()`; Playwright
  descarta los diálogos por defecto.
- "El ranking «Por VP» ordena mal" — el desorden estaba en el *fixture*. Pero
  destapó un defecto real: la tabla no ordenaba, se fiaba del orden de llegada.

El resto del informe solo recoge hallazgos verificados contra el código o
reproducidos en el navegador.

---

## 2. El hallazgo principal

**«Nuevo pedido» no cargaba sus propias dependencias.**

`openNewOrderModal()` reseteaba el formulario y abría el modal. Los clientes y
los productos solo se cargaban al **entrar** en las secciones Clientes y
Productos (`loadViewData`). Como la pantalla de inicio del back office es
Pedidos, en una sesión recién abierta el modal salía con el desplegable de
clientes **vacío** y la caja de productos **en blanco**, con "Guardar pedido"
en gris y sin ninguna explicación.

El agente de Punto de Venta lo descubrió por casualidad: *"si visito Clientes
antes de abrir el modal, los clientes aparecen"*. Nadie puede deducir eso.

Corregido: el modal carga ambas listas al abrirse (`forkJoin`), y si falla lo
dice dentro del propio modal en vez de quedarse mudo.

## 3. Riesgo de actuar sobre el registro equivocado

Dos agentes independientes cayeron en la misma trampa.

Los paneles de detalle de **Clientes** y **Empleados** arrancan precargados con
el primer registro de la lista (`this.customers[0]`, `this.employees[0]`) y la
tabla **no marcaba de ninguna forma** cuál estaba abierto (cero coincidencias
de resalte por selección en toda la plantilla).

- En Clientes, el agente trabajó sobre la ficha de Ana López creyendo que era
  la de Carlos Ruiz. En una pantalla con un botón "Pagar comisiones", eso es un
  pago al cliente equivocado esperando a ocurrir.
- En Empleados el panel se titulaba solo "Acceso y privilegios", sin nombrar a
  la persona, y aparecía con las 30 casillas marcadas (las del superusuario).
  El agente: *"Si llego a tocar algo ahí, le habría cambiado los permisos al
  administrador sin darme cuenta."*

Corregido: la fila abierta se resalta con fondo y una barra dorada a la
izquierda, su botón pasa a "Viendo", y la cabecera del panel de permisos dice
**"Permisos de {nombre}"** con el recuento de permisos concedidos.

## 4. Los permisos eran 30 adivinanzas

Un agente tenía que dar a María Torres acceso solo a pedidos y a marcarlos
enviados. La lista eran 30 casillas con **etiqueta y nada más**: sin
descripción, sin agrupación, dentro de una caja de 256px que mostraba 7 filas,
con el botón de guardar pegado al borde inferior. Se verificó
mecánicamente que ese botón **tapa la casilla "Cambiar orden a Pagado"** y se
come el clic.

Además:
- Las etiquetas decían "orden" cuando toda la app dice "pedido".
- `Acceso a panel admin` y `Marcar usuario como administrador` no se
  distinguían. `Registrar privilegios` no decía que quien lo tenga puede
  concederse cualquier otro permiso.
- `Marcar stock como danado` (sin ñ), `Estadisticas`, `Configuracion`.
- Nada avisaba de que un permiso de acción sin su permiso de pantalla **no
  sirve para nada**: se concedía en silencio.

Corregido: las 30 opciones llevan descripción en lenguaje llano, van agrupadas
en seis bloques (Acceso a pantallas · Pedidos · Catálogo · Inventario ·
Personas y dinero · Sistema), sin caja con scroll, y se marca en rojo el
permiso que no tendrá efecto por faltarle su pantalla.

## 5. Etiquetas que decían otra cosa

| Dónde | Decía | Problema | Ahora |
|---|---|---|---|
| Panel lateral | "Estado del mes · $479" | Sumaba **todos** los pedidos cargados, de cualquier fecha, e incluía los pendientes de cobro | "Pedidos cargados · $359 cobrado · + $120 por cobrar" |
| Fila de pedido | "Cambiar estado" | Con 9 estados posibles, había que pulsar para saber a cuál iba | "Marcar como pagado" / "Registrar envío" / "Marcar como entregado" |
| Aviso al avanzar | "Orden actualizada." | No decía qué pedido ni a qué estado | "Pedido #1001 de Ana Lopez: ahora está Pagado." |
| Fila de cupón | papelera roja, `title="Desactivar"` | Icono de borrar para desactivar; seguía diciendo "Desactivar" en cupones ya inactivos; encender uno apagado no tenía botón | Botones con texto **Activar** / **Desactivar** según el estado, y el de activar avisa de cuántos usos quedan |
| Cliente | "Estructura simulada." / "Mock. En producción: pintar con datos reales." | Texto de andamiaje visible en el back office | Descripciones reales |

## 6. Cuadro de Honor

Meta: "quién va 1º, quién 2º, y cuánto le falta al segundo". El agente
respondió lo primero en dos clics y **tuvo que restar a mano** lo tercero.

- La tabla no ordenaba por la columna que anunciaba: pintaba el orden de
  llegada del servidor.
- La columna `#` venía del servidor, así que en "Alfabético" salía 4, 6, 7, 9…
- `VG`, `VP` y `Δ` no tenían leyenda en ninguna parte.

Corregido: ordena en cliente por la columna activa; el `#` refleja el orden
real de la tabla; nueva columna **Falta** con la diferencia respecto a quien
está arriba; y un pie que explica las cuatro columnas.

## 7. Texto roto invisible

Ocho caracteres `U+00AD` (guion blando) incrustados dentro de palabras
españolas en `admin.component.html`: `enví­o`, `crí­ticos`, `Lí­der`. No se ven
en el editor pero parten la palabra al renderizar. Eliminados.
También `COL?GENO` en el fixture del mock, visible en cuatro pantallas.

## 8. Notas de intuitividad por sección

| Sección | Meta | Resultado | Nota |
|---|---|---|---|
| Pedidos | Marcar pagado | Alcanzada en 1 acción | 3/5 |
| Cupones | Reactivar con límite | A medias | 3/5 |
| Stocks | Registrar 50 unidades | Alcanzada en 13 (mínimo 5) | 2/5 |
| Empleados | Alta con permisos mínimos | A medias | 2/5 |
| Productos | Subir precio + destacar | A medias | 2/5 |
| Clientes | Pagar comisiones | **No alcanzada** | 2/5 |
| Campañas | Montar un 2x1 | **No alcanzada** | 2/5 |
| Notificaciones | Avisar a los clientes | A medias | 2/5 |
| Estadísticas | Tres cifras para la junta | **No alcanzada** | 2/5 |
| Cuadro de Honor | 1º, 2º y diferencia | Alcanzada calculando a mano | 2/5 |
| Configuración | Bajar comisión al 8% | Campo encontrado | 1/5 |
| Punto de Venta | Cobrar en mostrador | **No alcanzada** | 1/5 |

## 9. Lo que queda: huecos de producto, no de pantalla

Cuatro metas fueron imposibles porque **la función no existe**, no porque no se
encontrara. Esto no se arregla moviendo botones:

1. **Cobrar en efectivo.** No hay ningún campo de forma de pago en el flujo de
   pedidos. La palabra "efectivo" solo aparece dentro del Punto de Venta.
   Tampoco hay importe entregado, cambio, ni ticket.
2. **Promociones por unidades.** El cupón solo admite "Porcentaje" o "Monto
   fijo", sobre el carrito entero: no hay selector de producto, así que un 2x1
   o un 3x2 es inexpresable. Y "Campañas", bajo un grupo llamado "CATÁLOGO Y
   OFERTA", no tiene ni fechas ni importes: es un editor de material gráfico.
3. **Pagar comisiones del mes en curso.** El botón "Pagar comisiones" solo
   aparece si el bloque "mes anterior" está "Pendiente de pago"; los $40 del
   mes actual de un cliente no son pagables por ningún camino. Y el botón
   **desaparece** en vez de deshabilitarse con un motivo, lo que obliga a
   comparar tres fichas para saber que no se puede.
4. **Comparar con el mes anterior.** Estadísticas no tiene ni una flecha, ni un
   porcentaje, ni un "mes anterior: $X". Una de las tres preguntas típicas de
   un jefe no tiene ningún elemento que la responda.

Y dos más, de arquitectura de la información:

- **Destinatarios de las notificaciones.** El formulario no tiene campo de
  público, ni previsualización, ni contador de alcance. Se publica a ciegas. La
  pantalla vecina de Campañas, mucho menos delicada, sí valida y sí previsualiza.
- **El destinatario cambia de nombre en cada pantalla**: "los usuarios"
  (Notificaciones), "Clientes" (menú), "la red" (Campañas). Un empleado nuevo
  no puede saber si son el mismo grupo.

## 10. Barrido mecánico complementario

Además de los agentes se pulsaron todos los controles visibles de las 12
secciones (~448 clics): **0 modales que no cierren con Escape**, **0 errores de
consola** provocados por un clic, y ningún control muerto real (los "sin efecto
visible" eran botones de navegación pulsados desde su propia sección).

## 11. Verificación

`ng build` correcto y sin avisos · `ng test` 2/2 ·
`python3 tools/auditoria_ui.py` sin categorías bloqueantes ·
correcciones comprobadas en navegador una por una.
