# Overview del Proyecto

Resumen funcional del producto en lenguaje de negocio y operación.

## Qué es

Plataforma de ventas con gamificación multinivel para dos perfiles:

- Cliente/asociado: compra, sigue pedidos, cumple metas, comparte referidos y gestiona comisiones.
- Administrador: opera pedidos, clientes, catálogo, avisos y métricas.

## Flujo principal

1. El usuario llega a la landing.
2. Se registra o inicia sesión.
3. Compra desde tienda/carrito.
4. Sigue su orden.
5. Mantiene actividad con metas, red y comisiones.

## Experiencia del cliente

### Landing (`/` o `/:refToken`)

- Presenta la oferta y la propuesta de valor.
- Permite registro rápido.
- Soporta referido por `/:refToken` y selección de producto por `?p=...`.

### Login (`/login`)

- Acceso por correo/usuario y contraseña.
- Recuperación por correo con OTP.
- Redirección por rol: admin a `/admin`, cliente a `/dashboard`.

### Dashboard (`/dashboard`)

Centro operativo del asociado. Reúne:

- meta mensual y metas secundarias,
- avisos del portal,
- tienda y carrito,
- red y links para compartir,
- órdenes,
- comisiones, CLABE, comprobantes y documentos asociados por administración.

Si no hay sesión activa, muestra CTAs para registro.

### Carrito (`/carrito`)

- Edita cantidades, muestra sugeridos y resume montos.
- Valida formulario de entrega y enfoca el primer error.
- Crea la orden y redirige a seguimiento.

### Seguimiento (`/orden/:idOrden`)

- Expone estado, timeline, montos y datos de envío/pago.
- Su objetivo es dejar claro el siguiente paso sin soporte manual.

## Experiencia del administrador (`/admin`)

Panel único para operación diaria:

- pedidos y estados logísticos,
- clientes, niveles y comisiones,
- carga de documentos por cliente,
- catálogo y assets,
- métricas y alertas,
- notificaciones con rango de fechas y link opcional.

Incluye accesos rápidos para alta de pedidos, estructura y cierre de sesión.

## Modelo de negocio

La app sostiene este ciclo:

1. venta directa,
2. activación por metas mensuales,
3. descuentos por nivel,
4. crecimiento por referidos,
5. comisiones por actividad de red,
6. pagos con trazabilidad.

Por eso el producto combina consumo personal, progreso gamificado, red, pedidos y comisiones.

## Arquitectura funcional

### Frontend (`src/`)

- `pages/`: pantallas por flujo.
- `components/ui-*`: capa visual reusable.
- `services/`: estado y lógica de negocio del cliente.
- `models/`: contratos de datos.
- `guards/`: control de acceso.
- `styles.css`: sistema visual global.

### Backend (`lambda/handler.py`)

Expone login, registro, dashboard, pedidos, clientes, comisiones, activos, dashboard admin y producto del mes. También concentra reglas de red, metas y comisiones.

### Documentación (`docs/`)

- `catalogo-componentes-ui.md`: API resumida de `ui-*`.
- `guia-diseno-styles.md`: reglas del sistema visual global.
- `validacion-catalogo-componentes.md`: estado de adopción de componentes.
- `inventario-controles-componentizacion.md`: contexto histórico de la componentización.
- `dynamodb-plan.md`: diseño documental de almacenamiento.

## Rutas principales

- `/`: landing
- `/:refToken`: landing con referido
- `/login`: acceso
- `/dashboard`: panel cliente
- `/carrito`: checkout
- `/orden/:idOrden`: seguimiento
- `/admin`: panel admin

Nota: el frontend navega con hash (`/#/...`) para despliegues estáticos simples.

## Valor por rol

- Cliente/asociado: compra guiada, seguimiento, metas, referidos y comisiones.
- Administrador: control operativo, catálogo, clientes y métricas.

## Onboarding rápido

Para entender el producto con rapidez:

1. `src/app/app.routes.ts`
2. `src/app/pages/landing/*`
3. `src/app/pages/user-dashboard/*`
4. `src/app/pages/carrito/*`
5. `src/app/pages/admin/*`
6. `lambda/handler.py`
