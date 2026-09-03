# Diario — Sofía Herrera — 12 de diciembre de 2026 (tarde)

Se fue la luz a media mañana y me quedaron pendientes estas tareas. Retomo como a la 1 pm.

## 12:38 (hora del sistema) — Entrando de nuevo

Voy a `http://localhost:4321/#/login` y mi sesión guardada ya no valía — me pidió correo y contraseña otra vez. Entro con `sofia@findingu.mx` / `GXNBEP68WH`. Tras dar clic en "Ingresar al panel" caigo en `http://localhost:4321/#/admin` — nota para mí: si navego directo a `#/` (raíz) sin pasar por login, me manda a la vista de **cliente/socia** (Tienda, Red, Órdenes, Cuadro de Honor de mi propia cuenta), no al panel admin. El panel de administración vive en `#/admin`.

## Tarea 5 primero (rápida): Acciones urgentes

Doy clic en el botón "Acciones 1 urgentes" de la barra superior. Se abre un panel:

> **Acciones urgentes** — "Resolvé pendientes críticos desde aquí."
> **4 pedidos pagados sin envío** — etiqueta "Importante" — botón "Ir a resolver"

Solo hay una tarjeta. No aparece nada de comisiones pendientes, transferencias ni ventas POS del día (aunque en Configuración vi que esos SÍ son advertencias configurables — hoy simplemente no hay ninguna activa salvo la de envíos).

## Tarea 1: Producto nuevo — Magnesio Glicinato 120 caps

Entro a **Productos**. El catálogo tenía 12 productos activos + 1 retirado (Glu-10). Antes de dar de alta el producto necesito la categoría "Descanso", que no existe: solo veo "Proteínas" en la lista de categorías del formulario.

Bajo hasta "Árbol de categorías", doy clic en "Nueva raíz", aparece un campo "Nombre de categoría" con botones Agregar/Cancelar. Escribo "Descanso" y doy Agregar. Confirmación en pantalla: **"Categoría guardada: Descanso"**. Ya aparece como checkbox nuevo en "Categorías" del formulario de producto.

Genero con Node (no con ninguna herramienta de la app) un PNG real de 64×64 píxeles, morado sólido, 179 bytes — lo dejo en mi carpeta de scripts como `magnesio.png`. Es un archivo mío, de prueba, no una foto real del producto.

Lleno el formulario "Agregar / editar producto":
- Nombre: Magnesio Glicinato 120 caps
- Precio: 520
- Puntos VP por unidad: 10 (el campo dice "Puntos de Volumen Personal... Si se deja vacío se calculan automáticamente desde el precio", así que lo llené a mano con 10 como me pidieron)
- Categoría: marco la casilla "Descanso"
- Subo mi PNG a los 3 campos de imagen (Redes/Story-Feed, Landing/Hero 16:9, Miniatura 1:1) — los tres aceptaron el archivo sin queja
- Dejo los defaults: Producto activo, Tienda en línea, Punto de Venta y Comisionable, los cuatro checkbox venían marcados de fábrica

Doy "Guardar". Confirmación en pantalla: **"Producto creado: Magnesio Glicinato 120 caps."**

Verifico: el catálogo pasó de "12 productos" a **"13 productos"**, "Productos activos" pasó de 12 a **13**, "Assets faltantes" se quedó en **0** (antes y después), y en la lista aparece hasta arriba: **"Magnesio Glicinato 120 caps · $520 · Activo"**.

## Tarea 2: Producto del mes de diciembre

En esa misma fila del catálogo hay un botón (ícono de estrella) "Hacer producto del mes". Antes de tocarlo, el KPI de la pantalla decía "Producto del mes: Colageno Hidrolizado". Le doy clic sobre la fila de Magnesio Glicinato.

Confirmación en pantalla: **"Producto del mes actualizado: Magnesio Glicinato 120 caps."** El KPI "Producto del mes" ahora muestra: **"Magnesio Glicinato 120 caps"**.

## Tarea 3: Campaña "Navidad 2026"

Entro a **Campañas**. Solo había 1 campaña ("Mes del colágeno", octubre, activa). El formulario "Crear / editar campaña" pide, en este orden:

- **Nombre**
- **Tipo de campaña**: Multinivel / Tienda (producto) — un toggle, no checkbox
- **Hook corto**
- **Descripción**
- **Hero badge**
- **Campaña activa** (checkbox)
- **Hero título (línea 1)** / **Hero acento (línea 2)** / **Hero cola (línea 3)**
- **Hero descripción**
- **CTA primario** / **CTA secundario**
- **Beneficios** (hasta 4, separados por coma)
- **Asset Story (9:16)**, **Asset Feed (1:1)**, **Asset Banner (16:9)** — cada uno con botón "Cargar imagen"
- **Hero imagen (opcional)** — otro campo de imagen

**No existe ningún campo de fecha de inicio/fin de campaña.** El texto de abajo del botón Guardar avisa qué es obligatorio: "Faltan campos obligatorios: Nombre · Hook · Story (URL o archivo) · Feed (URL o archivo) · Banner (URL o archivo)" — o sea Nombre, Hook y las 3 imágenes son obligatorias; todo lo demás (hero, CTAs, beneficios, tipo) es opcional.

Como no hay campo de fechas, metí el rango "12 al 31 de diciembre" como texto dentro del Hook corto y del Hero badge, ya que no hay dónde más ponerlo:
- Nombre: Navidad 2026
- Hook corto: "12 al 31 de diciembre: envuelve tu bienestar esta Navidad"
- Hero badge: "Del 12 al 31 de diciembre"
- Hero título: Navidad / Hero acento: 2026 / Hero cola: Regala bienestar
- CTA primario: "Ver ofertas de Navidad"
- Subí mi mismo PNG de prueba a Story, Feed y Banner

Doy "Guardar campana". Confirmación en pantalla: **"Campana guardada: Navidad 2026."** La tarjeta nueva aparece en el catálogo de campañas: **"Navidad 2026 / 12 al 31 de diciembre: envuelve tu bienestar esta Navidad / Activa / Multinivel / Story OK · Feed OK · Banner OK"**. El contador "Campañas" pasó de 1 a **2**, "Activas" de 1 a **2**, "Assets completos" de 1 a **2**.

(El formulario, ya vacío para la siguiente campaña, vuelve a mostrar el aviso de campos obligatorios — no es un error de mi campaña, es el estado normal del formulario en blanco.)

## Tarea 4: Buscar "evaluar bonos/rangos" del mes

Recorrí todas las pantallas donde podría vivir esto:

- **Estadísticas**: pestañas Resumen, Pedidos, Clientes, Productos, Stocks. Nada de bonos ni rangos, solo ventas/ticket/clientes activos/productos vendidos y "Reporte completo Excel".
- **Configuración**: aquí SÍ está toda la definición de "Rangos de la Red" (BRONCE/PLATA/ORO/PLATINO/DIAMANTE con sus mínimos de PC, VG, líneas y bono mensual/anual) y "Reglas de Bonos" (Bono de Inicio Rápido, Bono Mensual por rango, etc.) — pero es pura configuración de las reglas, **no encontré ningún botón de "Evaluar" o "Calcular" o "Ejecutar" del mes**. Leí toda la pantalla de arriba a abajo.
- **Cuadro de Honor**: aquí se ve el resultado ya calculado — top 10 del mes 2026-12 con columna "RANGO". Los 10 primeros (Verónica con 91 VG hasta Patricia con 0) tienen **"—"** en la columna Rango: nadie calificó a ningún rango todavía. No hay botón de evaluar tampoco, el cálculo parece ser automático/en vivo.
- **Notificaciones** y **Clientes**: tampoco hay nada de bonos/rangos ahí (en Clientes solo veo comisiones mes actual/anterior por cliente individual, sin rango).

**Conclusión: no encontré ningún botón para "evaluar bonos" o "rangos" manualmente. El Cuadro de Honor ya muestra el resultado (parece calcularse solo) y hoy, 12 de diciembre, nadie califica a ningún rango — todos con "—".**

## Tarea 6: WhatsApp a Nadia

📱 A Nadia: Nadia, el código de autorización del POS ya quedó puesto: **7412**. Es para pagos parciales y retiros de efectivo en caja. Guárdalo.

## Mensajes que mandé

📱 A Sistemas: busqué en Estadísticas, Configuración, Cuadro de Honor, Notificaciones y Clientes algo como "Evaluar bonos" o "Evaluar rangos" del mes y no lo encontré en ningún lado — en Configuración solo están las reglas/definiciones de Rangos y Bonos, y en Cuadro de Honor se ve el resultado ya calculado (hoy todos con Rango "—"). ¿El cálculo de rangos/bonos corre solo (por ejemplo al cierre de mes) o hay una pantalla o botón que se me está pasando?

## Lo que no pude hacer

- No pude "evaluar bonos/rangos" con ningún botón porque no existe — solo pude confirmar, viendo Cuadro de Honor, que hoy nadie califica a ningún rango.
- No pude ponerle fecha de inicio/fin a la campaña "Navidad 2026": el formulario de Campañas no tiene ningún campo de fecha, así que metí el rango de fechas como texto en el Hook y el Hero badge.

## Lo que preguntaría

- ¿Dónde corre realmente el cálculo de rangos y bonos del mes? ¿Es automático o hay una pantalla que no vi? (ya mandé esta duda a Sistemas)
- ¿Las campañas de verdad no llevan fecha de vigencia en el sistema, o solo es un campo que falta en esta pantalla? Si no llevan fecha, ¿cómo se "apaga" sola una campaña como "Navidad 2026" el 1 de enero?
