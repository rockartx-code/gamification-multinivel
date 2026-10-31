"""Guarda 4 (docs/qa/27 §4): lo comprado como invitado cuenta al ligar la ficha.

$5,038 pagados por tres clientes y el mes en cero. Julio pagó $1,209, Mariana
$829 y Aurora $3,000 en dos pedidos; los tres compraron sin cuenta y después
alguien les creó ficha (o se registraron con el mismo correo). El mes contable
seguía en `vp=0.0, netVolume=0.0`, y de ahí salían cinco síntomas distintos: el
*"Este mes has comprado $0"* encima de *"$1,209 Pagada"*, los tres fuera del
Cuadro de Honor, el *"0 % recompra"* de Alma, la mejor clienta del mes marcada
como inactiva y el tramo de descuento por volumen perdido.

Estas tres pruebas fijan las tres puertas por las que entra una ficha nueva
—registro propio, ficha creada por la coach, ligado repetido— y que el Cuadro
de Honor los vea desde la primera.
"""
import json

import pytest

ADMIN = {"x-user-id": "1", "x-user-role": "admin",
         "x-user-privileges": json.dumps({"access_screen_customers": True,
                                          "access_screen_honor_board": True})}


@pytest.fixture
def mundo(utils):
    import auth_utils, commissions_lambda, customer_lambda, dashboard_lambda
    utils._put_entity("PRODUCT", "P-PROT", {"entityType": "product", "productId": "P-PROT", "name": "Proteína",
                                            "price": 1000, "vpPoints": 10, "stock": 300, "isActive": True})
    return auth_utils, commissions_lambda, customer_lambda, dashboard_lambda


def _pedido_invitado(utils, oid, correo, total, *, nombre="Julio Peña"):
    order = {"entityType": "order", "orderId": oid, "customerId": None, "buyerType": "guest",
             "customerName": nombre, "email": correo, "phone": "5544332211",
             "status": "paid", "total": total, "netTotal": total, "grossTotal": total,
             "monthKey": utils._month_key(), "paidAt": utils._now_iso(),
             "items": [{"productId": "P-PROT", "name": "Proteína", "quantity": 1,
                        "price": total, "unitPrice": total, "subtotal": total}],
             "createdAt": utils._now_iso()}
    utils._put_entity("ORDER", oid, order)
    return order


def _mes(utils, cid):
    item = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key())) or {}
    return {"netVolume": float(utils._to_decimal(item.get("netVolume", 0))),
            "netVP": float(utils._to_decimal(item.get("netVP", 0))),
            "isActive": bool(item.get("isActive"))}


def _honor(dashboard_lambda):
    r = dashboard_lambda.get_honor_board()
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    return {e["name"]: e for e in cuerpo["byVp"]}, {e["name"]: e for e in cuerpo["byVg"]}


def test_registrarse_con_un_correo_que_ya_compro_recalcula_el_mes(mundo, utils):
    """Julio: *"«Este mes has comprado $0» arriba de «$1,209 Pagada»"*."""
    auth_utils, _, _, _ = mundo
    _pedido_invitado(utils, "ORD-JUL1", "julio@test.com", 1209)

    r = auth_utils.handle_create_account({"email": "julio@test.com", "password": "Secreta123",
                                         "name": "Julio Peña"})
    assert r["statusCode"] in (200, 201), r["body"]
    cid = utils._find_customer_id_by_email("julio@test.com")
    assert cid, "la cuenta se creó"

    mes = _mes(utils, cid)
    assert mes["netVolume"] == pytest.approx(1209.0), "el volumen del mes se quedaba en cero"
    assert mes["netVP"] > 0, "los VP se quedaban en cero"
    # El pedido queda marcado: es lo único que impide sumarlo dos veces.
    assert utils._get_by_id("ORDER", "ORD-JUL1").get("rewardsAppliedAt")

    # Y volver a ligar (la coach ya le había creado ficha a alguna) no duplica.
    auth_utils._vincular_pedidos_de_invitado(cid, "julio@test.com")
    auth_utils._vincular_pedidos_de_invitado(cid, "julio@test.com")
    assert _mes(utils, cid)["netVolume"] == pytest.approx(1209.0)


def test_ligar_la_ficha_desde_el_back_office_activa_el_mes(mundo, utils):
    """Aurora: dos pedidos, $3,000, ficha creada por Gaby… y "inactiva".

    Era *la mejor clienta del mes* saliendo como inactiva en la pantalla de la
    coach, con el tramo de descuento por volumen perdido de paso.
    """
    _, _, customer_lambda, _ = mundo
    _pedido_invitado(utils, "ORD-AUR1", "aurora@test.com", 1500, nombre="Aurora Vega")
    _pedido_invitado(utils, "ORD-AUR2", "aurora@test.com", 1500, nombre="Aurora Vega")

    r = customer_lambda.lambda_handler({"httpMethod": "POST", "path": "/customers/seguimiento/ficha-invitado",
                                        "headers": ADMIN, "queryStringParameters": None,
                                        "body": json.dumps({"email": "aurora@test.com"})}, None)
    assert r["statusCode"] == 201, r["body"]
    cid = json.loads(r["body"])["customer"]["customerId"]

    mes = _mes(utils, cid)
    assert mes["netVolume"] == pytest.approx(3000.0), "los dos pedidos entran, no solo el último"
    assert mes["netVP"] > 0
    assert mes["isActive"] is True, "la mejor clienta del mes salía como inactiva"


def test_el_cuadro_de_honor_incluye_a_quien_compro_como_invitado(mundo, utils):
    """Los tres estaban fuera del Cuadro de Honor con $5,038 pagados entre ellos.

    Que el mes contable se recalcule no basta: el ranking lee VP y VG por su
    cuenta, y es la pantalla donde se notaba la ausencia.
    """
    auth_utils, _, customer_lambda, dashboard_lambda = mundo
    _pedido_invitado(utils, "ORD-JUL1", "julio@test.com", 1209, nombre="Julio Peña")
    _pedido_invitado(utils, "ORD-MAR1", "mariana@test.com", 829, nombre="Mariana Ríos")
    _pedido_invitado(utils, "ORD-AUR1", "aurora@test.com", 1500, nombre="Aurora Vega")
    _pedido_invitado(utils, "ORD-AUR2", "aurora@test.com", 1500, nombre="Aurora Vega")

    # Antes de ligar nada, el cuadro está vacío: nadie tiene cuenta todavía.
    por_vp, _ = _honor(dashboard_lambda)
    assert por_vp == {}

    auth_utils.handle_create_account({"email": "julio@test.com", "password": "Secreta123", "name": "Julio Peña"})
    auth_utils.handle_create_account({"email": "mariana@test.com", "password": "Secreta123", "name": "Mariana Ríos"})
    r = customer_lambda.lambda_handler({"httpMethod": "POST", "path": "/customers/seguimiento/ficha-invitado",
                                        "headers": ADMIN, "queryStringParameters": None,
                                        "body": json.dumps({"email": "aurora@test.com"})}, None)
    assert r["statusCode"] == 201, r["body"]

    por_vp, por_vg = _honor(dashboard_lambda)
    assert set(por_vp) == {"Julio Peña", "Mariana Ríos", "Aurora Vega"}, "los tres estaban fuera del cuadro"
    assert all(e["vp"] > 0 for e in por_vp.values())
    # Aurora, con $3,000, encabeza; el orden es el de los VP, no el del alta.
    assert por_vp["Aurora Vega"]["position"] == 1
    assert por_vp["Aurora Vega"]["vp"] > por_vp["Julio Peña"]["vp"] > por_vp["Mariana Ríos"]["vp"]
    assert por_vg["Aurora Vega"]["vg"] >= por_vg["Aurora Vega"]["vp"]
