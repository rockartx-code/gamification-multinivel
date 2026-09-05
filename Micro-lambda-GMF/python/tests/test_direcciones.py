"""Guarda 6 (docs/qa/27 §4): "Guardar esta dirección" guarda, y la suscripción la ve.

El §5 del informe 27 lo pone entre "lo que nunca se había ejercido":
`saveShippingAddress` se manda desde el carrito desde antes de la ronda y **el
backend nunca lo había leído**; solo el mock lo implementaba. De ahí salían dos
números de marzo: 7 de 7 clientes con `addresses = 0` y **cero suscripciones en
todo el mes** — Ernesto llenó el alta completa (Klinhart, día 5, envío a su
domicilio) y le salió *"Aún no tienes direcciones guardadas"*, en un mensaje
que además lo mandaba a guardarla con la casilla que acababa de palomear.

Esta guarda recorre la cadena entera de una sola vez, que es donde se rompía:
casilla → ficha → panel del cliente → alta de suscripción con esa dirección.
`test_direcciones_guardadas.py` cubre las esquinas (dedupe, alias, invitado,
pickup); aquí está el candado del camino completo.
"""
import json
from datetime import date

import pytest

CID = 700
CLIENTE = {"x-user-id": str(CID), "x-user-role": "cliente"}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}

DIRECCION = {
    "street": "Av. Constitución", "number": "1500", "address": "Av. Constitución 1500, Centro",
    "city": "Monterrey", "state": "Nuevo León", "postalCode": "64000", "country": "MX",
    "betweenStreets": "Hidalgo y Padre Mier", "references": "Portón verde",
}


@pytest.fixture
def mundo(utils, monkeypatch):
    import order_lambda, customer_lambda
    from core import email as correo
    monkeypatch.setattr(correo, "_send_ses_email", lambda *a, **k: None)
    utils._put_entity("CUSTOMER", CID, {"entityType": "customer", "customerId": CID, "name": "Ernesto Salas",
                                        "email": "ernesto@test.com", "phone": "8112223344",
                                        "createdAt": utils._now_iso()})
    utils._put_entity("PRODUCT", "P-KLIN", {"entityType": "product", "productId": "P-KLIN", "name": "Klinhart",
                                            "price": 480, "vpPoints": 10, "stock": 50, "isActive": True,
                                            "active": True})
    return order_lambda, customer_lambda


def _llamar(lam, metodo, ruta, cuerpo=None, headers=ADMIN):
    r = lam.lambda_handler({"httpMethod": metodo, "path": ruta, "headers": headers,
                            "queryStringParameters": None, "body": json.dumps(cuerpo or {})}, None)
    return r["statusCode"], json.loads(r["body"] or "{}")


def _pedido(**extra):
    return {"customerId": CID, "customerName": "Ernesto Salas", "email": "ernesto@test.com",
            "phone": "8112223344", "deliveryType": "delivery",
            "items": [{"productId": "P-KLIN", "quantity": 1}],
            "shippingAddress": dict(DIRECCION), **extra}


def test_saveShippingAddress_persiste(mundo, utils):
    order_lambda, customer_lambda = mundo

    # 1. Ernesto palomea la casilla y compra.
    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/create",
                             _pedido(saveShippingAddress=True, shippingAddressLabel="Casa"))
    assert estado == 201, cuerpo

    # 2. La dirección quedó en su ficha, entera y elegible.
    guardadas = utils._get_by_id("CUSTOMER", CID).get("addresses") or []
    assert len(guardadas) == 1, "la ficha se quedaba con addresses = 0"
    casa = guardadas[0]
    assert casa["label"] == "Casa" and casa["street"] == "Av. Constitución" and casa["number"] == "1500"
    assert casa["postalCode"] == "64000" and casa["city"] == "Monterrey" and casa["state"] == "Nuevo León"
    assert casa.get("id"), "sin id no se puede elegir en ningún formulario"
    assert casa["isDefault"] is True
    # …y el pedido deja dicho con qué dirección guardada se hizo.
    assert cuerpo["order"]["savedShippingAddressId"] == casa["id"]

    # 3. El panel del cliente la ve (es lo que lee el formulario de suscripción).
    normalizada = customer_lambda._normalize_dashboard_customer(utils._get_by_id("CUSTOMER", CID))
    assert [d["label"] for d in normalizada["addresses"]] == ["Casa"]
    assert normalizada["defaultAddressId"] == casa["id"]

    # 4. Y la suscripción la acepta: el alta que en todo marzo nadie logró cerrar.
    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/suscripciones",
                             {"items": [{"productId": "P-KLIN", "quantity": 1}], "dayOfMonth": 5,
                              "deliveryType": "delivery", "shippingAddressId": casa["id"]},
                             headers=CLIENTE)
    assert estado == 201, cuerpo
    sub = cuerpo["subscription"]
    assert sub["shippingAddressId"] == casa["id"]
    assert sub["shippingAddress"]["postalCode"] == "64000"
    assert sub["status"] == "active" and date.fromisoformat(sub["nextRunDate"]).day == 5


def test_sin_la_casilla_la_suscripcion_dice_la_verdad_y_no_manda_a_la_casilla(mundo, utils):
    """El otro lado del candado: sin dirección guardada el alta se rechaza, y
    con un motivo que se puede resolver desde donde está la persona.

    Lo que Ernesto leyó —*"Aún no tienes direcciones guardadas"* justo después
    de guardarla— era mentira por el defecto de arriba; sin defecto, el mensaje
    tiene que seguir siendo cierto y no rebotar a la casilla del carrito.
    """
    order_lambda, _ = mundo
    estado, _ = _llamar(order_lambda, "POST", "/orders/create", _pedido(shippingAddressLabel="Casa"))
    assert estado == 201
    assert not (utils._get_by_id("CUSTOMER", CID).get("addresses") or []), "sin casilla no se guarda nada"

    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/suscripciones",
                             {"items": [{"productId": "P-KLIN", "quantity": 1}], "dayOfMonth": 5,
                              "deliveryType": "delivery"}, headers=CLIENTE)
    assert estado == 400, cuerpo
    assert "dirección" in cuerpo["message"]

    # Y hay una salida desde el propio perfil, sin volver a pasar por el carrito.
    _, cliente_lambda = mundo
    token = "session-ernesto"
    utils._put_session(token, {"sessionId": token, "userId": str(CID), "role": "cliente",
                               "name": "Ernesto Salas", "privileges": {}})
    estado, cuerpo = _llamar(cliente_lambda, "PATCH", "/customers/profile",
                             {"newAddress": {**DIRECCION, "label": "Casa"}},
                             headers={"Authorization": f"Bearer {token}"})
    assert estado == 200, cuerpo
    nueva = cuerpo["customer"]["addresses"][0]

    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/suscripciones",
                             {"items": [{"productId": "P-KLIN", "quantity": 1}], "dayOfMonth": 5,
                              "deliveryType": "delivery", "shippingAddressId": nueva["id"]},
                             headers=CLIENTE)
    assert estado == 201, cuerpo


def test_una_direccion_que_no_es_suya_no_se_puede_usar_en_la_suscripcion(mundo, utils):
    """Guardar direcciones abre una puerta de escritura; que no abra una de lectura."""
    order_lambda, _ = mundo
    _llamar(order_lambda, "POST", "/orders/create",
            _pedido(saveShippingAddress=True, shippingAddressLabel="Casa"))
    casa = (utils._get_by_id("CUSTOMER", CID).get("addresses") or [])[0]

    utils._put_entity("CUSTOMER", 701, {"entityType": "customer", "customerId": 701, "name": "Otra",
                                        "email": "otra@test.com", "createdAt": utils._now_iso()})
    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/suscripciones",
                             {"items": [{"productId": "P-KLIN", "quantity": 1}], "dayOfMonth": 5,
                              "deliveryType": "delivery", "shippingAddressId": casa["id"]},
                             headers={"x-user-id": "701", "x-user-role": "cliente"})
    assert estado == 400, cuerpo
    assert "no está entre tus direcciones guardadas" in cuerpo["message"]
