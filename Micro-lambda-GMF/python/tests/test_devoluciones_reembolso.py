"""Reembolso sugerido por líneas, plazo y medio en pantalla y correo (propuesta 18).

Memo: "¿Cuánto tiempo tarda y a dónde regresa el dinero?" (memo-dic12). Lucía
pagó $165 de envío de retorno que no le reembolsaron (lucia-dia15).
"""
import json
from decimal import Decimal

import pytest

from test_devoluciones_parciales import EVIDENCIA_COMPLETA, evento, pedido_lupita, solicitar
from test_pedidos_creacion import _crear_pedido_invitado


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, html)))
    return enviados


@pytest.fixture
def admin(monkeypatch, utils):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    return {"x-user-id": "1", "x-user-role": "admin"}


CERRADO = {"fotos_paquete_cerrado": ["cerrado.jpg"]}
INSPECCION_OK = {"empaque_original": True, "sellos_intactos": True, "sin_uso": True,
                 "coincide_con_pedido": True, "trazabilidad_valida": True}


def test_desistimiento_solo_reembolsa_productos(order_lambda, utils):
    """Aunque devuelva todo y declare envío de regreso, en arrepentimiento no se reembolsa ningún envío."""
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DESISTIMIENTO", "evidence": CERRADO, "returnShippingCost": 165})
    assert r["statusCode"] == 201, r["body"]
    d = json.loads(r["body"])
    assert d["shippingResponsibility"] == "cliente"
    assert d["refund"] == {"suggested": 504.0, "products": 504.0, "returnShipping": 0.0, "originalShipping": 0.0,
                           "method": "mismo medio de pago", "businessDays": "3 a 5"}


def test_danio_devolviendo_todo_incluye_envio_de_regreso_y_original(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA, "returnShippingCost": 165})
    d = json.loads(r["body"])
    assert d["refund"]["products"] == 504.0 and d["refund"]["returnShipping"] == 165.0 and d["refund"]["originalShipping"] == 129.0
    assert d["refund"]["suggested"] == 798.0


def test_danio_parcial_incluye_envio_de_regreso_pero_no_el_original(order_lambda, utils):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "returnShippingCost": 165, "lines": [{"productId": 7, "quantity": 1}]})
    d = json.loads(r["body"])
    assert d["refund"] == {"suggested": 417.0, "products": 252.0, "returnShipping": 165.0, "originalShipping": 0.0,
                           "method": "mismo medio de pago", "businessDays": "3 a 5"}


def test_el_cupon_se_prorratea_en_el_neto_unitario(order_lambda, utils):
    """Neto 504 con cupón de $50.40 (10 % del neto) → unitario 280 × 0.9 − 280 × 50.4/560 = 226.80."""
    oid = pedido_lupita(utils, couponCode="OCTUBRE10", couponDiscount=utils._to_decimal("50.40"),
                        netTotal=utils._to_decimal("453.60"), total=utils._to_decimal("582.60"))
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "lines": [{"productId": 7, "quantity": 1}]})
    d = json.loads(r["body"])
    assert d["lines"][0]["unitNet"] == 226.8 and d["refund"]["suggested"] == 226.8


def test_el_plazo_sale_de_config(order_lambda, utils):
    utils._put_entity("CONFIG", "app-v1", {"config": {"returns": {"refundBusinessDays": "5 a 7"}}})
    utils._invalidate_app_config_cache()
    oid = pedido_lupita(utils)
    d = json.loads(solicitar(order_lambda, oid, {"motivo": "DESISTIMIENTO", "evidence": CERRADO})["body"])
    assert d["refund"]["businessDays"] == "5 a 7" and "5 a 7 días hábiles" in d["message"]


def test_la_bodega_marca_linea_por_linea_y_una_que_no_coincide_rechaza(order_lambda, utils, admin):
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                  "lines": [{"productId": 7, "quantity": 1}]})
    r = order_lambda.handle_return_inspection(oid, {"inspection": INSPECCION_OK,
                                                    "lines": [{"productId": 7, "quantity": 1, "matches": False}]}, admin)
    assert r["statusCode"] == 200, r["body"]
    d = json.loads(r["body"])
    assert d["approved"] is False and d["orderStatus"] == "devolucion_rechazada"
    assert d["linesReceived"] == [{"productId": 7, "quantity": 1, "matches": False}]
    folio = d["requestId"]
    solicitud = utils._get_by_id("RETURN_REQUEST", folio)
    assert solicitud["inspection"]["coincide_con_pedido"] is False
    assert solicitud["inspection"]["linesReceived"][0]["matches"] is False


def test_la_inspeccion_aprobada_devuelve_el_sugerido_y_anota_parcial_en_comisiones(order_lambda, utils, admin, monkeypatch):
    anulaciones = []
    monkeypatch.setattr(order_lambda, "_void_commissions_for_order",
                        lambda order_id, reason: anulaciones.append(reason) or [])
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                  "lines": [{"productId": 7, "quantity": 1}]})
    r = order_lambda.handle_return_inspection(oid, {"inspection": INSPECCION_OK,
                                                    "lines": [{"productId": 7, "quantity": 1, "matches": True}]}, admin)
    d = json.loads(r["body"])
    assert d["approved"] is True and d["refundSuggested"] == 252.0
    assert d["refundBreakdown"]["products"] == 252.0
    assert "$252.00" in d["message"] and "3 a 5 días hábiles" in d["message"]
    # Decisión §13.14: la parcial anula la comisión completa y queda anotado el motivo.
    assert anulaciones == ["return_approved_partial"]


def _validar(order_lambda, utils, admin, oid):
    r = order_lambda.handle_return_inspection(oid, {"inspection": INSPECCION_OK}, admin)
    assert json.loads(r["body"])["approved"] is True


def test_reembolsar_distinto_al_sugerido_exige_motivo_del_ajuste(order_lambda, utils, admin):
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                  "lines": [{"productId": 7, "quantity": 1}]})
    _validar(order_lambda, utils, admin, oid)

    r = order_lambda.handle_refund_order(oid, {"amount": 200}, admin)
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "ADJUSTMENT_REASON_REQUIRED" and d["refundSuggested"] == 252.0
    assert utils._get_by_id("ORDER", oid)["status"] == "devuelto_validado"

    r = order_lambda.handle_refund_order(oid, {"amount": 200, "adjustmentReason": "El bote llegó a medias"}, admin)
    assert r["statusCode"] == 200, r["body"]
    d = json.loads(r["body"])
    assert d["refundAmount"] == 200.0 and d["refundSuggested"] == 252.0
    assert d["breakdown"]["products"] == 252.0 and d["refundAdjustmentReason"] == "El bote llegó a medias"
    assert "$200.00" in d["message"]
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["refundAmount"] == Decimal("200") and pedido["refundAdjustmentReason"] == "El bote llegó a medias"


def test_sin_importe_se_reembolsa_el_sugerido(order_lambda, utils, admin):
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                  "returnShippingCost": 165, "lines": [{"productId": 7, "quantity": 1}]})
    _validar(order_lambda, utils, admin, oid)
    r = order_lambda.handle_refund_order(oid, {}, admin)
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["refundAmount"] == 417.0
    assert utils._get_by_id("ORDER", oid)["refundAmount"] == Decimal("417.00")


def test_no_se_reembolsa_mas_de_lo_cobrado(order_lambda, utils, admin):
    oid = pedido_lupita(utils)
    solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA, "returnShippingCost": 165})
    _validar(order_lambda, utils, admin, oid)
    r = order_lambda.handle_refund_order(oid, {"amount": 900, "adjustmentReason": "error"}, admin)
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "REFUND_EXCEEDS_TOTAL" and d["max"] == 798.0   # 633 cobrados + 165 de regreso


def test_los_correos_dicen_cuanto_cuando_y_a_donde(order_lambda, utils, admin, buzon):
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DANADO_DEFECTUOSO", "evidence": EVIDENCIA_COMPLETA,
                                      "lines": [{"productId": 7, "quantity": 1}]})
    folio = json.loads(r["body"])["requestId"]

    para, asunto, html = buzon[-1]
    assert para == "lupita@test.com" and folio in asunto
    assert "solo los productos que marcaste" in html and "1 × Naplus" in html
    assert "$252.00" in html and "mismo medio de pago" in html and "3 a 5 días hábiles" in html
    assert "lo paga la empresa" in html

    _validar(order_lambda, utils, admin, oid)
    _, asunto, html = buzon[-1]
    assert "aprobada" in asunto.lower()
    assert "$252.00" in html and "mismo medio de pago" in html and "3 a 5 días hábiles" in html

    order_lambda.handle_refund_order(oid, {}, admin)
    _, asunto, html = buzon[-1]
    assert "Reembolso" in asunto
    assert "$252.00" in html and "mismo medio de pago" in html


def test_el_correo_de_cancelacion_de_un_pedido_pagado_dice_plazo_y_medio(order_lambda, utils, admin, buzon):
    """Hallazgo 2 de la ronda 4: prometía el reembolso sin decir cuándo ni a dónde."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert order_lambda.handle_update_status(oid, {"status": "paid"}, admin)["statusCode"] == 200
    assert order_lambda.handle_cancel_order(oid, {}, {})["statusCode"] == 200
    _, asunto, html = buzon[-1]
    assert "cancelado" in asunto
    assert "mismo medio de pago" in html and "3 a 5 días hábiles" in html
