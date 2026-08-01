# Índice de Documentación — Monorepo Gamificación Multinivel

## Raíz del monorepo

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`../CLAUDE.md`](../CLAUDE.md) | Guía de arranque para agentes y sesiones de Claude Code | Inicio de una nueva sesión; referencia sobre tools/arquitectura del proyecto |
| [`backend-architecture.md`](backend-architecture.md) | Monolito handler.py: patrón DynamoDB bucket+REF, motor de comisiones, roadmap hacia Micro-lambda-GMF | Antes de tocar backend; para entender deuda técnica y estado actual |
| [`order-architecture-refactor-notes.md`](order-architecture-refactor-notes.md) | Refactor pendiente: migración core_utils.py → order_domain/order_repository | Planificación de cambios en dominio de órdenes |

## Historias de Usuario (ingeniería inversa, 2026-08)

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`hu/01-hu-auth-registro-perfil.md`](hu/01-hu-auth-registro-perfil.md) | 18 HU: registro, verificación email, login, recuperación, perfil | Cambios en auth/perfil; diseño de pruebas |
| [`hu/02-hu-tienda-carrito-ordenes.md`](hu/02-hu-tienda-carrito-ordenes.md) | 31 HU: tienda, carrito, checkout, pagos, ciclo de vida de órdenes | Cambios en compra/órdenes; diseño de pruebas |
| [`hu/03-hu-dashboard-red-comisiones.md`](hu/03-hu-dashboard-red-comisiones.md) | 18 HU: metas, red, comisiones, notificaciones (3 MOCK-ONLY) | Cambios en dashboard del asociado |
| [`hu/04-hu-admin.md`](hu/04-hu-admin.md) | 25 HU: panel admin completo + RBAC de 30 privilegios | Cambios en el panel admin |

## QA

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`qa/01-funcionalidades-sistema.md`](qa/01-funcionalidades-sistema.md) | Inventario exhaustivo de funcionalidades implementadas | Antes de diseñar pruebas o cambios de negocio |
| [`qa/02-matriz-pruebas-e2e.md`](qa/02-matriz-pruebas-e2e.md) | Matriz E2E DISEÑADA (estructura y escenarios); implementación pendiente | Referencia de cobertura planeada (NO ejecutable aún) |
| [`qa/03-comparacion-matriz-hallazgos-findingu.md`](qa/03-comparacion-matriz-hallazgos-findingu.md) | Trazabilidad: hallazgos del cliente vs. matriz E2E | Validación de cobertura frente a requerimientos reales |
| [`qa/04-cambios-aplicados-y-validacion-plan.md`](qa/04-cambios-aplicados-y-validacion-plan.md) | Registro de cambios implementados y plan de validación | Cierre de ciclos; auditoría de fixes aplicados |
| [`qa/05-cobertura-e2e-playwright-y-hallazgos.md`](qa/05-cobertura-e2e-playwright-y-hallazgos.md) | Suite E2E Playwright implementada (196 tests), bugs confirmados y quirks | Ejecutar/ampliar pruebas E2E; priorizar fixes |
| [`qa/06-correcciones-y-features-2026-08.md`](qa/06-correcciones-y-features-2026-08.md) | Cierre 2026-08: 16 bugs corregidos, 9 peticiones implementadas, causas raíz de errores dev, pendientes de deploy | Estado actual del sistema; decidir despliegue |
| [`../gamificacion-multinivel-f/docs/ux/analisis-ui-ux-2026-08.md`](../gamificacion-multinivel-f/docs/ux/analisis-ui-ux-2026-08.md) | Análisis UI/UX de 12 pantallas con capturas y propuestas priorizadas | Planear mejoras visuales/usabilidad |

## Frontend — Operación y arquitectura

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`../gamificacion-multinivel-f/README.md`](../gamificacion-multinivel-f/README.md) | Guía técnica de mantenimiento: stack, arquitectura, estándares, checklist PR | Inicio del trabajo frontend; PR guidelines |
| [`../gamificacion-multinivel-f/AGENTS.md`](../gamificacion-multinivel-f/AGENTS.md) | Reglas operativas para agentes: capas, contrato API sincronizado, restricciones | Trabajo con agentes Claude en este proyecto |
| [`../gamificacion-multinivel-f/overview.md`](../gamificacion-multinivel-f/overview.md) | Visión funcional y de negocio; casos de uso e impacto | Contexto de negocio antes de cambios arquitectónicos |

## Frontend — Componentes y diseño

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`../gamificacion-multinivel-f/docs/catalogo-componentes-ui.md`](../gamificacion-multinivel-f/docs/catalogo-componentes-ui.md) | API de componentes ui-* (props, ejemplos, consumo) | Desarrollo de features; reutilización de componentes |
| [`../gamificacion-multinivel-f/docs/guia-diseno-styles.md`](../gamificacion-multinivel-f/docs/guia-diseno-styles.md) | Tokens de diseño, sistema visual, convenciones de color/espaciado | Antes de escribir estilos nuevos |
| [`../gamificacion-multinivel-f/docs/dynamodb-plan.md`](../gamificacion-multinivel-f/docs/dynamodb-plan.md) | Patrón real de claves DynamoDB (actualizado 2026-08) | Diseño de queries y estructura de datos backend |
| [`../gamificacion-multinivel-f/docs/envia_quote.md`](../gamificacion-multinivel-f/docs/envia_quote.md) | Integración de cotización de envíos | Feature específica; consultar si se trabaja con envíos |

## Frontend — Histórico y gobernanza

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`../gamificacion-multinivel-f/docs/inventario-controles-componentizacion.md`](../gamificacion-multinivel-f/docs/inventario-controles-componentizacion.md) | Histórico de adopción de componentes; evolución de la arquitectura | Auditoría de deuda técnica en UI |
| [`../gamificacion-multinivel-f/docs/validacion-catalogo-componentes.md`](../gamificacion-multinivel-f/docs/validacion-catalogo-componentes.md) | Validación de adopción del catálogo; cobertura e inconsistencias | Planeación de sprints de refactor |
| [`../gamificacion-multinivel-f/docs/archive/`](../gamificacion-multinivel-f/docs/archive/) | Histórico de decisiones previas: migraciones, arquitectura pasada | Referencia únicamente; no activo |

## Backend split (`../Micro-lambda-GMF/`)

| Documento | Alcance | Cuándo leerlo |
|-----------|---------|---------------|
| [`../Micro-lambda-GMF/openapi-aws.yaml`](../Micro-lambda-GMF/openapi-aws.yaml) | Contrato OpenAPI 3.0 del API Gateway (microlambdas) | Cambios de contrato API; integración frontend-backend |
| [`../Micro-lambda-GMF/stepFunctions.json`](../Micro-lambda-GMF/stepFunctions.json) | Orquestación AWS Step Functions del split backend | Cambios en flujos de órdenes/comisiones del split |
