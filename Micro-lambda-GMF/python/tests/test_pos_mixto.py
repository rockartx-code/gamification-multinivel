"""Pago mixto en mostrador (paquete E): mitad efectivo, mitad tarjeta."""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def inventory_lambda(utils, monkeypatch):
    import inventory_lambda
    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", "arn:sim:sfn")
    # Código real (no un doble): así la pantalla puede distinguir "no hay código
    # configurado" de "código incorrecto", que es la propuesta 6.
    utils._put_entity("CONFIG", "pos-auth-v1", {"entityType": "config", "configId": "pos-auth-v1",
                                                "posAuthCode": "2468"})
    return inventory_lambda


class _SfnFalso:
    def __init__(self, registro):
        self.registro = registro

    def start_execution(self, **kw):
        self.registro.append(json.loads(kw["input"])["action"])


def _mostrador(utils, pid=201, stock="STK-1"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("STOCK", stock, {"entityType": "stock", "stockId": stock, "name": "Tienda",
                                       "inventory": {str(pid): 40}})
    return pid, stock


def _venta(inventory_lambda, pid, stock, **extra):
    cuerpo = {"stockId": stock, "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": 1}], **extra}
    return inventory_lambda.handle_pos_sale(cuerpo, {"x-user-id": "nadia"})


def test_las_partes_deben_sumar_el_total_y_no_se_descuenta_inventario_si_no(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    r = _venta(inventory_lambda, pid, stock, payments=[{"method": "cash", "amount": 200}, {"method": "card", "amount": 200}])
    assert r["statusCode"] == 400, r["body"]
    assert "$400.00" in json.loads(r["body"])["message"] and "$480.00" in json.loads(r["body"])["message"]
    # Regresión: antes el inventario se descontaba antes de validar y la venta rechazada dejaba el stock en 39.
    assert utils._get_by_id("STOCK", stock)["inventory"][str(pid)] == 40
    r = _venta(inventory_lambda, pid, stock, payments=[{"method": "cash", "amount": 480}, {"method": "vales", "amount": 0}])
    assert r["statusCode"] == 400


def test_la_venta_mixta_acredita_puntos_igual_que_una_normal(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55, "name": "Rodrigo"})
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    r = _venta(inventory_lambda, pid, stock, customerId=55, customerName="Rodrigo", cashReceived=250,
               payments=[{"method": "cash", "amount": 200}, {"method": "transfer", "amount": 280}])
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    assert disparos == ["ORDER_PAID", "ORDER_DELIVERED"]
    assert cuerpo["sale"]["paymentMethod"] == "mixed" and cuerpo["cashPortion"] == 200 and cuerpo["change"] == 50
    assert cuerpo["total"] == 480 and cuerpo["payments"] == [{"method": "cash", "amount": 200}, {"method": "transfer", "amount": 280}]
    guardada = utils._get_by_id("POS_SALE", cuerpo["saleId"])
    assert isinstance(guardada["cashPortion"], Decimal) and guardada["payments"][0]["amount"] == Decimal("200")
    assert utils._get_by_id("ORDER", cuerpo["orderId"])["items"][0]["vpPoints"] == 10
    assert utils._get_by_id("STOCK", stock)["inventory"][str(pid)] == 39


def test_el_corte_solo_cuenta_la_parte_en_efectivo_de_la_mixta(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    r = _venta(inventory_lambda, pid, stock, payments=[{"method": "cash", "amount": 200}, {"method": "card", "amount": 280}])
    assert r["statusCode"] == 201, r["body"]
    assert inventory_lambda._build_pos_cash_control(stock, "nadia")["currentTotal"] == 200
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 200, "cashToKeep": 200, "withdrawalAmount": 0}, {"x-user-id": "nadia"})
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    assert corte["total"] == 200 and corte["cashFromMixed"] == 200 and corte["nonCashTotal"] == 280 and corte["salesCount"] == 1


def test_el_mixto_no_se_mezcla_con_pago_parcial_ni_con_efectivo_insuficiente(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    r = _venta(inventory_lambda, pid, stock, paymentType="partial", amountPaid=300, authCode="2468",
               payments=[{"method": "cash", "amount": 200}, {"method": "card", "amount": 280}])
    assert r["statusCode"] == 400 and "una sola forma de pago" in json.loads(r["body"])["message"]
    r = _venta(inventory_lambda, pid, stock, cashReceived=100,
               payments=[{"method": "cash", "amount": 200}, {"method": "card", "amount": 280}])
    assert r["statusCode"] == 400 and "menor que la parte en efectivo" in json.loads(r["body"])["message"]
    # Una sola parte en la lista es una venta normal de ese método.
    r = _venta(inventory_lambda, pid, stock, payments=[{"method": "card", "amount": 480}])
    assert r["statusCode"] == 201 and json.loads(r["body"])["sale"]["paymentMethod"] == "card"


def test_una_venta_en_efectivo_devuelve_el_cambio_calculado_por_el_servidor(inventory_lambda, utils, monkeypatch):
    """Paco: "¿debo guardarme los $440 de cambio en mi bolsillo?" — el cambio viene del servidor."""
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    r = _venta(inventory_lambda, pid, stock, paymentMethod="cash", cashReceived=500)
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["change"] == 20 and cuerpo["cashPortion"] == 480 and cuerpo["orderId"].startswith("POS-")
    r = _venta(inventory_lambda, pid, stock, paymentMethod="cash", cashReceived=400)
    assert r["statusCode"] == 400
