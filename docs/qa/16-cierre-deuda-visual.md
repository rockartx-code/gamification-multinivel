# 16 · Cierre de la deuda visual: barrido, correcciones y empaquetado

Cierra el ciclo abierto en `13` (censo), `14` (ejecución de la deuda) y `15`
(auditoría mecánica). El punto de partida fue el barrido masivo de plantillas
hecho por agentes en paralelo; este documento recoge **lo que las auditorías
adversarias encontraron mal en ese barrido** y cómo quedó resuelto.

---

## 1. La regresión de cascada (severidad alta)

El barrido sustituyó ~126 valores arbitrarios `text-[11px]` / `text-[10px]`
por las clases `text-mini` / `text-micro`. Esas clases estaban declaradas en
`styles.css` como **CSS plano**, es decir, fuera de cualquier `@layer`.

En Tailwind v4 el CSS sin capa gana a cualquier regla con capa,
independientemente del orden. Consecuencia real, confirmada en
`user-dashboard.component.html`:

```html
<!-- antes: en ≥640px el texto subía a 12px -->
class="text-[11px] sm:text-xs …"
<!-- después: .text-mini ganaba siempre; sm:text-xs dejó de aplicar -->
class="text-mini sm:text-xs …"
```

La corrección es usar la directiva nativa de Tailwind v4:

```css
@utility text-mini  { font-size: 11px; }
@utility text-micro { font-size: 10px; }
@utility elev-rest  { box-shadow: var(--shadow-rest); }
@utility elev-lift  { box-shadow: var(--shadow-lift); }
@utility elev-float { box-shadow: var(--shadow-float); }
```

Verificado sobre el CSS compilado, no sobre el fuente: en
`styles-*.css` ambas reglas caen ya dentro de la capa `utilities`, con
`.sm\:text-xs` **después** de `.text-mini`, así que la variante responsive
vuelve a ganar a partir de 40rem.

## 2. Utilidades nuevas creadas por necesidad real

| Utilidad | Motivo |
|---|---|
| `elev-up` | La barra fija al borde inferior de tienda usaba `elev-float`, una sombra *hacia abajo* que caía fuera de la pantalla. La sombra tiene que ir hacia arriba, que es de donde llega el contenido. |
| `glow-gold` | El punto de estado del hero usaba `elev-rest` (sombra de tarjeta): invisible en un punto de 8px. Un halo sí se lee como indicador. |
| `.text-success` global | Solo existía anidado en `.modal-card`, así que fuera del modal las plantillas caían en `emerald-*`. |
| `.text-sage` / `.bg-sage-10` / `.border-sage-30` | Estado *en curso*, distinto del bosque (estado final). |
| `.text-gold-vivo` | Primer puesto del podio, donde el oro plano compite con los chips ámbar vecinos. |

## 3. Correcciones semánticas de color

- **`order-status`, bloque «En camino»**: usaba el mismo verde bosque que
  «Entregado». Un pedido en tránsito y uno entregado se veían idénticos.
  Ahora usa salvia.
- **`admin`, chips de producto**: «En POS» (ámbar) quedaba pegado a
  «Comisionable» (oro). Dos amarillos casi idénticos no se leen como estados
  distintos. El oro es la marca (comisión/valor); POS pasa a salvia informativa.
- **`admin`, iconos de tipo de archivo**: `text-danger` significa error, no
  «es un PDF». Iconos a color neutro.
- **`user-dashboard`, toggles activos**: `bg-emerald-500/10` (paleta ajena) en
  3 sitios → `bg-forest-10`.
- **Podio**: primer puesto en `text-gold` quedaba más apagado que el bronce
  (`amber-700`) que tenía debajo. Ahora `text-gold-vivo`, en 7 sitios.
- **Toasts**: los dos toasts flotantes de la app tenían elevación distinta
  (`elev-float` vs `elev-lift`) siendo el mismo patrón. Unificados.
- **Reversión de 4 bajadas de contraste**: el barrido había cambiado
  `text-green-900`, `text-amber-900` y `text-emerald-900` por su variante
  `-800` en texto de énfasis. Revertido.

## 4. Defecto en el propio auditor

`tools/auditoria_ui.py` daba por nombrado cualquier botón con un atributo que
casara `aria-?[Ll]abel`. Eso incluye un `aria-label` suelto sobre
`<ui-button>`, que **se queda en el host** y no llega al `<button>` interior:
un falso negativo que ocultaba botones sin nombre accesible.

La comprobación ahora depende de la etiqueta:

- `<ui-button>` → solo vale el `@Input` `ariaLabel`.
- `<button>` nativo → vale `aria-label` o `[attr.aria-label]`.

Con la regla corregida aparecieron 3 casos reales (tienda ×2,
user-dashboard ×1), ya convertidos a `ariaLabel`.

## 5. Font Awesome deja de venir de un CDN

La app cargaba los iconos desde `cdnjs.cloudflare.com` en tiempo de ejecución:
una dependencia de terceros en la ruta crítica del render. Ahora se empaqueta
desde `node_modules`:

- `@fortawesome/fontawesome-free` como dependencia del proyecto.
- `angular.json` → `styles` incluye `all.min.css`; Angular emite las webfonts
  con hash en `media/`.
- Retirado el `<link>` del CDN en `src/index.html`.

Coste: el CSS inicial pasa de 11.85 kB a 29.82 kB transferidos. A cambio, los
iconos dejan de depender de un tercero. Verificado en navegador con
`document.fonts.check('900 16px "Font Awesome 6 Free"')` → `true` en tienda,
user-dashboard y galería.

Quedan 3 referencias a CDN (Google Fonts: 2 `preconnect` + 1 hoja). No se
tocan en esta ronda.

## 6. Estado del trinquete

Presupuestos en `tools/auditoria_ui.py`, congelados en el valor medido hoy.
El script sale con código 1 si alguno sube.

| Categoría | Antes (docs/qa/15) | Ahora |
|---|---|---|
| `controles_nativos` | 0 | **0** |
| `atributos_desconocidos` | 0 | **0** |
| `img_sin_alt` | 0 | **0** |
| `iconos_sin_nombre` | 31 | **0** |
| `paleta_ajena` | 47 | **0** |
| `file_inputs` | 13 | 13 |
| `radios_nativos` | 2 | 2 |

Informativos (sin presupuesto): `color_literal` 18, `tamanos_arbitrarios` 12,
`cdn_en_runtime` 3, `emoji_en_plantilla` 0.

## 7. Verificación

- `ng build` — correcto (los 3 avisos de presupuesto de bundle son previos).
- `ng test` — 2/2.
- `python3 tools/auditoria_ui.py` — ninguna categoría bloqueante excede.
- Capturas con Chromium headless de tienda, user-dashboard, admin,
  order-status y galería: sin errores en consola.

## 8. Pendiente

- `file_inputs` (13) y `radios_nativos` (2): requieren componentes nuevos
  (`ui-file-input`, `ui-radio-group`), no un barrido.
- Google Fonts sigue viniendo de CDN.
- `color_literal` (18) y `tamanos_arbitrarios` (12): informativos; la mayoría
  son valores de un solo uso en gráficos y micro-iconografía.
