# Catálogo de Componentes UI (`ui-*`)

Referencia breve de la capa presentacional en `src/app/components/ui-*`.

## Convenciones

- Los componentes `ui-*` son `standalone` y deben mantenerse livianos en lógica de dominio.
- La composición vive en `pages` o contenedores; `ui-*` resuelve presentación, inputs y eventos.
- Priorizar clases globales de `src/styles.css` y props de clase (`extraClass`, `containerClass`, `panelClass`, etc.) antes de crear variantes nuevas.
- Este catálogo resume la API; la fuente de verdad para defaults finos sigue siendo cada archivo `.ts`.

## Componentes base

### `ui-badge`

- Archivo: `src/app/components/ui-badge/ui-badge.component.ts`
- Uso: píldora simple.
- API: `tone`, `size`, `extraClass`.

### `ui-status-badge`

- Archivo: `src/app/components/ui-status-badge/ui-status-badge.component.ts`
- Uso: badge derivado desde `status` de negocio.
- API: `status`, `context`, `showIcon`.
- Nota: usa `ui-badge` y aplica una sola clase de representación por vez.

### `ui-button`

- Archivo: `src/app/components/ui-button/ui-button.component.ts`
- Uso: botón reusable.
- API principal: `type`, `variant`, `size`, `disabled`, `fullWidth`, `iconClass`, `extraClass`, `routerLink`, `stacked`, `title`, `subtitle`, `class`.
- Evento: `pressed`.
- Slots: contenido libre o pares `btnTitle`/`btnSubtitle` cuando `stacked=true`.

### `ui-form-field`

- Archivo: `src/app/components/ui-form-field/ui-form-field.component.ts`
- Uso: campo genérico con CVA.
- API principal: `kind`, `type`, `label`, `placeholder`, `name`, `helpText`, `errorText`, `rows`, `readonly`, `min`, `max`, `step`, `accept`, `iconClass`, `leadingIconClass`, `options`, `wrapperClass`, `inputClass`.

### `ui-modal`

- Archivo: `src/app/components/ui-modal/ui-modal.component.ts`
- Uso: shell modal reusable.
- API: `isOpen`, `maxWidthClass`, `contentClass`, `containerClass`, `panelClass`, `closeOnBackdrop`.
- Evento: `closed`.

## Shell y navegación

### `ui-header`

- Archivo: `src/app/components/ui-header/ui-header.component.ts`
- Uso: header por contexto.
- API: `variant`, `containerClass`.
- Slots: `[header-left]` y contenido principal.

### `ui-footer`

- Archivo: `src/app/components/ui-footer/ui-footer.component.ts`
- Uso: footer institucional.
- API: `logoMode`, `containerClass`.

### `ui-sidebar-nav`

- Archivo: `src/app/components/ui-sidebar-nav/ui-sidebar-nav.component.ts`
- Uso: navegación lateral por links.
- API: `links`, `activeId`, `compact`.
- Evento: `linkSelect`.

## Datos y visualización

### `ui-kpi-card`

- Archivo: `src/app/components/ui-kpi-card/ui-kpi-card.component.ts`
- Uso: KPI simple.
- API: `label`, `value`, `iconClass`.
- Slot: `[kpi-label-extra]`.

### `ui-goal-progress`

- Archivo: `src/app/components/ui-goal-progress/ui-goal-progress.component.ts`
- Uso: progreso contra meta con capa base y carrito.
- API: `title`, `subtitle`, `currentValue`, `cartValue`, `targetValue`.
- Slot: contenido libre bajo la barra.

### `ui-table`

- Archivo: `src/app/components/ui-table/ui-table.component.ts`
- Uso: contenedor visual de tabla/listado.
- API: `title`, `subtitle`, `iconClass`.
- Slot: contenido libre.

### `ui-data-table`

- Archivo: `src/app/components/ui-data-table/ui-data-table.component.ts`
- Uso: tabla responsive por templates.
- API: `rows`, `mobileDividerClass`, `desktopDividerClass`.
- Templates: `#mobileRow`, `#desktopHeader` opcional, `#desktopRow`.

### `ui-order-timeline`

- Archivo: `src/app/components/ui-order-timeline/ui-order-timeline.component.ts`
- Uso: timeline de estado de orden.
- API: `status`, `steps`.

### `ui-networkgraph`

- Archivo: `src/app/components/ui-networkgraph/ui-networkgraph.component.ts`
- Uso: red jerárquica SVG interactiva.
- API principal: `nodes`, `links`, `viewBoxWidth`, `viewBoxHeight`, `heightPx`, `linkStyle`, `labelMode`, `interactive`, `selectedNodeId`, `showLegend`, `emptyStateText`, `spendMax`, `showSpend`, `showStatusDot`, `portraitTree`, `portraitBreakpoint`.
- Eventos: `nodeClick`, `nodeHover`.

## Comercio y contenido

### `ui-product-card`

- Archivo: `src/app/components/ui-product-card/ui-product-card.component.ts`
- Uso: card de producto en modo detallado o compacto.
- API: `product`, `discountedPriceLabel`, `originalPriceLabel`, `discountLabel`, `qty`, `mode`.
- Eventos: `qtyChange`, `viewDetails`, `add`.

## Reglas transversales

- Mantener `ui-*` sin lógica de dominio pesada.
- Reusar extensiones por clase antes de sumar nuevas variantes.
- Para estados visuales, apoyar la implementación en `styles.css` (`badge`, `btn-*`, `surface-soft`, `text-*`, `ring-*`).
- Si cambia la API pública de un componente, actualizar este archivo.
