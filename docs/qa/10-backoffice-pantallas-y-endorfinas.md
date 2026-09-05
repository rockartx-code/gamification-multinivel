# 10 · Tienda con endorfinas y back office pantalla por pantalla

**Fecha:** 2026-09-01
**Método:** sesiones sembradas (cliente con 15 % y admin superusuario) + API simulada; captura headless de la tienda en interacción (click en "Agregar a carrito") y de las 12 vistas del admin navegando el sidebar; inspección visual de cada una.

---

## 1. Tienda del cliente: capa de celebración

Objetivo: que cada interacción de compra dispare una recompensa sensorial inmediata, conservando la esencia (misma estructura, mismos datos).

**Lo nuevo:**

- **Celebración al agregar al carrito** (todas las rutas: héroe, tarjeta sin variantes, cantidad, botón "Agregar" de variantes):
  - Ráfaga de 6 partículas doradas ancladas al icono del carrito del header.
  - Rebote *spring* del icono (`cubic-bezier(0.34, 1.56, 0.64, 1)`).
  - **Toast de logro** (nuevo tipo `logro`): medallón dorado + "Agregado al carrito" + detalle que conecta la compra con la meta: `+N PC hacia tu meta` cuando el producto suma puntos; si no, `Tu 15 % de descuento aplicado`.
- **Progreso vivo global**: todas las barras `.progress-fill` ahora animan su ancho con `--ease-luxe` y llevan un brillo periódico que las hace sentir activas (aplica a meta del mes, meta de red y barra de la tienda pública).
- Los toasts de meta con emoji roto (`?? Meta alcanzada`) pasaron al formato de logro: "¡Meta alcanzada! · Lo lograste con tu constancia" y "¡Ya casi! · Estás a un paso de tu meta del mes".
- Todo respeta `prefers-reduced-motion` (partículas ocultas, sin rebotes, barras estáticas).

**Esencia conservada:** el modal épico de metas cumplidas, los medallones de rango/bonos y la estructura de secciones no cambian; la celebración se añade sobre los flujos existentes.

## 2. Back office: análisis de las 12 pantallas

Criterios: (a) ¿la estructura se entiende sola?, (b) ¿hay sobrecarga?, (c) ¿el usuario sabe qué sigue?

| Vista | Diagnóstico | Acción tomada |
|-------|-------------|---------------|
| **Pedidos** | Estructura clara; con las pestañas contadas y el flujo escrito (ronda 2) el proceso se entiende. Faltaba una respuesta global a "¿qué hago ahora?". | **Panel "Siguiente"** (ver §3). |
| **Punto de Venta** | Buena separación caja/venta/historial. El bloqueo "no tienes stock ligado" explicaba el problema pero no daba salida. | Botón **"Ir a Stocks"** dentro del aviso (visible solo con permiso). |
| **Stocks** | Tarjetas por proceso correctas. Encabezados de tabla colapsados ("Fecha Origen DestinoProductos…") cuando la tabla está vacía. | Documentado (bug estético compartido, ver §4). |
| **Clientes** | Maestro-detalle claro; "Comisiones por depositar" es trabajo pendiente visible. Encabezado "DescuentoMes anterior" colapsado. | Documentado; candidato a entrar en "Siguiente" (§4). |
| **Empleados** | Alta + privilegios por pantalla: claro y sin sobrecarga. | — |
| **Productos** | **Sobrecarga**: 4 botones apilados por fila convertían la tabla en columnas de botones; KPI "Assets faltantes" **hardcodeado en 2**. | Acciones de escritorio compactadas a iconos con tooltip/aria-label (las tarjetas móviles conservan etiquetas); KPI ahora computado (`productsMissingAssetsCount`: activos sin ninguna imagen). |
| **Campañas** | Catálogo + vista previa + editor en un flujo; el aviso de "faltan campos obligatorios" guía bien. | — |
| **Cupones** | **El título decía "Pedidos"** con el subtítulo del flujo de pedidos (casos faltantes en `viewTitle`/`viewSubtitle`). | Título "Cupones" + subtítulo propio. |
| **Estadísticas** | **Bug funcional**: NG0103 (detección de cambios infinita), spinner eterno y selector de periodo vacío. Estructura (KPIs + sub-pestañas + advertencias operativas) es buena. | Causa: getter `availableReportMonths` devolvía un array nuevo en cada ciclo → cacheado por referencia de `orders` (patrón ya usado en el archivo); selector inicializado con el mes activo; `requestViewUpdate()` en los callbacks de carga (OnPush no repintaba). Verificado: sin NG0103 y selector con "Septiembre de 2026". |
| **Cuadro de Honor** | Subtítulo equivocado (flujo de pedidos) y "Cargando…" sin repintado. | Subtítulo propio + `requestViewUpdate()` en la carga. |
| **Notificaciones** | Formulario + listado con vigencias: claro; el "Consejo" de uso es buena práctica. | — |
| **Configuración** | Tarjetas por dominio, bien. Jerga de desarrollador en labels: "Mapeo delivered_branch -> orden". | Renombrados a lenguaje operativo: "Al entregar en sucursal, la orden queda como" / "Al cobrar en sucursal, la orden queda como". |

## 3. "El usuario siempre debe saber qué sigue": panel **Siguiente**

Franja permanente bajo el título de toda vista del admin, computada de los datos reales (`nextActions`), en el orden del flujo del pedido:

`Confirmar pagos (N) → Preparar envíos (N) → Confirmar entregas (N) → Recibir devoluciones (N) → Resolver devoluciones validadas (N)`

- Cada chip navega a Pedidos con el filtro de estado correcto (`runNextAction`); el primero se pinta dorado (la prioridad).
- Sin trabajo pendiente muestra **"Operación al día"** en verde — el estado vacío también informa.
- Máximo 4 chips para no convertirse en otra fuente de sobrecarga.

## 4. Pendientes documentados (no bloqueantes)

1. **Encabezados de tabla colapsados** en Stocks ("Fecha Origen Destino…") y Clientes ("DescuentoMes anterior"): los grids de encabezado necesitan `gap` o anchos mínimos; corregir el patrón compartido en una pasada.
2. Extender `nextActions` más allá de pedidos: "Depositar comisiones ($X)" (dato ya visible en Clientes) y "Completar assets de productos (N)".
3. El nombre de producto mock "COL?GENO" tiene mojibake en los datos simulados (no es UI).
4. `docs/qa/09` §deuda sigue vigente (CDN de iconos, lazy-loading, orquestación de modales del dashboard).
