"""Plantillas de WhatsApp y nota de contacto (paquete F, tarea 6 de docs/qa/22).

Ivonne redactaba el mismo mensaje unas siete veces por turno y después anotaba
la nota a mano; Sofía igual con la CLABE de Claudia y Bety. Al pulsar "Abrir
WhatsApp" el sistema prellena el enlace `wa.me` y deja la nota con canal,
plantilla y hora.
"""
import json
from urllib.parse import unquote

import pytest

COACH = {"x-user-id": "900", "x-user-role": "employee", "x-user-name": "Ivonne Castro",
         "x-user-privileges": json.dumps({"access_screen_customers": True})}
SIN_PRIVILEGIO = {"x-user-id": "77", "x-user-role": "employee", "x-user-privileges": "{}"}


@pytest.fixture
def modulos(utils):
    import customer_lambda, seguimiento_handlers
    utils._put_entity("CUSTOMER", 11, {"entityType": "customer", "customerId": 11, "name": "Rosa Elena Ortiz",
                                       "email": "rosa@test.com", "phone": "+52 1 55 1234 5678", "createdAt": utils._now_iso()})
    utils._put_entity("CUSTOMER", 14, {"entityType": "customer", "customerId": 14, "name": "Karla Méndez",
                                       "email": "karla@test.com", "phone": "5511112222", "doNotContact": True, "createdAt": utils._now_iso()})
    utils._put_entity("ORDER", "ORD-HEC1", {"entityType": "order", "orderId": "ORD-HEC1", "customerId": None, "buyerType": "guest",
                                            "customerName": "Héctor Mora", "email": "hector@test.com", "phone": "55 9988 7766",
                                            "status": "delivered", "total": 500, "createdAt": utils._now_iso()})
    return customer_lambda, seguimiento_handlers


def _post(customer_lambda, ruta, body, headers=COACH):
    return customer_lambda.lambda_handler({"httpMethod": "POST", "path": ruta, "headers": headers,
                                           "queryStringParameters": None, "body": json.dumps(body)}, None)


def test_las_plantillas_traen_las_cuatro_situaciones_y_sus_marcadores(modulos):
    customer_lambda, _ = modulos
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/plantillas", "headers": COACH,
                                        "queryStringParameters": None, "body": ""}, None)
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    # La situación `activa` existía y no tenía plantilla: la pantalla rellenaba
    # con `fria` y Gaby estuvo a un clic de mandarle "hace tiempo que no te
    # vemos" a Julio, con el pedido entregado el viernes (propuesta 11).
    assert set(cuerpo["templates"]) == {"bienvenida", "fria", "clabe_pendiente", "pedido_tardio", "activa"}
    assert "{nombre}" in cuerpo["templates"]["fria"]["text"] and "{coach}" in cuerpo["templates"]["fria"]["text"]
    assert "{monto}" in cuerpo["templates"]["clabe_pendiente"]["text"]
    assert "{folio}" in cuerpo["templates"]["pedido_tardio"]["text"]
    assert cuerpo["placeholders"] == ["{nombre}", "{coach}", "{producto}", "{monto}", "{folio}"]


def test_la_configuracion_sobreescribe_una_plantilla_sin_tocar_las_demas(modulos, utils):
    customer_lambda, _ = modulos
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "config": {
        "seguimiento": {"templates": {"fria": {"text": "Hola {nombre}, te extrañamos en Finding'U."}}}}})
    utils._invalidate_app_config_cache()
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/plantillas", "headers": COACH,
                                        "queryStringParameters": None, "body": ""}, None)
    plantillas = json.loads(r["body"])["templates"]
    assert plantillas["fria"]["text"] == "Hola {nombre}, te extrañamos en Finding'U."
    assert plantillas["fria"]["title"] == "Cliente fría"
    assert "{producto}" not in plantillas["fria"]["text"] and "{coach}" in plantillas["bienvenida"]["text"]


def test_renderizar_sustituye_los_marcadores(modulos):
    _, seguimiento = modulos
    texto = seguimiento.renderizar("Hola {nombre}, soy {coach}. ¿Qué tal {producto} ({monto}, {folio})?",
                                   {"nombre": "Rosa", "coach": "Ivonne", "producto": "Colágeno", "monto": "$960.00", "folio": "ORD-1"})
    assert texto == "Hola Rosa, soy Ivonne. ¿Qué tal Colágeno ($960.00, ORD-1)?"
    assert seguimiento.renderizar("{nombre}{desconocido}", {}) == "{desconocido}"


def test_abrir_whatsapp_deja_la_nota_con_canal_plantilla_y_hora(modulos, utils):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "whatsapp", "templateKey": "fria", "message": "Hola Rosa, soy Ivonne de Finding'U. ¿Cómo te fue con Colágeno?"})
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    nota = cuerpo["note"]
    assert nota["channel"] == "whatsapp" and nota["templateKey"] == "fria" and nota["by"] == "900"
    assert nota["text"].startswith("WhatsApp · plantilla fría: Hola Rosa")
    assert nota["at"] == cuerpo["lastContactAt"]
    assert cuerpo["customerName"] == "Rosa Elena Ortiz"
    # El teléfono "+52 1 55 1234 5678" queda en 10 dígitos y el texto viaja prellenado.
    assert cuerpo["whatsappUrl"].startswith("https://wa.me/525512345678?text=")
    assert unquote(cuerpo["whatsappUrl"].split("text=")[1]).startswith("Hola Rosa, soy Ivonne")

    ficha = utils._get_by_id("CUSTOMER", 11)
    assert ficha["lastContactAt"] == nota["at"]
    assert ficha["contactNotes"][-1]["templateKey"] == "fria"
    # La ficha de Clientes lo pinta como cualquier otra nota.
    salida = customer_lambda._format_customer_output(ficha)
    assert salida["lastContactAt"] == nota["at"] and salida["contactNotes"][-1]["channel"] == "whatsapp"


def test_no_contactar_bloquea_la_nota(modulos, utils):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/14/contacto", {"channel": "whatsapp", "templateKey": "fria", "message": "Hola Karla"})
    assert r["statusCode"] == 409
    assert json.loads(r["body"])["code"] == "doNotContact"
    assert not utils._get_by_id("CUSTOMER", 14).get("contactNotes")


def test_el_contacto_valida_canal_plantilla_mensaje_y_cliente(modulos):
    customer_lambda, _ = modulos
    assert _post(customer_lambda, "/customers/11/contacto", {"channel": "paloma", "message": "x"})["statusCode"] == 400
    assert _post(customer_lambda, "/customers/11/contacto", {"channel": "whatsapp", "templateKey": "otra", "message": "x"})["statusCode"] == 400
    assert _post(customer_lambda, "/customers/11/contacto", {"channel": "whatsapp", "message": "   "})["statusCode"] == 400
    assert _post(customer_lambda, "/customers/999/contacto", {"channel": "call", "message": "Llamé y no contestó"})["statusCode"] == 404


def test_una_llamada_anotada_no_lleva_texto_prellenado(modulos):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/11/contacto", {"channel": "call", "message": "Llamé, quedó de pedir el viernes"})
    assert r["statusCode"] == 201
    cuerpo = json.loads(r["body"])
    assert cuerpo["note"]["text"] == "Llamada: Llamé, quedó de pedir el viernes"
    assert cuerpo["whatsappUrl"] == "https://wa.me/525512345678"


def test_el_invitado_sin_ficha_guarda_la_nota_aparte_y_la_lista_la_ve(modulos, utils):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/invitado/contacto",
              {"channel": "whatsapp", "templateKey": "fria", "message": "Hola Héctor", "guestEmail": "Hector@Test.com"})
    assert r["statusCode"] == 201, r["body"]
    cuerpo = json.loads(r["body"])
    assert cuerpo["guestEmail"] == "hector@test.com" and cuerpo["whatsappUrl"].startswith("https://wa.me/525599887766?text=")
    registro = utils._get_by_id("GUEST_CONTACT", "hector@test.com")
    assert registro["notes"][0]["templateKey"] == "fria" and registro["lastContactAt"] == cuerpo["lastContactAt"]

    # Segunda nota: se acumula, no se pisa.
    _post(customer_lambda, "/customers/invitado/contacto", {"channel": "call", "message": "No contestó", "guestEmail": "hector@test.com"})
    assert len(utils._get_by_id("GUEST_CONTACT", "hector@test.com")["notes"]) == 2

    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/hoy", "headers": COACH,
                                        "queryStringParameters": {"scope": "all", "situation": "activa"}, "body": ""}, None)
    hector = [f for f in json.loads(r["body"])["rows"] if f["isGuest"]][0]
    assert hector["daysSinceLastContact"] == 0

    assert _post(customer_lambda, "/customers/invitado/contacto", {"channel": "call", "message": "x"})["statusCode"] == 400
    assert _post(customer_lambda, "/customers/invitado/contacto", {"channel": "call", "message": "x", "guestEmail": "nadie@test.com"})["statusCode"] == 404


def test_anotar_un_contacto_exige_el_privilegio_de_clientes(modulos, utils):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/11/contacto", {"channel": "whatsapp", "message": "Hola"}, headers=SIN_PRIVILEGIO)
    assert r["statusCode"] == 403
    assert not utils._get_by_id("CUSTOMER", 11).get("contactNotes")


# --- Propuesta 11 · la plantilla que decía lo contrario -----------------------

def test_la_situacion_activa_ya_tiene_su_propia_plantilla(modulos):
    """*"La plantilla no me ahorró trabajo, me puso una trampa."* (`gaby-2027-03-08.md`)

    Gaby estuvo a un clic de mandarle "Hace tiempo que no te vemos por la
    tienda" a Julio, cuyo pedido se había entregado el viernes, mientras el
    mismo cuadro le decía arriba "Compró hace poco; no necesita contacto hoy".
    """
    customer_lambda, _ = modulos
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/plantillas", "headers": COACH,
                                        "queryStringParameters": None, "body": ""}, None)
    plantillas = json.loads(r["body"])["templates"]
    activa = plantillas["activa"]
    assert activa["title"] == "Compró hace poco"
    assert "{nombre}" in activa["text"] and "{coach}" in activa["text"] and "{producto}" in activa["text"]
    # No dice lo contrario de lo que la pantalla acaba de decir.
    assert "hace tiempo que no te vemos" not in activa["text"].lower()


def test_la_plantilla_de_clabe_manda_a_mi_perfil_que_si_existe(modulos):
    """La ruta "Mi cuenta → Datos bancarios" no existe en el producto."""
    customer_lambda, _ = modulos
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/plantillas", "headers": COACH,
                                        "queryStringParameters": None, "body": ""}, None)
    texto = json.loads(r["body"])["templates"]["clabe_pendiente"]["text"]
    assert "Mi cuenta" not in texto and "Datos bancarios" not in texto
    assert "Mi perfil" in texto and "#/perfil" in texto


def test_toda_situacion_de_la_lista_tiene_plantilla(modulos):
    """Mientras una situación no tenga plantilla no se propone ninguna: al
    frontend no le queda hueco que rellenar con `fria`."""
    _, seguimiento = modulos
    assert set(seguimiento.PLANTILLAS) == set(seguimiento.SITUACIONES)


def test_la_fila_de_una_clienta_activa_propone_su_plantilla_y_no_la_de_fria(modulos, utils):
    """Julio, con el pedido entregado el viernes, sale con `templateKey` propia."""
    customer_lambda, _ = modulos
    utils._put_entity("CUSTOMER", 21, {"entityType": "customer", "customerId": 21, "name": "Julio Peña",
                                       "email": "julio@test.com", "phone": "5544332211",
                                       "createdAt": "2027-01-05T10:00:00Z"})
    pedido = {"entityType": "order", "orderId": "ORD-JUL1", "customerId": 21, "customerName": "Julio Peña",
              "status": "delivered", "total": 1209, "netTotal": 1209,
              "items": [{"productId": "P1", "name": "Proteína", "quantity": 1}], "createdAt": utils._now_iso()}
    utils._put_entity("ORDER", "ORD-JUL1", pedido)
    utils._upsert_order_customer_history(pedido)
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/hoy", "headers": COACH,
                                        "queryStringParameters": {"scope": "all", "situation": "activa"}, "body": ""}, None)
    assert r["statusCode"] == 200, r["body"]
    filas = {f["name"]: f for f in json.loads(r["body"])["rows"]}
    assert filas["Julio Peña"]["situation"] == "activa"
    assert filas["Julio Peña"]["templateKey"] == "activa"


def test_se_puede_anotar_un_contacto_con_la_plantilla_activa(modulos):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "whatsapp", "templateKey": "activa", "message": "Hola Rosa, ¿cómo te fue con el Colágeno?"})
    assert r["statusCode"] == 201, r["body"]
    assert json.loads(r["body"])["note"]["templateKey"] == "activa"


# --- Propuesta 12 · la bitácora firmada con nombre ----------------------------

def test_la_nota_queda_firmada_con_el_nombre_y_conserva_el_id(modulos, utils):
    """*"Si mañana Mireya lee «1803978000111», no sabe si fui yo o Alma, y le
    vuelve a escribir a Julio. Para eso, me sigo yendo con mi libreta."*
    (`gaby-2027-03-08.md`)

    El nombre se resuelve **al escribir**: resolverlo al leer serían N nombres
    por ficha, un N+1 de manual, y la vista Clientes ni carga empleados.
    """
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "call", "message": "Llamé, quedó de pedir el viernes"})
    assert r["statusCode"] == 201, r["body"]
    nota = json.loads(r["body"])["note"]
    assert nota["byName"] == "Ivonne Castro"
    assert nota["by"] == "900", "el id se conserva: el cambio es aditivo"
    guardada = utils._get_by_id("CUSTOMER", 11)["contactNotes"][-1]
    assert guardada["byName"] == "Ivonne Castro" and guardada["by"] == "900"


def test_la_nota_del_invitado_tambien_queda_firmada(modulos, utils):
    customer_lambda, _ = modulos
    r = _post(customer_lambda, "/customers/invitado/contacto",
              {"channel": "call", "message": "Le avisé del bote estrellado", "guestEmail": "hector@test.com"})
    assert r["statusCode"] == 201, r["body"]
    assert json.loads(r["body"])["note"]["byName"] == "Ivonne Castro"
    assert utils._get_by_id("GUEST_CONTACT", "hector@test.com")["notes"][-1]["byName"] == "Ivonne Castro"


def test_sin_nombre_en_la_sesion_se_firma_con_el_de_la_ficha_de_empleada(modulos, utils):
    customer_lambda, _ = modulos
    utils._put_entity("EMPLOYEE", 901, {"entityType": "employee", "employeeId": 901, "name": "Alma Rivera"})
    sin_nombre = {"x-user-id": "901", "x-user-role": "employee",
                  "x-user-privileges": json.dumps({"access_screen_customers": True})}
    r = _post(customer_lambda, "/customers/11/contacto",
              {"channel": "call", "message": "Le marqué"}, headers=sin_nombre)
    assert r["statusCode"] == 201, r["body"]
    assert json.loads(r["body"])["note"]["byName"] == "Alma Rivera"


def test_la_nota_escrita_desde_la_ficha_de_clientes_tambien_lleva_nombre(modulos, utils):
    """La otra puerta de la bitácora: PATCH /customers/{id} con `note`."""
    customer_lambda, _ = modulos
    r = customer_lambda.lambda_handler({"httpMethod": "PATCH", "path": "/customers/11", "headers": COACH,
                                        "queryStringParameters": None,
                                        "body": json.dumps({"note": "Pasó a la sucursal por su pedido"})}, None)
    assert r["statusCode"] == 200, r["body"]
    nota = utils._get_by_id("CUSTOMER", 11)["contactNotes"][-1]
    assert nota["byName"] == "Ivonne Castro"
    assert "by" in nota, "el id se conserva: el cambio es aditivo"
