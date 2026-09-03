"""Paquete A · pagos-comisiones (propuestas 4, 12 y 22 del doc 22).

Que el día de pago sea **una pantalla**, no dieciséis fichas: la gerente ve
quién cobra cuánto, exporta el archivo para el banco, sube un comprobante por
lote y marca pagados en bloque; el sistema pide la CLABE a la socia antes de
que haga falta y avisa a tiempo lo que está por perderse por no activarse.

Rutas (prefijo `/commissions`, todas con `commissions_register_payment`):

    GET  /pagos?month=YYYY-MM          estado de pago por beneficiaria
    GET  /pagos/dispersion.csv?month=  archivo para el banco (solo las listas)
    POST /pagos/lote                   un comprobante, N pagos
    POST /pagos/pedir-clabe            recordatorio manual de CLABE
    POST /avisos/bloqueadas            tarea programable (días 20 y 27)

El motor (`commissions_lambda`) se importa de forma perezosa: él mismo importa
este módulo al final de su archivo para colgar las rutas, y un import circular
en tiempo de carga dejaría a uno de los dos a medias.
"""
import calendar
import csv
import io
import math
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import core_utils as utils

Ruta = utils.routing.Ruta

PRIVILEGIO = "commissions_register_payment"
PORTAL_URL = os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx").rstrip("/")
ENLACE_COMISIONES = f"{PORTAL_URL}/#/dashboard#comisiones"
ENLACE_TIENDA = f"{PORTAL_URL}/#/tienda"

_RE_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _motor():
    """`commissions_lambda`, importado cuando hace falta (ver docstring del módulo)."""
    import commissions_lambda
    return commissions_lambda


# ---------------------------------------------------------------------------
# Utilidades de fecha, dinero y fichas
# ---------------------------------------------------------------------------

def _hoy() -> str:
    """Fecha de hoy (YYYY-MM-DD) tomada del reloj que usa todo el backend."""
    return utils._now_iso()[:10]


def _mes_anterior(month_key: str) -> str:
    anio, mes = int(month_key[:4]), int(month_key[5:7])
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def _ultimo_dia_mes(month_key: str) -> str:
    anio, mes = int(month_key[:4]), int(month_key[5:7])
    return f"{month_key}-{calendar.monthrange(anio, mes)[1]:02d}"


def _mes_valido(month_key) -> bool:
    return bool(month_key) and bool(_RE_MES.match(str(month_key)))


def _pesos(valor) -> str:
    return f"${float(utils._to_decimal(valor)):,.2f}"


def _ficha(customer_id) -> dict:
    return utils._get_by_id("CUSTOMER", utils._customer_entity_id(customer_id)) or {}


def _clabe_de(ficha: dict) -> str:
    return re.sub(r"\D", "", str(ficha.get("clabeInterbancaria") or ""))


def _clabe_enmascarada(clabe: str) -> str:
    """`••••••••••••••1234`: en pantalla nunca se ve la CLABE completa."""
    clabe = clabe or ""
    if len(clabe) <= 4:
        return "•" * len(clabe)
    return "•" * (len(clabe) - 4) + clabe[-4:]


def _nombre_pila(ficha: dict) -> str:
    return (str(ficha.get("name") or "").strip().split(" ") or [""])[0] or "Hola"


def _meses_contables(month_key: str) -> list:
    """Meses contables de `month_key` (la partición se recorre entera: su SK es
    por beneficiaria, no por fecha)."""
    marca = f"#MONTH#{month_key}"
    return [
        item for item in utils._query_bucket("COMMISSION_MONTH")
        if marca in str(item.get("SK") or "") and str(item.get("beneficiaryId") or "")
    ]


def _recibos_pagados(month_key: str) -> dict:
    """Último comprobante vigente (`paid`, no anulado) por beneficiaria."""
    recibos = {}
    for r in utils._query_bucket("COMMISSION_RECEIPT", sk_from=month_key):
        if str(r.get("monthKey")) != str(month_key) or r.get("status") != "paid":
            continue
        cid = str(r.get("customerId"))
        if cid not in recibos or str(r.get("createdAt") or "") > str(recibos[cid].get("createdAt") or ""):
            recibos[cid] = r
    return recibos


# ---------------------------------------------------------------------------
# Estado de pagos del mes
# ---------------------------------------------------------------------------

def estado_pagos(month_key: str) -> dict:
    """Una fila por beneficiaria con `totalConfirmed > 0` y su estado:
    `pagado` (mes contable PAID), `sin_clabe` (no hay CLABE en la ficha) o
    `listo` (se puede depositar)."""
    recibos = _recibos_pagados(month_key)
    filas = []
    for item in _meses_contables(month_key):
        confirmado = utils._to_decimal(item.get("totalConfirmed", 0))
        if confirmado <= 0:
            continue
        cid = str(item.get("beneficiaryId"))
        ficha = _ficha(cid)
        clabe = _clabe_de(ficha)
        recibo = recibos.get(cid) or {}
        if str(item.get("status") or "").upper() == "PAID":
            estado = "pagado"
        elif not clabe:
            estado = "sin_clabe"
        else:
            estado = "listo"
        filas.append({
            "customerId": cid,
            "name": str(ficha.get("name") or f"Cliente {cid}"),
            "email": str(ficha.get("email") or ""),
            "phone": str(ficha.get("phone") or ""),
            "amount": float(confirmado),
            "clabeMasked": _clabe_enmascarada(clabe),
            "bankInstitution": str(ficha.get("bankInstitution") or ""),
            "status": estado,
            "receiptUrl": str(recibo.get("assetUrl") or ""),
            "paidAt": item.get("paidAt") or recibo.get("createdAt"),
            "batchId": recibo.get("batchId"),
            "clabeReminderAt": item.get("clabeReminderAt"),
            "doNotContact": bool(ficha.get("doNotContact")),
        })
    filas.sort(key=lambda f: ({"listo": 0, "sin_clabe": 1, "pagado": 2}[f["status"]], f["name"].lower()))

    totales = {"listo": {"count": 0, "amount": 0.0}, "sinClabe": {"count": 0, "amount": 0.0}, "pagado": {"count": 0, "amount": 0.0}}
    clave = {"listo": "listo", "sin_clabe": "sinClabe", "pagado": "pagado"}
    for f in filas:
        t = totales[clave[f["status"]]]
        t["count"] += 1
        t["amount"] = round(t["amount"] + f["amount"], 2)
    return {"monthKey": month_key, "rows": filas, "totals": totales}


def handle_pagos_mes(peticion) -> dict:
    """GET /commissions/pagos?month=YYYY-MM"""
    mes = peticion.query.get("month") or _mes_anterior(utils._month_key())
    if not _mes_valido(mes):
        return utils._json_response(400, {"message": "El mes debe tener la forma AAAA-MM (por ejemplo 2026-08)."})
    return utils._json_response(200, estado_pagos(mes))


def handle_dispersion_csv(peticion) -> dict:
    """GET /commissions/pagos/dispersion.csv?month= — archivo para el banco.

    Lleva la CLABE completa (es el archivo que se sube al portal bancario);
    en pantalla siempre va enmascarada. Solo las filas `listo`.
    """
    mes = peticion.query.get("month") or _mes_anterior(utils._month_key())
    if not _mes_valido(mes):
        return utils._json_response(400, {"message": "El mes debe tener la forma AAAA-MM (por ejemplo 2026-08)."})
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(["CLABE", "Beneficiario", "Monto", "Concepto", "Referencia", "Email"])
    for fila in estado_pagos(mes)["rows"]:
        if fila["status"] != "listo":
            continue
        escritor.writerow([
            _clabe_de(_ficha(fila["customerId"])), fila["name"], f"{fila['amount']:.2f}",
            f"Comisiones {mes} Finding'U", fila["customerId"], fila["email"],
        ])
    cabeceras = utils._cors_headers("text/csv; charset=utf-8")
    cabeceras["Content-Disposition"] = f'attachment; filename="dispersion-{mes}.csv"'
    return {"statusCode": 200, "headers": cabeceras, "body": salida.getvalue()}


# ---------------------------------------------------------------------------
# Pago por lote
# ---------------------------------------------------------------------------

def handle_pago_lote(peticion) -> dict:
    """POST /commissions/pagos/lote — un comprobante para N beneficiarias.

    Sube el archivo **una vez**, crea un COMMISSION_RECEIPT por beneficiaria
    con `batchId`, marca cada mes PAID y manda el correo de depósito. Las
    filas que no cumplen (sin CLABE, ya pagada, sin confirmado) se saltan con
    su código; nunca se marca pagada una socia sin CLABE.
    """
    body = peticion.body or {}
    mes = body.get("monthKey") or body.get("month")
    ids = body.get("customerIds")
    nombre = str(body.get("name") or "").strip()
    contenido = body.get("contentBase64")
    if not _mes_valido(mes) or not nombre or not contenido:
        return utils._json_response(400, {"message": "Faltan datos: monthKey (AAAA-MM), name y contentBase64 del comprobante."})
    if not isinstance(ids, list) or not [c for c in ids if str(c or "").strip()]:
        return utils._json_response(409, {"message": "Selecciona al menos una comisión lista para depositar.", "code": "EMPTY_SELECTION"})

    motor = _motor()
    ids_unicos = []
    for c in ids:
        c = str(c).strip()
        if c and c not in ids_unicos:
            ids_unicos.append(c)

    try:
        asset = motor._upload_receipt_s3(nombre, contenido, body.get("contentType") or "application/pdf", "comprobantes")
    except ValueError:
        return utils._json_response(400, {"message": "El comprobante no se pudo leer (contentBase64 inválido)."})

    lote_id = f"LOTE-{utils.uuid.uuid4().hex[:8].upper()}"
    referencia = str(body.get("bankReference") or "").strip()
    pagados, saltados = [], []
    for cid in ids_unicos:
        ledger = utils._get_ledger_month(cid, mes)
        if utils._to_decimal(ledger.get("totalConfirmed", 0)) <= 0:
            saltados.append({"customerId": cid, "code": "NO_CONFIRMED"})
            continue
        codigo = motor._validar_pago(cid, mes)
        if codigo:
            saltados.append({"customerId": cid, "code": codigo})
            continue
        recibo = motor._registrar_pago(cid, mes, asset, batch_id=lote_id, bank_reference=referencia or None)
        pagados.append({"customerId": cid, "receiptId": recibo.get("receiptId"),
                        "amount": float(utils._to_decimal(ledger.get("totalConfirmed", 0)))})

    total = round(sum(p["amount"] for p in pagados), 2)
    if not pagados:
        return utils._json_response(409, {
            "message": "Ninguna de las seleccionadas se pudo marcar como pagada; revisa los motivos por fila.",
            "code": "NOTHING_PAID", "skipped": saltados, "assetUrl": asset.get("url"),
        })

    actor = utils._extract_actor(peticion.headers or {})
    ahora = utils._now_iso()
    lote = {
        "entityType": "commissionPaymentBatch", "batchId": lote_id, "monthKey": mes,
        "assetId": asset.get("assetId"), "assetUrl": asset.get("url"), "bankReference": referencia,
        "customerIds": [p["customerId"] for p in pagados], "totalPaid": utils._to_decimal(str(total)),
        "skipped": saltados, "createdBy": str(actor.get("user_id") or ""), "createdAt": ahora, "updatedAt": ahora,
    }
    utils._put_entity("COMMISSION_PAYMENT_BATCH", lote_id, lote, created_at_iso=ahora)
    utils._log("commission_batch_paid", "INFO", batchId=lote_id, monthKey=mes, paid=len(pagados), skipped=len(saltados), total=total)
    return utils._json_response(201, {
        "batchId": lote_id, "monthKey": mes, "assetUrl": asset.get("url"),
        "paid": pagados, "skipped": saltados, "totalPaid": total,
    })


# ---------------------------------------------------------------------------
# Aviso "registra tu CLABE"
# ---------------------------------------------------------------------------

def _aviso_panel_clabe(customer_id, month_key: str) -> str:
    """Aviso en el panel dirigido solo a esa socia (uno por mes)."""
    nid = f"NTF-CLABE-{utils._customer_id_str(customer_id)}-{month_key}"
    if utils._get_by_id("NOTIFICATION", nid):
        return nid
    hoy = _hoy()
    # Caduca solo: cuando la socia captura la CLABE no hay hook que lo apague.
    fin_iso = (datetime.strptime(hoy, "%Y-%m-%d") + timedelta(days=45)).strftime("%Y-%m-%d")
    utils._put_entity("NOTIFICATION", nid, {
        "entityType": "notification", "notificationId": nid,
        "title": "Registra tu CLABE para cobrar tus comisiones",
        "description": "Ya tienes comisiones a tu favor. Para depositártelas el día de pago necesitamos tu CLABE interbancaria: captúrala en Comisiones, toma un minuto.",
        "linkUrl": ENLACE_COMISIONES, "linkText": "Registrar mi CLABE",
        "startAt": hoy, "endAt": fin_iso, "active": True,
        "targetCustomerId": utils._customer_id_str(customer_id),
        "createdAt": utils._now_iso(),
    })
    return nid


def _correo_clabe(ficha: dict, monto, motivo: str) -> bool:
    """Correo "Registra tu CLABE para cobrar". Respeta `doNotContact`."""
    para = str(ficha.get("email") or "").strip()
    if not para or ficha.get("doNotContact"):
        return False
    nombre = _nombre_pila(ficha)
    if motivo == "activacion":
        razon = "Acabas de activarte este mes: desde ahora las compras de tu red te generan comisiones."
    else:
        razon = f"Ya tienes <strong>{_pesos(monto)}</strong> en comisiones confirmadas."
    from core.email import _email_shell
    cuerpo = f"""
    <div class="icon">🏦</div>
    <h1 class="title">Registra tu CLABE para cobrar</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. {razon} Para depositártelas el día de pago necesitamos tu CLABE interbancaria (18 dígitos) y tu banco.</p>
    <p class="lead">Se captura una sola vez en tu panel, en la sección Comisiones. Sin CLABE no podemos hacer el depósito y la comisión se queda esperando.</p>
    <p class="lead"><a class="btn" href="{ENLACE_COMISIONES}">Registrar mi CLABE</a></p>"""
    texto = (f"Hola {nombre}. Para depositarte tus comisiones necesitamos tu CLABE interbancaria. "
             f"Captúrala en tu panel, en Comisiones: {ENLACE_COMISIONES}")
    utils._send_ses_email(para, "Registra tu CLABE para cobrar tus comisiones", texto, _email_shell(cuerpo))
    return True


def avisar_clabe_al_activarse(customer_id) -> bool:
    """Primera activación sin CLABE: un solo aviso en la vida de la ficha
    (`clabeReminderFirstAt`)."""
    ficha = _ficha(customer_id)
    if not ficha or _clabe_de(ficha) or ficha.get("clabeReminderFirstAt"):
        return False
    ahora = utils._now_iso()
    try:
        utils._update_by_id("CUSTOMER", utils._customer_entity_id(customer_id),
                            "SET clabeReminderFirstAt = :t", {":t": ahora})
    except Exception as e:  # pragma: no cover
        utils._log("clabe_reminder_flag_error", "ERROR", customer=customer_id, err=e)
    _aviso_panel_clabe(customer_id, utils._month_key())
    _correo_clabe(ficha, 0, "activacion")
    utils._log("clabe_reminder_sent", "INFO", customer=customer_id, reason="activacion")
    return True


def avisar_clabe_por_comision_confirmada(customer_id, month_key: str, order_id: Optional[str] = None) -> bool:
    """Primera comisión confirmada del mes sin CLABE: un aviso por mes
    (`clabeReminderAt` en el mes contable)."""
    ficha = _ficha(customer_id)
    if not ficha or _clabe_de(ficha):
        return False
    ledger = utils._get_ledger_month(customer_id, month_key)
    if ledger.get("clabeReminderAt") or utils._to_decimal(ledger.get("totalConfirmed", 0)) <= 0:
        return False
    if order_id and not any(r.get("orderId") == order_id and r.get("status") == "confirmed" for r in ledger.get("ledger") or []):
        return False
    return enviar_recordatorio_clabe(customer_id, month_key, "comision_confirmada")


def enviar_recordatorio_clabe(customer_id, month_key: str, motivo: str) -> bool:
    ficha = _ficha(customer_id)
    if not ficha:
        return False
    ahora = utils._now_iso()
    ledger = utils._get_ledger_month(customer_id, month_key)
    monto = ledger.get("totalConfirmed", 0)

    def _marcar(item):
        item["clabeReminderAt"] = ahora
        return True

    utils._mutate_ledger_month(customer_id, month_key, _marcar)
    _aviso_panel_clabe(customer_id, month_key)
    enviado = _correo_clabe(ficha, monto, motivo)
    utils._log("clabe_reminder_sent", "INFO", customer=customer_id, month=month_key, reason=motivo, email=enviado)
    return True


def handle_pedir_clabe(peticion) -> dict:
    """POST /commissions/pagos/pedir-clabe — la gerente reenvía el recordatorio."""
    body = peticion.body or {}
    cid = str(body.get("customerId") or "").strip()
    if not cid:
        return utils._json_response(400, {"message": "customerId es obligatorio"})
    ficha = _ficha(cid)
    if not ficha:
        return utils._json_response(404, {"message": "No existe una ficha con ese id."})
    if _clabe_de(ficha):
        return utils._json_response(409, {"message": f"{ficha.get('name') or 'La socia'} ya tiene CLABE registrada; no hace falta pedirla.", "code": "CLABE_PRESENT"})
    mes = body.get("monthKey") or _mes_anterior(utils._month_key())
    if not _mes_valido(mes):
        return utils._json_response(400, {"message": "El mes debe tener la forma AAAA-MM."})
    ahora = utils._now_iso()
    ledger = utils._get_ledger_month(cid, mes)

    def _marcar(item):
        item["clabeReminderAt"] = ahora
        return True

    utils._mutate_ledger_month(cid, mes, _marcar)
    _aviso_panel_clabe(cid, mes)
    correo = _correo_clabe(ficha, ledger.get("totalConfirmed", 0), "recordatorio")

    # Bitácora de contacto de la ficha (la misma que usa Seguimiento).
    actor = utils._extract_actor(peticion.headers or {})
    notas = list(ficha.get("contactNotes") or [])
    notas.append({"text": f"Se pidió la CLABE para pagar comisiones de {mes} ({'correo y panel' if correo else 'solo panel: no contactar por correo'}).",
                  "by": str(actor.get("user_id") or "admin"), "at": ahora})
    try:
        utils._update_by_id("CUSTOMER", utils._customer_entity_id(cid), "SET contactNotes = :n", {":n": notas[-200:]})
    except Exception as e:  # pragma: no cover
        utils._log("clabe_reminder_note_error", "ERROR", customer=cid, err=e)
    return utils._json_response(200, {
        "sent": True, "channel": "email+panel" if correo else "panel",
        "customerId": cid, "name": ficha.get("name"), "email": ficha.get("email") if correo else "",
        "monthKey": mes, "clabeReminderAt": ahora,
    })


# ---------------------------------------------------------------------------
# Avisos de bloqueadas (política 22, opción b)
# ---------------------------------------------------------------------------

def _producto_que_salva(faltan_vp: float, net_volume_mes, tiers: list) -> Optional[dict]:
    """El producto activo más barato que cierra los VP que faltan.

    Para cada producto en tienda con `vpPoints > 0`: la tasa de descuento que
    tendría la compra (acumulado del mes + precio), los VP netos por unidad
    (`vpPoints × (1 − tasa)`), las unidades necesarias y el costo. Se elige el
    menor costo. Misma fórmula que el paquete C (§3.5); I2 las unifica.
    """
    if faltan_vp <= 0:
        return None
    from order_lambda import _resolve_discount_rate
    acumulado = utils._to_decimal(net_volume_mes or 0)
    mejor = None
    for p in utils._query_bucket("PRODUCT"):
        if p.get("active") is False or p.get("inOnlineStore") is False:
            continue
        precio = utils._to_decimal(p.get("price", 0))
        pc = float(utils._to_decimal(p.get("vpPoints", 0)))
        if precio <= 0 or pc <= 0:
            continue
        tasa = float(_resolve_discount_rate(tiers, acumulado + precio))
        vp_neto = pc * (1 - tasa)
        if vp_neto <= 0:
            continue
        unidades = int(math.ceil(faltan_vp / vp_neto - 1e-9))
        costo = round(float(precio) * unidades * (1 - tasa), 2)
        candidato = {"id": str(p.get("productId") or p.get("id") or ""), "name": str(p.get("name") or ""),
                     "price": float(precio), "units": unidades, "cost": costo, "rate": tasa,
                     "vpPerUnit": round(vp_neto, 2), "vpTotal": round(vp_neto * unidades, 2)}
        if mejor is None or (costo, unidades) < (mejor["cost"], mejor["units"]):
            mejor = candidato
    return mejor


def _correo_bloqueadas(ficha: dict, month_key: str, bloqueado, vp_faltan: float, producto: Optional[dict]) -> bool:
    para = str(ficha.get("email") or "").strip()
    if not para or ficha.get("doNotContact"):
        return False
    nombre = _nombre_pila(ficha)
    cierre = _ultimo_dia_mes(month_key)
    dia_cierre = f"{int(cierre[8:10])} de {_nombre_mes(month_key)}"
    if producto:
        unidades = f"{producto['units']} {producto['name']}" if producto["units"] > 1 else f"1 {producto['name']}"
        salva = (f"Te faltan <strong>{vp_faltan:.1f} VP</strong>. Lo más barato que lo cierra: <strong>{unidades}</strong> "
                 f"({_pesos(producto['cost'])} con tu descuento de {int(round(producto['rate'] * 100))} %, "
                 f"+{producto['vpTotal']:.1f} VP).")
        boton = f'<p class="lead"><a class="btn" href="{ENLACE_TIENDA}">Ir a la tienda</a></p>'
    else:
        salva = f"Te faltan <strong>{vp_faltan:.1f} VP</strong> para activarte."
        boton = ""
    from core.email import _email_shell
    cuerpo = f"""
    <div class="icon">⏳</div>
    <h1 class="title">Tienes {_pesos(bloqueado)} en comisiones bloqueadas</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Tu red compró este mes y te generó <strong>{_pesos(bloqueado)}</strong> en comisiones, pero están bloqueadas porque todavía no te activas (20 VP netos en el mes).</p>
    <p class="lead">{salva}</p>
    <p class="lead">Si te activas antes del <strong>{dia_cierre}</strong>, se recalculan y pasan a pendientes o confirmadas; si no, se pierden al cerrar el mes.</p>
    {boton}"""
    texto = (f"Hola {nombre}. Tienes {_pesos(bloqueado)} en comisiones bloqueadas que se pierden el {dia_cierre}. "
             f"Te faltan {vp_faltan:.1f} VP para activarte"
             + (f"; lo más barato que lo cierra: {producto['units']} {producto['name']} ({_pesos(producto['cost'])})." if producto else ".")
             + " Si te activas antes del cierre se recalculan; si no, se pierden.")
    utils._send_ses_email(para, f"Tienes {_pesos(bloqueado)} en comisiones bloqueadas que se pierden el {dia_cierre}", texto, _email_shell(cuerpo))
    return True


_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]


def _nombre_mes(month_key: str) -> str:
    return _MESES[int(month_key[5:7]) - 1]


def avisar_bloqueadas(force: bool = False, dry_run: bool = False) -> dict:
    """Recorre los meses contables del mes en curso con `totalBlocked > 0`;
    a cada socia inactiva le manda el aviso con el producto que la salva.
    Idempotente por día (`blockedNoticeSentDays` en el mes contable)."""
    motor = _motor()
    motor._reset_request_cache()
    cfg = utils._load_app_config()
    rewards = cfg.get("rewards") or {}
    hoy = _hoy()
    dia = int(hoy[8:10])
    mes = hoy[:7]
    dias_aviso = [int(utils._to_decimal(d)) for d in (rewards.get("blockedNoticeDays") or [])]
    if dia not in dias_aviso and not force:
        return {"day": dia, "monthKey": mes, "notified": [], "skipped": "not_notice_day", "noticeDays": dias_aviso}

    mxn_per_vp = utils._mxn_per_vp(cfg)
    activation_vp = float(utils._activation_vp(cfg))
    tiers = rewards.get("discountTiers") or []
    avisadas, ya_avisadas = [], []
    for item in _meses_contables(mes):
        bloqueado = utils._to_decimal(item.get("totalBlocked", 0))
        if bloqueado <= 0:
            continue
        cid = str(item.get("beneficiaryId"))
        if dia in [int(utils._to_decimal(d)) for d in (item.get("blockedNoticeSentDays") or [])]:
            ya_avisadas.append(cid)
            continue
        if motor._is_active(cid, mes, mxn_per_vp, activation_vp):
            continue
        ficha = _ficha(cid)
        if not ficha or ficha.get("doNotContact"):
            continue
        vp = motor._calc_vp(cid, mes, mxn_per_vp)
        faltan = max(activation_vp - vp, 0.0)
        estado_mes = motor._cached_month_state(cid, mes)
        producto = _producto_que_salva(faltan, estado_mes.get("netVolume", 0), tiers)
        if not dry_run:
            _correo_bloqueadas(ficha, mes, bloqueado, faltan, producto)

            def _marcar(ledger, _dia=dia):
                dias = [int(utils._to_decimal(d)) for d in (ledger.get("blockedNoticeSentDays") or [])]
                if _dia in dias:
                    return False
                ledger["blockedNoticeSentDays"] = [utils._to_decimal(d) for d in dias + [_dia]]
                return True

            utils._mutate_ledger_month(cid, mes, _marcar)
        avisadas.append({"customerId": cid, "name": ficha.get("name"), "email": ficha.get("email"),
                         "blocked": float(bloqueado), "vpNow": round(vp, 2), "vpMissing": round(faltan, 2),
                         "product": producto, "closesOn": _ultimo_dia_mes(mes)})
    utils._log("blocked_notices_sent", "INFO", day=dia, month=mes, notified=len(avisadas), dryRun=dry_run)
    return {"day": dia, "monthKey": mes, "notified": avisadas, "alreadyNotified": ya_avisadas, "dryRun": dry_run}


def handle_avisos_bloqueadas(peticion) -> dict:
    """POST /commissions/avisos/bloqueadas — programable (privilegio o superadmin)."""
    body = peticion.body or {}
    return utils._json_response(200, avisar_bloqueadas(force=bool(body.get("force")), dry_run=bool(body.get("dryRun"))))


# ---------------------------------------------------------------------------
# Tabla de rutas y tareas programadas
# ---------------------------------------------------------------------------

RUTAS = [
    Ruta("GET", "pagos", privilegio=PRIVILEGIO,
         descripcion="Pagos del mes: beneficiarias, CLABE enmascarada y estado", handler=handle_pagos_mes),
    Ruta("GET", "pagos/dispersion.csv", privilegio=PRIVILEGIO,
         descripcion="Archivo de dispersión bancaria (CSV, solo listas)", handler=handle_dispersion_csv),
    Ruta("POST", "pagos/lote", privilegio=PRIVILEGIO,
         descripcion="Registrar pago por lote con un comprobante", handler=handle_pago_lote),
    Ruta("POST", "pagos/pedir-clabe", privilegio=PRIVILEGIO,
         descripcion="Reenviar el recordatorio de CLABE a una socia", handler=handle_pedir_clabe),
    Ruta("POST", "avisos/bloqueadas", privilegio=PRIVILEGIO,
         descripcion="Aviso de comisiones bloqueadas (días 20 y 27; programable)", handler=handle_avisos_bloqueadas),
]

#: Rutas que un programador externo (EventBridge → API Gateway con el token de
#: superadmin) o el reloj del harness invocan a diario. Idempotentes por día.
TAREAS_PROGRAMADAS = [("POST", "/commissions/avisos/bloqueadas")]
