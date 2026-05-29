# Finding'U — Matriz de Pruebas E2E

> **Propósito:** Matriz de casos de prueba End-to-End para **cada funcionalidad** del sistema
> Finding'U (ver `01-funcionalidades-sistema.md`), cubriendo escenarios *happy path*, límite y de
> error. Este es **solo el documento de diseño de pruebas** (no se implementan los tests aquí).
>
> **Versión:** Mayo 2026
>
> **Convenciones**
> - **ID:** `E2E-<MÓDULO>-<n>`. Módulos: AUTH, REF, LAND, SHOP, CART, SHIP, PAY, ORD, RET, DASH, PROF, COMP, ADM, REP, NOTI.
> - **Tipo:** `Happy` (flujo feliz), `Borde` (límite/validación), `Error` (negativo/excepción).
> - **Prioridad:** `Crítica`, `Alta`, `Media`, `Baja`.
> - **Resultado esperado:** comportamiento observable correcto.
> - Los casos marcados con 🔎 están directamente ligados a un hallazgo de la matriz del cliente
>   (ver `03-comparacion-matriz-hallazgos-findingu.md`).

---

## 1. Autenticación (AUTH)

| ID | Escenario | Tipo | Prioridad | Precondiciones | Pasos | Resultado esperado |
|---|---|---|---|---|---|---|
| E2E-AUTH-01 | Login exitoso cliente | Happy | Crítica | Cuenta verificada rol cliente | Ingresar email+password válidos → Entrar | Redirige a `/dashboard`; sesión activa |
| E2E-AUTH-02 | Login exitoso admin | Happy | Crítica | Cuenta admin | Login admin | Redirige a `/admin` |
| E2E-AUTH-03 | Credenciales inválidas | Error | Alta | — | Password incorrecto | Mensaje de error; sin sesión |
| E2E-AUTH-04 | Email no verificado | Error | Alta | Cuenta sin verificar | Login | Mensaje "Confirma tu cuenta" + botón reenviar |
| E2E-AUTH-05 | Reenviar correo de confirmación | Happy | Media | Cuenta sin verificar | Click "Reenviar" | Toast de envío; correo recibido |
| E2E-AUTH-06 | Campos vacíos | Borde | Media | — | Enviar sin email/password | Validación bloquea envío |
| E2E-AUTH-07 | Toggle visibilidad password | Borde | Baja | — | Click ojo | Alterna texto/oculto |
| E2E-AUTH-08 | Solicitar recuperación con email existente | Happy | Alta | Cuenta existe | Solicitar OTP | OTP enviado por correo (200 OK) |
| E2E-AUTH-09 | Solicitar recuperación con email inexistente | Borde | Media | — | Solicitar OTP | 200 OK genérico (no revela existencia) |
| E2E-AUTH-10 | Reset con OTP válido | Happy | Alta | OTP vigente | email+otp+nueva password+confirmación | Password cambiada; redirige a login |
| E2E-AUTH-11 | Reset con OTP expirado (>15 min) | Error | Alta | OTP vencido | Reset | Error de OTP inválido/expirado |
| E2E-AUTH-12 | Reset con OTP ya usado | Error | Alta | OTP usado | Reset | Error |
| E2E-AUTH-13 | Reset con contraseñas que no coinciden | Borde | Media | — | confirmación ≠ password | Validación bloquea |
| E2E-AUTH-14 | Verificar email con token válido | Happy | Alta | Token vigente | Abrir `/verificar-email?token=...` | Estado success; `emailVerified=true` |
| E2E-AUTH-15 | Verificar email con token expirado (>24 h) | Error | Media | Token vencido | Abrir link | Estado error |
| E2E-AUTH-16 | Verificar email con token ya usado | Error | Media | Token usado | Abrir link | Estado error |
| E2E-AUTH-17 | Cambio de contraseña autenticado | Happy | Media | Sesión activa | actual+nueva (≥8) | Password cambiada |
| E2E-AUTH-18 | Cambio con contraseña actual incorrecta | Error | Media | Sesión activa | actual errónea | Error |
| E2E-AUTH-19 | Cambio con nueva <8 caracteres | Borde | Media | Sesión activa | nueva corta | Validación bloquea |
| E2E-AUTH-20 | Acceso a `/admin` sin rol admin | Error | Alta | Sesión cliente | Navegar a `/admin` | `adminGuard` bloquea/redirige |
| E2E-AUTH-21 | Acceso a `/dashboard` sin sesión | Borde | Media | Sin sesión | Navegar `/dashboard` | CTA de registro / restricción `dashboardGuard` |
| E2E-AUTH-22 | Expiración/persistencia de sesión | Borde | Media | Sesión activa | Recargar app | Sesión persiste desde `localStorage` |

---

## 2. Registro y vinculación de red (REF) 🔎

| ID | Escenario | Tipo | Prioridad | Precondiciones | Pasos | Resultado esperado |
|---|---|---|---|---|---|---|
| E2E-REF-01 | Registro vía `/landing/:idSponsor` | Happy | Crítica | Patrocinador válido | Completar formulario | Cuenta creada con `leaderId` del patrocinador |
| E2E-REF-02 | 🔎 Afiliado aparece en la red del patrocinador | Happy | Crítica | E2E-REF-01 ok | Patrocinador abre su red | Nuevo afiliado **visible** en su red |
| E2E-REF-03 | 🔎 Patrocinador visible en perfil del nuevo afiliado | Happy | Crítica | E2E-REF-01 ok | Nuevo afiliado abre dashboard/perfil | Aparece nombre/correo del patrocinador |
| E2E-REF-04 | Registro vía `/tienda/:refToken` | Happy | Alta | refToken válido | Registrar | `leaderId` correcto |
| E2E-REF-05 | Registro con código manual (sin ruta) | Happy | Alta | Código válido | Capturar código en formulario | Vinculación correcta |
| E2E-REF-06 | Código de referido inexistente | Error | Alta | Código inválido | Registrar | Mensaje de código inválido; sin vínculo erróneo |
| E2E-REF-07 | Registro sin código (directo) | Borde | Media | — | Registrar | Cuenta creada sin `leaderId` (o patrocinador default) |
| E2E-REF-08 | Email ya registrado | Error | Alta | Email existe | Registrar | Error de email duplicado |
| E2E-REF-09 | Generación de código de referido propio | Happy | Media | Registro ok | — | Código `{Nombre}-{Iniciales}` generado y único |
| E2E-REF-10 | Colisión de código de referido | Borde | Baja | Nombre repetido | Registrar varios | Sufijo incremental (`-2`, `-3`) |
| E2E-REF-11 | Notificación por correo al patrocinador | Happy | Media | Patrocinador con email | Registro de afiliado | Patrocinador recibe correo |
| E2E-REF-12 | Persistencia de `leaderId` en BD | Happy | Crítica | Registro ok | Consultar `CUSTOMER` | `leaderId` persistido |
| E2E-REF-13 | refToken en localStorage tras visitar landing | Borde | Media | — | Visitar `/landing/:id`, luego registrar | `leaderId` recuperado del storage |
| E2E-REF-14 | Prevención de ciclo de patrocinio | Error | Media | A patrocina B | Asignar B como líder de A | Bloqueo de ciclo (`_check_leader_cycle`) |

---

## 3. Landing (LAND)

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-LAND-01 | Landing con patrocinador | Happy | Media | Abrir `/landing/:id` | Muestra nombre/mensaje/WhatsApp del patrocinador |
| E2E-LAND-02 | Landing sin patrocinador | Happy | Media | Abrir `/landing` | Modo sin patrocinador |
| E2E-LAND-03 | Botón WhatsApp al patrocinador | Happy | Baja | Click WhatsApp | Abre chat con mensaje preformateado |
| E2E-LAND-04 | Producto destacado por `?p=` | Borde | Baja | Abrir con `?p=ID` | Destaca producto indicado |
| E2E-LAND-05 | Tabla de plan de recompensas | Happy | Media | Ver landing | Muestra niveles, %, bonos por rango, inicio rápido |
| E2E-LAND-06 | 🔎 Carrusel de 2 posiciones (Tienda/Sistema) | Error | Media | Ver landing | **Ausente** — debe implementarse |
| E2E-LAND-07 | 🔎 Textos del home cargados | Borde | Media | Ver landing | Textos definitivos presentes (pendiente de contenido) |

---

## 4. Tienda y catálogo (SHOP)

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-SHOP-01 | Listado de productos activos | Happy | Alta | Abrir `/tienda` | Solo productos `inOnlineStore` |
| E2E-SHOP-02 | Filtro por categoría | Happy | Media | Seleccionar categoría | Lista filtrada |
| E2E-SHOP-03 | Producto hero con variantes | Happy | Media | Seleccionar variante | Precio/imagen cambian por variante |
| E2E-SHOP-04 | Agregar al carrito desde tienda | Happy | Alta | Click agregar | Contador y subtotal aumentan |
| E2E-SHOP-05 | Ir al carrito | Happy | Media | Click "Ir al carrito" | Navega a `/carrito` |
| E2E-SHOP-06 | Registro desde tienda con refToken | Happy | Media | Registrar en `/tienda/:refToken` | Cuenta con `leaderId` |
| E2E-SHOP-07 | 🔎 PC oficiales + PC netos por descuento en tarjeta | Borde | Media | Ver producto | Debe mostrar PC del producto y PC netos por nivel |
| E2E-SHOP-08 | 🔎 Carga de tabla de PC para 13 productos | Borde | Media | Revisar catálogo | `vpPoints` cargado y correcto en todos |
| E2E-SHOP-09 | 🔎 URL directa/subdominio de tienda | Error | Alta | Abrir `tienda.findingu.com.mx` | **Ausente** — solo ruta hash |
| E2E-SHOP-10 | Catálogo vacío | Borde | Baja | Sin productos activos | Estado vacío sin error |

---

## 5. Carrito y checkout (CART) 🔎

| ID | Escenario | Tipo | Prioridad | Precondiciones | Pasos | Resultado esperado |
|---|---|---|---|---|---|---|
| E2E-CART-01 | Editar cantidades | Happy | Alta | Carrito con ítems | Cambiar cantidad | Subtotal recalcula |
| E2E-CART-02 | Eliminar producto | Happy | Alta | Carrito con ítems | Quitar ítem | Total recalcula correctamente |
| E2E-CART-03 | 🔎 "Regresar" durante la compra no elimina el alias del afiliado | Error | Alta | En proceso de compra | Click "Regresar" | El alias **se conserva** |
| E2E-CART-04 | 🔎 "Regresar" no deja producto fantasma | Error | Alta | En proceso | Quitar/regresar producto | El costo del producto **no** permanece acumulado |
| E2E-CART-05 | 🔎 Agregar producto tras "Regresar" no suma a fantasma | Error | Alta | Tras E2E-CART-04 | Agregar nuevo producto | Total correcto, sin suma fantasma |
| E2E-CART-06 | Cancelar/vaciar carrito | Happy | Media | Carrito con ítems | Vaciar | Carrito en cero y limpio |
| E2E-CART-07 | Restaurar estado de entrega al volver | Borde | Media | Estado guardado | Volver al carrito | Datos de entrega restaurados |
| E2E-CART-08 | Productos sugeridos por tags | Happy | Media | Carrito con ítem | Ver sugeridos | Lista por afinidad de tags |
| E2E-CART-09 | 🔎 Lógica documentada de sugeridos | Borde | Media | — | Revisar criterio | Definir si por categoría/historial/manual |
| E2E-CART-10 | Selección de dirección guardada | Happy | Media | Direcciones previas | Elegir dirección | Formulario poblado |
| E2E-CART-11 | Validación CP 5 dígitos | Borde | Media | — | CP inválido | Bloquea y enfoca error |
| E2E-CART-12 | Validación de formulario incompleto | Borde | Alta | — | Enviar incompleto | Enfoca primer error |
| E2E-CART-13 | Crear orden (entrega a domicilio) | Happy | Crítica | Formulario válido | Confirmar | Orden creada; redirige a `/orden/:id` |
| E2E-CART-14 | 🔎 Aplicar código de descuento/cupón | Error | Alta | — | Capturar cupón | **Ausente** — no hay campo de cupón |
| E2E-CART-15 | Carrito vacío al checkout | Borde | Media | Sin ítems | Intentar pagar | Bloquea / mensaje |

---

## 6. Envío y paqueterías (SHIP) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-SHIP-01 | Cotización de envío por destino/peso | Happy | Media | Capturar CP destino | Devuelve tarifas por carrier |
| E2E-SHIP-02 | Selección de tarifa | Happy | Media | Elegir tarifa | Total incluye envío |
| E2E-SHIP-03 | Sin tarifas disponibles | Borde | Media | Destino sin cobertura | Mensaje sin error fatal |
| E2E-SHIP-04 | Token de paquetería ausente/inválido | Error | Media | Sin `ENVIA_TOKEN` | Error controlado |
| E2E-SHIP-05 | Seleccionar "recoger en sucursal" | Happy | Alta | Cambiar a pickup | Carga lista de sucursales |
| E2E-SHIP-06 | 🔎 "Recoger en sucursal" sin "error desconocido" | Error | Alta | Elegir pickup | **No** debe aparecer "error desconocido" |
| E2E-SHIP-07 | 🔎 Aviso de stock en sucursal elegida | Borde | Alta | Elegir sucursal | Notifica disponibilidad de stock |
| E2E-SHIP-08 | 🔎 Mensaje de confirmación pickup (sin botón Mercado Pago) | Happy | Alta | Confirmar pickup pago en sucursal | "Tu pedido quedó confirmado, podrás recogerlo y pagarlo en sucursal"; sin botón MP |
| E2E-SHIP-09 | 🔎 Generación de guía de paquetería | Error | Media | Tras pagar | **Ausente** — no se genera guía |

---

## 7. Pagos (PAY) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-PAY-01 | Checkout en línea (Mercado Pago) | Happy | Crítica | Pagar pedido pendiente | Redirige a `initPoint` de MP |
| E2E-PAY-02 | Retorno exitoso + polling | Happy | Alta | Volver de MP con success | Polling cada 60 s hasta `paid` |
| E2E-PAY-03 | Pago fallido/cancelado en MP | Error | Alta | Cancelar en MP | Orden sigue `pending`; permite reintento |
| E2E-PAY-04 | Webhook de pago marca `paid` | Happy | Alta | MP notifica | Orden → `paid`; comisiones `pending` |
| E2E-PAY-05 | 🔎 Pago en sucursal: forma de pago en POS | Happy | Alta | Pedido pickup `at_store` | Operador registra método (efectivo/tarjeta/débito/transferencia) |
| E2E-PAY-06 | 🔎 Campo de forma de pago visible/editable en pedido pickup | Borde | Alta | Gestionar pedido pickup | Campo de método visible y editable |
| E2E-PAY-07 | POS_SALE automático al pasar a `paid` (pickup at_store) | Happy | Media | Marcar `paid` | Se crea `POS_SALE` con método y atendedor |
| E2E-PAY-08 | Pago en sucursal sin botón Mercado Pago | Borde | Alta | Flujo pickup at_store | Botón MP **oculto** |

---

## 8. Pedidos: seguimiento, cancelación, devolución (ORD / RET) 🔎

### 8.1 Seguimiento y cancelación (ORD)

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-ORD-01 | Ver estado y timeline | Happy | Alta | Abrir `/orden/:id` | Estado, timeline, montos, envío/pago |
| E2E-ORD-02 | Pagar pedido pendiente desde seguimiento | Happy | Alta | Click pagar | Redirige a MP |
| E2E-ORD-03 | Cancelar pedido `pending` | Happy | Alta | Cancelar | Estado `cancelled`, sin reembolso |
| E2E-ORD-04 | Cancelar pedido `paid` | Happy | Alta | Cancelar | `cancelled` + `pendingRefund=true`; comisiones revertidas |
| E2E-ORD-05 | Cancelar pedido `shipped/delivered` | Error | Alta | Intentar cancelar | 409 bloqueado; sugiere devolución |
| E2E-ORD-06 | Transiciones de estado admin (`paid→shipped→delivered`) | Happy | Alta | Admin cambia estado | Inventario despacha; comisiones confirman; bonos evaluados |
| E2E-ORD-07 | Reversión de comisiones al cancelar pagado | Happy | Alta | Cancelar `paid` | Comisiones `reverted` |

### 8.2 Devolución (RET) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-RET-01 | 🔎 Solicitud de devolución exitosa | Happy | Alta | Pedido `delivered`, motivo + evidencia | Solicitud enviada sin "No se pudo enviar la solicitud" |
| E2E-RET-02 | Motivo DANADO_DEFECTUOSO dentro de 48 h | Happy | Alta | Solicitar | `shippingResponsibility=empresa` |
| E2E-RET-03 | Motivo DESISTIMIENTO dentro de 7 días | Happy | Alta | Solicitar | `shippingResponsibility=cliente` |
| E2E-RET-04 | Fuera de plazo (DANADO >48 h) | Error | Alta | Solicitar tardío | Bloqueado por plazo |
| E2E-RET-05 | Fuera de plazo (DESISTIMIENTO >7 días) | Error | Alta | Solicitar tardío | Bloqueado por plazo |
| E2E-RET-06 | Evidencia incompleta (falta categoría) | Error | Alta | Sin fotos guía | Validación obliga 3 categorías |
| E2E-RET-07 | Devolución duplicada | Error | Media | Pedido ya en devolución | `RETURN_ALREADY_EXISTS` |
| E2E-RET-08 | Devolución sobre pedido no `delivered` | Error | Alta | Pedido `paid` | Bloqueado (solo entregados) |
| E2E-RET-09 | Inspección backoffice aprobada (checklist completo) | Happy | Alta | Admin valida todo true | `devuelto_validado`; comisiones revertidas |
| E2E-RET-10 | Inspección rechazada (algún check false) | Error | Alta | Admin marca un false | `devolucion_rechazada`; comisiones intactas |
| E2E-RET-11 | Reembolso con comprobante | Happy | Alta | Admin sube comprobante | `refunded`; `refundReceiptUrl` |
| E2E-RET-12 | 🔎 Ajuste de PC/volumen/rango tras devolución | Happy | Alta | Devolución validada | VP/VG y bono/rango recalculados |

---

## 9. Dashboard del asociado (DASH) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-DASH-01 | 🔎 VP y VG mostrados en Puntos (no pesos) | Happy | Crítica | Abrir dashboard | Métricas de red/metas/rangos en PC |
| E2E-DASH-02 | 🔎 PC acumulados del mes y faltante al siguiente nivel | Happy | Crítica | Ver dashboard | Muestra acumulado y faltante |
| E2E-DASH-03 | 🔎 Nivel de descuento actual visible | Happy | Crítica | Ver perfil/dashboard | Badge de nivel + % |
| E2E-DASH-04 | Metas con barra de progreso | Happy | Alta | Ver metas | Activa, secundarias y completadas |
| E2E-DASH-05 | Red multinivel (L1–L5) y grafo | Happy | Alta | Ver red | Miembros por nivel + grafo |
| E2E-DASH-06 | 🔎 Cuadro de Honor desde el primer mes | Happy | Media | Ver cuadro | Top 10 por VG y VP con deltas |
| E2E-DASH-07 | Modal automático al entrar al top 10 | Borde | Baja | Usuario en top | Modal de reconocimiento |
| E2E-DASH-08 | Carrusel de destacados (prev/next) | Happy | Media | Navegar carrusel | Cambia destacado |
| E2E-DASH-09 | 🔎 Carrusel de 3 posiciones (Producto del mes) | Borde | Media | Ver dashboard | 3 posiciones configurables |
| E2E-DASH-10 | Compartir en redes (copiar link+copy+imagen) | Happy | Media | Elegir canal/formato | Copia al portapapeles |
| E2E-DASH-11 | 🔎 Imágenes dedicadas con código de referido | Borde | Media | Compartir | Piezas por tamaño con código |
| E2E-DASH-12 | Comisiones: ledger pagado/pendiente/bloqueado | Happy | Alta | Abrir comisiones | Estados correctos |
| E2E-DASH-13 | Solicitud de retiro con CLABE registrada | Happy | Alta | Solicitar payout | Solicitud creada |
| E2E-DASH-14 | Solicitud de retiro sin CLABE | Error | Media | Solicitar payout | Bloquea/pide CLABE |
| E2E-DASH-15 | 🔎 Copiar correo del patrocinador (escritorio) | Happy | Alta | Click en correo | Copia al portapapeles (además de mailto) |
| E2E-DASH-16 | 🔎 mailto sin cliente de correo | Borde | Alta | Click correo sin cliente | El "copiar" funciona aunque mailto no abra |
| E2E-DASH-17 | Órdenes paginadas + detalle expandible | Happy | Media | Ver órdenes | Paginación y detalle |
| E2E-DASH-18 | CTAs para invitado (sin sesión) | Borde | Media | Abrir `/` sin sesión | Muestra CTA de registro |
| E2E-DASH-19 | 🔎 Acciones/avisos según rol | Borde | Media | Cliente no afiliado | No ve acciones de red/comisiones |

---

## 10. Perfil del usuario (PROF) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-PROF-01 | Actualizar datos personales | Happy | Media | Editar y guardar | Datos persistidos |
| E2E-PROF-02 | Registrar CLABE 18 dígitos | Happy | Alta | Capturar + confirmar | Guardada; muestra máscara/last4 |
| E2E-PROF-03 | CLABE con longitud inválida | Error | Media | <18 dígitos | Validación bloquea |
| E2E-PROF-04 | Subir documento (PDF/imagen) | Happy | Media | Subir + preview | Documento cargado |
| E2E-PROF-05 | Documento de tipo/tamaño no soportado | Error | Baja | Subir inválido | Rechazo controlado |
| E2E-PROF-06 | 🔎 Patrocinador visible en perfil | Happy | Alta | Abrir perfil | Nombre/correo del patrocinador presente |
| E2E-PROF-07 | 🔎 Aviso de privacidad mostrado al registro/primer acceso | Error | Baja | Primer acceso | **Ausente** — debe mostrarse |

---

## 11. Plan de compensación (COMP) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-COMP-01 | 1 PC ≈ $50 (`mxnPerVp`) | Happy | Crítica | Compra y cálculo de VP | VP = neto/50 (o `vpPoints`) |
| E2E-COMP-02 | 🔎 PC proporcionales al neto pagado (descuento) | Happy | Crítica | Compra con descuento | PC = oficiales × (1 − %desc) |
| E2E-COMP-03 | 🔎 Activación mensual ($1,000 netos) | Happy | Crítica | Compra ≥ umbral | Usuario activo; comisiones se pagan |
| E2E-COMP-04 | Sin activación no se cobran comisiones | Error | Crítica | Compra < umbral | Comisiones `blocked` |
| E2E-COMP-05 | 🔎 Escalera de descuentos 0/10/20/30/40% | Borde | Crítica | Compras por tramo MPN | Descuento por tramo correcto |
| E2E-COMP-06 | 🔎 Comisiones Gen1–Gen5 (10/5/4/3/2), tope 24% | Happy | Crítica | Venta en red de 5 niveles | Pago por generación correcto |
| E2E-COMP-07 | 🔎 Desbloqueo Gen2 (2 directos activos) | Borde | Alta | Cumplir requisito | Gen2 habilitada |
| E2E-COMP-08 | 🔎 Desbloqueo Gen3 (80 PC + 3 directos + 2 líneas 300 PC) | Borde | Alta | Cumplir requisito | Gen3 habilitada |
| E2E-COMP-09 | 🔎 Desbloqueo Gen4 / Gen5 (requisitos del plan) | Borde | Alta | Cumplir requisitos | Gen4/Gen5 habilitadas |
| E2E-COMP-10 | 🔎 Compresión dinámica (saltar inactivo, pagar al siguiente calificado) | Borde | Alta | Intermediario inactivo | Comisión sube al siguiente calificado |
| E2E-COMP-11 | 🔎 Rangos Bronce/Plata/Oro/Platino/Diamante | Happy | Alta | Alcanzar VG por rango | Rango asignado correcto |
| E2E-COMP-12 | 🔎 Bono por rango desde 4º mes consecutivo (Bronce $500…Diamante $10,000) | Borde | Alta | Mantener rango 4 meses | Bono mensual otorgado |
| E2E-COMP-13 | Bono de Inicio Rápido (600 PC en 30 días → $5,000, una vez) | Happy | Alta | Cumplir en 30 días | Bono otorgado una sola vez |
| E2E-COMP-14 | 🔎 Tabla de PC oficiales por producto/nivel cargada | Borde | Alta | Revisar config | PC por producto correctos |
| E2E-COMP-15 | Reversión de VP/VG/comisiones por devolución | Happy | Alta | Devolución validada | Volúmenes y comisiones ajustados |
| E2E-COMP-16 | Solicitud de retiro + comprobante | Happy | Media | Saldo confirmado | Solicitud y recibo registrados |

---

## 12. Administración (ADM) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-ADM-01 | Listar y filtrar pedidos por estado | Happy | Alta | Filtrar | Lista correcta |
| E2E-ADM-02 | Crear orden manual / POS | Happy | Alta | Alta de pedido | Orden creada |
| E2E-ADM-03 | Buscar cliente y ver perfil | Happy | Media | Buscar | Perfil con red y comisiones |
| E2E-ADM-04 | Cambiar patrocinador de un cliente | Happy | Media | Reasignar líder | Vínculo actualizado (sin ciclo) |
| E2E-ADM-05 | Asignar privilegios a empleado | Happy | Media | Editar privilegios | Permisos aplicados |
| E2E-ADM-06 | CRUD de productos (con `vpPoints`, imágenes, variantes) | Happy | Alta | Crear/editar | Producto guardado |
| E2E-ADM-07 | Producto del mes | Happy | Media | Establecer | Reflejado en dashboard/landing |
| E2E-ADM-08 | Stocks: entrada/merma/transferencia/recepción | Happy | Media | Operar inventario | Movimientos registrados |
| E2E-ADM-09 | POS: registrar venta con método de pago | Happy | Alta | Vender | Venta + descuento de stock |
| E2E-ADM-10 | POS: corte de caja | Happy | Media | Corte | Reporte de caja |
| E2E-ADM-11 | POS: descuento de cajero / crédito | Borde | Media | Aplicar | Total ajustado |
| E2E-ADM-12 | 🔎 Aviso interno de pedido por recoger/pagar en sucursal | Borde | Media | Pedido pickup at_store | Operador notificado |
| E2E-ADM-13 | Notificaciones: crear con vigencia y link | Happy | Media | Crear | Estado active/scheduled/expired |
| E2E-ADM-14 | Configurar descuentos/comisiones/rangos/bonos | Happy | Alta | Editar config | Persistida en `/config/rewards` |
| E2E-ADM-15 | 🔎 Configurar códigos de descuento / pagos especiales | Error | Alta | Buscar módulo de cupones | **Ausente** — no existe |
| E2E-ADM-16 | 🔎 Acciones según perfil (vista inicial permitida) | Borde | Media | Login con privilegios limitados | Solo ve vistas permitidas |
| E2E-ADM-17 | 🔎 Configurar pago parcial (pago especial) | Error | Alta | Buscar opción de pago parcial | **Ausente** — no hay soporte |
| E2E-ADM-18 | 🔎 Configurar pago a crédito (pago especial) | Error | Alta | Definir crédito fuera de POS | **Parcial** — solo crédito de cajero en POS |
| E2E-ADM-19 | 🔎 Descuento manual / pago manual configurable | Error | Alta | Definir descuento/pago manual | **Parcial/Ausente** — solo descuento de cajero en POS |
| E2E-ADM-20 | 🔎 Permisos para crear/aplicar códigos de descuento | Borde | Alta | Asignar permiso a rol | Sin módulo de cupones; permisos por definir |

---

## 13. Reportes (REP) 🔎

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-REP-01 | Exportar reporte de Pedidos | Happy | Alta | Exportar mes | XLSX con hojas Pedidos/Por estado/Top clientes |
| E2E-REP-02 | Exportar reporte de Clientes | Happy | Alta | Exportar | Todos / Activos del mes |
| E2E-REP-03 | Exportar reporte de Productos | Happy | Media | Exportar | Ventas / Catálogo |
| E2E-REP-04 | Exportar reporte de Stocks | Happy | Media | Exportar | Inventario / Resumen / Movimientos |
| E2E-REP-05 | Exportar reporte mensual consolidado | Happy | Alta | Exportar | Resumen / Pedidos / Clientes / Productos / Inventario |
| E2E-REP-06 | 🔎 Encabezados de columna presentes aun sin datos | Error | Alta | Exportar mes sin movimientos | Hojas con encabezados (no vacías) |
| E2E-REP-07 | 🔎 Catálogo de reportes necesarios definido | Borde | Media | Revisar | Ventas/red/comisiones/rangos/actividad disponibles |
| E2E-REP-08 | Exportar mes sin datos | Borde | Media | Mes vacío | Sin error; estructura visible |
| E2E-REP-09 | 🔎 Reporte de comisiones | Error | Alta | Exportar comisiones | **Por definir** — no hay export dedicado de comisiones |
| E2E-REP-10 | 🔎 Reporte de red | Error | Media | Exportar red multinivel | **Por definir** — no hay export dedicado de red |
| E2E-REP-11 | 🔎 Reporte de rangos | Error | Media | Exportar rangos | **Por definir** — no hay export dedicado de rangos |
| E2E-REP-12 | 🔎 Reporte de actividad mensual | Borde | Media | Exportar actividad | Parcial vía reporte mensual consolidado (`E2E-REP-05`) |

---

## 14. Notificaciones del portal (NOTI)

| ID | Escenario | Tipo | Prioridad | Pasos | Resultado esperado |
|---|---|---|---|---|---|
| E2E-NOTI-01 | Notificaciones activas filtradas por fecha | Happy | Media | Ver portal | Solo vigentes |
| E2E-NOTI-02 | Marcar notificación como leída | Happy | Baja | Click | Estado `read=true` |
| E2E-NOTI-03 | Notificación programada (futura) | Borde | Baja | Crear con `startAt` futuro | No visible hasta vigencia |
| E2E-NOTI-04 | Notificación expirada | Borde | Baja | `endAt` pasado | No visible |
| E2E-NOTI-05 | Correo de meta lograda | Happy | Media | Transición meta no→sí | Correo enviado una vez |
| E2E-NOTI-06 | 🔎 Aviso de privacidad en primer acceso | Error | Baja | Primer acceso | **Ausente** — debe mostrarse |

---

## 15. Cobertura por funcionalidad (resumen)

| Módulo | Casos | Happy | Borde | Error |
|---|---|---|---|---|
| AUTH | 22 | 9 | 7 | 6 |
| REF | 14 | 7 | 4 | 3 |
| LAND | 7 | 4 | 2 | 1 |
| SHOP | 10 | 6 | 3 | 1 |
| CART | 15 | 5 | 5 | 5 |
| SHIP | 9 | 3 | 3 | 3 |
| PAY | 8 | 4 | 3 | 1 |
| ORD | 7 | 5 | 0 | 2 |
| RET | 12 | 5 | 0 | 7 |
| DASH | 19 | 9 | 8 | 2 |
| PROF | 7 | 3 | 1 | 3 |
| COMP | 16 | 6 | 8 | 2 |
| ADM | 20 | 11 | 5 | 4 |
| REP | 12 | 5 | 3 | 4 |
| NOTI | 6 | 3 | 2 | 1 |
| **Total** | **184** | **85** | **54** | **45** |

> Los **56 casos marcados con 🔎** trazan directamente a los hallazgos del cliente y son el
> conjunto mínimo de regresión prioritario (ver matriz de comparación). Todos los 20 hallazgos
> (H1–H20) y sus sub-puntos quedan cubiertos — ver la matriz de trazabilidad en
> `03-comparacion-matriz-hallazgos-findingu.md`.
