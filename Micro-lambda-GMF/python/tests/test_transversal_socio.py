"""Ola B · I2 `transversal-socio`: una sola fórmula para "el producto que te activa".

El correo de bloqueadas del día 20 (paquete A, `_producto_que_salva`) y la
tarjeta "Completa tu activación" del carrito (paquete C,
`sugerir_producto_activacion`) calculaban por separado el producto más barato
que cierra los VP que faltan. Si un día divergían, Bety recibiría por correo
un producto y en el carrito otro. Ahora A delega en C.
"""
from decimal import Decimal

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, checkout_handlers, pagos_handlers
    return order_lambda, checkout_handlers, pagos_handlers


TRAMOS = [
    {"min": 0, "max": 1000, "rate": Decimal("0")},
    {"min": 1000, "max": 2000, "rate": Decimal("0.10")},
    {"min": 2000, "max": 3000, "rate": Decimal("0.20")},
]


def _catalogo(utils):
    for pid, nombre, precio, pc in ((1, "Klinhart", 480, 10), (2, "Naplus", 280, 6), (3, "Longevit", 390, 7)):
        utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": nombre, "price": precio, "vpPoints": pc, "active": True})
    # Fuera de la tienda en línea: el carrito no lo ofrece, el correo tampoco debe hacerlo.
    utils._put_entity("PRODUCT", 4, {"entityType": "product", "productId": 4, "name": "Solo mostrador", "price": 50, "vpPoints": 20, "active": True, "inOnlineStore": False})
    utils._put_entity("PRODUCT", 5, {"entityType": "product", "productId": 5, "name": "Retirado", "price": 10, "vpPoints": 50, "active": False})


def test_el_correo_y_el_carrito_sugieren_el_mismo_producto(modulos, utils):
    """Bety lleva $1,080 netos (10 %) y le faltan 2 VP: Naplus ×1 a $252, en los dos caminos."""
    order_lambda, ch, pagos = modulos
    _catalogo(utils)
    acumulado = Decimal("1080")
    correo = pagos._producto_que_salva(2.0, acumulado, TRAMOS)

    productos = [p for p in utils._query_bucket("PRODUCT") if p.get("inOnlineStore") is not False]
    carrito = ch.sugerir_producto_activacion(
        productos, 2.0, lambda precio: order_lambda._resolve_discount_rate(TRAMOS, acumulado + utils._to_decimal(precio))
    )

    assert correo["name"] == carrito["name"] == "Naplus"
    assert correo["units"] == carrito["units"] == 1
    assert correo["cost"] == carrito["cost"] == 252.0
    # Claves que usa la plantilla del correo, traducidas desde la respuesta del carrito.
    assert correo["id"] == "2" and correo["rate"] == 0.1
    assert correo["vpPerUnit"] == 5.4 and correo["vpTotal"] == 5.4 and correo["price"] == 280.0


def test_sin_hueco_o_sin_catalogo_no_hay_sugerencia(modulos, utils):
    _, _, pagos = modulos
    assert pagos._producto_que_salva(0, 0, TRAMOS) is None
    assert pagos._producto_que_salva(-1, 0, TRAMOS) is None
    # Solo productos retirados o de mostrador: nada que sugerir.
    utils._put_entity("PRODUCT", 5, {"entityType": "product", "productId": 5, "name": "Retirado", "price": 10, "vpPoints": 50, "active": False})
    utils._put_entity("PRODUCT", 4, {"entityType": "product", "productId": 4, "name": "Solo mostrador", "price": 50, "vpPoints": 20, "inOnlineStore": False})
    assert pagos._producto_que_salva(5.0, 0, TRAMOS) is None


def test_varias_unidades_y_tasa_del_tramo_con_el_producto(modulos, utils):
    """Sin acumulado y con 8 VP faltantes gana Klinhart ×1 ($480, 10 VP) sobre Naplus ×2 ($560)."""
    _, _, pagos = modulos
    _catalogo(utils)
    p = pagos._producto_que_salva(8.0, 0, TRAMOS)
    assert p["name"] == "Klinhart" and p["units"] == 1 and p["cost"] == 480.0 and p["rate"] == 0.0
    assert p["vpTotal"] == 10.0
