"""Los cabos que la ronda 7 dejó atados a la integración (docs/arquitectura/26).

Cada paquete trabajó en su worktree y dejó por escrito lo que no podía tocar
sin invadir región ajena. Estas pruebas fijan lo que la integración montó
después, para que nadie lo vuelva a desatar:

- El texto de la base de la comisión (§3.2) se escribe **una sola vez**, en
  `impuestos.py`: `pagos_handlers` ya no lleva su copia de respaldo.
- Campañas exige su propio privilegio también en el servidor (§4.14): con
  `access_screen_stocks` la cajera dejó de verlo en el menú, pero un POST a
  mano seguía pasando.
- Guardar un producto desde la vista Productos ya no le borra su `minStock`
  (propuesta 28c): el formulario no manda ese campo.
- `cutoffAt`/`serverNow` viajan en los **tres** paneles de §3.6, y también en
  la configuración pública, que es de donde lee el invitado sin sesión.
- La venta de mostrador congela su desglose de IVA como el checkout (§38).
- El correo de bienvenida al modo socio está escrito sin género (§3.7/§25).
"""
import json

from decimal import Decimal

import pytest

SUPER = {"x-user-id": "1", "x-user-role": "admin"}


# ── §3.2 · una sola redacción de la base de la comisión ──────────────────────

def test_pagos_del_mes_no_guarda_su_propia_copia_del_texto_de_la_comision(utils):
    """Ximena leyó "$135 de $1,350 o de $1,500, ¿de cuál?": una frase, no dos."""
    import impuestos
    import pagos_handlers

    assert pagos_handlers.frase_base_comision() == impuestos.FRASE_BASE_COMISION
    esperado = impuestos.texto_base_comision(Decimal("1350.00"), Decimal("0.10"), Decimal("135.00"))
    assert pagos_handlers.texto_base_comision(Decimal("1350.00"), Decimal("0.10"), Decimal("135.00")) == esperado
    assert esperado == "10 % de $1,350.00 netos, sin envío = $135.00"


def test_el_codigo_de_pagos_no_vuelve_a_escribir_la_frase_a_mano():
    """Si alguien copia la redacción otra vez, esta prueba lo caza."""
    import os
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pagos_handlers.py")
    with open(ruta, encoding="utf-8") as archivo:
        fuente = archivo.read()
    # Las palabras de la frase larga y las del respaldo local: ninguna vive aquí.
    assert "sin contar el envío" not in fuente
    assert "el precio ya con su descuento" not in fuente
    assert "commissionBase" not in fuente


# ── §4.14 · Campañas con su propio privilegio, también en el servidor ────────

def _crear_campana(privilegios):
    """Toño es empleado: sus privilegios los manda la sesión, no el rol."""
    import catalog_lambda
    cabeceras = {"x-user-id": "77", "x-user-role": "employee",
                 "x-user-privileges": json.dumps({p: True for p in privilegios})}
    return catalog_lambda.lambda_handler(
        {"path": "/campaigns", "httpMethod": "POST", "headers": cabeceras,
         "queryStringParameters": {},
         "body": json.dumps({"name": "Campaña de mayo", "active": True})}, None)


def test_la_cajera_no_puede_crear_campanas_por_mas_que_escriba_el_post(utils):
    """El recorte de la 27a era solo visual: el menú la escondía, el POST pasaba."""
    respuesta = _crear_campana(["access_screen_stocks", "pos_register_sale"])
    assert respuesta["statusCode"] == 403, respuesta["body"]
    assert "access_screen_campaigns" in json.loads(respuesta["body"])["message"]


def test_quien_si_tiene_el_privilegio_de_campanas_entra(utils):
    respuesta = _crear_campana(["access_screen_campaigns"])
    assert respuesta["statusCode"] in (200, 201), respuesta["body"]


# ── Propuesta 28c · guardar un producto no le borra su mínimo ────────────────

def _guardar_producto(cuerpo):
    import catalog_lambda
    return catalog_lambda.lambda_handler(
        {"path": "/products", "httpMethod": "POST", "headers": SUPER,
         "queryStringParameters": {}, "body": json.dumps(cuerpo)}, None)


def test_editar_el_nombre_de_un_producto_conserva_su_minimo_de_piezas(utils):
    """Sin esto, corregir una falta de ortografía apagaba el aviso de stock bajo."""
    creado = _guardar_producto({"name": "Klinhart", "price": 480, "minStock": 12})
    assert creado["statusCode"] == 201, creado["body"]
    pid = json.loads(creado["body"])["product"]["productId"]

    editado = _guardar_producto({"productId": pid, "name": "Klinhart Omega 3", "price": 480})
    assert editado["statusCode"] == 201, editado["body"]
    assert utils._to_decimal(json.loads(editado["body"])["product"]["minStock"]) == Decimal("12")
    assert utils._to_decimal(utils._get_by_id("PRODUCT", int(pid)).get("minStock")) == Decimal("12")


def test_el_minimo_si_se_puede_cambiar_cuando_el_cuerpo_lo_manda(utils):
    creado = _guardar_producto({"name": "Naplus", "price": 560, "minStock": 4})
    pid = json.loads(creado["body"])["product"]["productId"]
    editado = _guardar_producto({"productId": pid, "name": "Naplus", "price": 560, "minStock": 9})
    assert utils._to_decimal(json.loads(editado["body"])["product"]["minStock"]) == Decimal("9")


# ── §3.6 · el corte lo dice el servidor en los tres paneles y en la pública ──

def test_la_configuracion_de_la_app_publica_el_corte_y_la_hora_del_servidor(utils):
    """El panel del back office leía la fecha del corte del reloj del navegador."""
    import commissions_lambda
    respuesta = commissions_lambda.lambda_handler(
        {"path": "/commissions/config/app", "httpMethod": "GET", "headers": SUPER,
         "queryStringParameters": {}, "body": "{}"}, None)
    assert respuesta["statusCode"] == 200, respuesta["body"]
    cuerpo = json.loads(respuesta["body"])
    assert cuerpo["cutoffAt"] and cuerpo["serverNow"] and cuerpo["cutoffLabel"]
    assert cuerpo["config"]["rewards"]


def test_el_invitado_sin_sesion_recibe_el_mismo_corte_que_la_socia(utils):
    """Ernesto veía 26 días sin sesión y 21 con sesión, en el mismo minuto."""
    import catalog_lambda
    import corte_mes
    respuesta = catalog_lambda.lambda_handler(
        {"path": "/catalog/config/public", "httpMethod": "GET", "headers": {},
         "queryStringParameters": {}, "body": "{}"}, None)
    assert respuesta["statusCode"] == 200, respuesta["body"]
    publica = json.loads(respuesta["body"])["config"]
    assert publica["cutoffAt"] == corte_mes.campos_corte()["cutoffAt"]
    assert publica["serverNow"] and publica["cutoffLabel"]


# ── §38 · la venta de mostrador congela su desglose de IVA ───────────────────

def test_la_venta_de_mostrador_guarda_su_desglose_de_iva(utils, monkeypatch):
    """El comprobante del corte no puede recalcular con la tasa de mañana."""
    import impuestos
    import inventory_lambda

    monkeypatch.setattr(inventory_lambda, "ORDER_SFN_ARN", "arn:sim:sfn")
    utils._put_entity("PRODUCT", 201, {"entityType": "product", "productId": 201,
                                       "name": "Klinhart", "price": 480, "vpPoints": 10,
                                       "active": True})
    utils._put_entity("STOCK", "STK-1", {"entityType": "stock", "stockId": "STK-1",
                                         "name": "Tienda", "inventory": {"201": 40}})
    respuesta = inventory_lambda.handle_pos_sale(
        {"stockId": "STK-1", "paymentMethod": "cash",
         "items": [{"productId": 201, "name": "Klinhart", "price": 480, "quantity": 2}]},
        {"x-user-id": "paco"})
    assert respuesta["statusCode"] == 201, respuesta["body"]
    order_id = json.loads(respuesta["body"])["orderId"]

    pedido = utils._get_by_id("ORDER", order_id)
    total = utils._to_decimal(pedido["total"])
    assert utils._to_decimal(pedido["vatRate"]) == impuestos.tasa_iva()
    assert utils._to_decimal(pedido["taxBase"]) + utils._to_decimal(pedido["taxAmount"]) == total
    assert utils._to_decimal(pedido["taxAmount"]) > 0


# ── §25 · el correo de bienvenida no supone el género de quien lo lee ────────

def test_el_correo_de_bienvenida_al_modo_socio_no_da_por_hecho_el_genero():
    import os
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modo_handlers.py")
    with open(ruta, encoding="utf-8") as archivo:
        fuente = archivo.read()
    assert "Bienvenida al modo socio" not in fuente
    assert "Te damos la bienvenida al modo socio" in fuente
