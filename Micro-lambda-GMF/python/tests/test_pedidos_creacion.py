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
