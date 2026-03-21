# Inventario y contexto de componentización

Documento histórico resumido. Conserva el porqué de la capa `ui-*` sin repetir el catálogo ni la validación final.

## Hallazgos que originaron la iniciativa

- Había alta repetición en botones, campos, badges y tablas.
- `src/styles.css` ya contenía tokens y patrones suficientes para encapsular una librería visual.
- Algunas animaciones y efectos del dashboard eran demasiado específicos para generalizarlos en una primera etapa.

## Decisión tomada

- Estandarizar controles frecuentes en componentes `ui-*`.
- Mantener dominio y orquestación en `pages` y `services`.
- Reusar clases semánticas globales en lugar de multiplicar estilos locales.

## Estado actual

- La base de componentización ya fue implementada en las pantallas principales.
- El detalle vigente de componentes vive en `docs/catalogo-componentes-ui.md`.
- El cierre de adopción y pendientes operativos vive en `docs/validacion-catalogo-componentes.md`.

## Qué sigue siendo útil de este documento

- Recordar la motivación arquitectónica: menos duplicación, menor deuda visual y APIs de UI más claras.
