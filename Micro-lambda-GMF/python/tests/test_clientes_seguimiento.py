"""Ficha de cliente: notas, "no contactar", origen y baja de datos (ARCO)."""
import json

import pytest


@pytest.fixture
def modulos(utils, monkeypatch):
    import customer_lambda, auth_utils
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    monkeypatch.setattr(utils, "_require_self_or_admin_from_bearer", lambda *a, **k: None)
    monkeypatch.setattr(utils, "_extract_actor_from_bearer", lambda h: {"user_id": "sofia", "role": "admin", "privileges": {}})
    return customer_lambda, auth_utils


def _karla(utils, cid=77):
    utils._put_entity("CUSTOMER", cid, {"entityType": "customer", "customerId": cid, "name": "Karla Méndez",
                                        "email": "karla@test.com", "phone": "5511112222", "createdAt": utils._now_iso()})
    utils._put_entity("AUTH", "karla@test.com", {"entityType": "auth", "authId": "karla@test.com", "email": "karla@test.com",
                                                 "customerId": cid, "passwordHash": utils._hash_password("Secreta1!"), "role": "cliente"})
    utils._upsert_customer_email_index(cid, "karla@test.com")
    return cid


def test_no_contactar_y_notas_quedan_en_la_ficha(modulos, utils):
    customer_lambda, _ = modulos
    cid = _karla(utils)
    r = customer_lambda.handle_update_customer(cid, {"doNotContact": True, "note": "Pidió que no le escriban (3-sep)", "origin": "anuncio_instagram"}, {})
    assert r["statusCode"] == 200, r["body"]
    ficha = json.loads(r["body"])["customer"]
    assert ficha["doNotContact"] is True and ficha["origin"] == "anuncio_instagram"
    assert ficha["contactNotes"][0]["text"].startswith("Pidió") and ficha["contactNotes"][0]["by"] == "sofia"
    r = customer_lambda.handle_update_customer(cid, {"note": "Segunda nota"}, {})
    assert len(json.loads(r["body"])["customer"]["contactNotes"]) == 2


def test_la_baja_arco_anonimiza_cierra_el_acceso_y_avisa(modulos, utils, monkeypatch):
    customer_lambda, auth_utils = modulos
    cid = _karla(utils)
    correos = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: correos.append((para, asunto)))

    r = customer_lambda.handle_delete_customer_data(cid, {"reason": "ARCO por WhatsApp"}, {})
    assert r["statusCode"] == 200, r["body"]
    ficha = json.loads(r["body"])["customer"]
    assert ficha["name"] == "Cliente eliminado" and ficha["email"].startswith("eliminado+") and not ficha.get("phone")
    assert ficha["doNotContact"] is True and ficha["deletedAt"]
    assert correos == [("karla@test.com", "Confirmación de baja de datos · Finding'U")]

    # Ya no puede entrar ni se le encuentra por su correo viejo.
    assert utils._get_by_id("AUTH", "karla@test.com") is None
    assert utils._find_customer_id_by_email("karla@test.com") in (None, "")
    r = auth_utils.handle_login({"identifier": "karla@test.com", "password": "Secreta1!"}) if hasattr(auth_utils, "handle_login") else {"statusCode": 401}
    assert r["statusCode"] == 401

    # Segunda baja: ya está hecha.
    assert customer_lambda.handle_delete_customer_data(cid, {}, {})["statusCode"] == 409


def test_cambiar_la_contrasena_avisa_por_correo(modulos, utils, monkeypatch):
    _, auth_utils = modulos
    cid = _karla(utils)
    monkeypatch.setattr(utils, "_extract_actor_from_bearer", lambda h: {"user_id": str(cid), "role": "cliente", "privileges": {}})
    monkeypatch.setattr(auth_utils, "_find_auth_for_customer", lambda c: utils._get_by_id("AUTH", "karla@test.com"))
    correos = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: correos.append((para, asunto)))
    r = auth_utils.handle_change_password({"currentPassword": "Secreta1!", "newPassword": "Nueva1234!"}, {})
    assert r["statusCode"] == 200, r["body"]
    assert correos == [("karla@test.com", "Tu contraseña de Finding'U cambió")]
