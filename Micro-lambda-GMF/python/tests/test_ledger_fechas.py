"""Guarda 3 (docs/qa/27 §4): recalcular una comisión no le mueve la fecha.

*"Le movieron la fecha a mis comisiones"* (`paulina-rios-2027-03-20.md`).
Paulina se activó el 20 de marzo; el recálculo que desbloqueó las comisiones de
Ximena (día 2) y Fabiola (día 4) reescribía la fila entera con `createdAt` = hoy,
así que las tres comisiones del mes aparecían fechadas el 20 y el historial se
reordenaba solo.

Esto es de lo que el informe 27 llama "lo que ya servía y hay que blindar": la
propuesta 32 lo corrigió y esta prueba es el candado. No mira solo `createdAt`:
compara la fila **campo por campo** antes y después del recálculo y exige que lo
único que se mueva sea el estado y las marcas del propio recálculo.
"""
import json

import pytest
from freezegun import freeze_time

MES = "2027-03"

#: Lo único que un recálculo puede cambiar de una fila que ya existía: su estado
#: y la marca de por qué se recalculó (el `updatedAt` del informe 27 vive en la
#: cabecera del mes, no en la fila — ver `core/ledger.py::_write_ledger_rows`).
CAMPOS_QUE_EL_RECALCULO_PUEDE_TOCAR = {"status", "recalculatedAt", "recalculatedReason", "reason"}


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda
    return order_lambda, commissions_lambda


@pytest.fixture(autouse=True)
def _sin_correos(utils, monkeypatch):
    monkeypatch.setattr(utils, "_send_ses_email", lambda *a, **k: None)


def _cliente(utils, cid, nombre, leader=None):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.lower()}@test.com"}
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


def _filas(utils, cid, mes=MES):
    return {f["rowId"]: f for f in utils._get_ledger_month(cid, mes)["ledger"]
            if str(f.get("status") or "").lower() != "voided"}


def _mundo(utils, order_lambda, commissions_lambda):
    """Ximena compra el 2, Fabiola el 4; Paulina —su patrocinadora— se activa el 20."""
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    fabiola = _cliente(utils, 3, "Fabiola", leader=paulina)
    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    with freeze_time("2027-03-04 09:00:00"):
        _pagar(order_lambda, commissions_lambda, fabiola, pid, 2)
    return paulina, pid


def test_recalculo_no_reescribe_createdAt(modulos, utils):
    order_lambda, commissions_lambda = modulos
    paulina, pid = _mundo(utils, order_lambda, commissions_lambda)

    antes = _filas(utils, paulina)
    assert len(antes) == 2
    assert sorted(f["createdAt"][:10] for f in antes.values()) == ["2027-03-02", "2027-03-04"]
    assert {f["status"] for f in antes.values()} == {"blocked"}, "Paulina no está activa todavía"

    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)      # se activa: recálculo

    despues = _filas(utils, paulina)
    assert set(despues) >= set(antes), "el recálculo no puede perder filas"

    for row_id, fila_antes in antes.items():
        fila = despues[row_id]
        # 1. La fecha de nacimiento de la comisión no se toca. Nunca.
        assert fila["createdAt"] == fila_antes["createdAt"], f"{row_id}: le movieron la fecha"
        assert fila["createdAt"][:10] != "2027-03-20", f"{row_id}: quedó fechada el día de la activación"
        # 2. Ni la del pedido, que es la que la socia reconoce.
        assert fila["orderCreatedAt"] == fila_antes["orderCreatedAt"]
        # 3. El recálculo sí hace su trabajo: desbloquea.
        assert fila_antes["status"] == "blocked" and fila["status"] == "pending"
        # 4. Y no cambia nada más: importe, tasa, base, generación y pedido siguen igual.
        cambiados = {k for k in set(fila) | set(fila_antes) if fila.get(k) != fila_antes.get(k)}
        assert cambiados <= CAMPOS_QUE_EL_RECALCULO_PUEDE_TOCAR, f"{row_id}: cambió {sorted(cambiados)}"
        # 5. Y deja dicho por qué se movió, para que nadie tenga que adivinarlo.
        assert fila["recalculatedAt"][:10] == "2027-03-20"
        assert fila["recalculatedReason"] == "te activaste este mes"


def test_recalculo_no_reescribe_createdAt_con_el_esquema_por_filas(modulos, utils, monkeypatch):
    """El mismo candado en el esquema por filas, donde el mes se reconstruye
    leyendo cada fila: si se ordenara por `createdAt` el historial se reordenaría
    entero en cada recálculo, que es la otra mitad de la queja de Paulina."""
    from core import ledger as core_ledger, settings as core_settings
    monkeypatch.setattr(core_settings, "LEDGER_ROW_SCHEME", "rows")
    monkeypatch.setattr(core_ledger, "LEDGER_ROW_SCHEME", "rows")
    order_lambda, commissions_lambda = modulos
    paulina, pid = _mundo(utils, order_lambda, commissions_lambda)

    antes = [(f["rowId"], f["createdAt"]) for f in utils._get_ledger_month(paulina, MES)["ledger"]]
    with freeze_time("2027-03-20 09:14:39"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)

    filas = utils._get_ledger_month(paulina, MES)["ledger"]
    despues = {f["rowId"]: f for f in filas}
    for row_id, nacio in antes:
        assert despues[row_id]["createdAt"] == nacio, f"{row_id}: le movieron la fecha"
    # El orden del historial es el de los pedidos, y no se reordena al recalcular.
    fechas = [f["orderCreatedAt"][:10] for f in filas if f["rowId"] in dict(antes)]
    assert fechas == sorted(fechas) == ["2027-03-02", "2027-03-04"]


def test_una_fila_nueva_nace_con_la_fecha_de_su_pedido_y_sin_marca_de_recalculo(modulos, utils):
    """La contraparte: si `createdAt` se congelara mal, una comisión nueva
    nacería con la fecha de otra. Y nadie recalculó nada, así que no hay marca."""
    order_lambda, commissions_lambda = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina)
    with freeze_time("2027-03-02 11:18:00"):
        _pagar(order_lambda, commissions_lambda, paulina, pid, 2)      # activa desde el principio
    with freeze_time("2027-03-09 16:40:00"):
        _pagar(order_lambda, commissions_lambda, ximena, pid, 2)

    fila = next(f for f in _filas(utils, paulina).values() if f["status"] == "pending")
    assert fila["createdAt"][:10] == "2027-03-09" and fila["orderCreatedAt"][:10] == "2027-03-09"
    assert "recalculatedAt" not in fila and "recalculatedReason" not in fila
