# 09 · Auditoría UX/UI del frontend y rediseño luxury-wellness

**Fecha:** 2026-09-01
**Alcance:** validación visual de todas las páginas públicas (landing, tienda, login, carrito, raíz/dashboard invitado) en escritorio (1440×900) y móvil (390×844), análisis de UX/usabilidad/diseño, y rediseño de la capa pública (tienda + landing) hacia un lenguaje de lujo sereno orientado a salud, bienestar y crecimiento personal, sin perder la gamificación.

**Método:** servidor de desarrollo con API simulada + capturas headless (Playwright/Chromium) de cada página antes y después, inspección multimodal de cada captura, build de producción como verificación final.

---

## 1. Hallazgos de la auditoría (estado previo)

| # | Hallazgo | Severidad | Estado |
|---|----------|-----------|--------|
| 1 | Las cabeceras declaraban `"Libre Baskerville", "Playfair Display"` pero **ninguna fuente se cargaba** en `index.html`: en producción todos los títulos caían a Georgia y el cuerpo a la fuente del sistema. | Alta | Corregido |
| 2 | `index.html` tenía **head duplicado**: dos `<base href>`, favicon duplicado, viewport declarado al final del head. | Media | Corregido |
| 3 | El botón "Entendido y acepto" del aviso de privacidad era **texto blanco sobre dorado claro**: contraste insuficiente en el primer contacto con el sitio. | Alta | Corregido |
| 4 | Iconografía de secciones clave con **emojis** (🌱🤝📈 en Visión, ⚡ en bonos, círculos de color plano en rangos): rompía el tono sofisticado. | Media | Corregido |
| 5 | La sección **"Por qué elegir …"** de la tienda renderizaba un único chip huérfano alineado a la izquierda en una rejilla de 3 columnas (tags vacíos o únicos). | Media | Corregido |
| 6 | **Login descentrado**: la tarjeta vivía en la columna izquierda de una rejilla de 2 columnas con la derecha vacía. | Media | Corregido |
| 7 | La sección Visión **no tenía título de sección**; la landing móvil resultaba muy larga y monótona sin jerarquía entre bloques. | Media | Corregido |
| 8 | **Sin sistema de movimiento**: ninguna animación de entrada, transiciones genéricas de 200 ms lineales; la página se sentía estática, no "premium". | Media | Corregido |
| 9 | La clase `border-gold`/`bg-gold` se usaba en la tarjeta "Popular" **sin estar definida**: el borde caía a `currentColor` (oscuro). | Baja | Corregido |
| 10 | Font Awesome se carga desde CDN en runtime: si el CDN falla, los controles con solo icono (carrito, entrar) quedan **sin etiqueta visible**. | Media | Documentado (ver §4) |

## 2. Sistema de diseño aplicado

### Paleta (luxury wellness)
- **Oro refinado** `#c8a24a` (antes mostaza `#d3b350`): ancla de marca, gamificación y CTAs.
- **Verde bosque** `#1f3d31` + **salvia** `#7c8c72` (nuevos): salud, calma, acompañamiento. El texto base pasa a un carbón verdoso `#26312b`.
- Superficies crema existentes se conservan (compatibilidad con dashboard/admin/carrito).

### Tipografía
- **Fraunces** (serif display, optical sizing) para h1–h4; **Inter** para cuerpo. Ambas cargadas vía Google Fonts con `preconnect` y fallbacks reales (Libre Baskerville → Georgia; SF Pro → system-ui).

### Movimiento (beziers de tiempo)
Tokens en `:root`:
- `--ease-luxe: cubic-bezier(0.22, 1, 0.36, 1)` — entradas/reveals.
- `--ease-swift: cubic-bezier(0.4, 0, 0.2, 1)` — cambios de color/sombra.
- `--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)` — micro-interacciones (botones, orbes).
- Duraciones `200/400/700 ms`.

Piezas:
- Directiva standalone `revealOnScroll` (`src/app/directives/reveal-on-scroll.directive.ts`): IntersectionObserver fuera de NgZone, clase `.reveal → .is-visible`, retraso escalonable por tarjeta (`[revealDelay]`).
- `.card-lift` (elevación al hover), `.img-zoom` (zoom suave de producto), `.icon-orb` (rotación-escala spring), botones con lift/press.
- **`prefers-reduced-motion: reduce` desactiva todo** (contenido visible sin transiciones).

### Primitivas nuevas
`.eyebrow` (etiqueta de sección con filetes dorados), `.medallion` (medallón dorado para logros/rangos), `.icon-orb` (círculo salvia para conceptos de bienestar), `.bg-hero-luxe` (luces radiales oro/salvia), `.btn-forest` (CTA verde bosque con texto crema — contraste AA), `border-gold`/`bg-gold` ahora definidas.

## 3. Rediseño por página

- **Landing:** eyebrow "Salud · Bienestar · Crecimiento personal"; h1 serif con línea media en itálica verde bosque; imagen héroe con anillos concéntricos dorados y badge flotante "Bienestar que se comparte"; microcopy de acompañamiento bajo los CTAs ("Nunca caminas en solitario…"). Visión con título propio ("Un camino en tres pasos, nunca en solitario") y orbes con iconos FA en lugar de emojis. Plan de Recompensas y rangos con eyebrows narrativos ("Gamificación con propósito", "Tu viaje de rangos"), medallones dorados y reveals escalonados (120 ms por tarjeta). Registro con encabezado "Empieza acompañado".
- **Tienda:** héroe sobre `bg-hero-luxe` con acento en itálica verde; sección de beneficios ahora se oculta sin tags, filtra tags vacíos (getter `heroTags`) y centra los chips; catálogo con eyebrow, tarjetas con `card-lift` + `img-zoom` y stagger por columna; registro alineado con la landing. Barra de carrito fija intacta.
- **Aviso de privacidad:** medallón en cabecera, botón de aceptación `btn-forest` (verde bosque + texto crema + icono) con contraste correcto.
- **Login:** tarjeta centrada (max-w-md) sobre fondo héroe, sombra bosque, título como `h1` serif, CTA primario dorado.

## 4. Validación

- Capturas después del cambio: landing (desktop + móvil), tienda (desktop + móvil), login, carrito, raíz — layout correcto, sin errores JS propios (solo fallos de red esperados de los CDNs bloqueados por el proxy del sandbox).
- **Regresión:** carrito y dashboard raíz heredan los tokens nuevos (oro degradado, serif) sin romperse; los cambios de utilidades existentes fueron solo de valor, nunca de nombre.
- `ng build` (producción) exitoso; las dos advertencias de presupuesto (bundle inicial y CSS del networkgraph) son preexistentes.
- Nota de captura fullPage: los elementos `.reveal` bajo el fold no disparan IntersectionObserver durante capturas headless; el script de validación fuerza `.is-visible` antes de la captura (solo herramienta local, no comprometida).

### Deuda pendiente (no bloqueante)
1. **Font Awesome por CDN**: valorar empaquetarlo (npm `@fortawesome/fontawesome-free`) o migrar iconos críticos a SVG inline para eliminar la dependencia de runtime.
2. El bundle inicial (1.8 MB) excede el presupuesto desde antes; candidato a lazy-loading por ruta.
3. El emoji de rango (`rankIcon`) se conserva dentro del medallón dorado; si se quiere un acabado 100 % vectorial, sustituir por SVGs de medalla/diamante.
