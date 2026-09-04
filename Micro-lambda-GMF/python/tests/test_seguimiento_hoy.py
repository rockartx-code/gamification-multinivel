"""Seguimiento de hoy (paquete F): la lista priorizada que la coach abre al empezar el turno.

Ivonne cruzaba Clientes, Pedidos y Estadísticas y abría 36 fichas en cinco
turnos para saber quién se enfrió y quién es su patrocinadora. Aquí se fija
que una sola ruta traiga todo eso en la misma fila, con la situación ya
decidida y los excluidos ("no contactar", otra ejecutiva) contados aparte.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

IVONNE = 900
OTRA_EJECUTIVA = 901
COACH = {"x-user-id": str(IVONNE), "x-user-role": "employee", "x-user-name": "Ivonne Castro",
         "x-user-privileges": json.dumps({"access_screen_customers": True})}
SIN_PRIVILEGIO = {"x-user-id": "77", "x-user-role": "employee", "x-user-privileges": json.dumps({"access_screen_orders": True})}
ADMIN = {"x-user-id": "1", "x-user-role": "admin"}


def _hace(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cliente(utils, cid, nombre, *, dias_registro=60, **extra):
    item = {"entityType": "customer", "customerId": cid, "name": nombre, "email": f"{nombre.split()[0].lower()}@test.com",
            "phone": "55 1234 5678", "createdAt": _hace(dias_registro), "isAssociate": True}
    item.update(extra)
    utils._put_entity("CUSTOMER", cid, item, created_at_iso=item["createdAt"])
    utils._upsert_customer_email_index(cid, item["email"])
    return cid


def _pedido(utils, oid, cid, *, dias, status="delivered", total=960, email=None, nombre="Cliente", phone=None):
    order = {"entityType": "order", "orderId": oid, "customerId": cid, "customerName": nombre, "status": status,
             "total": total, "netTotal": total, "items": [{"productId": "P1", "name": "Colágeno", "quantity": 1}],
             "createdAt": _hace(dias), "updatedAt": _hace(dias), "buyerType": "associate" if cid else "guest",
             "email": email, "phone": phone}
    utils._put_entity("ORDER", oid, order, created_at_iso=order["createdAt"])
    if cid:
        utils._upsert_order_customer_history(order)
    return order


@pytest.fixture
def mundo(utils):
    """El mundo de la ronda 4 reducido a lo que la lista tiene que decidir."""
    import commissions_lambda
    utils._put_entity("EMPLOYEE", IVONNE, {"entityType": "employee", "employeeId": IVONNE, "name": "Ivonne Castro",
                                           "email": "ivonne@findingu.com.mx", "phone": "5551112222", "active": True})
    utils._put_entity("EMPLOYEE", OTRA_EJECUTIVA, {"entityType": "employee", "employeeId": OTRA_EJECUTIVA, "name": "Sofía Rangel",
                                                   "email": "sofia@findingu.com.mx", "active": True})
    # Rosa Elena: compró hace 45 días → fría. Tiene patrocinadora (Marcela).
    _cliente(utils, 10, "Marcela Ruiz")
    _cliente(utils, 11, "Rosa Elena Ortiz", leaderId=10)
    _pedido(utils, "ORD-ROSA", 11, dias=45)
    # Tomás: se registró hace 20 días y nunca compró → la bienvenida venció, es fría.
    _cliente(utils, 12, "Tomás Vega", dias_registro=20)
    # Claudia: comisión confirmada este mes y sin CLABE → CLABE pendiente (urgente).
    _cliente(utils, 13, "Claudia Pérez", leaderId=10)
    commissions_lambda._mutate_ledger_month(13, utils._month_key(), lambda item: item["ledger"].append(
        {"rowId": "O#G1", "orderId": "O", "amount": 250.74, "level": 1, "status": "confirmed"}) or True)
    # Karla pidió que no le escriban → no aparece, pero se cuenta.
    _cliente(utils, 14, "Karla Méndez", doNotContact=True)
    # Lupita es de la cartera de Sofía → fuera de "mi cartera", dentro de "todas".
    _cliente(utils, 15, "Lupita Sánchez", executiveId=str(OTRA_EJECUTIVA))
    # Patricia: pagó hace 6 días y nadie ha despachado → pedido tardío (urgente).
    _cliente(utils, 16, "Patricia Luna", leaderId=10)
    _pedido(utils, "ORD-PATY", 16, dias=6, status="paid")
    # Memo: se registró hace 2 días, sin compra → bienvenida.
    _cliente(utils, 17, "Memo Díaz", dias_registro=2)
    # Bety compró hace 3 días → activa; no sale salvo con el filtro.
    _cliente(utils, 18, "Bety Flores", leaderId=10)
    _pedido(utils, "ORD-BETY", 18, dias=3)
    # Héctor compró dos veces como invitado y no tiene ficha.
    _pedido(utils, "ORD-HEC1", None, dias=40, email="hector@test.com", nombre="Héctor Mora", phone="5599887766")
    _pedido(utils, "ORD-HEC2", None, dias=35, email="hector@test.com", nombre="Héctor Mora", phone="5599887766")
    # Una baja ARCO no aparece ni se cuenta.
    _cliente(utils, 19, "Cliente eliminado", deletedAt=_hace(1), doNotContact=True)
    import customer_lambda
    return customer_lambda


def _hoy(customer_lambda, headers, **query):
    return customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/hoy", "headers": headers,
                                           "queryStringParameters": query or None, "body": ""}, None)


def _filas(r):
    assert r["statusCode"] == 200, r["body"]
    cuerpo = json.loads(r["body"])
    return cuerpo, {f["name"]: f for f in cuerpo["rows"]}


def test_la_lista_decide_la_situacion_de_cada_persona(mundo):
    cuerpo, por_nombre = _filas(_hoy(mundo, COACH))
    assert por_nombre["Rosa Elena Ortiz"]["situation"] == "fria"
    assert por_nombre["Rosa Elena Ortiz"]["daysSinceLastPurchase"] == 45
    assert por_nombre["Tomás Vega"]["situation"] == "fria" and por_nombre["Tomás Vega"]["daysSinceLastPurchase"] is None
    assert por_nombre["Claudia Pérez"]["situation"] == "clabe_pendiente"
    assert por_nombre["Patricia Luna"]["situation"] == "pedido_tardio"
    assert por_nombre["Patricia Luna"]["lastOrder"]["id"] == "ORD-PATY" and por_nombre["Patricia Luna"]["lastOrder"]["status"] == "paid"
    assert por_nombre["Memo Díaz"]["situation"] == "bienvenida"
    assert "Bety Flores" not in por_nombre, "activa: no aparece sin filtro"
    assert "Karla Méndez" not in por_nombre and "Cliente eliminado" not in por_nombre
    assert cuerpo["excluded"]["doNotContact"] == 1
    assert cuerpo["coachName"] == "Ivonne Castro"


def test_cada_fila_trae_lo_que_ivonne_abria_ficha_por_ficha(mundo):
    _, por_nombre = _filas(_hoy(mundo, COACH))
    rosa = por_nombre["Rosa Elena Ortiz"]
    assert rosa["sponsorName"] == "Marcela Ruiz"
    assert rosa["phone"] == "55 1234 5678" and rosa["whatsappUrl"] == "https://wa.me/525512345678"
    assert rosa["lastOrder"]["id"] == "ORD-ROSA" and rosa["lastOrder"]["total"] == 960.0
    assert rosa["daysSinceLastContact"] is None and rosa["templateKey"] == "fria"
    assert rosa["placeholders"]["nombre"] == "Rosa" and rosa["placeholders"]["coach"] == "Ivonne Castro"
    assert rosa["placeholders"]["producto"] == "Colágeno"


def test_los_urgentes_van_primero(mundo):
    cuerpo, _ = _filas(_hoy(mundo, COACH))
    situaciones = [f["situation"] for f in cuerpo["rows"]]
    urgentes = {"clabe_pendiente", "pedido_tardio"}
    primeros = situaciones[:2]
    assert set(primeros) == urgentes, situaciones
    urgentes_flag = [f["urgent"] for f in cuerpo["rows"]]
    assert urgentes_flag == sorted(urgentes_flag, reverse=True), "primero las urgentes, luego el resto"
    del_resto = [f["priority"] for f in cuerpo["rows"] if not f["urgent"]]
    assert del_resto == sorted(del_resto, reverse=True)


def test_mi_cartera_excluye_a_la_clienta_de_otra_ejecutiva_y_todas_la_incluye(mundo):
    cuerpo, por_nombre = _filas(_hoy(mundo, COACH))
    assert "Lupita Sánchez" not in por_nombre
    assert cuerpo["excluded"]["otherExecutive"] == 1
    cuerpo, por_nombre = _filas(_hoy(mundo, COACH, scope="all"))
    assert por_nombre["Lupita Sánchez"]["executiveName"] == "Sofía Rangel"
    assert cuerpo["excluded"]["otherExecutive"] == 0


def test_el_invitado_aparece_como_fila_sin_cuenta_con_sus_pedidos(mundo):
    _, por_nombre = _filas(_hoy(mundo, COACH))
    hector = por_nombre["Héctor Mora"]
    assert hector["isGuest"] is True and hector["customerId"] == "" and hector["email"] == "hector@test.com"
    assert hector["orderCount"] == 2 and hector["lastOrder"]["id"] == "ORD-HEC2"
    assert hector["situation"] == "fria" and hector["daysSinceLastPurchase"] == 35
    assert hector["whatsappUrl"] == "https://wa.me/525599887766"


def test_el_filtro_de_situacion_incluye_a_las_activas(mundo):
    _, por_nombre = _filas(_hoy(mundo, COACH, situation="activa"))
    assert list(por_nombre) == ["Bety Flores"]
    _, por_nombre = _filas(_hoy(mundo, COACH, situation="fria"))
    assert {"Rosa Elena Ortiz", "Tomás Vega", "Héctor Mora"} <= set(por_nombre)
    assert "Claudia Pérez" not in por_nombre
    assert _hoy(mundo, COACH, situation="inventada")["statusCode"] == 400


def test_sin_telefono_no_hay_enlace_de_whatsapp(mundo, utils):
    _cliente(utils, 20, "Lucía Sin Teléfono", phone="")
    _cliente(utils, 21, "Andrés Extranjero", phone="+1 305 555 0100")
    _, por_nombre = _filas(_hoy(mundo, ADMIN, scope="all"))
    assert por_nombre["Lucía Sin Teléfono"]["whatsappUrl"] == ""
    assert por_nombre["Andrés Extranjero"]["whatsappUrl"] == ""


def test_la_lista_exige_el_privilegio_de_clientes(mundo):
    assert _hoy(mundo, SIN_PRIVILEGIO)["statusCode"] == 403
    assert _hoy(mundo, {})["statusCode"] == 403


def test_los_umbrales_salen_de_la_configuracion(mundo, utils):
    """Con coldDays=50, Rosa (45 días) deja de ser fría y pasa a activa."""
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "config": {"seguimiento": {"coldDays": 50}}})
    utils._invalidate_app_config_cache()
    _, por_nombre = _filas(_hoy(mundo, COACH))
    assert "Rosa Elena Ortiz" not in por_nombre
    _, por_nombre = _filas(_hoy(mundo, COACH, situation="activa"))
    assert por_nombre["Rosa Elena Ortiz"]["situation"] == "activa"


def test_los_invitados_se_leen_acotados_por_fecha_y_no_todo_el_historico(mundo, utils, monkeypatch):
    """§0.1: `_pedidos_de_invitados` recorría el bucket ORDER entero en cada carga."""
    import seguimiento_handlers
    consultas = []
    original = utils._query_bucket

    def espia(entity, *a, **k):
        if entity == "ORDER":
            consultas.append(k.get("sk_from"))
        return original(entity, *a, **k)

    monkeypatch.setattr(seguimiento_handlers.utils, "_query_bucket", espia)
    # Un invitado de hace un año no es un seguimiento de hoy (frío × 2 = 60 días).
    _pedido(utils, "ORD-VIEJO", None, dias=400, email="viejo@test.com", nombre="Viejo Invitado")
    _, por_nombre = _filas(_hoy(mundo, COACH))
    assert "Héctor Mora" in por_nombre and "Viejo Invitado" not in por_nombre
    assert consultas and all(desde and desde >= _hace(61)[:10] for desde in consultas), consultas


# ─────────────────────────────────────────────────────────────────────────────
# Guarda 1 (docs/qa/27 §4): toda situación trae su plantilla.
#
# La situación `activa` existía, tenía etiqueta y NO tenía plantilla, así que la
# pantalla rellenaba con la de cliente fría: Gaby estuvo a un clic de mandarle
# "Hace tiempo que no te vemos por la tienda" a Julio, con el pedido entregado
# el viernes. La propuesta 11 le dio plantilla propia; esta prueba es el candado.
# ─────────────────────────────────────────────────────────────────────────────


def _plantillas(customer_lambda, headers=COACH):
    r = customer_lambda.lambda_handler({"httpMethod": "GET", "path": "/customers/seguimiento/plantillas",
                                        "headers": headers, "queryStringParameters": None, "body": ""}, None)
    assert r["statusCode"] == 200, r["body"]
    return json.loads(r["body"])["templates"]


def test_toda_situacion_tiene_plantilla(mundo, utils):
    import seguimiento_handlers as sh

    # Ninguna situación puede quedarse sin plantilla: si alguien añade una
    # sexta a SITUACIONES, esto se cae antes de que la coach lo descubra.
    faltantes = set(sh.SITUACIONES) - set(sh.PLANTILLAS)
    assert faltantes == set(), f"situaciones sin plantilla: {sorted(faltantes)}"
    assert set(sh.SITUACIONES) == set(sh.ETIQUETAS_SITUACION)

    # …y `activa` trae la suya, no la de `fria`.
    activa, fria = sh.PLANTILLAS["activa"], sh.PLANTILLAS["fria"]
    assert activa["text"] != fria["text"]
    assert "Hace tiempo que no te vemos" not in activa["text"], "la trampa de la plantilla de fría"

    # Lo que la pantalla realmente sirve (plantillas de código + override de config).
    plantillas = _plantillas(mundo)
    assert set(sh.SITUACIONES) <= set(plantillas)
    assert plantillas["activa"]["text"] != plantillas["fria"]["text"]

    # Y la fila de Bety (compró hace 3 días) apunta a esa plantilla, no a "fria".
    _, por_nombre = _filas(_hoy(mundo, COACH, situation="activa"))
    assert por_nombre["Bety Flores"]["templateKey"] == "activa"
    assert por_nombre["Bety Flores"]["situationLabel"] == "Activa"

    # La bitácora firma con la plantilla que se usó: "activa" es una clave válida.
    r = mundo.lambda_handler({"httpMethod": "POST", "path": "/customers/18/contacto", "headers": COACH,
                              "queryStringParameters": None,
                              "body": json.dumps({"channel": "whatsapp", "templateKey": "activa",
                                                  "message": "¿cómo te fue con el Colágeno?"})}, None)
    assert r["statusCode"] == 201, r["body"]
    nota = (utils._get_by_id("CUSTOMER", 18).get("contactNotes") or [])[-1]
    assert nota["templateKey"] == "activa" and "plantilla activa" in nota["text"]
