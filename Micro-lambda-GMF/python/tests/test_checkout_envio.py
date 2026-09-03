"""Envío visible: la regla de envío gratis se mide sobre el subtotal bruto y el carrito la explica.

Verónica, Patricia, Rosa, Rodrigo y Lucía vieron "Envío gratis" que se volvía
$129 al poner el código postal (docs/qa/22 §5 fila 4).
"""
import json

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, checkout_handlers
    return order_lambda, checkout_handlers


def _config(utils, **shipping):
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "config": {"shipping": {"freeShippingMin": 1000, **shipping}}})
    utils._invalidate_app_config_cache()


def _socio(utils, cid=555):
    utils._put_entity("CUSTOMER", cid, {"entityType": "customer", "customerId": cid, "name": "Rosa"})
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Klinhart", "price": 1090, "vpPoints": 20, "active": True})
    return cid


def _pedido(cid):
    return {"customerId": cid, "customerName": "Rosa", "items": [{"productId": 9, "name": "Klinhart", "price": 1090, "quantity": 1}],
            "deliveryType": "delivery", "shippingCost": 129, "shippingCarrier": "Estafeta",
            "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "QUE", "postalCode": "76000", "country": "MX"}}


def test_gratis_sobre_el_bruto_aunque_el_descuento_deje_el_neto_abajo(modulos, utils):
    """$1,090 brutos con 10 % = $981 netos: con la regla sobre el bruto el envío es gratis."""
    order_lambda, _ = modulos
    _config(utils)
    cid = _socio(utils)
    r = json.loads(order_lambda.handle_create_order(_pedido(cid), {})["body"])["order"]
    assert float(r["discountRate"]) == 0.10 and float(r["netTotal"]) == 981
    assert r["shippingFreeApplied"] is True and float(r["shippingCost"]) == 0
    assert float(r["total"]) == 981


def test_con_basis_net_se_cobra_el_envio(modulos, utils):
    order_lambda, _ = modulos
    _config(utils, freeShippingBasis="net")
    cid = _socio(utils)
    r = json.loads(order_lambda.handle_create_order(_pedido(cid), {})["body"])["order"]
    assert r["shippingFreeApplied"] is False and float(r["shippingCost"]) == 129
    assert float(r["total"]) == 981 + 129


def test_envio_info_dice_tarifa_umbral_y_faltante(modulos, utils):
    order_lambda, _ = modulos
    _config(utils)
    r = order_lambda.lambda_handler({"path": "/orders/checkout/envio-info", "httpMethod": "GET", "headers": {},
                                     "queryStringParameters": {"subtotal": "960"}, "body": ""}, None)
    assert r["statusCode"] == 200
    d = json.loads(r["body"])
    assert d["baseRateMxn"] == 129 and d["freeShippingMin"] == 1000 and d["basis"] == "gross"
    assert d["missingForFree"] == 40 and d["freeNow"] is False
    assert d["checkout"]["invoiceEnabled"] is True and d["checkout"]["regimenesFiscales"]

    r = order_lambda.lambda_handler({"path": "/orders/checkout/envio-info", "httpMethod": "GET", "headers": {},
                                     "queryStringParameters": {"subtotal": "1000"}, "body": ""}, None)
    d = json.loads(r["body"])
    assert d["freeNow"] is True and d["missingForFree"] == 0


def test_sin_regla_no_promete_nada(modulos, utils):
    """freeShippingMin = 0 (valor por omisión): nunca es gratis y no hay faltante que anunciar."""
    order_lambda, ch = modulos
    d = ch.info_envio(5000)
    assert d["freeNow"] is False and d["missingForFree"] == 0 and d["freeShippingMin"] == 0
    assert ch.envio_gratis_aplica({"grossSubtotal": 5000, "netTotal": 5000}, 129) is False
