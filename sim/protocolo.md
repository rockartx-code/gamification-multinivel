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

## Tercera ola (Día 5): prospectos desde redes, sin conocer a la socia ni al producto
| Persona | Modelo | Canal | Entra por |
|---|---|---|---|
| Tomás Ibarra, 21 | haiku, MÓVIL | TikTok de Marcela (energía sin café), link en bio | `/#/landing/MARCELA-MO` |
| Patricia Solís, 47 | sonnet, MÓVIL | Publicación de Instagram de Marcela (colágeno), solo código "MARCELA-MO" | `/#/` y tiene que encontrar dónde va el código |
| Andrés Quintero, 35 | opus | Video de YouTube de Marcela ("cómo funciona el plan"), link y código en la descripción | `/#/landing/MARCELA-MO` |

## Cuarta ola (Día 5): anuncios pagados por FindingU, sin patrocinador (cartera de Ivonne)
| Persona | Modelo | Canal | Entra por |
|---|---|---|---|
| Héctor Lara, 52 | sonnet | Anuncio de búsqueda en Google ("omega 3 alta pureza precio") | `/#/tienda` |
| Rosa Elena Mendoza, 58 | haiku, MÓVIL | Anuncio en Facebook ("Suplementos premium · envío gratis") | `/#/` |
| Iván Robles, 28 | opus | Anuncio pre-roll de YouTube (Finding Pro, proteína con colágeno) | `/#/tienda` |

## Calendario ejecutado (además del previsto)
| Fecha | Qué pasó |
|---|---|
| 17-sep (Día 15) | Relevos cruzados: Marcela lee a Rodrigo y a Andrés y contesta con sus cifras reales; Andrés hace su punto de equilibrio; Rodrigo cierra a un mes; Iván y Rosa Elena reciben a soporte; Sofía registra las mermas y los envíos (las guías las genera administración, no el almacén); Beto se detiene antes de inventar guías; Lucía envía el paquete de devolución; Patricia vive once días sin paquete. |
| 22-sep | Estafeta confirma entregas; Beto marca entregados y recibe la devolución con foto ("Recibir paquete" = validada). |
| 1-oct | Cierre de mes: nadie cobra; Marcela cierra su cuenta; Ivonne cierra su cartera en cero; Sofía no puede dar de baja datos (dos ARCO) ni cancelar un pedido pendiente; reembolsa a Lucía $800 con comprobante subido a mano; Héctor pide cancelar y no ser contactado. Paco (cajero) abre la tienda física: dos ventas de mostrador (público en general y un socio) y un corte de caja que falla. |
| 2-oct | Lucía reclama los $165 del envío de regreso; Paco reintenta el corte tras la corrección. |

Soporte se presenta a los clientes como "Daniel, Soporte Finding'U" y contesta solo con lo que contestaría un soporte real, sin internos; cuando promete algo fuera del sistema (factura, ficha técnica, envío de retorno) queda registrado como promesa incumplida si el sistema no lo puede sostener.

