"""El IVA desglosado y la base de la comisión escrita (paquete B, 37 y 38).

Ximena Paredes lo buscó en tres pantallas y no lo encontró en ninguna:
"$135 de $1,350 o de $1,500, ¿de cuál?" (`ximena-paredes-2027-03-02.md`).
Y ninguna pantalla del producto decía cuánto de lo que se paga es impuesto,
aunque los precios de lista ya lo traen dentro.

Estas pruebas fijan el supuesto de docs/arquitectura/26 §3.1 y §4.1-§4.3:
el IVA se **desglosa** de un total que no cambia, la base es todo lo que se
cobra (envío incluido), se redondea una sola vez al final y `base + IVA` da
el total al centavo.
"""
from decimal import Decimal

import pytest


@pytest.fixture
def iva(utils):
    import impuestos
    return impuestos


def _config(utils, taxes: dict) -> None:
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1",
                                           "config": {"taxes": taxes}})
    utils._invalidate_app_config_cache()


def test_la_tasa_por_omision_es_del_dieciseis_por_ciento(iva, utils):
    cfg = utils._load_app_config()
    assert cfg["taxes"] == {"vatRate": Decimal("0.16"), "pricesIncludeVat": True,
                            "appliesToShipping": True, "label": "IVA"}
    assert iva.tasa_iva() == Decimal("0.16") and iva.etiqueta_iva() == "IVA"
    assert iva.precios_con_iva() is True and iva.iva_incluye_envio() is True


def test_el_desglose_no_mueve_el_total_ni_un_centavo(iva):
    """El caso del contrato: $1,350.00 se lee 1,163.79 + 186.21."""
    d = iva.desglose_iva(Decimal("1350.00"))
    assert d["base"] == Decimal("1163.79")
    assert d["iva"] == Decimal("186.21")
    assert d["base"] + d["iva"] == d["total"] == Decimal("1350.00")
    assert d["rate"] == Decimal("0.16") and d["label"] == "IVA"


@pytest.mark.parametrize("total", ["0.01", "1.00", "129.00", "933.00", "1090.00", "1350.00",
                                   "1479.00", "1605.33", "9999.99", "100000.00"])
def test_base_mas_iva_siempre_da_el_total(iva, total):
    d = iva.desglose_iva(Decimal(total))
    assert d["base"] + d["iva"] == Decimal(total)
    assert d["base"] >= 0 and d["iva"] >= 0


def test_el_total_cero_o_negativo_no_inventa_impuesto(iva):
    for total in (0, "-15.00", None):
        d = iva.desglose_iva(total)
        assert d["iva"] == Decimal("0.00") and d["base"] == d["total"]


def test_cambiar_la_tasa_cambia_el_desglose_y_no_el_total(iva, utils):
    """Propuesta 38: la tasa es configurable y el total cobrado no se mueve."""
    _config(utils, {"vatRate": Decimal("0.08")})
    d = iva.desglose_iva(Decimal("1350.00"))
    assert d["rate"] == Decimal("0.08")
    assert d["base"] == Decimal("1250.00") and d["iva"] == Decimal("100.00")
    assert d["base"] + d["iva"] == Decimal("1350.00")


def test_una_tasa_imposible_se_ignora_en_vez_de_deformar_el_precio(iva, utils):
    for tasa in (Decimal("-0.16"), Decimal("1"), Decimal("2.5")):
        _config(utils, {"vatRate": tasa})
        d = iva.desglose_iva(Decimal("1350.00"))
        assert d["rate"] == Decimal("0") and d["base"] == Decimal("1350.00") and d["iva"] == Decimal("0.00")


def test_el_redondeo_es_uno_solo_y_al_final_no_por_linea(iva):
    """Redondear por línea y sumar descuadra un centavo; el contrato lo prohíbe."""
    lineas = [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    por_linea = sum(iva.desglose_iva(l)["iva"] for l in lineas)
    de_una = iva.desglose_iva(sum(lineas))["iva"]
    assert de_una == Decimal("137.93")
    assert por_linea != de_una  # justamente por eso se calcula sobre el total
    assert iva.desglose_iva(sum(lineas))["base"] + de_una == Decimal("1000.00")


def test_los_campos_del_pedido_son_los_tres_del_contrato(iva):
    campos = iva.campos_pedido(Decimal("1479.00"))
    assert set(campos) == {"vatRate", "taxBase", "taxAmount"}
    assert campos["taxBase"] + campos["taxAmount"] == Decimal("1479.00")


def test_un_pedido_viejo_sin_campos_de_iva_se_desglosa_al_vuelo(iva):
    """§4.4: los pedidos anteriores a la ronda no se migran."""
    viejo = iva.desglose_de_pedido({"total": Decimal("1350.00")})
    assert viejo["base"] == Decimal("1163.79") and viejo["iva"] == Decimal("186.21")


def test_un_pedido_guardado_conserva_su_desglose_aunque_cambie_la_tasa(iva, utils):
    pedido = {"total": Decimal("1350.00"), "vatRate": Decimal("0.16"),
              "taxBase": Decimal("1163.79"), "taxAmount": Decimal("186.21")}
    _config(utils, {"vatRate": Decimal("0.08")})
    d = iva.desglose_de_pedido(pedido)
    assert d["rate"] == Decimal("0.16") and d["base"] == Decimal("1163.79") and d["iva"] == Decimal("186.21")


# ── El pedido guarda su desglose al nacer ──────────────────────────────────

def _pedido_de_invitado(utils, precio=1221, envio=129):
    utils._put_entity("PRODUCT", 101, {"entityType": "product", "productId": 101,
                                       "name": "Finding Pro 500g", "price": precio,
                                       "vpPoints": 15, "active": True})
    return {
        "items": [{"productId": 101, "name": "Finding Pro 500g", "price": precio, "quantity": 1}],
        "guest": True, "customerName": "Lucía Fernández", "email": "lucia@test.com",
        "phone": "3311112222", "deliveryType": "shipping",
        "shippingAddress": {"street": "Av. Vallarta", "number": "100", "city": "Guadalajara",
                            "state": "Jalisco", "postalCode": "44100", "country": "MX"},
        "shippingCarrier": "Estafeta", "shippingService": "Terrestre", "shippingCost": envio,
    }


def _guardado(utils) -> dict:
    return next(v for (pk, sk), v in utils._table.store.items() if pk == "ORDER" and sk != "REF")


def test_el_pedido_nace_con_su_desglose_y_el_total_no_se_mueve(iva, utils):
    """$1,221 de producto + $129 de envío = $1,350.00, que se lee 1,163.79 + 186.21."""
    import order_lambda
    r = order_lambda.handle_create_order(_pedido_de_invitado(utils), {})
    assert r["statusCode"] in (200, 201), r["body"]
    pedido = _guardado(utils)
    assert pedido["total"] == Decimal("1350.00")
    assert pedido["vatRate"] == Decimal("0.16")
    assert pedido["taxBase"] == Decimal("1163.79") and pedido["taxAmount"] == Decimal("186.21")
    assert pedido["taxBase"] + pedido["taxAmount"] == pedido["total"]


def test_el_envio_entra_en_la_base_gravable(iva, utils):
    """§4.1: el envío es un servicio gravado y el importe que la persona compara
    con su estado de cuenta es el total."""
    import order_lambda
    order_lambda.handle_create_order(_pedido_de_invitado(utils, precio=1221, envio=0), {})
    sin_envio = _guardado(utils)
    assert sin_envio["total"] == Decimal("1221.00")
    assert sin_envio["taxBase"] + sin_envio["taxAmount"] == Decimal("1221.00")
    assert sin_envio["taxAmount"] == Decimal("168.41")


def test_el_iva_no_toca_el_neto_comisionable_ni_el_cobro(iva, utils):
    """El IVA es desglose, no cargo: `netTotal` sigue siendo la base de la comisión."""
    import order_lambda
    order_lambda.handle_create_order(_pedido_de_invitado(utils), {})
    pedido = _guardado(utils)
    assert pedido["netTotal"] == Decimal("1221.00")
    assert pedido["total"] == pedido["netTotal"] + pedido["shippingCost"]
    # Y la comisión se sigue calculando sobre el neto sin envío, no sobre la base fiscal.
    assert iva.texto_base_comision(pedido["netTotal"], Decimal("0.10"), Decimal("122.10")) == \
        "10 % de $1,221.00 netos, sin envío = $122.10"


def test_los_pedidos_de_la_semilla_no_se_migran(iva, utils):
    """§4.4: sin script de migración sobre dinero ya cobrado; el recibo desglosa al vuelo."""
    utils._put_entity("ORDER", "ORD-VIEJO", {"entityType": "order", "orderId": "ORD-VIEJO",
                                             "total": Decimal("1350.00"), "status": "paid"})
    viejo = utils._get_by_id("ORDER", "ORD-VIEJO")
    assert "taxBase" not in viejo
    d = iva.desglose_de_pedido(viejo)
    assert d["base"] + d["iva"] == Decimal("1350.00")


# ── Propuesta 37: sobre qué base se paga la comisión ────────────────────────

def test_la_frase_por_fila_es_la_del_contrato(iva):
    assert iva.texto_base_comision(Decimal("1350.00"), Decimal("0.10"), Decimal("135.00")) == \
        "10 % de $1,350.00 netos, sin envío = $135.00"


def test_la_frase_por_fila_no_pierde_los_centavos_ni_inventa_decimales(iva):
    assert iva.texto_base_comision(Decimal("1120"), Decimal("0.05"), Decimal("56")) == \
        "5 % de $1,120.00 netos, sin envío = $56.00"
    assert iva.texto_base_comision(Decimal("980.50"), Decimal("0.075"), Decimal("73.54")) == \
        "7.5 % de $980.50 netos, sin envío = $73.54"


def test_la_frase_larga_dice_las_tres_cosas_que_ximena_buscaba(iva):
    frase = iva.FRASE_BASE_COMISION
    assert "neto" in frase and "descuento" in frase and "sin contar el envío" in frase
    assert iva.BASE_COMISION == "neto pagado por producto, sin envío"


def test_la_config_publica_publica_la_tasa_para_que_nadie_la_invente(utils):
    """El carrito y el POS desglosan sin escribir 0.16 en el frontend."""
    import json

    import catalog_lambda
    r = catalog_lambda.lambda_handler({"httpMethod": "GET", "path": "/config/public",
                                       "headers": {}, "body": "{}"}, None)
    assert r["statusCode"] == 200, r["body"]
    assert json.loads(r["body"])["config"]["taxes"] == {
        "vatRate": 0.16, "label": "IVA", "pricesIncludeVat": True, "appliesToShipping": True}


def test_el_helper_no_lleva_la_tasa_escrita_en_el_codigo(iva, utils):
    """Ningún número del negocio vive en el módulo: todo sale de `taxes`."""
    import inspect
    fuente = inspect.getsource(iva.desglose_iva) + inspect.getsource(iva.tasa_iva)
    assert "0.16" not in fuente and "1.16" not in fuente
