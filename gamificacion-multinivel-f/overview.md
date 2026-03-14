# Overview del Proyecto (Nivel Usuario)

Este documento explica el proyecto completo en lenguaje orientado a usuario/operación, no a implementación técnica.

## 1) ¿Qué es este sistema?

Es una plataforma de **ventas con gamificación multinivel** para dos tipos de usuario:

- **Cliente/Asociado**: compra productos, ve metas mensuales, comparte links, crece su red y gestiona comisiones.
- **Administrador**: controla pedidos, clientes, catálogo de productos, alertas y métricas del negocio.

El sistema guía al usuario por un flujo claro:

1. Descubre la oferta en landing.
2. Se registra o inicia sesión.
3. Compra en tienda y paga en carrito.
4. Da seguimiento a su orden.
5. En paralelo, gana beneficios por metas y red.

---

## 2) Experiencia del Usuario Final (Cliente/Asociado)

## 2.1 Landing (`/` o `/:refToken`)

La landing está pensada para conversión:

- Presenta el producto y beneficios.
- Explica recompensas de forma simple (descuento, comisiones, pagos claros).
- Permite registro rápido.
- Soporta **token de referido** (cuando la URL tiene `/:refToken`) para atribuir invitaciones.
- Soporta selección de producto por query (`?p=...`) para campañas.

Resultado para el usuario:

- Entiende valor del producto.
- Se registra con pocos campos.
- Entra directo al dashboard al crear cuenta.

## 2.2 Login (`/login`)

Pantalla de acceso con validación de correo/usuario y contraseña.

- Incluye icono de ojo para mostrar u ocultar la contraseña.
- Incluye flujo de recuperación por correo con OTP.
- El cambio de contraseña vive en `/recuperar-contrasena` y puede recibir `email` y `otp` por query string.

- Si credenciales son correctas:
  - Admin va a `/admin`.
  - Cliente va a `/dashboard`.
- Si son inválidas, muestra error claro.

## 2.3 Dashboard de Cliente (`/dashboard`)

Es el centro operativo del asociado. Incluye:

- **Meta principal del mes** con barra de progreso.
- **Metas secundarias** (opcionalmente visibles).
- **Notificaciones del portal**:
  - aparecen al iniciar sesión,
  - aceptan link opcional para capacitaciones o recordatorios,
  - se marcan como leí­das para no repetirse.
- **Tienda** con producto del mes, productos destacados y sugeridos.
- **Carrito** rápido y acceso a checkout.
- **Red** (estructura de miembros y su estado).
- **Links** para compartir en redes (story/feed/banner).
- **Órdenes** del usuario.
- **Comisiones**:
  - estado de comisiones,
  - CLABE,
  - solicitud de pago,
  - carga de comprobante.

También maneja casos de invitado:

- Si no hay cuenta activa, muestra CTAs para registrarse y desbloquear beneficios.

## 2.4 Carrito (`/carrito`)

Pantalla para cerrar compra:

- Lista de productos con cantidad editable.
- Sugeridos para aumentar ticket.
- Resumen económico (subtotal, descuento, total).
- Formulario de entrega.
- Botón de pagar que:
  - valida campos obligatorios,
  - marca visualmente faltantes,
  - enfoca el primer campo pendiente,
  - crea la orden.

Después de pagar, redirige al seguimiento de orden.

## 2.5 Seguimiento de Orden (`/orden/:idOrden`)

Pantalla de post-compra:

- Estado actual (pendiente, pagado, enviado, entregado).
- Timeline visual del progreso.
- Resumen de montos (subtotal, descuento, total).
- Detalles de envío o datos de pago según estado.

Objetivo para usuario:

- Tener claridad de “qué sigue” sin contactar soporte.

---

## 3) Experiencia del Administrador (`/admin`)

Panel único para operación diaria con secciones:

- **Pedidos**:
  - ver pedidos por estado,
  - cambiar estado (pendiente/pagado/enviado/entregado),
  - registrar guía o entrega.
- **Clientes**:
  - consultar niveles y estatus,
  - ver estado de comisiones,
  - cargar comprobantes administrativos.
- **Productos**:
  - alta/edición de productos,
  - imágenes por canal (redes, landing, miniatura),
  - selección de producto del mes.
- **Estadísticas**:
  - KPIs y alertas operativas (pagos pendientes, envíos, activos, etc.).

- **Notificaciones**:
  - alta y edición de avisos,
  - programación por rango de fechas,
  - link opcional a materiales, sesiones o recursos.

Además incluye acciones rápidas:

- Nuevo pedido,
- alta de estructura,
- acciones urgentes,
- cierre de sesión.

---

## 4) Modelo de Negocio que refleja la App

La app está diseñada para sostener este ciclo:

1. Venta directa de producto.
2. Activación del cliente por metas mensuales de consumo.
3. Descuentos por nivel.
4. Crecimiento de red por referidos.
5. Comisiones por actividad de la red.
6. Pago de comisiones con trazabilidad (CLABE + comprobantes).

Por eso casi todas las pantallas combinan:

- consumo personal,
- progreso gamificado,
- crecimiento de red,
- trazabilidad de pedidos y comisiones.

---

## 5) Estructura del Proyecto (Vista General)

## 5.1 Frontend Angular (`src/`)

- `pages/`: pantallas principales por flujo (landing, login, dashboard, carrito, orden, admin).
- `components/ui-*`: librería visual reusable (botones, badges, modales, tablas, nav, network graph, etc.).
- `services/`: estado y lógica de negocio del cliente:
  - autenticación,
  - carrito,
  - dashboard,
  - metas,
  - administración.
- `models/`: contratos de datos de usuario, carrito, admin y auth.
- `guards/`: control de acceso por rol.
- `styles.css`: sistema visual global.

## 5.2 Backend Lambda (`lambda/handler.py`)

Backend principal con endpoints para:

- login y creación de cuenta,
- dashboard de usuario,
- pedidos,
- clientes,
- comisiones,
- activos (imágenes/archivos),
- dashboard admin,
- producto del mes.

Incluye lógica de negocio de red y metas (activación, niveles, progreso, comisiones).

## 5.3 Documentación (`docs/`)

Actualmente hay documentos de soporte para:

- catálogo de componentes UI,
- guía de estilos globales,
- inventarios y validaciones internas.

---

## 6) Navegación principal del sistema

Rutas relevantes:

- `/` → Landing
- `/login` → Login
- `/dashboard` → Panel cliente
- `/carrito` → Checkout
- `/orden/:idOrden` → Seguimiento
- `/admin` → Panel admin
- `/:refToken` → Landing con referido

Nota de UX:

- El proyecto usa navegación con hash (`/#/...`), útil para despliegues sencillos en hosting estático.

---

## 7) Qué obtiene cada tipo de usuario

## Cliente/Asociado

- Compra guiada y seguimiento de pedido.
- Visibilidad de metas y progreso mensual.
- Herramientas para compartir y crecer red.
- Gestión de comisiones y cuenta bancaria (CLABE).

## Administrador

- Control operativo de pedidos y entregas.
- Gestión de catálogo y assets.
- Gestión de clientes y su estado comercial.
- Visión consolidada de métricas y alertas.

---

## 8) Estado funcional actual (resumen)

El proyecto está estructurado como producto completo de operación:

- front office (landing + registro + compra),
- back office (admin),
- capa de negocio gamificada (metas/red/comisiones),
- backend centralizado en Lambda.

En términos de experiencia de usuario, ya cubre el ciclo principal:

**captación → registro → compra → seguimiento → retención por metas/comisiones**.

---

## 9) Recomendación de lectura para onboarding

Para entender el sistema rápidamente, revisar en este orden:

1. `src/app/app.routes.ts`
2. `src/app/pages/landing/*`
3. `src/app/pages/user-dashboard/*`
4. `src/app/pages/carrito/*`
5. `src/app/pages/admin/*`
6. `lambda/handler.py`

Con eso se entiende el 90% del producto desde negocio + operación.
