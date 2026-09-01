"""Las fronteras del paquete `core` no deben degradarse.

El valor de partir `core_utils` no está en tener 13 archivos, sino en que las
dependencias vayan en una sola dirección. Sin una prueba, la primera urgencia
reintroduce un ciclo y volvemos al módulo de 2,000 líneas repartido en trozos.
"""
import ast
import io
import os

import pytest

CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core")

#: Orden de capas. Un módulo solo puede importar de los ANTERIORES.
CAPAS = ["settings", "domain", "values", "logs", "http", "db",
         "config", "network", "entities", "indexes", "ledger",
         "security", "email", "audit"]
NIVEL = {m: i for i, m in enumerate(CAPAS)}


def _imports_del_paquete(modulo):
    arbol = ast.parse(io.open(os.path.join(CORE, f"{modulo}.py"), encoding="utf-8").read())
    destinos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.level == 1:
            if nodo.module:
                destinos.add(nodo.module)
            else:                                   # from . import db
                destinos.update(a.name for a in nodo.names)
    return destinos


@pytest.mark.parametrize("modulo", CAPAS)
def test_las_dependencias_van_en_una_sola_direccion(modulo):
    for destino in _imports_del_paquete(modulo):
        assert destino in NIVEL, f"{modulo} importa un módulo desconocido: {destino}"
        assert NIVEL[destino] < NIVEL[modulo], (
            f"{modulo} importa {destino}, que está en su mismo nivel o por encima: "
            "eso es un ciclo o una inversión de capas"
        )


def test_la_capa_de_datos_no_conoce_entidades_de_negocio():
    """`core.db` no debe traer dentro un `if entity == "ALGO"`.

    Las entidades con clave no estándar se registran (`register_entity_reader`),
    que es lo que permitió separar el acceso a datos del dominio.
    """
    texto = io.open(os.path.join(CORE, "db.py"), encoding="utf-8").read()
    for entidad in ("ASSOCIATE_MONTH", "CUSTOMER", "ORDER", "COMMISSION_MONTH"):
        assert f'== "{entidad}"' not in texto, (
            f"core/db.py decide según la entidad {entidad}: usar el registro de lectores"
        )


def test_la_fachada_solo_reexporta():
    """`core_utils` no debe volver a acumular lógica propia."""
    arbol = ast.parse(io.open(os.path.join(CORE, "..", "core_utils.py"), encoding="utf-8").read())
    definiciones = [
        n.name for n in arbol.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert not definiciones, f"la fachada define lógica propia: {definiciones}"


def test_la_fachada_expone_todo_lo_que_usan_los_lambdas():
    """Ningún `utils.X` de los lambdas puede quedarse sin resolver."""
    import re
    import core_utils

    raiz = os.path.join(CORE, "..")
    usados = set()
    for archivo in os.listdir(raiz):
        if archivo.endswith(".py") and archivo != "core_utils.py":
            texto = io.open(os.path.join(raiz, archivo), encoding="utf-8").read()
            usados |= set(re.findall(r"utils\.(\w+)", texto))
    faltan = sorted(n for n in usados if not hasattr(core_utils, n))
    assert not faltan, f"la fachada no expone: {faltan}"
