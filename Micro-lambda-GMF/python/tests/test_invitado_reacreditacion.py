"""Lo que se compró como invitado suma al ligar la ficha (paquete G, propuesta 16).

`GET /commissions/associates/<id>/month/2027-03` devolvía `vp=0.0,
netVolume=0.0` para Julio (que pagó $1,209), Mariana ($829) y Aurora ($3,000 en
dos pedidos). Ernesto, que se registró **antes** de comprar, sí tenía `vp=10.0`.
Los pedidos de Aurora traían `linkedToAccountAt` —Gaby les creó ficha— y aun
así su mes seguía en cero.

De ese solo defecto salían cinco cosas que cinco personas reportaron por
separado: *"«Este mes has comprado $0» arriba de «$1,209 Pagada»"* (Julio); los
tres fuera del Cuadro de Honor; *"0 % recompra"* pese a las dos compras de
Aurora (Alma); **la mejor clienta del mes como inactiva**; y el tramo de
descuento por volumen perdido.

Al ligar se corre **solo el paso 1** de `handle_apply_rewards` (volumen, VP,
tramo, activación y reevaluación de bloqueadas). El paso 2 —repartir comisión a
la línea ascendente— no se toca: repartirla otra vez pagaría dos veces por el
mismo pedido.
"""
import json

import pytest

ADMIN = {"x-user-id": "1", "x-user-role": "admin",
         "x-user-privileges": json.dumps({"access_screen_customers": True})}


@pytest.fixture
def mundo(utils):
    import auth_utils, commissions_lambda, customer_lambda
    utils._put_entity("PRODUCT", "P-PROT", {"entityType": "product", "productId": "P-PROT", "name": "Proteína",
                                            "price": 1209, "stock": 30, "isActive": True})
    return auth_utils, commissions_lambda, customer_lambda


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


def _mes(commissions_lambda, cid, utils):
    item = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key())) or {}
    return {"netVolume": float(utils._to_decimal(item.get("netVolume", 0))),
            "netVP": float(utils._to_decimal(item.get("netVP", 0))),
            "isActive": bool(item.get("isActive"))}


def test_al_crear_la_cuenta_lo_comprado_como_invitado_deja_de_valer_cero(mundo, utils):
    """*"«Este mes has comprado $0» arriba de «$1,209 Pagada»"* (`julio-2027-03-02.md`)."""
    auth_utils, commissions_lambda, _ = mundo
    _pedido_invitado(utils, "ORD-JUL1", "julio@test.com", 1209)

    r = auth_utils.handle_create_account({"email": "julio@test.com", "password": "Secreta123",
                                          "name": "Julio Peña"})
    assert r["statusCode"] in (200, 201), r["body"]
    cid = utils._find_customer_id_by_email("julio@test.com")
    assert cid, "la cuenta se creó"

    mes = _mes(commissions_lambda, cid, utils)
    assert mes["netVolume"] == pytest.approx(1209.0), "el volumen del mes seguía en cero"
    assert mes["netVP"] > 0, "los VP seguían en cero"
    # El pedido queda marcado: es lo que impide sumarlo dos veces.
    assert utils._get_by_id("ORDER", "ORD-JUL1").get("rewardsAppliedAt")


def test_ligar_dos_veces_no_suma_dos_veces(mundo, utils):
    """Idempotencia obligatoria: Gaby ya les había creado ficha a las de Aurora."""
    auth_utils, commissions_lambda, _ = mundo
    _pedido_invitado(utils, "ORD-MAR1", "mariana@test.com", 829, nombre="Mariana Ríos")
    auth_utils.handle_create_account({"email": "mariana@test.com", "password": "Secreta123",
                                      "name": "Mariana Ríos"})
    cid = utils._find_customer_id_by_email("mariana@test.com")
    primera = _mes(commissions_lambda, cid, utils)

    auth_utils._vincular_pedidos_de_invitado(cid, "mariana@test.com")
    auth_utils._vincular_pedidos_de_invitado(cid, "mariana@test.com")
    segunda = _mes(commissions_lambda, cid, utils)

    assert segunda["netVolume"] == primera["netVolume"] == pytest.approx(829.0)
    assert segunda["netVP"] == primera["netVP"]


def test_la_ficha_que_crea_la_coach_tambien_reacredita(mundo, utils):
    """Aurora: dos pedidos, $3,000, `linkedToAccountAt` puesto y el mes en cero."""
    auth_utils, commissions_lambda, customer_lambda = mundo
    _pedido_invitado(utils, "ORD-AUR1", "aurora@test.com", 1500, nombre="Aurora Vega")
    _pedido_invitado(utils, "ORD-AUR2", "aurora@test.com", 1500, nombre="Aurora Vega")

    r = customer_lambda.lambda_handler({"httpMethod": "POST", "path": "/customers/seguimiento/ficha-invitado",
                                        "headers": ADMIN, "queryStringParameters": None,
                                        "body": json.dumps({"email": "aurora@test.com"})}, None)
    assert r["statusCode"] == 201, r["body"]
    cid = json.loads(r["body"])["customer"]["customerId"]
    mes = _mes(commissions_lambda, cid, utils)
    assert mes["netVolume"] == pytest.approx(3000.0), "la mejor clienta del mes salía como inactiva"
    assert mes["isActive"] is True


def test_la_reacreditacion_no_reparte_comision_a_la_linea_ascendente(mundo, utils):
    """El paso 2 no se toca: repartir otra vez pagaría dos veces el mismo pedido."""
    auth_utils, commissions_lambda, _ = mundo
    utils._put_entity("CUSTOMER", 500, {"entityType": "customer", "customerId": 500, "name": "Patrocinadora",
                                        "email": "madrina@test.com", "isAssociate": True,
                                        "createdAt": utils._now_iso()})
    pedido = _pedido_invitado(utils, "ORD-LIG1", "ligada@test.com", 1000, nombre="Ligada")
    utils._update_by_id("ORDER", pedido["orderId"], "SET leaderId = :l", {":l": 500})

    auth_utils.handle_create_account({"email": "ligada@test.com", "password": "Secreta123",
                                      "name": "Ligada", "leaderId": 500})
    ledger = utils._get_ledger_month(500, utils._month_key()) or {}
    assert not (ledger.get("ledger") or []), "no se reparte comisión al ligar"


def test_un_pedido_no_pagado_no_se_acredita(mundo, utils):
    auth_utils, commissions_lambda, _ = mundo
    pedido = _pedido_invitado(utils, "ORD-PEND", "pendiente@test.com", 900, nombre="Sin pagar")
    utils._update_by_id("ORDER", "ORD-PEND", "SET #s = :s", {":s": "pending"}, {"#s": "status"})

    auth_utils.handle_create_account({"email": "pendiente@test.com", "password": "Secreta123",
                                      "name": "Sin pagar"})
    cid = utils._find_customer_id_by_email("pendiente@test.com")
    assert _mes(commissions_lambda, cid, utils)["netVolume"] == 0.0


def test_un_pedido_que_ya_habia_acreditado_no_se_vuelve_a_sumar(mundo, utils):
    """El caso de Aurora: `linkedToAccountAt` puesto por una ronda anterior."""
    auth_utils, commissions_lambda, _ = mundo
    _pedido_invitado(utils, "ORD-YA", "ya@test.com", 700, nombre="Ya acreditada")
    utils._update_by_id("ORDER", "ORD-YA", "SET rewardsAppliedAt = :t", {":t": utils._now_iso()})

    auth_utils.handle_create_account({"email": "ya@test.com", "password": "Secreta123", "name": "Ya acreditada"})
    cid = utils._find_customer_id_by_email("ya@test.com")
    assert _mes(commissions_lambda, cid, utils)["netVolume"] == 0.0
