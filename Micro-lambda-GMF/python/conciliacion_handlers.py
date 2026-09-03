"""Conciliación de pagos con MercadoPago (paquete H, propuesta 21).

Cuando el webhook se pierde, el pago aprobado no acredita el pedido: el
cliente pagó y el sistema lo sigue mostrando "pendiente de pago"
(rodrigo-dia3: "el dinero salió, los puntos no llegaron"). Esta ruta consulta
a la pasarela por los pedidos pendientes de las últimas horas y acredita los
que aparecen aprobados. Es idempotente: un pedido ya cobrado no se toca.

Rutas (se montan como extensión de `order_lambda`, §0.2):
  POST /orders/conciliacion          order_mark_paid o superadmin (programable)
  GET  /orders/conciliacion/ultima   access_screen_orders
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

import core_utils as utils

TAREAS_PROGRAMADAS = [("POST", "/orders/conciliacion")]

ENTIDAD_CORRIDA = "RECONCILIATION_RUN"


def _segmentos(request) -> list:
    seg = list(request.segments or [])
    return seg[1:] if seg[:1] == ["orders"] else seg


def atender(request) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = _segmentos(request)
    if not seg or seg[0] != "conciliacion":
        return None
    if len(seg) == 1 and request.method == "POST":
        err = utils._require_admin(request.headers, "order_mark_paid")
        if err:
            return err
        return handle_conciliar(request.body or {}, request.headers)
    if len(seg) == 2 and seg[1] == "ultima" and request.method == "GET":
        err = utils._require_admin(request.headers, "access_screen_orders")
        if err:
            return err
        return handle_ultima_corrida()
    if len(seg) <= 2:
        return utils._json_response(405, {"message": f"Método {request.method} no permitido en conciliación"})
    return None


# ---------------------------------------------------------------------------
# MercadoPago
# ---------------------------------------------------------------------------

def _config_mp() -> dict:
    return (utils._load_app_config().get("payments") or {})


def _buscar_pagos_del_pedido(order_id: str) -> list:
    """GET /v1/payments/search?external_reference={orderId} → lista de pagos."""
    ml_cfg = _config_mp().get("mercadoLibre") or {}
    plantilla = str(ml_cfg.get("paymentSearchUrlTemplate") or "")
    url = plantilla.format(order_id=urllib.parse.quote(str(order_id), safe=""))
    token = utils.os.getenv("MERCADOPAGO_ACCESS_TOKEN") or str(ml_cfg.get("accessToken") or "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as res:
        datos = json.loads(res.read().decode() or "{}")
    return list(datos.get("results") or [])


def _pago_aprobado(pagos: list) -> Optional[dict]:
    for pago in pagos:
        if str(pago.get("status") or "").lower() == "approved":
            return pago
    return None


# ---------------------------------------------------------------------------
# Corrida
# ---------------------------------------------------------------------------

def _pedidos_pendientes(horas: int, order_ids: Optional[list]) -> list:
    """Pedidos `pending` con preferencia de pago creados en la ventana."""
    if order_ids:
        pedidos = [utils._get_by_id("ORDER", oid) for oid in order_ids]
        return [p for p in pedidos if p]
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).replace(microsecond=0)
    desde_iso = desde.isoformat().replace("+00:00", "Z")
    candidatos = utils._query_bucket("ORDER", sk_from=desde_iso)
    return [
        p for p in candidatos
        if str(p.get("status") or "").lower() == "pending" and p.get("paymentPreferenceId")
    ]


def handle_conciliar(body: dict, headers: dict) -> dict:
    """POST /orders/conciliacion — {hours?, orderIds?, dryRun?}."""
    import order_lambda  # anfitrión; import tardío para evitar el ciclo de importación

    cfg = _config_mp()
    try:
        horas_pedidas = body.get("hours")
        horas = int(utils._to_decimal(cfg.get("reconciliationHours") if horas_pedidas in (None, "") else horas_pedidas))
    except Exception:
        return utils._json_response(400, {"message": "El número de horas no es válido"})
    if horas <= 0 or horas > 24 * 90:
        return utils._json_response(400, {"message": "El número de horas debe estar entre 1 y 2160 (90 días)"})
    order_ids = body.get("orderIds") if isinstance(body.get("orderIds"), list) else None
    dry_run = bool(body.get("dryRun"))
    actor = utils._extract_actor(headers)

    inicio = utils._now_iso()
    run_id = f"CONC-{utils.uuid.uuid4().hex[:8].upper()}"
    acreditados, sin_pago, errores = [], [], []
    pendientes = _pedidos_pendientes(horas, order_ids)

    for pedido in pendientes:
        oid = str(pedido.get("orderId") or "")
        if str(pedido.get("status") or "").lower() != "pending":
            # Pedido pedido a mano (orderIds) que ya no está pendiente: no se toca.
            continue
        try:
            pagos = _buscar_pagos_del_pedido(oid)
        except urllib.error.HTTPError as exc:
            errores.append({"orderId": oid, "error": f"MercadoPago respondió {exc.code}"})
            continue
        except Exception as exc:  # noqa: BLE001 - se informa por pedido
            errores.append({"orderId": oid, "error": str(exc) or exc.__class__.__name__})
            continue
        aprobado = _pago_aprobado(pagos)
        if not aprobado:
            sin_pago.append(oid)
            continue
        payment_id = str(aprobado.get("id") or "")
        if dry_run:
            acreditados.append({"orderId": oid, "paymentId": payment_id, "dryRun": True})
            continue
        # Sin actor: el pago viene de la pasarela, igual que en el webhook (la
        # regla del operador de sucursal no aplica a un pago en línea).
        respuesta = order_lambda.handle_update_status(oid, {
            "status": "paid", "paymentId": payment_id, "paidVia": "reconciliation",
            "paymentStatusDetail": "approved", "reconciledAt": utils._now_iso(),
        }, {})
        if respuesta.get("statusCode") != 200:
            errores.append({"orderId": oid, "error": json.loads(respuesta.get("body") or "{}").get("message") or "No se pudo acreditar"})
            continue
        acreditados.append({"orderId": oid, "paymentId": payment_id})

    corrida = {
        "entityType": "reconciliation_run", "runId": run_id, "startedAt": inicio, "finishedAt": utils._now_iso(),
        "hours": horas, "dryRun": dry_run, "checked": len(pendientes),
        "credited": acreditados, "unpaid": sin_pago, "errors": errores,
        "triggeredBy": str(actor.get("user_id") or "sistema"),
    }
    if not dry_run:
        utils._put_entity(ENTIDAD_CORRIDA, run_id, corrida)
    utils._audit_event("orders.reconcile", headers, {"hours": horas, "dryRun": dry_run},
                       {"runId": run_id, "checked": len(pendientes), "credited": len(acreditados)})

    salida = {"runId": run_id, "checked": len(pendientes), "credited": acreditados, "unpaid": sin_pago,
              "errors": errores, "dryRun": dry_run, "hours": horas}
    # Si MercadoPago no respondió para NINGÚN pedido consultado, la corrida no sirvió: 502.
    if pendientes and len(errores) == len(pendientes):
        return utils._json_response(502, {"message": "MercadoPago no respondió; no se pudo revisar ningún pedido", **salida})
    return utils._json_response(200, salida)


def handle_ultima_corrida() -> dict:
    """GET /orders/conciliacion/ultima — la corrida más reciente."""
    corridas = utils._query_bucket(ENTIDAD_CORRIDA, limit=1, forward=False)
    corrida = corridas[0] if corridas else None
    if corrida:
        corrida = {k: v for k, v in corrida.items() if k not in ("PK", "SK")}
    return utils._json_response(200, {"run": corrida})
