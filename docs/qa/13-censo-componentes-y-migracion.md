# 13 · Censo de componentes a mano, migración y animaciones de siguiente nivel

**Fecha:** 2026-09-01
**Pregunta:** ¿todas las pantallas usan la librería `ui-*` o hay componentes visuales duplicados a mano? Validar variantes de cada componente y elevar el diseño con animaciones.

## 1. Censo (medido con grep sobre todos los templates)

| Duplicación encontrada | Cantidad | Componente que debía usarse |
|------------------------|----------|------------------------------|
| Paginaciones ‹ 1 2 3 › a mano | **6** (admin ×5, campañas ×1) + 1 variante en dashboard | No existía → **creado `ui-pagination`** |
| Tarjetas KPI a mano (label + valor) | **9** del patrón exacto en admin | `ui-kpi-card` existente |
| Tarjetas de selección (entrega/sucursal/pago/dirección/paquetería) | **5 bloques** en carrito con clases idénticas | No existía → **creado `ui-choice-card`** |
| Stepper −/n/+ | 2 implementaciones (product-card, carrito con input numérico) | No existía → **creado `ui-qty-stepper`** |
| Campo de contraseña con toggle a mano | **2** (login, reset-password ×2 campos) | `ui-form-field type=password` ya lo trae integrado |
| Búsquedas de tabla con lupa a mano | **4** migradas (admin ×3, campañas ×1) | `ui-form-field` con `leadingIconClass` |
| Textareas con label a mano | 2 (carrito, devolución) | `ui-form-field kind=textarea` |
| Botones crudos duplicando `ui-button` | cupón Aplicar/Quitar, "Usar otra dirección", botón del aviso de privacidad | `ui-button` (nueva **variante `forest`**) |
| Campos crudos restantes en admin | ~60 (formularios de productos/stocks/POS/configuración) | Documentado como deuda dirigida (§4) |

## 2. Migraciones ejecutadas

- **`ui-pagination`** (nuevo): página base cero, ventana de 5, se oculta con una página, `aria-current`, deshabilitable durante cargas. Reemplaza los 7 bloques; el activo se pinta oro con micro-hover.
- **`ui-choice-card`** (nuevo): `role="radio"` + `aria-checked`, layouts `stack` (columna centrada con check) y `row`; estado seleccionado con elevación y **pop spring** al elegir. Migrados los 5 bloques del carrito — el flujo (tipo de entrega → sucursal → método de pago) se verificó en vivo con la captura.
- **`ui-qty-stepper`** (nuevo): clamp min/max, `aria-label` por artículo, hover con escala spring. Sustituye los +/− del product-card y el input numérico del carrito (mejor tap-target móvil).
- **`ui-form-field`** absorbe: los 3 campos de contraseña a mano (login/reset — se eliminó el código muerto de toggles), 4 búsquedas de tabla, 2 textareas. El botón "Aplicar" del cupón (texto blanco sobre dorado, bajo contraste) ahora es `ui-button primary`.
- **`ui-kpi-card`** absorbe 9 tiles del admin; el KPI "Prom. descuento" estaba **hardcodeado en "10%"** → ahora se computa (`averageDiscountLabel`); ídem ronda previa con "Assets faltantes".
- **`ui-button`** gana la variante **`forest`** (CTA de énfasis en verde bosque) y el aviso de privacidad la usa.

## 3. Variantes y animaciones de siguiente nivel

- **`linkish` rediseñada**: era un gemelo visual de `ghost` (mismo fondo marfil + borde). Ahora es una acción terciaria real con aspecto de enlace: sin fondo, subrayado dorado al hover. Tres pesos de acción claramente distintos: primary / ghost / linkish.
- **Modal**: entrada animada — backdrop con fade y tarjeta con **pop spring** (`--ease-spring`, 400 ms).
- **Botón primario y forest**: **barrido de brillo** al hover (900 ms `--ease-luxe`) — el toque de lujo discreto.
- **`ui-choice-card`**: pop al seleccionar + elevación.
- **`ui-qty-stepper` y `ui-pagination`**: micro-escala spring en hover/active.
- **`.skeleton`**: esqueleto de carga con barrido de luz, aplicado a los estados de carga de Estadísticas y Cuadro de Honor (con `aria-busy`).
- Todo desactivable vía `prefers-reduced-motion` (bloque global ampliado).

## 4. Deuda dirigida (siguiente pasada)

1. **~60 campos crudos del admin** (formularios de Productos, Stocks, POS, Configuración): migrarlos a `ui-form-field` por vista, con prueba funcional de cada formulario — los selects con `[ngValue]` numérico requieren verificación caso por caso (los getters `*OptionsStable` ya existen para alimentarlos).
2. Las búsquedas de admin con markup ligeramente distinto al patrón (2 restantes) — mismo tratamiento.
3. `admin-categories` (3 campos) — pendiente menor.
4. Regla de equipo sugerida: *un botón, campo, badge, KPI, stepper, paginación o tarjeta de selección nunca se escribe a mano; si falta una variante, se agrega al componente y a la galería.*

## 5. Verificación

Galería `/#/galeria` ampliada con la sección "Selección, cantidad y paginación" (choice-cards interactivas, stepper, paginación con página activa, skeletons) y el botón forest como variante de `ui-button`. Capturas: galería completa, carrito con "Recoger en sucursal" seleccionada vía `ui-choice-card` (flujo funcional intacto: Entrega=Sucursal, Envío=Gratis), login con el campo de contraseña del sistema. `ng build` de producción limpio.
