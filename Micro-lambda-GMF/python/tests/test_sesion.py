"""Sesión: "Recordarme" 30 días, enlace de acceso por correo y el código de recuperación más reciente siempre válido.

Memo, Lupita, Claudia y Patricia pedían dos códigos porque el primero se
invalidaba; Verónica, Claudia y Rosa volvían a entrar "como tres veces" por
sesión (docs/qa/22 §5 fila 5 y §6 tarea 9).
"""
import json
import re
import time
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def auth(utils):
    import auth_utils
    return auth_utils


@pytest.fixture
def buzon(utils, monkeypatch):
    enviados = []
    monkeypatch.setattr(utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append({"para": para, "asunto": asunto, "texto": texto, "html": html}))
    return enviados


def _cuenta(utils, email="ana@test.com", cid=5, **auth_extra):
    utils._put_entity("CUSTOMER", cid, {"entityType": "customer", "customerId": cid, "name": "Ana", "email": email})
    utils._put_entity("AUTH", email, {"entityType": "auth", "authId": email, "email": email, "customerId": cid,
                                      "passwordHash": utils._hash_password("secreta123"), "role": "cliente", **auth_extra})
    return email


def _llamar(auth, ruta, body):
    r = auth.lambda_handler({"path": ruta, "httpMethod": "POST", "headers": {}, "body": json.dumps(body)}, None)
    return r["statusCode"], json.loads(r["body"])


def _ttl_de(utils, token):
    return int(utils._table.store[(f"SESSION#{token}", "SESSION")]["ttl"])


def test_recordarme_por_omision_30_dias_y_sin_marcar_24_horas(auth, utils):
    email = _cuenta(utils)
    ahora = int(time.time())
    estado, d = _llamar(auth, "/auth/login", {"email": email, "password": "secreta123"})
    assert estado == 200 and d["rememberMe"] is True and d["expiresAt"].endswith("Z")
    assert abs(_ttl_de(utils, d["token"]) - (ahora + 30 * 24 * 3600)) < 60

    estado, d = _llamar(auth, "/auth/login", {"email": email, "password": "secreta123", "rememberMe": False})
    assert estado == 200 and d["rememberMe"] is False
    assert abs(_ttl_de(utils, d["token"]) - (ahora + 86400)) < 60
    # La sesión corta sigue sirviendo para autenticar peticiones.
    actor = utils._extract_actor({"authorization": f"Bearer {d['token']}"})
    assert actor["user_id"] == "5" and actor["role"] == "cliente"


def test_enlace_de_acceso_se_emite_canjea_una_vez_y_caduca(auth, utils, buzon):
    email = _cuenta(utils)
    estado, d = _llamar(auth, "/auth/enlace-acceso", {"email": email})
    assert estado == 200 and "Si el correo existe" in d["message"]
    assert len(buzon) == 1 and buzon[0]["para"] == email
    token = re.search(r"/#/login\?enlace=([^\s\"'<>]+)", buzon[0]["texto"]).group(1)
    assert "una sola vez" in buzon[0]["html"]

    estado, d = _llamar(auth, "/auth/enlace-acceso/canjear", {"token": token})
    assert estado == 200 and d["token"] and d["user"]["userId"] == "5" and d["rememberMe"] is True
    assert utils._extract_actor({"authorization": f"Bearer {d['token']}"})["user_id"] == "5"

    # Reusado → 401 con mensaje que manda a pedir otro.
    estado, d = _llamar(auth, "/auth/enlace-acceso/canjear", {"token": token})
    assert estado == 401 and d["code"] == "LOGIN_LINK_INVALID" and "Pide uno nuevo" in d["message"]

    # Caducado → 401.
    _llamar(auth, "/auth/enlace-acceso", {"email": email, "rememberMe": False})
    token2 = re.search(r"enlace=([^\s\"'<>]+)", buzon[1]["texto"]).group(1)
    registro = utils._get_by_id("LOGIN_LINK", utils._hash_token(token2))
    assert registro["rememberMe"] is False
    utils._update_by_id("LOGIN_LINK", registro["tokenHash"], "SET expiresAt = :e",
                        {":e": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()})
    assert _llamar(auth, "/auth/enlace-acceso/canjear", {"token": token2})[0] == 401
    assert _llamar(auth, "/auth/enlace-acceso/canjear", {"token": "inventado"})[0] == 401


def test_el_enlace_no_revela_correos_ni_sale_para_cuentas_sin_verificar(auth, utils, buzon):
    estado, d = _llamar(auth, "/auth/enlace-acceso", {"email": "nadie@test.com"})
    assert estado == 200 and "Si el correo existe" in d["message"]
    _cuenta(utils, email="pendiente@test.com", cid=6, emailVerified=False)
    estado, d = _llamar(auth, "/auth/enlace-acceso", {"email": "pendiente@test.com"})
    assert estado == 200 and "Si el correo existe" in d["message"]
    assert buzon == []
    assert _llamar(auth, "/auth/enlace-acceso", {"email": ""})[0] == 400


def _codigo(correo):
    return re.search(r"es: (\d{6})", correo["texto"]).group(1)


def test_con_dos_codigos_pedidos_ambos_valen_y_el_correo_lo_explica(auth, utils, buzon):
    """Regresión: el segundo código invalidaba al primero, así que quien recibía
    el primer correo tarde ya no podía usarlo."""
    email = _cuenta(utils)
    estado, d = _llamar(auth, "/auth/password/recovery", {"email": email})
    assert estado == 200 and "más reciente" in d["message"]
    _llamar(auth, "/auth/password/recovery", {"email": email})
    primero, segundo = _codigo(buzon[0]), _codigo(buzon[1])
    assert "usa el más reciente" in buzon[1]["texto"] and "usa el más reciente" in buzon[1]["html"]
    assert len(utils._get_by_id("PASSWORD_RESET", email)["otpHashes"]) == 2

    estado, d = _llamar(auth, "/auth/password/reset", {"email": email, "otp": primero, "password": "nueva-clave-1"})
    assert estado == 200, d
    assert utils._verify_password("nueva-clave-1", utils._get_by_id("AUTH", email)["passwordHash"])
    # Al usar uno, los demás dejan de valer.
    estado, d = _llamar(auth, "/auth/password/reset", {"email": email, "otp": segundo, "password": "otra-clave-2"})
    assert estado == 401 and d["message"] == "Código inválido o caducado: pide uno nuevo"


def test_solo_se_conservan_los_ultimos_tres_codigos(auth, utils, buzon):
    email = _cuenta(utils)
    for _ in range(4):
        _llamar(auth, "/auth/password/recovery", {"email": email})
    assert len(utils._get_by_id("PASSWORD_RESET", email)["otpHashes"]) == 3
    assert _llamar(auth, "/auth/password/reset", {"email": email, "otp": _codigo(buzon[0]), "password": "nueva-clave-1"})[0] == 401
    assert _llamar(auth, "/auth/password/reset", {"email": email, "otp": _codigo(buzon[1]), "password": "nueva-clave-1"})[0] == 200


def test_el_codigo_caduca_a_los_15_minutos(auth, utils, buzon):
    """Regresión: `expiresAt` se guardaba pero nunca se comprobaba."""
    email = _cuenta(utils)
    _llamar(auth, "/auth/password/recovery", {"email": email})
    codigo = _codigo(buzon[0])
    vencido = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    registro = utils._get_by_id("PASSWORD_RESET", email)
    for c in registro["otpHashes"]:
        c["expiresAt"] = vencido
    utils._update_by_id("PASSWORD_RESET", email, "SET otpHashes = :h, expiresAt = :e", {":h": registro["otpHashes"], ":e": vencido})
    estado, d = _llamar(auth, "/auth/password/reset", {"email": email, "otp": codigo, "password": "nueva-clave-1"})
    assert estado == 401 and "caducado" in d["message"]


def test_un_registro_viejo_solo_con_otphash_sigue_funcionando(auth, utils):
    email = _cuenta(utils)
    expira = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    utils._put_entity("PASSWORD_RESET", email, {"entityType": "passwordReset", "email": email,
                                                "otpHash": utils._hash_token("123456"), "expiresAt": expira, "used": False})
    assert _llamar(auth, "/auth/password/reset", {"email": email, "otp": "123456", "password": "nueva-clave-1"})[0] == 200
    assert _llamar(auth, "/auth/password/reset", {"email": email, "otp": "123456", "password": "nueva-clave-2"})[0] == 401
