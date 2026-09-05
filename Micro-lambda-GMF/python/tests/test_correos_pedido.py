"""Cada paso del pedido avisa al comprador por correo (docs/qa/18: no había ninguno)."""
import json

import pytest

from test_pedidos_creacion import _crear_pedido_invitado, _evento


@pytest.fixture
def order_lambda(utils):
    import order_lambda
    return order_lambda


@pytest.fixture
def buzon(monkeypatch):
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email", lambda para, asunto, texto, html: enviados.append((para, asunto, html)))
    return enviados


def _admin():
    return {"Authorization": "Bearer x"}


def test_el_invitado_recibe_correo_en_cada_paso(order_lambda, utils, buzon, monkeypatch):
    monkeypatch.setattr(utils, "_require_admin", lambda *a, **k: None)
    monkeypatch.setattr(utils, "_require_self_or_admin", lambda *a, **k: None)
    oid = _crear_pedido_invitado(order_lambda, utils)
    assert utils._get_by_id("ORDER", oid)["email"] == "lucia@test.com"   # antes el pedido no guardaba a quién escribirle

    for estado, extra in (("paid", {}), ("shipped", {"shippingType": "carrier", "trackingNumber": "EST-1"}), ("delivered", {})):
        r = order_lambda.handle_update_status(oid, {"status": estado, **extra}, {})
        assert r["statusCode"] == 200, r["body"]
    asuntos = [a for _, a, _ in buzon]
    assert [p for p, _, _ in buzon] == ["lucia@test.com"] * 3
    assert "Recibimos tu pago" in asuntos[0] and "va en camino" in asuntos[1] and "entregado" in asuntos[2]
    assert "EST-1" in buzon[1][2] and "$929.00" in buzon[1][2]   # guía y total con envío en el cuerpo
    assert f"/#/orden/{oid}" in buzon[1][2]   # el enlace de seguimiento existe

    cuerpo = {"motivo": "DANADO_DEFECTUOSO", "reason": "DANADO_DEFECTUOSO", "descripcion": "Tapa rajada",
              "evidencia": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]},
              "evidence": {"fotos_producto": ["a.jpg"], "fotos_empaque": ["b.jpg"], "fotos_guia_envio": ["c.jpg"]}}
    r = order_lambda.lambda_handler(_evento("POST", f"/orders/{oid}/return", cuerpo), None)
    assert r["statusCode"] == 201, r["body"]
    folio = json.loads(r["body"])["requestId"]
    assert folio in buzon[-1][1]

    inspeccion = {"inspection": {"empaque_original": True, "sellos_intactos": True, "sin_uso": True,
                                 "coincide_con_pedido": True, "trazabilidad_valida": True}}
    r = order_lambda.handle_return_inspection(oid, inspeccion, _admin())
    assert r["statusCode"] == 200, r["body"]
    assert "aprobada" in buzon[-1][1].lower()

    r = order_lambda.handle_refund_order(oid, {"reason": "return"}, _admin())
    assert r["statusCode"] == 200, r["body"]
    assert "Reembolso" in buzon[-1][1]
    assert len(buzon) == 6


def test_repetir_el_mismo_estado_no_manda_dos_correos(order_lambda, utils, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    assert len(buzon) == 1


def test_sin_correo_no_se_manda_nada_y_el_pedido_sigue(order_lambda, utils, buzon):
    oid = _crear_pedido_invitado(order_lambda, utils)
    utils._update_by_id("ORDER", oid, "SET email = :e", {":e": None})
    r = order_lambda.handle_update_status(oid, {"status": "paid"}, {})
    assert r["statusCode"] == 200 and buzon == []


# ── Paquete C · ronda 26 · propuesta 7: el correo repite lo que se eligió ──

@pytest.fixture
def buzon_completo(monkeypatch):
    """Como `buzon`, pero conservando también la versión de texto plano."""
    from core import email as correo
    enviados = []
    monkeypatch.setattr(correo, "_send_ses_email",
                        lambda para, asunto, texto, html: enviados.append({"para": para, "asunto": asunto,
                                                                           "texto": texto, "html": html}))
    return enviados


def _pedido_de_mostrador(utils, **extra):
    """Un pedido para recoger en la sucursal de Guadalajara, como el de Aurora."""
    utils._put_entity("STOCK", "STK-GDL", {"entityType": "stock", "stockId": "STK-GDL",
                                           "name": "Sucursal Guadalajara", "location": "Av. Chapultepec 480",
                                           "city": "Guadalajara", "state": "JAL", "allowPickup": True,
                                           "linkedUserIds": [], "inventory": {"101": 10}})
    order = {
        "orderId": "ORD-MOSTRADOR", "customerName": "Aurora Vega", "recipientName": "Aurora Vega",
        "email": "aurora@test.com", "deliveryType": "pickup", "pickupStockId": "STK-GDL",
        "items": [{"productId": 101, "name": "Finding Pro 500g", "price": 800, "quantity": 2}],
        "total": 1600, "netTotal": 1600,
    }
    order.update(extra)
    return order


def test_el_correo_de_texto_plano_trae_el_detalle_de_la_compra(utils, buzon_completo):
    """Mariana compró sin cuenta y su único comprobante fue un correo que no decía qué compró:
    la versión de texto plano nunca pintaba el detalle."""
    from core import order_emails
    order_emails.notificar_pedido(_pedido_de_mostrador(utils), "paid", {}, lambda cid: None, "http://x")
    texto = buzon_completo[-1]["texto"]
    assert "2 × Finding Pro 500g" in texto
    assert "Total — $1,600.00" in texto


def test_quien_recoge_en_sucursal_no_recibe_un_paquete_en_camino(utils, buzon_completo):
    """Tres personas que eligieron recoger leyeron "estamos preparando tu paquete y te
    avisaremos cuando salga"; Paulina llevaba 21 días sin saber en qué tienda estaba el suyo."""
    from core import order_emails
    order_emails.notificar_pedido(_pedido_de_mostrador(utils), "paid", {}, lambda cid: None, "http://x")
    correo = buzon_completo[-1]
    assert "Recoges en Sucursal Guadalajara, Av. Chapultepec 480" in correo["texto"]
    assert "Recoges en Sucursal Guadalajara, Av. Chapultepec 480" in correo["html"]
    assert "te avisaremos por este medio cuando salga" not in correo["html"]

    order_emails.notificar_pedido(_pedido_de_mostrador(utils), "shipped", {}, lambda cid: None, "http://x")
    assert "listo para recoger" in buzon_completo[-1]["asunto"]
    assert "va en camino" not in buzon_completo[-1]["asunto"]


def test_el_correo_repite_los_datos_fiscales_de_la_factura(utils, buzon_completo):
    """Aurora abandonó la tarea buscando dónde volver a ver su RFC: no había ninguna pantalla
    ni ningún correo donde releerlo."""
    from core import order_emails
    pedido = _pedido_de_mostrador(utils, invoiceRequested=True, invoiceStatus="solicitada",
                                  invoiceData={"rfc": "VEAA850101AB1", "razonSocial": "Aurora Vega",
                                               "email": "facturas@test.com"})
    order_emails.notificar_pedido(pedido, "paid", {}, lambda cid: None, "http://x")
    correo = buzon_completo[-1]
    assert "Factura solicitada a nombre de Aurora Vega · RFC VEAA850101AB1" in correo["texto"]
    assert "facturas@test.com" in correo["html"]


def test_el_correo_desglosa_el_iva_que_guardo_el_pedido(utils, buzon_completo):
    """Decisión 38: el IVA se desglosa donde el dinero se explica, y el total no cambia ni un peso."""
    from core import order_emails
    pedido = _pedido_de_mostrador(utils, vatRate="0.16", taxBase="1379.31", taxAmount="220.69")
    order_emails.notificar_pedido(pedido, "paid", {}, lambda cid: None, "http://x")
    texto = buzon_completo[-1]["texto"]
    assert "Subtotal sin IVA — $1,379.31" in texto
    assert "IVA 16 % — $220.69" in texto
    assert "Total — $1,600.00" in texto


def test_un_pedido_sin_iva_guardado_no_inventa_el_desglose(utils, buzon_completo):
    """Los pedidos anteriores a la ronda no traen taxBase/taxAmount: se enseña el total y ya."""
    from core import order_emails
    order_emails.notificar_pedido(_pedido_de_mostrador(utils), "paid", {}, lambda cid: None, "http://x")
    assert "Subtotal sin IVA" not in buzon_completo[-1]["texto"]
