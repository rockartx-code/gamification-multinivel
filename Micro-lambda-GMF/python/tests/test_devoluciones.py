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
def test_quien_paga_el_envio_de_la_devolucion(order_lambda, motivo, responsable):
    assert order_lambda.RETURN_MOTIVOS[motivo]["responsable_envio"] == responsable
