# Arquitectura BI Mensual (Ordenes -> Athena -> CSV -> Dynamo + Archivado)

## Objetivo
Automatizar un pipeline mensual que:
1. Procese las ordenes cerradas del mes anterior almacenadas en S3 (`Ordenes/{yyyymm}/{uuid}.json`).
2. Genere estadisticas mensuales con Athena.
3. Guarde el CSV resultado en S3.
4. Inserte/actualice un registro historico de comportamiento en DynamoDB.
5. Archive las ordenes crudas del mes en `tar.gz` y las mande a Glacier/Deep Archive.
6. Elimine la carpeta mensual original solo despues de validar el archivado.

## Artefacto IaC
- Template CloudFormation incluido en:
  - `gamificacion-multinivel-f/docs/archive/planning/bi-monthly-cloudformation.yaml`
- El template crea:
  - S3 bucket de data lake.
  - Glue database/table para Athena.
  - Athena pipeline mensual orquestado con Step Functions.
  - EventBridge Scheduler mensual.
  - Lambdas (`resolve-month`, `bi-ingest-csv`, `archive-month`).
  - DynamoDB de historico de comportamiento.

## Componentes AWS
- Amazon S3
  - Bucket `data-lake` (o equivalente):
    - `Ordenes/{yyyymm}/{uuid}.json` (raw)
    - `athena-results/monthly-stats/` (CSV de Athena)
    - `archives/orders/{yyyymm}.tar.gz` (archivo comprimido en storage frio)
- AWS Lambda
  - `order-writer` (ya existente): escribe orden cerrada en S3.
  - `bi-ingest-csv`: lee CSV mensual y escribe en DynamoDB.
  - `archive-month`: empaqueta `Ordenes/{yyyymm}/` en `tar.gz`, sube a Glacier/Deep Archive y elimina raw.
- Amazon Athena + AWS Glue Data Catalog
  - Tabla externa de ordenes en S3 (particion por `yyyymm`).
  - Query mensual de agregados.
- AWS Step Functions (Standard)
  - Orquesta todo el proceso mensual de forma idempotente.
- Amazon EventBridge Scheduler
  - Dispara el flujo una vez al mes.
- Amazon DynamoDB
  - Tabla historica de comportamiento mensual.

## Flujo de Alto Nivel
1. `EventBridge Scheduler` dispara State Machine el dia 1 de cada mes.
2. `Step Functions` calcula `targetMonth` (mes anterior, formato `yyyymm`).
3. Ejecuta query Athena para `targetMonth`.
4. Espera `SUCCEEDED` en Athena.
5. Invoca `bi-ingest-csv` pasando `bucket/key` del CSV generado.
6. Invoca `archive-month` pasando `targetMonth`.
7. `archive-month`:
   - Lista `Ordenes/{targetMonth}/`.
   - Genera `archives/orders/{targetMonth}.tar.gz`.
   - Sube con `StorageClass=DEEP_ARCHIVE` (o `GLACIER`).
   - Verifica integridad (conteo/tamano/checksum/manifest).
   - Borra objetos de `Ordenes/{targetMonth}/`.
8. `Step Functions` registra auditoria final (success/failure).

## Diseno Recomendado de State Machine
Estados sugeridos:
1. `ResolveMonth` (Lambda corta o Pass + parameters)
2. `StartAthenaQuery` (SDK integration)
3. `WaitAthena` (Wait 20-30s)
4. `GetAthenaStatus` (SDK integration)
5. `AthenaDone?` (Choice: SUCCEEDED/FAILED/RUNNING)
6. `IngestCsvToDynamo` (Lambda)
7. `ArchiveMonthRawOrders` (Lambda)
8. `Success` / `Fail`

Idempotencia:
- `bi-ingest-csv`: escribir con PK/SK por mes y metrica; usar `ConditionExpression` si aplica.
- `archive-month`: si `archives/orders/{yyyymm}.tar.gz` ya existe y manifest valido, no recomprimir.

## Athena / Glue
Tabla externa orientativa:
- Ubicacion raiz: `s3://<bucket>/Ordenes/`
- Particion: `yyyymm` (string)
- Formato actual: JSON line/object por archivo.

Query mensual ejemplo (conceptual):
- `SELECT yyyymm, count(*) as orders, sum(netTotal) as revenue, avg(netTotal) as ticket ... WHERE yyyymm='<targetMonth>' GROUP BY yyyymm`

Salida:
- `s3://<bucket>/athena-results/monthly-stats/`
- Athena genera CSV automaticamente en el output location configurado.

## DynamoDB Historico (sugerido)
Tabla: `behavior_history`
- `PK`: `MONTH#<yyyymm>`
- `SK`: `METRIC#<metricName>` o `SEGMENT#...`
- Campos: `value`, `calculatedAt`, `sourceCsvKey`, `version`, `pipelineRunId`

Opcional:
- GSI por tipo de metrica para consultas cross-month.

## Archivado en Glacier
Estrategia:
- No mover millones de JSON individuales a Glacier.
- Comprimir por mes en un solo `tar.gz`.
- Subir ese archivo con storage frio y luego borrar carpeta raw mensual.

Validaciones previas al borrado:
1. Objeto `tar.gz` existe.
2. Tamano > 0.
3. Conteo de objetos en manifest coincide con origen.
4. Se guarda manifest JSON de respaldo:
   - `archives/orders/{yyyymm}.manifest.json`

## Seguridad e IAM
Roles minimos:
- Step Functions role:
  - `athena:StartQueryExecution`, `athena:GetQueryExecution`
  - `lambda:InvokeFunction`
- Lambdas:
  - Lectura/escritura en prefijos S3 especificos.
  - `dynamodb:PutItem|BatchWriteItem|UpdateItem` en tabla historica.
- Athena Workgroup:
  - Output location fijo y cifrado SSE-S3 o SSE-KMS.

## Operacion y Observabilidad
- CloudWatch Logs en todas las Lambdas y en Step Functions.
- Alarmas:
  - Falla de ejecucion mensual.
  - CSV no generado.
  - Error en archivado o borrado parcial.
- DLQ opcional (SQS) para errores de `bi-ingest-csv`.

## Costos (resumen de arquitectura)
- EventBridge Scheduler: practicamente cero con una ejecucion mensual (usualmente dentro de free tier).
- Step Functions Standard: muy bajo para 1 corrida/mes (decenas de transiciones).
- Athena: depende de bytes escaneados (optimizar con particiones y formato columnar a futuro).
- S3: costo principal en almacenamiento acumulado; archivado mensual comprimido reduce costo long-term.

## Orden de Implementacion
1. Definir Glue table/Athena query mensual.
2. Crear Lambda `bi-ingest-csv`.
3. Crear Lambda `archive-month` (streaming + manifest + borrado seguro).
4. Crear State Machine Standard.
5. Crear EventBridge Scheduler mensual.
6. Probar en ambiente dev con un mes de datos sinteticos.
7. Habilitar en produccion con alarmas.

## Criterios de Aceptacion
1. El dia programado se procesa exactamente el mes anterior.
2. Se genera CSV mensual en S3.
3. DynamoDB queda con registro historico consistente del mes.
4. Se crea `tar.gz` en storage frio con manifest.
5. La carpeta `Ordenes/{yyyymm}/` se elimina solo despues de validacion exitosa.
