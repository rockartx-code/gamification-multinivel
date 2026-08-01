# Correcciones y mejoras aplicadas — 2026-08-01

Cierre del ciclo iniciado con la suite E2E (`05-cobertura-e2e-playwright-y-hallazgos.md`). Estado final: **205/205 tests E2E en verde**, `npm run build` OK. Nada desplegado a AWS ni commiteado a git (pendiente de decisión).

## 1. Errores reportados en dev — causa raíz y fix

| Error | Causa raíz | Fix |
|---|---|---|
| "Internal Inventory Error" / "No se pudo crear la orden" | DynamoDB rechaza `float` de Python (`Float types are not supported`). El JSON del carrito se parseaba sin `parse_float=Decimal` y order/inventory casteaban montos a `float` antes de persistir. Evidencia: CloudWatch `/aws/lambda/Multinivel-order` y `-inventory` (2026-07-22) + reproducción offline con `TypeSerializer`. | `core_utils.py` (`_parse_body` con `parse_float=Decimal`), `order_lambda.py`, `inventory_lambda.py` (sin casts a float; errores de datos ahora devuelven 400 con mensaje claro). |
| Descuentos no aplican | El checkout web nunca envía `buyerType` y `order_lambda` asumía `"guest"` → 0% descuento y sin acumulación de monto personal. Verificado: 30/30 órdenes reales en dev con `buyerType:'guest'`, `discountRate:0`. | `order_lambda.handle_create_order` infiere `registered` cuando hay `customerId` autenticado. |
| Nadie califica como "activo" | Las microlambdas comparaban el umbral `activationNetMin` ($2,500 **pesos**) contra **puntos VP** (~10-80 por compra); además el flag `isActive` persistido nunca se escribía. Bloqueaba comisiones de generación 2+. | `commissions_lambda`, `dashboard_lambda`, `costumer_lambda`, `catalog_lambda`: activación por `netVolume` (MXN) vs `activationNetMin` (default $2,500). |

## 2. Bugs de frontend corregidos (16, detectados por la suite E2E)

Compra/órdenes: orden reembolsada mostraba "Pago pendiente" con botón de pago; botón Mercado Pago visible en pickup con pago en sucursal; páginas de cancelación/devolución en blanco ante error; foco de validación del checkout roto; sugeridos duplicaban productos del carrito; toast de registro de invitado nunca aparecía (zoneless); `referrerAssociateId` nunca se enviaba (comisión de invitado inalcanzable).

Dashboard/admin/UI: badge "Activa" para miembros inactivos (`ui-status-badge`); toasts/modales sin render tras callbacks async (copiar link, CLABE); botón "Solicitar retiro" de comisiones inexistente (modal era inalcanzable); `honorBoard` nunca mapeado; POS inoperable para superusuario (`Number('admin-001')=NaN`); `aria-label` de `ui-button` no llegaba al botón interno; y `syncBusinessConfigDraft()` mostraba config default en vez de la real (zoneless).

Todos los `test.fixme` fueron convertidos en tests de regresión del comportamiento correcto.

## 3. Peticiones implementadas

1. **Acciones pendientes por privilegios**: el widget/badge/modal de acciones urgentes del admin filtra por privilegio del usuario (mapa acción→privilegio; superusuario ve todo).
2. **Forma de pago al marcar pagado**: modal (efectivo/transferencia/tarjeta/Mercado Pago) antes de confirmar; viaja en el PATCH, se persiste en backend (`order_lambda`, allow-list ampliada) y se muestra en el detalle de la orden.
3. **Sucursales ligadas a stock** (carrito/pickup): solo se listan sucursales con stock completo del carrito; degradación elegante (aviso ámbar, deselección con toast, fallback si el endpoint falla). Sin cambio de backend: `GET /inventory/pickup-stocks` ya traía el inventario y el frontend lo descartaba.
4. **Ticket del corte**: vista imprimible estilo ticket (folio, fecha, operador, sucursal, totales) desde la tarjeta "Último corte", con `@media print`.
5. **Histórico POS agrupado por cortes**: "Corte en curso" (ventas sin corte) + cortes con totales y drill-down "Ver detalles" (ventas + retiros por corte).
6. **Referidos requeridos por nivel**: campo `requiredDirects` en `bonuses.rankThresholds` (config), aplicado en `_compute_rank` (backend), editable en la vista Configuración del admin y visible en la landing.
7. **Usuario activo en pesos**: ver sección 1.
8. **Descuentos**: ver sección 1.
9. **Landing desde configuración**: consumía la config pública pero sin fallback (tablas vacías ante error) — corregido con defaults espejo del backend; muestra también los referidos requeridos por rango.

## 4. Análisis UI/UX

`gamificacion-multinivel-f/docs/ux/analisis-ui-ux-2026-08.md`: 12 pantallas × 2 viewports (24 capturas en `docs/ux/img/`), hallazgos con severidad, top 10 priorizado, inconsistencias sistémicas y quick wins de accesibilidad. Top: barra inferior del admin móvil tapa ~41% del viewport; estados negativos sin variante visual (`--color-danger` sin uso); overlay sobre campo CURP en perfil móvil; sin placeholder de imagen de producto; tabla de comisiones del landing vacía/ilegible.

## 4b. Cutover completado (2026-08-01, tarde)

- Monolito **DEPRECADO**: producción ya consumía las microlambdas; lambda `Multinivel` marcada DEPRECATED en AWS (sin tráfico desde 2026-04).
- Layer `Multinivel-Core` **v19** publicada; las 8 funciones reapuntadas (corrige el bug crítico de Comissions↔layer v16) y 7 funciones con código actualizado.
- Frontend publicado a `s3://findingu-ventas` + CloudFront (ACL `public-read` requerida — el bucket sirve por website endpoint).
- Recursos API Gateway creados y desplegados: `/coupons`+`/coupons/{proxy+}`→order, `/user-dashboard`→Dashboard (cupones y tienda pública funcionan por primera vez).
- `dashboard_lambda`: `/user-dashboard` permite modo invitado anónimo (solo catálogo público); reclamar `userId` sigue exigiendo self-or-admin.
- `inventory_lambda`: fix de routing de `POST /stocks/transfers/{id}/receive` (desplegado).
- Webhook Mercado Pago: `notificationUrl` en config → `.../Prod/webhooks/mercadolibre` (order_lambda).

## 5. Pendientes que requieren decisión/acción

1. **Deploy a dev (AWS)**: los fixes de backend viven solo en el repo. Afectan `core_utils.py` (⚠️ va en la layer compartida `Multinivel-Core` v17 — confirmar empaquetado antes de publicar) y las lambdas order, inventory, commissions, dashboard, costumer, catalog (`aws lambda update-function-code`). Comandos plantilla en el reporte del diagnóstico; sin desplegar, dev seguirá fallando al crear órdenes.
2. **Paridad con el monolito (producción)**: los fixes/features de microlambdas NO existen en `handler.py`. Producción además mantiene el drift de auth (token `demo-token`, sin `/auth/*`).
3. **Nada commiteado**: todo el trabajo (docs, e2e, fixes, features) está en el working tree.
4. Backend aún sin soporte: devoluciones (flujo solo frontend) y cupones en el monolito.
5. Implementar las mejoras del análisis UI/UX (documento priorizado listo).
