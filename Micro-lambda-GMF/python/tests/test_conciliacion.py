"""Conciliación de pagos con MercadoPago (paquete H, propuesta 21).

Cuando el webhook se pierde, el cliente pagó y el pedido sigue "pendiente".
La conciliación consulta a la pasarela por los pendientes de las últimas 72 h
y acredita los aprobados; un pedido ya cobrado no se toca.
"""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from test_pedidos_creacion import _crear_pedido_invitado

ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
EMPLEADO_SIN_PERMISO = {"x-user-id": "2", "x-user-role": "employee", "x-user-privileges": json.dumps({"access_screen_orders": True})}


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


class _Respuesta:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def mercadopago(monkeypatch):
    """Doble de payments/search: `pagos[orderId] = [(paymentId, estado), ...]`.

    Si un pedido está en `caidos`, la consulta falla (MercadoPago no responde).
    """
    import urllib.parse
    import urllib.request
    pagos, consultas, caidos = {}, [], set()

    def urlopen(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        assert "/v1/payments/search" in url, url
        oid = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["external_reference"][0]
        consultas.append(oid)
        if oid in caidos:
            raise RuntimeError("MercadoPago no disponible")
        return _Respuesta({"results": [{"id": pid, "status": estado, "external_reference": oid}
                                        for pid, estado in pagos.get(oid, [])]})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return {"pagos": pagos, "consultas": consultas, "caidos": caidos}


def _pendiente_con_preferencia(order_lambda, utils):
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET paymentPreferenceId = :p, paymentProvider = :pr",
                        {":p": f"pref-{oid}", ":pr": "mercadolibre"})
    return oid


def _conciliar(order_lambda, cuerpo=None, headers=ADMIN):
    evento = {"httpMethod": "POST", "path": "/orders/conciliacion", "headers": headers, "body": json.dumps(cuerpo or {})}
    r = order_lambda.lambda_handler(evento, None)
    return r["statusCode"], json.loads(r["body"] or "{}")


def test_un_pago_aprobado_sin_webhook_se_acredita(order_lambda, utils, mercadopago, buzon):
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("mp-77", "approved")]

    estado, cuerpo = _conciliar(order_lambda)
    assert estado == 200, cuerpo
    assert cuerpo["checked"] == 1 and cuerpo["credited"] == [{"orderId": oid, "paymentId": "mp-77"}]
    assert cuerpo["unpaid"] == [] and cuerpo["errors"] == [] and cuerpo["runId"].startswith("CONC-")
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "paid" and pedido["paidVia"] == "reconciliation" and pedido["paymentId"] == "mp-77"
    assert pedido.get("reconciledAt") and pedido.get("paidAt")
    assert len(buzon) == 1 and "Recibimos tu pago" in buzon[0][1]

    # La corrida queda guardada y es la última.
    r = order_lambda.lambda_handler({"httpMethod": "GET", "path": "/orders/conciliacion/ultima", "headers": ADMIN, "body": "{}"}, None)
    corrida = json.loads(r["body"])["run"]
    assert r["statusCode"] == 200 and corrida["runId"] == cuerpo["runId"] and corrida["credited"][0]["orderId"] == oid


def test_un_pedido_ya_pagado_no_se_consulta_ni_se_toca(order_lambda, utils, mercadopago, buzon):
    oid = _pendiente_con_preferencia(order_lambda, utils)
    order_lambda.handle_update_status(oid, {"status": "paid", "paymentId": "mp-1"}, {})
    paid_at = utils._get_by_id("ORDER", oid)["paidAt"]
    mercadopago["pagos"][oid] = [("mp-2", "approved")]

    estado, cuerpo = _conciliar(order_lambda)
    assert estado == 200 and cuerpo["checked"] == 0 and cuerpo["credited"] == []
    assert mercadopago["consultas"] == []
    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["paymentId"] == "mp-1" and pedido["paidAt"] == paid_at and len(buzon) == 1


def test_fuera_de_la_ventana_no_se_consulta(order_lambda, utils, mercadopago):
    viejo = (datetime.now(timezone.utc) - timedelta(hours=100)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    utils._put_entity("ORDER", "ORD-VIEJO", {"entityType": "order", "orderId": "ORD-VIEJO", "status": "pending",
                                             "paymentPreferenceId": "pref-viejo", "netTotal": Decimal("100"),
                                             "items": [], "createdAt": viejo})
    reciente = _pendiente_con_preferencia(order_lambda, utils)
    sin_preferencia = _crear_pedido_invitado(order_lambda, utils)      # nunca llegó a la pasarela
    mercadopago["pagos"]["ORD-VIEJO"] = [("mp-9", "approved")]

    estado, cuerpo = _conciliar(order_lambda, {"hours": 72})
    assert estado == 200 and cuerpo["checked"] == 1 and mercadopago["consultas"] == [reciente]
    assert cuerpo["unpaid"] == [reciente]
    assert utils._get_by_id("ORDER", "ORD-VIEJO")["status"] == "pending"
    assert utils._get_by_id("ORDER", sin_preferencia)["status"] == "pending"

    # Con una ventana mayor sí entra.
    estado, cuerpo = _conciliar(order_lambda, {"hours": 200})
    assert cuerpo["credited"] == [{"orderId": "ORD-VIEJO", "paymentId": "mp-9"}]


def test_dry_run_informa_sin_acreditar_ni_guardar_corrida(order_lambda, utils, mercadopago, buzon):
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("mp-3", "approved")]

    estado, cuerpo = _conciliar(order_lambda, {"dryRun": True})
    assert estado == 200 and cuerpo["dryRun"] is True
    assert cuerpo["credited"] == [{"orderId": oid, "paymentId": "mp-3", "dryRun": True}]
    assert utils._get_by_id("ORDER", oid)["status"] == "pending" and buzon == []
    assert utils._query_bucket("RECONCILIATION_RUN") == []


def test_un_pago_pendiente_o_rechazado_deja_el_pedido_como_sin_pago(order_lambda, utils, mercadopago):
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("mp-4", "rejected"), ("mp-5", "pending")]
    estado, cuerpo = _conciliar(order_lambda)
    assert estado == 200 and cuerpo["unpaid"] == [oid] and cuerpo["credited"] == []
    assert utils._get_by_id("ORDER", oid)["status"] == "pending"


def test_si_mercadopago_no_responde_se_informa_por_pedido(order_lambda, utils, mercadopago):
    caido = _pendiente_con_preferencia(order_lambda, utils)
    vivo = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["caidos"].add(caido)
    mercadopago["pagos"][vivo] = [("mp-6", "approved")]

    estado, cuerpo = _conciliar(order_lambda)
    assert estado == 200, "parcial: se informa por pedido"
    assert cuerpo["credited"] == [{"orderId": vivo, "paymentId": "mp-6"}]
    assert cuerpo["errors"] == [{"orderId": caido, "error": "MercadoPago no disponible"}]

    mercadopago["caidos"].add(vivo)
    otro = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["caidos"].add(otro)
    estado, cuerpo = _conciliar(order_lambda)
    assert estado == 502 and len(cuerpo["errors"]) == 2


def test_la_conciliacion_exige_el_privilegio_de_marcar_pagado(order_lambda, utils, mercadopago):
    estado, cuerpo = _conciliar(order_lambda, headers=EMPLEADO_SIN_PERMISO)
    assert estado == 403 and "order_mark_paid" in cuerpo["message"]
    estado, _ = _conciliar(order_lambda, headers={})
    assert estado == 403
    # Ver la última corrida solo pide acceso a la pantalla de Pedidos.
    r = order_lambda.lambda_handler({"httpMethod": "GET", "path": "/orders/conciliacion/ultima", "headers": EMPLEADO_SIN_PERMISO, "body": "{}"}, None)
    assert r["statusCode"] == 200 and json.loads(r["body"])["run"] is None


def test_el_superadmin_puede_programarla(order_lambda, utils, mercadopago, monkeypatch):
    """Así la invoca el programador externo y el reloj de la simulación."""
    from core import security
    monkeypatch.setattr(security, "_SUPERADMIN_TOKEN", "token-maestro")
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("mp-8", "approved")]
    estado, cuerpo = _conciliar(order_lambda, headers={"authorization": "Bearer token-maestro"})
    assert estado == 200 and cuerpo["credited"][0]["orderId"] == oid
    assert utils._query_bucket("RECONCILIATION_RUN")[0]["triggeredBy"] == "superadmin"


def test_horas_invalidas_responden_400(order_lambda, utils, mercadopago):
    estado, cuerpo = _conciliar(order_lambda, {"hours": "muchas"})
    assert estado == 400
    estado, cuerpo = _conciliar(order_lambda, {"hours": 0})
    assert estado == 400 and "horas" in cuerpo["message"]


def test_la_ruta_esta_declarada_como_tarea_programada(order_lambda):
    assert ("POST", "/orders/conciliacion") in order_lambda.TAREAS_PROGRAMADAS


# --- Propuesta 26 · conciliación con rango (paquete G) -------------------------

def test_la_corrida_devuelve_la_hora_del_servidor_para_no_pisarla_con_la_del_navegador(
        order_lambda, utils, mercadopago):
    """*"la tarjeta «última corrida» muestra la hora del navegador"*.

    El front escribía `finishedAt: new Date().toISOString()` sobre la respuesta,
    y con el navegador en 2026-09 y el mundo en 2027-04 la corrida quedaba
    fechada siete meses antes de existir. Ahora la respuesta ya trae la hora
    del servidor y no hay nada que inventar.
    """
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("PAY-1", "approved")]
    estado, cuerpo = _conciliar(order_lambda, {})
    assert estado == 200
    assert cuerpo["startedAt"].endswith("Z") and cuerpo["finishedAt"].endswith("Z")
    assert cuerpo["finishedAt"] >= cuerpo["startedAt"]
    guardada = utils._query_bucket("RECONCILIATION_RUN")[0]
    assert cuerpo["finishedAt"] == guardada["finishedAt"]


def test_el_rango_pedido_viaja_y_se_devuelve(order_lambda, utils, mercadopago):
    """A Renata le encargaron revisar **todo marzo** y la pantalla estaba clavada
    en 72 horas, así que obtuvo "Revisados 0"."""
    oid = _pendiente_con_preferencia(order_lambda, utils)
    mercadopago["pagos"][oid] = [("PAY-2", "approved")]
    estado, cuerpo = _conciliar(order_lambda, {"hours": 744})
    assert estado == 200 and cuerpo["hours"] == 744
    assert cuerpo["checked"] >= 1, "con un mes de ventana el pedido entra"


def test_la_corrida_se_acota_para_no_disparar_mil_consultas_a_mercadopago(
        order_lambda, utils, mercadopago):
    """Cada pedido candidato dispara una consulta a la pasarela: con 90 días de
    ventana, sin tope, una sola corrida podría hacer cientos."""
    ids = [_pendiente_con_preferencia(order_lambda, utils) for _ in range(4)]
    for oid in ids:
        mercadopago["pagos"][oid] = [("PAY-X", "approved")]
    estado, cuerpo = _conciliar(order_lambda, {"hours": 2160, "limit": 2})
    assert estado == 200
    assert cuerpo["checked"] == 2 and len(mercadopago["consultas"]) == 2
    assert cuerpo["limit"] == 2
    # Y dice cuántos quedaron fuera, para que la gerente sepa que falta pasada.
    assert cuerpo["pending"] == 2 and cuerpo["hasMore"] is True


def test_desde_una_fecha_el_servidor_calcula_las_horas_con_su_propio_reloj(
        order_lambda, utils, mercadopago):
    """El "desde-hasta" de la pantalla: la fecha la traduce el servidor, porque
    el reloj del navegador iba en 2026-09 con el mundo en 2027-04."""
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    estado, cuerpo = _conciliar(order_lambda, {"since": ayer})
    assert estado == 200, cuerpo
    assert 24 <= cuerpo["hours"] <= 49


def test_una_fecha_imposible_se_rechaza_con_su_motivo(order_lambda, utils, mercadopago):
    manana = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    estado, cuerpo = _conciliar(order_lambda, {"since": manana})
    assert estado == 400 and "anterior a hoy" in cuerpo["message"]

    estado, cuerpo = _conciliar(order_lambda, {"since": "el martes"})
    assert estado == 400 and "AAAA-MM-DD" in cuerpo["message"]

    viejisima = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    estado, cuerpo = _conciliar(order_lambda, {"since": viejisima})
    assert estado == 400 and "90 días" in cuerpo["message"]


def test_sin_tope_explicito_hay_un_tope_por_omision(order_lambda, utils, mercadopago):
    estado, cuerpo = _conciliar(order_lambda, {})
    assert estado == 200 and cuerpo["limit"] == 50


def test_un_tope_absurdo_se_rechaza_con_su_numero(order_lambda, utils, mercadopago):
    estado, cuerpo = _conciliar(order_lambda, {"limit": 0})
    assert estado == 400 and "1 y 200" in cuerpo["message"]
    estado, cuerpo = _conciliar(order_lambda, {"limit": 5000})
    assert estado == 400 and "1 y 200" in cuerpo["message"]
