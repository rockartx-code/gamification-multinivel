"""Seguimiento de hoy para la coach (paquete F, propuestas 15 y 19).

La ejecutiva de recuperación cruzaba Clientes, Pedidos y Estadísticas y abría
ficha por ficha (36 fichas en cinco turnos) para saber a quién escribirle, y
después redactaba el mismo WhatsApp y anotaba la nota a mano. Este módulo
resuelve las dos cosas desde `customer_lambda`:

- `GET  /customers/seguimiento/hoy`            lista priorizada por situación
- `GET  /customers/seguimiento/plantillas`     plantillas de WhatsApp
- `POST /customers/{id}/contacto`              anota el contacto (wa.me prellenado)
- `POST /customers/seguimiento/ficha-invitado` crea la ficha de un comprador invitado

El mensaje lo manda la persona desde su teléfono (`wa.me`); el sistema solo
prellena y anota. Todas las rutas exigen `access_screen_customers`.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import core_utils as utils

PRIVILEGIO = "access_screen_customers"

SITUACIONES = ("bienvenida", "fria", "clabe_pendiente", "pedido_tardio", "activa")
CANALES = ("whatsapp", "email", "call")
PREFERENCIAS = ("whatsapp", "email", "none")
SIN_CONTACTO = 999          # "nunca contactado" pesa como 999 días en la prioridad
PRIORIDAD_URGENTE = 100     # extra para CLABE pendiente y pedido tardío
DIAS_ENVIO_SIN_ENTREGA = 7  # pedido enviado sin entrega que ya amerita avisar

PLACEHOLDERS = ["{nombre}", "{coach}", "{producto}", "{monto}", "{folio}"]

#: Plantillas por situación. La config `seguimiento.templates` las sobreescribe
#: por clave (`{"fria": {"text": "..."}}`), sin necesidad de tocar código.
PLANTILLAS = {
    "bienvenida": {
        "title": "Bienvenida",
        "text": ("Hola {nombre}, soy {coach} de Finding'U. Vi que ya tienes tu cuenta; "
                 "si quieres te ayudo a armar tu primer pedido o a resolver cualquier duda. "
                 "¿Te escribo por aquí?"),
    },
    "fria": {
        "title": "Cliente fría",
        "text": ("Hola {nombre}, soy {coach} de Finding'U. Hace tiempo que no te vemos por la tienda; "
                 "¿cómo te fue con {producto}? Si quieres repetirlo o probar algo nuevo, te ayudo con tu pedido."),
    },
    "clabe_pendiente": {
        "title": "CLABE pendiente",
        # La ruta "Mi cuenta → Datos bancarios" no existe en el producto: es
        # Mi perfil. Gaby mandaba a la gente a un menú inventado.
        "text": ("Hola {nombre}, soy {coach} de Finding'U. Tienes {monto} de comisiones listas para depositar, "
                 "pero nos falta tu CLABE. Regístrala en Mi perfil (findingu.mx/#/perfil) y te la "
                 "depositamos el día de pago."),
    },
    "pedido_tardio": {
        "title": "Pedido tardío",
        "text": ("Hola {nombre}, soy {coach} de Finding'U. Vi que tu pedido {folio} sigue en camino; "
                 "ya estoy revisando con almacén y te aviso en cuanto tenga la guía o la fecha de entrega. "
                 "Gracias por la paciencia."),
    },
    # Propuesta 11: la situación existía, tenía etiqueta y no tenía plantilla, así
    # que la pantalla rellenaba con la de cliente fría. Gaby estuvo a un clic de
    # mandarle "Hace tiempo que no te vemos por la tienda" a Julio, con el pedido
    # entregado el viernes: *"La plantilla no me ahorró trabajo, me puso una trampa."*
    "activa": {
        "title": "Compró hace poco",
        "text": ("Hola {nombre}, soy {coach} de Finding'U. Vi que ya recibiste {producto}; "
                 "paso a preguntarte cómo te fue con él y si necesitas algo más. "
                 "Cualquier duda me escribes por aquí."),
    },
}

ETIQUETAS_SITUACION = {
    "bienvenida": "Bienvenida", "fria": "Fría", "clabe_pendiente": "CLABE pendiente",
    "pedido_tardio": "Pedido tardío", "activa": "Activa",
}
ETIQUETAS_CANAL = {"whatsapp": "WhatsApp", "email": "Correo", "call": "Llamada"}

_ESTADOS_COMPRA = ("paid", "shipped", "delivered", "en_devolucion", "devolucion_rechazada", "devuelto_validado")


# --- Utilidades ---------------------------------------------------------------

def _config() -> dict:
    return utils._load_app_config().get("seguimiento") or {}


def _entero(valor, por_defecto: int) -> int:
    try:
        return int(utils._to_decimal(valor))
    except Exception:
        return por_defecto


def _telefono_10(telefono) -> str:
    """Deja el celular en 10 dígitos; si no cuadra, cadena vacía (sin enlace)."""
    digitos = re.sub(r"\D", "", str(telefono or ""))
    if len(digitos) == 10:
        return digitos
    if len(digitos) == 12 and digitos.startswith("52"):
        return digitos[2:]
    if len(digitos) == 13 and digitos.startswith("521"):
        return digitos[3:]
    return ""


def _whatsapp_url(telefono, texto: Optional[str] = None) -> str:
    diez = _telefono_10(telefono)
    if not diez:
        return ""
    url = f"https://wa.me/52{diez}"
    if texto:
        from urllib.parse import quote
        url += "?text=" + quote(texto)
    return url


def _fecha(iso) -> Optional[datetime]:
    texto = str(iso or "").strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _dias_desde(iso, ahora: datetime) -> Optional[int]:
    fecha = _fecha(iso)
    if not fecha:
        return None
    return max(0, (ahora - fecha).days)


def _ejecutivas() -> dict:
    """Empleadas por id (como cadena) para nombrar la ejecutiva asignada."""
    try:
        return {str(e.get("employeeId")): e for e in utils._query_bucket("EMPLOYEE") if e.get("employeeId") is not None}
    except Exception as ex:
        utils._log_error("seguimiento_employees_error", ex)
        return {}


def _formato_monto(valor) -> str:
    try:
        return "${:,.2f}".format(float(utils._to_decimal(valor or 0)))
    except Exception:
        return "$0.00"


def _plantillas() -> dict:
    """Plantillas de código con el override de config por clave."""
    override = _config().get("templates") or {}
    salida = {}
    for clave, base in PLANTILLAS.items():
        propia = override.get(clave) if isinstance(override, dict) else None
        propia = propia if isinstance(propia, dict) else {}
        salida[clave] = {
            "title": str(propia.get("title") or base["title"]),
            "text": str(propia.get("text") or base["text"]),
        }
    return salida


def renderizar(texto: str, valores: dict) -> str:
    """Sustituye {nombre}, {coach}, {producto}, {monto}, {folio}."""
    salida = str(texto or "")
    for marcador in PLACEHOLDERS:
        salida = salida.replace(marcador, str(valores.get(marcador[1:-1]) or ""))
    return salida


# --- Lectura del cliente ------------------------------------------------------

def _historial_pedidos(customer_id) -> list:
    """Últimos pedidos del cliente (más reciente primero) del historial por cliente."""
    try:
        resp = utils._table.query(
            KeyConditionExpression=utils.Key("PK").eq(utils._order_customer_history_pk(customer_id)),
            ScanIndexForward=False, Limit=8,
        )
        return resp.get("Items", []) or []
    except Exception as ex:
        utils._log("seguimiento_history_error", "ERROR", customer=customer_id, error=ex)
        return []


def _resumen_pedido(pedido: Optional[dict]) -> Optional[dict]:
    if not pedido:
        return None
    lineas = pedido.get("items") or []
    primero = lineas[0] if lineas and isinstance(lineas[0], dict) else {}
    total = pedido.get("total")
    if total in (None, ""):
        total = pedido.get("netTotal") or 0
    return {
        "id": str(pedido.get("orderId") or ""),
        "createdAt": pedido.get("createdAt"),
        "total": float(utils._to_decimal(total)),
        "status": str(pedido.get("status") or ""),
        "productName": str(primero.get("name") or primero.get("productName") or ""),
    }


def _pedido_tardio(pedidos: list, ahora: datetime, dias_tardio: int) -> Optional[dict]:
    """Pedido pagado sin envío desde hace ≥ lateOrderDays, o enviado sin entrega ≥ 7 días."""
    for p in pedidos:
        estado = str(p.get("status") or "").lower()
        dias = _dias_desde(p.get("updatedAt") or p.get("createdAt"), ahora)
        if dias is None:
            continue
        if estado == "paid" and dias >= dias_tardio:
            return p
        if estado == "shipped" and dias >= DIAS_ENVIO_SIN_ENTREGA:
            return p
    return None


def _ledgers_confirmados() -> dict:
    """Comisiones confirmadas por beneficiaria en el mes actual y el anterior."""
    actual = utils._month_key()
    y, m = [int(x) for x in actual.split("-")]
    anterior = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    confirmado = {}
    try:
        for item in utils._listar_meses_contables(actual) + utils._listar_meses_contables(anterior):
            cid = str(item.get("beneficiaryId") or "")
            confirmado[cid] = confirmado.get(cid, 0.0) + float(utils._to_decimal(item.get("totalConfirmed", 0)))
    except Exception as ex:
        utils._log_error("seguimiento_ledger_error", ex)
    return confirmado


def _situacion(ficha: dict, pedidos: list, ahora: datetime, cfg: dict, comision_confirmada: float) -> tuple:
    """Devuelve (situación, pedido tardío o None). Aplica la primera regla que cumpla."""
    dias_frio = _entero(cfg.get("coldDays"), 30)
    dias_bienvenida = _entero(cfg.get("welcomeDays"), 7)
    dias_tardio = _entero(cfg.get("lateOrderDays"), 5)

    tiene_clabe = bool(str(ficha.get("clabeInterbancaria") or ficha.get("clabe") or "").strip())
    # Primero el pedido tardío: "Pedido tardío 0" mientras Acciones decía "4 pagados sin envío"
    # porque la CLABE pendiente se llevaba a la persona.
    tardio = _pedido_tardio(pedidos, ahora, dias_tardio)
    if tardio:
        return "pedido_tardio", tardio
    if comision_confirmada > 0 and not tiene_clabe:
        return "clabe_pendiente", None
    ultima_compra = next((p.get("createdAt") for p in pedidos if str(p.get("status") or "").lower() in _ESTADOS_COMPRA), None)
    dias_compra = _dias_desde(ultima_compra, ahora)
    dias_registro = _dias_desde(ficha.get("createdAt"), ahora)
    if dias_compra is None:
        if dias_registro is not None and dias_registro <= dias_bienvenida:
            return "bienvenida", None
        return "fria", None
    if dias_compra >= dias_frio:
        return "fria", None
    return "activa", None


def _ultimo_contacto(ficha: dict) -> Optional[str]:
    if ficha.get("lastContactAt"):
        return ficha.get("lastContactAt")
    notas = ficha.get("contactNotes") or []
    return notas[-1].get("at") if notas and isinstance(notas[-1], dict) else None


def _es_urgente(situacion: str) -> bool:
    return situacion in ("clabe_pendiente", "pedido_tardio")


def _prioridad(situacion: str, dias_compra: Optional[int], dias_contacto: Optional[int],
               dias_registro: Optional[int] = None) -> int:
    """días sin compra + días sin contacto (nunca contactada = 999), +100 si es urgente.

    Quien nunca compró cuenta los días desde que se registró: es lo que la coach
    lee como "días sin compra". La lista se ordena por urgencia y luego por esta
    prioridad, para que una CLABE con dinero esperando o un pedido pagado sin
    despachar siempre queden arriba de las frías de toda la vida.
    """
    sin_compra = dias_compra if dias_compra is not None else (dias_registro if dias_registro is not None else SIN_CONTACTO)
    base = sin_compra + (SIN_CONTACTO if dias_contacto is None else dias_contacto)
    if _es_urgente(situacion):
        base += PRIORIDAD_URGENTE
    return base


def _fila_cliente(ficha: dict, ahora: datetime, cfg: dict, ejecutivas: dict, patrocinadores: dict,
                  confirmados: dict, nombre_coach: str) -> dict:
    cid = str(ficha.get("customerId") or "")
    pedidos = _historial_pedidos(ficha.get("customerId"))
    situacion, tardio = _situacion(ficha, pedidos, ahora, cfg, confirmados.get(cid, 0.0))
    ultima_compra = next((p.get("createdAt") for p in pedidos if str(p.get("status") or "").lower() in _ESTADOS_COMPRA), None)
    dias_compra = _dias_desde(ultima_compra, ahora)
    dias_contacto = _dias_desde(_ultimo_contacto(ficha), ahora)
    ultimo = _resumen_pedido(tardio or (pedidos[0] if pedidos else None))
    ejecutiva = ejecutivas.get(str(ficha.get("executiveId") or ""))
    leader_id = ficha.get("leaderId")
    patrocinador = patrocinadores.get(str(leader_id)) if leader_id not in (None, "") else None
    telefono = str(ficha.get("phone") or "").strip()
    monto = confirmados.get(cid, 0.0) if situacion == "clabe_pendiente" else (ultimo or {}).get("total", 0)
    return {
        "customerId": cid,
        "isGuest": False,
        "email": str(ficha.get("email") or ""),
        "name": str(ficha.get("name") or ""),
        "mode": str(ficha.get("mode") or ("cliente" if ficha.get("isAssociate") is False else "socio")),
        "phone": telefono,
        "whatsappUrl": _whatsapp_url(telefono),
        "sponsorName": (patrocinador or {}).get("name") or ("" if leader_id in (None, "") else str(leader_id)),
        "executiveId": str(ficha.get("executiveId") or ""),
        "executiveName": str((ejecutiva or {}).get("name") or ""),
        "origin": str(ficha.get("origin") or ""),
        "contactPreference": str(ficha.get("contactPreference") or ""),
        "lastOrder": ultimo,
        "registeredAt": ficha.get("createdAt"),
        "daysSinceRegistration": _dias_desde(ficha.get("createdAt"), ahora),
        "daysSinceLastPurchase": dias_compra,
        "daysSinceLastContact": dias_contacto,
        "lastContactAt": _ultimo_contacto(ficha),
        "situation": situacion,
        "situationLabel": ETIQUETAS_SITUACION[situacion],
        "urgent": _es_urgente(situacion),
        "priority": _prioridad(situacion, dias_compra, dias_contacto, _dias_desde(ficha.get("createdAt"), ahora)),
        "templateKey": situacion if situacion in PLANTILLAS else "",
        "placeholders": {
            "nombre": str(ficha.get("name") or "").split(" ")[0],
            "coach": nombre_coach,
            "producto": (ultimo or {}).get("productName") or "tu último pedido",
            "monto": _formato_monto(monto),
            "folio": (ultimo or {}).get("id") or "",
        },
    }


# --- Invitados (compradores sin ficha) ----------------------------------------

def _pedidos_de_invitados(dias: int = 365) -> dict:
    """Pedidos hechos sin cuenta en los últimos `dias`, agrupados por correo
    (más reciente primero). Se acota con `sk_from` (§0.1): recorrer el bucket
    ORDER entero crecía con el histórico en cada carga de la pantalla."""
    grupos = {}
    desde = (datetime.now(timezone.utc) - timedelta(days=max(1, int(dias)))).strftime("%Y-%m-%d")
    try:
        for pedido in utils._query_bucket("ORDER", sk_from=desde) or []:
            if pedido.get("customerId") not in (None, "", 0, "0"):
                continue
            correo = utils._normalize_email(pedido.get("email"))
            if not correo:
                continue
            grupos.setdefault(correo, []).append(pedido)
    except Exception as ex:
        utils._log_error("seguimiento_guest_orders_error", ex)
    for correo in grupos:
        grupos[correo].sort(key=lambda p: str(p.get("createdAt") or ""), reverse=True)
    return grupos


def _fila_invitado(correo: str, pedidos: list, ahora: datetime, cfg: dict, nombre_coach: str) -> dict:
    ultimo_pedido = pedidos[0]
    contacto = utils._get_by_id("GUEST_CONTACT", correo) or {}
    notas = contacto.get("notes") or []
    ficha_virtual = {"createdAt": pedidos[-1].get("createdAt"), "lastContactAt": contacto.get("lastContactAt"),
                     "contactNotes": notas, "clabeInterbancaria": "x"}
    situacion, tardio = _situacion(ficha_virtual, pedidos, ahora, cfg, 0.0)
    ultima_compra = next((p.get("createdAt") for p in pedidos if str(p.get("status") or "").lower() in _ESTADOS_COMPRA), None)
    dias_compra = _dias_desde(ultima_compra, ahora)
    dias_contacto = _dias_desde(_ultimo_contacto(ficha_virtual), ahora)
    ultimo = _resumen_pedido(tardio or ultimo_pedido)
    telefono = str(ultimo_pedido.get("phone") or (ultimo_pedido.get("shippingAddress") or {}).get("phone") or "").strip()
    nombre = str(ultimo_pedido.get("customerName") or ultimo_pedido.get("recipientName") or correo)
    return {
        "customerId": "",
        "isGuest": True,
        "email": correo,
        "name": nombre,
        "mode": "invitado",
        "phone": telefono,
        "whatsappUrl": _whatsapp_url(telefono),
        "sponsorName": "",
        "executiveId": "",
        "executiveName": "",
        "origin": "invitado",
        "contactPreference": "",
        "lastOrder": ultimo,
        "registeredAt": pedidos[-1].get("createdAt"),
        "daysSinceRegistration": _dias_desde(pedidos[-1].get("createdAt"), ahora),
        "daysSinceLastPurchase": dias_compra,
        "daysSinceLastContact": dias_contacto,
        "lastContactAt": _ultimo_contacto(ficha_virtual),
        "situation": situacion,
        "situationLabel": ETIQUETAS_SITUACION[situacion],
        "urgent": _es_urgente(situacion),
        "priority": _prioridad(situacion, dias_compra, dias_contacto, _dias_desde(pedidos[-1].get("createdAt"), ahora)),
        "templateKey": situacion if situacion in PLANTILLAS else "",
        "orderCount": len(pedidos),
        "placeholders": {
            "nombre": nombre.split(" ")[0],
            "coach": nombre_coach,
            "producto": (ultimo or {}).get("productName") or "tu último pedido",
            "monto": _formato_monto((ultimo or {}).get("total", 0)),
            "folio": (ultimo or {}).get("id") or "",
        },
    }


# --- Handlers -----------------------------------------------------------------

def _nombre_actor(headers: dict, actor: dict, ejecutivas: dict) -> str:
    h = headers or {}
    nombre = str(h.get("x-user-name") or h.get("X-User-Name") or "").strip()
    if nombre:
        return nombre
    empleada = ejecutivas.get(str(actor.get("user_id") or ""))
    return str((empleada or {}).get("name") or "tu coach")


def firmar_nota(headers: dict, actor: Optional[dict] = None) -> str:
    """Nombre con el que se firma una nota de bitácora (propuesta 12).

    *"Si mañana Mireya lee «1803978000111», no sabe si fui yo o Alma, y le
    vuelve a escribir a Julio. Para eso, me sigo yendo con mi libreta."*
    (`gaby-2027-03-08.md`)

    Se resuelve **al escribir** y se guarda junto al id, nunca al leer: la
    vista Clientes no carga empleados y la coach no tiene privilegio para
    verlos, así que resolver al leer serían N nombres por ficha (un N+1) y
    encima con 403. Si no hay de dónde sacar el nombre devuelve cadena vacía
    y la pantalla cae al id, que es lo que hay hoy.

    El nombre sale de la **sesión** o de la ficha, nunca del encabezado
    `x-user-name`: ese lo escribe quien llama, y con él la bitácora podía
    firmarse con cualquier nombre —una nota escrita por Mireya quedaba a
    nombre de Alma— que es justo lo contrario de para lo que se puso la firma.
    """
    h = headers or {}
    actor = actor if isinstance(actor, dict) else utils._extract_actor(h)
    nombre = str(actor.get("name") or "").strip()
    if nombre:
        return nombre
    uid = str(actor.get("user_id") or "").strip()
    if not uid:
        return ""
    try:
        empleada = utils._get_by_id("EMPLOYEE", int(uid))
    except (TypeError, ValueError):
        empleada = None
    except Exception as ex:  # noqa: BLE001 - firmar nunca debe tumbar la nota
        utils._log_error("nota_firma_error", ex)
        empleada = None
    if empleada and empleada.get("name"):
        return str(empleada["name"]).strip()
    try:
        ficha = utils._get_by_id("CUSTOMER", utils._customer_entity_id(uid))
    except Exception as ex:  # noqa: BLE001
        utils._log_error("nota_firma_error", ex)
        ficha = None
    return str((ficha or {}).get("name") or "").strip()


def _es_cartera_por_defecto(actor: dict, cfg: dict) -> bool:
    """La cartera FindingU (sin patrocinadora ni ejecutiva) es de la ejecutiva por
    defecto; si no hay una configurada, de cualquier admin o empleada con la pantalla."""
    por_defecto = str(cfg.get("defaultExecutiveId") or "").strip()
    if actor.get("role") == "admin" or not por_defecto:
        return True
    return str(actor.get("user_id") or "") == por_defecto


def handle_seguimiento_hoy(query: dict, headers: dict) -> dict:
    """GET /customers/seguimiento/hoy?scope=mine|all&situation=&limit="""
    err = utils._require_admin(headers, PRIVILEGIO)
    if err:
        return err
    query = query or {}
    alcance = "all" if str(query.get("scope") or "mine").lower() == "all" else "mine"
    filtro = str(query.get("situation") or "").strip().lower()
    if filtro and filtro not in SITUACIONES:
        return utils._json_response(400, {"message": f"situation debe ser una de: {', '.join(SITUACIONES)}"})
    try:
        limite = max(1, min(int(query.get("limit") or 200), 500))
    except (TypeError, ValueError):
        limite = 200

    actor = utils._extract_actor(headers)
    actor_id = str(actor.get("user_id") or "")
    cfg = _config()
    ahora = datetime.now(timezone.utc)
    ejecutivas = _ejecutivas()
    nombre_coach = _nombre_actor(headers, actor, ejecutivas)
    cartera_defecto = _es_cartera_por_defecto(actor, cfg)
    confirmados = _ledgers_confirmados()

    fichas = [c for c in utils._query_bucket("CUSTOMER") if isinstance(c, dict) and c.get("customerId") is not None]
    patrocinadores = {str(c.get("customerId")): c for c in fichas}
    excluidos = {"doNotContact": 0, "otherExecutive": 0}
    filas = []

    def _es_mia(ejecutiva_id) -> bool:
        """"Mi cartera": las asignadas a la actora más las que nadie tiene asignadas
        (cartera FindingU) cuando ella es la ejecutiva por defecto. Tener
        patrocinadora no saca a nadie de la lista: la socia vende, la coach recupera."""
        if alcance == "all":
            return True
        if ejecutiva_id and ejecutiva_id == actor_id:
            return True
        return (not ejecutiva_id) and cartera_defecto

    for ficha in fichas:
        if ficha.get("deletedAt"):
            continue
        if ficha.get("doNotContact"):
            excluidos["doNotContact"] += 1
            continue
        if not _es_mia(str(ficha.get("executiveId") or "")):
            excluidos["otherExecutive"] += 1
            continue
        filas.append(_fila_cliente(ficha, ahora, cfg, ejecutivas, patrocinadores, confirmados, nombre_coach))

    correos_con_ficha = {utils._normalize_email(c.get("email")) for c in fichas if c.get("email")}
    # Un invitado más viejo que el doble de "frío" ya no es un seguimiento de hoy.
    for correo, pedidos in _pedidos_de_invitados(dias=_entero(cfg.get("coldDays"), 30) * 2).items():
        if correo in correos_con_ficha:
            continue
        if not _es_mia(""):
            excluidos["otherExecutive"] += 1
            continue
        filas.append(_fila_invitado(correo, pedidos, ahora, cfg, nombre_coach))

    if filtro:
        filas = [f for f in filas if f["situation"] == filtro]
    else:
        filas = [f for f in filas if f["situation"] != "activa"]
    filas.sort(key=lambda f: (not f["urgent"], -f["priority"], f["name"].lower()))

    return utils._json_response(200, {
        "date": ahora.date().isoformat(),
        "scope": alcance,
        "executiveId": actor_id,
        "coachName": nombre_coach,
        "rows": filas[:limite],
        "total": len(filas),
        "excluded": excluidos,
        "executives": [
            {"id": eid, "name": str(e.get("name") or ""), "active": e.get("active") is not False}
            for eid, e in sorted(ejecutivas.items(), key=lambda kv: str(kv[1].get("name") or "").lower())
        ],
        "thresholds": {
            "coldDays": _entero(cfg.get("coldDays"), 30),
            "welcomeDays": _entero(cfg.get("welcomeDays"), 7),
            "lateOrderDays": _entero(cfg.get("lateOrderDays"), 5),
        },
    })


def handle_plantillas(headers: dict) -> dict:
    """GET /customers/seguimiento/plantillas"""
    err = utils._require_admin(headers, PRIVILEGIO)
    if err:
        return err
    return utils._json_response(200, {"templates": _plantillas(), "placeholders": list(PLACEHOLDERS)})


def _texto_nota(canal: str, plantilla: str, mensaje: str) -> str:
    encabezado = ETIQUETAS_CANAL.get(canal, canal)
    if plantilla:
        encabezado += f" · plantilla {ETIQUETAS_SITUACION.get(plantilla, plantilla).lower()}"
    return f"{encabezado}: {mensaje}"[:1000]


def handle_contacto(customer_id, body: dict, headers: dict) -> dict:
    """POST /customers/{id}/contacto — anota el contacto y devuelve el enlace wa.me.

    Para invitados sin ficha: `id = "invitado"` y `guestEmail` en el cuerpo; la
    nota se guarda en GUEST_CONTACT y se migra a la ficha cuando se crea.
    """
    err = utils._require_admin(headers, PRIVILEGIO)
    if err:
        return err
    body = body or {}
    canal = str(body.get("channel") or "whatsapp").strip().lower()
    if canal not in CANALES:
        return utils._json_response(400, {"message": "channel debe ser whatsapp, email o call"})
    plantilla = str(body.get("templateKey") or "").strip().lower()
    if plantilla and plantilla not in PLANTILLAS:
        return utils._json_response(400, {"message": f"templateKey desconocida: {plantilla}"})
    mensaje = str(body.get("message") or "").strip()
    if not mensaje:
        return utils._json_response(400, {"message": "Escribe el mensaje que vas a mandar; es lo que queda en la bitácora."})

    actor = utils._extract_actor(headers)
    ahora = utils._now_iso()
    nota = {"text": _texto_nota(canal, plantilla, mensaje), "by": str(actor.get("user_id") or "admin"),
            "byName": firmar_nota(headers, actor), "at": ahora, "channel": canal, "templateKey": plantilla}

    if str(customer_id) == "invitado":
        correo = utils._normalize_email(body.get("guestEmail"))
        if not correo:
            return utils._json_response(400, {"message": "guestEmail es obligatorio para un invitado"})
        pedidos = _pedidos_de_invitados().get(correo) or []
        if not pedidos:
            return utils._json_response(404, {"message": "No hay pedidos de invitado con ese correo"})
        registro = utils._get_by_id("GUEST_CONTACT", correo)
        notas = list((registro or {}).get("notes") or [])
        notas.append(nota)
        if registro:
            utils._update_by_id("GUEST_CONTACT", correo, "SET notes = :n, lastContactAt = :t, updatedAt = :t",
                                {":n": notas[-200:], ":t": ahora})
        else:
            utils._put_entity("GUEST_CONTACT", correo, {"entityType": "guestContact", "email": correo,
                                                        "notes": notas, "lastContactAt": ahora, "createdAt": ahora})
        telefono = pedidos[0].get("phone") or (pedidos[0].get("shippingAddress") or {}).get("phone")
        return utils._json_response(201, {
            "note": nota, "whatsappUrl": _whatsapp_url(telefono, mensaje if canal == "whatsapp" else None),
            "guestEmail": correo, "lastContactAt": ahora,
        })

    cid = utils._customer_entity_id(customer_id)
    ficha = utils._get_by_id("CUSTOMER", cid)
    if not ficha:
        return utils._json_response(404, {"message": "Cliente no encontrado"})
    if ficha.get("doNotContact"):
        return utils._json_response(409, {"message": "Este cliente pidió que no se le contacte; la nota no se guardó.",
                                          "code": "doNotContact"})
    notas = list(ficha.get("contactNotes") or [])
    notas.append(nota)
    utils._update_by_id("CUSTOMER", cid, "SET contactNotes = :n, lastContactAt = :t, updatedAt = :t",
                        {":n": notas[-200:], ":t": ahora})
    return utils._json_response(201, {
        "note": nota,
        "whatsappUrl": _whatsapp_url(ficha.get("phone"), mensaje if canal == "whatsapp" else None),
        "customerId": str(ficha.get("customerId") or cid),
        "customerName": str(ficha.get("name") or ""),
        "lastContactAt": ahora,
    })


def handle_ficha_invitado(body: dict, headers: dict) -> dict:
    """POST /customers/seguimiento/ficha-invitado — crea la ficha de un comprador invitado.

    Modo cliente, origen `invitado`, sin acceso (no se crea AUTH): la persona
    puede registrarse después con el mismo correo y su cuenta hereda la ficha.
    Sus pedidos quedan ligados con `_vincular_pedidos_de_invitado`.
    """
    err = utils._require_admin(headers, PRIVILEGIO)
    if err:
        return err
    correo = utils._normalize_email((body or {}).get("email"))
    if not correo:
        return utils._json_response(400, {"message": "email es obligatorio"})
    existente = utils._find_customer_id_by_email(correo)
    if existente not in (None, ""):
        return utils._json_response(409, {"message": "Ese correo ya tiene ficha de cliente", "customerId": str(existente)})
    pedidos = _pedidos_de_invitados().get(correo) or []
    if not pedidos:
        return utils._json_response(404, {"message": "No hay pedidos de invitado con ese correo"})

    ultimo = pedidos[0]
    ahora = utils._now_iso()
    customer_id = int(datetime.now(timezone.utc).timestamp() * 1000)
    nombre = str(ultimo.get("customerName") or ultimo.get("recipientName") or correo).strip()
    telefono = str(ultimo.get("phone") or (ultimo.get("shippingAddress") or {}).get("phone") or "").strip() or None
    contacto = utils._get_by_id("GUEST_CONTACT", correo) or {}
    notas = list(contacto.get("notes") or [])
    item = {
        "entityType": "customer", "customerId": customer_id, "name": nombre, "email": correo,
        "phone": telefono, "city": ultimo.get("city"), "leaderId": None,
        "isAssociate": False, "mode": "cliente", "canAccessAdmin": False, "privileges": utils._normalize_privileges({}),
        "activeBuyer": False, "discountRate": utils.D_ZERO, "discount": "0%", "commissions": utils.D_ZERO,
        "origin": "invitado", "contactPreference": "whatsapp" if telefono else "email",
        "contactNotes": notas, "lastContactAt": contacto.get("lastContactAt"),
        "createdAt": pedidos[-1].get("createdAt") or ahora, "updatedAt": ahora,
        "guestProfileCreatedAt": ahora,
    }
    principal = utils._put_entity("CUSTOMER", customer_id, item, created_at_iso=item["createdAt"])
    utils._upsert_customer_name_index(customer_id, nombre, correo, created_at_iso=item["createdAt"])
    utils._upsert_customer_email_index(customer_id, correo)

    import auth_utils as identidad  # mismo CodeUri; se importa aquí para no cargar el login al arrancar
    ligados = identidad._vincular_pedidos_de_invitado(customer_id, correo)

    import customer_lambda
    salida = customer_lambda._format_customer_output(principal)
    utils._audit_event("customer.guest_profile.create", headers, {"email": correo},
                       {"customerId": customer_id, "linkedOrders": len(ligados)})
    return utils._json_response(201, {"customer": salida, "linkedOrders": ligados})


# --- Enganche en customer_lambda ----------------------------------------------

def atender(request) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = list(request.segments or [])
    if seg[:1] == ["customers"]:
        seg = seg[1:]
    metodo = request.method
    if len(seg) == 2 and seg[0] == "seguimiento":
        if seg[1] == "hoy" and metodo == "GET":
            return handle_seguimiento_hoy(request.query, request.headers)
        if seg[1] == "plantillas" and metodo == "GET":
            return handle_plantillas(request.headers)
        if seg[1] == "ficha-invitado" and metodo == "POST":
            return handle_ficha_invitado(request.body, request.headers)
    if len(seg) == 2 and seg[1] == "contacto" and metodo == "POST":
        return handle_contacto(seg[0], request.body, request.headers)
    return None
