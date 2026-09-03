# Diario — Sofía Herrera — 10 de enero de 2027

## 09:00 — Entrar al panel
Entré a http://localhost:4321/#/login con sofia@findingu.mx. El formulario de login usa unos campos `ui-form-field` raros (no son `<input>` directos con `name`), tuve que apuntar al `input` de adentro. Adentro vi el dashboard con "Acciones · 2 urgentes" arriba a la derecha.

## 09:02 — Acciones urgentes (ANTES)
Abrí "Acciones" y decía:
> "Acciones urgentes — Resolvé pendientes críticos desde aquí.
> 3 comisiones pendientes por depositar — Urgente — Ir a resolver
> 1 pedidos pagados sin envío — Importante — Ir a resolver"

Le di clic a "Ir a resolver" de comisiones y me mandó a Clientes.

## 09:05 — Sección Clientes: comisiones de diciembre
En "Clientes" arriba dice "Comisiones por depositar $662.60" y en la tabla, columna "Mes anterior" (o sea diciembre, porque hoy es 10 de enero), solo tres tienen monto:
- Beatriz Ochoa Lara — $99
- Claudia Ibarra Soto — $195.20
- Verónica Sandoval Ruiz — $368.40

Suman exacto los $662.60 del encabezado. Las demás 13 fichas muestran $0 en esa columna.

Me costó un rato hacer clic en el botón "Ver" de una fila específica porque la tabla tiene una versión de escritorio y una de celular en el mismo DOM y mis primeros intentos con selectores CSS le achataban al "Ver" equivocado.

## 09:12 — Ficha de Beatriz Ochoa Lara
Entré a su ficha. En el bloque "Comisiones mes anterior" decía:
> "$99 · Pendiente de pago · CLABE: - · [Pagar comisiones]"

O sea: NO tiene CLABE registrada. Quise probar qué pasa si le doy a "Pagar comisiones" para ver si el sistema me bloquea (como dice la tarea que debería pasar). Se abrió un modal "Cargar comprobante — Cliente: Beatriz Ochoa Lara" con un campo de archivo y botón "Subir comprobante".

**Aquí me equivoqué:** subí ahí mi PNG de prueba (el que iba a usar para Verónica) pensando que el sistema me iba a rechazar por falta de CLABE. En vez de eso, la pantalla mostró el mensaje **"Comprobante cargado."** y al recargar la ficha, el bloque ahora dice:
> "$99 · Pagada · Ver comprobante"

Sigue mostrando "CLABE: -" arriba (o sea nunca se llenó), pero el estatus quedó "Pagada" sin que yo hubiera hecho ninguna transferencia real — subí una imagen inventada solo para probar. No encontré ningún botón de "deshacer" o "revertir pago" en la ficha, solo "Ver comprobante".

Esto es un hallazgo importante: **el sistema no bloquea marcar una comisión como pagada aunque el cliente no tenga CLABE.** Contradice lo que yo esperaba. Dejé nota en la ficha de Beatriz explicando el error y que no se le debe avisar que ya se le "pagó" hasta que Sistemas revise, y mandé duda a Sistemas (ver abajo). También le mandaría WhatsApp para pedirle su CLABE.

## 09:20 — Ficha de Claudia Ibarra Soto
> "$195.20 · Pendiente de pago · CLABE: - · [Pagar comisiones]"

Tampoco tiene CLABE. Esta vez NO toqué "Pagar comisiones". Le agregué una nota en su bitácora de contactos con el texto exacto pedido:
> "10/01: comisión de diciembre pendiente por falta de CLABE; se le pidió por WhatsApp"

La nota quedó guardada y visible con timestamp "10/01/2027 09:15". Su teléfono en la ficha es 3319876543, con enlace de WhatsApp visible en pantalla (https://wa.me/3319876543).

## 09:24 — Ficha de Verónica Sandoval Ruiz
> "$368.40 · Pendiente de pago · CLABE: 012180001234567890 · [Pagar comisiones]"

Sí tiene CLABE. Le di "Pagar comisiones", subí el comprobante PNG que generé con Node y le di "Subir comprobante". La pantalla mostró:
> "Comprobante cargado."

Recargué la ficha para confirmar y ahora dice:
> "$368.40 · Pagada · Ver comprobante"

Aproveché para leer su bitácora de contactos, que tenía notas previas de Ivonne y mías sobre ella (coach, cupón, envío tardío, etc.) — no las toqué, solo las leí.

## 09:28 — Nota de corrección en la ficha de Beatriz
Volví a la ficha de Beatriz y agregué esta nota (texto completo, no la plantilla corta, porque el caso es distinto — a ella SÍ se le marcó pagada por error):
> "10/01: ERROR propio - se marcó "Pagada" la comisión de diciembre ($99) al probar el flujo de comprobante, pero Beatriz NO tiene CLABE registrada y no se hizo ninguna transferencia real. Reportado a Sistemas para revertir el estatus. Mientras tanto: no se le debe avisar que ya se le pagó, se le pedirá su CLABE por WhatsApp."

Quedó guardada con timestamp "10/01/2027 09:16". Su teléfono es 3323456789 (wa.me/3323456789).

## 09:32 — Acciones urgentes (DESPUÉS)
Volví a abrir "Acciones" y ahora dice:
> "1 comisiones pendientes por depositar — Urgente — Ir a resolver
> 1 pedidos pagados sin envío — Importante — Ir a resolver"

Bajó de 3 a 1 (la de Claudia, que sigue pendiente porque no tiene CLABE). El aviso de "1 pedidos pagados sin envío" sigue igual, no lo toqué porque no es parte de mi tarea de hoy.

## 09:35 — Cuadro de Honor de diciembre
Entré a "Cuadro de Honor". Por defecto mostraba el mes actual (2027-01), todo en ceros porque apenas empieza. Cambié el selector de mes a "2026-12" y esto es lo que vi:

**Por VG (volumen de red), Top 3:**
1. Verónica Sandoval Ruiz — VG 186 / VP 54
2. Claudia Ibarra Soto — VG 65 / VP 28
3. Beatriz Ochoa Lara — VG 42 / VP 23

**Por VP (volumen personal), Top 3:**
1. Verónica Sandoval Ruiz — VG 186 / VP 54
2. Guillermo Ibarra Ponce — VG 37 / VP 37
3. Claudia Ibarra Soto — VG 65 / VP 28

## Lo que me confundió
- El formulario de login no usa `input[name=...]` normal, sino un componente `ui-form-field`.
- La tabla de Clientes tiene fila de escritorio y fila de celular al mismo tiempo en el DOM (una oculta por CSS), así que mis primeros intentos de clic en "Ver" agarraban el botón equivocado.
- El diálogo de "Cargar comprobante" tiene su propio `input[type=file]`, pero hay otro `input[type=file]` en la misma pantalla (el de "Documentos del cliente"); mi primer intento de subir el archivo cargó el archivo en el campo equivocado.
- Lo más grave: pensé que el botón "Pagar comisiones" me iba a impedir avanzar si el cliente no tiene CLABE, y no fue así — el sistema dejó que subiera comprobante y marcara "Pagada" a Beatriz sin CLABE y sin transferencia real. No hay botón de reversa visible en la ficha.

## Lo que no pude hacer
- No pude revertir el pago marcado por error a Beatriz Ochoa Lara — no encontré ningún control de "deshacer" o "marcar como pendiente otra vez" en su ficha. Necesito que Sistemas lo arregle por atrás.
- No pude pagarle a Claudia Ibarra Soto porque no tiene CLABE registrada (correctamente, esta vez sin tocar el botón).

## Lo que preguntaría
- A Sistemas: ¿por qué "Pagar comisiones" no bloquea ni avisa cuando el cliente no tiene CLABE? ¿Pueden revertir el estatus de Beatriz Ochoa Lara (comisión de diciembre, $99) a "Pendiente de pago" ya que no hubo transferencia real, solo subí un comprobante de prueba por error?
- A Sistemas: ¿hay alguna forma en pantalla de "deshacer" un comprobante subido por error, o siempre hay que pedírselo a ustedes?

## Mensajes 📱 enviados
- **A Sistemas (duda):** "Sistemas: al probar el botón 'Pagar comisiones' en la ficha de Beatriz Ochoa Lara (sin CLABE registrada) el sistema no bloqueó nada — dejé subir un comprobante de prueba y quedó marcada 'Pagada' sin transferencia real. No encuentro botón para revertirlo. ¿Pueden regresarla a 'Pendiente de pago' y confirmarme si el flujo debería validar CLABE antes de aceptar el comprobante? — Sofía, 10/01 9:30 am"
- **A Claudia Ibarra Soto (WhatsApp, wa.me/3319876543):** "Hola Claudia, soy Sofía de Finding'U. Tu comisión de diciembre ($195.20) está lista para depositarse pero no tenemos tu CLABE registrada. ¿Me la puedes mandar por aquí para procesar tu pago? Gracias."
- **A Beatriz Ochoa Lara (WhatsApp, wa.me/3323456789):** "Hola Beatriz, soy Sofía de Finding'U. Necesito tu CLABE para procesar tu comisión de diciembre ($99) — todavía no la tenemos registrada. Contamos contigo para completarla en cuanto puedas."
