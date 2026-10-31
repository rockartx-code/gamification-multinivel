"""Ficha unificada (paquete F, propuesta 19).

Compradores invitados y registrados con la misma ficha (origen, preferencia de
contacto, ejecutiva asignada), y la coach visible en el panel de quien no
tiene patrocinadora: "Yo le compré a Finding'U, no a Marcela".
"""
import json

import pytest

IVONNE = 900
COACH = {"x-user-id": str(IVONNE), "x-user-role": "employee", "x-user-name": "Ivonne Castro",
         "x-user-privileges": json.dumps({"access_screen_customers": True})}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
SIN_PRIVILEGIO = {"x-user-id": "77", "x-user-role": "employee", "x-user-privileges": "{}"}


@pytest.fixture
def modulos(utils):
    import customer_lambda, dashboard_common
    utils._put_entity("EMPLOYEE", IVONNE, {"entityType": "employee", "employeeId": IVONNE, "name": "Ivonne Castro",
                                           "email": "ivonne@findingu.com.mx", "phone": "55 5111 2222", "active": True})
    utils._put_entity("EMPLOYEE", 902, {"entityType": "employee", "employeeId": 902, "name": "Ex empleada",
                                        "email": "ex@findingu.com.mx", "phone": "5500000000", "active": False})
    for oid, dias in (("ORD-HEC1", "2026-07-01T10:00:00Z"), ("ORD-HEC2", "2026-08-02T10:00:00Z")):
        utils._put_entity("ORDER", oid, {"entityType": "order", "orderId": oid, "customerId": None, "buyerType": "guest",
                                         "customerName": "Héctor Mora", "email": "hector@test.com", "phone": "5599887766",
                                         "city": "Querétaro", "status": "delivered", "total": 500, "createdAt": dias}, created_at_iso=dias)
    return customer_lambda, dashboard_common


def _post(customer_lambda, ruta, body, headers=COACH):
    return customer_lambda.lambda_handler({"httpMethod": "POST", "path": ruta, "headers": headers,
                                           "queryStringParameters": None, "body": json.dumps(body)}, None)


def test_crear_ficha_de_invitado_liga_sus_pedidos_y_no_le_abre_acceso(modulos, utils):
    customer_lambda, _ = modulos
    # Una nota tomada cuando aún era invitado viaja a la ficha nueva.
    _post(customer_lambda, "/customers/invitado/contacto", {"channel": "whatsapp", "templateKey": "fria", "message": "Hola Héctor", "guestEmail": "hector@test.com"})

    r = _post(customer_lambda, "/customers/seguimiento/ficha-invitado", {"email": "hector@test.com"})
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    ficha = cuerpo["customer"]
    assert ficha["name"] == "Héctor Mora" and ficha["email"] == "hector@test.com" and ficha["phone"] == "5599887766"
    assert ficha["mode"] == "cliente" and ficha["origin"] == "invitado" and ficha["isAssociate"] is False
    assert ficha["contactPreference"] == "whatsapp" and ficha["canAccessAdmin"] is False
    assert ficha["contactNotes"][0]["templateKey"] == "fria"
    assert ficha["createdAt"] == "2026-07-01T10:00:00Z", "la antigüedad es la de su primera compra"
    assert sorted(cuerpo["linkedOrders"]) == ["ORD-HEC1", "ORD-HEC2"]

    cid = ficha["customerId"]
    for oid in ("ORD-HEC1", "ORD-HEC2"):
        pedido = utils._get_by_id("ORDER", oid)
        assert str(pedido["customerId"]) == str(cid) and pedido["buyerType"] == "guest"
    assert utils._get_by_id("AUTH", "hector@test.com") is None, "sin acceso: se registra después si quiere"
    assert str(utils._find_customer_id_by_email("hector@test.com")) == str(cid)

    # Ya no aparece como invitado en la lista, sino como cliente con ficha.
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/hoy", "headers": ADMIN,
                                        "queryStringParameters": {"scope": "all"}, "body": ""}, None)
    filas = [f for f in json.loads(r["body"])["rows"] if f["email"] == "hector@test.com"]
    assert len(filas) == 1 and filas[0]["isGuest"] is False and filas[0]["mode"] == "cliente"
    assert filas[0]["lastOrder"]["id"] == "ORD-HEC2"

    # Segunda vez: ya existe.
    r = _post(customer_lambda, "/customers/seguimiento/ficha-invitado", {"email": "hector@test.com"})
    assert r["statusCode"] == 409 and json.loads(r["body"])["customerId"] == str(cid)


def test_crear_ficha_valida_correo_pedidos_y_privilegio(modulos):
    customer_lambda, _ = modulos
    assert _post(customer_lambda, "/customers/seguimiento/ficha-invitado", {})["statusCode"] == 400
    assert _post(customer_lambda, "/customers/seguimiento/ficha-invitado", {"email": "nadie@test.com"})["statusCode"] == 404
    assert _post(customer_lambda, "/customers/seguimiento/ficha-invitado", {"email": "hector@test.com"}, headers=SIN_PRIVILEGIO)["statusCode"] == 403


def test_la_ficha_guarda_preferencia_de_contacto_y_ejecutiva(modulos, utils, monkeypatch):
    customer_lambda, _ = modulos
    monkeypatch.setattr(utils, "_require_self_or_admin_from_bearer", lambda *a, **k: None)
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz", "createdAt": utils._now_iso()})

    r = customer_lambda.handle_update_customer(11, {"contactPreference": "whatsapp", "executiveId": str(IVONNE)}, ADMIN)
    assert r["statusCode"] == 200, r["body"]
    ficha = json.loads(r["body"])["customer"]
    assert ficha["contactPreference"] == "whatsapp" and ficha["executiveId"] == str(IVONNE)

    # La lista nombra a la ejecutiva y respeta la preferencia.
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/hoy", "headers": COACH,
                                        "queryStringParameters": None, "body": ""}, None)
    rosa = [f for f in json.loads(r["body"])["rows"] if f["name"] == "Rosa Elena Ortiz"][0]
    assert rosa["situation"] == "bienvenida", "recién registrada y sin compra"
    assert rosa["executiveName"] == "Ivonne Castro" and rosa["contactPreference"] == "whatsapp"

    # Quitar la ejecutiva: cadena vacía.
    r = customer_lambda.handle_update_customer(11, {"executiveId": ""}, ADMIN)
    assert json.loads(r["body"])["customer"]["executiveId"] == ""


def test_la_ficha_rechaza_preferencias_y_ejecutivas_inexistentes(modulos, utils, monkeypatch):
    customer_lambda, _ = modulos
    monkeypatch.setattr(utils, "_require_self_or_admin_from_bearer", lambda *a, **k: None)
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz", "createdAt": utils._now_iso()})
    assert customer_lambda.handle_update_customer(11, {"contactPreference": "paloma"}, ADMIN)["statusCode"] == 400
    assert customer_lambda.handle_update_customer(11, {"executiveId": "123456"}, ADMIN)["statusCode"] == 400
    assert customer_lambda.handle_update_customer(11, {"executiveId": "no-numerico"}, ADMIN)["statusCode"] == 400
    assert "executiveId" not in utils._get_by_id("CUSTOMER", 11)


def test_sin_patrocinadora_el_panel_muestra_a_la_coach_asignada(modulos, utils):
    _, dashboard_common = modulos
    sponsor = dashboard_common._find_effective_sponsor({"customerId": 11, "leaderId": None, "executiveId": str(IVONNE)})
    assert sponsor["isCoach"] is True and sponsor["isDefault"] is True
    assert sponsor["name"] == "Ivonne Castro" and sponsor["coachTitle"] == "Tu coach en Finding'U"
    assert sponsor["phone"] == "55 5111 2222" and sponsor["whatsapp"] == "https://wa.me/525551112222"
    assert sponsor["email"] == "ivonne@findingu.com.mx"


def test_sin_ejecutiva_asignada_se_usa_la_cartera_por_defecto(modulos, utils):
    _, dashboard_common = modulos
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "config": {"seguimiento": {"defaultExecutiveId": str(IVONNE)}}})
    utils._invalidate_app_config_cache()
    sponsor = dashboard_common._find_effective_sponsor({"customerId": 11, "leaderId": None})
    assert sponsor["isCoach"] is True and sponsor["name"] == "Ivonne Castro"


def test_una_ejecutiva_inactiva_o_inexistente_deja_el_contacto_generico(modulos, utils):
    _, dashboard_common = modulos
    for eid in ("902", "123456"):
        sponsor = dashboard_common._find_effective_sponsor({"customerId": 11, "leaderId": None, "executiveId": eid})
        assert sponsor["isDefault"] is True and "isCoach" not in sponsor
        assert sponsor["name"] == "FindingU" and sponsor["whatsapp"] == "https://wa.me/5215514982351"


def test_con_patrocinadora_el_panel_sigue_mostrandola(modulos, utils):
    _, dashboard_common = modulos
    utils._put_entity("CUSTOMER", 10, {"entityType": "customer", "customerId": 10, "name": "Marcela Ruiz", "phone": "5533334444",
                                       "email": "marcela@test.com", "createdAt": utils._now_iso()})
    sponsor = dashboard_common._find_effective_sponsor({"customerId": 11, "leaderId": 10, "executiveId": str(IVONNE)})
    assert sponsor["name"] == "Marcela Ruiz" and sponsor["isDefault"] is False and "isCoach" not in sponsor


def test_el_panel_completo_del_cliente_trae_a_la_coach(modulos, utils, monkeypatch):
    customer_lambda, _ = modulos
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz",
                                       "email": "rosa@test.com", "executiveId": str(IVONNE), "createdAt": utils._now_iso()})
    monkeypatch.setattr(utils, "_extract_actor_from_bearer", lambda h: {"user_id": "11", "role": "cliente", "privileges": {}})
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/dashboard", "headers": {"Authorization": "Bearer x"},
                                        "queryStringParameters": {}, "body": ""}, None)
    assert r["statusCode"] == 200, r["body"][:300]
    sponsor = json.loads(r["body"])["sponsor"]
    assert sponsor["isCoach"] is True and sponsor["name"] == "Ivonne Castro" and sponsor["whatsapp"].startswith("https://wa.me/52")
