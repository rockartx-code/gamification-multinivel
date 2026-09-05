"""La casilla que guarda la dirección (paquete G, propuesta 19).

Ernesto palomeó "Guardar esta dirección para futuras compras", le puso alias
"Casa" y compró. El pedido quedó con `shippingAddressLabel: 'Casa'` y su ficha
siguió con `addresses = 0` — igual que las siete fichas de clientes del mundo
sembrado: `handle_create_order` **nunca leía** `saveShippingAddress`.

Encadenado: sin dirección guardada la suscripción no se puede crear. Ernesto
llenó todo —Klinhart, día 5, envío a su domicilio— y le salió *"Aún no tienes
direcciones guardadas"*, en un mensaje que además lo mandaba a guardarla con la
casilla que acababa de usar. En todo marzo no se dio de alta ni una suscripción.

Y el único camino de escritura de direcciones que existía, `PATCH /customers/{id}`,
exigía mandar además una llave `shippingAddress` que no se usa para nada.
"""
import json

import pytest

ADMIN = {"x-user-id": "1", "x-user-role": "admin", "x-user-privileges": json.dumps({"user_manage_privileges": True})}

DIRECCION = {
    "street": "Av. Constitución", "number": "1500", "address": "Av. Constitución 1500, Centro",
    "city": "Monterrey", "state": "Nuevo León", "postalCode": "64000", "country": "MX",
    "betweenStreets": "Hidalgo y Padre Mier", "references": "Portón verde",
}


@pytest.fixture
def mundo(utils):
    import order_lambda, customer_lambda
    utils._put_entity("CUSTOMER", 700, {"entityType": "customer", "customerId": 700, "name": "Ernesto Salas",
                                        "email": "ernesto@test.com", "phone": "8112223344",
                                        "createdAt": utils._now_iso()})
    utils._put_entity("PRODUCT", "P-KLIN", {"entityType": "product", "productId": "P-KLIN", "name": "Klinhart",
                                            "price": 480, "stock": 50, "isActive": True})
    return order_lambda, customer_lambda


def _crear(order_lambda, cuerpo):
    return order_lambda.lambda_handler({"httpMethod": "POST", "path": "/orders/create", "headers": ADMIN,
                                        "queryStringParameters": None, "body": json.dumps(cuerpo)}, None)


def _pedido_base(**extra):
    cuerpo = {
        "customerId": 700, "customerName": "Ernesto Salas", "email": "ernesto@test.com",
        "phone": "8112223344", "deliveryType": "delivery",
        "items": [{"productId": "P-KLIN", "quantity": 1}],
        "shippingAddress": dict(DIRECCION),
    }
    cuerpo.update(extra)
    return cuerpo


def test_palomear_la_casilla_guarda_la_direccion_en_la_ficha(mundo, utils):
    """*"Aún no tienes direcciones guardadas"* justo después de guardarla."""
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    pedido = json.loads(r["body"])["order"]

    ficha = utils._get_by_id("CUSTOMER", 700)
    direcciones = ficha.get("addresses") or []
    assert len(direcciones) == 1, "la ficha seguía con addresses = 0"
    guardada = direcciones[0]
    assert guardada["label"] == "Casa"
    assert guardada["street"] == "Av. Constitución" and guardada["number"] == "1500"
    assert guardada["postalCode"] == "64000" and guardada["state"] == "Nuevo León"
    assert guardada["isDefault"] is True, "la primera dirección queda como la de siempre"
    assert guardada.get("id"), "sin id no se puede elegir después en el carrito"
    # El pedido deja rastro de con qué dirección guardada se hizo.
    assert pedido["savedShippingAddressId"] == guardada["id"]


def test_sin_la_casilla_no_se_guarda_nada(mundo, utils):
    """Quien no la palomea no encuentra su dirección en el perfil al día siguiente."""
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    assert not (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])
    assert json.loads(r["body"])["order"].get("savedShippingAddressId") is None


def test_repetir_la_compra_no_duplica_la_direccion(mundo, utils):
    """Se deduplica por calle + número + CP; el alias nuevo sí se respeta."""
    order_lambda, _ = mundo
    _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa"))
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa de siempre"))
    assert r["statusCode"] == 201, r["body"]
    direcciones = utils._get_by_id("CUSTOMER", 700).get("addresses") or []
    assert len(direcciones) == 1
    assert direcciones[0]["label"] == "Casa de siempre"


def test_una_direccion_distinta_se_suma_sin_pisar_la_anterior(mundo, utils):
    order_lambda, _ = mundo
    _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa"))
    otra = dict(DIRECCION, street="Río Nazas", number="88", address="Río Nazas 88", postalCode="64650")
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Oficina",
                                          shippingAddress=otra))
    assert r["statusCode"] == 201, r["body"]
    direcciones = utils._get_by_id("CUSTOMER", 700).get("addresses") or []
    assert sorted(d["label"] for d in direcciones) == ["Casa", "Oficina"]
    # La primera sigue siendo la de siempre: guardar otra no cambia la elegida.
    assert [d["label"] for d in direcciones if d.get("isDefault")] == ["Casa"]


def test_elegir_una_direccion_ya_guardada_no_crea_otra(mundo, utils):
    """El carrito manda `shippingAddressId` cuando la persona la elige de la lista."""
    order_lambda, _ = mundo
    _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa"))
    guardada = (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])[0]
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressId=guardada["id"],
                                          shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    direcciones = utils._get_by_id("CUSTOMER", 700).get("addresses") or []
    assert len(direcciones) == 1 and direcciones[0]["id"] == guardada["id"]
    assert json.loads(r["body"])["order"]["savedShippingAddressId"] == guardada["id"]


def test_un_pedido_de_invitado_no_guarda_direccion_en_ninguna_ficha(mundo, utils):
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(customerId=None, saveShippingAddress=True, shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    assert not (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])


def test_recoger_en_sucursal_no_guarda_la_direccion_de_la_tienda(mundo, utils):
    """La sucursal no es la casa de nadie."""
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(deliveryType="pickup", saveShippingAddress=True,
                                          shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    assert not (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])


def test_sin_alias_la_direccion_se_guarda_con_un_nombre_util(mundo, utils):
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True))
    assert r["statusCode"] == 201, r["body"]
    direcciones = utils._get_by_id("CUSTOMER", 700).get("addresses") or []
    assert direcciones and direcciones[0]["label"] == "Monterrey"


def test_una_direccion_vacia_no_se_guarda(mundo, utils):
    order_lambda, _ = mundo
    r = _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddress={}, shippingAddressLabel="Casa"))
    assert r["statusCode"] == 201, r["body"]
    assert not (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])


def test_el_panel_de_admin_puede_guardar_direcciones_sin_mandar_una_llave_de_relleno(mundo, utils):
    """`PATCH /customers/{id}` exigía además `shippingAddress`, que no se usa.

    Era el único camino de escritura de direcciones que existía, y estaba
    cerrado con llave.
    """
    _, customer_lambda = mundo
    entrada = [dict(DIRECCION, id="addr-1", label="Casa", isDefault=True)]
    r = customer_lambda.lambda_handler({"httpMethod": "PATCH", "path": "/customers/700", "headers": ADMIN,
                                        "queryStringParameters": None,
                                        "body": json.dumps({"addresses": entrada})}, None)
    assert r["statusCode"] == 200, r["body"]
    ficha = utils._get_by_id("CUSTOMER", 700)
    assert [d["label"] for d in (ficha.get("addresses") or [])] == ["Casa"]
    assert [d["label"] for d in (ficha.get("shippingAddresses") or [])] == ["Casa"]


def test_la_direccion_guardada_sale_en_el_panel_del_cliente(mundo, utils):
    """Lo que la suscripción lee para dejar de decir "Aún no tienes direcciones"."""
    order_lambda, customer_lambda = mundo
    _crear(order_lambda, _pedido_base(saveShippingAddress=True, shippingAddressLabel="Casa"))
    normalizada = customer_lambda._normalize_dashboard_customer(utils._get_by_id("CUSTOMER", 700))
    assert [d["label"] for d in normalizada["addresses"]] == ["Casa"]
    assert normalizada["defaultAddressId"] == normalizada["addresses"][0]["id"]


def test_la_persona_puede_dar_de_alta_su_direccion_desde_su_propio_perfil(mundo, utils):
    """La otra mitad de la propuesta 19: *"y que la suscripción deje capturar una
    dirección ahí mismo"*. Sin esto, quien no compró antes con la casilla
    palomeada seguía sin poder dar de alta la suscripción con envío a domicilio,
    y el aviso lo mandaba de vuelta a la casilla del carrito."""
    _, customer_lambda = mundo
    token = "session-token-ernesto"
    utils._put_session(token, {"sessionId": token, "userId": "700", "role": "cliente",
                               "name": "Ernesto Salas", "privileges": {}})
    cabeceras = {"Authorization": f"Bearer {token}"}

    r = customer_lambda.lambda_handler({"httpMethod": "PATCH", "path": "/customers/profile", "headers": cabeceras,
                                        "queryStringParameters": None,
                                        "body": json.dumps({"newAddress": {**DIRECCION, "label": "Casa",
                                                                           "recipientName": "Ernesto Salas"}})}, None)
    assert r["statusCode"] == 200, r["body"]
    direcciones = json.loads(r["body"])["customer"]["addresses"]
    assert len(direcciones) == 1
    guardada = direcciones[0]
    assert guardada["label"] == "Casa" and guardada["postalCode"] == "64000"
    assert guardada["id"] and guardada["isDefault"] is True, "la primera queda como la de siempre"

    # La misma dirección otra vez no duplica la lista (misma dedupe que el checkout).
    r = customer_lambda.lambda_handler({"httpMethod": "PATCH", "path": "/customers/profile", "headers": cabeceras,
                                        "queryStringParameters": None,
                                        "body": json.dumps({"newAddress": {**DIRECCION, "label": "Casa"}})}, None)
    assert len(json.loads(r["body"])["customer"]["addresses"]) == 1


def test_sin_sesion_no_se_le_escribe_una_direccion_a_nadie(mundo, utils):
    _, customer_lambda = mundo
    r = customer_lambda.lambda_handler({"httpMethod": "PATCH", "path": "/customers/profile", "headers": {},
                                        "queryStringParameters": None,
                                        "body": json.dumps({"newAddress": dict(DIRECCION)})}, None)
    assert r["statusCode"] == 401, r["body"]
    assert not (utils._get_by_id("CUSTOMER", 700).get("addresses") or [])
