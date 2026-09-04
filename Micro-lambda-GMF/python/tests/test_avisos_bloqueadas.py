"""Política de comisiones bloqueadas (paquete A, propuesta 22, opción b).

Marcela perdió $166 al cierre del mes sin que nadie le avisara. Ahora los
días 20 y 27 la socia inactiva recibe cuánto tiene bloqueado, cuántos VP le
faltan y el producto más barato que la activa. La opción a (gracia) queda
como parámetro apagado.
"""
import json
from decimal import Decimal

import pytest
from freezegun import freeze_time

ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
SIN_PRIVILEGIO = {"x-user-id": "7", "x-user-role": "employee", "x-user-privileges": "{}"}


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda, pagos_handlers
    return order_lambda, commissions_lambda, pagos_handlers


@pytest.fixture
def correos(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto)))
    return enviados


def _cliente(utils, cid, nombre, leader=None, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.lower()}@test.com", **extra}
    if leader is not None:
        item["leaderId"] = leader
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _catalogo(utils):
    for pid, nombre, precio, pc in ((1, "Klinhart", 480, 10), (2, "Naplus", 280, 6), (3, "Longevit", 390, 7), (4, "Finding Pro", 800, 15)):
        utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": nombre, "price": precio, "vpPoints": pc, "active": True})
    utils._put_entity("PRODUCT", 5, {"entityType": "product", "productId": 5, "name": "Muestra gratis", "price": 10, "vpPoints": 6, "active": False})


def _pagar(order_lambda, commissions_lambda, cid, items):
    cuerpo = {"customerId": cid, "customerName": "x", "items": items, "recipientName": "x", "deliveryType": "shipping",
              "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro", "postalCode": "76000", "country": "MX"}}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    return oid


def _bloqueada(utils, cid, monto, mes):
    item = utils._get_ledger_month(cid, mes)
    item["ledger"].append({"rowId": f"ORD-X#G1", "orderId": "ORD-X", "amount": Decimal(str(monto)), "level": 1, "generation": 1,
                           "status": "blocked", "reason": "no_califica_gen", "createdAt": utils._now_iso()})
    utils._save_ledger_month(item)


def _post(motor, body=None, headers=ADMIN):
    return motor.lambda_handler({"path": "/commissions/avisos/bloqueadas", "httpMethod": "POST", "headers": headers,
                                 "queryStringParameters": {}, "body": json.dumps(body or {})}, None)


@pytest.fixture
def bety(utils):
    """Bety: 18 VP netos (compró $1,200 de lista con 10 %), $138.60 bloqueados."""
    _catalogo(utils)
    cid = _cliente(utils, 2, "Bety")
    with freeze_time("2026-10-05"):
        utils._increment_associate_month_net_volume(cid, "2026-10", Decimal("1080"))
        utils._increment_associate_month_net_vp(cid, "2026-10", 18.0)
        _bloqueada(utils, cid, "138.60", "2026-10")
    return cid


def test_el_dia_20_avisa_con_el_producto_mas_barato_que_la_activa(modulos, utils, correos, bety):
    _, motor, _ = modulos
    with freeze_time("2026-10-20"):
        r = _post(motor)
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["day"] == 20 and [n["customerId"] for n in datos["notified"]] == ["2"]
    aviso = datos["notified"][0]
    assert aviso["blocked"] == 138.6 and aviso["vpNow"] == 18.0 and aviso["vpMissing"] == 2.0
    # Naplus: $280 de lista, con 10 % de descuento son 5.4 VP y $252; más barato que Klinhart ($432) o Longevit ($351).
    assert aviso["product"]["name"] == "Naplus" and aviso["product"]["units"] == 1
    assert aviso["product"]["cost"] == 252.0 and aviso["product"]["rate"] == 0.1 and aviso["product"]["vpPerUnit"] == 5.4
    assert aviso["closesOn"] == "2026-10-31"
    assert len(correos) == 1
    para, asunto, texto = correos[0]
    assert para == "bety@test.com"
    assert asunto == "Tienes $138.60 en comisiones bloqueadas que se pierden el 31 de octubre"
    assert "1 Naplus ($252.00)" in texto and "se recalculan; si no, se pierden" in texto
    assert [int(d) for d in utils._get_ledger_month(2, "2026-10")["blockedNoticeSentDays"]] == [20]


def test_el_dia_21_no_avisa_y_el_27_si(modulos, utils, correos, bety):
    _, motor, _ = modulos
    with freeze_time("2026-10-21"):
        datos = json.loads(_post(motor)["body"])
    assert datos["notified"] == [] and datos["skipped"] == "not_notice_day" and correos == []
    with freeze_time("2026-10-27"):
        datos = json.loads(_post(motor)["body"])
    assert [n["customerId"] for n in datos["notified"]] == ["2"] and len(correos) == 1


def test_dos_llamadas_el_mismo_dia_mandan_un_solo_correo(modulos, utils, correos, bety):
    _, motor, _ = modulos
    with freeze_time("2026-10-20"):
        _post(motor)
        datos = json.loads(_post(motor)["body"])
    assert datos["notified"] == [] and datos["alreadyNotified"] == ["2"]
    assert len(correos) == 1
    with freeze_time("2026-10-27"):
        _post(motor)
    assert len(correos) == 2
    assert [int(d) for d in utils._get_ledger_month(2, "2026-10")["blockedNoticeSentDays"]] == [20, 27]


def test_force_y_dry_run_sirven_para_probar_sin_dejar_huella(modulos, utils, correos, bety):
    _, motor, _ = modulos
    with freeze_time("2026-10-21"):
        datos = json.loads(_post(motor, {"force": True, "dryRun": True})["body"])
    assert [n["customerId"] for n in datos["notified"]] == ["2"] and datos["dryRun"] is True
    assert correos == [] and "blockedNoticeSentDays" not in utils._get_ledger_month(2, "2026-10")


def test_una_socia_activa_o_que_no_quiere_contacto_no_recibe_el_aviso(modulos, utils, correos, bety):
    _, motor, _ = modulos
    _cliente(utils, 3, "Claudia")
    with freeze_time("2026-10-05"):
        utils._increment_associate_month_net_vp(3, "2026-10", 25.0)
        _bloqueada(utils, 3, "50.00", "2026-10")
    utils._update_by_id("CUSTOMER", 2, "SET doNotContact = :d", {":d": True})
    with freeze_time("2026-10-20"):
        datos = json.loads(_post(motor)["body"])
    assert datos["notified"] == [] and correos == []


def test_la_tarea_programable_exige_privilegio_o_superadmin(modulos, utils, monkeypatch, bety):
    _, motor, _ = modulos
    with freeze_time("2026-10-20"):
        assert _post(motor, headers=SIN_PRIVILEGIO)["statusCode"] == 403
        from core import security
        monkeypatch.setattr(security, "_SUPERADMIN_TOKEN", "token-de-prueba")
        r = _post(motor, headers={"authorization": "Bearer token-de-prueba"})
    assert r["statusCode"] == 200 and json.loads(r["body"])["notified"]
    # Paquete A · ronda 26: el reloj recorre también el correo del día de pago.
    assert motor.TAREAS_PROGRAMADAS == [("POST", "/commissions/avisos/bloqueadas"),
                                        ("POST", "/commissions/pagos/dia-de-pago")]


def test_sin_producto_que_alcance_se_avisa_igual_con_los_vp_que_faltan(modulos, utils, correos):
    _, motor, pagos = modulos
    cid = _cliente(utils, 2, "Bety")
    with freeze_time("2026-10-05"):
        _bloqueada(utils, cid, "96.00", "2026-10")
    with freeze_time("2026-10-20"):
        datos = json.loads(_post(motor)["body"])
    assert datos["notified"][0]["product"] is None and datos["notified"][0]["vpMissing"] == 20.0
    assert len(correos) == 1
    assert pagos._producto_que_salva(0, 0, []) is None


def test_gracia_apagada_no_reevalua_el_mes_anterior_y_encendida_si(modulos, utils, monkeypatch):
    """Marcela (inactiva) recibe $96 bloqueados en agosto; se activa el 3 de
    septiembre. Con `blockedGraceDays = 0` agosto se queda bloqueado; con 5,
    la fila de agosto pasa a pendiente."""
    order_lambda, motor, _ = modulos
    _catalogo(utils)
    marcela = _cliente(utils, 1, "Marcela", clabeInterbancaria="012345678901231234")
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela)
    klinhart = [{"productId": 1, "name": "Klinhart", "price": 480, "quantity": 2}]
    with freeze_time("2026-08-15"):
        oid = _pagar(order_lambda, motor, rodrigo, klinhart)
    assert {r["status"] for r in utils._get_ledger_month(marcela, "2026-08")["ledger"]} == {"blocked"}

    with freeze_time("2026-09-03"):
        _pagar(order_lambda, motor, marcela, klinhart)
    filas = {r["orderId"]: r["status"] for r in utils._get_ledger_month(marcela, "2026-08")["ledger"]}
    assert filas[oid] == "blocked", "con la gracia apagada, agosto no se toca"

    cfg = utils._load_app_config()
    cfg["rewards"]["blockedGraceDays"] = 5
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    marcela2 = _cliente(utils, 11, "Verónica", clabeInterbancaria="012345678901231234")
    rosa = _cliente(utils, 12, "Rosa", leader=marcela2)
    with freeze_time("2026-08-15"):
        oid2 = _pagar(order_lambda, motor, rosa, klinhart)
    with freeze_time("2026-09-03"):
        _pagar(order_lambda, motor, marcela2, klinhart)
    ledger = utils._get_ledger_month(marcela2, "2026-08")
    vigentes = {r["orderId"]: r["status"] for r in ledger["ledger"] if r["status"] != "voided"}
    assert vigentes[oid2] == "pending", ledger["ledger"]
    assert Decimal(str(ledger["totalPending"])) == Decimal("96.00") and Decimal(str(ledger["totalBlocked"])) == Decimal("0")

    # Fuera de la ventana de gracia (día 6) no se reevalúa aunque esté encendida.
    marcela3 = _cliente(utils, 21, "Lupita", clabeInterbancaria="012345678901231234")
    memo = _cliente(utils, 22, "Memo", leader=marcela3)
    with freeze_time("2026-08-15"):
        oid3 = _pagar(order_lambda, motor, memo, klinhart)
    with freeze_time("2026-09-06"):
        _pagar(order_lambda, motor, marcela3, klinhart)
    assert {r["orderId"]: r["status"] for r in utils._get_ledger_month(marcela3, "2026-08")["ledger"]}[oid3] == "blocked"
