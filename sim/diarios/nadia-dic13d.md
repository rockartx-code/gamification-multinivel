# Nadia — 13 dic 2026, 5 pm

Entré a Punto de Venta. Arriba de "Ventas registradas" apareció la sección nueva:

> **Saldos pendientes (1)**
> Ventas con pago parcial de esta sucursal, aunque ya estén en un corte. Cobra el resto cuando el cliente regrese.
> POS-D7F97B91 · Roberto Chávez Mena
> Total $840 · pagado $500 · 13 dic 2026, 11:06 a.m.
> Saldo $340
> [Cobrar saldo]

Antes de cobrar, Caja actual: **$500**, Ventas en caja: 2.

Pulsé "Cobrar saldo". La pantalla preguntó, en este orden:
1. "Saldo pendiente de POS-D7F97B91: $340. ¿Cuánto abona el cliente?" → contesté 340 (el saldo completo).
2. "Forma de pago del abono: efectivo, tarjeta o transferencia" → contesté tarjeta.

Confirmación en pantalla: **"Abono registrado. Venta liquidada."**

Al recargar Punto de Venta:
- La sección "Saldos pendientes" **ya no aparece** (Roberto salió de ahí).
- "Ventas en caja" subió de 2 a 3.
- Caja actual sigue en **$500**, sin cambio (correcto, era tarjeta).
- "Ventas registradas" del corte (efectivo) sigue en 0.
- En "Ventas registradas → Tarjeta" ahora hay 3 ventas, con una nueva línea: **POS-D7F97B91 · Roberto Chávez Mena · $340 · 13 dic 2026, 11:31 a.m.**, además de las dos que ya estaban (POS-785DCAA4 Beatriz $480 y POS-6947D029 Roberto $840).

Todo cuadra: Roberto quedó liquidado, el abono no tocó el efectivo de caja y sí quedó registrado como venta por tarjeta separada.

📱 A Sofía: "Ya cobré el saldo de Roberto: pedí el monto, contesté 340, elegí tarjeta y salió 'Abono registrado. Venta liquidada.' Roberto desapareció de Saldos pendientes, la caja se quedó en $500 y el abono de $340 aparece en Ventas registradas → Tarjeta. Gracias, ahora sí quedó donde se veía."

Capturas:
- nadia-dic13d-01-postlogin.png
- nadia-dic13d-02-pos.png (antes de cobrar)
- nadia-dic13d-03-tras-cobro.png (justo tras el clic, toast visible)
- nadia-dic13d-04-recargada.png (estado final tras recargar)
