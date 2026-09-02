# Diario de Sofía Herrera — sábado 6 de septiembre de 2026, 1:30 pm

Llego a la oficina un sábado a mediodía porque me llegaron tres mensajes desde el jueves: Beto sobre entregas e inventario, Ivonne sobre una clienta que pidió no ser contactada, y soporte técnico avisándome de una devolución por producto dañado. Entro con el perfil 'sofia' (la sesión del jueves seguía activa) y reviso todo antes de contestar.

## Lo primero: el tablero de Pedidos

Entro a `#/admin`. La tarjeta "Pedidos cargados" sigue en $1,760 · 3 pedidos, pero ahora el resumen de pestañas cambió: **Entregado: 2** (antes 0), Cancelado 1 sigue igual. El "SIGUIENTE" ya no dice "Confirmar entregas", dice **"Operación al día"** primero y luego, al refrescar, **"Recibir devoluciones (1)"**. Algo nuevo pasó.

Abro **Entregado** y veo el pedido de Rodrigo Aguilar Ramírez ($960, guía FDU-2026-0001) ahora como "Entregada", con "Stock origen: Bodega Central" (antes decía "Sin stock" — con esto confirmo mi duda del jueves: esa etiqueta cambia sola según el estado del pedido, no era un problema de inventario).

## La devolución de Lucia — lo que avisó soporte

Voy a la pestaña **Por devolver** y ahí está: Lucia Fernandez, $800, estado **"En Devolución"**, guía FDU-2026-0002. Abro el detalle: producto Finding Pro 500g x1 $800, y una caja con el texto exacto:

> **"Solicitud devolución: RET-3137193D — En proceso de validación"**

Esto coincide con lo que avisó soporte (pedido ORD-8E2E57C2 es justo el de Finding Pro 500g, según la bitácora de Stocks). El sistema no muestra en ningún lado el motivo "tapa rajada" que me dio soporte — solo el folio RET-3137193D y el estado de validación. La única acción disponible es **"Recibir paquete"**. No la voy a usar todavía: no tengo ninguna prueba en pantalla de que el paquete físico ya llegó de vuelta a la bodega, solo sé que la clienta *solicitó* la devolución. Marcar "Recibir paquete" sin eso sería inventar un hecho que no puedo comprobar, igual que el jueves decidí no marcar "Entregado" sin prueba real.

## Lo de Beto — inventario de Longevit

Voy a **Stocks**. La existencia de Longevit bajó de 40 a **39** (solo 1 unidad, tal como dice Beto). En la bitácora encuentro la línea exacta:

> 06/09/2026 10:08 · Bodega Central · Longevit · **Salida por venta POS** · -1 · **Sello roto - entrega del proveedor** · usuario: -

Esto me aclara el problema: Beto NO usó el botón correcto. En vez de "Marcar dañado" (que existe en cada fila de producto, junto a "Entrada"), registró el frasco roto como si fuera una **venta de mostrador** en Punto de Venta, escribiendo el motivo a mano en una nota. Por eso "el inventario solo bajó 1" — probablemente metió los 2 frascos rotos como una sola operación de "venta" de 1 unidad, o solo alcanzó a registrar uno antes de escribirme. Reviso mi propia caja en **Punto de Venta**: "Ventas registradas: 0, No hay ventas registradas para esta caja" — pero esa es MI caja, no la de Beto; el sistema no me deja ver el corte de caja de otro operador desde aquí, así que no puedo confirmar exactamente qué venta se generó del lado de él.

Para los 10 frascos buenos que llegaron del proveedor, reviso la pantalla de Stocks: cada producto tiene un botón **"Entrada"** junto a "Marcar dañado". Confirmo en **Empleados → permisos** la descripción exacta de ese botón: *"Registrar entradas de mercancía: Suma unidades cuando llega el proveedor."* — es decir, "Entrada" ES el flujo de "llegó proveedor" que Beto buscaba, solo que no se llama así en el botón. Y el de los dañados es *"Registrar mercancía dañada: Da de baja unidades rotas o caducadas. Resta del inventario."* — ese es el que debió usar para los 2 frascos con sello roto, no el de venta POS.

También reviso el contador "Daños registrados" en Stocks: **0**. Confirma que, aunque Beto cree haber registrado 2 dañados, en el sistema no hay ningún registro oficial de "daño" — lo que hizo quedó contabilizado como una venta, no como merma.

## Lo de Ivonne — nota de "no contactar"

Entro a **Clientes**, busco a "Karla" y abro su ficha. Reviso todo el panel "Detalle del cliente": Perfil, Documentos del cliente (solo archivos), Posición en la red, Consumo de la red. No hay ningún campo de texto libre, ninguna sección de "notas" ni de "historial de contacto" en ninguna parte de la ficha. Confirmo lo que dice Ivonne: no hay dónde anotar "no contactar". Es un hueco real del sistema, no un error de ella.

## Revisión de gerente de sábado

- **Acciones** (rayo): sigue diciendo "0 urgentes" / "Todo en orden. No hay acciones urgentes pendientes." — ni la devolución de Lucia ni el problema de inventario de Beto aparecen ahí como urgentes, aunque a mí sí me lo parecen.
- **Estadísticas** (septiembre 2026): ahora "Top clientes del periodo" sí muestra nombres reales (Rodrigo $960, Lucia $800, Prueba Interna $0) — el defecto que vi el jueves (IDs en vez de nombres) ya no aparece hoy. "Pedidos por estado": delivered 1 ($0), en_devolucion 1 ($0), cancelled 1 ($0). Sigo viendo "Ventas del periodo: $0" con "33% entregados" — me sigue pareciendo inconsistente que ya haya un pedido entregado y la venta del periodo marque $0; no sé si es normal o un defecto, lo anoto para preguntarlo.
- **Clientes → Comisiones por depositar: $0** — nada pendiente de pagar todavía.
- No toqué Configuración ni Empleados hoy más que para leer las descripciones de permisos.

## Lo que sentí

Alivio rápido al ver "Entregado: 2" — pensé que Beto ya había resuelto todo solo. Luego, al leer "Sello roto... Salida por venta POS" en la bitácora, sentí ese golpe de "ya se me escapó algo mientras no estaba" — un dato mal clasificado que puede afectar las cuentas si no lo corrijo a tiempo. Con la devolución de Lucia sentí calma relativa: al menos el sistema sí tiene un lugar formal para eso (folio RET-3137193D), no como con las notas de clientes. Con lo de Ivonne sentí frustración genuina — es la segunda vez en dos días que confirmo que al sistema le falta algo básico (antes el teléfono visible, ahora las notas).

## Dónde me sentí sin control

Frente a la línea de la bitácora **"Salida por venta POS · -1 · Sello roto - entrega del proveedor"** — no puedo deshacerla ni corregirla desde ninguna pantalla que haya visto, y no sé si ya generó una "venta" fantasma en las estadísticas del negocio. Tampoco pude ver la caja de Beto para confirmar exactamente qué pasó ahí, solo la mía.

## Lo que me faltó

Una forma de corregir o anular una línea de bitácora mal clasificada. Un campo de notas/etiquetas por cliente (para "no contactar" y cosas similares). Ver el corte de caja de otros operadores, no solo el propio. Y saber si "Ventas del periodo: $0" con pedidos ya entregados es normal o un defecto — no lo puedo comprobar solo mirando la pantalla.
