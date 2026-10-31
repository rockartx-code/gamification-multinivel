"""Evidencia según el motivo (propuesta 18).

Patricia tuvo que subir tres fotos para un paquete que nunca abrió
(patricia-dic16). En desistimiento basta una foto del paquete cerrado con la
guía visible; en daño o error de envío siguen siendo producto, empaque y guía.
"""
import json

import pytest

from test_devoluciones_parciales import EVIDENCIA_COMPLETA, pedido_lupita, solicitar


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _pedido(**extra):
    return {"orderId": "ORD-1", "status": "delivered", "customerId": 1,
            "items": [{"productId": 7, "name": "Naplus", "price": 280, "quantity": 1}], **extra}


def test_cada_motivo_declara_su_evidencia(order_lambda, utils):
    """Paquete D · ronda 26: la evidencia se lee de configuración
    (`returns.motivos[].evidencia`), con los mismos valores de siempre."""
    motivos = order_lambda._motivos_devolucion()
    assert motivos["DESISTIMIENTO"]["evidencia"] == ("fotos_paquete_cerrado",)
    for motivo in ("DANADO_DEFECTUOSO", "ERROR_ENVIO"):
        assert motivos[motivo]["evidencia"] == ("fotos_producto", "fotos_empaque", "fotos_guia_envio")
    assert not hasattr(order_lambda, "RETURN_EVIDENCIA_REQUERIDA"), "la evidencia ya no es una constante global"


def test_desistimiento_con_una_foto_del_paquete_cerrado_pasa(order_lambda):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), "DESISTIMIENTO", {"fotos_paquete_cerrado": ["cerrado.jpg"]}, 1.0)
    assert r is None


def test_desistimiento_sin_foto_pide_la_del_paquete_cerrado(order_lambda):
    r = order_lambda._validar_solicitud_devolucion(_pedido(), "DESISTIMIENTO", {}, 1.0)
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "MISSING_EVIDENCE" and d["missing"] == ["fotos_paquete_cerrado"]
    assert d["evidenceRule"] == "paquete_cerrado"
    assert "paquete cerrado" in d["message"]


def test_desistimiento_acepta_el_juego_completo_del_asistente_anterior(order_lambda):
    r = order_lambda._validar_solicitud_devolucion(_pedido(), "DESISTIMIENTO", EVIDENCIA_COMPLETA, 1.0)
    assert r is None


@pytest.mark.parametrize("motivo", ["DANADO_DEFECTUOSO", "ERROR_ENVIO"])
def test_danio_con_una_sola_foto_falla_y_dice_que_falta(order_lambda, motivo):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), motivo, {"fotos_producto": ["a.jpg"]}, 1.0)
    assert r["statusCode"] == 400
    d = json.loads(r["body"])
    assert d["code"] == "MISSING_EVIDENCE"
    assert d["missing"] == ["fotos_empaque", "fotos_guia_envio"]
    assert d["evidenceRule"] == "completa"
    # La foto del paquete cerrado no sustituye a las tres en un daño.
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), motivo, {"fotos_paquete_cerrado": ["cerrado.jpg"]}, 1.0)
    assert r["statusCode"] == 400 and json.loads(r["body"])["missing"] == list(EVIDENCIA_COMPLETA)


def test_la_solicitud_guarda_la_regla_de_evidencia_y_las_fotos_por_categoria(order_lambda, utils, monkeypatch):
    subidas = []

    def _falso_s3(nombre, contenido, tipo, prefix):
        subidas.append((prefix, nombre))
        return {"assetId": f"{prefix}/{nombre}", "url": f"https://fotos.test/{prefix}/{nombre}"}

    monkeypatch.setattr(order_lambda, "_upload_evidence_s3", _falso_s3)
    oid = pedido_lupita(utils)
    r = solicitar(order_lambda, oid, {"motivo": "DESISTIMIENTO",
                                      "evidence": {"fotos_paquete_cerrado": [{"contentBase64": "eA==", "contentType": "image/jpeg", "fileName": "cerrado.jpg"}]},
                                      "lines": [{"productId": 7, "quantity": 2}]})
    assert r["statusCode"] == 201, r["body"]
    folio = json.loads(r["body"])["requestId"]
    solicitud = utils._get_by_id("RETURN_REQUEST", folio)
    assert solicitud["evidenceRule"] == "paquete_cerrado"
    assert list(solicitud["evidence"]) == ["fotos_paquete_cerrado"]
    assert solicitud["evidence"]["fotos_paquete_cerrado"] == [f"https://fotos.test/devoluciones/{oid}/{folio}/fotos_paquete_cerrado/cerrado.jpg"]
    assert subidas == [(f"devoluciones/{oid}/{folio}/fotos_paquete_cerrado", "cerrado.jpg")]

    # Regresión: el resumen para la gerente iteraba el dict y listaba los
    # nombres de las categorías ("fotos_producto") en lugar de las fotos.
    resumen = order_lambda._resumen_devolucion(folio)
    assert resumen["evidence"] == solicitud["evidence"]["fotos_paquete_cerrado"]


def test_sin_sesion_el_pedido_de_invitado_no_expone_datos_personales_ni_evidencia(order_lambda, utils, monkeypatch):
    """El ID de un pedido de invitado circula en correos y capturas: quien solo
    lo conoce ve el seguimiento, no el teléfono, la calle, la descripción libre
    ni las fotos. Con sesión de back office se sigue viendo todo."""
    from test_pedidos_creacion import _crear_pedido_invitado, _evento
    monkeypatch.setattr(order_lambda, "_upload_evidence_s3",
                        lambda nombre, contenido, tipo, prefix: {"assetId": nombre, "url": f"https://fotos.test/{prefix}/{nombre}"})
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET #s = :s, deliveredAt = :d", {":s": "delivered", ":d": utils._now_iso()}, {"#s": "status"})
    r = solicitar(order_lambda, oid, {"motivo": "DESISTIMIENTO", "descripcion": "No lo quiero, cambié de opinión",
                                      "evidence": {"fotos_paquete_cerrado": [{"contentBase64": "eA==", "contentType": "image/jpeg", "fileName": "cerrado.jpg"}]}})
    assert r["statusCode"] == 201, r["body"]

    pedido = json.loads(order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)["body"])["order"]
    assert pedido["status"] == "en_devolucion" and pedido["orderId"] == oid
    assert pedido["phone"] == "••••••2222" and pedido["email"] == "l•••@test.com"
    assert "street" not in pedido["shippingAddress"] and pedido["shippingAddress"]["city"] == "Guadalajara"

    detalle = json.loads(order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}/devolucion"), None)["body"])["request"]
    assert detalle["status"] and detalle["refund"]["suggested"] is not None
    assert detalle["descripcion"] == "" and detalle["evidence"] == {}

    admin = {"x-user-id": "1", "x-user-role": "admin"}
    completo = json.loads(order_lambda.lambda_handler({**_evento("GET", f"/orders/{oid}/devolucion"), "headers": admin}, None)["body"])["request"]
    assert completo["descripcion"] == "No lo quiero, cambié de opinión" and completo["evidence"]["fotos_paquete_cerrado"]
    pedido_admin = json.loads(order_lambda.lambda_handler({**_evento("GET", f"/orders/{oid}"), "headers": admin}, None)["body"])["order"]
    assert pedido_admin["phone"] == "3311112222" and pedido_admin["shippingAddress"]["street"] == "Av. Vallarta"
