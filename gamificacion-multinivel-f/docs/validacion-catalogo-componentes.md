# Validación del catálogo de componentes y cobertura en HTML

Fecha de validación: 2026-02-14 (actualización)

## Alcance

- Revisado `gamificacion-multinivel-f/src/app/components/**`.
- Revisados templates de `gamificacion-multinivel-f/src/app/pages/**/*.html`.
- Objetivo: validar adopción del catálogo `ui-*` y detectar controles aún pendientes de migración.

## Catálogo actual de componentes

1. `ui-button`
2. `ui-form-field`
3. `ui-badge`
4. `ui-modal`
5. `ui-table`

## Uso actual por pantalla (tags `ui-*`)

| Pantalla | ui-button | ui-form-field | ui-badge | ui-modal | ui-table |
|---|---:|---:|---:|---:|---:|
| admin.component.html | 3 | 0 | 2 | 1 | 0 |
| carrito.component.html | 4 | 2 | 0 | 0 | 0 |
| landing.component.html | 0 | 0 | 0 | 0 | 0 |
| login.component.html | 2 | 2 | 0 | 0 | 0 |
| order-status.component.html | 0 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 13 | 1 | 4 | 2 | 3 |

## Inventario de controles nativos remanentes por pantalla

| Pantalla | button | input | select | textarea | table | form | a |
|---|---:|---:|---:|---:|---:|---:|---:|
| admin.component.html | 42 | 21 | 2 | 4 | 3 | 0 | 0 |
| carrito.component.html | 11 | 9 | 0 | 0 | 0 | 1 | 0 |
| landing.component.html | 1 | 5 | 0 | 0 | 0 | 1 | 10 |
| login.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| order-status.component.html | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| user-dashboard.component.html | 61 | 10 | 0 | 1 | 3 | 2 | 2 |

## Resultado de validación

- El catálogo `ui-*` está operativo y en uso en Dashboard/Admin/Carrito/Login.
- La cobertura **todavía es parcial**: aún quedan controles nativos por migrar, principalmente en:
  - `user-dashboard.component.html`
  - `admin.component.html`
  - `carrito.component.html`

## Próximos pasos recomendados

1. Migrar más `button` en Dashboard/Admin a `ui-button`.
2. Migrar formularios restantes (inputs/select/textarea) de Admin/Dashboard a `ui-form-field`.
3. Reemplazar badges nativos residuales por `ui-badge` en pantallas secundarias.
4. Evaluar un `ui-link-button` para sustituir anchors de acción (`a`) cuando actúan como CTA.

## Conclusión

Aún **quedan controles por componentizar**. La migración avanza, pero no está cerrada al 100%.
