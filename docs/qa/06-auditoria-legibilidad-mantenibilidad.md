# Auditoría de legibilidad y mantenibilidad del backend

> **Alcance:** los 9 módulos Python de `Micro-lambda-GMF/python` (9,890 líneas, 315 funciones).
> **Objetivo:** validar que el código sea legible y mantenible; no cubre rendimiento
> (auditado en `05`) ni una revisión de seguridad exhaustiva, aunque señala lo que apareció.
> **Fecha:** septiembre 2026 · **Rama:** `claude/ultimos-cambios-integrados-fylhiw`

---

## 1. Método

Métricas objetivas extraídas por AST sobre los 9 módulos (longitud de funciones, anidación,
duplicación por similitud de texto, manejo de excepciones, docstrings, anotaciones de tipo,
código sin referencias), más lectura dirigida de los puntos que las métricas señalaron.

## 2. Resumen ejecutivo

| Dimensión | Estado | Resumen |
|---|---|---|
| Organización por módulos | 🟢 Buena | Un lambda por dominio + `core_utils` como capa común; responsabilidades claras |
| Documentación interna | 🟡 Media | Docstrings útiles y comentarios que explican el *porqué*, pero cobertura irregular (inventory 93% · core_utils 34%) |
| **Duplicación** | 🔴 **Crítica** | **~25 funciones casi idénticas** entre `costumer_lambda` y `dashboard_lambda` (hasta 100% de similitud) |
| **Consistencia semántica** | 🔴 **Crítica** | La misma clave de config se lee con defaults **2500 / 50 / 20** y dos unidades distintas (MXN vs PC) |
| Tamaño de funciones | 🟠 Débil | 45 funciones >50 líneas; 19 >100; la mayor tiene 211 |
| Manejo de errores y logging | 🟠 Débil | 62 `except Exception`, 3 desnudos, 4 que tragan el error; logging mezclado (`print(f"[TAG]")` vs JSON estructurado) |
| Pruebas y tooling | 🔴 Ausente | Sin pruebas unitarias del negocio, sin `requirements.txt`, sin linter configurado, sin CI |
| Seguridad accidental | 🔴 Grave | Token de superadmin y usuarios demo con contraseña fija **en el código fuente**; hash de contraseñas SHA-256 sin sal |

**Veredicto: el backend es legible en lo pequeño pero frágil en lo grande.** Las funciones se
entienden una a una (nombres descriptivos, comentarios honestos), pero la duplicación
`costumer`/`dashboard` y los defaults contradictorios hacen que cualquier cambio de negocio
deba aplicarse en 2–3 sitios que nadie sabe que existen, y que dos pantallas puedan calcular
resultados distintos con la misma configuración.

---

## 3. Lo que está bien (y conviene conservar)

- **Separación por dominios**: `auth`, `catalog`, `commissions`, `costumer`, `dashboard`,
  `inventory`, `order`, `shipping` sobre una capa común `core_utils`. La frontera es clara.
- **`core_utils` como única puerta a DynamoDB**: el patrón bucket+REF, el árbol de red, el
  ledger y los índices viven en un solo sitio; los lambdas no improvisan acceso a datos
  (con las excepciones que se listan en M8).
- **Comentarios que explican decisiones**, no sintaxis ("un award de `month_key` nunca se
  crea antes de ese mes", "el alias leaderId nunca se borra…"). Es el estilo correcto.
- **`inventory_lambda`** es el módulo mejor documentado (14/15 docstrings) y sirve de
  referencia interna de estilo.
- Existen **pruebas reproducibles de la capa de datos** (`tools/`: probe de operaciones,
  equivalencia de VG, concurrencia del ledger) — nacidas de la auditoría `05`.

---

## 4. Hallazgos

### M1 · Duplicación masiva entre `costumer_lambda` y `dashboard_lambda` — severidad ALTA

`GET /customers/dashboard` nació como copia de `GET /user-dashboard` (legacy) y hoy **todo el
subsistema de metas/red/correos existe dos veces**, con derivas ya visibles. Medido por
similitud de texto:

| Función | Similitud | Comentario |
|---|---:|---|
| `_goal_email_shell`, `_build_goal_achieved_email` | 100% | Plantillas HTML de correo duplicadas íntegras |
| `_mxn_to_vp_dash`, `_prev_month_key`, `_flatten_tree` | 99–100% | Utilidades puras idénticas |
| `_campaign_payload`, `_get_month_state`, `_active_notifications_for_customer` | 94–96% | |
| `_compute_buy_again_ids`, `_goal_reward_lines` | 91–92% | |
| `_build_goals` (211 y 175 líneas) | 87% | **La lógica de negocio de metas, duplicada y ya divergente** |
| `_notify_goal_achievements`, `_network_members_from_tree`, `_calc_vg_from_tree` | 84–85% | |
| `_get_product_summary`, `_find_effective_sponsor` | 60–63% | Derivadas: una copia evolucionó y la otra no |
| `_get_rank_dash` | 45% | La copia de `dashboard` exige `vpMin` (plan abril 2026); la de `costumer` — **la que ve el usuario en `/customers/dashboard`** — no: pueden mostrar rangos distintos |
| `_is_product_active`, `_pick_product_image` | 97–100% | **Triplicadas** (también en `catalog_lambda`) |

Son **~570 líneas redundantes** solo en copias con >50% de similitud. El costo real no son las
líneas: es que un fix de metas o de rango aplicado en un módulo **no** llega al otro (ya pasó:
`_get_rank_dash` y `_find_effective_sponsor` divergieron).

**Recomendación:** extraer un `dashboard_common.py` (o sección en `core_utils`) con las
utilidades puras y las plantillas de correo; después decidir el destino de `/user-dashboard`
(el frontend ya no lo usa: la tienda migró a `/catalog` en la auditoría 05). Si el endpoint
legacy se elimina, la duplicación cae casi entera por sí sola.

### M2 · La misma clave de configuración con tres defaults y dos unidades — severidad ALTA

`rewards.activationNetMin` se lee en 7 sitios con **tres** valores por defecto:

```
catalog_lambda.py:305      .get("activationNetMin", 50)     # PC
commissions_lambda.py:787  .get("activationNetMin", 20)     # PC (plan abril 2026)
costumer_lambda.py:446     .get("activationNetMin", 2500)   # MXN (semántica vieja)
costumer_lambda.py:548     .get("activationNetMin", 50)
dashboard_lambda.py:217    .get("activationNetMin", 2500)
dashboard_lambda.py:411    .get("activationNetMin", 50)
dashboard_lambda.py:909    .get("activationNetMin", 50)
```

El árbol de red marca "activo" comparando `netVolume` (MXN) contra 2500, mientras el motor de
comisiones compara VP contra 20. Si la config guardada no trae la clave, **la misma persona
aparece activa en una pantalla e inactiva en otra**. Es el hallazgo con más probabilidad de
convertirse en un bug de negocio reportado por un usuario.

**Recomendación:** un solo módulo de acceso a config con defaults centralizados
(`_default_app_config` ya existe en `commissions_lambda` y es la fuente natural — moverlo a
`core_utils` y que todos lean de ahí), y decidir la unidad canónica de `activationNetMin`
documentándola en el propio default.

### M3 · Funciones y ruteadores gigantes — severidad MEDIA

45 funciones superan 50 líneas y 19 superan 100. Las peores:

| Líneas | Función | Problema |
|---:|---|---|
| 211 | `costumer_lambda._build_goals` | 6 metas distintas + reglas de bono + email en un solo cuerpo |
| 199 | `dashboard_lambda.get_user_dashboard` | Carga catálogo + red + metas + comisiones + persiste caché |
| 189 | `costumer_lambda.handle_customer_dashboard` | Ídem, con instrumentación intercalada |
| 187 | `commissions_lambda.lambda_handler` | Ruteo a mano de ~15 rutas con auth inline |
| 167 | `inventory_lambda.lambda_handler` | Ruteo con anidación de 6 niveles |
| 161 | `order_lambda.handle_return_request` | Validación + stock + reembolso + correo en línea |
| 149 | `commissions_lambda._default_app_config` | Aceptable: es un literal de datos, no lógica |

Los 8 `lambda_handler` repiten el mismo patrón artesanal (`segments = path.split("/")`,
cascada de `if segments[0] == …`, permiso inline, 5–6 niveles de anidación). Cada ruta nueva
se inserta "donde quepa" y el orden de los `if` es significativo — fácil de romper sin notar.

**Recomendación:** un mini-ruteador declarativo en `core_utils` — una tabla
`(método, patrón, privilegio, handler)` por lambda — dejaría cada `lambda_handler` en ~20
líneas y haría el privilegio de cada ruta auditable de un vistazo (hoy hay que leer 190
líneas para saber qué exige cada endpoint). Para las funciones de negocio: trocear por meta /
por paso, sin cambiar comportamiento, con las pruebas de `tools/` como red.

### M4 · Credenciales y puertas traseras en el código fuente — severidad ALTA (seguridad)

- `core_utils.py:1396` — `_SUPERADMIN_TOKEN = "demo-token-8d522a140ce34cbc"`: un Bearer fijo
  que otorga rol superadmin, **válido en producción** para cualquiera que lea el repo.
- `auth_utils.py:176-177` — usuarios demo con contraseñas fijas (`admin123`, `cliente123`)
  activos en el flujo de login real.
- `_hash_password` es SHA-256 **sin sal ni factor de trabajo**: las contraseñas son atacables
  por tabla arcoíris si la tabla se filtra.

**Recomendación:** mover el token a variable de entorno (y rotarlo: el actual ya está en el
historial de git), desactivar los usuarios demo salvo bajo un flag de entorno, y migrar el
hash a `bcrypt`/`scrypt` con re-hash transparente en el siguiente login. Amerita tratarse
aparte de la mantenibilidad, con prioridad.

### M5 · Manejo de errores y logging inconsistentes — severidad MEDIA

- **62 `except Exception` + 3 desnudos**; 4 tragan el error con `pass`/`continue` sin dejar
  rastro (p. ej. el `except Exception: pass` al marcar PAID un mes contable). Un fallo de
  DynamoDB y un bug de tipos reciben el mismo tratamiento: silencio.
- **Dos estilos de log conviven**: `print(f"[VOID_COMM_ERROR] {e}")` (53 usos) y
  `print(json.dumps({...}))` estructurado (12 usos, casi todos en `core_utils`). Los tags
  entre corchetes no son consultables en CloudWatch Insights; los JSON sí.
- No hay `logger` con niveles: no se puede subir/bajar verbosidad sin redeploy.

**Recomendación:** helper único `_log(event, **fields)` en `core_utils` (JSON siempre), y
regla de estilo: `except Exception` solo en fronteras (handler HTTP, punto de entrada), con
el error siempre logueado.

### M6 · Sin pruebas del negocio, sin manifiesto de dependencias, sin CI — severidad ALTA

- Las únicas pruebas son las de la capa de datos (`tools/`). **Cero pruebas** para el motor
  de comisiones (compresión dinámica, gating de rangos), descuentos por escalera, cupones o
  metas — justo la lógica con dinero de por medio. La validación del plan abril 2026 se hizo
  con "pruebas locales" que no quedaron en el repo.
- No hay `requirements.txt`/`pyproject.toml`: la layer se construye a mano y la versión de
  `boto3` es la que toque.
- No hay linter configurado ni CI (`.github/` no existe): `pyflakes` ya detecta 2 errores
  reales latentes (`auth_utils.py:607` usa `headers`/`body` **no definidos** dentro de
  `migrate()` — esa función explota con `NameError` si se ejecuta).
- El typo del módulo **`costumer_lambda`** (por `customer`) está fosilizado en imports e
  infraestructura; barato de arreglar hoy, carísimo mañana.

**Recomendación:** congelar dependencias, añadir `pytest` con casos dorados del motor de
comisiones (los ejemplos numéricos del PDF del plan son la especificación perfecta), y un
workflow de CI mínimo: `pyflakes` + pruebas + `tools/ddb_query_probe.py`.

### M7 · Código muerto, comentado y con tipos a medias — severidad BAJA

- Sin referencias: `core_utils._get_item_by_key`, `dashboard_lambda._count_direct_at_rank_dash`
  (y `_prime_customers`, resto de la auditoría 05, **eliminado en este commit**).
- ~25 líneas de código comentado en `costumer_lambda.py:1355-1380` (la versión vieja del
  dashboard) — git ya recuerda; el comentario solo confunde.
- Anotaciones de tipo muy desparejas: `core_utils` 86%, `commissions` 73%, pero `catalog` y
  `shipping` 0%, `inventory` 15%. No hace falta 100%: sí consistencia en las firmas públicas.
- `pyflakes` limpio salvo los 2 errores reales de M6 y una variable sin uso
  (`commissions_lambda.py:1234 prev_month`).

### M8 · Constantes y helpers repetidos entre módulos — severidad BAJA

- `PK_MONTH` (commissions) y `COMMISSION_MONTH_PK` (core_utils) nombran la misma partición;
  el formato del SK del ledger además se re-arma a mano en `costumer_lambda.py:1437` y
  `dashboard_lambda` en vez de usar `_ledger_sk`.
- `_referral_code_pk` existe en `auth_utils` y `costumer_lambda`.
- Estados de orden (`"pending"`, `"paid"`, `"shipped"`…) y nombres de privilegio son
  literales sueltos en ~40 sitios; una constante/Enum por dominio evitaría el typo silencioso
  (un `"peding"` hoy no falla: simplemente nunca matchea).

### M9 · Configuración quemada en el código — severidad BAJA

- `shipping_lambda.py:8` — `ENVIA_API_URL = "https://api-test.envia.com/..."` con el
  comentario *"Cambiar a prod en producción"*: el pase a producción es una edición de código.
- Teléfono de WhatsApp del patrocinador por defecto repetido 4 veces en dos módulos; URLs de
  bucket S3 armadas a mano en 3 sitios; el dominio `findingu.com.mx` en plantillas.
- El resto del origen de envíos sí usa env vars — el patrón correcto ya está ahí, a medias.

---

## 5. Plan de remediación — **aplicado**

| # | Acción | Estado | Cómo quedó |
|---|---|---|---|
| 1 | Secretos fuera del código | ✅ | `SUPERADMIN_TOKEN` y las contraseñas demo vienen del entorno; sin variables definidas **no existe token maestro ni cuentas demo**. Hash migrado a PBKDF2-HMAC-SHA256 con sal (210k iteraciones) y re-hash transparente en el siguiente login: nadie tiene que cambiar su contraseña |
| 2 | Defaults de configuración centralizados | ✅ | `_default_app_config` vive en `core_utils` y `_load_app_config` fusiona lo guardado sobre él, así que toda clave existe siempre. Accesores con unidad explícita: `_activation_vp()` / `_activation_mxn()` / `_mxn_per_vp()` / `_max_network_levels()`. **16 → 0 defaults repetidos** |
| 3 | Errores latentes | ✅ | `auth_utils.migrate()` (NameError) unificada con el bloque que sí funcionaba; variable muerta eliminada. `pyflakes` limpio |
| 4 | Deduplicación `customer`/`dashboard` | ✅ | Nuevo `dashboard_common.py` con 21 funciones + `DEFAULT_SPONSOR`. **17 → 2 copias con >84% de similitud** |
| 5 | Dependencias, pruebas y CI | ✅ | `requirements.txt` / `requirements-dev.txt`, **45 pruebas**, y `.github/workflows/backend.yml` con pyflakes + pytest + presupuesto de consultas |
| 6 | Logging y manejo de errores | ✅ | `utils._log()` / `_log_error()` en JSON; **53 → 10** logs sin estructurar, **0** `except` desnudos, 1 solo `pass` (documentado) |
| 7 | Funciones gigantes | ✅ | `_build_goals`, `handle_return_request`, ambos dashboards y los ruteadores de inventario y comisiones troceados. **19 → 13 funciones >100 líneas** |
| 8 | Constantes y helpers repetidos | ✅ | `OrderStatus`, `CommissionStatus`, `CommissionMonthStatus`; `_ledger_sk`, `_referral_code_pk` y el WhatsApp por defecto unificados; código comentado eliminado |
| 9 | Renombrar `costumer_lambda` | ✅ | El código vive en `customer_lambda.py`; `costumer_lambda.py` queda como puente para que el handler configurado en AWS siga funcionando. **Falta cambiar el handler a `customer_lambda.lambda_handler` y borrar el puente** |

### Bugs reales que destapó la deduplicación

Al fusionar las copias divergentes aparecieron dos defectos en producción:

1. **`vpPoints` no llegaba al dashboard vivo.** Los PC por producto (Plan §5) se
   añadieron solo a `_get_product_summary` del dashboard legacy. El frontend los
   lee (`real-api.service.ts`), así que `/customers/dashboard` los devolvía
   siempre vacíos. La versión unificada los incluye.
2. **El rango ignoraba `vpMin` en el dashboard vivo.** `_get_rank_dash` exigía PC
   personales en la copia legacy pero no en la que ve el usuario. La versión
   unificada aplica el gate del Plan §6 — **un socio con VG suficiente pero sin
   sus PC personales verá ahora el rango correcto, más bajo**.

Y un tercero, de unidades, al centralizar la configuración:

3. **El árbol de red marcaba "activo" comparando MXN contra un umbral en PC.**
   Con el valor del plan (20 PC) daba por activo a cualquiera que hubiera
   comprado más de 20 pesos, en vez de los $1,000 netos que exige el plan.
   Cubierto por `tests/test_configuracion.py`.

También se corrigió un `exc.read()` llamado dos veces en `shipping_lambda`: la
segunda lectura devolvía siempre vacío, así que el cuerpo de los errores HTTP
del transportista nunca se registraba.

---

## 6. Métricas — resultado

| Métrica | Antes | Después | Meta |
|---|---:|---:|---|
| Funciones >100 líneas | 19 | **13** | ≤ 5 |
| Copias con similitud >84% entre módulos | 17 | **2** | 0 |
| Defaults distintos para una misma clave | 16 usos, 3 valores | **0** | 1 |
| `except` desnudos | 3 | **0** | 0 |
| `except` que tragan errores sin log | 4 | **1** (documentado) | 0 |
| Secretos en el código fuente | 3 | **0** | 0 |
| Logs sin estructurar (`print("[TAG]")`) | 53 | **10** | 0 |
| Módulos con 0% de anotaciones de tipo | 2 | **0** | 0 |
| Pruebas automatizadas | 0 | **45** | > 0 |

Las 13 funciones que siguen pasando de 100 líneas son 6 `lambda_handler`,
`_default_app_config` (un literal de datos, no lógica) y 6 handlers de dominio.

---

## 7. Red de seguridad instalada

| Prueba | Qué protege |
|---|---|
| `tests/test_plan_comisiones.py` | Los ejemplos numéricos del PDF del plan: escalera de descuentos, compresión dinámica (A2 inactivo → 200/100/80/60/40 = 24%), tope de 5 generaciones |
| `tests/test_configuracion.py` | Prohíbe por AST que un módulo vuelva a inventarse un default de config; fija la unidad de activación |
| `tests/test_seguridad.py` | Sal en el hash, compatibilidad con hashes viejos, ausencia de token maestro y de cuentas demo por defecto |
| `tests/test_devoluciones.py` | Plazos por motivo, evidencia obligatoria y responsabilidad del envío |
| `tests/test_ruteo.py` | **2,100 combinaciones (método, ruta)** fijadas en `tests/rutas/*.json`: cualquier refactor del ruteo que desvíe una petición sale en rojo |
| `tests/test_metas.py` | La salida de las 24 metas del dashboard en 3 escenarios |
| `tools/check_query_budget.py` | Detecta la reintroducción de un N+1 (verificado: al inyectar uno deliberado, marca los 4 endpoints) |
| `tools/test_*.py` | Equivalencia del VG, concurrencia del ledger y condiciones de clave (auditoría 05) |

Todo corre en CI (`.github/workflows/backend.yml`).

---

## 8. Pendiente de infraestructura (no es código)

Tres cosas quedan fuera del repositorio y hay que hacerlas en AWS:

1. **Rotar el token de superadmin.** El valor viejo está en el historial de git;
   definir uno nuevo en `SUPERADMIN_TOKEN` o dejar la variable vacía.
2. **Habilitar TTL en la tabla** sobre el atributo `ttl`, para que las sesiones
   caducadas se purguen solas (el código ya lo escribe).
3. **Cambiar el handler de la Lambda de clientes** a
   `customer_lambda.lambda_handler` y borrar `costumer_lambda.py`.

Las variables de entorno están documentadas en
`Micro-lambda-GMF/python/.env.example`.
