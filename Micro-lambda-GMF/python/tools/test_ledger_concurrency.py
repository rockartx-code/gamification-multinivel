"""Reproduce la carrera de dos órdenes pagadas a la vez sobre el mismo beneficiario."""
import os, sys, threading
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

STORE, LOCK = {}, threading.Lock()

class Err(Exception):
    def __init__(self, code): self.response = {"Error": {"Code": code}}

class FakeTable:
    meta = type("M", (), {"client": None})
    def get_item(self, Key=None, **kw):
        with LOCK:
            it = STORE.get((Key["PK"], Key["SK"]))
            return {"Item": dict(it)} if it else {}
    def put_item(self, Item=None, ConditionExpression=None, ExpressionAttributeValues=None, **kw):
        with LOCK:
            key = (Item["PK"], Item["SK"])
            current = STORE.get(key)
            if ConditionExpression:
                expected = ExpressionAttributeValues[":expected"]
                if current is None:
                    if "attribute_not_exists" not in ConditionExpression:
                        raise Err("ConditionalCheckFailedException")
                elif Decimal(str(current.get("version", 0))) != Decimal(str(expected)):
                    raise Err("ConditionalCheckFailedException")
            STORE[key] = dict(Item)
    def update_item(self, **kw): return {"Attributes": {}}
    def query(self, **kw): return {"Items": []}

import boto3
boto3.resource = lambda *a, **k: type("R", (), {"Table": lambda s, n: FakeTable()})()
boto3.client = lambda *a, **k: None
import core_utils as utils
utils._table = FakeTable()
utils.ClientError = Err

def escribir(order_id, n_hilos=12):
    errores = []
    def worker(i):
        def mutate(item):
            item["ledger"] = [r for r in item["ledger"] if r.get("rowId") != f"{order_id}-{i}"]
            item["ledger"].append({"rowId": f"{order_id}-{i}", "orderId": f"{order_id}-{i}",
                                   "amount": Decimal("100"), "status": "pending"})
            return True
        try:
            utils._mutate_ledger_month("777", "2026-09", mutate)
        except Exception as ex:
            errores.append(ex)
    hilos = [threading.Thread(target=worker, args=(i,)) for i in range(n_hilos)]
    for h in hilos: h.start()
    for h in hilos: h.join()
    return errores

errores = escribir("ORD", 12)
item = utils._get_ledger_month("777", "2026-09")
filas = len(item["ledger"])
print(f"hilos concurrentes : 12")
print(f"filas persistidas  : {filas}   (esperado 12)")
print(f"totalPending       : {item['totalPending']}   (esperado 1200)")
print(f"version final      : {item['version']}")
print(f"errores            : {[type(e).__name__ for e in errores]}")

ok = filas == 12 and item["totalPending"] == Decimal("1200") and not errores

# Anulación concurrente con el mismo bloqueo
utils._void_ledger_rows_for_order("777", "2026-09", "ORD-3")
item = utils._get_ledger_month("777", "2026-09")
print(f"\ntras anular ORD-3  : {len(item['ledger'])} filas, totalPending={item['totalPending']}")
ok = ok and len(item["ledger"]) == 11 and item["totalPending"] == Decimal("1100")

print("\nRESULTADO:", "OK" if ok else "FALLA")
sys.exit(0 if ok else 1)
