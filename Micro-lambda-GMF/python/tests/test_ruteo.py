"""Instantánea del ruteo: qué handler atiende cada (método, ruta).

Los 8 `lambda_handler` rutean con cascadas de `if` donde el ORDEN importa.
No hay forma de saber, leyendo, si un cambio desvía una ruta a otro handler.
Esta prueba fija el comportamiento actual: cualquier refactor del ruteo que
cambie el destino de una petición sale aquí en rojo.

El handler se identifica interceptando las funciones `handle_*` del módulo y
registrando cuál se invocó, sin ejecutar su cuerpo.
"""
import importlib
import itertools

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


def _rutas_del_modulo(raices):
    for raiz, sub in itertools.product(raices, SEGUNDO_NIVEL):
        yield f"/{raiz}" if not sub else f"/{raiz}/{sub}"


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
                modulo.lambda_handler(evento, None)
            except Exception as ex:                      # noqa: BLE001
                observado[f"{metodo} {ruta}"] = f"<error:{type(ex).__name__}>"
                continue
            observado[f"{metodo} {ruta}"] = llamadas[0] if llamadas else "<sin handler>"

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
