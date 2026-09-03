"""Contraseñas, actores y privilegios."""

import hashlib
import hmac
import json
import os
from typing import Any, Optional

from .settings import PASSWORD_HASH_ITERATIONS, PASSWORD_HASH_SCHEME, _ALL_PRIVILEGES, _SUPERADMIN_TOKEN
from .http import _json_response
from .network import _get_session


def _hash_token(value: str) -> str:
    """Digest determinista para valores de un solo uso (OTP, tokens de enlace).

    Determinista a propósito: se compara el digest de la entrada contra el
    almacenado. NO usar para contraseñas — para eso está `_hash_password`.
    """
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

def _hash_password(password: str, *, salt: Optional[bytes] = None,
                   iterations: Optional[int] = None) -> str:
    """Deriva la contraseña con PBKDF2-HMAC-SHA256 y sal aleatoria.

    Formato: `pbkdf2_sha256$<iteraciones>$<sal_hex>$<derivado_hex>`.

    El esquema anterior era SHA-256 a secas: sin sal ni factor de trabajo, dos
    usuarios con la misma contraseña producían el mismo hash y una filtración
    de la tabla se rompía con tablas precalculadas. `_verify_password` sigue
    aceptando los hashes viejos para no invalidar las cuentas existentes.
    """
    salt = salt or os.urandom(16)
    rounds = int(iterations or PASSWORD_HASH_ITERATIONS)
    derived = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt, rounds)
    return f"{PASSWORD_HASH_SCHEME}${rounds}${salt.hex()}${derived.hex()}"

def _is_legacy_password_hash(stored: Optional[str]) -> bool:
    """True si el hash guardado usa el esquema viejo (SHA-256 sin sal)."""
    return bool(stored) and not str(stored).startswith(f"{PASSWORD_HASH_SCHEME}$")

def _verify_password(password: str, stored: Optional[str]) -> bool:
    """Compara una contraseña contra el hash guardado, sea del esquema que sea.

    Usa comparación en tiempo constante para no filtrar información por el
    tiempo de respuesta.
    """
    if not stored:
        return False
    stored = str(stored)

    if _is_legacy_password_hash(stored):
        return hmac.compare_digest(_hash_token(password), stored)

    try:
        _scheme, rounds, salt_hex, expected = stored.split("$", 3)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", str(password).encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)

def _superadmin_actor() -> dict:
    """Actor con todos los privilegios para el token de superadmin."""
    return {
        "user_id": "superadmin",
        "role": "admin",
        "privileges": {p: True for p in _ALL_PRIVILEGES},
    }

def _normalize_privileges(raw: Any) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {p: bool(data.get(p)) for p in _ALL_PRIVILEGES}

def _extract_actor(headers: dict) -> dict:
    """Extrae identidad del actor desde headers inyectados por API Gateway / Authorizer.

    Retorna dict con:
      user_id    : str | None
      role       : str  — 'admin' | 'employee' | 'cliente' | ''
      privileges : dict — mapa de privilegios (vacío si no es admin/employee)
    """
    h = headers or {}

    # Bearer token tiene prioridad: contiene rol y privilegios completos de la sesión
    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if token:
        if token == _SUPERADMIN_TOKEN:
            return _superadmin_actor()
        session = _get_session(token)
        if isinstance(session, dict):
            return _actor_de_sesion(session)

    # Fallback: headers legacy inyectados por API Gateway / Authorizer
    user_id = (h.get("x-user-id") or h.get("X-User-Id") or "").strip() or None
    role = (h.get("x-user-role") or h.get("X-User-Role") or "").strip().lower()
    raw_privs = h.get("x-user-privileges") or h.get("X-User-Privileges") or "{}"
    try:
        privs = json.loads(raw_privs) if isinstance(raw_privs, str) else (raw_privs or {})
    except Exception:
        privs = {}
    return {"user_id": user_id, "role": role, "privileges": _normalize_privileges(privs)}

def _extract_actor_from_bearer(headers: dict) -> dict:
    """Extrae identidad unicamente desde Authorization: Bearer <token>."""
    h = headers or {}
    auth_header = (h.get("authorization") or h.get("Authorization") or "").strip()
    token = _extract_bearer_token(auth_header)
    if not token:
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    if token == _SUPERADMIN_TOKEN:
        return _superadmin_actor()

    session = _get_session(token)
    if not isinstance(session, dict):
        return {"user_id": None, "role": "", "privileges": _normalize_privileges({})}

    return _actor_de_sesion(session)

def _actor_de_sesion(session: dict) -> dict:
    """Actor a partir de la sesión. Un cliente con `canAccessAdmin` opera el back
    office como un empleado (sus privilegios mandan); sin esa marca, un cliente
    con privilegios guardados recibía 403 en todo."""
    role = str(session.get("role") or "").strip().lower()
    if role == "cliente" and bool(session.get("canAccessAdmin")):
        role = "employee"
    return {
        "user_id": str(session.get("userId") or "").strip() or None,
        "role": role,
        "privileges": _normalize_privileges(session.get("privileges")),
        "isCustomer": str(session.get("role") or "").strip().lower() == "cliente",
        "name": str(session.get("name") or "").strip(),
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
    # admin tiene acceso total; los privilegios solo restringen a employee
    if privilege and actor["role"] == "employee" and not actor["privileges"].get(privilege):
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
