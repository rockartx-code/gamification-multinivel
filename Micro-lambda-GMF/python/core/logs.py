"""Logging estructurado en JSON."""

import json

from .settings import TABLE_NAME
from .values import _json_default, _normalize_ddb_key


def _log(event: str, level: str = "INFO", **fields) -> None:
    """Emite una línea de log en JSON.

    CloudWatch Insights puede filtrar y agregar por campo sobre JSON; sobre
    `print(f"[TAG] {e}")` no puede. Todo log nuevo debe pasar por aquí.

        _log("void_commissions_failed", "ERROR", orderId=oid, message=str(ex))
    """
    payload = {"event": event, "level": level}
    payload.update(fields)
    try:
        print(json.dumps(payload, default=_log_default))
    except Exception:
        # Un fallo serializando el log jamás debe tumbar la petición.
        print(json.dumps({"event": event, "level": level, "logSerializationFailed": True}))

def _log_default(value):
    """Serializador tolerante SOLO para logs.

    `_json_default` (el de las respuestas HTTP) lanza TypeError ante un valor
    no serializable, y con él un `_log(..., error=ex)` colapsaba a
    `logSerializationFailed` perdiendo el mensaje y todo el contexto. En un
    log, un valor raro convertido a texto siempre es mejor que nada.
    """
    try:
        return _json_default(value)
    except TypeError:
        return str(value)

def _log_error(event: str, error: Exception, **fields) -> None:
    """Registra una excepción con su tipo y mensaje."""
    _log(event, "ERROR", errorType=error.__class__.__name__, message=str(error), **fields)

def _log_get_item_failure(event: str, key: dict, error: Exception, **extra) -> None:
    payload = {
        "event": event,
        "table": TABLE_NAME,
        "key": _normalize_ddb_key(key) or key,
        "errorType": error.__class__.__name__,
        "message": str(error),
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload, default=_json_default))
