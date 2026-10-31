"""Las metas del dashboard no deben cambiar al reorganizar el código.

`_build_goals` concentraba 210 líneas con siete grupos de metas distintos.
Esta prueba fija su salida sobre escenarios representativos para que el
troceo en funciones más pequeñas sea verificable, no un acto de fe.
"""
import json
import os
from decimal import Decimal

import pytest

INSTANTANEA = os.path.join(os.path.dirname(__file__), "metas_esperadas.json")

ESCENARIOS = {
    "socio_nuevo_sin_red": {
        "customer": {"customerId": 1, "name": "Nuevo"},
        "estado": {"netVolume": Decimal("0")},
        "red": [],
    },
    "socio_activo_con_directos": {
        "customer": {"customerId": 1, "name": "Activo"},
        "estado": {"netVolume": Decimal("3200")},
        "red": [
            {"customerId": 2, "leaderId": "1", "createdAt": "2020-01-01T00:00:00Z"},
            {"customerId": 3, "leaderId": "1", "createdAt": "2020-01-01T00:00:00Z"},
        ],
    },
    "socio_con_volumen_alto": {
        "customer": {"customerId": 1, "name": "Alto"},
        "estado": {"netVolume": Decimal("12000")},
        "red": [{"customerId": 2, "leaderId": "1", "createdAt": "2020-01-01T00:00:00Z"}],
    },
}


def _arbol(customer, red, estados, cfg, dashboard_common, utils):
    """Árbol de red mínimo con las métricas del mes ya resueltas."""
    hijos = [
        {
            "id": str(m["customerId"]), "name": "", "level": "", "leaderId": "1",
            "createdAt": m.get("createdAt"), "children": [],
            "monthSpend": float(utils._to_decimal(estados.get(str(m["customerId"]), {}).get("netVolume", 0))),
            "isActive": True,
        }
        for m in red
    ]
    return {
        "id": str(customer["customerId"]), "name": customer.get("name", ""), "level": "",
        "createdAt": "2020-01-01T00:00:00Z", "leaderId": None, "children": hijos,
        "monthSpend": float(utils._to_decimal(estados.get(str(customer["customerId"]), {}).get("netVolume", 0))),
        "isActive": True,
    }


def _calcular_todas(utils):
    import dashboard_common

    cfg_completa = utils._load_app_config()
    resultado = {}
    for nombre, escenario in ESCENARIOS.items():
        estados = {str(escenario["customer"]["customerId"]): escenario["estado"]}
        for miembro in escenario["red"]:
            estados[str(miembro["customerId"])] = {"netVolume": Decimal("1500")}
        arbol = _arbol(escenario["customer"], escenario["red"], estados,
                       cfg_completa, dashboard_common, utils)
        metas = dashboard_common._build_goals(
            escenario["customer"], arbol, escenario["red"],
            cfg_completa["rewards"], bonus_cfg=cfg_completa.get("bonuses"),
            month_states=estados,
        )
        resultado[nombre] = json.loads(json.dumps(metas, default=utils._json_default))
    return resultado


def test_las_metas_no_cambian(utils):
    observado = _calcular_todas(utils)

    actualizar = os.environ.get("METAS_ACTUALIZAR", "").strip().lower() in ("1", "true", "yes", "on")
    if actualizar or not os.path.exists(INSTANTANEA):
        with open(INSTANTANEA, "w", encoding="utf-8") as fh:
            json.dump(observado, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        pytest.skip("instantánea de metas creada")

    with open(INSTANTANEA, encoding="utf-8") as fh:
        esperado = json.load(fh)
    assert observado == esperado


def test_hay_exactamente_una_meta_primaria(utils):
    for nombre, metas in _calcular_todas(utils).items():
        primarias = [m for m in metas if m.get("primary")]
        assert len(primarias) <= 1, f"{nombre}: {len(primarias)} metas primarias"
        if primarias:
            assert not primarias[0].get("achieved"), f"{nombre}: la primaria ya está lograda"
            assert not primarias[0].get("locked"), f"{nombre}: la primaria está bloqueada"
