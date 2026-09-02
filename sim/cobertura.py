#!/usr/bin/env python3
"""Cobertura a la inversa: qué rutas expone el frontend y cuáles alcanzó alguien.

Lee `servidor.log` (cada petición HTTP real) y las cruza con los patrones que
usa real-api.service.ts. Lo que nunca aparece en el log es capacidad del
sistema que ningún usuario encontró o necesitó.
"""
import re, sys, os, collections
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
svc = open(os.path.join(RAIZ, "gamificacion-multinivel-f/src/app/services/real-api.service.ts"), encoding="utf-8").read()

# patrones de ruta del frontend → regex
patrones = set()
for m in re.finditer(r"`\$\{this\.baseUrl\}([^`]+)`", svc):
    p = m.group(1).split("?")[0]
    p = re.sub(r"\$\{[^}]+\}", "{x}", p)
    patrones.add(p.rstrip("/"))
def a_regex(p):
    return re.compile("^" + re.escape(p).replace(r"\{x\}", r"[^/]+") + "$")
tabla = [(p, a_regex(p)) for p in sorted(patrones)]

# método por patrón (el que use el frontend): lo inferimos del contexto
metodos = collections.defaultdict(set)
for m in re.finditer(r"this\.http\.(get|post|put|patch|delete)<[^>]*>\(\s*`\$\{this\.baseUrl\}([^`]+)`", svc, re.S):
    p = re.sub(r"\$\{[^}]+\}", "{x}", m.group(2).split("?")[0]).rstrip("/")
    metodos[p].add(m.group(1).upper())

golpes = collections.Counter(); desconocidas = collections.Counter()
for linea in open(os.path.join(os.path.dirname(__file__), "servidor.log"), encoding="utf-8", errors="replace"):
    m = re.match(r"\[http\] (\w+) (\S+)", linea)
    if not m: continue
    metodo, ruta = m.group(1), m.group(2).split("?")[0].rstrip("/")
    if metodo == "OPTIONS" or ruta.startswith("/__sim"): continue
    for p, rx in tabla:
        if rx.match(ruta): golpes[(metodo, p)] += 1; break
    else:
        desconocidas[(metodo, ruta)] += 1

tocadas = {p for (_, p) in golpes}
print(f"Rutas que expone el frontend: {len(patrones)} · alcanzadas: {len(tocadas)} · nunca tocadas: {len(patrones)-len(tocadas)}\n")
print("== ALCANZADAS (método, ruta, veces)")
for (m, p), n in sorted(golpes.items(), key=lambda kv: -kv[1]): print(f"  {n:4d}  {m:6s} {p}")
print("\n== NUNCA TOCADAS")
for p in sorted(patrones - tocadas): print(f"        {'/'.join(sorted(metodos.get(p, {'?'}))):6s} {p}")
if desconocidas:
    print("\n== PETICIONES A RUTAS QUE EL FRONTEND NO DECLARA (¿enlaces de correo, webhooks?)")
    for (m, r), n in desconocidas.most_common(20): print(f"  {n:4d}  {m:6s} {r}")
