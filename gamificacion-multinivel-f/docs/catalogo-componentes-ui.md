# Catálogo de Componentes UI (`ui-*`)

Este documento resume la configuración y el uso de los componentes ubicados en `src/app/components/ui-*`.

## Convenciones generales

- Todos los componentes `ui-*` son `standalone`.
- La mayoría usa Tailwind utility classes + clases globales de `src/styles.css`.
- En componentes de presentación, el patrón principal es:
  - `@Input()` para configuración visual y de datos.
  - `@Output()` para eventos de interacción.
  - `ng-content` o `TemplateRef` para composición flexible.

---

## 1) `UiBadgeComponent`

- Archivo: `src/app/components/ui-badge/ui-badge.component.ts`
- Selector: `ui-badge`
- Propósito: renderizar una píldora (`<span class="badge ...">`) con tono y tamaño base.

### Inputs

- `tone: 'active' | 'inactive' | 'pending' | 'delivered'` (default: `'inactive'`)
- `size: 'default' | 'mini'` (default: `'default'`)
- `extraClass: string` (default: `''`) para variantes adicionales (`level-*`, `status-*`).

### Outputs

- Sin outputs.

### Uso recomendado

```html
<ui-badge tone="active" extraClass="level-2">Activo</ui-badge>
```

---

## 2) `UiStatusBadgeComponent`

- Archivo: `src/app/components/ui-status-badge/ui-status-badge.component.ts`
- Selector: `ui-status-badge`
- Propósito: mapear un `status` de negocio a un badge con ícono, tono y representación visual.

### Inputs

- `status: string`
- `context: 'order' | 'network'` (default: `'order'`)
- `showIcon: boolean` (default: `true`)

### Outputs

- Sin outputs.

### Notas de implementación

- Usa internamente `ui-badge`.
- Calcula una sola clase de representación a la vez (`representationClass`):
  - `level-*` o `status-*` según contexto/estado.

### Uso recomendado

```html
<ui-status-badge status="delivered" context="order"></ui-status-badge>
```

---

## 3) `UiButtonComponent`

- Archivo: `src/app/components/ui-button/ui-button.component.ts`
- Selector: `ui-button`
- Propósito: botón reusable con variantes, tamaños, ícono y evento unificado.

### Inputs

- `type: 'button' | 'submit' | 'reset'` (default: `'button'`)
- `variant: 'primary' | 'secondary' | 'ghost' | 'linkish'` (default: `'ghost'`)
- `size: 'sm' | 'md' | 'lg'` (default: `'md'`)
- `disabled: boolean` (default: `false`)
- `fullWidth: boolean` (default: `false`)
- `iconClass: string`
- `extraClass: string`
- `routerLink: string | unknown[] | null`
- `hostClass` via `@Input('class')`
- `stacked: boolean` (default: `false`)
- `title: string`
- `subtitle: string`

### Outputs

- `pressed: EventEmitter<MouseEvent>`

### Slots (`ng-content`)

- Normal: contenido libre del botón.
- `stacked=true`:
  - `<span btnTitle>...</span>`
  - `<span btnSubtitle>...</span>`

### Uso recomendado

```html
<ui-button variant="primary" size="lg" iconClass="fa-solid fa-lock" (pressed)="save()">
  Guardar
</ui-button>
```

Ejemplo stacked:

```html
<ui-button [stacked]="true" variant="ghost">
  <span btnTitle>Meta principal</span>
  <span btnSubtitle>Actualizado hace 5 min</span>
</ui-button>
```

---

## 4) `UiFormFieldComponent`

- Archivo: `src/app/components/ui-form-field/ui-form-field.component.ts`
- Selector: `ui-form-field`
- Propósito: campo de formulario genérico (`input`/`textarea`/`select`) con soporte CVA.

### Inputs

- `kind: 'input' | 'textarea' | 'select'` (default: `'input'`)
- `type: string` (default: `'text'`)
- `label`, `placeholder`, `name`, `helpText`, `errorText`
- `rows`, `readonly`, `min`, `max`, `step`, `accept`
- `iconClass`, `leadingIconClass`
- `options: { value: string | number; label: string }[]`
- `wrapperClass`, `inputClass`

### Outputs

- Sin outputs explícitos (usa `ControlValueAccessor`).

### Uso recomendado

```html
<ui-form-field
  label="Correo"
  type="email"
  name="email"
  [(ngModel)]="email"
  [errorText]="emailError ? 'Correo inválido' : ''"
></ui-form-field>
```

---

## 5) `UiModalComponent`

- Archivo: `src/app/components/ui-modal/ui-modal.component.ts`
- Selector: `ui-modal`
- Propósito: contenedor modal reusable con backdrop y cierre configurable.

### Inputs

- `isOpen: boolean`
- `maxWidthClass: string` (default: `max-w-lg`)
- `contentClass: string`
- `containerClass: string`
- `panelClass: string`
- `closeOnBackdrop: boolean` (default: `true`)

### Outputs

- `closed: EventEmitter<void>`

### Slots

- `ng-content` dentro del panel modal.

### Uso recomendado

```html
<ui-modal [isOpen]="open" (closed)="open = false">
  <h3 class="text-xl font-bold">Título</h3>
  <p>Contenido</p>
</ui-modal>
```

---

## 6) `UiHeaderComponent`

- Archivo: `src/app/components/ui-header/ui-header.component.ts`
- Selector: `ui-header`
- Propósito: header con variantes de contexto (`landing`, `dashboard`, `admin`).

### Inputs

- `variant: 'landing' | 'dashboard' | 'admin' | 'default'`
- `containerClass: string`

### Outputs

- Sin outputs.

### Slots

- `[header-left]`: bloque junto al logo.
- `ng-content` principal: acciones en la derecha.

### Uso recomendado

```html
<ui-header variant="dashboard">
  <div header-left class="text-sm font-semibold">Panel</div>
  <ui-button variant="ghost">Salir</ui-button>
</ui-header>
```

---

## 7) `UiFooterComponent`

- Archivo: `src/app/components/ui-footer/ui-footer.component.ts`
- Selector: `ui-footer`
- Propósito: footer institucional con logo y contenedor configurable.

### Inputs

- `logoMode: 'default' | 'compact'`
- `containerClass: string`

### Outputs

- Sin outputs.

### Uso recomendado

```html
<ui-footer logoMode="compact"></ui-footer>
```

---

## 8) `UiKpiCardComponent`

- Archivo: `src/app/components/ui-kpi-card/ui-kpi-card.component.ts`
- Selector: `ui-kpi-card`
- Propósito: tarjeta KPI simple con ícono, etiqueta y valor.

### Inputs

- `label: string`
- `value: string | number`
- `iconClass: string`

### Outputs

- Sin outputs.

### Slots

- `[kpi-label-extra]`: contenido opcional junto a la etiqueta.

### Uso recomendado

```html
<ui-kpi-card label="Ventas" [value]="total" iconClass="fa-solid fa-chart-line"></ui-kpi-card>
```

---

## 9) `UiGoalProgressComponent`

- Archivo: `src/app/components/ui-goal-progress/ui-goal-progress.component.ts`
- Selector: `ui-goal-progress`
- Propósito: barra de progreso doble (base + carrito) contra una meta.

### Inputs

- `title: string`
- `subtitle: string`
- `currentValue: number`
- `cartValue: number`
- `targetValue: number`

### Outputs

- Sin outputs.

### Slots

- `ng-content` para texto/resumen bajo la barra.

### Uso recomendado

```html
<ui-goal-progress title="Meta" subtitle="Meta principal" [currentValue]="30" [cartValue]="20" [targetValue]="100">
  <div class="mt-2 text-xs">Te faltan $500</div>
</ui-goal-progress>
```

---

## 10) `UiTableComponent`

- Archivo: `src/app/components/ui-table/ui-table.component.ts`
- Selector: `ui-table`
- Propósito: shell visual de tabla con header opcional.

### Inputs

- `title: string`
- `subtitle: string`
- `iconClass: string`

### Outputs

- Sin outputs.

### Slots

- `ng-content` para colocar tabla/listado interno.

### Uso recomendado

```html
<ui-table title="Pedidos" subtitle="Últimos 30 días" iconClass="fa-solid fa-receipt">
  <!-- contenido de tabla -->
</ui-table>
```

---

## 11) `UiDataTableComponent<T>`

- Archivo: `src/app/components/ui-data-table/ui-data-table.component.ts`
- Selector: `ui-data-table`
- Propósito: tabla responsive por proyección de templates (`mobile` y `desktop`).

### Inputs

- `rows: T[]`
- `mobileDividerClass: string`
- `desktopDividerClass: string`

### Outputs

- Sin outputs.

### Templates esperados

- `#mobileRow`
- `#desktopHeader` (opcional)
- `#desktopRow`

### Uso recomendado

```html
<ui-data-table [rows]="items">
  <ng-template #mobileRow let-row>...</ng-template>
  <ng-template #desktopHeader>...</ng-template>
  <ng-template #desktopRow let-row>...</ng-template>
</ui-data-table>
```

---

## 12) `UiProductCardComponent`

- Archivo: `src/app/components/ui-product-card/ui-product-card.component.ts`
- Selector: `ui-product-card`
- Propósito: card de producto en modo detallado o compacto.

### Inputs

- `product` (`required`): `{ id, name, badge?, img, price }`
- `discountedPriceLabel: string`
- `originalPriceLabel: string`
- `discountLabel: string`
- `qty: number`
- `mode: 'detailed' | 'compact'` (default: `'detailed'`)

### Outputs

- `qtyChange: EventEmitter<number>`
- `viewDetails: EventEmitter<void>`
- `add: EventEmitter<void>`

### Uso recomendado

```html
<ui-product-card
  [product]="product"
  [discountedPriceLabel]="formatMoney(product.price)"
  [qty]="qty"
  (qtyChange)="updateQty($event)"
  (viewDetails)="open(product)"
  (add)="add(product)"
></ui-product-card>
```

---

## 13) `UiSidebarNavComponent`

- Archivo: `src/app/components/ui-sidebar-nav/ui-sidebar-nav.component.ts`
- Selector: `ui-sidebar-nav`
- Propósito: navegación lateral por lista de links.

### Inputs

- `links: { id, icon, label, subtitle? }[]`
- `activeId: string`
- `compact: boolean` (actualmente no afecta template de forma visible)

### Outputs

- `linkSelect: EventEmitter<string>`

### Uso recomendado

```html
<ui-sidebar-nav
  [links]="navLinks"
  [activeId]="activeSection"
  (linkSelect)="activeSection = $event"
></ui-sidebar-nav>
```

---

## 14) `UiOrderTimelineComponent`

- Archivo: `src/app/components/ui-order-timeline/ui-order-timeline.component.ts`
- Selector: `ui-order-timeline`
- Propósito: timeline de estado de orden con pasos configurables.

### Inputs

- `status: string` (default: `'pending'`)
- `steps: { key, label, description }[]` (tiene default).

### Outputs

- Sin outputs.

### Uso recomendado

```html
<ui-order-timeline [status]="order.status"></ui-order-timeline>
```

---

## 15) `UiNetworkGraphComponent`

- Archivo: `src/app/components/ui-networkgraph/ui-networkgraph.component.ts`
- Selector: `ui-networkgraph`
- Propósito: renderizar red jerárquica interactiva en SVG con zoom/foco/tooltip/placa de nodo.

### Inputs

- `nodes` (`required`): `UiNetworkGraphNode[]`
- `links` (`required`): `UiNetworkGraphLink[]`
- `viewBoxWidth?: number`
- `viewBoxHeight?: number`
- `heightPx?: number | null`
- `linkStyle: 'curved' | 'straight'` (default: `curved`)
- `labelMode: 'initials' | 'short' | 'full'` (default: `short`)
- `interactive: boolean` (default: `true`)
- `selectedNodeId: string | null`
- `showLegend: boolean`
- `emptyStateText: string`
- `spendMax?: number | null`
- `showSpend: boolean`
- `showStatusDot: boolean`
- `portraitTree: boolean | 'auto'` (default: `'auto'`)
- `portraitBreakpoint: number` (default: `860`)

### Outputs

- `nodeClick: EventEmitter<UiNetworkGraphNode>`
- `nodeHover: EventEmitter<UiNetworkGraphNode | null>`

### Uso recomendado

```html
<ui-networkgraph
  [nodes]="nodes"
  [links]="links"
  [showLegend]="true"
  [interactive]="true"
  (nodeClick)="onNodeClick($event)"
></ui-networkgraph>
```

---

## Recomendaciones de uso transversal

- Mantener los componentes `ui-*` sin lógica de dominio pesada; la composición debe vivir en páginas/containers.
- Reusar `extraClass`, `containerClass`, `inputClass`, `panelClass`, etc. antes de crear nuevas variantes.
- Para estados visuales, priorizar clases globales semánticas de `styles.css` (`badge`, `btn-*`, `surface-soft`, `text-*`, `ring-*`).
- En badges de estado/nivel, aplicar siempre la representación al elemento `.badge` real (sin wrappers con estilos propios).
