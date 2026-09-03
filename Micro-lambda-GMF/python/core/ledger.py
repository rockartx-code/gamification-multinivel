"""Mes contable de comisiones, con bloqueo optimista."""
from . import db

import json
import time
from typing import Optional
from botocore.exceptions import ClientError

from .settings import COMMISSION_MONTH_PK, D_ZERO, LEDGER_MAX_ATTEMPTS, LEDGER_ROW_SCHEME
from .values import _now_iso, _to_decimal



def _ledger_sk(beneficiary_id, month_key) -> str:
    return f"#BENEFICIARY#{beneficiary_id}#MONTH#{month_key}"

def _get_ledger_month(beneficiary_id, month_key):
    """Obtiene o inicializa el registro contable mensual del socio.

    Con `LEDGER_ROW_SCHEME="rows"` se reconstruye desde los items por fila; si
    ese mes aún no existe ahí, cae al esquema original para no perder datos
    durante la transición.
    """
    if LEDGER_ROW_SCHEME == "rows":
        desde_filas = _read_ledger_rows(beneficiary_id, month_key)
        if desde_filas is not None:
            return desde_filas

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
        elif st == "voided": continue  # tachada: se ve, no suma
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

    if LEDGER_ROW_SCHEME == "rows":
        # Sin item único: no hay nada que bloquear de forma optimista.
        _write_ledger_rows(item)
        return item

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
        if LEDGER_ROW_SCHEME == "dual":
            # Se puebla el esquema nuevo con tráfico real sin depender de él.
            try:
                _write_ledger_rows(item)
            except Exception as error:                                # noqa: BLE001
                from .logs import _log_error
                _log_error("ledger_dual_write_failed", error,
                           beneficiaryId=item.get("beneficiaryId"),
                           monthKey=item.get("monthKey"))
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

def _void_ledger_rows_for_order(beneficiary_id, month_key, order_id, reason: str = None) -> Optional[dict]:
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
        removed = [r for r in rows if r.get("orderId") == order_id and (r.get("status") or "").lower() != "voided"]
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

        # Las filas anuladas se conservan tachadas: la socia veía "Sin movimientos
        # este mes" donde antes había una comisión avisada por correo.
        ahora = _now_iso()
        conservadas = []
        for r in rows:
            if r.get("orderId") == order_id and (r.get("status") or "").lower() != "voided":
                conservadas.append({**r, "status": "voided", "previousStatus": r.get("status"),
                                    "voidedAt": ahora, "voidReason": reason or "anulada"})
            else:
                conservadas.append(r)
        item["ledger"] = conservadas
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

# ---------------------------------------------------------------------------
# Esquema por filas (un item por comisión)
# ---------------------------------------------------------------------------
# El esquema original guarda TODAS las filas del mes dentro de una lista en un
# único item. Eso trae tres problemas:
#
#   1. Techo de 400 KB por item: un líder con volumen alto lo alcanza y las
#      escrituras empiezan a fallar con ValidationException.
#   2. Contención: el bloqueo optimista serializa a los escritores del mismo
#      mes; sus reintentos no son paralelismo, son cola.
#   3. Cada fila nueva reescribe el item entero.
#
# El esquema por filas guarda cada comisión como su propio item y mantiene los
# totales con `ADD` atómico en una cabecera. Escrituras concurrentes sobre el
# mismo mes dejan de competir.
#
# La transición es en dos fases y sin ventana de caída:
#   - LEDGER_ROW_SCHEME="off"  (por defecto): esquema original, sin cambios.
#   - LEDGER_ROW_SCHEME="dual": escribe en ambos y lee del original. Permite
#     poblar el esquema nuevo con tráfico real y comparar.
#   - LEDGER_ROW_SCHEME="rows": lee y escribe solo por filas.
#
# `tools/migrate_ledger_rows.py` expande los meses existentes; es idempotente.

def _ledger_rows_pk(beneficiary_id, month_key) -> str:
    return f"LEDGER#{beneficiary_id}#{month_key}"


def _ledger_row_sk(row_id) -> str:
    return f"ROW#{row_id}"


LEDGER_HEADER_SK = "HEADER"

# Índice por mes del esquema por filas: la partición `LEDGER#<socia>#<mes>` no
# se puede recorrer "por mes", y Pagos del mes, los avisos y las acciones
# urgentes necesitan justo eso. Cada cabecera se copia aquí con SK `<mes>#<socia>`.
COMMISSION_MONTH_INDEX_PK = "COMMISSION_MONTH_INDEX"

# Campos que el esquema por filas reconstruye por su cuenta; el resto (marcas de
# idempotencia como `blockedNoticeSentDays`, `clabeReminderAt`, `paidAt`…) viaja
# en la cabecera para que ninguna se pierda al cambiar de esquema.
_CAMPOS_RECONSTRUIDOS = frozenset((
    "PK", "SK", "entityType", "ledger", "totalPending", "totalConfirmed", "totalBlocked",
    "updatedAt", "version", "status", "createdAt", "beneficiaryId", "monthKey",
))


def _ledger_index_sk(beneficiary_id, month_key) -> str:
    return f"{month_key}#{beneficiary_id}"


def _campos_extra(item: dict) -> dict:
    return {k: v for k, v in (item or {}).items() if k not in _CAMPOS_RECONSTRUIDOS}


def _read_ledger_rows(beneficiary_id, month_key) -> Optional[dict]:
    """Reconstruye el mes contable desde los items por fila.

    Devuelve None si ese mes aún no existe en el esquema nuevo, para que el
    llamador pueda caer al esquema original durante la transición.
    """
    from .db import _query_all_pages
    from boto3.dynamodb.conditions import Key

    items = _query_all_pages(
        KeyConditionExpression=Key("PK").eq(_ledger_rows_pk(beneficiary_id, month_key))
    )
    if not items:
        return None

    cabecera = next((i for i in items if i.get("SK") == LEDGER_HEADER_SK), {})
    filas = [
        {k: v for k, v in item.items() if k not in ("PK", "SK")}
        for item in items if str(item.get("SK", "")).startswith("ROW#")
    ]
    filas.sort(key=lambda f: str(f.get("createdAt") or ""))

    reconstruido = {
        **_campos_extra(cabecera),
        "PK": COMMISSION_MONTH_PK,
        "SK": _ledger_sk(beneficiary_id, month_key),
        "entityType": "commissionMonth",
        "beneficiaryId": cabecera.get("beneficiaryId", beneficiary_id),
        "monthKey": month_key,
        "ledger": filas,
        "status": cabecera.get("status", "IN_PROGRESS"),
        "createdAt": cabecera.get("createdAt") or _now_iso(),
        "version": cabecera.get("version", 0),
    }
    return _recalc_ledger_totals(reconstruido)


def _write_ledger_rows(item: dict) -> None:
    """Persiste el mes en el esquema por filas.

    Los totales se recalculan y se escriben en la cabecera. La ventaja frente
    al item único no está aquí sino en `_add_ledger_row`, que añade una fila
    sin tocar a las demás.
    """
    beneficiario, mes = item.get("beneficiaryId"), item.get("monthKey")
    pk = _ledger_rows_pk(beneficiario, mes)
    _recalc_ledger_totals(item)

    cabecera = {
        **_campos_extra(item),
        "entityType": "commissionMonthHeader",
        "beneficiaryId": beneficiario, "monthKey": mes,
        "totalPending": item.get("totalPending", D_ZERO),
        "totalConfirmed": item.get("totalConfirmed", D_ZERO),
        "totalBlocked": item.get("totalBlocked", D_ZERO),
        "status": item.get("status", "IN_PROGRESS"),
        "createdAt": item.get("createdAt") or _now_iso(),
        "updatedAt": _now_iso(),
        "version": item.get("version", 0),
    }
    db._table.put_item(Item={"PK": pk, "SK": LEDGER_HEADER_SK, **cabecera})
    db._table.put_item(Item={"PK": COMMISSION_MONTH_INDEX_PK, "SK": _ledger_index_sk(beneficiario, mes),
                             **cabecera, "entityType": "commissionMonthIndex"})

    vigentes = set()
    for fila in item.get("ledger", []):
        row_id = str(fila.get("rowId") or "")
        if not row_id:
            continue
        vigentes.add(row_id)
        db._table.put_item(Item={"PK": pk, "SK": _ledger_row_sk(row_id), **fila})

    # Filas que ya no están en el item (una anulación las quitó).
    from .db import _query_all_pages
    from boto3.dynamodb.conditions import Key
    for existente in _query_all_pages(KeyConditionExpression=Key("PK").eq(pk)):
        sk = str(existente.get("SK", ""))
        if sk.startswith("ROW#") and sk[len("ROW#"):] not in vigentes:
            db._table.delete_item(Key={"PK": pk, "SK": sk})


def _add_ledger_row(beneficiary_id, month_key, fila: dict) -> None:
    """Añade o reemplaza UNA fila y actualiza los totales atómicamente.

    Este es el camino que el esquema por filas hace barato: no lee ni reescribe
    el resto del mes, así que dos órdenes pagadas a la vez no compiten.
    """
    pk = _ledger_rows_pk(beneficiary_id, month_key)
    row_id = str(fila.get("rowId") or "")
    importe = _to_decimal(fila.get("amount"))
    estado = fila.get("status") or "pending"
    campo_total = {
        "confirmed": "totalConfirmed",
        "blocked": "totalBlocked",
        "voided": None,  # tachada: no suma en ningún total
    }.get(estado, "totalPending")

    anterior = db._table.get_item(Key={"PK": pk, "SK": _ledger_row_sk(row_id)}).get("Item")
    db._table.put_item(Item={"PK": pk, "SK": _ledger_row_sk(row_id), **fila})

    deltas = {campo_total: importe} if campo_total else {}
    if anterior:
        # Reescritura de una fila existente: se descuenta su aporte previo.
        campo_previo = {
            "confirmed": "totalConfirmed",
            "blocked": "totalBlocked",
            "voided": None,
        }.get(anterior.get("status") or "pending", "totalPending")
        if campo_previo:
            deltas[campo_previo] = deltas.get(campo_previo, D_ZERO) - _to_decimal(anterior.get("amount"))

    if not deltas:
        deltas = {"totalPending": D_ZERO}
    expresion = "ADD " + ", ".join(f"{campo} :{campo}" for campo in deltas)
    valores = {
        **{f":{campo}": valor for campo, valor in deltas.items()},
        ":u": _now_iso(), ":b": beneficiary_id, ":m": month_key,
    }
    for clave in ((pk, LEDGER_HEADER_SK), (COMMISSION_MONTH_INDEX_PK, _ledger_index_sk(beneficiary_id, month_key))):
        db._table.update_item(
            Key={"PK": clave[0], "SK": clave[1]},
            UpdateExpression=expresion + " SET updatedAt = :u, beneficiaryId = :b, monthKey = :m",
            ExpressionAttributeValues=valores,
        )


def _listar_meses_contables(month_key: Optional[str] = None) -> list:
    """Meses contables (uno por beneficiaria) de `month_key`, o todos si no se
    indica, con la misma forma en ambos esquemas: totales, `status`,
    `beneficiaryId`, `monthKey`, las marcas de idempotencia y el `SK` original.

    Es el único lector "por mes" que deben usar Pagos del mes, el CSV, el lote,
    los avisos y las acciones urgentes: con el esquema por filas el bucket
    `COMMISSION_MONTH` no existe.
    """
    from .db import _query_all_pages
    from boto3.dynamodb.conditions import Key

    if LEDGER_ROW_SCHEME != "rows":
        condicion = Key("PK").eq(COMMISSION_MONTH_PK)
        items = _query_all_pages(KeyConditionExpression=condicion)
        marca = f"#MONTH#{month_key}" if month_key else None
        return [i for i in items if str(i.get("beneficiaryId") or "") and (not marca or marca in str(i.get("SK") or ""))]

    condicion = Key("PK").eq(COMMISSION_MONTH_INDEX_PK)
    if month_key:
        condicion = condicion & Key("SK").begins_with(f"{month_key}#")
    salida = []
    for cabecera in _query_all_pages(KeyConditionExpression=condicion):
        beneficiario, mes = cabecera.get("beneficiaryId"), cabecera.get("monthKey")
        if beneficiario in (None, "") or not mes:
            continue
        salida.append({
            **{k: v for k, v in cabecera.items() if k not in ("PK", "SK")},
            "PK": COMMISSION_MONTH_PK, "SK": _ledger_sk(beneficiario, mes),
            "entityType": "commissionMonth", "ledger": [],
        })
    return salida
