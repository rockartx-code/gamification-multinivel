#!/usr/bin/env python3
"""Falla si el coste en viajes a DynamoDB de un endpoint crece con el dataset.

Ejecuta `ddb_query_probe` con 100 y 800 clientes y compara. Una regresión que
reintroduzca un N+1 (un `_get_by_id` dentro de un bucle sobre la red) se nota
aquí como un salto proporcional al tamaño del dataset, no como un test rojo
en otro sitio.

Uso:  python3 tools/check_query_budget.py
"""
import os
import subprocess
import sys

PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ddb_query_probe.py")

# Máximo de GetItem **individuales** por invocación. Este es el detector de
# N+1: un `_get_by_id` dentro de un bucle sobre la red crece con el número de
# clientes, mientras que el código correcto usa BatchGetItem y se queda en una
# constante. Los BatchGetItem sí pueden crecer (agrupan 100 claves por viaje):
# un endpoint que legítimamente recorre toda la colección, como el cuadro de
# honor, necesita N/100 lotes y eso no es una regresión.
PRESUPUESTO_GETITEM = {
    "GET /user-dashboard": 20,
    "GET /customers/dashboard": 20,
    "GET /dashboard/honor-board": 5,
    "ORDER_PAID": 40,
}
# Viajes totales (GetItem + Query + BatchGetItem) admitidos con 800 clientes.
PRESUPUESTO_VIAJES = {
    "GET /user-dashboard": 60,
    "GET /customers/dashboard": 40,
    "GET /dashboard/honor-board": 60,
    "ORDER_PAID": 80,
}
N_PEQUENO, N_GRANDE = 100, 800


def medir(n):
    salida = subprocess.run(
        [sys.executable, PROBE, str(n)],
        capture_output=True, text=True, check=True,
    ).stdout

    resultados, actual = {}, None
    for linea in salida.split("\n"):
        if linea.startswith("---"):
            actual = next((k for k in PRESUPUESTO_VIAJES if k in linea), None)
            if actual:
                resultados[actual] = {"GetItem": 0, "viajes": 0}
        elif actual and linea.strip():
            partes = linea.split()
            if len(partes) >= 2 and partes[-1].isdigit():
                metrica, valor = " ".join(partes[:-1]), int(partes[-1])
                if metrica in ("GetItem", "Query", "BatchGetItem"):
                    resultados[actual]["viajes"] += valor
                if metrica == "GetItem":
                    resultados[actual]["GetItem"] += valor
    return resultados


def main():
    pequeno, grande = medir(N_PEQUENO), medir(N_GRANDE)

    print(f"{'endpoint':<32}{'GetItem':>18}{'viajes':>16}")
    print(f"{'':<32}{f'N={N_PEQUENO}':>9}{f'N={N_GRANDE}':>9}{f'N={N_PEQUENO}':>8}{f'N={N_GRANDE}':>8}   estado")
    fallos = []
    for endpoint, tope_viajes in PRESUPUESTO_VIAJES.items():
        chico = pequeno.get(endpoint, {"GetItem": 0, "viajes": 0})
        gordo = grande.get(endpoint, {"GetItem": 0, "viajes": 0})
        tope_get = PRESUPUESTO_GETITEM[endpoint]

        estado = "ok"
        if gordo["GetItem"] > tope_get:
            estado = f"N+1: {gordo['GetItem']} GetItem individuales (tope {tope_get})"
            fallos.append(f"{endpoint}: {estado}")
        elif gordo["GetItem"] > chico["GetItem"] * 2 + 5:
            estado = f"los GetItem crecen con el dataset ({chico['GetItem']}→{gordo['GetItem']})"
            fallos.append(f"{endpoint}: {estado}")
        elif gordo["viajes"] > tope_viajes:
            estado = f"excede el tope de viajes ({gordo['viajes']} > {tope_viajes})"
            fallos.append(f"{endpoint}: {estado}")

        print(f"{endpoint:<32}{chico['GetItem']:>9}{gordo['GetItem']:>9}"
              f"{chico['viajes']:>8}{gordo['viajes']:>8}   {estado}")

    if fallos:
        print("\nPresupuesto excedido:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("\nPresupuesto de consultas respetado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
