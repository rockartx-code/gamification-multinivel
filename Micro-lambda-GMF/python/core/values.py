"""Conversiones y normalizaciones puras (sin acceso a datos)."""

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from .settings import D_ZERO


def _to_decimal(n: Any) -> Decimal:
    if isinstance(n, Decimal): return n
    if n is None or n == "": return D_ZERO
    try:
        return Decimal(str(n))
    except (ArithmeticError, TypeError, ValueError):
        return D_ZERO

def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _ttl_epoch(seconds_from_now: int) -> int:
    """Epoch en segundos para el atributo TTL de DynamoDB.

    Requiere tener el TTL habilitado en la tabla con el atributo `ttl`; si no
    lo está, el valor es inocuo y la purga simplemente no ocurre.
    """
    return int(time.time()) + int(seconds_from_now)

def _month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"

def _normalize_ddb_key(key: dict) -> Optional[dict]:
    if not isinstance(key, dict):
        return None

    pk = key.get("PK")
    sk = key.get("SK")
    if pk in (None, "") or sk in (None, ""):
        return None

    return {
        "PK": str(pk),
        "SK": str(sk),
    }

def _dedupe_ddb_keys(keys: List[dict]) -> List[dict]:
    normalized: List[dict] = []
    seen = set()

    for raw_key in keys or []:
        key = _normalize_ddb_key(raw_key)
        if not key:
            continue
        dedupe_key = (key["PK"], key["SK"])
        if dedupe_key in seen:
            continue
        normalized.append(key)
        seen.add(dedupe_key)

    return normalized

def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()

def _customer_entity_id(raw_id: Any) -> Any:
    """Convierte el ID de un customer al tipo correcto (int si es numérico, str si no)."""
    try:
        return int(raw_id)
    except (ValueError, TypeError):
        return raw_id

def _customer_id_str(raw_id: Any) -> str:
    value = _customer_entity_id(raw_id)
    if value in (None, ""):
        return ""
    return str(value)

def _associate_month_entity_id(associate_id: Any, month_key: str) -> str:
    customer_id = _customer_id_str(associate_id)
    normalized_month_key = str(month_key or "").strip()
    if not customer_id or not normalized_month_key:
        return ""
    return f"{customer_id}#{normalized_month_key}"

def _customer_id_list(raw_ids: Any) -> List[str]:
    if not isinstance(raw_ids, list):
        return []
    out: List[str] = []
    seen = set()
    for raw_id in raw_ids:
        cid = _customer_id_str(raw_id)
        if not cid or cid in seen:
            continue
        out.append(cid)
        seen.add(cid)
    return out

def _merge_dict(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for k, v in override.items():
            merged[k] = _merge_dict(merged.get(k), v)
        return merged
    return override if override is not None else base
