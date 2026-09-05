#!/usr/bin/env python3
"""Expande los meses contables al esquema por filas (un item por comisión).

El esquema original guarda todas las comisiones del mes dentro de una lista en
un único item: techo de 400 KB, contención entre escritores y reescritura del
item completo por cada fila. Este script copia esos meses al esquema por filas
sin borrar el original, de modo que se pueda volver atrás cambiando la variable
`LEDGER_ROW_SCHEME`.

Es **idempotente**: reejecutarlo deja el mismo resultado.

    python3 tools/migrate_ledger_rows.py            # simulacro (no escribe)
    python3 tools/migrate_ledger_rows.py --apply    # aplica
    python3 tools/migrate_ledger_rows.py --apply --month 2026-09

Secuencia recomendada:
    1. LEDGER_ROW_SCHEME=dual  → el tráfico nuevo puebla ambos esquemas.
    2. Ejecutar este script    → se copia el histórico.
    3. Verificar con --verify  → compara totales entre ambos esquemas.
    4. LEDGER_ROW_SCHEME=rows  → se lee del nuevo.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="escribe (sin esto, simulacro)")
    parser.add_argument("--month", help="limita a un mes concreto (YYYY-MM)")
    parser.add_argument("--verify", action="store_true",
                        help="compara totales entre ambos esquemas y sale")
    args = parser.parse_args()

    import core_utils as utils
    from core import ledger
    from botocore.exceptions import ClientError, NoCredentialsError

    try:
        contables = utils._query_bucket("COMMISSION_MONTH")
    except (ClientError, NoCredentialsError) as error:
        print("No se pudo leer la tabla. Este script opera sobre DynamoDB real "
              "y necesita credenciales AWS con acceso a la tabla.\n"
              f"  TABLE_NAME={utils.TABLE_NAME}  AWS_REGION={utils.AWS_REGION}\n"
              f"  {type(error).__name__}: {error}", file=sys.stderr)
        return 2

    meses = [
        item for item in contables
        if item.get("beneficiaryId") not in (None, "")
        and (not args.month or str(item.get("monthKey")) == args.month)
    ]
    print(f"{len(meses)} meses contables en el esquema original"
          + (f" (mes {args.month})" if args.month else ""))

    if args.verify:
        return _verificar(meses, ledger, utils)

    migrados = omitidos = errores = 0
    for item in meses:
        beneficiario, mes = item.get("beneficiaryId"), item.get("monthKey")
        filas = item.get("ledger") or []
        if not filas:
            omitidos += 1
            continue
        if not args.apply:
            print(f"  [simulacro] {beneficiario} {mes}: {len(filas)} filas")
            migrados += 1
            continue
        try:
            ledger._write_ledger_rows(dict(item))
            migrados += 1
        except Exception as error:                                    # noqa: BLE001
            print(f"  ERROR {beneficiario} {mes}: {type(error).__name__}: {error}")
            errores += 1

    print(f"\nmigrados: {migrados}   sin filas: {omitidos}   errores: {errores}")
    if not args.apply:
        print("Simulacro: no se escribió nada. Repetir con --apply.")
    return 1 if errores else 0


def _verificar(meses, ledger, utils) -> int:
    """Comprueba que los totales coinciden entre ambos esquemas."""
    discrepancias = 0
    for item in meses:
        beneficiario, mes = item.get("beneficiaryId"), item.get("monthKey")
        por_filas = ledger._read_ledger_rows(beneficiario, mes)
        if por_filas is None:
            print(f"  FALTA  {beneficiario} {mes}: no existe en el esquema por filas")
            discrepancias += 1
            continue
        original = ledger._recalc_ledger_totals(dict(item))
        for campo in ("totalPending", "totalConfirmed", "totalBlocked"):
            if utils._to_decimal(original.get(campo)) != utils._to_decimal(por_filas.get(campo)):
                print(f"  DIFIERE {beneficiario} {mes} {campo}: "
                      f"{original.get(campo)} vs {por_filas.get(campo)}")
                discrepancias += 1
        if len(original.get("ledger") or []) != len(por_filas.get("ledger") or []):
            print(f"  DIFIERE {beneficiario} {mes}: número de filas")
            discrepancias += 1

    print(f"\ndiscrepancias: {discrepancias}")
    return 1 if discrepancias else 0


if __name__ == "__main__":
    sys.exit(main())
