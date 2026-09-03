"""Paquetería integrada: rastreo, "¿te llegó?" y cierre automático (paquete D, propuesta 20).

docs/qa/22 §6 tarea 3: Beto y Sofía marcaban entregados uno a uno con el
reporte de Estafeta recibido por WhatsApp y cuatro pedidos se quedaron meses
en "Enviada". Aquí el rastreo entrega con fecha y firma, el cliente puede
confirmar desde el correo y, si nadie responde, el pedido se cierra solo.
"""
import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from test_despacho_bloque import _bodegas, _empleado, _pedido, _llamar, BETO


@pytest.fixture
def inventory_lambda(utils):
    import inventory_lambda
    return inventory_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto, html)))
    return enviados


@pytest.fixture
def sfn(monkeypatch):
    """Captura las acciones del motor de comisiones que dispara una entrega."""
    import order_lambda
    acciones = []

    class _Sfn:
        def start_execution(self, **kw):
            acciones.append(json.loads(kw["input"])["action"])

    monkeypatch.setattr(order_lambda, "ORDER_SFN_ARN", "arn:sim:orders")
    monkeypatch.setattr(order_lambda, "sfn", _Sfn())
    return acciones


def _hace(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _integracion(utils, **extra):
    cfg = {"enabled": True, "provider": "simulada", "trackingEnabled": True, "askDays": 7, "autoCloseDays": 10, "simDeliveryDays": 3, **extra}
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {"shipping": {"carrierIntegration": cfg}}})
    utils._invalidate_app_config_cache()


def _enviado(utils, oid, dias, **extra):
    return _pedido(utils, oid, status="shipped", shippingCarrier="Simulada", trackingNumber=f"SIM-{oid}",
                   shippedAt=_hace(dias), **extra)


# ── Adaptador ────────────────────────────────────────────────────────────────

def test_la_paqueteria_simulada_genera_guia_y_entrega_a_los_tres_dias(utils):
    import carriers
    paq = carriers.PaqueteriaSimulada(3)
    guia = paq.generar_guia({"orderId": "ORD-77"})
    assert guia["carrier"] == "Simulada" and guia["trackingNumber"] == "SIM-77" and guia["labelUrl"].endswith(".pdf")

    en_camino = paq.rastrear("Simulada", "SIM-77", order={"orderId": "ORD-77", "shippedAt": _hace(1), "recipientName": "Lucía"})
    assert en_camino["status"] == "in_transit"
    entregado = paq.rastrear("Simulada", "SIM-77", order={"orderId": "ORD-77", "shippedAt": _hace(4), "recipientName": "Lucía"})
    assert entregado["status"] == "delivered" and entregado["signedBy"] == "Recibió: Lucía"
    assert entregado["deliveredAt"] and entregado["events"][-1]["text"].startswith("Entregado")


def test_la_paqueteria_activa_sale_de_la_configuracion(utils):
    import carriers
    assert isinstance(carriers.paqueteria_activa(), carriers.EnviaPaqueteria)   # por omisión: Envia
    _integracion(utils, simDeliveryDays=5)
    paq = carriers.paqueteria_activa()
    assert isinstance(paq, carriers.PaqueteriaSimulada) and paq.dias_entrega == 5


def test_envia_traduce_la_respuesta_de_rastreo(monkeypatch):
    import carriers
    paq = carriers.EnviaPaqueteria(api_key="k", track_url="https://envia.test/track")
    monkeypatch.setattr(paq, "_llamar", lambda url, payload: {"data": [{"status": "Delivered", "deliveredAt": "2026-09-05T12:00:00Z",
                                                                          "signedBy": "MARIA", "events": [{"date": "2026-09-05", "description": "Entregado"}]}]})
    r = paq.rastrear("estafeta", "EST-1")
    assert r["status"] == "delivered" and r["signedBy"] == "MARIA" and r["events"] == [{"at": "2026-09-05", "text": "Entregado"}]

    def falla(url, payload):
        raise RuntimeError("timeout")
    monkeypatch.setattr(paq, "_llamar", falla)
    assert paq.rastrear("estafeta", "EST-1")["status"] == "exception"


# ── Rastrear ─────────────────────────────────────────────────────────────────

def test_rastrear_marca_entregado_con_firma_y_confirma_comisiones(inventory_lambda, utils, buzon, sfn):
    _bodegas(utils)
    beto = _empleado(utils)
    _integracion(utils)
    _enviado(utils, "ORD-LEJOS", 4)
    _enviado(utils, "ORD-CERCA", 1)
    _pedido(utils, "ORD-SINGUIA", status="shipped", shippedAt=_hace(4))   # sin guía: no se rastrea

    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/rastrear", {}, headers=beto)
    assert st == 200, d
    assert d["checked"] == 2 and d["inTransit"] == ["ORD-CERCA"]
    assert d["delivered"][0]["orderId"] == "ORD-LEJOS" and d["delivered"][0]["signedBy"] == "Recibió: Cliente ORD-LEJOS"

    pedido = utils._get_by_id("ORDER", "ORD-LEJOS")
    assert pedido["status"] == "delivered" and pedido["deliveredBy"] == "carrier"
    assert pedido["deliverySignedBy"] == "Recibió: Cliente ORD-LEJOS" and pedido["carrierDeliveredAt"]
    assert pedido["deliveredAt"] == d["delivered"][0]["deliveredAt"]
    assert pedido["trackingEvents"][-1]["text"].startswith("Entregado")
    assert sfn == ["ORDER_DELIVERED"]                       # confirma comisiones como una entrega normal
    assert [a for _, a, _, _ in buzon] == ["Tu pedido ORD-LEJOS fue entregado"]
    assert utils._get_by_id("ORDER", "ORD-CERCA")["status"] == "shipped"
    assert utils._get_by_id("ORDER", "ORD-CERCA")["trackingEvents"]

    # Idempotente: volver a correr el mismo día no vuelve a entregar ni a avisar.
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/rastrear", {}, headers=beto)
    assert d["checked"] == 1 and d["delivered"] == [] and len(buzon) == 1


def test_rastrear_esta_apagado_por_omision(inventory_lambda, utils, sfn):
    _bodegas(utils)
    beto = _empleado(utils)
    _enviado(utils, "ORD-LEJOS", 4)
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/rastrear", {}, headers=beto)
    assert st == 200 and d["enabled"] is False and d["checked"] == 0
    assert "Configuración" in d["message"]
    assert utils._get_by_id("ORDER", "ORD-LEJOS")["status"] == "shipped" and sfn == []


def test_dry_run_no_toca_nada(inventory_lambda, utils, sfn):
    _bodegas(utils)
    beto = _empleado(utils)
    _integracion(utils)
    _enviado(utils, "ORD-LEJOS", 4)
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/rastrear", {"dryRun": True}, headers=beto)
    assert st == 200 and d["delivered"][0]["orderId"] == "ORD-LEJOS"
    assert utils._get_by_id("ORDER", "ORD-LEJOS")["status"] == "shipped" and sfn == []


def test_las_tareas_exigen_privilegio_o_superadmin(inventory_lambda, utils, monkeypatch):
    _bodegas(utils)
    nadia = _empleado(utils, "7002", {"access_screen_pos": True}, "Nadia")
    for ruta in ("/inventory/envios/rastrear", "/inventory/envios/cerrar"):
        st, d = _llamar(inventory_lambda, "POST", ruta, {}, headers=nadia)
        assert st == 403, ruta
    from core import security
    monkeypatch.setattr(security, "_SUPERADMIN_TOKEN", "token-maestro")
    for ruta in ("/inventory/envios/rastrear", "/inventory/envios/cerrar"):
        st, d = _llamar(inventory_lambda, "POST", ruta, {}, headers={"authorization": "Bearer token-maestro"})
        assert st == 200, (ruta, d)


# ── Cerrar ───────────────────────────────────────────────────────────────────

def test_cerrar_pregunta_al_dia_siete_una_sola_vez_y_cierra_al_diez(inventory_lambda, utils, buzon, sfn, monkeypatch):
    import despacho_handlers
    monkeypatch.setattr(despacho_handlers, "API_BASE_URL", "https://api.findingu.test")
    _bodegas(utils)
    beto = _empleado(utils)
    _integracion(utils, trackingEnabled=False)
    _enviado(utils, "ORD-7", 7)
    _enviado(utils, "ORD-3", 3)
    _enviado(utils, "ORD-10", 11)

    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/cerrar", {}, headers=beto)
    assert st == 200, d
    assert d["asked"] == ["ORD-7"] and d["closed"] == ["ORD-10"]

    # "¿Te llegó?" con los dos botones: confirmar y avisar a soporte.
    pregunta = [m for m in buzon if "¿Te llegó" in m[1]]
    assert len(pregunta) == 1 and pregunta[0][0] == "ord-7@test.com"
    texto, html = pregunta[0][2], pregunta[0][3]
    assert "https://api.findingu.test/inventory/envios/ORD-7/confirmar-entrega?token=" in html
    assert "mailto:" in html and "Aún no" in html
    assert "confirmar-entrega?token=" in texto
    pedido7 = utils._get_by_id("ORDER", "ORD-7")
    assert pedido7["status"] == "shipped" and pedido7["deliveryCheckEmailSentAt"] and pedido7["deliveryCheckTokenHash"]

    # Cierre automático: entregado por "auto", con nota interna y comisiones confirmadas.
    pedido10 = utils._get_by_id("ORDER", "ORD-10")
    assert pedido10["status"] == "delivered" and pedido10["deliveredBy"] == "auto" and pedido10["autoClosedAt"]
    assert "Cerrado automáticamente" in pedido10["adminNotes"][-1]["text"]
    assert sfn == ["ORDER_DELIVERED"]
    assert utils._get_by_id("ORDER", "ORD-3")["status"] == "shipped"

    # Segunda corrida el mismo día: no repite el correo ni cierra dos veces.
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/cerrar", {}, headers=beto)
    assert d["asked"] == [] and d["closed"] == []
    assert len([m for m in buzon if "¿Te llegó" in m[1]]) == 1


def test_cerrar_apagado_no_manda_nada(inventory_lambda, utils, buzon):
    _bodegas(utils)
    beto = _empleado(utils)
    _enviado(utils, "ORD-10", 11)
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/cerrar", {}, headers=beto)
    assert st == 200 and d["enabled"] is False and d["closed"] == [] and buzon == []
    assert utils._get_by_id("ORDER", "ORD-10")["status"] == "shipped"


# ── Enlace del cliente ───────────────────────────────────────────────────────

def test_el_cliente_confirma_la_entrega_desde_el_correo(inventory_lambda, utils, buzon, sfn, monkeypatch):
    import despacho_handlers
    monkeypatch.setattr(despacho_handlers, "API_BASE_URL", "https://api.findingu.test")
    _bodegas(utils)
    beto = _empleado(utils)
    _integracion(utils)
    _enviado(utils, "ORD-7", 8)
    _llamar(inventory_lambda, "POST", "/inventory/envios/cerrar", {}, headers=beto)
    texto = next(m[2] for m in buzon if "¿Te llegó" in m[1])
    token = re.search(r"confirmar-entrega\?token=([A-Za-z0-9_\-]+)", texto).group(1)

    # Token equivocado: no se puede cerrar el pedido de otro.
    r = inventory_lambda.lambda_handler({"httpMethod": "GET", "path": "/inventory/envios/ORD-7/confirmar-entrega",
                                         "headers": {}, "queryStringParameters": {"token": "otro"}, "body": ""}, None)
    assert r["statusCode"] == 401 and "text/html" in r["headers"]["Content-Type"]
    assert utils._get_by_id("ORDER", "ORD-7")["status"] == "shipped"

    # El botón del correo es un enlace (GET): página de gracias y pedido entregado por el cliente.
    r = inventory_lambda.lambda_handler({"httpMethod": "GET", "path": "/inventory/envios/ORD-7/confirmar-entrega",
                                         "headers": {}, "queryStringParameters": {"token": token}, "body": ""}, None)
    assert r["statusCode"] == 200 and "Marcamos tu pedido como entregado" in r["body"]
    pedido = utils._get_by_id("ORDER", "ORD-7")
    assert pedido["status"] == "delivered" and pedido["deliveredBy"] == "cliente"
    assert pedido["deliverySignedBy"] == "Confirmado por el cliente desde el correo"
    assert sfn == ["ORDER_DELIVERED"]

    # Repetir el clic es inofensivo (JSON para el POST).
    st, d = _llamar(inventory_lambda, "POST", "/inventory/envios/ORD-7/confirmar-entrega", {}, query={"token": token})
    assert st == 200 and d["status"] == "delivered"


def test_el_correo_de_te_llego_existe_en_las_plantillas(utils):
    from core import order_emails
    plantilla = order_emails._plantillas({"orderId": "ORD-1", "recipientName": "Rosa", "shippingCarrier": "Estafeta", "trackingNumber": "EST-1"},
                                         "delivery_check", {"confirmUrl": "https://x/si", "supportUrl": "mailto:s@x"}, "https://front")
    asunto, texto, html = plantilla
    assert asunto == "¿Te llegó tu pedido ORD-1?"
    assert "https://x/si" in html and "mailto:s@x" in html and "EST-1" in html
    assert "https://x/si" in texto
