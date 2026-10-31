"""Que "Guardar CLABE" guarde, y que se pueda quitar (paquete A, propuesta 1).

Fabiola lo intentó cinco veces y Paulina cinco más, en dos pantallas y en dos
días distintos, sin un solo mensaje: *"El único dato que sirve para que YO
cobre es justo el que no se guarda"* (`fabiola-2027-03-04.md`). Marzo cerró con
$0.00 depositados. El backend siempre funcionó; lo que faltaba era guardar al
primer intento y poder borrar lo guardado (informe 25 §3.1: *"una CLABE
guardada no se puede borrar ni vaciar, solo sustituir por otra"*).
"""
import json

import pytest


def _sesion(utils, uid, role="cliente", name="Paulina Ríos"):
    token = f"session-token-{uid}"
    utils._put_session(token, {"sessionId": token, "userId": str(uid), "role": role, "name": name,
                               "privileges": {}, "canAccessAdmin": role != "cliente"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def socia(utils):
    utils._put_entity("CUSTOMER", 55, {"entityType": "customer", "customerId": 55,
                                       "name": "Paulina Ríos", "email": "paulina@test.com",
                                       "isAssociate": True})
    return 55


def test_guardar_la_clabe_responde_con_su_terminacion(utils, socia):
    import customer_lambda
    r = customer_lambda.handle_update_clabe("55", {"clabe": "012345678901236789", "bankInstitution": "BBVA"},
                                            _sesion(utils, socia))
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo == {"ok": True, "clabeLast4": "6789", "removed": False}
    ficha = utils._get_by_id("CUSTOMER", 55)
    assert ficha["clabeInterbancaria"] == "012345678901236789" and ficha["bankInstitution"] == "BBVA"


def test_quitar_la_clabe_la_borra_de_la_ficha(utils, socia):
    """"Quitar CLABE": antes respondía 400 y la socia se quedaba con la de otra cuenta."""
    import customer_lambda
    customer_lambda.handle_update_clabe("55", {"clabe": "012345678901236789", "bankInstitution": "BBVA"},
                                        _sesion(utils, socia))
    r = customer_lambda.handle_update_clabe("55", {"clabe": ""}, _sesion(utils, socia))
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"]) == {"ok": True, "clabeLast4": "", "removed": True}
    ficha = utils._get_by_id("CUSTOMER", 55)
    assert not ficha.get("clabeInterbancaria") and not ficha.get("clabe") and not ficha.get("bankInstitution")


def test_quitar_la_clabe_apaga_los_avisos_pendientes(utils, socia):
    import customer_lambda, pagos_handlers
    nid = pagos_handlers._aviso_panel_clabe(55, "2027-03", "comision")
    customer_lambda.handle_update_clabe("55", {"clabe": ""}, _sesion(utils, socia))
    assert utils._get_by_id("NOTIFICATION", nid)["active"] is False


def test_una_clabe_incompleta_se_rechaza_con_el_motivo_acentuado(utils, socia):
    import customer_lambda
    r = customer_lambda.handle_update_clabe("55", {"clabe": "12345"}, _sesion(utils, socia))
    assert r["statusCode"] == 400
    assert json.loads(r["body"])["message"] == "La CLABE debe tener 18 dígitos numéricos."


def test_nadie_puede_borrar_la_clabe_de_otra_socia(utils, socia):
    """La verificación de identidad ya existía y se conserva también al borrar."""
    import customer_lambda
    utils._put_entity("CUSTOMER", 56, {"entityType": "customer", "customerId": 56, "name": "Fabiola",
                                       "clabeInterbancaria": "012345678901231111"})
    r = customer_lambda.handle_update_clabe("56", {"clabe": ""}, _sesion(utils, socia))
    assert r["statusCode"] == 403
    assert utils._get_by_id("CUSTOMER", 56)["clabeInterbancaria"] == "012345678901231111"
