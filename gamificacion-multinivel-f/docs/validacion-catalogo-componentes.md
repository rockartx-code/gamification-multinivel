# Validación del catálogo de componentes y cobertura en HTML

Fecha de validación: 2026-02-14 (fase 9 - cierre de remanentes en landing.component)

## Alcance

- Revisado `gamificacion-multinivel-f/src/app/components/**`.
- Revisados templates de `gamificacion-multinivel-f/src/app/pages/**/*.html`.
- Objetivo: validar adopción del catálogo `ui-*`, detectar remanentes y avanzar la migración hacia `componentes-ui` con foco en `landing.component.html`.

## Catálogo actual de componentes

1. `ui-button`
2. `ui-form-field`
3. `ui-badge`
4. `ui-modal`
5. `ui-table`

## Uso actual por pantalla (tags `ui-*`)

| Pantalla | ui-button | ui-form-field | ui-badge | ui-modal | ui-table |
|---|---:|---:|---:|---:|---:|
| admin.component.html | 48 | 24 | 2 | 1 | 0 |
| carrito.component.html | 15 | 11 | 0 | 0 | 0 |
| landing.component.html | 11 | 5 | 0 | 0 | 0 |
| login.component.html | 2 | 2 | 0 | 0 | 0 |
| order-status.component.html | 2 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 74 | 12 | 4 | 2 | 3 |

## Inventario de controles nativos remanentes por pantalla

| Pantalla | button | input | select | textarea | table | form | a |
|---|---:|---:|---:|---:|---:|---:|---:|
| admin.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| carrito.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| landing.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| login.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| order-status.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 0 | 0 | 0 | 0 | 3 | 2 | 2 |

## Resultado de validación

- El catálogo `ui-*` se consolida en `admin.component.html`, `carrito.component.html` y `landing.component.html` con eliminación total de tags HTML nativos de control/formulario/listado.
- En esta fase se completó la migración de los pendientes de `landing.component.html`:
  - Anchors (`a`) de navegación/CTA migrados a `ui-button` con `routerLink` y acciones `(pressed)` para scroll.
  - Formulario nativo de registro (`form`) migrado a contenedor `div` con submit explícito por `ui-button` (`(pressed)="createAccount()"`).
- Mejora medida en inventario nativo:
  - `landing.component.html`: `a` **10→0**, `form` **1→0**.

## Remanentes pendientes de componentizar

- `user-dashboard.component.html`:
  - `table` nativas en vistas desktop.
  - `form` de modales.
  - `a` de navegación/CTA para invitados.

## Próximos pasos recomendados

1. Completar la migración de `table`/`form`/`a` en User Dashboard para cerrar cobertura total en páginas principales.
2. Evaluar reutilización explícita de `ui-table` en User Dashboard para uniformar estructura de listados.
3. Ejecutar fase de hardening visual y accesibilidad tras cierre de remanentes en dashboard.

## Conclusión

Aún **quedan controles por componentizar** en User Dashboard, pero en esta fase queda **cerrada la migración de `landing.component.html`** con cobertura total por componentes UI y sin tags nativos remanentes de formulario/navegación.
