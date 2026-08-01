# Plan de Almacenamiento en DynamoDB

**Actualizado 2026-08-01** para reflejar el código real (handler.py). La versión anterior describía un esquema `USER#<id>` + GSI1/2/3 que nunca se implementó.

## Tabla

- Nombre: variable de entorno `TABLE_NAME`, default `"multinivel"`
- Estrategia: single-table con patrón **bucket + REF**
- Cada entidad se persiste DOS veces por razones de acceso:

| Caso | PK | SK | Propósito |
|------|----|----|-----------|
| **Bucket** (listados) | `ENTITY` (ej. `CUSTOMER`, `ORDER`) | `<createdAt ISO>#<id>` | Listar por tipo, orden cronológico |
| **Ref** (lookup) | `ENTITY#<id>` | `REF` | Lectura directa por identificador |

**Ejemplo:**
```
Bucket:  PK=CUSTOMER, SK=2026-01-15T10:30:00Z#user123
Ref:     PK=CUSTOMER#user123, SK=REF
```

Nota: Las dos escrituras **no son atómicas** (sin `TransactWriteItems`); riesgo aceptado según código handler.py:661-662.

## Entidades en Uso

ADMIN_EVENT, AUTH, PASSWORD_RESET, CONFIG, ASSOCIATE_MONTH, CUSTOMER, ORDER, PRODUCT_CATEGORY, PRODUCT, CAMPAIGN, ASSET, INVENTORY_MOVEMENT, STOCK, STOCK_DAMAGE, STOCK_TRANSFER, POS_CASH_CUT, POS_SALE, COMMISSION_REQUEST, COMMISSION_RECEIPT, NOTIFICATION, PRODUCT_OF_MONTH, EMPLOYEE.

## Claves Especiales

- **ASSOCIATE_MONTH**: estado mensual de volumen/actividad por asociado (método `_get_month_state`, handler.py:1656)
- **COMMISSION_MONTH**: ledger mensual por beneficiario
  - `PK = "COMMISSION_MONTH"`
  - `SK = "#BENEFICIARY#<id>#MONTH#<mes>"`
  - Atributos: `ledger`, `totalPending`, `totalConfirmed`, `totalBlocked`

## Limitaciones Conocidas

1. **Sin GSIs**: No existen índices secundarios globales. Una búsqueda por email requiere escaneo de bucket (comentario handler.py:970-972). Oportunidad de optimización pendiente.
2. **Doble escritura no atómica**: El fallo en la segunda escritura deja bucket/ref inconsistentes. Aceptado por diseño.

## Referencia

Para arquitectura backend completa: `../../docs/backend-architecture.md`
