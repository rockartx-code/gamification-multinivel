# Validación del catálogo de componentes y cobertura en HTML

Fecha de validación: 2026-02-14 (fase 4 - actualización)

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
| admin.component.html | 11 | 4 | 2 | 1 | 0 |
| carrito.component.html | 10 | 10 | 0 | 0 | 0 |
| landing.component.html | 1 | 5 | 0 | 0 | 0 |
| login.component.html | 2 | 2 | 0 | 0 | 0 |
| order-status.component.html | 2 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 23 | 7 | 4 | 2 | 3 |

## Inventario de controles nativos remanentes por pantalla

| Pantalla | button | input | select | textarea | table | form | a |
|---|---:|---:|---:|---:|---:|---:|---:|
| admin.component.html | 36 | 18 | 2 | 4 | 3 | 0 | 0 |
| carrito.component.html | 5 | 1 | 0 | 0 | 0 | 1 | 0 |
| landing.component.html | 0 | 0 | 0 | 0 | 0 | 1 | 10 |
| login.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| order-status.component.html | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| user-dashboard.component.html | 51 | 4 | 0 | 1 | 3 | 2 | 2 |

## Resultado de validación

- El catálogo `ui-*` está operativo y en uso en Dashboard/Admin/Carrito/Login/Landing/Order Status.
- En esta fase se avanzó de forma directa sobre `admin.component.html` y `user-dashboard.component.html`, migrando botones/inputs de formularios y modales clave hacia `ui-button` y `ui-form-field`.
- Mejora medida en inventario nativo:
  - `admin.component.html`: `button` **44→36**, `input` **22→18**.
  - `user-dashboard.component.html`: `button` **61→51**, `input` **10→4**.
- La cobertura **todavía es parcial**: continúan pendientes en Admin y User Dashboard (acciones tabulares, controles operativos y algunos inputs especiales).

## Próximos pasos recomendados

1. Completar la migración de `button` residuales en Admin y User Dashboard (acciones de tablas, navegación secundaria y comandos rápidos).
2. Finalizar `input` residuales en Admin y User Dashboard, priorizando los de texto/number y evaluando componentes UI específicos para `checkbox`/`radio`/`file`.
3. Sustituir `table` nativas en Admin/User Dashboard por `ui-table` donde aplique.
4. Evaluar un `ui-link-button` para anchors de CTA en Landing y otras pantallas.

## Conclusión

Aún **quedan controles por componentizar**. No obstante, en esta fase se avanzó específicamente sobre Admin y User Dashboard con una reducción relevante de `button` e `input` nativos, manteniendo el enfoque de cierre en esas dos pantallas.
