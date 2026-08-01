# Cobertura E2E con Playwright y hallazgos — 2026-08-01

## 1. Contexto y método

Ingeniería inversa del comportamiento real (código frontend + backend) → **92 Historias de Usuario** en `docs/hu/01-04` → **suite E2E Playwright** en `gamificacion-multinivel-f/e2e/`, validada en verde contra la app real corriendo en local.

Estrategia: **modo mocked por defecto** — todas las pruebas interceptan el API (`page.route`) con payloads fieles al contrato de `real-api.service.ts`. Ninguna prueba escribe en AWS. Los tests marcados `@live` (opt-in con `E2E_LIVE=1`) son las únicas excepciones y solo hacen lecturas contra el API dev.

## 2. Validación del ambiente AWS (2026-08-01)

Cuenta `049945345964`, usuario IAM `pytagoraz_a`, región `us-east-1`:

- API **dev** `ge2omdgk33` (la de `environment.ts`) → **microlambdas** `Multinivel-*` (Auth, order, catalog, costumer, Dashboard, Comissions, inventory, shiping).
- API **prod** `m85v7secp8` (la de `environment.prod.ts`) → **monolito** Lambda `Multinivel` (`handler.py`).
- Tabla DynamoDB `multinivel` existente.

⚠️ **Riesgo mayor detectado**: el monolito (producción) difiere del split (dev) en auth — el monolito no implementa rutas `/auth/*`, no verifica email realmente y emite token hardcodeado `"demo-token"` (ver `docs/hu/01`, Observaciones). Lo que pasa en dev no garantiza lo mismo en prod hasta que el split se promueva.

## 3. Inventario de la suite

| Archivo | Tests | Estado |
|---|---|---|
| `e2e/smoke.spec.ts` | 4 | ✅ verde |
| `e2e/auth.spec.ts` | 21 | ✅ verde |
| `e2e/registro-perfil.spec.ts` | 26 | ✅ verde |
| `e2e/tienda.spec.ts` | 12 | ✅ verde |
| `e2e/carrito-checkout.spec.ts` | 29 | 25 verdes + 4 `fixme` (bugs) |
| `e2e/ordenes.spec.ts` | 22 | 18 verdes + 4 `fixme` (bugs) |
| `e2e/dashboard-metas.spec.ts` | 7 | ✅ verde |
| `e2e/dashboard-red.spec.ts` | 12 | 10 verdes + 2 `fixme` (bugs) |
| `e2e/dashboard-comisiones.spec.ts` | 15 | 11 verdes + 4 `fixme` (bugs) |
| `e2e/admin-acceso.spec.ts` | 6 | ✅ verde |
| `e2e/admin-pedidos.spec.ts` | 9 | ✅ verde |
| `e2e/admin-clientes.spec.ts` | 6 | ✅ verde |
| `e2e/admin-catalogo-stocks.spec.ts` | 9 | ✅ verde |
| `e2e/admin-operacion.spec.ts` | 15 | ✅ verde |
| **Total** | **196** | **182 verdes, 14 `test.fixme` (bugs documentados), 0 rotos** |

Soporte: `e2e/support/fixtures.ts` (sesión, privacidad, mocks), `e2e/support/dashboard-mocks.ts`, `e2e/support/admin-mocks.ts`.

Cobertura HU: 89/92 con al menos un escenario automatizado; las restantes están documentadas como no automatizables en el pie de cada spec (backend-only como el webhook de Mercado Pago, o sin superficie de UI).

## 4. Cómo ejecutar

```bash
cd gamificacion-multinivel-f
npm run e2e          # suite completa (mocked; levanta ng serve en :4300 si no existe)
npm run e2e:ui       # modo interactivo
npm run e2e:report   # último reporte HTML
E2E_LIVE=1 npx playwright test --grep @live   # smoke opcional contra API dev real
```

Los `test.fixme` se saltan y quedan como marcador: al corregir el bug correspondiente, quitar el `fixme` y el test valida el fix.

## 5. Bugs reales confirmados (por las pruebas o durante su construcción)

**Frontend — visibles para el usuario:**
1. `ui-status-badge`: miembros de red con estado "Inactiva" muestran badge/tono **"Activa"** — el código comprueba la subcadena `'activa'` antes que `'inact'` y `"inactiva".includes("activa") === true`.
2. **Change detection zoneless** (app sin zone.js): callbacks asíncronos (`clipboard.then`, `subscribe`) no re-renderizan. Sin confirmación visual al copiar el enlace de referido, al guardar CLABE (modal no cierra) y el toast "revisa tu correo" del registro de invitado nunca aparece.
3. Orden **reembolsada** se muestra como "Pago pendiente" con botón de pago visible (`order-status` omite `'refunded'` en su lista local de estados).
4. Botón "Pagar con MercadoPago" visible en pedidos **pickup con pago en sucursal**.
5. `order-cancelacion` y `order-devolucion`: si falla la carga de la orden, la página queda **en blanco** (el error se asigna pero ningún template lo renderiza).
6. Foco de validación del checkout roto: `focusFirstMissingDeliveryField()` busca `[name=...]` que solo matchea el host `<ui-form-field>` (no enfocable), nunca el `<input>` real.
7. Productos sugeridos pueden repetir artículos ya presentes en el carrito (el relleno de 3 slots no re-verifica `cartIds`).

**Funcionalidad inalcanzable (código muerto o cableado incompleto):**
8. Solicitud de retiro de comisiones (HU-DASH-10): el modal y el POST existen, pero **ningún botón** del template los invoca.
9. Comisión one-shot 10% por compra de invitado (HU-SHOP-31): el carrito **nunca envía** `referrerAssociateId` en `createOrder()` aunque el `leaderId` esté en localStorage.
10. Gestión de privilegios de cliente desde admin (HU-ADM-08): lógica implementada en `admin.component.ts:3945-3973` sin ningún template asociado.
11. Cuadro de Honor: `UserDashboardControlService.load()` nunca copia `honorBoard` del payload (y `DashboardData` no lo declara).
12. POS con superusuario: `currentOperatorId = Number(userId)` → `NaN` para IDs no numéricos (`admin-001`); el admin por defecto no puede operar POS ni cortes de caja.

**Backend / contrato:**
13. Flujo de devolución: enteramente frontend, **sin ruta backend** en el monolito.
14. Cupones: UI completa (carrito + CRUD admin) con **cero soporte** en el monolito (solo existe en el split `order_lambda.py`).
15. Drift monolito vs split en auth (sección 2): `demo-token`, `/auth/*` ausentes, sin verificación real de email en prod.
16. Menores: `ui-form-field` no propaga `name` al `<input>` (selectores/autofill), `aria-label` en host de `ui-button` no forma parte del nombre accesible (a11y).

**Verificado como NO-bug:** el mismatch `"canceled"`/`"cancelled"` está mitigado por `normalizeOrderStatus()` en `real-api.service.ts` (test de regresión incluido).

## 6. Correcciones a documentación previa

- `docs/qa/02-matriz-pruebas-e2e.md` quedó desactualizada en: E2E-REP-06/09 (el fix de headers XLSX y el reporte de comisiones YA existen) y varios casos AUTH que describen el comportamiento del split, no del monolito.
- `docs/hu/01` marca el Aviso de Privacidad como "funcionalidad ausente": **sí existe** (`PrivacyNoticeComponent`, clave `privacy-notice-accepted-v1`) y bloquea la primera visita.

## 7. Quirks para escribir nuevas pruebas (leer antes de ampliar la suite)

- Hash routing: navegar siempre a `/#/ruta`. Puerto dedicado **4300** (el 4200 suele estar ocupado por otras apps del equipo).
- Sembrar sesión con `seedSession(page, USERS.x)` ANTES de `goto` (incluye aceptar el aviso de privacidad).
- `page.route` es **LIFO**: registrar `blockUnmockedApi` antes de los `mockApi` específicos.
- `ui-form-field` replica atributos en el host: usar `getByRole('textbox', { name })`, nunca `getByPlaceholder`/`[name=...]`.
- `<ui-modal>` host reporta "hidden" aunque el contenido sea visible: asertar sobre el contenido interior.
- Selects de `ui-form-field` con labels que comparten prefijo rompen `getByLabel`: usar `selectByExactLabel` de `e2e/support/admin-mocks.ts`.
