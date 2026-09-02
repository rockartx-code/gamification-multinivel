"""Punto de venta: lo que vive el cajero sin capacitación."""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def inventory_lambda(utils, monkeypatch):
    import inventory_lambda
    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", "arn:sim:sfn")
    return inventory_lambda


def _mostrador(utils, pid=201, stock="STK-1"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("STOCK", stock, {"entityType": "stock", "stockId": stock, "name": "Tienda",
                                       "inventory": {str(pid): 40}})
    return pid, stock


class _SfnFalso:
    def __init__(self, registro):
        self.registro = registro

    def start_execution(self, **kw):
        self.registro.append(json.loads(kw["input"])["action"])


def _venta(inventory_lambda, pid, stock, **extra):
    cuerpo = {"stockId": stock, "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": 1}],
              "paymentMethod": "cash", **extra}
    return inventory_lambda.handle_pos_sale(cuerpo, {"x-user-id": "paco"})


def test_el_corte_de_caja_se_guarda_sin_floats(inventory_lambda, utils):
    """Regresión: el corte respondía 500 ("Float types are not supported")
    y el cajero no podía cerrar su caja."""
    pid, stock = _mostrador(utils)
    r = _venta(inventory_lambda, pid, stock)
    assert r["statusCode"] == 201, r["body"]
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashToKeep": 100}, {"x-user-id": "paco"})
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    guardado = utils._get_by_id("POS_CASH_CUT", corte["cashCutId"])
    for campo in ("total", "cashToKeep", "withdrawnAmount", "totalWithdrawals"):
        assert isinstance(guardado[campo], Decimal), (campo, type(guardado[campo]))
    assert guardado["total"] == Decimal("480") and guardado["withdrawnAmount"] == Decimal("380")


def test_la_venta_de_mostrador_a_un_socio_activa_y_comisiona(inventory_lambda, utils, monkeypatch):
    """Regresión: la venta POS creaba un pedido ya entregado y solo disparaba
    ORDER_DELIVERED; el socio que compraba en tienda física no acumulaba
    volumen ni VP y su patrocinador no cobraba."""
    pid, stock = _mostrador(utils)
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55, "name": "Rodrigo"})
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    r = _venta(inventory_lambda, pid, stock, customerId=55, customerName="Rodrigo")
    assert r["statusCode"] == 201, r["body"]
    assert disparos == ["ORDER_PAID", "ORDER_DELIVERED"]
    pedido = utils._get_by_id("ORDER", json.loads(r["body"])["orderId"])
    assert pedido["items"][0]["vpPoints"] == 10  # puntos del catálogo, como en la tienda en línea


def test_la_venta_a_publico_en_general_no_activa_a_nadie(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    r = _venta(inventory_lambda, pid, stock)
    assert r["statusCode"] == 201, r["body"]
    assert disparos == ["ORDER_DELIVERED"]
