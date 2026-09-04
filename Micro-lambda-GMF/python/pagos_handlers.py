"""Paquete A · pagos-comisiones (propuestas 4, 12 y 22 del doc 22).

Que el día de pago sea **una pantalla**, no dieciséis fichas: la gerente ve
quién cobra cuánto, exporta el archivo para el banco, sube un comprobante por
lote y marca pagados en bloque; el sistema pide la CLABE a la socia antes de
que haga falta y avisa a tiempo lo que está por perderse por no activarse.

Rutas (prefijo `/commissions`, todas con `commissions_register_payment`):

    GET  /pagos?month=YYYY-MM          estado de pago por beneficiaria
    GET  /pagos/dispersion.csv?month=  archivo para el banco (solo las listas)
    GET  /pagos/pendientes.csv?month=  anexo de las que faltan, con su motivo
    POST /pagos/lote                   un comprobante, N pagos
    POST /pagos/pedir-clabe            recordatorio manual de CLABE
    POST /pagos/dia-de-pago            correo del día 10 (tarea programada)
    GET  /periodos                     meses con datos y hora del servidor
    POST /avisos/bloqueadas            tarea programable (días 20 y 27)

El motor (`commissions_lambda`) se importa de forma perezosa: él mismo importa
este módulo al final de su archivo para colgar las rutas, y un import circular
en tiempo de carga dejaría a uno de los dos a medias.
"""
import calendar
import csv
import io
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


def _celda_segura(texto) -> str:
    """Excel evalúa como fórmula una celda que empieza por =, +, -, @ (o tab/CR).
    El nombre lo edita la propia socia: se neutraliza con un apóstrofo."""
    texto = str(texto or "")
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def _nombre_pila(ficha: dict) -> str:
    return (str(ficha.get("name") or "").strip().split(" ") or [""])[0] or "Hola"


def _meses_contables(month_key: str) -> list:
    """Meses contables de `month_key`, sirva el esquema que sirva (core.ledger)."""
    return utils._listar_meses_contables(month_key)


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

def texto_base_comision(neto, tasa, importe) -> str:
    """Propuesta 37, §3.2: *"10 % de $1,350.00 netos, sin envío = $135.00"*.

    La redacción la publica el paquete B en `impuestos.py`; mientras no esté
    desplegado se arma aquí con las mismas palabras, para que no haya dos
    versiones del texto en producción.
    """
    try:
        import impuestos  # paquete B
        return impuestos.texto_base_comision(neto, tasa, importe)
    except Exception:
        porcentaje = float(utils._to_decimal(tasa)) * 100
        porcentaje_txt = f"{porcentaje:.0f}" if abs(porcentaje - round(porcentaje)) < 0.05 else f"{porcentaje:.1f}"
        return f"{porcentaje_txt} % de {_pesos(neto)} netos, sin envío = {_pesos(importe)}"


def frase_base_comision() -> str:
    """La frase larga de §3.2, con la base que dice la configuración."""
    try:
        import impuestos  # paquete B
        return impuestos.FRASE_BASE_COMISION
    except Exception:
        rewards = utils._load_app_config().get("rewards") or {}
        con_iva = str(rewards.get("commissionBase") or "neto_con_iva") == "neto_con_iva"
        matiz = "el precio ya con su descuento, con IVA incluido" if con_iva else "el precio ya con su descuento, sin IVA"
        return ("La comisión se calcula sobre el neto que pagó la referida por producto "
                f"—{matiz}— y sin contar el envío.")


def _dias_desde(iso: str) -> int:
    """Días completos entre `iso` y el reloj del servidor (nunca el del navegador)."""
    try:
        inicio = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        hoy = datetime.strptime(_hoy(), "%Y-%m-%d")
        return max((hoy - inicio).days, 0)
    except Exception:
        return 0


def _freno(filas: list, estado: str, texto: str) -> Optional[dict]:
    """El pedido más viejo que retiene ese importe, con sus días.

    "Ninguna columna dice cuántos días llevan parados. 37 días se ven igual
    que 1 día" — y de ese pedido colgaba la comisión de una socia.
    """
    candidatas = [r for r in filas if (r.get("status") or "").lower() == estado and r.get("orderId")]
    if not candidatas:
        return None
    vieja = min(candidatas, key=lambda r: str(r.get("orderCreatedAt") or r.get("createdAt") or ""))
    desde = str(vieja.get("orderCreatedAt") or vieja.get("createdAt") or "")
    return {"orderId": str(vieja.get("orderId")), "desde": desde, "dias": _dias_desde(desde),
            "texto": texto, "pedidos": len({r.get("orderId") for r in candidatas})}


def _detalle_mes(cid, month_key: str, item: dict) -> dict:
    """Las tres cifras del mes con el pedido que frena cada una.

    Alma acabó con tres cifras distintas del mismo concepto ($135 contra
    $259.20) y ninguna pantalla que explicara el paso de una a otra. El ledger
    ya tenía los números; lo que faltaba era publicarlos.
    """
    pendiente = utils._to_decimal(item.get("totalPending", 0))
    bloqueado = utils._to_decimal(item.get("totalBlocked", 0))
    detalle = {"frenoPorConfirmar": None, "frenoBloqueado": None}
    if pendiente > 0 or bloqueado > 0:
        filas = utils._get_ledger_month(cid, month_key).get("ledger") or []
        if pendiente > 0:
            detalle["frenoPorConfirmar"] = _freno(
                filas, "pending", "se confirma cuando el pedido se entrega")
        if bloqueado > 0:
            detalle["frenoBloqueado"] = _freno(
                filas, "blocked", "bloqueada porque no estaba activa en el mes")
    return detalle


def estado_pagos(month_key: str) -> dict:
    """Una fila por beneficiaria con las **tres cifras del mismo dinero**:
    `confirmado` (lo que se deposita), `porConfirmar` (esperando la entrega del
    pedido) y `bloqueado` (sin activación), con el pedido que frena cada
    importe y sus días.

    Estados: `pagado` (mes contable PAID), `sin_clabe` (hay confirmado y no hay
    CLABE), `listo` (se puede depositar) y `por_confirmar` (todavía no hay nada
    que depositar). **Solo las `listo` entran al CSV del banco y al lote**;
    quien tiene 0 confirmados ya no desaparece de la pantalla.
    """
    recibos = _recibos_pagados(month_key)
    filas = []
    for item in _meses_contables(month_key):
        confirmado = utils._to_decimal(item.get("totalConfirmed", 0))
        por_confirmar = utils._to_decimal(item.get("totalPending", 0))
        bloqueado = utils._to_decimal(item.get("totalBlocked", 0))
        if confirmado <= 0 and por_confirmar <= 0 and bloqueado <= 0:
            continue
        cid = str(item.get("beneficiaryId"))
        ficha = _ficha(cid)
        clabe = _clabe_de(ficha)
        recibo = recibos.get(cid) or {}
        if str(item.get("status") or "").upper() == "PAID":
            estado = "pagado"
        elif confirmado <= 0:
            estado = "por_confirmar"
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
            "confirmado": float(confirmado),
            "porConfirmar": float(por_confirmar),
            "bloqueado": float(bloqueado),
            "reconocido": float(confirmado + por_confirmar + bloqueado),
            **_detalle_mes(cid, month_key, item),
            "clabeMasked": _clabe_enmascarada(clabe),
            "bankInstitution": str(ficha.get("bankInstitution") or ""),
            "status": estado,
            "receiptUrl": str(recibo.get("assetUrl") or ""),
            "paidAt": item.get("paidAt") or recibo.get("createdAt"),
            "batchId": recibo.get("batchId"),
            "clabeReminderAt": item.get("clabeReminderAt"),
            "doNotContact": bool(ficha.get("doNotContact")),
        })
    orden = {"listo": 0, "sin_clabe": 1, "por_confirmar": 2, "pagado": 3}
    filas.sort(key=lambda f: (orden[f["status"]], f["name"].lower()))

    totales = {"listo": {"count": 0, "amount": 0.0}, "sinClabe": {"count": 0, "amount": 0.0},
               "pagado": {"count": 0, "amount": 0.0}, "porConfirmarFilas": {"count": 0, "amount": 0.0}}
    clave = {"listo": "listo", "sin_clabe": "sinClabe", "pagado": "pagado", "por_confirmar": "porConfirmarFilas"}
    for f in filas:
        t = totales[clave[f["status"]]]
        t["count"] += 1
        t["amount"] = round(t["amount"] + f["amount"], 2)
    # Las tres columnas del mes y el total reconocido, para que las dos mitades
    # de la pantalla dejen de decir cifras distintas del mismo dinero.
    totales["confirmado"] = round(sum(f["confirmado"] for f in filas), 2)
    totales["porConfirmar"] = round(sum(f["porConfirmar"] for f in filas), 2)
    totales["bloqueado"] = round(sum(f["bloqueado"] for f in filas), 2)
    totales["reconocido"] = round(totales["confirmado"] + totales["porConfirmar"] + totales["bloqueado"], 2)
    return {"monthKey": month_key, "rows": filas, "totals": totales,
            "baseComisionTexto": frase_base_comision()}


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
            _clabe_de(_ficha(fila["customerId"])), _celda_segura(fila["name"]), f"{fila['amount']:.2f}",
            f"Comisiones {mes} Finding'U", fila["customerId"], _celda_segura(fila["email"]),
        ])
    cabeceras = utils._cors_headers("text/csv; charset=utf-8")
    cabeceras["Content-Disposition"] = f'attachment; filename="dispersion-{mes}.csv"'
    return {"statusCode": 200, "headers": cabeceras, "body": salida.getvalue()}


def handle_pendientes_csv(peticion) -> dict:
    """GET /commissions/pagos/pendientes.csv?month= — el anexo de las que faltan.

    Alma perdió el mes entero por una sola socia. El bloqueo del archivo del
    banco está bien hecho y el personal lo elogió: lo que faltaba era llevarse
    la lista de quién falta y por qué. Va como **segundo archivo**, nunca como
    filas más en el layout que se sube al portal bancario (§4.13).
    """
    mes = peticion.query.get("month") or _mes_anterior(utils._month_key())
    if not _mes_valido(mes):
        return utils._json_response(400, {"message": "El mes debe tener la forma AAAA-MM (por ejemplo 2026-08)."})
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(["Nombre", "Monto", "Correo", "Teléfono", "Motivo"])
    for fila in estado_pagos(mes)["rows"]:
        if fila["status"] == "sin_clabe":
            motivo = "Falta su CLABE: no se le puede depositar."
        elif fila["status"] == "por_confirmar":
            freno = fila.get("frenoPorConfirmar") or fila.get("frenoBloqueado") or {}
            dias = f" ({freno['dias']} días)" if freno.get("dias") else ""
            motivo = (f"Sin comisión confirmada todavía: {freno.get('texto') or 'esperando el cierre del pedido'}"
                      f"{(' · pedido ' + freno['orderId'] + dias) if freno.get('orderId') else ''}.")
        else:
            continue
        escritor.writerow([
            _celda_segura(fila["name"]), f"{fila['reconocido']:.2f}",
            _celda_segura(fila["email"]), _celda_segura(fila["phone"]), motivo,
        ])
    cabeceras = utils._cors_headers("text/csv; charset=utf-8")
    cabeceras["Content-Disposition"] = f'attachment; filename="pendientes-{mes}.csv"'
    return {"statusCode": 200, "headers": cabeceras, "body": salida.getvalue()}


# ---------------------------------------------------------------------------
# Periodos: el mes lo manda el servidor (propuesta 17)
# ---------------------------------------------------------------------------

def periodos(month_key: Optional[str] = None) -> dict:
    """Los meses contables **con datos**, el mes por omisión y la hora del servidor.

    Renata recargó Pagos del mes tres veces y marzo de 2027 desaparecía del
    selector: los doce meses se armaban con `new Date()` del navegador, que en
    la corrida iba en 2026-09. Ninguna pantalla de dinero vuelve a construir
    meses con el reloj del cliente (§3.6).

    Recorre el índice de meses **en su propio endpoint**: nunca dentro de
    `/commissions/pagos` ni del dashboard (§4.20).
    """
    resumen = {}
    for item in _meses_contables(None):
        mes = str(item.get("monthKey") or "")
        if not _mes_valido(mes):
            continue
        confirmado = utils._to_decimal(item.get("totalConfirmed", 0))
        pendiente = utils._to_decimal(item.get("totalPending", 0))
        bloqueado = utils._to_decimal(item.get("totalBlocked", 0))
        if confirmado <= 0 and pendiente <= 0 and bloqueado <= 0:
            continue
        fila = resumen.setdefault(mes, {"monthKey": mes, "label": f"{_nombre_mes(mes)} de {mes[:4]}",
                                        "beneficiarias": 0, "confirmado": 0.0, "porConfirmar": 0.0,
                                        "bloqueado": 0.0, "pagados": 0})
        fila["beneficiarias"] += 1
        fila["confirmado"] = round(fila["confirmado"] + float(confirmado), 2)
        fila["porConfirmar"] = round(fila["porConfirmar"] + float(pendiente), 2)
        fila["bloqueado"] = round(fila["bloqueado"] + float(bloqueado), 2)
        if str(item.get("status") or "").upper() == "PAID":
            fila["pagados"] += 1

    lista = sorted(resumen.values(), key=lambda f: f["monthKey"], reverse=True)
    for fila in lista:
        fila["estado"] = "PAID" if fila["pagados"] and fila["pagados"] == fila["beneficiarias"] else "IN_PROGRESS"
        del fila["pagados"]

    ahora = utils._now_iso()
    vigente = ahora[:7]
    # El mes que se paga: el anterior al vigente si tiene datos; si no, el más
    # reciente que sí los tenga. Nunca un mes vacío sin decirlo.
    anterior = _mes_anterior(vigente)
    con_datos = [f["monthKey"] for f in lista]
    if anterior in con_datos:
        por_omision = anterior
    elif con_datos:
        por_omision = con_datos[0]
    else:
        por_omision = anterior
    return {"serverNow": ahora, "mesContableVigente": vigente, "defaultMonth": por_omision,
            "payoutDay": _dia_de_pago(), "periodos": lista}


def handle_periodos(peticion) -> dict:
    """GET /commissions/periodos"""
    return utils._json_response(200, periodos())


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

    # Primero se valida y solo después se sube el comprobante: un doble clic
    # (todas ALREADY_PAID) dejaba un archivo huérfano en S3 por intento.
    pagables, saltados = [], []
    for cid in ids_unicos:
        ledger = utils._get_ledger_month(cid, mes)
        if utils._to_decimal(ledger.get("totalConfirmed", 0)) <= 0:
            saltados.append({"customerId": cid, "code": "NO_CONFIRMED"})
            continue
        codigo = motor._validar_pago(cid, mes)
        if codigo:
            saltados.append({"customerId": cid, "code": codigo})
            continue
        pagables.append((cid, ledger))
    if not pagables:
        return utils._json_response(409, {
            "message": "Ninguna de las seleccionadas se pudo marcar como pagada; revisa los motivos por fila.",
            "code": "NOTHING_PAID", "skipped": saltados,
        })

    try:
        asset = motor._upload_receipt_s3(nombre, contenido, body.get("contentType") or "application/pdf", "comprobantes")
    except ValueError:
        return utils._json_response(400, {"message": "El comprobante no se pudo leer (contentBase64 inválido)."})

    lote_id = f"LOTE-{utils.uuid.uuid4().hex[:8].upper()}"
    referencia = str(body.get("bankReference") or "").strip()
    pagados = []
    for cid, ledger in pagables:
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

#: Propuesta 2: el aviso del portal dice lo mismo que el correo, que ya
#: distinguía los dos casos. "Ya tienes comisiones a tu favor" con $0.00 y la
#: red vacía es lo único que le tiró la confianza a Ximena en todos los
#: números buenos del sitio. Por motivo: texto, y a los cuántos días caduca.
_TEXTOS_AVISO_CLABE = {
    "activacion": (
        "Acabas de activarte este mes: desde hoy las compras de tu red te generan comisiones. "
        "Registra tu CLABE para cobrarlas.",
        30,
    ),
    "comision": (
        "Ya tienes {monto} en comisiones confirmadas. Para depositártelas el día {dia} necesitamos tu CLABE.",
        45,
    ),
}


def _motivo_aviso(motivo: str) -> str:
    """`activacion` o `comision`: el recordatorio manual y el de comisión
    confirmada cuentan lo mismo (hay dinero), y por eso comparten texto."""
    return "activacion" if str(motivo or "") == "activacion" else "comision"


def _dia_de_pago() -> int:
    return int(utils._to_decimal((utils._load_app_config().get("rewards") or {}).get("payoutDay") or 10))


def _aviso_panel_clabe(customer_id, month_key: str, motivo: str = "comision") -> str:
    """Aviso en el panel dirigido solo a esa socia, uno por mes **y por motivo**.

    Con el id anterior (`NTF-CLABE-<cliente>-<mes>`), quien recibía el aviso de
    activación no veía nunca el de comisión de verdad.
    """
    clave = _motivo_aviso(motivo)
    nid = f"NTF-CLABE-{utils._customer_id_str(customer_id)}-{month_key}-{clave}"
    if utils._get_by_id("NOTIFICATION", nid):
        return nid
    hoy = _hoy()
    plantilla, dias = _TEXTOS_AVISO_CLABE[clave]
    monto = utils._to_decimal(utils._get_ledger_month(customer_id, month_key).get("totalConfirmed", 0))
    texto = plantilla.format(monto=_pesos(monto), dia=_dia_de_pago())
    titulo = ("Registra tu CLABE: ya te activaste" if clave == "activacion"
              else "Registra tu CLABE para cobrar tus comisiones")
    # Caduca solo: cuando la socia captura la CLABE no hay hook que lo apague.
    fin_iso = (datetime.strptime(hoy, "%Y-%m-%d") + timedelta(days=dias)).strftime("%Y-%m-%d")
    utils._put_entity("NOTIFICATION", nid, {
        "entityType": "notification", "notificationId": nid,
        "title": titulo,
        "description": texto,
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
        razon = "Acabas de activarte este mes: desde hoy las compras de tu red te generan comisiones."
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
    _aviso_panel_clabe(customer_id, utils._month_key(), "activacion")
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
    _aviso_panel_clabe(customer_id, month_key, motivo)
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
    _aviso_panel_clabe(cid, mes, "recordatorio")
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

    Ola B (I2): la fórmula vive en una sola función,
    `checkout_handlers.sugerir_producto_activacion` (la misma que usa
    "Completa tu activación" en el carrito), para que el correo del día 20 y
    el carrito nunca sugieran productos distintos. Aquí solo se arma la tasa
    de descuento con el acumulado del mes y se traduce la respuesta a las
    claves que usa el correo (`id`, `rate`, `vpPerUnit`, `vpTotal`).
    """
    if faltan_vp <= 0:
        return None
    from order_lambda import _resolve_discount_rate
    import checkout_handlers
    acumulado = utils._to_decimal(net_volume_mes or 0)
    productos = [
        p for p in utils._query_bucket("PRODUCT")
        if p.get("active") is not False and p.get("inOnlineStore") is not False
    ]

    def _tasa(precio):
        return _resolve_discount_rate(tiers, acumulado + utils._to_decimal(precio))

    mejor = checkout_handlers.sugerir_producto_activacion(productos, faltan_vp, _tasa)
    if not mejor:
        return None
    tasa = float(mejor.get("discountRate") or 0)
    vp_unidad = float(mejor.get("netVpPerUnit") or 0)
    unidades = int(mejor.get("units") or 0)
    return {"id": str(mejor.get("productId") or ""), "name": str(mejor.get("name") or ""),
            "price": float(mejor.get("price") or 0), "units": unidades, "cost": float(mejor.get("cost") or 0),
            "rate": tasa, "vpPerUnit": round(vp_unidad, 2), "vpTotal": round(vp_unidad * unidades, 2)}


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
# El día de pago (propuesta 34)
# ---------------------------------------------------------------------------

def _correo_deposito_hecho(ficha: dict, month_key: str, monto, clabe: str, enlace: str) -> bool:
    """*"Abrí el correo esperando un «te depositamos». Mi último correo es del
    20 de marzo. Nada"* (`paulina-rios-2027-03-20.md`)."""
    para = str(ficha.get("email") or "").strip()
    if not para or ficha.get("doNotContact"):
        return False
    nombre = _nombre_pila(ficha)
    terminacion = clabe[-4:] if clabe else ""
    cuenta = f" a tu CLABE terminación {terminacion}" if terminacion else ""
    comprobante = (f'<p class="lead"><a class="btn" href="{enlace}">Ver comprobante</a></p>' if enlace
                   else '<p class="lead">El comprobante lo tienes en tu panel, en Comisiones.</p>')
    from core.email import _email_shell
    cuerpo = f"""
    <div class="icon">💸</div>
    <h1 class="title">Te depositamos {_pesos(monto)}{cuenta}</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Ya te depositamos tus comisiones confirmadas de {_nombre_mes(month_key)} de {month_key[:4]}: <strong>{_pesos(monto)}</strong>{cuenta}.</p>
    <p class="lead">{frase_base_comision()}</p>
    {comprobante}"""
    texto = (f"Hola {nombre}. Te depositamos {_pesos(monto)}{cuenta}: son tus comisiones confirmadas de "
             f"{_nombre_mes(month_key)} de {month_key[:4]}. El comprobante está en tu panel, en Comisiones.")
    utils._send_ses_email(para, f"Te depositamos {_pesos(monto)}{cuenta}", texto, _email_shell(cuerpo))
    return True


def _correo_sin_clabe_dia_de_pago(ficha: dict, month_key: str, monto) -> bool:
    """"No te pudimos depositar porque nos falta tu CLABE", con el enlace directo."""
    para = str(ficha.get("email") or "").strip()
    if not para or ficha.get("doNotContact"):
        return False
    nombre = _nombre_pila(ficha)
    from core.email import _email_shell
    cuerpo = f"""
    <div class="icon">🏦</div>
    <h1 class="title">No te pudimos depositar: nos falta tu CLABE</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Hoy es día de pago y tienes <strong>{_pesos(monto)}</strong> en comisiones confirmadas de {_nombre_mes(month_key)} de {month_key[:4]}, pero no podemos hacer la transferencia porque no tenemos tu CLABE.</p>
    <p class="lead">Se captura una sola vez, en tu panel, en la sección Comisiones: son 18 dígitos y toma un minuto. En cuanto la tengamos, te depositamos.</p>
    <p class="lead"><a class="btn" href="{ENLACE_COMISIONES}">Registrar mi CLABE</a></p>"""
    texto = (f"Hola {nombre}. Hoy es día de pago y tienes {_pesos(monto)} en comisiones confirmadas de "
             f"{month_key}, pero nos falta tu CLABE. Captúrala en tu panel, en Comisiones: {ENLACE_COMISIONES}")
    utils._send_ses_email(para, "No te pudimos depositar: nos falta tu CLABE", texto, _email_shell(cuerpo))
    return True


def dia_de_pago(force: bool = False, dry_run: bool = False, month_key: Optional[str] = None) -> dict:
    """El día `rewards.payoutDay` sale un correo, pase lo que pase.

    Recorre por lotes los meses contables del mes anterior y manda **una sola
    vez por beneficiaria y mes** (marca `payoutNoticeSentAt` en el mes
    contable, respetando `doNotContact`): "te depositamos $X" si el mes está
    PAID, "no te pudimos depositar porque nos falta tu CLABE" si le falta, y
    nada si ese mes no tiene nada.

    **Nunca se avisa un depósito sin recibo**: el correo de "te depositamos"
    sale del comprobante existente, no de la fecha.
    """
    _motor()._reset_request_cache()
    cfg = utils._load_app_config()
    rewards = cfg.get("rewards") or {}
    hoy = _hoy()
    dia = int(hoy[8:10])
    dia_pago = int(utils._to_decimal(rewards.get("payoutDay") or 10))
    mes = month_key or _mes_anterior(hoy[:7])
    if not rewards.get("payoutNoticeEnabled", True):
        return {"day": dia, "monthKey": mes, "notified": [], "skipped": "disabled"}
    if dia != dia_pago and not force:
        return {"day": dia, "monthKey": mes, "notified": [], "skipped": "not_payout_day", "payoutDay": dia_pago}

    recibos = _recibos_pagados(mes)
    avisadas, ya_avisadas = [], []
    for item in _meses_contables(mes):
        confirmado = utils._to_decimal(item.get("totalConfirmed", 0))
        if confirmado <= 0:
            continue                      # ese mes no tiene nada: no se dice nada
        cid = str(item.get("beneficiaryId"))
        if item.get("payoutNoticeSentAt"):
            ya_avisadas.append(cid)
            continue
        ficha = _ficha(cid)
        if not ficha:
            continue
        clabe = _clabe_de(ficha)
        recibo = recibos.get(cid) or {}
        pagado = str(item.get("status") or "").upper() == "PAID" and bool(recibo)
        if pagado:
            clase = "depositado"
        elif not clabe:
            clase = "sin_clabe"
        else:
            # Tiene CLABE y todavía no se le transfiere: no se le promete un
            # depósito que no existe; se avisa cuando el recibo esté.
            continue
        if dry_run:
            avisadas.append({"customerId": cid, "name": ficha.get("name"), "kind": clase,
                             "amount": float(confirmado), "dryRun": True})
            continue
        if clase == "depositado":
            enviado = _correo_deposito_hecho(ficha, mes, confirmado, clabe, str(recibo.get("assetUrl") or ""))
        else:
            enviado = _correo_sin_clabe_dia_de_pago(ficha, mes, confirmado)

        def _marcar(ledger, _clase=clase):
            if ledger.get("payoutNoticeSentAt"):
                return False
            ledger["payoutNoticeSentAt"] = utils._now_iso()
            ledger["payoutNoticeKind"] = _clase
            return True

        utils._mutate_ledger_month(cid, mes, _marcar)
        avisadas.append({"customerId": cid, "name": ficha.get("name"), "email": ficha.get("email") if enviado else "",
                         "kind": clase, "amount": float(confirmado),
                         "channel": "email" if enviado else "ninguno"})
    utils._log("payout_day_notices", "INFO", day=dia, month=mes, notified=len(avisadas), dryRun=dry_run)
    return {"day": dia, "monthKey": mes, "payoutDay": dia_pago, "notified": avisadas,
            "alreadyNotified": ya_avisadas, "dryRun": dry_run}


def handle_dia_de_pago(peticion) -> dict:
    """POST /commissions/pagos/dia-de-pago — programable (privilegio o superadmin)."""
    body = peticion.body or {}
    mes = body.get("monthKey") or body.get("month")
    if mes and not _mes_valido(mes):
        return utils._json_response(400, {"message": "El mes debe tener la forma AAAA-MM (por ejemplo 2027-03)."})
    return utils._json_response(200, dia_de_pago(force=bool(body.get("force")),
                                                 dry_run=bool(body.get("dryRun")),
                                                 month_key=mes or None))


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
    # ── Paquete A · ronda 26 ──
    Ruta("GET", "periodos", privilegio=PRIVILEGIO,
         descripcion="Meses contables con datos, mes por omisión y hora del servidor", handler=handle_periodos),
    Ruta("GET", "pagos/pendientes.csv", privilegio=PRIVILEGIO,
         descripcion="Anexo de las que no se pueden depositar todavía, con su motivo", handler=handle_pendientes_csv),
    Ruta("POST", "pagos/dia-de-pago", privilegio=PRIVILEGIO,
         descripcion="Correo del día de pago: depositado o falta CLABE (programable)", handler=handle_dia_de_pago),
]

#: Rutas que un programador externo (EventBridge → API Gateway con el token de
#: superadmin) o el reloj del harness invocan a diario. Idempotentes por día.
TAREAS_PROGRAMADAS = [("POST", "/commissions/avisos/bloqueadas"),
                      ("POST", "/commissions/pagos/dia-de-pago")]
