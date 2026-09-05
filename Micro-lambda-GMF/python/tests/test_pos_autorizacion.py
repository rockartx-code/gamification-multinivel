"""Guarda 8 (docs/qa/27 §4): el código de autorización se valida antes del retiro.

Mireya escribió 1234 "a ver qué pasaba", la pantalla la dejó pasar, le hizo leer
todo el resumen del arqueo y el HTTP 403 le llegó en "Cerrar el corte", con el
dinero contado en la mano y el turno terminado. Y en esa tienda **no había
ningún código dado de alta**: decirle "incorrecto" era mentirle, porque no
existía ningún código que pudiera escribir bien.

Lo que esta guarda fija son las dos mitades:

* el estado se puede consultar **antes** (`authCodeConfigured` en el arqueo y
  `POST /pos/validate-auth`), así que el 403 no espera al final; y
* los tres estados son tres —sin código, código incorrecto, código bueno— en
  todas las puertas que mueven dinero: el retiro suelto y el retiro del corte.

Y, pase lo que pase con el código, ningún retiro se escribe si no se autorizó.
"""
import json

import pytest

CAJERA = {"x-user-id": "paco"}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}
SIN_PRIVILEGIO = {"x-user-id": "nadia", "x-user-role": "employee", "x-user-privileges": "{}"}


@pytest.fixture
def inventory_lambda(utils, monkeypatch):
    import inventory_lambda
    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", None)
    return inventory_lambda


def _mostrador(utils, pid=201, stock="STK-1"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Klinhart",
                                       "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("STOCK", stock, {"entityType": "stock", "stockId": stock, "name": "Tienda",
                                       "inventory": {str(pid): 40}, "linkedUserIds": ["paco"]})
    return pid, stock


def _codigo(utils, valor="2468"):
    utils._put_entity("CONFIG", "pos-auth-v1", {"entityType": "config", "configId": "pos-auth-v1",
                                                "posAuthCode": valor})


def _venta(inventory_lambda, pid, stock, **extra):
    cuerpo = {"stockId": stock, "items": [{"productId": pid, "name": "Klinhart", "price": 480, "quantity": 1}],
              "paymentMethod": "cash", **extra}
    r = inventory_lambda.handle_pos_sale(cuerpo, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    return json.loads(r["body"])


def _peticion(inventory_lambda, metodo, ruta, cuerpo=None, headers=None, query=None):
    return inventory_lambda.lambda_handler({
        "httpMethod": metodo, "path": ruta, "headers": headers or (ADMIN | CAJERA),
        "queryStringParameters": query or {}, "body": json.dumps(cuerpo or {}),
    }, None)


def _retiros(utils, stock):
    return [w for w in utils._query_bucket("POS_WITHDRAWAL") if w.get("stockId") == stock]


def test_el_codigo_se_valida_antes_del_retiro_y_no_al_final(inventory_lambda, utils):
    """El paso 3 del corte se puede comprobar sin llegar a "Cerrar el corte"."""
    pid, stock = _mostrador(utils)
    _codigo(utils)
    _venta(inventory_lambda, pid, stock)

    # La pantalla puede preguntar por el código sola, antes de contar nada.
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": "1234"})
    assert r["statusCode"] == 403 and json.loads(r["body"])["configured"] is True
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": ""})
    assert r["statusCode"] == 400 and "Escribe el código" in json.loads(r["body"])["message"]
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": "2468"})
    assert r["statusCode"] == 200 and json.loads(r["body"])["ok"] is True

    # Validar no es retirar: hasta aquí no se ha movido un peso.
    assert _retiros(utils, stock) == []

    # Un retiro con código malo se rechaza y no deja rastro de dinero movido.
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 100, "reason": "paquetería",
                                                "receiver": "Beto", "authCode": "1234"}, CAJERA)
    assert r["statusCode"] == 403, r["body"]
    assert "incorrecto" in json.loads(r["body"])["message"]
    assert _retiros(utils, stock) == [], "se rechazó el código y aun así se retiró"
    assert inventory_lambda._build_pos_cash_control(stock, "paco")["currentTotal"] == 480

    # Con el bueno sí, y el efectivo baja exactamente lo retirado.
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 100, "reason": "paquetería",
                                                "receiver": "Beto", "authCode": "2468"}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    assert len(_retiros(utils, stock)) == 1
    assert json.loads(r["body"])["remainingCash"] == 380


def test_sin_codigo_dado_de_alta_se_dice_eso_y_no_incorrecto(inventory_lambda, utils):
    """En la tienda de Mireya no había ningún código: "incorrecto" era mentira."""
    pid, stock = _mostrador(utils)
    _codigo(utils, "")            # dado de alta pero vacío: sigue siendo "no hay"
    _venta(inventory_lambda, pid, stock)

    # 1. La pantalla lo sabe desde el arqueo, sin pedir el privilegio de configuración.
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", query={"stockId": stock})
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["arqueo"]["config"]["authCodeConfigured"] is False

    # 2. Preguntar por un código cualquiera responde 409 "no hay", con la salida honesta.
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": "1234"})
    assert r["statusCode"] == 409, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["configured"] is False and cuerpo["ok"] is False
    assert "no hay un código de autorización configurado" in cuerpo["message"]
    assert "Deja todo como fondo" in cuerpo["message"]

    # 3. El retiro suelto y el retiro del corte dicen lo mismo, no "incorrecto".
    r = inventory_lambda.handle_pos_withdrawal({"stockId": stock, "amount": 100, "reason": "paquetería",
                                                "receiver": "Beto", "authCode": "1234"}, CAJERA)
    assert r["statusCode"] == 403, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["authCodeConfigured"] is False and "incorrecto" not in cuerpo["message"]

    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 480, "cashToKeep": 80,
                                          "withdrawalAmount": 400, "withdrawalReceiver": "Sofía",
                                          "authCode": "1234"}, CAJERA)
    assert r["statusCode"] == 403, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["authCodeConfigured"] is False and "incorrecto" not in cuerpo["message"]
    assert _retiros(utils, stock) == []

    # 4. Y la salida honesta funciona: sin retiro, el corte cierra sin código.
    r = inventory_lambda.handle_cash_cut({"stockId": stock, "cashCounted": 480, "cashToKeep": 480,
                                          "withdrawalAmount": 0}, CAJERA)
    assert r["statusCode"] == 201, r["body"]
    assert json.loads(r["body"])["cut"]["cashToKeep"] == 480


def test_el_codigo_nunca_viaja_de_vuelta_ni_se_valida_sin_privilegio(inventory_lambda, utils):
    """Un código que se pudiera leer no autoriza nada."""
    _mostrador(utils)
    _codigo(utils)

    # El estado se puede consultar; el código, no.
    r = _peticion(inventory_lambda, "GET", "/inventory/pos/arqueo", query={"stockId": "STK-1"})
    cuerpo = r["body"]
    assert json.loads(cuerpo)["arqueo"]["config"]["authCodeConfigured"] is True
    assert "2468" not in cuerpo

    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": "2468"})
    assert r["statusCode"] == 200 and "2468" not in r["body"]

    # Y sin el privilegio del POS no se puede ni preguntar (sería un oráculo de códigos).
    r = _peticion(inventory_lambda, "POST", "/inventory/pos/validate-auth", {"code": "2468"},
                  headers=SIN_PRIVILEGIO)
    assert r["statusCode"] == 403, r["body"]
