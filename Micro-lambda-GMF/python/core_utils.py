import base64
import hashlib
import json
import os
import uuid
import functools
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
from boto3.dynamodb.conditions import Attr, Key

# ---------------------------------------------------------------------------
# Configuración Global (Extraída de Variables de Entorno)
# ---------------------------------------------------------------------------
TABLE_NAME = os.getenv("TABLE_NAME", "multinivel")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("BUCKET_NAME", "findingu-ventas")

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)

# Constantes de Negocio
D_ZERO = Decimal("0")
D_ONE = Decimal("1")
D_CENT = Decimal("0.01")
MAX_NETWORK_DEPTH = 3

# ---------------------------------------------------------------------------
# Helpers de Tipos y JSON
# ---------------------------------------------------------------------------
def _to_decimal(n: Any) -> Decimal:
    if isinstance(n, Decimal): return n
    if n is None or n == "": return D_ZERO
    try:
        return Decimal(str(n))
    except:
        return D_ZERO

def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

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

def _parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body: return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except:
        return {}

# ---------------------------------------------------------------------------
# Manejo de Tiempo
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"

# ---------------------------------------------------------------------------
# Patrón de Persistencia (Pattern 1: BUCKET PK + REF)
# ---------------------------------------------------------------------------
def _bucket_pk(entity: str) -> str:
    return entity.upper()

def _ref_pk(entity: str, entity_id: Any) -> str:
    return f"{entity.upper()}#{entity_id}"

def _make_bucket_sk(created_at_iso: str, entity_id: Any) -> str:
    return f"{created_at_iso}#{entity_id}"

def _put_entity(entity: str, entity_id: Any, item: dict, created_at_iso: Optional[str] = None) -> dict:
    entity = entity.upper()
    created_at = created_at_iso or item.get("createdAt") or _now_iso()
    
    main_item = dict(item)
    main_item["PK"] = _bucket_pk(entity)
    main_item["SK"] = main_item.get("SK") or _make_bucket_sk(created_at, entity_id)
    main_item["createdAt"] = main_item.get("createdAt") or created_at
    main_item["updatedAt"] = _now_iso()

    ref_item = {
        "PK": _ref_pk(entity, entity_id),
        "SK": "REF",
        "entityId": entity_id,
        "refPK": main_item["PK"],
        "refSK": main_item["SK"],
        "updatedAt": main_item["updatedAt"]
    }

    _table.put_item(Item=main_item)
    _table.put_item(Item=ref_item)
    return main_item

def _get_by_id(entity: str, entity_id: Any) -> Optional[dict]:
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: return None
    resp_main = _table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return resp_main.get("Item")

def _update_by_id(entity: str, entity_id: Any, expression: str, values: dict, names: dict = None) -> dict:
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: raise KeyError(f"{entity}_NOT_FOUND")

    kwargs = {
        "Key": {"PK": ref["refPK"], "SK": ref["refSK"]},
        "UpdateExpression": expression,
        "ExpressionAttributeValues": values,
        "ReturnValues": "ALL_NEW"
    }
    if names: kwargs["ExpressionAttributeNames"] = names
    
    resp = _table.update_item(**kwargs)
    return resp.get("Attributes")

def _query_bucket(entity: str, limit: int = None, forward: bool = False) -> List[dict]:
    pk = _bucket_pk(entity)
    query_kwargs = {"KeyConditionExpression": Key("PK").eq(pk), "ScanIndexForward": forward}
    if limit: query_kwargs["Limit"] = limit
    
    items = []
    while True:
        resp = _table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek or (limit and len(items) >= limit): break
        query_kwargs["ExclusiveStartKey"] = lek
    return items

# ---------------------------------------------------------------------------
# Seguridad y Privilegios
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()

def _customer_entity_id(raw_id: Any) -> Any:
    """Convierte el ID de un customer al tipo correcto (int si es numérico, str si no)."""
    try:
        return int(raw_id)
    except (ValueError, TypeError):
        return raw_id

_ALL_PRIVILEGES = [
    "access_screen_orders",
    "access_screen_customers",
    "access_screen_products",
    "access_screen_stocks",
    "access_screen_pos",
    "access_screen_stats",
    "access_screen_settings",
    "order_mark_paid",
    "order_mark_shipped",
    "order_mark_delivered",
    "order_create",
    "customer_add",
    "commissions_register_payment",
    "product_add",
    "product_update",
    "product_set_month",
    "stock_create",
    "stock_create_transfer",
    "stock_add_inventory",
    "stock_mark_damaged",
    "stock_receive_transfer",
    "pos_register_sale",
    "user_mark_admin",
    "user_manage_privileges",
    "employee_add",
    "employee_manage_privileges",
    "access_screen_employees",
    "config_manage",
    "access_screen_honor_board",
]

def _normalize_privileges(raw: Any) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {p: bool(data.get(p)) for p in _ALL_PRIVILEGES}


# ---------------------------------------------------------------------------
# Autenticación y Autorización
# ---------------------------------------------------------------------------

def _extract_actor(headers: dict) -> dict:
    """Extrae identidad del actor desde headers inyectados por API Gateway / Authorizer.

    Retorna dict con:
      user_id    : str | None
      role       : str  — 'admin' | 'employee' | 'cliente' | ''
      privileges : dict — mapa de privilegios (vacío si no es admin/employee)
    """
    h = headers or {}
    user_id = (h.get("x-user-id") or h.get("X-User-Id") or "").strip() or None
    role = (h.get("x-user-role") or h.get("X-User-Role") or "").strip().lower()
    # Privilegios llegan serializados como JSON en el header x-user-privileges
    raw_privs = h.get("x-user-privileges") or h.get("X-User-Privileges") or "{}"
    try:
        privs = json.loads(raw_privs) if isinstance(raw_privs, str) else (raw_privs or {})
    except Exception:
        privs = {}
    if user_id:
        return {"user_id": user_id, "role": role, "privileges": _normalize_privileges(privs)}

    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if token:
        session = _get_by_id("SESSION", token)
        if isinstance(session, dict):
            return {
                "user_id": str(session.get("userId") or "").strip() or None,
                "role": str(session.get("role") or "").strip().lower(),
                "privileges": _normalize_privileges(session.get("privileges")),
            }
    return {"user_id": user_id, "role": role, "privileges": _normalize_privileges(privs)}


def _extract_actor_from_bearer(headers: dict) -> dict:
    """Extrae identidad unicamente desde Authorization: Bearer <token>."""
    h = headers or {}
    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if not token:
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    session = _get_by_id("SESSION", token)
    if not isinstance(session, dict):
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    return {
        "user_id": str(session.get("userId") or "").strip() or None,
        "role": str(session.get("role") or "").strip().lower(),
        "privileges": _normalize_privileges(session.get("privileges")),
    }


def _extract_admin_actor(headers: dict) -> dict:
    """Extrae actor administrativo desde headers x-user-* legacy."""
    actor = _extract_actor(headers)
    if actor.get("role") in ("admin", "employee"):
        return actor
    return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}


def _extract_bearer_token(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    prefix = "bearer "
    if raw.lower().startswith(prefix):
        token = raw[len(prefix):].strip()
        return token or None
    return None


def _require_admin(headers: dict, privilege: Optional[str] = None) -> Optional[dict]:
    """Devuelve respuesta 403 si el actor NO es admin/employee con el privilegio requerido.

    Si el actor está autorizado, devuelve None (sin error).
    Uso:
        err = _require_admin(headers, "order_mark_paid")
        if err: return err
    """
    actor = _extract_actor(headers)
    if actor["role"] not in ("admin", "employee"):
        return _json_response(403, {"message": "Acceso denegado: se requiere perfil admin"})
    if privilege and not actor["privileges"].get(privilege):
        return _json_response(403, {"message": f"Acceso denegado: privilegio '{privilege}' requerido"})
    return None


def _require_self_or_admin(headers: dict, resource_customer_id: Any) -> Optional[dict]:
    """Devuelve respuesta 403 si el actor NO es el propietario del recurso ni un admin.

    Un customer sólo puede acceder a recursos cuyo customerId coincida con su user_id.
    Un admin/employee siempre puede acceder.
    Uso:
        err = _require_self_or_admin(headers, order["customerId"])
        if err: return err
    """
    actor = _extract_actor(headers)
    if actor["role"] in ("admin", "employee"):
        return None
    if not actor["user_id"]:
        return _json_response(401, {"message": "No autenticado"})
    if str(actor["user_id"]) != str(resource_customer_id):
        return _json_response(403, {"message": "Acceso denegado: solo puedes ver tus propios recursos"})
    return None


def _require_self_or_admin_from_bearer(headers: dict, resource_customer_id: Any) -> Optional[dict]:
    """Protege endpoints self-service con Bearer para customers y conserva admin legacy."""
    bearer_actor = _extract_actor_from_bearer(headers)
    if bearer_actor["role"] in ("admin", "employee"):
        return None
    if bearer_actor["user_id"]:
        if str(bearer_actor["user_id"]) != str(resource_customer_id):
            return _json_response(403, {"message": "Acceso denegado: solo puedes ver tus propios recursos"})
        return None

    admin_actor = _extract_admin_actor(headers)
    if admin_actor["role"] in ("admin", "employee"):
        return None
    return _json_response(401, {"message": "No autenticado"})

# ---------------------------------------------------------------------------
# Carga de Configuración (con Cache)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def _load_app_config() -> dict:
    # Intenta cargar la configuración global del negocio
    cfg = _get_by_id("CONFIG", "app-v1")
    if cfg: return cfg.get("config", {})
    return {} # Retornar default si no existe

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
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Email (SES) — Envío Genérico
# ---------------------------------------------------------------------------

_ses_client = None

def _get_ses():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses", region_name=AWS_REGION)
    return _ses_client

SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "info@findingu.com.mx")
def _send_ses_email(to_email: str, subject: str, text: str, html: str) -> None:
    """Envía un correo vía SES. Falla silenciosamente para no interrumpir el flujo."""
    try:
        _get_ses().send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            },
        )
    except Exception as e:
        print(f"[SES_ERROR] {to_email}: {e}")
