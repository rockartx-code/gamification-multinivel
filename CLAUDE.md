# CLAUDE.md

Guía de arranque para trabajar en este monorepo. Datos densos y punteros: leer los docs profundos bajo demanda, no duplicarlos aquí.

## Qué es

**Finding'U** (findingu.com.mx): plataforma de venta con gamificación y compensación multinivel (MLM). Tienda online, carrito, pedidos, red de referidos, metas gamificadas, comisiones y panel admin.

- Infra 100% AWS nativa: API Gateway + Lambda (Python/boto3) + DynamoDB single-table + S3 + SES + Mercado Pago.
- **No** hay Supabase/Firebase, **no** hay i18n (todo el copy hardcodeado en español) y **no** hay CI/CD. Tests: 1 spec unitario (`app.spec.ts`) + suite E2E Playwright de 196 tests en `gamificacion-multinivel-f/e2e/` (ver `docs/qa/05-cobertura-e2e-playwright-y-hallazgos.md`, incluye quirks obligatorios para escribir pruebas).

## Mapa del monorepo

| Carpeta | Contenido |
|---|---|
| `gamificacion-multinivel-f/` | Frontend Angular 21 **y también** el backend monolito actual (`lambda/handler.py`, 6.5k líneas) |
| `Micro-lambda-GMF/` | Split del backend en microlambdas Python (en progreso) + `stepFunctions.json` + `openapi-aws.yaml` |
| `docs/` | Docs transversales: `backend-architecture.md`, `order-architecture-refactor-notes.md`, `qa/01-04`, índice en `docs/README.md` |
| `idasparaimplementar/` | Backlog de ideas; ignorar salvo petición explícita |

## Comandos

Todos se ejecutan dentro de `gamificacion-multinivel-f/`:

```bash
npm start                        # dev server (ng serve)
npm run build                    # build producción
npm run test -- --watch=false    # tests unitarios (Vitest), modo headless
npm run e2e                      # suite E2E Playwright (mocked; puerto 4300)
npm run e2e:ui                   # Playwright en modo interactivo
```

Formato: Prettier con `printWidth 100`, `singleQuote` (config en `package.json`). Indentación 2 espacios (`.editorconfig`).

## Dónde vive la lógica de negocio

Toda la lógica de negocio está en el backend (`gamificacion-multinivel-f/lambda/handler.py`); el frontend solo consume resultados calculados. Detalle completo en `docs/backend-architecture.md`.

| Qué | Dónde |
|---|---|
| Entrada HTTP + router manual (sin framework) | `lambda_handler`, handler.py:6417 y tabla de rutas 6437+ |
| Árbol de referidos (vía `leaderId`) | `_build_network_tree_with_month`, handler.py:279 |
| Metas gamificadas (7 metas dinámicas) | `_build_goals`, handler.py:459 |
| Activación mensual (default $2,500 MXN) | `_is_active` / `ASSOCIATE_MONTH`, handler.py:1656-1707 |
| Descuentos por consumo (tiers 30/40/50%) | `_calc_discount_rate`, handler.py:1604 |
| Comisiones multinivel ({1:10%, 2:5%, 3:3%}, máx. 3 niveles) | handler.py:73-78; alta en `paid` (`_apply_rewards_on_paid_order`, 3319), confirmación en `delivered` (2312), anulación en cancel/refund (2399), bloqueo por ancestro inactivo (2178) |
| Persistencia DynamoDB (patrón bucket+REF) | `_put_entity` y helpers, handler.py:630-704 |
| Pagos Mercado Pago (checkout + webhook) | handler.py:2469-2842 |

## Arquitectura frontend (resumen)

Capas estrictas (detalle en `gamificacion-multinivel-f/README.md` y reglas en `AGENTS.md`):

- `pages/` orquestan flujo → `*ControlService` (estado con `BehaviorSubject`) → `ApiService` (fachada) → `RealApiService` **o** `MockApiService` según `environment.useMockApi`.
- `components/ui-*`: presentación pura, sin lógica de negocio.
- Routing con hash (`/#/ruta`); guards por rol en `src/app/guards/auth.guard.ts`.
- Auth: JWT emitido por el backend, guardado en `localStorage['auth-user']`; `RealApiService` añade `Authorization: Bearer` + headers `x-user-id/name/role` manualmente (no hay HttpInterceptor).

## Convenciones críticas

- Si cambia un contrato API: actualizar `models/` + `services/` + consumidores **y docs** en el mismo cambio (regla de `AGENTS.md`).
- No introducir patrones nuevos si ya existe uno válido; reusar tokens/clases de `src/styles.css` (nada de estilos ad-hoc).
- La lógica de negocio va en el backend; no duplicarla en el frontend.
- Git: ramas `feat/*` o `claude/*`, PR a `main`.

## Trampas conocidas

- **El backend vive dentro del repo frontend**: `gamificacion-multinivel-f/lambda/handler.py`. No es un servicio separado ni está solo en `Micro-lambda-GMF/`.
- **Split en progreso**: `Micro-lambda-GMF/` reimplementa parte del monolito en microlambdas. Verificado en AWS (2026-08-01): la API **dev** (`ge2omdgk33`, `environment.ts`) ya enruta a las **microlambdas** `Multinivel-*`; la API **prod** (`m85v7secp8`, `environment.prod.ts`) sigue en el **monolito** `Multinivel`. Mapeo detallado en `docs/backend-architecture.md` §2.
- **Rank/VP/VG/honor board son mock-only**: existen en `MockApiService` y en los modelos TS, pero tienen 0 referencias en `handler.py`. No hay datos reales detrás.
- **`gamificacion-multinivel-f/docs/dynamodb-plan.md` histórico describía GSIs nunca implementados**; el patrón real es bucket+REF y **no hay GSIs** (la búsqueda por email es un bucket scan — limitación conocida).
- **Refactor de órdenes pendiente**: `docs/order-architecture-refactor-notes.md` — el historial de órdenes vive temporalmente mezclado en `Micro-lambda-GMF/python/core_utils.py`.
- La matriz E2E de `docs/qa/02-matriz-pruebas-e2e.md` está **diseñada pero no implementada**.
- `README.md` del frontend no menciona `Micro-lambda-GMF/`; para visión backend completa usar `docs/backend-architecture.md`.

## Documentación profunda (leer bajo demanda)

| Documento | Cuándo |
|---|---|
| `docs/README.md` | Índice completo de toda la documentación |
| `docs/backend-architecture.md` | Cualquier cambio backend: datos, comisiones, split |
| `gamificacion-multinivel-f/README.md` | Arquitectura frontend, estándares, checklist PR |
| `gamificacion-multinivel-f/AGENTS.md` | Reglas operativas antes de editar |
| `gamificacion-multinivel-f/overview.md` | Visión funcional/negocio |
| `gamificacion-multinivel-f/docs/catalogo-componentes-ui.md` | Usar/crear componentes `ui-*` |
| `gamificacion-multinivel-f/docs/guia-diseno-styles.md` | Tokens y sistema visual |
| `Micro-lambda-GMF/openapi-aws.yaml` | Contrato API (OpenAPI 3.0) |
| `docs/qa/01-04` | Funcionalidades y matriz de pruebas |
