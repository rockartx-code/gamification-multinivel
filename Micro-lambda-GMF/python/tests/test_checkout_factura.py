"""Quiero factura: casilla en el checkout, estado "solicitada" visible en el back office, "emitida" a mano.

A Rodrigo le prometieron la factura cuatro veces en 15 días y le recapturaron
los datos fiscales (docs/qa/22 §6 tarea 11). Sin timbrado CFDI en esta ronda.
"""
import json

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, checkout_handlers
    return order_lambda, checkout_handlers


ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
EMPLEADO_SIN_PRIVILEGIO = {"x-user-id": "2", "x-user-role": "employee", "x-user-privileges": "{}"}

DATOS = {"rfc": "GOMR850101AB1", "razonSocial": "Rodrigo Gómez", "regimenFiscal": "626",
         "cpFiscal": "06100", "usoCfdi": "G03", "email": "rodrigo@test.com"}


def _producto(utils):
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Klinhart", "price": 480, "vpPoints": 10})


def _pedido(cid=None, **extra):
    base = {"customerName": "Rodrigo", "items": [{"productId": 9, "name": "Klinhart", "price": 480, "quantity": 2}],
            "deliveryType": "delivery", "email": "rodrigo@test.com",
            "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "QUE", "postalCode": "76000", "country": "MX"}}
    if cid is not None:
        base["customerId"] = cid
    base.update(extra)
    return base


def _llamar(order_lambda, metodo, ruta, body=None, headers=None, query=None):
    r = order_lambda.lambda_handler({"path": ruta, "httpMethod": metodo, "headers": headers or {},
                                     "queryStringParameters": query or {}, "body": json.dumps(body or {})}, None)
    return r["statusCode"], json.loads(r["body"])


def test_el_pedido_nace_con_factura_solicitada_y_se_ve_en_el_listado(modulos, utils):
    order_lambda, _ = modulos
    _producto(utils)
    estado, d = _llamar(order_lambda, "POST", "/orders/create", _pedido(invoiceRequested=True, invoiceData=DATOS))
    assert estado == 201, d
    pedido = d["order"]
    assert pedido["invoiceStatus"] == "solicitada" and pedido["invoiceRequested"] is True
    assert pedido["invoiceData"]["rfc"] == "GOMR850101AB1" and pedido["invoiceRequestedAt"]

    # Un segundo pedido sin factura no entra en el filtro.
    _llamar(order_lambda, "POST", "/orders/create", _pedido())
    estado, lista = _llamar(order_lambda, "GET", "/orders/find", headers=ADMIN)
    assert estado == 200 and len(lista["orders"]) == 2
    estados = {o["orderId"]: o["invoiceStatus"] for o in lista["orders"]}
    assert sorted(estados.values()) == ["no_aplica", "solicitada"]
    estado, filtrado = _llamar(order_lambda, "GET", "/orders/find", headers=ADMIN, query={"invoiceStatus": "solicitada"})
    assert [o["orderId"] for o in filtrado["orders"]] == [pedido["orderId"]]
    assert filtrado["orders"][0]["invoiceData"]["razonSocial"] == "Rodrigo Gómez"


def test_rfc_invalido_se_rechaza_al_crear_y_al_solicitar(modulos, utils):
    order_lambda, _ = modulos
    _producto(utils)
    malos = {**DATOS, "rfc": "NO-ES-RFC"}
    estado, d = _llamar(order_lambda, "POST", "/orders/create", _pedido(invoiceRequested=True, invoiceData=malos))
    assert estado == 400 and d["code"] == "INVALID_INVOICE_DATA" and "RFC" in d["message"]

    estado, d = _llamar(order_lambda, "POST", "/orders/create", _pedido())
    oid = d["order"]["orderId"]
    estado, d = _llamar(order_lambda, "POST", f"/orders/{oid}/factura", malos)
    assert estado == 400 and "RFC" in d["message"]
    estado, d = _llamar(order_lambda, "POST", f"/orders/{oid}/factura", {**DATOS, "cpFiscal": "123"})
    assert estado == 400 and "postal" in d["message"]


def test_el_invitado_solicita_por_folio_y_otro_cliente_no_puede(modulos, utils):
    order_lambda, _ = modulos
    _producto(utils)
    # Invitado: sin sesión, por folio.
    _, d = _llamar(order_lambda, "POST", "/orders/create", _pedido())
    oid = d["order"]["orderId"]
    estado, d = _llamar(order_lambda, "POST", f"/orders/{oid}/factura", DATOS)
    assert estado == 200 and d["invoiceStatus"] == "solicitada" and d["invoiceData"]["rfc"] == DATOS["rfc"]
    assert "días hábiles" in d["message"]
    assert utils._get_by_id("ORDER", oid)["invoiceStatus"] == "solicitada"

    # Socia: solo ella (o un admin).
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Bety"})
    _, d = _llamar(order_lambda, "POST", "/orders/create", _pedido(555), headers={"x-user-id": "555", "x-user-role": "cliente"})
    oid = d["order"]["orderId"]
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/factura", DATOS, headers={"x-user-id": "777", "x-user-role": "cliente"})[0] == 403
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/factura", DATOS, headers={"x-user-id": "555", "x-user-role": "cliente"})[0] == 200


def test_marcar_emitida_con_archivo_y_aviso(modulos, utils, monkeypatch):
    order_lambda, _ = modulos
    _producto(utils)
    _, d = _llamar(order_lambda, "POST", "/orders/create", _pedido(invoiceRequested=True, invoiceData=DATOS))
    oid = d["order"]["orderId"]
    monkeypatch.setattr(order_lambda, "_upload_evidence_s3",
                        lambda name, b64, ct, prefix: {"assetId": f"{prefix}/{name}", "url": f"https://s3.test/{prefix}/{name}"})
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto)))

    cuerpo = {"folioFiscal": "A1B2-C3", "name": "factura.pdf", "contentType": "application/pdf", "contentBase64": "aGVsbG8="}
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/factura/emitida", cuerpo, headers=EMPLEADO_SIN_PRIVILEGIO)[0] == 403
    estado, d = _llamar(order_lambda, "POST", f"/orders/{oid}/factura/emitida", cuerpo, headers=ADMIN)
    assert estado == 200, d
    assert d["invoiceStatus"] == "emitida" and d["invoiceFolio"] == "A1B2-C3"
    assert d["invoiceFileUrl"] == f"https://s3.test/facturas/{oid}/factura.pdf" and d["invoiceIssuedAt"]
    guardado = utils._get_by_id("ORDER", oid)
    assert guardado["invoiceStatus"] == "emitida" and guardado["invoiceFileUrl"] == d["invoiceFileUrl"]
    assert enviados and enviados[0][0] == "rodrigo@test.com" and "A1B2-C3" in enviados[0][2]

    # Dos veces no; y un pedido sin solicitud tampoco.
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/factura/emitida", {}, headers=ADMIN)[0] == 409
    _, otro = _llamar(order_lambda, "POST", "/orders/create", _pedido())
    estado, d = _llamar(order_lambda, "POST", f"/orders/{otro['order']['orderId']}/factura/emitida", {}, headers=ADMIN)
    assert estado == 409 and d["code"] == "INVOICE_NOT_REQUESTED"
    # Ya emitida: no se puede volver a solicitar.
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/factura", DATOS)[0] == 409


def test_un_pedido_cancelado_pasa_a_no_aplica(modulos, utils, monkeypatch):
    order_lambda, ch = modulos
    _producto(utils)
    _, d = _llamar(order_lambda, "POST", "/orders/create", _pedido(invoiceRequested=True, invoiceData=DATOS))
    oid = d["order"]["orderId"]
    monkeypatch.setattr(order_lambda, "_avisar", lambda *a, **k: None)
    assert _llamar(order_lambda, "POST", f"/orders/{oid}/cancel", {"reason": "me arrepentí"})[0] == 200
    assert ch.estado_factura(utils._get_by_id("ORDER", oid)) == "no_aplica"
    _, lista = _llamar(order_lambda, "GET", "/orders/find", headers=ADMIN, query={"invoiceStatus": "solicitada"})
    assert lista["orders"] == []
    estado, d = _llamar(order_lambda, "POST", f"/orders/{oid}/factura", DATOS)
    assert estado == 409 and d["code"] == "INVOICE_NOT_APPLICABLE"


def test_el_rfc_sigue_la_expresion_del_sat(modulos):
    _, ch = modulos
    for bueno in ("GOMR850101AB1", "ABC850101XY2", "XAXX010101000", "ÑOZ850101A11"):
        assert ch.validar_datos_fiscales({**DATOS, "rfc": bueno.lower()})[1] == "", bueno
    for malo in ("GOMR85010AB1", "12345678901234", "GOMR-850101-AB1", ""):
        assert ch.validar_datos_fiscales({**DATOS, "rfc": malo})[1], malo
