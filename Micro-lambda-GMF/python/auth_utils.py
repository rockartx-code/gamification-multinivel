import random
import secrets
import core_utils as utils # Importado desde la Lambda Layer
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from typing import Optional
import modo_handlers  # paquete B

FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")

from core.email import _EMAIL_BASE_CSS, _email_shell  # plantilla compartida con los correos del pedido



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


def _build_password_recovery_email(otp: str, minutos: int = 15) -> tuple:
    body = f"""
    <div class="icon">🔑</div>
    <h1 class="title">¿Olvidaste tu contraseña?</h1>
    <p class="lead">Recibimos una solicitud para restablecer la contraseña de tu cuenta.<br>
    Usa el siguiente código para continuar:</p>

    <div class="otp-box">{otp}</div>

    <p style="font-size:13px;color:#999;margin-top:8px;">El código expira en {minutos} minutos.</p>
    <p style="font-size:13px;color:#636e72;margin-top:12px;">
      Si pediste varios códigos, usa el más reciente; los anteriores dejan de valer en cuanto uses uno o pasen {minutos} minutos.
    </p>
    <p style="font-size:13px;color:#999;margin-top:12px;">
      Si no solicitaste este cambio puedes ignorar este correo.
    </p>
    """
    html = _email_shell(body)
    text = (f"Tu código de recuperación Finding'U es: {otp}. Expira en {minutos} minutos. "
            "Si pediste varios códigos, usa el más reciente; los anteriores dejan de valer en cuanto uses uno "
            f"o pasen {minutos} minutos.")
    return "Recupera tu contraseña — Finding'U", text, html


def _build_login_link_email(name: str, url: str, minutos: int) -> tuple:
    """Enlace de acceso de un solo uso: quien no recuerda su contraseña entra desde el correo."""
    body = f"""
    <div class="icon">🔗</div>
    <h1 class="title">Tu enlace para entrar</h1>
    <p class="lead">Hola <strong>{name}</strong>, toca el botón y entras a tu panel sin escribir contraseña.</p>
    <a href="{url}" class="btn">Entrar a Finding&rsquo;U &rarr;</a>
    <p style="font-size:13px;color:#999;margin-top:16px;">El enlace sirve una sola vez y caduca en {minutos} minutos.</p>
    <p style="font-size:13px;color:#999;margin-top:12px;">Si no lo pediste, ignora este correo: nadie puede entrar sin él.</p>
    """
    html = _email_shell(body)
    text = f"Hola {name}, entra a Finding'U con este enlace (sirve una vez, caduca en {minutos} minutos): {url}"
    return "Tu enlace para entrar a Finding'U", text, html


def _cfg_auth() -> dict:
    return utils._load_app_config().get("auth") or {}


def _minutos_codigo() -> int:
    return int(utils._to_decimal(_cfg_auth().get("loginLinkMinutes") or 15))


def _ttl_sesion(remember_me: bool) -> int:
    """30 días con "Recordarme"; sin marcarlo, la sesión corta de config (24 h)."""
    if remember_me:
        return int(utils.SESSION_TTL_SECONDS)
    corta = int(utils._to_decimal(_cfg_auth().get("sessionShortSeconds") or 86400))
    return min(corta, int(utils.SESSION_TTL_SECONDS))


def _remember_me(body: dict) -> bool:
    """La casilla viene marcada por omisión: solo un `false` explícito la apaga."""
    valor = body.get("rememberMe", True)
    if isinstance(valor, str):
        return valor.strip().lower() not in ("false", "0", "no", "")
    return bool(valor)


def _abrir_sesion(auth: dict, profile: dict, entity_type: str, user_id, remember_me: bool) -> dict:
    """Crea la sesión y arma la respuesta de login (la usan login y el enlace de acceso)."""
    token = "session-token-" + utils.uuid.uuid4().hex[:16]
    ttl = _ttl_sesion(remember_me)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    # Clave directa: validar el Bearer cuesta 1 GetItem en vez de 2, y no deja
    # un puntero REF por sesión. El TTL (epoch) hace que DynamoDB las purgue;
    # `expiresAt` es informativo para el frontend.
    utils._put_session(token, {
        "sessionId": token,
        "userId": str(user_id),
        "role": auth.get("role"),
        "authId": auth.get("authId") or auth.get("email"),
        "privileges": utils._normalize_privileges(profile.get("privileges")),
        # Una socia con acceso al back office entra con rol cliente: el backend
        # necesita saberlo para aplicar sus privilegios.
        "canAccessAdmin": bool(profile.get("canAccessAdmin")),
        "rememberMe": bool(remember_me),
        "expiresAt": expires_at,
    }, ttl_epoch=utils._ttl_epoch(ttl))

    return utils._json_response(200, {
        "token": token,
        "expiresAt": expires_at,
        "rememberMe": bool(remember_me),
        "user": {
            "userId": str(user_id),
            "name": profile.get("name"),
            "role": auth.get("role"),
            "canAccessAdmin": bool(profile.get("canAccessAdmin")),
            "privileges": utils._normalize_privileges(profile.get("privileges")),
            "isEmployee": (entity_type == "EMPLOYEE"),
            "mode": modo_handlers.modo_de(profile) if entity_type == "CUSTOMER" else None,  # paquete B
        }
    })


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

DEMO_LOGIN_ENABLED = str(utils.os.getenv("DEMO_LOGIN_ENABLED", "")).strip().lower() in ("1", "true", "yes", "on")


def _demo_users() -> list:
    """Cuentas de demostración, deshabilitadas salvo configuración explícita.

    Requiere `DEMO_LOGIN_ENABLED` **y** que las contraseñas vengan del entorno:
    antes estaban escritas en el código, de modo que cualquiera con acceso al
    repositorio conocía unas credenciales de admin válidas en producción.
    """
    if not DEMO_LOGIN_ENABLED:
        return []
    cuentas = [
        {"u": "admin", "p": utils.os.getenv("DEMO_ADMIN_PASSWORD", ""),
         "role": "admin", "id": "admin-001", "name": "Admin"},
        {"u": "cliente", "p": utils.os.getenv("DEMO_CLIENTE_PASSWORD", ""),
         "role": "cliente", "id": "client-001", "name": "Valeria Torres"},
    ]
    return [c for c in cuentas if c["p"]]


def _rehash_password_if_legacy(auth_id: str, auth: dict, password: str) -> None:
    """Migra al vuelo un hash viejo (SHA-256 sin sal) tras un login correcto.

    El login es el único momento en que se tiene la contraseña en claro, así
    que la migración es transparente: nadie tiene que cambiar su contraseña.
    Un fallo aquí no debe impedir el acceso.
    """
    if not utils._is_legacy_password_hash(auth.get("passwordHash")):
        return
    try:
        utils._update_by_id(
            "AUTH", auth_id,
            "SET passwordHash = :p, updatedAt = :u",
            {":p": utils._hash_password(str(password)), ":u": utils._now_iso()},
        )
    except Exception as ex:
        utils._log("password_rehash_error", "ERROR", authId=auth_id, error=ex)


def handle_login(body):
    """POST /auth/login"""
    identifier = (body.get("email") or body.get("username", "")).strip().lower()
    password = body.get("password")
    remember_me = _remember_me(body)

    if not identifier or not password:
        return utils._json_response(401, {"message": "Credenciales incompletas"})

    # 1. Usuarios demo (solo si se habilitan explícitamente por entorno).
    # Sus contraseñas están en el código, así que en producción DEMO_LOGIN_ENABLED
    # debe quedar sin definir: de lo contrario cualquiera con acceso al repo
    # entra como admin.
    for d in _demo_users():
        if (identifier == d["u"] or identifier == f"{d['u']}@demo.local") and password == d["p"]:
            token = "demo-token-" + utils.uuid.uuid4().hex[:16]
            utils._put_session(token, {
                "sessionId": token,
                "userId": str(d["id"]),
                "role": d["role"],
                "privileges": {},
                "rememberMe": remember_me,
            }, ttl_epoch=utils._ttl_epoch(_ttl_sesion(remember_me)))
            return utils._json_response(200, {"token": token, "rememberMe": remember_me, "user": {
                "userId": d["id"], "name": d["name"], "role": d["role"], "canAccessAdmin": (d["role"] == "admin")
            }})

    # 2. Buscar en tabla AUTH
    auth = utils._get_by_id("AUTH", identifier)

    if not auth:
        # Fallback: cliente con passwordHash antiguo pero sin registro AUTH
        matched_customer_id = utils._find_customer_id_by_email(identifier)
        customer = (utils._get_by_id("CUSTOMER", utils._customer_entity_id(matched_customer_id))
                    if matched_customer_id else None)
        if customer and utils._verify_password(password, customer.get("passwordHash")):
            auth = utils._put_entity("AUTH", identifier, {
                "entityType": "auth", "authId": identifier, "email": identifier,
                "customerId": customer.get("customerId"),
                "passwordHash": utils._hash_password(str(password)), "role": "cliente",
            })
        else:
            return utils._json_response(401, {"message": "Credenciales invalidas"})

    elif not utils._verify_password(password, auth.get("passwordHash")):
        return utils._json_response(401, {"message": "Credenciales invalidas"})

    else:
        _rehash_password_if_legacy(identifier, auth, password)

    if auth.get("emailVerified") is False:
        # El código permite al frontend ofrecer "Reenviar confirmación" sin comparar textos.
        return utils._json_response(403, {"message": "Confirma tu cuenta desde tu correo electrónico para iniciar sesión.", "code": "EMAIL_NOT_VERIFIED"})

    # 3. Determinar Perfil
    user_id = auth.get("employeeId") or auth.get("customerId")
    entity_type = "EMPLOYEE" if auth.get("employeeId") else "CUSTOMER"
    profile = utils._get_by_id(entity_type, user_id)

    if not profile:
        return utils._json_response(401, {"message": "Perfil no encontrado"})

    return _abrir_sesion({**auth, "authId": auth.get("authId") or identifier}, profile, entity_type, user_id, remember_me)


# --- ENLACE DE ACCESO POR CORREO (paquete C) ---

def _respuesta_enlace_generica() -> dict:
    """Nunca revela si el correo existe."""
    return utils._json_response(200, {"ok": True, "message": "Si el correo existe, enviamos un enlace para entrar. Revisa tu bandeja (y la de no deseados)."})


def handle_login_link_request(body):
    """POST /auth/enlace-acceso — manda un enlace de un solo uso (config auth.loginLinkMinutes)."""
    email = utils._normalize_email(body.get("email"))
    if not email or "@" not in email:
        return utils._json_response(400, {"message": "Escribe tu correo electrónico para mandarte el enlace."})
    auth = utils._get_by_id("AUTH", email)
    # Solo cuentas verificadas: el enlace equivale a una contraseña.
    if not auth or auth.get("emailVerified") is False:
        return _respuesta_enlace_generica()

    token = secrets.token_urlsafe(32)
    minutos = _minutos_codigo()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=minutos)).isoformat()
    utils._put_entity("LOGIN_LINK", utils._hash_token(token), {
        "entityType": "loginLink", "tokenHash": utils._hash_token(token), "email": email,
        "expiresAt": expires, "used": False, "rememberMe": _remember_me(body),
    })
    user_id = auth.get("employeeId") or auth.get("customerId")
    profile = utils._get_by_id("EMPLOYEE" if auth.get("employeeId") else "CUSTOMER", user_id) or {}
    url = f"{FRONTEND_URL.rstrip('/')}/#/login?enlace={quote(token)}"
    subj, txt, html = _build_login_link_email(profile.get("name") or "hola", url, minutos)
    utils._send_ses_email(email, subj, txt, html)
    return _respuesta_enlace_generica()


def handle_login_link_redeem(body):
    """POST /auth/enlace-acceso/canjear — abre la sesión con un enlace vigente y no usado."""
    token = str(body.get("token") or "").strip()
    rechazo = utils._json_response(401, {"message": "El enlace ya no sirve (se usó o caducó). Pide uno nuevo desde el login.",
                                          "code": "LOGIN_LINK_INVALID"})
    if not token:
        return rechazo
    registro = utils._get_by_id("LOGIN_LINK", utils._hash_token(token))
    if not registro or registro.get("used"):
        return rechazo
    try:
        expira = datetime.fromisoformat(str(registro.get("expiresAt") or "").replace("Z", "+00:00"))
    except ValueError:
        return rechazo
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expira:
        return rechazo

    email = registro.get("email")
    auth = utils._get_by_id("AUTH", email)
    if not auth:
        return rechazo
    user_id = auth.get("employeeId") or auth.get("customerId")
    entity_type = "EMPLOYEE" if auth.get("employeeId") else "CUSTOMER"
    profile = utils._get_by_id(entity_type, user_id)
    if not profile:
        return utils._json_response(401, {"message": "Perfil no encontrado"})

    # Un solo uso: se marca antes de abrir la sesión.
    utils._update_by_id("LOGIN_LINK", registro.get("tokenHash"), "SET used = :t, usedAt = :u",
                        {":t": True, ":u": utils._now_iso()})
    remember_me = _remember_me(body) if "rememberMe" in body else bool(registro.get("rememberMe", True))
    return _abrir_sesion({**auth, "authId": auth.get("authId") or email}, profile, entity_type, user_id, remember_me)


def _vincular_pedidos_de_invitado(customer_id, email: str) -> list:
    """Liga al nuevo cliente los pedidos hechos como invitado con su mismo correo.

    Solo se toca la referencia del comprador y el historial del panel: el
    tipo de comprador sigue siendo invitado, así que el motor de comisiones
    no vuelve a acreditar nada.
    """
    ligados = []
    try:
        for order in utils._query_bucket("ORDER") or []:
            if order.get("customerId") not in (None, "", 0, "0"):
                continue
            if utils._normalize_email(order.get("email")) != email:
                continue
            oid = order.get("orderId")
            if not oid:
                continue
            actualizado = utils._update_by_id("ORDER", oid, "SET customerId = :c, linkedToAccountAt = :t",
                                              {":c": customer_id, ":t": utils._now_iso()})
            utils._upsert_order_customer_history(actualizado or {**order, "customerId": customer_id})
            ligados.append(oid)
    except Exception as ex:
        utils._log_error("guest_orders_link_failed", ex)
    return ligados

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

    # Resolver patrocinador: primero intentar lookup por código de referido,
    # si no aplica usar leaderId directo (admin/internal flows)
    raw_referral = body.get("referralToken") or body.get("referralCodeInput")
    leader_id = _resolve_leader_from_referral_code(raw_referral) or body.get("leaderId") or None
    if raw_referral and not leader_id:
        utils._log("referral_code_unresolved", "INFO", referralToken=raw_referral, detail='se registra sin líder')
    modo_handlers.asegurar_socio(leader_id, "referido")  # paquete B: quien ya tiene red es socio
    
    customer_item = {
        "entityType": "customer", "customerId": customer_id, "name": name,
        "email": email, "phone": body.get("phone"), "leaderId": leader_id,
        "isAssociate": True, "canAccessAdmin": False, "createdAt": now,
        "mode": "cliente", "modeSince": now, "modeReason": "registro",  # paquete B: todo registro nace cliente
    }
    utils._put_entity("CUSTOMER", customer_id, customer_item)

    # Referencia propia: REFERRAL_CODE#{customerId} → leaderId={customerId}
    _upsert_referral_code_self(customer_id, name)

    # Índices de búsqueda (nombre y email). El helper compartido garantiza que
    # se escriban igual desde el auto-registro y desde el alta por admin.
    utils._upsert_customer_name_index(customer_id, name, email, created_at_iso=now)
    utils._upsert_customer_email_index(customer_id, email)
    # Quien compró como invitado y luego crea su cuenta con el mismo correo
    # debe ver ese historial en su panel (antes desaparecía).
    _vincular_pedidos_de_invitado(customer_id, email)

    try:
        utils._sync_customer_network_metadata()
    except Exception as ex:
        utils._log("customer_network_sync_error", "ERROR", customerId=customer_id, error=ex, detail='action=create_account')

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
            utils._log_error("email_leader_failed", ex)

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
        return utils._json_response(400, {"message": "Ingresa tu correo electrónico."})

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
    minutos = _minutos_codigo()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=minutos)).isoformat()

    # Se conservan los últimos N códigos vigentes (config auth.recoveryCodesKept):
    # Memo, Lupita, Claudia y Patricia pedían dos códigos porque el primero se
    # invalidaba en cuanto llegaba el segundo. `otpHash` se conserva por compatibilidad.
    previo = utils._get_by_id("PASSWORD_RESET", email) or {}
    vigentes = [] if previo.get("used") else [c for c in (previo.get("otpHashes") or []) if isinstance(c, dict)]
    if previo.get("otpHash") and not previo.get("used") and not any(c.get("hash") == previo.get("otpHash") for c in vigentes):
        vigentes.append({"hash": previo.get("otpHash"), "expiresAt": previo.get("expiresAt"), "used": False})
    vigentes.append({"hash": utils._hash_token(otp), "expiresAt": expires, "used": False})
    conservar = max(1, int(utils._to_decimal(_cfg_auth().get("recoveryCodesKept") or 3)))
    utils._put_entity("PASSWORD_RESET", email, {
        "entityType": "passwordReset", "email": email,
        "otpHash": utils._hash_token(otp), "expiresAt": expires, "used": False,
        "otpHashes": vigentes[-conservar:],
    })

    subj, txt, html = _build_password_recovery_email(otp, minutos)
    utils._send_ses_email(email, subj, txt, html)
    return utils._json_response(200, {
        "ok": True,
        "message": f"Te mandamos un código de 6 dígitos. Vale {minutos} minutos; si pediste varios, usa el más reciente.",
    })


def _codigo_vigente(reset_rec: dict, otp: str) -> bool:
    """True si `otp` coincide con alguno de los últimos códigos emitidos, no usado y dentro de su vigencia."""
    if not reset_rec or reset_rec.get("used") or not otp:
        return False
    candidatos = [c for c in (reset_rec.get("otpHashes") or []) if isinstance(c, dict)]
    if reset_rec.get("otpHash") and not any(c.get("hash") == reset_rec.get("otpHash") for c in candidatos):
        candidatos.append({"hash": reset_rec.get("otpHash"), "expiresAt": reset_rec.get("expiresAt"), "used": False})
    ahora = datetime.now(timezone.utc)
    digest = utils._hash_token(otp)
    for c in candidatos:
        if c.get("used") or not utils.hmac.compare_digest(digest, str(c.get("hash") or "")):
            continue
        # Antes no se comprobaba `expiresAt`: un código de hace días seguía valiendo.
        try:
            expira = datetime.fromisoformat(str(c.get("expiresAt") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if ahora <= expira:
            return True
    return False

def handle_password_reset(body):
    """POST /auth/password/reset"""
    email = utils._normalize_email(body.get("email"))
    otp = body.get("otp", "").strip()
    new_password = body.get("password")

    if not new_password or len(str(new_password)) < 8:
        return utils._json_response(400, {"message": "La nueva contraseña debe tener al menos 8 caracteres."})
    reset_rec = utils._get_by_id("PASSWORD_RESET", email)
    if not _codigo_vigente(reset_rec, otp):
        return utils._json_response(401, {"message": "Código inválido o caducado: pide uno nuevo", "code": "OTP_INVALID"})

    # Actualizar password en AUTH
    pass_hash = utils._hash_password(str(new_password))
    utils._update_by_id("AUTH", email, "SET passwordHash = :p, updatedAt = :u", {":p": pass_hash, ":u": utils._now_iso()})
    
    # Marcar el registro como usado: al usar un código dejan de valer todos los anteriores.
    utils._update_by_id("PASSWORD_RESET", email, "SET used = :t, usedAt = :u", {":t": True, ":u": utils._now_iso()})

    return utils._json_response(200, {"ok": True, "message": "Contraseña actualizada. Ya puedes entrar con ella."})

def _find_auth_for_customer(customer_id) -> Optional[dict]:
    """Registro AUTH de un cliente/empleado, sin barrer la colección.

    AUTH está indexado por email (`authId`), así que basta con leer el perfil
    para conocerlo. Solo si el perfil no tiene email —o el AUTH está bajo otro
    identificador— se recurre al barrido, que además ya no es el camino normal.
    """
    cid = str(customer_id or "").strip()
    if not cid:
        return None

    profile = utils._get_by_id("CUSTOMER", utils._customer_entity_id(cid)) or utils._get_by_id("EMPLOYEE", cid)
    email = utils._normalize_email((profile or {}).get("email"))
    if email:
        auth = utils._get_by_id("AUTH", email)
        if auth and str(auth.get("customerId") or auth.get("employeeId") or "") == cid:
            return auth

    return next(
        (r for r in utils._query_bucket("AUTH")
         if str(r.get("customerId") or r.get("employeeId") or "") == cid),
        None,
    )


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

    # El registro AUTH está indexado por email, así que se resuelve desde el
    # perfil del cliente (1-2 GetItem) en vez de leer la colección AUTH entera.
    auth = _find_auth_for_customer(customer_id)
    if not auth:
        return utils._json_response(404, {"message": "Cuenta no encontrada"})

    # Validar contraseña actual
    if not utils._verify_password(current_password, auth.get("passwordHash")):
        return utils._json_response(401, {"message": "La contraseña actual es incorrecta"})

    # Actualizar contraseña
    email = auth.get("email") or auth.get("authId")
    utils._update_by_id("AUTH", email, "SET passwordHash = :p, updatedAt = :u", {
        ":p": utils._hash_password(str(new_password)),
        ":u": utils._now_iso()
    })

    # Aviso de seguridad: "cambié mi contraseña y no me llegó ningún correo;
    # si alguien más me la cambiara, nunca me entero" (docs/qa/19).
    try:
        from core.email import _email_shell
        cuerpo = """
    <div class="icon">🔒</div>
    <h1 class="title">Tu contraseña cambió</h1>
    <p class="lead">Acabamos de actualizar la contraseña de tu cuenta Finding&rsquo;U. Si fuiste tú, no tienes que hacer nada.</p>
    <p class="lead">Si <strong>no</strong> fuiste tú, recupera tu acceso desde "¿Olvidaste tu contraseña?" y escríbenos de inmediato.</p>"""
        utils._send_ses_email(email, "Tu contraseña de Finding'U cambió",
                              "Acabamos de actualizar la contraseña de tu cuenta. Si no fuiste tú, recupera tu acceso desde '¿Olvidaste tu contraseña?' y escríbenos.",
                              _email_shell(cuerpo))
    except Exception as ex:
        utils._log("change_password_email_error", "ERROR", error=ex)
    return utils._json_response(200, {"ok": True, "message": "Contraseña actualizada"})



def _build_user_referral_code(name: str) -> str:
    """Genera el código de referido a partir del nombre completo.
    Ej: 'Maria Garcia Lopez' → 'Maria-MGL'
    Idéntico a buildReferralCode() en el frontend."""
    # Sin acentos ni ñ: "TOMÁS-TIL" solo resolvía escrito con acento; quien lo
    # teclea como "TOMAS-TIL" (lo normal en un código) se registraba sin líder.
    import unicodedata
    name = "".join(c for c in unicodedata.normalize("NFD", str(name or "")) if unicodedata.category(c) != "Mn")
    n = (name or "").strip()
    if not n:
        return ""
    words = n.split()
    initials = "".join(w[0].upper() for w in words if w)
    return f"{words[0]}-{initials}"

def _resolve_unique_referral_code(base_code: str, customer_id) -> str:
    """Devuelve base_code si está libre o ya pertenece a customer_id.
    Si está tomado por otro, prueba base_code-2, base_code-3, … hasta encontrar uno libre."""
    candidate = base_code
    suffix = 2
    while True:
        resp = utils._table.get_item(Key={"PK": utils._referral_code_pk(candidate), "SK": "REFCodeInput"})
        item = resp.get("Item")
        if not item:
            # Libre — usar este
            return candidate
        existing_leader = item.get("leaderId")
        try:
            same_owner = int(existing_leader) == int(customer_id)
        except (TypeError, ValueError):
            same_owner = str(existing_leader) == str(customer_id)
        if same_owner:
            # Ya existe y ya es del mismo customer — no hay conflicto
            return candidate
        # Colisión con otro customer — probar siguiente consecutivo
        candidate = f"{base_code}-{suffix}"
        suffix += 1

def _upsert_referral_code_self(customer_id, name: str = "") -> str | None:
    """Crea/actualiza REFERRAL_CODE#{userReferralCode} → leaderId={customerId}.
    El código se genera desde el nombre; si hay colisión agrega consecutivo (-2, -3…)."""
    base_code = _build_user_referral_code(name)
    if not base_code:
        utils._log("referral_code_self_skip", "INFO", customerId=customer_id, detail='sin nombre — omitido')
        return None
    try:
        code = _resolve_unique_referral_code(base_code, customer_id)
        utils._table.put_item(Item={
            "PK": utils._referral_code_pk(code),
            "SK": "REFCodeInput",
            "code": code.upper(),
            "leaderId": customer_id,
            "leaderName": name,
            "createdAt": utils._now_iso(),
        })
        if code != base_code:
            utils._log("referral_code_collision", "INFO", customerId=customer_id, base=base_code, asignado=code)
        # El código también tiene que vivir en la ficha del cliente: es lo que
        # el frontend usa para armar el link que el socio comparte. Sin esto,
        # el perfil devolvía referralCode vacío y el link se construía con el
        # ID numérico, que no resolvía como código.
        utils._update_by_id(
            "CUSTOMER", customer_id,
            "SET referralCode = :referralCode, updatedAt = :updatedAt",
            {":referralCode": code.upper(), ":updatedAt": utils._now_iso()},
        )
        return code
    except Exception as ex:
        utils._log("referral_code_self_insert_error", "ERROR", customerId=customer_id, error=ex)
        return None

def _resolve_leader_from_referral_code(raw_code) -> str | None:
    """Dada una referralCode, devuelve el leaderId asociado o None si no existe."""
    if not raw_code:
        return None
    import unicodedata
    code = "".join(c for c in unicodedata.normalize("NFD", str(raw_code).strip()) if unicodedata.category(c) != "Mn").upper()
    try:
        resp = utils._table.get_item(Key={"PK": utils._referral_code_pk(code), "SK": "REFCodeInput"})
        item = resp.get("Item")
        if item:
            return str(item["leaderId"])
    except Exception as ex:
        utils._log("referral_code_lookup_error", "ERROR", code=code, error=ex)
    # El link que la propia plataforma genera para el socio lleva su ID numérico
    # (el frontend cae a settings.userCode porque referralCode no viaja en el
    # perfil). Sin esta rama, TODOS esos links registraban al invitado sin
    # líder y el patrocinador se quedaba sin su referido.
    if code.isdigit():
        try:
            if utils._get_by_id("CUSTOMER", int(code)):
                return code
        except Exception as ex:
            utils._log("referral_id_lookup_error", "ERROR", code=code, error=ex)
    return None

def _migrate_referral_codes(headers, body) -> dict:
    """Asigna su código de referido propio a todos los clientes que no lo tengan.

    Corrida masiva idempotente. Antes existía dos veces: como función suelta
    `migrate()` —que además referenciaba `headers`/`body` inexistentes y
    reventaba con NameError si alguien la llamaba— y como bloque en línea
    dentro de la ruta.
    """
    inserted = skipped = errors = 0
    for customer in utils._query_bucket("CUSTOMER"):
        cid = customer.get("customerId")
        if not cid:
            skipped += 1
            continue
        try:
            referral_code = _upsert_referral_code_self(cid, str(customer.get("name") or ""))
            if not referral_code:
                skipped += 1
                continue
            utils._update_by_id(
                "CUSTOMER",
                cid,
                "SET referralCode = :referralCode, updatedAt = :updatedAt",
                {":referralCode": referral_code, ":updatedAt": utils._now_iso()},
            )
            inserted += 1
        except Exception as ex:
            utils._log("migrate_referral_code_error", "ERROR", customerId=cid, error=ex)
            errors += 1

    utils._audit_event("referral_code.migrate", headers, body, {
        "inserted": inserted, "skipped": skipped, "errors": errors,
    })
    return utils._json_response(200, {
        "ok": True, "inserted": inserted, "skipped": skipped, "errors": errors,
    })

def handle_referral_code(method, body, code_segment, headers):
    """
    POST   /auth/referral-code           → crear relación código → leaderId (requiere admin)
    POST   /auth/referral-code/migrate   → corrida masiva para todos los customers (requiere admin)
    GET    /auth/referral-code/{code}    → consultar a qué líder apunta un código
    DELETE /auth/referral-code/{code}    → eliminar relación (requiere admin)
    """
    # ── MIGRATE — corrida masiva para todos los customers existentes ──────────
    if code_segment == "migrate" and method == "POST":
        err = utils._require_admin(headers, "config_manage")
        if err: return err
        return _migrate_referral_codes(headers, body)

    # ── GET (lookup público para validar código en registro) ─────────────────
    if method == "GET":
        if not code_segment:
            return utils._json_response(400, {"message": "Se requiere el código en la URL."})
        code = code_segment.strip().upper()
        resp = utils._table.get_item(Key={"PK": utils._referral_code_pk(code), "SK": "REFCodeInput"})
        item = resp.get("Item")
        if not item:
            return utils._json_response(404, {"message": "Código de referido no encontrado."})
        leader_id = item.get("leaderId")
        try:
            lid = int(leader_id)
        except (TypeError, ValueError):
            lid = leader_id
        leader = utils._get_by_id("CUSTOMER", lid)
        return utils._json_response(200, {
            "code": code,
            "leaderId": leader_id,
            "leaderName": leader.get("name") if leader else None,
        })

    # ── POST (crear / actualizar) ─────────────────────────────────────────────
    if method == "POST":
        err = utils._require_admin(headers, "config_manage")
        if err: return err
        code = str(body.get("code") or "").strip().upper()
        leader_id = body.get("leaderId")
        if not code or not leader_id:
            return utils._json_response(400, {"message": "Se requieren 'code' y 'leaderId'."})
        try:
            leader_id = int(leader_id)
        except (TypeError, ValueError):
            # leaderId no numérico: se conserva tal cual (IDs legados en texto).
            pass
        # Verificar que el líder existe
        try:
            lid_int = int(leader_id)
        except (TypeError, ValueError):
            lid_int = leader_id
        leader = utils._get_by_id("CUSTOMER", lid_int)
        if not leader:
            return utils._json_response(404, {"message": "Líder no encontrado."})
        utils._table.put_item(Item={
            "PK": utils._referral_code_pk(code),
            "SK": "REFCodeInput",
            "code": code,
            "leaderId": leader_id,
            "leaderName": leader.get("name") or "",
            "createdAt": utils._now_iso(),
        })
        utils._audit_event("referral_code.create", headers, body, {"code": code, "leaderId": leader_id})
        return utils._json_response(201, {"ok": True, "code": code, "leaderId": leader_id})

    # ── DELETE ────────────────────────────────────────────────────────────────
    if method == "DELETE":
        err = utils._require_admin(headers, "config_manage")
        if err: return err
        if not code_segment:
            return utils._json_response(400, {"message": "Se requiere el código en la URL."})
        code = code_segment.strip().upper()
        utils._table.delete_item(Key={"PK": utils._referral_code_pk(code), "SK": "REFCodeInput"})
        utils._audit_event("referral_code.delete", headers, body, {"code": code})
        return utils._json_response(200, {"ok": True, "code": code})

    return utils._json_response(405, {"message": "Método no permitido."})

def handle_get_referrer(referrer_id):
    """GET /referrer/{id}"""
    # Intentar lookup por ID numérico o string
    try:
        rid = int(referrer_id)
    except (TypeError, ValueError):
        rid = referrer_id

    customer = utils._get_by_id("CUSTOMER", rid)
    if not customer:
        return utils._json_response(200, {"referrer": {
            "name": "FindingU",
            "email": "contacto@findingu.com.mx",
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
        
        if "name" in body: updates.append("#n = :n"); eav[":n"] = str(body["name"]).strip()
        # El panel mandaba `phone` y aquí se ignoraba: el celular del empleado no se podía corregir.
        if "phone" in body: updates.append("phone = :ph"); eav[":ph"] = str(body.get("phone") or "").strip()
        if "active" in body: updates.append("active = :a"); eav[":a"] = bool(body["active"])
        # El panel mandaba canAccessAdmin y aquí se ignoraba: no había forma de quitarle el acceso a un empleado.
        if "canAccessAdmin" in body: updates.append("canAccessAdmin = :ca"); eav[":ca"] = bool(body["canAccessAdmin"])
        if "privileges" in body: 
            updates.append("privileges = :p"); eav[":p"] = utils._normalize_privileges(body["privileges"])
        
        updated = utils._update_by_id("EMPLOYEE", eid, f"SET {', '.join(updates)}", eav, {"#n": "name"} if "name" in body else None)
        return utils._json_response(200, {"employee": updated})

# --- LAMBDA HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return utils._cors_preflight_response()
    request = utils._http_request(event, strip_prefix="auth")
    path, method = request.path, request.method
    body, headers, segments = request.body, request.headers, request.segments

    try:

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

        if root == "enlace-acceso" and method == "POST":
            sub = segments[1] if len(segments) > 1 else ""
            if not sub: return handle_login_link_request(body)
            if sub == "canjear": return handle_login_link_redeem(body)

        if root == "referrer" and len(segments) > 1:
            return handle_get_referrer(segments[1])

        if root == "referral-code":
            code_segment = segments[1] if len(segments) > 1 else None
            return handle_referral_code(method, body, code_segment, headers)

        if root == "employees":
            emp_id = segments[1] if len(segments) > 1 else None
            # POST /employees/{id}/reset-password
            if emp_id and len(segments) >= 3 and segments[2] == "reset-password" and method == "POST":
                err = utils._require_admin(headers, "employee_manage_privileges")
                if err: return err
                eid = int(emp_id)
                emp = utils._get_by_id("EMPLOYEE", eid)
                if not emp:
                    return utils._json_response(404, {"message": "Empleado no encontrado"})
                auth_record = utils._get_by_id("AUTH", emp.get("email"))
                if not auth_record:
                    return utils._json_response(404, {"message": "Cuenta de acceso no encontrada"})
                temp_pass = "".join(random.choices("ABCDEFGHJKMNPQRSTUVWXYZ23456789", k=10))
                utils._update_by_id(
                    "AUTH", emp.get("email"),
                    "SET passwordHash = :p, updatedAt = :u",
                    {":p": utils._hash_password(temp_pass), ":u": utils._now_iso()}
                )
                return utils._json_response(200, {"tempPassword": temp_pass})
            return handle_employees(method, body, emp_id, headers)

        return utils._json_response(404, {"message": f"Ruta {path} no encontrada"})

    except Exception as e:
        utils._log_error("auth_unhandled_error", e, path=path, method=method)
        return utils._json_response(500, {"message": "Error interno del servidor", "error": str(e)})
