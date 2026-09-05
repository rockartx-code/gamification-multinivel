# Roadmap de arquitectura, mantenibilidad y legibilidad

> **Punto de partida:** auditorías `05` (consultas) y `06` (mantenibilidad) aplicadas y
> validadas; revisión adversarial del diff completo con sus 8 hallazgos corregidos.
> **Propósito:** qué sigue, en qué orden y por qué — para que la arquitectura siga
> mejorando en lugar de estabilizarse en el estado actual.
> **Estado:** los 8 puntos están ejecutados salvo el 5 (asíncrono), que depende
> de infraestructura nueva. Ver §9.
> **Fecha:** septiembre 2026 · **Rama:** `claude/ultimos-cambios-integrados-fylhiw`

---

## 0. Estado validado (lo que ya se puede dar por bueno)

| Verificación | Resultado |
|---|---|
| Suite de pruebas | **46/46** (plan de comisiones, config, seguridad, devoluciones, metas, ruteo) |
| Instantánea de ruteo | 2,100 combinaciones (método, ruta) sin desvíos |
| Presupuesto de consultas | Sin N+1; GetItem constante de 100 → 800 clientes |
| `pyflakes .` (el gate de CI, sin filtros) | Limpio, exit 0 |
| Revisión adversarial de `main..HEAD` | 8 hallazgos, **8 corregidos** — incluido uno bloqueante: el candado del ledger no podía escribir sobre meses contables previos al despliegue |
| `ng build` | OK |

La lección de la revisión queda incorporada: los dos fakes de DynamoDB eran más
permisivos que el servicio real (`version = :0` no falla en el fake si el atributo no
existe; en DynamoDB sí) y por eso 45 pruebas no cazaron un bug de despliegue. **Los fakes
ahora modelan la semántica real y hay un test que reproduce el caso.** Regla para el
futuro: cuando un doble de pruebas simule un servicio externo, imitar sus fallos, no solo
sus éxitos.

---

## Estado de ejecución

| # | Mejora | Estado | Resultado |
|---|---|---|---|
| 1 | Infraestructura como código | ✅ | `template.yaml` (SAM) con tabla, TTL, 8 funciones, API, Step Functions y políticas. Los 3 pendientes de AWS pasan a ser un diff revisable. `tests/test_infraestructura.py` la ata al código |
| 2 | Retirar `/user-dashboard` | ✅ instrumentado | Registra `legacy_user_dashboard_hit` y responde con cabeceras RFC 8594. **Falta el borrado**, que requiere una semana de datos que confirmen que nadie lo llama |
| 3 | Ledger por filas | ✅ tras bandera | `LEDGER_ROW_SCHEME` (off/dual/rows) + script de migración idempotente. Añadir una comisión a un mes con 200: **201 → 1 fila reescrita** |
| 4 | `core/` como paquete | ✅ | 14 módulos, dependencias en una dirección, paridad completa de API. Dos violaciones de capa resueltas con registros de entidad |
| 5 | Trabajo pesado fuera del request | ⏳ Parcial | Streams ya habilitados en la plantilla; falta la función consumidora y la cola de correo. Ver §9 |
| 6 | Ruteo declarativo | ✅ 2 de 8 lambdas | Motor + `catalog` (148 → 6 líneas) y `commissions` (180 → 17). El resto, al tocarlos |
| 7 | Un solo camino de autenticación | ✅ corto plazo | Sesiones con clave directa: 1 GetItem por petición en vez de 2, sin punteros huérfanos. El authorizer sigue pendiente (§9) |
| 8 | Legibilidad continua | ✅ | `ARCHITECTURE.md`, tipos y troceo aplicados; las reglas las hace cumplir el CI |

### Lo que la ejecución destapó

Cada mejora encontró defectos que el código anterior escondía:

- **Fakes más permisivos que DynamoDB.** El de las pruebas no aplicaba
  `UpdateItem` (solo devolvía el item), así que ningún efecto de un `ADD`/`SET`
  era visible. Y `version = :0` no fallaba con el atributo ausente, que fue
  justo el bug bloqueante de la revisión anterior. Ambos corregidos.
- **`RUTEO_ACTUALIZAR=0` regeneraba la referencia.** `os.environ.get(VAR)`
  devuelve `"0"`, que es verdadero: la instantánea de ruteo se sobrescribía en
  silencio y la prueba pasaba siempre.
- **La instantánea medía lo que no era.** Solo registraba qué `handle_*` se
  invocaba; en comisiones la lógica era inline y 98 de 100 entradas eran
  `<sin handler>`. Ahora registra el código de estado.
- **`STATE_MACHINE_ARN` vs `ORDER_FULFILLMENT_SFN_ARN`.** La plantilla declaraba
  un nombre que el código no lee: la máquina de estados nunca se habría
  disparado. Lo encontró el test que exige documentar cada variable.
- **Rutas que escribían en URLs no declaradas.** `POST /notifications/{id}`
  creaba una notificación y `POST /product-categories/{id}` una categoría.
- **Rutas DELETE sobre handlers sin DELETE**, que devolvían 502.

---

## 1. Infraestructura como código — la mejora que habilita todas las demás

**Hoy:** la tabla, el TTL, las 8 funciones Lambda, sus handlers, la layer, las variables de
entorno, API Gateway y Step Functions viven solo en la consola de AWS. El repo no puede
reproducir el sistema, y las tres tareas pendientes de las auditorías (rotar el token,
habilitar TTL sobre `ttl`, cambiar el handler a `customer_lambda.lambda_handler`) están
pendientes **precisamente porque la infraestructura no es código**: nada en el repo puede
hacerlas ni verificarlas.

**Propuesta:** una plantilla SAM (o CDK) en `Micro-lambda-GMF/template.yaml` que declare
tabla + TTL + funciones + layer + variables (referenciando `.env.example`) + el import del
`openapi-aws.yaml` que ya existe. El pipeline de CI pasa de "probar" a "probar y
desplegar a un entorno de staging".

**Criterio de cierre:** `sam deploy` levanta el sistema completo en una cuenta limpia; las
3 tareas pendientes de AWS se convierten en un diff revisable.
**Esfuerzo:** medio. **Riesgo:** bajo (se importa lo existente, no se recrea).

## 2. Retirar `/user-dashboard` y el código que solo existe para él

**Hoy:** el frontend ya no lo llama (la tienda usa `/catalog`, el dashboard usa
`/customers/dashboard`), pero el endpoint sigue vivo y con él `get_user_dashboard`,
`_associate_section`, `_catalog_section` y el modo invitado — cientos de líneas cuyo único
consumidor posible es un cliente viejo cacheado. Es también donde quedan efectos
indeseables: **envía correos de metas dentro de un GET** (`_notify_goal_achievements`) y
escribe caché en cada lectura.

**Propuesta en dos pasos:** (1) instrumentar: un `_log("legacy_user_dashboard_hit")` y una
semana de CloudWatch deciden si queda tráfico real; (2) si no lo hay, borrar la ruta del
OpenAPI y el código, y `getUserDashboardData()` del frontend. Las 2 copias restantes con
similitud >84% (`_active_notifications_for_customer` ya unificada; quedan restos menores)
desaparecen con él.

**Criterio de cierre:** `grep user-dashboard` solo aparece en documentación histórica.
**Esfuerzo:** bajo. **Riesgo:** bajo con la instrumentación previa.

## 3. Ledger de comisiones: un item por fila (la deuda P1-2 restante)

**Hoy:** el candado optimista cierra la carrera, pero `ledger` sigue siendo una lista
dentro de un solo item: techo duro de **400 KB** (un líder con volumen alto lo alcanza),
contención de escritores en meses calientes (los reintentos del candado son serialización,
no paralelismo) y reescritura del item completo por cada fila añadida.

**Propuesta:** `PK="LEDGER#<beneficiario>#<mes>"`, `SK="ROW#<orderId>#G<gen>"`, totales
mantenidos con `UpdateItem … ADD` atómico en un item de cabecera. Migración: script
idempotente que expanda los items existentes + doble lectura durante la transición (el
patrón REF→direct de `ASSOCIATE_MONTH` ya ensayó exactamente esto). De paso, una clave
por mes hace consultable "todas las comisiones de junio" con `begins_with`, que el
reporte admin de comisiones sigue resolviendo hoy leyendo la partición entera.

**Criterio de cierre:** el test de concurrencia pasa sin reintentos; el reporte mensual
deja de leer `COMMISSION_MONTH` completo.
**Esfuerzo:** alto (migración de datos). **Riesgo:** medio — hacerlo detrás de un flag.

## 4. Partir `core_utils` en un paquete con fronteras

**Hoy:** 2,000+ líneas que mezclan siete responsabilidades: acceso a datos, ledger, red,
config, seguridad, email y logging. Todo lo que toca todo importa todo; la convención
`_privado` ya no significa nada (los lambdas usan ~60 símbolos "privados" del módulo).

**Propuesta:** paquete `core/` con módulos por responsabilidad —
`db.py` (bucket+REF, batch, paginación), `ledger.py`, `network.py` (árbol), `config.py`
(defaults+accesores), `security.py` (hash, actores, privilegios), `email.py`, `logging.py`
— y `core_utils.py` reducido a fachada de reexports para no tocar los ~280 puntos de
llamada. Después, migrar los imports módulo a módulo. Los símbolos que los lambdas usan
dejan de llamarse `_privado`: el guion bajo pasa a reservarse para lo interno de cada
módulo del paquete.

**Criterio de cierre:** `core_utils.py` < 100 líneas (solo reexports); ningún módulo del
paquete importa a otro salvo hacia abajo (`ledger → db`, nunca `db → ledger`).
**Esfuerzo:** medio (mecánico, con pyflakes + suite como red). **Riesgo:** bajo.

## 5. Trabajo pesado fuera del camino de la petición

Tres cosas corren hoy dentro de un request/evento síncrono y no deberían:

| Qué | Dónde | Propuesta |
|---|---|---|
| Envío de correos (SES) | metas logradas, confirmaciones, recuperación | Encolar (SQS) y enviar desde un worker; un SES caído hoy alarga o rompe la petición |
| Reconstrucción del árbol de red | `_load_network_scope` la dispara en línea si detecta desfase (N escrituras dentro de un GET) | DynamoDB Streams sobre CUSTOMER → actualización incremental del árbol; el GET solo lee |
| Evaluación de bonos con gating recursivo | `handle_confirm_commissions` | Ya es asíncrona vía Step Functions; falta hacerla **idempotente verificada**: un retry de ORDER_DELIVERED no debe duplicar awards (hoy `_has_bonus_award` protege, pero sin test) |

**Criterio de cierre:** ninguna petición HTTP escribe más de O(1) items ni llama a SES.
**Esfuerzo:** medio. **Riesgo:** medio (nueva pieza de infra, depende del punto 1).

## 6. Ruteo declarativo con 404 estrictos — ahora sí es posible

**Hoy:** las cascadas de `if` despachan por prefijo, así que `/campaigns/loquesea` cae en
`handle_campaigns` con cualquier método. Con la instantánea de 2,100 rutas ya instalada,
el cambio es verificable: se escribe la tabla `(método, patrón, privilegio, handler)` por
lambda, se regenera la instantánea, y **el diff de la instantánea ES la revisión** — cada
ruta que pasa a 404 queda listada y se aprueba explícitamente contra el OpenAPI (24 rutas
declaradas vs ~56 prefijos aceptados hoy).

El beneficio mayor no es estético: el privilegio de cada endpoint queda auditable en una
tabla de una pantalla, en lugar de enterrado en 6 ruteadores.

**Criterio de cierre:** los 6 `lambda_handler` restantes de >100 líneas bajan a <30; la
tabla de rutas y el OpenAPI se validan entre sí en CI.
**Esfuerzo:** medio-alto. **Riesgo:** medio, acotado por la instantánea.

## 7. Sesiones y actores: un solo camino de autenticación

**Hoy:** conviven tres mecanismos — Bearer contra items SESSION (2 GetItem por petición),
headers `x-user-id`/`x-user-role` inyectados sin verificación criptográfica (cualquiera
que alcance el API puede declararse admin si la ruta solo mira headers), y el token de
superadmin. `_extract_actor` los reconcilia en cada lambda.

**Propuesta:** (1) corto plazo: clave directa `PK=SESSION#<token>` (1 GetItem, sin REF);
(2) medio plazo: un **authorizer de API Gateway** que valide una sola vez y pase el actor
ya verificado en el contexto — los headers legacy dejan de ser fuente de verdad. Esto es
además el cierre correcto del hallazgo de seguridad M4.

**Criterio de cierre:** ninguna ruta protegida decide con `x-user-role` a secas.
**Esfuerzo:** medio. **Riesgo:** medio (coordinar con el frontend), depende del punto 1.

## 8. Legibilidad continua (barato, constante)

- **Idioma**: fijar convención (código/identificadores en un idioma, hoy hay
  `handle_return_request` junto a `_marcar_meta_primaria`) y aplicarla solo en código
  nuevo — renombrar lo viejo no paga su riesgo.
- **Tipos**: subir `auth_utils` (40%) e `inventory` (15%) al nivel de `core_utils` (84%)
  al tocar cada función; considerar `mypy --strict` solo para `core/` cuando exista.
- **Los 6 handlers de dominio >100 líneas restantes** (`handle_update_status`,
  `handle_pos_sale`, `handle_get_quote`, `handle_monthly_stats`, `handle_return_inspection`,
  `handle_products`): trocear al tocarlos, con el patrón validación/efectos ya usado en
  `handle_return_request` — no como proyecto aparte.
- **Documentación viva**: un `CLAUDE.md`/`ARCHITECTURE.md` de una página con el mapa
  (tabla única, patrón bucket+REF, árbol persistido, ledger, flujo de Step Functions) para
  que el próximo que llegue no lo reconstruya leyendo 10,000 líneas.

---

## Orden recomendado y dependencias

```
1. IaC ──────────────┬─→ 5. Async (SQS/Streams)
                     └─→ 7. Authorizer
2. Retirar /user-dashboard        (independiente, empezar ya con la instrumentación)
3. Ledger item-por-fila           (independiente; detrás de flag)
4. core/ como paquete             (independiente; mecánico)
6. Ruteo declarativo              (cuando se toque el siguiente endpoint)
8. Continuo                       (regla de "al tocar", no proyecto)
```

Si solo se hace una cosa este trimestre: **el punto 1**. Todo lo demás se puede hacer con
más seguridad, y dos pendientes de seguridad reales (TTL y rotación del token) dependen
de él.

---

## 9. Lo que sigue después de esta ronda

Con los puntos 1-4 y 6-8 ejecutados, el trabajo restante es este:

**Corto plazo, sin infraestructura nueva**

1. **Borrar `/user-dashboard`** cuando una semana de `legacy_user_dashboard_hit`
   confirme que no hay tráfico. Se lleva por delante el resto de la duplicación
   `customer`/`dashboard`.
2. **Migrar los 6 ruteadores restantes** a tabla declarativa, al tocar cada
   lambda. El patrón está probado y la instantánea verifica cada migración.
3. **Activar `LEDGER_ROW_SCHEME=dual`** en staging, correr la migración,
   verificar con `--verify` y pasar a `rows`.
4. **Desplegar la plantilla en `dev`** y contrastarla con producción; con eso
   se cierran los tres pendientes de AWS.

**Requiere infraestructura nueva (punto 5)**

5. **Correo por cola.** Hoy `_send_ses_email` se llama dentro de peticiones y de
   la evaluación de bonos. Con SES caído, la petición se alarga o falla. Una
   cola SQS y un worker lo desacoplan.
6. **Árbol de red por Streams.** `_load_network_scope` reconstruye el árbol en
   línea si detecta desfase: N escrituras dentro de un GET. Los Streams ya están
   habilitados en la plantilla; falta la función que mantenga el árbol de forma
   incremental.
7. **Idempotencia verificada del pipeline de bonos.** `_has_bonus_award` protege
   contra duplicados, pero no hay ninguna prueba que lo confirme ante un reintento
   de `ORDER_DELIVERED`. Es barato de añadir y protege dinero.

**Cambio de contrato (decisión de producto, no técnica)**

8. **Authorizer de API Gateway.** Los headers `x-user-id`/`x-user-role` siguen
   siendo fuente de verdad en las rutas que no exigen Bearer: cualquiera que
   alcance el API puede declararse admin. Cerrarlo requiere coordinar con el
   frontend.
9. **`GET /product-categories/{id}` y `GET /notifications/{id}`** devuelven la
   colección completa ignorando el id. Se preservó a propósito al migrar el
   ruteo; corregirlo es una decisión de API.
