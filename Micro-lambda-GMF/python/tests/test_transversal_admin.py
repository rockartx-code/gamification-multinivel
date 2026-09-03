"""I1 · transversal-admin: cada confirmación del back office muestra lo que el
servidor guardó, así que las respuestas deben traer el dato (folio, estado)."""
import json

import pytest


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _evento(metodo, ruta, cuerpo=None):
    return {"httpMethod": metodo, "path": ruta, "headers": {}, "body": json.dumps(cuerpo or {})}


def test_desactivar_cupon_devuelve_el_cupon_guardado(order_lambda, utils, monkeypatch):
    """Sofía verificaba cada toast recargando: al desactivar un cupón solo
    volvía un mensaje. Ahora vuelve el cupón con `active` tal como quedó."""
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    r = order_lambda.lambda_handler(_evento("POST", "/orders/coupons", {"code": "VERANO20", "type": "percent", "value": 20, "active": True}), None)
    assert r["statusCode"] in (200, 201), r["body"]

    r = order_lambda.lambda_handler(_evento("DELETE", "/orders/coupons/VERANO20"), None)
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["code"] == "VERANO20"
    assert cuerpo["coupon"]["code"] == "VERANO20"
    assert cuerpo["coupon"]["active"] is False
    # Y lo guardado coincide con lo respondido.
    assert utils._get_by_id("COUPON", "VERANO20")["active"] is False


def test_desactivar_cupon_sin_permiso_se_rechaza(order_lambda, utils):
    """Sin sesión de admin ni el privilegio `config_manage` no se toca el cupón."""
    utils._put_entity("COUPON", "VERANO20", {"entityType": "coupon", "code": "VERANO20", "type": "percent",
                                             "value": 20, "active": True})
    r = order_lambda.lambda_handler(_evento("DELETE", "/orders/coupons/VERANO20"), None)
    assert r["statusCode"] == 403, r["body"]
    assert utils._get_by_id("COUPON", "VERANO20")["active"] is True


def test_cancelar_pedido_responde_estado_y_reembolso_pendiente(order_lambda, utils, monkeypatch):
    """La confirmación de "Cancelar pedido" lee folio, estado y si queda
    reembolso pendiente de la respuesta, no del formulario."""
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    utils._put_entity("PRODUCT", 101, {"entityType": "product", "productId": 101, "name": "Finding Pro 500g",
                                       "price": 800, "active": True})
    pedido = {
        "items": [{"productId": 101, "name": "Finding Pro 500g", "price": 800, "quantity": 1}],
        "guest": True, "customerName": "Lucía Fernández", "email": "lucia@test.com", "phone": "3311112222",
        "recipientName": "Lucía Fernández", "deliveryType": "shipping",
        "shippingAddress": {"street": "Av. Vallarta", "number": "100", "city": "Guadalajara",
                            "state": "Jalisco", "postalCode": "44100", "country": "MX"},
        "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": 129,
    }
    r = order_lambda.handle_create_order(pedido, {})
    assert r["statusCode"] in (200, 201), r["body"]
    oid = json.loads(r["body"])["order"]["orderId"]

    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/cancel", {"reason": "la clienta se arrepintió"}), None)
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["orderId"] == oid
    assert cuerpo["status"] == "cancelled"
    assert cuerpo["pendingRefund"] is False  # nunca se pagó: no hay nada que devolver
