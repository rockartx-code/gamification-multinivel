"""Punto de venta: lo que vive el cajero sin capacitación."""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def inventory_lambda(utils, monkeypatch):
    import inventory_lambda
    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", "arn:sim:sfn")
    return inventory_lambda


def _mostrador(utils, pid=201, stock="STK-1"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("STOCK", stock, {"entityType": "stock", "stockId": stock, "name": "Tienda",
                                       "inventory": {str(pid): 40}})
    return pid, stock


class _SfnFalso:
    def __init__(self, registro):
        self.registro = registro

    def start_execution(self, **kw):
        self.registro.append(json.loads(kw["input"])["action"])


def _venta(inventory_lambda, pid, stock, **extra):
    cuerpo = {"stockId": stock, "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": 1}],
              "paymentMethod": "cash", **extra}
    return inventory_lambda.handle_pos_sale(cuerpo, {"x-user-id": "paco"})


def test_el_corte_de_caja_se_guarda_sin_floats(inventory_lambda, utils):
    """Regresión: el corte respondía 500 ("Float types are not supported")
    y el cajero no podía cerrar su caja."""
    pid, stock = _mostrador(utils)
    r = _venta(inventory_lambda, pid, stock)
    assert r["statusCode"] == 201, r["body"]
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashToKeep": 100}, {"x-user-id": "paco"})
    assert r["statusCode"] == 201, r["body"]
    corte = json.loads(r["body"])["cut"]
    guardado = utils._get_by_id("POS_CASH_CUT", corte["cashCutId"])
    for campo in ("total", "cashToKeep", "withdrawnAmount", "totalWithdrawals"):
        assert isinstance(guardado[campo], Decimal), (campo, type(guardado[campo]))
    assert guardado["total"] == Decimal("480") and guardado["withdrawnAmount"] == Decimal("380")


def test_la_venta_de_mostrador_a_un_socio_activa_y_comisiona(inventory_lambda, utils, monkeypatch):
    """Regresión: la venta POS creaba un pedido ya entregado y solo disparaba
    ORDER_DELIVERED; el socio que compraba en tienda física no acumulaba
    volumen ni VP y su patrocinador no cobraba."""
    pid, stock = _mostrador(utils)
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55, "name": "Rodrigo"})
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    r = _venta(inventory_lambda, pid, stock, customerId=55, customerName="Rodrigo")
    assert r["statusCode"] == 201, r["body"]
    assert disparos == ["ORDER_PAID", "ORDER_DELIVERED"]
    pedido = utils._get_by_id("ORDER", json.loads(r["body"])["orderId"])
    assert pedido["items"][0]["vpPoints"] == 10  # puntos del catálogo, como en la tienda en línea


def test_la_venta_a_publico_en_general_no_activa_a_nadie(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    r = _venta(inventory_lambda, pid, stock)
    assert r["statusCode"] == 201, r["body"]
    assert disparos == ["ORDER_DELIVERED"]


def test_ligar_una_venta_a_un_cliente_le_avisa_por_correo(inventory_lambda, utils, monkeypatch):
    pid, stock = _mostrador(utils)
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55, "name": "Rodrigo", "email": "r@test.com"})
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto)))
    r = _venta(inventory_lambda, pid, stock, customerId=55, customerName="Rodrigo")
    assert r["statusCode"] == 201, r["body"]
    assert enviados and enviados[0][0] == "r@test.com" and "a tu nombre" in enviados[0][1]


def test_anular_una_venta_regresa_inventario_y_cancela_el_pedido(inventory_lambda, utils, monkeypatch):
    """Rodrigo: "aparece POS-B68ED084 a mi nombre y yo no compré nada"; no
    existía forma de quitarla."""
    pid, stock = _mostrador(utils)
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55, "name": "Rodrigo", "email": "r@test.com"})
    disparos = []
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso(disparos))
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append(asunto))
    r = _venta(inventory_lambda, pid, stock, customerId=55, customerName="Rodrigo")
    sale_id = json.loads(r["body"])["saleId"]; oid = json.loads(r["body"])["orderId"]
    assert utils._get_by_id("STOCK", stock)["inventory"][str(pid)] == 39

    r = inventory_lambda.lambda_handler({"httpMethod": "POST", "path": f"/inventory/pos/sales/{sale_id}/void",
                                         "headers": {"x-user-id": "sofia"}, "body": json.dumps({"reason": "el cliente no la reconoce"})}, None)
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("STOCK", stock)["inventory"][str(pid)] == 40
    assert utils._get_by_id("POS_SALE", sale_id)["status"] == "voided"
    assert utils._get_by_id("ORDER", oid)["status"] == "cancelled"
    assert disparos[-1] == "ORDER_CANCELLED"
    assert any("Anulamos" in a for a in enviados)
    # Segunda anulación: ya está.
    r = inventory_lambda.lambda_handler({"httpMethod": "POST", "path": f"/inventory/pos/sales/{sale_id}/void",
                                         "headers": {"x-user-id": "sofia"}, "body": "{}"}, None)
    assert r["statusCode"] == 409


def test_el_retiro_de_efectivo_se_guarda_sin_floats(inventory_lambda, utils, monkeypatch):
    """Regresión: "Internal Inventory Error" al retirar $400 para la paquetería."""
    pid, stock = _mostrador(utils)
    monkeypatch.setattr(inventory_lambda, "sfn", _SfnFalso([]))
    # Código real (no un doble): así la pantalla puede distinguir "no hay código
    # configurado" de "código incorrecto", que es la propuesta 6.
    utils._put_entity("CONFIG", "pos-auth-v1", {"entityType": "config", "configId": "pos-auth-v1",
                                                "posAuthCode": "2468"})
    _venta(inventory_lambda, pid, stock)
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 400, "reason": "paquetería", "authCode": "2468"}, {"x-user-id": "paco"})
    assert r["statusCode"] == 201, r["body"]
    wid = json.loads(r["body"])["withdrawal"]["withdrawalId"]
    assert isinstance(utils._get_by_id("POS_WITHDRAWAL", wid)["amount"], Decimal)


def test_recibir_una_transferencia_con_faltante_registra_la_merma(inventory_lambda, utils, monkeypatch):
    """Beto contó 4 de 5 colágenos y solo podía confirmar 5 o nada."""
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    utils._put_entity("PRODUCT", 7, {"entityType": "product", "productId": 7, "name": "Colageno", "price": 700, "vpPoints": 13, "active": True})
    utils._put_entity("STOCK", "STK-A", {"entityType": "stock", "stockId": "STK-A", "name": "Bodega", "inventory": {"7": 30}})
    utils._put_entity("STOCK", "STK-B", {"entityType": "stock", "stockId": "STK-B", "name": "Tienda", "inventory": {}})
    r = inventory_lambda.handle_transfers("POST", {"sourceStockId": "STK-A", "destinationStockId": "STK-B", "lines": [{"productId": 7, "qty": 5}]}, {})
    assert r["statusCode"] in (200, 201), r["body"]
    tid = json.loads(r["body"])["transfer"]["transferId"]
    assert utils._get_by_id("STOCK", "STK-A")["inventory"]["7"] == 25

    r = inventory_lambda.lambda_handler({"httpMethod": "POST", "path": f"/inventory/stocks/transfers/{tid}/receive",
                                         "headers": {"x-user-id": "beto"}, "body": json.dumps({"received": {"7": 4}})}, None)
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("STOCK", "STK-B")["inventory"]["7"] == 4
    trf = utils._get_by_id("STOCK_TRANSFER", tid)
    assert trf["status"] == "received" and trf["discrepancies"][0]["missing"] == 1
    mermas = [m for m in utils._query_bucket("INVENTORY_MOVEMENT") if m.get("type") == "damage" and m.get("stockId") == "STK-A"]
    assert mermas and mermas[-1]["quantity"] == 1 if "quantity" in mermas[-1] else mermas[-1].get("qty") == 1


def test_abonar_el_saldo_de_una_venta_parcial(inventory_lambda, utils):
    """Regresión: una venta con pago parcial no tenía forma de liquidarse después;
    el saldo solo se veía al cobrar. El abono entra a caja como un cobro más."""
    from decimal import Decimal
    utils._put_entity("POS_SALE", "SALE-P1", {"entityType": "posSale", "saleId": "SALE-P1", "orderId": "POS-P1", "stockId": "STK-1",
                                              "attendantUserId": "9", "customerId": 5, "customerName": "Roberto", "total": Decimal("840"),
                                              "paymentType": "partial", "amountPaid": Decimal("500"), "pendingAmount": Decimal("340"),
                                              "paymentStatus": "partial", "paymentMethod": "cash", "lines": [], "createdAt": utils._now_iso()})
    h = {"Authorization": "Bearer sim-superadmin-token"}
    r = inventory_lambda.handle_settle_pos_sale("SALE-P1", {"amount": 400, "paymentMethod": "card"}, h)
    assert r["statusCode"] == 400
    r = inventory_lambda.handle_settle_pos_sale("SALE-P1", {"amount": 340, "paymentMethod": "card"}, h)
    assert r["statusCode"] == 200, r["body"]
    venta = utils._get_by_id("POS_SALE", "SALE-P1")
    assert Decimal(str(venta["pendingAmount"])) == Decimal("0") and venta["paymentStatus"] == "paid" and len(venta["payments"]) == 1
    abonos = [v for (pk, sk), v in utils._table.store.items() if pk.startswith("POS_SALE") and v.get("source") == "settlement"]
    assert len(abonos) == 1 and Decimal(str(abonos[0]["amountPaid"])) == Decimal("340") and abonos[0]["orderId"] == "POS-P1"
    assert inventory_lambda.handle_settle_pos_sale("SALE-P1", {"amount": 10}, h)["statusCode"] == 409
