"""Webhook de MercadoPago: secreto, idempotencia y rastro del pago (paquete H).

rodrigo-dia3: "el dinero salió, los puntos no llegaron". El webhook aceptaba
cualquier llamada sin secreto, y un webhook repetido volvía a marcar 'paid',
a disparar el motor de comisiones y a mandar el correo.
"""
import json
from decimal import Decimal

import pytest

from test_pedidos_creacion import _crear_pedido_invitado


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, html)))
    return enviados


class _SfnFalso:
    def __init__(self):
        self.ejecuciones = []

    def start_execution(self, **kw):
        self.ejecuciones.append(json.loads(kw.get("input") or "{}"))
        return {"executionArn": "arn:test"}


@pytest.fixture
def sfn(order_lambda, monkeypatch):
    falso = _SfnFalso()
    monkeypatch.setattr(order_lambda, "ORDER_SFN_ARN", "arn:test:sfn", raising=False)
    monkeypatch.setattr(order_lambda, "sfn", falso)
    return falso


class _Respuesta:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def mercadopago(monkeypatch):
    """Doble de /v1/payments/{id}: `pagos[id] = (estado, orderId)`; anota las consultas."""
    import urllib.request
    pagos, consultas = {}, []

    def urlopen(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        consultas.append(url)
        pid = url.rstrip("/").split("/")[-1]
        if pid not in pagos:
            raise RuntimeError("pago desconocido " + pid)
        estado, oid = pagos[pid]
        return _Respuesta({"id": pid, "status": estado, "external_reference": oid})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return {"pagos": pagos, "consultas": consultas}


def _configurar_secreto(utils, store, secreto):
    now = "2026-01-01T00:00:00Z"
    store[("CONFIG#app-v1", "REF")] = {"PK": "CONFIG#app-v1", "SK": "REF", "refPK": "CONFIG", "refSK": f"{now}#app-v1"}
    store[("CONFIG", f"{now}#app-v1")] = {"PK": "CONFIG", "SK": f"{now}#app-v1",
                                          "config": {"payments": {"mercadoLibre": {"webhookSecret": secreto}}}}
    utils._invalidate_app_config_cache()


def _webhook(order_lambda, pago_id, secreto=None):
    query = {"topic": "payment", "id": pago_id}
    if secreto is not None:
        query["webhookSecret"] = secreto
    evento = {"httpMethod": "POST", "path": "/orders/webhooks/mercadolibre", "headers": {},
              "queryStringParameters": query, "body": "{}"}
    r = order_lambda.lambda_handler(evento, None)
    return r["statusCode"], json.loads(r["body"] or "{}")


def test_con_secreto_configurado_y_erroneo_responde_401_y_no_toca_el_pedido(order_lambda, utils, store, mercadopago, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    _configurar_secreto(utils, store, "s3cr3t")
    mercadopago["pagos"]["mp-1"] = ("approved", oid)

    estado, cuerpo = _webhook(order_lambda, "mp-1", secreto="otro")
    assert estado == 401 and cuerpo["message"] == "Secreto de webhook inválido"
    assert utils._get_by_id("ORDER", oid)["status"] == "pending"
    assert mercadopago["consultas"] == [], "con el secreto mal no se consulta a MercadoPago"
    assert buzon == []

    estado, _ = _webhook(order_lambda, "mp-1")          # sin secreto tampoco
    assert estado == 401


def test_con_el_secreto_correcto_acredita_el_pago(order_lambda, utils, store, mercadopago, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    _configurar_secreto(utils, store, "s3cr3t")
    mercadopago["pagos"]["mp-2"] = ("approved", oid)

    estado, cuerpo = _webhook(order_lambda, "mp-2", secreto="s3cr3t")
    assert estado == 200 and cuerpo == {"ok": True, "orderId": oid, "applied": True}
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "paid" and pedido["paymentId"] == "mp-2" and pedido["paidVia"] == "mercadopago"
    assert pedido["paymentStatusDetail"] == "approved" and pedido.get("webhookReceivedAt")
    assert [a for _, a, _ in buzon] and "Recibimos tu pago" in buzon[0][1]


def test_sin_secreto_configurado_se_acepta_y_queda_en_el_log(order_lambda, utils, mercadopago, monkeypatch):
    registros = []
    monkeypatch.setattr(utils, "_log", lambda evento, nivel="INFO", **campos: registros.append(evento))
    oid = _crear_pedido_invitado(order_lambda, utils)
    mercadopago["pagos"]["mp-3"] = ("approved", oid)

    estado, cuerpo = _webhook(order_lambda, "mp-3")
    assert estado == 200 and cuerpo["applied"] is True
    assert utils._get_by_id("ORDER", oid)["status"] == "paid"
    assert "mp_webhook_secret_missing" in registros


def test_el_webhook_repetido_es_idempotente(order_lambda, utils, mercadopago, buzon, sfn):
    """Un solo paidAt, una sola ejecución del motor de comisiones, un solo correo."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    mercadopago["pagos"]["mp-4"] = ("approved", oid)

    estado, primero = _webhook(order_lambda, "mp-4")
    paid_at = utils._get_by_id("ORDER", oid)["paidAt"]
    estado2, segundo = _webhook(order_lambda, "mp-4")
    assert estado == estado2 == 200
    assert primero["applied"] is True
    assert segundo == {"ok": True, "orderId": oid, "applied": False, "idempotent": True}
    assert utils._get_by_id("ORDER", oid)["paidAt"] == paid_at
    assert len([e for e in sfn.ejecuciones if e.get("action") == "ORDER_PAID"]) == 1
    assert len(buzon) == 1


def test_un_pago_rechazado_no_cambia_el_estado_pero_deja_rastro(order_lambda, utils, mercadopago, buzon, sfn):
    oid = _crear_pedido_invitado(order_lambda, utils)
    mercadopago["pagos"]["mp-5"] = ("rejected", oid)

    estado, cuerpo = _webhook(order_lambda, "mp-5")
    assert estado == 200 and cuerpo["ignored"] == "not_approved" and cuerpo["applied"] is False
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "pending" and pedido["paymentStatusDetail"] == "rejected"
    assert sfn.ejecuciones == [] and buzon == []


def test_un_pago_de_un_pedido_inexistente_se_ignora_sin_error(order_lambda, utils, mercadopago):
    mercadopago["pagos"]["mp-6"] = ("approved", "ORD-NOEXISTE")
    estado, cuerpo = _webhook(order_lambda, "mp-6")
    assert estado == 200 and cuerpo["ignored"] == "order_not_found"


def test_si_mercadopago_no_responde_se_devuelve_502_para_que_reintente(order_lambda, utils, mercadopago):
    oid = _crear_pedido_invitado(order_lambda, utils)
    estado, cuerpo = _webhook(order_lambda, "mp-desconocido")
    assert estado == 502 and "MercadoPago" in cuerpo["message"]
    assert utils._get_by_id("ORDER", oid)["status"] == "pending"


def test_marcar_pagado_un_pedido_ya_enviado_no_mueve_nada(order_lambda, utils, buzon, sfn):
    """La guarda de idempotencia vive en handle_update_status: también cubre a la conciliación."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    order_lambda.handle_update_status(oid, {"status": "paid", "paymentId": "mp-7"}, {})
    order_lambda.handle_update_status(oid, {"status": "shipped", "shippingType": "carrier", "trackingNumber": "EST-9"}, {})
    correos, ejecuciones = len(buzon), len(sfn.ejecuciones)

    r = order_lambda.handle_update_status(oid, {"status": "paid", "paymentId": "mp-8"}, {})
    assert r["statusCode"] == 200
    cuerpo = json.loads(r["body"])
    assert cuerpo["alreadyPaid"] is True and cuerpo["order"]["status"] == "shipped"
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "shipped" and pedido["paymentId"] == "mp-7"
    assert len(buzon) == correos and len(sfn.ejecuciones) == ejecuciones


def test_el_pago_en_mostrador_y_el_del_admin_quedan_marcados_por_su_via(order_lambda, utils, monkeypatch):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.handle_update_status(oid, {"status": "paid"}, {"x-user-id": "7", "x-user-role": "admin"})
    assert json.loads(r["body"])["order"]["paidVia"] == "admin"
    assert utils._get_by_id("ORDER", oid).get("total") == Decimal("929.00")
