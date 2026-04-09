# Notas de arquitectura: refactor de ordenes

## 1) Contexto actual

- El cambio reciente para historial de ordenes por cliente queda, por ahora, en `Micro-lambda-GMF/python/core_utils.py`.
- Hoy existen dos puntos que crean o actualizan ordenes y además sincronizan el historial resumido del cliente:
  - `Micro-lambda-GMF/python/order_lambda.py`
  - `Micro-lambda-GMF/python/inventory_lambda.py`
- La arquitectura objetivo es mover esta logica a un modulo de dominio, probablemente `Micro-lambda-GMF/python/order_domain.py`, y separar persistencia/escrituras de bajo nivel en algo como `Micro-lambda-GMF/python/order_repository.py`.

## 2) Por que `core_utils.py` quedo contaminado con logica de ordenes

- `core_utils.py` ya funciona como modulo compartido transversal y tiene acceso directo a `_table`, helpers de fechas, normalizacion y utilidades Dynamo.
- Para resolver rapido el historial por cliente, fue mas barato agregar ahi `_order_customer_history_pk`, `_order_customer_history_sk`, `_build_order_customer_history_item` y `_upsert_order_customer_history` que abrir todavia una frontera nueva de dominio.
- El costo es claro: un archivo "utilitario" termino mezclando infraestructura general con reglas y shape de datos propios de ordenes.

## 3) Por que `inventory_lambda.py` crea ordenes hoy y por que NO conviene que invoque directamente a `order_lambda.py`

- `Micro-lambda-GMF/python/inventory_lambda.py` crea ordenes en flujo POS porque la venta de mostrador descuenta stock, registra `posSale` y deja la orden ya entregada en una sola transaccion de negocio.
- Ese flujo necesita construir una orden distinta a ecommerce: `status=delivered`, `deliveryType=pickup`, `attendantUserId`, `stockId`, etc.
- NO conviene que una lambda invoque directamente a otra (`inventory_lambda.py` -> `order_lambda.py`) porque eso acopla handlers HTTP/APIGateway entre si, duplica contratos de entrada/salida, complica observabilidad y hace mas fragil el manejo de errores/reintentos.
- La mejor direccion es compartir dominio/repositorio, no encadenar lambdas de borde.

## 4) Por que la Step Function actual no es el lugar correcto para registrar ordenes

- `Micro-lambda-GMF/python/stepFunctions.json` hoy orquesta comisiones y sincronizacion analitica, no la escritura primaria de la orden.
- Solo contempla acciones como `ORDER_PAID` y `ORDER_DELIVERED`; no representa la creacion completa de la orden como fuente de verdad.
- Registrar la orden ahi meteria persistencia core dentro de un flujo asincronico pensado para efectos secundarios posteriores.
- Si la Step Function falla o se reintenta, se vuelve mas dificil garantizar idempotencia y consistencia del alta de la orden.
- La orden debe nacer en el flujo sincrono del dominio de ordenes; la Step Function puede seguir reaccionando a eventos de estado.

## 5) Que funciones candidatas deberian migrar a `order_domain.py`

- Desde `Micro-lambda-GMF/python/core_utils.py`:
  - `_order_customer_history_pk`
  - `_order_customer_history_sk`
  - `_build_order_customer_history_item`
  - `_upsert_order_customer_history` (o dividirla entre dominio y repositorio)
- Desde `Micro-lambda-GMF/python/order_lambda.py`:
  - construccion de `order_item` en `handle_create_order`
  - reglas de cambio de estado en `handle_update_status`
  - backfill del historial por cliente (`_backfill_customer_order_history`), idealmente como caso de uso del dominio
- Desde `Micro-lambda-GMF/python/inventory_lambda.py`:
  - construccion de la orden POS dentro de `create_pos_sale`
  - sincronizacion del historial de orden tras crear la venta

## 6) Que cosas deben quedarse fuera de `order_domain.py`

- Detalles de acceso a DynamoDB: `_table.put_item`, query expressions, buckets y `Key(...)`.
- Integraciones de borde e infraestructura: APIGateway response, boto3 clients, S3, Mercado Pago, Step Functions.
- Auditoria, transporte HTTP y parsing especifico de eventos lambda.
- Logica exclusiva de inventario/POS que no pertenezca al ciclo de vida de una orden como agregado.

## 7) Propuesta de frontera entre `order_domain.py` y `order_repository.py`

- `order_domain.py`
  - construye entidades/DTOs de orden
  - valida transiciones de estado
  - define el shape del historial por cliente
  - decide cuando debe regenerarse ese historial
- `order_repository.py`
  - guarda y lee `ORDER`
  - guarda y consulta `orderCustomerHistory`
  - encapsula claves PK/SK, queries, upserts y backfills sobre DynamoDB
- Regla practica: si conoce boto3/Dynamo, va al repository; si conoce reglas del negocio de ordenes, va al domain.

## 8) Orden de migracion recomendado

1. Crear `Micro-lambda-GMF/python/order_domain.py` con builders puros para orden ecommerce/POS e item de historial.
2. Crear `Micro-lambda-GMF/python/order_repository.py` para persistencia de `ORDER` y `orderCustomerHistory`.
3. Hacer que `Micro-lambda-GMF/python/order_lambda.py` use domain + repository sin cambiar contratos externos.
4. Hacer que `Micro-lambda-GMF/python/inventory_lambda.py` reutilice el mismo domain + repository para la orden POS.
5. Cuando ambos flujos usen la nueva frontera, eliminar la logica de ordenes de `Micro-lambda-GMF/python/core_utils.py`.

## 9) Riesgos y tradeoffs

- Separar demasiado pronto puede abrir un refactor mas grande que el cambio puntual del helper.
- Mantenerlo en `core_utils.py` por ahora deja deuda tecnica, pero reduce riesgo de romper flujos productivos de creacion/actualizacion de ordenes.
- Mover backfill y historial exige cuidar idempotencia, compatibilidad de claves y no duplicar registros por cliente.
- Si el repositorio queda demasiado generico, se vuelve otro `core_utils.py`; si queda demasiado fino, aumenta el boilerplate.

## 10) Decision temporal: mantener lo actual en `core_utils.py` hasta el refactor completo

- Decision vigente: el helper actual de historial de ordenes se mantiene en `Micro-lambda-GMF/python/core_utils.py`.
- Esto es temporal y consciente: se prioriza destrabar el cambio actual con bajo riesgo.
- El destino correcto sigue siendo extraer la logica a `Micro-lambda-GMF/python/order_domain.py` y probablemente la persistencia a `Micro-lambda-GMF/python/order_repository.py` cuando se haga el refactor integral del dominio de ordenes.
