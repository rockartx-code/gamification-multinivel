"""Instantánea del ruteo: qué handler atiende cada (método, ruta).

Los 8 `lambda_handler` rutean con cascadas de `if` donde el ORDEN importa.
No hay forma de saber, leyendo, si un cambio desvía una ruta a otro handler.
Esta prueba fija el comportamiento actual: cualquier refactor del ruteo que
cambie el destino de una petición sale aquí en rojo.

El handler se identifica interceptando las funciones `handle_*` del módulo y
registrando cuál se invocó, sin ejecutar su cuerpo.
"""
import importlib
import io
import itertools
import os
import re

import pytest

MODULOS = {
    "auth_utils": ["auth"],
    "catalog_lambda": ["catalog", "products", "product-categories", "campaigns", "notifications"],
    "commissions_lambda": ["commissions"],
    "customer_lambda": ["customers", "network", "associates"],
    "dashboard_lambda": ["dashboard", "admin", "user", "user-dashboard"],
    "inventory_lambda": ["inventory", "stocks", "pos", "pickup-stocks"],
    "order_lambda": ["orders", "cart", "coupons"],
}

SEGUNDO_NIVEL = [
    "", "getall", "find", "create", "login", "dashboard", "summary", "config",
    "product", "categories", "sales", "movements", "transfers", "cash-cut",
    "cash-control", "cash-cuts", "withdrawal", "honor-board", "warnings",
    "referral-code", "employees", "receipt", "request", "evaluate", "123",
]
METODOS = ["GET", "POST", "PATCH", "DELETE"]


def _rutas_del_openapi():
    """Rutas declaradas en el contrato, con los `{param}` sustituidos.

    El corpus genérico de dos niveles no alcanza rutas como
    `/commissions/associates/{id}/month/{mes}`. El OpenAPI sí las declara, y
    además es la fuente independiente de la implementación: si un refactor
    rompe una ruta del contrato, se ve aquí.
    """
    especificacion = os.path.join(os.path.dirname(__file__), "..", "..", "openapi-aws.yaml")
    if not os.path.exists(especificacion):
        return []
    texto = io.open(especificacion, encoding="utf-8").read()
    rutas = re.findall(r"^  (/[A-Za-z0-9_\-{}/\.]+):", texto, re.M)
    return [re.sub(r"\{[^}]+\}", "123", r).replace("/+", "/") for r in rutas]


def _rutas_del_modulo(raices):
    vistas = set()
    for raiz, sub in itertools.product(raices, SEGUNDO_NIVEL):
        ruta = f"/{raiz}" if not sub else f"/{raiz}/{sub}"
        vistas.add(ruta)
        yield ruta
    for ruta in _rutas_del_openapi():
        if ruta.strip("/").split("/")[0] in raices and ruta not in vistas:
            vistas.add(ruta)
            yield ruta


@pytest.fixture
def espia(monkeypatch):
    """Sustituye las funciones handle_*/get_* por espías que anotan su nombre."""
    llamadas = []

    def instrumentar(modulo):
        for nombre in dir(modulo):
            if not (nombre.startswith("handle_") or nombre.startswith("get_")):
                continue
            objetivo = getattr(modulo, nombre)
            if not callable(objetivo):
                continue

            def espiar(*a, __n=nombre, **k):
                llamadas.append(__n)
                return {"statusCode": 200, "body": "{}"}

            monkeypatch.setattr(modulo, nombre, espiar)
        # El permiso no debe cortar el ruteo: la instantánea es de destino.
        monkeypatch.setattr(modulo.utils, "_require_admin", lambda *a, **k: None)
        monkeypatch.setattr(modulo.utils, "_require_self_or_admin", lambda *a, **k: None)
        monkeypatch.setattr(
            modulo.utils, "_require_self_or_admin_from_bearer", lambda *a, **k: None
        )
        return llamadas

    return instrumentar


@pytest.mark.parametrize("nombre_modulo", sorted(MODULOS))
def test_el_ruteo_es_estable(nombre_modulo, espia, snapshot_ruteo):
    modulo = importlib.import_module(nombre_modulo)
    llamadas = espia(modulo)

    observado = {}
    for ruta in _rutas_del_modulo(MODULOS[nombre_modulo]):
        for metodo in METODOS:
            llamadas.clear()
            evento = {
                "path": ruta, "httpMethod": metodo,
                "headers": {"x-user-id": "1", "x-user-role": "admin"},
                "queryStringParameters": {}, "body": "{}",
            }
            try:
                respuesta = modulo.lambda_handler(evento, None)
                estado = (respuesta or {}).get("statusCode", "<None → 502>")
            except Exception as ex:                      # noqa: BLE001
                observado[f"{metodo} {ruta}"] = f"<error:{type(ex).__name__}>"
                continue
            # Se registra también el estado: en varios lambdas la lógica está
            # en línea y no invoca ningún `handle_*`, así que solo con el
            # nombre del handler la instantánea no distinguía 200 de 404.
            quien = llamadas[0] if llamadas else "<sin handler>"
            observado[f"{metodo} {ruta}"] = f"{quien} [{estado}]"

    snapshot_ruteo(nombre_modulo, observado)


def test_options_siempre_responde_cors(espia):
    """Todo lambda debe contestar el preflight sin autenticación."""
    for nombre_modulo in sorted(MODULOS):
        modulo = importlib.import_module(nombre_modulo)
        respuesta = modulo.lambda_handler(
            {"path": "/lo-que-sea", "httpMethod": "OPTIONS", "headers": {}}, None
        )
        assert respuesta["statusCode"] == 200, nombre_modulo
        assert "Access-Control-Allow-Origin" in respuesta["headers"], nombre_modulo


# --- Contrato del ruteador declarativo --------------------------------------

def test_una_ruta_inexistente_responde_404_y_no_502(espia):
    """Los sub-paths que no existen deben ser 404, no caer en otro handler.

    Antes las cascadas despachaban por prefijo: `/campaigns/loquesea` iba a
    `handle_campaigns`, que no atiende ese método, devolvía `None`, y API
    Gateway lo traducía a **502 Bad Gateway**. Un 404 explícito es correcto y
    además no parece una caída del servicio.
    """
    import catalog_lambda
    espia(catalog_lambda)

    for ruta in ("/campaigns/loquesea", "/catalog/producto-inventado", "/no-existe"):
        respuesta = catalog_lambda.lambda_handler(
            {"path": ruta, "httpMethod": "DELETE", "headers": {}, "body": "{}"}, None)
        assert respuesta["statusCode"] == 404, ruta


def test_un_metodo_no_permitido_responde_405(espia):
    """Si la ruta existe pero no acepta ese método, 405 (no 404 ni 502)."""
    import catalog_lambda
    espia(catalog_lambda)

    for metodo, ruta in (("DELETE", "/catalog"), ("PATCH", "/products"),
                         ("DELETE", "/notifications")):
        respuesta = catalog_lambda.lambda_handler(
            {"path": ruta, "httpMethod": metodo, "headers": {}, "body": "{}"}, None)
        assert respuesta["statusCode"] == 405, f"{metodo} {ruta}"


def test_la_tabla_de_rutas_declara_el_privilegio_de_cada_endpoint():
    """La superficie del lambda debe poder auditarse de un vistazo."""
    import catalog_lambda
    import core_utils

    tabla = core_utils.routing.describir(catalog_lambda.RUTAS)
    assert tabla, "la tabla de rutas está vacía"
    for fila in tabla:
        assert fila["metodo"] in ("GET", "POST", "PATCH", "DELETE", "PUT", "ANY")
        assert fila["patron"].startswith("/")
        assert fila["privilegio"], f"{fila['metodo']} {fila['patron']} sin privilegio declarado"

    # Ninguna escritura del catálogo puede quedar sin privilegio explícito.
    escrituras_publicas = [
        f for f in tabla
        if f["metodo"] in ("POST", "PATCH", "DELETE") and f["privilegio"] == "público"
    ]
    permitidas = {"/notifications/{id}/read"}          # acuse del propio cliente
    inesperadas = [f["patron"] for f in escrituras_publicas if f["patron"] not in permitidas]
    assert not inesperadas, f"escrituras sin privilegio: {inesperadas}"


def test_el_dashboard_legado_anuncia_su_retirada(utils):
    """`/user-dashboard` debe avisar a cualquier cliente que siga usándolo."""
    import dashboard_lambda

    # Sin espía: se necesita la respuesta real, no una simulada.
    respuesta = dashboard_lambda.get_user_dashboard({}, {})

    cabeceras = respuesta.get("headers", {})
    assert cabeceras.get("Deprecation") == "true"
    assert "successor-version" in cabeceras.get("Link", "")
    assert "/customers/dashboard" in cabeceras.get("Link", "")
