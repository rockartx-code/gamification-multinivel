"""El esquema por filas debe ser equivalente al original — y mejor bajo carga.

Cambiar dónde viven las comisiones solo vale la pena si (a) los totales salen
idénticos y (b) los escritores concurrentes dejan de competir. Ambas cosas se
comprueban aquí; la segunda es el motivo del cambio.
"""
from decimal import Decimal

import pytest


def _fila(row_id, importe, estado="pending", orden=None):
    return {
        "rowId": row_id, "orderId": orden or row_id.split("#")[0],
        "amount": Decimal(str(importe)), "status": estado,
        "level": 1, "generation": 1, "createdAt": f"2026-09-01T00:00:{row_id[-2:]}Z",
    }


@pytest.fixture
def esquema_filas(monkeypatch, utils):
    """Activa el esquema por filas para la prueba."""
    from core import ledger
    monkeypatch.setattr(ledger, "LEDGER_ROW_SCHEME", "rows")
    return ledger


def test_los_totales_coinciden_entre_ambos_esquemas(utils, esquema_filas):
    item = utils._get_ledger_month(10, "2026-09")
    item["ledger"] = [
        _fila("A#G1", "200"), _fila("B#G2", "100", "confirmed"),
        _fila("C#G3", "50", "blocked"),
    ]
    utils._save_ledger_month(item)

    releido = utils._get_ledger_month(10, "2026-09")
    assert len(releido["ledger"]) == 3
    assert releido["totalPending"] == Decimal("200")
    assert releido["totalConfirmed"] == Decimal("100")
    assert releido["totalBlocked"] == Decimal("50")


def test_cada_fila_es_un_item_propio(utils, esquema_filas, store):
    """Sin lista dentro de un item, no hay techo de 400 KB."""
    item = utils._get_ledger_month(11, "2026-09")
    item["ledger"] = [_fila(f"ORD{i}#G1", "10") for i in range(25)]
    utils._save_ledger_month(item)

    claves = [k for k in store if k[0] == esquema_filas._ledger_rows_pk(11, "2026-09")]
    filas = [k for k in claves if k[1].startswith("ROW#")]
    cabeceras = [k for k in claves if k[1] == "HEADER"]
    assert len(filas) == 25
    assert len(cabeceras) == 1


def test_anular_una_orden_deja_sus_filas_tachadas(utils, esquema_filas):
    item = utils._get_ledger_month(12, "2026-09")
    item["ledger"] = [_fila("X#G1", "100", orden="X"), _fila("Y#G1", "80", orden="Y")]
    utils._save_ledger_month(item)

    utils._void_ledger_rows_for_order(12, "2026-09", "X")

    releido = utils._get_ledger_month(12, "2026-09")
    # La fila anulada se conserva tachada (la socia veía "Sin movimientos") y sale de los totales.
    assert sorted((f["orderId"], f["status"]) for f in releido["ledger"]) == [("X", "voided"), ("Y", "pending")]
    anulada = next(f for f in releido["ledger"] if f["orderId"] == "X")
    assert anulada["previousStatus"] == "pending" and anulada["voidedAt"]
    assert releido["totalPending"] == Decimal("80")
    # Anular dos veces no vuelve a restar.
    assert utils._void_ledger_rows_for_order(12, "2026-09", "X") is None


def test_anadir_una_fila_no_reescribe_las_demas(utils, esquema_filas, store):
    """`_add_ledger_row` es el camino barato: toca una fila y la cabecera."""
    item = utils._get_ledger_month(13, "2026-09")
    item["ledger"] = [_fila("A#G1", "100"), _fila("B#G1", "100")]
    utils._save_ledger_month(item)

    pk = esquema_filas._ledger_rows_pk(13, "2026-09")
    antes = dict(store[(pk, "ROW#A#G1")])

    esquema_filas._add_ledger_row(13, "2026-09", _fila("C#G1", "50"))

    assert store[(pk, "ROW#A#G1")] == antes, "una fila ajena fue reescrita"
    assert (pk, "ROW#C#G1") in store
    assert store[(pk, "HEADER")]["totalPending"] == Decimal("250")


def test_reescribir_una_fila_no_duplica_su_aporte(utils, esquema_filas, store):
    """Reintento de la misma comisión: el total no debe sumarse dos veces."""
    esquema_filas._add_ledger_row(14, "2026-09", _fila("A#G1", "100"))
    esquema_filas._add_ledger_row(14, "2026-09", _fila("A#G1", "100"))

    pk = esquema_filas._ledger_rows_pk(14, "2026-09")
    assert store[(pk, "HEADER")]["totalPending"] == Decimal("100")


def test_cambiar_una_fila_de_pendiente_a_confirmada_mueve_el_total(utils, esquema_filas, store):
    esquema_filas._add_ledger_row(15, "2026-09", _fila("A#G1", "100"))
    esquema_filas._add_ledger_row(15, "2026-09", _fila("A#G1", "100", "confirmed"))

    cabecera = store[(esquema_filas._ledger_rows_pk(15, "2026-09"), "HEADER")]
    assert cabecera["totalPending"] == Decimal("0")
    assert cabecera["totalConfirmed"] == Decimal("100")


def test_cae_al_esquema_original_si_el_mes_no_existe_por_filas(utils, esquema_filas, store):
    """Durante la transición no se puede perder un mes que solo existe viejo."""
    sk = utils._ledger_sk(16, "2026-09")
    store[("COMMISSION_MONTH", sk)] = {
        "PK": "COMMISSION_MONTH", "SK": sk, "beneficiaryId": 16, "monthKey": "2026-09",
        "ledger": [_fila("VIEJA#G1", "70")],
        "totalPending": Decimal("70"), "totalConfirmed": Decimal("0"),
        "totalBlocked": Decimal("0"), "version": 3,
    }
    releido = utils._get_ledger_month(16, "2026-09")
    assert len(releido["ledger"]) == 1
    assert releido["totalPending"] == Decimal("70")


def test_el_modo_dual_escribe_en_ambos(utils, monkeypatch, store):
    from core import ledger
    monkeypatch.setattr(ledger, "LEDGER_ROW_SCHEME", "dual")

    item = utils._get_ledger_month(17, "2026-09")
    item["ledger"] = [_fila("A#G1", "40")]
    utils._save_ledger_month(item)

    assert ("COMMISSION_MONTH", utils._ledger_sk(17, "2026-09")) in store, "falta el original"
    pk = ledger._ledger_rows_pk(17, "2026-09")
    assert (pk, "HEADER") in store and (pk, "ROW#A#G1") in store, "falta el nuevo"
