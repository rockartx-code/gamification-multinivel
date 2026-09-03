# Diario Nadia Ruiz — 13 dic 2026, tarde

## Tarea: cobrar saldo de $340 a Roberto Chávez Mena (venta POS-D7F97B91)

1. Entré a Punto de Venta. En "Ventas registradas" (Efectivo/Tarjeta/Transferencia) el bloque
   "Efectivo" dice "0 venta(s)" / "Sin ventas en efectivo." — la venta de Roberto no está ahí
   (fue una venta en efectivo y ya se hizo un corte de caja después de registrarla).
   El bloque "Tarjeta" sí lista 2 ventas (POS-785DCAA4 Beatriz $480, POS-6947D029 Roberto
   Chávez Mena $840, ambas del 15 nov) pero ninguna trae botón de cobro adicional, solo
   folio, cliente, monto, fecha y sucursal/usuario.

2. Abrí "Ver historial de cortes". En el corte CUT-E19A0108 (13 dic 2026, 11:11 a.m.) sí
   aparece la venta que busco:
   "POS-D7F97B91 · $840 · Roberto Chávez Mena · 13 dic 2026, 11:06 a.m." y debajo, en
   "Retiros (1)": "entrega a gerencia · - $500 · 13 dic 2026, 11:10 a.m."
   Reviso el HTML de esa tarjeta de venta: solo tiene dos líneas de texto (folio+monto,
   cliente+fecha). No hay ningún botón "Cobrar saldo" ni nada clickeable dentro de esa
   tarjeta — los únicos botones de esa fila son "CSV" y "Mostrar u ocultar el detalle del
   corte", y ambos pertenecen al CORTE completo, no a la venta individual.

3. Probé click directo sobre el texto "POS-D7F97B91": no reaccionó (no es un control).

4. Revisé "Pedidos" con el buscador ("Roberto") en la pestaña Pendiente: "Sin resultados
   para 'Roberto' en este estado." — la venta de mostrador no aparece ahí tampoco.

## Conclusión
No until ahora encontré ningún botón "Cobrar saldo" en la tarjeta de la venta, ni en
"Ventas registradas" ni en "Historial de cortes" del Punto de Venta. No pude cobrar el
saldo. Caja actual sigue en $500, sin cambios (no se ejecutó ningún cobro).

Le escribí a Sofía explicando exactamente dónde busqué y lo que vi.
