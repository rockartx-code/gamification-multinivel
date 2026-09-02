"""Creación de pedidos: el camino que recorre cualquier compra."""
from decimal import Decimal

import pytest


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _producto(utils, pid=101, **extra):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Finding Pro 500g",
                                       "price": 800, "vpPoints": 15, "active": True, **extra})


def _pedido_invitado(pid=101):
    return {
        "items": [{"productId": pid, "name": "Finding Pro 500g", "price": 800, "quantity": 1}],
        "guest": True, "customerName": "Lucía Fernández", "email": "lucia@test.com", "phone": "3311112222",
        "recipientName": "Lucía Fernández", "deliveryType": "shipping",
        "shippingAddress": {"street": "Av. Vallarta", "number": "100", "city": "Guadalajara",
                            "state": "Jalisco", "postalCode": "44100", "country": "MX"},
        "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": 129,
    }


def test_un_producto_con_puntos_no_impide_crear_el_pedido(order_lambda, utils):
    """Regresión: `vpPoints` se convertía a float al enriquecer los ítems y el
    serializador de DynamoDB rechazaba el pedido entero ("Float types are not
    supported"). Como el frontend nunca manda vpPoints, fallaba TODA compra de
    un producto con puntos, fuera invitado o socio."""
    _producto(utils)
    respuesta = order_lambda.handle_create_order(_pedido_invitado(), {})
    assert respuesta["statusCode"] in (200, 201), respuesta["body"]

    guardado = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")
    puntos = guardado["items"][0]["vpPoints"]
    assert isinstance(puntos, Decimal) and puntos == Decimal("15")
    # Y el ítem completo debe ser serializable tal cual para DynamoDB.
    from core.db import _ddb_serialize_item
    _ddb_serialize_item(guardado)


class _RespuestaMP:
    def __init__(self): self._b = b'{"id":"pref-1","init_point":"https://mp.test/pagar","sandbox_init_point":"https://mp.test/pagar"}'
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _crear_pedido_invitado(order_lambda, utils):
    _producto(utils)
    import json
    r = order_lambda.handle_create_order(_pedido_invitado(), {})
    d = json.loads(r["body"])
    return d.get("orderId") or d["order"]["orderId"]


def _evento(metodo, ruta, cuerpo=None):
    import json
    return {"httpMethod": metodo, "path": ruta, "headers": {}, "body": json.dumps(cuerpo or {})}


def test_el_invitado_puede_ver_su_pedido_sin_sesion(order_lambda, utils):
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)
    assert r["statusCode"] == 200, r["body"]
    import json
    pedido = json.loads(r["body"])["order"]
    # El seguimiento mostraba "$0": el item crudo no lleva "total".
    assert float(pedido.get("total") or 0) == 800.0, pedido


def test_el_invitado_puede_iniciar_el_pago_sin_sesion(order_lambda, utils, monkeypatch):
    """Regresión: la tienda ofrece comprar sin cuenta y el pedido se creaba,
    pero /checkout exigía sesión del dueño y respondía 401: el invitado nunca
    llegaba a la pasarela."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", lambda *a, **k: _RespuestaMP())
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] == 200, r["body"]
    assert "init_point" in r["body"]


def test_un_pedido_de_socio_sigue_exigiendo_sesion(order_lambda, utils):
    _producto(utils)
    cuerpo = {**_pedido_invitado(), "guest": False, "buyerType": "customer", "customerId": 777}
    utils._put_entity("CUSTOMER", 777, {"entityType": "customer", "customerId": 777, "name": "Socio"})
    import json
    oid = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = oid.get("orderId") or oid["order"]["orderId"]
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] in (401, 403)
