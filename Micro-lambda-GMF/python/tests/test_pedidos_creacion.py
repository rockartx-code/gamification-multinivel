"""Creación de pedidos: el camino que recorre cualquier compra."""
from decimal import Decimal

import pytest


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


def _producto(utils, pid=101, **extra):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": "Finding Pro 500g",
                                       "price": 800, "vpPoints": 15, "active": True, **extra})


def _pedido_invitado(pid=101):
    return {
        "items": [{"productId": pid, "name": "Finding Pro 500g", "price": 800, "quantity": 1}],
        "guest": True, "customerName": "Lucía Fernández", "email": "lucia@test.com", "phone": "3311112222",
        "recipientName": "Lucía Fernández", "deliveryType": "shipping",
        "shippingAddress": {"street": "Av. Vallarta", "number": "100", "city": "Guadalajara",
                            "state": "Jalisco", "postalCode": "44100", "country": "MX"},
        "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": 129,
    }


def test_un_producto_con_puntos_no_impide_crear_el_pedido(order_lambda, utils):
    """Regresión: `vpPoints` se convertía a float al enriquecer los ítems y el
    serializador de DynamoDB rechazaba el pedido entero ("Float types are not
    supported"). Como el frontend nunca manda vpPoints, fallaba TODA compra de
    un producto con puntos, fuera invitado o socio."""
    _producto(utils)
    respuesta = order_lambda.handle_create_order(_pedido_invitado(), {})
    assert respuesta["statusCode"] in (200, 201), respuesta["body"]

    guardado = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")
    puntos = guardado["items"][0]["vpPoints"]
    assert isinstance(puntos, Decimal) and puntos == Decimal("15")
    # Y el ítem completo debe ser serializable tal cual para DynamoDB.
    from core.db import _ddb_serialize_item
    _ddb_serialize_item(guardado)


class _RespuestaMP:
    def __init__(self): self._b = b'{"id":"pref-1","init_point":"https://mp.test/pagar","sandbox_init_point":"https://mp.test/pagar"}'
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _crear_pedido_invitado(order_lambda, utils):
    _producto(utils)
    import json
    r = order_lambda.handle_create_order(_pedido_invitado(), {})
    d = json.loads(r["body"])
    return d.get("orderId") or d["order"]["orderId"]


def _evento(metodo, ruta, cuerpo=None):
    import json
    return {"httpMethod": metodo, "path": ruta, "headers": {}, "body": json.dumps(cuerpo or {})}


def test_el_invitado_puede_ver_su_pedido_sin_sesion(order_lambda, utils):
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)
    assert r["statusCode"] == 200, r["body"]
    import json
    pedido = json.loads(r["body"])["order"]
    # El seguimiento mostraba "$0": el item crudo no lleva "total".
    assert float(pedido.get("total") or 0) == 929.0, pedido  # 800 + 129 de envío


def test_el_invitado_puede_iniciar_el_pago_sin_sesion(order_lambda, utils, monkeypatch):
    """Regresión: la tienda ofrece comprar sin cuenta y el pedido se creaba,
    pero /checkout exigía sesión del dueño y respondía 401: el invitado nunca
    llegaba a la pasarela."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", lambda *a, **k: _RespuestaMP())
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] == 200, r["body"]
    assert "init_point" in r["body"]


def test_un_pedido_de_socio_sigue_exigiendo_sesion(order_lambda, utils):
    _producto(utils)
    cuerpo = {**_pedido_invitado(), "guest": False, "buyerType": "customer", "customerId": 777}
    utils._put_entity("CUSTOMER", 777, {"entityType": "customer", "customerId": 777, "name": "Socio"})
    import json
    oid = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])
    oid = oid.get("orderId") or oid["order"]["orderId"]
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    assert r["statusCode"] in (401, 403)


def test_el_envio_se_guarda_y_se_cobra(order_lambda, utils, monkeypatch):
    """Regresión: el carrito cotizaba $129 de envío, el pedido lo descartaba
    (total $800 en el seguimiento) y la pasarela cobraba solo los productos."""
    import json
    oid = _crear_pedido_invitado(order_lambda, utils)
    pedido = json.loads(order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)["body"])["order"]
    assert float(pedido["shippingCost"]) == 129.0 and float(pedido["total"]) == 929.0, pedido
    assert float(pedido["netTotal"]) == 800.0, "el envío no debe entrar en la base comisionable"

    enviado = {}
    def _urlopen(req, *a, **k):
        enviado.update(json.loads(req.data.decode())); return _RespuestaMP()
    monkeypatch.setattr(order_lambda.urllib.request, "urlopen", _urlopen)
    order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/checkout"), None)
    cobrado = sum(i["unit_price"] * i["quantity"] for i in enviado["items"])
    assert cobrado == 929.0, enviado["items"]


def test_el_invitado_puede_solicitar_devolucion_sin_sesion(order_lambda, utils):
    """Regresión: el asistente de devolución dejaba completar los tres pasos y
    en "Enviar solicitud" respondía "No autenticado"."""
    import json
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET #s = :s, deliveredAt = :d", {":s": "delivered", ":d": utils._now_iso()}, {"#s": "status"}) if False else None
    pedido = utils._get_by_id("ORDER", oid); pedido["status"] = "delivered"; pedido["deliveredAt"] = utils._now_iso()
    utils._table.put_item(Item=pedido)
    cuerpo = {"motivo": "DANADO", "reason": "DANADO", "descripcion": "Tapa rajada",
              "evidencia": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]},
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] not in (401, 403), r["body"]


def test_el_invitado_puede_cancelar_su_pedido_pendiente_sin_sesion(order_lambda, utils):
    """Regresión: el invitado que se arrepiente en la pasarela pulsa "Cancelar
    pedido" y recibía "No autenticado"; el pedido pendiente quedaba colgado."""
    oid = _crear_pedido_invitado(order_lambda, utils)
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/cancel", {"reason": "customer_request"}), None)
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("ORDER", oid)["status"] == "cancelled"


def _entregado(utils, oid):
    pedido = utils._get_by_id("ORDER", oid); pedido["status"] = "delivered"; pedido["deliveredAt"] = utils._now_iso()
    utils._table.put_item(Item=pedido)


def test_el_reembolso_suma_el_envio_de_regreso_declarado(order_lambda, utils, monkeypatch):
    """Lucía pagó $165 en Estafeta para regresar el bote; la gerente reembolsó
    "la única cifra que el sistema mostraba" ($800) y ella reclamó después."""
    import json
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    _entregado(utils, oid)
    cuerpo = {"motivo": "DANADO_DEFECTUOSO", "descripcion": "Tapa rajada", "returnShippingCost": 165,
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] == 201, r["body"]
    assert utils._get_by_id("ORDER", oid)["returnShippingCost"] == Decimal("165")
    ok = {"inspection": {"empaque_original": True, "sellos_intactos": True, "sin_uso": True, "coincide_con_pedido": True, "trazabilidad_valida": True}}
    assert order_lambda.handle_return_inspection(oid, ok, {})["statusCode"] == 200
    r = order_lambda.handle_refund_order(oid, {"reason": "return"}, {})
    assert r["statusCode"] == 200, r["body"]
    assert Decimal(str(json.loads(r["body"])["refundAmount"])) == Decimal("1094")   # 929 cobrados + 165 de regreso
    assert utils._get_by_id("ORDER", oid)["refundAmount"] == Decimal("1094")


def test_el_reembolso_acepta_un_importe_distinto(order_lambda, utils, monkeypatch):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert order_lambda.handle_cancel_order(oid, {}, {})["statusCode"] == 200
    r = order_lambda.handle_refund_order(oid, {"reason": "parcial", "amount": 500}, {})
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("ORDER", oid)["refundAmount"] == Decimal("500")
    assert order_lambda.handle_refund_order(oid, {"amount": -1}, {})["statusCode"] in (400, 409)


def test_los_cupones_responden_bajo_el_prefijo_que_enruta_api_gateway(order_lambda, utils, monkeypatch):
    """Regresión: el frontend llamaba /coupons y la Lambda solo recibe
    /orders/{proxy+}; los cupones eran inalcanzables en producción."""
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    r = order_lambda.lambda_handler(_evento("POST", "/orders/coupons", {"code": "OCTUBRE10", "type": "percent", "value": 10, "active": True}), None)
    assert r["statusCode"] in (200, 201), r["body"]
    r = order_lambda.lambda_handler(_evento("GET", "/orders/coupons"), None)
    assert r["statusCode"] == 200 and "OCTUBRE10" in r["body"]
    r = order_lambda.lambda_handler(_evento("POST", "/orders/coupons/validate", {"code": "OCTUBRE10", "subtotal": 1000}), None)
    assert r["statusCode"] == 200, r["body"]
    r = order_lambda.lambda_handler(_evento("DELETE", "/orders/coupons/OCTUBRE10"), None)
    assert r["statusCode"] == 200, r["body"]


def test_un_pedido_cerrado_admite_notas_internas(order_lambda, utils, monkeypatch):
    """La gerente reembolsó fuera del sistema y no tenía dónde dejar rastro."""
    import json
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    monkeypatch.setattr(utils, "_extract_actor_from_bearer", lambda h: {"user_id": "sofia"})
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert order_lambda.handle_cancel_order(oid, {}, {})["statusCode"] == 200
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/notes", {"text": "Transferí $165 del envío de regreso el 3-oct"}), None)
    assert r["statusCode"] == 200, r["body"]
    notas = json.loads(r["body"])["order"]["adminNotes"]
    assert notas[0]["text"].startswith("Transferí") and notas[0]["by"] == "sofia"
    assert order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/notes", {"text": ""}), None)["statusCode"] == 400


def test_envio_gratis_por_importe_segun_configuracion(order_lambda, utils, monkeypatch):
    """Un aviso prometía envío gratis desde $1,000 y el checkout cobraba $129 igual."""
    import json
    cfg = utils._load_app_config()
    cfg.setdefault("shipping", {})["freeShippingMin"] = Decimal("1000")
    monkeypatch.setattr(utils, "_load_app_config", lambda *a, **k: cfg)
    _producto(utils)
    cuerpo = {**_pedido_invitado(), "items": [{"productId": 101, "name": "Finding Pro 500g", "price": 800, "quantity": 2}]}
    r = order_lambda.handle_create_order(cuerpo, {})
    o = json.loads(r["body"]); o = o.get("order") or o
    assert float(o["shippingCost"]) == 0 and o["shippingFreeApplied"] is True and float(o["total"]) == 1600.0
    r = order_lambda.handle_create_order(_pedido_invitado(), {})
    o = json.loads(r["body"]); o = o.get("order") or o
    assert float(o["shippingCost"]) == 129 and float(o["total"]) == 929.0


def test_la_pasarela_puede_marcar_pagado_un_pickup_con_pago_en_linea(order_lambda, utils, monkeypatch):
    """Regresión: el webhook de MercadoPago (sin usuario) recibía 403 'no
    vinculado a la sucursal' en pedidos de recoger en tienda pagados en línea,
    y el pedido se quedaba pendiente aunque el cliente ya hubiera pagado."""
    import json as _json
    utils._put_entity("STOCK", "STK-T1", {"entityType": "stock", "stockId": "STK-T1", "name": "Tienda", "allowPickup": True, "linkedUserIds": [], "inventory": {}})
    utils._put_entity("ORDER", "ORD-PK1", {"entityType": "order", "orderId": "ORD-PK1", "customerId": 1, "status": "pending",
                                            "deliveryType": "pickup", "pickupStockId": "STK-T1", "pickupPaymentMethod": "online",
                                            "netTotal": 350, "total": 350, "items": [], "monthKey": utils._month_key()})
    monkeypatch.setattr(order_lambda, "ORDER_SFN_ARN", None, raising=False)
    r = order_lambda.handle_update_status("ORD-PK1", {"status": "paid", "paymentId": "mp-1"}, {})
    assert r["statusCode"] == 200, r["body"]
    assert utils._get_by_id("ORDER", "ORD-PK1")["status"] == "paid"
    # Pago en sucursal sin operador ligado: sigue prohibido.
    utils._put_entity("ORDER", "ORD-PK2", {"entityType": "order", "orderId": "ORD-PK2", "customerId": 1, "status": "pending",
                                            "deliveryType": "pickup", "pickupStockId": "STK-T1", "pickupPaymentMethod": "at_store",
                                            "netTotal": 350, "total": 350, "items": [], "monthKey": utils._month_key()})
    r = order_lambda.handle_update_status("ORD-PK2", {"status": "paid", "paymentMethod": "cash"}, {})
    assert r["statusCode"] == 403


def test_no_se_puede_recoger_en_una_sucursal_sin_existencia(order_lambda, utils):
    """Regresión: Claudia pagó una Biotina para recoger en Del Valle, donde había 0."""
    utils._put_entity("PRODUCT", 901, {"entityType": "product", "productId": 901, "name": "Biotina", "price": 400, "active": True, "vpPoints": 8})
    utils._put_entity("STOCK", "STK-DV", {"entityType": "stock", "stockId": "STK-DV", "name": "Del Valle", "allowPickup": True, "linkedUserIds": [], "inventory": {"901": 0}})
    cuerpo = {"customerId": None, "guest": True, "email": "c@test.com", "customerName": "Claudia", "deliveryType": "pickup", "pickupStockId": "STK-DV",
              "items": [{"productId": 901, "quantity": 1, "price": 400}]}
    r = order_lambda.handle_create_order(cuerpo, {})
    assert r["statusCode"] == 400, r["body"]
    assert "Biotina" in r["body"]
    utils._put_entity("STOCK", "STK-DV", {"entityType": "stock", "stockId": "STK-DV", "name": "Del Valle", "allowPickup": True, "linkedUserIds": [], "inventory": {"901": 3}})
    r = order_lambda.handle_create_order(cuerpo, {})
    assert r["statusCode"] in (200, 201), r["body"]


def test_rechazar_con_cortesia_emite_un_cupon_personal(order_lambda, utils, monkeypatch):
    """Regresión: 'se le ofrece 20% en su próximo bote' vivía solo en el correo;
    la clienta compró y no hubo descuento. Ahora se emite un cupón personal."""
    import json as _json
    enviados = []
    monkeypatch.setattr(order_lambda.utils, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto)), raising=False)
    from core import order_emails as _oe
    monkeypatch.setattr(_oe._correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, texto)), raising=False)
    utils._put_entity("CUSTOMER", 77, {"entityType": "customer", "customerId": 77, "name": "Lupita", "email": "lupita@test.com"})
    utils._put_entity("ORDER", "ORD-R1", {"entityType": "order", "orderId": "ORD-R1", "customerId": 77, "customerName": "Lupita", "email": "lupita@test.com",
                                           "status": "en_devolucion", "returnRequestId": "RET-1", "netTotal": 700, "total": 700, "items": [], "monthKey": utils._month_key()})
    utils._put_entity("RETURN_REQUEST", "RET-1", {"entityType": "returnRequest", "requestId": "RET-1", "orderId": "ORD-R1", "customerId": 77, "status": "PENDIENTE", "motivo": "DANIO"})
    r = order_lambda.handle_return_inspection("ORD-R1", {"inspection": {"sellos_intactos": False}, "rejectionReason": "Sello abierto", "courtesyPercent": 20}, {"Authorization": "Bearer sim-superadmin-token"})
    assert r["statusCode"] == 200, r["body"]
    cupones = [v for (pk, sk), v in utils._table.store.items() if pk == "COUPON" and str(v.get("code", "")).startswith("CORTESIA-")]
    assert len(cupones) == 1 and str(cupones[0]["customerId"]) == "77" and cupones[0]["maxRedemptions"] == 1
    code = cupones[0]["code"]
    assert any(code in (t or "") for _, _, t in enviados), enviados
    # Solo ella puede usarlo.
    assert order_lambda._evaluate_coupon(utils._get_by_id("COUPON", code), 500, 77)["valid"]
    assert not order_lambda._evaluate_coupon(utils._get_by_id("COUPON", code), 500, 78)["valid"]


# ── Paquete C · ronda 26 · propuestas 3 y 31: contratos de los que vive el carrito ──

def test_recoger_en_sucursal_guarda_nombre_y_telefono_de_quien_recoge(order_lambda, utils):
    """Los dos pedidos de mostrador de Aurora quedaron con `recipientName` y `phone` en null
    porque los campos vivían dentro del bloque de envío a domicilio. El backend siempre los
    aceptó en cualquier modo de entrega: esta prueba amarra ese contrato, que es de lo que
    depende el bloque de contacto del carrito."""
    import json
    _producto(utils)
    utils._put_entity("STOCK", "STK-GDL", {"entityType": "stock", "stockId": "STK-GDL",
                                           "name": "Sucursal Guadalajara", "location": "Av. Chapultepec 480",
                                           "city": "Guadalajara", "state": "JAL", "allowPickup": True,
                                           "linkedUserIds": [], "inventory": {"101": 10}})
    cuerpo = {
        "items": [{"productId": 101, "name": "Finding Pro 500g", "price": 800, "quantity": 1}],
        "guest": True, "customerName": "Aurora Vega", "email": "aurora@test.com",
        "recipientName": "Aurora Vega", "phone": "3312345678",
        "deliveryType": "pickup", "pickupStockId": "STK-GDL", "pickupPaymentMethod": "online",
    }
    r = order_lambda.handle_create_order(cuerpo, {})
    assert r["statusCode"] in (200, 201), r["body"]
    d = json.loads(r["body"])
    oid = d.get("orderId") or d["order"]["orderId"]

    guardado = utils._get_by_id("ORDER", oid)
    assert guardado["recipientName"] == "Aurora Vega"
    assert guardado["phone"] == "3312345678"

    # Y el seguimiento del invitado los sigue devolviendo (con el teléfono enmascarado).
    r = order_lambda.lambda_handler(_evento("GET", f"/orders/{oid}"), None)
    pedido = json.loads(r["body"])["order"]
    assert pedido["recipientName"] == "Aurora Vega"
    assert pedido["deliveryType"] == "pickup" and pedido["pickupStockId"] == "STK-GDL"


def test_la_cotizacion_de_envio_solo_necesita_el_codigo_postal(utils):
    """Mariana escribió solo su CP "a propósito, para no dar mi dirección" y no pasó nada.
    El cotizador acepta el CP solo, pero rechaza la dirección a medias: o todos los campos o
    ninguno. Por eso el carrito le manda únicamente `zipTo` y los bultos."""
    import shipping_lambda

    def cotizar(cuerpo):
        return shipping_lambda.lambda_handler(_evento("POST", "/shipping/quote", cuerpo), None)

    solo_cp = cotizar({"zipTo": "03100", "items": [{"weightKg": 0.5, "lengthCm": 20, "widthCm": 15,
                                                    "heightCm": 10, "quantity": 1}]})
    assert solo_cp["statusCode"] == 200, solo_cp["body"]

    # Añadirle el estado sin el resto de la dirección lo rompe: es la premisa que corrige
    # la propuesta 31 y la razón de no mandar campos sueltos.
    con_estado = cotizar({"zipTo": "03100", "state": "CMX"})
    assert con_estado["statusCode"] == 400, con_estado["body"]

    assert cotizar({"zipTo": "031"})["statusCode"] == 400


def test_dar_por_cobrado_a_mano_guarda_la_referencia_del_deposito(order_lambda, utils):
    """Ronda 7 · Marisol: «"Marcar como pagado" mueve dinero de un clic: sin
    confirmación, sin referencia y sin deshacer». La pantalla ya pregunta; el
    servidor guarda con qué se dio por cobrado, que es lo que después permite
    cuadrar el banco."""
    _producto(utils)
    respuesta = order_lambda.handle_create_order(_pedido_invitado(), {})
    oid = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")["orderId"]

    admin = {"x-user-id": "1", "x-user-role": "admin"}
    r = order_lambda.handle_update_status(oid, {"status": "paid", "paymentReference": "SPEI 4482910"}, admin)
    assert r["statusCode"] == 200, r["body"]

    pedido = utils._get_by_id("ORDER", oid)
    assert pedido["status"] == "paid"
    assert pedido["paymentReference"] == "SPEI 4482910"


def test_sin_referencia_el_pedido_no_inventa_una(order_lambda, utils):
    _producto(utils)
    order_lambda.handle_create_order(_pedido_invitado(), {})
    oid = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")["orderId"]
    admin = {"x-user-id": "1", "x-user-role": "admin"}

    order_lambda.handle_update_status(oid, {"status": "paid", "paymentReference": "   "}, admin)

    assert "paymentReference" not in utils._get_by_id("ORDER", oid)


def test_un_pedido_de_invitado_lleva_un_nombre_con_el_que_se_pueda_llamar(order_lambda, utils):
    """Ronda 7 · Marisol: «cuatro de cuatro pendientes aparecen como "Cliente",
    sin nombre de persona… no hay a quién llamarle para cobrar un pendiente de 5
    días». El dato estaba en el propio pedido."""
    _producto(utils)
    pedido = _pedido_invitado()
    pedido.pop("customerName")
    order_lambda.handle_create_order(pedido, {})

    guardado = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")
    assert guardado["customerName"] == "Lucía Fernández"   # el nombre de a quién se le entrega


def test_sin_nombre_ni_destinatario_queda_el_correo_antes_que_la_palabra_cliente(order_lambda, utils):
    _producto(utils)
    pedido = _pedido_invitado()
    pedido.pop("customerName")
    pedido.pop("recipientName")
    order_lambda.handle_create_order(pedido, {})

    guardado = next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")
    assert guardado["customerName"] == "lucia@test.com"
