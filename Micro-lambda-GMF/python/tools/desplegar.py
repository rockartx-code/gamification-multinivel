#!/usr/bin/env python3
"""Publica `python/` sobre las ocho funciones Lambda que ya existen en la cuenta.

Por qué este script y no `sam deploy`
-------------------------------------
`template.yaml` describe un sistema **nuevo**: crea la tabla `multinivel-<entorno>`,
ocho funciones `multinivel-*-<entorno>` y un API Gateway propio. Sirve para
levantar el sistema en una cuenta limpia, que es su criterio de cierre declarado
en `docs/qa/07-roadmap-arquitectura.md`.

Lo que hay hoy en producción es otra cosa: ocho funciones hechas a mano en la
consola (`Multinivel-order`, `Multinivel-Auth`, …), sin stack de CloudFormation,
colgando de un API Gateway `{proxy+}` por dominio, con los datos reales en la
tabla `multinivel`. Correr `sam deploy` ahí no actualiza nada: construye un
entorno paralelo y vacío al lado. Este script actualiza **lo que está vivo**.

Qué hace, por función
---------------------
1. Sube el paquete: `python/` completo menos pruebas, herramientas y semillas.
2. Apunta el `Handler` al módulo de verdad (`order_lambda.lambda_handler` en vez
   del `lambda_function.lambda_handler` histórico, que era un archivo plano).
3. Ajusta memoria y tiempo a lo que declara `template.yaml`. Comisiones y
   Dashboard corrían a 128 MB / 3 s: el motor de comisiones y el cuadro de honor
   no caben ahí.
4. Fija las variables de entorno **sin pisar las que ya tienen valor**. Los
   secretos (`ENVIA_API_KEY`, `MERCADOPAGO_ACCESS_TOKEN`) y el ARN de la máquina
   de estados se conservan tal cual: este script nunca los lee ni los escribe.
5. Desengancha la layer `Multinivel-Core`. Traía el `core_utils.py` monolítico de
   40 KB; el paquete ya lleva el paquete `core/` y la fachada nueva. Dejarla
   colgando es una trampa para quien venga después.
6. Guarda el código y la configuración **anteriores** en `--respaldo DIR` antes
   de tocar nada, y después publica una versión numerada del código nuevo.

   Ojo con el punto de retorno: `publish_version` numera lo que acaba de
   quedar, no lo que había. Antes del primer uso de este script las ocho
   funciones solo tenían `$LATEST`, así que la única vuelta atrás posible es el
   respaldo del paso 6. El respaldo **no guarda valores de variables**: los
   secretos nunca se leen, y como el script tampoco los pisa, siguen intactos
   en la función.

Uso
---
    cd Micro-lambda-GMF/python
    python tools/desplegar.py --dry-run                  # el plan, sin tocar nada
    python tools/desplegar.py --respaldo ../../respaldo  # despliega, guardando lo anterior
    python tools/desplegar.py --solo Multinivel-shiping
    python tools/desplegar.py --revertir 1 --solo Multinivel-order

`--dry-run` no necesita credenciales de escritura.
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys
import zipfile

import boto3
from botocore.exceptions import ClientError

CODIGO = pathlib.Path(__file__).resolve().parent.parent   # Micro-lambda-GMF/python/

# ── Qué función corre qué módulo ─────────────────────────────────────────────
# El nombre en AWS es histórico (con sus erratas: "costumer", "shiping"). No se
# renombra: cambiarlo obligaría a rehacer el cableado del API Gateway.
#
# memoria/tiempo salen de template.yaml: 512 MB / 30 s por defecto; comisiones y
# dashboard piden más porque recorren toda la red.
FUNCIONES = {
    "Multinivel-Auth":       {"modulo": "auth_utils",         "memoria": 512,  "tiempo": 30},
    "Multinivel-catalog":    {"modulo": "catalog_lambda",     "memoria": 512,  "tiempo": 30},
    "Multinivel-costumer":   {"modulo": "customer_lambda",    "memoria": 512,  "tiempo": 30},
    "Multinivel-Comissions": {"modulo": "commissions_lambda", "memoria": 1024, "tiempo": 120},
    "Multinivel-order":      {"modulo": "order_lambda",       "memoria": 512,  "tiempo": 30},
    "Multinivel-inventory":  {"modulo": "inventory_lambda",   "memoria": 512,  "tiempo": 30},
    "Multinivel-Dashboard":  {"modulo": "dashboard_lambda",   "memoria": 1024, "tiempo": 60},
    "Multinivel-shiping":    {"modulo": "shipping_lambda",    "memoria": 512,  "tiempo": 30},
}

# ── Variables de entorno ─────────────────────────────────────────────────────
# Solo se escriben las que NO tienen ya un valor en la función. Ver `_fusionar`.
#
# AWS_REGION no está aquí a propósito: Lambda la inyecta y la rechaza como
# variable de usuario. `SUPERADMIN_TOKEN` vacío = no existe superadmin, que es
# lo recomendado en producción; el valor histórico vivía en el código fuente y
# debe considerarse comprometido. `TRUST_ACTOR_HEADERS` vacío = los encabezados
# `x-user-role` no deciden nada, que es el agujero que cerró la ronda 7.
COMUNES = {
    "TABLE_NAME": "multinivel",
    "BUCKET_NAME": "findingu-ventas",
    "SUPERADMIN_TOKEN": "",
    "TRUST_ACTOR_HEADERS": "",
    "PASSWORD_HASH_ITERATIONS": "210000",
    "SESSION_TTL_SECONDS": "2592000",
    "APP_CONFIG_TTL_SECONDS": "60",
    "FRONTEND_BASE_URL": "https://www.findingu.com.mx",
    "SES_FROM_EMAIL": "info@findingu.com.mx",
    "API_BASE_URL": "https://ge2omdgk33.execute-api.us-east-1.amazonaws.com/Prod",
    "LEDGER_ROW_SCHEME": "off",
    "ATHENA_DATABASE": "",
}

# Envíos: se dejan los endpoints de **prueba** de Envia. Este entorno sigue
# siendo friends and family; apuntar a producción genera guías que se cobran.
POR_FUNCION = {
    "Multinivel-shiping": {
        "ENVIA_API_URL": "https://api-test.envia.com/ship/rate/",
        "ENVIA_GENERATE_URL": "https://api-test.envia.com/ship/generate/",
        "ENVIA_TRACK_URL": "https://api-test.envia.com/ship/generaltrack/",
        "SHIPPING_ORIGIN_NAME": "Warehouse MX",
        "SHIPPING_ORIGIN_PHONE": "8180000000",
        "SHIPPING_ORIGIN_STREET": "Av. Principal",
        "SHIPPING_ORIGIN_NUMBER": "1",
        "SHIPPING_ORIGIN_CITY": "Monterrey",
        "SHIPPING_ORIGIN_STATE": "NL",
        "SHIPPING_ORIGIN_POSTAL_CODE": "64060",
    },
    "Multinivel-inventory": {
        "ENVIA_API_URL": "https://api-test.envia.com/ship/rate/",
        "ENVIA_GENERATE_URL": "https://api-test.envia.com/ship/generate/",
        "ENVIA_TRACK_URL": "https://api-test.envia.com/ship/generaltrack/",
    },
}

# Lo que no viaja: pruebas, herramientas, semillas y el puente muerto.
DIRS_FUERA = {"tests", "tools", "seed", "__pycache__", ".pytest_cache"}
ARCHIVOS_FUERA = {"costumer_lambda.py", ".env.example", "conftest.py"}


def construir_paquete() -> bytes:
    """Empaqueta `python/` en memoria. Sale del orden de 280 KB comprimido."""
    buf = io.BytesIO()
    incluidos = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(CODIGO.rglob("*.py")):
            rel = p.relative_to(CODIGO)
            if set(rel.parts) & DIRS_FUERA or p.name in ARCHIVOS_FUERA:
                continue
            z.write(p, rel.as_posix())
            incluidos += 1
        sfn = CODIGO / "stepFunctions.json"
        if sfn.exists():
            z.write(sfn, "stepFunctions.json")
            incluidos += 1
    datos = buf.getvalue()
    print(f"paquete: {incluidos} archivos, {len(datos):,} bytes")
    if len(datos) > 50 * 1024 * 1024:
        sys.exit("el paquete pasa de 50 MB: hay que subirlo por S3")
    return datos


def _fusionar(actuales: dict, deseadas: dict) -> tuple[dict, list, list]:
    """Las que ya tienen valor mandan. Devuelve (final, añadidas, conservadas)."""
    final = dict(deseadas)
    conservadas = []
    for k, v in actuales.items():
        # Toda variable que ya existe se conserva, tenga o no opinión este
        # script. Así los secretos (ENVIA_API_KEY, MERCADOPAGO_ACCESS_TOKEN) y
        # el ARN de la máquina de estados sobreviven sin que nadie los lea.
        if k not in deseadas or final[k] != v:
            conservadas.append(k)
        final[k] = v
    anadidas = [k for k in deseadas if k not in actuales]
    return final, sorted(anadidas), sorted(conservadas)


def respaldar(cliente, nombre: str, destino: pathlib.Path) -> None:
    """Guarda el zip y la config actuales. Sin valores de variables: solo los
    nombres, para poder auditar qué había sin volcar un secreto a disco."""
    import json
    import urllib.request

    destino.mkdir(parents=True, exist_ok=True)
    info = cliente.get_function(FunctionName=nombre)
    with urllib.request.urlopen(info["Code"]["Location"]) as r:
        (destino / f"{nombre}.zip").write_bytes(r.read())
    c = info["Configuration"]
    (destino / f"{nombre}.json").write_text(json.dumps({
        "FunctionName": c["FunctionName"],
        "Handler": c["Handler"],
        "MemorySize": c["MemorySize"],
        "Timeout": c["Timeout"],
        "Runtime": c["Runtime"],
        "Layers": [l["Arn"] for l in c.get("Layers", [])],
        "VariablesDeEntorno": sorted((c.get("Environment") or {}).get("Variables") or {}),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  respaldo -> {destino / nombre}.zip + .json")


def desplegar(cliente, nombre: str, cfg: dict, paquete: bytes, seco: bool) -> None:
    try:
        actual = cliente.get_function_configuration(FunctionName=nombre)
    except ClientError as e:
        print(f"  {nombre}: NO EXISTE ({e.response['Error']['Code']})")
        return

    entorno_actual = (actual.get("Environment") or {}).get("Variables") or {}
    deseadas = {**COMUNES, **POR_FUNCION.get(nombre, {})}
    entorno, anadidas, conservadas = _fusionar(entorno_actual, deseadas)

    handler = f"{cfg['modulo']}.lambda_handler"
    capas = [c["Arn"] for c in actual.get("Layers", [])]

    print(f"\n{nombre}")
    print(f"  handler  {actual['Handler']}  ->  {handler}")
    print(f"  memoria  {actual['MemorySize']} MB  ->  {cfg['memoria']} MB")
    print(f"  tiempo   {actual['Timeout']} s  ->  {cfg['tiempo']} s")
    print(f"  codigo   {actual['CodeSize']:,} B  ->  {len(paquete):,} B")
    if capas:
        print(f"  layers   {len(capas)} enganchada(s)  ->  ninguna (el paquete ya trae core/)")
    if anadidas:
        print(f"  variables nuevas    {', '.join(anadidas)}")
    if conservadas:
        print(f"  variables intactas  {', '.join(conservadas)}  (valor existente, no se toca)")

    if seco:
        return

    cliente.update_function_code(FunctionName=nombre, ZipFile=paquete)
    cliente.get_waiter("function_updated_v2").wait(FunctionName=nombre)

    cliente.update_function_configuration(
        FunctionName=nombre,
        Handler=handler,
        MemorySize=cfg["memoria"],
        Timeout=cfg["tiempo"],
        Environment={"Variables": entorno},
        Layers=[],
    )
    cliente.get_waiter("function_updated_v2").wait(FunctionName=nombre)

    v = cliente.publish_version(FunctionName=nombre)["Version"]
    print(f"  LISTO. version {v} publicada (es el codigo NUEVO, no la vuelta atras)")


def revertir(cliente, nombre: str, version: str) -> None:
    """Devuelve $LATEST al código y a la config de una versión publicada."""
    v = cliente.get_function_configuration(FunctionName=nombre, Qualifier=version)
    codigo = cliente.get_function(FunctionName=nombre, Qualifier=version)["Code"]["Location"]
    import urllib.request
    with urllib.request.urlopen(codigo) as r:
        datos = r.read()
    cliente.update_function_code(FunctionName=nombre, ZipFile=datos)
    cliente.get_waiter("function_updated_v2").wait(FunctionName=nombre)
    cliente.update_function_configuration(
        FunctionName=nombre,
        Handler=v["Handler"],
        MemorySize=v["MemorySize"],
        Timeout=v["Timeout"],
        Environment={"Variables": (v.get("Environment") or {}).get("Variables") or {}},
        Layers=[c["Arn"] for c in v.get("Layers", [])],
    )
    cliente.get_waiter("function_updated_v2").wait(FunctionName=nombre)
    print(f"{nombre}: revertida a la version {version}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="imprime el plan sin tocar AWS")
    ap.add_argument("--solo", action="append", metavar="FUNCION",
                    help="limita a una función (repetible)")
    ap.add_argument("--revertir", metavar="VERSION",
                    help="devuelve las funciones a una versión publicada")
    ap.add_argument("--respaldo", metavar="DIR",
                    help="guarda codigo y config actuales ahi ANTES de desplegar")
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    objetivo = {k: v for k, v in FUNCIONES.items()
                if not args.solo or k in args.solo}
    if not objetivo:
        sys.exit(f"ninguna función coincide con {args.solo}")

    cliente = boto3.client("lambda", region_name=args.region)

    if args.revertir:
        for nombre in objetivo:
            revertir(cliente, nombre, args.revertir)
        return

    paquete = construir_paquete()
    if args.dry_run:
        print("\n--- PLAN (dry-run, no se toca nada) ---")
    for nombre, cfg in objetivo.items():
        if args.respaldo and not args.dry_run:
            respaldar(cliente, nombre, pathlib.Path(args.respaldo))
        desplegar(cliente, nombre, cfg, paquete, args.dry_run)
    print()


if __name__ == "__main__":
    main()
