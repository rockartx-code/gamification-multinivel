# 15 · Auditoría mecánica: cuánto queda suelto

**Fecha:** 2026-09-02
**Herramienta:** `gamificacion-multinivel-f/tools/auditoria_ui.py` (`npm run audit:ui`)

No es una opinión: es un script determinista que recorre las 25 plantillas del frontend, lee el
contrato real de cada componente `ui-*` (sus `@Input`/`@Output` declarados en el `.ts`) y cuenta
todo lo que queda fuera del sistema. Sale con código 1 si alguna categoría **sube** respecto al
valor medido hoy, así que la deuda no puede crecer en silencio.

## Resultado

### En cero — no admiten reincidencia

| Categoría | Cuenta |
|-----------|--------|
| `<input>`/`<select>`/`<textarea>` de texto en plantillas de página | **0** |
| Atributos que un `ui-*` ignoraría en silencio (tipo el antiguo `hint=`) | **0** |
| `<img>` sin `alt` | **0** |

### Deuda aceptada, con presupuesto congelado

| Categoría | Cuenta | Por qué |
|-----------|--------|---------|
| `<input type="file">` | 13 | Disparadores y zonas de arrastre propias; piden un `ui-file-field` propio |
| Radios nativos | 2 | Control segmentado (radios ocultos dentro de etiquetas estilizadas), patrón válido |
| **Botones solo-icono sin nombre accesible** | **31** | Deuda real de accesibilidad: sin texto, `aria-label` ni `title`, un lector de pantalla solo anuncia "botón" |
| **Colores fuera de la paleta** | **47** | `text-red-400` ×11, `text-gray-300` ×7, `text-yellow-500` ×7, emerald/sky/violet/rose sueltos. 25 de los 47 están en `admin.component.html` |

### Informativo — decisiones de diseño, no defectos

| Métrica | Cuenta | Lectura |
|---------|--------|---------|
| `text-[Npx]` arbitrarios | 239 | El sistema no tiene escala de micro-tipografía (10/11 px); merece tokens, no corrección caso a caso |
| Colores literales (`#hex`, `rgba()`) en plantillas | 31 | Sobre todo sombras y el verde de WhatsApp |
| `shadow-[…]` arbitrarios | 13 | Anteriores a los tokens `--shadow-rest/lift/float` |
| Texto visible sin acentos | 13 | "Configuracion de negocio", "Codigo de autorizacion POS", "Numero de guia"… |
| Dependencias CDN en runtime | 4 | Font Awesome + Google Fonts: el mayor riesgo visual del producto |
| Emoji en plantilla | 1 | El `rankIcon` de rangos, decisión consciente |

### Uso de la librería (contexto)

`ui-button` 325 · `ui-form-field` 233 · `ui-checkbox` 37 · `ui-kpi-card` 32 · `ui-modal` 29 ·
`ui-status-badge` 12 · `ui-choice-card` 9 · `ui-pagination` 8 · `ui-product-card` 6 ·
`ui-badge` 6 · `feature-badge` 5 · `ui-goal-progress` 4 · `ui-data-table` 4 · `ui-qty-stepper` 3 ·
`ui-order-timeline` 3 · `ui-sidebar-nav` 3 · `ui-table` 3 · `ui-networkgraph` 2

## Falsos positivos que hubo que eliminar del propio auditor

Medir mal es peor que no medir; tres reglas se corrigieron antes de dar cifras:

1. `[alt]="producto.nombre"` **sí** es un `alt` (enlazado): 10 falsos positivos.
2. La plantilla interna de `ui-button` proyecta contenido con `<ng-content>`, así que no puede
   juzgarse por su texto literal: 3 falsos positivos.
3. `(keydown.enter)` sobre el host de un componente **sí** funciona —el evento burbujea desde el
   `<input>` interno—, no es un atributo desconocido: 3 falsos positivos.

## Siguiente pase, en orden de valor

1. **Empaquetar Font Awesome** (elimina 1 de las 4 dependencias CDN y, con ella, el riesgo de que
   31 botones solo-icono queden mudos si el CDN falla).
2. **31 nombres accesibles**: cada botón solo-icono necesita un `aria-label` con significado
   humano; no es automatizable, hay que leer el contexto de cada uno.
3. **47 colores fuera de paleta**: decidir por caso si son estado semántico (→ token `danger`,
   `success`) o descuido (→ token del sistema).
4. **Escala de micro-tipografía** (`--text-2xs`/`--text-xs`) para absorber los 239 `text-[Npx]`.
5. `ui-file-field` con zona de arrastre para los 13 `type="file"`.
