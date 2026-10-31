"""Guarda: `POST /dashboard/notifications/{id}` no debe crear nada.

Lo destapó el recorrido end-to-end contra el mundo simulado, no la suite:
`POST /dashboard/notifications/999` respondía **201** con una notificación
recién creada, ignorando el `999` de la URL. Es decir, una escritura real en
una dirección que nadie declaró.

Es el mismo agujero que `tests/rutas/CAMBIOS-ACEPTADOS.md` documenta y cierra
en `catalog_lambda` al migrarlo a tabla declarativa
(«**Escritura real** en una URL no declarada → 404»). `dashboard_lambda` sigue
despachando con cascada de `if` —`ARCHITECTURE.md` dice de migrarlos «al
tocarlos»— así que ahí el agujero sobrevivió.

Crear sigue siendo `POST /notifications` a secas; marcar leído sigue siendo
`POST /notifications/{id}/read`. Lo de en medio, 404.
"""
import json

import dashboard_lambda

ADMIN = {"x-user-id": "1", "x-user-role": "admin"}


def _evento(metodo, ruta, cuerpo=None, headers=None):
    return {
        "httpMethod": metodo,
        "path": ruta,
        "headers": headers or ADMIN,
        "queryStringParameters": None,
        "body": None if cuerpo is None else json.dumps(cuerpo),
        "isBase64Encoded": False,
    }


def _cuantas(utils):
    return len(utils._query_bucket("NOTIFICATION"))


def test_post_a_notificacion_con_id_no_crea_nada(utils):
    antes = _cuantas(utils)

    r = dashboard_lambda.lambda_handler(
        _evento("POST", "/dashboard/notifications/999",
                {"title": "inyectada"}), {})

    assert r["statusCode"] == 404, (
        f"POST a una URL no declarada devolvio {r['statusCode']}: "
        "vuelve a escribir donde nadie lo declaro")
    assert _cuantas(utils) == antes, "creo una notificacion pese al 404"


def test_post_a_notificaciones_sigue_creando(utils):
    antes = _cuantas(utils)

    r = dashboard_lambda.lambda_handler(
        _evento("POST", "/dashboard/notifications",
                {"title": "aviso de verdad"}), {})

    assert r["statusCode"] == 201, r
    assert _cuantas(utils) == antes + 1


def test_marcar_leida_sigue_funcionando(utils):
    r = dashboard_lambda.lambda_handler(
        _evento("POST", "/dashboard/notifications",
                {"title": "para leer"}), {})
    nid = json.loads(r["body"])["notification"]["notificationId"]

    r = dashboard_lambda.lambda_handler(
        _evento("POST", f"/dashboard/notifications/{nid}/read",
                {"userId": "1"}), {})

    assert r["statusCode"] == 200, r
