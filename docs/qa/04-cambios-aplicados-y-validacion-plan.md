# Finding'U — Validación contra el Plan (abril 2026) y Cambios Aplicados

> **Propósito:** Documentar (a) la validación de los documentos QA contra el documento fuente
> `docs/findingu_plan_completo25.04.26.pdf`, y (b) los cambios de código aplicados para alinear
> la implementación con el plan, corregir bugs y construir faltantes.
>
> **Fecha:** Junio 2026 · **Rama:** `feat/plan-abril-2026-alineacion`

---

## 1. Validación de los documentos QA

Se verificaron afirmaciones clave de los 3 documentos QA contra el código real y contra el PDF
del plan. **Los documentos son en su mayoría precisos.** Correcciones detectadas:

| Documento | Afirmación previa | Realidad verificada |
|---|---|---|
| `03` H4 (carrito fantasma) | 🐞 Bug activo | El alias `leaderId` **nunca** se borra en el código (solo se elimina `cart-items` y la clave de sesión). El carrito calcula `subtotal`/`total` con *getters* puros sobre `cartItems` (no hay acumulador que genere "costo fantasma"). **No reproducible en el código actual**; requiere regresión E2E para cerrar. |
| `02`/`03` REP-09 | "No hay export dedicado de comisiones" | **Sí existe** un export de comisiones (`comisiones-{mes}.xlsx`) con hojas *Resumen* y *Desglose por árbol* (`admin.component.ts` `_buildAndDownloadCommissionsReport`). |
| `01` §12.7 / `03` H1 | "config 2–3 niveles de comisión" | Confirmado: era cierto **antes** de este cambio. Ahora la config trae las **5 generaciones** del plan. |

---

## 2. Parámetros exactos del plan (fuente: PDF abril 2026)

Extraídos del PDF y usados como fuente de verdad para la configuración:

- **1 PC ≈ $50 MXN** (`$2,950` paquete = `59 PC`).
- **PC = PC oficiales × (1 − %descuento)** (proporcional al neto pagado).
- **Activación mensual:** $1,000 MXN netos = **20 PC**.
- **Escalera de descuentos (MPN acumulado del mes):** `$0–999 → 0%` · `$1,000–1,999 → 10%` ·
  `$2,000–2,999 → 20%` · `$3,000–5,999 → 30%` · `$6,000+ → 40%`. El nivel se determina con
  *acumulado previo + compra actual* y aplica a toda la compra (sin retroactividad).
- **Comisiones por generación (tope 24%):** Gen1 10% · Gen2 5% · Gen3 4% · Gen4 3% · Gen5 2%.
- **Desbloqueo:** Gen1 activo · Gen2 2 directos activos · Gen3 80 PC + 3 directos + 2 líneas (300 PC) ·
  Gen4 120 PC + 4 directos + 3 líneas (450 PC) · Gen5 160 PC + 5 directos + 3 líneas (750 PC).
- **Compresión dinámica:** salta posiciones no calificadas y paga al siguiente ascendente calificado.
- **Rangos:** Bronce (60 PC / 4,500 VG) · Plata (90 / 9,000) · Oro (140 / 15,000) ·
  Platino (200 / 21,000) · Diamante (280 / 25,000), con líneas y PC por línea.
- **Bono Inicio Rápido:** 600 PC grupales en 30 días → $5,000 (una vez).
- **Bono mensual por rango (desde 4º mes consecutivo):** $500 / $1,500 / $3,000 / $6,000 / $10,000.
- **Premios físicos por sostenimiento** (una vez por rango).
- **Catálogo (13 productos) y PC oficiales:** ver §5.

---

## 3. Cambios de código aplicados

### Backend (`Micro-lambda-GMF/python`)

1. **`commissions_lambda.py` — `_default_app_config`** reescrita al plan:
   - `activationNetMin = 20` (PC; equivale a $1,000 netos).
   - `discountTiers` = escalera 0/10/20/30/40 por MPN (MXN).
   - `commissionLevels` = 5 generaciones con requisitos de desbloqueo
     (`reqActiveDirects`, `reqPersonalPC`, `reqLines`, `reqPCPerLine`).
   - `rankThresholds` = Bronce/Plata/Oro/Platino/Diamante con `vpMin`, `vgMin`, `minLines`,
     `pcMinPerLine`, `requiredLeaders`, `monthlyBonus`, `annualBonus`.
   - `rules` = Bono Inicio Rápido (600 PC/30d/$5,000), bonos mensuales por rango (4º mes),
     premios físicos por rango.
   - `cutRule = "dynamic_compression"`.
2. **`commissions_lambda.py` — `MAX_COMMISSION_LEVELS = 5`** (antes 3).
3. **`commissions_lambda.py` — `handle_apply_rewards`** reescrita con **compresión dinámica**:
   recorre toda la cadena ascendente; cada generación la cobra el siguiente ascendente que
   **califique** (activo + directos + PC + líneas); a los no calificados se les registra fila
   `blocked` informativa y se brinca la posición. Helpers nuevos: `_is_active`,
   `_count_active_directs`, `_count_qualifying_lines`, `_generation_qualified`.
4. **`order_lambda.py` — `_calculate_totals`** ahora resuelve el descuento desde `discountTiers`
   usando *MPN acumulado del mes + compra actual* (helper `_resolve_discount_rate`). Se eliminó la
   regla *hardcoded* `gross >= 3600 → 30%`. `MAX_COMMISSION_LEVELS = 5`.
5. **`dashboard_lambda.py` — `_get_product_summary`** ahora incluye `vpPoints` en el payload de
   producto (para mostrar PC en el front).

**Validación de cálculo (pruebas locales, sin AWS):**
- Compresión: red `A1..A6` con A2 inactivo → A1 gen1 ($200), A3 gen2 ($100), A4 gen3 ($80),
  A5 gen4 ($60), A6 gen5 ($40). Total **$480 = 24%** de $2,000. ✅
- Descuento: compra $2,950 sin previo → **20% / $2,360**; previo $1,500 + $1,000 → **20%**;
  previo $2,400 + $900 → **30%**; invitado → **0%**. Coincide con los ejemplos del PDF. ✅

### Frontend (`gamificacion-multinivel-f/src/app`)

6. **PC por producto (H16 / PV):** `ui-product-card` muestra "X PC" y "Y PC netos" (según
   descuento vigente). Se añadió `vpPoints` a `ProductCardModel` y a `DashboardProduct`, input
   `discountRate`, y se mapea `vpPoints` en `normalizeDashboardProduct`. La **tienda** (grid +
   hero) y el **dashboard** muestran el badge de PC.
7. **Reportes XLSX (H11):** helper `buildSheet(rows, headers)` que **siempre** emite encabezados
   (usa `aoa_to_sheet([headers])` si no hay datos). Aplicado a todas las hojas de Pedidos,
   Clientes, Productos, Stocks, Reporte mensual y Comisiones.
8. **Aviso de privacidad (H19):** nuevo `PrivacyNoticeComponent` (modal de primer acceso, una vez
   por `localStorage`), montado en `app.html`. Sin cookies ni analítica.
9. **Carrusel del home en landing (H17):** carrusel de **2 posiciones** (Tienda / Conoce el
   sistema) en modo sin patrocinador, con controles e indicadores.

**Build:** `ng build` (development) **OK** tras todos los cambios.

---

## 4. Segunda iteración (pendientes resueltos)

6. **Admin: migración de esquema de comisiones/rangos (✅).**
   - Modelos `CommissionLevel` (+`gen`, `reqActiveDirects`, `reqPersonalPC`, `reqLines`,
     `reqPCPerLine`) y `RankThreshold` (+`vpMin`, `minLines`, `pcMinPerLine`, `requiredLeaders`,
     `monthlyBonus`, `annualBonus`).
   - Editor admin: campos nuevos por generación y por rango; opción `Compresión dinámica`.
   - Preview de comisiones (`_buildAndDownloadCommissionsReport`) reescrito al nuevo gating
     (directos activos, PC personales, líneas calificadas) usando `mxnPerVp` y la activación.
   - Defaults de fallback (`getDefaultBusinessConfig`, `mock-api`) alineados al plan abril 2026.
   - Tabla de comisiones del **landing** ahora muestra Generación / Comisión / Directos / PC / Líneas.
7. **Gating de rango completo (✅).** `_compute_rank` (commissions) exige `vgMin` + `vpMin` +
   líneas calificadas + **`requiredLeaders`** (N líderes del rango inferior en la red, evaluado
   recursivamente con memoización y guard de ciclos). Verificado: Plata exige 2 Bronces; Oro exige
   2 Platas; al perder un líder, el rango cae correctamente. `_get_rank_dash` (dashboard) exige
   además `vpMin`.
8. **Seed de PC de los 13 productos (✅).** `seed/product_pc_seed.json` (tabla oficial §5) y
   `seed/seed_product_pc.py` (idempotente, `--apply`, empareja por nombre normalizado; verificado
   13/13). Ejecutar con credenciales AWS para poblar `vpPoints` en DynamoDB.
9. **H7 — Cupones / códigos de descuento (✅ backend + checkout).**
   - Backend (`order_lambda`): entidad `COUPON`, `POST /coupons/validate` (público),
     `GET/POST /coupons` y `DELETE /coupons/{code}` (admin), contador de redenciones.
   - Aplicación en la orden: el cupón reduce el **neto pagado** (`netTotal`), por lo que PC y
     comisiones lo reflejan — consistente con §2 ("no se acumula volumen sobre dinero no recibido").
   - Frontend: `ApiService.validateCoupon` (real + mock) y campo de cupón en el checkout del carrito.
   - OpenAPI: rutas `/coupons*` añadidas.
   - Admin: nueva pantalla **Cupones** (vista `coupons`, privilegio `config_manage`) con
     formulario de alta/edición (código, tipo %/fijo, valor, subtotal mínimo, usos máximos,
     vigencia, activo) y tabla con editar/desactivar. Métodos `listCoupons/saveCoupon/deleteCoupon`
     en `ApiService` (real + mock). Enlace en sidebar y barra móvil.

## 5bis. Trabajo restante

| Tema | Estado | Nota |
|---|---|---|
| Carga real de `vpPoints` en DynamoDB | ⚠️ Datos | Ejecutar `seed/seed_product_pc.py --apply` en el entorno. |
| H4 — Regresión carrito | ✅ Código sano | Ejecutar E2E-CART-03/04/05 contra el build. |

> **Nota de rendimiento:** el gating recursivo de `requiredLeaders` calcula el rango de la
> descendencia (con `_calc_vg` por nodo). Se memoiza por evaluación; en redes muy grandes puede
> ser costoso. Se ejecuta de forma asíncrona en la evaluación de bonos, no en el camino de pago.

---

## 5. Catálogo y PC oficiales (fuente PDF §1)

| Producto | Precio | PC |
|---|---|---|
| Finding Pro 500g (Proteína) | $800 | 15 |
| Klinhart (Omega 3) | $480 | 10 |
| Longevit (Antioxidantes) | $390 | 7 |
| Boom!! (Complejo B) | $420 | 8 |
| Naplus (Sodio) | $280 | 6 |
| Glu-10 (Ác. Alfa Lipoico) | $630 | 13 |
| BHB Ácido (Hidroxibutirato) | $630 | 13 |
| Biotina | $400 | 8 |
| Keto Elektrolyte Fusion | $750 | 15 |
| CRT-1200 (Carnitina) | $550 | 10 |
| Colágeno Hidrolizado | $700 | 13 |
| Creatina Monohidratada | $650 | 9 |
| Gel Reductivo | $400 | 6 |

> Paquete básico (Longevit+Boom+Klinhart+Keto+Naplus+Glu-10) = **$2,950 / 59 PC**.
