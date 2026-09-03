"""Resumen automático de turno (paquete D, propuesta 23a).

docs/qa/22 §6 tarea 12: Beto (9 turnos) y Nadia (6) redactaban a mano el
mensaje de cierre con folios, guías y contadores. El resumen se calcula al
vuelo desde la bitácora y el `text` es ese mensaje, listo para WhatsApp.
"""
import json

import pytest

from test_despacho_bloque import _bodegas, _empleado, _pedido, _llamar, BETO


@pytest.fixture
def inventory_lambda(utils):
    import inventory_lambda
    return inventory_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    monkeypatch.setattr(correo, "_send_ses_email", lambda *a, **k: None)


PRIVILEGIOS_ALMACEN = {"order_mark_shipped": True, "order_mark_delivered": True, "stock_create_transfer": True,
                       "stock_receive_transfer": True, "stock_add_inventory": True, "stock_mark_damaged": True,
                       "pos_register_sale": True, "access_screen_stocks": True}


def _turno_de_beto(inventory_lambda, utils):
    """Un turno completo: despacho, transferencia recibida con faltante, entrada, merma y venta POS."""
    _bodegas(utils)
    beto = _empleado(utils, BETO, PRIVILEGIOS_ALMACEN)
    _pedido(utils, "ORD-1"); _pedido(utils, "ORD-2")
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar",
                    {"stockId": "STK-CENTRAL", "csv": "ORD-1,Estafeta,EST-1\nORD-2,DHL,DHL-2\n"}, headers=beto)
    assert st == 200, d

    # Entrega marcada por Beto (firma capturada)
    import order_lambda
    r = order_lambda.handle_update_status("ORD-1", {"status": "delivered", "deliverySignedBy": "Firmó Lucía 12:40"}, beto)
    assert r["statusCode"] == 200

    # Transferencia creada por Beto y recibida por él con un faltante
    st, d = _llamar(inventory_lambda, "POST", "/inventory/stocks/transfers",
                    {"sourceStockId": "STK-CENTRAL", "destinationStockId": "STK-VALLE", "lines": [{"productId": 101, "qty": 3}]}, headers=beto)
    assert st == 201, d
    tid = d["transfer"]["transferId"]
    st, d = _llamar(inventory_lambda, "POST", f"/inventory/stocks/transfers/{tid}/receive", {"received": {"101": 2}}, headers=beto)
    assert st == 200, d

    # Entrada y merma
    st, _ = _llamar(inventory_lambda, "POST", "/inventory/stocks/STK-CENTRAL/entries", {"productId": 102, "qty": 5, "userId": BETO}, headers=beto)
    assert st == 200
    st, _ = _llamar(inventory_lambda, "POST", "/inventory/stocks/STK-CENTRAL/damages",
                    {"productId": 102, "qty": 1, "userId": BETO, "reason": "Frasco roto"}, headers=beto)
    assert st == 200

    # Venta de mostrador y corte
    st, d = _llamar(inventory_lambda, "POST", "/inventory/pos/sales",
                    {"stockId": "STK-CENTRAL", "items": [{"productId": 101, "name": "Magnesio", "price": 480, "quantity": 1}],
                     "paymentMethod": "cash"}, headers=beto)
    assert st == 201, d
    st, d = _llamar(inventory_lambda, "POST", "/inventory/pos/cash-cut", {"stockId": "STK-CENTRAL", "cashToKeep": 0}, headers=beto)
    assert st == 201, d
    return beto, tid


def test_el_turno_aparece_completo_y_el_texto_lleva_los_folios(inventory_lambda, utils, buzon):
    beto, tid = _turno_de_beto(inventory_lambda, utils)
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=beto, query={"userId": BETO})
    assert st == 200, d
    assert d["user"] == {"id": BETO, "name": "Beto"}

    assert [x["orderId"] for x in d["dispatched"]] == ["ORD-1", "ORD-2"]
    assert d["dispatched"][0]["trackingNumber"] == "EST-1" and d["dispatched"][0]["stock"] == "Bodega Central"
    assert [x["orderId"] for x in d["delivered"]] == ["ORD-1"] and d["delivered"][0]["signedBy"] == "Firmó Lucía 12:40"
    assert d["transfers"]["created"][0]["transferId"] == tid and d["transfers"]["created"][0]["destination"] == "Del Valle"
    assert d["transfers"]["received"][0]["transferId"] == tid and d["transfers"]["received"][0]["missing"] == 1
    assert d["entries"] == [dict(d["entries"][0], qty=5, name="Colágeno")]
    # Dos mermas: el faltante de la transferencia (registrado como merma en el origen) y el frasco roto.
    mermas = {m["reason"]: m for m in d["damages"]}
    assert mermas["Frasco roto"]["qty"] == 1 and mermas["Frasco roto"]["name"] == "Colágeno"
    assert any(r.startswith("Faltante en transferencia") for r in mermas)
    assert len(d["pos"]["sales"]) == 1 and d["pos"]["salesTotal"] == 480.0 and len(d["pos"]["cuts"]) == 1
    assert d["counters"]["dispatched"] == 2 and d["counters"]["transfersReceived"] == 1 and d["counters"]["cashCuts"] == 1
    assert d["counters"]["damages"] == 2
    assert any(ev["action"] == "despacho.enviar" for ev in d["events"])

    texto = d["text"]
    assert texto.startswith("Resumen de turno · Beto · ")
    for fragmento in ("ORD-1 (Estafeta EST-1)", "ORD-2 (DHL DHL-2)", "Entregados (1): ORD-1 (firmó Firmó Lucía 12:40)",
                      f"{tid} → Del Valle", f"{tid} (faltaron 1)", "Entradas: 5 Colágeno", "1 Colágeno (Frasco roto)", "1 Magnesio (Faltante en transferencia",
                      "Caja: 1 ventas por $480.00; cortes: 1"):
        assert fragmento in texto, (fragmento, texto)


def test_otro_dia_sale_vacio_y_la_fecha_se_valida(inventory_lambda, utils, buzon):
    beto, _ = _turno_de_beto(inventory_lambda, utils)
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=beto, query={"userId": BETO, "date": "2020-01-01"})
    assert st == 200 and d["counters"]["dispatched"] == 0 and d["text"].endswith("Entregados (0): ninguno")
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=beto, query={"date": "ayer"})
    assert st == 400


def test_la_gerente_ve_el_turno_de_beto_y_un_companero_solo_el_suyo(inventory_lambda, utils, buzon):
    beto, _ = _turno_de_beto(inventory_lambda, utils)
    sofia = _empleado(utils, "7003", {"access_screen_stats": True}, "Sofía")
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=sofia, query={"userId": BETO})
    assert st == 200 and d["counters"]["dispatched"] == 2
    assert [e["name"] for e in d["team"]] == ["Beto", "Sofía"]   # para elegir de quién es el turno

    nadia = _empleado(utils, "7002", {"access_screen_pos": True}, "Nadia")
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=nadia, query={"userId": BETO})
    assert st == 403 and "access_screen_stats" in d["message"]
    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers=nadia)   # sin userId: el propio
    assert st == 200 and d["user"]["id"] == "7002" and d["counters"]["dispatched"] == 0
    assert "team" not in d   # sin permiso de estadísticas no se lista al equipo

    st, d = _llamar(inventory_lambda, "GET", "/inventory/turno/resumen", headers={}, query={"userId": BETO})
    assert st == 403
