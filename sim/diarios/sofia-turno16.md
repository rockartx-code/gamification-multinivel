# Sofía Herrera — jueves 10 de diciembre 2026, 9:00 am
## Oficina. Día de pago de comisiones (se pagan las de noviembre).

---

### 9:05 — Entro y reviso el panel

Login con `sofia@findingu.mx`. Panel de "Pedidos cargados": $18,981.40 cobrado, 26 pedidos, "Pendientes: 0, Pagados: 1, Pendientes envío: 1". No hay menú que diga "Comisiones" en la navegación — está dentro de **Clientes** ("Niveles, estructura y comisiones") y dentro de cada ficha de cliente.

### 9:12 — Tarea 1: quién tiene comisión de noviembre

Entro a **Clientes**. Arriba de la lista: **"Comisiones por depositar: $393.60"**. La lista tiene 16 clientes (2 páginas), columna "Mes anterior" (o sea noviembre). Reviso las dos páginas completas: de los 16, solo **Verónica Sandoval Ruiz** trae algo distinto de $0 en "Mes anterior": **$393.60**. Todos los demás (incluida Claudia Ibarra Soto) muestran $0.

Para confirmar que no se me escapó nadie, entro a **Estadísticas**, que por default me abrió en "Noviembre de 2026". Ahí las "Advertencias operativas" dicen literal: **"1 comisiones pendientes por depositar — high"**. Coincide: solo una persona.

Abro la ficha de Verónica: "Comisiones mes anterior: **$393.60** — Pendiente de pago" y debajo **"CLABE: 012180001234567890"**. Sí tiene CLABE registrada. Botón "Pagar comisiones".

Claudia Ibarra Soto (la reviso por el punto 3): su ficha dice "Comisiones mes anterior: $0 — Sin movimientos". No tiene sección de CLABE ni botón de pago visible (solo aparece cuando hay algo pendiente). No es aplicable a ella este mes — ver más abajo.

**Conclusión tarea 1: un solo socio con comisión de noviembre por pagar — Verónica Sandoval Ruiz, $393.60, con CLABE registrada.**

### 9:30 — Tarea 2: registrar el depósito

Antes de nada, hago mi propio comprobante de prueba. Desde terminal, con Node, generé un PNG de 1×1 píxel real (70 bytes) en mi carpeta de trabajo — no es un comprobante real, es un archivo de prueba que yo misma fabriqué para tener algo que subir.

En la ficha de Verónica, doy clic en "Pagar comisiones" y se abre un modal **"Cargar comprobante"** ("Cliente: Verónica Sandoval Ruiz") con un campo "Comprobante (PDF o imagen)" y botones Cancelar / Subir comprobante (este último sale deshabilitado hasta que subo el archivo). Cargo mi PNG de prueba, el botón se habilita, doy "Subir comprobante".

Confirmación en pantalla (toast): **"Comprobante cargado."** No hay ningún número de folio en el mensaje ni en la ficha después.

Verifico refrescando: el contador de "Acciones urgentes" bajó de "2 urgentes" a "1 urgentes" (ya solo queda "1 pedidos pagados sin envío"). Y en "Clientes" el total "Comisiones por depositar" pasó de $393.60 a **$0**. Vuelvo a abrir la ficha de Verónica: ahora dice **"Comisiones mes anterior: $393.60 — Pagada"** con un enlace **"Ver comprobante"**. Le doy clic para confirmar que el archivo quedó: no abre pestaña nueva, no descarga nada, no navega — se queda igual, sin error en consola. No pude verificar visualmente el archivo subido desde ese enlace, pero el estado "Pagada" y el $0 en comisiones por depositar sí confirman que el pago quedó registrado.

**Conclusión tarea 2: depósito registrado a Verónica Sandoval Ruiz por $393.60, comprobante subido (PNG de prueba fabricado por mí), confirmación exacta: "Comprobante cargado." Sin folio visible en ningún lado.**

### 9:52 — Tarea 3: Claudia Ibarra y los $172 "bloqueados"

Abro la ficha de Claudia Ibarra Soto. Su sección de comisiones dice, textual:

> Comisiones mes actual: $0
> Por confirmar: $0
> Comisiones mes anterior: **$0**
> **Sin movimientos**

No hay ninguna mención a los $172, ni a "bloqueada", ni a que se haya perdido o expirado nada — simplemente no aparece. No tiene botón de "Pagar comisiones" ni campo de CLABE (esa sección solo sale cuando hay un pendiente). En su bitácora de contactos: "Sin notas todavía." — tampoco hay ninguna nota administrativa sobre esos $172.

**Conclusión tarea 3: el sistema no muestra registro alguno de los $172 bloqueados de noviembre en la ficha de Claudia. Con el mes cerrado, su comisión de noviembre simplemente aparece en $0, "Sin movimientos" — no hay mensaje de que se haya cancelado, vencido o transferido.**

### 10:05 — Tarea 4: Cuadro de Honor / ranking de noviembre

Entro a **Cuadro de Honor**. Arriba dice: "Mes: **2026-12**" (diciembre, el mes actual) — es un texto fijo, no encontré ningún selector de mes en esta pantalla (los controles que hay son solo "Por VG", "Por VP", "Alfabético" para ordenar la tabla del mes actual). Como estamos a inicios de diciembre, todo el ranking sale en cero: los primeros 10 lugares muestran VG=0, VP=0 para todos (Prueba Reenvio, Roberto Chávez Mena, Rosa Elena Mendoza, Guadalupe Ochoa Lara...). **No hay forma de ver aquí el Cuadro de Honor de noviembre.**

Como alternativa reviso **Estadísticas** con el periodo "Noviembre de 2026" (que es el que carga por default): tiene una tabla "Top clientes del periodo" pero es por pedidos/monto de compra, no el ranking de red (VG/VP) del Cuadro de Honor:
1. Rosa Elena Mendoza — 1 pedido, $829
2. Hector Lara — 1 pedido, $609
3. Patricia Solís Ek — 1 pedido, $829

No es lo mismo que "por red y por personal" que pide la tarea, así que lo dejo anotado como aproximación, no como el ranking real de noviembre.

**Conclusión tarea 4: el sistema NO permite ver el Cuadro de Honor de un mes cerrado (noviembre); solo muestra el mes en curso (diciembre), y en diciembre todo está en cero porque acaba de empezar.**

### 10:20 — Tarea 5: empleada duplicada

Entro a **Empleados**: 6 empleados, el primero de la lista es **"Veronica Sandoval Ruiz TEST"** (veronica.sandoval.coach@findingu.mx), estatus "Activo". No hay botón "Desactivar" ni "Eliminar" junto a su nombre en la lista ni en su ficha — solo "Guardar datos", "Generar nueva contraseña" y, en la sección de permisos, una casilla **"Acceso a panel admin — Habilitado"** con "Guardar permisos".

Desmarco esa casilla y doy "Guardar permisos". Toast: **"Permisos del empleado guardados."** Miré la llamada de red que se dispara: es un `PATCH` a `/auth/employees/1794474655789/privileges` que sí manda `"canAccessAdmin": false` y responde con status 200 — pero el cuerpo de esa misma respuesta trae `"canAccessAdmin": true`. Al recargar la ficha desde cero, la casilla sigue marcada y el empleado sigue "Activo" en la lista.

**Conclusión tarea 5: intenté desactivarla (desmarcar "Acceso a panel admin" + Guardar permisos) y la pantalla dijo que se guardó, pero no se guardó de verdad — el servidor la regresa siempre en `canAccessAdmin: true`. No encontré ningún otro control para desactivarla sin borrarla. Mandé pregunta a Sistemas.**

### Mensajes que mandé
📱 A Sistemas: en Empleados, ficha de 'Veronica Sandoval Ruiz TEST', desmarqué 'Acceso a panel admin' y di Guardar permisos (toast: 'Permisos del empleado guardados.'). El PATCH a /auth/employees/.../privileges mandó canAccessAdmin:false y respondió 200, pero el JSON de respuesta trae canAccessAdmin:true — y al recargar la ficha sigue en 'Activo' con la casilla marcada. No encontré botón de 'Desactivar empleado' en la pantalla. ¿Así está pensado (no se puede quitar acceso admin desde ahí) o es un bug?

### Lo que no pude hacer
- No pude desactivar a "Veronica Sandoval Ruiz TEST": la pantalla acepta el cambio (toast de éxito) pero el servidor no lo persiste (ver arriba). Sigue "Activo".
- No pude ver el Cuadro de Honor de noviembre: la pantalla solo muestra el mes en curso, sin selector de mes.
- No pude confirmar visualmente el contenido del comprobante subido a Verónica: el enlace "Ver comprobante" no abrió pestaña, no descargó nada ni dio error — se quedó igual, sin explicación en pantalla.
- No encontré ningún folio o número de referencia para el pago de comisión de Verónica — solo el toast "Comprobante cargado."

### Lo que preguntaría
- ¿La casilla "Acceso a panel admin" en Empleados de verdad sirve para desactivar a alguien, o es solo decorativa/con bug? (ya la mandé a Sistemas)
- ¿Dónde quedó el registro de los $172 bloqueados de Claudia de octubre-noviembre? ¿Se pierden sin dejar rastro cuando no se activa, o debería aparecer en algún reporte histórico que no encontré?
- ¿Hay alguna pantalla para ver el Cuadro de Honor de meses anteriores, o solo existe para el mes en curso?
