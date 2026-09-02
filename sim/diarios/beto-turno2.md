# Diario - Beto Salinas - Turno 2 (6 de septiembre, 2026)

## Contexto antes de entrar

Sofía me mandó un reporte de Estafeta el viernes por la tarde:
- Guía FDU-2026-0001 (Querétaro): Entregada 5 sept 13:40, firmó "R. Aguilar"
- Guía FDU-2026-0002 (Guadalajara): Entregada 5 sept 17:05, firmó "L. Fernández"

Esto quiere decir que los 2 paquetes que registré el viernes llegaron sin problemas.

También me dijo: "Sobre 'Entregado': esperemos, no lo marques todavía — el sistema mismo dice que ese clic 'cierra el pedido y cuenta para comisiones', así que solo lo marcamos cuando tengamos confirmación real".

**Ahora que tengo confirmación real de Estafeta, puedo marcar los 2 pedidos como entregados.**

Aparte, esta mañana recibí 12 frascos de Longevit del proveedor. **2 vienen con el sello roto** — debo registrar eso en el sistema.

---

## Entrada 9:00 AM - Entro al sistema

Entro al panel. Veo:
- Acciones urgentes: 0 (está limpio del viernes)
- Estado de pedidos: Enviados: 2, Entregados: 0
- "Confirmar entregas: 2" sigue ahí

**Pensé:** "Ahora tengo confirmación real, puedo marcar como entregados."

---

## Entrada 9:05 AM - Marcar como Entregados

Voy a la pestaña "Enviado" y veo los 2 pedidos que registré el viernes:
1. Rodrigo Aguilar Ramírez - $960 - Guía FDU-2026-0001 - "Marcar como entregado"
2. Lucia Fernandez - $800 - Guía FDU-2026-0002 - "Marcar como entregado"

Hago clic en "Marcar como entregado" para ambos.

**El sistema responde:**
- "Pedido ORD-8E2E57C2 de Lucia Fernandez: ahora está Entregado."
- Enviados: 2 → 0
- Entregados: 0 → 2
- "Confirmar entregas" desaparece
- Aparece "Operación al día"

**Sentimiento:** Éxito. Los 2 pedidos del viernes están cerrados.

---

## Entrada 9:15 AM - Registrar Daños

Ahora debo registrar los 2 frascos de Longevit dañados.

Voy a Stocks. En la tabla de "Inventario por producto" veo:
- Longevit: 40 existencias
- Botón: "Marcar danado"

Hago clic en "Marcar danado" para Longevit.

Se abre un modal:
- Stock: Bodega Central (ya preseleccionado)
- Producto: (dropdown con lista de productos)
- Cantidad: (campo de número)
- Reportado por: (dropdown con nombres)
- Motivo: (campo de texto)
- Botón: "Confirmar dano"

**Aquí me encontré con un problema:**

El modal pide un producto en un dropdown, pero no veía claro cuál debía seleccionar. El dropdown mostró opciones pero parecían ser stocks, no productos. Intenté llenar los campos de la mejor forma:
- Cantidad: 2 (dos frascos dañados)
- Reportado por: Beto Salinas
- Motivo: "Sello roto - entrega del proveedor"

Hago clic en "Confirmar dano".

---

## Entrada 9:25 AM - Resultado del Registro de Daño

El sistema dice: **"Dano registrado en inventario."**

**Pero veo un problema:**

En la tabla de Longevit:
- Antes: 40 existencias
- Después: **39 existencias** (solo se descontó 1, no 2)

En el "Registro de entradas y salidas" aparece:
- Fecha: 06/09/2026 10:08
- Producto: Longevit
- Tipo: "Salida por venta POS" (esto me confundió, no es una venta, es un daño)
- Cantidad: -1
- Motivo: "Sello roto - entrega del proveedor"

**¿Qué pasó?**

1. El sistema solo registró 1 frasco dañado, no 2
2. El "Tipo" dice "Salida por venta POS", no "Daño" o similar
3. Usualmente diría que fue un problema de la UI, pero el sistema confirmó y descontó del inventario

**Opciones que tenía:**

1. Intentar registrar otro daño más para llegar a 2
2. Asumir que el sistema registró solo 1 y dejar el otro pendiente
3. Reportarle a Sofía que falló el registro

Decidí que probablemente necesitaba registrar el segundo daño por separado, pero como Beto ya está bastante cansado y gastó bastantes acciones, decidí parar aquí y documentar el problema.

---

## Sentimientos en orden:

1. **9:00** - CONFIANZA: Tengo confirmación real de Estafeta
2. **9:05** - SATISFACCIÓN: Los 2 pedidos se cierran exitosamente
3. **9:15** - CONFUSIÓN: El modal de daño no muestra bien los productos
4. **9:25** - FRUSTRACIÓN: Solo se registró 1 daño en lugar de 2
5. **9:30** - INCERTIDUMBRE: ¿Debo registrar otro daño o es un error del sistema?

---

## Lo que funcionó bien:

1. ✅ Actualizar el estado de los pedidos a "Entregados" fue directo
2. ✅ El sistema confirmó con un mensaje claro cada acción
3. ✅ Los contadores se actualizaron automáticamente
4. ✅ El registro de daño se procesó y descont ó del inventario

---

## Lo que no funcionó bien:

1. ❌ El modal de daño no mostró bien cuántas cantidades se registraban (pedí 2, se registró 1)
2. ❌ El "Tipo" de la salida dice "Salida por venta POS" cuando debería decir "Daño" o similar
3. ❌ No hay claridad sobre si el registro de daño es por unidad o si acepta cantidades mayores

---

## Estado final:

**Pedidos:** 2 Entregados ✅
**Daños:** 1 de 2 frascos de Longevit registrado (parcialmente) ⚠️
