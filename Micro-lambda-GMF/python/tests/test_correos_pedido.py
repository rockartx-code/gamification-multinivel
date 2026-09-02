"""Cada paso del pedido avisa al comprador por correo (docs/qa/18: no había ninguno)."""
import json

import pytest

from test_pedidos_creacion import _crear_pedido_invitado, _evento


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


def _admin():
    return {"Authorization": "Bearer x"}


def test_el_invitado_recibe_correo_en_cada_paso(order_lambda, utils, buzon, monkeypatch):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    monkeypatch.setattr(utils, "_require_self_or_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert utils._get_by_id("ORDER", oid)["email"] == "lucia@test.com"   # antes el pedido no guardaba a quién escribirle

    for estado, extra in (("paid", {}), ("shipped", {"shippingType": "carrier", "trackingNumber": "EST-1"}), ("delivered", {})):
        r = order_lambda.handle_update_status(oid, {"status": estado, **extra}, {})
        assert r["statusCode"] == 200, r["body"]
    asuntos = [a for _, a, _ in buzon]
    assert [p for p, _, _ in buzon] == ["lucia@test.com"] * 3
    assert "Recibimos tu pago" in asuntos[0] and "va en camino" in asuntos[1] and "entregado" in asuntos[2]
    assert "EST-1" in buzon[1][2] and "$929.00" in buzon[1][2]   # guía y total con envío en el cuerpo

    cuerpo = {"motivo": "DANADO_DEFECTUOSO", "reason": "DANADO_DEFECTUOSO", "descripcion": "Tapa rajada",
              "evidencia": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]},
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] == 201, r["body"]
    folio = json.loads(r["body"])["requestId"]
    assert folio in buzon[-1][1]

    inspeccion = {"inspection": {"empaque_original": True, "sellos_intactos": True, "sin_uso": True,
                                 "coincide_con_pedido": True, "trazabilidad_valida": True}}
    r = order_lambda.handle_return_inspection(oid, inspeccion, _admin())
    assert r["statusCode"] == 200, r["body"]
    assert "aprobada" in buzon[-1][1].lower()

    r = order_lambda.handle_refund_order(oid, {"reason": "return"}, _admin())
    assert r["statusCode"] == 200, r["body"]
    assert "Reembolso" in buzon[-1][1]
    assert len(buzon) == 6


def test_repetir_el_mismo_estado_no_manda_dos_correos(order_lambda, utils, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    assert len(buzon) == 1


def test_sin_correo_no_se_manda_nada_y_el_pedido_sigue(order_lambda, utils, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET email = :e", {":e": None})
    r = order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    assert r["statusCode"] == 200 and buzon == []
