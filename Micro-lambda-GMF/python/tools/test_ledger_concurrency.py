"""Reproduce la carrera de dos órdenes pagadas a la vez sobre el mismo beneficiario."""
import os, sys, threading
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

STORE, LOCK = {}, threading.Lock()
CONTADOR = {}

class Err(Exception):
    def __init__(self, code): self.response = {"Error": {"Code": code}}

class FakeTable:
    meta = type("M", (), {"client": None})
    def get_item(self, Key=None, **kw):
        with LOCK:
            CONTADOR["get"] = CONTADOR.get("get", 0) + 1
            it = STORE.get((Key["PK"], Key["SK"]))
            return {"Item": dict(it)} if it else {}
    def put_item(self, Item=None, ConditionExpression=None, ExpressionAttributeValues=None, **kw):
        with LOCK:
            key = (Item["PK"], Item["SK"])
            current = STORE.get(key)
            if ConditionExpression:
                # Semántica REAL de DynamoDB: `version = :v` falla si el
                # atributo no existe (no se trata como cero).
                expected = ExpressionAttributeValues[":expected"]
                cumple = False
                if "attribute_not_exists(version)" in ConditionExpression:
                    cumple = current is None or "version" not in current
                if not cumple and current is not None and "version" in current:
                    cumple = Decimal(str(current["version"])) == Decimal(str(expected))
                if not cumple:
                    raise Err("ConditionalCheckFailedException")
            STORE[key] = dict(Item)
            if str(Item.get("SK", "")).startswith("ROW#") or "ledger" in Item:
                CONTADOR["filas_escritas"] = CONTADOR.get("filas_escritas", 0) + (
                    len(Item.get("ledger", [])) if "ledger" in Item else 1)
            CONTADOR["put"] = CONTADOR.get("put", 0) + 1
    def update_item(self, Key=None, UpdateExpression="", ExpressionAttributeValues=None, **kw):
        """`ADD`/`SET` mínimos, como en tests/conftest.py."""
        import re as _re
        with LOCK:
            CONTADOR["update"] = CONTADOR.get("update", 0) + 1
            clave = (str(Key["PK"]), str(Key["SK"]))
            item = dict(STORE.get(clave, {}))
            item.setdefault("PK", clave[0]); item.setdefault("SK", clave[1])
            valores = ExpressionAttributeValues or {}
            partes = _re.split(r"\b(SET|ADD)\b", UpdateExpression or "")
            for i in range(1, len(partes) - 1, 2):
                tipo, cuerpo = partes[i].upper(), partes[i + 1]
                for asig in cuerpo.split(","):
                    asig = asig.strip()
                    if not asig: continue
                    if tipo == "ADD":
                        attr, ph = asig.split(None, 1)
                        item[attr] = Decimal(str(item.get(attr, 0))) + Decimal(str(valores[ph.strip()]))
                    else:
                        izq, der = asig.split("=", 1)
                        item[izq.strip()] = valores.get(der.strip(), der.strip())
            STORE[clave] = item
            return {"Attributes": dict(item)}
    def query(self, **kw):
        with LOCK:
            CONTADOR["query"] = CONTADOR.get("query", 0) + 1
            cond = kw.get("KeyConditionExpression")
            pk = cond._values[1] if hasattr(cond, "_values") else None
            return {"Items": [dict(v) for (p, _s), v in STORE.items() if p == pk]}

import boto3
boto3.resource = lambda *a, **k: type("R", (), {"Table": lambda s, n: FakeTable()})()
boto3.client = lambda *a, **k: None
import core_utils as utils
from core import db as core_db
core_db._table = FakeTable()
utils._table = core_db._table
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
print("hilos concurrentes : 12")
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


# ---------------------------------------------------------------------------
# Qué toca cada esquema al añadir UNA comisión
# ---------------------------------------------------------------------------
# La ventaja del esquema por filas es estructural, no estadística: añadir una
# comisión no lee ni reescribe las demás. Simular contención sobre una tabla en
# memoria protegida por un lock no mediría nada real (el lock serializa todo),
# así que se mide lo que sí es cierto y comprobable: operaciones y filas
# tocadas por escritura, en función de cuántas comisiones ya tiene el mes.

def _tocado_al_anadir(esquema, filas_previas):
    """Devuelve (operaciones, filas escritas) al añadir una comisión más."""
    from core import ledger
    STORE.clear()
    ledger.LEDGER_ROW_SCHEME = esquema

    previas = [
        {"rowId": f"P{i}", "orderId": f"P{i}", "amount": Decimal("10"),
         "status": "pending", "createdAt": f"2026-09-01T00:00:{i:02d}Z"}
        for i in range(filas_previas)
    ]
    base = utils._get_ledger_month("777", "2026-09")
    base["ledger"] = previas
    if esquema == "rows":
        ledger._write_ledger_rows(base)
    else:
        utils._save_ledger_month(base)

    CONTADOR.clear()
    nueva = {"rowId": "NUEVA", "orderId": "NUEVA", "amount": Decimal("10"),
             "status": "pending", "createdAt": "2026-09-01T23:59:59Z"}
    if esquema == "rows":
        ledger._add_ledger_row("777", "2026-09", nueva)
    else:
        def mutate(item):
            item["ledger"].append(nueva)
            return True
        utils._mutate_ledger_month("777", "2026-09", mutate)

    ledger.LEDGER_ROW_SCHEME = "off"
    return sum(CONTADOR.values()), CONTADOR.get("filas_escritas", 0)


print("\n--- Coste de añadir UNA comisión, según cuántas ya tiene el mes ---")
print(f"{'filas previas':>14}{'item único':>26}{'un item por fila':>26}")
crece_unico = crece_filas = []
medidas = {}
for previas in (5, 50, 200):
    ops_unico, filas_unico = _tocado_al_anadir("off", previas)
    ops_filas, filas_filas = _tocado_al_anadir("rows", previas)
    medidas[previas] = (filas_unico, filas_filas)
    print(f"{previas:>14}{f'{filas_unico} filas reescritas':>26}"
          f"{f'{filas_filas} fila reescrita':>26}")

sin_crecer = len({v[1] for v in medidas.values()}) == 1
crece = medidas[200][0] > medidas[5][0]
print(f"\n  item único: las filas reescritas CRECEN con el mes  → {crece}")
print(f"  por filas : se mantienen constantes               → {sin_crecer}")

todo_ok = crece and sin_crecer
print("\nRESULTADO ESQUEMAS:", "OK" if todo_ok else "FALLA")
sys.exit(0 if (ok and todo_ok) else 1)
