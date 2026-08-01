# Historias de Usuario — Dashboard del Asociado (gamificación / red / comisiones)

> **Propósito:** HU de ingeniería inversa del dominio *Dashboard del Asociado* de Finding'U,
> derivadas de comportamiento **real** verificado en código. Base para priorizar/diseñar
> pruebas E2E y negociar alcance con el cliente.
> **Fecha:** 2026-08-01
> **Método:** lectura directa de `handler.py` (backend monolito, probablemente el desplegado —
> ver `docs/backend-architecture.md` §2), `user-dashboard.component.ts`,
> `goal-control.service.ts`, `landing.component.ts`, `real-api.service.ts` y
> `mock-api.service.ts`, contrastado contra `docs/qa/01`, `docs/qa/02` y
> `docs/backend-architecture.md`. Donde el código difiere de `qa/01`/`02` (mayo 2026) se
> documenta el comportamiento **actual** y se anota la discrepancia.
> **Leyenda:** HU normales = respaldadas por `handler.py`. **[MOCK-ONLY — sin backend real]** =
> datos que el frontend renderiza sin soporte en `handler.py` (0 ocurrencias de `rank`, `vp`,
> `vg`, `honorBoard`, `bonuses` por grep sobre el archivo completo) — solo viven en
> `MockApiService`. **No deben entrar a regresión E2E contra el API real.**

## Resumen

| # | Título | Prioridad | Cobertura E2E |
|---|---|---|---|
| HU-DASH-01 | Metas gamificadas del mes (8 metas dinámicas) | Alta | E2E-DASH-04 |
| HU-DASH-02 | Activación mensual y niveles de descuento | Crítica | E2E-DASH-02, E2E-COMP-03/05 |
| HU-DASH-03 | Vista previa del carrito en progreso de metas | Media | SIN COBERTURA EN MATRIZ |
| HU-DASH-04 | Metas de invitar/activar red | Alta | E2E-REF-01, E2E-DASH-04 |
| HU-DASH-05 | Árbol de red multinivel y estado de miembros | Alta | E2E-DASH-05 |
| HU-DASH-06 | Enlace de referido propio | Crítica | E2E-REF-01, E2E-REF-13 |
| HU-DASH-07 | Ledger de comisiones del mes | Alta | E2E-DASH-12 |
| HU-DASH-08 | Bloqueo de comisiones por ancestro inactivo | Alta | E2E-COMP-04 (parcial) |
| HU-DASH-09 | Registro/actualización de CLABE | Alta | E2E-PROF-02, E2E-PROF-03 |
| HU-DASH-10 | Solicitud de retiro de comisiones | Alta | E2E-DASH-13, E2E-DASH-14 |
| HU-DASH-11 | Notificaciones del portal | Media | E2E-NOTI-01, E2E-NOTI-02 |
| HU-DASH-12 | Compartir en redes con enlace de referido | Media | E2E-DASH-10 |
| HU-DASH-13 | Contacto del patrocinador (correo/WhatsApp) | Alta | E2E-DASH-15, E2E-DASH-16 |
| HU-DASH-14 | Historial de órdenes paginado y expandible | Media | E2E-DASH-17 |
| HU-DASH-15 | Vista de invitado sin sesión | Media | E2E-DASH-18 |
| HU-DASH-16 [MOCK-ONLY] | KPIs de VP/VG y rango de liderazgo | — | NO APLICA |
| HU-DASH-17 [MOCK-ONLY] | Cuadro de Honor (Top 10) | — | NO APLICA |
| HU-DASH-18 [MOCK-ONLY] | Bonos por rango / inicio rápido | — | NO APLICA |

Total: **18 HU** (15 reales, 3 MOCK-ONLY) · **1 sin cobertura en matriz** · **3 MOCK-ONLY**.

---

### HU-DASH-01 — Metas gamificadas del mes
**Como** asociado **quiero** ver mis metas del mes con barra de progreso **para** saber qué me
falta para desbloquear beneficios.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que abro el dashboard, entonces veo **8 metas** calculadas en servidor: `active`,
  `discount_1/2/3`, `invite`, `network_one_active`, `direct_all_active`,
  `network_member_invited`.
- Dado el cálculo, entonces la primera meta no lograda y no bloqueada se marca `primary=true`;
  el resto de no logradas, `secondary=true`.
- Dado que no tengo directos, `direct_all_active` se marca `locked=true` (subtítulo "Aún no
  tienes miembros directos") y queda excluida de ser `primary`.
- Las metas se recalculan y **persisten en `CUSTOMER`** en cada carga (no son estáticas).
**Fuente (código):** `handler.py:459-589` (`_build_goals`); `user-dashboard.component.ts:275`
**Cobertura E2E:** E2E-DASH-04 (no hay caso por cada una de las 8 metas — ampliar matriz).

---

### HU-DASH-02 — Activación mensual y niveles de descuento
**Como** asociado **quiero** ver mi consumo neto del mes y cuánto falta para activarme o subir
de nivel de descuento **para** planear mis compras.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Dado `activationNetMin` (default $2,500 MXN), cuando mi `netVolume` del mes lo alcanza,
  entonces `active` se marca lograda.
- Dado los tramos por defecto ($3,600–$8,000→30%, $8,001–$12,000→40%, $12,001+→50%), cuando mi
  consumo neto cruza cada umbral, `discount_1/2/3` se marcan logradas en orden.
- El descuento efectivo es `max(discountRate persistido, tasa por tramo)` — nunca baja de un
  valor ya otorgado.
- **Discrepancia:** el dashboard opera en **pesos (MXN)**, no en "Puntos" como sugieren
  E2E-DASH-01/02 (hallazgo del cliente) — no hay unidad de puntos en el motor real de metas.
**Fuente (código):** `handler.py:70-79`, `460-518` (`_build_goals`)
**Cobertura E2E:** E2E-DASH-02, E2E-COMP-03, E2E-COMP-05.

---

### HU-DASH-03 — Vista previa del carrito en progreso de metas
**Como** asociado **quiero** ver cómo impacta mi carrito actual en mis metas de consumo antes de
pagar **para** decidir si agrego más productos.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado un carrito con productos, las metas de consumo (`active`, `discount_1/2/3` — no las de
  conteo ni las con `unit==='vp'`) muestran un campo `cart` con el subtotal superpuesto a `base`.
- Dado que el carrito cambia, el servicio solo recompone/emite si cambian `key`, `base`, `cart`,
  `target`, `achieved` o `locked`.
- Cálculo **100% frontend**; el `cart` nunca se envía ni persiste hasta pagar la orden.
**Fuente (código):** `goal-control.service.ts:19-42`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ.

---

### HU-DASH-04 — Metas de invitar y activar red
**Como** asociado **quiero** que se reconozca cuando invito gente o mi red activa miembros
**para** avanzar en mis metas de crecimiento.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un nuevo directo registrado este mes con mi `customerId` como `leaderId`, `invite` se
  marca lograda.
- Dado que cualquier miembro de mi árbol (no solo directos) se activa este mes,
  `network_one_active` se marca lograda.
- Dado que cualquier miembro de mi árbol agrega un nuevo miembro este mes,
  `network_member_invited` se marca lograda.
**Fuente (código):** `handler.py:414-457`
**Cobertura E2E:** E2E-REF-01, E2E-DASH-04 (falta caso específico de "red que replica").

---

### HU-DASH-05 — Árbol de red multinivel y estado de miembros
**Como** asociado **quiero** ver mi red por niveles con gasto mensual y estado de cada miembro
**para** saber a quién impulsar.
**Prioridad:** Alta
**Criterios de aceptación:**
- El árbol se arma a partir de `leaderId` de cada `CUSTOMER`, se poda a `MAX_NETWORK_DEPTH`
  niveles, y los hijos se ordenan por `monthSpend` descendente.
- Miembro con `netVolume ≥ activationNetMin` → "Activa"; `0 < netVolume < umbral` → "En
  progreso"; `netVolume = 0` → "Inactiva".
- Solo se listan los primeros **30 miembros** aplanados (`max_rows=30`), sin paginación
  adicional.
- Con algún L1 "Inactiva", el dashboard expone `hasInactiveIntermediate` para advertir sobre
  bloqueos de comisión.
**Fuente (código):** `handler.py:279-393`; `user-dashboard.component.ts:350`, `1408-1410`
**Cobertura E2E:** E2E-DASH-05.

---

### HU-DASH-06 — Enlace de referido propio
**Como** asociado **quiero** obtener mi enlace de invitación **para** compartirlo y crecer mi
red.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Con sesión activa, el enlace es `{origin}/#/landing/{userCode}`, donde `userCode` es
  literalmente mi `customerId` (no un alias amigable).
- Como invitado (sin sesión), el enlace es cadena vacía.
- Al abrir `/landing/:idSponsor`, el valor se persiste en `localStorage['leaderId']` para usarlo
  al registrarse.
- **Discrepancia:** `docs/qa/01` (3.7) documenta un código tipo `{Nombre}-{Iniciales}` — esa
  lógica vive en `Micro-lambda-GMF/python/auth_utils.py` (split, no confirmado en producción).
  El monolito, que sirve `/user-dashboard`, expone el `customerId` crudo como código.
**Fuente (código):** `user-dashboard.component.ts:592-611`; `landing.component.ts:123-128`;
`handler.py:6179-6194`
**Cobertura E2E:** E2E-REF-01, E2E-REF-13.

---

### HU-DASH-07 — Ledger de comisiones del mes
**Como** asociado **quiero** ver el detalle de mis comisiones pendientes, confirmadas y
bloqueadas **para** entender cuánto he ganado y por qué.
**Prioridad:** Alta
**Criterios de aceptación:**
- Al abrir comisiones, veo `totalPending`, `totalConfirmed`, `totalBlocked` y el `ledger`
  completo del mes (`COMMISSION_MONTH` por beneficiario+mes).
- `prevStatus` del mes anterior: `no_moves` (sin confirmado), `paid` (hay comprobante
  `COMMISSION_RECEIPT`), o `pending` (confirmado sin comprobante).
- Al expandir el ledger, veo fecha, nivel y estado de cada comisión individual.
**Fuente (código):** `handler.py:6127-6165`, `2131-2163`; `user-dashboard.component.ts:1722`
**Cobertura E2E:** E2E-DASH-12.

---

### HU-DASH-08 — Bloqueo de comisiones por ancestro inactivo
**Como** asociado **quiero** entender por qué una comisión está bloqueada **para** saber qué
acción tomar.
**Prioridad:** Alta
**Criterios de aceptación:**
- Si un ancestro de mi cadena ascendente no está activo ese mes, la comisión queda `blocked`
  (`cutRule: "hard_cut_no_pass"` — **no** se traspasa al siguiente calificado).
- Cuando el ancestro se reactiva, las comisiones bloqueadas de ese cliente se desbloquean.
- Con comisiones bloqueadas, el tooltip informativo explica el motivo (`toggleBlockedTooltip`).
**Fuente (código):** `handler.py:2178`, `2202`; `user-dashboard.component.ts:1726`
**Cobertura E2E:** E2E-COMP-04 (ampliar con caso de tooltip de bloqueo en dashboard).

---

### HU-DASH-09 — Registro/actualización de CLABE interbancaria
**Como** asociado **quiero** registrar mi CLABE **para** poder cobrar mis comisiones.
**Prioridad:** Alta
**Criterios de aceptación:**
- El frontend exige 18 dígitos numéricos (`/^\d{18}$/`) antes de confirmar el cambio.
- El backend (`PATCH /customers/clabe`) también exige 18 dígitos numéricos; si falla, responde
  **HTTP 200** con `Error: "BadRequest"` (no 4xx) y mensaje "CLABE invalida".
- El dashboard solo expone `clabeLast4`, nunca la CLABE completa.
**Fuente (código):** `user-dashboard.component.ts:1703-1715`; `handler.py:5409-5431`
**Cobertura E2E:** E2E-PROF-02, E2E-PROF-03.

---

### HU-DASH-10 — Solicitud de retiro de comisiones
**Como** asociado **quiero** solicitar el pago de mis comisiones confirmadas **para** recibir mi
dinero.
**Prioridad:** Alta
**Criterios de aceptación:**
- Sin CLABE guardada ni capturada, la solicitud se bloquea ("Ingresa tu CLABE interbancaria");
  el backend replica la validación ("CLABE es obligatoria").
- Con comisión confirmada del mes = $0, el backend responde "No hay comisiones por cobrar" y no
  crea la solicitud.
- Al solicitar con éxito, se crea `COMMISSION_REQUEST` (`status="requested"`, monto =
  `totalConfirmed`, `clabeLast4`); el dashboard se recarga (`force: true`).
- **Discrepancia interna:** `_request_commission_payout` valida CLABE con ≥10 caracteres,
  mientras `_update_customer_clabe` exige exactamente 18 dígitos — una CLABE de 10-17 dígitos
  podría colarse por el flujo de retiro sin pasar la validación estricta del perfil.
**Fuente (código):** `handler.py:5364-5407`; `user-dashboard.component.ts:1813-1843`
**Cobertura E2E:** E2E-DASH-13, E2E-DASH-14 (agregar borde de longitud de CLABE entre ambos
endpoints).

---

### HU-DASH-11 — Notificaciones del portal
**Como** asociado **quiero** ver avisos vigentes y marcarlos leídos **para** enterarme de
novedades.
**Prioridad:** Media
**Criterios de aceptación:**
- Notificaciones `active=true` cuyo rango `startAt`–`endAt` cubre "ahora" se listan ordenadas
  por `startAt`/`createdAt` descendente.
- Con `startAt` futuro o `endAt` pasado, la notificación no aparece.
- Marcar como leída es idempotente: repetir la acción responde `ok:true` sin duplicar el
  registro.
**Fuente (código):** `handler.py:5570-5597`, `5689-5720`; `user-dashboard.component.ts:465-475`
**Cobertura E2E:** E2E-NOTI-01, E2E-NOTI-02.

---

### HU-DASH-12 — Compartir en redes con enlace de referido
**Como** asociado **quiero** copiar un link + copy listo para publicar **para** promocionar mi
enlace en redes.
**Prioridad:** Media
**Criterios de aceptación:**
- Al elegir canal (WhatsApp/Instagram/Facebook), se genera un texto (`generateTemplate`) con mi
  `referralLink` embebido.
- Al copiar, el contenido se envía al portapapeles con toast de confirmación.
- **Código muerto:** la personalización de copy por canal (wa.me, Facebook Sharer, caption IG)
  está **comentada**; hoy todos los canales copian el mismo contenido — el canal solo cambia el
  formato de imagen sugerido (`story`/`feed`).
**Fuente (código):** `user-dashboard.component.ts:1449-1499`, `1515`
**Cobertura E2E:** E2E-DASH-10 (agregar caso: copy idéntico entre canales).

---

### HU-DASH-13 — Contacto del patrocinador (correo/WhatsApp)
**Como** asociado **quiero** ver y contactar a mi patrocinador **para** resolver dudas sobre mi
red.
**Prioridad:** Alta
**Criterios de aceptación:**
- Con patrocinador asignado, veo nombre/correo/WhatsApp; sin uno, se asigna un patrocinador por
  defecto (`isDefault=true`, "Soporte FindingU asignado").
- Al hacer clic en el correo, en el **mismo evento** se dispara `mailto:` **y** se copia el
  correo al portapapeles, de modo que aunque el cliente de correo no abra, el correo ya se copió.
- Sin correo del patrocinador, el `href` cae a `mailto:contacto@findingu.com.mx`.
**Fuente (código):** `user-dashboard.component.html:477-483`; `user-dashboard.component.ts:477-494`
**Cobertura E2E:** E2E-DASH-15, E2E-DASH-16.

---

### HU-DASH-14 — Historial de órdenes paginado y expandible
**Como** asociado **quiero** revisar mis pedidos anteriores con detalle **para** dar seguimiento
a mis compras.
**Prioridad:** Media
**Criterios de aceptación:**
- Las órdenes se cargan de forma paginada.
- Al hacer clic en una orden, se expande el detalle de línea sin cambiar de pantalla
  (`toggleOrderDetail` por `orderId`).
**Fuente (código):** `user-dashboard.component.ts:116`, `1187`, `1734-1736`
**Cobertura E2E:** E2E-DASH-17.

---

### HU-DASH-15 — Vista de invitado sin sesión
**Como** visitante sin cuenta **quiero** ver una versión reducida del dashboard con CTAs **para**
decidir registrarme.
**Prioridad:** Media
**Criterios de aceptación:**
- Sin sesión, `isGuest=true` y el menú lateral solo muestra "Tienda" (se ocultan
  Red/Links/Órdenes/Comisiones/Cuadro de Honor/Perfil).
- Como invitado, el backend no arma `goals`/`commissions`, solo catálogo.
**Fuente (código):** `user-dashboard.component.ts:233-263`; `handler.py:6166-6168`
**Cobertura E2E:** E2E-DASH-18.

---

### HU-DASH-16 [MOCK-ONLY — sin backend real] — KPIs de VP/VG y rango de liderazgo
**Como** asociado **quiero** ver mis puntos de volumen y mi rango **para** medir mi desempeño en
el plan de compensación.
**Prioridad:** — (no priorizable sin decisión de negocio)
**Criterios de aceptación (UI actual, no verificados contra backend real):**
- El dashboard lee `vpPoints`/`vgPoints`/`currentRank` de `data.vp`/`.vg`/`.rank`.
- **Verificado:** el payload real de `_get_user_dashboard` (`handler.py:6179-6193`) **no incluye
  `vp`, `vg` ni `rank`** (0 resultados de grep sobre el archivo completo). Contra la API real
  estos campos llegan `undefined`.
- Solo `MockApiService` (líneas `720-722`, `973-975`) puebla estos valores en memoria.
**Fuente (código):** `user-dashboard.component.ts:358-368`; `mock-api.service.ts:720-722`,
`973-975`; `docs/backend-architecture.md` §10
**Cobertura E2E:** NO APLICA a API real; si se prueba, documentarlo como prueba de UI contra
`MockApiService`, no de integración.

---

### HU-DASH-17 [MOCK-ONLY — sin backend real] — Cuadro de Honor (Top 10)
**Como** asociado **quiero** ver el ranking Top 10 por VG y VP, con mi posición y variación
**para** sentirme motivado a competir.
**Prioridad:** — (no priorizable sin decisión de negocio)
**Criterios de aceptación (UI actual, no verificados contra backend real):**
- El frontend llama `GET /dashboard/honor-board` y espera `honorBoard` en `/user-dashboard`.
- **Verificado:** `handler.py` no tiene ninguna ruta ni función con "honor" (0 resultados) — el
  endpoint **no existe** en el router del monolito; una llamada real devolvería 404.
- El modal automático "entraste al Top 10" solo puede dispararse con datos mock.
**Fuente (código):** `user-dashboard.component.ts:370-433`, `1133-1136`;
`real-api.service.ts:450`; `mock-api.service.ts:972`, `2258-2279`
**Cobertura E2E:** NO APLICA — excluir de regresión E2E contra API real.

---

### HU-DASH-18 [MOCK-ONLY — sin backend real] — Bonos por rango / inicio rápido
**Como** asociado **quiero** ver los bonos ganados por rango o inicio rápido **para** saber
cuánto se me pagará además de comisiones.
**Prioridad:** — (no priorizable sin decisión de negocio)
**Criterios de aceptación (UI actual, no verificados contra backend real):**
- El dashboard lee `data.bonuses` y renderiza tarjetas con `rewardType`/`rewardAmount`/`status`.
- **Verificado:** `handler.py` no contiene la clave `"bonuses"` (0 resultados) ni la arma dentro
  de `_get_user_dashboard`. El motor de bonos por rango (`docs/backend-architecture.md` §7) vive
  en el **split** `commissions_lambda.py`, no en el monolito.
- Contra la API real, `bonusAwards` siempre es `[]` (`hasBonuses=false`).
**Fuente (código):** `user-dashboard.component.ts:435-463`; `handler.py:6179-6193`;
`docs/backend-architecture.md` §7, §10
**Cobertura E2E:** NO APLICA — excluir hasta confirmar despliegue del motor de bonos.

---

## Observaciones para QA

1. **"Puntos vs pesos":** E2E-DASH-01/02 de la matriz asumen una unidad "PC/Puntos" en el
   dashboard. El motor real trabaja en **MXN netos** (`netVolume`). Decidir si el hallazgo aplica
   a una unidad de puntos aún inexistente o se reinterpreta como "monto neto acumulado".
2. **Trampa mock-only ampliada:** además de `rank`/`vp`/`vg`/`honorBoard`
   (`docs/backend-architecture.md` §10), este documento confirma que **`bonuses`** corre la misma
   suerte en el monolito. Excluir HU-DASH-16/17/18 de la regresión E2E contra API real.
3. **Enlace de referido "amigable":** confirmar con negocio si `/#/landing/{customerId}`
   (comportamiento real) es aceptable o si se requiere el generador `{Nombre}-{Iniciales}` que
   solo vive en el split.
4. **CLABE con dos validaciones distintas:** unificar `_update_customer_clabe` (18 dígitos) y
   `_request_commission_payout` (≥10 caracteres) antes de certificar el flujo de retiro.
5. **Código muerto en "compartir":** si el negocio espera copys distintos por canal social, es
   una regresión pendiente de corregir en `user-dashboard.component.ts:1482-1498`, no solo de
   probar.
6. **Backend desplegado sin confirmar:** todas las HU reales asumen que `handler.py` (monolito)
   es el backend de producción (`docs/backend-architecture.md` §2). Si se confirma que el split
   es el desplegado, reverificar el payload real de `/customers/dashboard` o `/catalog` (que
   documentadamente reemplazan a `/user-dashboard`) antes de mover HU-DASH-16/17/18 fuera de
   MOCK-ONLY.
