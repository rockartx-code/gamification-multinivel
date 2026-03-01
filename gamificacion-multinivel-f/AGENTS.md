# AGENTS.md

Guía de operación para agentes que trabajen en este repositorio.

## Objetivo

Asegurar cambios consistentes con la arquitectura, estándares y documentación vigente del proyecto.

## Orden obligatorio de lectura (antes de editar)

1. `README.md`  
2. `overview.md`  
3. `docs/catalogo-componentes-ui.md`  
4. `docs/guia-diseno-styles.md`

Si el trabajo es de backend/API, revisar además:

5. `lambda/handler.py`  
6. `src/app/models/*.ts`  
7. `src/app/services/api.service.ts`, `src/app/services/real-api.service.ts`, `src/app/services/mock-api.service.ts`

## Principios de trabajo

- No introducir patrones nuevos si ya existe uno en el proyecto.
- Mantener separación:
  - `pages`: orquestación de casos de uso.
  - `services`: estado/lógica de dominio y acceso a datos.
  - `components/ui-*`: presentación reusable.
- Reusar clases y tokens globales en `src/styles.css`; evitar estilos ad-hoc duplicados.
- Cambios de contrato API deben reflejarse en `models` + `services` + consumidor(es).

## Flujo recomendado para cualquier tarea

1. Identificar módulo afectado (`pages`, `services`, `models`, `ui-*`, `lambda`).
2. Confirmar estándar/documentación aplicable.
3. Implementar cambio mínimo viable.
4. Validar build/tests.
5. Actualizar documentación si cambió comportamiento o API interna.

## Comandos de validación

```bash
npm run build
npm run test -- --watch=false
```

## Reglas de documentación

Actualizar docs cuando aplique:

- `README.md`: cambios arquitectónicos, flujos técnicos, estándares.
- `overview.md`: cambios funcionales visibles a usuario.
- `docs/catalogo-componentes-ui.md`: cambios en `@Input/@Output`, slots o uso de `ui-*`.
- `docs/guia-diseno-styles.md`: cambios de sistema visual global.

## Criterios de aceptación para cambios

- Compila sin errores.
- No rompe rutas principales:
  - `/`
  - `/login`
  - `/dashboard`
  - `/carrito`
  - `/orden/:idOrden`
  - `/admin`
- Mantiene consistencia visual (tokens/clases semánticas).
- Mantiene compatibilidad de contrato entre frontend y backend.

## Antipatrones (evitar)

- Duplicar lógica de negocio en componentes `ui-*`.
- Crear estilos locales que contradigan `styles.css`.
- Mezclar responsabilidades de `page` y `service`.
- Cambiar contratos API sin actualizar modelos/consumidores.
- Dejar documentación desalineada tras cambios estructurales.
