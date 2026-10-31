# El set de agentes de la ronda 6

Doce personas: siete que compran (o evalúan) y cinco que trabajan aquí. Cada archivo es lo único que
recibe ese agente: quién es, con qué llega y qué quiere lograr. **Ninguno recibe instrucciones de uso
de la plataforma**; si no encuentra algo, eso es el hallazgo.

El reparto está diseñado sobre lo que aprendimos en `docs/qa/22` y sobre lo que se construyó en
`docs/qa/23`: cada persona toca una mejora distinta, y las cuatro dudas que más se repitieron en las
rondas 1 a 5 (¿esto es una tienda o un negocio?, ¿cuánto gano?, ¿cuánto cuesta el envío?, ¿quedó
guardado?) las vuelve a vivir alguien que nunca las oyó.

| # | Persona | Rol | Dispositivo | Día | Qué mejora pone a prueba |
|---|---|---|---|---|---|
| 1 | Mariana Robles, 29 | compradora de un producto | celular | 2-mar | Modo cliente, ahorro como socia, checkout móvil |
| 2 | Ernesto Vidal, 63 | cliente mayor, recompra mensual | celular | 2-mar | Accesibilidad, formularios, suscripción |
| 3 | Ximena Paredes, 34 | prospecta analítica | laptop | 2-mar | Landing "Modo socio", plan publicado con números |
| 4 | Julio Herrera, 26 | cliente con producto dañado | celular | 2 y 6-mar | Devolución por líneas, evidencia por motivo, reembolso |
| 5 | Aurora Vega, 45 | compra en Guadalajara, pide factura | laptop | 4-mar | Recoger en sucursal por ciudad, factura |
| 6 | Fabiola Cantú, 41 | socia nueva por el link de Paulina | laptop | 4-mar | Tabla única de descuento, "completa tu activación", CLABE |
| 7 | Paulina Ríos, 44 | socia con red que no compró | laptop | 20-mar y 10-abr | Aviso de bloqueadas y producto que salva, cobro de comisiones |
| 8 | Mireya Solano | cajera de mostrador | escritorio | 3-mar | Arqueo, pago mixto, botones que explican por qué |
| 9 | Toño Vera | almacén | escritorio | 3-mar | Despacho en bloque, surtido, paquetería, resumen de turno |
| 10 | Gaby Ledesma | ejecutiva de cuentas | escritorio | 8-mar | Seguimiento de hoy, plantillas, ficha unificada |
| 11 | Renata Bustos | gerente de operaciones | escritorio | 10-abr | Pagos del mes por lote, conciliación, acciones urgentes |
| 12 | Alma Rentería | administración y finanzas | escritorio | 10-abr | Cuadrar el mes: dispersión, facturas, reembolsos, cortes |

Orden de ejecución: **uno a la vez** (un solo navegador en todo el arnés). El reloj avanza entre
turnos con `sim/dia.sh`.

Todos escriben diario en `sim/diarios/` y bitácora en `sim/metricas/` (ver `sim/protocolo.md`).
