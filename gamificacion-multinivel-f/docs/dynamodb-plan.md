# Plan de almacenamiento en DynamoDB + S3

## Objetivo
Centralizar los datos de gamificación (panel del usuario, metas, productos, red y activos multimedia) en una sola tabla de DynamoDB para optimizar consultas por índice, y usar S3 para archivos pesados (imágenes, banners, adjuntos).

## Diseño de tabla (single-table)
**Tabla:** `Gamificacion` (nombre configurable por ambiente).

| Atributo | Descripción |
| --- | --- |
| `PK` | Partition key principal (`USER#<userId>` o `ASSET#<assetId>`). |
| `SK` | Sort key (`PROFILE`, `DASHBOARD`, `GOAL#<goalId>`, `PRODUCT#<productId>`, `FEATURED#<id>`, `NETWORK#<memberId>`). |
| `entityType` | Tipo lógico del item (`profile`, `dashboard`, `goal`, `product`, `featured`, `network`, `asset`). |
| `createdAt` / `updatedAt` | Timestamps ISO-8601 para auditoría. |
| Campos del dominio | Datos propios de cada entidad (ej. `userCode`, `level`, `badge`, etc.). |

### Índices globales (GSI)
| Índice | Uso | Claves |
| --- | --- | --- |
| `GSI1` | Buscar por `userCode` para recuperar perfil/dashboard. | `GSI1PK = USERCODE#<userCode>`, `GSI1SK = USER#<userId>` |
| `GSI2` | Consultar miembros de red por nivel. | `GSI2PK = LEVEL#<level>`, `GSI2SK = USER#<userId>#MEMBER#<memberId>` |
| `GSI3` | Consultar miembros de red por estado. | `GSI3PK = STATUS#<status>`, `GSI3SK = USER#<userId>#MEMBER#<memberId>` |

> Nota: Si se requiere listar productos por badge, se puede añadir otro GSI (`BADGE#<badge>`).

## Accesos principales (access patterns)
1. **Obtener dashboard completo por usuario:**
   - `PK = USER#<userId>` y `SK` prefix (`PROFILE`, `DASHBOARD`, `GOAL#`, `PRODUCT#`, `FEATURED#`, `NETWORK#`).
2. **Buscar usuario por código (`userCode`):**
   - Consulta en `GSI1` con `GSI1PK = USERCODE#<code>`.
3. **Filtrar red por nivel o estado:**
   - Consulta en `GSI2` (`LEVEL#<level>`) o `GSI3` (`STATUS#<status>`).
4. **Guardar/leer assets:**
   - Metadata en DynamoDB (`PK = ASSET#<assetId>`, `SK = METADATA`) y archivo en S3.

## Uso de S3
- **Bucket**: configurable por ambiente.
- **Estrategia**: los clientes suben/descargan con URLs pre-firmadas.
- **Metadata**: se guarda en DynamoDB para relacionar el archivo con entidades (`userId`, `productId`, `featuredId`, etc.).

## Consideraciones
- Se recomienda habilitar **TTL** si hay objetos temporales (ej. uploads expirados).
- Para tamaños grandes (p. ej. redes extensas), se sugiere paginación con `LastEvaluatedKey`.
- Usar **TransactWrite** si se necesita consistencia fuerte entre items relacionados.
