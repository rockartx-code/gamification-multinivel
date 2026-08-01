# Guía de Diseño de `src/styles.css`

Resumen operativo del sistema visual global.

## Objetivo

Mantener una UI cálida (arena/dorado/oliva), consistente y reusable desde `src/styles.css`.

## Reglas base

- La fuente de verdad visual vive en `:root` y en las clases globales.
- Antes de crear un color o variante nueva, intentar resolverlo con tokens existentes o con `rgba(var(--rgb-primary), x)`.
- Priorizar composición por clases semánticas; evitar estilos inline o locales para casos ya cubiertos.
- Verificar siempre desktop y mobile antes de consolidar una variante.

## Tokens y fundaciones

- Color: `--color-primary`, `--color-text*`, `--color-success`, `--color-danger`, `--color-surface-*`, `--color-bg-*`.
- Base global: `box-sizing`, altura completa en `html/body`, tipografía principal, foco accesible y estilo uniforme para `input`, `textarea` y `select`.

## Primitivas reutilizables

- Superficies: `surface-soft`, `modal-backdrop`, `modal-card`, `grain`, `bg-ambient`.
- Botones: `btn`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-ghost-danger`, `btn-linkish`, `btn-disabled`.
- Badges: `badge`, `badge-compact`, `badge-active`, `badge-inactive`, `badge-pending`, `badge-danger`, variantes `level-*` y `status-*`.
- Datos y estado: `progress*`, `table-soft`, `callout`, `empty-state`, `kpi-*`.
- Imágenes: `img-fallback` (usar junto con la directiva `[imgFallback]` sobre cualquier `<img>` de producto para mostrar un placeholder neutro si el `src` falla).
- Utilidades semánticas: familias `text-*`, `bg-*`, `border-*`, `ring-*`, `icon-*`.

### Estados negativos / destructivos

`--color-danger` (y su par `--rgb-danger`/`--text-on-danger`) alimenta `badge-danger` y
`btn-ghost-danger`. Usarlos para estados de error o acciones irreversibles (Cancelado, Devuelto,
Dev. rechazada, "Cancelar orden", "Eliminar") en vez de reutilizar `badge-active`/`btn-ghost`
neutros. `ui-status-badge` ya resuelve `tone="danger"` automáticamente para esos estados de orden;
para badges o botones ad-hoc, usar `tone="danger"`/`variant="danger"` en `ui-badge`/`ui-button`.

## Criterios de uso

- En botones, usar `ui-button` y variantes globales; no hardcodear gradientes o colores por pantalla.
- En badges, aplicar una sola representación visual sobre `.badge`; no duplicar fondo/borde en wrappers.
- En modales, preferir `ui-modal` con `panelClass`/`containerClass` antes que crear shells nuevos.
- Agregar utilidades nuevas solo cuando resuelven un patrón reusable, no un caso aislado.

## Qué evitar

- Colores hardcoded fuera del sistema.
- Variantes locales de botones o badges cuando ya existe una global.
- Múltiples estrategias para el mismo estado visual.
- Duplicar estilos entre wrapper e hijo.

## Cómo extender el sistema

1. Extender tokens en `:root`.
2. Crear o ajustar una clase semántica reusable.
3. Integrarla en `ui-*` mediante inputs de clase (`extraClass`, `containerClass`, `panelClass`, etc.).
4. Actualizar esta guía y el catálogo de componentes si la API cambia.
