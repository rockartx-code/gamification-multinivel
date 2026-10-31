"""Devolución por producto (propuesta 18): Lupita devuelve 1 de 2 Naplus.

"¿Tengo que regresar todo el pedido o nada más el bote dañado?" (lupita-nov14).
La solicitud lleva las líneas y cantidades que se devuelven; el reembolso
sugerido se calcula por líneas con el descuento del pedido.
"""
import json

import pytest


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


EVIDENCIA_COMPLETA = {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}


def pedido_lupita(utils, oid="ORD-LUPITA", **extra):
    """2 × Naplus a $280 con 10 % de descuento (neto 504) y envío de $129 (total 633)."""
    now = utils._now_iso()
    item = {
        "entityType": "order", "orderId": oid, "customerId": None, "buyerType": "guest",
        "customerName": "Lupita", "email": "lupita@test.com", "status": "delivered", "deliveredAt": now,
        "items": [{"productId": 7, "name": "Naplus", "price": 280, "quantity": 2}],
        "grossSubtotal": utils._to_decimal(560), "discountRate": utils._to_decimal("0.10"),
        "discountAmount": utils._to_decimal(56), "netTotal": utils._to_decimal(504),
        "shippingCost": utils._to_decimal(129), "total": utils._to_decimal(633),
        "monthKey": utils._month_key(), "createdAt": now, "updatedAt": now, **extra,
    }
    utils._put_entity("ORDER", oid, item, created_at_iso=now)
    return oid


def evento(metodo, ruta, cuerpo=None, headers=None):
    return {"httpMethod": metodo, "path": ruta, "headers": headers or {}, "body": json.dumps(cuerpo or {})}


def solicitar(order_lambda, oid, cuerpo, headers=None):
    return order_lambda.lambda_handler(evento("POST", f"/orders/{oid}/return", cuerpo, headers), None)


def test_devuelve_una_de_dos_unidades_y_el_sugerido_es_una_por_su_neto(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "lines": [{"productId": 7, "quantity": 1}]})
    assert r["statusCode"] == 201, r["body"]
    d = json.loads(r["body"])
    assert d["partial"] is True
    assert d["lines"] == [{"productId": 7, "name": "Naplus", "quantity": 1, "purchasedQuantity": 2,
                           "unitPrice": 280.0, "unitNet": 252.0}]
    # 280 × (1 − 0.10) = 252; sin envío original porque no se devuelve todo.
    assert d["refund"]["suggested"] == 252.0
    assert d["refund"]["products"] == 252.0 and d["refund"]["originalShipping"] == 0.0
    assert d["refund"]["method"] == "mismo medio de pago" and d["refund"]["businessDays"] == "3 a 5"
    assert d["requestId"].startswith("RET-") and d["requestId"] in d["message"]
    assert "$252.00" in d["message"] and "3 a 5 días hábiles" in d["message"]

    solicitud = utils._get_by_id("RETURN_REQUEST", d["requestId"])
    assert solicitud["partial"] is True and solicitud["lines"][0]["quantity"] == 1
    assert solicitud["refundSuggested"] == utils._to_decimal(252)
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "en_devolucion"
    assert pedido["returnedLines"][0]["quantity"] == 1 and pedido["refundSuggested"] == utils._to_decimal(252)


def test_sin_lineas_se_devuelve_todo_el_pedido(order_lambda, utils):
    """Compatibilidad: el asistente anterior no mandaba `lines`."""
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA})
    assert r["statusCode"] == 201, r["body"]
    d = json.loads(r["body"])
    assert d["partial"] is False and d["lines"][0]["quantity"] == 2
    # Todo el pedido y el motivo es nuestro: neto pagado + envío original.
    assert d["refund"]["products"] == 504.0 and d["refund"]["originalShipping"] == 129.0
    assert d["refund"]["suggested"] == 633.0


def test_producto_que_no_esta_en_el_pedido_es_400(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "lines": [{"productId": 99, "quantity": 1}]})
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "INVALID_LINES" and d["productId"] == 99
    assert utils._get_by_id("ORDER", oid)["status"] == "delivered"


def test_cantidad_mayor_a_la_comprada_es_400(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "lines": [{"productId": 7, "quantity": 3}]})
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "INVALID_LINES" and d["purchasedQuantity"] == 2
    assert "Compraste 2" in d["message"]


def test_lista_vacia_o_todo_en_cero_es_400(order_lambda, utils):
    oid = pedido_lupita(utils)
    for lines in ([], [{"productId": 7, "quantity": 0}]):
        r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA, "lines": lines})
        assert r["statusCode"] == 400 and "INVALID_LINES" in r["body"], lines


def test_la_clienta_consulta_su_solicitud_en_get_devolucion(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion"), None)
    assert r["statusCode"] == 404 and "RETURN_NOT_FOUND" in r["body"]

    d = json.loads(solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                                 "lines": [{"productId": 7, "quantity": 1}]})["body"])
    r = order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion"), None)
    assert r["statusCode"] == 200, r["body"]
    req = json.loads(r["body"])["request"]
    assert req["requestId"] == d["requestId"] and req["status"] == "PENDIENTE"
    assert req["motivoLabel"] == "Producto dañado o defectuoso"
    assert req["lines"][0]["quantity"] == 1 and req["partial"] is True
    assert req["refund"]["suggested"] == 252.0 and req["refund"]["businessDays"] == "3 a 5"
    assert req["inspection"] is None and req["refundedAt"] is None


def test_get_devolucion_solo_para_la_duena_o_admin(order_lambda, utils):
    """Un pedido con cuenta exige sesión de su dueña; otra clienta recibe 403."""
    oid = pedido_lupita(utils, customerId=5, buyerType="associate")
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA},
              headers={"x-user-id": "5", "x-user-role": "cliente"})
    assert order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion"), None)["statusCode"] == 401
    otra = {"x-user-id": "6", "x-user-role": "cliente"}
    assert order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion", headers=otra), None)["statusCode"] == 403
    duena = {"x-user-id": "5", "x-user-role": "cliente"}
    assert order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion", headers=duena), None)["statusCode"] == 200
    admin = {"x-user-id": "1", "x-user-role": "admin"}
    assert order_lambda.lambda_handler(evento("GET", f"/orders/{oid}/devolucion", headers=admin), None)["statusCode"] == 200


def test_devolucion_solo_acepta_get(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = order_lambda.lambda_handler(evento("POST", f"/orders/{oid}/devolucion"), None)
    assert r["statusCode"] == 405


def test_la_gerente_ve_las_lineas_devueltas_en_la_ficha_del_pedido(order_lambda, utils):
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                  "lines": [{"productId": 7, "quantity": 1}]})
    admin = {"x-user-id": "1", "x-user-role": "admin"}
    r = order_lambda.lambda_handler(evento("GET", f"/orders/{oid}", headers=admin), None)
    assert r["statusCode"] == 200, r["body"]
    ri = json.loads(r["body"])["order"]["returnInspection"]
    assert ri["lines"][0]["quantity"] == 1 and ri["partial"] is True
    assert ri["refundSuggested"] == 252.0
    assert ri["refundBreakdown"] == {"products": 252.0, "returnShipping": 0.0, "originalShipping": 0.0}
    assert ri["motivoLabel"] == "Producto dañado o defectuoso"
