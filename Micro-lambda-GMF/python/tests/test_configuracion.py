"""La configuración del negocio debe tener una sola fuente de verdad."""
import io
import os
import re
from decimal import Decimal

MODULOS = [
    f for f in sorted(os.listdir(os.path.join(os.path.dirname(__file__), "..")))
    if f.endswith(".py")
]
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def test_ningun_modulo_repite_un_default_de_configuracion():
    """Prohíbe `cfg.get("activationNetMin", <valor>)` fuera de core_utils.

    Estas claves llegaron a leerse con tres defaults distintos (2500 en MXN,
    50 y 20 en PC) según el módulo: si la clave no estaba guardada, la misma
    persona salía activa en una pantalla e inactiva en otra.
    """
    claves = ("activationNetMin", "mxnPerVp", "maxNetworkLevels")
    infracciones = []
    for modulo in MODULOS:
        if modulo == "core_utils.py":
            continue
        texto = io.open(os.path.join(RAIZ, modulo), encoding="utf-8").read()
        for numero, linea in enumerate(texto.split("\n"), 1):
            for clave in claves:
                if re.search(rf'get\(\s*"{clave}"\s*,', linea):
                    infracciones.append(f"{modulo}:{numero} {linea.strip()}")
    assert not infracciones, "Usar los accesores de core_utils:\n" + "\n".join(infracciones)


def test_la_config_cargada_siempre_trae_las_claves(utils):
    """`_load_app_config` fusiona lo guardado sobre los defaults."""
    cfg = utils._load_app_config()
    assert cfg["rewards"]["activationNetMin"] == Decimal("20")
    assert len(cfg["rewards"]["commissionLevels"]) == 5
    assert cfg["bonuses"]["vpConfig"]["mxnPerVp"] == Decimal("50")


def test_lo_guardado_gana_sobre_el_default(utils, store):
    now = "2026-01-01T00:00:00Z"
    store[("CONFIG#app-v1", "REF")] = {
        "PK": "CONFIG#app-v1", "SK": "REF", "refPK": "CONFIG", "refSK": f"{now}#app-v1",
    }
    store[("CONFIG", f"{now}#app-v1")] = {
        "PK": "CONFIG", "SK": f"{now}#app-v1",
        "config": {"rewards": {"activationNetMin": Decimal("35")}},
    }
    utils._invalidate_app_config_cache()
    cfg = utils._load_app_config()
    assert cfg["rewards"]["activationNetMin"] == Decimal("35"), "lo guardado manda"
    assert len(cfg["rewards"]["commissionLevels"]) == 5, "el resto sigue viniendo del default"


def test_la_activacion_se_expresa_en_pc_y_en_mxn(utils):
    """20 PC × $50/PC = $1,000 netos (Plan §3)."""
    assert utils._activation_vp() == 20.0
    assert utils._activation_mxn() == 1000.0


def test_el_arbol_de_red_marca_activo_comparando_en_pc(utils, store, monkeypatch):
    """Regresión: el árbol comparaba `netVolume` en MXN contra un umbral en PC.

    Con el umbral del plan (20 PC) eso daba «activo» a cualquiera que hubiera
    comprado más de 20 pesos, en vez de los $1,000 netos que exige el plan.
    """
    import dashboard_lambda

    month_key = utils._month_key()
    clientes = [
        {"customerId": 1, "name": "Compra 900", "leaderId": None},
        {"customerId": 2, "name": "Compra 1000", "leaderId": None},
    ]
    estados = {"1": {"netVolume": Decimal("900")}, "2": {"netVolume": Decimal("1000")}}
    nodos, _ = dashboard_lambda._build_month_node_index(
        month_key, clientes, utils._load_app_config()["rewards"], estados
    )
    assert nodos["1"]["isActive"] is False, "$900 netos = 18 PC < 20 PC"
    assert nodos["2"]["isActive"] is True, "$1,000 netos = 20 PC"
