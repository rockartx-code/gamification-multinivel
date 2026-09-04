"""Paquete D · propuesta 39 — la política se publica antes de comprar y en los correos.

Julio preguntó por WhatsApp las cuatro cosas —qué plazo hay, qué fotos se
piden, quién paga el envío de regreso y a dónde se manda el paquete— porque no
estaban escritas en ninguna pantalla (docs/qa/25 §7.3 nº 39). Ahora hay **una
sola fuente**: `ayuda_handlers.texto_politica`. Estas pruebas comprueban que
las cuatro salidas dicen lo mismo y que cambiar la configuración las cambia a
las cuatro.
"""
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
    monkeypatch.setattr(correo, "_send_ses_email",
                        lambda para, asunto, texto, html: enviados.append((para, asunto, texto, html)))
    return enviados


def _plazo_corto(utils, horas=24):
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"motivos": [
            {"key": "DANADO_DEFECTUOSO", "label": "Llegó dañado o defectuoso", "limiteHoras": horas,
             "responsableEnvio": "empresa", "evidencia": "completa"}]}}})
    utils._invalidate_app_config_cache()


def test_el_correo_de_entrega_explica_el_proceso_completo(order_lambda, utils, buzon):
    """"Si algo llegó dañado tienes 48 horas" estaba escrito a mano en el correo
    y no decía ni quién paga el envío ni a dónde se manda el paquete."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    order_lambda.handle_update_status(oid, {"status": "shipped"}, {})
    order_lambda.handle_update_status(oid, {"status": "delivered"}, {})
    _, asunto, texto, html = buzon[-1]
    assert "entregado" in asunto
    for frase in ("Qué puedes devolver", "En qué plazo", "Qué evidencia te pedimos",
                  "Quién paga el envío de regreso", "A dónde mandas el paquete",
                  "Cuánto tarda y cómo te llega el dinero"):
        assert frase in html, frase
    assert "lo paga quien devuelve" in html
    assert "En qué plazo" in texto          # también en la versión de texto plano


def test_el_correo_de_solicitud_recibida_repite_el_mismo_proceso(order_lambda, utils, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    for estado in ("paid", "shipped", "delivered"):
        order_lambda.handle_update_status(oid, {"status": estado}, {})
    evidencia = {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}
    r = order_lambda.lambda_handler(
        _evento("POST", f"/orders/{oid}/return",
                {"motivo": "DANADO_DEFECTUOSO", "descripcion": "Tapa rajada", "evidence": evidencia}), None)
    assert r["statusCode"] == 201, r["body"]
    _, asunto, texto, html = buzon[-1]
    assert "solicitud de devolución" in asunto
    assert "El proceso, paso a paso" in html
    assert "Cuánto tarda y cómo te llega el dinero" in html
    assert "Cuánto tarda y cómo te llega el dinero" in texto


def test_cambiar_el_plazo_lo_cambia_en_la_pantalla_y_en_el_correo(order_lambda, utils, buzon):
    """La misma fuente en las cuatro salidas: si el negocio pone 24 horas, la
    página, el bloque del pedido y el correo de entrega dicen 24 horas."""
    _plazo_corto(utils, horas=24)

    import ayuda_handlers
    publicado = ayuda_handlers.handle_ayuda()
    pasos = {p["clave"]: p["texto"] for p in json.loads(publicado["body"])["devoluciones"]["pasos"]}
    assert "24 horas" in pasos["plazo"]

    estado = order_lambda._estado_devolucion({"orderId": "ORD-1", "status": "paid"})
    assert "24 horas" in estado["plazoTexto"]

    oid = _crear_pedido_invitado(order_lambda, utils)
    for e in ("paid", "shipped", "delivered"):
        order_lambda.handle_update_status(oid, {"status": e}, {})
    assert "24 horas" in buzon[-1][3]
    assert "7 días" not in buzon[-1][3]


def test_la_solicitud_ya_creada_conserva_su_politica(order_lambda, utils, buzon):
    """La configuración nunca es retroactiva: lo que se prometió al abrir la
    solicitud es lo que se cumple, aunque después cambie el reembolso."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    for e in ("paid", "shipped", "delivered"):
        order_lambda.handle_update_status(oid, {"status": e}, {})
    evidencia = {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}
    r = order_lambda.lambda_handler(
        _evento("POST", f"/orders/{oid}/return",
                {"motivo": "DANADO_DEFECTUOSO", "evidence": evidencia}), None)
    folio = json.loads(r["body"])["requestId"]

    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"refundBusinessDays": "30 a 45"}}})
    utils._invalidate_app_config_cache()

    solicitud = utils._get_by_id("RETURN_REQUEST", folio)
    assert solicitud["refundPolicy"]["businessDays"] == "3 a 5"
