"""El plan publicado (paquete B, propuesta 2).

"El problema de esta empresa no es que mienta. Es que no publica" (andres-dia5).
`GET /catalog/plan` lo publica con los números reales de la configuración.
"""
import inspect
import json
import re
from decimal import Decimal

import pytest


@pytest.fixture
def catalogo(utils):
    import catalog_lambda
    return catalog_lambda


def _plan(catalog_lambda):
    r = catalog_lambda.lambda_handler({"httpMethod": "GET", "path": "/catalog/plan", "headers": {}, "body": "{}"}, None)
    assert r["statusCode"] == 200, r["body"]
    return json.loads(r["body"])["plan"]


def _productos(utils):
    utils._put_entity("PRODUCT", 9, {"entityType": "product", "productId": 9, "name": "Klinhart", "price": 480, "vpPoints": 10, "active": True})
    utils._put_entity("PRODUCT", 10, {"entityType": "product", "productId": 10, "name": "Naplus", "price": 545, "vpPoints": 10, "active": True})
    utils._put_entity("PRODUCT", 11, {"entityType": "product", "productId": 11, "name": "Sin puntos", "price": 100, "vpPoints": 0, "active": True})
    utils._put_entity("PRODUCT", 12, {"entityType": "product", "productId": 12, "name": "Inactivo", "price": 50, "vpPoints": 5, "active": False})


def test_el_plan_es_publico_y_trae_las_ocho_secciones(catalogo, utils):
    _productos(utils)
    plan = _plan(catalogo)
    assert plan["version"] == "abril-2026"
    assert set(plan) >= {"unidades", "activacion", "descuento", "generaciones", "compresionDinamica", "pago", "datos", "rangos", "bonos"}
    assert plan["unidades"]["mxnPerVp"] == 50 and plan["unidades"]["maxLevels"] == 5
    assert plan["activacion"]["vpNetos"] == 20
    assert [t["rate"] for t in plan["descuento"]["tramos"]] == [0, 0.10, 0.20, 0.30, 0.40]
    assert [g["rate"] for g in plan["generaciones"]] == [0.10, 0.05, 0.04, 0.03, 0.02]
    assert plan["compresionDinamica"] is True
    # Ronda 7 · Gerardo: los avisos caen antes del corte del mes (día 25), no después.
    assert plan["pago"]["dia"] == 10 and plan["pago"]["bloqueo"] == {"avisos": [20, 24], "graciaDias": 0}
    assert [d["cuando"] for d in plan["datos"]] == ["registro", "modo socio", "primera comisión confirmada", "facturación"]
    # Paquete A · propuesta 2: la CLABE se pide al activarse, no al confirmar
    # la primera comisión; el plan lo dice para no contradecir el recordatorio.
    assert plan["datos"][1]["que"] == ["CLABE, cuando te actives en el mes"]
    assert plan["datos"][2]["que"] == []
    assert plan["datos"][3]["que"] == ["Constancia de situación fiscal", "INE (frente y reverso)", "CURP"]
    assert [r["rank"] for r in plan["rangos"]] == ["BRONCE", "PLATA", "ORO", "PLATINO", "DIAMANTE"]
    assert plan["rangos"][0]["monthlyBonus"] == 500
    assert [b["id"] for b in plan["bonos"]] == ["inicio_rapido"]


def test_los_ejemplos_de_activacion_salen_de_los_productos_mas_baratos_con_pc(catalogo, utils):
    """Incluye el caso honesto: 20 PC de lista con 10 % de descuento = 18 VP, no activa."""
    _productos(utils)
    plan = _plan(catalogo)
    ejemplos = plan["activacion"]["ejemplos"]
    assert [e["productos"][0]["name"] for e in ejemplos] == ["Klinhart", "Naplus"]
    assert ejemplos[0] == {"productos": [{"id": "9", "name": "Klinhart", "price": 480, "pc": 10, "qty": 2}],
                           "bruto": 960, "rate": 0, "vp": 20, "activa": True}
    assert ejemplos[1]["bruto"] == 1090 and ejemplos[1]["rate"] == 0.10 and ejemplos[1]["vp"] == 18 and ejemplos[1]["activa"] is False
    assert plan["activacion"]["nota"] == "20 PC de lista con 10 % de descuento = 18 VP: no activa."


def test_sin_productos_el_plan_sigue_publicandose(catalogo, utils):
    plan = _plan(catalogo)
    assert plan["activacion"]["ejemplos"] == [] and plan["descuento"]["tramos"]
    # Sin catálogo no hay rango honesto que publicar: se calla, no se inventa.
    assert plan["activacion"]["rango"] is None
    assert plan["baseComision"]["compraEjemplo"] == 0


def test_el_numero_falso_de_la_activacion_ya_no_se_publica(catalogo, utils):
    """Propuesta 14. Ximena Paredes: "La misma pantalla me dice que $1,000
    activa y que $1,000 no activa. Es el número más importante del plan"
    (`ximena-paredes-2027-03-02.md`). `pesosAprox` sale del contrato."""
    _productos(utils)
    plan = _plan(catalogo)
    assert "pesosAprox" not in plan["activacion"]
    assert json.dumps(plan, ensure_ascii=False).find("pesosAprox") == -1


def test_el_rango_de_activacion_sale_del_catalogo_real(catalogo, utils):
    """Ximena midió el hoyo a mano; ahora lo calcula la página.

    Con Klinhart ($480 / 10 PC) bastan $960 y no hay descuento que reste VP;
    con Naplus ($545 / 10 PC) los $1,090 caen en el tramo del 10 % y hay que
    llegar a $1,211.11 para conservar los 20 VP netos.
    """
    _productos(utils)
    rango = _plan(catalogo)["activacion"]["rango"]
    assert rango["min"] == 960 and rango["max"] == 1211.11
    assert rango["notaProducto"] == ("Depende del producto: con Klinhart te activas con $960.00; "
                                     "con Naplus necesitas $1,211.11.")


def test_el_rango_respeta_la_escalera_no_solo_el_precio_por_pc(catalogo, utils):
    """El descuento se muerde la cola: pasar de $1,000 baja los VP un 10 %,
    así que el costo de activarse salta de tramo en vez de crecer parejo."""
    _productos(utils)
    import modo_handlers
    tiers = utils._load_app_config()["rewards"]["discountTiers"]
    barato = modo_handlers._costo_para_activar({"price": Decimal("480"), "pc": Decimal("10")}, tiers, Decimal("20"))
    caro = modo_handlers._costo_para_activar({"price": Decimal("545"), "pc": Decimal("10")}, tiers, Decimal("20"))
    assert barato == Decimal("960.00")
    assert caro == Decimal("1211.11")  # 1090 / 0.9, porque a los $1,090 ya aplica el 10 %


def test_el_ejemplo_de_comision_usa_una_compra_que_de_verdad_existe(catalogo, utils):
    """Propuestas 14 y 37: "si compra $960 netos ganas $96" tiene que ser
    aritmética verdadera sobre la misma base que paga el motor."""
    _productos(utils)
    plan = _plan(catalogo)
    base = plan["baseComision"]
    assert base["compraEjemplo"] == 960 and base["canastaEjemplo"] == "2 × Klinhart"
    assert base["clave"] == "neto pagado por producto, sin envío"
    assert "sin contar el envío" in base["frase"]
    gen1 = plan["generaciones"][0]
    assert gen1["ejemplo"]["comision"] == round(base["compraEjemplo"] * gen1["rate"], 2)


def test_el_plan_dice_el_iva_que_llevan_dentro_los_precios(catalogo, utils):
    """Propuesta 38: ningún número queda sin explicación en la página del plan."""
    plan = _plan(catalogo)
    assert plan["iva"] == {"tasa": 0.16, "etiqueta": "IVA",
                           "preciosIncluyenIva": True, "aplicaAlEnvio": True}


def test_los_ejemplos_cuadran_con_la_escalera_real_y_con_las_generaciones(catalogo, utils):
    import order_lambda
    _productos(utils)
    plan = _plan(catalogo)
    tiers = utils._load_app_config()["rewards"]["discountTiers"]
    assert len(plan["descuento"]["ejemplos"]) == 4
    for ejemplo in plan["descuento"]["ejemplos"]:
        tasa = order_lambda._resolve_discount_rate(tiers, Decimal(str(ejemplo["compraMes"])))
        assert Decimal(str(ejemplo["rate"])) == tasa
        assert Decimal(str(ejemplo["descuento"])) == (Decimal(str(ejemplo["compraMes"])) * tasa).quantize(Decimal("0.01"))
        assert ejemplo["pagas"] == ejemplo["compraMes"] - ejemplo["descuento"]
    assert plan["descuento"]["ejemplos"][0] == {"compraMes": 1200, "rate": 0.10, "descuento": 120, "pagas": 1080}

    g = {x["gen"]: x for x in plan["generaciones"]}
    # La compra de referencia es el neto de la canasta más barata que de verdad
    # activa (2 × Klinhart = $960 sin descuento), no el "más o menos $1,000".
    assert g[1]["requisitoTexto"] == "sin requisito" and g[1]["ejemplo"] == {"compraReferido": 960, "comision": 96}
    assert g[2]["requisitoTexto"] == "2 directas activas" and g[2]["ejemplo"]["comision"] == 48
    assert g[3]["requisitoTexto"] == "3 directas activas y 80 PC personales y 2 líneas con 300 PC cada una"
    assert g[3]["requisitos"] == {"activeDirects": 3, "personalPC": 80, "lines": 2, "pcPerLine": 300}


def test_el_plan_refleja_los_cambios_de_configuracion(catalogo, utils):
    """Si la gerente cambia la escalera o una generación, la página cambia sola."""
    cfg = {
        "rewards": {
            "discountTiers": [{"min": 0, "max": 500, "rate": 0}, {"min": 500, "max": None, "rate": Decimal("0.15")}],
            "commissionLevels": [{"gen": 1, "rate": Decimal("0.12"), "reqActiveDirects": 0, "reqPersonalPC": 0, "reqLines": 0, "reqPCPerLine": 0},
                                 {"gen": 2, "rate": Decimal("0.06"), "reqActiveDirects": 1, "reqPersonalPC": 0, "reqLines": 0, "reqPCPerLine": 0}],
            "payoutDay": 15,
        }
    }
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": cfg})
    utils._invalidate_app_config_cache()
    plan = _plan(catalogo)
    assert [t["rate"] for t in plan["descuento"]["tramos"]] == [0, 0.15]
    assert plan["descuento"]["ejemplos"] == [{"compraMes": 600, "rate": 0.15, "descuento": 90, "pagas": 510}]
    assert [g["rate"] for g in plan["generaciones"]] == [0.12, 0.06]
    assert plan["generaciones"][1]["requisitoTexto"] == "1 directa activa"
    assert plan["pago"]["dia"] == 15
    assert plan["activacion"]["nota"] == "20 PC de lista con 15 % de descuento = 17 VP: no activa."


def test_el_handler_del_plan_no_lleva_numeros_del_negocio_escritos(utils):
    """Ningún porcentaje ni umbral vive en el código: todo sale de `core/config`."""
    import modo_handlers
    fuente = inspect.getsource(modo_handlers.construir_plan) + inspect.getsource(modo_handlers._generaciones) \
        + inspect.getsource(modo_handlers._ejemplos_descuento) + inspect.getsource(modo_handlers._ejemplos_activacion)
    prohibidos = re.findall(r"(?<![\w.])(?:1000|2000|3000|6000|0\.10|0\.05|0\.04|0\.03|0\.02|0\.40|4500|9000)(?![\w.])", fuente)
    assert not prohibidos, prohibidos


def test_las_rutas_nuevas_declaran_su_privilegio(utils):
    import catalog_lambda
    tabla = {f["patron"]: f for f in utils.routing.describir(catalog_lambda.RUTAS)}
    assert tabla["/catalog/plan"]["privilegio"] == "público" and tabla["/catalog/plan"]["metodo"] == "GET"
