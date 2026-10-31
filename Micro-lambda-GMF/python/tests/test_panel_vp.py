"""El panel del socio debe mostrar los mismos puntos que paga el motor."""
from decimal import Decimal


def test_el_panel_usa_los_puntos_del_catalogo_y_no_pesos_entre_tarifa(utils):
    """Regresión: 2 × Klinhart (10 PC cada uno, $480) = 20 PC según la tienda y
    según el motor (netVP=20), pero el panel mostraba 960/50 = 19.2."""
    import dashboard_common as dash
    estado = {"netVolume": Decimal("960"), "netVP": Decimal("20")}
    assert dash._state_vp_dash(estado, 50.0) == 20.0


def test_sin_netvp_el_panel_sigue_convirtiendo_por_tarifa(utils):
    import dashboard_common as dash
    assert dash._state_vp_dash({"netVolume": Decimal("960")}, 50.0) == 19.2
    assert dash._state_vp_dash({}, 50.0) == 0.0


def test_vg_de_directos_suma_puntos_reales(utils):
    import dashboard_common as dash
    clientes = [{"customerId": 2, "leaderId": 1}, {"customerId": 3, "leaderId": 1}, {"customerId": 4, "leaderId": 9}]
    estados = {"2": {"netVolume": Decimal("960"), "netVP": Decimal("20")}, "3": {"netVolume": Decimal("500")}, "4": {"netVP": Decimal("99")}}
    assert dash._get_direct_vg_dash("1", "2026-09", clientes, 50.0, month_states=estados) == 30.0


def test_el_cuadro_de_honor_usa_los_mismos_puntos_que_el_panel(utils, monkeypatch):
    """Regresión: el Cuadro de Honor calculaba VP = pesos ÷ tarifa (960/50 = 19.2)
    mientras el panel del mismo socio decía 20 VP (puntos del catálogo)."""
    import dashboard_lambda as dl
    utils._put_entity("CUSTOMER", 1, {"entityType": "customer", "customerId": 1, "name": "Rodri", "leaderId": None})
    utils._put_entity("CUSTOMER", 2, {"entityType": "customer", "customerId": 2, "name": "Patricia", "leaderId": 1})
    mes = utils._month_key()
    for cid, vol, vp in ((1, "960", "20"), (2, "700", "13")):
        utils._put_entity("ASSOCIATE_MONTH", utils._associate_month_entity_id(cid, mes),
                          {"entityType": "associateMonth", "associateId": cid, "month": mes,
                           "netVolume": Decimal(vol), "netVP": Decimal(vp)})
    tablero = dl.get_honor_board()
    cuerpo = tablero.get("body") or tablero
    import json
    datos = json.loads(cuerpo) if isinstance(cuerpo, str) else cuerpo
    por_vp = {e["name"]: e["vp"] for e in datos["byVp"]}
    assert por_vp.get("Rodri") == 20.0, datos
    assert por_vp.get("Patricia") == 13.0, datos
