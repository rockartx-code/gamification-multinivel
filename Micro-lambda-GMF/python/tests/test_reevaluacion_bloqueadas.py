"""Las comisiones bloqueadas por inactividad se recalculan cuando el
patrocinador se activa dentro del mismo mes."""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda
    return order_lambda, commissions_lambda


def _cliente(utils, cid, nombre, leader=None):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.lower()}@test.com"}
    if leader is not None:
        item["leaderId"] = leader
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _producto(utils, pid=9):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart", "price": 480, "vpPoints": 10, "active": True})
    return pid


def _pagar(order_lambda, commissions_lambda, cid, pid, qty):
    cuerpo = {"customerId": cid, "customerName": "x", "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": qty}],
              "recipientName": "x", "deliveryType": "shipping",
              "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro", "postalCode": "76000", "country": "MX"}}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    return oid


def _ledger(utils, cid):
    return utils._get_ledger_month(cid, utils._month_key())


def test_activarse_desbloquea_las_comisiones_del_mes(modulos, utils):
    """Marcela (inactiva) tiene un referido que paga $960: su comisión de $96
    queda 'blocked'. Cuando ella compra sus 20 PC ese mismo mes, la fila pasa
    a 'pending'. Antes se quedaba bloqueada para siempre."""
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela")
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)

    oid = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)      # $960 → $96 para Marcela
    filas = _ledger(utils, marcela)["ledger"]
    assert [(r["orderId"], r["status"]) for r in filas] == [(oid, "blocked")]

    _pagar(order_lambda, commissions_lambda, marcela, pid, 2)            # Marcela se activa (20 PC)
    ledger = _ledger(utils, marcela)
    filas = {r["orderId"]: r for r in ledger["ledger"]}
    assert filas[oid]["status"] == "pending", filas
    assert Decimal(str(filas[oid]["amount"])) == Decimal("96.00")
    assert Decimal(str(ledger["totalBlocked"])) == Decimal("0")
    assert Decimal(str(ledger["totalPending"])) == Decimal("96.00")


def test_si_el_pedido_ya_se_entrego_la_comision_reevaluada_queda_confirmada(modulos, utils):
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela")
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)
    oid = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)
    utils._update_by_id("ORDER", oid, "SET #s = :s", {":s": "delivered"}, {"#s": "status"})
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_DELIVERED"}, None)   # nada que confirmar aún

    _pagar(order_lambda, commissions_lambda, marcela, pid, 2)
    filas = {r["orderId"]: r for r in _ledger(utils, marcela)["ledger"]}
    assert filas[oid]["status"] == "confirmed"


def test_la_reevaluacion_se_puede_apagar_por_configuracion(modulos, utils, monkeypatch):
    order_lambda, commissions_lambda = modulos
    cfg = utils._load_app_config()
    cfg["rewards"]["reevaluateBlockedOnActivation"] = False
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela")
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)
    oid = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)
    _pagar(order_lambda, commissions_lambda, marcela, pid, 2)
    filas = {r["orderId"]: r for r in _ledger(utils, marcela)["ledger"]}
    assert filas[oid]["status"] == "blocked"


def test_una_compra_que_no_activa_no_toca_las_bloqueadas(modulos, utils):
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela")
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)
    oid = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)
    _pagar(order_lambda, commissions_lambda, marcela, pid, 1)            # 10 PC: sigue inactiva
    filas = {r["orderId"]: r for r in _ledger(utils, marcela)["ledger"]}
    assert filas[oid]["status"] == "blocked"


def test_el_patrocinador_recibe_correo_cuando_su_red_compra(modulos, utils, monkeypatch):
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela")
    _pagar(order_lambda, commissions_lambda, marcela, pid, 2)            # activa
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)
    correos = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: correos.append((para, asunto)))
    _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)
    assert ("marcela@test.com", "x compró: comisión de $96.00 en camino") in correos or any(p == "marcela@test.com" and "$96.00" in a for p, a in correos)
