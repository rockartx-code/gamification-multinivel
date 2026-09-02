"""Patrocinio por link de referido: el mecanismo del que vive la red."""
import pytest


@pytest.fixture
def auth(utils):
    import auth_utils
    return auth_utils


def _alta(auth, nombre, correo, referido=None):
    cuerpo = {"name": nombre, "email": correo, "password": "Secreta123!", "confirmPassword": "Secreta123!"}
    if referido:
        cuerpo["referralToken"] = referido
    r = auth.handle_create_account(cuerpo)
    assert r["statusCode"] in (200, 201), r["body"]
    import json
    return json.loads(r["body"])["customerId"]


def _cliente(utils, cid):
    return utils._get_by_id("CUSTOMER", cid)


def test_el_alta_deja_el_codigo_en_la_ficha_del_cliente(auth, utils):
    """Regresión: el código se creaba como entidad aparte pero la ficha quedaba
    con referralCode vacío, y el frontend armaba el link de invitación con el
    ID numérico, que no resolvía."""
    cid = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    assert _cliente(utils, cid)["referralCode"], "la ficha debe llevar el código que se comparte"


def test_el_link_con_codigo_asigna_patrocinador(auth, utils):
    lider = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    codigo = _cliente(utils, lider)["referralCode"]
    invitado = _alta(auth, "Rodrigo Aguilar", "rodrigo@test.com", referido=codigo)
    assert str(_cliente(utils, invitado)["leaderId"]) == str(lider)


def test_el_link_con_id_numerico_tambien_asigna_patrocinador(auth, utils):
    """Regresión: los links que la plataforma ya generó llevan el ID del socio.
    Registrarse con uno de esos links dejaba al invitado sin líder."""
    lider = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    invitado = _alta(auth, "Rodrigo Aguilar", "rodrigo@test.com", referido=str(lider))
    assert str(_cliente(utils, invitado)["leaderId"]) == str(lider)


def test_un_referido_inexistente_no_inventa_lider(auth, utils):
    invitado = _alta(auth, "Karla Méndez", "karla@test.com", referido="999999999")
    assert not _cliente(utils, invitado).get("leaderId")


def test_el_codigo_no_lleva_acentos_y_resuelve_tecleado_sin_ellos(auth, utils):
    """Regresión: "Tomás Ibarra" generaba TOMÁS-TIL; escrito TOMAS-TIL no resolvía."""
    lider = _alta(auth, "Tomás Ibarra López", "tomas@test.com")
    codigo = _cliente(utils, lider)["referralCode"]
    assert codigo == codigo.encode("ascii", "ignore").decode(), codigo
    invitado = _alta(auth, "Patricia Solís", "pat@test.com", referido=codigo.lower())
    assert str(_cliente(utils, invitado)["leaderId"]) == str(lider)
