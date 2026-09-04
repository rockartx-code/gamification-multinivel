"""El día de pago existe, y los meses los manda el servidor (paquete A, 17 y 34).

Paulina: *"Abrí el correo esperando un «te depositamos». Mi último correo es
del 20 de marzo. Nada"* (`paulina-rios-2027-03-20.md`). Y Renata recargó Pagos
del mes tres veces: *"Marzo 2027 ya no estaba en el selector"*, porque los doce
meses salían de `new Date()` del navegador.
"""
import base64
import json
from decimal import Decimal

import pytest
from freezegun import freeze_time

ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
SIN_PRIVILEGIO = {"x-user-id": "7", "x-user-role": "employee", "x-user-privileges": "{}"}
MES = "2027-03"


class FakeS3:
    def __init__(self):
        self.subidas = []

    def put_object(self, **kw):
        self.subidas.append(kw)


@pytest.fixture
def motor(utils, monkeypatch):
    import commissions_lambda
    monkeypatch.setattr(commissions_lambda, "_s3", FakeS3())
    return commissions_lambda


@pytest.fixture
def correos(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto)))
    return enviados


def _cliente(utils, cid, nombre, clabe=None, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre,
            "email": f"{nombre.lower()}@test.com", "phone": "5512345678", **extra}
    if clabe:
        item["clabeInterbancaria"] = clabe
        item["bankInstitution"] = "BBVA"
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _fila(utils, cid, monto, estado="confirmed", mes=MES, order_id=None, creado="2027-03-04T09:00:00Z"):
    item = utils._get_ledger_month(cid, mes)
    item["ledger"].append({"rowId": f"{order_id or 'ORD-' + str(cid)}#G1", "orderId": order_id or f"ORD-{cid}",
                           "amount": Decimal(str(monto)), "level": 1, "generation": 1, "status": estado,
                           "createdAt": creado, "orderCreatedAt": creado})
    utils._save_ledger_month(item)


def _get(motor, ruta, query=None, headers=ADMIN):
    return motor.lambda_handler({"path": ruta, "httpMethod": "GET", "headers": headers,
                                 "queryStringParameters": query or {}, "body": "{}"}, None)


def _post(motor, ruta, body=None, headers=ADMIN):
    return motor.lambda_handler({"path": ruta, "httpMethod": "POST", "headers": headers,
                                 "queryStringParameters": {}, "body": json.dumps(body or {})}, None)


@pytest.fixture
def escenario(utils, motor):
    """Paulina cobrada, Fabiola sin CLABE, Ximena solo con pendientes."""
    paulina = _cliente(utils, 1, "Paulina", clabe="012345678901236789")
    fabiola = _cliente(utils, 2, "Fabiola")
    ximena = _cliente(utils, 3, "Ximena", clabe="002180000000005678")
    _fila(utils, paulina, "135.00")
    _fila(utils, fabiola, "135.00")
    _fila(utils, ximena, "124.20", estado="pending", creado="2027-03-02T11:18:00Z")
    return {"paulina": paulina, "fabiola": fabiola, "ximena": ximena}


# ── 17 · el mes lo manda el servidor ─────────────────────────────────────────

def test_los_periodos_salen_del_servidor_con_el_mes_por_omision_y_su_hora(motor, escenario):
    with freeze_time("2027-04-10 13:15:37"):
        r = _get(motor, "/commissions/periodos")
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["serverNow"].startswith("2027-04-10")
    assert datos["mesContableVigente"] == "2027-04"
    assert datos["defaultMonth"] == MES, "marzo de 2027 sigue ahí al recargar"
    assert datos["payoutDay"] == 10
    marzo = next(p for p in datos["periodos"] if p["monthKey"] == MES)
    assert marzo["label"] == "marzo de 2027"
    assert marzo["beneficiarias"] == 3
    assert marzo["confirmado"] == 270.0 and marzo["porConfirmar"] == 124.2 and marzo["bloqueado"] == 0.0
    assert marzo["estado"] == "IN_PROGRESS"


def test_los_periodos_solo_traen_meses_con_datos(motor, escenario, utils):
    _cliente(utils, 9, "Lupita", clabe="014180000000009999")   # sin comisiones
    with freeze_time("2027-04-10"):
        datos = json.loads(_get(motor, "/commissions/periodos")["body"])
    assert [p["monthKey"] for p in datos["periodos"]] == [MES]


def test_si_el_mes_anterior_no_tiene_datos_se_ofrece_el_ultimo_que_si(motor, escenario):
    with freeze_time("2027-09-10"):
        datos = json.loads(_get(motor, "/commissions/periodos")["body"])
    assert datos["mesContableVigente"] == "2027-09"
    assert datos["defaultMonth"] == MES, "nunca se planta sola en un mes sin datos"


def test_los_periodos_exigen_el_privilegio_de_pagos(motor, escenario):
    assert _get(motor, "/commissions/periodos", headers=SIN_PRIVILEGIO)["statusCode"] == 403


# ── 18 · las tres cifras del mes ─────────────────────────────────────────────

def test_pagos_del_mes_muestra_confirmado_por_confirmar_y_bloqueado(motor, escenario, utils):
    """Alma acabó con tres cifras del mismo concepto: $135 contra $259.20."""
    _fila(utils, escenario["paulina"], "124.20", estado="pending", order_id="ORD-TARDE",
          creado="2027-03-04T09:00:00Z")
    _fila(utils, escenario["paulina"], "40.00", estado="blocked", order_id="ORD-BLOQ",
          creado="2027-03-06T09:00:00Z")
    with freeze_time("2027-04-10"):
        datos = json.loads(_get(motor, "/commissions/pagos", {"month": MES})["body"])
    filas = {f["name"]: f for f in datos["rows"]}
    paulina = filas["Paulina"]
    assert paulina["confirmado"] == 135.0 and paulina["porConfirmar"] == 124.2 and paulina["bloqueado"] == 40.0
    assert paulina["reconocido"] == 299.2
    assert paulina["frenoPorConfirmar"]["orderId"] == "ORD-TARDE"
    assert paulina["frenoPorConfirmar"]["dias"] == 37, "37 días no se ven igual que 1 día"
    assert paulina["frenoPorConfirmar"]["texto"] == "se confirma cuando el pedido se entrega"
    assert paulina["frenoBloqueado"]["orderId"] == "ORD-BLOQ"
    assert datos["totals"]["reconocido"] == round(299.2 + 135.0 + 124.2, 2)
    assert "sin contar el envío" in datos["baseComisionTexto"], "se dice sobre qué base se paga (37)"


def test_quien_solo_tiene_pendientes_ya_no_desaparece_de_la_pantalla(motor, escenario):
    with freeze_time("2027-04-10"):
        datos = json.loads(_get(motor, "/commissions/pagos", {"month": MES})["body"])
    ximena = next(f for f in datos["rows"] if f["name"] == "Ximena")
    assert ximena["status"] == "por_confirmar"
    assert ximena["confirmado"] == 0.0 and ximena["porConfirmar"] == 124.2
    assert ximena["frenoPorConfirmar"]["dias"] == 39


def test_el_csv_del_banco_sigue_llevando_solo_las_listas(motor, escenario):
    with freeze_time("2027-04-10"):
        r = _get(motor, "/commissions/pagos/dispersion.csv", {"month": MES})
    lineas = [l for l in r["body"].split("\r\n") if l]
    assert len(lineas) == 2 and lineas[1].startswith("012345678901236789,Paulina,135.00")


def test_el_lote_no_paga_a_quien_no_tiene_confirmado(motor, escenario):
    cuerpo = {"monthKey": MES, "customerIds": [3], "name": "t.pdf", "contentType": "application/pdf",
              "contentBase64": base64.b64encode(b"%PDF").decode()}
    r = _post(motor, "/commissions/pagos/lote", cuerpo)
    assert r["statusCode"] == 409 and json.loads(r["body"])["code"] == "NOTHING_PAID"


# ── 35 · el anexo de pendientes ──────────────────────────────────────────────

def test_el_anexo_de_pendientes_lista_a_quien_falta_y_por_que(motor, escenario):
    """Alma perdió el mes entero por una sola socia; el archivo del banco sigue
    saliendo, y aparte se lleva la lista de las que faltan."""
    with freeze_time("2027-04-10"):
        r = _get(motor, "/commissions/pagos/pendientes.csv", {"month": MES})
    assert r["statusCode"] == 200
    assert r["headers"]["Content-Disposition"] == 'attachment; filename="pendientes-2027-03.csv"'
    lineas = [l for l in r["body"].split("\r\n") if l]
    assert lineas[0] == "Nombre,Monto,Correo,Teléfono,Motivo"
    assert lineas[1].startswith("Fabiola,135.00,fabiola@test.com,5512345678,Falta su CLABE")
    assert any(l.startswith("Ximena,124.20") for l in lineas), "también las que aún no confirman"
    assert not any("012345678901236789" in l for l in lineas), "nunca la CLABE de nadie"


def test_el_anexo_exige_privilegio_y_valida_el_mes(motor, escenario):
    assert _get(motor, "/commissions/pagos/pendientes.csv", {"month": MES},
                headers=SIN_PRIVILEGIO)["statusCode"] == 403
    assert _get(motor, "/commissions/pagos/pendientes.csv", {"month": "marzo"})["statusCode"] == 400


# ── 34 · el correo del día 10 ────────────────────────────────────────────────

def _pagar(motor, cid, mes=MES):
    return json.loads(_post(motor, "/commissions/pagos/lote", {
        "monthKey": mes, "customerIds": [cid], "name": "t.pdf", "contentType": "application/pdf",
        "contentBase64": base64.b64encode(b"%PDF").decode()})["body"])


def test_el_dia_10_sale_te_depositamos_o_nos_falta_tu_clabe(motor, escenario, correos, utils):
    with freeze_time("2027-04-09"):
        _pagar(motor, 1)                                  # Paulina cobró de verdad
    correos.clear()
    with freeze_time("2027-04-10 08:00:00"):
        r = _post(motor, "/commissions/pagos/dia-de-pago")
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["day"] == 10 and datos["monthKey"] == MES
    por_cliente = {a["customerId"]: a for a in datos["notified"]}
    assert por_cliente["1"]["kind"] == "depositado" and por_cliente["2"]["kind"] == "sin_clabe"
    assert ("paulina@test.com", "Te depositamos $135.00 a tu CLABE terminación 6789") in correos
    assert ("fabiola@test.com", "No te pudimos depositar: nos falta tu CLABE") in correos
    assert not [a for _, a in correos if "ximena" in a.lower()], "sin comisión confirmada: no se le dice nada"
    assert utils._get_ledger_month(1, MES)["payoutNoticeKind"] == "depositado"


def test_disparar_la_tarea_dos_veces_no_manda_dos_correos(motor, escenario, correos):
    with freeze_time("2027-04-10 08:00:00"):
        _post(motor, "/commissions/pagos/dia-de-pago")
        antes = len(correos)
        datos = json.loads(_post(motor, "/commissions/pagos/dia-de-pago")["body"])
    assert len(correos) == antes
    assert datos["notified"] == [] and set(datos["alreadyNotified"]) == {"2"}


def test_fuera_del_dia_de_pago_la_tarea_no_hace_nada(motor, escenario, correos):
    with freeze_time("2027-04-07"):
        datos = json.loads(_post(motor, "/commissions/pagos/dia-de-pago")["body"])
    assert datos["skipped"] == "not_payout_day" and correos == []


def test_nunca_se_avisa_un_deposito_sin_comprobante(motor, escenario, correos, utils):
    """El correo de "te depositamos" sale del recibo, no de la fecha."""
    with freeze_time("2027-04-10 08:00:00"):
        datos = json.loads(_post(motor, "/commissions/pagos/dia-de-pago")["body"])
    assert [a["customerId"] for a in datos["notified"]] == ["2"], "Paulina tiene CLABE pero aún no le transfieren"
    assert not [a for _, a in correos if a.startswith("Te depositamos")]


def test_el_correo_del_dia_de_pago_respeta_no_contactar_y_se_puede_apagar(motor, escenario, correos, utils, monkeypatch):
    utils._update_by_id("CUSTOMER", 2, "SET doNotContact = :d", {":d": True})
    with freeze_time("2027-04-10 08:00:00"):
        datos = json.loads(_post(motor, "/commissions/pagos/dia-de-pago")["body"])
    assert datos["notified"][0]["channel"] == "ninguno" and correos == []

    cfg = utils._load_app_config()
    cfg["rewards"]["payoutNoticeEnabled"] = False
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    with freeze_time("2027-04-10 08:00:00"):
        datos = json.loads(_post(motor, "/commissions/pagos/dia-de-pago")["body"])
    assert datos["skipped"] == "disabled"


def test_la_tarea_del_dia_de_pago_exige_privilegio_y_es_programada(motor, escenario):
    assert _post(motor, "/commissions/pagos/dia-de-pago", headers=SIN_PRIVILEGIO)["statusCode"] == 403
    assert ("POST", "/commissions/pagos/dia-de-pago") in motor.TAREAS_PROGRAMADAS
    assert _post(motor, "/commissions/pagos/dia-de-pago", {"monthKey": "marzo"})["statusCode"] == 400
