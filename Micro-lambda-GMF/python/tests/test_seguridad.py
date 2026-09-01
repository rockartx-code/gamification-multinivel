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
