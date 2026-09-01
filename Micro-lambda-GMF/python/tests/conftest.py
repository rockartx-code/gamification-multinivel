"""Infraestructura común de las pruebas: DynamoDB en memoria.

Las pruebas no tocan AWS. Se sustituye la tabla por una implementación en
memoria que respeta las condiciones de clave y la paginación, de modo que el
código de producción se ejercita tal cual, sin ramas de "modo test".
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") )
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from boto3.dynamodb.conditions import (  # noqa: E402
    And, BeginsWith, Between, Equals, GreaterThanEquals, LessThanEquals,
)


def _matches(condition, pk, sk):
    if isinstance(condition, And):
        return all(_matches(v, pk, sk) for v in condition._values)
    attr, *values = condition._values
    actual = pk if attr.name == "PK" else sk
    if isinstance(condition, Equals):
        return actual == values[0]
    if isinstance(condition, BeginsWith):
        return str(actual).startswith(str(values[0]))
    if isinstance(condition, Between):
        return str(values[0]) <= str(actual) <= str(values[1])
    if isinstance(condition, GreaterThanEquals):
        return str(actual) >= str(values[0])
    if isinstance(condition, LessThanEquals):
        return str(actual) <= str(values[0])
    raise AssertionError(f"condición no soportada en el doble de prueba: {type(condition).__name__}")


class FakeTable:
    """Tabla DynamoDB en memoria con soporte de KeyCondition y paginación."""

    meta = type("Meta", (), {"client": None})

    def __init__(self, store, page_size=25):
        self.store = store
        self.page_size = page_size

    def get_item(self, Key=None, **kw):
        item = self.store.get((str(Key["PK"]), str(Key["SK"])))
        return {"Item": dict(item)} if item else {}

    def put_item(self, Item=None, ConditionExpression=None,
                 ExpressionAttributeValues=None, **kw):
        key = (str(Item["PK"]), str(Item["SK"]))
        if ConditionExpression is not None:
            self._check_condition(ConditionExpression, ExpressionAttributeValues or {},
                                  self.store.get(key))
        self.store[key] = dict(Item)
        return {}

    @staticmethod
    def _check_condition(expression, values, current):
        """Evalúa las condiciones que usa el backend, con semántica REAL.

        En DynamoDB `version = :v` FALLA si el atributo no existe: no lo trata
        como cero. El fake anterior era más permisivo que DynamoDB y por eso
        la suite no cazó un candado optimista que jamás podía escribir sobre
        items legados sin `version`.
        """
        import re as _re
        from botocore.exceptions import ClientError as _ClientError

        def _fail():
            raise _ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException",
                           "Message": "The conditional request failed"}},
                "PutItem",
            )

        for disjunct in [p.strip() for p in str(expression).split(" OR ")]:
            m = _re.fullmatch(r"attribute_not_exists\((\w+)\)", disjunct)
            if m:
                attr = m.group(1)
                if current is None or attr not in current:
                    return
                continue
            m = _re.fullmatch(r"(\w+) = (:\w+)", disjunct)
            if m:
                attr, placeholder = m.groups()
                if (current is not None and attr in current
                        and str(current[attr]) == str(values.get(placeholder))):
                    return
                continue
            raise AssertionError(f"condición no soportada en el fake: {disjunct}")
        _fail()

    def delete_item(self, Key=None, **kw):
        self.store.pop((str(Key["PK"]), str(Key["SK"])), None)
        return {}

    def update_item(self, Key=None, **kw):
        return {"Attributes": dict(self.store.get((str(Key["PK"]), str(Key["SK"])), {}))}

    def query(self, **kw):
        rows = [
            dict(v) for (p, s), v in self.store.items()
            if _matches(kw["KeyConditionExpression"], p, s)
        ]
        rows.sort(key=lambda i: str(i["SK"]), reverse=not kw.get("ScanIndexForward", False))
        start = kw.get("ExclusiveStartKey")
        if start:
            keys = [r["SK"] for r in rows]
            rows = rows[keys.index(start["SK"]) + 1:]
        size = min(kw.get("Limit", self.page_size), self.page_size)
        page, rest = rows[:size], rows[size:]
        out = {"Items": page}
        if rest and page:
            out["LastEvaluatedKey"] = {"PK": page[-1]["PK"], "SK": page[-1]["SK"]}
        return out


class FakeResource:
    def __init__(self, store):
        self.store = store

    def Table(self, _name):
        return FakeTable(self.store)

    def batch_get_item(self, RequestItems=None, **kw):
        table_name = list(RequestItems)[0]
        found = []
        for key in RequestItems[table_name]["Keys"]:
            item = self.store.get((str(key["PK"]), str(key["SK"])))
            if item:
                found.append(dict(item))
        return {"Responses": {table_name: found}, "UnprocessedKeys": {}}


@pytest.fixture
def store():
    return {}


@pytest.fixture
def utils(store, monkeypatch):
    """`core_utils` apuntando a la tabla en memoria, con la caché limpia."""
    import boto3
    monkeypatch.setattr(boto3, "resource", lambda *a, **k: FakeResource(store))
    monkeypatch.setattr(boto3, "client", lambda *a, **k: None)
    import core_utils
    from core import db as core_db

    # La costura está en `core.db`, no en la fachada: `core_utils` reexporta
    # los bindings, así que sustituirlos ahí no alcanzaría al código real.
    monkeypatch.setattr(core_db, "_table", FakeTable(store))
    monkeypatch.setattr(core_db, "_dynamodb", FakeResource(store))
    monkeypatch.setattr(core_utils, "_table", FakeTable(store))
    monkeypatch.setattr(core_utils, "_dynamodb", FakeResource(store))
    core_utils._invalidate_app_config_cache()
    yield core_utils
    core_utils._invalidate_app_config_cache()


@pytest.fixture
def snapshot_ruteo(utils, request):
    """Compara el mapa de ruteo contra la instantánea guardada en `tests/rutas/`.

    Si no existe, la crea (y hay que revisarla al añadirla al repo). Regenerar
    a propósito: `RUTEO_ACTUALIZAR=1 pytest tests/test_ruteo.py`.
    """
    import json
    import os

    def comparar(nombre_modulo, observado):
        carpeta = os.path.join(os.path.dirname(__file__), "rutas")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"{nombre_modulo}.json")

        if os.environ.get("RUTEO_ACTUALIZAR") or not os.path.exists(ruta):
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(observado, fh, indent=2, ensure_ascii=False, sort_keys=True)
                fh.write("\n")
            return

        with open(ruta, encoding="utf-8") as fh:
            esperado = json.load(fh)

        diferencias = {
            clave: (esperado.get(clave), observado.get(clave))
            for clave in set(esperado) | set(observado)
            if esperado.get(clave) != observado.get(clave)
        }
        assert not diferencias, (
            f"El ruteo de {nombre_modulo} cambió:\n"
            + "\n".join(f"  {k}: {v[0]} → {v[1]}" for k, v in sorted(diferencias.items()))
        )

    return comparar
