"""El simulador del plan (paquete B, propuesta 36).

Ximena Paredes hizo 16 tareas y **10 de ellas sin un solo clic**: se pasó la
sesión con lápiz y papel calculando si el negocio le convenía, porque la
plataforma publica el plan pero no publica ganancias. Sacó a mano que
*"para recuperar los ~$1,350 que tengo que gastar cada mes necesito diez
personas comprando $1,350 cada una, todos los meses"*, y cerró con
*"Ese número contesta solo. No voy a poner a mis amigas ahí."*
(`ximena-paredes-2027-03-02.md`).

`POST /catalog/plan/simular` hace esa cuenta con los porcentajes, los
requisitos y la escalera reales de la configuración, y enseña **siempre** la
ganancia neta, también cuando sale en rojo.
"""
import json
from decimal import Decimal

import pytest


@pytest.fixture
def catalogo(utils):
    import catalog_lambda
    return catalog_lambda


def _simular(catalog_lambda, cuerpo: dict):
    r = catalog_lambda.lambda_handler({"httpMethod": "POST", "path": "/catalog/plan/simular",
                                       "headers": {}, "body": json.dumps(cuerpo)}, None)
    return r["statusCode"], json.loads(r["body"])


def test_el_simulador_es_publico_y_declara_su_ruta(catalogo, utils):
    """Se contesta sin sesión: quien viene a decidir si esto es un negocio
    todavía no tiene cuenta."""
    tabla = {f["patron"]: f for f in utils.routing.describir(catalogo.RUTAS)}
    assert tabla["/catalog/plan/simular"]["privilegio"] == "público"
    assert tabla["/catalog/plan/simular"]["metodo"] == "POST"
    codigo, _ = _simular(catalogo, {"directos": 0, "compraPorDirecto": 0, "compraPropia": 0})
    assert codigo == 200


def test_el_caso_honesto_de_ximena_sale_en_rojo_y_lo_dice(catalogo, utils):
    """2 directas × $1,000 y $1,120 de compra propia: comisión $200, gasto
    $1,008 (el neto tras el 10 %) y el resultado del mes en negativo."""
    codigo, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 1000,
                                         "compraPropia": 1120, "nivelesProfundidad": 1})
    assert codigo == 200
    s = cuerpo["simulacion"]
    assert s["comisionTotal"] == 200
    assert s["tuCompra"] == {"bruto": 1120, "tramo": 0.10, "descuento": 112, "netoPagado": 1008,
                             "vp": 20.16, "activa": True, "vpParaActivar": 20,
                             "iva": {"base": 868.97, "iva": 139.03, "tasa": 0.16, "etiqueta": "IVA"}}
    assert s["gastoPropio"] == 1008 and s["gananciaNeta"] == -808
    assert s["explicacion"][0] == "Con 2 directas que compran $1,000.00 ganas $200.00 al mes."
    assert s["explicacion"][1] == "Tú pagaste $1,008.00 para activarte: tu resultado del mes es -$808.00."


def test_la_ganancia_neta_se_muestra_tambien_cuando_es_negativa(catalogo, utils):
    """§4.10: el simulador nunca esconde el número feo."""
    _, cuerpo = _simular(catalogo, {"directos": 1, "compraPorDirecto": 500, "compraPropia": 3000})
    s = cuerpo["simulacion"]
    assert s["gananciaNeta"] < 0
    assert "-$" in s["explicacion"][1]


def test_todo_sale_de_la_configuracion_y_nada_esta_escrito_a_mano(catalogo, utils):
    """Si la gerente cambia la generación 1 al 12 %, el simulador cambia solo."""
    cfg = {"rewards": {"commissionLevels": [
        {"gen": 1, "rate": Decimal("0.12"), "reqActiveDirects": 0, "reqPersonalPC": 0,
         "reqLines": 0, "reqPCPerLine": 0}]}}
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": cfg})
    utils._invalidate_app_config_cache()
    _, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 1000, "compraPropia": 1120})
    assert cuerpo["simulacion"]["generaciones"][0]["rate"] == 0.12
    assert cuerpo["simulacion"]["comisionTotal"] == 240


def test_sin_activarse_las_comisiones_quedan_bloqueadas_y_se_explica_por_que(catalogo, utils):
    """La misma regla que aplica el motor: sin activación no se cobra."""
    _, cuerpo = _simular(catalogo, {"directos": 3, "compraPorDirecto": 1000, "compraPropia": 500})
    s = cuerpo["simulacion"]
    assert s["tuCompra"]["activa"] is False and s["tuCompra"]["vp"] == 10
    assert s["comisionTotal"] == 0
    gen1 = s["generaciones"][0]
    assert gen1["cumple"] is False
    assert gen1["porQue"] == "no activas el mes: llevas 10 VP netos de los 20 que pide la activación"
    assert "quedan bloqueadas" in s["explicacion"][-1]


def test_cada_generacion_dice_si_cumple_su_requisito_y_por_que_no(catalogo, utils):
    """La generación 2 pide 2 directas activas: con una sola, se dice cuántas faltan."""
    _, cuerpo = _simular(catalogo, {"directos": 1, "compraPorDirecto": 1000,
                                    "compraPropia": 1200, "nivelesProfundidad": 3})
    gens = {g["gen"]: g for g in cuerpo["simulacion"]["generaciones"]}
    assert gens[1]["cumple"] is True and gens[1]["comision"] == 100
    assert gens[2]["cumple"] is False and gens[2]["comision"] == 0
    assert gens[2]["porQue"] == "te faltan 1 directas activas de las 2 que pide"
    assert gens[3]["cumple"] is False and "PC personales" in gens[3]["porQue"]
    assert cuerpo["simulacion"]["comisionTotal"] == 100


def test_cada_fila_dice_sobre_que_base_se_paga(catalogo, utils):
    """Propuesta 37, con la frase única de `impuestos.texto_base_comision`."""
    _, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 675, "compraPropia": 1200})
    gen1 = cuerpo["simulacion"]["generaciones"][0]
    assert gen1["textoBase"] == "10 % de $1,350.00 netos, sin envío = $135.00"
    assert cuerpo["simulacion"]["baseComision"] == "neto pagado por producto, sin envío"
    assert "sin contar el envío" in cuerpo["simulacion"]["fraseBaseComision"]


def test_el_simulador_desglosa_el_iva_de_tu_propia_compra(catalogo, utils):
    """Propuesta 38: ningún número del simulador queda sin explicación."""
    _, cuerpo = _simular(catalogo, {"directos": 0, "compraPorDirecto": 0, "compraPropia": 1350})
    iva = cuerpo["simulacion"]["tuCompra"]["iva"]
    assert iva["base"] + iva["iva"] == cuerpo["simulacion"]["tuCompra"]["netoPagado"]


def test_el_simulador_no_promete_ni_extrapola(catalogo, utils):
    """§4.10: aviso fijo, supuestos dichos y ninguna red que crezca sola."""
    _, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 1000,
                                    "compraPropia": 1120, "nivelesProfundidad": 3})
    s = cuerpo["simulacion"]
    assert s["aviso"] == "Esto es una calculadora con las reglas del plan, no una promesa de ingresos."
    assert any("no suponemos que tu red crezca sola" in t for t in s["supuestos"])
    # Las tres generaciones usan las mismas personas capturadas: nada de 2, 4, 8.
    assert [g["personas"] for g in s["generaciones"]] == [2, 2, 2]


def test_los_topes_se_dicen_con_su_numero_en_vez_de_recortar_en_silencio(catalogo, utils):
    codigo, cuerpo = _simular(catalogo, {"directos": 500, "compraPorDirecto": 1000, "compraPropia": 0})
    assert codigo == 400 and cuerpo["message"] == "El número de personas directas tiene que estar entre 0 y 100."

    codigo, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 250000, "compraPropia": 0})
    assert codigo == 400 and cuerpo["message"] == "Lo que compra cada persona tiene que estar entre $0 y $100,000.00."

    codigo, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 100, "compraPropia": -5})
    assert codigo == 400 and cuerpo["message"] == "Tu propia compra tiene que estar entre $0 y $100,000.00."

    codigo, cuerpo = _simular(catalogo, {"directos": 2, "compraPorDirecto": 100,
                                         "compraPropia": 100, "nivelesProfundidad": 9})
    assert codigo == 400 and cuerpo["message"] == "Los niveles de profundidad tiene que estar entre 1 y 5."


def test_la_simulacion_en_ceros_no_revienta_ni_promete(catalogo, utils):
    codigo, cuerpo = _simular(catalogo, {"directos": 0, "compraPorDirecto": 0, "compraPropia": 0})
    s = cuerpo["simulacion"]
    assert codigo == 200 and s["comisionTotal"] == 0 and s["gananciaNeta"] == 0
    assert s["explicacion"][0] == "Sin nadie en tu red comprando este mes, tu comisión es de $0.00."


def test_el_simulador_usa_la_misma_escalera_que_cobra_el_pedido(catalogo, utils):
    """Si el simulador y el carrito no dan lo mismo, vuelve la desconfianza."""
    import order_lambda
    tiers = utils._load_app_config()["rewards"]["discountTiers"]
    for bruto in (500, 1200, 2500, 6500):
        _, cuerpo = _simular(catalogo, {"directos": 0, "compraPorDirecto": 0, "compraPropia": bruto})
        esperado = order_lambda._resolve_discount_rate(tiers, Decimal(str(bruto)))
        assert Decimal(str(cuerpo["simulacion"]["tuCompra"]["tramo"])) == esperado
