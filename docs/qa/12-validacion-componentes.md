# 12 · Validación de la librería de componentes (funcional + estética)

**Fecha:** 2026-09-01
**Método:** lectura del código de los 16 componentes `ui-*` + **galería interna** nueva en `/#/galeria` (styleguide vivo, ruta lazy sin enlaces de navegación) que renderiza cada componente en todos sus estados; capturas desktop/móvil y del estado modal.

## Veredicto por componente

| Componente | Funcional | Estético | Hallazgos y acciones |
|------------|-----------|----------|----------------------|
| **ui-button** | ✓ | ✓ | 4 variantes × 3 tamaños, disabled, fullWidth, stacked; micro-interacciones spring correctas. Nota: `sanitizeClasses` filtra clases legacy del host — comportamiento intencional documentado. |
| **ui-form-field** | ⚠→✓ | ✓ | **El estado de error era invisible**: usaba clases inexistentes (`border-danger/70`, `focus:border-danger`) → el borde nunca se pintaba, solo el texto pequeño. Nueva clase real `.input-error` (borde + ring de foco rojos). CVA, toggle de contraseña con `aria-label`, label implícito correcto. |
| **login (campo manual)** | ⚠→✓ | — | Usaba las mismas clases muertas `border-danger`/`focus-border-danger`; ahora existen en styles.css. |
| **ui-badge** | ✓ | ✓ | Añadido tono `danger` (faltaba un tono negativo en todo el sistema). |
| **ui-status-badge** | ✗→✓ | ⚠→✓ | **Bug real**: `'inactiva'.includes('activa')` es verdadero → el estado de red "Inactiva" se mostraba como **"Activa"** (etiqueta, tono e icono). Reordenados los matches (inact primero). **Cobertura**: solo entendía 4 de los 9 estados de pedido; cancelada/reembolsada/devoluciones caían a texto crudo gris. Ahora: Cancelada y Dev. rechazada en tono peligro, En devolución en pendiente, Devuelta en entregado, con iconos propios; los `level-*` ya no pisan el tono peligro por especificidad. |
| **ui-modal** | ⚠→✓ | ✓ | Sin semántica ni teclado: añadidos `role="dialog"`, `aria-modal`, `ariaLabel` opcional y **cierre con Escape** (respetando `closeOnBackdrop`). Focus-trap queda como pendiente (abajo). |
| **ui-order-timeline** | ✓ | ✗→✓ | **Fuera de paleta**: esmeralda y azul cielo en un sistema oro/bosque. Ahora: completado en bosque suave, paso actual en oro. |
| **ui-data-table / ui-table** | ✓ | ⚠→✓ | Divisores por defecto `divide-white/10`: invisibles en tema claro. Default cambiado a `divide-olive-20`. Patrón mobileRow/desktopRow correcto. |
| **ui-goal-progress** | ✓ | ✓ | Clamp correcto (incluye target=0 y no-finito); el segmento de carrito nunca desborda el 100 %. |
| **ui-kpi-card** | ✓ | ✓ | Slot `kpi-label-extra` útil (tooltip de bloqueadas lo usa). |
| **ui-product-card** | ✓ | ✓ | Tres modos verificados en galería: sin variantes (Qty+CTA), con variantes (mixto: seleccionada con steppers, resto con "Agregar" de un tap), compacto. PC oficiales vs netos correcto. |
| **ui-sidebar-nav** | ✓ | ✓ | Soporta encabezados de grupo no clicables (`heading`). |
| **feature-badge / chips / callout** | ✓ | ✓ | Coherentes con el sistema. |
| **medallion / icon-orb / eyebrow / toast-logro** | ✓ | ✓ | Primitivas de gamificación renderizando de forma consistente. |
| **privacy-notice** | ✓ | ✓ | Verificado de nuevo al aparecer sobre la galería: CTA bosque con contraste correcto. |
| **ui-networkgraph** | — | — | Fuera del alcance de esta pasada (SVG especializado); sin cambios. |

## Galería interna (`/#/galeria`)

Nueva página de validación permanente: fundamentos (paleta con hex + escala tipográfica), botones (todas las combinaciones), campos (normal/error/icono/contraseña/select/textarea), las 9+3 insignias de estado, primitivas de gamificación (medallones, orbes, toast de logro, metas parcial y cumplida), KPIs, tres tarjetas de producto, dos líneas de tiempo, navegación agrupada y modal funcional. Sirve como contrato visual: cualquier regresión de estilo se ve aquí primero.

## Pendientes

1. **Focus-trap y retorno de foco en ui-modal** (hoy Escape + backdrop; el foco puede escapar con Tab).
2. `ui-networkgraph`: auditoría propia (tipografía interna del SVG y colores aún pre-sistema).
3. Los `level-*` de insignias siguen siendo cinco variaciones de oro/gris; si se quiere distinción más fuerte entre "Pagada" y "Enviada", introducir un tono informativo adicional.
