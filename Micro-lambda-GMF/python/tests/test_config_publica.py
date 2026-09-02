"""La landing es la única tabla pública del plan: tiene que traer los requisitos."""
import json


def test_la_config_publica_trae_requisitos_por_generacion_y_regla_de_corte(utils):
    import catalog_lambda
    r = catalog_lambda.handle_public_config()
    assert r["statusCode"] == 200
    cfg = json.loads(r["body"]); cfg = cfg.get("config") or cfg
    niveles = cfg["rewards"]["commissionLevels"]
    assert [n["gen"] for n in niveles] == [1, 2, 3, 4, 5]
    assert niveles[2]["reqActiveDirects"] == 3 and niveles[2]["reqPersonalPC"] == 80 and niveles[2]["reqLines"] == 2 and niveles[2]["reqPCPerLine"] == 300
    assert cfg["rewards"]["cutRule"] == "dynamic_compression"
