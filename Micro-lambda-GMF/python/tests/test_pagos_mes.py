"""Pantalla "Pagos del mes" (paquete A, propuesta 12).

Sofía abría 16 fichas el día de pago: transferir fuera, generar comprobante,
subirlo, recargar. Ahora una sola lista dice quién cobra cuánto, se exporta el
archivo del banco, se sube un comprobante por lote y se deshace por fila.
"""
import base64
import json
from decimal import Decimal

import pytest
from freezegun import freeze_time

ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
SIN_PRIVILEGIO = {"x-user-id": "7", "x-user-role": "employee", "x-user-privileges": "{}"}
MES = "2026-08"


class FakeS3:
    def __init__(self):
        self.subidas = []

    def put_object(self, **kw):
        self.subidas.append(kw)


@pytest.fixture
def motor(utils, monkeypatch):
    import commissions_lambda
    s3 = FakeS3()
    monkeypatch.setattr(commissions_lambda, "_s3", s3)
    commissions_lambda._s3_fake = s3
    return commissions_lambda


@pytest.fixture
def correos(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto)))
    return enviados


def _cliente(utils, cid, nombre, clabe=None, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.lower()}@test.com", "phone": "5512345678", **extra}
    if clabe:
        item["clabeInterbancaria"] = clabe
        item["bankInstitution"] = "BBVA"
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _confirmadas(utils, cid, monto, mes=MES):
    item = utils._get_ledger_month(cid, mes)
    item["ledger"].append({"rowId": f"ORD-{cid}#G1", "orderId": f"ORD-{cid}", "amount": Decimal(str(monto)),
                           "level": 1, "generation": 1, "status": "confirmed", "createdAt": utils._now_iso()})
    utils._save_ledger_month(item)


def _get(motor, ruta, query=None, headers=ADMIN):
    return motor.lambda_handler({"path": ruta, "httpMethod": "GET", "headers": headers,
                                 "queryStringParameters": query or {}, "body": "{}"}, None)


def _post(motor, ruta, body, headers=ADMIN):
    return motor.lambda_handler({"path": ruta, "httpMethod": "POST", "headers": headers,
                                 "queryStringParameters": {}, "body": json.dumps(body)}, None)


def _cuerpo_lote(ids, mes=MES, **extra):
    return {"monthKey": mes, "customerIds": ids, "name": "transferencia.pdf", "contentType": "application/pdf",
            "contentBase64": base64.b64encode(b"%PDF-1.4 comprobante").decode(), **extra}


@pytest.fixture
def escenario(utils, motor):
    """Claudia lista, Bety sin CLABE, Memo ya pagado, Lupita sin confirmado."""
    claudia = _cliente(utils, 1, "Claudia", clabe="012345678901231234")
    bety = _cliente(utils, 2, "Bety")
    memo = _cliente(utils, 3, "Memo", clabe="002180000000005678")
    lupita = _cliente(utils, 4, "Lupita", clabe="014180000000009999")
    _confirmadas(utils, claudia, "250.74")
    _confirmadas(utils, bety, "138.60")
    _confirmadas(utils, memo, "96.00")
    motor._registrar_pago(memo, MES, {"assetId": "comprobantes/memo.pdf", "url": "https://s3/memo.pdf"})
    return {"claudia": claudia, "bety": bety, "memo": memo, "lupita": lupita}


def test_el_listado_trae_los_tres_estados_y_los_totales_cuadran_con_el_ledger(motor, escenario, correos):
    r = _get(motor, "/commissions/pagos", {"month": MES})
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    filas = {f["name"]: f for f in datos["rows"]}
    assert set(filas) == {"Claudia", "Bety", "Memo"}, "Lupita no tiene confirmado: no aparece"
    assert filas["Claudia"]["status"] == "listo" and filas["Claudia"]["amount"] == 250.74
    assert filas["Claudia"]["clabeMasked"] == "••••••••••••••1234", "en pantalla la CLABE va enmascarada"
    assert filas["Claudia"]["bankInstitution"] == "BBVA"
    assert filas["Bety"]["status"] == "sin_clabe" and filas["Bety"]["clabeMasked"] == ""
    assert filas["Memo"]["status"] == "pagado" and filas["Memo"]["receiptUrl"] == "https://s3/memo.pdf"
    assert datos["totals"]["listo"] == {"count": 1, "amount": 250.74}
    assert datos["totals"]["sinClabe"] == {"count": 1, "amount": 138.6}
    assert datos["totals"]["pagado"] == {"count": 1, "amount": 96.0}
    assert [f["status"] for f in datos["rows"]] == ["listo", "sin_clabe", "pagado"], "primero lo que hay que hacer"


def test_un_mes_mal_formado_responde_400(motor, escenario):
    assert _get(motor, "/commissions/pagos", {"month": "agosto"})["statusCode"] == 400
    assert _get(motor, "/commissions/pagos/dispersion.csv", {"month": "2026-13"})["statusCode"] == 400


def test_sin_el_privilegio_de_pagos_no_se_ve_ni_se_paga(motor, escenario):
    assert _get(motor, "/commissions/pagos", {"month": MES}, headers=SIN_PRIVILEGIO)["statusCode"] == 403
    assert _get(motor, "/commissions/pagos/dispersion.csv", {"month": MES}, headers=SIN_PRIVILEGIO)["statusCode"] == 403
    assert _post(motor, "/commissions/pagos/lote", _cuerpo_lote([1]), headers=SIN_PRIVILEGIO)["statusCode"] == 403
    assert _post(motor, "/commissions/pagos/pedir-clabe", {"customerId": 2}, headers=SIN_PRIVILEGIO)["statusCode"] == 403
    cliente = {"x-user-id": "2", "x-user-role": "cliente"}
    assert _get(motor, "/commissions/pagos", {"month": MES}, headers=cliente)["statusCode"] == 403


def test_el_csv_de_dispersion_solo_lleva_las_listas_con_la_clabe_completa(motor, escenario):
    r = _get(motor, "/commissions/pagos/dispersion.csv", {"month": MES})
    assert r["statusCode"] == 200
    assert r["headers"]["Content-Type"] == "text/csv; charset=utf-8"
    assert r["headers"]["Content-Disposition"] == 'attachment; filename="dispersion-2026-08.csv"'
    lineas = [l for l in r["body"].split("\r\n") if l]
    assert lineas[0] == "CLABE,Beneficiario,Monto,Concepto,Referencia,Email"
    assert lineas[1:] == ["012345678901231234,Claudia,250.74,Comisiones 2026-08 Finding'U,1,claudia@test.com"]


def test_el_lote_paga_las_listas_y_salta_con_motivo_las_que_no(motor, escenario, correos, utils):
    r = _post(motor, "/commissions/pagos/lote", _cuerpo_lote([1, 2, 3, 4], bankReference="REF-889"))
    assert r["statusCode"] == 201, r["body"]
    datos = json.loads(r["body"])
    assert datos["batchId"].startswith("LOTE-")
    assert [p["customerId"] for p in datos["paid"]] == ["1"]
    assert datos["paid"][0]["amount"] == 250.74 and datos["totalPaid"] == 250.74
    assert {(s["customerId"], s["code"]) for s in datos["skipped"]} == {("2", "CLABE_REQUIRED"), ("3", "ALREADY_PAID"), ("4", "NO_CONFIRMED")}

    assert len(motor._s3_fake.subidas) == 1, "un solo archivo para todo el lote"
    assert utils._get_ledger_month(1, MES)["status"] == "PAID"
    assert utils._get_ledger_month(2, MES)["status"] != "PAID", "sin CLABE nunca se marca pagada"
    recibo = next(r for r in utils._query_bucket("COMMISSION_RECEIPT") if str(r.get("customerId")) == "1")
    assert recibo["batchId"] == datos["batchId"] and recibo["bankReference"] == "REF-889"
    lote = utils._get_by_id("COMMISSION_PAYMENT_BATCH", datos["batchId"])
    assert lote and lote["customerIds"] == ["1"] and Decimal(str(lote["totalPaid"])) == Decimal("250.74")
    assert correos == [("claudia@test.com", "Depositamos tus comisiones de 2026-08: $250.74")]

    # La pantalla se recarga desde el servidor y ya lo refleja.
    filas = {f["name"]: f for f in json.loads(_get(motor, "/commissions/pagos", {"month": MES})["body"])["rows"]}
    assert filas["Claudia"]["status"] == "pagado" and filas["Claudia"]["batchId"] == datos["batchId"]


def test_el_lote_rechaza_cuerpos_incompletos_y_selecciones_vacias(motor, escenario):
    assert _post(motor, "/commissions/pagos/lote", {"monthKey": MES, "customerIds": [1]})["statusCode"] == 400
    assert _post(motor, "/commissions/pagos/lote", _cuerpo_lote([]))["statusCode"] == 409
    malo = _cuerpo_lote([1]); malo["contentBase64"] = "%%no-es-base64%%"
    assert _post(motor, "/commissions/pagos/lote", malo)["statusCode"] == 400
    # Si ninguna fila se pudo pagar, se dice con los motivos en vez de fingir un lote.
    r = _post(motor, "/commissions/pagos/lote", _cuerpo_lote([2, 3]))
    assert r["statusCode"] == 409 and json.loads(r["body"])["code"] == "NOTHING_PAID"


def test_deshacer_una_fila_del_lote_no_toca_a_las_demas(motor, escenario, correos, utils):
    _cliente(utils, 5, "Verónica", clabe="072180000000004321")
    _confirmadas(utils, 5, "80.00")
    lote = json.loads(_post(motor, "/commissions/pagos/lote", _cuerpo_lote([1, 5]))["body"])
    assert len(lote["paid"]) == 2

    r = _post(motor, "/commissions/admin/receipt/revert", {"customerId": 1, "monthKey": MES, "reason": "se transfirió a otra cuenta"})
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["receiptsVoided"] == 1 and datos["batchId"] == lote["batchId"]
    assert utils._get_ledger_month(1, MES)["status"] == "IN_PROGRESS"
    assert utils._get_ledger_month(5, MES)["status"] == "PAID"
    filas = {f["name"]: f for f in json.loads(_get(motor, "/commissions/pagos", {"month": MES})["body"])["rows"]}
    assert filas["Claudia"]["status"] == "listo" and filas["Verónica"]["status"] == "pagado"
    assert _post(motor, "/commissions/admin/receipt/revert", {"customerId": 1, "monthKey": MES, "reason": "otra vez"})["statusCode"] == 409


def test_el_pago_individual_sigue_funcionando_con_las_mismas_reglas(motor, escenario, correos):
    cuerpo = {"customerId": 1, "monthKey": MES, "name": "c.pdf", "contentBase64": base64.b64encode(b"x").decode()}
    assert _post(motor, "/commissions/admin/receipt", {**cuerpo, "customerId": 2})["statusCode"] == 409
    assert _post(motor, "/commissions/admin/receipt", {**cuerpo, "customerId": 3})["statusCode"] == 409
    r = _post(motor, "/commissions/admin/receipt", cuerpo)
    assert r["statusCode"] == 201 and json.loads(r["body"])["receipt"]["status"] == "paid"
    assert ("claudia@test.com", "Depositamos tus comisiones de 2026-08: $250.74") in correos


def test_el_resumen_distingue_sin_clabe_de_pendiente(motor, escenario):
    resumen = json.loads(_get(motor, "/commissions/summary", {"month": MES})["body"])["summary"]
    assert resumen["1"]["status"] == "pending"
    assert resumen["2"]["status"] == "sin_clabe"
    assert resumen["3"]["status"] == "paid"


def test_pedir_clabe_manda_correo_y_aviso_y_lo_anota_en_la_ficha(motor, escenario, correos, utils):
    import dashboard_common
    r = _post(motor, "/commissions/pagos/pedir-clabe", {"customerId": 2, "monthKey": MES})
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["sent"] is True and datos["channel"] == "email+panel" and datos["name"] == "Bety"
    assert correos == [("bety@test.com", "Registra tu CLABE para cobrar tus comisiones")]
    assert utils._get_ledger_month(2, MES)["clabeReminderAt"] == datos["clabeReminderAt"]
    notas = utils._get_by_id("CUSTOMER", 2)["contactNotes"]
    assert len(notas) == 1 and "CLABE" in notas[0]["text"] and notas[0]["by"] == "1"
    avisos = dashboard_common._active_notifications_for_customer(2)
    assert [a["title"] for a in avisos] == ["Registra tu CLABE para cobrar tus comisiones"]
    assert dashboard_common._active_notifications_for_customer(1) == [], "el aviso es solo para Bety"

    assert _post(motor, "/commissions/pagos/pedir-clabe", {"customerId": 999})["statusCode"] == 404
    assert _post(motor, "/commissions/pagos/pedir-clabe", {"customerId": 1})["statusCode"] == 409, "Claudia ya tiene CLABE"


def test_pedir_clabe_respeta_no_contactar_y_avisa_solo_en_el_panel(motor, escenario, correos, utils):
    utils._update_by_id("CUSTOMER", 2, "SET doNotContact = :d", {":d": True})
    datos = json.loads(_post(motor, "/commissions/pagos/pedir-clabe", {"customerId": 2, "monthKey": MES})["body"])
    assert datos["channel"] == "panel" and correos == []


def test_acciones_urgentes_separa_listas_de_sin_clabe_y_sube_la_urgencia_con_la_fecha(utils, motor, escenario):
    import dashboard_lambda
    with freeze_time("2026-09-01"):
        avisos = {w["type"]: w for w in json.loads(dashboard_lambda.get_admin_warnings()["body"])["warnings"]}
    assert "commissions" not in avisos, "el aviso genérico se sustituye"
    assert avisos["commissions_ready"]["text"] == "1 comisiones listas para depositar · $250.74"
    assert avisos["commissions_no_clabe"]["text"] == "1 socias con comisión y sin CLABE · $138.60"
    assert avisos["commissions_ready"]["severity"] == "low" and avisos["commissions_no_clabe"]["severity"] == "low"
    with freeze_time("2026-09-08"):   # payoutDay 10 − 2
        avisos = {w["type"]: w for w in json.loads(dashboard_lambda.get_admin_warnings()["body"])["warnings"]}
    assert avisos["commissions_ready"]["severity"] == "high" and avisos["commissions_no_clabe"]["severity"] == "high"


def test_el_csv_neutraliza_nombres_que_excel_leeria_como_formula(motor, escenario, utils):
    """El nombre lo edita la propia socia: `=HYPERLINK(...)` no debe ejecutarse al abrir el CSV."""
    _cliente(utils, 5, '=HYPERLINK("http://x","a")', clabe="032180000118359719")
    _confirmadas(utils, 5, "10.00")
    r = _get(motor, "/commissions/pagos/dispersion.csv", {"month": MES})
    fila = next(l for l in r["body"].split("\r\n") if ",5," in l)
    assert fila.startswith('032180000118359719,"\'=HYPERLINK(""http://x"",""a"")",10.00')
    assert fila.endswith(",5,'=hyperlink(\"\"http://x\"\",\"\"a\"\")@test.com\"") or "'=hyperlink" in fila


def test_el_lote_no_sube_el_comprobante_si_ninguna_fila_se_puede_pagar(motor, escenario, correos, utils):
    """Doble clic en «Registrar pago por lote»: el segundo intento no deja un archivo huérfano en S3."""
    r = _post(motor, "/commissions/pagos/lote", _cuerpo_lote([1]))
    assert r["statusCode"] == 201
    r = _post(motor, "/commissions/pagos/lote", _cuerpo_lote([1]))
    assert r["statusCode"] == 409 and json.loads(r["body"])["code"] == "NOTHING_PAID"
    assert len(motor._s3_fake.subidas) == 1, "solo el primer intento subió el comprobante"
    assert len([r for r in utils._query_bucket("COMMISSION_RECEIPT") if str(r.get("customerId")) == "1"]) == 1
