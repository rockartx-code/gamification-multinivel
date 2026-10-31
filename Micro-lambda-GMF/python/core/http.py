"""Contrato HTTP con API Gateway: CORS, respuestas y petición normalizada."""

import base64
import json
from typing import Optional

from .values import _json_default
from .logs import _log_error


def _cors_headers(content_type: Optional[str] = "application/json") -> dict:
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-User-Id,X-User-Name,X-User-Role",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers

def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(payload, default=_json_default),
    }

def _cors_preflight_response() -> dict:
    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({"ok": True}),
    }

class HttpRequest:
    """Datos ya normalizados de una petición de API Gateway.

    Los 8 `lambda_handler` repetían este mismo preámbulo: leer método y ruta,
    responder el preflight CORS, parsear el cuerpo, sacar las cabeceras y
    partir la ruta en segmentos quitando el prefijo del recurso.
    """

    __slots__ = ("event", "method", "path", "headers", "query", "body", "segments")

    def __init__(self, event: dict, strip_prefix: Optional[str] = None):
        self.event = event or {}
        self.method = (self.event.get("httpMethod") or "").upper()
        self.path = self.event.get("path") or ""
        self.headers = self.event.get("headers") or {}
        self.query = self.event.get("queryStringParameters") or {}
        self.body = _parse_body(self.event)

        segments = [s for s in self.path.strip("/").split("/") if s]
        # API Gateway entrega el path con el prefijo del recurso
        # (ANY /commissions/{proxy+} llega como /commissions/...).
        if strip_prefix and segments and segments[0] == strip_prefix:
            segments = segments[1:]
        self.segments = segments

    @property
    def is_preflight(self) -> bool:
        return self.method == "OPTIONS"

    def segment(self, index: int) -> Optional[str]:
        """Segmento `index` de la ruta, o None si no existe."""
        return self.segments[index] if len(self.segments) > index else None

def _http_request(event: dict, strip_prefix: Optional[str] = None) -> HttpRequest:
    return HttpRequest(event, strip_prefix)

def _handle_unexpected(event_name: str, error: Exception, **fields) -> dict:
    """Respuesta 500 con el error registrado en JSON.

    Antes cada lambda cerraba con su propio `except Exception` y un
    `print(f"[TAG] {e}")`, con formatos distintos e imposibles de agregar.
    """
    _log_error(event_name, error, **fields)
    return _json_response(500, {"message": "Error interno", "error": str(error)})

def _parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body: return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return {}
