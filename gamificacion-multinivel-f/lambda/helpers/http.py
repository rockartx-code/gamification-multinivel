import base64
import json
from typing import Any, Dict, List


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            return {}
    try:
        return json.loads(body)
    except Exception:
        return {}


def get_query_params(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("queryStringParameters") or {}


def get_path(event: Dict[str, Any]) -> str:
    path_params = event.get("pathParameters") or {}
    proxy = path_params.get("proxy")

    if proxy:
        path = f"/{proxy}"
    else:
        path = event.get("path", "/") or "/"

    stage = (event.get("requestContext") or {}).get("stage")
    if stage and path.startswith(f"/{stage}/"):
        path = path[len(stage) + 1 :]

    if path.startswith("/Multinivel/"):
        path = path[11:]

    return path if path.startswith("/") else f"/{path}"


def path_segments(event: Dict[str, Any]) -> List[str]:
    path = get_path(event).strip("/")
    return [segment for segment in path.split("/") if segment]
