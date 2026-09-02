"""Un socio que compra en la tienda tiene que activarse y acumular descuento."""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda
    return order_lambda, commissions_lambda


def _socio(utils, cid=555):
    utils._put_entity("CUSTOMER", cid, {"entityType": "customer", "customerId": cid, "name": "Rodrigo", "email": "r@test.com"})
    return cid


def _producto(utils, pid=9):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart", "price": 480, "vpPoints": 10, "active": True})
    return pid


def _pedido(cid, pid, qty=2):
    # Lo que manda el frontend: customerId sí, buyerType NO.
    return {"customerId": cid, "customerName": "Rodrigo", "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": qty}],
            "recipientName": "Rodrigo", "deliveryType": "shipping",
            "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro", "postalCode": "76000", "country": "MX"}}


def test_el_pedido_de_un_socio_no_es_de_invitado(modulos, utils):
    """Regresión: sin buyerType en el cuerpo, el pedido se guardaba como guest
    aunque llevara customerId de un socio con ficha."""
    order_lambda, _ = modulos
    cid, pid = _socio(utils), _producto(utils)
    r = order_lambda.handle_create_order(_pedido(cid, pid), {})
    assert r["statusCode"] in (200, 201), r["body"]
    pedido = json.loads(r["body"]); pedido = pedido.get("order") or pedido
    assert pedido["buyerType"] == "associate"


def test_el_pago_acredita_volumen_personal_al_socio(modulos, utils):
    """Regresión: el socio pagaba 20 puntos exactos y su panel seguía en 0%."""
    order_lambda, commissions_lambda = modulos
    cid, pid = _socio(utils), _producto(utils)
    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid), {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert estado, "tras pagar debe existir el estado mensual del socio"
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("960")


def test_un_pedido_viejo_marcado_guest_con_ficha_tambien_se_acredita(modulos, utils):
    """Los pedidos creados antes de la corrección quedaron como guest con
    customerId; al reprocesarlos deben acreditar igual."""
    order_lambda, commissions_lambda = modulos
    cid, pid = _socio(utils), _producto(utils)
    utils._put_entity("ORDER", "ORD-VIEJO", {"entityType": "order", "orderId": "ORD-VIEJO", "customerId": cid, "buyerType": "guest",
                                             "status": "paid", "netTotal": Decimal("960"), "grossSubtotal": Decimal("960"),
                                             "items": [{"productId": pid, "price": 480, "quantity": 2, "vpPoints": Decimal("10"), "commissionable": True}]})
    commissions_lambda.lambda_handler({"orderId": "ORD-VIEJO", "action": "ORDER_PAID"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert estado and Decimal(str(estado.get("netVolume", 0))) == Decimal("960")


def test_un_invitado_de_verdad_sigue_sin_acreditar(modulos, utils):
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    cuerpo = {**_pedido(None, pid), "customerId": None, "guest": True, "email": "x@test.com"}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    assert not [k for k in utils._table.store if k[0].startswith("ASSOCIATE_MONTH")]


def test_cancelar_o_reembolsar_resta_el_volumen_acreditado(modulos, utils):
    """Regresión: un pedido cancelado o reembolsado dejaba al socio con el
    volumen y los VP de esa compra (seguía "activo" con un pedido devuelto)."""
    order_lambda, commissions_lambda = modulos
    cid, pid = _socio(utils), _producto(utils)
    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid), {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("960")

    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_REFUNDED"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("0")
    assert Decimal(str(estado.get("netVP", 0))) == Decimal("0")
    # Una segunda anulación no resta dos veces.
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_CANCELLED"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("0")


def test_cancelar_un_pedido_nunca_pagado_no_resta_volumen(modulos, utils):
    """Regresión: Verónica canceló un carrito de $1,952 que nunca pagó y quedó
    con -14.6 VP; el motor restaba el volumen aunque jamás se hubiera sumado."""
    order_lambda, commissions_lambda = modulos
    cid, pid = _socio(utils), _producto(utils)
    pendiente = json.loads(order_lambda.handle_create_order(_pedido(cid, pid), {})["body"])
    oid_pendiente = (pendiente.get("order") or pendiente)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid_pendiente, "action": "ORDER_CANCELLED"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert not estado or Decimal(str(estado.get("netVolume", 0))) == Decimal("0")

    pagado = json.loads(order_lambda.handle_create_order(_pedido(cid, pid), {})["body"])
    oid_pagado = (pagado.get("order") or pagado)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid_pagado, "action": "ORDER_PAID"}, None)
    assert utils._get_by_id("ORDER", oid_pagado).get("rewardsAppliedAt")
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("960")
    # El pedido pagado sí se resta al cancelarse.
    commissions_lambda.lambda_handler({"orderId": oid_pagado, "action": "ORDER_CANCELLED"}, None)
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()))
    assert Decimal(str(estado.get("netVolume", 0))) == Decimal("0")


def test_la_pasarela_cobra_el_total_con_descuento(modulos, utils, monkeypatch):
    """Regresión: la preferencia de MercadoPago llevaba precios de lista; el
    socio veía Total $1,137 y pagaba $1,249."""
    order_lambda, _ = modulos
    cid, pid = _socio(utils), _producto(utils)
    utils._put_entity("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()),
                      {"entityType": "associateMonth", "associateId": cid, "monthKey": utils._month_key(), "netVolume": Decimal("1000")})
    pedido = json.loads(order_lambda.handle_create_order({**_pedido(cid, pid, qty=1), "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": 129}, {})["body"])
    o = pedido.get("order") or pedido
    assert float(o["discountRate"]) == 0.1 and float(o["netTotal"]) == 432.0 and float(o["total"]) == 561.0
    capturado = {}
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"id": "pref-1", "init_point": "https://mp/x"}).encode()
    def _urlopen(req, *a, **k):
        capturado["pref"] = json.loads(req.data.decode()); return _Resp()
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", _urlopen)
    r = order_lambda.handle_mercadopago_checkout(o["orderId"], {})
    assert r["statusCode"] == 200, r["body"]
    cobrado = sum(it["unit_price"] * it["quantity"] for it in capturado["pref"]["items"])
    assert abs(cobrado - 561.0) < 0.01, capturado["pref"]["items"]
