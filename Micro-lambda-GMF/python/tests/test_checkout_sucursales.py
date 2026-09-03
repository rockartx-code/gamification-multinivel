"""Recoger en sucursal solo si hay sucursal en tu ciudad/estado y con existencia.

Patricia (Mérida) veía la opción aunque la única sucursal está en CDMX; Claudia
recibió "No se pudo crear la orden" porque la sucursal no tenía el producto.
"""
import json

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, inventory_lambda
    return order_lambda, inventory_lambda


def _sucursal_cdmx(utils, magnesio=0):
    utils._put_entity("PRODUCT", 7, {"entityType": "product", "productId": 7, "name": "Naplus", "price": 280, "vpPoints": 6})
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Magnesio", "price": 480, "vpPoints": 10})
    utils._put_entity("STOCK", "STK-DV", {"entityType": "stock", "stockId": "STK-DV", "name": "Del Valle", "location": "Col. Del Valle",
                                          "city": "Ciudad de México", "state": "CMX", "allowPickup": True, "linkedUserIds": [],
                                          "inventory": {"7": 5, "9": magnesio}})
    utils._put_entity("STOCK", "STK-BOD", {"entityType": "stock", "stockId": "STK-BOD", "name": "Bodega Central", "location": "Vallejo",
                                           "city": "Ciudad de México", "state": "CMX", "allowPickup": False, "linkedUserIds": [],
                                           "inventory": {"7": 50, "9": 50}})


def _consultar(order_lambda, body):
    r = order_lambda.lambda_handler({"path": "/orders/checkout/sucursales-recoger", "httpMethod": "POST",
                                     "headers": {}, "body": json.dumps(body)}, None)
    assert r["statusCode"] == 200, r["body"]
    return json.loads(r["body"])


def test_merida_no_tiene_sucursal_pero_ve_donde_si_hay(modulos, utils):
    order_lambda, _ = modulos
    _sucursal_cdmx(utils, magnesio=3)
    d = _consultar(order_lambda, {"city": "Mérida", "state": "YUC", "items": [{"productId": 7, "quantity": 1}]})
    assert d["available"] is False and d["locationGiven"] is True
    assert d["cities"] == ["Ciudad de México"]
    # Solo las sucursales con allowPickup entran en la lista; la bodega no.
    assert [s["id"] for s in d["stocks"]] == ["STK-DV"]
    assert d["stocks"][0]["inArea"] is False and d["stocks"][0]["canPickup"] is False


def test_cdmx_sin_magnesio_muestra_el_faltante(modulos, utils):
    order_lambda, _ = modulos
    _sucursal_cdmx(utils, magnesio=0)
    d = _consultar(order_lambda, {"city": "Ciudad de México", "state": "CMX",
                                  "items": [{"productId": 7, "quantity": 1}, {"productId": 9, "quantity": 1}]})
    assert d["available"] is False
    sucursal = d["stocks"][0]
    assert sucursal["inArea"] is True and sucursal["canPickup"] is False and sucursal["missing"] == ["Magnesio"]


def test_cdmx_con_existencia_permite_recoger(modulos, utils):
    order_lambda, _ = modulos
    _sucursal_cdmx(utils, magnesio=2)
    d = _consultar(order_lambda, {"state": "CMX", "items": [{"productId": 9, "quantity": 2}]})
    assert d["available"] is True and d["stocks"][0]["canPickup"] is True and d["stocks"][0]["missing"] == []


def test_el_estado_se_reconoce_por_nombre_o_codigo_y_la_ciudad_sin_acentos(modulos, utils):
    order_lambda, _ = modulos
    _sucursal_cdmx(utils, magnesio=1)
    assert _consultar(order_lambda, {"state": "Ciudad de Mexico", "items": []})["available"] is True
    assert _consultar(order_lambda, {"state": "CDMX", "items": []})["available"] is True
    assert _consultar(order_lambda, {"city": "ciudad de mexico", "items": []})["available"] is True
    assert _consultar(order_lambda, {"state": "JAL", "city": "Guadalajara", "items": []})["available"] is False


def test_sin_direccion_lista_todas_con_su_existencia(modulos, utils):
    order_lambda, _ = modulos
    _sucursal_cdmx(utils, magnesio=0)
    d = _consultar(order_lambda, {"items": [{"productId": 9, "quantity": 1}]})
    assert d["locationGiven"] is False and d["cities"] == ["Ciudad de México"]
    assert d["stocks"][0]["inArea"] is True and d["stocks"][0]["canPickup"] is False


def test_el_almacen_guarda_ciudad_y_estado(modulos, utils):
    """Formulario de almacén: `city` y `state` en POST y PATCH de /inventory/stocks."""
    _, inventory_lambda = modulos
    r = inventory_lambda.handle_stocks("POST", {"name": "Del Valle", "location": "Col. Del Valle", "city": "Ciudad de México",
                                                "state": "CMX", "allowPickup": True})
    stock = json.loads(r["body"])["stock"]
    assert stock["city"] == "Ciudad de México" and stock["state"] == "CMX"
    r = inventory_lambda.handle_stocks("PATCH", {"city": "Mérida", "state": "YUC"}, stock["stockId"])
    actualizado = json.loads(r["body"])["stock"]
    assert actualizado["city"] == "Mérida" and actualizado["state"] == "YUC"
