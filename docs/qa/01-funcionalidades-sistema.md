# Finding'U — Documento de Funcionalidades del Sistema

> **Propósito:** Inventario completo y verificado de las funcionalidades del sistema Finding'U
> (frontend Angular + backend AWS Lambda/DynamoDB/S3), construido a partir de revisión directa
> del código fuente. Sirve como base para la matriz de pruebas E2E y para la comparación contra
> la matriz de hallazgos del cliente.
>
> **Versión:** Mayo 2026
> **Alcance de revisión:** `gamificacion-multinivel-f/src/app/**` (frontend) y `Micro-lambda-GMF/python/**` (backend).
> **Leyenda de estado de implementación:**
> - ✅ Implementado — funcionalidad presente y operativa en código.
> - ⚠️ Parcial — existe estructura/parte del flujo, pero le falta lógica, configuración o cobertura.
> - ❌ Ausente — no existe en el código revisado.

---

## 1. Arquitectura y módulos

| Capa | Tecnología | Ubicación |
|---|---|---|
| Frontend | Angular 21 (standalone, strict) | `gamificacion-multinivel-f/src/app` |
| Estado de dominio | Servicios `*ControlService` + `BehaviorSubject` | `src/app/services` |
| Acceso a datos | `ApiService` → `RealApiService` / `MockApiService` | `src/app/services` |
| Backend | AWS Lambda (Python) | `Micro-lambda-GMF/python` |
| Persistencia | DynamoDB (tabla única) + S3 (assets) + SES (correo) + Step Functions | `Micro-lambda-GMF/python` |
| Contrato API | OpenAPI 3.0 (API Gateway) | `Micro-lambda-GMF/python/openapi-aws.yaml` |

### Rutas del frontend (`src/app/app.routes.ts`)

| Ruta | Componente | Guard | Descripción |
|---|---|---|---|
| `/` y `/dashboard` | `UserDashboardComponent` | `dashboardGuard` (en `/dashboard`) | Panel del asociado / home |
| `/login` | `LoginComponent` | — | Acceso |
| `/recuperar-contrasena` | `ResetPasswordComponent` | — | Reset con OTP |
| `/verificar-email`, `/verify-email` | `VerifyEmailComponent` | — | Verificación de correo |
| `/admin` | `AdminComponent` | `adminGuard` | Panel administrador |
| `/carrito` | `CarritoComponent` | — | Checkout |
| `/perfil` | `UserProfileComponent` | `dashboardGuard` | Perfil del usuario |
| `/orden/:idOrden` | `OrderStatusComponent` | — | Seguimiento de pedido |
| `/orden/:idOrden/cancelar` | `OrderCancelacionComponent` | — | Cancelación |
| `/orden/:idOrden/devolucion` | `OrderDevolucionComponent` | — | Devolución |
| `/tienda`, `/tienda/:refToken` | `TiendaComponent` | — | Tienda pública / con referido |
| `/landing`, `/landing/:idSponsor` | `LandingComponent` | — | Landing pública / con patrocinador |

> Navegación por *hash* (`/#/...`) para despliegue estático.

---

## 2. Autenticación y cuentas

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 2.1 | **Login** por email/usuario + contraseña, hash SHA-256, sesión en tabla `SESSION`, JWT de 16 hex | ✅ | `auth_utils.py:165`; `login.component.ts` |
| 2.2 | **Redirección por rol** tras login (admin → `/admin`, cliente → `/dashboard`) | ✅ | `login.component.ts:78`; `auth.service.ts` |
| 2.3 | **Bloqueo por email no verificado** (403 + mensaje "Confirma tu cuenta") | ✅ | `auth_utils.py`; `login.component.ts:37` |
| 2.4 | **Reenviar correo de confirmación** desde login | ✅ | `login.component.ts:135` |
| 2.5 | **Recuperación de contraseña** (solicitud OTP 6 dígitos, 15 min, envío SES) | ✅ | `auth_utils.py:411`; `login.component.ts:93` |
| 2.6 | **Reset de contraseña** con OTP (email+otp+password+confirm) | ✅ | `reset-password.component.ts:54`; `auth_utils.py` |
| 2.7 | **Verificación de email** vía token de 24 h | ✅ | `verify-email.component.ts:32`; `auth_utils.py:330` |
| 2.8 | **Cambio de contraseña** autenticado (mín. 8 caracteres) | ✅ | `user-profile.component.ts:287`; `auth_utils.py` |
| 2.9 | **Toggle de visibilidad de contraseña** | ✅ | `login/reset/profile components` |
| 2.10 | **Guards de acceso** `adminGuard`, `dashboardGuard`, `loginGuard` | ✅ | `guards/auth.guard.ts` |

---

## 3. Registro y vinculación de red (referidos)

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 3.1 | **Registro de cuenta** (nombres, email, teléfono, contraseña + confirmación) | ✅ | `landing.component.ts`; `tienda.component.ts:218`; `auth_utils.py:244` |
| 3.2 | **Validación de coincidencia de contraseñas** | ✅ | `landing.component.ts:243` |
| 3.3 | **Captura de patrocinador por ruta** `/landing/:idSponsor` y `/tienda/:refToken` (persistido en `localStorage` como `leaderId`) | ✅ | `landing.component.ts:92`; `tienda.component.ts:93` |
| 3.4 | **Campo manual de código de referido** si no viene en la ruta | ✅ | `landing.component.html:491` |
| 3.5 | **Resolución de patrocinador** desde código de referido → `leaderId` (tabla `REFERRAL_CODE#{code}`) | ✅ | `auth_utils.py:264`, `547` |
| 3.6 | **Persistencia de relación patrocinador-afiliado** en `CUSTOMER.leaderId` y árbol `NETWORK_TREE` | ✅ | `auth_utils.py:270`, `costumer_lambda.py:460-518` |
| 3.7 | **Generación automática de código de referido propio** (`{Nombre}-{Iniciales}`, con desambiguación) | ✅ | `auth_utils.py:275`, `523` |
| 3.8 | **Notificación por correo al patrocinador** cuando alguien se une a su red | ✅ | `auth_utils.py:310` |
| 3.9 | **Estado de registro "pendiente"** (pantalla de verificación de correo) | ✅ | `landing.component.html:381` |
| 3.10 | **Datos públicos del patrocinador** en landing (nombre, mensaje, WhatsApp) | ✅ | `landing.component.ts:322`; `costumer_lambda.py:818` |

---

## 4. Landing y captación

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 4.1 | **Landing con/sin patrocinador** (modo dual) | ✅ | `landing.component.html:25` |
| 4.2 | **Botón WhatsApp al patrocinador** (link dinámico con encoding) | ✅ | `landing.component.ts:209` |
| 4.3 | **Producto destacado por query** `?p=...` | ✅ | `landing.component.ts:93` |
| 4.4 | **Tabla de plan de recompensas** (niveles, %, VP mínimos, bonos por rango, inicio rápido) | ✅ | `landing.component.html:238` |
| 4.5 | **Carga de catálogo y campañas** para destacados | ✅ | `landing.component.ts:336` |
| 4.6 | **Carrusel en landing (home)** de 2 posiciones (Tienda / Conoce el sistema) | ❌ | No encontrado en `landing.*` |
| 4.7 | **Textos del home definidos/cargados** | ⚠️ | Estructura presente; contenidos pendientes de definición |

---

## 5. Tienda y catálogo

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 5.1 | **Listado de productos activos** (`inOnlineStore`) | ✅ | `tienda.component.ts:253`; `catalog_lambda.py` |
| 5.2 | **Filtro por categorías** (árbol de categorías) | ✅ | `tienda.component.ts:144`; `catalog_lambda.py` |
| 5.3 | **Producto destacado (hero) con variantes** y precio dinámico por variante | ✅ | `tienda.component.ts:150` |
| 5.4 | **Agregar al carrito** desde tienda | ✅ | `tienda.component.ts:181` |
| 5.5 | **Contador y subtotal de carrito** en tienda | ✅ | `tienda.component.ts:109` |
| 5.6 | **Registro desde tienda** (mismo formulario, capta `refToken`) | ✅ | `tienda.component.ts:68` |
| 5.7 | **Campo `vpPoints` por producto** en modelo de datos | ✅ | `catalog_lambda.py:79`, `217`; `admin.model.ts:284` |
| 5.8 | **Visualización de PC oficiales + PC netos por nivel de descuento en tarjeta de producto** | ⚠️ | El dato `vpPoints` existe; la visualización explícita en catálogo no es completa |
| 5.9 | **URL directa/limpia a la tienda** (p. ej. `tienda.findingu.com.mx`) | ❌ | Solo existe ruta hash `/#/tienda`; sin subdominio/redirección dedicada |

---

## 6. Carrito y checkout

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 6.1 | **Edición de cantidades** y cálculo de subtotal | ✅ | `carrito.component.ts:375` |
| 6.2 | **Cálculo de descuento** y **total** (incluye envío) | ✅ | `carrito.component.ts:379`, `386` |
| 6.3 | **Productos sugeridos** por scoring de tags (solo frontend) | ⚠️ | `carrito.component.ts:204-240`; sin lógica de backend |
| 6.4 | **Persistencia/restauración de estado de entrega** en `localStorage` | ✅ | `carrito.component.ts:132`, `176` |
| 6.5 | **Direcciones de envío guardadas + selección** | ✅ | `carrito.component.ts:69`, `872` |
| 6.6 | **Validación de formulario de entrega** (CP 5 dígitos) + foco al primer error | ✅ | `carrito.component.ts:837`; `overview.md` |
| 6.7 | **Selección de tipo de entrega** `delivery` / `pickup` | ✅ | `carrito.component.ts:48` |
| 6.8 | **Recoger en sucursal**: carga de `pickup-stocks` y selección de sucursal | ✅ | `carrito.component.ts:963`; `order_lambda.py:495` |
| 6.9 | **Pago en sucursal** `pickupPaymentMethod` (`online` / `at_store`) | ✅ | `carrito.component.ts:49`, `543`; `order_lambda.py:498` |
| 6.10 | **Cotización de envío** (peso/dimensiones del producto → tarifas) | ✅ | `carrito.component.ts:642`; `shipping_lambda.py` |
| 6.11 | **Creación de orden** y redirección a seguimiento | ✅ | `carrito.component.ts:543`; `order_lambda.py:455` |
| 6.12 | **Aplicación de código de descuento/cupón** en checkout | ❌ | No existe campo ni endpoint de cupón |
| 6.13 | **Comportamiento "Regresar" sin perder alias/carrito** (carrito fantasma) | ⚠️ | Estado se persiste, pero ver hallazgos del cliente (sección comparación) |

---

## 7. Envío y paqueterías

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 7.1 | **Cotización automática de envío** `POST /shipping/quote` | ✅ | `shipping_lambda.py`; `openapi-aws.yaml:2091` |
| 7.2 | **Tarifas por carrier/servicio/precio/días** | ✅ | `shipping_lambda.py`; `envia_quote.md` |
| 7.3 | **Integración con paquetería externa** (Envia.com / Skydropx) | ⚠️ | Estructura y documentación presentes; depende de token/entorno |
| 7.4 | **Punto de retiro público** `GET /pickup-stocks` | ✅ | `order_lambda.py:119`; `openapi-aws.yaml` |
| 7.5 | **Aviso de stock en sucursal elegida** al seleccionar pickup | ⚠️ | Selección de sucursal sí; aviso explícito de stock no confirmado |
| 7.6 | **Generación de guías de envío** | ❌ | No hay generación de guía en el código revisado |

---

## 8. Pagos

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 8.1 | **Checkout en línea (Mercado Pago)** `POST /orders/{id}/checkout` → redirección a `initPoint` | ✅ | `order-status.component.ts:300`; `order_lambda.py` |
| 8.2 | **Webhook de pago (Mercado Libre/Pago)** | ✅ | `order_lambda.py:1157`; `openapi-aws.yaml` |
| 8.3 | **Pago en sucursal (al recoger)** sin botón de Mercado Pago | ✅ | `order_lambda.py:498`, `557` |
| 8.4 | **Forma de pago en POS** (efectivo/tarjeta/transferencia/online) | ✅ | `admin.component.ts:337`; `order_lambda.py:557` |
| 8.5 | **Registro de venta de mostrador (`POS_SALE`)** al pasar a `paid` en pickup `at_store` | ✅ | `order_lambda.py:129` |

---

## 9. Seguimiento, cancelación y devolución de pedidos

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 9.1 | **Seguimiento de orden** (estado, timeline, montos, envío/pago) | ✅ | `order-status.component.ts`; `order_lambda.py` |
| 9.2 | **Polling de pago** cada 60 s tras retorno de Mercado Pago | ✅ | `order-status.component.ts:102` |
| 9.3 | **Estados de orden** (`pending`, `paid`, `shipped`, `delivered`, `cancelled`, `en_devolucion`, `devuelto_validado`, `devolucion_rechazada`, `refunded`) | ✅ | `order-status.component.ts:18`; `order_lambda.py:512` |
| 9.4 | **Cancelación** (solo `pending`/`paid`; `pendingRefund` si pagado) | ✅ | `order-cancelacion.component.ts`; `order_lambda.py:751` |
| 9.5 | **Reversión de comisiones** al cancelar pedido pagado | ✅ | `order_lambda.py:795` |
| 9.6 | **Solicitud de devolución** (motivos `DANADO_DEFECTUOSO`, `ERROR_ENVIO`, `DESISTIMIENTO`) | ✅ | `order-devolucion.component.ts`; `order_lambda.py:822` |
| 9.7 | **Validación de plazo** (48 h / 7 días según motivo) | ✅ | `order_lambda.py:822` |
| 9.8 | **Evidencia obligatoria** (fotos producto/empaque/guía) subida a S3 | ✅ | `order-devolucion.component.ts:99`; `order_lambda.py` |
| 9.9 | **Responsabilidad de envío** según motivo (empresa/cliente) | ✅ | `order-devolucion.component.ts:83`; `order_lambda.py` |
| 9.10 | **Inspección backoffice** (checklist 7 puntos → aprobar/rechazar) | ✅ | `order_lambda.py:989` |
| 9.11 | **Reembolso con comprobante** (S3) tras devolución validada o cancelación | ✅ | `order_lambda.py:1104` |
| 9.12 | **Ajuste de PC/volumen/comisiones tras devolución** (void de comisiones) | ✅ | `order_lambda.py`; `commissions_lambda.py:771` |

---

## 10. Dashboard del asociado

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 10.1 | **KPIs de VP (Volumen Personal) y VG (Volumen Grupal)** | ✅ | `user-dashboard.component.ts:358-364`; `dashboard_lambda.py` |
| 10.2 | **Nivel de descuento actual** visible (badge + %) | ✅ | `user-dashboard.component.ts:219-231` |
| 10.3 | **Metas del mes** (activa, secundarias, completadas) con barra de progreso | ✅ | `user-dashboard.component.ts:275`; `dashboard_lambda.py:309` |
| 10.4 | **Red multinivel** (miembros L1–L5, grafo, gasto por miembro) | ✅ | `user-dashboard.component.ts:350`, `862`; `costumer_lambda.py` |
| 10.5 | **Cuadro de Honor** (Top 10 por VG y VP, deltas, modal automático si entra al top) | ✅ | `user-dashboard.component.ts:370`; `dashboard_lambda.py:1034` |
| 10.6 | **Carrusel de destacados** (campañas + featured + productos, paginación) | ✅ | `user-dashboard.component.ts:291`, `1412` |
| 10.7 | **Carrusel de 3 posiciones donde está "Producto del mes"** (requisito específico) | ⚠️ | Existe carrusel de destacados; falta confirmar las 3 posiciones del requisito |
| 10.8 | **Compartir en redes** (canal WhatsApp/Instagram/Facebook, formatos story/feed/banner, copy + imagen al portapapeles) | ✅ | `user-dashboard.component.ts:1449`, `1467`, `2153` |
| 10.9 | **Imágenes optimizadas para compartir** por formato (story/feed/banner) | ⚠️ | Usa assets de campaña/featured; falta set de piezas dedicadas con código de referido |
| 10.10 | **Comisiones**: modal, ledger (pagado/pendiente/bloqueado), CLABE, solicitud de retiro | ✅ | `user-dashboard.component.ts:147`, `1703`, `1813` |
| 10.11 | **Órdenes** (carga paginada, expansión de detalle) | ✅ | `user-dashboard.component.ts:116`, `1187` |
| 10.12 | **Datos del patrocinador** + **botón copiar correo** (además de `mailto`) | ✅ | `user-dashboard.component.html:477-480`; `user-dashboard.component.ts:481` |
| 10.13 | **CTAs para invitado (sin sesión)** | ✅ | `user-dashboard.component.ts:233` |
| 10.14 | **Avisos/notificaciones del portal** filtrados por fecha | ✅ | `user-dashboard.component.ts`; `dashboard_lambda.py:495` |

---

## 11. Perfil del usuario

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 11.1 | **Datos personales** (nombre, teléfono, RFC, CURP) + actualización | ✅ | `user-profile.component.ts:72` |
| 11.2 | **CLABE interbancaria** (18 dígitos, confirmación, máscara) | ✅ | `user-profile.component.ts:142`; `costumer_lambda.py:1170` |
| 11.3 | **Cambio de contraseña** | ✅ | `user-profile.component.ts:287` |
| 11.4 | **Carga de documentos propios** (constancia/INE/CURP, preview PDF/imagen) | ✅ | `user-profile.component.ts:186`; `costumer_lambda.py:1243` |
| 11.5 | **Visualización del patrocinador en el perfil** | ✅ | Disponible vía sponsor en dashboard/perfil; ver hallazgos para detalle |

---

## 12. Plan de compensación (motor de negocio)

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 12.1 | **Unidad de volumen en Puntos (VP/PC)** con `mxnPerVp` configurable (default 50 ≈ $50) | ✅ | `commissions_lambda.py:52`, `223`, `288` |
| 12.2 | **Cálculo de VP por orden** (usa `vpPoints` directo o `price/mxnPerVp`, factor de descuento) | ✅ | `commissions_lambda.py:69-103` |
| 12.3 | **Cálculo de VG** (BFS hasta `maxNetworkLevels`=5) | ✅ | `commissions_lambda.py:141-162` |
| 12.4 | **Activación mensual** por umbral (`activationNetMin`, default 50 VP) | ✅ | `commissions_lambda.py:334` |
| 12.5 | **Escalera de descuentos por volumen** (`discountTiers`) | ⚠️ | Estructura existe pero `discountTiers` por defecto está **vacío**; hay regla *hardcoded* en `order_lambda.py:50-69` |
| 12.6 | **Comisiones por generación** (`commissionLevels`, estado pending/blocked por activación) | ✅ | `commissions_lambda.py:531-593` |
| 12.7 | **Niveles de comisión por defecto** (config trae 2 niveles: 10%, 5%; `default_rates` 3 niveles 10/5/3) | ⚠️ | `commissions_lambda.py:339-340`, `562` — **no** las 5 generaciones del plan de abril |
| 12.8 | **Desbloqueo/bloqueo de generaciones** por actividad del beneficiario | ✅ | `commissions_lambda.py:570-592` |
| 12.9 | **Compresión dinámica** (saltar inactivos y pagar al siguiente calificado) | ⚠️ | Config `cutRule = "hard_cut_no_pass"`: bloquea sin traspasar; no hay compresión ascendente |
| 12.10 | **Rangos de liderazgo** por `rankThresholds` (VG mínimo) | ✅ | `commissions_lambda.py:164-170` |
| 12.11 | **Rangos configurados por defecto** (ORO 700 / PLATINO 2000 / DIAMANTE 6000) | ⚠️ | Faltan **Bronce** y **Plata** del plan de abril |
| 12.12 | **Bono de Inicio Rápido** (primeros 30 días, VG directos ≥ 600 → $5,000) | ✅ | `commissions_lambda.py:378-383` |
| 12.13 | **Bonos por rango / motor de bonos configurable** (condiciones: `vg_min`, `vp_min`, `direct_vg_min`, `consecutive_months`, `direct_rank_count`, `first_30_days`, `first_time`; cooldown once/monthly/annual) | ✅ | `commissions_lambda.py:172-325` |
| 12.14 | **Bonos por rango con tabla del plan de abril** (Bronce $500 … Diamante $10,000 desde 4º mes consecutivo) | ⚠️ | El motor existe, pero la **configuración por defecto** trae bonos distintos (Smart TV, viaje, 2/3 meses) |
| 12.15 | **Tabla de PC oficiales por producto y por nivel de descuento** | ⚠️ | Soporta `vpPoints` por producto; falta la tabla oficial completa cargada/validada |
| 12.16 | **Solicitud de retiro de comisiones + comprobante** | ✅ | `commissions_lambda.py:621-701` |
| 12.17 | **Estadísticas/recibos mensuales de comisiones** | ✅ | `commissions_lambda.py:850` |

---

## 13. Panel de administración

Vistas (sidebar): **Pedidos, Clientes, Empleados, Productos, Stocks, Campañas, Punto de Venta, Estadísticas, Cuadro de Honor, Notificaciones, Configuración** (`admin.component.ts:936-1004`).

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 13.1 | **Pedidos**: listado filtrable por estado, cambio de estado, nueva orden manual | ✅ | `admin.component.ts:358`, `508` |
| 13.2 | **Clientes**: búsqueda, perfil, cambiar patrocinador, privilegios, documentos | ✅ | `admin.component.ts:397-453`, `1408`; `costumer_lambda.py` |
| 13.3 | **Empleados**: CRUD + privilegios + reset password temporal | ✅ | `admin.component.ts:705`; `auth_utils.py:720` |
| 13.4 | **Productos**: CRUD, SKU, precio, `vpPoints`, tags, categorías, peso/dimensiones, imágenes (redes/landing/miniatura), variantes, producto del mes | ✅ | `admin.component.ts:441-507`; `catalog_lambda.py` |
| 13.5 | **Stocks**: crear stock, transferencias, entradas, mermas, movimientos | ✅ | `admin.component.ts:533-563`; `inventory_lambda.py` |
| 13.6 | **Campañas**: CRUD + assets hero | ✅ | `admin.component.ts`; `dashboard_lambda.py:1150` |
| 13.7 | **Punto de Venta (POS)**: registro de venta, métodos de pago, descuento de cajero, crédito, corte de caja | ✅ | `admin.component.ts:583-633`; `inventory_lambda.py` |
| 13.8 | **Forma de pago detallada en POS / pedido con pago en sucursal** | ⚠️ | POS registra método; falta confirmar campo editable en pedido pickup `at_store` desde admin |
| 13.9 | **Aviso interno al operador** cuando hay pedido pendiente de recoger/pagar en sucursal | ⚠️ | Existe `_register_branch_sale_for_pickup_order` y alertas admin; aviso UI explícito a confirmar |
| 13.10 | **Cuadro de Honor** (carga, filtro VG/VP) | ✅ | `admin.component.ts:739` |
| 13.11 | **Notificaciones**: crear/editar con rango de fechas y link, estados (active/scheduled/expired) | ✅ | `admin.component.ts:500`, `859` |
| 13.12 | **Configuración de negocio**: descuentos por tramo, comisiones, rangos, bonos, settings de POS | ✅ | `admin.component.ts:215-336`; `commissions_lambda.py` config |
| 13.13 | **Configuración de códigos de descuento / pagos especiales** (pago parcial, crédito, descuento/pago manual) | ❌ | No existe módulo de cupones; solo descuento de cajero/crédito en POS |
| 13.14 | **Acciones/avisos filtrados por rol** (cliente vs afiliado vs admin) | ⚠️ | Hay privilegios y `getFirstAllowedView`; filtrado fino de avisos por rol a reforzar |

---

## 14. Reportes administrativos (exportación XLSX)

Generación con `xlsx` en `admin.component.ts`. Cada reporte produce un libro con varias hojas:

| # | Reporte | Hojas | Estado | Evidencia |
|---|---|---|---|---|
| 14.1 | **Pedidos** | Pedidos / Por estado / Top clientes | ✅ | `admin.component.ts:1805-1815` |
| 14.2 | **Clientes** | Todos los clientes / Activos del mes | ✅ | `admin.component.ts:1843-1850` |
| 14.3 | **Productos** | Ventas del mes / Catálogo | ✅ | `admin.component.ts:1878-1885` |
| 14.4 | **Stocks** | Inventario actual / Resumen / Movimientos | ✅ | `admin.component.ts:1906-1916` |
| 14.5 | **Reporte mensual consolidado** | Resumen / Pedidos / Clientes activos / Productos / Inventario | ✅ | `admin.component.ts:1921-1983` |
| 14.6 | **Encabezados de columna presentes aun sin datos** | — | ⚠️ | `json_to_sheet` no emite encabezados si el arreglo está vacío (ver hallazgos) |

---

## 15. Notificaciones y avisos del portal

| # | Funcionalidad | Estado | Evidencia |
|---|---|---|---|
| 15.1 | **Listar notificaciones activas** filtradas por rango/fecha | ✅ | `dashboard_lambda.py:495`, `1182` |
| 15.2 | **Crear notificación** (título, descripción, link, vigencia) | ✅ | `dashboard_lambda.py:1150`; `admin.component.ts:500` |
| 15.3 | **Marcar como leída** por cliente | ✅ | `dashboard_lambda.py:1182` |
| 15.4 | **Notificación de metas logradas** por correo (transición no-logrado → logrado) | ✅ | `dashboard_lambda.py:682-801` |

---

## 16. Componentes UI reutilizables

`ui-product-card`, `ui-goal-progress`, `ui-order-timeline`, `ui-networkgraph`, `ui-status-badge`, `ui-modal`, `ui-data-table`, `ui-table`, `ui-sidebar-nav`, `ui-header`, `ui-footer`, `ui-kpi-card`, `ui-form-field`, `ui-button`, `ui-badge`, `feature-badge` (`src/app/components/ui-*`).

---

## 17. Funcionalidades pendientes/ausentes (resumen)

| Funcionalidad | Estado | Nota |
|---|---|---|
| Códigos de descuento / cupones | ❌ | Sin endpoint ni UI de cupón |
| URL directa/subdominio de tienda | ❌ | Solo ruta hash |
| Carrusel de landing (2 posiciones) | ❌ | No implementado |
| Generación de guías de paquetería | ❌ | No implementado |
| Aviso de privacidad del usuario | ❌ | No encontrado en `src/`/`public/` |
| Compresión dinámica de generaciones | ⚠️ | `hard_cut_no_pass` (sin traspaso ascendente) |
| Plan de compensación de abril 2026 completo (5 generaciones, Bronce/Plata, escalera 0/10/20/30/40%, bonos por rango mensuales) | ⚠️ | Motor configurable presente; configuración por defecto difiere del plan |
| Imágenes dedicadas para compartir con código del afiliado | ⚠️ | Usa assets genéricos de campaña/featured |
| Visualización de PC oficiales + netos por producto en catálogo | ⚠️ | Dato presente, visualización incompleta |

> Las divergencias del plan de compensación se detallan en `03-comparacion-matriz-hallazgos-findingu.md`.
