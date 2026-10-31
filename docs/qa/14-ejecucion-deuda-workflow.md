# 14 · Ejecución de la deuda con workflow multiagente

**Fecha:** 2026-09-02
**Encargo:** ejecutar la deuda documentada en `docs/qa/13` §4 (y las pendientes de 09/12) orquestando agentes.

## 1. Diseño del workflow

El reto no era el volumen (65 campos) sino la **concurrencia**: 61 de esos campos viven en un único archivo de
4 235 líneas (`admin.component.html`). Agentes en paralelo sobre el mismo archivo se pisan. El workflow por tanto:

- **Una cadena serial** de 6 agentes sobre `admin.component.html` (settings → coupons → products → stocks → varios → modales), cada uno localizando su bloque por el marcador `*ngIf="currentView === '…'"` en vez de por número de línea, porque los agentes anteriores ya habían desplazado el archivo.
- **Cuatro agentes en paralelo** sobre archivos independientes (categorías, perfil de usuario, focus-trap del modal, galería), corriendo *a la vez* que la cadena serial.
- **Tres auditores adversariales** al final, en paralelo y de solo lectura, cada uno con una lente distinta: bindings, integridad de imports/restos, y coherencia visual.

13 agentes, 0 errores, ~25 min, 948 k tokens.

## 2. Resultado de la migración

**75 campos migrados.** Censo final de controles nativos en plantillas de página:

| Antes | Ahora |
|-------|-------|
| 25 checkboxes nativos (azul del navegador) | 0 — 37 usos de `ui-checkbox` |
| 14 números, 11 textos, 6 selects, 2 fechas, 2 textareas crudos | 0 — 233 usos de `ui-form-field` |
| 13 `type="file"` | 13 (fuera de alcance: disparadores y estilos propios) |
| 2 radios (control segmentado con radios ocultos) | 2 (fuera de alcance: patrón válido) |

Además: focus-trap y devolución de foco en `ui-modal` (deuda de `docs/qa/12`), y la galería `/#/galeria` documenta ya el componente nuevo en sus 8 estados.

## 3. Lo que encontraron los auditores — 29 problemas, 6 de ellos rompían el build

La fase adversarial pagó su coste de inmediato. Los seis bloqueantes tenían la **misma raíz**, así que se corrigieron
en el componente y no en los seis call sites:

- `<ui-checkbox compact>` (atributo sin corchetes) pasa la cadena `''`, que con `strictTemplates` no es asignable a `boolean` → **error de compilación**; y aunque compilara, `''` es *falsy*: el modo compacto nunca se habría activado.
- `[checked]="stock.allowPickup"` con un modelo `boolean | undefined` → mismo error. Antes no fallaba porque Angular no tipa los bindings a propiedades del DOM nativo; al pasar a un `@Input` sí los tipa.

**Corrección sistémica:** `@Input({ transform: booleanAttribute })` en `checked`, `disabled` y `compact`. Un cambio, seis bloqueantes resueltos, y de paso la forma abreviada queda soportada de verdad.

Otros hallazgos sistémicos corregidos en la raíz:

| Hallazgo | Corrección |
|----------|-----------|
| El host de `ui-checkbox`/`ui-form-field` era `display: inline`, así que el `space-y-*` del contenedor se ignoraba y `layout="row"` no podía ocupar el ancho (~20 sitios afectados) | `display: block` para ambos hosts en el sistema |
| `.ui-check` fijaba `color`, matando las clases de color pasadas al host (`text-gray-600` inerte en 3 sitios) | `color: inherit` |
| La etiqueta interna de `ui-form-field` era de 11 px: al migrar, formularios enteros encogían respecto al original de 12 px | Etiqueta del sistema a `text-xs` (12 px) — más legible en toda la app |
| 2 casillas sin nombre accesible (su etiqueta vivía en un `<span>` hermano) | Lista de privilegios → `layout="row"` con `[label]`; interruptor de envío → nuevo `@Input() ariaLabel` |
| Etiqueta huérfana "Motivo del rechazo" (no envolvía nada, no enfocaba el campo) | Plegada en el `label=` del componente |
| Último `<select>` nativo superviviente (filtro por stock de Pedidos) | Migrado, con getter `stockFilterOptions` |
| `hint="…"` en Configuración: input inexistente, el texto de ayuda nunca se mostró | `helpText` |

Los auditores también detectaron que **un agente ejecutó build y tests pese a la prohibición** (creó y borró un spec temporal) y reportaron el `app.spec.ts` en rojo. La causa era real y **anterior al workflow**: al migrar el botón del aviso de privacidad a `ui-button` (que declara `RouterLink`), el shell pasó a necesitar `ActivatedRoute` y el spec no lo proveía. Corregido con `provideRouter([])`.

## 4. Verificación

`ng build` de producción limpio · `ng test` 2/2 en verde · capturas de Configuración (31 campos migrados, casillas doradas), Cupones, Empleados (privilegios en `layout="row"`) y la galería con `ui-checkbox` en sus 8 estados.

## 5. Deuda restante

1. **Font Awesome por CDN** — sigue siendo el mayor riesgo visual (con el CDN caído los controles solo-icono quedan mudos). Empaquetarlo es la solución de fondo.
2. Bundle inicial de 1,8 MB: lazy-loading por ruta.
3. `ui-networkgraph`: auditoría propia (SVG con tipografía y colores pre-sistema).
4. Los 13 `type="file"`: merecen un `ui-file-field` con zona de arrastre unificada.
5. Orquestación de los dos modales encadenados al entrar al dashboard.
