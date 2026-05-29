# Finding'U — Comparación contra la Matriz de Hallazgos (Requerimientos Mayo 2026)

> **Propósito:** Confrontar cada uno de los 20 requerimientos/hallazgos del documento del cliente
> ("FINDING'U — Requerimientos del Sistema", Mayo 2026) contra el **estado real verificado en el
> código** y contra la **matriz de pruebas E2E** (`02-matriz-pruebas-e2e.md`).
>
> **Veredicto por hallazgo:**
> - ✅ **Implementado** — el código ya cubre el requerimiento.
> - 🟡 **Parcial** — existe parte; falta lógica, configuración o UI.
> - 🐞 **Bug/Integración** — la función existe pero falla o no se comporta como se espera.
> - ❌ **Ausente** — no existe en el código revisado.
>
> Estado del cliente = columna "Status" del documento de hallazgos.

---

## Tabla resumen ejecutiva

| # | Hallazgo (cliente) | Prioridad | Status cliente | **Veredicto código** | Casos E2E |
|---|---|---|---|---|---|
| H1 | Plan de Compensación — implementación completa | Crítica | En Progreso | 🟡 Parcial | E2E-COMP-01..16 |
| H2 | Puntos en lugar de dinero (visualización) | Crítica | En Progreso | 🟡 Parcial | E2E-DASH-01..03 |
| H3 | Registro por código de referido — red no vincula | Alta | En Progreso | ✅ Backend OK / 🐞 verificar UI | E2E-REF-02, 03, 12 |
| H4 | Pérdida de datos/productos al cancelar compra | Alta | En Progreso | 🐞 Bug | E2E-CART-03, 04, 05 |
| H5 | Recoger pedido en sucursal/consultorio | Alta | En Progreso | ✅ Backend OK / 🐞 "error desconocido" | E2E-SHIP-05..08 |
| H6 | Especificar forma de pago en Punto de Venta | Alta | Pendiente | 🟡 Parcial | E2E-PAY-05, 06 |
| H7 | Códigos de descuento / pagos especiales | Alta | Pendiente | ❌ Ausente | E2E-CART-14, E2E-ADM-15 |
| H8 | Devolución — error al enviar solicitud | Alta | Pendiente | ✅ Backend OK / 🐞 integración | E2E-RET-01 |
| H9 | URL directa a la tienda | Alta | En Progreso | ❌ Ausente | E2E-SHOP-09 |
| H10 | Correo del patrocinador — botón copiar | Alta | Resuelto (ajuste) | ✅ Implementado | E2E-DASH-15, 16 |
| H11 | Reportes generales — hojas vacías/sin estructura | Alta | En Progreso | 🐞 Bug | E2E-REP-06, 07 |
| H12 | POS sucursal — opciones de pago dual | Media | En Progreso | 🟡 Parcial | E2E-PAY-05..08, E2E-ADM-12 |
| H13 | APIs de paqueterías — cálculo de envío | Media | En Progreso | 🟡 Parcial | E2E-SHIP-01..04, 09 |
| H14 | Niveles, metas y Cuadro de Honor | Media | En Progreso | ✅ / 🟡 (alineación plan) | E2E-DASH-04, 06; E2E-COMP-11 |
| H15 | Módulo de Productos Sugeridos | Media | Pendiente | 🟡 Parcial (solo frontend) | E2E-CART-08, 09 |
| H16 | Agregar PC a cada producto en catálogo | Media | Pendiente | 🟡 Parcial | E2E-SHOP-07, 08 |
| H17 | Carruseles en Dashboard y Landing | Media | Pendiente | 🟡 Dashboard / ❌ Landing | E2E-DASH-09, E2E-LAND-06 |
| H18 | Acciones según perfil de usuario | Media | Pendiente | 🟡 Parcial | E2E-DASH-19, E2E-ADM-16 |
| H19 | Aviso de Privacidad del Usuario | Baja | Pendiente | ❌ Ausente | E2E-PROF-07, E2E-NOTI-06 |
| H20 | Imágenes para compartir en Redes Sociales | Media | Pendiente | 🟡 Parcial | E2E-DASH-10, 11 |

**Conteo:** ✅ 4 · 🟡 9 · 🐞 4 · ❌ 3 (con solapes donde backend OK pero UI/integración falla).

---

## Detalle por hallazgo

### H1 — Plan de Compensación: implementación completa · 🟡 Parcial
**Estado cliente:** Crítica / En Progreso.
**Hallazgo código:** El **motor** del plan está implementado y es configurable (VP, VG, comisiones por generación, rangos, bonos, activación, inicio rápido). Sin embargo, **la configuración por defecto NO corresponde al plan de abril 2026**:

| Regla del plan (abril 2026) | Implementación actual | Brecha |
|---|---|---|
| 1 PC ≈ $50 MXN | `mxnPerVp = 50` (`commissions_lambda.py:334`) | ✅ Coincide |
| PC proporcionales al neto (× (1−%desc)) | Factor de descuento aplicado (`commissions_lambda.py:84-87`) | ✅ |
| Activación $1,000 MXN netos/mes | `activationNetMin = 50` (VP) | 🟡 Umbral en VP, no $1,000 MXN |
| Escalera descuentos 0/10/20/30/40% | `discountTiers = []` (vacío); regla *hardcoded* 30% en `order_lambda.py:50-69` | 🟡 No cargada según plan |
| Comisiones Gen1–Gen5 (10/5/4/3/2), tope 24% | Config 2 niveles (10/5); `default_rates` 3 (10/5/3) | 🟡 Faltan Gen4/Gen5 |
| Desbloqueo Gen2–Gen5 (PC + directos + líneas) | Bloqueo solo por activación del beneficiario | 🟡 Falta lógica de líneas/PC |
| Compresión dinámica | `cutRule = "hard_cut_no_pass"` | 🟡 Sin traspaso ascendente |
| Rangos Bronce/Plata/Oro/Platino/Diamante | ORO/PLATINO/DIAMANTE (700/2000/6000) | 🟡 Faltan Bronce y Plata |
| Bono por rango desde 4º mes (Bronce $500…Diamante $10,000) | Bonos distintos (Smart TV, viaje, 2/3 meses) | 🟡 Config difiere |
| Bono inicio rápido $5,000 / 600 PC / 30 días | `inicio_rapido` first_30_days + direct_vg_min 600 → $5,000 | ✅ Coincide |
| Tabla de PC oficiales por producto | `vpPoints` por producto | 🟡 Falta tabla oficial completa |

**Evidencia:** `commissions_lambda.py:50-426`, `order_lambda.py:50-69`.
**Acción QA:** ejecutar E2E-COMP-01..16; priorizar 05 (escalera), 06–10 (generaciones/compresión), 11–12 (rangos/bonos).

---

### H2 — Puntos en lugar de dinero (visualización) · 🟡 Parcial
**Estado cliente:** Crítica / En Progreso.
**Hallazgo código:** El backend ya entrega `vp`, `vg`, `rank` y metas en puntos (`dashboard_lambda.py`), y el dashboard expone getters `vpPoints`/`vgPoints` y nivel de descuento (`user-dashboard.component.ts:358-364`, `219-231`). **Falta verificar que TODAS las vistas (red, metas, rangos) muestren PC y no pesos**, y que se muestre claramente "PC acumulados del mes" y "faltante al siguiente nivel".
**Casos:** E2E-DASH-01, 02, 03.
**Acción QA:** auditoría visual de cada vista buscando montos en MXN donde deba haber PC.

---

### H3 — Registro por código de referido: red no vincula · ✅ Backend OK / 🐞 verificar UI
**Estado cliente:** Alta / En Progreso.
**Hallazgo código:** En backend la vinculación **sí** se resuelve y persiste: `referralToken → leaderId` (`auth_utils.py:264`), guardado en `CUSTOMER.leaderId` (`:270`), notificación al patrocinador (`:310`) y árbol de red (`costumer_lambda.py:460-518`). El frontend captura el `idSponsor`/`refToken` y lo guarda en `localStorage` (`landing.component.ts:92`).
**Posible causa del síntoma reportado** (afiliado no aparece en la red / patrocinador no aparece en perfil): desincronización del árbol de red persistido, `leaderId` no propagado al payload de registro desde el frontend en algún flujo, o caché de dashboard. **Requiere reproducción E2E.**
**Casos:** E2E-REF-02, E2E-REF-03, E2E-REF-12 (y E2E-PROF-06).
**Acción QA:** registrar con código y validar (a) red del patrocinador, (b) perfil del afiliado, (c) `CUSTOMER.leaderId` en BD; ejecutar `network-tree/rebuild` si aplica.

---

### H4 — Pérdida de datos/productos al cancelar compra · 🐞 Bug
**Estado cliente:** Alta / En Progreso.
**Hallazgo código:** El carrito persiste/restaura estado de entrega (`carrito.component.ts:132,176`) y calcula totales con getters (`:375-392`), pero los síntomas reportados (alias borrado, producto fantasma con costo, suma sobre producto invisible) **apuntan a un bug de estado** entre el evento "Regresar" y el `CartControlService`. No se localizó manejo explícito del alias del afiliado en el carrito.
**Casos:** E2E-CART-03 (alias persiste), E2E-CART-04 (sin fantasma), E2E-CART-05 (suma correcta tras agregar).
**Acción QA/Dev:** reproducir "Regresar" → inspeccionar `cartItems` y totales; corregir sincronización del subject y conservar alias.

---

### H5 — Recoger pedido en sucursal/consultorio · ✅ Backend OK / 🐞 "error desconocido"
**Estado cliente:** Alta / En Progreso.
**Hallazgo código:** El backend soporta `deliveryType=pickup`, `pickupStockId`, `pickupPaymentMethod` (`online`/`at_store`) y registra venta en sucursal (`order_lambda.py:129,495-501`); el frontend carga sucursales (`carrito.component.ts:963`). El reporte de **"error desconocido"** al seleccionar pickup es un **bug de integración frontend↔API** (validación o payload). Falta confirmar el mensaje de confirmación exacto y el ocultamiento del botón Mercado Pago.
**Casos:** E2E-SHIP-05, 06 (sin "error desconocido"), 07 (aviso de stock), 08 (mensaje + sin botón MP).
**Acción QA:** reproducir selección de pickup y capturar la respuesta de API que produce el error.

---

### H6 — Forma de pago en Punto de Venta · 🟡 Parcial
**Estado cliente:** Alta / Pendiente.
**Hallazgo código:** El POS sí soporta métodos de pago (efectivo/tarjeta/transferencia) y los pedidos pickup `at_store` generan `POS_SALE` con `paymentMethod` (`order_lambda.py:557-566`; `admin.component.ts:337`). **Falta el campo visible/editable de método al gestionar un pedido pickup pago-en-sucursal desde el detalle del pedido** (no solo "Cambiar estado").
**Casos:** E2E-PAY-05, 06.
**Acción Dev:** añadir selector de método en la gestión del pedido pickup `at_store`.

---

### H7 — Códigos de descuento / pagos especiales · ❌ Ausente
**Estado cliente:** Alta / Pendiente.
**Hallazgo código:** **No existe** módulo de cupones ni endpoint de descuento por código en backend (búsqueda sin coincidencias en `Micro-lambda-GMF/python/`). Solo hay descuento por volumen y descuento/crédito de cajero en POS. Falta soporte para pago parcial, crédito, descuento manual y pago manual configurables, y los permisos asociados.
**Casos:** E2E-CART-14 (cupón en checkout), E2E-ADM-15 (módulo admin).
**Acción Dev:** diseñar e implementar módulo de códigos de descuento + permisos.

---

### H8 — Devolución: error al enviar solicitud · ✅ Backend OK / 🐞 integración
**Estado cliente:** Alta / Pendiente.
**Hallazgo código:** El flujo de devolución **sí** está implementado de extremo a extremo: solicitud con motivo/plazo/evidencia (`order_lambda.py:822-982`), inspección (`:989-1101`), reembolso (`:1104-1154`) y reversión de comisiones. El mensaje "No se pudo enviar la solicitud" es un **bug de integración** (probable: subida de evidencia a S3, tamaño de imágenes base64, o validación de las 3 categorías).
**Casos:** E2E-RET-01 (envío exitoso), 06 (evidencia incompleta), 12 (ajuste de PC/volumen).
**Acción QA/Dev:** reproducir con evidencia de las 3 categorías y revisar payload/límites de carga.

---

### H9 — URL directa a la tienda · ❌ Ausente
**Estado cliente:** Alta / En Progreso.
**Hallazgo código:** Solo existe la ruta hash `/#/tienda` (`app.routes.ts`); no hay subdominio/redirección tipo `tienda.findingu.com.mx`. Es tarea de **infraestructura/routing** (DNS + configuración), no de código de componente. Además los textos del home del landing siguen pendientes.
**Casos:** E2E-SHOP-09, E2E-LAND-07.
**Acción Dev/Infra:** definir subdominio y redirección; cargar textos del home.

---

### H10 — Correo del patrocinador: botón copiar · ✅ Implementado
**Estado cliente:** Alta / Resuelto (pendiente ajuste).
**Hallazgo código:** El correo del patrocinador es visible y el click ejecuta **`copyText(sponsorContact.email)`** además del `mailto` (`user-dashboard.component.html:477-480`; `user-dashboard.component.ts:481`). Cumple el requisito de copiar en escritorio aunque no haya cliente de correo.
**Casos:** E2E-DASH-15, 16.
**Acción QA:** confirmar feedback visual ("Copiado") y separar idealmente ícono de copiar del `mailto` para claridad UX.

---

### H11 — Reportes generales: hojas vacías/sin estructura · 🐞 Bug
**Estado cliente:** Alta / En Progreso.
**Hallazgo código:** La exportación XLSX existe y arma varias hojas (`admin.component.ts:1805-1983`), pero usa `XLSX.utils.json_to_sheet(rows)`: **si `rows` está vacío, la hoja sale sin encabezados de columna**, justo el síntoma reportado. Solución: emitir encabezados fijos (usar `header` en `json_to_sheet` o `aoa_to_sheet` con fila de títulos) aunque no haya datos.
**Casos:** E2E-REP-06 (encabezados sin datos), 07 (catálogo de reportes), 08 (mes vacío).
**Acción Dev:** forzar encabezados en todas las hojas y definir el set de reportes requeridos (ventas, red, comisiones, rangos, actividad mensual).

---

### H12 — POS sucursal: opciones de pago dual · 🟡 Parcial
**Estado cliente:** Media / En Progreso.
**Hallazgo código:** Existe `pickupPaymentMethod` (`online`/`at_store`) y registro de venta en sucursal. **Falta la UI dual explícita** al confirmar ("Pagar en línea" vs "Pagar en sucursal"), el ocultamiento del botón MP en `at_store`, y la **notificación interna al operador** del consultorio.
**Casos:** E2E-PAY-05..08, E2E-ADM-12.
**Acción Dev:** UI de elección dual + aviso al operador.

---

### H13 — APIs de paqueterías: cálculo de envío · 🟡 Parcial
**Estado cliente:** Media / En Progreso.
**Hallazgo código:** Hay endpoint `POST /shipping/quote` y lógica de cotización (`shipping_lambda.py`; doc `envia_quote.md` para Envia.com). **Falta** confirmar viabilidad/configuración productiva del proveedor (token/entorno), aviso de stock en sucursal, y **generación de guías** (no implementada).
**Casos:** E2E-SHIP-01..04 (cotización), 09 (guía ausente).
**Acción Dev:** validar integración Envia.com con credenciales y agregar generación de guía.

---

### H14 — Niveles, metas y Cuadro de Honor · ✅ / 🟡 (alineación con plan)
**Estado cliente:** Media / En Progreso.
**Hallazgo código:** Metas dinámicas (`dashboard_lambda.py:309-483`) y Cuadro de Honor Top 10 por VG/VP con deltas y modal (`dashboard_lambda.py:1034`; `user-dashboard.component.ts:370`) **están implementados y visibles desde el primer mes**. La brecha es de **alineación de rangos** con el plan de abril (Bronce/Plata faltantes — ver H1).
**Casos:** E2E-DASH-04, 06; E2E-COMP-11.
**Acción Dev:** alinear `rankThresholds` y requisitos al documento final.

---

### H15 — Módulo de Productos Sugeridos · 🟡 Parcial (solo frontend)
**Estado cliente:** Media / Pendiente.
**Hallazgo código:** Hay sugeridos por **scoring de tags solo en frontend** (`carrito.component.ts:204-240`) y "buy again" en backend (`dashboard_lambda.py:485-493`). **Falta definir y documentar la lógica oficial** (categoría/historial/manual) y unificarla.
**Casos:** E2E-CART-08, 09.
**Acción Producto/Dev:** definir criterio y, si aplica, moverlo a backend.

---

### H16 — Agregar PC a cada producto en catálogo · 🟡 Parcial
**Estado cliente:** Media / Pendiente.
**Hallazgo código:** El campo `vpPoints` existe en modelo y backend (`catalog_lambda.py:79,217`; `admin.model.ts:284`). **Falta la visualización en tarjeta de producto** de (a) PC oficiales y (b) PC netos según descuento vigente, y **validar la carga de los 13 productos**.
**Casos:** E2E-SHOP-07, 08; E2E-COMP-14.
**Acción Dev:** mostrar PC en `ui-product-card` y verificar datos cargados.

---

### H17 — Carruseles en Dashboard y Landing · 🟡 Dashboard / ❌ Landing
**Estado cliente:** Media / Pendiente.
**Hallazgo código:** El **dashboard** ya tiene carrusel de destacados con paginación (`user-dashboard.component.ts:291,1412`) — falta confirmar las **3 posiciones** donde está "Producto del mes". El **landing NO tiene** el carrusel de 2 posiciones (Tienda/Conoce el sistema).
**Casos:** E2E-DASH-09 (3 posiciones), E2E-LAND-06 (landing, ausente).
**Acción Dev:** ajustar dashboard a 3 posiciones; implementar carrusel del landing.

---

### H18 — Acciones según perfil de usuario · 🟡 Parcial
**Estado cliente:** Media / Pendiente.
**Hallazgo código:** Existe control de privilegios y `getFirstAllowedView()` en admin (`admin.component.ts:675`), y distinción guest/cliente en dashboard (`user-dashboard.component.ts:233`). **Falta filtrado fino** de avisos/acciones por rol (que un cliente no afiliado no vea red/comisiones).
**Casos:** E2E-DASH-19, E2E-ADM-16.
**Acción Dev:** filtrar notificaciones y acciones por rol.

---

### H19 — Aviso de Privacidad del Usuario · ❌ Ausente
**Estado cliente:** Baja / Pendiente.
**Hallazgo código:** No se encontró aviso de privacidad en `src/` ni `public/`. Debe mostrarse al registro o primer acceso (sin banner de cookies ni analytics, según el requerimiento).
**Casos:** E2E-PROF-07, E2E-NOTI-06.
**Acción Dev:** agregar aviso general de privacidad.

---

### H20 — Imágenes para compartir en Redes Sociales · 🟡 Parcial
**Estado cliente:** Media / Pendiente.
**Hallazgo código:** El dashboard ya permite compartir con canal/formato y copia link+copy+imagen (`user-dashboard.component.ts:1449,1467,2153`) usando **assets de campaña/featured**. **Falta el set de piezas dedicadas** por tamaño (Instagram/WhatsApp/Facebook) **personalizables con el código de referido**.
**Casos:** E2E-DASH-10, 11.
**Acción Diseño/Dev:** definir piezas y tamaños; personalizar con código del afiliado.

---

## Recomendaciones de priorización para QA y desarrollo

1. **Crítica inmediata (bugs que rompen flujos):**
   - H4 (carrito fantasma) → E2E-CART-03/04/05
   - H5 (pickup "error desconocido") → E2E-SHIP-06
   - H8 (devolución falla) → E2E-RET-01
   - H3 (vinculación de red visible) → E2E-REF-02/03/12
   - H11 (reportes sin encabezados) → E2E-REP-06

2. **Crítica de negocio (alineación con plan abril 2026):**
   - H1 + H2 + H14 + H16 → E2E-COMP-* y E2E-DASH-01..03

3. **Faltantes a construir:**
   - H7 (cupones), H9 (URL/subdominio), H17 (carrusel landing), H19 (aviso privacidad), H12 (UI pago dual + aviso operador), H6 (forma de pago en pedido pickup), H13 (guías de paquetería), H20 (piezas para redes).

4. **Ya cubierto (validar y cerrar):**
   - H10 (copiar correo patrocinador) → E2E-DASH-15/16.

> **Nota metodológica:** varios hallazgos catalogados por el cliente como "Pendiente/En Progreso"
> ya tienen **backend funcional**; el trabajo restante es de **frontend/integración/UX o de
> configuración del plan**, no de construir el motor desde cero. Esto reduce el esfuerzo real
> de H3, H5, H8, H14 y H16.
