# Validación del catálogo de componentes y cobertura en HTML

Fecha de validación: 2026-02-14 (fase 5 - migración buttons/inputs en Admin y User Dashboard)

## Alcance

- Revisado `gamificacion-multinivel-f/src/app/components/**`.
- Revisados templates de `gamificacion-multinivel-f/src/app/pages/**/*.html`.
- Objetivo: validar adopción del catálogo `ui-*`, detectar remanentes y avanzar la migración en `admin.component.html` y `user-dashboard.component.html`.

## Catálogo actual de componentes

1. `ui-button`
2. `ui-form-field`
3. `ui-badge`
4. `ui-modal`
5. `ui-table`

## Uso actual por pantalla (tags `ui-*`)

| Pantalla | ui-button | ui-form-field | ui-badge | ui-modal | ui-table |
|---|---:|---:|---:|---:|---:|
| admin.component.html | 47 | 13 | 2 | 1 | 0 |
| carrito.component.html | 10 | 10 | 0 | 0 | 0 |
| landing.component.html | 1 | 5 | 0 | 0 | 0 |
| login.component.html | 2 | 2 | 0 | 0 | 0 |
| order-status.component.html | 2 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 74 | 10 | 4 | 2 | 3 |

## Inventario de controles nativos remanentes por pantalla

| Pantalla | button | input | select | textarea | table | form | a |
|---|---:|---:|---:|---:|---:|---:|---:|
| admin.component.html | 0 | 9 | 2 | 4 | 3 | 0 | 0 |
| carrito.component.html | 5 | 1 | 0 | 0 | 0 | 1 | 0 |
| landing.component.html | 0 | 0 | 0 | 0 | 0 | 1 | 10 |
| login.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| order-status.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 0 | 1 | 0 | 1 | 3 | 2 | 2 |

## Resultado de validación

- El catálogo `ui-*` está operativo y creciendo en cobertura en todas las pantallas principales.
- En esta fase se avanzó de forma directa sobre `admin.component.html` y `user-dashboard.component.html` con foco en botones e inputs:
  - **Botones nativos** en Admin y User Dashboard: **0 remanentes**.
  - Inputs de texto/fecha/número migrados a `ui-form-field` en formularios de producto, envíos, estructura y cantidades clave.
- Mejora medida en inventario nativo:
  - `admin.component.html`: `button` **36→0**, `input` **18→9**.
  - `user-dashboard.component.html`: `button` **51→0**, `input` **4→1**.

## Remanentes pendientes de componentizar

- `admin.component.html` (9 inputs):
  - Inputs especiales: `file`, `checkbox`, `radio`.
  - Input numérico contextual (`cantidad` en selección dinámica de productos).
  - Inputs de solo lectura/estado en modal de estructura.
- `user-dashboard.component.html` (1 input):
  - Input readonly de link de referido.

## Próximos pasos recomendados

1. Extender catálogo con variantes para controles especiales (`ui-file-field`, `ui-choice` para `checkbox/radio`, y opción readonly explícita para `ui-form-field`).
2. Evaluar migración del input numérico dinámico de cantidad en Admin a `ui-form-field` con soporte de `min/max/step` y estilos compactos.
3. Sustituir `table` nativas pendientes (Admin/User Dashboard) por `ui-table` donde no haya restricciones funcionales.
4. Evaluar un `ui-link-button` para anchors CTA en Landing y otras pantallas.

## Conclusión

Aún **quedan controles por componentizar**, pero esta fase deja **cerrada la migración de todos los `button`** en Admin y User Dashboard, y reduce significativamente inputs nativos en ambas pantallas con avances directos hacia `componentes-ui`.
