"""Quién dice ser quien llama: la sesión, nunca un encabezado.

Tres agujeros que hacían decorativo todo el trabajo de permisos de la ronda:

1. `_extract_actor` caía a `x-user-id` / `x-user-role` / `x-user-privileges`
   cuando no había Bearer, y el API Gateway se publica sin autorizador: con
   `x-user-role: admin` y sin credencial ninguna se abría hasta el CSV del
   banco, que lleva la CLABE completa de cada socia.
2. El alta de empleados escribía la credencial con `"role": "admin"`, y
   `_require_admin` solo aplica privilegios al rol `employee`: los cinco
   empleados pasaban cualquier guarda, con sus casillas en `false`.
3. La firma de la bitácora salía de `x-user-name`, así que una nota escrita
   por Mireya podía quedar firmada "Alma Rentería".

La suite usa los encabezados como atajo de identidad (`TRUST_ACTOR_HEADERS=1`
en `conftest.py`). Este archivo los apaga: aquí se mide lo que hace un
despliegue de verdad.
"""
import json

import pytest


@pytest.fixture
def sin_confianza(monkeypatch):
    """Como cualquier despliegue: los `x-user-*` no valen nada."""
    monkeypatch.delenv("TRUST_ACTOR_HEADERS", raising=False)


FORJADOS = {"x-user-id": "1", "x-user-role": "admin",
            "x-user-privileges": json.dumps({"commissions_register_payment": True,
                                             "access_screen_stats": True,
                                             "access_screen_customers": True})}


def _sesion(utils, uid, role="employee", nombre="", privilegios=None):
    token = f"session-token-{uid}"
    utils._put_session(token, {"sessionId": token, "userId": str(uid), "role": role, "name": nombre,
                               "privileges": utils._normalize_privileges(privilegios or {}),
                               "canAccessAdmin": role != "cliente"})
    return {"Authorization": f"Bearer {token}"}


def _get(modulo, ruta, headers, query=None):
    return modulo.lambda_handler({"path": ruta, "httpMethod": "GET", "headers": headers,
                                  "queryStringParameters": query or {}, "body": "{}"}, None)


def _post(modulo, ruta, body, headers):
    return modulo.lambda_handler({"path": ruta, "httpMethod": "POST", "headers": headers,
                                  "queryStringParameters": {}, "body": json.dumps(body)}, None)


# ── 1. Sin credencial no se entra, aunque el encabezado diga "admin" ─────────

def test_las_rutas_de_pagos_no_se_abren_con_el_encabezado_forjado(utils, sin_confianza):
    """`curl -H 'x-user-role: admin' …/dispersion.csv` traía las CLABES completas."""
    import commissions_lambda
    for ruta in ("/commissions/periodos", "/commissions/pagos",
                 "/commissions/pagos/pendientes.csv", "/commissions/pagos/dispersion.csv"):
        r = _get(commissions_lambda, ruta, FORJADOS, {"month": "2027-04"})
        assert r["statusCode"] == 403, f"{ruta} se abrió sin credencial: {r['body']}"
    assert _post(commissions_lambda, "/commissions/pagos/dia-de-pago",
                 {"dryRun": True, "force": True}, FORJADOS)["statusCode"] == 403


def test_el_resumen_de_turno_no_se_manda_por_correo_con_el_encabezado_forjado(utils, sin_confianza):
    """`{"reenviar": true}` mandaba el resumen al destinatario que se le dijera."""
    import inventory_lambda
    r = _post(inventory_lambda, "/inventory/turno/resumen/enviar",
              {"userId": "1809421204364", "date": "2027-01-15", "email": "quien.sea@example.com"}, FORJADOS)
    assert r["statusCode"] == 403, r["body"]
    assert _get(inventory_lambda, "/inventory/stocks/minimos", FORJADOS)["statusCode"] == 403


def test_con_la_sesion_de_verdad_las_mismas_rutas_abren(utils, sin_confianza):
    import commissions_lambda
    alma = _sesion(utils, 5, privilegios={"commissions_register_payment": True})
    assert _get(commissions_lambda, "/commissions/periodos", alma)["statusCode"] == 200
    assert _get(commissions_lambda, "/commissions/pagos", alma, {"month": "2027-04"})["statusCode"] == 200


# ── 2. Un empleado es `employee`, y sus privilegios sí restringen ────────────

def _alta_de_empleada(auth, utils, nombre, correo, privilegios):
    admin = _sesion(utils, "gerencia", role="admin")
    st = auth.lambda_handler({"path": "/auth/employees", "httpMethod": "POST", "headers": admin,
                              "queryStringParameters": {}, "body": json.dumps(
                                  {"name": nombre, "email": correo, "jobTitle": "Caja",
                                   "privileges": {p: True for p in privilegios}})}, None)
    assert st["statusCode"] == 201, st["body"]
    return json.loads(st["body"])


def test_la_cajera_entra_como_employee_y_no_pasa_la_guarda_de_comisiones(utils, sin_confianza):
    """"Todo empleado inicia sesión con role admin": con eso, ningún privilegio
    de los que se le configuran restringía nada."""
    import auth_utils, commissions_lambda
    alta = _alta_de_empleada(auth_utils, utils, "Mireya Solano", "mireya@findingu.mx",
                             ["access_screen_pos", "pos_register_sale", "access_screen_orders"])
    r = auth_utils.lambda_handler({"path": "/auth/login", "httpMethod": "POST", "headers": {},
                                  "queryStringParameters": {}, "body": json.dumps(
                                      {"email": "mireya@findingu.mx", "password": alta["tempPassword"]})}, None)
    assert r["statusCode"] == 200, r["body"]
    sesion = json.loads(r["body"])
    assert sesion["user"]["role"] == "employee", "una ficha de empleado nunca entra como admin"
    assert sesion["user"]["canAccessAdmin"] is True, "sigue abriendo el back office"
    assert sesion["user"]["privileges"]["commissions_register_payment"] is False

    cabeceras = {"Authorization": f"Bearer {sesion['token']}"}
    assert _get(commissions_lambda, "/commissions/periodos", cabeceras)["statusCode"] == 403
    assert _get(commissions_lambda, "/commissions/pagos", cabeceras, {"month": "2027-04"})["statusCode"] == 403


# ── 3. La bitácora se firma con la sesión, no con `x-user-name` ──────────────

def test_la_nota_no_se_puede_firmar_con_el_nombre_de_otra(utils, sin_confianza):
    """Mireya escribía la nota y la bitácora decía "Alma Rentería"."""
    import customer_lambda
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz",
                                       "email": "rosa@test.com", "phone": "5511112222"})
    mireya = _sesion(utils, 700, nombre="Mireya Solano", privilegios={"access_screen_customers": True})
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "call", "message": "Le marqué"},
              {**mireya, "x-user-name": "Alma Rentería"})
    assert r["statusCode"] == 201, r["body"]
    nota = json.loads(r["body"])["note"]
    assert nota["byName"] == "Mireya Solano" and nota["by"] == "700"


def test_sin_nombre_en_la_sesion_se_firma_con_la_ficha_de_empleada(utils, sin_confianza):
    import customer_lambda
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz"})
    utils._put_entity("EMPLOYEE", 901, {"entityType": "employee", "employeeId": 901, "name": "Alma Rivera"})
    sesion = _sesion(utils, 901, privilegios={"access_screen_customers": True})
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "call", "message": "Le marqué"}, {**sesion, "x-user-name": "Quien sea"})
    assert json.loads(r["body"])["note"]["byName"] == "Alma Rivera"
