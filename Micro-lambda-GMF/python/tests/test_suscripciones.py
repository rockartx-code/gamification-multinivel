"""Suscripción mensual: "recibe esto cada mes" (paquete H, propuesta 14).

Bety, Rosa y Patricia recompran lo mismo cada mes y su activación dependía de
acordarse del día 20 (docs/qa/22 §6 tarea 8). El día indicado el sistema crea
el pedido con el tramo real, genera el enlace de pago y lo manda por correo.
"""
import json
from datetime import date
from decimal import Decimal

import pytest

CID = 555
SOCIA = {"x-user-id": str(CID), "x-user-role": "cliente"}
OTRA = {"x-user-id": "999", "x-user-role": "cliente"}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
EMPLEADO_SIN_PERMISO = {"x-user-id": "2", "x-user-role": "employee", "x-user-privileges": json.dumps({"access_screen_orders": True})}


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, html)))
    return enviados


class _Respuesta:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def pasarela(monkeypatch):
    """Doble del checkout de MercadoPago: devuelve el enlace de pago del pedido."""
    import urllib.request
    preferencias = []

    def urlopen(req, *a, **k):
        pref = json.loads(req.data.decode())
        preferencias.append(pref)
        oid = pref["external_reference"]
        return _Respuesta({"id": f"pref-{oid}", "init_point": f"https://mp.test/pagar/{oid}"})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return preferencias


@pytest.fixture
def mundo(utils):
    utils._put_entity("CUSTOMER", CID, {
        "entityType": "customer", "customerId": CID, "name": "Bety", "email": "bety@test.com", "phone": "3311112222",
        "addresses": [{"addressId": "addr-1", "label": "Casa", "street": "Av. Vallarta", "number": "100",
                       "address": "Av. Vallarta 100", "city": "Guadalajara", "state": "Jalisco", "postalCode": "44100",
                       "country": "MX", "isDefault": True}],
    })
    utils._put_entity("PRODUCT", 101, {"entityType": "product", "productId": 101, "name": "Naplus", "price": 400, "vpPoints": 8, "active": True})
    utils._put_entity("PRODUCT", 102, {"entityType": "product", "productId": 102, "name": "Magnesio", "price": 350, "vpPoints": 7, "active": True})
    utils._put_entity("PRODUCT", 103, {"entityType": "product", "productId": 103, "name": "Descontinuado", "price": 100, "vpPoints": 1, "active": False})
    utils._put_entity("STOCK", "suc-1", {"entityType": "stock", "stockId": "suc-1", "name": "Del Valle", "location": "CDMX", "allowPickup": True, "inventory": {}})
    return CID


def _llamar(order_lambda, metodo, ruta, cuerpo=None, headers=SOCIA, query=None):
    evento = {"httpMethod": metodo, "path": ruta, "headers": headers, "body": json.dumps(cuerpo or {}),
              "queryStringParameters": query}
    r = order_lambda.lambda_handler(evento, None)
    return r["statusCode"], json.loads(r["body"] or "{}")


def _alta(dia=20, **extra):
    return {"items": [{"productId": 101, "quantity": 2}, {"productId": 102, "quantity": 1}], "dayOfMonth": dia,
            "deliveryType": "delivery", "shippingAddressId": "addr-1", **extra}


def _crear(order_lambda, **extra):
    estado, cuerpo = _llamar(order_lambda, "POST", "/orders/suscripciones", _alta(**extra))
    assert estado == 201, cuerpo
    return cuerpo["subscription"]


def test_crear_guarda_la_suscripcion_y_avisa_por_correo(order_lambda, mundo, buzon):
    sub = _crear(order_lambda)
    assert sub["subscriptionId"].startswith("SUS-") and sub["status"] == "active" and sub["dayOfMonth"] == 20
    assert [i["name"] for i in sub["items"]] == ["Naplus", "Magnesio"] and sub["items"][0]["quantity"] == 2
    assert sub["shippingAddress"]["postalCode"] == "44100" and sub["shippingAddressId"] == "addr-1"
    proximo = date.fromisoformat(sub["nextRunDate"])
    assert proximo.day == 20 and proximo > date.today()
    assert len(buzon) == 1 and buzon[0][0] == "bety@test.com" and "quedó guardada" in buzon[0][1]
    assert "2 × Naplus" in buzon[0][2] and "pausarla o cancelarla" in buzon[0][2]

    estado, cuerpo = _llamar(order_lambda, "GET", "/orders/suscripciones")
    assert estado == 200 and [s["subscriptionId"] for s in cuerpo["subscriptions"]] == [sub["subscriptionId"]]


@pytest.mark.parametrize("cuerpo, fragmento", [
    (_alta(dia=29), "entre 1 y 28"),
    (_alta(dia=0), "entre 1 y 28"),
    ({**_alta(), "items": []}, "al menos un producto"),
    ({**_alta(), "items": [{"productId": 103, "quantity": 1}]}, "ya no está disponible"),
    ({**_alta(), "items": [{"productId": 101, "quantity": 0}]}, "mayor a cero"),
    ({**_alta(), "shippingAddressId": "addr-x"}, "direcciones guardadas"),
    ({**_alta(), "deliveryType": "pickup", "pickupStockId": "suc-sin-pickup"}, "sucursal"),
])
def test_rechaza_altas_invalidas(order_lambda, mundo, buzon, cuerpo, fragmento):
    estado, respuesta = _llamar(order_lambda, "POST", "/orders/suscripciones", cuerpo)
    assert estado == 400 and fragmento in respuesta["message"], respuesta
    assert buzon == []


def test_sin_sesion_responde_401_y_otra_socia_no_puede_tocarla(order_lambda, mundo, buzon):
    estado, _ = _llamar(order_lambda, "GET", "/orders/suscripciones", headers={})
    assert estado == 401
    estado, _ = _llamar(order_lambda, "POST", "/orders/suscripciones", _alta(), headers={})
    assert estado == 401
    sub = _crear(order_lambda)
    sid = sub["subscriptionId"]
    for metodo in ("PATCH", "DELETE"):
        estado, _ = _llamar(order_lambda, metodo, f"/orders/suscripciones/{sid}", {"status": "paused"}, headers=OTRA)
        assert estado == 403, metodo
    estado, _ = _llamar(order_lambda, "PATCH", "/orders/suscripciones/SUS-NOEXISTE", {"status": "paused"})
    assert estado == 404


def test_pausar_reanudar_y_cancelar(order_lambda, mundo, buzon):
    sub = _crear(order_lambda)
    sid, proximo = sub["subscriptionId"], date.fromisoformat(sub["nextRunDate"])

    estado, cuerpo = _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}", {"status": "paused"})
    pausada = cuerpo["subscription"]
    assert estado == 200 and pausada["status"] == "paused"
    hasta = date.fromisoformat(pausada["pausedUntil"])
    assert hasta > proximo and hasta.day == 20, "pausar un mes salta el próximo pedido"
    assert date.fromisoformat(pausada["nextRunDate"]) >= hasta
    assert "Pausamos" in buzon[-1][1]

    estado, cuerpo = _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}", {"status": "active"})
    assert estado == 200 and cuerpo["subscription"]["status"] == "active" and cuerpo["subscription"]["pausedUntil"] is None
    assert cuerpo["subscription"]["nextRunDate"] == sub["nextRunDate"]
    assert "vuelve a estar activa" in buzon[-1][1]

    estado, cuerpo = _llamar(order_lambda, "DELETE", f"/orders/suscripciones/{sid}")
    assert estado == 200 and cuerpo["subscription"]["status"] == "cancelled" and cuerpo["subscription"]["nextRunDate"] is None
    assert "Cancelamos" in buzon[-1][1]
    estado, cuerpo = _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}", {"dayOfMonth": 5})
    assert estado == 409
    assert len(buzon) == 4   # alta, pausa, reanudación, cancelación


def test_editar_productos_y_dia(order_lambda, mundo, buzon):
    sub = _crear(order_lambda)
    sid = sub["subscriptionId"]
    estado, cuerpo = _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}",
                             {"items": [{"productId": 102, "quantity": 3}], "dayOfMonth": 5,
                              "deliveryType": "pickup", "pickupStockId": "suc-1"})
    assert estado == 200, cuerpo
    editada = cuerpo["subscription"]
    assert editada["items"] == [{"productId": 102, "name": "Magnesio", "quantity": 3, "price": 350, "vpPoints": 7}]
    assert editada["dayOfMonth"] == 5 and date.fromisoformat(editada["nextRunDate"]).day == 5
    assert editada["deliveryType"] == "pickup" and editada["pickupStockId"] == "suc-1" and editada["pickupStockName"] == "Del Valle"
    assert "Actualizamos" in buzon[-1][1] and "3 × Magnesio" in buzon[-1][2]
    estado, cuerpo = _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}", {"dayOfMonth": 31})
    assert estado == 400


def _generar(order_lambda, fecha, headers=ADMIN, dry_run=False):
    return _llamar(order_lambda, "POST", "/orders/suscripciones/generar", {"date": fecha, "dryRun": dry_run}, headers=headers)


def test_el_dia_indicado_crea_el_pedido_con_el_tramo_real_y_manda_el_enlace(order_lambda, utils, mundo, buzon, pasarela):
    # Bety ya lleva $500 de MPN este mes: con los $1,150 del pedido el tramo es 10 %.
    utils._increment_associate_month_net_volume(CID, utils._month_key(), Decimal("500"))
    sub = _crear(order_lambda)
    dia = sub["nextRunDate"]

    estado, cuerpo = _generar(order_lambda, dia)
    assert estado == 200, cuerpo
    assert len(cuerpo["generated"]) == 1 and cuerpo["skipped"] == []
    generado = cuerpo["generated"][0]
    oid = generado["orderId"]
    assert generado["subscriptionId"] == sub["subscriptionId"] and generado["initPoint"] == f"https://mp.test/pagar/{oid}"

    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["customerId"] == CID and pedido["buyerType"] == "associate" and pedido["status"] == "pending"
    assert pedido["subscriptionId"] == sub["subscriptionId"]
    assert pedido["grossSubtotal"] == Decimal("1150") and pedido["discountRate"] == Decimal("0.10")
    assert pedido["netTotal"] == Decimal("1035.00") and pedido["shippingCarrier"] == "por confirmar"
    # Integrado con C: la tarifa base shipping.baseRateMxn ($129) se cobra en el pedido de suscripción.
    assert pedido["shippingCost"] == Decimal("129") and pedido["total"] == Decimal("1164.00")
    assert pedido["shippingAddress"]["postalCode"] == "44100" and pedido["email"] == "bety@test.com"
    assert pedido["paymentPreferenceId"] == f"pref-{oid}"

    correo = buzon[-1]
    assert correo[0] == "bety@test.com" and "paga aquí" in correo[1] and oid in correo[1]
    assert f"https://mp.test/pagar/{oid}" in correo[2] and "$1,164.00" in correo[2] and "10 %" in correo[2]

    actualizada = utils._get_by_id("SUBSCRIPTION", sub["subscriptionId"])
    assert actualizada["lastRunDate"] == dia and actualizada["lastOrderId"] == oid
    siguiente = date.fromisoformat(actualizada["nextRunDate"])
    assert siguiente > date.fromisoformat(dia) and siguiente.day == 20


def test_no_duplica_el_pedido_el_mismo_dia_ni_antes_de_la_fecha(order_lambda, utils, mundo, buzon, pasarela):
    sub = _crear(order_lambda)
    dia = date.fromisoformat(sub["nextRunDate"])
    correos = len(buzon)

    estado, cuerpo = _generar(order_lambda, (dia.replace(day=19)).isoformat())
    assert cuerpo["generated"] == [] and cuerpo["skipped"][0]["reason"] == "not_due"

    _generar(order_lambda, dia.isoformat())
    estado, cuerpo = _generar(order_lambda, dia.isoformat())
    assert cuerpo["generated"] == [] and cuerpo["skipped"][0]["reason"] == "already_generated_today"
    pedidos = [v for (pk, sk), v in utils._table.store.items() if pk == "ORDER"]
    assert len(pedidos) == 1 and len(pasarela) == 1 and len(buzon) == correos + 1


def test_una_pausada_no_genera_y_al_vencer_la_pausa_vuelve_a_activa(order_lambda, utils, mundo, buzon, pasarela):
    sub = _crear(order_lambda)
    sid = sub["subscriptionId"]
    _llamar(order_lambda, "PATCH", f"/orders/suscripciones/{sid}", {"status": "paused"})
    pausada = utils._get_by_id("SUBSCRIPTION", sid)

    estado, cuerpo = _generar(order_lambda, sub["nextRunDate"])
    assert cuerpo["generated"] == [] and cuerpo["skipped"] == [{"subscriptionId": sid, "reason": "paused"}]

    estado, cuerpo = _generar(order_lambda, pausada["nextRunDate"])
    assert len(cuerpo["generated"]) == 1, cuerpo
    assert utils._get_by_id("SUBSCRIPTION", sid)["status"] == "active"


def test_una_cancelada_no_genera(order_lambda, mundo, buzon, pasarela):
    sub = _crear(order_lambda)
    _llamar(order_lambda, "DELETE", f"/orders/suscripciones/{sub['subscriptionId']}")
    estado, cuerpo = _generar(order_lambda, sub["nextRunDate"])
    assert cuerpo["generated"] == [] and cuerpo["skipped"][0]["reason"] == "cancelled" and len(pasarela) == 0


def test_dry_run_dice_que_generaria_sin_crear_nada(order_lambda, utils, mundo, buzon, pasarela):
    sub = _crear(order_lambda)
    correos = len(buzon)
    estado, cuerpo = _generar(order_lambda, sub["nextRunDate"], dry_run=True)
    assert estado == 200 and cuerpo["generated"][0]["dryRun"] is True and cuerpo["generated"][0]["orderId"] is None
    assert [v for (pk, sk), v in utils._table.store.items() if pk == "ORDER"] == [] and len(buzon) == correos
    assert utils._get_by_id("SUBSCRIPTION", sub["subscriptionId"])["lastRunDate"] is None


def test_generar_exige_order_create_o_superadmin(order_lambda, mundo, buzon, pasarela, monkeypatch):
    sub = _crear(order_lambda)
    estado, cuerpo = _generar(order_lambda, sub["nextRunDate"], headers=EMPLEADO_SIN_PERMISO)
    assert estado == 403 and "order_create" in cuerpo["message"]
    estado, _ = _generar(order_lambda, sub["nextRunDate"], headers=SOCIA)
    assert estado == 403
    from core import security
    monkeypatch.setattr(security, "_SUPERADMIN_TOKEN", "token-maestro")
    estado, cuerpo = _generar(order_lambda, sub["nextRunDate"], headers={"authorization": "Bearer token-maestro"})
    assert estado == 200 and len(cuerpo["generated"]) == 1
    assert ("POST", "/orders/suscripciones/generar") in order_lambda.TAREAS_PROGRAMADAS


def test_un_producto_retirado_del_catalogo_no_genera_pero_no_rompe_a_las_demas(order_lambda, utils, mundo, buzon, pasarela):
    sub_a = _crear(order_lambda)
    sub_b = _crear(order_lambda)
    utils._update_by_id("PRODUCT", 102, "SET active = :a", {":a": False})
    utils._update_by_id("SUBSCRIPTION", sub_a["subscriptionId"], "SET items = :i",
                        {":i": [{"productId": 101, "name": "Naplus", "quantity": 1, "price": Decimal("400"), "vpPoints": Decimal("8")}]})
    estado, cuerpo = _generar(order_lambda, sub_a["nextRunDate"])
    assert [g["subscriptionId"] for g in cuerpo["generated"]] == [sub_a["subscriptionId"]]
    assert cuerpo["skipped"] == [{"subscriptionId": sub_b["subscriptionId"], "reason": "product_inactive",
                                  "detail": "El producto Magnesio ya no está disponible"}]


def test_el_admin_puede_ver_las_suscripciones_de_una_clienta(order_lambda, mundo, buzon):
    sub = _crear(order_lambda)
    estado, cuerpo = _llamar(order_lambda, "GET", "/orders/suscripciones", headers=ADMIN, query={"customerId": str(CID)})
    assert estado == 200 and cuerpo["subscriptions"][0]["subscriptionId"] == sub["subscriptionId"]
    estado, cuerpo = _llamar(order_lambda, "GET", f"/orders/suscripciones/{sub['subscriptionId']}", headers=OTRA)
    assert estado == 403
