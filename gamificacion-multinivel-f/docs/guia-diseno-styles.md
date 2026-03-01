# Guía de Diseño de `src/styles.css`

Este documento describe la intención de diseño del archivo global `src/styles.css` para futuras implementaciones.

## 1. Objetivo del sistema visual

El CSS global define un sistema temático cálido (arena/dorado/oliva) con:

- superficies claras y suaves,
- contraste moderado para legibilidad,
- componentes tipo “pill/card” consistentes,
- utilidades semánticas para acelerar implementación en páginas nuevas.

## 2. Tokens base (`:root`)

La fuente de verdad está en variables CSS:

- Color primario: `--color-primary` y `--rgb-primary`.
- Texto: `--color-text`, `--color-text-muted`, `--color-text-inverse`.
- Estados: `--color-success`, `--color-danger`.
- Superficies: `--color-surface-1`, `--color-surface-2`, `--color-surface-3`.
- Derivados de fondo: `--color-bg-primary`, `--color-bg-secondary`.

Regla recomendada:

- Si necesitas un color nuevo para UI de producto, primero evalúa si puede expresarse con `rgba(var(--rgb-primary), x)` o con los tokens de superficie existentes.

## 3. Fundaciones globales

Bloques base relevantes:

- `* { box-sizing: border-box; }`
- `html, body { height: 100%; }`
- tipografía principal en `body` y títulos en `h1..h4`.
- foco accesible con `:focus-visible`.
- estilo base consistente para `input`, `textarea`, `select`.

## 4. Superficies y capas

Clases clave:

- `.surface-soft`: superficie principal para tarjetas internas.
- `.modal-backdrop` y `.modal-card`: base para overlays/modales.
- `.grain` y `.bg-ambient`: textura y atmósfera de fondo.

Uso recomendado:

- Tarjetas de contenido: `surface-soft`.
- Modal reusable: usar `ui-modal` con `panelClass` que incluya `modal-card`.

## 5. Sistema de botones

Base:

- `.btn` define forma, borde y transición.

Variantes:

- `.btn-primary`
- `.btn-secondary`
- `.btn-ghost`
- `.btn-linkish`
- `.btn-disabled`

Regla de implementación:

- No hardcodear gradientes/colores de botón en páginas; usar `ui-button` + variantes.

## 6. Sistema de badges

Base:

- `.badge` + opcional `.badge-compact`.
- tonos base: `.badge-active`, `.badge-inactive`, `.badge-pending`.

Variantes de representación (aplicadas al mismo `.badge`):

- Niveles: `.badge.level-1` ... `.badge.level-5`
- Estado: `.badge.status-active`, `.badge.status-inactive`

Regla crítica:

- Debe existir una sola capa de badge (sin wrapper con estilos de fondo/borde/padding).
- Evitar combinaciones duplicadas tipo `.level-*` + `.level-* .badge`.

## 7. Progreso, tablas y callouts

Clases funcionales:

- Progreso: `.progress`, `.progress-fill`, `.progress-fill-secondary`
- Tabla: `.table-soft` + subreglas `thead/tbody/hover`
- Mensajes: `.callout`
- KPIs: `.kpi-mini`, `.kpi-warn`, `.kpi-good`

Patrón:

- Se prioriza composición por clases semánticas, no estilos inline complejos.

## 8. Utilidades semánticas

Textos:

- `.text-main`, `.text-muted`, `.text-accent`, `.text-gold`, `.text-danger`, etc.

Fondos:

- `.bg-olive`, `.bg-olive-10`, `.bg-gold-12`, `.bg-sand-*`, `.bg-ivory-*`.

Bordes/anillos:

- `.border-olive-*`, `.border-gold-35`, `.ring`, `.ring-primary`, `.ring-secondary`,
- `.ring-status-active`, `.ring-status-inactive`.

Íconos:

- `.icon-muted`, `.icon-accent`, `.icon-status-active`, `.icon-status-inactive`.

## 9. Guía para implementar nuevas pantallas

Checklist práctico:

1. Definir estructura con componentes `ui-*` existentes.
2. Reusar tokens (`var(--color-*)`, `var(--rgb-*)`) antes de crear nuevos colores.
3. Reusar clases semánticas globales (`surface-soft`, `btn-*`, `badge`, `text-*`, `ring-*`).
4. Añadir utilidades nuevas solo si cubren un patrón reutilizable, no un caso único.
5. Mantener consistencia de contraste con los estados `success/danger/muted`.
6. Verificar mobile + desktop (breakpoints ya usados en el proyecto).

## 10. Qué evitar

- Duplicar estilos de un mismo componente en wrapper e hijo.
- Introducir colores hardcoded fuera del sistema sin tokenizar.
- Mezclar múltiples estrategias para un mismo estado visual (ej. badge por tono y por contenedor simultáneamente).
- Crear variantes locales de botones/badges cuando ya existen variantes globales.

## 11. Si se necesita extender el sistema

Orden recomendado:

1. Extender tokens en `:root`.
2. Crear o ajustar clase semántica global reutilizable.
3. Integrarla en `ui-*` mediante inputs (`extraClass`, `containerClass`, etc.).
4. Documentar el cambio en este archivo y en el catálogo de componentes.
