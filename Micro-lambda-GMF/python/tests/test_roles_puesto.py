"""Rol real y recorte honesto (paquete E, propuestas 27 y 4).

Los tres empleados que no son gerencia lo reportaron por su cuenta:

    Toño, el de las cajas: "llenar el formulario para crear una campaña de
    publicidad. Yo. El de las cajas." (`tono-2027-03-03.md`)

    Gaby, coach: "debajo de mi nombre dice ADMIN, igual que le diría a Renata"
    (`gaby-2027-03-08.md`)

Aquí se prueban las dos piezas que viven en el backend: que Campañas estrene su
propio privilegio (`access_screen_campaigns`) en vez de colgar del de Stocks, y
que el empleado tenga un puesto (`jobTitle`) que la insignia pueda pintar.
"""
import json

import pytest

SUPER = {"x-user-id": "1", "x-user-role": "admin"}


@pytest.fixture
def auth(utils):
    import auth_utils
    return auth_utils


def _alta(auth, nombre, correo, privilegios, puesto=None):
    body = {"name": nombre, "email": correo, "phone": "5551100000",
            "privileges": {p: True for p in privilegios}}
    if puesto is not None:
        body["jobTitle"] = puesto
    resp = auth.lambda_handler({"httpMethod": "POST", "path": "/auth/employees", "headers": SUPER,
                                "queryStringParameters": None, "body": json.dumps(body)}, None)
    return resp["statusCode"], json.loads(resp["body"])


def _login(auth, correo, password):
    resp = auth.lambda_handler({"httpMethod": "POST", "path": "/auth/login", "headers": {},
                                "queryStringParameters": None,
                                "body": json.dumps({"email": correo, "password": password})}, None)
    return resp["statusCode"], json.loads(resp["body"])


# ── Campañas estrena privilegio (propuesta 27a, decisión §4.14) ──

def test_campanas_es_un_privilegio_propio_del_catalogo(utils):
    """Sin este privilegio, `_normalize_privileges` lo descartaría en silencio."""
    assert "access_screen_campaigns" in utils._ALL_PRIVILEGES
    normalizados = utils._normalize_privileges({"access_screen_campaigns": True})
    assert normalizados["access_screen_campaigns"] is True


def test_el_de_las_cajas_no_estrena_campanas_por_tener_almacen(auth, utils):
    """Toño: 'llenar el formulario para crear una campaña de publicidad. Yo. El de las cajas.'"""
    st, r = _alta(auth, "Toño Vera", "tono@findingu.mx",
                  ["access_screen_orders", "access_screen_stocks", "stock_add_inventory"])
    assert st == 201, r
    privs = r["employee"]["privileges"]
    assert privs["access_screen_stocks"] is True
    assert privs["access_screen_campaigns"] is False, "el almacén no administra publicidad"


def test_quien_administra_la_configuracion_conserva_campanas(auth):
    """Alma (administración y finanzas) tenía Campañas y no se le quita en silencio."""
    st, r = _alta(auth, "Alma Rentería", "alma@findingu.mx",
                  ["access_screen_customers", "config_manage", "commissions_register_payment"])
    assert st == 201, r
    assert r["employee"]["privileges"]["access_screen_campaigns"] is True


def test_al_editar_privilegios_se_respeta_la_misma_siembra(auth, utils):
    st, r = _alta(auth, "Renata Bustos", "renata@findingu.mx", ["access_screen_orders"])
    eid = r["employee"]["employeeId"]
    resp = auth.lambda_handler({"httpMethod": "PATCH", "path": f"/auth/employees/{eid}", "headers": SUPER,
                                "queryStringParameters": None,
                                "body": json.dumps({"privileges": {"access_screen_orders": True,
                                                                   "config_manage": True}})}, None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["employee"]["privileges"]["access_screen_campaigns"] is True


def test_apagar_la_casilla_de_campanas_se_respeta_aunque_administre_la_configuracion(auth, utils):
    """La gerente apagaba la casilla, el backend respondía 200 y la devolvía en
    `true`: al recargar volvía a aparecer palomeada. La siembra mira si la llave
    **viene**, no su valor, así que un `false` explícito manda."""
    st, r = _alta(auth, "Alma Rentería", "alma2@findingu.mx",
                  ["access_screen_customers", "config_manage"])
    eid = r["employee"]["employeeId"]
    assert r["employee"]["privileges"]["access_screen_campaigns"] is True

    resp = auth.lambda_handler({"httpMethod": "PATCH", "path": f"/auth/employees/{eid}", "headers": SUPER,
                                "queryStringParameters": None,
                                "body": json.dumps({"privileges": {"access_screen_customers": True,
                                                                   "config_manage": True,
                                                                   "access_screen_campaigns": False}})}, None)
    assert resp["statusCode"] == 200, resp["body"]
    assert json.loads(resp["body"])["employee"]["privileges"]["access_screen_campaigns"] is False
    guardada = utils._get_by_id("EMPLOYEE", eid)
    assert guardada["privileges"]["access_screen_campaigns"] is False, "y queda apagada en la ficha"


def test_una_ficha_guardada_antes_del_privilegio_lo_recibe_al_leerla(auth, utils):
    """En un mundo ya sembrado, la ficha no trae la llave nueva: sin migración
    al leer, la gerente y la de finanzas se quedaban sin Campañas hasta que
    alguien volviera a guardar cada empleado a mano."""
    st, r = _alta(auth, "Renata Bustos", "renata2@findingu.mx",
                  ["access_screen_orders", "config_manage"])
    eid = r["employee"]["employeeId"]
    vieja = dict(utils._get_by_id("EMPLOYEE", eid))
    vieja["privileges"] = {k: v for k, v in vieja["privileges"].items() if k != "access_screen_campaigns"}
    utils._put_entity("EMPLOYEE", eid, vieja)
    assert "access_screen_campaigns" not in utils._get_by_id("EMPLOYEE", eid)["privileges"]

    listado = auth.lambda_handler({"httpMethod": "GET", "path": "/auth/employees", "headers": SUPER,
                                   "queryStringParameters": None, "body": ""}, None)
    fichas = {e["employeeId"]: e for e in json.loads(listado["body"])["employees"]}
    assert fichas[eid]["privileges"]["access_screen_campaigns"] is True

    st, sesion = _login(auth, "renata2@findingu.mx", r["tempPassword"])
    assert sesion["user"]["privileges"]["access_screen_campaigns"] is True, "y la sesión también"


# ── El puesto (propuesta 27c) ──

def test_el_alta_guarda_el_puesto_y_el_login_lo_devuelve(auth):
    """Gaby: 'debajo de mi nombre dice ADMIN, igual que le diría a Renata'."""
    st, r = _alta(auth, "Gaby Ledesma", "gaby@findingu.mx",
                  ["access_screen_customers", "access_screen_orders"], puesto="Coach")
    assert st == 201, r
    assert r["employee"]["jobTitle"] == "Coach"

    st, sesion = _login(auth, "gaby@findingu.mx", r["tempPassword"])
    assert st == 200, sesion
    assert sesion["user"]["jobTitle"] == "Coach", "la insignia necesita el puesto, no el rol"
    assert sesion["user"]["role"] == "employee", (
        "una ficha de empleado entra como employee: con admin, _require_admin daba "
        "acceso total y sus privilegios no restringían nada")


def test_el_puesto_se_puede_corregir_sin_tocar_los_privilegios(auth):
    st, r = _alta(auth, "Mireya Solano", "mireya@findingu.mx", ["access_screen_pos", "pos_register_sale"])
    eid = r["employee"]["employeeId"]
    assert r["employee"].get("jobTitle", "") == ""

    resp = auth.lambda_handler({"httpMethod": "PATCH", "path": f"/auth/employees/{eid}", "headers": SUPER,
                                "queryStringParameters": None,
                                "body": json.dumps({"jobTitle": "Caja"})}, None)
    assert resp["statusCode"] == 200
    empleado = json.loads(resp["body"])["employee"]
    assert empleado["jobTitle"] == "Caja"
    assert empleado["privileges"]["pos_register_sale"] is True

    st, sesion = _login(auth, "mireya@findingu.mx", r["tempPassword"])
    assert sesion["user"]["jobTitle"] == "Caja"


def test_un_puesto_vacio_no_inventa_texto(auth):
    """Sin puesto declarado la pantalla no debe caer en 'ADMIN' ni en una clave técnica."""
    st, r = _alta(auth, "Sin Puesto", "sinpuesto@findingu.mx", ["access_screen_orders"])
    st, sesion = _login(auth, "sinpuesto@findingu.mx", r["tempPassword"])
    assert sesion["user"]["jobTitle"] == ""
