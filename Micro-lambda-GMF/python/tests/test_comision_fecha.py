"""La fecha de la comisión no se reescribe (paquete A, propuesta 32).

Paulina se activó el 20 de marzo y el recálculo le puso esa fecha a las
comisiones del 2 y del 4: *"Le movieron la fecha a mis comisiones"*
(`paulina-rios-2027-03-20.md`). Ahora la fila conserva su fecha, lleva la del
pedido, el historial no se reordena y dice por qué se recalculó.
"""
import json

import pytest
from freezegun import freeze_time


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda
    return order_lambda, commissions_lambda


@pytest.fixture
def correos(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto)))
    return enviados


def _cliente(utils, cid, nombre, leader=None, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre,
            "email": f"{nombre.lower()}@test.com", **extra}
    if leader is not None:
        item["leaderId"] = leader
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _producto(utils, pid=9):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    return pid


def _pagar(order_lambda, commissions_lambda, cid, pid, qty):
    cuerpo = {"customerId": cid, "customerName": "x",
              "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": qty}],
              "recipientName": "x", "deliveryType": "shipping",
              "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro",
                                  "postalCode": "76000", "country": "MX"}}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    return oid


MES = "2027-03"


def _filas(utils, cid, mes=MES):
    return [r for r in utils._get_ledger_month(cid, mes)["ledger"]
            if (r.get("status") or "").lower() != "voided"]


def test_al_recalcular_la_comision_conserva_su_fecha_y_dice_por_que_cambio(modulos, utils, correos):
    """Ximena compró el 2 y Fabiola el 4; Paulina se activó el 20."""
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    fabiola = _cliente(utils, 3, "Fabiola", leader=paulina)

    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    with freeze_time("2027-03-04 09:00:00"):
        _pagar(order_lambda, commissions_lambda, fabiola, pid, 2)

    antes = _filas(utils, paulina)
    assert [f["status"] for f in antes] == ["blocked", "blocked"], "Paulina no está activa todavía"
    assert [f["createdAt"][:10] for f in antes] == ["2027-03-02", "2027-03-04"]

    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)      # se activa

    despues = {f["rowId"]: f for f in _filas(utils, paulina)}
    de_ximena = despues[[f["rowId"] for f in antes][0]]
    de_fabiola = despues[[f["rowId"] for f in antes][1]]
    assert de_ximena["createdAt"][:10] == "2027-03-02", "la fecha de la comisión no se reescribe"
    assert de_fabiola["createdAt"][:10] == "2027-03-04"
    assert de_ximena["orderCreatedAt"][:10] == "2027-03-02"
    assert de_ximena["status"] == "pending" and de_fabiola["status"] == "pending"
    assert de_ximena["recalculatedAt"][:10] == "2027-03-20"
    assert de_ximena["recalculatedReason"] == "te activaste este mes"


def test_el_historial_no_se_reordena_al_recalcular(modulos, utils, correos, monkeypatch):
    """Con el esquema por filas el mes se reconstruye ordenado por la fecha del pedido."""
    from core import ledger as core_ledger, settings as core_settings
    monkeypatch.setattr(core_settings, "LEDGER_ROW_SCHEME", "rows")
    monkeypatch.setattr(core_ledger, "LEDGER_ROW_SCHEME", "rows")
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    fabiola = _cliente(utils, 3, "Fabiola", leader=paulina)

    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    with freeze_time("2027-03-04 09:00:00"):
        _pagar(order_lambda, commissions_lambda, fabiola, pid, 2)
    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)

    fechas = [f["orderCreatedAt"][:10] for f in _filas(utils, paulina)]
    assert fechas == sorted(fechas) == ["2027-03-02", "2027-03-04"], "el historial sigue en el orden de los pedidos"


def test_una_comision_nueva_no_nace_marcada_como_recalculada(modulos, utils, correos):
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)      # activa desde el principio
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    fila = _filas(utils, paulina)[0]
    assert fila["status"] == "pending"
    assert "recalculatedAt" not in fila and "recalculatedReason" not in fila
    assert float(fila["commissionRate"]) == 0.10
    assert float(fila["commissionBaseNet"]) > 0


def test_al_desbloquearse_las_comisiones_la_socia_se_entera(modulos, utils, correos):
    """Propuesta 34: "se desbloquearon $X" sale cuando el recálculo las libera."""
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    correos.clear()
    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)
    asuntos = [a for _, a in correos if "desbloquearon" in a]
    assert asuntos == ["Se desbloquearon $96.00 de tus comisiones"]
    assert ("paulina@test.com", asuntos[0]) in correos


def test_el_aviso_de_desbloqueo_se_puede_apagar(modulos, utils, correos, monkeypatch):
    order_lambda, commissions_lambda = modulos
    cfg = utils._load_app_config()
    cfg["rewards"]["blockedUnlockNotice"] = False
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    correos.clear()
    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)
    assert [a for _, a in correos if "desbloquearon" in a] == []
