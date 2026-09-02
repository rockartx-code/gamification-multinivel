# Protocolo de la simulación

## Mundo
- Frontend real en :4321, backend real (8 Lambdas) en :4400 sobre DynamoDB en memoria persistida.
- Correo interceptado en `buzon/`. Reloj simulado (`dia.sh`). Pago vía pasarela simulada. Envíos con tarifas fijas.
- Limitación conocida: Estadísticas (Athena) queda vacía.

## Reparto
| Persona | Modelo | Origen | Entra por |
|---|---|---|---|
| Lucía Fernández, 38 | sonnet | compra suplementos habitualmente, búsqueda orgánica | `/#/` |
| Rodrigo Aguilar, 29 | opus | ya está en otra red; su amiga Marcela le mandó su link | `/#/landing/<código Marcela>` |
| Karla Méndez, 24 | haiku, MÓVIL | anuncio en Instagram del producto "Boom" | `/#/tienda` |
| Diego (amigo de Rodrigo) | haiku | solo aparece si Rodrigo comparte su link | el link que Rodrigo comparta |
| Beto Salinas | haiku | almacén y pedidos, sin entrenamiento | back office |
| Sofía Herrera | sonnet | gerente, todos los permisos, sin entrenamiento | back office |
| Paco Luna | haiku | cajero POS; solo si alguien elige recoger en tienda | back office |

## Reglas para los agentes-persona
- Reciben SOLO su historia y su punto de entrada. Ninguna meta ni instrucción de uso.
- Prohibido leer código. Solo pantalla y correo.
- Pueden mandar UN mensaje estilo WhatsApp a "Soporte Finding'U" por cada duda. Lo contesto yo, con lo que contestaría un soporte real (sin internos). Cada pregunta se registra como fricción.
- Los empleados atienden lo que el sistema les muestre. Tampoco reciben metas.

## Calendario
| Día | Fecha | Qué pasa |
|---|---|---|
| 1 | 02-sep | Llegan los tres clientes. Turno de tarde de Beto y Sofía. |
| 2 | 03-sep | Correos, seguimiento, despacho. |
| 5 | 06-sep | Entregas. Rodrigo (si quiere) comparte. Karla recibe. |
| 15 | 17-sep | Segunda compra / activación mensual. |
| 31→1 | 01-oct | Cierre de mes: comisiones del mes anterior, solicitud de pago, ranking. |
| 41 | 12-oct | Tras el día de pago (10). |

## Cobertura
`servidor.log` registra cada llamada HTTP. Al final se cruza con las 75 rutas que expone el frontend y con las acciones de cada pantalla para saber qué alcanzó cada persona y qué nunca tocó nadie.

## Añadido a mitad de simulación
| Ivonne Castro | sonnet | ejecutiva de recuperación de cuentas: "maneja" al patrocinador por defecto FindingU (que no es una cuenta sino un valor fijo del backend). Debe detectar clientes que se enfriaron desde la plataforma y contactarlos por WhatsApp como su coach | back office (Clientes, Pedidos, Estadísticas, Cuadro de Honor) |

Sus WhatsApp salientes (`📱 A [nombre]:`) los entrego yo al agente-cliente correspondiente; las respuestas vuelven a ella.
