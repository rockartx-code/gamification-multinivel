"""Compara el VG agregado nuevo (O(N·L)) contra el recorrido de árbol original."""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
import boto3
boto3.resource = lambda *a, **k: type("R", (), {"Table": lambda s, n: type("T", (), {"meta": type("M", (), {"client": None})})()})()
boto3.client = lambda *a, **k: None

import dashboard_lambda as dash

def naive_vg(nodes, children, vp_by_id, max_levels, root):
    """Réplica del algoritmo anterior: árbol recortado + suma de todos los nodos."""
    total, stack, visited = 0.0, [(root, 0)], {root}
    while stack:
        cid, depth = stack.pop()
        total += vp_by_id.get(cid, 0.0)
        if depth >= max_levels:
            continue
        for ch in children.get(cid, []):
            if ch in nodes and ch not in visited:
                visited.add(ch); stack.append((ch, depth + 1))
    return total

def build(n, seed, max_children=4):
    rnd = random.Random(seed)
    nodes, children = {}, {}
    for i in range(1, n + 1):
        cid = str(1000 + i)
        leader = str(1000 + rnd.randint(1, i - 1)) if i > 1 and rnd.random() < 0.9 else None
        nodes[cid] = {"id": cid, "leaderId": leader}
        if leader:
            children.setdefault(leader, []).append(cid)
    vp = {cid: round(rnd.uniform(0, 500), 2) for cid in nodes}
    return nodes, children, vp

fails = 0
for seed in range(40):
    for max_levels in (1, 3, 5):
        n = random.Random(seed).randint(5, 120)
        nodes, children, vp = build(n, seed)
        fast = dash._aggregate_vg_by_node(nodes, children, vp, max_levels)
        for cid in nodes:
            expected = naive_vg(nodes, children, vp, max_levels, cid)
            if abs(fast.get(cid, 0.0) - expected) > 1e-6:
                fails += 1
                print(f"DIFERENCIA seed={seed} L={max_levels} nodo={cid}: {fast.get(cid)} != {expected}")

# Caso patológico: ciclo leaderId (A→B→A) — no debe colgarse
nodes = {"A": {"id": "A", "leaderId": "B"}, "B": {"id": "B", "leaderId": "A"}}
children = {"A": ["B"], "B": ["A"]}
out = dash._aggregate_vg_by_node(nodes, children, {"A": 10.0, "B": 5.0}, 5)
print("ciclo tolerado ->", out)

# Cadena profunda (2000 niveles): sin RecursionError
depth = 2000
nodes = {str(i): {"id": str(i), "leaderId": str(i - 1) if i else None} for i in range(depth)}
children = {str(i): [str(i + 1)] for i in range(depth - 1)}
out = dash._aggregate_vg_by_node(nodes, children, {str(i): 1.0 for i in range(depth)}, 5)
print("cadena de 2000 niveles -> raíz VG =", out["0"], "(esperado 6.0)")

print("\nDIFERENCIAS:", fails)
sys.exit(1 if fails else 0)
