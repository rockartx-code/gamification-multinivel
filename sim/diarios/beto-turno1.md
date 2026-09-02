# Diario - Beto Salinas - Turno 1 (4 de septiembre, 2026)

## Entrada: 11:00 AM - Primer contacto con el sistema

Sofía me mandó un WhatsApp ayer diciendo que hoy entrara al sistema. Llego a la computadora de la bodega, entro a `http://localhost:4321/#/login`. Me aparece:
- Pantalla de login limpia
- Un modal gigante de "Aviso de Privacidad" que me bloquea todo
- Necesito aceptarlo para continuar

**Pensé:** "Bueno, es un aviso legal. Debo aceptarlo." Hago clic en "Entendido y acepto". El modal desaparece.

**Entrada 11:05 AM**

Ahora veo el formulario de login:
- Campo: Correo electrónico
- Campo: Contraseña
- Botón: "Ingresar al panel"
- Opción: "Recuperar contraseña"

Meto mis credenciales que Sofía me pasó:
- beto@findingu.mx
- U4Z3GEUEGP

Hago clic en "Ingresar al panel". El sistema carga... y me muestra el panel.

**Entrada 11:10 AM**

¡Estoy dentro! El panel me dice:
- Soy "Beto Salinas" (está bien, es mi nombre)
- Rol: "ADMIN" (no estaba seguro de tener ese rol, pero bueno)
- "Acciones - 1 urgentes" en rojo (esto me llama la atención)
- Lado izquierdo: "Pedidos cargados: $1,760 cobrado · 3 pedidos"
  - Pendientes: 0
  - Pagados: 2
  - Pendientes envío: 2

**Pensé:** "Ok, hay algo urgente y hay 2 pedidos que no se han enviado. Probablemente eso es lo que debo hacer."

## Entrada: 11:15 AM - Descubriendo la tarea urgente

Hago clic en "Acciones - 1 urgentes". Un modal se abre y me dice claro:

> **"Acciones urgentes - Resolvé pendientes críticos desde aquí. 2 pedidos pagados sin envío - Importante - Ir a resolver"**

**Sentimiento:** Alivio. El sistema me está diciendo exactamente qué hacer. No tengo que adivinar.

Hago clic en "Ir a resolver". Me lleva a la pestaña "Pagado" y veo los 2 pedidos:

1. **Rodrigo Aguilar Ramírez** - $960 - Pagada - Guía: "-" - Botón: "Registrar envío"
2. **Lucia Fernandez** - $800 - Pagada - Guía: "-" - Botón: "Registrar envío"

Ambos necesitan que registre el envío. Hago clic en "Registrar envío" del primer pedido (Rodrigo).

## Entrada: 11:20 AM - El primer obstáculo: Stock vacío

Se abre un modal que me pide:

1. **Stock origen** - Un dropdown que dice "Selecciona stock" (¡pero está vacío!)
2. **Tipo de entrega** - Paquetería (Guía) o Entrega personal
3. **Número de guía** - Un campo para llenar

**Aquí me atoré por primera vez:**

El dropdown de stock está vacío. No hay opciones para seleccionar. El sistema me pide que elija un stock, ¡pero no me da ninguno!

**Pensé:** "¿De dónde saco un stock? ¿Debo crear uno? ¿Hay alguno por defecto?" 

No sé qué hacer. Intento abrir el dropdown esperando que aparezca algo mágicamente. Nada.

## Entrada: 11:25 AM - Buscando información: Voy a Stocks

Cierro el modal y voy a la sección de "Stocks" para ver si hay stocks disponibles que deba seleccionar.

**En Stocks descubro:**

- Hay un dropdown de "Stock activo" que también dice "Selecciona stock"
- ¡Pero en la sección "Bodega Central · Av. Insurgentes Sur 1234, Col. Del Valle, CDMX"!
- El inventario muestra:
  - Klinhart: 40 unidades (¡eso es lo que necesito enviar!)
  - Todos los productos: 40 unidades cada uno

**Pensé:** "Aha! Existe 'Bodega Central'. Probablemente debo seleccionar eso en el dropdown."

Selecciono "Bodega Central" en el dropdown de "Stock activo".

## Entrada: 11:30 AM - Segundo intento: Ahora funciona

Vuelvo a Pedidos, voy a "Pagado", e intento de nuevo "Registrar envío".

Esta vez el dropdown de stock SÍ muestra opciones:
- "Todos los stocks"
- "Bodega Central"

¡Perfecto! Selecciono "Bodega Central".

El tipo de entrega está en "Paquetería (Guía)". Lo dejo así porque necesito poner un número de guía.

**Aquí tomé una decisión sin estar seguro:**

No tengo un número de guía real de DHL, FedEx o correos. Pero el sistema me lo pide. Decido poner un número de prueba: "FDU-2026-0001" (pensando: "Si es un número de prueba del sistema, puede ser cualquiera. Si necesita uno real, el sistema me dirá").

Selecciono "Bodega Central", pongo "FDU-2026-0001" como guía, y hago clic en "Marcar como enviado".

## Entrada: 11:35 AM - ¡Primer éxito!

El sistema me dice: **"Envio registrado."**

Los números cambian:
- Pagados: 1 (bajó de 2)
- Pendientes envío: 1 (bajó de 2)
- Enviados: 1 (subió de 0)
- Aparece: "Confirmar entregas: 1"

**Sentimiento:** ¡Lo hice! Uno está hecho.

## Entrada: 11:40 AM - Segundo pedido (Lucia Fernandez)

Repito lo mismo para Lucia:
- Voy a "Pagado"
- Hago clic en "Registrar envío" del segundo pedido
- Selecciono "Bodega Central"
- Pongo guía: "FDU-2026-0002"
- Hago clic en "Marcar como enviado"

Sistema dice: **"Envio registrado."**

Números finales:
- Pagados: 0
- Pendientes envío: 0
- Enviados: 2
- **Acciones urgentes: 0** (¡desapareció!)
- Confirmar entregas: 2

**Sentimiento:** Alivio. La tarea urgente está completa.

## Entrada: 11:45 AM - Nueva tarea: Confirmar entregas

El sistema ahora me muestra una nueva sección: "Confirmar entregas: 2"

Hago clic. Me muestra los 2 pedidos que acabo de registrar como enviados:

1. Rodrigo Aguilar Ramírez - $960 - Estado: "Enviada" - Guía: "FDU-2026-0001 · Bodega Central" - Botón: "Marcar como entregado"
2. Lucia Fernandez - $800 - Estado: "Enviada" - Guía: "FDU-2026-0002 · Bodega Central" - Botón: "Marcar como entregado"

**Aquí me congelo:**

¿Debo marcar como "entregado"? Los pedidos acaban de ser enviados por paquetería. ¿Cómo sé si llegaron? ¿Debo esperar a que el cliente confirme? ¿O debo hacerlo ahora porque es parte del workflow?

**Sentimiento:** Confusión. El sistema me da un botón para clickear, pero no me dice si debo hacerlo.

No intento hacer nada más porque no estoy seguro de si esto es lo correcto.

## Sentimientos en orden cronológico:

1. **11:05 - Alivio:** El sistema me dice claramente qué debo hacer con "1 urgentes"
2. **11:20 - Frustración:** El dropdown de stock está vacío y no sé qué hacer
3. **11:25 - Esperanza:** Encuentro "Bodega Central" en la sección de Stocks
4. **11:30 - Dudas:** Tengo que poner un número de guía de prueba, sin saber si es correcto
5. **11:35 - Éxito:** El primer pedido se registra sin problemas
6. **11:40 - Confianza:** El segundo pedido es igual al primero, funciona
7. **11:45 - Confusión:** No sé si debo clickear "Marcar como entregado"

## Dudas y cosas que no entendí:

1. ¿Por qué el dropdown de stock estaba vacío la primera vez?
2. ¿Eran los números de guía "FDU-2026-0001" y "FDU-2026-0002" válidos? ¿O el sistema debería haberme rechazado?
3. ¿Qué debo hacer con "Confirmar entregas: 2"? ¿Es automático o manual?
4. ¿Hay un tercero pedido (dice "3 pedidos" pero solo vimos 2 pagados)?

## Decisiones que tomé sin estar seguro:

1. Seleccionar "Bodega Central" sin que nadie me lo dijera
2. Poner números de guía de prueba en lugar de guías reales
3. Asumir que "Paquetería (Guía)" era la opción correcta

## Lo que el sistema me dijo que tenía que hacer:

1. "1 urgentes" - "2 pedidos pagados sin envío" - **Claro y directo**
2. "Preparar envíos: 2" - **Claro en el botón principal**
3. Luego "Confirmar entregas: 2" - **Aparece, pero no me dice si debo hacerlo ahora**

---

## Estado final:
- ✅ 2 pedidos registrados como enviados
- ✅ Números urgentes reducidos a 0
- ⏳ 2 pedidos pendientes de "confirmar entrega"
- ❓ No sé si continuar con las entregas o esperar indicaciones
