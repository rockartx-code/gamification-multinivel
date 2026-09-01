# 11 · Auditoría de diseño del sistema visual (mirada de diseñador)

**Fecha:** 2026-09-01
**Método:** matriz de contraste WCAG computada sobre los pares (fondo, texto) que `styles.css` combina realmente (mezclando alphas sobre las superficies reales), más crítica visual sobre capturas 1:1 de landing, tienda con sesión y admin.

---

## 1. Matriz de contraste (evidencia objetiva)

23 pares medidos. El sistema resultó mayormente sólido — el cuerpo (12.2:1), los muted (4.6–5.0), todos los pares oro (5.7–9.0), el bosque (10.7) y los botones pasan AA. Fallas y arreglos:

| Par | Antes | Después |
|-----|-------|---------|
| `text-gray-400` de Tailwind (#9ca3af) sobre crema — usado en timestamps, notas, "Próximamente" | **2.46 FALLA** | Colapsado al muted del sistema (#66706a → 4.6–5.0). Un gris menos, además: la escala tenía demasiados escalones indistinguibles. |
| Placeholder claro #b4aea3 | **2.13 FALLA** | #7c766c (~4.5): la pista del campo vuelve a leerse. |
| `.text-stone` #8f8673 | **3.49** (solo apto texto grande, se usaba pequeño) | #746b5a (5.1/4.75). |
| `--color-success` #5f7f6a | **4.30** (bajo AA por poco) | #51705f (5.3/4.95); anillos de estado activos actualizados al mismo tono. |
| `.text-gold-70` | **Clase inexistente** (5 usos en el dashboard heredaban el color del padre: el label "RANGO ACTUAL" no era dorado) | Definida: `rgba(107,83,32,.85)`. |

## 2. Crítica de diseñador y correcciones

**Tipografía — monocultivo de peso.** Prácticamente todo era `font-extrabold` (800): títulos de sección, KPIs, precios, labels. Cuando todo grita, nada destaca; la jerarquía dependía solo del tamaño. Corrección: los títulos de sección de dashboard y admin bajan a **semibold (600)** — la serif Fraunces aporta la personalidad y el 800 queda reservado para los datos (números, precios, KPIs), creando dos ejes de jerarquía (tamaño × peso) en lugar de uno.

**Temperatura de los grises.** `.text-gray-600/700` eran neutros fríos (#5a5a5a/#4e4e4e) dentro de un sistema cálido con tinta verdosa (#26312b): en pantalla producían una vibración sutil de "dos mundos". Reentonados a la misma familia (#57615a / #47514b), mismo contraste, una sola temperatura.

**Elevación sin idioma.** Las sombras eran ad-hoc (`0 10px 28px rgba(0,0,0,.06)`, `0 30px 90px…`, negras puras). Ahora hay una escala de tres pasos con tinte bosque —`--shadow-rest / --shadow-lift / --shadow-float`— aplicada a kpi-mini, modal-card y tarjetas; las sombras teñidas del color ambiental se sienten materia, no manchas grises.

**Radios sin escala.** Convivían 12/16/18/24/28 px. Tokens `--radius-sm/md/lg` (12/16/24) y los componentes de styles.css armonizados (kpi 18→16, modal 28→24, tablas 18→16).

**Ruido de encuadre.** Cada tarjeta llevaba triple marco: borde dorado + lavado interior + grano al 18 %. El grano baja a 12 % — la textura se percibe, deja de competir — y la sombra del botón primario se atempera (0.28→0.24).

**Higiene tipográfica del copy visible.** La navegación del admin decía "Campanas" (campanas de iglesia, no campañas), "Estadisticas", "Configuracion"; el dashboard decía "Ordenes", "Iniciar sesion", "Aun no tienes ordenes". En un producto que se vende como premium, los acentos ausentes son el equivalente a una costura torcida. Corregidos en labels de navegación, títulos de vista, subtítulos y encabezados visibles (los ids internos no cambian).

## 3. Verificación

Capturas después del cambio (landing hero, tienda con sesión, Volumen & Rangos, admin Pedidos): la jerarquía respira, "RANGO ACTUAL" es dorado, los acentos están, y no hay regresiones de layout. `ng build` de producción limpio.

## 4. Señales que quedan abiertas (para una siguiente pasada de diseño)

1. Los aros del stepper y varios controles solo-icono siguen dependiendo del CDN de Font Awesome: con el CDN caído quedan círculos vacíos (ya documentado en 09/10; la solución de fondo es empaquetar los iconos).
2. Las sombras arbitrarias dentro de templates (`shadow-[0_28px_80px…]` del héroe de tienda) aún no usan los tokens de elevación; migrarlas cuando se toquen esos templates.
3. El sub-header "Volver a comprar"/"Todos los productos" usa `font-bold` sans sobre serif de secciones — aceptable como jerarquía de tercer nivel, pero si se quiere una voz única, definir un estilo `h3` utilitario.
