import json
import boto3
import random
import core_utils as utils # Importado desde la Lambda Layer
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")

_EMAIL_BASE_CSS = """
body { margin:0; padding:0; background-color:#F9F7F2; font-family:'Segoe UI',Arial,sans-serif; }
.wrap { width:100%; max-width:600px; margin:0 auto; padding:24px 16px; }
.card { background:#ffffff; border-radius:24px; padding:40px 36px; text-align:center; border:1px solid #e8e3d8; }
.logo { margin-bottom:24px; }
.icon { font-size:48px; margin-bottom:8px; }
.title { color:#2D3436; font-family:Georgia,serif; font-size:26px; font-weight:bold; margin:0 0 16px; }
.lead { color:#636e72; line-height:1.7; font-size:15px; margin:0 0 20px; }
.benefit-item { text-align:left; margin-bottom:14px; padding:14px 16px; background:#FFFDF5; border-radius:14px; display:flex; align-items:flex-start; gap:12px; }
.benefit-icon { font-size:20px; flex-shrink:0; margin-top:2px; }
.benefit-body strong { display:block; color:#2D3436; font-size:14px; }
.benefit-body span { color:#636e72; font-size:13px; }
.info-box { background:#f9f9f9; border-radius:14px; padding:18px 20px; margin:20px 0; text-align:left; }
.info-box p { margin:0 0 6px; color:#333; font-size:14px; }
.info-box p:last-child { margin-bottom:0; }
.btn { background:#D4AF37; color:#333 !important; padding:14px 32px; border-radius:50px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:20px; font-size:15px; }
.otp-box { display:inline-block; background:#FFFDF5; border:2px solid #D4AF37; border-radius:16px; padding:16px 40px; margin:20px 0; font-size:36px; font-weight:bold; letter-spacing:10px; color:#2D3436; }
.divider { border:none; border-top:1px solid #eee; margin:28px 0; }
.footer { font-size:12px; color:#aaa; margin-top:24px; }
"""


def _email_shell(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_EMAIL_BASE_CSS}</style></head>
<body>
<div class="wrap">
  <div class="logo" style="text-align:center">
    <img src="https://www.findingu.com.mx/Logo-colores.svg" alt="Finding'u" width="140">
  </div>
  <div class="card">
    {body_html}
    <hr class="divider">
    <div class="footer">&copy; 2026 Finding&rsquo;U &nbsp;&bull;&nbsp; Nutrici&oacute;n que te impulsa</div>
  </div>
</div>
</body></html>"""


def _build_activation_email(name: str, confirmation_url: str) -> tuple:
    url = confirmation_url
    body = f"""
    <div class="icon">✉️</div>
    <h1 class="title">Activa tu cuenta de Finding&rsquo;U</h1>
    <p class="lead">Hola <strong>{name}</strong>, solo falta confirmar tu correo electrónico para activar tu cuenta.</p>

    <div class="benefit-item">
      <span class="benefit-icon">✅</span>
      <div class="benefit-body">
        <strong>Activa tu acceso</strong>
        <span>Confirma tu correo y termina el alta de tu cuenta.</span>
      </div>
    </div>

    <div class="benefit-item">
      <span class="benefit-icon">🔒</span>
      <div class="benefit-body">
        <strong>Protege tu registro</strong>
        <span>El enlace verifica que el correo realmente te pertenece.</span>
      </div>
    </div>

    <div class="benefit-item">
      <span class="benefit-icon">⏳</span>
      <div class="benefit-body">
        <strong>Enlace temporal</strong>
        <span>Por seguridad, este enlace de activación expira automáticamente.</span>
      </div>
    </div>

    <a href="{url}" class="btn">Activar mi cuenta &rarr;</a>
    """
    html = _email_shell(body)
    text = f"Hola {name}, activa tu cuenta de Finding'U desde este enlace: {url}"
    return "Activa tu cuenta de Finding'U", text, html


def _build_email_confirmation_url(token: str) -> str:
    base = FRONTEND_URL.rstrip("/")
    return f"{base}/#/verificar-email?token={quote(token)}"


def _create_email_confirmation(email: str, customer_id) -> str:
    token = "email-confirm-" + utils.uuid.uuid4().hex
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    utils._put_entity("EMAIL_CONFIRMATION", token, {
        "entityType": "emailConfirmation",
        "token": token,
        "email": email,
        "customerId": customer_id,
        "expiresAt": expires,
        "used": False,
    })
    return token


def _build_password_recovery_email(otp: str) -> tuple:
    body = f"""
    <div class="icon">🔑</div>
    <h1 class="title">¿Olvidaste tu contraseña?</h1>
    <p class="lead">Recibimos una solicitud para restablecer la contraseña de tu cuenta.<br>
    Usa el siguiente código para continuar:</p>

    <div class="otp-box">{otp}</div>

    <p style="font-size:13px;color:#999;margin-top:8px;">El código expira en 15 minutos.</p>
    <p style="font-size:13px;color:#999;margin-top:12px;">
      Si no solicitaste este cambio puedes ignorar este correo.
    </p>
    """
    html = _email_shell(body)
    text = f"Tu código de recuperación Finding'U es: {otp}. Expira en 15 minutos."
    return "Recupera tu contraseña — Finding'U", text, html


def _build_new_network_member_email(
    leader_name: str,
    new_name: str,
    new_email: str,
    new_phone: str,
    dashboard_url: str = "",
) -> tuple:
    url = dashboard_url or FRONTEND_URL + "/dashboard"
    phone_row = f'<p><strong>Teléfono:</strong> {new_phone}</p>' if new_phone else ""
    body = f"""
    <div class="icon">🚀</div>
    <h1 class="title">¡Tu red está creciendo!</h1>
    <p class="lead">Hola <strong>{leader_name}</strong>,<br>
    <strong>{new_name}</strong> se ha unido a tu red de beneficios.</p>

    <div class="info-box">
      <p><strong>Datos de contacto:</strong></p>
      <p><strong>Nombre:</strong> {new_name}</p>
      <p><strong>Correo:</strong> <a href="mailto:{new_email}" style="color:#D4AF37">{new_email}</a></p>
      {phone_row}
    </div>

    <p class="lead" style="font-size:14px;">
      Cada nuevo miembro te acerca más a tus metas mensuales y aumenta tus bonos de red.
      ¡Apóyalo para que se active y multiplica tus beneficios!
    </p>

    <a href="{url}" class="btn">Ver mi red &rarr;</a>
    """
    html = _email_shell(body)
    text = (
        f"Hola {leader_name}, {new_name} ({new_email}) se unió a tu red en Finding'U. "
        f"Ve tu red: {url}"
    )
    return "¡Alguien se unió a tu red! — Finding'U", text, html

# --- LÓGICA DE NEGOCIO ---

def handle_login(body):
    """POST /auth/login"""
    identifier = (body.get("email") or body.get("username", "")).strip().lower()
    password = body.get("password")

    if not identifier or not password:
        return utils._json_response(401, {"message": "Credenciales incompletas"})

    # 1. Usuarios Demo (Compatibilidad)
    demo_users = [
        {"u": "admin", "p": "admin123", "role": "admin", "id": "admin-001", "name": "Admin"},
        {"u": "cliente", "p": "cliente123", "role": "cliente", "id": "client-001", "name": "Valeria Torres"}
    ]
    for d in demo_users:
        if (identifier == d["u"] or identifier == f"{d['u']}@demo.local") and password == d["p"]:
            token = "demo-token-" + utils.uuid.uuid4().hex[:16]
            utils._put_entity("SESSION", token, {
                "entityType": "session",
                "sessionId": token,
                "userId": str(d["id"]),
                "role": d["role"],
                "privileges": {},
            })
            return utils._json_response(200, {"token": token, "user": {
                "userId": d["id"], "name": d["name"], "role": d["role"], "canAccessAdmin": (d["role"] == "admin")
            }})

    # 2. Buscar en tabla AUTH
    auth = utils._get_by_id("AUTH", identifier)
    pass_hash = utils._hash_password(str(password))

    if not auth:
        # Fallback: Buscar cliente por email para crear registro AUTH si existe passHash antiguo
        customer = next((c for c in utils._query_bucket("CUSTOMER") 
                        if utils._normalize_email(c.get("email")) == identifier), None)
        if customer and customer.get("passwordHash") == pass_hash:
            auth = utils._put_entity("AUTH", identifier, {
                "entityType": "auth", "authId": identifier, "email": identifier,
                "customerId": customer.get("customerId"), "passwordHash": pass_hash, "role": "cliente"
            })
        else:
            return utils._json_response(401, {"message": "Credenciales invalidas"})

    if auth.get("passwordHash") != pass_hash:
        return utils._json_response(401, {"message": "Credenciales invalidas"})

    if auth.get("emailVerified") is False:
        return utils._json_response(403, {"message": "Confirma tu cuenta desde tu correo electronico para iniciar sesion."})

    # 3. Determinar Perfil
    user_id = auth.get("employeeId") or auth.get("customerId")
    entity_type = "EMPLOYEE" if auth.get("employeeId") else "CUSTOMER"
    profile = utils._get_by_id(entity_type, user_id)

    if not profile:
        return utils._json_response(401, {"message": "Perfil no encontrado"})

    token = "session-token-" + utils.uuid.uuid4().hex[:16]
    utils._put_entity("SESSION", token, {
        "entityType": "session",
        "sessionId": token,
        "userId": str(user_id),
        "role": auth.get("role"),
        "authId": auth.get("authId") or identifier,
        "privileges": utils._normalize_privileges(profile.get("privileges")),
    })

    return utils._json_response(200, {
        "token": token,
        "user": {
            "userId": str(user_id),
            "name": profile.get("name"),
            "role": auth.get("role"),
            "canAccessAdmin": bool(profile.get("canAccessAdmin")),
            "privileges": utils._normalize_privileges(profile.get("privileges")),
            "isEmployee": (entity_type == "EMPLOYEE")
        }
    })

def handle_create_account(body):
    """POST /crearcuenta"""
    email = utils._normalize_email(body.get("email"))
    password = body.get("password")
    name = body.get("name", "").strip()

    if not email or not password or not name:
        return utils._json_response(400, {"message": "Faltan datos obligatorios"})

    if utils._get_by_id("AUTH", email):
        return utils._json_response(409, {"message": "El correo ya está registrado"})

    # Crear Customer ID (Timestamp)
    customer_id = int(datetime.now(timezone.utc).timestamp() * 1000)
    pass_hash = utils._hash_password(str(password))
    now = utils._now_iso()

    # Resolver patrocinador
    leader_id = body.get("leaderId") or body.get("referralToken")
    
    customer_item = {
        "entityType": "customer", "customerId": customer_id, "name": name,
        "email": email, "phone": body.get("phone"), "leaderId": leader_id,
        "isAssociate": True, "canAccessAdmin": False, "createdAt": now
    }
    utils._put_entity("CUSTOMER", customer_id, customer_item)

    # Índice por nombre para búsqueda rápida paginada: PK="REF#NOMBRE#{letra}" SK="{createdAt}#{customerId}"
    try:
        name_letter = (name[0] if name else "?").upper()
        utils._table.put_item(Item={
            "PK": f"REF#NOMBRE#{name_letter}",
            "SK": f"{now}#{customer_id}",
            "customerId": customer_id,
            "nameLower": name.lower(),
            "email": email,
            "createdAt": now,
        })
    except Exception as ex:
        print(f"[CUSTOMER_NAME_INDEX_ERROR] customerId={customer_id} error={ex}")

    try:
        utils._sync_customer_network_metadata()
    except Exception as ex:
        print(f"[CUSTOMER_NETWORK_SYNC_ERROR] action=create_account customerId={customer_id} error={ex}")

    utils._put_entity("AUTH", email, {
        "entityType": "auth", "authId": email, "email": email,
        "customerId": customer_id, "passwordHash": pass_hash, "role": "cliente", "emailVerified": False
    })

    confirmation_token = _create_email_confirmation(email, customer_id)
    confirmation_url = _build_email_confirmation_url(confirmation_token)

    # Correo de activacion al nuevo usuario
    subj, txt, html = _build_activation_email(name, confirmation_url)
    utils._send_ses_email(email, subj, txt, html)

    # Notificar al promotor/líder que alguien se unió a su red
    if leader_id:
        try:
            try:
                lid = int(leader_id)
            except (ValueError, TypeError):
                lid = leader_id
            leader = utils._get_by_id("CUSTOMER", lid)
            if leader and leader.get("email"):
                l_subj, l_txt, l_html = _build_new_network_member_email(
                    leader_name=str(leader.get("name") or ""),
                    new_name=name,
                    new_email=email,
                    new_phone=str(body.get("phone") or ""),
                )
                utils._send_ses_email(leader.get("email"), l_subj, l_txt, l_html)
        except Exception as ex:
            print(f"[EMAIL_LEADER_ERROR] {ex}")

    return utils._json_response(201, {"customerId": customer_id, "ok": True})

def handle_verify_email(body):
    """POST /auth/verify-email"""
    token = str(body.get("token") or "").strip()
    if not token:
        return utils._json_response(400, {"message": "Falta el token de confirmacion"})

    record = utils._get_by_id("EMAIL_CONFIRMATION", token)
    if not record:
        return utils._json_response(404, {"message": "El enlace es invalido o ya expiro."})

    if record.get("used"):
        return utils._json_response(409, {"message": "Este enlace de activacion ya fue utilizado."})

    expires_at_raw = str(record.get("expiresAt") or "").strip()
    try:
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    except ValueError:
        expires_at = None

    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        return utils._json_response(410, {"message": "El enlace de activacion ya expiro."})

    email = utils._normalize_email(record.get("email"))
    customer_id = record.get("customerId")
    now = utils._now_iso()

    auth = utils._get_by_id("AUTH", email)
    if not auth:
        return utils._json_response(404, {"message": "No encontramos la cuenta asociada a este enlace."})

    utils._update_by_id(
        "AUTH",
        email,
        "SET emailVerified = :verified, updatedAt = :updatedAt",
        {":verified": True, ":updatedAt": now},
    )

    if customer_id is not None and utils._get_by_id("CUSTOMER", customer_id):
        utils._update_by_id(
            "CUSTOMER",
            customer_id,
            "SET emailVerified = :verified, emailConfirmedAt = :confirmedAt, updatedAt = :updatedAt",
            {":verified": True, ":confirmedAt": now, ":updatedAt": now},
        )

    utils._update_by_id(
        "EMAIL_CONFIRMATION",
        token,
        "SET used = :used, usedAt = :usedAt, updatedAt = :updatedAt",
        {":used": True, ":usedAt": now, ":updatedAt": now},
    )

    return utils._json_response(200, {"ok": True, "message": "Correo verificado correctamente."})

def handle_resend_email_confirmation(body):
    """POST /auth/resend-email-confirmation"""
    email = utils._normalize_email(body.get("email"))
    if not email:
        return utils._json_response(400, {"message": "Ingresa tu correo electronico."})

    auth = utils._get_by_id("AUTH", email)
    if not auth:
        return utils._json_response(404, {"message": "No encontramos una cuenta registrada con ese correo."})

    if auth.get("emailVerified") is True:
        return utils._json_response(409, {"message": "La cuenta ya fue confirmada. Ya puedes iniciar sesion."})

    customer_id = auth.get("customerId")
    customer = utils._get_by_id("CUSTOMER", customer_id) if customer_id is not None else None
    customer_name = str((customer or {}).get("name") or auth.get("email") or "")

    confirmation_token = _create_email_confirmation(email, customer_id)
    confirmation_url = _build_email_confirmation_url(confirmation_token)
    subj, txt, html = _build_activation_email(customer_name, confirmation_url)
    utils._send_ses_email(email, subj, txt, html)

    return utils._json_response(200, {
        "ok": True,
        "message": "Te reenviamos el correo de confirmacion. Revisa tu bandeja de entrada."
    })

def handle_password_recovery(body):
    """POST /auth/password/recovery"""
    email = utils._normalize_email(body.get("email"))
    auth = utils._get_by_id("AUTH", email)
    
    if not auth:
        return utils._json_response(200, {"message": "Si el correo existe, enviamos un código"})

    otp = "".join(random.choices("0123456789", k=6))
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    
    utils._put_entity("PASSWORD_RESET", email, {
        "entityType": "passwordReset", "email": email, 
        "otpHash": utils._hash_password(otp), "expiresAt": expires, "used": False
    })

    subj, txt, html = _build_password_recovery_email(otp)
    utils._send_ses_email(email, subj, txt, html)
    return utils._json_response(200, {"ok": True, "message": "Código enviado"})

def handle_password_reset(body):
    """POST /auth/password/reset"""
    email = utils._normalize_email(body.get("email"))
    otp = body.get("otp", "").strip()
    new_password = body.get("password")

    reset_rec = utils._get_by_id("PASSWORD_RESET", email)
    if not reset_rec or reset_rec.get("used") or utils._hash_password(otp) != reset_rec.get("otpHash"):
        return utils._json_response(401, {"message": "Código inválido o expirado"})

    # Actualizar password en AUTH
    pass_hash = utils._hash_password(str(new_password))
    utils._update_by_id("AUTH", email, "SET passwordHash = :p, updatedAt = :u", {":p": pass_hash, ":u": utils._now_iso()})
    
    # Marcar OTP como usado
    utils._update_by_id("PASSWORD_RESET", email, "SET used = :t", {":t": True})

    return utils._json_response(200, {"ok": True, "message": "Contraseña actualizada"})

def handle_change_password(body, headers):
    """POST /auth/changepassword — Requiere Bearer token; obtiene customerId desde la sesión."""
    actor = utils._extract_actor_from_bearer(headers)
    if not actor.get("user_id"):
        return utils._json_response(401, {"message": "No autenticado"})

    customer_id = str(actor["user_id"])
    current_password = body.get("currentPassword")
    new_password = body.get("newPassword")

    if not current_password or not new_password:
        return utils._json_response(400, {"message": "currentPassword y newPassword son requeridos"})
    if len(str(new_password)) < 8:
        return utils._json_response(400, {"message": "La nueva contraseña debe tener al menos 8 caracteres"})

    # Buscar registro AUTH por customerId
    auth_records = utils._query_bucket("AUTH")
    auth = next((r for r in auth_records if str(r.get("customerId")) == customer_id), None)
    if not auth:
        return utils._json_response(404, {"message": "Cuenta no encontrada"})

    # Validar contraseña actual
    if auth.get("passwordHash") != utils._hash_password(str(current_password)):
        return utils._json_response(401, {"message": "La contraseña actual es incorrecta"})

    # Actualizar contraseña
    email = auth.get("email") or auth.get("authId")
    utils._update_by_id("AUTH", email, "SET passwordHash = :p, updatedAt = :u", {
        ":p": utils._hash_password(str(new_password)),
        ":u": utils._now_iso()
    })

    return utils._json_response(200, {"ok": True, "message": "Contraseña actualizada"})


def handle_get_referrer(referrer_id):
    """GET /referrer/{id}"""
    # Intentar lookup por ID numérico o string
    try:
        rid = int(referrer_id)
    except:
        rid = referrer_id

    customer = utils._get_by_id("CUSTOMER", rid)
    if not customer:
        return utils._json_response(200, {"referrer": {
            "name": "FindingU",
            "email": "coach@findingu.com.mx",
            "phone": "+52 1 55 1498 2351",
            "isDefault": True,
        }})

    return utils._json_response(200, {"referrer": {
        "name": customer.get("name"), "phone": customer.get("phone"), 
        "email": customer.get("email"), "isDefault": False
    }})

# --- GESTIÓN DE EMPLEADOS ---

def handle_employees(method, body, employee_id=None, headers=None):
    """GET, POST, PATCH /employees"""
    now = utils._now_iso()

    if method == "GET":
        err = utils._require_admin(headers, "access_screen_employees")
        if err: return err
        items = utils._query_bucket("EMPLOYEE")
        return utils._json_response(200, {"employees": items})

    if method == "POST":
        err = utils._require_admin(headers, "employee_add")
        if err: return err
        email = utils._normalize_email(body.get("email"))
        if utils._get_by_id("AUTH", email):
            return utils._json_response(400, {"message": "Email ya registrado"})
        
        emp_id = int(datetime.now(timezone.utc).timestamp() * 1000)
        temp_pass = "".join(random.choices("ABCDEFGHJKMNPQRSTUVWXYZ23456789", k=10))
        
        emp_item = {
            "entityType": "employee", "employeeId": emp_id, "name": body.get("name"),
            "email": email, "phone": body.get("phone"), "canAccessAdmin": True,
            "privileges": utils._normalize_privileges(body.get("privileges")), "active": True,
            "createdAt": now
        }
        utils._put_entity("EMPLOYEE", emp_id, emp_item)
        
        utils._put_entity("AUTH", email, {
            "entityType": "auth", "authId": email, "email": email, "employeeId": emp_id,
            "passwordHash": utils._hash_password(temp_pass), "role": "admin"
        })

        return utils._json_response(201, {"employee": emp_item, "tempPassword": temp_pass})

    if method == "PATCH" and employee_id:
        err = utils._require_admin(headers, "employee_manage_privileges")
        if err: return err
        # Lógica de actualización de nombre/celular/privilegios
        # Se puede separar en sub-rutas según el path
        eid = int(employee_id)
        updates = ["updatedAt = :u"]
        eav = {":u": now}
        
        if "name" in body: updates.append("#n = :n"); eav[":n"] = body["name"]
        if "active" in body: updates.append("active = :a"); eav[":a"] = bool(body["active"])
        if "privileges" in body: 
            updates.append("privileges = :p"); eav[":p"] = utils._normalize_privileges(body["privileges"])
        
        updated = utils._update_by_id("EMPLOYEE", eid, f"SET {', '.join(updates)}", eav, {"#n": "name"} if "name" in body else None)
        return utils._json_response(200, {"employee": updated})

# --- LAMBDA HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    headers = event.get("headers") or {}
    segments = [s for s in path.strip("/").split("/") if s]

    try:
        if segments and segments[0] == "auth":
            segments = segments[1:]

        # Enrutamiento Manual (Dispatcher)
        if not segments: return utils._json_response(200, {"service": "auth-identity"})

        root = segments[0]

        if root == "login" and method == "POST":
            return handle_login(body)

        if root == "crearcuenta" and method == "POST":
            return handle_create_account(body)

        if root == "verify-email" and method == "POST":
            return handle_verify_email(body)

        if root == "resend-email-confirmation" and method == "POST":
            return handle_resend_email_confirmation(body)

        if root == "changepassword" and method == "POST":
            return handle_change_password(body, headers)

        if root == "password":
            sub = segments[1] if len(segments) > 1 else ""
            if sub == "recovery": return handle_password_recovery(body)
            if sub == "reset": return handle_password_reset(body)

        if root == "referrer" and len(segments) > 1:
            return handle_get_referrer(segments[1])

        if root == "employees":
            emp_id = segments[1] if len(segments) > 1 else None
            return handle_employees(method, body, emp_id, headers)

        return utils._json_response(404, {"message": f"Ruta {path} no encontrada"})

    except Exception as e:
        print(f"[FATAL_ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Error interno del servidor", "error": str(e)})
