"""El precio de una línea de venta sale del catálogo, no de quien pide.

Por qué existe este módulo
--------------------------
Hasta ahora `order_lambda._enrich_items_commissionable` copiaba del catálogo el
nombre, los puntos y la bandera `commissionable`, pero **no el precio**, y
`_calculate_totals` leía `it.get("price", 0)`. Es decir: el importe del pedido
lo fijaba el cuerpo de la petición.

    POST /orders  {"items": [{"productId": <de $650>, "quantity": 2, "price": 1}]}
    → 201, pedido por $2.00

    POST /orders  {"items": [{"productId": <de $650>, "quantity": 2}]}
    → 201, pedido por $0.00

Y el mismo dato traía un segundo problema: un precio con centavos llega del
navegador como float de JSON (`199.9`), y el serializador de DynamoDB rechaza
los floats. Cualquier producto que no costara una cantidad entera reventaba el
checkout con «Float types are not supported. Use Decimal types instead.». No se
notaba porque todo el catálogo tiene precios cerrados.

Las dos cosas se arreglan en el mismo sitio: si el precio se resuelve aquí,
contra el catálogo y con `_to_decimal`, ni lo decide el cliente ni llega nunca
un float al almacenamiento.

Qué NO hace
-----------
No es el lugar para descontar. El descuento por volumen lo calcula
`order_lambda._calculate_totals` con la escalera del plan, y el descuento de
mostrador tiene su propio camino con código de autorización
(`inventory_lambda`, `cashierDiscountMode`). Cobrar distinto es una decisión
del negocio con su permiso; escribir otro número en la petición no lo era.
"""

from typing import Any, Optional, Tuple

from .db import _get_by_id
from .settings import D_ZERO
from .values import _to_decimal


def precio_de_catalogo(producto: dict, variante: Any = None):
    """Precio vigente de un producto, o de una de sus variantes.

    Las variantes (sabores, presentaciones) pueden traer precio propio; si no,
    heredan el del producto.
    """
    if variante not in (None, "") and isinstance(producto.get("variants"), list):
        clave = str(variante).strip().lower()
        for v in producto["variants"]:
            if not isinstance(v, dict):
                continue
            nombre = str(v.get("name") or v.get("label") or v.get("id") or "").strip().lower()
            if nombre and nombre == clave and v.get("price") is not None:
                return _to_decimal(v["price"])
    return _to_decimal(producto.get("price") or 0)


def resolver_linea(linea: dict) -> Tuple[dict, Optional[str]]:
    """Completa una línea de venta con los datos del catálogo.

    Devuelve `(línea, error)`. El error es un texto para la persona, no para el
    registro: si el producto ya no existe o quedó inactivo, el pedido no debe
    crearse a medias.

    El precio del catálogo **manda siempre**: lo que venga en `price` se ignora.
    """
    item = dict(linea) if isinstance(linea, dict) else {}
    pid = item.get("productId")
    if pid in (None, ""):
        return item, "Cada línea del pedido necesita un producto"

    producto = _get_by_id("PRODUCT", pid) or _get_by_id("PRODUCT", str(pid))
    if not producto:
        return item, f"El producto {item.get('name') or pid} ya no está en el catálogo"
    if producto.get("active") is False:
        return item, f"«{producto.get('name') or pid}» ya no está disponible"

    # Sin nombre, el back office mostraba "Producto x1".
    if not item.get("name") and producto.get("name"):
        item["name"] = producto.get("name")
    if "commissionable" not in item:
        item["commissionable"] = bool(producto.get("commissionable", True))
    if "vpPoints" not in item and producto.get("vpPoints") is not None:
        item["vpPoints"] = _to_decimal(producto["vpPoints"])

    item["price"] = precio_de_catalogo(
        producto, item.get("variant") or item.get("variantName") or item.get("variante"))
    return item, None


def resolver_lineas(lineas: list) -> Tuple[list, Optional[str]]:
    """`resolver_linea` sobre una lista. Se detiene en el primer problema."""
    resueltas = []
    for linea in lineas or []:
        item, error = resolver_linea(linea)
        if error:
            return [], error
        resueltas.append(item)
    return resueltas, None


def total_bruto(lineas: list):
    """Suma precio × cantidad de líneas ya resueltas."""
    bruto = D_ZERO
    for it in lineas or []:
        try:
            qty = int(_to_decimal(it.get("quantity") or 1))
        except (TypeError, ValueError):
            qty = 1
        bruto += _to_decimal(it.get("price") or 0) * qty
    return bruto
