"""Modo cliente / modo socio (paquete B, propuesta 1).

"Yo quería un bote de proteína y salí dado de alta como vendedor" (ivan-dia5).
Todo registro nuevo nace cliente: compra a precio de lista, no ve red ni
comisiones y cada compra le dice cuánto habría ahorrado como socia.
"""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def modulos(utils):
    import auth_utils, customer_lambda, order_lambda, commissions_lambda, modo_handlers
    return auth_utils, customer_lambda, order_lambda, commissions_lambda, modo_handlers


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, html)))
    return enviados


def _alta(auth, nombre, correo, referido=None):
    cuerpo = {"name": nombre, "email": correo, "password": "Secreta123!", "confirmPassword": "Secreta123!"}
    if referido:
        cuerpo["referralToken"] = referido
    r = auth.handle_create_account(cuerpo)
    assert r["statusCode"] in (200, 201), r["body"]
    return json.loads(r["body"])["customerId"]


def _ficha(utils, cid):
    return utils._get_by_id("CUSTOMER", cid)


def _sesion(utils, cid, role="cliente"):
    token = f"session-token-{cid}"
    utils._put_session(token, {"sessionId": token, "userId": str(cid), "role": role,
                               "privileges": {}, "canAccessAdmin": False})
    return {"Authorization": f"Bearer {token}"}


def _evento(metodo, ruta, cuerpo=None, headers=None):
    return {"httpMethod": metodo, "path": ruta, "headers": headers or {},
            "queryStringParameters": {}, "body": json.dumps(cuerpo or {})}


def _producto(utils, pid=9, precio=480, pc=10, nombre="Klinhart"):
    utils._put_entity("PRODUCT", pid, {"entityType": "product", "productId": pid, "name": nombre,
                                       "price": precio, "vpPoints": pc, "active": True})
    return pid


def _pedido(cid, pid, qty=2, precio=480):
    return {"customerId": cid, "customerName": "Karla", "items": [{"productId": pid, "name": "Klinhart", "price": precio, "quantity": qty}],
            "recipientName": "Karla", "deliveryType": "shipping",
            "shippingAddress": {"street": "x", "number": "1", "city": "Qro", "state": "Qro", "postalCode": "76000", "country": "MX"}}


def _crear_y_pagar(order_lambda, commissions_lambda, cuerpo):
    r = order_lambda.handle_create_order(cuerpo, {})
    assert r["statusCode"] in (200, 201), r["body"]
    pedido = json.loads(r["body"])["order"]
    r = order_lambda.handle_update_status(pedido["orderId"], {"status": "paid"}, {})
    assert r["statusCode"] == 200, r["body"]
    commissions_lambda.lambda_handler({"orderId": pedido["orderId"], "action": "ORDER_PAID"}, None)
    return pedido["orderId"]


# ── El modo de la cuenta ───────────────────────────────────────────────────

def test_un_registro_nuevo_nace_cliente(modulos, utils):
    auth, _, _, _, modo = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    ficha = _ficha(utils, cid)
    assert ficha["mode"] == "cliente" and ficha["modeReason"] == "registro"
    assert modo.modo_de(ficha) == "cliente"


def test_una_ficha_sin_atributo_es_socio(modulos, utils):
    """Las socias anteriores a esta ronda no cambian."""
    _, _, _, _, modo = modulos
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Rodrigo", "email": "r@test.com"})
    assert modo.modo_de(_ficha(utils, 555)) == "socio"
    assert modo.modo_de({}) == "socio" and modo.modo_de(None) == "socio"


def test_registrarse_con_el_codigo_de_alguien_lo_vuelve_socio(modulos, utils):
    """Quien ya tiene red es socio aunque nunca lo haya pedido."""
    auth, _, _, _, _ = modulos
    lider = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    assert _ficha(utils, lider)["mode"] == "cliente"
    invitada = _alta(auth, "Karla Méndez", "karla@test.com", referido=_ficha(utils, lider)["referralCode"])
    assert _ficha(utils, invitada)["mode"] == "cliente"
    assert _ficha(utils, lider)["mode"] == "socio"
    assert _ficha(utils, lider)["modeReason"] == "referido"


def test_una_fila_de_comision_vuelve_socio_al_beneficiario(modulos, utils):
    auth, _, order_lambda, commissions_lambda, _ = modulos
    lider = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    # Se fuerza la relación sin pasar por el código para que el líder siga en cliente.
    invitada = _alta(auth, "Karla Méndez", "karla@test.com")
    utils._update_by_id("CUSTOMER", invitada, "SET leaderId = :l", {":l": lider})
    utils._update_by_id("CUSTOMER", lider, "SET #m = :m", {":m": "cliente"}, names={"#m": "mode"})
    utils._sync_customer_network_metadata()
    pid = _producto(utils)
    _crear_y_pagar(order_lambda, commissions_lambda, _pedido(invitada, pid))
    assert _ficha(utils, lider)["mode"] == "socio"
    assert _ficha(utils, lider)["modeReason"] == "comision"


def test_el_login_dice_el_modo(modulos, utils):
    auth, _, _, _, _ = modulos
    _alta(auth, "Karla Méndez", "karla@test.com")
    utils._update_by_id("AUTH", "karla@test.com", "SET emailVerified = :v", {":v": True})
    r = auth.handle_login({"username": "karla@test.com", "password": "Secreta123!"})
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["user"]["mode"] == "cliente"


# ── Activar modo socio ─────────────────────────────────────────────────────

def test_activar_modo_socio_es_idempotente_y_avisa_una_vez(modulos, utils, buzon):
    auth, customer_lambda, _, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    buzon.clear()
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {"acceptedPlanVersion": "abril-2026"}, _sesion(utils, cid)), None)
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["mode"] == "socio" and datos["alreadyPartner"] is False and datos["modeActivatedAt"]
    assert datos["name"] == "Karla Méndez"   # la confirmación muestra lo guardado
    ficha = _ficha(utils, cid)
    assert ficha["mode"] == "socio" and ficha["modeReason"] == "solicitud" and ficha["acceptedPlanVersion"] == "abril-2026"
    assert [a for _, a, _ in buzon] == ["Tu cuenta ya está en modo socio"]

    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {}, _sesion(utils, cid)), None)
    assert json.loads(r["body"])["alreadyPartner"] is True
    assert len(buzon) == 1


def test_sin_sesion_no_se_puede_activar(modulos, utils):
    _, customer_lambda, _, _, _ = modulos
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {}), None)
    assert r["statusCode"] == 401
    r = customer_lambda.lambda_handler(_evento("GET", "/customers/modo"), None)
    assert r["statusCode"] == 401


def test_una_clienta_no_puede_cambiar_el_modo_de_otra(modulos, utils):
    auth, customer_lambda, _, _, _ = modulos
    karla = _alta(auth, "Karla Méndez", "karla@test.com")
    tomas = _alta(auth, "Tomás Ibarra", "tomas@test.com")
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {"customerId": tomas}, _sesion(utils, karla)), None)
    assert r["statusCode"] == 403
    assert _ficha(utils, tomas)["mode"] == "cliente"


def test_un_admin_cambia_el_modo_desde_la_ficha_en_ambos_sentidos(modulos, utils, buzon):
    auth, customer_lambda, _, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    admin = {"x-user-id": "1", "x-user-role": "admin"}
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {"customerId": cid}, admin), None)
    assert r["statusCode"] == 200, r["body"]
    assert _ficha(utils, cid)["mode"] == "socio" and _ficha(utils, cid)["modeReason"] == "admin"
    assert not [a for _, a, _ in buzon if "modo socio" in a]   # el cambio por admin no manda correo

    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {"customerId": cid, "mode": "cliente"}, admin), None)
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["mode"] == "cliente"
    assert _ficha(utils, cid)["mode"] == "cliente"

    # Un empleado sin `customer_add` no puede.
    empleado = {"x-user-id": "2", "x-user-role": "employee", "x-user-privileges": json.dumps({"access_screen_customers": True})}
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/modo-socio", {"customerId": cid}, empleado), None)
    assert r["statusCode"] == 403


def test_la_lista_y_la_ficha_del_back_office_traen_el_modo(modulos, utils):
    auth, customer_lambda, _, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Rodrigo", "email": "r@test.com"})
    admin = {"x-user-id": "1", "x-user-role": "admin"}
    r = customer_lambda.lambda_handler(_evento("GET", f"/customers/{cid}", None, admin), None)
    assert json.loads(r["body"])["customer"]["mode"] == "cliente"
    r = customer_lambda.lambda_handler(_evento("GET", "/customers/getall", None, admin), None)
    modos = {c["name"]: c["mode"] for c in json.loads(r["body"])["customers"]}
    assert modos == {"Karla Méndez": "cliente", "Rodrigo": "socio"}


# ── El pedido en modo cliente ──────────────────────────────────────────────

def test_en_modo_cliente_se_paga_precio_de_lista_y_se_guarda_el_ahorro(modulos, utils):
    """$960 → sin descuento y "con $40 más tendrías 10 %"; $1,200 → habrías ahorrado $120."""
    auth, _, order_lambda, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    pid = _producto(utils)

    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid, qty=2), {})["body"])["order"]
    assert pedido["buyerType"] == "associate"
    assert Decimal(str(pedido["discountRate"])) == 0 and Decimal(str(pedido["netTotal"])) == Decimal("960")
    assert pedido["partnerMode"] == "cliente"
    assert Decimal(str(pedido["partnerSavings"])) == 0
    assert Decimal(str(pedido["partnerSavingsNextMissing"])) == Decimal("40")
    assert Decimal(str(pedido["partnerSavingsNextRate"])) == Decimal("0.10")

    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid, qty=1, precio=1200), {})["body"])["order"]
    assert Decimal(str(pedido["discountRate"])) == 0 and Decimal(str(pedido["netTotal"])) == Decimal("1200")
    assert Decimal(str(pedido["partnerSavings"])) == Decimal("120")
    assert Decimal(str(pedido["partnerSavingsRate"])) == Decimal("0.10")


def test_el_ahorro_cuenta_el_acumulado_del_mes(modulos, utils):
    """Con $900 ya comprados, una compra de $300 habría tenido 10 % sobre los $300."""
    auth, _, order_lambda, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    utils._put_entity("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()),
                      {"entityType": "associateMonth", "associateId": str(cid), "monthKey": utils._month_key(), "netVolume": Decimal("900")})
    pid = _producto(utils)
    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid, qty=1, precio=300), {})["body"])["order"]
    assert Decimal(str(pedido["discountRate"])) == 0
    assert Decimal(str(pedido["partnerSavings"])) == Decimal("30")
    assert Decimal(str(pedido["partnerSavingsProjected"])) == Decimal("1200")


def test_en_modo_socio_la_escalera_aplica_y_el_ahorro_es_cero(modulos, utils):
    _, _, order_lambda, _, _ = modulos
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Rodrigo", "email": "r@test.com"})
    pid = _producto(utils)
    pedido = json.loads(order_lambda.handle_create_order(_pedido(555, pid, qty=1, precio=1200), {})["body"])["order"]
    assert Decimal(str(pedido["discountRate"])) == Decimal("0.10")
    assert Decimal(str(pedido["netTotal"])) == Decimal("1080")
    assert pedido["partnerMode"] == "socio" and Decimal(str(pedido["partnerSavings"])) == 0


def test_el_invitado_tambien_ve_su_ahorro(modulos, utils):
    _, _, order_lambda, _, _ = modulos
    pid = _producto(utils)
    cuerpo = {**_pedido(None, pid, qty=1, precio=1200), "customerId": None, "guest": True, "email": "x@test.com"}
    pedido = json.loads(order_lambda.handle_create_order(cuerpo, {})["body"])["order"]
    assert pedido["partnerMode"] == "invitado" and Decimal(str(pedido["partnerSavings"])) == Decimal("120")


def test_la_compra_en_modo_cliente_acredita_volumen_y_paga_comision_a_su_linea(modulos, utils):
    """El volumen se sigue acreditando (la activación es inmediata al cambiar de modo)
    y la patrocinadora cobra igual: el motor no cambia."""
    auth, _, order_lambda, commissions_lambda, _ = modulos
    lider = _alta(auth, "Marcela Ortiz", "marcela@test.com")
    invitada = _alta(auth, "Karla Méndez", "karla@test.com", referido=_ficha(utils, lider)["referralCode"])
    pid = _producto(utils)
    oid = _crear_y_pagar(order_lambda, commissions_lambda, _pedido(invitada, pid, qty=2))
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(invitada, utils._month_key()))
    assert estado and Decimal(str(estado["netVolume"])) == Decimal("960")
    mes = utils._get_ledger_month(lider, utils._month_key())
    assert mes and any(r.get("orderId") == oid for r in mes.get("ledger") or [])


# ── El correo de pago ──────────────────────────────────────────────────────

def test_el_correo_de_pago_de_una_clienta_lleva_el_ahorro_y_el_de_un_socio_no(modulos, utils, buzon):
    auth, _, order_lambda, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Rodrigo", "email": "r@test.com"})
    pid = _producto(utils)
    buzon.clear()

    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid, qty=1, precio=1200), {})["body"])["order"]
    order_lambda.handle_update_status(pedido["orderId"], {"status": "paid"}, {})
    para, asunto, html = buzon[-1]
    assert para == "karla@test.com" and "Recibimos tu pago" in asunto
    assert "Como socia habrías ahorrado <strong>$120.00</strong>" in html
    assert f"/#/modo-socio?desde=orden&id={pedido['orderId']}" in html

    pedido = json.loads(order_lambda.handle_create_order(_pedido(cid, pid, qty=2), {})["body"])["order"]
    order_lambda.handle_update_status(pedido["orderId"], {"status": "paid"}, {})
    assert "con <strong>$40.00</strong> más de compra este mes tendrías 10 % de descuento" in buzon[-1][2]

    pedido = json.loads(order_lambda.handle_create_order(_pedido(555, pid, qty=1, precio=1200), {})["body"])["order"]
    order_lambda.handle_update_status(pedido["orderId"], {"status": "paid"}, {})
    assert buzon[-1][0] == "r@test.com" and "Como socia" not in buzon[-1][2] and "modo-socio" not in buzon[-1][2]


# ── El panel ───────────────────────────────────────────────────────────────

def test_el_panel_en_modo_cliente_no_trae_red_ni_comisiones_y_si_indicadores(modulos, utils):
    auth, customer_lambda, order_lambda, commissions_lambda, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    pid = _producto(utils)
    _crear_y_pagar(order_lambda, commissions_lambda, _pedido(cid, pid, qty=1, precio=1200))

    r = customer_lambda.lambda_handler(_evento("GET", "/customers/dashboard", None, _sesion(utils, cid)), None)
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["mode"] == "cliente"
    assert datos["networkMembers"] == [] and datos["commissions"] is None
    assert datos["vp"] == 0 and datos["vg"] == 0 and datos["rank"] == "" and datos["bonuses"] == []
    assert datos["user"]["discountPercent"] == 0 and datos["user"]["discountActive"] is False
    assert [g["key"] for g in datos["goals"]] == ["active"]
    assert datos["goals"][0]["title"] == "Meta de compra del mes"
    ind = datos["clientIndicators"]
    assert ind["monthSpend"] == 1200.0
    assert ind["monthVp"] > 0, "los VP se acumulan aunque esté en modo cliente: la tabla no debe decir «llevas 0»"
    assert ind["monthSavingsIfPartner"] == 120.0
    assert ind["currentRateIfPartner"] == 0.10
    assert ind["nextTier"] == {"rate": 0.20, "missing": 800.0}
    assert ind["exampleEarnings"] == {"friends": 2, "purchaseEach": 1000.0, "rate": 0.10, "total": 200.0}


def test_el_panel_en_modo_socio_es_el_de_siempre(modulos, utils):
    _, customer_lambda, _, _, _ = modulos
    utils._put_entity("CUSTOMER", 555, {"entityType": "customer", "customerId": 555, "name": "Rodrigo", "email": "r@test.com"})
    r = customer_lambda.lambda_handler(_evento("GET", "/customers/dashboard", None, _sesion(utils, 555)), None)
    datos = json.loads(r["body"])
    assert datos["mode"] == "socio" and "clientIndicators" not in datos
    assert datos["commissions"] is not None and len(datos["goals"]) > 1


def test_get_modo_devuelve_el_modo_y_los_indicadores(modulos, utils):
    auth, customer_lambda, _, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    r = customer_lambda.lambda_handler(_evento("GET", "/customers/modo", None, _sesion(utils, cid)), None)
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos["mode"] == "cliente" and datos["modeSince"] and datos["planVersion"] == "abril-2026"
    assert datos["indicators"]["monthSpend"] == 0 and datos["indicators"]["nextTier"] == {"rate": 0.10, "missing": 1000.0}


# ── Cálculo público del ahorro ─────────────────────────────────────────────

def test_ahorro_socio_publico_calcula_con_la_escalera_real(modulos, utils):
    _, customer_lambda, _, _, _ = modulos
    r = customer_lambda.lambda_handler(_evento("POST", "/customers/ahorro-socio", {"items": [{"price": 600, "quantity": 2}]}), None)
    assert r["statusCode"] == 200, r["body"]
    datos = json.loads(r["body"])
    assert datos == {"gross": 1200.0, "monthNet": 0.0, "projected": 1200.0, "rate": 0.10, "savings": 120.0,
                     "nextTier": {"rate": 0.20, "missing": 800.0}}


def test_ahorro_socio_rechaza_lineas_invalidas(modulos, utils):
    _, customer_lambda, _, _, _ = modulos
    for cuerpo in ({}, {"items": []}, {"items": [{"price": -1, "quantity": 1}]}, {"items": [{"price": 10, "quantity": 0}]}, {"items": "x"}):
        r = customer_lambda.lambda_handler(_evento("POST", "/customers/ahorro-socio", cuerpo), None)
        assert r["statusCode"] == 400, cuerpo


def test_ahorro_socio_solo_usa_el_neto_del_mes_de_la_propia_sesion(modulos, utils):
    """Sin sesión, `customerId` no revela lo que otra persona compró."""
    auth, customer_lambda, _, _, _ = modulos
    cid = _alta(auth, "Karla Méndez", "karla@test.com")
    utils._put_entity("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, utils._month_key()),
                      {"entityType": "associateMonth", "associateId": str(cid), "monthKey": utils._month_key(), "netVolume": Decimal("900")})
    cuerpo = {"items": [{"price": 300, "quantity": 1}], "customerId": cid}
    anonimo = json.loads(customer_lambda.lambda_handler(_evento("POST", "/customers/ahorro-socio", cuerpo), None)["body"])
    assert anonimo["monthNet"] == 0 and anonimo["savings"] == 0
    propio = json.loads(customer_lambda.lambda_handler(_evento("POST", "/customers/ahorro-socio", cuerpo, _sesion(utils, cid)), None)["body"])
    assert propio["monthNet"] == 900.0 and propio["savings"] == 30.0
