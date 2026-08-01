# Finding'U — Historias de Usuario: Tienda, Carrito, Checkout y Ciclo de Vida de Órdenes

> **Propósito:** Documentar como Historias de Usuario (HU) el comportamiento **realmente
> implementado** en el código de Finding'U para el dominio de tienda pública, carrito, checkout
> (entrega, envío, pago) y ciclo de vida de órdenes (seguimiento, cancelación, devolución) y sus
> efectos sobre comisiones. Construido por ingeniería inversa directa sobre el código, no sobre
> especificación previa.
>
> **Fecha:** 2026-08-01
> **Método:** Lectura de `docs/qa/01-funcionalidades-sistema.md` y
> `docs/qa/02-matriz-pruebas-e2e.md` como base, verificada y ampliada con lectura dirigida de
> `gamificacion-multinivel-f/lambda/handler.py` (backend monolito) y de los componentes
> `pages/tienda`, `pages/carrito`, `pages/order-status`, `pages/order-cancelacion`,
> `pages/order-devolucion` y los servicios `cart-control.service.ts`, `goal-control.service.ts`,
> `real-api.service.ts`. Cada HU refleja lo que el código hace hoy, incluyendo bugs y huecos
> frontend/backend detectados durante la revisión.
>
> **Alcance:** `/tienda`, `/tienda/:refToken`, `/carrito`, `/orden/:idOrden`,
> `/orden/:idOrden/cancelar`, `/orden/:idOrden/devolucion`.

## Tabla resumen

| ID | Título | Prioridad | E2E vinculados |
|---|---|---|---|
| HU-SHOP-01 | Listado y filtro del catálogo público | Alta | E2E-SHOP-01, E2E-SHOP-02, E2E-SHOP-10 |
| HU-SHOP-02 | Producto hero con variantes y precio dinámico | Media | E2E-SHOP-03 |
| HU-SHOP-03 | Agregar producto al carrito desde la tienda | Alta | E2E-SHOP-04, E2E-SHOP-05 |
| HU-SHOP-04 | Contador y subtotal del carrito visibles en la tienda | Media | SIN COBERTURA EN MATRIZ |
| HU-SHOP-05 | Acceso a la tienda con token de referido persistente | Alta | E2E-SHOP-06, E2E-REF-04, E2E-REF-13 |
| HU-SHOP-06 | Registro de cuenta desde la tienda capturando el referido | Alta | E2E-SHOP-06, E2E-REF-04 |
| HU-SHOP-07 | Editar cantidades y eliminar productos del carrito | Alta | E2E-CART-01, E2E-CART-02 |
| HU-SHOP-08 | Persistencia y restauración del estado de entrega | Media | E2E-CART-07 |
| HU-SHOP-09 | El subtotal del carrito impacta el progreso de la meta activa | Alta | SIN COBERTURA EN MATRIZ |
| HU-SHOP-10 | Productos sugeridos por afinidad de tags | Media | E2E-CART-08, E2E-CART-09 |
| HU-SHOP-11 | Aplicar código de cupón en el carrito | Baja | E2E-CART-14 (matriz desactualizada) |
| HU-SHOP-12 | Elegir tipo de entrega: domicilio o recoger en sucursal | Alta | E2E-CART-13, E2E-SHIP-05 |
| HU-SHOP-13 | Validación del formulario de entrega a domicilio | Alta | E2E-CART-11, E2E-CART-12 |
| HU-SHOP-14 | Selección de dirección de envío guardada | Media | E2E-CART-10 |
| HU-SHOP-15 | Cotización automática de envío por destino y peso | Alta | E2E-SHIP-01, E2E-SHIP-02, E2E-SHIP-03, E2E-SHIP-04 |
| HU-SHOP-16 | Recoger en sucursal con método de pago en línea o en tienda | Alta | E2E-SHIP-05, E2E-SHIP-06, E2E-SHIP-07 |
| HU-SHOP-17 | Ver el nivel de descuento por volumen de consumo en el carrito | Alta | E2E-COMP-05 |
| HU-SHOP-18 | Comprar como invitado sin crear cuenta | Alta | E2E-CART-15, SIN COBERTURA EN MATRIZ (bug de comisión) |
| HU-SHOP-19 | Crear cuenta desde el modal de invitado en el carrito | Media | SIN COBERTURA EN MATRIZ |
| HU-SHOP-20 | Confirmar el pedido y ser redirigido al seguimiento | Crítica | E2E-CART-13 |
| HU-SHOP-21 | Pagar con Mercado Pago desde el seguimiento de la orden | Crítica | E2E-PAY-01, E2E-ORD-02 |
| HU-SHOP-22 | El webhook de Mercado Pago actualiza el estado de la orden | Alta | E2E-PAY-04 |
| HU-SHOP-23 | Confirmación de pedido con pago en sucursal (pickup at_store) | Alta | E2E-SHIP-08, E2E-PAY-08 (matriz desactualizada) |
| HU-SHOP-24 | Seguimiento de orden: estado, timeline y montos | Alta | E2E-ORD-01, E2E-PAY-02, E2E-PAY-03 |
| HU-SHOP-25 | Aviso de corte de descuento mensual en pedido pendiente | Media | SIN COBERTURA EN MATRIZ |
| HU-SHOP-26 | Cancelar un pedido pendiente o pagado | Alta | E2E-ORD-03, E2E-ORD-04, E2E-ORD-05 |
| HU-SHOP-27 | Solicitar devolución de un pedido entregado | Alta | E2E-RET-01 a E2E-RET-08 (matriz desactualizada) |
| HU-SHOP-28 | El pago de un pedido genera comisiones pendientes en la red | Crítica | E2E-PAY-04, E2E-COMP-06 |
| HU-SHOP-29 | La entrega confirmada convierte comisiones pendientes en confirmadas | Alta | E2E-ORD-06 |
| HU-SHOP-30 | Cancelar o reembolsar un pedido pagado revierte sus comisiones | Alta | E2E-ORD-07, E2E-RET-12 |
| HU-SHOP-31 | Comisión única (10%) al referidor por compra de invitado | Media | SIN COBERTURA EN MATRIZ (bug de integración) |

---

### HU-SHOP-01 — Listado y filtro del catálogo público
**Como** visitante **quiero** ver el catálogo de productos activos y filtrarlo por categoría **para** encontrar lo que quiero comprar sin necesidad de iniciar sesión.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que entro a `/tienda`, cuando la página carga, entonces solo se listan productos con `inOnlineStore !== false` (`tienda.component.ts:254`).
- Dado el catálogo cargado, cuando selecciono una categoría, entonces la lista se filtra por `categoryIds` de cada producto (`tienda.component.ts:140-147`); solo se muestran categorías realmente usadas por algún producto activo (`availableCategories`, `tienda.component.ts:135-138`).
- Dado que no hay productos activos, cuando la tienda carga, entonces `allProducts` queda vacío y la vista no lanza error (no hay manejo explícito de "estado vacío" dedicado; depende del template).
**Fuente (código):** `gamificacion-multinivel-f/src/app/pages/tienda/tienda.component.ts:135-267`
**Cobertura E2E:** E2E-SHOP-01, E2E-SHOP-02, E2E-SHOP-10

### HU-SHOP-02 — Producto hero con variantes y precio dinámico
**Como** visitante **quiero** ver el producto destacado con sus variantes y su precio actualizado según la variante elegida **para** decidir qué comprar.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado un producto destacado (por `?p=`, campaña `campaign:` o producto del mes), cuando la tienda carga, entonces se resuelve el hero desde la query, la campaña o `productOfMonth`, en ese orden de prioridad (`pickFromQuery`, `pickDefaultProduct`, `tienda.component.ts:269-287`).
- Dado que el producto tiene variantes activas, cuando selecciono una variante, entonces el precio (`heroPrice`) y la imagen (`heroImage`) cambian a los de esa variante (`tienda.component.ts:124-165`).
- Dado que no hay `selectedVariantId`, cuando se muestra el hero, entonces se usa el precio/imagen base del producto o del hero por defecto ("COLÁGENO").
**Fuente (código):** `tienda.component.ts:117-165`, `269-323`
**Cobertura E2E:** E2E-SHOP-03

### HU-SHOP-03 — Agregar producto al carrito desde la tienda
**Como** visitante o asociado **quiero** agregar el producto destacado al carrito **para** continuar mi compra.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un producto/variante seleccionados, cuando presiono "Agregar al carrito", entonces se agrega un ítem con el precio de la variante (si existe) o el precio base, con `qty=1` (`tienda.component.ts:182-192`).
- Dado que agrego el mismo producto varias veces, cuando reviso el carrito, entonces la cantidad se acumula vía `CartControlService.addItem`.
- Dado que agregué al menos un producto, cuando presiono "Ir al carrito", entonces navego a `/carrito` (`tienda.component.ts:194-196`).
**Fuente (código):** `tienda.component.ts:182-196`
**Cobertura E2E:** E2E-SHOP-04, E2E-SHOP-05

### HU-SHOP-04 — Contador y subtotal del carrito visibles en la tienda
**Como** visitante **quiero** ver cuántos productos llevo y el subtotal mientras navego la tienda **para** saber el estado de mi compra sin entrar al carrito.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que tengo productos en el carrito, cuando estoy en `/tienda`, entonces `cartCount` y `cartSubtotal` reflejan el estado actual de `CartControlService` (`tienda.component.ts:110-111`).
- Dado que el carrito cambia (otra pestaña o acción), cuando `cartControl.data$` emite, entonces la vista se refresca automáticamente (`tienda.component.ts:102-106`).
- Dado un usuario con meta de gasto activa (`activeSpendTarget > 0`), cuando reviso la tienda, entonces se exponen `cartGapToGoal` y `cartBenefitPercent` para mostrar avance hacia la meta (`tienda.component.ts:112-114`).
**Fuente (código):** `tienda.component.ts:93-115`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ

### HU-SHOP-05 — Acceso a la tienda con token de referido persistente
**Como** invitado que llega desde el link de un afiliado **quiero** que mi navegación en `/tienda/:refToken` recuerde a mi referidor **para** que mi eventual registro o compra quede vinculado a él.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que abro `/tienda/:refToken`, cuando la página carga, entonces el token se guarda en `localStorage['leaderId']` (`tienda.component.ts:93-100`).
- Dado que ya tengo un `refToken` guardado, cuando navego a otra ruta de la tienda o vuelvo, entonces el valor persiste en `localStorage` (no se limpia por la navegación del propio componente).
- Dado que el `refToken` está vacío, cuando entro a `/tienda` sin parámetro, entonces no se escribe nada en `localStorage`.
**Fuente (código):** `tienda.component.ts:93-100`
**Cobertura E2E:** E2E-SHOP-06, E2E-REF-04, E2E-REF-13

### HU-SHOP-06 — Registro de cuenta desde la tienda capturando el referido
**Como** invitado **quiero** registrarme desde la tienda usando el `refToken` capturado **para** unirme a la red de mi referidor.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado el formulario de registro con nombres, email, teléfono y contraseña+confirmación, cuando faltan campos obligatorios, entonces se bloquea con mensaje de error (`tienda.component.ts:198-207`).
- Dado que las contraseñas no coinciden, cuando envío el formulario, entonces se muestra "Las contraseñas no coinciden" (`tienda.component.ts:204-207`).
- Dado un envío válido, cuando `createAccount` responde `requiresEmailVerification`, entonces se limpia el formulario y se pide confirmar el correo, sin iniciar sesión aún (`tienda.component.ts:222-227`).
- Dado un envío válido sin verificación requerida, cuando la cuenta se crea, entonces se autentica al usuario y se redirige a `/dashboard` (`tienda.component.ts:228-234`).
- Dado un error del backend (p. ej. email duplicado), cuando `createAccount` falla, entonces se muestra el mensaje del backend o uno genérico (`tienda.component.ts:236-240`).
**Fuente (código):** `tienda.component.ts:198-243`
**Cobertura E2E:** E2E-SHOP-06, E2E-REF-04

### HU-SHOP-07 — Editar cantidades y eliminar productos del carrito
**Como** comprador **quiero** cambiar cantidades o quitar productos en `/carrito` **para** ajustar mi pedido antes de pagar.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un ítem en el carrito, cuando cambio su cantidad a un valor válido, entonces se actualiza en `CartControlService` y se muestra el toast "Cantidad actualizada." (`carrito.component.ts:496-505`).
- Dado que ajusto la cantidad a 0, cuando se aplica el cambio, entonces el producto se remueve y se muestra "Producto removido." (`carrito.component.ts:500-503`).
- Dado un ítem en el carrito, cuando presiono eliminar, entonces se quita del carrito y el total se recalcula (`carrito.component.ts:507-511`).
**Fuente (código):** `carrito.component.ts:496-511`
**Cobertura E2E:** E2E-CART-01, E2E-CART-02

### HU-SHOP-08 — Persistencia y restauración del estado de entrega
**Como** comprador **quiero** que mis datos de entrega (dirección, tipo de envío, notas) se conserven si salgo y vuelvo al carrito **para** no tener que capturarlos de nuevo.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que salgo de `/carrito`, cuando el componente se destruye, entonces se guarda el estado de entrega completo (tipo, dirección seleccionada, transportista, campos de dirección) vía `cartControl.saveDeliveryState` (`carrito.component.ts:181-198`).
- Dado que vuelvo a `/carrito`, cuando el componente inicia, entonces se restauran todos los campos guardados y, si hay datos de envío suficientes, se vuelve a cotizar el envío automáticamente (`carrito.component.ts:137-162`).
- Dado que restauro una dirección guardada previamente seleccionada, cuando el estado se restaura, entonces `hasPrefilledDashboardAddress` se marca en `true` para no sobrescribirla con el prellenado del dashboard (`carrito.component.ts:142-145`).
**Fuente (código):** `carrito.component.ts:113-198`
**Cobertura E2E:** E2E-CART-07

### HU-SHOP-09 — El subtotal del carrito impacta el progreso de la meta activa
**Como** asociado **quiero** ver cómo mi compra actual mueve el avance de mi meta de consumo mientras armo el carrito **para** decidir si agrego más productos y alcanzar el siguiente nivel.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que tengo metas cargadas, cuando `GoalControlService` combina `dashboardControl.data$` con `cartControl.data$`, entonces a las metas de consumo (`key === 'active'`, `key === 'discount'` o `key.startsWith('discount_')`) que no son de conteo y no están en unidad `vp` se les inyecta `cart = subtotal del carrito` (`goal-control.service.ts:19-37`).
- Dado que una meta está definida en puntos (`unit === 'vp'`), cuando se recalculan las metas, entonces **no** se le inyecta el subtotal del carrito en pesos (comentario explícito en el código: "VP-unit goals track volume points, not MXN cart") — es decir, el carrito solo afecta metas en MXN, no metas en PC.
- Dado el carrito y la meta activa, cuando estoy en `/carrito`, entonces `cartPercent` y `gapToGoal` se calculan sobre `target - base` de la meta activa, acotados a `[0, 100 - basePercent]` (`carrito.component.ts:288-300`, `457-480`).
**Fuente (código):** `goal-control.service.ts:19-43`; `carrito.component.ts:267-300`, `457-490`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ

### HU-SHOP-10 — Productos sugeridos por afinidad de tags
**Como** comprador **quiero** ver sugerencias relacionadas con lo que ya tengo en el carrito **para** descubrir productos complementarios.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que tengo productos en el carrito, cuando se recalculan sugerencias, entonces se puntúan los productos del catálogo por coincidencia de tags con los tags acumulados del carrito y se excluyen los que ya están en el carrito (`carrito.component.ts:209-241`).
- Dado que hay menos de 3 sugerencias con score > 0, cuando se arma la lista final, entonces se completa con productos sin score, respetando el orden original del catálogo, hasta un máximo de 3 (`carrito.component.ts:230-240`).
- Dado que agrego un producto sugerido, cuando lo confirmo, entonces se agrega al carrito y se dispara una animación de "agregado" (`carrito.component.ts:523-532`).
- Esta lógica es **puramente de frontend**: no hay endpoint de backend para "recomendaciones"; el criterio (tags/badge del producto) no está documentado para negocio.
**Fuente (código):** `carrito.component.ts:209-245`, `976-990`
**Cobertura E2E:** E2E-CART-08, E2E-CART-09

### HU-SHOP-11 — Aplicar código de cupón en el carrito
**Como** comprador **quiero** capturar un código de cupón y ver su descuento reflejado en el total **para** aprovechar una promoción.
**Prioridad:** Baja
**Criterios de aceptación:**
- Dado un código capturado, cuando presiono "Aplicar", entonces se llama a `api.validateCoupon(code, netAfterVolumeDiscount, customerId)`, que golpea `POST /coupons/validate` (`carrito.component.ts:401-423`; `real-api.service.ts:1157-1163`).
- Dado un cupón válido, cuando se aplica, entonces `couponDiscount` se descuenta del total tanto en modo `pickup` como `delivery` (`carrito.component.ts:392-437`).
- Dado que confirmo la orden con un cupón válido aplicado, cuando se arma el payload, entonces se agrega `couponCode` al `createOrder` (`carrito.component.ts:658-660`).
- **Bug/hueco confirmado:** el backend (`handler.py`) no define ninguna ruta `/coupons*` ni lee `couponCode` en `_create_order`. En producción, `applyCoupon()` fallará (404/500) y, aunque se enviara `couponCode`, la orden lo ignoraría por completo. Ver Observaciones para QA.
**Fuente (código):** `carrito.component.ts:391-437`, `658-660`; `real-api.service.ts:1157-1180`; ausencia verificada en `handler.py` (sin coincidencias para `coupon`)
**Cobertura E2E:** E2E-CART-14 (la matriz de mayo 2026 marca esta funcionalidad como "Ausente"; el código de frontend ya la implementó parcialmente, ver observaciones)

### HU-SHOP-12 — Elegir tipo de entrega: domicilio o recoger en sucursal
**Como** comprador **quiero** elegir entre recibir mi pedido a domicilio o recogerlo en sucursal **para** adaptarlo a mi conveniencia.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que cambio el tipo de entrega, cuando selecciono `delivery`, entonces se dispara la cotización de envío si los datos ya son válidos (`carrito.component.ts:1003-1009`).
- Dado que selecciono `pickup`, cuando confirmo el pedido, entonces el total no incluye envío (`shippingLabel` muestra "Gratis (recoger en sucursal)", `carrito.component.ts:439-441`).
- Dado el modo `pickup`, cuando armo el payload de la orden, entonces se envía `deliveryType: 'pickup'`, `pickupStockId` y `pickupPaymentMethod`, sin datos de dirección (`carrito.component.ts:580-589`).
**Fuente (código):** `carrito.component.ts:53-54`, `560-589`, `1003-1009`
**Cobertura E2E:** E2E-CART-13, E2E-SHIP-05

### HU-SHOP-13 — Validación del formulario de entrega a domicilio
**Como** comprador **quiero** que el formulario de entrega valide mis datos antes de confirmar **para** evitar pedidos con direcciones incompletas o inválidas.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado el formulario de entrega, cuando falta calle, número, ciudad, CP, estado o país, entonces `placeOrder()` bloquea el envío, muestra el toast "Completa calle, numero, ciudad, CP, estado y pais para continuar." y hace scroll + foco al primer campo faltante (`carrito.component.ts:600-613`, `838-861`).
- Dado un código postal, cuando no tiene exactamente 5 dígitos numéricos, entonces se marca como inválido (`/^\d{5}$/`, `carrito.component.ts:884-885`, `963-964`); el campo solo acepta dígitos y se trunca a 5 caracteres mientras se escribe (`carrito.component.ts:870-873`).
- Dado un estado, cuando no está en el catálogo `ESTADOS_MX_CODES`, entonces se marca como inválido (`carrito.component.ts:886-887`, `966`).
- Dado que corrijo un campo de entrega válido, cuando cambia el valor, entonces se vuelve a intentar cotizar el envío automáticamente (`carrito.component.ts:891`).
**Fuente (código):** `carrito.component.ts:600-613`, `864-974`
**Cobertura E2E:** E2E-CART-11, E2E-CART-12

### HU-SHOP-14 — Selección de dirección de envío guardada
**Como** asociado con historial de compras **quiero** elegir una dirección guardada en lugar de recapturarla **para** agilizar el checkout.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que tengo direcciones guardadas, cuando entro al carrito autenticado, entonces se prellena con la dirección por defecto o la primera disponible (`carrito.component.ts:1064-1094`).
- Dado que elijo otra dirección guardada, cuando la selecciono, entonces el formulario se repuebla con sus datos y se recotiza el envío (`carrito.component.ts:920-929`, `1199-1220`).
- Dado que soy invitado (`isGuest`), cuando reviso el carrito, entonces no se muestra la sección de direcciones guardadas (`carrito.component.html:297`, `439`; `isGuest` = `!authService.currentUser`, `carrito.component.ts:255-257`).
- Dado que quiero capturar una dirección nueva, cuando presiono "nueva dirección", entonces se limpia el formulario y se marca `saveShippingAddress = true` para persistirla al confirmar (`carrito.component.ts:931-955`).
**Fuente (código):** `carrito.component.ts:920-955`, `1064-1094`, `1199-1220`
**Cobertura E2E:** E2E-CART-10

### HU-SHOP-15 — Cotización automática de envío por destino y peso
**Como** comprador **quiero** ver tarifas de envío reales según mi destino y el peso de mis productos **para** conocer el costo total antes de pagar.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un formulario de entrega completo y válido, cuando cambia cualquier campo relevante, entonces se llama a `POST /shipping/quote` con nombre, teléfono, dirección completa y los ítems del carrito (peso/dimensiones por producto o valores por defecto 0.5kg/20x15x10cm) (`carrito.component.ts:690-750`; `handler.py:4610-4643`).
- Dado que `ENVIA_API_KEY` no está configurado, cuando se solicita la cotización, entonces el backend responde `{rates: [], error: "Servicio de envío no configurado."}` con 200 (`handler.py:4612-4614`).
- Dado un `zipTo` inválido (no numérico o distinto de 5 dígitos), cuando se llama al backend, entonces responde 400 "zipTo es obligatorio" (`handler.py:4616-4618`).
- Dado que el proveedor devuelve tarifas, cuando se listan, entonces se ordenan por `displayPrice` ascendente y se aplica un `markup` configurable sobre el precio base (`handler.py:4650-4711`).
- Dado que el proveedor externo falla (HTTPError o excepción) para un carrier, cuando se cotiza, entonces ese carrier se omite sin abortar la respuesta completa (`handler.py:4706-4709`); si no hay ninguna tarifa, el frontend muestra "No se pudo calcular el envío." (`carrito.component.ts:728-732`).
- Dado que selecciono una tarifa, cuando confirmo el pedido, entonces el total usa `selectedShippingRate.displayPrice` en vez del estimado genérico (`carrito.component.ts:435`).
**Fuente (código):** `carrito.component.ts:690-750`; `handler.py:4610-4712`
**Cobertura E2E:** E2E-SHIP-01, E2E-SHIP-02, E2E-SHIP-03, E2E-SHIP-04

### HU-SHOP-16 — Recoger en sucursal con método de pago en línea o en tienda
**Como** comprador **quiero** elegir sucursal y decidir si pago en línea o al recoger **para** completar mi compra sin envío.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que entro al carrito, cuando el componente inicia, entonces se cargan las sucursales habilitadas para pickup desde `GET /pickup-stocks` (solo `stockId`, `name`, `location`; sin dato de existencias) (`carrito.component.ts:1011-1029`; `handler.py:4715-4721`).
- Dado el modo `pickup`, cuando intento confirmar sin seleccionar sucursal, entonces se bloquea con "Selecciona una sucursal para recoger tu pedido." (`carrito.component.ts:560-566`).
- Dado el modo `pickup`, cuando intento confirmar sin `pickupPaymentMethod`, entonces se bloquea con "Selecciona un método de pago para continuar." (`carrito.component.ts:567-570`).
- Dado que elijo pago `at_store`, cuando la orden se crea, entonces el pedido queda `pending` con `pickupPaymentMethod = 'at_store'` sin que el backend distinga automáticamente ese caso del flujo en línea al momento de crear la orden (`handler.py:3074-3102`).
- **Hueco confirmado:** el endpoint público de sucursales no expone existencias por producto/sucursal, por lo que no hay "aviso de stock en la sucursal elegida" (coincide con lo ya señalado en `docs/qa/01`).
**Fuente (código):** `carrito.component.ts:560-571`, `1011-1029`; `handler.py:4715-4721`
**Cobertura E2E:** E2E-SHIP-05, E2E-SHIP-06, E2E-SHIP-07

### HU-SHOP-17 — Ver el nivel de descuento por volumen de consumo en el carrito
**Como** asociado **quiero** ver mi nivel y porcentaje de descuento actual, y si esta compra me sube de nivel, **para** entender el beneficio de mi consumo mensual.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado mi volumen neto acumulado del mes, cuando el carrito calcula mi descuento, entonces se usa el mayor entre mi `discountRate` guardado y la tasa proyectada por tramo (`_effective_discount_rate_for_order`, `handler.py:1614-1634`), sobre tramos por defecto de 30% ($3,600–$8,000), 40% ($8,001–$12,000) y 50% (desde $12,001) (`handler.py:1320-1336`).
- Dado el porcentaje de descuento activo, cuando se muestra en el carrito, entonces se etiqueta como "Nivel base" (0%), "Nivel 1" (≥30%), "Nivel 2" (≥40%) o "Nivel 3" (≥50%) (`carrito.component.ts:324-342`).
- Dado que el subtotal actual del carrito, sumado a mi consumo del mes, me haría subir de tramo, cuando reviso el resumen, entonces se muestra el mensaje "Con esta compra subes a Nivel X (Y%)." (`carrito.component.ts:363-370`, usando `dashboardControl.getProjectedDiscountPercent`).
- Dado un usuario no-cliente (rol distinto de `cliente`), cuando se calcula el descuento a mostrar, entonces se usa directamente `authService.currentUser.discountPercent` sin proyección (`carrito.component.ts:302-307`).
**Fuente (código):** `carrito.component.ts:302-370`; `handler.py:1604-1634`, `1320-1336`
**Cobertura E2E:** E2E-COMP-05

### HU-SHOP-18 — Comprar como invitado sin crear cuenta
**Como** visitante sin cuenta **quiero** poder confirmar mi pedido sin registrarme **para** comprar rápido.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que no tengo sesión (`isGuest = true`), cuando lleno el formulario de entrega y confirmo, entonces `placeOrder()` no exige registro previo: el botón "Confirmar pedido" está disponible igual que para un usuario autenticado (`carrito.component.html:625`, `650`; sin `*ngIf` que lo restrinja a usuarios logueados).
- Dado que soy invitado, cuando se arma el payload, entonces `resolveOrderCustomerId()` envía `customerId = 0` y `buyerType` se infiere en backend como `"guest"` si no llega `customerId` (`carrito.component.ts:1256-1263`; `handler.py:2940`).
- **Bug/hueco confirmado:** el payload de `placeOrder()` (tanto en modo `pickup` como `delivery`, `carrito.component.ts:552-657`) **nunca incluye `referrerAssociateId`**, aunque el `refToken`/`leaderId` sí quedó guardado en `localStorage` al visitar `/tienda/:refToken`. El backend solo paga la comisión one-shot de invitado si `order_item.get("referrerAssociateId")` existe (`handler.py:3369`, `3400-3401`). En consecuencia, una compra de invitado hecha directamente en `/carrito` **no** genera la comisión al referidor documentada en HU-SHOP-31, incluso si el `refToken` fue capturado correctamente. Ver Observaciones para QA.
**Fuente (código):** `carrito.component.ts:255-257`, `552-657`, `1256-1263`; `handler.py:2940`, `3369`, `3400-3401`
**Cobertura E2E:** E2E-CART-15 (carrito vacío); no hay caso E2E dedicado a validar la comisión one-shot desde el flujo real de `/carrito`

### HU-SHOP-19 — Crear cuenta desde el modal de invitado en el carrito
**Como** invitado con productos en el carrito **quiero** poder crear mi cuenta sin perder mi carrito **para** aprovechar beneficios de asociado sin reiniciar mi compra.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que soy invitado, cuando abro el modal de registro desde el carrito, entonces se muestra un formulario de nombres, apellidos, email, teléfono y contraseña+confirmación (`carrito.component.ts:1111-1146`).
- Dado que las contraseñas no coinciden o faltan campos obligatorios, cuando envío el formulario, entonces se bloquea con mensaje de error sin llamar al backend (`carrito.component.ts:1127-1136`).
- Dado un registro válido, cuando se envía, entonces se usa `localStorage['leaderId']` como `referralToken` (`carrito.component.ts:1145`), igual que en el registro desde la tienda.
- Dado que el registro requiere verificación de correo, cuando la API responde `requiresEmailVerification`, entonces se cierra el modal y se informa que falta confirmar el correo, **sin iniciar sesión ni continuar el checkout automáticamente**; el usuario debe verificar su correo y luego re-intentar `placeOrder()` manualmente.
- Dado un registro válido sin verificación pendiente, cuando la cuenta se crea, entonces se autentica al usuario y la página se recarga por completo (`window.location.reload()`, `carrito.component.ts:1187-1188`), lo cual depende de que `CartControlService` persista el carrito en `localStorage` para no perderlo tras el reload.
**Fuente (código):** `carrito.component.ts:1111-1197`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ

### HU-SHOP-20 — Confirmar el pedido y ser redirigido al seguimiento
**Como** comprador **quiero** confirmar mi pedido y ver de inmediato su estado **para** dar seguimiento a mi compra.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Dado un carrito vacío, cuando presiono confirmar, entonces se bloquea con el toast "Agrega productos para continuar." (`carrito.component.ts:552-556`).
- Dado un carrito y formulario válidos, cuando confirmo, entonces se llama a `POST /orders` con `status: 'pending'`, ítems, dirección o datos de pickup, y `couponCode` si aplica (`carrito.component.ts:552-660`; `handler.py:2916-3100`).
- Dado que la orden se crea correctamente, cuando la respuesta llega, entonces se limpia el carrito local y se navega a `/orden/:id` (`carrito.component.ts:670-682`).
- Dado que la respuesta no trae un ID de orden, cuando se procesa, entonces se muestra "Orden creada, pero no se recibió el ID." y **no** se navega (`carrito.component.ts:675-677`).
- Dado un error de red o servidor, cuando `createOrder` falla, entonces se muestra "No se pudo crear la orden." y el carrito **no** se limpia (`carrito.component.ts:684-686`).
**Fuente (código):** `carrito.component.ts:552-687`; `handler.py:2916-3175` (aprox.)
**Cobertura E2E:** E2E-CART-13

### HU-SHOP-21 — Pagar con Mercado Pago desde el seguimiento de la orden
**Como** comprador con un pedido pendiente **quiero** pagar en línea con Mercado Pago **para** completar mi compra.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Dado un pedido `pending`, cuando abro `/orden/:idOrden`, entonces se muestra la tarjeta de pago con botón "Pagar con MercadoPago" (`order-status.component.html:244-272`).
- Dado que presiono pagar, cuando `createOrderCheckout` responde, entonces se redirige a `initPoint` (o `sandboxInitPoint` si no hay `initPoint`) (`order-status.component.ts:292-317`).
- Dado que Mercado Pago no está habilitado o mal configurado (`enabled`, `accessToken`, `checkoutPreferencesUrl` faltantes), cuando se solicita el checkout, entonces el backend responde 200 con `{"message": "Mercado Libre no configurado", "Error": "BadRequest"}` (`handler.py:2606-2619`) y el frontend muestra "No se pudo iniciar el pago en MercadoPago." (`order-status.component.ts:304-308`).
- Dado que el pedido no tiene ítems, cuando se arma la preferencia de pago, entonces el backend responde "Pedido sin productos" sin crear la preferencia (`handler.py:2626-2628`).
- Dado un error del proveedor (status ≥ 400) o una respuesta sin `id`/`init_point`, cuando se procesa, entonces el backend responde con error controlado (200 + `Error: BadGateway`) en vez de propagar una excepción (`handler.py:2676-2688`).
**Fuente (código):** `order-status.component.ts:292-318`; `handler.py:2599-2718`
**Cobertura E2E:** E2E-PAY-01, E2E-ORD-02

### HU-SHOP-22 — El webhook de Mercado Pago actualiza el estado de la orden
**Como** sistema **quiero** recibir la notificación de pago de Mercado Pago y actualizar la orden automáticamente **para** que el comprador y el negocio vean el pago reflejado sin intervención manual.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un webhook secreto configurado, cuando llega una notificación sin el secreto correcto, entonces se responde 401 "Webhook no autorizado" (`handler.py:2726-2732`).
- Dado un `payment_id` no resoluble desde `query`/`body`, cuando llega el webhook, entonces se ignora con 200 `{"ignored": true, "reason": "payment_id_not_found"}` sin error (`handler.py:2736-2740`).
- Dado un pago consultado exitosamente, cuando se mapea su estado, entonces `approved → paid`, `pending/in_process → pending`, `refunded/charged_back → refunded`, `rejected/cancelled → canceled` (nota: en minúscula sin doble "l") (`handler.py:2530-2539`).
- Dado que el estado actual de la orden ya es `paid/shipped/delivered/canceled/refunded`, cuando el webhook intenta bajarla a `pending`, entonces se bloquea el downgrade (`handler.py:2786-2788`); lo mismo si intenta bajar de esos estados a `paid` (`handler.py:2789-2791`).
- Dado un mapeo válido y sin bloqueo, cuando se actualiza el estado, entonces se reutiliza `_update_order_status`, disparando efectos de negocio (comisiones) según el nuevo estado (`handler.py:2793-2802`; ver HU-SHOP-28).
**Fuente (código):** `handler.py:2720-2831`
**Cobertura E2E:** E2E-PAY-04

### HU-SHOP-23 — Confirmación de pedido con pago en sucursal (pickup at_store)
**Como** comprador que eligió recoger y pagar en sucursal **quiero** que mi seguimiento de orden no me ofrezca pagar en línea **para** no confundirme sobre cómo completar el pago.
**Prioridad:** Alta
**Criterios de aceptación (comportamiento documentado por el negocio):**
- Dado un pedido `pending` con `deliveryType = 'pickup'` y `pickupPaymentMethod = 'at_store'`, cuando abro `/orden/:idOrden`, entonces debería mostrarse un mensaje de confirmación de pickup sin botón de Mercado Pago.
**Bug/hueco confirmado (comportamiento real del código):**
- La tarjeta "MercadoPago" de `/orden/:idOrden` se muestra únicamente con la condición `*ngIf="statusValue === 'pending'"` (`order-status.component.html:244`); **no existe ninguna referencia a `pickupPaymentMethod` ni `deliveryType` en `order-status.component.ts` ni en su plantilla** (verificado por búsqueda exhaustiva). En consecuencia, un pedido `pending` creado como pickup + pago en sucursal **sí muestra** el botón "Pagar con MercadoPago" en el seguimiento, contradiciendo el comportamiento esperado por negocio y por `docs/qa/01` (ítem 8.3, marcado como ✅ pero no verificable en este componente). Ver Observaciones para QA.
**Fuente (código):** `order-status.component.html:244-272`; ausencia verificada en `order-status.component.ts`
**Cobertura E2E:** E2E-SHIP-08, E2E-PAY-08 (ambos casos de la matriz de mayo 2026 asumen que el botón se oculta; el código actual no lo hace)

### HU-SHOP-24 — Seguimiento de orden: estado, timeline y montos
**Como** comprador **quiero** ver el estado actual de mi pedido, su línea de tiempo y sus montos **para** saber en qué va mi compra.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un pedido válido, cuando abro `/orden/:idOrden`, entonces se muestran subtotal, descuento (monto y %) y total, calculados a partir de `grossSubtotal`/`netTotal`/`discountAmount` con reglas de respaldo si algún campo falta (`order-status.component.ts:203-251`).
- Dado el estado de la orden, cuando se traduce a etiqueta visible, entonces se soportan `pending → "Pago pendiente"`, `paid → "Pago registrado"`, `shipped → "Pedido enviado"`, `delivered → "Pedido entregado"`, `cancelled → "Cancelado"`, `en_devolucion → "En devolución"`, `devuelto_validado → "Devolución aprobada"`, `devolucion_rechazada → "Devolución rechazada"` (`order-status.component.ts:138-168`); cualquier valor no reconocido cae por defecto a `pending` (`normalizeStatus`, `order-status.component.ts:355-361`).
- Dado que vuelvo de Mercado Pago con `status=success` en la URL, cuando la orden aún no está en `paid/shipped/delivered` ni `markedByWebhook`, entonces se hace polling cada 60s reconsultando la orden hasta que cambie (`order-status.component.ts:74-76`, `102-136`).
- Dado que el pedido es de tipo `shipped`, cuando se muestra el detalle, entonces se distingue entre envío por paquetería (número de guía, dirección) y entrega personal (lugar y fecha) según `shippingType` (`order-status.component.html:113-233`).
**Fuente (código):** `order-status.component.ts:1-260`; `order-status.component.html`
**Cobertura E2E:** E2E-ORD-01, E2E-PAY-02, E2E-PAY-03

### HU-SHOP-25 — Aviso de corte de descuento mensual en pedido pendiente
**Como** asociado con un pedido pendiente **quiero** saber si mi descuento por volumen solo aplica hasta el corte de mes **para** decidir si pago antes de que cambie mi tramo.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que estoy dentro de la ventana de corte (últimos 3 días del mes), cuando el backend calcula el estado de la orden, entonces expone `isWindow: true`, `secondsLeft`, `countdownLabel` (formato `Xd HHh MMm`) y el mensaje "Tu descuento solo aplicara hasta el corte de mes." (`handler.py:1636-1648`).
- Dado que la orden trae `discountCutoffWindow` y `discountCutoffCountdown`, cuando se sincroniza el estado en el frontend, entonces se muestra el mensaje "Tu descuento solo aplicara hasta el corte de mes. Tiempo restante: {cuenta regresiva}" (`order-status.component.ts:125-131`).
- Dado que no estoy en ventana de corte, cuando se sincroniza el estado, entonces el mensaje de cuenta regresiva no se muestra.
**Fuente (código):** `handler.py:1636-1648`; `order-status.component.ts:125-131`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ

### HU-SHOP-26 — Cancelar un pedido pendiente o pagado
**Como** comprador **quiero** cancelar mi pedido mientras aún no ha sido despachado **para** desistir de la compra.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un pedido en estado `pending` o `paid`, cuando abro `/orden/:idOrden/cancelar`, entonces el botón de confirmar cancelación está habilitado (`canCancel`, `order-cancelacion.component.ts:44-47`).
- Dado un pedido `shipped`, `delivered` o `en_devolucion`, cuando intento cancelar, entonces se muestra "Pedido en proceso logístico, solicitar devolución" y la acción queda bloqueada (`order-cancelacion.component.ts:53-59`; `order-status.component.ts:271-274`).
- Dado que confirmo la cancelación, cuando se envía, entonces se llama a `POST /orders/{id}/cancel` con `reason: 'customer_request'` (`order-cancelacion.component.ts:62-73`; ruta registrada en `handler.py:6500`).
- Dado que la orden no existe, cuando se cancela, entonces el backend responde 200 con `{"message": "Pedido no encontrado", "Error": "NoEncontrado"}` (`handler.py:3744-3745`).
- Dado que la cancelación se aplica, cuando se persiste, entonces el estado se fija a `"canceled"` (inglés, una sola "l") y se disparan las reversiones de comisión de la orden (`_void_commissions_for_order`, `handler.py:3742-3749`; ver HU-SHOP-30).
- **Bug confirmado:** el backend escribe el estado como `"canceled"`, pero tanto `order-status.component.ts` (`allowedStatuses`, línea 18) como `order-cancelacion.component.ts` (`blockReason`, línea 58) comparan contra `"cancelled"` (doble "l"). Como consecuencia, una orden recién cancelada por este endpoint **no** es reconocida como cancelada por el frontend: `normalizeStatus` la revierte silenciosamente a `"pending"` y la UI seguirá ofreciendo "Cancelar orden" y el botón de Mercado Pago sobre un pedido que en realidad ya está cancelado en base de datos. Ver Observaciones para QA.
**Fuente (código):** `order-cancelacion.component.ts:44-74`; `order-status.component.ts:18`, `266-290`; `handler.py:3742-3749`
**Cobertura E2E:** E2E-ORD-03, E2E-ORD-04, E2E-ORD-05

### HU-SHOP-27 — Solicitar devolución de un pedido entregado
**Como** comprador con un pedido entregado **quiero** solicitar una devolución indicando el motivo y subiendo evidencia **para** obtener un reembolso o reemplazo cuando algo salió mal.
**Prioridad:** Alta
**Criterios de aceptación (comportamiento documentado por el negocio, implementado en frontend):**
- Dado un pedido con estado distinto de `delivered`, cuando abro `/orden/:idOrden/devolucion`, entonces se muestra "Solo puedes solicitar devoluciones de pedidos entregados." (`order-devolucion.component.ts:66-70`).
- Dado el paso 1, cuando elijo un motivo (`DANADO_DEFECTUOSO`, `ERROR_ENVIO`, `DESISTIMIENTO`), entonces puedo avanzar al paso 2 (`order-devolucion.component.ts:46-50`, `77`).
- Dado el motivo elegido, cuando se calcula la responsabilidad de envío, entonces `DESISTIMIENTO → cliente` y cualquier otro motivo → `empresa` (`order-devolucion.component.ts:83-85`).
- Dado el paso 2, cuando falta al menos una categoría de evidencia (fotos de producto, empaque o guía), entonces no puedo avanzar al paso 3 (`canProceedStep2`, `order-devolucion.component.ts:78-82`).
- Dado el paso 3 completo, cuando envío la solicitud, entonces se llama a `POST /orders/{id}/return` con motivo, descripción opcional y evidencia en base64 (`order-devolucion.component.ts:127-146`; `real-api.service.ts:1199-1205`).
**Bug/hueco confirmado (comportamiento real del backend):**
- No existe, en ningún punto de `handler.py`, una ruta `POST /orders/{id}/return`, ni funciones de inspección, checklist, aprobación/rechazo de devolución, ni transición a los estados `en_devolucion`, `devuelto_validado` o `devolucion_rechazada` (búsqueda exhaustiva sin coincidencias para "return"/"devolu"/"DANADO"/"DESISTIMIENTO"/"checklist"). Además, `_update_order_status` solo acepta `{"pending", "paid", "delivered", "canceled", "refunded", "shipped"}` como `status` válido (`handler.py:3606`), por lo que ni siquiera un cambio manual de estado por API puede llevar una orden a esos tres estados de devolución. **Toda la funcionalidad de devolución es frontend-only: cualquier solicitud real fallará con 404/501 y mostrará "No se pudo enviar la solicitud."** (mensaje de error genérico de `order-devolucion.component.ts:144`). Esto contradice `docs/qa/01` (sección 9, marcada mayormente ✅) y toda la sección RET de `docs/qa/02`. Ver Observaciones para QA — es el hallazgo más crítico de este documento.
**Fuente (código):** `order-devolucion.component.ts:1-152`; ausencia verificada en `handler.py` (rutas 3-segmentos POST solo soportan `refund`, `cancel`, `checkout`, `status`: `handler.py:6499-6502`)
**Cobertura E2E:** E2E-RET-01 a E2E-RET-11 (todos asumen backend funcional; ninguno es ejecutable end-to-end con el código actual)

### HU-SHOP-28 — El pago de un pedido genera comisiones pendientes en la red
**Como** sistema **quiero** generar el ledger de comisiones de toda la línea ascendente cuando un pedido pasa a `paid` **para** que la red vea reflejado su beneficio potencial antes de la entrega.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Dado un pedido que cambia de cualquier estado a `paid` por primera vez, cuando se procesa la transición, entonces se llama a `_apply_rewards_on_paid_order` (`handler.py:3679-3680`).
- Dado un comprador `registered`/`associate`, cuando se aplican las recompensas, entonces se calcula la tasa de descuento efectiva (mayor entre la guardada y la proyectada por tramo), se recalcula `grossSubtotal`/`discountAmount`/`netTotal` de la orden, y se actualiza el volumen mensual del comprador (`_upsert_month_volume`) (`handler.py:3362-3480`).
- Dado la cadena ascendente (`_upline_chain`, hasta `MAX_COMMISSION_LEVELS` o el número de niveles configurados), cuando se generan comisiones, entonces cada beneficiario recibe una fila de ledger con `status: 'pending'` (o `'blocked'` si algún ascendente intermedio no está activo ese mes), de forma idempotente por `orderId + nivel` (`_upsert_ledger_row`, `handler.py:3500-3576`).
- Dado un beneficiario que no cumple los requisitos configurados por nivel (mínimo de usuarios activos directos o volumen grupal), cuando se evalúa, entonces esa fila se omite por completo (`_check_commission_requirements`, `handler.py:3509-3511`).
- Dado que la orden es de tipo `guest` **y** trae `referrerAssociateId`, cuando se aplican las recompensas, entonces se genera una única fila de comisión al 10% del neto para el referidor, marcada `referrerOneShot: true`, en lugar del reparto multinivel (`handler.py:3400-3475`; ver también HU-SHOP-31 sobre por qué esta rama casi nunca se alcanza desde `/carrito`).
**Fuente (código):** `handler.py:3319-3601`, `3679-3680`
**Cobertura E2E:** E2E-PAY-04, E2E-COMP-06

### HU-SHOP-29 — La entrega confirmada convierte comisiones pendientes en confirmadas
**Como** asociado **quiero** que mi comisión pase de "pendiente" a "confirmada" cuando el pedido de mi referido/red se entrega **para** saber que ya puedo contar con ese ingreso.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un pedido que cambia a `delivered` por primera vez, cuando se procesa la transición, entonces se llama a `_confirm_order_commissions` (`handler.py:3681-3685`).
- Dado el ledger de cada beneficiario de esa orden, cuando se confirma, entonces las filas en `status: 'pending'` pasan a `'confirmed'` y las filas `blocked` marcan `blockedStatus: 'confirmed'` (quedan a la espera de que el beneficiario se active) — **no se agregan filas nuevas**, solo se transiciona lo ya generado en `paid` (`handler.py:2312-2396`).
- Dado que el comprador es `guest` con referidor, cuando se confirma la entrega, entonces el referidor también se incluye entre los beneficiarios a confirmar (`handler.py:2336-2339`).
- Dado que un pedido `shipped` pasa a `delivered` mientras requiere líneas de despacho, cuando no se proporcionó `stockId` o `dispatchLines` en el paso `shipped`, entonces esa restricción ya se validó antes (al marcar `shipped`), no en `delivered` (`handler.py:3646-3661`).
**Fuente (código):** `handler.py:2312-2396`, `3681-3685`
**Cobertura E2E:** E2E-ORD-06

### HU-SHOP-30 — Cancelar o reembolsar un pedido pagado revierte sus comisiones
**Como** sistema **quiero** anular las comisiones generadas por un pedido cuando este se cancela o se reembolsa **para** que la red no cobre por una venta que no se concretó.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un pedido `paid` que se cancela (`POST /orders/{id}/cancel`) o se reembolsa (`POST /orders/{id}/refund`), cuando se procesa, entonces se llama a `_void_commissions_for_order(order_id, reason)` (`handler.py:3739`, `3748`).
- Dado el ledger de cada beneficiario upline de esa orden (incluyendo al referidor si el comprador era `guest`), cuando se anulan las comisiones, entonces se recalculan los totales (`pending`/`confirmed`/`blocked`) descontando las filas de esa orden (`handler.py:2399-2464`).
- Dado un reembolso, cuando se aplica, entonces el estado de la orden pasa a `"refunded"` y se guarda `refundReason` (`handler.py:3733-3740`).
- Dado una cancelación, cuando se aplica, entonces el estado pasa a `"canceled"` y se guarda `cancelReason` (`handler.py:3742-3749`) — mismo problema de nomenclatura que HU-SHOP-26 (el frontend espera `"cancelled"`).
- Nota: a diferencia del flujo de devolución con inspección (HU-SHOP-27), `_refund_order` es un endpoint directo sin checklist ni evidencia — cualquier llamada válida a `POST /orders/{id}/refund` marca la orden como reembolsada de inmediato.
**Fuente (código):** `handler.py:2399-2464`, `3733-3749`
**Cobertura E2E:** E2E-ORD-07, E2E-RET-12 (este último asume el flujo de inspección de HU-SHOP-27, que no existe; solo se cubre la reversión de comisiones en sí)

### HU-SHOP-31 — Comisión única (10%) al referidor por compra de invitado
**Como** afiliado que comparte su link de tienda (`/tienda/:refToken`) **quiero** recibir una comisión cuando un invitado compra a través de mi link, sin que ese invitado se registre **para** monetizar mis referidos incluso si no se afilian de inmediato.
**Prioridad:** Media
**Criterios de aceptación (comportamiento documentado por el negocio):**
- Dado un pedido `buyerType = 'guest'` con `referrerAssociateId` presente, cuando el pedido pasa a `paid`, entonces se genera una comisión única del 10% del neto para el referidor (`rate = Decimal("0.10")`, `handler.py:3400-3475`).
- Dado que el monto calculado es `<= 0`, cuando se evalúa, entonces no se crea ninguna fila de comisión (`handler.py:3404-3408`).
**Bug/hueco confirmado (comportamiento real end-to-end):**
- El único lugar donde el frontend guarda el `refToken` es `localStorage['leaderId']` (`tienda.component.ts:93-100`), y el único lugar donde ese valor se envía al backend es como `referralToken` en `createAccount()` (registro de cuenta, tanto en `tienda.component.ts:215` como en `carrito.component.ts:1145`), **nunca** como `referrerAssociateId` en el payload de `createOrder()` de `carrito.component.ts` (`552-657`, sin ninguna referencia a `referrerAssociateId` en todo el archivo). Por lo tanto, la ruta de "invitado compra sin registrarse" que el backend implementa (`buyerType: 'guest'` + `referrerAssociateId`) es **inalcanzable** desde el flujo real de checkout: un invitado que compra en `/carrito` sin registrarse generará una orden con `referrerAssociateId: undefined`, y la comisión one-shot nunca se calculará, aun si llegó desde un `refToken` válido. La única forma de que el referidor reciba crédito es que el invitado complete el registro completo (lo cual lo convierte en `registered`, no en `guest`, y activa el reparto multinivel normal en vez del 10% one-shot).
**Fuente (código):** `handler.py:3400-3475`; ausencia verificada en `carrito.component.ts` (sin `referrerAssociateId` en todo el archivo) y en `real-api.service.ts`/`cart-control.service.ts`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ

---

## Observaciones para QA

Inconsistencias y huecos más relevantes detectados, priorizados por impacto:

1. **Devolución (RET) es 100% frontend, 0% backend.** `order-devolucion.component.ts` envía a `POST /orders/{id}/return`, ruta inexistente en `handler.py`; tampoco existen los estados `en_devolucion`/`devuelto_validado`/`devolucion_rechazada` en `_update_order_status` (solo acepta `pending/paid/delivered/canceled/refunded/shipped`). Toda la sección RET de `docs/qa/02` (E2E-RET-01 a 12) es hoy no ejecutable contra el backend real. Es la brecha más grave del dominio; confirmar con el equipo si el backend vive en otro repo no incluido en esta revisión o si es trabajo pendiente real.

2. **Desalineación de estado "cancelado": `"canceled"` (backend) vs `"cancelled"` (frontend).** `_cancel_order`/`_refund_order` escriben `"canceled"` (una "l"); `order-status.component.ts` (`allowedStatuses`) y `order-cancelacion.component.ts` (`blockReason`) comparan contra `"cancelled"` (doble "l"). Efecto: una orden cancelada en backend se sigue mostrando como "Pago pendiente", con el botón de Mercado Pago aún visible. Bug reproducible de alto impacto.

3. **Botón de Mercado Pago no se oculta para pickup + pago en sucursal.** `docs/qa/01` (8.3) y `docs/qa/02` (E2E-SHIP-08, E2E-PAY-08) dan por hecho que se oculta con `pickupPaymentMethod = 'at_store'`. `order-status` (TS y HTML) no referencia `pickupPaymentMethod` ni `deliveryType`; el botón se muestra siempre que `status === 'pending'`.

4. **Cupones: la matriz de mayo 2026 dice "ausente"; el código ya tiene UI completa (carrito + panel admin) pero cero backend.** `carrito.component.ts` y `admin.component.ts` (CRUD de cupones) llaman a `/coupons*`; `handler.py` no implementa ninguna ruta de cupones. No es "no implementado" sino "roto en producción": cualquier intento de aplicar o administrar un cupón fallará. Actualizar `docs/qa/01` (6.12/13.13) y `docs/qa/02` (E2E-CART-14, E2E-ADM-15/20).

5. **Comisión one-shot de invitado (10%) es inalcanzable desde el checkout real.** El backend soporta `buyerType: 'guest'` + `referrerAssociateId`, pero `carrito.component.ts` nunca puebla `referrerAssociateId` en `createOrder`; `localStorage['leaderId']` solo se usa para `createAccount` (registro), no para compra sin registro. Falta cablear ese valor hacia `placeOrder()`.

6. **Tramos de descuento por defecto ya no están vacíos.** `docs/qa/01` (12.5) afirma `discountTiers` vacío por defecto; `_default_rewards_config()` (`handler.py:1320-1336`) ya define 30/40/50% ($3,600/$8,001/$12,001) como fallback si no hay `CONFIG` en DynamoDB. Revalidar contra la configuración persistida real, que puede diferir del código.

7. **"Aviso de stock en sucursal elegida" sigue sin implementarse.** `GET /pickup-stocks` solo devuelve `id/name/location`, sin existencias. Confirma lo ya señalado en `docs/qa/01` (7.5); no es hallazgo nuevo.

8. **`POS_SALE` no se crea automáticamente al pagar un pickup `at_store` desde el carrito de cliente.** La creación de `POS_SALE` (`handler.py:5210-5289`) es un flujo manual de operador en el panel admin; `_update_order_status` no la dispara. Confirma lo marcado ⚠️ en `docs/qa/01` (6.9, 8.5, 13.9).

9. **Productos sugeridos sin criterio de negocio documentado.** El scoring por tags/badge (`carrito.component.ts:209-241`) es enteramente de frontend, sin respaldo de backend. Confirma `docs/qa/01` (6.3); se necesita definición formal antes de escribir criterios de aceptación de negocio para E2E-CART-09.
