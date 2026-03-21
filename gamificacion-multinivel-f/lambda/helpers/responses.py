import json
from decimal import Decimal
from typing import Any, Dict


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def json_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": (
                "Content-Type,Authorization,"
                "X-User-Id,X-User-Name,X-User-Role,"
                "x-user-id,x-user-name,x-user-role,"
                "X-Webhook-Secret,x-webhook-secret,"
                "X-MercadoLibre-Signature,x-mercadolibre-signature"
            ),
        },
        "body": json.dumps(payload, default=json_default),
    }
