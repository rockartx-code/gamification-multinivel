"""Guardas: el importe de una venta lo pone el catálogo, no quien pide.

Los dos defectos que cierran estas pruebas se encontraron preparando el manual,
al ver que todos los pedidos de ejemplo salían en $0.

1. **El precio lo decidía el cliente.** `_enrich_items_commissionable` copiaba
   del catálogo el nombre, los `vpPoints` y `commissionable`, pero no el precio,
   y `_calculate_totals` leía `it.get("price", 0)`. Comprobado contra el sistema
   corriendo: un pedido de dos unidades de un producto de $650 con `"price": 1`
   se creaba por **$2.00**, y sin `price` por **$0.00**.

2. **Un precio con centavos reventaba el checkout.** El navegador manda `199.9`
   —`JSON.stringify` no escribe `199.90`— y el serializador de DynamoDB rechaza
   los floats: HTTP 500, «Float types are not supported. Use Decimal types
   instead.». No se notaba porque todo el catálogo tiene precios cerrados; el
   día que un producto costara $199.90, nadie podría comprarlo.

Los dos se arreglan en el mismo sitio (`core/catalogo.py`): si el precio se
resuelve contra el catálogo y con `_to_decimal`, ni lo decide quien llama ni
llega nunca un float al almacenamiento.
"""
import json
from decimal import Decimal

import pytest

import inventory_lambda
import order_lambda

CAJERA = {"x-user-id": "paco"}
DIRECCION = {"street": "x", "number": "1", "city": "Qro", "state": "Qro",
             "postalCode": "76000", "country": "MX"}


def _producto(utils, pid, precio, activo=True):
    # `_to_decimal` igual que hace `catalog_lambda` al dar de alta un producto:
    # la tabla rechaza floats, así que el catálogo nunca guarda uno.
    utils._put_entity("PRODUCT", pid, {
        "entityType": "product", "productId": pid, "name": f"Producto {pid}",
        "price": utils._to_decimal(precio), "vpPoints": 10, "active": activo})
    return pid


def _pedir(items):
    return order_lambda.handle_create_order(
        {"customerName": "Karla", "email": "k@test.com", "items": items,
         "recipientName": "Karla", "deliveryType": "shipping",
         "shippingAddress": DIRECCION}, {})


def _orden(r):
    return json.loads(r["body"])["order"]


# ── 1. el precio no lo pone quien pide ──────────────────────────────────────

def test_un_precio_inventado_en_la_peticion_se_ignora(utils):
    pid = _producto(utils, 1, 650)

    r = _pedir([{"productId": pid, "quantity": 2, "price": 1}])

    assert r["statusCode"] in (200, 201), r["body"]
    pedido = _orden(r)
    assert Decimal(str(pedido["grossSubtotal"])) == Decimal("1300"), (
        "dos unidades de un producto de $650 son $1,300, mande lo que mande el cuerpo")
    assert Decimal(str(pedido["items"][0]["price"])) == Decimal("650")


def test_sin_precio_el_pedido_no_vale_cero(utils):
    pid = _producto(utils, 2, 480)

    pedido = _orden(_pedir([{"productId": pid, "quantity": 2}]))

    assert Decimal(str(pedido["grossSubtotal"])) == Decimal("960")


def test_un_precio_regalado_no_llega_al_ledger(utils):
    """El agujero costaba dinero dos veces: el cobro y la comisión que genera."""
    pid = _producto(utils, 3, 800)

    pedido = _orden(_pedir([{"productId": pid, "quantity": 1, "price": 0}]))

    assert Decimal(str(pedido["netTotal"])) == Decimal("800")


def test_el_mostrador_tampoco_acepta_el_precio_del_cuerpo(utils):
    pid = _producto(utils, 4, 500)
    utils._put_entity("STOCK", "STK-1", {"entityType": "stock", "stockId": "STK-1",
                                         "name": "Tienda", "inventory": {str(pid): 10},
                                         "linkedUserIds": ["paco"]})

    r = inventory_lambda.handle_pos_sale(
        {"stockId": "STK-1", "paymentMethod": "cash",
         "items": [{"productId": pid, "quantity": 2, "price": 1}]}, CAJERA)

    assert r["statusCode"] == 201, r["body"]
    venta = json.loads(r["body"])
    total = venta.get("sale", venta).get("grossSubtotal")
    assert Decimal(str(total)) == Decimal("1000"), (
        "cobrar distinto en el mostrador va por el descuento de cajera con código "
        "de autorización, no por escribir otro número en la petición")


# ── 2. los centavos no revientan el pedido ──────────────────────────────────

@pytest.mark.parametrize("precio, esperado", [
    (199.9, "199.9"),      # lo que manda el navegador para $199.90
    (199.99, "199.99"),
    (1250.5, "1250.5"),
    (650, "650"),          # el caso que sí funcionaba
])
def test_un_producto_con_centavos_se_puede_comprar(utils, precio, esperado):
    pid = _producto(utils, f"C{precio}", precio)

    r = _pedir([{"productId": pid, "quantity": 1}])

    assert r["statusCode"] in (200, 201), (
        f"un producto de ${precio} debería poder comprarse: {r['body'][:160]}")
    pedido = _orden(r)
    assert Decimal(str(pedido["grossSubtotal"])) == Decimal(esperado)


def test_el_precio_guardado_es_decimal_no_float(utils):
    """DynamoDB rechaza floats; guardar el precio como float rompía el pedido."""
    from core import catalogo

    _producto(utils, 5, 199.9)
    linea, error = catalogo.resolver_linea({"productId": 5, "quantity": 1})

    assert error is None
    assert isinstance(linea["price"], Decimal), type(linea["price"])


# ── 3. lo que ya no existe no se puede pedir ────────────────────────────────

def test_un_producto_que_no_esta_en_el_catalogo_no_crea_pedido(utils):
    r = _pedir([{"productId": "NO-EXISTE", "quantity": 1, "price": 999}])

    assert r["statusCode"] == 400, r["body"]
    assert "catálogo" in json.loads(r["body"])["message"]


def test_un_producto_dado_de_baja_no_se_puede_pedir(utils):
    pid = _producto(utils, 6, 300, activo=False)

    r = _pedir([{"productId": pid, "quantity": 1}])

    assert r["statusCode"] == 400, r["body"]
    assert "disponible" in json.loads(r["body"])["message"]


def test_de_extremo_a_extremo_un_producto_de_199_90_se_da_de_alta_y_se_compra(utils):
    """La reproducción exacta del defecto que se veía desde el navegador.

    `JSON.stringify` manda `199.9`, no `199.90`. Antes ese número viajaba en la
    línea del pedido, llegaba tal cual al almacenamiento y el checkout moría con
    HTTP 500. Ahora el alta lo normaliza y la compra lo toma de ahí.
    """
    import catalog_lambda

    r = catalog_lambda.handle_products(
        "POST", {"name": "Con centavos", "price": 199.9, "vpPoints": 4, "active": True}, None)
    assert r["statusCode"] in (200, 201), r["body"]
    pid = json.loads(r["body"])["product"]["productId"]

    r = _pedir([{"productId": pid, "quantity": 3}])

    assert r["statusCode"] in (200, 201), r["body"]
    assert Decimal(str(_orden(r)["grossSubtotal"])) == Decimal("599.7")
