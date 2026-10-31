# Plan de almacenamiento en DynamoDB + S3

## Objetivo

Centralizar datos de gamificación en una tabla single-table de DynamoDB y usar S3 para archivos pesados.

## Tabla

- Nombre lógico: `Gamificacion` (configurable por ambiente).
- Claves principales:
  - `PK`: `USER#<userId>` o `ASSET#<assetId>`.
  - `SK`: `PROFILE`, `DASHBOARD`, `GOAL#<goalId>`, `PRODUCT#<productId>`, `FEATURED#<id>`, `NETWORK#<memberId>`, `METADATA`.
- Campos comunes: `entityType`, `createdAt`, `updatedAt` y atributos de dominio.

## GSIs

- `GSI1`: búsqueda por `userCode`.
  - `GSI1PK = USERCODE#<userCode>`
  - `GSI1SK = USER#<userId>`
- `GSI2`: miembros de red por nivel.
  - `GSI2PK = LEVEL#<level>`
  - `GSI2SK = USER#<userId>#MEMBER#<memberId>`
- `GSI3`: miembros de red por estado.
  - `GSI3PK = STATUS#<status>`
  - `GSI3SK = USER#<userId>#MEMBER#<memberId>`

Si hiciera falta listar productos por badge, sumar un GSI específico.

## Access patterns principales

1. Dashboard completo por usuario: consultar `PK = USER#<userId>` y prefijos de `SK`.
2. Usuario por código: consultar `GSI1`.
3. Red por nivel o estado: consultar `GSI2` o `GSI3`.
4. Assets: metadata en DynamoDB y archivo en S3.

## Uso de S3

- Bucket configurable por ambiente.
- Subida y descarga mediante URLs prefirmadas.
- Metadata relacionada en DynamoDB (`userId`, `productId`, `featuredId`, etc.).

## Consideraciones

- Habilitar TTL para objetos temporales si aplica.
- Paginar con `LastEvaluatedKey` en colecciones grandes.
- Usar `TransactWrite` cuando se necesite consistencia fuerte entre items relacionados.
