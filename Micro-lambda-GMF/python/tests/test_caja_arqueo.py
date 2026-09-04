"""Arqueo de caja (paquete E): lo que Nadia y Paco cuadraban a mano.

"La pantalla sólo registra el número" (nadia-turno2); "¿Debo guardarme los
$440 de cambio en mi bolsillo?" (paco-turno1). El corte compara el efectivo
esperado con el contado, exige motivo a la diferencia y dice a dónde va el
dinero.
"""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def inventory_lambda(utils, monkeypatch):
    import inventory_lambda
    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", None)
    monkeypatch.setattr(inventory_lambda, "_validate_pos_auth", lambda code: code == "2468")
    return inventory_lambda


CAJERA = {"x-user-id": "paco"}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}


def _mostrador(utils, pid=201, stock="STK-1"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("STOCK", stock, {"entityType": "stock", "stockId": stock, "name": "Tienda",
                                       "inventory": {str(pid): 40}, "linkedUserIds": ["paco"]})
    return pid, stock


def _venta(inventory_lambda, pid, stock, **extra):
    cuerpo = {"stockId": stock, "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": 1}],
              "paymentMethod": "cash", **extra}
    r = inventory_lambda.handle_pos_sale(cuerpo, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    return json.loads(r["body"])


def _peticion(inventory_lambda, metodo, ruta, cuerpo=None, headers=None, query=None):
    return inventory_lambda.lambda_handler({
        "httpMethod": metodo, "path": ruta, "headers": headers or ADMIN,
        "queryStringParameters": query or {}, "body": json.dumps(cuerpo or {}),
    }, None)


def _turno_completo(inventory_lambda, utils):
    """Fondo 200 + efectivo 480 + parcial en efectivo 500 + abono 100 + mixta 200 − retiro 150 = 1,330."""
    pid, stock = _mostrador(utils)
    utils._put_entity("POS_CASH_CUT", "CUT-AYER", {
        "entityType": "posCashCut", "cashCutId": "CUT-AYER", "stockId": stock, "attendantUserId": "paco",
        "total": Decimal("900"), "salesCount": 3, "cashToKeep": Decimal("200"), "withdrawnAmount": Decimal("700"),
        "createdAt": "2026-09-01T20:00:00Z"})
    _venta(inventory_lambda, pid, stock)                                           # 480 efectivo
    parcial = _venta(inventory_lambda, pid, stock, paymentType="partial", amountPaid=500, authCode="2468",
                     items=[{"productId": pid, "name": "Klinhart", "price": 840, "quantity": 1}])  # 500 ahora
    r = inventory_lambda.handle_settle_pos_sale(parcial["saleId"], {"amount": 100, "paymentMethod": "cash"}, CAJERA)
    assert r["statusCode"] == 200, r["body"]                                         # abono 100
    _venta(inventory_lambda, pid, stock, paymentMethod="card")                       # tarjeta: no entra
    _venta(inventory_lambda, pid, stock, payments=[{"method": "cash", "amount": 200},
                                                   {"method": "card", "amount": 280}])  # mixta: 200
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 150, "reason": "paquetería",
                                                "receiver": "Beto", "authCode": "2468"}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    return pid, stock


def test_el_efectivo_esperado_suma_fondo_ventas_abonos_y_mixtas_y_resta_retiros(inventory_lambda, utils):
    _, stock = _turno_completo(inventory_lambda, utils)
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", headers=ADMIN | CAJERA, query={"stockId": stock})
    assert r["statusCode"] == 200, r["body"]
    arqueo = json.loads(r["body"])["arqueo"]
    assert arqueo["openingCash"] == 200
    assert arqueo["cashSales"] == 980            # 480 + 500 del parcial
    assert arqueo["cashSettlements"] == 100
    assert arqueo["cashFromMixed"] == 200
    assert arqueo["withdrawals"] == 150
    assert arqueo["expectedCash"] == 1330
    assert arqueo["nonCashTotal"] == 760         # tarjeta 480 + parte con tarjeta de la mixta 280
    assert arqueo["salesCount"] == 5             # 4 ventas + el abono; la tarjeta también es venta del turno
    tipos = [m["type"] for m in arqueo["movements"]]
    assert tipos[0] == "opening" and tipos[-1] == "withdrawal"
    assert "settlement" in tipos and "mixed" in tipos and "sale" in tipos
    assert arqueo["config"]["denominations"][:3] == [1000, 500, 200]
    assert arqueo["config"]["requireDifferenceReason"] is True

    # El control de caja usa exactamente la misma suma.
    control = inventory_lambda._build_pos_cash_control(stock, "paco")
    assert control["currentTotal"] == 1330


def test_el_arqueo_sin_sucursal_ni_liga_explica_que_pedirle_a_la_gerente(inventory_lambda, utils):
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", headers=ADMIN | {"x-user-id": "nadia"})
    assert r["statusCode"] == 400
    assert "gerente" in json.loads(r["body"])["message"]


def test_el_arqueo_exige_el_privilegio_del_pos(inventory_lambda, utils):
    empleado = {"x-user-id": "nadia", "x-user-role": "employee", "x-user-privileges": "{}"}
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", headers=empleado, query={"stockId": "STK-1"})
    assert r["statusCode"] == 403


def test_una_diferencia_sin_motivo_no_cierra_el_corte(inventory_lambda, utils):
    _, stock = _turno_completo(inventory_lambda, utils)
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 1300, "cashToKeep": 1300, "withdrawalAmount": 0}, CAJERA)
    assert r["statusCode"] == 400, r["body"]
    assert "faltan $30.00" in json.loads(r["body"])["message"]
    # Con motivo sí cierra y la diferencia queda registrada.
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 1300, "cashToKeep": 1300, "withdrawalAmount": 0,
                                          "differenceReason": "di cambio de más en la venta de las 5"}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    assert corte["cashExpected"] == 1330 and corte["cashCounted"] == 1300 and corte["difference"] == -30
    assert corte["differenceReason"].startswith("di cambio")
    guardado = utils._get_by_id("POS_CASH_CUT", corte["cashCutId"])
    for campo in ("cashExpected", "cashCounted", "difference", "openingCash", "cashFromMixed"):
        assert isinstance(guardado[campo], Decimal), campo


def test_el_corte_reparte_lo_contado_entre_fondo_y_retiro_con_codigo(inventory_lambda, utils):
    _, stock = _turno_completo(inventory_lambda, utils)
    base = {"stockId": stock, "cashCounted": 1330, "cashToKeep": 330, "withdrawalAmount": 1000, "withdrawalReceiver": "Sofía"}
    # Sin código (o con uno malo) no se retira nada.
    r = inventory_lambda.handle_cash_cut(base | {"authCode": "0000"}, CAJERA)
    assert r["statusCode"] == 403, r["body"]
    # Fondo + retiro tienen que dar lo contado.
    r = inventory_lambda.handle_cash_cut(base | {"authCode": "2468", "cashToKeep": 300}, CAJERA)
    assert r["statusCode"] == 400 and "sumar exactamente" in json.loads(r["body"])["message"]
    # Sin quién recibe, tampoco.
    r = inventory_lambda.handle_cash_cut(base | {"authCode": "2468", "withdrawalReceiver": ""}, CAJERA)
    assert r["statusCode"] == 400 and "recibe" in json.loads(r["body"])["message"]

    r = inventory_lambda.handle_cash_cut(base | {"authCode": "2468", "denominations": {"500": 2, "200": 1, "100": 1, "20": 1, "10": 1}}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    corte, control = cuerpo["cut"], cuerpo["control"]
    assert corte["cashCutId"].startswith("CUT-")
    assert corte["cashToKeep"] == 330 and corte["withdrawnAmount"] == 1000 and corte["withdrawalReceiver"] == "Sofía"
    assert corte["difference"] == 0 and corte["denominations"]["500"] == 2
    # El retiro del corte queda como retiro ligado, y el fondo arranca la caja siguiente.
    retiro = utils._get_by_id("POS_WITHDRAWAL", corte["cutWithdrawalId"])
    assert retiro["cashCutId"] == corte["cashCutId"] and retiro["receiver"] == "Sofía" and retiro["amount"] == Decimal("1000")
    assert control["currentTotal"] == 330 and control["salesCount"] == 0 and control["openingCash"] == 330
    # Todas las ventas del turno (también la de tarjeta) quedaron dentro del corte.
    ventas = [v for v in utils._query_bucket("POS_SALE") if v.get("stockId") == stock]
    assert ventas and all(v.get("cashCutId") == corte["cashCutId"] for v in ventas)


def test_un_retiro_mayor_al_efectivo_disponible_se_rechaza(inventory_lambda, utils):
    pid, stock = _mostrador(utils)
    _venta(inventory_lambda, pid, stock)
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 500, "reason": "proveedor",
                                                "receiver": "Beto", "authCode": "2468"}, CAJERA)
    assert r["statusCode"] == 400, r["body"]
    assert "$480.00" in json.loads(r["body"])["message"]
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 100, "reason": "proveedor",
                                                "receiver": "Beto", "authCode": "2468"}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["withdrawal"]["receiver"] == "Beto" and cuerpo["remainingCash"] == 380


def test_el_comprobante_se_consulta_por_folio_y_se_envia_por_correo(inventory_lambda, utils, monkeypatch):
    _, stock = _turno_completo(inventory_lambda, utils)
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 1330, "cashToKeep": 1330, "withdrawalAmount": 0}, CAJERA)
    cut_id = json.loads(r["body"])["cut"]["cashCutId"]

    r = _peticion(inventory_lambda, "GET", f"/inventory/pos/cash-cuts/{cut_id}")
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["cut"]["cashCounted"] == 1330
    assert _peticion(inventory_lambda, "GET", "/inventory/pos/cash-cuts/CUT-NADA")["statusCode"] == 404

    enviados = []
    from core import email as correo
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto)))
    # Sin correo configurado ni escrito: 400 con la instrucción.
    r = _peticion(inventory_lambda, "POST", f"/inventory/pos/cash-cuts/{cut_id}/enviar")
    assert r["statusCode"] == 400 and "Configuración" in json.loads(r["body"])["message"]
    # Con el correo de la gerente en config, se manda.
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1",
                                           "config": {"pos": {"cashCutNotifyEmail": "sofia@findingu.mx"}}})
    utils._invalidate_app_config_cache()
    r = _peticion(inventory_lambda, "POST", f"/inventory/pos/cash-cuts/{cut_id}/enviar")
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["to"] == "sofia@findingu.mx"
    assert enviados and enviados[0][0] == "sofia@findingu.mx" and "$1,330.00" in enviados[0][2]
    assert utils._get_by_id("POS_CASH_CUT", cut_id)["notifiedTo"] == "sofia@findingu.mx"


def test_los_cortes_sin_arqueo_siguen_funcionando_igual(inventory_lambda, utils):
    """Compatibilidad: sin `cashCounted` se guarda contado = esperado y diferencia 0."""
    pid, stock = _mostrador(utils)
    _venta(inventory_lambda, pid, stock)
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashToKeep": 100}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    assert corte["total"] == 480 and corte["withdrawnAmount"] == 380 and corte["cashToKeep"] == 100
    assert corte["cashCounted"] == 480 and corte["difference"] == 0
    assert inventory_lambda.handle_cash_cut({"stockId": stock, "cashToKeep": 5}, CAJERA)["statusCode"] == 400


def test_una_venta_anulada_no_cuenta_en_el_efectivo_esperado(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    venta = _venta(inventory_lambda, pid, stock)
    _venta(inventory_lambda, pid, stock)
    r = inventory_lambda.handle_void_pos_sale(venta["saleId"], {"reason": "se arrepintió"}, CAJERA)
    assert r["statusCode"] == 200, r["body"]
    control = inventory_lambda._build_pos_cash_control(stock, "paco")
    assert control["currentTotal"] == 480 and control["salesCount"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Abrir turno (paquete F · ronda 26, propuesta 5)
#
# Mireya, cajera de tercer día: "llegué con $500 en el cajón y la pantalla me
# dijo Fondo inicial $0.00 en un campo de solo lectura". Vendió todo el día
# descuadrada, el corte le salió con un sobrante falso de $540 y los $1,040 se
# quedaron toda la noche en el cajón de la tienda.
# ─────────────────────────────────────────────────────────────────────────────


def test_una_caja_sin_corte_previo_pide_el_fondo_y_lo_declara(inventory_lambda, utils):
    pid, stock = _mostrador(utils)

    # Antes de declarar nada: la pantalla no enseña un $0.00 de adorno, pide el fondo.
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", headers=ADMIN | CAJERA, query={"stockId": stock})
    arqueo = json.loads(r["body"])["arqueo"]
    assert arqueo["openingCash"] == 0
    assert arqueo["openingSource"] == "sin_declarar"
    assert arqueo["needsOpening"] is True

    # Mireya declara los $500 con los que arrancó.
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"stockId": stock, "openingCash": 500}, headers=ADMIN | CAJERA)
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["opening"]["openingCash"] == 500
    assert cuerpo["arqueo"]["openingCash"] == 500 and cuerpo["arqueo"]["needsOpening"] is False

    # El fondo declarado manda en el arqueo y aparece en "Ver movimientos".
    _venta(inventory_lambda, pid, stock)  # 480 en efectivo
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", headers=ADMIN | CAJERA, query={"stockId": stock})
    arqueo = json.loads(r["body"])["arqueo"]
    assert arqueo["openingCash"] == 500 and arqueo["openingSource"] == "apertura"
    assert arqueo["expectedCash"] == 980
    apertura = arqueo["movements"][0]
    assert apertura["type"] == "opening" and apertura["amount"] == 500
    assert apertura["label"] == "Fondo declarado al abrir el turno"
    assert apertura["at"] and apertura["id"].startswith("APE-")


def test_con_el_fondo_declarado_el_corte_cuadra_en_vez_de_sobrar_540(inventory_lambda, utils):
    """El corte de Mireya: $500 de fondo + $40 de venta = $540 contados, diferencia $0."""
    pid, stock = _mostrador(utils)
    _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
              cuerpo={"stockId": stock, "openingCash": 500}, headers=ADMIN | CAJERA)
    _venta(inventory_lambda, pid, stock, items=[{"productId": pid, "name": "Klinhart", "price": 40, "quantity": 1}])

    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 540, "cashToKeep": 540,
                                          "withdrawalAmount": 0}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    assert corte["cashExpected"] == 540 and corte["difference"] == 0
    assert corte["openingSource"] == "apertura"
    assert "declarado al abrir el turno" in inventory_lambda.caja_handlers.texto_comprobante(corte)

    # La apertura queda dentro del corte: el siguiente turno hereda el fondo del corte.
    control = inventory_lambda._build_pos_cash_control(stock, "paco")
    assert control["openingCash"] == 540


def test_el_fondo_no_se_cambia_con_el_turno_ya_andando(inventory_lambda, utils):
    pid, stock = _mostrador(utils)
    _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
              cuerpo={"stockId": stock, "openingCash": 500}, headers=ADMIN | CAJERA)
    # Corregirse antes de vender sí se puede: no se crea una segunda apertura.
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"stockId": stock, "openingCash": 300}, headers=ADMIN | CAJERA)
    assert r["statusCode"] == 201, r["body"]
    assert json.loads(r["body"])["arqueo"]["openingCash"] == 300
    assert len(utils._query_bucket("POS_SHIFT_OPENING")) == 1

    _venta(inventory_lambda, pid, stock)
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"stockId": stock, "openingCash": 900}, headers=ADMIN | CAJERA)
    assert r["statusCode"] == 400
    mensaje = json.loads(r["body"])["message"]
    assert "ya tiene movimientos" in mensaje and "corte de caja" in mensaje


def test_abrir_turno_pide_privilegio_sucursal_y_monto_valido(inventory_lambda, utils):
    _mostrador(utils)
    empleado = {"x-user-id": "nadia", "x-user-role": "employee", "x-user-privileges": "{}"}
    assert _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                     cuerpo={"stockId": "STK-1", "openingCash": 100}, headers=empleado)["statusCode"] == 403

    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"openingCash": 100}, headers=ADMIN | {"x-user-id": "nadia"})
    assert r["statusCode"] == 400 and "gerente" in json.loads(r["body"])["message"]

    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"stockId": "STK-1"}, headers=ADMIN | CAJERA)
    assert r["statusCode"] == 400 and "fondo" in json.loads(r["body"])["message"]

    r = _peticion(inventory_lambda, "POST", "/inventory/pos/turno/abrir",
                  cuerpo={"stockId": "STK-1", "openingCash": -50}, headers=ADMIN | CAJERA)
    assert r["statusCode"] == 400 and "negativo" in json.loads(r["body"])["message"]
