# Inventario de controles HTML/CSS y plan de componentización

## 1) Alcance y metodología

Se revisaron:
- Maquetas estáticas: `maquetas/*.html`.
- Aplicación Angular: `gamificacion-multinivel-f/src/**/*.html` y `gamificacion-multinivel-f/src/**/*.css`.
- Se excluyó `node_modules`.

Se realizó un conteo de controles por etiquetas HTML y una lectura de clases utilitarias/globales en `styles.css` para identificar patrones repetidos.

## 2) Inventario global de controles (HTML)

Totales encontrados en 12 archivos HTML (4 maquetas + 8 de `src`):

| Control / Etiqueta | Ocurrencias |
|---|---:|
| `button` | 204 |
| `input` | 78 |
| `label` | 74 |
| `a` (links/acciones de navegación) | 36 |
| `img` | 28 |
| `section` | 25 |
| `option` | 11 |
| `table` | 10 |
| `header` | 10 |
| `textarea` | 8 |
| `main` | 8 |
| `footer` | 5 |
| `aside` | 5 |
| `form` | 5 |
| `select` | 4 |
| `nav` | 3 |
| `article` | 3 |

### Controles por pantalla (resumen)

- **Admin** (`admin.component.html` + `maquetas/Admin.html`): alta densidad de formularios, tablas, selectores, textareas y acciones masivas (muchos botones).
- **User Dashboard** (`user-dashboard.component.html` + `maquetas/UserDashBoard.html`): mezcla de navegación, tablas, formularios ligeros y alta cantidad de CTAs.
- **Carrito** (`carrito.component.html` + `maquetas/Carrito.html`): formularios de compra, inputs y acciones de checkout.
- **Landing/Login/Order Status**: flujos más simples centrados en CTA, inputs y navegación.

## 3) Inventario de estilos reutilizables (CSS)

Aunque gran parte del layout usa utilidades (Tailwind en clases inline), hay una base reusable en `src/styles.css`:

### Familias de controles ya presentes

- **Botones**:
  - `.btn-primary`, `.btn-olive`, `.btn-ghost`, `.btn-linkish`, `.btn-disabled`.
- **Inputs/Form fields**:
  - estilo global para `input`, `textarea`, `select` + estados `:focus` y `::placeholder`.
- **Modales**:
  - `.modal-backdrop`, `.modal-card`, `.modal-close`, `.modal-primary-btn`.
- **Tablas**:
  - `.table-soft` y variantes de `thead`, `tbody`, `tr:hover`, `td.muted`.
- **Badges/estado**:
  - `.badge`, `.badge-active`, `.badge-inactive`, `.badge-pending`, `.badge-delivered`.
  - `.badge-mini-*` para insignias compactas.
- **Tarjetas/UI chips**:
  - `.kpi-mini`, `.user-pill`, `.progress-card`, `.chip`, `.callout`.

### Estilos específicos por página

- `user-dashboard.component.css`: animaciones/efectos de progreso (`.goal-*`, `.spark-*`).
- `login.component.css`: `.role-card`.
- `carrito.component.css`: `.fade-in-item`.

## 4) Evaluación de similitud (qué controles conviene unificar)

## Alta similitud (prioridad alta)

1. **Botones de acción**
   - Se repiten muchos botones con variaciones visuales pequeñas (primario, secundario, ghost, disabled).
   - Ya existe taxonomía CSS (`.btn-*`), por lo que falta encapsulación en componente.

2. **Campos de formulario**
   - Inputs/select/textarea comparten tokens visuales globales.
   - Variación principal: etiqueta, icono, hint/error y ancho.

3. **Badges de estado**
   - Estados repetidos (`activo`, `inactivo`, `pendiente`, `entregado`, niveles mini).
   - Buen candidato a componente parametrizable por `status`/`size`.

4. **Tablas administrativas y de seguimiento**
   - Estructura homogénea (`thead` + `tbody`, filas hover, celdas muted).
   - Repetición entre dashboard/admin/maquetas.

## Similitud media (prioridad media)

5. **Cards de métricas/progreso**
   - `kpi-mini`, `progress-card`, `user-pill`, `callout` comparten contenedor, bordes, sombra y jerarquía tipográfica.
   - Diferencian contenido, pero la “caja visual” es muy parecida.

6. **Bloques de layout de pantalla**
   - Headers, secciones y wrappers repiten gradientes, blur, bordes y spacing.
   - Útil para un “Shell” de página reutilizable.

## Similitud baja (mantener específico)

7. **Animaciones épicas del dashboard (`goal-*`)**
   - Son altamente contextuales al módulo de gamificación.
   - No conviene generalizar en una primera fase.

## 5) Plan propuesto de componentización

## Fase 1 — Fundaciones (rápida, alto impacto)

1. **Definir design tokens únicos**
   - Consolidar colores, radios, shadows y spacing en variables/tokens (ya iniciados en `:root`).
2. **Componente `ui-button`**
   - Props: `variant` (`primary|olive|ghost|linkish`), `size`, `disabled`, `loading`, `icon`.
3. **Componente `ui-badge`**
   - Props: `status`, `size` (`default|mini`), `icon?`.
4. **Componente `ui-input` base**
   - Soporte para `input/select/textarea`, etiqueta, ayuda, error y prefijo/sufijo.

**Objetivo de salida:** eliminar duplicación de botones/campos/estados en Admin, Carrito y User Dashboard.

## Fase 2 — Estructuras de negocio

5. **Componente `ui-table`**
   - API por columnas + data + slots para celdas custom.
   - Estados vacíos/cargando y variantes compacta/normal.
6. **Componentes de card reutilizable**
   - `ui-stat-card`, `ui-progress-card`, `ui-callout`.
7. **Componente `ui-modal`**
   - Encapsular backdrop/card/close/actions; permitir contenido proyectado.

**Objetivo de salida:** homogeneizar vistas de gestión y reducir mantenimiento visual.

## Fase 3 — Plantillas de página

8. **Page shell reusable**
   - `ui-page-header`, `ui-section`, `ui-aside-panel`.
9. **Normalización por feature modules**
   - Migrar progresivamente Admin → Dashboard → Carrito → Landing/Login.
10. **Hardening**
   - Tests visuales/regresión y guía de uso (Storybook o catálogo interno).

## 6) Backlog sugerido (orden de ejecución)

1. `ui-button`
2. `ui-input`
3. `ui-badge`
4. `ui-modal`
5. `ui-table`
6. `ui-stat-card` / `ui-progress-card`
7. `ui-page-header` / `ui-section`

## 7) Riesgos y recomendaciones

- **Riesgo:** mezclar utilidades inline con estilos de componente sin convención.
  - **Mitigación:** definir criterio (ej. utilidades para layout, componentes para controles).
- **Riesgo:** romper pantallas con mucha densidad de acciones (Admin/Dashboard).
  - **Mitigación:** migración incremental por componente + snapshot visual por pantalla.
- **Riesgo:** variantes no documentadas (estado, tamaño, iconografía).
  - **Mitigación:** matriz de variantes y “contrato” de props antes de migrar masivo.

---

## Resultado ejecutivo

Existe alta repetición de controles de interacción (botones, campos, badges, tablas), con base visual ya presente en CSS global. La oportunidad principal no es crear más estilos, sino encapsular los existentes en componentes UI reutilizables con API clara y migración por fases para bajar deuda visual y acelerar nuevas pantallas.
