"""Despacho en bloque con lista de surtido (paquete D, propuestas 9 y 13).

Beto (docs/qa/22 §6, tareas 1 y 2) transcribía 13 productos por 10 pedidos
para saber si alcanzaba el inventario y copiaba cada guía de WhatsApp en
siete pasos. Aquí se fija que el surtido se calcule solo, que el bloqueo diga
qué falta y qué sucursal sí lo tiene, y que "Despachar N" haga lo mismo que
el despacho de uno en uno (inventario, correo) sin repetirlo.
"""
import json

import pytest


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


BETO = "7001"
PRIVILEGIOS_BETO = {"order_mark_shipped": True, "order_mark_delivered": True, "access_screen_orders": True}


def _empleado(utils, user_id=BETO, privilegios=None, nombre="Beto"):
    utils._put_entity("EMPLOYEE", user_id, {"entityType": "employee", "employeeId": int(user_id), "name": nombre,
                                            "email": f"{nombre.lower()}@findingu.test", "canAccessAdmin": True,
                                            "privileges": utils._normalize_privileges(privilegios or PRIVILEGIOS_BETO), "active": True})
    token = f"tok-{user_id}"
    utils._put_session(token, {"userId": user_id, "role": "employee",
                               "privileges": utils._normalize_privileges(privilegios or PRIVILEGIOS_BETO)})
    return {"authorization": f"Bearer {token}", "x-user-id": user_id}


def _bodegas(utils):
    utils._put_entity("PRODUCT", 101, {"entityType": "product", "productId": 101, "name": "Magnesio", "price": 480, "active": True})
    utils._put_entity("PRODUCT", 102, {"entityType": "product", "productId": 102, "name": "Colágeno", "price": 620, "active": True})
    utils._put_entity("STOCK", "STK-CENTRAL", {"entityType": "stock", "stockId": "STK-CENTRAL", "name": "Bodega Central",
                                               "inventory": {"101": 10, "102": 10}, "isMainWarehouse": True})
    utils._put_entity("STOCK", "STK-VALLE", {"entityType": "stock", "stockId": "STK-VALLE", "name": "Del Valle",
                                             "inventory": {"101": 4, "102": 0}})


def _pedido(utils, oid, status="paid", delivery="shipping", items=None, **extra):
    utils._put_entity("ORDER", oid, {
        "entityType": "order", "orderId": oid, "status": status, "deliveryType": delivery,
        "customerName": f"Cliente {oid}", "recipientName": f"Cliente {oid}", "email": f"{oid.lower()}@test.com",
        "city": "Guadalajara", "state": "Jalisco", "paidAt": utils._now_iso(),
        "items": items or [{"productId": 101, "name": "Magnesio", "price": 480, "quantity": 1}],
        "netTotal": 480, "total": 609, **extra,
    })
    return oid


def _evento(metodo, ruta, cuerpo=None, headers=None, query=None):
    return {"httpMethod": metodo, "path": ruta, "headers": headers or {},
            "queryStringParameters": query or {}, "body": json.dumps(cuerpo or {})}


def _llamar(inventory_lambda, metodo, ruta, cuerpo=None, headers=None, query=None):
    r = inventory_lambda.lambda_handler(_evento(metodo, ruta, cuerpo, headers, query), None)
    return r["statusCode"], json.loads(r["body"] or "{}")


# ── Pendientes ───────────────────────────────────────────────────────────────

def test_pendientes_lista_solo_pagados_a_domicilio(inventory_lambda, utils):
    """Un pedido para recoger en sucursal nunca entra al bloque; uno pendiente de pago tampoco."""
    _bodegas(utils)
    beto = _empleado(utils)
    _pedido(utils, "ORD-A")
    _pedido(utils, "ORD-B", delivery="pickup")
    _pedido(utils, "ORD-C", status="pending")
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/pendientes", headers=beto)
    assert st == 200, d
    assert [o["id"] for o in d["orders"]] == ["ORD-A"]
    assert d["orders"][0]["items"] == [{"productId": "101", "name": "Magnesio", "quantity": 1}]
    assert d["orders"][0]["city"] == "Guadalajara"
    assert d["carrierIntegration"]["enabled"] is False  # apagada por omisión (docs/arquitectura/23 §13.8)


def test_pendientes_avisa_enviados_hace_mas_de_siete_dias(inventory_lambda, utils):
    """Cuatro pedidos se quedaron meses en "Enviada" sin que nadie lo viera."""
    _bodegas(utils)
    beto = _empleado(utils)
    _pedido(utils, "ORD-VIEJO", status="shipped", trackingNumber="EST-1", shippedAt="2026-01-01T10:00:00Z")
    _pedido(utils, "ORD-HOY", status="shipped", trackingNumber="EST-2", shippedAt=utils._now_iso())
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/pendientes", headers=beto)
    assert st == 200
    assert [r["id"] for r in d["staleShipped"]] == ["ORD-VIEJO"]
    assert d["staleShipped"][0]["daysSinceShipped"] >= 7


def test_sin_privilegio_de_envio_no_se_ve_el_despacho(inventory_lambda, utils):
    _bodegas(utils)
    nadia = _empleado(utils, "7002", {"access_screen_pos": True}, "Nadia")
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/pendientes", headers=nadia)
    assert st == 403 and "order_mark_shipped" in d["message"]
    st, _ = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar", {"stockId": "STK-CENTRAL"}, headers=nadia)
    assert st == 403


# ── Surtido ──────────────────────────────────────────────────────────────────

def test_surtido_con_faltante_dice_que_sucursal_si_lo_tiene(inventory_lambda, utils):
    """Rojo con "Del Valle tiene 4" en vez de "stock insuficiente" a secas."""
    _bodegas(utils)
    beto = _empleado(utils)
    utils._update_by_id("STOCK", "STK-CENTRAL", "SET inventory = :i", {":i": {"101": 1, "102": 10}})
    _pedido(utils, "ORD-1", items=[{"productId": 101, "name": "Magnesio", "quantity": 1}, {"productId": 102, "name": "Colágeno", "quantity": 2}])
    _pedido(utils, "ORD-2", items=[{"productId": 101, "name": "Magnesio", "quantity": 2}, {"productId": 102, "name": "Colágeno", "quantity": 2}])
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/surtido",
                    {"stockId": "STK-CENTRAL", "orderIds": ["ORD-1", "ORD-2", "ORD-2"]}, headers=beto)
    assert st == 200, d
    assert d["canDispatch"] is False
    lineas = {l["productId"]: l for l in d["lines"]}
    assert lineas["101"]["needed"] == 3 and lineas["101"]["available"] == 1 and lineas["101"]["short"] == 2
    assert lineas["101"]["status"] == "short"
    assert lineas["101"]["elsewhere"] == [{"stockId": "STK-VALLE", "name": "Del Valle", "available": 4}]
    assert lineas["102"]["status"] == "ok" and lineas["102"]["needed"] == 4
    assert "Faltan 2 Magnesio en Bodega Central; Del Valle tiene 4" in d["reasons"][0]


def test_surtido_valida_pedidos_y_bodega(inventory_lambda, utils):
    _bodegas(utils)
    beto = _empleado(utils)
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/surtido", {"stockId": "STK-CENTRAL"}, headers=beto)
    assert st == 400 and "Selecciona" in d["message"]
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/surtido", {"stockId": "STK-NADA", "orderIds": ["ORD-1"]}, headers=beto)
    assert st == 404
    _pedido(utils, "ORD-PICK", delivery="pickup")
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/surtido", {"stockId": "STK-CENTRAL", "orderIds": ["ORD-PICK", "ORD-X"]}, headers=beto)
    assert st == 200 and d["canDispatch"] is False
    motivos = {b["orderId"]: b["reason"] for b in d["blockedOrders"]}
    assert "recoger en sucursal" in motivos["ORD-PICK"] and "no existe" in motivos["ORD-X"]


# ── Enviar ───────────────────────────────────────────────────────────────────

def test_despacho_de_tres_pedidos_con_guias_por_csv(inventory_lambda, utils, buzon):
    """Los tres quedan shipped, el inventario baja una sola vez por pedido y
    cada comprador recibe su correo "va en camino" con la guía."""
    _bodegas(utils)
    beto = _empleado(utils)
    for n in (1, 2, 3):
        _pedido(utils, f"ORD-{n}")
    csv = "orderId,carrier,tracking\nORD-1,Estafeta,EST-111\nORD-2;DHL;DHL-222\nORD-3\tFedex\tFDX-333\n"
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar", {"stockId": "STK-CENTRAL", "csv": csv}, headers=beto)
    assert st == 200, d
    assert sorted(e["orderId"] for e in d["shipped"]) == ["ORD-1", "ORD-2", "ORD-3"]
    assert d["failed"] == []
    assert d["stockName"] == "Bodega Central" and d["batchId"].startswith("DSP-")

    guias = {e["orderId"]: (e["carrier"], e["trackingNumber"]) for e in d["shipped"]}
    assert guias["ORD-2"] == ("DHL", "DHL-222") and guias["ORD-3"] == ("Fedex", "FDX-333")
    for n in (1, 2, 3):
        pedido = utils._get_by_id("ORDER", f"ORD-{n}")
        assert pedido["status"] == "shipped"
        assert pedido["shippedBy"] == BETO and pedido["shippedAt"]
        assert pedido["dispatchBatchId"] == d["batchId"]
        assert pedido["trackingNumber"] == guias[f"ORD-{n}"][1]
    assert utils._get_by_id("STOCK", "STK-CENTRAL")["inventory"]["101"] == 7   # 10 − 3, una vez por pedido

    assert sorted(a for _, a, _, _ in buzon) == sorted(f"Tu pedido ORD-{n} va en camino" for n in (1, 2, 3))
    assert any("EST-111" in html for _, _, _, html in buzon)

    lote = utils._get_by_id("DISPATCH_BATCH", d["batchId"])
    assert lote["createdBy"] == BETO and lote["results"] == {"shipped": 3, "failed": 0}
    assert any(ev.get("action") == "despacho.enviar" for ev in utils._query_bucket("ADMIN_EVENT"))


def test_el_pedido_pickup_se_rechaza_y_el_resto_se_despacha(inventory_lambda, utils, buzon):
    """Parcial permitido después de validar el surtido (docs/arquitectura/23 §13.9)."""
    _bodegas(utils)
    beto = _empleado(utils)
    _pedido(utils, "ORD-DOM")
    _pedido(utils, "ORD-PICK", delivery="pickup")
    _pedido(utils, "ORD-SINGUIA")
    envios = [{"orderId": "ORD-DOM", "carrier": "Estafeta", "trackingNumber": "EST-9"},
              {"orderId": "ORD-PICK", "carrier": "Estafeta", "trackingNumber": "EST-10"},
              {"orderId": "ORD-SINGUIA", "carrier": "Estafeta", "trackingNumber": ""}]
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar", {"stockId": "STK-CENTRAL", "shipments": envios}, headers=beto)
    assert st == 200, d
    assert [e["orderId"] for e in d["shipped"]] == ["ORD-DOM"]
    fallos = {f["orderId"]: f["reason"] for f in d["failed"]}
    assert "recoger en sucursal" in fallos["ORD-PICK"]
    assert "Falta la guía" in fallos["ORD-SINGUIA"]
    assert utils._get_by_id("ORDER", "ORD-PICK")["status"] == "paid"
    assert utils._get_by_id("ORDER", "ORD-SINGUIA")["status"] == "paid"
    assert utils._get_by_id("STOCK", "STK-CENTRAL")["inventory"]["101"] == 9


def test_no_se_despacha_nada_si_el_surtido_no_alcanza(inventory_lambda, utils, buzon):
    _bodegas(utils)
    beto = _empleado(utils)
    utils._update_by_id("STOCK", "STK-CENTRAL", "SET inventory = :i", {":i": {"101": 1}})
    _pedido(utils, "ORD-1"); _pedido(utils, "ORD-2")
    envios = [{"orderId": "ORD-1", "carrier": "Estafeta", "trackingNumber": "A"},
              {"orderId": "ORD-2", "carrier": "Estafeta", "trackingNumber": "B"}]
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar", {"stockId": "STK-CENTRAL", "shipments": envios}, headers=beto)
    assert st == 409 and d["code"] == "STOCK_SHORT"
    assert "Del Valle tiene 4" in d["message"]
    assert d["lines"][0]["short"] == 1
    assert utils._get_by_id("ORDER", "ORD-1")["status"] == "paid"
    assert buzon == []


def test_solo_pedidos_pickup_responde_400(inventory_lambda, utils):
    _bodegas(utils)
    beto = _empleado(utils)
    _pedido(utils, "ORD-PICK", delivery="pickup")
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar",
                    {"stockId": "STK-CENTRAL", "shipments": [{"orderId": "ORD-PICK", "trackingNumber": "X"}]}, headers=beto)
    assert st == 400 and d["failed"][0]["orderId"] == "ORD-PICK"


def test_generar_guias_con_la_paqueteria_configurada(inventory_lambda, utils, buzon):
    """Con la integración encendida, "Generar guías" completa las que faltan."""
    _bodegas(utils)
    beto = _empleado(utils)
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1",
                                            "config": {"shipping": {"carrierIntegration": {"enabled": True, "provider": "simulada"}}}})
    utils._invalidate_app_config_cache()
    _pedido(utils, "ORD-1")
    st, d = _llamar(inventory_lambda, "POST", "/inventory/despacho/enviar",
                    {"stockId": "STK-CENTRAL", "orderIds": ["ORD-1"], "generateLabels": True}, headers=beto)
    assert st == 200, d
    assert d["shipped"][0]["trackingNumber"] == "SIM-1" and d["shipped"][0]["labelUrl"].endswith("SIM-1.pdf")
    pedido = utils._get_by_id("ORDER", "ORD-1")
    assert pedido["labelUrl"] and pedido["shippingCarrier"] == "Simulada"


# ── Bodega por defecto ───────────────────────────────────────────────────────

def test_la_bodega_por_defecto_se_guarda_y_se_lee_del_perfil(inventory_lambda, utils):
    """Propuesta 9: el stock activo de Beto es Bodega Central sin cambiarlo cada turno."""
    _bodegas(utils)
    beto = _empleado(utils)
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/preferencias", headers=beto)
    assert st == 200 and d == {"defaultStockId": None, "stockName": None}
    st, d = _llamar(inventory_lambda, "PUT", "/inventory/despacho/preferencias", {"defaultStockId": "STK-CENTRAL"}, headers=beto)
    assert st == 200 and d == {"defaultStockId": "STK-CENTRAL", "stockName": "Bodega Central"}
    assert utils._get_by_id("EMPLOYEE", BETO)["defaultStockId"] == "STK-CENTRAL"
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/preferencias", headers=beto)
    assert st == 200 and d["stockName"] == "Bodega Central"


def test_la_bodega_por_defecto_valida_bodega_y_sesion(inventory_lambda, utils):
    _bodegas(utils)
    beto = _empleado(utils)
    st, d = _llamar(inventory_lambda, "PUT", "/inventory/despacho/preferencias", {"defaultStockId": "STK-NO"}, headers=beto)
    assert st == 404
    st, d = _llamar(inventory_lambda, "PUT", "/inventory/despacho/preferencias", {}, headers=beto)
    assert st == 400
    st, d = _llamar(inventory_lambda, "GET", "/inventory/despacho/preferencias", headers={})
    assert st == 401


def test_el_reloj_descubre_las_tareas_programadas(inventory_lambda):
    """docs/arquitectura/23 §0.3: el harness lee TAREAS_PROGRAMADAS del anfitrión."""
    assert inventory_lambda.TAREAS_PROGRAMADAS == [("POST", "/inventory/envios/rastrear"), ("POST", "/inventory/envios/cerrar")]
