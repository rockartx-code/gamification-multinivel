#!/usr/bin/env python3
"""
Medidor de operaciones DynamoDB por endpoint.

Sustituye la tabla real por una tabla en memoria que cuenta cada operación
(GetItem / Query / BatchGetItem / PutItem / UpdateItem) y ejecuta los handlers
reales de los lambdas contra un dataset sintético. Sirve para detectar
amplificación de lecturas (N+1, O(N), O(N^2)) sin desplegar en AWS.

Uso:
    pip install boto3
    python3 tools/ddb_query_probe.py [n_clientes]      # por defecto 200
    TRACE=1 python3 tools/ddb_query_probe.py 200       # además atribuye cada GetItem a su llamador

Interpretación: el número de operaciones debe ser ~constante respecto a
`n_clientes`. Si crece linealmente el endpoint tiene un N+1; si crece con el
cuadrado, tiene un bucle anidado sobre toda la tabla.
"""
import collections
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

COUNTS = collections.Counter()
STORE = {}  # (PK, SK) -> item


def _trace_caller():
    if not os.environ.get("TRACE"):
        return
    import traceback
    frames = [
        f for f in traceback.extract_stack()[:-2]
        if f.filename.endswith("_lambda.py") or f.filename.endswith("core_utils.py")
    ]
    if frames:
        last = frames[-1]
        COUNTS[f"  ↳ {last.name} @{os.path.basename(last.filename)}:{last.lineno}"] += 1


class FakeTable:
    class _Meta:
        class _Client:
            pass
        client = _Client()
    meta = _Meta()

    def get_item(self, Key=None, **kw):
        COUNTS["GetItem"] += 1
        _trace_caller()
        item = STORE.get((str(Key["PK"]), str(Key["SK"])))
        return {"Item": dict(item)} if item else {}

    def put_item(self, Item=None, **kw):
        COUNTS["PutItem"] += 1
        STORE[(str(Item["PK"]), str(Item["SK"]))] = dict(Item)
        return {}

    def update_item(self, Key=None, **kw):
        COUNTS["UpdateItem"] += 1
        return {"Attributes": dict(STORE.get((str(Key["PK"]), str(Key["SK"])), {}))}

    def delete_item(self, Key=None, **kw):
        COUNTS["DeleteItem"] += 1
        STORE.pop((str(Key["PK"]), str(Key["SK"])), None)
        return {}

    def query(self, **kw):
        COUNTS["Query"] += 1
        condition = kw.get("KeyConditionExpression")
        pk = condition._values[1] if hasattr(condition, "_values") else None
        items = [dict(v) for (p, _s), v in STORE.items() if p == pk]
        items.sort(key=lambda i: str(i.get("SK")), reverse=not kw.get("ScanIndexForward", False))
        COUNTS["Query:itemsLeidos"] += len(items)
        return {"Items": items}


class FakeResource:
    def Table(self, name):
        return FakeTable()

    def batch_get_item(self, RequestItems=None, **kw):
        COUNTS["BatchGetItem"] += 1
        out = []
        for _table_name, spec in (RequestItems or {}).items():
            for key in spec["Keys"]:
                COUNTS["BatchGetItem:claves"] += 1
                item = STORE.get((str(key["PK"]), str(key["SK"])))
                if item:
                    out.append(dict(item))
        return {"Responses": {list(RequestItems)[0]: out}, "UnprocessedKeys": {}}


import boto3  # noqa: E402

boto3.resource = lambda *a, **k: FakeResource()
boto3.client = lambda *a, **k: type("C", (), {"__getattr__": lambda s, n: (lambda **kw: {})})()

import core_utils as utils  # noqa: E402

from core import db as core_db

core_db._table = FakeTable()
core_db._dynamodb = FakeResource()
utils._table = core_db._table
utils._dynamodb = core_db._dynamodb


def seed(n_customers, month=None):
    """Árbol ternario de `n_customers` clientes, todos con estado del mes."""
    import commissions_lambda as commissions

    STORE.clear()
    month = month or utils._month_key()
    now = "2026-01-01T00:00:00Z"

    for i in range(1, n_customers + 1):
        cid = 1000 + i
        leader = 1000 + (i // 3) if i > 3 else None
        sk = f"{now}#{cid}"
        STORE[("CUSTOMER", sk)] = {
            "PK": "CUSTOMER", "SK": sk, "entityType": "customer", "customerId": cid,
            "name": f"Cliente {cid}", "leaderId": leader, "createdAt": now,
        }
        STORE[(f"CUSTOMER#{cid}", "REF")] = {
            "PK": f"CUSTOMER#{cid}", "SK": "REF", "entityId": cid,
            "refPK": "CUSTOMER", "refSK": sk,
        }
        entity_id = f"{cid}#{month}"
        STORE[("ASSOCIATE_MONTH", entity_id)] = {
            "PK": "ASSOCIATE_MONTH", "SK": entity_id, "associateId": str(cid),
            "monthKey": month, "netVolume": Decimal("1500"), "netVP": Decimal("500"),
        }

    order_id = "ORD-PROBE"
    order = {
        "PK": "ORDER", "SK": f"{now}#{order_id}", "orderId": order_id,
        "customerId": 1000 + n_customers, "buyerType": "associate", "monthKey": month,
        "netTotal": Decimal("2000"), "grossSubtotal": Decimal("2000"),
        "items": [], "createdAt": now, "status": "paid",
    }
    STORE[("ORDER", order["SK"])] = order
    STORE[(f"ORDER#{order_id}", "REF")] = {
        "PK": f"ORDER#{order_id}", "SK": "REF", "refPK": "ORDER", "refSK": order["SK"],
    }

    STORE[("SESSION#tok-probe", "REF")] = {
        "PK": "SESSION#tok-probe", "SK": "REF", "refPK": "SESSION", "refSK": f"{now}#tok-probe",
    }
    STORE[("SESSION", f"{now}#tok-probe")] = {
        "PK": "SESSION", "SK": f"{now}#tok-probe", "userId": "1002", "role": "cliente", "privileges": {},
    }

    STORE[("CONFIG#app-v1", "REF")] = {
        "PK": "CONFIG#app-v1", "SK": "REF", "refPK": "CONFIG", "refSK": f"{now}#app-v1",
    }
    STORE[("CONFIG", f"{now}#app-v1")] = {
        "PK": "CONFIG", "SK": f"{now}#app-v1", "config": commissions._default_app_config(),
    }


def run(label, fn):
    COUNTS.clear()
    try:
        fn()
        status = "ok"
    except Exception as ex:  # noqa: BLE001
        status = f"ERROR {type(ex).__name__}: {ex}"
    print(f"\n--- {label}  [{status}]")
    for key in sorted(COUNTS):
        print(f"      {key:<52s} {COUNTS[key]:>9d}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed(n)
    print(f"Dataset: {n} clientes (árbol ternario), 1 ASSOCIATE_MONTH por cliente, mes {utils._month_key()}")

    import commissions_lambda as commissions
    import costumer_lambda as customers
    import dashboard_lambda as dashboard

    run("GET /user-dashboard        dashboard_lambda.get_user_dashboard",
        lambda: dashboard.get_user_dashboard({"userId": "1002"}, {}))
    run("GET /customers/dashboard   costumer_lambda.handle_customer_dashboard (frío)",
        lambda: customers.handle_customer_dashboard({"authorization": "Bearer tok-probe"}))
    run("GET /customers/dashboard   costumer_lambda.handle_customer_dashboard (árbol ya persistido)",
        lambda: customers.handle_customer_dashboard({"authorization": "Bearer tok-probe"}))
    run("GET /dashboard/honor-board dashboard_lambda.get_honor_board",
        lambda: dashboard.get_honor_board())
    run("ORDER_PAID                 commissions_lambda.handle_apply_rewards",
        lambda: commissions.handle_apply_rewards("ORD-PROBE"))


if __name__ == "__main__":
    main()
