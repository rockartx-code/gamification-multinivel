"""Correcciones de la jornada del 12 de enero (Diana, Sofía, Beto, Nadia y Claudia)."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

CAJERA = {"x-user-id": "paco"}


def _hace(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sesion(utils, uid, role="admin", name="Sofía Herrera"):
    token = f"session-token-{uid}"
    utils._put_session(token, {"sessionId": token, "userId": str(uid), "role": role, "name": name,
                               "privileges": {}, "canAccessAdmin": role != "cliente"})
    return {"Authorization": f"Bearer {token}"}


def test_registrar_la_clabe_apaga_el_aviso_registra_tu_clabe(utils):
    """Claudia guardó la CLABE y el Centro de avisos seguía marcando "Registra tu CLABE"."""
    import customer_lambda, pagos_handlers
    utils._put_entity("CUSTOMER", 77, {"entityType": "customer", "customerId": 77, "name": "Claudia Ibarra", "isAssociate": True})
    nid = pagos_handlers._aviso_panel_clabe(77, "2026-12")
    assert utils._get_by_id("NOTIFICATION", nid)["active"] is True
    r = customer_lambda.handle_update_clabe("77", {"clabe": "012345678901234567"}, _sesion(utils, 77, role="cliente", name="Claudia"))
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("NOTIFICATION", nid)["active"] is False


def test_la_lista_de_pedidos_trae_las_notas_internas_con_el_nombre_de_quien_las_escribio(utils):
    """Beto abría el detalle y el bloque "Notas internas" salía vacío; el autor era un id."""
    import order_lambda
    utils._put_entity("ORDER", "ORD-NOTA", {"entityType": "order", "orderId": "ORD-NOTA", "customerId": 5,
                                            "customerName": "Rosa", "status": "paid", "total": 800, "items": [],
                                            "createdAt": _hace(1)}, created_at_iso=_hace(1))
    r = order_lambda.handle_add_order_note("ORD-NOTA", {"text": "No despachar hasta aclarar"}, _sesion(utils, 1788339615521))
    assert r["statusCode"] == 200, r["body"]
    nota = json.loads(r["body"])["order"]["adminNotes"][-1]
    assert nota["by"] == "1788339615521" and nota["byName"] == "Sofía Herrera"
    r = order_lambda.handle_list_orders(None, {"status": "paid"}, {"x-user-id": "1", "x-user-role": "admin"})
    assert r["statusCode"] == 200, r["body"]
    listado = {o["orderId"]: o for o in json.loads(r["body"])["orders"]}
    assert listado["ORD-NOTA"]["adminNotes"][0]["text"] == "No despachar hasta aclarar"


def test_el_cuadro_de_honor_no_lista_a_quien_lleva_cero(utils):
    """Siete socias con 0 VP salían en el top 10 y recibían "Bajaste en el ranking"."""
    import dashboard_lambda as dl
    utils._put_entity("CUSTOMER", 1, {"entityType": "customer", "customerId": 1, "name": "Rodri", "leaderId": None})
    utils._put_entity("CUSTOMER", 2, {"entityType": "customer", "customerId": 2, "name": "Claudia", "leaderId": None})
    mes = utils._month_key()
    utils._put_entity("ASSOCIATE_MONTH", utils._associate_month_entity_id(1, mes),
                      {"entityType": "associateMonth", "associateId": 1, "month": mes,
                       "netVolume": Decimal("960"), "netVP": Decimal("20")})
    tablero = dl.get_honor_board()
    cuerpo = tablero.get("body") or tablero
    datos = json.loads(cuerpo) if isinstance(cuerpo, str) else cuerpo
    assert [e["name"] for e in datos["byVp"]] == ["Rodri"]
    assert [e["name"] for e in datos["byVg"]] == ["Rodri"]


def test_un_pedido_creado_por_api_toma_el_nombre_del_cliente_y_de_los_productos(utils, monkeypatch):
    """ORD-66407B13: "Cliente" con "Producto x1 · $800" en Pedidos, imposible de despachar."""
    import order_lambda
    monkeypatch.setattr(order_lambda, "ORDER_SFN_ARN", None, raising=False)
    utils._put_entity("CUSTOMER", 44, {"entityType": "customer", "customerId": 44, "name": "Rosa Elena Mendoza",
                                       "email": "rosa@test.com", "isAssociate": True})
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Finding Pro 500g",
                                     "price": 800, "vpPoints": 15, "active": True, "commissionable": True})
    r = order_lambda.handle_create_order({"customerId": 44, "items": [{"productId": 9, "quantity": 1, "price": 800}]}, {})
    assert r["statusCode"] == 201, r["body"]
    pedido = json.loads(r["body"])
    pedido = pedido.get("order") or pedido
    assert pedido["customerName"] == "Rosa Elena Mendoza"
    assert pedido["items"][0]["name"] == "Finding Pro 500g"


def test_una_venta_con_tarjeta_anterior_al_ultimo_corte_entra_al_siguiente(utils):
    """Nadia: dos ventas con tarjeta de noviembre seguían "sin corte" después de cuatro cortes."""
    import caja_handlers
    utils._put_entity("POS_SALE", "POS-NOV", {"entityType": "posSale", "saleId": "POS-NOV", "stockId": "STK-1",
                                              "attendantUserId": "paco", "paymentMethod": "card", "total": Decimal("480"),
                                              "createdAt": "2026-11-15T12:00:00Z"}, created_at_iso="2026-11-15T12:00:00Z")
    utils._put_entity("POS_CASH_CUT", "CUT-DIC", {"entityType": "posCashCut", "cashCutId": "CUT-DIC", "stockId": "STK-1",
                                                  "attendantUserId": "paco", "total": Decimal("0"), "salesCount": 0,
                                                  "cashToKeep": Decimal("500"), "createdAt": "2026-12-13T11:31:00Z"},
                      created_at_iso="2026-12-13T11:31:00Z")
    ventas = caja_handlers.ventas_desde("STK-1", "paco", "2026-12-13T11:31:00Z")
    assert [v["saleId"] for v in ventas] == ["POS-NOV"]


def test_un_pedido_tardio_pesa_mas_que_la_clabe_pendiente(utils):
    """"Pedido tardío 0" mientras Acciones decía "4 pedidos pagados sin envío"."""
    import seguimiento_handlers as sh
    ficha = {"customerId": 1, "name": "Claudia", "createdAt": _hace(60)}
    pedidos = [{"orderId": "ORD-1", "status": "paid", "createdAt": _hace(23), "updatedAt": _hace(23)}]
    situacion, tardio = sh._situacion(ficha, pedidos, datetime.now(timezone.utc), {}, 195.2)
    assert situacion == "pedido_tardio" and tardio is not None
    situacion, _ = sh._situacion(ficha, [], datetime.now(timezone.utc), {}, 195.2)
    assert situacion == "clabe_pendiente"


def test_el_correo_de_pago_en_texto_plano_no_deja_espacios_dobles_ni_pega_el_enlace(utils):
    """"En modo socio, con  $300.00  más..." con el enlace pegado al final del párrafo."""
    from core import order_emails
    order = {"orderId": "ORD-X", "customerName": "Diana", "partnerMode": "invitado", "partnerSavings": 0,
             "partnerSavingsNextMissing": 300, "partnerSavingsNextRate": "0.10", "items": [], "total": 829}
    _, texto, _ = order_emails._plantillas(order, "paid", {}, "http://localhost:4321")
    assert "con $300.00 más" in texto and "  " not in texto.replace("\n", "")
    assert "\nConoce el modo socio: http://localhost:4321/#/modo-socio" in texto
