"""Caja y arqueo (paquete E): efectivo esperado, comprobante del corte y correo.

Los diarios de Nadia y Paco lo resumen: "la pantalla sólo registra el número"
y "¿debo guardarme los $440 de cambio en mi bolsillo?". Este módulo calcula el
efectivo que *debería* haber en el cajón (fondo del corte anterior + ventas en
efectivo + abonos en efectivo + parte en efectivo de pagos mixtos − retiros) y
lo expone para que el corte lo compare con lo contado.

Es una extensión de `inventory_lambda` (anfitrión en cascada): `atender`
responde las rutas propias y devuelve None para el resto.
"""
from decimal import Decimal
from typing import Optional

import core_utils as utils
from core import email as correo

#: Todas las rutas de caja reutilizan el privilegio de la pantalla del POS.
PRIVILEGIO = "pos_register_sale"


# --- Configuración -----------------------------------------------------------

def config_pos() -> dict:
    """Bloque `pos` de la configuración del negocio (con sus valores por omisión)."""
    return dict((utils._load_app_config() or {}).get("pos") or {})


def denominaciones() -> list:
    return [int(utils._to_decimal(d)) for d in (config_pos().get("denominations") or [])]


# --- Lectura de ventas y retiros --------------------------------------------

def _stock_str(value) -> str:
    return "" if value is None else str(value).strip()


def ultimo_corte(stock_id: str, attendant_user_id) -> dict:
    """Último corte de caja de un operador en un almacén (o {} si nunca cortó)."""
    for item in utils._iter_bucket("POS_CASH_CUT", forward=False):
        if (_stock_str(item.get("stockId")) == _stock_str(stock_id)
                and str(item.get("attendantUserId")) == str(attendant_user_id)):
            return item
    return {}


def ventas_desde(stock_id: str, attendant_user_id, since: Optional[str]) -> list:
    """Ventas del operador en ese almacén sin corte, de cualquier forma de pago."""
    ventas = [
        s for s in utils._query_bucket("POS_SALE", sk_from=since or None)
        if _stock_str(s.get("stockId")) == _stock_str(stock_id)
        and str(s.get("attendantUserId")) == str(attendant_user_id)
        and not s.get("cashCutId")
        and (not since or str(s.get("createdAt") or "") > since)
    ]
    ventas.sort(key=lambda s: str(s.get("createdAt") or ""))
    return ventas


def retiros_desde(stock_id: str, attendant_user_id, since: Optional[str]) -> list:
    """Retiros del operador que todavía no pertenecen a ningún corte."""
    retiros = [
        w for w in utils._query_bucket("POS_WITHDRAWAL", sk_from=since or None)
        if _stock_str(w.get("stockId")) == _stock_str(stock_id)
        and str(w.get("attendantUserId")) == str(attendant_user_id)
        and not w.get("cashCutId")
    ]
    retiros.sort(key=lambda w: str(w.get("createdAt") or ""))
    return retiros


def efectivo_de_venta(venta: dict) -> Decimal:
    """Pesos que entraron al cajón por esta venta.

    Tarjeta y transferencia no entran; una venta anulada tampoco (el dinero se
    devolvió). En un pago mixto solo cuenta `cashPortion`; en un pago parcial
    o a crédito, lo que se pagó ahora (`amountPaid`).
    """
    if venta.get("status") == "voided":
        return utils.D_ZERO
    # Ventas nuevas: `cashPortion` es lo que entró al cajón al cobrar (0 en
    # tarjeta/transferencia). Los abonos posteriores son su propio registro.
    if venta.get("cashPortion") is not None:
        return utils._to_decimal(venta.get("cashPortion"))
    metodo = str(venta.get("paymentMethod") or "cash").strip().lower()
    if metodo == "mixed":
        return utils.D_ZERO
    if metodo != "cash":
        return utils.D_ZERO
    if venta.get("paymentType") in ("partial", "credit"):
        # Ventas viejas: `amountPaid` crece con cada abono y el abono ya es
        # otra venta de caja; se resta para no contarlo dos veces.
        abonos = sum((utils._to_decimal(p.get("amount")) for p in (venta.get("payments") or [])), utils.D_ZERO)
        return max(utils._to_decimal(venta.get("amountPaid")) - abonos, utils.D_ZERO)
    return utils._to_decimal(venta.get("total"))


def _no_efectivo_de_venta(venta: dict) -> Decimal:
    """Lo cobrado con tarjeta o transferencia (no entra a caja, pero sí al turno)."""
    if venta.get("status") == "voided":
        return utils.D_ZERO
    metodo = str(venta.get("paymentMethod") or "cash").strip().lower()
    if metodo == "mixed":
        return utils._to_decimal(venta.get("total")) - utils._to_decimal(venta.get("cashPortion"))
    if metodo in ("card", "transfer"):
        if venta.get("paymentType") in ("partial", "credit"):
            abonos = sum((utils._to_decimal(p.get("amount")) for p in (venta.get("payments") or [])), utils.D_ZERO)
            return max(utils._to_decimal(venta.get("amountPaid")) - abonos, utils.D_ZERO)
        return utils._to_decimal(venta.get("total"))
    return utils.D_ZERO


def calcular_arqueo(stock_id: str, attendant_user_id) -> dict:
    """Efectivo esperado en el cajón y de dónde sale, en Decimal.

    expectedCash = openingCash + cashSales + cashSettlements + cashFromMixed − withdrawals
    """
    corte = ultimo_corte(stock_id, attendant_user_id)
    since = str(corte.get("createdAt") or "") or None
    ventas = ventas_desde(stock_id, attendant_user_id, since)
    retiros = retiros_desde(stock_id, attendant_user_id, since)

    opening = utils._to_decimal(corte.get("cashToKeep")) if corte else utils.D_ZERO
    cash_sales = cash_settlements = cash_mixed = no_efectivo = utils.D_ZERO
    movimientos = []
    if opening > utils.D_ZERO:
        movimientos.append({"type": "opening", "id": corte.get("cashCutId"), "at": corte.get("createdAt"),
                            "amount": opening, "label": "Fondo que dejó el corte anterior"})
    ventas_vivas = 0
    for v in ventas:
        if v.get("status") == "voided":
            continue
        ventas_vivas += 1
        no_efectivo += _no_efectivo_de_venta(v)
        efectivo = efectivo_de_venta(v)
        if efectivo <= utils.D_ZERO:
            continue
        metodo = str(v.get("paymentMethod") or "cash").strip().lower()
        if v.get("source") == "settlement":
            tipo, etiqueta = "settlement", f"Abono a {v.get('orderId') or 'venta'}"
            cash_settlements += efectivo
        elif metodo == "mixed":
            tipo, etiqueta = "mixed", f"Venta {v.get('orderId')} (parte en efectivo)"
            cash_mixed += efectivo
        else:
            tipo, etiqueta = "sale", f"Venta {v.get('orderId')}"
            if v.get("paymentType") in ("partial", "credit"):
                etiqueta += " (pago parcial)"
            cash_sales += efectivo
        movimientos.append({"type": tipo, "id": v.get("saleId"), "at": v.get("createdAt"),
                            "amount": efectivo, "label": etiqueta,
                            "customerName": v.get("customerName") or "Público en general"})
    total_retiros = utils.D_ZERO
    for w in retiros:
        monto = utils._to_decimal(w.get("amount"))
        total_retiros += monto
        movimientos.append({"type": "withdrawal", "id": w.get("withdrawalId"), "at": w.get("createdAt"),
                            "amount": -monto, "label": f"Retiro: {w.get('reason') or ''}".strip(),
                            "customerName": w.get("receiver") or ""})
    movimientos.sort(key=lambda m: str(m.get("at") or ""))
    esperado = opening + cash_sales + cash_settlements + cash_mixed - total_retiros
    return {
        "stockId": stock_id,
        "attendantUserId": attendant_user_id,
        "since": since,
        "lastCut": corte,
        "ventas": ventas,
        "retiros": retiros,
        "openingCash": opening,
        "cashSales": cash_sales,
        "cashSettlements": cash_settlements,
        "cashFromMixed": cash_mixed,
        "withdrawals": total_retiros,
        "withdrawalCount": len(retiros),
        "nonCashTotal": no_efectivo,
        "expectedCash": esperado,
        "salesCount": ventas_vivas,
        "movements": movimientos,
    }


def arqueo_para_respuesta(arqueo: dict) -> dict:
    """Versión JSON (floats) del arqueo, con lo que la pantalla necesita."""
    cfg = config_pos()
    corte = arqueo.get("lastCut") or {}
    ventas = [v for v in arqueo["ventas"] if v.get("status") != "voided"]
    return {
        "stockId": arqueo["stockId"],
        "attendantUserId": arqueo["attendantUserId"],
        "since": arqueo["since"],
        "lastCutId": corte.get("cashCutId"),
        "lastCutAt": corte.get("createdAt"),
        "openingCash": float(arqueo["openingCash"]),
        "cashSales": float(arqueo["cashSales"]),
        "cashSettlements": float(arqueo["cashSettlements"]),
        "cashFromMixed": float(arqueo["cashFromMixed"]),
        "withdrawals": float(arqueo["withdrawals"]),
        "withdrawalCount": arqueo["withdrawalCount"],
        "nonCashTotal": float(arqueo["nonCashTotal"]),
        "expectedCash": float(arqueo["expectedCash"]),
        "salesCount": arqueo["salesCount"],
        "startedAt": ventas[0].get("createdAt") if ventas else corte.get("createdAt"),
        "lastSaleAt": ventas[-1].get("createdAt") if ventas else None,
        "movements": [dict(m, amount=float(m["amount"])) for m in arqueo["movements"]],
        "config": {
            "denominations": denominaciones(),
            "requireDifferenceReason": bool(cfg.get("requireDifferenceReason", True)),
            "notifyEmailConfigured": bool(str(cfg.get("cashCutNotifyEmail") or "").strip()),
        },
    }


# --- Rutas propias -----------------------------------------------------------

def _stock_del_usuario(user_id) -> str:
    for stock in utils._query_bucket("STOCK"):
        if str(user_id) in [str(u) for u in (stock.get("linkedUserIds") or [])]:
            return str(stock.get("stockId"))
    return ""


def handle_arqueo(query: dict, headers: dict) -> dict:
    """GET /pos/arqueo?stockId= — efectivo esperado y movimientos desde el último corte."""
    user_id = (headers or {}).get("x-user-id")
    if not user_id:
        return utils._json_response(400, {"message": "Se requiere x-user-id"})
    stock_id = (query or {}).get("stockId") or _stock_del_usuario(user_id)
    if not stock_id:
        return utils._json_response(400, {"message": "Sin sucursal vinculada: pide a la gerente que te ligue a una"})
    return utils._json_response(200, {"arqueo": arqueo_para_respuesta(calcular_arqueo(stock_id, user_id))})


def handle_get_cash_cut(cut_id: str, headers: dict) -> dict:
    """GET /pos/cash-cuts/{id} — el corte completo, para imprimir el comprobante."""
    cut = utils._get_by_id("POS_CASH_CUT", cut_id)
    if not cut:
        return utils._json_response(404, {"message": f"No existe el corte {cut_id}"})
    return utils._json_response(200, {"cut": cut})


def _dinero(valor) -> str:
    return f"${utils._to_decimal(valor):,.2f}"


def texto_comprobante(cut: dict) -> str:
    """Comprobante del corte en texto plano (también sirve de cuerpo del correo)."""
    lineas = [
        f"Comprobante del corte {cut.get('cashCutId')}",
        f"Sucursal: {cut.get('stockId')} · Operador: {cut.get('attendantUserId')}",
        f"Periodo: {cut.get('startedAt') or '-'} a {cut.get('endedAt') or cut.get('createdAt') or '-'}",
        "",
        f"Fondo inicial: {_dinero(cut.get('openingCash'))}",
        f"Ventas en efectivo: {_dinero(cut.get('cashSales'))}",
        f"Abonos en efectivo: {_dinero(cut.get('cashSettlements'))}",
        f"Parte en efectivo de pagos mixtos: {_dinero(cut.get('cashFromMixed'))}",
        f"Retiros del turno: -{_dinero(cut.get('totalWithdrawals'))}",
        f"Efectivo esperado: {_dinero(cut.get('cashExpected'))}",
        f"Efectivo contado: {_dinero(cut.get('cashCounted'))}",
        f"Diferencia: {_dinero(cut.get('difference'))}"
        + (f" · Motivo: {cut.get('differenceReason')}" if cut.get("differenceReason") else ""),
        "",
        f"Se deja como fondo: {_dinero(cut.get('cashToKeep'))}",
        f"Se retira: {_dinero(cut.get('withdrawnAmount'))}"
        + (f" (recibe {cut.get('withdrawalReceiver')})" if cut.get("withdrawalReceiver") else ""),
        f"Ventas del turno: {int(cut.get('salesCount') or 0)} · Tarjeta/transferencia: {_dinero(cut.get('nonCashTotal'))}",
    ]
    return "\n".join(lineas)


def html_comprobante(cut: dict) -> str:
    filas = [
        ("Fondo inicial", cut.get("openingCash")),
        ("Ventas en efectivo", cut.get("cashSales")),
        ("Abonos en efectivo", cut.get("cashSettlements")),
        ("Parte en efectivo de pagos mixtos", cut.get("cashFromMixed")),
        ("Retiros del turno", -utils._to_decimal(cut.get("totalWithdrawals"))),
        ("Efectivo esperado", cut.get("cashExpected")),
        ("Efectivo contado", cut.get("cashCounted")),
        ("Diferencia", cut.get("difference")),
        ("Se deja como fondo", cut.get("cashToKeep")),
        ("Se retira", cut.get("withdrawnAmount")),
        ("Tarjeta y transferencia (no entran a caja)", cut.get("nonCashTotal")),
    ]
    tabla = "".join(
        f"<tr><td style='text-align:left;padding:4px 8px'>{nombre}</td>"
        f"<td style='text-align:right;padding:4px 8px'><strong>{_dinero(valor)}</strong></td></tr>"
        for nombre, valor in filas
    )
    motivo = f"<p>Motivo de la diferencia: {cut.get('differenceReason')}</p>" if cut.get("differenceReason") else ""
    recibe = f"<p>El retiro lo recibe: {cut.get('withdrawalReceiver')}</p>" if cut.get("withdrawalReceiver") else ""
    cuerpo = (
        f"<h1 class='title'>Corte de caja {cut.get('cashCutId')}</h1>"
        f"<p>Sucursal {cut.get('stockId')} · operador {cut.get('attendantUserId')} · "
        f"{int(cut.get('salesCount') or 0)} ventas.</p>"
        f"<table style='width:100%;border-collapse:collapse'>{tabla}</table>{motivo}{recibe}"
    )
    return correo._email_shell(cuerpo)


def handle_enviar_corte(cut_id: str, body: dict, headers: dict) -> dict:
    """POST /pos/cash-cuts/{id}/enviar — manda el comprobante por correo a la gerente."""
    cut = utils._get_by_id("POS_CASH_CUT", cut_id)
    if not cut:
        return utils._json_response(404, {"message": f"No existe el corte {cut_id}"})
    destino = str((body or {}).get("email") or "").strip() or str(config_pos().get("cashCutNotifyEmail") or "").strip()
    if not destino or "@" not in destino:
        return utils._json_response(400, {
            "message": "No hay un correo al que enviar el corte: escribe uno aquí o pide a la gerente que lo "
                       "configure en Configuración → Punto de venta → Correo para cortes."})
    asunto = f"Corte de caja {cut_id}: efectivo contado {_dinero(cut.get('cashCounted'))}"
    correo._send_ses_email(destino, asunto, texto_comprobante(cut), html_comprobante(cut))
    now = utils._now_iso()
    utils._update_by_id("POS_CASH_CUT", cut_id, "SET notifiedTo = :d, notifiedAt = :t",
                        {":d": destino, ":t": now})
    return utils._json_response(200, {"sent": True, "to": destino, "cashCutId": cut_id, "sentAt": now})


def atender(peticion):
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = peticion.segments[1:] if peticion.segments[:1] == ["inventory"] else peticion.segments
    if seg[:1] != ["pos"]:
        return None
    metodo = peticion.method
    if seg == ["pos", "arqueo"] and metodo == "GET":
        err = utils._require_admin(peticion.headers, PRIVILEGIO)
        if err:
            return err
        return handle_arqueo(peticion.query, peticion.headers)
    if len(seg) == 3 and seg[1] == "cash-cuts" and metodo == "GET":
        err = utils._require_admin(peticion.headers, PRIVILEGIO)
        if err:
            return err
        return handle_get_cash_cut(seg[2], peticion.headers)
    if len(seg) == 4 and seg[1] == "cash-cuts" and seg[3] == "enviar" and metodo == "POST":
        err = utils._require_admin(peticion.headers, PRIVILEGIO)
        if err:
            return err
        return handle_enviar_corte(seg[2], peticion.body, peticion.headers)
    return None
