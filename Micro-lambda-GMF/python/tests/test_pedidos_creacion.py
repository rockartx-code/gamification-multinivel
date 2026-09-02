"""Creación de pedidos: el camino que recorre cualquier compra."""
from decimal import Decimal

import pytest


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _producto(utils, pid=101, **extra):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Finding Pro 500g",
                                       "price": 800, "vpPoints": 15, "active": True, **extra})


def _pedido_invitado(pid=101):
    return {
        "items": [{"productId": pid, "name": "Finding Pro 500g", "price": 800, "quantity": 1}],
        "guest": True, "customerName": "Lucía Fernández", "email": "lucia@test.com", "phone": "3311112222",
        "recipientName": "Lucía Fernández", "deliveryType": "shipping",
        "shippingAddress": {"street": "Av. Vallarta", "number": "100", "city": "Guadalajara",
                            "state": "Jalisco", "postalCode": "44100", "country": "MX"},
        "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": 129,
    }


def test_un_producto_con_puntos_no_impide_crear_el_pedido(order_lambda, utils):
    """Regresión: `vpPoints` se convertía a float al enriquecer los ítems y el
    serializador de DynamoDB rechazaba el pedido entero ("Float types are not
    supported"). Como el frontend nunca manda vpPoints, fallaba TODA compra de
    un producto con puntos, fuera invitado o socio."""
    _producto(utils)
    respuesta = order_lambda.handle_create_order(_pedido_invitado(), {})
    assert respuesta["statusCode"] in (200, 201), respuesta["body"]

    guardado = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")
    puntos = guardado["items"][0]["vpPoints"]
    assert isinstance(puntos, Decimal) and puntos == Decimal("15")
    # Y el ítem completo debe ser serializable tal cual para DynamoDB.
    from core.db import _ddb_serialize_item
    _ddb_serialize_item(guardado)


class _RespuestaMP:
    def __init__(self): self._b = b'{"id":"pref-1","init_point":"https://mp.test/pagar","sandbox_init_point":"https://mp.test/pagar"}'
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _crear_pedido_invitado(order_lambda, utils):
    _producto(utils)
    import json
    r = order_lambda.handle_create_order(_pedido_invitado(), {})
    d = json.loads(r["body"])
    return d.get("orderId") or d["order"]["orderId"]


def _evento(metodo, ruta, cuerpo=None):
    import json
    return {"httpMethod": metodo, "path": ruta, "headers": {}, "body": json.dumps(cuerpo or {})}


def test_el_invitado_puede_ver_su_pedido_sin_sesion(order_lambda, utils):
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)
    assert r["statusCode"] == 200, r["body"]
    import json
    pedido = json.loads(r["body"])["order"]
    # El seguimiento mostraba "$0": el item crudo no lleva "total".
    assert float(pedido.get("total") or 0) == 929.0, pedido  # 800 + 129 de envío


def test_el_invitado_puede_iniciar_el_pago_sin_sesion(order_lambda, utils, monkeypatch):
    """Regresión: la tienda ofrece comprar sin cuenta y el pedido se creaba,
    pero /checkout exigía sesión del dueño y respondía 401: el invitado nunca
    llegaba a la pasarela."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", lambda *a, **k: _RespuestaMP())
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] == 200, r["body"]
    assert "init_point" in r["body"]


def test_un_pedido_de_socio_sigue_exigiendo_sesion(order_lambda, utils):
    _producto(utils)
    cuerpo = {**_pedido_invitado(), "guest": False, "buyerType": "customer", "customerId": 777}
    utils._put_entity("CUSTOMER", 777, {"entityType": "customer", "customerId": 777, "name": "Socio"})
    import json
    oid = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = oid.get("orderId") or oid["order"]["orderId"]
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] in (401, 403)


def test_el_envio_se_guarda_y_se_cobra(order_lambda, utils, monkeypatch):
    """Regresión: el carrito cotizaba $129 de envío, el pedido lo descartaba
    (total $800 en el seguimiento) y la pasarela cobraba solo los productos."""
    import json
    oid = _crear_pedido_invitado(order_lambda, utils)
    pedido = json.loads(order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)["body"])["order"]
    assert float(pedido["shippingCost"]) == 129.0 and float(pedido["total"]) == 929.0, pedido
    assert float(pedido["netTotal"]) == 800.0, "el envío no debe entrar en la base comisionable"

    enviado = {}
    def _urlopen(req, *a, **k):
        enviado.update(json.loads(req.data.decode())); return _RespuestaMP()
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", _urlopen)
    order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    cobrado = sum(i["unit_price"] * i["quantity"] for i in enviado["items"])
    assert cobrado == 929.0, enviado["items"]


def test_el_invitado_puede_solicitar_devolucion_sin_sesion(order_lambda, utils):
    """Regresión: el asistente de devolución dejaba completar los tres pasos y
    en "Enviar solicitud" respondía "No autenticado"."""
    import json
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET #s = :s, deliveredAt = :d", {":s": "delivered", ":d": utils._now_iso()}, {"#s": "status"}) if False else None
    pedido = utils._get_by_id("ORDER", oid); pedido["status"] = "delivered"; pedido["deliveredAt"] = utils._now_iso()
    utils._table.put_item(Item=pedido)
    cuerpo = {"motivo": "DANADO", "reason": "DANADO", "descripcion": "Tapa rajada",
              "evidencia": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]},
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] not in (401, 403), r["body"]


def test_el_invitado_puede_cancelar_su_pedido_pendiente_sin_sesion(order_lambda, utils):
    """Regresión: el invitado que se arrepiente en la pasarela pulsa "Cancelar
    pedido" y recibía "No autenticado"; el pedido pendiente quedaba colgado."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/cancel", {"reason": "customer_request"}), None)
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("ORDER", oid)["status"] == "cancelled"


def _entregado(utils, oid):
    pedido = utils._get_by_id("ORDER", oid); pedido["status"] = "delivered"; pedido["deliveredAt"] = utils._now_iso()
    utils._table.put_item(Item=pedido)


def test_el_reembolso_suma_el_envio_de_regreso_declarado(order_lambda, utils, monkeypatch):
    """Lucía pagó $165 en Estafeta para regresar el bote; la gerente reembolsó
    "la única cifra que el sistema mostraba" ($800) y ella reclamó después."""
    import json
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    _entregado(utils, oid)
    cuerpo = {"motivo": "DANADO_DEFECTUOSO", "descripcion": "Tapa rajada", "returnShippingCost": 165,
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] == 201, r["body"]
    assert utils._get_by_id("ORDER", oid)["returnShippingCost"] == Decimal("165")
    ok = {"inspection": {"empaque_original": True, "sellos_intactos": True, "sin_uso": True, "coincide_con_pedido": True, "trazabilidad_valida": True}}
    assert order_lambda.handle_return_inspection(oid, ok, {})["statusCode"] == 200
    r = order_lambda.handle_refund_order(oid, {"reason": "return"}, {})
    assert r["statusCode"] == 200, r["body"]
    assert Decimal(str(json.loads(r["body"])["refundAmount"])) == Decimal("1094")   # 929 cobrados + 165 de regreso
    assert utils._get_by_id("ORDER", oid)["refundAmount"] == Decimal("1094")


def test_el_reembolso_acepta_un_importe_distinto(order_lambda, utils, monkeypatch):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert order_lambda.handle_cancel_order(oid, {}, {})["statusCode"] == 200
    r = order_lambda.handle_refund_order(oid, {"reason": "parcial", "amount": 500}, {})
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("ORDER", oid)["refundAmount"] == Decimal("500")
    assert order_lambda.handle_refund_order(oid, {"amount": -1}, {})["statusCode"] in (400, 409)


def test_los_cupones_responden_bajo_el_prefijo_que_enruta_api_gateway(order_lambda, utils, monkeypatch):
    """Regresión: el frontend llamaba /coupons y la Lambda solo recibe
    /orders/{proxy+}; los cupones eran inalcanzables en producción."""
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    r = order_lambda.lambda_handler(_evento("POST", "/orders/coupons", {"code": "OCTUBRE10", "type": "percent", "value": 10, "active": True}), None)
    assert r["statusCode"] in (200, 201), r["body"]
    r = order_lambda.lambda_handler(_evento("GET", "/orders/coupons"), None)
    assert r["statusCode"] == 200 and "OCTUBRE10" in r["body"]
    r = order_lambda.lambda_handler(_evento("POST", "/orders/coupons/validate", {"code": "OCTUBRE10", "subtotal": 1000}), None)
    assert r["statusCode"] == 200, r["body"]
    r = order_lambda.lambda_handler(_evento("DELETE", "/orders/coupons/OCTUBRE10"), None)
    assert r["statusCode"] == 200, r["body"]
