"""Mínimo por producto y su aviso (paquete F · ronda 26, propuesta 28c).

Toño, almacén: "el día que Guadalajara se quede en 1 pieza, nadie se va a
enterar hasta que un cliente pague y no haya". Hoy la pantalla de Stocks no
tiene mínimo ni aviso: la existencia se lee sucursal por sucursal, a ojo.
"""
import json

import pytest


ALMACEN = {"x-user-id": "tono", "x-user-role": "employee",
           "x-user-privileges": json.dumps({"access_screen_stocks": True, "stock_add_inventory": True})}
CAJERA = {"x-user-id": "mireya", "x-user-role": "employee",
          "x-user-privileges": json.dumps({"access_screen_pos": True})}


@pytest.fixture
def inventory_lambda(utils):
    import inventory_lambda
    return inventory_lambda


@pytest.fixture
def dashboard_lambda(utils):
    import dashboard_lambda
    return dashboard_lambda


def _catalogo(utils):
    utils._put_entity("PRODUCT", 101, {"entityType": "product", "productId": 101, "name": "Colágeno",
                                       "price": 700, "active": True})
    utils._put_entity("PRODUCT", 102, {"entityType": "product", "productId": 102, "name": "Magnesio",
                                       "price": 480, "active": True})
    utils._put_entity("STOCK", "STK-GDL", {"entityType": "stock", "stockId": "STK-GDL", "name": "Guadalajara",
                                           "inventory": {"101": 1, "102": 30}})
    utils._put_entity("STOCK", "STK-CDMX", {"entityType": "stock", "stockId": "STK-CDMX", "name": "Ciudad de México",
                                            "inventory": {"101": 12, "102": 25}})


def _llamar(inventory_lambda, metodo, ruta, cuerpo=None, headers=None):
    return inventory_lambda.lambda_handler({
        "httpMethod": metodo, "path": ruta, "headers": headers or ALMACEN,
        "queryStringParameters": {}, "body": json.dumps(cuerpo or {}),
    }, None)


def _avisos(dashboard_lambda):
    return {w["type"]: w for w in json.loads(dashboard_lambda.get_admin_warnings()["body"])["warnings"]}


def test_el_minimo_se_guarda_por_producto_y_se_lee_de_vuelta(inventory_lambda, utils):
    _catalogo(utils)
    r = _llamar(inventory_lambda, "GET", "/inventory/stocks/minimos")
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"]) == {"minStockDefault": 0, "minimos": {"101": 0, "102": 0}}

    r = _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos", {"minimos": {"101": 5}})
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("PRODUCT", 101)["minStock"] == 5

    r = _llamar(inventory_lambda, "GET", "/inventory/stocks/minimos")
    assert json.loads(r["body"])["minimos"]["101"] == 5


def test_el_minimo_se_valida_y_pide_permiso_de_almacen(inventory_lambda, utils):
    _catalogo(utils)
    assert _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos",
                   {"minimos": {"101": 5}}, headers=CAJERA)["statusCode"] == 403
    assert _llamar(inventory_lambda, "GET", "/inventory/stocks/minimos", headers=CAJERA)["statusCode"] == 403

    r = _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos", {"minimos": {"999": 5}})
    assert r["statusCode"] == 400 and "no existe" in json.loads(r["body"])["message"]
    r = _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos", {"minimos": {"101": -2}})
    assert r["statusCode"] == 400 and "negativo" in json.loads(r["body"])["message"]
    r = _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos", {"minimos": {}})
    assert r["statusCode"] == 400
    assert utils._get_by_id("PRODUCT", 101).get("minStock") is None


def test_el_producto_bajo_su_minimo_sale_en_acciones_urgentes(inventory_lambda, utils, dashboard_lambda):
    _catalogo(utils)
    assert "stock_min" not in _avisos(dashboard_lambda)   # sin mínimo no se inventa un aviso

    _llamar(inventory_lambda, "PUT", "/inventory/stocks/minimos", {"minimos": {"101": 5}})
    avisos = _avisos(dashboard_lambda)
    aviso = avisos["stock_min"]
    assert aviso["text"] == "1 producto bajo su mínimo · Colágeno en Guadalajara: 1 de 5"
    assert aviso["count"] == 1 and aviso["severity"] == "medium"
    assert aviso["items"][0] == {"productId": "101", "productName": "Colágeno", "stockId": "STK-GDL",
                                 "stockName": "Guadalajara", "qty": 1, "minStock": 5}

    # Sin una sola pieza, el aviso es urgente.
    utils._put_entity("STOCK", "STK-GDL", {"entityType": "stock", "stockId": "STK-GDL", "name": "Guadalajara",
                                           "inventory": {"101": 0, "102": 30}})
    assert _avisos(dashboard_lambda)["stock_min"]["severity"] == "high"


def test_el_minimo_por_omision_de_la_configuracion_vigila_a_todos(inventory_lambda, utils, dashboard_lambda):
    _catalogo(utils)
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1",
                                           "config": {"stocks": {"minStockDefault": 20}}})
    utils._invalidate_app_config_cache()
    aviso = _avisos(dashboard_lambda)["stock_min"]
    # Colágeno en las dos sucursales (1 y 12) y Magnesio en CDMX (25 no, 30 no): 2 pares.
    assert aviso["count"] == 2
    assert aviso["text"].startswith("2 productos bajo su mínimo · Colágeno en Guadalajara: 1 de 20")

    assert json.loads(_llamar(inventory_lambda, "GET", "/inventory/stocks/minimos")["body"])["minStockDefault"] == 20
