# Gamificación Multinivel - Guía Técnica de Mantenimiento

Este README está orientado a onboarding técnico para mantener el proyecto con consistencia.

## 1. Stack y alcance

- Frontend: Angular 21 (`standalone components`, `strict mode`).
- UI: Tailwind + sistema global en `src/styles.css`.
- Estado local de dominio: servicios `*ControlService` con `BehaviorSubject`.
- API: capa adaptadora `ApiService` que enruta a `RealApiService` o `MockApiService`.
- Backend: AWS Lambda en `lambda/handler.py` (DynamoDB + S3).

## 2. Estructura del repositorio

- `src/app/pages`: vistas de negocio (`landing`, `login`, `dashboard`, `carrito`, `order-status`, `admin`).
- `src/app/components/ui-*`: librería de componentes visuales reutilizables.
- `src/app/services`: lógica de acceso a datos, sesión y estado.
- `src/app/models`: contratos de datos tipados.
- `src/app/guards`: control de acceso por rol.
- `src/styles.css`: tokens, utilidades semánticas y estilos base.
- `src/environments`: switch entre API real/mock.
- `lambda/handler.py`: router HTTP + lógica de negocio backend.
- `docs/`: documentación interna (catálogo UI, guía de estilos, inventarios).

## 3. Arquitectura frontend (patrón usado)

## 3.1 Routing y navegación

- Definido en `src/app/app.routes.ts`.
- Router usa `withHashLocation()` (`/#/ruta`) en `src/app/app.config.ts`.
- Guards:
  - `adminGuard`: restringe `/admin` a rol admin.
  - `dashboardGuard`: protege lógica por rol cliente.
  - `loginGuard`: redirige si usuario ya autenticado.

## 3.2 Patrón de datos

Separación principal:

1. `ApiService`: fachada única para páginas/servicios.
2. `RealApiService` / `MockApiService`: implementación concreta.
3. `*ControlService`: estado y reglas de UI/domino consumidas por páginas.

Servicios clave:

- `AuthService`: sesión y persistencia de usuario en `localStorage`.
- `UserDashboardControlService`: datos del dashboard, red, featured y metas.
- `GoalControlService`: metas derivadas (incluye impacto del carrito).
- `CartControlService`: carrito y totales con persistencia local.
- `AdminControlService`: estado del panel admin (pedidos, clientes, productos).

## 3.3 Componentización

- `ui-*` encapsula presentación; páginas concentran orquestación de casos de uso.
- Los componentes deben ser reutilizables y configurables por `@Input`/`@Output`.
- Priorizar composición por slots (`ng-content`, `TemplateRef`) antes de duplicar.

Referencia obligatoria:

- Catálogo técnico: `docs/catalogo-componentes-ui.md`.

## 4. Sistema visual y estándares de UI

Base:

- Tokens de color/superficie/estado en `:root` de `src/styles.css`.
- Clases semánticas globales (`btn-*`, `badge`, `surface-soft`, `text-*`, `ring-*`).
- Utilidades Tailwind para layout y spacing.

Reglas de mantenimiento visual:

- No hardcodear colores sin pasar por tokens o clases semánticas.
- Reusar clases globales antes de crear utilidades nuevas.
- En badges, aplicar la representación sobre `.badge` (una sola capa visual).

Referencia obligatoria:

- Guía de diseño: `docs/guia-diseno-styles.md`.

## 5. Backend Lambda (resumen operativo)

Archivo principal:

- `lambda/handler.py`.

Responsabilidades:

- Router de endpoints HTTP.
- Autenticación/login.
- Creación de cuenta.
- Pedidos (`create/get/list/update status`).
- Dashboard usuario y admin.
- Comisiones (solicitud, recibos, CLABE).
- Assets en S3.
- Producto del mes.
- Cálculo de red y metas de gamificación.

Persistencia:

- DynamoDB (tabla principal configurable por env vars).
- S3 para activos/comprobantes.

Importante para mantenimiento:

- La lógica de negocio está centralizada en el handler; evitar duplicarla en frontend.
- Si cambia el contrato de respuesta, actualizar `models/` y servicios frontend al mismo tiempo.

## 6. Configuración y ambientes

Archivos:

- `src/environments/environment.ts`
- `src/environments/environment.prod.ts`

Variables clave:

- `useMockApi`: `true` usa `MockApiService`, `false` usa API real.
- `apiBaseUrl`: base URL para Lambda/API Gateway.

Regla:

- Desarrollo funcional rápido: habilitar mock.
- Integración/QA: usar API real y validar contratos.

## 7. Estándares de código vigentes

## 7.1 TypeScript/Angular

- `strict: true`.
- `strictTemplates: true`.
- `strictInjectionParameters: true`.
- Tipar explícitamente `@Input`, `@Output`, modelos y retornos.

## 7.2 Formato

- Indentación: 2 espacios (`.editorconfig`).
- `utf-8`.
- Prettier:
  - `printWidth: 100`
  - `singleQuote: true`
  - parser Angular para `*.html`.

## 7.3 Convenciones de implementación

- Páginas: orquestan flujo de usuario y llamadas a servicios.
- Servicios: encapsulan estado y adaptación de datos.
- Componentes `ui-*`: presentación reutilizable, mínima lógica de negocio.
- Preferir `getter`s semánticos para estado derivado de UI.
- Evitar duplicar reglas de negocio entre páginas.

## 8. Comandos de trabajo

Instalación:

```bash
npm install
```

Servidor local:

```bash
npm run start
```

Build:

```bash
npm run build
```

Tests:

```bash
npm run test -- --watch=false
```

Notas:

- Existen budgets de Angular configurados en `angular.json`.
- El proyecto puede compilar con warnings de budget; no son necesariamente errores funcionales.

## 9. Flujo recomendado para cambios

1. Identificar módulo afectado (`pages`, `services`, `models`, `ui-*`).
2. Ajustar contrato en `models` si cambia payload.
3. Actualizar `ApiService` y servicio concreto (`real/mock`) en paralelo.
4. Actualizar lógica en `*ControlService`.
5. Ajustar página y componentes UI.
6. Validar visualmente desktop/mobile.
7. Ejecutar build + tests.
8. Actualizar docs si se cambia API de componentes o reglas de diseño.

## 10. Checklist de PR / mantenimiento

- Compila sin errores: `npm run build`.
- Tests unitarios pasan: `npm run test -- --watch=false`.
- No hay regresiones de flujo:
  - login,
  - dashboard cliente,
  - carrito/checkout,
  - tracking de orden,
  - panel admin.
- Se respetan clases semánticas y tokens globales.
- Si cambió UI reusable, actualizar:
  - `docs/catalogo-componentes-ui.md`
  - `docs/guia-diseno-styles.md`
- Si cambió visión funcional global, actualizar:
  - `overview.md`.

## 11. Documentación relacionada

- Overview funcional (usuario): `overview.md`.
- Catálogo componentes UI: `docs/catalogo-componentes-ui.md`.
- Guía de diseño global: `docs/guia-diseno-styles.md`.
