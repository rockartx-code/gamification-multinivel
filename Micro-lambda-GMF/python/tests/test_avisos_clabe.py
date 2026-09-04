"""Aviso "registra tu CLABE" (paquete A, propuesta 4).

Sofía escribía por WhatsApp a Claudia y a Bety el día de pago para pedirles
la CLABE. Ahora se pide sola: al activarse la socia por primera vez y al
confirmarse su primera comisión del mes; un correo por motivo y mes, con un
aviso en el panel dirigido solo a ella.
"""
import json

import pytest


@pytest.fixture
def modulos(utils):
    import order_lambda, commissions_lambda, dashboard_common
    return order_lambda, commissions_lambda, dashboard_common


@pytest.fixture
def correos(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto)))
    return enviados


def _cliente(utils, cid, nombre, leader=None, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.lower()}@test.com", **extra}
    if leader is not None:
        item["leaderId"] = leader
    utils._put_entity("CUSTOMER", cid, item)
    return cid


def _producto(utils, pid=9):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart", "price": 480, "vpPoints": 10, "active": True})
    return pid


def _pagar(order_lambda, commissions_lambda, cid, pid, qty):
    cuerpo = {"customerId": cid, "customerName": "x", "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": qty}],
              "recipientName": "x", "deliveryType": "shipping",
              "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro", "postalCode": "76000", "country": "MX"}}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = (pedido.get("order") or pedido)["orderId"]
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_PAID"}, None)
    return oid


def _entregar(utils, commissions_lambda, oid):
    utils._update_by_id("ORDER", oid, "SET #s = :s", {":s": "delivered"}, {"#s": "status"})
    commissions_lambda.lambda_handler({"orderId": oid, "action": "ORDER_DELIVERED"}, None)


ASUNTO = "Registra tu CLABE para cobrar tus comisiones"
#: Propuesta 2: el aviso del portal ya no promete dinero que no existe.
TITULO_ACTIVACION = "Registra tu CLABE: ya te activaste"
TITULO_COMISION = "Registra tu CLABE para cobrar tus comisiones"


def test_al_activarse_por_primera_vez_sin_clabe_se_le_pide_una_sola_vez(modulos, utils, correos):
    order_lambda, commissions_lambda, dashboard_common = modulos
    pid = _producto(utils)
    bety = _cliente(utils, 2, "Bety")
    _pagar(order_lambda, commissions_lambda, bety, pid, 1)            # 10 PC: aún no activa
    assert correos == []
    _pagar(order_lambda, commissions_lambda, bety, pid, 1)            # 20 PC: se activa
    assert correos == [("bety@test.com", ASUNTO)]
    assert utils._get_by_id("CUSTOMER", bety)["clabeReminderFirstAt"]
    avisos = dashboard_common._active_notifications_for_customer(bety)
    assert [a["title"] for a in avisos] == [TITULO_ACTIVACION]
    assert avisos[0]["description"].startswith("Acabas de activarte este mes")
    assert "comisiones a tu favor" not in avisos[0]["description"], "no se promete dinero que no existe"
    assert "#comisiones" in avisos[0]["linkUrl"]

    # Otra compra (sigue activa) o una activación del mes siguiente: no se repite.
    _pagar(order_lambda, commissions_lambda, bety, pid, 2)
    assert len(correos) == 1
    assert commissions_lambda.pagos_handlers.avisar_clabe_al_activarse(bety) is False


def test_con_clabe_registrada_no_se_pide_nada_al_activarse(modulos, utils, correos):
    order_lambda, commissions_lambda, _ = modulos
    pid = _producto(utils)
    claudia = _cliente(utils, 1, "Claudia", clabeInterbancaria="012345678901231234")
    _pagar(order_lambda, commissions_lambda, claudia, pid, 2)
    assert correos == []


def test_el_aviso_al_activarse_se_puede_apagar_por_configuracion(modulos, utils, correos, monkeypatch):
    order_lambda, commissions_lambda, _ = modulos
    cfg = utils._load_app_config()
    cfg["rewards"]["clabeReminderOnActivation"] = False
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    pid = _producto(utils)
    bety = _cliente(utils, 2, "Bety")
    _pagar(order_lambda, commissions_lambda, bety, pid, 2)
    assert correos == []


def test_al_confirmarse_la_primera_comision_del_mes_sin_clabe_se_pide_una_vez_por_mes(modulos, utils, correos):
    order_lambda, commissions_lambda, dashboard_common = modulos
    pid = _producto(utils)
    marcela = _cliente(utils, 1, "Marcela", clabeInterbancaria="012345678901231234")
    _pagar(order_lambda, commissions_lambda, marcela, pid, 2)          # activa, con CLABE: sin aviso
    utils._update_by_id("CUSTOMER", marcela, "REMOVE clabeInterbancaria", {})
    rodrigo = _cliente(utils, 2, "Rodrigo", leader=marcela, clabeInterbancaria="002180000000005678")
    oid = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 2)     # $96 pendientes para Marcela
    correos.clear()
    _entregar(utils, commissions_lambda, oid)                            # se confirma
    assert correos == [("marcela@test.com", ASUNTO)]
    assert utils._get_ledger_month(marcela, utils._month_key())["clabeReminderAt"]
    avisos_marcela = dashboard_common._active_notifications_for_customer(marcela)
    assert [a["title"] for a in avisos_marcela] == [TITULO_COMISION]
    assert "$96.00 en comisiones confirmadas" in avisos_marcela[0]["description"]
    assert dashboard_common._active_notifications_for_customer(rodrigo) == [], "dirigido solo a Marcela"

    oid2 = _pagar(order_lambda, commissions_lambda, rodrigo, pid, 1)
    correos.clear()
    _entregar(utils, commissions_lambda, oid2)                           # segunda confirmada del mes
    assert correos == []


def test_no_contactar_bloquea_el_correo_pero_el_panel_si_avisa(modulos, utils, correos):
    order_lambda, commissions_lambda, dashboard_common = modulos
    pid = _producto(utils)
    bety = _cliente(utils, 2, "Bety", doNotContact=True)
    _pagar(order_lambda, commissions_lambda, bety, pid, 2)
    assert correos == []
    assert [a["title"] for a in dashboard_common._active_notifications_for_customer(bety)] == [TITULO_ACTIVACION]


def test_un_aviso_dirigido_no_se_mezcla_con_los_generales(modulos, utils):
    _, _, dashboard_common = modulos
    utils._put_entity("NOTIFICATION", "NTF-GENERAL", {"entityType": "notification", "notificationId": "NTF-GENERAL",
                                                       "title": "Promoción de octubre", "active": True})
    utils._put_entity("NOTIFICATION", "NTF-SOLO-2", {"entityType": "notification", "notificationId": "NTF-SOLO-2",
                                                      "title": "Solo para Bety", "active": True, "targetCustomerId": "2"})
    assert {a["title"] for a in dashboard_common._active_notifications_for_customer(2)} == {"Promoción de octubre", "Solo para Bety"}
    assert {a["title"] for a in dashboard_common._active_notifications_for_customer(1)} == {"Promoción de octubre"}


def test_quien_recibio_el_aviso_de_activacion_recibe_despues_el_de_comision(modulos, utils, correos):
    """Ximena y Fabiola vieron "Ya tienes comisiones a tu favor" con $0.00 y la
    red vacía: *"Es lo único que me tiró la confianza en todo lo demás"*.
    Ahora el de activación dice lo que pasó, y el de comisión llega aparte,
    con su monto, cuando hay un peso confirmado."""
    order_lambda, commissions_lambda, dashboard_common = modulos
    pid = _producto(utils)
    paulina = _cliente(utils, 1, "Paulina")
    ximena = _cliente(utils, 2, "Ximena", leader=paulina, clabeInterbancaria="002180000000005678")
    _pagar(order_lambda, commissions_lambda, paulina, pid, 2)          # se activa, sin comisiones
    avisos = dashboard_common._active_notifications_for_customer(paulina)
    assert [a["title"] for a in avisos] == [TITULO_ACTIVACION]
    assert "$0.00" not in avisos[0]["description"]

    oid = _pagar(order_lambda, commissions_lambda, ximena, pid, 2)
    _entregar(utils, commissions_lambda, oid)                          # su primera comisión confirmada
    titulos = {a["title"] for a in dashboard_common._active_notifications_for_customer(paulina)}
    assert titulos == {TITULO_ACTIVACION, TITULO_COMISION}, "el segundo aviso sí llega, con el monto"
    comision = [a for a in dashboard_common._active_notifications_for_customer(paulina) if a["title"] == TITULO_COMISION][0]
    assert "$96.00 en comisiones confirmadas" in comision["description"]
    assert "el día 10" in comision["description"]


def test_el_aviso_de_activacion_caduca_a_los_30_dias_y_el_de_comision_a_los_45(utils):
    import pagos_handlers
    hoy = utils._now_iso()[:10]
    nid_a = pagos_handlers._aviso_panel_clabe(7, "2027-03", "activacion")
    nid_c = pagos_handlers._aviso_panel_clabe(7, "2027-03", "comision")
    assert nid_a != nid_c and nid_a.endswith("-activacion") and nid_c.endswith("-comision")
    from datetime import datetime, timedelta
    esperado = lambda d: (datetime.strptime(hoy, "%Y-%m-%d") + timedelta(days=d)).strftime("%Y-%m-%d")
    assert utils._get_by_id("NOTIFICATION", nid_a)["endAt"] == esperado(30)
    assert utils._get_by_id("NOTIFICATION", nid_c)["endAt"] == esperado(45)


def test_pedir_la_clabe_sin_comisiones_no_promete_dinero_que_no_existe(utils):
    """Renata: *"Le estamos prometiendo dinero a dos socias que según el
    sistema no tienen nada"*."""
    import dashboard_common, pagos_handlers
    utils._put_entity("CUSTOMER", 8, {"entityType": "customer", "customerId": 8, "name": "Ximena",
                                      "email": "ximena@test.com"})
    pagos_handlers._aviso_panel_clabe(8, "2027-03", "recordatorio")
    aviso = dashboard_common._active_notifications_for_customer(8)[0]
    assert "$0.00" not in aviso["description"]
    assert "comisiones confirmadas" not in aviso["description"]
    assert aviso["description"].startswith("Nos falta tu CLABE")
