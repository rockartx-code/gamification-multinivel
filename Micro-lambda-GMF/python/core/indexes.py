"""Índices secundarios mantenidos a mano (nombre, email, código de referido)."""

import json
from typing import Any, List, Optional
from boto3.dynamodb.conditions import Key

from .values import _customer_id_str, _json_default, _normalize_email, _now_iso
from . import db
from .db import _query_all_pages, _query_bucket


def _customer_email_index_key(email: Any) -> Optional[dict]:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    return {"PK": f"REF#EMAIL#{normalized}", "SK": "EMAIL"}

def _upsert_customer_email_index(customer_id: Any, email: Any, previous_email: Any = None) -> None:
    """Mantiene el índice `REF#EMAIL#<email>` → customerId."""
    cid = _customer_id_str(customer_id)
    key = _customer_email_index_key(email)
    previous_key = _customer_email_index_key(previous_email)

    if previous_key and (not key or previous_key["PK"] != key["PK"]):
        try:
            db._table.delete_item(Key=previous_key)
        except Exception as ex:
            print(json.dumps({
                "event": "customer_email_index_cleanup_failed",
                "customerId": cid, "message": str(ex),
            }, default=_json_default))

    if not cid or not key:
        return
    try:
        db._table.put_item(Item={
            **key,
            "entityType": "customerEmailIndex",
            "customerId": customer_id,
            "email": _normalize_email(email),
            "updatedAt": _now_iso(),
        })
    except Exception as ex:
        print(json.dumps({
            "event": "customer_email_index_write_failed",
            "customerId": cid, "message": str(ex),
        }, default=_json_default))

def _find_customer_id_by_email(email: Any) -> Optional[str]:
    """customerId asociado a un email, o None.

    Consulta primero el índice (1 GetItem). Como los clientes anteriores a la
    creación del índice no tienen entrada, cae al barrido de la colección
    cuando el índice no acierta: así el resultado sigue siendo correcto
    durante la transición y se acelera solo a medida que el índice se puebla.
    """
    key = _customer_email_index_key(email)
    if not key:
        return None

    try:
        indexed = db._table.get_item(Key=key).get("Item")
    except Exception:
        indexed = None
    if indexed and indexed.get("customerId") not in (None, ""):
        return _customer_id_str(indexed.get("customerId"))

    normalized = _normalize_email(email)
    for customer in _query_bucket("CUSTOMER"):
        if _normalize_email(customer.get("email")) == normalized:
            cid = _customer_id_str(customer.get("customerId"))
            # Rellena el índice sobre la marcha para no repetir el barrido.
            _upsert_customer_email_index(customer.get("customerId"), customer.get("email"))
            return cid
    return None

def _referral_code_pk(code: Any) -> str:
    """Partición del índice de códigos de referido."""
    return f"REFERRAL_CODE#{str(code or '').strip().upper()}"

def _customer_name_index_pk(name: Any) -> str:
    letter = (str(name or "").strip()[:1] or "?").upper()
    return f"REF#NOMBRE#{letter}"

def _upsert_customer_name_index(customer_id: Any, name: Any, email: Any = None,
                                created_at_iso: Optional[str] = None,
                                previous_name: Any = None) -> None:
    """Mantiene el índice de búsqueda por nombre `REF#NOMBRE#<letra>`.

    Antes solo lo escribía el auto-registro, así que los clientes dados de alta
    por un admin —y los renombrados— no aparecían en la búsqueda del panel.
    Debe invocarse desde toda alta y toda actualización de nombre de CUSTOMER.
    """
    cid = _customer_id_str(customer_id)
    normalized_name = str(name or "").strip()
    if not cid or not normalized_name:
        return

    created_at = str(created_at_iso or _now_iso())
    new_pk = _customer_name_index_pk(normalized_name)
    sort_key = f"{created_at}#{cid}"

    previous_pk = _customer_name_index_pk(previous_name) if previous_name else None
    if previous_pk and previous_pk != new_pk:
        try:
            db._table.delete_item(Key={"PK": previous_pk, "SK": sort_key})
        except Exception as ex:
            print(json.dumps({
                "event": "customer_name_index_cleanup_failed",
                "customerId": cid, "message": str(ex),
            }, default=_json_default))

    try:
        db._table.put_item(Item={
            "PK": new_pk,
            "SK": sort_key,
            "entityType": "customerNameIndex",
            "customerId": customer_id,
            "nameLower": normalized_name.lower(),
            "email": email,
            "createdAt": created_at,
            "updatedAt": _now_iso(),
        })
    except Exception as ex:
        print(json.dumps({
            "event": "customer_name_index_write_failed",
            "customerId": cid, "message": str(ex),
        }, default=_json_default))

def _query_customer_name_index(letter: str) -> List[dict]:
    """Lee TODAS las páginas del índice de nombres de una letra."""
    return _query_all_pages(
        KeyConditionExpression=Key("PK").eq(f"REF#NOMBRE#{str(letter or '?').upper()}"),
        ScanIndexForward=True,
    )
