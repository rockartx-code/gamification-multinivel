"""Registro de eventos de auditoría."""

import uuid

from .values import _now_iso
from .logs import _log_error
from .db import _put_entity


def _audit_event(action: str, headers, payload=None, target=None) -> None:
    """Registra un evento de auditoría."""
    headers = headers or {}
    actor_user_id = headers.get("x-user-id") or headers.get("x-actor-id")
    now = _now_iso()
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    item = {
        "entityType": "adminEvent", "eventId": event_id, "action": action,
        "actorUserId": actor_user_id, "target": target or {},
        "payload": payload or {}, "createdAt": now, "updatedAt": now,
    }
    try:
        _put_entity("ADMIN_EVENT", event_id, item, created_at_iso=now)
    except Exception as ex:
        # La auditoría no debe tumbar la operación auditada, pero perderla en
        # silencio deja un hueco en el rastro sin que nadie se entere.
        _log_error("audit_event_write_failed", ex, action=action, eventId=event_id)
