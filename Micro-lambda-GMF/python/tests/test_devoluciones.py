"""Reglas de devolución (3.1 plazo, 3.3 evidencia, 4 costo logístico)."""
import pytest

EVIDENCIA_COMPLETA = {
    "fotos_producto": ["a.jpg"],
    "fotos_empaque": ["b.jpg"],
    "fotos_guia_envio": ["c.jpg"],
}


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _pedido(status="delivered", **extra):
    return {"orderId": "ORD-1", "status": status, "customerId": 1, **extra}


def test_solo_se_devuelven_pedidos_entregados(order_lambda, utils):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(status="paid"), "DESISTIMIENTO", EVIDENCIA_COMPLETA, 1.0)
    assert r["statusCode"] == 409
    assert "NOT_DELIVERED" in r["body"]


def test_no_se_duplica_una_solicitud_activa(order_lambda):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(returnRequestId="RET-1"), "DESISTIMIENTO", EVIDENCIA_COMPLETA, 1.0)
    assert r["statusCode"] == 409
    assert "RETURN_ALREADY_EXISTS" in r["body"]


def test_rechaza_motivos_desconocidos(order_lambda):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), "PORQUE_SI", EVIDENCIA_COMPLETA, 1.0)
    assert r["statusCode"] == 400
    assert "INVALID_MOTIVO" in r["body"]


@pytest.mark.parametrize("motivo, horas, permitido", [
    ("DANADO_DEFECTUOSO", 47.0, True),
    ("DANADO_DEFECTUOSO", 49.0, False),    # plazo 48 h
    ("ERROR_ENVIO", 48.0, True),           # justo en el límite
    ("ERROR_ENVIO", 100.0, False),
    ("DESISTIMIENTO", 24 * 6, True),
    ("DESISTIMIENTO", 24 * 8, False),      # plazo 7 días
])
def test_plazos_por_motivo(order_lambda, motivo, horas, permitido):
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), motivo, EVIDENCIA_COMPLETA, horas)
    if permitido:
        assert r is None
    else:
        assert r["statusCode"] == 409 and "TIME_EXPIRED" in r["body"]


@pytest.mark.parametrize("falta", ["fotos_producto", "fotos_empaque", "fotos_guia_envio"])
def test_las_tres_categorias_de_evidencia_son_obligatorias(order_lambda, falta):
    """Para daño o error de envío siguen siendo obligatorias las tres fotos.
    (En desistimiento basta la foto del paquete cerrado: propuesta 18,
    `tests/test_devoluciones_evidencia.py`.)"""
    evidencia = {k: v for k, v in EVIDENCIA_COMPLETA.items() if k != falta}
    r = order_lambda._validar_solicitud_devolucion(
        _pedido(), "DANADO_DEFECTUOSO", evidencia, 1.0)
    assert r["statusCode"] == 400
    assert falta in r["body"]


@pytest.mark.parametrize("motivo, responsable", [
    ("DANADO_DEFECTUOSO", "empresa"),
    ("ERROR_ENVIO", "empresa"),
    ("DESISTIMIENTO", "cliente"),
])
def test_quien_paga_el_envio_de_la_devolucion(order_lambda, utils, motivo, responsable):
    """Decisión de negocio 39: el envío de regreso lo paga quien devuelve, salvo
    producto dañado o error de la empresa. Ahora se lee de configuración."""
    assert order_lambda._motivos_devolucion()[motivo]["responsable_envio"] == responsable


# ---------------------------------------------------------------------------
# Propuesta 24 · el botón apagado que explica su motivo
# ---------------------------------------------------------------------------

def test_en_un_pedido_pagado_el_boton_esta_apagado_y_dice_por_que(order_lambda, utils):
    """Julio tenía la proteína rota y el pedido en `paid`: el botón "Devolver /
    Llegó dañado" no existía. 17 clics, 9 pantallas, 341 s y se quedó con el bote."""
    estado = order_lambda._estado_devolucion(_pedido(status="paid"))
    assert estado["puedeSolicitar"] is False
    assert "en cuanto marquemos el pedido como entregado" in estado["motivo"]
    assert "pagado" in estado["motivo"]
    assert "48 horas" in estado["plazoTexto"] and "7 días" in estado["plazoTexto"]


def test_un_pedido_entregado_dentro_del_plazo_si_puede_devolverse(order_lambda, utils):
    from datetime import datetime, timedelta, timezone
    hace_dos_horas = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    estado = order_lambda._estado_devolucion(_pedido(deliveredAt=hace_dos_horas))
    assert estado["puedeSolicitar"] is True
    assert estado["motivo"] == ""
    assert estado["horasRestantes"] > 160          # quedan casi los 7 días del arrepentimiento


def test_pasado_el_plazo_el_boton_se_apaga_diciendo_cuantos_dias_pasaron(order_lambda, utils):
    from datetime import datetime, timedelta, timezone
    hace_diez_dias = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    estado = order_lambda._estado_devolucion(_pedido(deliveredAt=hace_diez_dias))
    assert estado["puedeSolicitar"] is False
    assert "El plazo para devolver este pedido terminó" in estado["motivo"]
    assert "10 días" in estado["motivo"] and "7 días" in estado["motivo"]


def test_con_una_solicitud_en_curso_el_motivo_trae_el_folio(order_lambda, utils):
    estado = order_lambda._estado_devolucion(_pedido(returnRequestId="RET-AB12CD34"))
    assert estado["puedeSolicitar"] is False
    assert "RET-AB12CD34" in estado["motivo"]


def test_el_plazo_del_boton_sale_de_la_misma_configuracion_que_valida_el_servidor(order_lambda, utils):
    """No hay una quinta versión de la regla: cambiar el plazo en configuración
    cambia a la vez lo que dice la pantalla y lo que acepta el servidor."""
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"motivos": [
            {"key": "DESISTIMIENTO", "label": "Cambié de opinión", "limiteHoras": 24,
             "responsableEnvio": "cliente", "evidencia": "paquete_cerrado"}]}}})
    utils._invalidate_app_config_cache()
    estado = order_lambda._estado_devolucion(_pedido(status="paid"))
    assert "24 horas" in estado["plazoTexto"]
    r = order_lambda._validar_solicitud_devolucion(_pedido(), "DESISTIMIENTO", EVIDENCIA_COMPLETA, 30.0)
    assert r["statusCode"] == 409 and "TIME_EXPIRED" in r["body"]


def test_el_invitado_tambien_ve_el_bloque_de_devolucion_en_su_pedido(order_lambda, utils):
    """Julio compró como invitado, como la propia página permite. Sin sesión."""
    import json
    utils._put_entity("ORDER", "ORD-JULIO", {
        "entityType": "order", "orderId": "ORD-JULIO", "status": "paid",
        "customerId": None, "guest": True, "email": "julio@example.com",
        "items": [], "total": 1209})
    r = order_lambda.lambda_handler({"path": "/orders/ORD-JULIO", "httpMethod": "GET",
                                     "headers": {}, "queryStringParameters": {}, "body": "{}"}, None)
    assert r["statusCode"] == 200, r["body"]
    devolucion = json.loads(r["body"])["order"]["devolucion"]
    assert devolucion["puedeSolicitar"] is False and devolucion["motivo"]
    assert [m["key"] for m in devolucion["motivos"]] == [
        "DANADO_DEFECTUOSO", "ERROR_ENVIO", "DESISTIMIENTO"]
