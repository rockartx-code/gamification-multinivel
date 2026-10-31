# Infraestructura como código

> **Qué cubre:** `Micro-lambda-GMF/template.yaml` (AWS SAM), qué declara, cómo
> adoptarlo sobre la cuenta existente y qué queda fuera.
> **Por qué:** las auditorías `05` y `06` dejaron tres pendientes de seguridad
> —habilitar el TTL, rotar el token de superadmin y corregir el handler de
> clientes— que **no se podían hacer ni revisar desde el repositorio** porque la
> infraestructura solo existía en la consola de AWS.

---

## 1. Advertencia de origen

La plantilla está **derivada del código y del OpenAPI**, no exportada de la
cuenta en producción. Refleja lo que el código necesita, que puede no coincidir
con lo desplegado hoy (nombres de función, memoria, timeouts, autorizadores).

**Antes del primer `sam deploy` sobre un entorno existente**, contrastar:

```bash
aws lambda list-functions --query 'Functions[].[FunctionName,Handler,MemorySize,Timeout]' --output table
aws dynamodb describe-table --table-name multinivel --query 'Table.[TableStatus,BillingModeSummary,TimeToLiveDescription]'
aws apigateway get-rest-apis --query 'items[].[id,name]' --output table
```

Ruta recomendada: desplegar primero en `dev` (`--parameter-overrides Entorno=dev`),
validar, y solo después importar los recursos de producción.

## 2. Qué declara

| Recurso | Notas |
|---|---|
| `TablaMultinivel` | Tabla única PK+SK, on-demand. **TTL habilitado sobre `ttl`** (el código ya escribe ese atributo; sin esto nada se purgaba). PITR solo en `prod`. Streams habilitados para el siguiente paso del roadmap. `Retain` en borrado. |
| 8 funciones Lambda | Una por dominio, python3.12/arm64. `FnComisiones` y `FnDashboard` con más memoria y timeout por el motor de comisiones y el cuadro de honor. |
| `ApiPublica` | API REST con CORS y throttling (100 rps, ráfaga 200). |
| `MaquinaVentas` | Step Functions desde `python/stepFunctions.json`, con los ARN sustituidos. |
| 3 políticas IAM | Tabla, bucket y SES. **Sin permiso de barrido de tabla**: el backend no hace ninguno y no debe empezar por accidente. |

Sin *layer*: cada función empaqueta `python/` completo, que ya trae `core/`.
Declarar una layer obligaría a mantener el mismo código en dos artefactos que
pueden desincronizarse, y `boto3` viene en el runtime.

## 3. Los tres pendientes, resueltos como configuración

| Pendiente | Cómo queda |
|---|---|
| TTL de sesiones | `TimeToLiveSpecification` en la tabla. |
| Rotar el token de superadmin | Parámetro `TokenSuperadmin` (`NoEcho`). **Vacío = no existe acceso de superadmin**, que es lo recomendado en producción. El valor histórico estaba en el código y debe considerarse comprometido. |
| Handler de clientes | `FnClientes` apunta a `customer_lambda.lambda_handler`. Tras desplegar, `costumer_lambda.py` (el puente) puede borrarse. |

## 4. La plantilla está atada al código por pruebas

`tests/test_infraestructura.py` impide que se desincronice:

- Cada `Handler` declarado existe y define esa función.
- El handler de clientes usa el nombre corregido (`costumer` no reaparece).
- El TTL está habilitado sobre el atributo `ttl`.
- Ninguna política concede el barrido completo de tabla.
- Toda variable de entorno declarada está documentada en `.env.example`, **y**
  toda `os.getenv` del código está documentada.

Esa última comprobación ya encontró cuatro problemas reales al escribirla:
`ATHENA_DATABASE`, `MERCADOPAGO_ACCESS_TOKEN` y `ORDER_FULFILLMENT_SFN_ARN` no
estaban documentadas, y la plantilla declaraba `STATE_MACHINE_ARN` cuando el
código lee `ORDER_FULFILLMENT_SFN_ARN` — la máquina de estados nunca se habría
disparado.

## 5. Uso

```bash
cd Micro-lambda-GMF
sam validate --lint
sam build
sam deploy --guided \
  --parameter-overrides Entorno=dev TokenSuperadmin="" \
                        UrlApiEnvios=https://api-test.envia.com/ship/rate/
```

Para producción, `Entorno=prod` activa PITR y conviene apuntar `UrlApiEnvios`
al endpoint de producción de Envia.

## 6. Qué queda fuera

- **Autorizador de API Gateway** (punto 7 del roadmap): hoy las rutas aceptan
  `x-user-id`/`x-user-role` sin verificación criptográfica. Cuando exista, se
  declara aquí y esos headers dejan de ser fuente de verdad.
- **SQS para correo y Streams para el árbol de red** (punto 5): los Streams ya
  están habilitados en la tabla; falta la función consumidora.
- **CI de despliegue**: el workflow actual solo prueba. El paso natural es
  `sam deploy` a `dev` en cada merge a la rama principal.
- **Dominio propio, WAF y alarmas**: no declarados.
