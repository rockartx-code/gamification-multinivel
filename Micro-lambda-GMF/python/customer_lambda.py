import base64
import json
import time
import boto3
import core_utils as utils  # Importado desde la Lambda Layer
import dashboard_common
from dashboard_common import (
    DEFAULT_SPONSOR,
    _active_notifications_for_customer,
    _build_goals,
    _build_network_tree_with_month,
    _calc_vg_from_tree,
    _compute_buy_again_ids,
    _find_effective_sponsor,
    _get_month_state,
    _get_rank_dash,
    _mxn_to_vp_dash,
    _network_members_from_tree,
    _prev_month_key,
)
from datetime import datetime, timezone
from typing import Optional

# Cliente S3 para subida de documentos propios del cliente
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")
_s3 = boto3.client("s3", region_name=utils.AWS_REGION)
FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")


# --- HELPERS DE NORMALIZACIÓN ---

def _format_customer_output(item):
    """Limpia el objeto de DynamoDB para el frontend y normaliza direcciones/documentos."""
    if not item:
        return None

    out = dict(item)
    # Eliminar llaves internas de DynamoDB
    out.pop("PK", None)
    out.pop("SK", None)
    out.pop("passwordHash", None)  # Nunca enviar el hash

    # Normalizar Direcciones
    addresses = item.get("addresses") or item.get("shippingAddresses") or []
    out["addresses"] = addresses
    out["shippingAddresses"] = addresses

    # Documentos del administrador (los que admin liga al cliente)
    out["documents"] = item.get("documents") or []

    # Documentos propios del cliente (subidos por él mismo)
    out["ownDocuments"] = item.get("ownDocuments") or []

    # Institución bancaria
    out["bankInstitution"] = item.get("bankInstitution") or ""

    # Seguimiento (docs/qa/18): la ejecutiva de recuperación y la gerente no
    # tenían dónde anotar "no contactar", de dónde llegó el cliente ni qué se
    # habló con él; la lista vivía fuera del sistema.
    out["doNotContact"] = bool(item.get("doNotContact"))
    out["contactNotes"] = item.get("contactNotes") or []
    out["origin"] = item.get("origin") or ""
    out["deletedAt"] = item.get("deletedAt")

    # Asegurar tipos decimales a float para JSON
    out["commissions"] = float(utils._to_decimal(item.get("commissions", 0)))
    out["discountRate"] = float(utils._to_decimal(item.get("discountRate", 0)))

    return out


def _mes_anterior(month_key: str) -> str:
    y, m = [int(x) for x in month_key.split("-")]
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def _con_comisiones(customers: list) -> list:
    """Añade a cada ficha lo que la gerente necesita el día de pago.

    La lista solo traía `commissions`, un campo histórico que nadie actualiza:
    el 10 de octubre todas las fichas decían $0 con $250.74 confirmados en el
    ledger y no se pagó nada. Se leen los meses contables una sola vez.
    """
    if not customers:
        return customers
    actual = utils._month_key()
    anterior = _mes_anterior(actual)
    ledgers = {}
    try:
        for item in utils._query_bucket("COMMISSION_MONTH"):
            sk = str(item.get("SK") or "")
            mk = actual if f"#MONTH#{actual}" in sk else (anterior if f"#MONTH#{anterior}" in sk else None)
            if mk:
                ledgers[(str(item.get("beneficiaryId") or ""), mk)] = item
        recibos = {
            str(r.get("customerId")): r.get("assetUrl") or ""
            for r in utils._query_bucket("COMMISSION_RECEIPT", sk_from=anterior)
            if str(r.get("monthKey")) == anterior
        }
    except Exception as ex:
        utils._log("customer_list_commissions_error", "ERROR", error=ex)
        return customers
    out = []
    for c in customers:
        cid = str(c.get("customerId") or "")
        hoy = ledgers.get((cid, actual)) or {}
        prev = ledgers.get((cid, anterior)) or {}
        confirmado_prev = float(utils._to_decimal(prev.get("totalConfirmed", 0)))
        recibo = recibos.get(cid, "")
        c = dict(c)
        c["commissionsCurrentConfirmed"] = float(utils._to_decimal(hoy.get("totalConfirmed", 0)))
        c["commissionsCurrentPending"] = float(utils._to_decimal(hoy.get("totalPending", 0)))
        c["commissionsPrevMonthKey"] = anterior
        c["commissionsPrevMonth"] = confirmado_prev
        c["commissionsPrevStatus"] = "no_moves" if confirmado_prev <= 0 else ("paid" if recibo else "pending")
        c["commissionsPrevReceiptUrl"] = recibo
        out.append(c)
    return out


def _normalize_dashboard_customer(customer):
    if not customer or not isinstance(customer, dict):
        return None

    raw_addresses = customer.get("addresses") or customer.get("shippingAddresses") or []
    default_address_id = str(customer.get("defaultAddressId") or customer.get("defaultShippingAddressId") or "").strip()
    addresses = []

    for index, entry in enumerate(raw_addresses):
        if not isinstance(entry, dict):
            continue

        address = str(entry.get("address") or "").strip()
        postal_code = str(entry.get("postalCode") or "").strip()
        state = str(entry.get("state") or entry.get("city") or "").strip()
        between_streets = str(entry.get("betweenStreets") or "").strip()
        references = str(entry.get("references") or entry.get("reference") or "").strip()

        if not any([address, postal_code, state, between_streets, references]):
            continue

        address_id = str(entry.get("addressId") or entry.get("id") or f"addr-{index + 1}").strip()
        is_default = bool(entry.get("isDefault")) or bool(default_address_id and address_id == default_address_id)

        addresses.append({
            "id": address_id,
            "label": str(entry.get("label") or "").strip(),
            "recipientName": str(entry.get("recipientName") or customer.get("name") or "").strip(),
            "phone": str(entry.get("phone") or customer.get("phone") or "").strip(),
            "street": str(entry.get("street") or "").strip(),
            "number": str(entry.get("number") or "").strip(),
            "address": address,
            "city": str(entry.get("city") or customer.get("city") or "").strip(),
            "postalCode": postal_code,
            "state": state,
            "country": str(entry.get("country") or "MX").strip(),
            "betweenStreets": between_streets,
            "references": references,
            "isDefault": is_default,
        })

    resolved_default_id = default_address_id or next((item["id"] for item in addresses if item.get("isDefault")), "")

    return {
        "id": str(customer.get("customerId") or "").strip(),
        "name": str(customer.get("name") or "").strip(),
        "referralCode": str(customer.get("referralCode") or "").strip().upper(),
        "phone": str(customer.get("phone") or "").strip(),
        "address": str(customer.get("address") or "").strip(),
        "city": str(customer.get("city") or "").strip(),
        "state": str(customer.get("state") or "").strip(),
        "postalCode": str(customer.get("postalCode") or "").strip(),
        "addresses": addresses,
        "defaultAddressId": resolved_default_id,
        "shippingAddresses": addresses,
        "defaultShippingAddressId": resolved_default_id,
    }


def _check_leader_cycle(customer_id, new_leader_id):
    """Evita que un usuario sea su propio abuelo (ciclos infinitos)."""
    if str(customer_id) == str(new_leader_id):
        return True

    leader_profile = utils._get_by_id("CUSTOMER", new_leader_id)
    if leader_profile and str(customer_id) in utils._get_customer_upline_ids(leader_profile):
        return True

    current_leader = new_leader_id
    visited = set()

    while current_leader:
        if current_leader in visited:
            break
        if str(current_leader) == str(customer_id):
            return True
        visited.add(current_leader)
        leader_profile = utils._get_by_id("CUSTOMER", current_leader)
        current_leader = leader_profile.get("leaderId") if leader_profile else None

    return False


class _DashboardTimer:
    def __init__(self, customer_id):
        self.customer_id = str(customer_id or "")
        self.request_id = utils.uuid.uuid4().hex[:12]
        self.started_at = time.perf_counter()
        self.last_at = self.started_at

    def mark(self, stage: str, **extra):
        now = time.perf_counter()
        payload = {
            "event": "customer_dashboard_timing",
            "requestId": self.request_id,
            "customerId": self.customer_id,
            "stage": stage,
            "elapsedMs": round((now - self.last_at) * 1000, 2),
            "totalMs": round((now - self.started_at) * 1000, 2),
        }
        if extra:
            payload.update(extra)
        print(json.dumps(payload, default=utils._json_default))
        self.last_at = now


def _encode_customers_next_token(last_evaluated_key) -> Optional[str]:
    if not last_evaluated_key:
        return None
    sort_key = str(last_evaluated_key.get("SK") or "").strip()
    if not sort_key:
        return None
    raw = json.dumps({"sk": sort_key}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_customers_next_token(token) -> Optional[dict]:
    token_value = str(token or "").strip()
    if not token_value:
        return None
    try:
        padded = token_value + ("=" * (-len(token_value) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        sort_key = str((payload or {}).get("sk") or "").strip()
    except Exception:
        return None
    if not sort_key:
        return None
    return {"PK": "CUSTOMER", "SK": sort_key}


def _query_customers_page(limit: int, next_token=None) -> tuple:
    """Una página real de CUSTOMER, sin leer la colección completa."""
    query_kwargs = {
        "KeyConditionExpression": utils.Key("PK").eq("CUSTOMER"),
        "ScanIndexForward": False,
        "Limit": limit,
    }
    start_key = _decode_customers_next_token(next_token)
    if start_key:
        query_kwargs["ExclusiveStartKey"] = start_key
    response = utils._table.query(**query_kwargs)
    return response.get("Items", []), _encode_customers_next_token(response.get("LastEvaluatedKey"))


def _load_customer_network_scope(customer: dict) -> tuple:
    """Cliente + descendencia vía árbol persistido (implementado en core_utils).

    La misma lógica vivía duplicada aquí, en dashboard_lambda y en
    commissions_lambda con tres niveles distintos de optimización; ahora las
    tres comparten `utils._load_network_scope`.
    """
    return utils._load_network_scope(customer)


# --- HELPERS S3 ---

def _upload_document_s3(name: str, content_base64: str, content_type: str, prefix: str = "documentos-clientes") -> dict:
    """Sube un archivo a S3 y devuelve el objeto de asset."""
    try:
        raw = base64.b64decode(content_base64)
    except Exception:
        raise ValueError("invalid_base64")

    asset_id = f"{prefix}/{utils.uuid.uuid4()}-{name}"
    _s3.put_object(
        Bucket=BUCKET_NAME,
        Key=asset_id,
        Body=raw,
        ContentType=content_type,
        ACL="public-read",
    )
    url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    now = utils._now_iso()
    asset_item = {
        "entityType": "asset",
        "assetId": asset_id,
        "name": name,
        "contentType": content_type,
        "url": url,
        "createdAt": now,
        "updatedAt": now,
    }
    utils._put_entity("ASSET", asset_id, asset_item, created_at_iso=now)
    return {"assetId": asset_id, "url": url, "contentType": content_type}
















def _load_month_states(associate_ids, month_key: str) -> dict:
    return utils._load_month_states(associate_ids, month_key)




























def _find_customer_by_referral_identifier(identifier):
    raw_identifier = str(identifier or "").strip()
    if not raw_identifier:
        return None

    sponsor = utils._get_by_id("CUSTOMER", raw_identifier)
    if sponsor:
        return sponsor

    try:
        sponsor = utils._get_by_id("CUSTOMER", int(raw_identifier))
        if sponsor:
            return sponsor
    except Exception:
        sponsor = None

    try:
        referral_item = utils._table.get_item(Key={"PK": utils._referral_code_pk(raw_identifier), "SK": "REFCodeInput"}).get("Item") or {}
        leader_id = referral_item.get("leaderId")
        if leader_id in (None, ""):
            return None
        sponsor = utils._get_by_id("CUSTOMER", leader_id)
        if sponsor:
            return sponsor
        try:
            return utils._get_by_id("CUSTOMER", int(leader_id))
        except Exception:
            return None
    except Exception as ex:
        utils._log("sponsor_referral_lookup_error", "ERROR", identifier=raw_identifier, error=ex)
        return None


def handle_get_public_sponsor(sponsor_id):
    """GET /customers/sponsor/{idSponsor} admitiendo customerId o referralCode."""
    raw_sponsor_id = str(sponsor_id or "").strip()
    if not raw_sponsor_id:
        return utils._json_response(400, {"message": "idSponsor es obligatorio"})

    sponsor = _find_customer_by_referral_identifier(raw_sponsor_id)

    if not sponsor:
        return utils._json_response(200, {
            "sponsor": {
                **DEFAULT_SPONSOR,
                "isDefault": True,
            }
        })

    return utils._json_response(200, {
        "sponsor": {
            "name": sponsor.get("name") or DEFAULT_SPONSOR["name"],
            "email": sponsor.get("email") or DEFAULT_SPONSOR["email"],
            "phone": sponsor.get("phone") or DEFAULT_SPONSOR["phone"],
            "isDefault": False,
        }
    })








def _resolve_clabe_customer_id(customer_id, body, headers):
    headers = headers or {}
    body = body or {}
    requested_customer_id = customer_id
    if not requested_customer_id or requested_customer_id == "clabe":
        requested_customer_id = str(body.get("customerId", "")).strip() or None

    bearer_actor = utils._extract_actor_from_bearer(headers)
    if bearer_actor.get("role") in ("admin", "employee"):
        if not requested_customer_id:
            return None, utils._json_response(400, {"message": "customerId requerido"})
        return utils._customer_entity_id(requested_customer_id), None

    legacy_admin = utils._extract_admin_actor(headers)
    if legacy_admin.get("role") in ("admin", "employee"):
        if not requested_customer_id:
            return None, utils._json_response(400, {"message": "customerId requerido"})
        return utils._customer_entity_id(requested_customer_id), None

    if not bearer_actor.get("user_id"):
        return None, utils._json_response(401, {"message": "No autenticado"})

    resolved_customer_id = utils._customer_entity_id(bearer_actor.get("user_id"))
    if requested_customer_id and str(requested_customer_id) != str(resolved_customer_id):
        return None, utils._json_response(403, {"message": "Acceso denegado: solo puedes actualizar tu propia CLABE"})
    return resolved_customer_id, None


# --- HANDLERS DE ENDPOINTS ---

def _crear_acceso_temporal(customer_id, name: str, email: str, now: str):
    """Crea el registro AUTH con contraseña temporal y avisa por correo.
    Devuelve la contraseña temporal o None si ya había acceso."""
    if not email or utils._get_by_id("AUTH", email):
        return None
    import secrets, string
    alfabeto = string.ascii_uppercase + string.digits
    temp_password = "".join(secrets.choice(alfabeto) for _ in range(10))
    utils._put_entity("AUTH", email, {
        "entityType": "auth", "authId": email, "email": email,
        "customerId": customer_id, "passwordHash": utils._hash_password(temp_password),
        "role": "cliente", "emailVerified": True, "mustChangePassword": True,
        "createdAt": now, "updatedAt": now,
    })
    try:
        from core.email import _email_shell
        frontend = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx").rstrip("/")
        cuerpo = f"""
    <div class="icon">🔑</div>
    <h1 class="title">Tu cuenta en Finding&rsquo;U</h1>
    <p class="lead">Hola <strong>{str(name).split(' ')[0]}</strong>. Te creamos una cuenta para que pidas desde casa y pases a recoger o recibas en tu domicilio.</p>
    <div class="info-box"><p>Correo: <strong>{email}</strong></p><p>Contraseña temporal: <strong>{temp_password}</strong></p></div>
    <p class="lead">Entra con esos datos y cámbiala por una tuya desde tu perfil.</p>
    <a class="btn" href="{frontend}/#/login">Entrar a mi cuenta</a>"""
        utils._send_ses_email(email, "Tu cuenta en Finding'U y tu contraseña temporal",
                              f"Hola {name}. Te creamos una cuenta. Correo: {email}. Contraseña temporal: {temp_password}. Entra en {frontend}/#/login y cámbiala desde tu perfil.",
                              _email_shell(cuerpo))
    except Exception as ex:
        utils._log("customer_access_email_error", "ERROR", customerId=customer_id, error=ex)
    return temp_password


def handle_create_customer(body, headers=None):
    """POST /customers and POST /customers/create"""
    err = utils._require_admin(headers or {}, "customer_add")
    if err:
        return err

    name = str(body.get("name") or "").strip()
    email = utils._normalize_email(body.get("email"))
    if not name:
        return utils._json_response(400, {"message": "name es obligatorio"})

    if email and utils._find_customer_id_by_email(email):
        return utils._json_response(409, {"message": "El correo ya esta registrado"})

    customer_id = body.get("customerId") or int(datetime.now(timezone.utc).timestamp() * 1000)
    leader_id = body.get("leaderId")
    leader_id = utils._customer_entity_id(leader_id) if leader_id not in (None, "") else None
    now = utils._now_iso()
    item = {
        "entityType": "customer",
        "customerId": customer_id,
        "name": name,
        "phone": body.get("phone"),
        "address": body.get("address"),
        "city": body.get("city"),
        "leaderId": leader_id,
        "isAssociate": bool(body.get("isAssociate", True)),
        "canAccessAdmin": bool(body.get("canAccessAdmin", False)),
        "privileges": utils._normalize_privileges(body.get("privileges")),
        "activeBuyer": False,
        "discountRate": utils.D_ZERO,
        "discount": "0%",
        "commissions": utils.D_ZERO,
        "createdAt": now,
        "updatedAt": now,
    }
    if email:
        item["email"] = email
    if body.get("level") is not None:
        item["level"] = body.get("level")
    main = utils._put_entity("CUSTOMER", customer_id, item, created_at_iso=now)
    # Los clientes dados de alta por un admin no aparecían en la búsqueda del
    # panel porque el índice de nombres solo lo escribía el auto-registro.
    utils._upsert_customer_name_index(customer_id, name, email, created_at_iso=now)
    utils._upsert_customer_email_index(customer_id, email)

    # Un cliente dado de alta desde el panel no tenía acceso: sin registro AUTH,
    # sin contraseña y sin correo. "Nunca me llegó nada para entrar." Se crea
    # el acceso con una contraseña temporal y se le avisa por correo.
    temp_password = _crear_acceso_temporal(customer_id, name, email, now) if email else None
    salida = _format_customer_output(main)
    salida["accessCreated"] = bool(temp_password)
    return utils._json_response(201, {"customer": salida})

def handle_get_customer(customer_id, headers=None):
    """GET /customers/{id}"""
    item = utils._get_by_id("CUSTOMER", customer_id)
    if not item:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    err = utils._require_self_or_admin_from_bearer(headers or {}, item.get("customerId", customer_id))
    if err: return err
    return utils._json_response(200, {"customer": _format_customer_output(item)})


def handle_update_privileges(customer_id, body: dict, headers: dict) -> dict:
    """PATCH /customers/{id}/privileges — asigna privilegios de admin/empleado.

    Escritura dedicada, a propósito fuera de `handle_update_customer`: los
    privilegios no deben poder colarse por el PATCH genérico del perfil (que
    acepta al propio cliente como actor). Antes esta ruta delegaba en ese
    handler, que ignoraba el campo: respondía 200 sin escribir nada.

    Las sesiones abiertas conservan su copia de privilegios hasta el próximo
    login (mismo comportamiento que con los empleados).
    """
    cid = utils._customer_entity_id(customer_id)
    if not utils._get_by_id("CUSTOMER", cid):
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    normalized = utils._normalize_privileges(body.get("privileges"))
    updated = utils._update_by_id(
        "CUSTOMER", cid,
        "SET privileges = :p, canAccessAdmin = :a, updatedAt = :u",
        {
            ":p": normalized,
            ":a": bool(body.get("canAccessAdmin", any(normalized.values()))),
            ":u": utils._now_iso(),
        },
    )
    utils._audit_event("customer.privileges.update", headers, body, {"customerId": cid})
    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_update_customer(customer_id, body, headers):
    """PATCH /customers/{id}"""
    cid = utils._customer_entity_id(customer_id)
    existing = utils._get_by_id("CUSTOMER", cid)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    err = utils._require_self_or_admin_from_bearer(headers or {}, existing.get("customerId", cid))
    if err: return err

    updates = ["updatedAt = :u"]
    eav = {":u": utils._now_iso()}
    ean = {}

    # 1. Cambio de Patrocinador (Lógica Crítica)
    leader_changed = False
    if "leaderId" in body:
        new_leader = body["leaderId"]
        if new_leader and _check_leader_cycle(cid, new_leader):
            return utils._json_response(400, {"message": "El cambio generaría un ciclo inválido en la red"})
        leader_changed = existing.get("leaderId") != new_leader
        updates.append("leaderId = :lid")
        eav[":lid"] = new_leader

    # 2. Campos básicos (name es reservada en DynamoDB → alias #name)
    _reserved = {"name"}
    fields = ["name", "phone", "address", "city", "level", "isAssociate", "origin"]
    for f in fields:
        if f in body:
            if f in _reserved:
                ean[f"#{f}"] = f
                updates.append(f"#{f} = :{f}")
            else:
                updates.append(f"{f} = :{f}")
            eav[f":{f}"] = body[f]

    # Correo: la ficha creada desde el panel podía quedar sin correo y no había
    # forma de ponérselo después; al agregarlo se crea el acceso si no existe.
    nuevo_correo = utils._normalize_email(body.get("email")) if "email" in body else None
    correo_cambio = bool(nuevo_correo) and nuevo_correo != str(existing.get("email") or "").strip().lower()
    if correo_cambio:
        otro = utils._find_customer_id_by_email(nuevo_correo)
        if otro and str(otro) != str(existing.get("customerId", cid)):
            return utils._json_response(409, {"message": "El correo ya esta registrado"})
        updates.append("email = :email")
        eav[":email"] = nuevo_correo

    # Seguimiento: "no contactar" y bitácora de contactos (solo se añade, nunca se borra).
    if "doNotContact" in body:
        updates.append("doNotContact = :dnc")
        eav[":dnc"] = bool(body["doNotContact"])
    nota = str(body.get("note") or "").strip()
    if nota:
        actor = utils._extract_actor_from_bearer(headers or {})
        notas = list(existing.get("contactNotes") or [])
        notas.append({"text": nota[:1000], "by": str(actor.get("user_id") or "admin"), "at": utils._now_iso()})
        updates.append("contactNotes = :notes")
        eav[":notes"] = notas[-200:]

    # 3. Direcciones (Upsert en lista)
    if "shippingAddress" in body:
        if "addresses" in body:
            updates.append("addresses = :addr")
            updates.append("shippingAddresses = :addr")
            eav[":addr"] = body["addresses"]

    updated = utils._update_by_id("CUSTOMER", cid, f"SET {', '.join(updates)}", eav, ean or None)
    if correo_cambio:
        try:
            utils._upsert_customer_email_index(existing.get("customerId", cid), nuevo_correo, previous_email=existing.get("email"))
        except Exception as ex:
            utils._log("customer_email_index_error", "ERROR", customerId=cid, error=ex)
        _crear_acceso_temporal(existing.get("customerId", cid), updated.get("name") if isinstance(updated, dict) else existing.get("name"), nuevo_correo, utils._now_iso())

    # Sin esto, renombrar a un cliente lo dejaba indexado bajo su inicial vieja
    # y la búsqueda del panel dejaba de encontrarlo.
    if "name" in body and str(body.get("name") or "").strip() != str(existing.get("name") or "").strip():
        utils._upsert_customer_name_index(
            existing.get("customerId", cid), body.get("name"),
            updated.get("email") if isinstance(updated, dict) else existing.get("email"),
            created_at_iso=existing.get("createdAt"),
            previous_name=existing.get("name"),
        )

    if leader_changed:
        try:
            utils._sync_customer_network_metadata()
            updated = utils._get_by_id("CUSTOMER", cid) or updated
        except Exception as ex:
            utils._log("customer_network_sync_error", "ERROR", customerId=cid, error=ex, detail='action=update_customer')

    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_delete_customer_data(customer_id, body, headers):
    """DELETE /customers/{id} — baja de datos (derechos ARCO).

    En un mes simulado tres personas pidieron formalmente borrar sus datos y
    la gerente no tenía ni botón ni permiso para hacerlo. Los pedidos y las
    comisiones se conservan como registro contable (obligación fiscal), pero
    el cliente deja de ser identificable: nombre, correo, teléfono,
    direcciones, documentos, CLABE y acceso desaparecen, y queda marcado
    "no contactar". Se le avisa por correo antes de perder la dirección.
    """
    err = utils._require_admin(headers, "user_manage_privileges")
    if err: return err
    cid = utils._customer_entity_id(customer_id)
    existing = utils._get_by_id("CUSTOMER", cid)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    if existing.get("deletedAt"):
        return utils._json_response(409, {"message": "Este cliente ya fue dado de baja."})

    correo_anterior = str(existing.get("email") or "").strip().lower()
    nombre_anterior = existing.get("name") or ""
    now = utils._now_iso()
    actor = utils._extract_actor_from_bearer(headers or {})
    motivo = str((body or {}).get("reason") or "solicitud del titular (ARCO)")[:300]

    if correo_anterior:
        try:
            from core.email import _email_shell
            cuerpo = f"""
    <div class="icon">🗂️</div>
    <h1 class="title">Tus datos fueron eliminados</h1>
    <p class="lead">Hola <strong>{nombre_anterior}</strong>. Atendimos tu solicitud: borramos tu nombre, correo, teléfono, direcciones y documentos de nuestra plataforma, y cerramos tu acceso. No volveremos a contactarte.</p>
    <p class="lead">Conservamos únicamente el registro contable de tus compras, sin datos que te identifiquen, por obligación fiscal.</p>"""
            utils._send_ses_email(correo_anterior, "Confirmación de baja de datos · Finding'U",
                                  f"Hola {nombre_anterior}. Atendimos tu solicitud de baja: borramos tus datos personales y cerramos tu acceso. No volveremos a contactarte.",
                                  _email_shell(cuerpo))
        except Exception as ex:
            utils._log("arco_email_error", "ERROR", customerId=cid, error=ex)

    correo_nuevo = f"eliminado+{existing.get('customerId', cid)}@anonimizado.local"
    updated = utils._update_by_id(
        "CUSTOMER", cid,
        "SET #name = :n, email = :e, phone = :ph, addresses = :vacio, shippingAddresses = :vacio, "
        "documents = :vacio, ownDocuments = :vacio, clabeInterbancaria = :ph, bankInstitution = :ph, "
        "doNotContact = :si, deletedAt = :now, deletedBy = :by, deletionReason = :r, updatedAt = :now",
        {":n": "Cliente eliminado", ":e": correo_nuevo, ":ph": None, ":vacio": [], ":si": True,
         ":now": now, ":by": str(actor.get("user_id") or "admin"), ":r": motivo},
        {"#name": "name"},
    )

    # Índices y acceso: que no aparezca en búsquedas ni pueda entrar.
    try:
        utils._upsert_customer_email_index(existing.get("customerId", cid), correo_nuevo, previous_email=correo_anterior)
    except Exception as ex:
        utils._log("arco_email_index_error", "ERROR", customerId=cid, error=ex)
    try:
        utils._upsert_customer_name_index(existing.get("customerId", cid), "Cliente eliminado", correo_nuevo,
                                          created_at_iso=existing.get("createdAt"), previous_name=nombre_anterior)
    except Exception as ex:
        utils._log("arco_name_index_error", "ERROR", customerId=cid, error=ex)
    if correo_anterior:
        auth = utils._get_by_id("AUTH", correo_anterior)
        if auth and auth.get("PK") and auth.get("SK"):
            try:
                utils._table.delete_item(Key={"PK": auth["PK"], "SK": auth["SK"]})
            except Exception as ex:
                utils._log("arco_auth_delete_error", "ERROR", customerId=cid, error=ex)

    utils._audit_event("customer.data_deleted", headers, {"reason": motivo},
                       {"customerId": existing.get("customerId", cid), "previousEmailDomain": correo_anterior.split("@")[-1] if correo_anterior else ""})
    return utils._json_response(200, {"ok": True, "customer": _format_customer_output(updated)})


def handle_update_profile(body, headers):
    """PATCH /customers/profile — el customerId se obtiene del token Bearer"""
    actor = utils._extract_actor_from_bearer(headers)
    if not actor.get("user_id"):
        return utils._json_response(401, {"message": "No autenticado"})
    cid = utils._customer_entity_id(actor["user_id"])
    existing = utils._get_by_id("CUSTOMER", cid)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    # DynamoDB reserved keywords must be aliased via ExpressionAttributeNames
    _reserved = {"name"}
    updates = ["updatedAt = :u"]
    eav = {":u": utils._now_iso()}
    ean = {}

    for field in ("name", "phone", "rfc", "curp"):
        if field in body:
            if field in _reserved:
                alias = f"#{field}"
                ean[alias] = field
                updates.append(f"{alias} = :{field}")
            else:
                updates.append(f"{field} = :{field}")
            eav[f":{field}"] = str(body[field]).strip()

    updated = utils._update_by_id("CUSTOMER", cid, f"SET {', '.join(updates)}", eav, ean or None)

    # El rename desde el propio perfil también debe refrescar el índice de
    # búsqueda por nombre; si no, el panel de admin sigue encontrando (o
    # dejando de encontrar) al cliente por su nombre viejo.
    if "name" in body and str(body.get("name") or "").strip() != str(existing.get("name") or "").strip():
        utils._upsert_customer_name_index(
            existing.get("customerId", cid), body.get("name"),
            updated.get("email") if isinstance(updated, dict) else existing.get("email"),
            created_at_iso=existing.get("createdAt"),
            previous_name=existing.get("name"),
        )

    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_update_clabe(customer_id, body, headers):
    """POST /customers/{id}/clabe  o  POST /customers/clabe (customerId en body)"""
    customer_id, err = _resolve_clabe_customer_id(customer_id, body, headers)
    if err:
        return err

    clabe = str(body.get("clabe", "")).strip()
    if len(clabe) != 18 or not clabe.isdigit():
        return utils._json_response(400, {"message": "CLABE debe tener 18 dígitos numéricos"})

    update_expr = "SET clabe = :c, clabeInterbancaria = :c, updatedAt = :u"
    eav = {":c": clabe, ":u": utils._now_iso()}

    bank_institution = str(body.get("bankInstitution", "")).strip()
    if bank_institution:
        update_expr += ", bankInstitution = :bi"
        eav[":bi"] = bank_institution

    utils._update_by_id("CUSTOMER", customer_id, update_expr, eav)

    return utils._json_response(200, {"ok": True, "clabeLast4": clabe[-4:]})


def handle_add_document(customer_id, body, headers):
    """POST /customers/{id}/documents  — Admin sube y liga un documento al cliente.
    Acepta contentBase64 (subida directa) o assetId (asset ya existente)."""
    err = utils._require_admin(headers or {}, "access_screen_customers")
    if err: return err
    doc_name = body.get("name", "Documento")
    content_b64 = body.get("contentBase64")

    if content_b64:
        content_type = str(body.get("contentType", "application/octet-stream")).strip()
        file_name = str(body.get("fileName", "documento")).strip() or "documento"
        try:
            asset = _upload_document_s3(file_name, content_b64, content_type, prefix=f"docs-admin/{customer_id}")
        except ValueError:
            return utils._json_response(400, {"message": "contentBase64 inválido"})
        except Exception as e:
            print(f"[S3_UPLOAD_ERROR] {e}")
            return utils._json_response(500, {"message": "Error al subir el archivo"})
        doc_entry = {
            "documentId": f"DOC-{utils.uuid.uuid4().hex[:8].upper()}",
            "assetId": asset["assetId"],
            "name": doc_name,
            "url": asset["url"],
            "contentType": content_type,
            "uploadedAt": utils._now_iso(),
        }
    else:
        asset_id = body.get("assetId")
        asset = utils._get_by_id("ASSET", asset_id)
        if not asset:
            return utils._json_response(404, {"message": "El archivo (asset) no existe en S3"})
        doc_entry = {
            "documentId": f"DOC-{utils.uuid.uuid4().hex[:8].upper()}",
            "assetId": asset_id,
            "name": doc_name,
            "url": asset.get("url"),
            "contentType": asset.get("contentType"),
            "uploadedAt": utils._now_iso(),
        }

    utils._update_by_id(
        "CUSTOMER", customer_id,
        "SET documents = list_append(if_not_exists(documents, :empty), :d), updatedAt = :u",
        {":empty": [], ":d": [doc_entry], ":u": utils._now_iso()},
    )

    updated = utils._get_by_id("CUSTOMER", customer_id)
    return utils._json_response(201, {"customer": _format_customer_output(updated)})


def handle_upload_own_document(body, headers):
    """POST /profile/documents  — El cliente sube su propio documento (Constancia, INE, CURP, etc.)

    Payload esperado:
      docType        : str   — clave del tipo (ej: "constancia", "ine", "curp")
      docLabel       : str   — nombre legible del documento
      contentBase64  : str   — contenido del archivo en base64
      contentType    : str   — MIME type (ej: "application/pdf")
      fileName       : str   — nombre original del archivo
    """
    headers = headers or {}
    actor = utils._extract_actor_from_bearer(headers)
    user_id = actor.get("user_id")
    if not user_id:
        return utils._json_response(401, {"message": "No autenticado"})

    doc_type  = str(body.get("docType", "")).strip()
    doc_label = str(body.get("docLabel", doc_type)).strip() or "Documento"
    content_b64 = str(body.get("contentBase64", "")).strip()
    content_type = str(body.get("contentType", "application/octet-stream")).strip()
    file_name = str(body.get("fileName", f"{doc_type}.bin")).strip()

    if not doc_type:
        return utils._json_response(400, {"message": "docType requerido"})
    if not content_b64:
        return utils._json_response(400, {"message": "contentBase64 requerido"})

    # 1. Subir a S3
    try:
        asset = _upload_document_s3(file_name, content_b64, content_type, prefix=f"docs-cliente/{user_id}")
    except ValueError:
        return utils._json_response(400, {"message": "Contenido base64 inválido"})
    except Exception as e:
        print(f"[S3_UPLOAD_ERROR] {e}")
        return utils._json_response(500, {"message": "Error al subir el archivo"})

    now = utils._now_iso()
    new_doc = {
        "documentId": f"ODOC-{utils.uuid.uuid4().hex[:8].upper()}",
        "assetId": asset["assetId"],
        "docType": doc_type,
        "name": doc_label,
        "url": asset["url"],
        "contentType": content_type,
        "uploadedAt": now,
    }

    # 2. Obtener documentos propios actuales y reemplazar el del mismo tipo
    existing = utils._get_by_id("CUSTOMER", user_id)
    if not existing:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    own_docs = [d for d in (existing.get("ownDocuments") or []) if d.get("docType") != doc_type]
    own_docs.append(new_doc)

    utils._update_by_id(
        "CUSTOMER", user_id,
        "SET ownDocuments = :od, updatedAt = :u",
        {":od": own_docs, ":u": now},
    )

    updated = utils._get_by_id("CUSTOMER", user_id)
    return utils._json_response(200, {"customer": _format_customer_output(updated)})


def handle_get_network(customer_id, query):
    """GET /network/{id} - Construye el árbol de profundidad N"""
    depth = int(query.get("depth", 3))
    root_customer = utils._get_by_id("CUSTOMER", customer_id)
    if not root_customer:
        return utils._json_response(404, {"message": "Usuario no encontrado en la red"})

    all_customers, _ = _load_customer_network_scope(root_customer)
    month_key = utils._month_key()
    month_states = _load_month_states([item.get("customerId") for item in all_customers], month_key)
    tree = _build_network_tree_with_month(
        str(root_customer.get("customerId")),
        month_key,
        all_customers,
        {},
        max_depth=depth,
        month_states=month_states,
    )
    return utils._json_response(200, {"network": tree})


def handle_rebuild_network_tree(headers):
    """POST /customers/network-tree/rebuild - Reconstuye el arbol persistido de red."""
    err = utils._require_admin(headers or {}, "access_screen_customers")
    if err:
        return err
    result = utils._sync_customer_network_metadata()
    return utils._json_response(200, {"ok": True, "networkTree": result})


def handle_customer_dashboard(headers: dict) -> dict:
    """GET /customers/dashboard — dashboard del socio autenticado.

    Los bloques que antes estaban en línea aquí (resumen de comisiones, bonos
    del mes, caché del dashboard) viven en `dashboard_common` porque el
    dashboard legacy los repetía casi palabra por palabra.
    """
    timer = _DashboardTimer("unknown")
    actor = utils._extract_actor_from_bearer(headers or {})
    if not actor.get("user_id"):
        timer.mark("auth_missing")
        return utils._json_response(401, {"message": "No autenticado"})

    customer_id = utils._customer_entity_id(actor["user_id"])
    timer = _DashboardTimer(customer_id)
    customer = utils._get_by_id("CUSTOMER", customer_id)
    if not customer or not isinstance(customer, dict):
        timer.mark("customer_missing")
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    timer.mark("load_customer")

    app_cfg = utils._load_app_config()
    cfg = app_cfg.get("rewards") or {}
    bonus_cfg = app_cfg.get("bonuses") or {}
    month_key = utils._month_key()
    prev_month_key = _prev_month_key()
    timer.mark("load_config", monthKey=month_key, prevMonthKey=prev_month_key)

    # Solo el socio y su descendencia (árbol persistido + BatchGetItem).
    customers_raw, network_scope_meta = _load_customer_network_scope(customer)
    timer.mark("load_network_scope", **network_scope_meta)
    month_states = _load_month_states(
        [item.get("customerId") for item in customers_raw], month_key
    )
    timer.mark("load_month_states", states=len(month_states))

    tree = _build_network_tree_with_month(
        str(customer.get("customerId")), month_key, customers_raw, cfg,
        max_depth=utils._max_network_levels(), month_states=month_states,
    )
    computed_network = _network_members_from_tree(tree, max_rows=30)
    computed_goals = _build_goals(customer, tree, customers_raw, cfg,
                                  bonus_cfg=bonus_cfg, month_states=month_states)
    buy_again_ids = _compute_buy_again_ids(customer, utils._query_bucket("PRODUCT"))
    active_notifications = _active_notifications_for_customer(customer.get("customerId"))
    timer.mark("compute_dashboard_data", scopeCustomers=len(customers_raw),
               networkMembers=len(computed_network), goals=len(computed_goals),
               notifications=len(active_notifications))

    cid = str(customer.get("customerId", ""))
    mxn_per_vp = utils._mxn_per_vp()
    my_net = float(utils._to_decimal(
        _get_month_state(cid, month_key, month_states).get("netVolume", 0)
    ))
    # Misma regla que el motor y que el resto del panel: netVP del catálogo
    # si existe. Esta ruta seguía convirtiendo pesos ÷ tarifa y el socio veía
    # "VP 19.2" debajo de "VG 20" en la misma tarjeta.
    vp_val = dashboard_common._state_vp_dash(_get_month_state(cid, month_key, month_states), mxn_per_vp)
    vg_val = _calc_vg_from_tree(tree, mxn_per_vp)
    rank_val = _get_rank_dash(vg_val, bonus_cfg.get("rankThresholds") or [], vp=vp_val)
    timer.mark("compute_rank_metrics", vp=round(vp_val, 2), vg=round(vg_val, 2), rank=rank_val)

    bonus_awards = dashboard_common.load_bonus_awards(cid, month_key)
    commission_summary = dashboard_common.build_commission_summary(
        customer, month_key, prev_month_key,
        payout_day=int(utils._to_decimal(cfg.get("payoutDay", 10))),
    )
    dashboard_common.persist_dashboard_cache(
        customer, computed_goals, computed_network, buy_again_ids
    )
    timer.mark("load_commissions", awards=len(bonus_awards))

    discount_rate = utils._to_decimal(customer.get("discountRate"))
    response = utils._json_response(200, {
        "isGuest": False,
        "settings": {
            "cutoffDay": 25,
            "cutoffHour": 23,
            "cutoffMinute": 59,
            "userCode": str(customer.get("referralCode")
                            or customer.get("customerId") or "").strip().upper(),
            "networkGoal": 300,
            "freeShippingMin": float(utils._to_decimal((utils._load_app_config().get("shipping") or {}).get("freeShippingMin") or 0)),
        },
        "customer": _normalize_dashboard_customer(customer),
        "user": {
            "discountPercent": int((discount_rate * 100).quantize(utils.D_ONE)) if discount_rate else 0,
            "discountActive": bool(customer.get("activeBuyer") or discount_rate > 0),
        },
        "sponsor": _find_effective_sponsor(customer),
        "goals": computed_goals,
        "featured": [],
        "campaigns": [],
        "notifications": active_notifications,
        "networkMembers": computed_network,
        "buyAgainIds": buy_again_ids,
        "commissions": commission_summary,
        "vp": round(vp_val, 2),
        # Consumo propio del mes en pesos: el panel pintaba "$0" en el nodo
        # raíz de la red porque no tenía de dónde sacarlo.
        "myNetSpend": round(float(my_net), 2),
        "vg": round(vg_val, 2),
        "rank": rank_val,
        "bonuses": bonus_awards,
    })
    timer.mark("complete", status="ok")
    return response



# --- LAMBDA HANDLER ---

def lambda_handler(event, context):
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return utils._cors_preflight_response()
    request = utils._http_request(event)
    method = request.method
    body, query, headers = request.body, request.query, request.headers
    segments = request.segments

    if not segments:
        return utils._json_response(200, {"service": "customer-profile"})

    try:
        root = segments[0]

        # ── GET /customers/getall  (lista paginada para admin) ─────────
        if root == "customers" and len(segments) == 2 and segments[1] == "getall" and method == "GET":
            err = utils._require_admin(headers, "access_screen_customers")
            if err: return err
            search = (query.get("search") or "").strip().lower()
            try:
                limit = max(1, min(int(query.get("limit", 50)), 200))
            except (TypeError, ValueError):
                limit = 50

            if search:
                # Índice por nombre `REF#NOMBRE#<letra>`, leyendo TODAS sus
                # páginas (antes se quedaba en la primera y omitía coincidencias).
                letter = search[0].upper()
                try:
                    name_refs = utils._query_customer_name_index(letter)
                    matched_ids = [
                        r["customerId"] for r in name_refs
                        if search in str(r.get("nameLower") or "").lower()
                    ]
                except Exception:
                    matched_ids = []

                if matched_ids:
                    # BatchGetItem en vez de un _get_by_id (2 GetItem) por resultado.
                    items = utils._batch_get_entities("CUSTOMER", matched_ids)
                else:
                    # Sin coincidencias en el índice: barrido completo con filtro.
                    items = [
                        c for c in utils._query_bucket("CUSTOMER")
                        if search in str(c.get("name") or "").lower()
                        or search in str(c.get("email") or "").lower()
                    ]

                total = len(items)
                page = items[:limit]
                return utils._json_response(200, {
                    "customers": _con_comisiones([_format_customer_output(c) for c in page]),
                    "total": total,
                    "count": len(page),
                    "nextToken": None,
                    "hasMore": False,
                })

            # Listado sin búsqueda: paginación real por ExclusiveStartKey.
            # Antes se leía la colección CUSTOMER entera y se cortaba en memoria,
            # así que cada página costaba lo mismo que la tabla completa.
            page, next_token = _query_customers_page(limit, query.get("nextToken"))
            return utils._json_response(200, {
                "customers": _con_comisiones([_format_customer_output(c) for c in page]),
                "count": len(page),
                "nextToken": next_token,
                "hasMore": bool(next_token),
            })

        # ── /customers/... ─────────────────────────────────────────────
        if root == "customers" and method == "POST" and (
            len(segments) == 1 or (len(segments) == 2 and segments[1] == "create")
        ):
            return handle_create_customer(body, headers)

        if root == "customers" and len(segments) > 1:
            target_id = segments[1]

            if target_id == "network-tree" and len(segments) == 3 and segments[2] == "rebuild" and method == "POST":
                return handle_rebuild_network_tree(headers)
            
            if method == "GET":
                if segments[1] == "dashboard":
                    return handle_customer_dashboard(headers)

            if target_id == "sponsor" and len(segments) == 3 and method == "GET":
                return handle_get_public_sponsor(segments[2])

            # POST /customers/documents  (cliente sube su propio doc desde su sesión)
            if target_id == "documents" and len(segments) == 2 and method == "POST":
                return handle_upload_own_document(body, headers)

            # PATCH /customers/profile  (customerId desde el token Bearer)
            if target_id == "profile" and len(segments) == 2 and method == "PATCH":
                return handle_update_profile(body, headers)

            # POST /customers/clabe  (customerId en el body)
            if target_id == "clabe" and method == "POST":
                return handle_update_clabe("clabe", body, headers)

            if len(segments) == 2:  # /customers/{id}
                if method == "GET":   return handle_get_customer(target_id, headers)
                if method == "PATCH": return handle_update_customer(target_id, body, headers)
                if method == "DELETE" and str(target_id).isdigit():
                    return handle_delete_customer_data(target_id, body, headers)

            if len(segments) == 3:
                sub = segments[2]
                # POST /customers/{id}/clabe
                if sub == "clabe" and method == "POST":
                    return handle_update_clabe(target_id, body, headers)
                # POST /customers/{id}/documents  (admin liga documento)
                if sub == "documents" and method == "POST":
                    return handle_add_document(target_id, body, headers)
                # PATCH /customers/{id}/privileges  (admin only)
                if sub == "privileges" and method == "PATCH":
                    err = utils._require_admin(headers, "user_manage_privileges")
                    if err: return err
                    return handle_update_privileges(target_id, body, headers)

        # ── /network/{id} ──────────────────────────────────────────────
        if root == "network" and len(segments) > 1:
            return handle_get_network(segments[1], query)

        return utils._json_response(404, {"message": "Ruta no encontrada en Customer Service"})

    except Exception as e:
        utils._log_error("customer_unhandled_error", e)
        return utils._json_response(500, {"message": "Error interno", "error": str(e)})
