"""Un solo corte de mes, del servidor (paquete G, propuesta 29).

*"El «Corte de mes» cuenta cinco días distintos según tengas sesión o no
(26 d sin cuenta, 21 d con cuenta, medido en el mismo minuto) y nunca dice de
qué es el corte."* Siete de doce personas lo anotaron y **ninguna de las siete
entendió qué se acababa**: *"¿se me vence el carrito? ¿se acaba una oferta?"*.

Había cuatro orígenes del mismo número. A partir de esta ronda el servidor
publica el instante absoluto (`cutoffAt`) y su propio reloj (`serverNow`), y el
frontend deja de fechar el negocio con el reloj del navegador.
"""
import json
from datetime import datetime, timezone

import pytest

import corte_mes

CLIENTE = {"x-user-id": "700", "x-user-role": "cliente"}


def test_el_corte_cae_el_dia_25_del_mes_en_curso():
    corte = corte_mes.proximo_corte("2027-03-02T11:18:04Z")
    assert corte == datetime(2027, 3, 25, 23, 59, 59, tzinfo=timezone.utc)


def test_pasado_el_dia_25_el_corte_es_el_del_mes_siguiente():
    """El mismo minuto en el que Ximena leyó 26 d sin cuenta y 21 d con cuenta."""
    assert corte_mes.proximo_corte("2027-03-25T23:59:59Z").month == 4
    assert corte_mes.proximo_corte("2027-03-26T00:00:01Z") == datetime(2027, 4, 25, 23, 59, 59, tzinfo=timezone.utc)


def test_febrero_y_diciembre_no_necesitan_un_caso_especial():
    assert corte_mes.proximo_corte("2027-02-26T09:00:00Z") == datetime(2027, 3, 25, 23, 59, 59, tzinfo=timezone.utc)
    assert corte_mes.proximo_corte("2027-12-31T09:00:00Z") == datetime(2028, 1, 25, 23, 59, 59, tzinfo=timezone.utc)


def test_los_campos_del_corte_traen_el_instante_el_reloj_y_de_que_es():
    campos = corte_mes.campos_corte("2027-04-10T13:15:37Z")
    assert campos["cutoffAt"] == "2027-04-25T23:59:59Z"
    assert campos["serverNow"] == "2027-04-10T13:15:37Z"
    # El rótulo dice de qué es el corte: un reloj sin explicación no apura, asusta.
    assert campos["cutoffLabel"] == "Cierre del mes de comisiones y de tu descuento por volumen"
    # Los campos viejos se conservan: nadie se queda sin su número.
    assert campos["cutoffDay"] == 25 and campos["cutoffHour"] == 23 and campos["cutoffMinute"] == 59


def test_el_panel_del_cliente_publica_el_corte_y_el_reloj_del_servidor(utils, monkeypatch):
    import customer_lambda
    utils._put_entity("CUSTOMER", 700, {"entityType": "customer", "customerId": 700, "name": "Ximena Paredes",
                                        "email": "ximena@test.com", "isAssociate": True,
                                        "createdAt": utils._now_iso()})
    monkeypatch.setattr(utils, "_extract_actor_from_bearer",
                        lambda h: {"user_id": "700", "role": "cliente", "privileges": {}})
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/dashboard",
                                        "headers": {"Authorization": "Bearer x"},
                                        "queryStringParameters": {}, "body": ""}, None)
    assert r["statusCode"] == 200, r["body"][:300]
    settings = json.loads(r["body"])["settings"]
    assert settings["cutoffAt"] == corte_mes.campos_corte(settings["serverNow"])["cutoffAt"]
    assert settings["serverNow"].endswith("Z")
    assert settings["cutoffLabel"].startswith("Cierre del mes de comisiones")


def test_el_panel_viejo_publica_los_mismos_campos(utils):
    """`GET /user-dashboard` sigue vivo y no puede decir otro número."""
    import dashboard_lambda
    r = dashboard_lambda.lambda_handler({"httpMethod": "GET", "path": "/user-dashboard", "headers": CLIENTE,
                                         "queryStringParameters": None, "body": ""}, None)
    assert r["statusCode"] == 200, str(r["body"])[:300]
    settings = json.loads(r["body"])["settings"]
    assert settings["cutoffAt"] == corte_mes.campos_corte(settings["serverNow"])["cutoffAt"]
    assert settings["cutoffLabel"].startswith("Cierre del mes de comisiones")


def test_el_dia_del_corte_vive_en_un_solo_sitio_del_backend():
    """Estaba escrito a mano en dos lambdas; si vuelve a aparecer, aquí se cae."""
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    for archivo in ("customer_lambda.py", "dashboard_lambda.py"):
        fuente = (raiz / archivo).read_text(encoding="utf-8")
        assert '"cutoffDay": 25' not in fuente, f"{archivo} vuelve a escribir el día del corte a mano"
