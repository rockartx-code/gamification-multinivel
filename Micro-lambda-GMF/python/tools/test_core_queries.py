"""Valida las condiciones de clave nuevas, la paginación y la escritura transaccional."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

STORE = {}
CALLS = {"transact": 0, "put": 0}
PAGE = 3   # páginas diminutas para forzar LastEvaluatedKey

from botocore.exceptions import ClientError
def Err(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "TransactWriteItems")

def _eval(cond, pk, sk):
    """Evalúa un boto3 ConditionBase contra una clave concreta."""
    from boto3.dynamodb.conditions import And, Equals, BeginsWith, Between, GreaterThanEquals, LessThanEquals
    if isinstance(cond, And):
        return all(_eval(v, pk, sk) for v in cond._values)
    attr, *vals = cond._values
    name = attr.name
    actual = pk if name == "PK" else sk
    if isinstance(cond, Equals):            return actual == vals[0]
    if isinstance(cond, BeginsWith):        return str(actual).startswith(str(vals[0]))
    if isinstance(cond, Between):           return str(vals[0]) <= str(actual) <= str(vals[1])
    if isinstance(cond, GreaterThanEquals): return str(actual) >= str(vals[0])
    if isinstance(cond, LessThanEquals):    return str(actual) <= str(vals[0])
    raise AssertionError(f"condición no soportada: {type(cond).__name__}")

class FakeTable:
    meta = type("M", (), {"client": None})
    def get_item(self, Key=None, **kw):
        it = STORE.get((Key["PK"], Key["SK"]))
        return {"Item": dict(it)} if it else {}
    def put_item(self, Item=None, **kw):
        CALLS["put"] += 1
        STORE[(Item["PK"], Item["SK"])] = dict(Item)
    def delete_item(self, Key=None, **kw): STORE.pop((Key["PK"], Key["SK"]), None)
    def update_item(self, **kw): return {"Attributes": {}}
    def query(self, **kw):
        rows = sorted(
            (dict(v) for (p, s), v in STORE.items() if _eval(kw["KeyConditionExpression"], p, s)),
            key=lambda i: str(i["SK"]), reverse=not kw.get("ScanIndexForward", False))
        start = kw.get("ExclusiveStartKey")
        if start:
            keys = [r["SK"] for r in rows]
            rows = rows[keys.index(start["SK"]) + 1:]
        size = min(kw.get("Limit", PAGE), PAGE)
        page, rest = rows[:size], rows[size:]
        if kw.get("ProjectionExpression"):
            keep = set(kw["ExpressionAttributeNames"].values())
            page = [{k: v for k, v in r.items() if k in keep} for r in page]
        out = {"Items": page}
        if rest and not kw.get("Limit", 0) <= size:
            out["LastEvaluatedKey"] = {"PK": kw and page[-1]["PK"], "SK": page[-1]["SK"]} if page else None
        elif rest:
            out["LastEvaluatedKey"] = {"PK": page[-1]["PK"], "SK": page[-1]["SK"]} if page else None
        return out

class FakeClient:
    def transact_write_items(self, TransactItems=None, **kw):
        CALLS["transact"] += 1
        raise Err("ValidationException")   # fuerza el camino de respaldo

import boto3
boto3.resource = lambda *a, **k: type("R", (), {"Table": lambda s, n: FakeTable()})()
boto3.client = lambda *a, **k: None
import core_utils as utils
utils._table = FakeTable()
utils._ddb_client = FakeClient()

for month in ("2026-06", "2026-07", "2026-08", "2026-09"):
    for i in range(5):
        sk = f"{month}-1{i}T00:00:00Z#{month}-{i}"
        STORE[("POS_SALE", sk)] = {"PK": "POS_SALE", "SK": sk, "saleId": f"{month}-{i}",
                                   "createdAt": sk.split("#")[0], "total": 10}

fallos = []
def check(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print(f"  {'ok ' if ok else 'FALLA'} {nombre}: {obtenido}" + ("" if ok else f"  (esperado {esperado})"))
    if not ok: fallos.append(nombre)

print("Condiciones de clave (20 ventas, 5 por mes, páginas de 3 → obliga a paginar):")
check("sin filtro",              len(utils._query_bucket("POS_SALE")), 20)
check("sk_prefix=2026-08",       len(utils._query_bucket("POS_SALE", sk_prefix="2026-08")), 5)
check("sk_from=2026-08",         len(utils._query_bucket("POS_SALE", sk_from="2026-08")), 10)
# sk_to es un tope crudo: "2026-07" deja fuera julio entero (2026-07-10 > 2026-07)
check("sk_to=2026-07 (excluye julio)", len(utils._query_bucket("POS_SALE", sk_to="2026-07")), 5)
check("sk_to con centinela (incluye julio)", len(utils._query_bucket("POS_SALE", sk_to="2026-07\uffff")), 10)
check("sk_from+sk_to (jul-ago)", len(utils._query_bucket("POS_SALE", sk_from="2026-07", sk_to="2026-08￿")), 10)
check("sk_from=None (sin filtro)", len(utils._query_bucket("POS_SALE", sk_from=None)), 20)

proyectado = utils._query_bucket("POS_SALE", sk_prefix="2026-09", projection=["saleId", "SK", "PK"])
check("projection deja 3 campos", sorted(proyectado[0].keys()), ["PK", "SK", "saleId"])

print("\nIteración con corte anticipado:")
leidos = 0
for _ in utils._iter_bucket("POS_SALE", forward=False):
    leidos += 1
    if leidos == 2: break
check("_iter_bucket corta a las 2", leidos, 2)

print("\n_query_all_pages recorre todas las páginas:")
from boto3.dynamodb.conditions import Key
check("query_all_pages", len(utils._query_all_pages(KeyConditionExpression=Key("PK").eq("POS_SALE"))), 20)

print("\nEscritura de entidad con transacción no disponible:")
CALLS["transact"] = CALLS["put"] = 0
utils._put_entity("PRODUCT", 42, {"entityType": "product", "name": "X"})
check("intenta la transacción", CALLS["transact"], 1)
check("respaldo escribe 2 items", CALLS["put"], 2)
check("el REF quedó legible", (utils._get_by_id("PRODUCT", 42) or {}).get("name"), "X")

print("\nRESULTADO:", "OK" if not fallos else f"FALLAN {fallos}")
sys.exit(1 if fallos else 0)
