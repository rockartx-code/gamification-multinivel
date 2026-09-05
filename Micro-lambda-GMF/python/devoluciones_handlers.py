"""Paquete G · devoluciones por producto (propuesta 18, docs/arquitectura/23 §7).

Lo que vivió la gente (docs/qa/22 §3.6): Lupita no sabía si tenía que regresar
todo el pedido o solo el bote dañado; Patricia tuvo que subir tres fotos para
un paquete que nunca abrió; Memo preguntó cuánto tarda y a dónde vuelve el
dinero. Este módulo concentra las reglas nuevas:

- qué líneas del pedido se devuelven (subconjunto con cantidades),
- qué evidencia exige cada motivo,
- cuánto se sugiere reembolsar por líneas y con qué política (medio y plazo),
- y la consulta `GET /orders/{id}/devolucion` con la que la clienta sigue su
  solicitud desde la misma página del asistente.

Las funciones `handle_return_*` y `handle_refund_order` siguen viviendo en
`order_lambda` (son las rutas existentes); desde ahí se llama a este módulo.
"""
from decimal import Decimal
from typing import Optional

import core_utils as utils
import order_lambda

#: Categorías de evidencia que exige cada regla.
EVIDENCIA_COMPLETA = ("fotos_producto", "fotos_empaque", "fotos_guia_envio")
EVIDENCIA_PAQUETE_CERRADO = ("fotos_paquete_cerrado",)
#: Todas las categorías que pueden llegar en una solicitud (para subirlas).
TODAS_LAS_CATEGORIAS = EVIDENCIA_COMPLETA + EVIDENCIA_PAQUETE_CERRADO

#: Nombres legibles de los motivos, para pantalla y correo.
MOTIVO_ETIQUETA = {
    "DANADO_DEFECTUOSO": "Producto dañado o defectuoso",
    "ERROR_ENVIO": "Error en el envío",
    "DESISTIMIENTO": "Ya no lo quiero (desistimiento)",
}


# ---------------------------------------------------------------------------
# Política de reembolso (config `returns`)
# ---------------------------------------------------------------------------

def politica_reembolso() -> dict:
    """Medio y plazo del reembolso, tal como se muestran en pantalla y correo."""
    cfg = (utils._load_app_config().get("returns") or {})
    return {
        "method": str(cfg.get("refundMethod") or "mismo medio de pago"),
        "businessDays": str(cfg.get("refundBusinessDays") or "3 a 5"),
    }


def texto_politica(politica: Optional[dict] = None) -> str:
    p = politica or politica_reembolso()
    return f"al {p['method']}, en {p['businessDays']} días hábiles después de validar el paquete"


# ---------------------------------------------------------------------------
# Líneas devueltas
# ---------------------------------------------------------------------------

def _mismo_producto(a, b) -> bool:
    return str(a).strip() == str(b).strip()


def _unit_net(order: dict, price: Decimal) -> Decimal:
    """Precio unitario neto: precio × (1 − descuento) menos el cupón prorrateado."""
    rate = utils._to_decimal(order.get("discountRate") or 0)
    gross = utils._to_decimal(order.get("grossSubtotal") or 0)
    coupon = utils._to_decimal(order.get("couponDiscount") or 0)
    neto = price * (Decimal("1") - rate)
    if gross > 0 and coupon > 0:
        neto -= price * (coupon / gross)
    return max(utils.D_ZERO, neto).quantize(utils.D_CENT)


def lineas_del_pedido(order: dict) -> list:
    """Todas las líneas del pedido en el formato de una devolución completa."""
    salida = []
    for it in order.get("items") or []:
        qty = int(it.get("quantity") or it.get("qty") or 0)
        if qty <= 0:
            continue
        price = utils._to_decimal(it.get("price") or 0)
        salida.append({
            "productId": it.get("productId"),
            "name": it.get("name") or it.get("productName") or str(it.get("productId")),
            "quantity": qty,
            "purchasedQuantity": qty,
            "unitPrice": price,
            "unitNet": _unit_net(order, price),
        })
    return salida


def normalizar_lineas(order: dict, lines):
    """Valida `lines` contra el pedido. Devuelve (lineas, error_http).

    - Sin `lines` (None) → todas las líneas del pedido (compatibilidad).
    - Producto que no está en el pedido, cantidad 0 o mayor que la comprada → 400 INVALID_LINES.
    """
    compradas = lineas_del_pedido(order)
    if lines is None:
        return compradas, None
    if not isinstance(lines, list) or not lines:
        return None, utils._json_response(400, {
            "message": "Indica al menos un producto y la cantidad que devuelves.",
            "code": "INVALID_LINES",
        })

    acumulado = {}
    for raw in lines:
        if not isinstance(raw, dict):
            return None, utils._json_response(400, {"message": "Formato de línea inválido.", "code": "INVALID_LINES"})
        pid = raw.get("productId")
        try:
            qty = int(raw.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        base = next((c for c in compradas if _mismo_producto(c["productId"], pid)), None)
        if base is None:
            return None, utils._json_response(400, {
                "message": f"El producto {pid} no está en este pedido.",
                "code": "INVALID_LINES", "productId": pid,
            })
        if qty <= 0:
            continue
        clave = str(pid).strip()
        acumulado[clave] = acumulado.get(clave, 0) + qty
        if acumulado[clave] > base["purchasedQuantity"]:
            return None, utils._json_response(400, {
                "message": f"Compraste {base['purchasedQuantity']} de {base['name']}; no puedes devolver {acumulado[clave]}.",
                "code": "INVALID_LINES", "productId": pid,
                "purchasedQuantity": base["purchasedQuantity"],
            })

    if not acumulado:
        return None, utils._json_response(400, {
            "message": "Indica al menos un producto y la cantidad que devuelves.",
            "code": "INVALID_LINES",
        })

    salida = []
    for base in compradas:
        qty = acumulado.get(str(base["productId"]).strip(), 0)
        if qty > 0:
            salida.append({**base, "quantity": qty})
    return salida, None


def es_devolucion_completa(order: dict, lineas: list) -> bool:
    compradas = lineas_del_pedido(order)
    if len(lineas) != len(compradas):
        return False
    por_producto = {str(l["productId"]).strip(): int(l["quantity"]) for l in lineas}
    return all(por_producto.get(str(c["productId"]).strip(), 0) == c["purchasedQuantity"] for c in compradas)


# ---------------------------------------------------------------------------
# Reembolso sugerido
# ---------------------------------------------------------------------------

def calcular_reembolso(order: dict, lineas: list, motivo: str, envio_regreso) -> dict:
    """Reembolso sugerido por líneas (docs/arquitectura/23 §7.5).

    - productos: Σ unitNet × cantidad (si se devuelve todo, exactamente el neto pagado);
    - envío de regreso: solo si el responsable es la empresa;
    - envío original: solo si se devuelve todo el pedido y el responsable es la empresa.
    Desistimiento: solo productos (regla de la ronda 4).
    """
    regla = order_lambda._motivos_devolucion().get(motivo) or {}
    empresa_paga = regla.get("responsable_envio") == "empresa"
    completa = es_devolucion_completa(order, lineas)

    if completa:
        productos = utils._to_decimal(order.get("netTotal") if order.get("netTotal") is not None else order.get("total") or 0)
    else:
        productos = sum((utils._to_decimal(l["unitNet"]) * int(l["quantity"]) for l in lineas), utils.D_ZERO)
    productos = productos.quantize(utils.D_CENT)

    regreso = utils._to_decimal(envio_regreso or 0) if empresa_paga else utils.D_ZERO
    original = utils._to_decimal(order.get("shippingCost") or 0) if (empresa_paga and completa) else utils.D_ZERO

    politica = politica_reembolso()
    return {
        "suggested": (productos + regreso + original).quantize(utils.D_CENT),
        "products": productos,
        "returnShipping": regreso.quantize(utils.D_CENT),
        "originalShipping": original.quantize(utils.D_CENT),
        "method": politica["method"],
        "businessDays": politica["businessDays"],
        "partial": not completa,
    }


def maximo_reembolsable(order: dict) -> Decimal:
    """Nunca se devuelve más de lo cobrado más el envío de regreso que pagó la clienta."""
    total = utils._to_decimal(order.get("total") if order.get("total") is not None else order.get("netTotal") or 0)
    return (total + utils._to_decimal(order.get("returnShippingCost") or 0)).quantize(utils.D_CENT)


# ---------------------------------------------------------------------------
# Detalle para la clienta
# ---------------------------------------------------------------------------

def _urls(evidencia) -> dict:
    if isinstance(evidencia, dict):
        return {k: [e.get("url") if isinstance(e, dict) else e for e in (v or [])] for k, v in evidencia.items() if v}
    return {}


def detalle_solicitud(req: dict, order: dict) -> dict:
    """Lo que la clienta ve en su página de devolución después de solicitarla."""
    politica = req.get("refundPolicy") or politica_reembolso()
    desglose = req.get("refundBreakdown") or {}
    insp = req.get("inspection") or {}
    return {
        "requestId": req.get("requestId"),
        "orderId": req.get("orderId"),
        "status": req.get("status"),
        "orderStatus": order.get("status"),
        "motivo": req.get("motivo"),
        "motivoLabel": MOTIVO_ETIQUETA.get(str(req.get("motivo") or ""), req.get("motivo")),
        "descripcion": req.get("descripcion") or "",
        "lines": req.get("lines") or [],
        "partial": bool(req.get("partial")),
        "evidence": _urls(req.get("evidence")),
        "evidenceRule": req.get("evidenceRule"),
        "shippingResponsibility": req.get("shippingResponsibility"),
        "returnShippingCost": req.get("returnShippingCost") or 0,
        "refund": {
            "suggested": req.get("refundSuggested"),
            "products": desglose.get("products"),
            "returnShipping": desglose.get("returnShipping"),
            "originalShipping": desglose.get("originalShipping"),
            "method": politica.get("method"),
            "businessDays": politica.get("businessDays"),
        },
        "inspection": {
            "inspectedAt": req.get("inspectedAt"),
            "notes": insp.get("notes"),
            "linesReceived": insp.get("linesReceived") or [],
        } if req.get("inspectedAt") else None,
        "rejectionReason": order.get("rejectionReason"),
        "courtesyCoupon": req.get("courtesyCoupon"),
        "refundedAt": order.get("refundedAt"),
        "refundAmount": order.get("refundAmount"),
        "refundAdjustmentReason": order.get("refundAdjustmentReason"),
        "warehouseAddress": order_lambda.order_emails._direccion_bodega_principal(),
        "createdAt": req.get("createdAt"),
    }


def handle_devolucion_detalle(order_id: str, headers: dict) -> dict:
    """GET /orders/{id}/devolucion — dueño, invitado (sin sesión) o admin."""
    order = utils._get_by_id("ORDER", order_id)
    if not order:
        return utils._json_response(404, {"message": "Pedido no encontrado"})
    if not order_lambda._is_guest_order(order):
        err = utils._require_self_or_admin(headers, order.get("customerId"))
        if err:
            return err
    request_id = order.get("returnRequestId")
    req = utils._get_by_id("RETURN_REQUEST", request_id) if request_id else None
    if not req:
        return utils._json_response(404, {
            "message": "Este pedido no tiene una solicitud de devolución.",
            "code": "RETURN_NOT_FOUND",
        })
    detalle = detalle_solicitud(req, order)
    if order_lambda._is_guest_order(order) and order_lambda._sin_sesion(headers):
        detalle = _detalle_publico(detalle)
    return utils._json_response(200, {"request": detalle})


def _detalle_publico(detalle: dict) -> dict:
    """Sin sesión solo se conoce el ID del pedido: el estado y el reembolso sí,
    pero no la descripción libre, las fotos de evidencia ni la inspección."""
    inspeccion = detalle.get("inspection") or None
    return {
        **detalle,
        "descripcion": "",
        "evidence": {},
        "inspection": {"inspectedAt": inspeccion.get("inspectedAt")} if inspeccion else None,
    }


# ---------------------------------------------------------------------------
# Enganche con order_lambda (§0.2: anfitrión en cascada)
# ---------------------------------------------------------------------------

def atender(peticion) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es."""
    seg = peticion.segments[1:] if peticion.segments[:1] == ["orders"] else peticion.segments
    if len(seg) == 2 and seg[1] == "devolucion":
        if peticion.method != "GET":
            return utils._json_response(405, {"message": "Método no permitido"})
        return handle_devolucion_detalle(seg[0], peticion.headers)
    return None
