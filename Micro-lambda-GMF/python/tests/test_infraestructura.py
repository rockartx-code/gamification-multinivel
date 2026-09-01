"""La plantilla de infraestructura no debe desincronizarse del código.

Una plantilla que declara un handler inexistente o una variable de entorno que
nadie lee es peor que no tenerla: da falsa confianza. Estas pruebas la atan al
código real.
"""
import io
import os
import re

import pytest

yaml = pytest.importorskip("yaml")

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLANTILLA = os.path.join(RAIZ, "..", "template.yaml")


class _Loader(yaml.SafeLoader):
    """CloudFormation usa etiquetas propias (!Ref, !Sub, …) que aquí no importan."""


_Loader.add_multi_constructor("!", lambda loader, sufijo, nodo: None)


@pytest.fixture(scope="module")
def plantilla():
    if not os.path.exists(PLANTILLA):
        pytest.skip("template.yaml no encontrado")
    return yaml.load(io.open(PLANTILLA, encoding="utf-8"), Loader=_Loader)


def _funciones(plantilla):
    return {
        nombre: recurso["Properties"]
        for nombre, recurso in plantilla["Resources"].items()
        if recurso.get("Type") == "AWS::Serverless::Function"
    }


def test_cada_handler_declarado_existe_en_el_codigo(plantilla):
    for nombre, props in _funciones(plantilla).items():
        modulo, funcion = props["Handler"].rsplit(".", 1)
        archivo = os.path.join(RAIZ, f"{modulo}.py")
        assert os.path.exists(archivo), f"{nombre}: no existe {modulo}.py"
        texto = io.open(archivo, encoding="utf-8").read()
        assert re.search(rf"^def {funcion}\(", texto, re.M), \
            f"{nombre}: {modulo}.py no define {funcion}()"


def test_el_handler_de_clientes_usa_el_nombre_corregido(plantilla):
    """El typo `costumer` no debe reaparecer en la infraestructura."""
    handlers = [p["Handler"] for p in _funciones(plantilla).values()]
    assert "customer_lambda.lambda_handler" in handlers
    assert not any("costumer" in h for h in handlers)


def test_el_ttl_de_la_tabla_esta_habilitado(plantilla):
    """El código escribe el atributo `ttl`; sin esto no se purga nada."""
    tabla = plantilla["Resources"]["TablaMultinivel"]["Properties"]
    ttl = tabla.get("TimeToLiveSpecification") or {}
    assert ttl.get("Enabled") is True
    assert ttl.get("AttributeName") == "ttl"


def test_el_rol_no_concede_barrido_de_tabla(plantilla):
    """El backend no hace ni un `scan`; el permiso tampoco debe existir."""
    acciones = set()
    for recurso in plantilla["Resources"].values():
        if recurso.get("Type") != "AWS::IAM::ManagedPolicy":
            continue
        for sentencia in recurso["Properties"]["PolicyDocument"]["Statement"]:
            accion = sentencia.get("Action")
            acciones |= set(accion if isinstance(accion, list) else [accion])
    prohibidas = {a for a in acciones if a and a.lower().endswith(":scan")}
    assert not prohibidas, f"permisos de barrido concedidos: {prohibidas}"


def test_las_variables_de_entorno_estan_documentadas(plantilla):
    """Toda variable declarada debe aparecer en .env.example."""
    ejemplo = io.open(os.path.join(RAIZ, ".env.example"), encoding="utf-8").read()
    documentadas = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", ejemplo, re.M))

    declaradas = set(
        (plantilla.get("Globals", {}).get("Function", {}).get("Environment", {}) or {})
        .get("Variables", {})
    )
    for props in _funciones(plantilla).values():
        declaradas |= set((props.get("Environment") or {}).get("Variables", {}))

    # STATE_MACHINE_ARN lo inyecta la propia plantilla, no es configuración.
    faltan = sorted(declaradas - documentadas)
    assert not faltan, f"variables sin documentar en .env.example: {faltan}"


def test_el_codigo_no_lee_variables_no_declaradas(plantilla):
    """Toda `os.getenv` del backend debe estar declarada o documentada."""
    leidas = set()
    for archivo in os.listdir(RAIZ):
        if archivo.endswith(".py"):
            texto = io.open(os.path.join(RAIZ, archivo), encoding="utf-8").read()
            leidas |= set(re.findall(r'os\.getenv\(\s*"([A-Z_][A-Z0-9_]*)"', texto))
    for archivo in os.listdir(os.path.join(RAIZ, "core")):
        if archivo.endswith(".py"):
            texto = io.open(os.path.join(RAIZ, "core", archivo), encoding="utf-8").read()
            leidas |= set(re.findall(r'os\.getenv\(\s*"([A-Z_][A-Z0-9_]*)"', texto))

    ejemplo = io.open(os.path.join(RAIZ, ".env.example"), encoding="utf-8").read()
    documentadas = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", ejemplo, re.M))
    # AWS_REGION la inyecta el runtime de Lambda.
    faltan = sorted(leidas - documentadas - {"AWS_REGION"})
    assert not faltan, f"variables leídas pero no documentadas: {faltan}"
