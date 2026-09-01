"""Mes contable de comisiones, con bloqueo optimista."""
from . import db

import json
import time
from typing import Optional
from botocore.exceptions import ClientError

from .settings import COMMISSION_MONTH_PK, D_ZERO, LEDGER_MAX_ATTEMPTS
from .values import _now_iso, _to_decimal



def _ledger_sk(beneficiary_id, month_key) -> str:
    return f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"

def _get_ledger_month(beneficiary_id, month_key):
    """Obtiene o inicializa el registro contable mensual del socio."""
    sk = _ledger_sk(beneficiary_id, month_key)
    res = db._table.get_item(Key={"PK": COMMISSION_MONTH_PK, "SK": sk})
    item = res.get("Item")

    if not item:
        item = {
            "PK": COMMISSION_MONTH_PK, "SK": sk, "entityType": "commissionMonth",
            "beneficiaryId": beneficiary_id, "monthKey": month_key,
            "ledger": [], "totalPending": D_ZERO,
            "totalConfirmed": D_ZERO, "totalBlocked": D_ZERO,
            "status": "IN_PROGRESS", "createdAt": _now_iso(),
            "version": 0,
        }
    return item

def _recalc_ledger_totals(item: dict) -> dict:
    tp, tc, tb = D_ZERO, D_ZERO, D_ZERO
    for r in item.get("ledger", []):
        amt = _to_decimal(r.get("amount"))
        st = r.get("status")
        if st == "confirmed": tc += amt
        elif st == "blocked": tb += amt
        else: tp += amt
    item.update({"totalPending": tp, "totalConfirmed": tc, "totalBlocked": tb,
                 "updatedAt": _now_iso()})
    return item

def _save_ledger_month(item):
    """Recalcula totales y persiste el mes contable con bloqueo optimista.

    El patrón anterior (GetItem → modificar en memoria → PutItem del item
    completo) perdía escrituras: dos órdenes pagadas a la vez para el mismo
    beneficiario leían el mismo estado y la segunda borraba la comisión de la
    primera. Ahora el put exige que `version` no haya cambiado; si cambió, se
    relee y se reaplica el cambio.
    """
    _recalc_ledger_totals(item)
    expected_version = int(_to_decimal(item.get("version", 0)))
    item["version"] = expected_version + 1

    try:
        if expected_version == 0:
            # `expected == 0` cubre dos casos: el item no existe todavía, o
            # existe de antes de introducir el candado y no tiene `version`.
            # En DynamoDB `version = :cero` FALLA cuando el atributo no existe
            # (no lo trata como cero), así que sin el `attribute_not_exists`
            # ninguna escritura sobre un mes contable legado podría pasar la
            # condición: comisiones, confirmaciones y anulaciones fallarían
            # para todos los beneficiarios existentes.
            db._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(version) OR version = :expected",
                ExpressionAttributeValues={":expected": _to_decimal(expected_version)},
            )
        else:
            db._table.put_item(
                Item=item,
                ConditionExpression="version = :expected",
                ExpressionAttributeValues={":expected": _to_decimal(expected_version)},
            )
        return item
    except ClientError as ex:
        if (ex.response or {}).get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        raise _LedgerConflict(item.get("beneficiaryId"), item.get("monthKey"))

class _LedgerConflict(Exception):
    """Otra escritura concurrente modificó el mes contable."""

    def __init__(self, beneficiary_id, month_key):
        super().__init__(f"ledger_conflict beneficiary={beneficiary_id} month={month_key}")
        self.beneficiary_id = beneficiary_id
        self.month_key = month_key

def _mutate_ledger_month(beneficiary_id, month_key, mutate) -> dict:
    """Aplica `mutate(item)` sobre el mes contable, reintentando ante conflicto.

    `mutate` debe ser idempotente respecto al item que recibe: se le vuelve a
    llamar con el estado recién leído cada vez que otra escritura gana la
    carrera.
    """
    last_error = None
    for attempt in range(LEDGER_MAX_ATTEMPTS):
        item = _get_ledger_month(beneficiary_id, month_key)
        if mutate(item) is False:
            return item
        try:
            return _save_ledger_month(item)
        except _LedgerConflict as conflict:
            last_error = conflict
            time.sleep(min(0.05 * (2 ** attempt), 0.5))

    print(json.dumps({
        "event": "ledger_conflict_exhausted",
        "beneficiaryId": str(beneficiary_id),
        "monthKey": str(month_key),
        "attempts": LEDGER_MAX_ATTEMPTS,
    }))
    raise last_error

def _void_ledger_rows_for_order(beneficiary_id, month_key, order_id) -> Optional[dict]:
    """Quita del mes contable todas las filas de una orden y recalcula totales.

    Antes esto era un `update_item` con deltas calculados sobre una lectura
    previa (`SET ledger = :l, totalPending = totalPending - :pd, ...`): una
    escritura concurrente sobre el mismo mes hacía que se guardara un ledger
    obsoleto y los totales quedaran descuadrados. Ahora comparte el bloqueo
    optimista con el resto de escrituras del ledger.
    """
    summary = {}

    def _mutate(item):
        rows = item.get("ledger") or []
        removed = [r for r in rows if r.get("orderId") == order_id]
        if not removed:
            return False

        pending = confirmed = blocked = D_ZERO
        for row in removed:
            amount = _to_decimal(row.get("amount"))
            status = (row.get("status") or "").lower()
            if status == "pending":
                pending += amount
            elif status == "confirmed":
                confirmed += amount
            elif status == "blocked" or row.get("blocked"):
                blocked += amount

        item["ledger"] = [r for r in rows if r.get("orderId") != order_id]
        summary.update({
            "beneficiaryId": beneficiary_id,
            "orderId": order_id,
            "removedRows": len(removed),
            "pendingRemoved": float(pending),
            "confirmedRemoved": float(confirmed),
            "blockedRemoved": float(blocked),
        })
        return True

    _mutate_ledger_month(beneficiary_id, month_key, _mutate)
    return summary or None
