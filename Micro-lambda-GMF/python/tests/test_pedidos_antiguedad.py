"""Antigüedad y recolección en Acciones urgentes (paquete F · ronda 26, propuesta 21).

Renata, el día 10: "Ninguna columna dice cuántos días llevan parados. 37 días
se ven igual que 1 día" (`renata-2027-04-10.md`). Y el aviso metía tres
recolecciones de mostrador dentro de "4 pedidos pagados sin envío", así que el
único envío de verdad atorado —del que colgaba la comisión de una socia—
quedaba escondido entre pedidos que nadie tiene que enviar.
"""
import json

import pytest


@pytest.fixture
def dashboard_lambda(utils):
    import dashboard_lambda
    return dashboard_lambda


def _pedido(utils, order_id, dias_atras, delivery_type="shipping", status="paid"):
    from datetime import datetime, timedelta
    fecha = (datetime.strptime(utils._now_iso()[:10], "%Y-%m-%d") - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
    creado = f"{fecha}T10:00:00Z"
    utils._put_entity("ORDER", order_id, {
        "entityType": "order", "orderId": order_id, "status": status,
        "deliveryType": delivery_type, "createdAt": creado, "paidAt": creado,
        "total": 1350,
    }, created_at_iso=creado)


def _avisos(dashboard_lambda):
    cuerpo = json.loads(dashboard_lambda.get_admin_warnings()["body"])
    return cuerpo, {w["type"]: w for w in cuerpo["warnings"]}


def test_las_recolecciones_no_se_cuentan_como_envios_pendientes(dashboard_lambda, utils):
    _pedido(utils, "ORD-VIEJO", 37)                                   # envío atorado
    for i, order_id in enumerate(("ORD-P1", "ORD-P2", "ORD-P3")):
        _pedido(utils, order_id, i + 1, delivery_type="pickup")       # mostrador

    cuerpo, avisos = _avisos(dashboard_lambda)
    assert avisos["shipping"]["text"] == "1 pedido pagado sin envío · 37 días el más viejo"
    assert avisos["shipping"]["count"] == 1 and avisos["shipping"]["oldestDays"] == 37
    assert avisos["shipping"]["orderIds"] == ["ORD-VIEJO"]
    assert avisos["pickup"]["text"] == "3 pedidos por recoger en mostrador · 3 días el más viejo"
    assert avisos["pickup"]["count"] == 3
    assert set(avisos["pickup"]["orderIds"]) == {"ORD-P1", "ORD-P2", "ORD-P3"}


def test_la_antiguedad_sale_del_reloj_del_servidor_y_el_rojo_es_configurable(dashboard_lambda, utils):
    _pedido(utils, "ORD-AYER", 1)
    cuerpo, avisos = _avisos(dashboard_lambda)
    assert cuerpo["serverNow"] == utils._now_iso()
    assert cuerpo["agingRedDays"] == 7
    assert avisos["shipping"]["text"] == "1 pedido pagado sin envío · 1 día el más viejo"
    assert avisos["shipping"]["severity"] == "medium"

    _pedido(utils, "ORD-SEMANA", 9)
    _, avisos = _avisos(dashboard_lambda)
    assert avisos["shipping"]["oldestDays"] == 9 and avisos["shipping"]["severity"] == "high"

    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1",
                                           "config": {"orders": {"agingRedDays": 30}}})
    utils._invalidate_app_config_cache()
    cuerpo, avisos = _avisos(dashboard_lambda)
    assert cuerpo["agingRedDays"] == 30 and avisos["shipping"]["severity"] == "medium"


def test_sin_pedidos_pagados_no_se_inventan_avisos(dashboard_lambda, utils):
    _pedido(utils, "ORD-ENTREGADO", 20, status="delivered")
    _pedido(utils, "ORD-RECOGIDO", 20, delivery_type="pickup", status="delivered")
    _, avisos = _avisos(dashboard_lambda)
    assert "shipping" not in avisos and "pickup" not in avisos
