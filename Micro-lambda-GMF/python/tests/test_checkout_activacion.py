"""Completa tu activación: el carrito sugiere el producto más barato que cierra los VP que faltan.

Cinco socias (Verónica, Bety, Lupita, Claudia, Patricia) quedaron en 18-19 VP
con "20 PC" de catálogo y tuvieron que hacer un segundo pedido chico a mano.
"""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, checkout_handlers
    return order_lambda, checkout_handlers


def _socio(utils, cid=555, **extra):
    utils._put_entity("CUSTOMER", cid, {"entityType": "customer", "customerId": cid, "name": "Bety", "email": "bety@test.com", **extra})
    return cid


def _catalogo(utils):
    utils._put_entity("PRODUCT", 7, {"entityType": "product", "productId": 7, "name": "Naplus", "price": 280, "vpPoints": 6, "active": True})
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Klinhart", "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("PRODUCT", 11, {"entityType": "product", "productId": 11, "name": "Taza", "price": 90, "vpPoints": 0, "active": True})
    utils._put_entity("PRODUCT", 12, {"entityType": "product", "productId": 12, "name": "Retirado", "price": 10, "vpPoints": 50, "active": False})


def _mes(utils, cid, volumen, vp):
    mes = utils._month_key()
    utils._increment_associate_month_net_volume(cid, mes, volumen)
    utils._increment_associate_month_net_vp(cid, mes, vp)


def _cabeceras(cid):
    return {"x-user-id": str(cid), "x-user-role": "cliente"}


def _pedir(order_lambda, body, headers):
    r = order_lambda.lambda_handler({"path": "/orders/checkout/sugerencia-activacion", "httpMethod": "POST",
                                     "headers": headers, "body": json.dumps(body)}, None)
    return r["statusCode"], json.loads(r["body"])


def test_caso_bety_sugiere_naplus(modulos, utils):
    """Bety: 18 VP en el mes, carrito vacío, faltan 2 VP. Naplus (280, 6 PC) con 10 %
    da 5.4 VP netos por $252; Klinhart (480, 10 PC) daría 9 VP por $432. Gana Naplus."""
    order_lambda, _ = modulos
    cid = _socio(utils); _catalogo(utils); _mes(utils, cid, 900, 18)
    estado, cuerpo = _pedir(order_lambda, {"customerId": cid, "items": []}, _cabeceras(cid))
    assert estado == 200, cuerpo
    assert cuerpo["applies"] is True
    assert cuerpo["vpNow"] == 18 and cuerpo["gap"] == 2
    s = cuerpo["suggestion"]
    assert s["name"] == "Naplus" and s["productId"] == 7
    assert s["units"] == 1 and s["netVpPerUnit"] == 5.4 and s["cost"] == 252
    assert s["vpAfter"] == 23.4


def test_sin_hueco_no_sugiere(modulos, utils):
    order_lambda, _ = modulos
    cid = _socio(utils); _catalogo(utils); _mes(utils, cid, 1050, 21)
    estado, cuerpo = _pedir(order_lambda, {"customerId": cid, "items": []}, _cabeceras(cid))
    assert estado == 200 and cuerpo["applies"] is False and cuerpo["suggestion"] is None
    assert cuerpo["gap"] == 0


def test_el_carrito_cuenta_y_el_cupon_recorta_los_vp(modulos, utils):
    """Dos Klinhart (960, 20 PC) sin cupón activan; con un cupón del 10 % quedan 18 VP y se sugiere."""
    order_lambda, _ = modulos
    cid = _socio(utils); _catalogo(utils)
    items = [{"productId": 9, "price": 480, "quantity": 2}]
    estado, sin_cupon = _pedir(order_lambda, {"customerId": cid, "items": items}, _cabeceras(cid))
    assert estado == 200 and sin_cupon["vpAfterCart"] == 20 and sin_cupon["applies"] is False

    utils._put_entity("COUPON", "DIEZ", {"entityType": "coupon", "code": "DIEZ", "type": "percent", "value": 10, "active": True})
    estado, con_cupon = _pedir(order_lambda, {"customerId": cid, "items": items, "couponCode": "DIEZ"}, _cabeceras(cid))
    assert estado == 200, con_cupon
    assert con_cupon["vpAfterCart"] == 18 and con_cupon["applies"] is True
    # El producto sugerido lleva el descuento que tendría la compra completa ($960 + $280 → 10 %)
    # y el mismo recorte del cupón: 6 PC × 0.9 × 0.9 = 4.86 VP netos.
    assert con_cupon["suggestion"]["name"] == "Naplus" and con_cupon["suggestion"]["netVpPerUnit"] == 4.86
    assert con_cupon["suggestion"]["units"] == 1
    # Consultar no consume el cupón.
    assert int(utils._get_by_id("COUPON", "DIEZ").get("redemptions", 0)) == 0


def test_solo_con_sesion_propia(modulos, utils):
    order_lambda, _ = modulos
    cid = _socio(utils); _catalogo(utils)
    assert _pedir(order_lambda, {"customerId": cid, "items": []}, {})[0] == 401
    assert _pedir(order_lambda, {"items": []}, _cabeceras(cid))[0] == 401
    assert _pedir(order_lambda, {"customerId": cid, "items": []}, _cabeceras(999))[0] == 403


def test_en_modo_cliente_no_hay_meta(modulos, utils):
    """Paquete B: quien compra en modo cliente no tiene meta de activación."""
    order_lambda, _ = modulos
    cid = _socio(utils, mode="cliente"); _catalogo(utils); _mes(utils, cid, 900, 18)
    estado, cuerpo = _pedir(order_lambda, {"customerId": cid, "items": []}, _cabeceras(cid))
    assert estado == 200 and cuerpo["applies"] is False and cuerpo["reason"] == "modo_cliente"


def test_la_formula_es_pura_y_elige_el_menor_costo(modulos):
    _, ch = modulos
    productos = [
        {"productId": 1, "name": "Caro", "price": 1000, "vpPoints": 25, "active": True},
        {"productId": 2, "name": "Chico", "price": 100, "vpPoints": 1, "active": True},
        {"productId": 3, "name": "Inactivo", "price": 5, "vpPoints": 50, "active": False},
        {"productId": 4, "name": "Sin puntos", "price": 5, "vpPoints": 0},
    ]
    # Faltan 3 VP sin descuento: Chico ×3 = $300 gana a Caro ×1 = $1,000.
    s = ch.sugerir_producto_activacion(productos, 3, lambda precio: Decimal("0"))
    assert s["name"] == "Chico" and s["units"] == 3 and s["cost"] == 300
    # Con 10 % de descuento Chico rinde 0.9 VP: hacen falta 4 piezas ($360).
    s = ch.sugerir_producto_activacion(productos, 3, lambda precio: Decimal("0.10"))
    assert s["units"] == 4 and s["cost"] == 360
    assert ch.sugerir_producto_activacion(productos, 0, lambda precio: 0) is None
