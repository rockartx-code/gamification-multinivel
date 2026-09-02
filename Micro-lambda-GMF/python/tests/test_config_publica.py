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


def test_renombrar_una_categoria_no_la_duplica_y_borrar_borra_la_elegida(utils):
    """La gerente renombró "Proteínas" y apareció una segunda; "eliminar" borró
    la más reciente en vez de la seleccionada."""
    import json, catalog_lambda
    r = catalog_lambda.handle_categories("POST", {"name": "Proteínas"}, None)
    cid = json.loads(r["body"])["category"]["categoryId"]
    r = catalog_lambda.handle_categories("POST", {"name": "Bienestar"}, None)
    otra = json.loads(r["body"])["category"]["categoryId"]
    r = catalog_lambda.handle_categories("POST", {"id": cid, "name": "Proteínas y colágeno"}, None)
    assert r["statusCode"] == 200, r["body"]
    cats = json.loads(catalog_lambda.handle_categories("GET", {}, None)["body"])["categories"]
    assert sorted(c["name"] for c in cats) == ["Bienestar", "Proteínas y colágeno"]
    catalog_lambda.handle_categories("DELETE", {}, otra)
    cats = json.loads(catalog_lambda.handle_categories("GET", {}, None)["body"])["categories"]
    assert [c["name"] for c in cats] == ["Proteínas y colágeno"]
