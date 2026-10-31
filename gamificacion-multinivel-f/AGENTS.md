# AGENTS.md

Guía breve para trabajar en este repositorio.

## Propósito

Mantener cambios consistentes con la arquitectura, el sistema visual y la documentación vigente.

## Lectura mínima antes de editar

1. `README.md`
2. `overview.md`
3. `docs/catalogo-componentes-ui.md`
4. `docs/guia-diseno-styles.md`

Si la tarea toca backend o contratos, revisar además:

5. `lambda/handler.py`
6. `src/app/models/*.ts`
7. `src/app/services/api.service.ts`, `src/app/services/real-api.service.ts`, `src/app/services/mock-api.service.ts`

## Reglas operativas

- Respetar la separación actual:
  - `pages`: orquestación de flujos.
  - `services`: estado, dominio y acceso a datos.
  - `components/ui-*`: presentación reusable.
- No introducir patrones nuevos si ya existe uno válido en el proyecto.
- Reusar tokens y clases globales de `src/styles.css`; evitar estilos ad-hoc duplicados.
- Si cambia un contrato API, actualizar `models`, `services`, consumidores y documentación relacionada.
- Mantener los cambios chicos, explícitos y alineados con el comportamiento actual.

## Flujo recomendado

1. Identificar el módulo afectado.
2. Revisar la documentación aplicable.
3. Implementar el cambio mínimo necesario.
4. Ejecutar una validación proporcional a la tarea.
5. Actualizar docs si cambió comportamiento, contrato o sistema visual.

## Validación

- Preferir checks livianos o focalizados.
- Cuando haga falta una validación completa, usar:

```bash
npm run build
npm run test -- --watch=false
```

## Qué documento actualizar

- `README.md`: arquitectura, flujos técnicos, estándares.
- `overview.md`: comportamiento visible para usuario.
- `docs/catalogo-componentes-ui.md`: API o uso de `ui-*`.
- `docs/guia-diseno-styles.md`: tokens, clases o reglas del sistema visual.

## Aceptación mínima

- Mantener operativas las rutas principales: `/`, `/login`, `/dashboard`, `/carrito`, `/orden/:idOrden`, `/admin`.
- Conservar consistencia visual y compatibilidad frontend/backend.
- No dejar documentación desalineada tras cambios estructurales.

## Evitar

- Lógica de dominio pesada dentro de `ui-*`.
- Mezclar responsabilidades entre `page` y `service`.
- Contradecir `src/styles.css` con estilos locales innecesarios.
- Cambiar contratos sin actualizar consumidores.
