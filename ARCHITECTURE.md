# Arquitectura del backend

Mapa de una página para orientarse sin leer 10,000 líneas. Para el detalle de
cada decisión, ver `docs/qa/05..08`.

## Panorama

```
Angular (gamificacion-multinivel-f)
        │  HTTPS
        ▼
API Gateway  ──►  8 funciones Lambda, una por dominio
                      │
                      ├── paquete core/  (capa común)
                      │
                      ▼
              DynamoDB  ·  tabla única  ·  sin índices secundarios
                      │
                      └── Step Functions ──► comisiones y bonos (asíncrono)
```

## Modelo de datos

Una sola tabla (`multinivel`), clave `PK` + `SK`, **sin GSI**.

```
Patrón general "bucket + REF"
  Item principal :  PK = "<ENTIDAD>"          SK = "<createdAt ISO>#<id>"
  Puntero        :  PK = "<ENTIDAD>#<id>"     SK = "REF"   → {refPK, refSK}
```

Leer por id cuesta 2 GetItem (puntero + principal). Como el `SK` empieza por
`createdAt`, **se puede acotar por fecha en la condición de clave**:
`_query_bucket("POS_SALE", sk_prefix="2026-09")`. Ojo: `sk_to` es un tope
crudo, no un prefijo (ver el docstring de `_query_bucket`).

Entidades que **no** siguen el patrón, por buenas razones:

| Entidad | Clave | Por qué |
|---|---|---|
| `ASSOCIATE_MONTH` | `PK="ASSOCIATE_MONTH"`, `SK="<id>#<YYYY-MM>"` | Se lee siempre por (socio, mes) |
| `SESSION` | `PK="SESSION#<token>"`, `SK="SESSION"` | Se busca solo por token; 1 GetItem por petición |
| Mes contable | `PK="COMMISSION_MONTH"`, `SK="#BENEFICIARY#<id>#MONTH#<mes>"` | Ver «Ledger» abajo |
| Historial de pedidos | `PK="ORDER_BY_CUSTOMER#<id>"`, `SK="<createdAt>#<orderId>"` | Paginación real por cliente |
| Árbol de red | `PK="NETWORK_TREE#customers"`, `SK="TREE"` | Singleton: toda la topología en un item |
| Índices | `REF#NOMBRE#<letra>`, `REF#EMAIL#<email>`, `REFERRAL_CODE#<código>` | Búsquedas sin GSI |

El cableado de las entidades con clave propia vive **solo** en
`core/entities.py`; `core/db.py` es genérico y no conoce ninguna.

## El paquete `core/`

Dependencias en una sola dirección; `tests/test_arquitectura.py` lo verifica.

```
settings → domain → values → logs → http → db → config
                                              ├→ network → entities
                                              ├→ indexes, ledger, security, email, audit
                                              └→ routing
```

`core_utils.py` es una **fachada de reexportación**: los ~280 puntos de llamada
existentes (`import core_utils as utils`) siguen funcionando. El código nuevo
debería importar del módulo concreto (`from core.db import _query_bucket`).

## Piezas que conviene conocer antes de tocar nada

**Árbol de red persistido.** `_load_network_scope(cliente)` devuelve el cliente
y su descendencia leyendo un singleton con toda la topología y resolviendo los
items con `BatchGetItem`. Es lo que evita el `GetItem` por cliente que hacía que
el cuadro de honor fuera O(N²). **Nunca** recorrer la red con `_get_by_id` en un
bucle: `tools/check_query_budget.py` lo detecta y CI falla.

**Ledger de comisiones.** Escrituras concurrentes sobre el mismo mes usan
bloqueo optimista (`version` + `ConditionExpression`). Hay un esquema alternativo
por filas, tras `LEDGER_ROW_SCHEME`, que elimina el techo de 400 KB y la
contención; ver `core/ledger.py` y `tools/migrate_ledger_rows.py`.

**Configuración del negocio.** Una sola fuente: `core/config.py`. Se lee con
accesores que llevan la unidad en el nombre (`_activation_vp` en PC vs
`_activation_mxn` en pesos) porque confundirlas ya causó un bug real. Está
prohibido por test repetir un valor por defecto en el punto de lectura.

**Ruteo.** `catalog_lambda` y `commissions_lambda` usan tabla declarativa
(`core/routing.py`): el privilegio de cada endpoint se lee de un vistazo con
`routing.describir()`. Los demás aún usan cascadas de `if`; migrarlos al
tocarlos. Cualquier cambio de ruteo se verifica contra
`tests/rutas/*.json` (2,100+ combinaciones método/ruta con su código de estado).

## Flujo de una venta

```
POST /orders            → crea el pedido, calcula descuento por escalera (MPN del mes)
   └─► Step Functions
        ORDER_PAID      → comisiones 'pending' con compresión dinámica (5 generaciones)
        ORDER_DELIVERED → pasa a 'confirmed' y evalúa bonos
        ORDER_CANCELLED
        ORDER_REFUNDED  → anula las filas del ledger de esa orden
        ORDER_RETURNED
```

Las reglas de negocio (escalera de descuentos, generaciones, rangos, bonos) son
**configuración**, no código: `core/config.py::_default_app_config`. Los
ejemplos numéricos del plan de abril 2026 están fijados en
`tests/test_plan_comisiones.py`.

## Cómo trabajar aquí

```bash
cd Micro-lambda-GMF/python
pip install -r requirements-dev.txt
python -m pyflakes .              # el gate de CI, sin filtros
python -m pytest tests -q         # 86 pruebas
python tools/check_query_budget.py # detecta la reintroducción de un N+1
```

Reglas que el CI hace cumplir:

- Las dependencias de `core/` van en una sola dirección.
- `core/db.py` no decide según la entidad.
- Ningún módulo repite un valor por defecto de configuración.
- El coste en viajes a DynamoDB no crece con el tamaño del dataset.
- La plantilla de infraestructura concuerda con el código (handlers, TTL,
  variables de entorno documentadas en ambos sentidos).

## Infraestructura

`Micro-lambda-GMF/template.yaml` (SAM) declara tabla, TTL, funciones, API,
máquina de estados y políticas. Está **derivada del código, no exportada de
producción**: contrastar antes del primer deploy (ver
`docs/qa/08-infraestructura.md`).
