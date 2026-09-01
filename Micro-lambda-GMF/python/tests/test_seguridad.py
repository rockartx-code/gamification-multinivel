"""Contraseñas, tokens y accesos de emergencia."""
import io
import os

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def test_el_hash_de_contrasena_lleva_sal(utils):
    a = utils._hash_password("misma-clave")
    b = utils._hash_password("misma-clave")
    assert a != b, "dos usuarios con la misma contraseña no deben compartir hash"
    assert a.startswith("pbkdf2_sha256$")
    assert utils._verify_password("misma-clave", a)
    assert not utils._verify_password("otra-clave", a)


def test_sigue_aceptando_los_hashes_del_esquema_viejo(utils):
    """Las cuentas creadas con SHA-256 sin sal deben poder iniciar sesión."""
    viejo = utils._hash_token("clave-antigua")
    assert utils._verify_password("clave-antigua", viejo)
    assert not utils._verify_password("incorrecta", viejo)
    assert utils._is_legacy_password_hash(viejo)
    assert not utils._is_legacy_password_hash(utils._hash_password("x"))


def test_tolera_hashes_corruptos_o_vacios(utils):
    for basura in (None, "", "pbkdf2_sha256$", "pbkdf2_sha256$abc$xx$yy"):
        assert not utils._verify_password("x", basura)


def test_no_hay_token_maestro_sin_variable_de_entorno(utils):
    """El token de superadmin debe venir del entorno, no del código fuente."""
    assert utils._SUPERADMIN_TOKEN == "", "SUPERADMIN_TOKEN no definido → sin puerta trasera"
    texto = io.open(os.path.join(RAIZ, "core", "settings.py"), encoding="utf-8").read()
    assert 'os.getenv("SUPERADMIN_TOKEN"' in texto


def test_el_login_demo_esta_apagado_por_defecto():
    import auth_utils
    assert auth_utils._demo_users() == [], "DEMO_LOGIN_ENABLED sin definir → sin cuentas demo"


# --- Sesiones: clave directa con respaldo al patrón anterior -----------------

def test_validar_un_bearer_cuesta_un_solo_getitem(utils, store, monkeypatch):
    """El patrón bucket+REF obligaba a 2 GetItem en CADA petición autenticada."""
    from core import db as core_db

    lecturas = {"n": 0}
    original = core_db._table.get_item

    def contando(**kw):
        lecturas["n"] += 1
        return original(**kw)

    utils._put_session("tok-1", {"userId": "5", "role": "cliente", "privileges": {}})
    monkeypatch.setattr(core_db._table, "get_item", contando)

    actor = utils._extract_actor({"authorization": "Bearer tok-1"})
    assert actor["user_id"] == "5"
    assert lecturas["n"] == 1, f"{lecturas['n']} GetItem para validar un token"


def test_sigue_aceptando_sesiones_del_patron_anterior(utils, store):
    """Las sesiones abiertas antes del cambio no deben invalidarse."""
    utils._put_entity("SESSION", "tok-viejo", {
        "entityType": "session", "sessionId": "tok-viejo",
        "userId": "9", "role": "admin", "privileges": {},
    })
    actor = utils._extract_actor({"authorization": "Bearer tok-viejo"})
    assert actor["user_id"] == "9"
    assert actor["role"] == "admin"


def test_la_sesion_nueva_no_deja_puntero_huerfano(utils, store):
    """El puntero REF por sesión se acumulaba sin caducar."""
    utils._put_session("tok-2", {"userId": "7", "role": "cliente", "privileges": {}})
    punteros = [k for k in store if k[0].startswith("SESSION#") and k[1] == "REF"]
    assert not punteros, f"punteros REF creados: {punteros}"


def test_la_sesion_lleva_ttl(utils, store):
    epoch = utils._ttl_epoch(utils.SESSION_TTL_SECONDS)
    utils._put_session("tok-3", {"userId": "8"}, ttl_epoch=epoch)
    item = store[("SESSION#tok-3", "SESSION")]
    assert item["ttl"] == epoch
