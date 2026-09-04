"""Modo cliente y modo socio, y el plan publicado (paquete B, propuestas 1, 2 y 3).

Nueve personas de los diarios (docs/qa/22 §3.1) llegaron por un producto y
salieron "dadas de alta como vendedoras": red, VP, comisiones y datos
bancarios aparecían sin que nadie los pidiera. Ocho más (§3.2) no podían
calcular el negocio porque el plan solo se explicaba por WhatsApp.

Este módulo resuelve las dos cosas:

- Cada cliente tiene un modo (`cliente` o `socio`). Todo registro nuevo nace
  cliente; las fichas anteriores a esta ronda (sin atributo) son socio. Se
  pasa a socio al pulsar "Activar modo socio", cuando alguien se registra con
  el código de la persona (ya tiene red) o cuando el motor le crea una fila de
  comisión. En modo cliente no aplica la escalera de descuento (se paga precio
  de lista) y el pedido guarda cuánto se habría ahorrado como socia.
- `GET /catalog/plan` publica el plan completo con los números reales de la
  configuración: ningún porcentaje va escrito aquí ni en el frontend.

Se engancha en `catalog_lambda` (tabla declarativa, `RUTAS_CATALOGO`) y en
`customer_lambda` (cascada, `atender`).
"""
import json
import math
from decimal import Decimal
from typing import Optional

import core_utils as utils
import impuestos  # paquete B · ronda 26: IVA (§38) y base de la comisión (§37)
from core import email as _correo
from core.routing import Ruta

#: Etiqueta de la versión del plan que acepta quien activa el modo socio.
PLAN_VERSION = "abril-2026"

MODOS = ("cliente", "socio")

#: Estados de pedido que cuentan como compra hecha (misma lista que el panel).
_ESTADOS_COMPRA = ("paid", "shipped", "delivered", "en_devolucion", "devolucion_rechazada", "devuelto_validado")

#: Con cuántas amigas y qué compra se ilustra "qué ganarías" en el panel del cliente.
_AMIGAS_EJEMPLO = 2


# ---------------------------------------------------------------------------
# Modo de la cuenta
# ---------------------------------------------------------------------------

def modo_de(customer) -> str:
    """`mode` de la ficha si es válido; las fichas sin atributo son socio."""
    modo = str((customer or {}).get("mode") or "").strip().lower()
    return modo if modo in MODOS else "socio"


def _correo_bienvenida_socio(customer: dict) -> None:
    """Solo cuando la persona lo pidió: los cambios automáticos no avisan."""
    try:
        para = str(customer.get("email") or "").strip()
        if not para or customer.get("doNotContact"):
            return
        nombre = (str(customer.get("name") or "").split(" ") or ["Hola"])[0] or "Hola"
        base = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx").rstrip("/")
        cuerpo = f"""
    <div class="icon">🤝</div>
    <h1 class="title">Bienvenida al modo socio</h1>
    <p class="lead">Hola <strong>{nombre}</strong>. Tu cuenta ya está en modo socio: desde tu próxima compra aplica el descuento por volumen, tienes tu propio código para invitar y las compras de tu red te generan comisiones.</p>
    <div class="info-box">
      <p>Cuando te actives en el mes te pediremos tu CLABE, para poder depositarte el día de pago. La registras en tu panel, en Comisiones, y toma un minuto.</p>
    </div>
    <a class="btn" href="{base}/#/dashboard">Ir a mi panel</a>
    <p><a href="{base}/#/modo-socio">Volver a leer cómo funciona el plan</a></p>
    """
        texto = (f"Bienvenida al modo socio\n\nHola {nombre}. Tu cuenta ya está en modo socio: desde tu próxima compra "
                 f"aplica el descuento por volumen, tienes tu propio código y las compras de tu red generan comisiones.\n\n"
                 f"Tu panel: {base}/#/dashboard\nCómo funciona el plan: {base}/#/modo-socio\n")
        _correo._send_ses_email(para, "Tu cuenta ya está en modo socio", texto, _correo._email_shell(cuerpo))
    except Exception as error:  # pragma: no cover - el correo nunca rompe la activación
        utils._log("modo_socio_email_error", "ERROR", error=str(error))


def asegurar_socio(customer_id, motivo: str = "solicitud", plan_version: Optional[str] = None) -> Optional[dict]:
    """Pasa la ficha a modo socio si estaba en cliente. Idempotente.

    `motivo` ∈ registro | solicitud | referido | comision | admin. Solo el
    motivo `solicitud` manda correo de bienvenida.
    """
    if customer_id in (None, ""):
        return None
    cid = utils._customer_entity_id(customer_id)
    customer = utils._get_by_id("CUSTOMER", cid)
    if not customer or not isinstance(customer, dict):
        return None
    if modo_de(customer) == "socio":
        return {
            "mode": "socio",
            "modeActivatedAt": customer.get("modeActivatedAt") or customer.get("modeSince"),
            "alreadyPartner": True,
        }
    ahora = utils._now_iso()
    valores = {":m": "socio", ":n": ahora, ":r": str(motivo or "solicitud")}
    expresion = "SET #m = :m, modeSince = :n, modeActivatedAt = :n, modeReason = :r, updatedAt = :n"
    if plan_version:
        expresion += ", acceptedPlanVersion = :v"
        valores[":v"] = str(plan_version)
    utils._update_by_id("CUSTOMER", cid, expresion, valores, names={"#m": "mode"})
    utils._log("customer_mode_changed", "INFO", customerId=str(cid), mode="socio", reason=motivo)
    if motivo == "solicitud":
        _correo_bienvenida_socio(customer)
    return {"mode": "socio", "modeActivatedAt": ahora, "alreadyPartner": False}


def _volver_a_cliente(customer_id) -> Optional[dict]:
    """Solo un admin puede regresar una ficha a modo cliente (desde la ficha)."""
    cid = utils._customer_entity_id(customer_id)
    customer = utils._get_by_id("CUSTOMER", cid)
    if not customer:
        return None
    ahora = utils._now_iso()
    utils._update_by_id(
        "CUSTOMER", cid,
        "SET #m = :m, modeSince = :n, modeReason = :r, updatedAt = :n",
        {":m": "cliente", ":n": ahora, ":r": "admin"}, names={"#m": "mode"},
    )
    utils._log("customer_mode_changed", "INFO", customerId=str(cid), mode="cliente", reason="admin")
    return {"mode": "cliente", "modeActivatedAt": None, "alreadyPartner": False}


# ---------------------------------------------------------------------------
# Escalera de descuento y ahorro "como socia"
# ---------------------------------------------------------------------------

def _tiers(cfg: Optional[dict] = None) -> list:
    rewards = (cfg or utils._load_app_config()).get("rewards") or {}
    return sorted(rewards.get("discountTiers") or [], key=lambda t: float(utils._to_decimal(t.get("min", 0))))


def _tasa(tiers, basis) -> Decimal:
    """La misma escalera que cobra el pedido: `order_lambda._resolve_discount_rate`."""
    import order_lambda  # import perezoso: order_lambda importa este módulo
    return utils._to_decimal(order_lambda._resolve_discount_rate(tiers, utils._to_decimal(basis)))


def siguiente_tramo(tiers, basis) -> Optional[dict]:
    """Primer tramo con `min` por encima de `basis`, o None si ya está en el último."""
    basis = utils._to_decimal(basis)
    for tier in sorted(tiers, key=lambda t: float(utils._to_decimal(t.get("min", 0)))):
        minimo = utils._to_decimal(tier.get("min", 0))
        if minimo > basis:
            return {"rate": utils._to_decimal(tier.get("rate", 0)), "missing": (minimo - basis).quantize(utils.D_CENT)}
    return None


def calcular_ahorro(gross, month_net, tiers=None) -> dict:
    """Cuánto se habría descontado esta compra en modo socio, con el neto previo del mes."""
    tiers = tiers if tiers is not None else _tiers()
    gross = utils._to_decimal(gross)
    month_net = utils._to_decimal(month_net)
    proyectado = month_net + gross
    tasa = _tasa(tiers, proyectado)
    ahorro = (gross * tasa).quantize(utils.D_CENT)
    return {
        "gross": gross, "monthNet": month_net, "projected": proyectado,
        "rate": tasa, "savings": ahorro, "nextTier": siguiente_tramo(tiers, proyectado),
    }


def campos_ahorro(gross, month_net, modo: str, tiers=None) -> dict:
    """Campos `partnerSavings*` que `_calculate_totals` deja en el pedido."""
    if modo == "socio":
        return {
            "partnerMode": "socio",
            "partnerSavings": utils.D_ZERO,
            "partnerSavingsRate": utils.D_ZERO,
            "partnerSavingsProjected": (utils._to_decimal(month_net) + utils._to_decimal(gross)).quantize(utils.D_CENT),
        }
    calc = calcular_ahorro(gross, month_net, tiers)
    siguiente = calc["nextTier"] or {}
    return {
        "partnerMode": modo,
        "partnerSavings": calc["savings"],
        "partnerSavingsRate": calc["rate"],
        "partnerSavingsProjected": calc["projected"].quantize(utils.D_CENT),
        "partnerSavingsNextRate": utils._to_decimal(siguiente.get("rate", 0)),
        "partnerSavingsNextMissing": utils._to_decimal(siguiente.get("missing", 0)),
    }


def _f(valor) -> float:
    return float(utils._to_decimal(valor or 0))


def _tramo_json(tier: dict) -> dict:
    return {
        "min": _f(tier.get("min")),
        "max": _f(tier.get("max")) if tier.get("max") is not None else None,
        "rate": _f(tier.get("rate")),
    }


def _ahorro_json(calc: dict) -> dict:
    siguiente = calc.get("nextTier")
    return {
        "gross": _f(calc["gross"]), "monthNet": _f(calc["monthNet"]), "projected": _f(calc["projected"]),
        "rate": _f(calc["rate"]), "savings": _f(calc["savings"]),
        "nextTier": {"rate": _f(siguiente["rate"]), "missing": _f(siguiente["missing"])} if siguiente else None,
    }


# ---------------------------------------------------------------------------
# Indicadores del panel en modo cliente
# ---------------------------------------------------------------------------

def _neto_del_mes(customer_id, month_key: str) -> Decimal:
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(customer_id, month_key)) or {}
    return utils._to_decimal(estado.get("netVolume", 0))


def _vp_del_mes(customer_id, month_key: str, cfg: dict) -> Decimal:
    """VP netos acumulados del mes: `netVP` del mes del socio; si el mes no lo
    trae, se derivan del neto con la tarifa (mismo criterio que el motor)."""
    estado = utils._get_by_id("ASSOCIATE_MONTH", utils._associate_month_entity_id(customer_id, month_key)) or {}
    if "netVP" in estado:
        return utils._to_decimal(estado.get("netVP", 0))
    tarifa = utils._to_decimal(utils._mxn_per_vp(cfg))
    if tarifa <= 0:
        return utils.D_ZERO
    return (utils._to_decimal(estado.get("netVolume", 0)) / tarifa).quantize(Decimal("0.01"))


def _ahorro_del_mes(customer_id, month_key: str) -> Decimal:
    """Suma de `partnerSavings` de los pedidos pagados del mes (historial por cliente)."""
    total = utils.D_ZERO
    try:
        resp = utils._table.query(
            KeyConditionExpression=utils.Key("PK").eq(utils._order_customer_history_pk(customer_id))
            & utils.Key("SK").begins_with(month_key),
        )
    except Exception:
        return total
    for fila in resp.get("Items", []) or []:
        if str(fila.get("status") or "").lower() not in _ESTADOS_COMPRA:
            continue
        pedido = utils._get_by_id("ORDER", fila.get("orderId")) or {}
        total += utils._to_decimal(pedido.get("partnerSavings", 0))
    return total.quantize(utils.D_CENT)


def _primera_generacion(cfg: dict) -> Decimal:
    niveles = (cfg.get("rewards") or {}).get("commissionLevels") or []
    primera = sorted(niveles, key=lambda n: int(utils._to_decimal(n.get("gen") or 0)))[0] if niveles else {}
    return utils._to_decimal(primera.get("rate", 0))


def indicadores_cliente(customer: dict) -> dict:
    """Lo que ve un cliente en su panel: cuánto compró, cuánto habría ahorrado y qué ganaría."""
    cfg = utils._load_app_config()
    tiers = _tiers(cfg)
    cid = customer.get("customerId")
    month_key = utils._month_key()
    gasto = _neto_del_mes(cid, month_key)
    # Mismo criterio que el plan (§14): la compra de ejemplo es el neto de la
    # canasta más barata que de verdad activa, no un "más o menos $1,000".
    canasta = _canasta_mas_barata_que_activa(tiers, utils._to_decimal(utils._activation_vp(cfg)))
    compra_ejemplo = canasta["neto"] if canasta else utils.D_ZERO
    tasa_gen1 = _primera_generacion(cfg)
    siguiente = siguiente_tramo(tiers, gasto)
    return {
        "monthKey": month_key,
        "monthSpend": _f(gasto),
        # La tabla única decía «llevas 0 VP» en modo cliente porque el panel
        # vacía `vp`; los VP sí se acumulan y aquí viajan para panel y carrito.
        "monthVp": _f(_vp_del_mes(cid, month_key, cfg)),
        "monthSavingsIfPartner": _f(_ahorro_del_mes(cid, month_key)),
        "currentRateIfPartner": _f(_tasa(tiers, gasto)),
        "nextTier": {"rate": _f(siguiente["rate"]), "missing": _f(siguiente["missing"])} if siguiente else None,
        "exampleEarnings": {
            "friends": _AMIGAS_EJEMPLO,
            "purchaseEach": _f(compra_ejemplo),
            "rate": _f(tasa_gen1),
            "total": _f((compra_ejemplo * tasa_gen1 * _AMIGAS_EJEMPLO).quantize(utils.D_CENT)),
        },
    }


def ajustar_dashboard(customer: dict, response: dict) -> dict:
    """Última línea de `handle_customer_dashboard`: añade `mode` y, en modo
    cliente, quita red, VP, comisiones y rangos y añade `clientIndicators`."""
    try:
        datos = json.loads(response.get("body") or "{}")
    except (TypeError, ValueError):
        return response
    modo = modo_de(customer)
    datos["mode"] = modo
    datos["modeActivatedAt"] = customer.get("modeActivatedAt")
    if modo == "socio":
        return utils._json_response(response.get("statusCode", 200), datos)

    datos["networkMembers"] = []
    datos["commissions"] = None
    datos["vp"] = 0
    datos["vg"] = 0
    datos["rank"] = ""
    datos["bonuses"] = []
    # En modo cliente no aplica la escalera: el carrito no debe prometer un descuento que el pedido no cobra.
    datos["user"] = {**(datos.get("user") or {}), "discountPercent": 0, "discountActive": False}
    metas = []
    for meta in datos.get("goals") or []:
        if meta.get("key") == "active":
            metas.append({
                **meta,
                "title": "Meta de compra del mes",
                "subtitle": "Al llegar aquí, como socia tendrías descuento y te activarías",
            })
    datos["goals"] = metas
    datos["clientIndicators"] = indicadores_cliente(customer)
    return utils._json_response(response.get("statusCode", 200), datos)


# ---------------------------------------------------------------------------
# Plan publicado (GET /catalog/plan)
# ---------------------------------------------------------------------------

def _productos_con_pc() -> list:
    """Productos activos de la tienda con PC, del más barato al más caro."""
    productos = []
    for item in utils._query_bucket("PRODUCT") or []:
        if not item.get("active", True) or not item.get("inOnlineStore", True):
            continue
        pc = utils._to_decimal(item.get("vpPoints") or 0)
        precio = utils._to_decimal(item.get("price") or 0)
        if pc <= 0 or precio <= 0:
            continue
        productos.append({"id": str(item.get("productId") or ""), "name": str(item.get("name") or ""),
                          "price": precio, "pc": pc})
    return sorted(productos, key=lambda p: (p["price"], p["name"]))


def _ejemplo_activacion(producto: dict, qty: int, tiers: list, vp_netos: Decimal) -> dict:
    bruto = producto["price"] * qty
    tasa = _tasa(tiers, bruto)
    vp = (producto["pc"] * qty * (1 - tasa)).quantize(utils.D_CENT)
    return {
        "productos": [{"id": producto["id"], "name": producto["name"], "price": _f(producto["price"]),
                       "pc": _f(producto["pc"]), "qty": qty}],
        "bruto": _f(bruto), "rate": _f(tasa), "vp": _f(vp), "activa": vp >= vp_netos,
    }


def _ejemplos_activacion(tiers: list, vp_netos: Decimal, productos: Optional[list] = None) -> list:
    productos = productos if productos is not None else _productos_con_pc()
    if not productos:
        return []
    ejemplos = []
    primero = productos[0]
    ejemplos.append(_ejemplo_activacion(primero, int(math.ceil(vp_netos / primero["pc"])), tiers, vp_netos))
    if len(productos) > 1:
        segundo = productos[1]
        ejemplos.append(_ejemplo_activacion(segundo, int(math.ceil(vp_netos / segundo["pc"])), tiers, vp_netos))
    else:
        ejemplos.append(_ejemplo_activacion(primero, int(math.ceil(vp_netos / primero["pc"])) + 1, tiers, vp_netos))
    return ejemplos


#: Tope de piezas del mismo producto que se prueban al buscar la canasta que
#: activa. Con la escalera real ninguna pasa de cuatro; el tope solo evita un
#: bucle infinito si alguien configura un producto con 0.01 PC.
_MAX_PIEZAS_CANASTA = 60


def _costo_para_activar(producto: dict, tiers: list, vp_netos: Decimal) -> Optional[Decimal]:
    """Cuánto hay que comprar de **este** producto para activarse, en pesos de lista.

    El descuento por volumen se muerde la cola: al pasar de $1,000 baja los VP
    un 10 %, así que comprar más de lista puede no bastar. Se resuelve por
    tramo: para cada tasa de la escalera se despeja el bruto que da los VP
    netos y se acepta si ese bruto cae de verdad dentro del tramo.
    """
    precio, pc = producto["price"], producto["pc"]
    if precio <= 0 or pc <= 0:
        return None
    candidatos = []
    for tier in sorted(tiers, key=lambda t: float(utils._to_decimal(t.get("min", 0)))):
        tasa = utils._to_decimal(tier.get("rate", 0))
        if tasa >= 1:
            continue
        minimo = utils._to_decimal(tier.get("min", 0))
        maximo = utils._to_decimal(tier.get("max")) if tier.get("max") is not None else None
        bruto = (vp_netos * precio / (pc * (1 - tasa))).quantize(utils.D_CENT)
        if bruto >= minimo and (maximo is None or bruto < maximo):
            candidatos.append(bruto)
    return min(candidatos) if candidatos else None


def _rango_activacion(tiers: list, vp_netos: Decimal, productos: Optional[list] = None) -> Optional[dict]:
    """Lo que de verdad cuesta activarse, de lo más barato a lo más caro.

    Sustituye al "más o menos $1,000" que la propia página desmentía tres
    renglones abajo. Ximena Paredes midió el hoyo a mano —"con $980 de Naplus
    activa, con $1,000 no"— y lo llamó *"el número más importante del plan, en
    la página que se llama «con los números reales»"*.
    """
    productos = productos if productos is not None else _productos_con_pc()
    costos = []
    for producto in productos:
        costo = _costo_para_activar(producto, tiers, vp_netos)
        if costo is not None:
            costos.append((costo, producto))
    if not costos:
        return None
    barato = min(costos, key=lambda c: c[0])
    caro = max(costos, key=lambda c: c[0])
    pesos = impuestos.formato_pesos
    nota = (f"Depende del producto: con {barato[1]['name']} te activas con {pesos(barato[0])}; "
            f"con {caro[1]['name']} necesitas {pesos(caro[0])}.") if barato[1]["id"] != caro[1]["id"] else \
        f"Con {barato[1]['name']} te activas con {pesos(barato[0])}."
    return {"min": _f(barato[0]), "max": _f(caro[0]), "notaProducto": nota}


def _canasta_mas_barata_que_activa(tiers: list, vp_netos: Decimal, productos: Optional[list] = None) -> Optional[dict]:
    """La compra real más barata —piezas enteras— que sí activa el mes.

    Es la compra de referencia de los ejemplos de comisión: así "si compra
    $960 netos ganas $96" es aritmética verdadera sobre la misma base que
    paga el motor (el neto pagado por producto, sin envío).
    """
    mejor = None
    for producto in (productos if productos is not None else _productos_con_pc()):
        for qty in range(1, _MAX_PIEZAS_CANASTA + 1):
            ejemplo = _ejemplo_activacion(producto, qty, tiers, vp_netos)
            if not ejemplo["activa"]:
                continue
            neto = (utils._to_decimal(ejemplo["bruto"]) * (1 - utils._to_decimal(ejemplo["rate"]))).quantize(utils.D_CENT)
            if mejor is None or neto < mejor["neto"]:
                mejor = {"neto": neto, "producto": producto["name"], "qty": qty,
                         "bruto": utils._to_decimal(ejemplo["bruto"]), "rate": utils._to_decimal(ejemplo["rate"])}
            break
    return mejor


def _pct(tasa) -> str:
    valor = _f(tasa) * 100
    return f"{valor:g}"


def _ejemplos_descuento(tiers: list) -> list:
    """Una compra de ejemplo por tramo con descuento, calculada con la escalera real."""
    ejemplos = []
    for tier in tiers:
        tasa = utils._to_decimal(tier.get("rate", 0))
        if tasa <= 0:
            continue
        minimo = utils._to_decimal(tier.get("min", 0))
        maximo = utils._to_decimal(tier.get("max")) if tier.get("max") is not None else None
        # Un punto dentro del tramo, no en el borde, para que se lea como una compra normal.
        compra = minimo + ((maximo - minimo) if maximo is not None else minimo) / 5
        compra = compra.quantize(Decimal("1"))
        tasa_real = _tasa(tiers, compra)
        descuento = (compra * tasa_real).quantize(utils.D_CENT)
        ejemplos.append({"compraMes": _f(compra), "rate": _f(tasa_real), "descuento": _f(descuento),
                         "pagas": _f(compra - descuento)})
    return ejemplos


def _texto_requisito(nivel: dict) -> str:
    directas = int(utils._to_decimal(nivel.get("reqActiveDirects") or 0))
    pc_personal = utils._to_decimal(nivel.get("reqPersonalPC") or 0)
    lineas = int(utils._to_decimal(nivel.get("reqLines") or 0))
    pc_linea = utils._to_decimal(nivel.get("reqPCPerLine") or 0)
    partes = []
    if directas > 0:
        partes.append(f"{directas} directa{'s' if directas != 1 else ''} activa{'s' if directas != 1 else ''}")
    if pc_personal > 0:
        partes.append(f"{_f(pc_personal):g} PC personales")
    if lineas > 0:
        partes.append(f"{lineas} línea{'s' if lineas != 1 else ''} con {_f(pc_linea):g} PC cada una")
    return " y ".join(partes) if partes else "sin requisito"


def _generaciones(cfg: dict, compra_ejemplo: Decimal) -> list:
    niveles = sorted((cfg.get("rewards") or {}).get("commissionLevels") or [],
                     key=lambda n: int(utils._to_decimal(n.get("gen") or 0)))
    salida = []
    for nivel in niveles[: utils._max_network_levels(cfg)]:
        tasa = utils._to_decimal(nivel.get("rate", 0))
        salida.append({
            "gen": int(utils._to_decimal(nivel.get("gen") or 0)),
            "rate": _f(tasa),
            "requisitos": {
                "activeDirects": int(utils._to_decimal(nivel.get("reqActiveDirects") or 0)),
                "personalPC": _f(nivel.get("reqPersonalPC")),
                "lines": int(utils._to_decimal(nivel.get("reqLines") or 0)),
                "pcPerLine": _f(nivel.get("reqPCPerLine")),
            },
            "requisitoTexto": _texto_requisito(nivel),
            "ejemplo": {"compraReferido": _f(compra_ejemplo),
                        "comision": _f((compra_ejemplo * tasa).quantize(utils.D_CENT))},
        })
    return salida


def construir_plan() -> dict:
    """Forma fija de docs/arquitectura/23 §2.4. Todo sale de la configuración."""
    cfg = utils._load_app_config()
    rewards = cfg.get("rewards") or {}
    bonuses = cfg.get("bonuses") or {}
    tiers = _tiers(cfg)
    vp_netos = utils._to_decimal(utils._activation_vp(cfg))
    mxn_por_vp = utils._to_decimal(utils._mxn_per_vp(cfg))
    productos = _productos_con_pc()
    rango = _rango_activacion(tiers, vp_netos, productos)
    # La compra de referencia de los ejemplos de comisión es una compra que de
    # verdad existe y de verdad activa, y se toma por su **neto pagado**, que
    # es la base sobre la que el motor paga (§37). Sin canasta (catálogo sin
    # PC) no se inventa ninguna: los ejemplos salen en cero.
    canasta = _canasta_mas_barata_que_activa(tiers, vp_netos, productos)
    compra_ejemplo = canasta["neto"] if canasta else utils.D_ZERO
    primer_tramo = next((t for t in tiers if utils._to_decimal(t.get("rate", 0)) > 0), None)
    tasa_primer_tramo = utils._to_decimal((primer_tramo or {}).get("rate", 0))
    vp_con_descuento = (vp_netos * (1 - tasa_primer_tramo)).quantize(utils.D_CENT)
    documentos = [str(d.get("label") or d.get("key") or "") for d in (cfg.get("customerDocumentTypes") or [])]
    # Estas dos claves las define el paquete A en `rewards`; hasta integrarlo se leen con su valor documentado.
    avisos = [int(utils._to_decimal(d)) for d in (rewards.get("blockedNoticeDays") or [20, 27])]
    gracia = int(utils._to_decimal(rewards.get("blockedGraceDays") or 0))

    return {
        "version": PLAN_VERSION,
        "unidades": {
            "mxnPerVp": _f(mxn_por_vp),
            "maxLevels": utils._max_network_levels(cfg),
            "pc": f"PC son los puntos de lista de cada producto (1 PC ≈ ${_f(mxn_por_vp):,.0f} de precio de lista).",
            "vp": "VP son los PC de lo que pagas en el mes, contados sobre el precio ya con descuento (PC × neto ÷ bruto).",
            "vg": f"VG son tus VP más los de tu red hasta {utils._max_network_levels(cfg)} niveles.",
        },
        "activacion": {
            "vpNetos": _f(vp_netos),
            # `pesosAprox` (el "más o menos $1,000" que la propia página
            # desmentía tres renglones abajo) se borró del contrato: en su
            # lugar va el rango real, calculado del catálogo (propuesta 14).
            "rango": rango,
            "ejemplos": _ejemplos_activacion(tiers, vp_netos, productos),
            "nota": (f"{_f(vp_netos):g} PC de lista con {_pct(tasa_primer_tramo)} % de descuento = "
                     f"{_f(vp_con_descuento):g} VP: no activa."),
        },
        "descuento": {
            "tramos": [_tramo_json(t) for t in tiers],
            "ejemplos": _ejemplos_descuento(tiers),
        },
        "generaciones": _generaciones(cfg, compra_ejemplo),
        # Sobre qué base se paga la comisión, dicho con las palabras de §3.2
        # y en el propio contrato, para que ninguna pantalla escriba la suya.
        "baseComision": {
            "clave": impuestos.BASE_COMISION,
            "frase": impuestos.FRASE_BASE_COMISION,
            "compraEjemplo": _f(compra_ejemplo),
            "canastaEjemplo": (f"{canasta['qty']} × {canasta['producto']}" if canasta else ""),
        },
        # El IVA que llevan dentro los precios de lista (propuesta 38).
        "iva": {
            "tasa": _f(impuestos.tasa_iva(cfg)),
            "etiqueta": impuestos.etiqueta_iva(cfg),
            "preciosIncluyenIva": impuestos.precios_con_iva(cfg),
            "aplicaAlEnvio": impuestos.iva_incluye_envio(cfg),
        },
        "compresionDinamica": str(rewards.get("cutRule") or "") == "dynamic_compression",
        "pago": {
            "dia": int(utils._to_decimal(rewards.get("payoutDay") or 0)),
            "estados": ["pendiente", "confirmada", "bloqueada", "pagada"],
            "reevaluaBloqueadasAlActivarse": bool(rewards.get("reevaluateBlockedOnActivation")),
            "bloqueo": {"avisos": avisos, "graciaDias": gracia},
        },
        "datos": [
            {"cuando": "registro", "que": ["nombre", "correo", "teléfono"]},
            # Paquete A · propuesta 2: la CLABE se pide al activarte (el día
            # de pago no da tiempo de conseguirla), y el plan lo dice, para
            # que no contradiga al recordatorio que la socia recibe.
            {"cuando": "modo socio", "que": ["CLABE, cuando te actives en el mes"]},
            {"cuando": "primera comisión confirmada", "que": []},
            {"cuando": "facturación", "que": documentos},
        ],
        "rangos": [
            {"rank": str(r.get("rank") or ""), "vgMin": _f(r.get("vgMin")), "vpMin": _f(r.get("vpMin")),
             "minLines": int(utils._to_decimal(r.get("minLines") or 0)), "monthlyBonus": _f(r.get("monthlyBonus"))}
            for r in sorted(bonuses.get("rankThresholds") or [], key=lambda x: _f(x.get("vgMin")))
        ],
        "bonos": [
            {"id": str(b.get("id") or ""), "name": str(b.get("name") or ""), "notes": str(b.get("notes") or "")}
            for b in (bonuses.get("rules") or []) if b.get("active", True) and not b.get("rank")
        ],
    }


# ---------------------------------------------------------------------------
# Handlers HTTP
# ---------------------------------------------------------------------------

def handle_plan() -> dict:
    """GET /catalog/plan — público."""
    return utils._json_response(200, {"plan": construir_plan()})


# ---------------------------------------------------------------------------
# Simulador de ganancias reales (propuesta 36)
# ---------------------------------------------------------------------------

#: Topes de entrada del simulador. Fuera de rango se responde 400 con el tope
#: escrito, nunca se recorta en silencio.
MAX_DIRECTOS = 100
MAX_IMPORTE = Decimal("100000")

#: Lo único que el simulador promete: que no promete nada.
AVISO_SIMULADOR = "Esto es una calculadora con las reglas del plan, no una promesa de ingresos."


def _entero(valor, nombre: str, minimo: int, maximo: int):
    try:
        numero = int(utils._to_decimal(valor if valor not in (None, "") else 0))
    except (TypeError, ValueError, ArithmeticError):
        return None, f"{nombre} tiene que ser un número entre {minimo} y {maximo}."
    if numero < minimo or numero > maximo:
        return None, f"{nombre} tiene que estar entre {minimo} y {maximo}."
    return numero, None


def _importe(valor, nombre: str):
    try:
        monto = utils._to_decimal(valor if valor not in (None, "") else 0).quantize(utils.D_CENT)
    except (TypeError, ValueError, ArithmeticError):
        return None, f"{nombre} tiene que ser un importe entre $0 y {impuestos.formato_pesos(MAX_IMPORTE)}."
    if monto < 0 or monto > MAX_IMPORTE:
        return None, f"{nombre} tiene que estar entre $0 y {impuestos.formato_pesos(MAX_IMPORTE)}."
    return monto, None


def _requisito_cumplido(nivel: dict, directos: int, vp_propios: Decimal, pc_por_linea: Decimal):
    """(cumple, motivo). Con la misma tabla de requisitos que usa el motor."""
    faltas = []
    pide_directas = int(utils._to_decimal(nivel.get("reqActiveDirects") or 0))
    if directos < pide_directas:
        faltas.append(f"te faltan {pide_directas - directos} directas activas de las {pide_directas} que pide")
    pide_pc = utils._to_decimal(nivel.get("reqPersonalPC") or 0)
    if vp_propios < pide_pc:
        faltas.append(f"llevas {_f(vp_propios):g} PC personales de los {_f(pide_pc):g} que pide")
    pide_lineas = int(utils._to_decimal(nivel.get("reqLines") or 0))
    pide_pc_linea = utils._to_decimal(nivel.get("reqPCPerLine") or 0)
    if pide_lineas > 0:
        lineas_ok = directos if pc_por_linea >= pide_pc_linea else 0
        if lineas_ok < pide_lineas:
            faltas.append(f"te faltan líneas con {_f(pide_pc_linea):g} PC: pide {pide_lineas} y tienes {lineas_ok}")
    return (not faltas), ("cumples el requisito" if not faltas else "; ".join(faltas))


def simular(entrada: dict) -> dict:
    """El cálculo del simulador, con la misma configuración que cobra el motor.

    Ximena Paredes hizo esta cuenta a mano, con lápiz y papel, en diez de sus
    dieciséis tareas: *"para recuperar los ~$1,350 que tengo que gastar cada
    mes necesito diez personas comprando $1,350 cada una, todos los meses"*.
    Aquí la hace la plataforma, con sus propios porcentajes y requisitos, y
    enseña **siempre** la ganancia neta, también cuando sale en rojo.
    """
    cfg = utils._load_app_config()
    tiers = _tiers(cfg)
    mxn_por_vp = utils._to_decimal(utils._mxn_per_vp(cfg))
    vp_activacion = utils._to_decimal(utils._activation_vp(cfg))

    directos = int(entrada["directos"])
    compra_directo = utils._to_decimal(entrada["compraPorDirecto"])
    compra_propia = utils._to_decimal(entrada["compraPropia"])
    niveles_pedidos = int(entrada["nivelesProfundidad"])

    # Tu compra: la misma escalera, el mismo redondeo y los mismos VP netos
    # que aplica el pedido de verdad.
    tasa = _tasa(tiers, compra_propia)
    descuento = (compra_propia * tasa).quantize(utils.D_CENT)
    neto_propio = (compra_propia - descuento).quantize(utils.D_CENT)
    vp_propios = (neto_propio / mxn_por_vp).quantize(utils.D_CENT) if mxn_por_vp > 0 else utils.D_ZERO
    activa = vp_propios >= vp_activacion
    desglose = impuestos.desglose_iva(neto_propio, cfg)

    niveles = sorted((cfg.get("rewards") or {}).get("commissionLevels") or [],
                     key=lambda n: int(utils._to_decimal(n.get("gen") or 0)))
    pc_por_linea = (compra_directo / mxn_por_vp).quantize(utils.D_CENT) if mxn_por_vp > 0 else utils.D_ZERO

    generaciones, comision_total = [], utils.D_ZERO
    for nivel in niveles[:niveles_pedidos]:
        tasa_gen = utils._to_decimal(nivel.get("rate", 0))
        cumple_req, motivo = _requisito_cumplido(nivel, directos, vp_propios, pc_por_linea)
        cumple = bool(activa and cumple_req and directos > 0 and compra_directo > 0)
        if not activa:
            motivo = (f"no activas el mes: llevas {_f(vp_propios):g} VP netos de los "
                      f"{_f(vp_activacion):g} que pide la activación")
        elif directos <= 0 or compra_directo <= 0:
            motivo = "nadie de tu red compró en el mes"
        comision = (compra_directo * directos * tasa_gen).quantize(utils.D_CENT) if cumple else utils.D_ZERO
        comision_total += comision
        generaciones.append({
            "gen": int(utils._to_decimal(nivel.get("gen") or 0)),
            "rate": _f(tasa_gen),
            "personas": directos,
            "compraNetaPorPersona": _f(compra_directo),
            "requisitoTexto": _texto_requisito(nivel),
            "cumple": cumple,
            "porQue": motivo,
            "comision": _f(comision),
            "textoBase": impuestos.texto_base_comision(compra_directo * directos, tasa_gen, comision),
        })

    ganancia_neta = (comision_total - neto_propio).quantize(utils.D_CENT)
    pesos = impuestos.formato_pesos
    explicacion = []
    if directos > 0 and compra_directo > 0:
        explicacion.append(
            f"Con {directos} directa{'s' if directos != 1 else ''} que compra"
            f"{'n' if directos != 1 else ''} {pesos(compra_directo)} ganas {pesos(comision_total)} al mes."
        )
    else:
        explicacion.append("Sin nadie en tu red comprando este mes, tu comisión es de $0.00.")
    if neto_propio > 0:
        explicacion.append(
            f"Tú pagaste {pesos(neto_propio)}"
            + (" para activarte" if activa else " y con eso no activas el mes")
            + f": tu resultado del mes es {pesos(ganancia_neta)}."
        )
    else:
        explicacion.append(f"No capturaste compra propia, así que tu resultado del mes es {pesos(ganancia_neta)}.")
    if not activa and comision_total == 0 and directos > 0:
        explicacion.append(
            f"Sin activarte, las comisiones de tu red quedan bloqueadas: necesitas "
            f"{_f(vp_activacion):g} VP netos en el mes."
        )

    return {
        "tuCompra": {
            "bruto": _f(compra_propia), "tramo": _f(tasa), "descuento": _f(descuento),
            "netoPagado": _f(neto_propio), "vp": _f(vp_propios), "activa": activa,
            "vpParaActivar": _f(vp_activacion),
            "iva": {"base": _f(desglose["base"]), "iva": _f(desglose["iva"]),
                    "tasa": _f(desglose["rate"]), "etiqueta": desglose["label"]},
        },
        "generaciones": generaciones,
        "comisionTotal": _f(comision_total),
        "gastoPropio": _f(neto_propio),
        "gananciaNeta": _f(ganancia_neta),
        "baseComision": impuestos.BASE_COMISION,
        "fraseBaseComision": impuestos.FRASE_BASE_COMISION,
        "explicacion": explicacion,
        "supuestos": [
            "Cada generación se calcula con las mismas personas y la misma compra que capturaste arriba: "
            "no suponemos que tu red crezca sola.",
            "El importe de cada persona es lo que paga, ya con su descuento y sin envío: "
            "es la misma base sobre la que se paga la comisión.",
        ],
        "aviso": AVISO_SIMULADOR,
    }


def handle_simular_plan(body: dict) -> dict:
    """POST /catalog/plan/simular — pública."""
    body = body or {}
    cfg = utils._load_app_config()
    max_niveles = utils._max_network_levels(cfg)

    directos, error = _entero(body.get("directos"), "El número de personas directas", 0, MAX_DIRECTOS)
    if error:
        return utils._json_response(400, {"message": error})
    niveles, error = _entero(body.get("nivelesProfundidad") or 1, "Los niveles de profundidad", 1, max_niveles)
    if error:
        return utils._json_response(400, {"message": error})
    compra_directo, error = _importe(body.get("compraPorDirecto"), "Lo que compra cada persona")
    if error:
        return utils._json_response(400, {"message": error})
    compra_propia, error = _importe(body.get("compraPropia"), "Tu propia compra")
    if error:
        return utils._json_response(400, {"message": error})

    return utils._json_response(200, {"simulacion": simular({
        "directos": directos, "compraPorDirecto": compra_directo,
        "compraPropia": compra_propia, "nivelesProfundidad": niveles,
    })})


def _cliente_de_la_sesion(headers: dict):
    """(customer, error). Solo sesiones de cliente con Bearer; nada de cabeceras legadas."""
    actor = utils._extract_actor_from_bearer(headers or {})
    if not actor.get("user_id") or not actor.get("isCustomer"):
        return None, utils._json_response(401, {"message": "Inicia sesión para ver tu modo de cuenta"})
    customer = utils._get_by_id("CUSTOMER", utils._customer_entity_id(actor["user_id"]))
    if not customer:
        return None, utils._json_response(404, {"message": "Cliente no encontrado"})
    return customer, None


def handle_modo(headers: dict) -> dict:
    """GET /customers/modo — modo de la cuenta e indicadores del mes."""
    customer, error = _cliente_de_la_sesion(headers)
    if error:
        return error
    return utils._json_response(200, {
        "mode": modo_de(customer),
        "modeSince": customer.get("modeSince"),
        "modeActivatedAt": customer.get("modeActivatedAt"),
        "modeReason": customer.get("modeReason"),
        "planVersion": PLAN_VERSION,
        "indicators": indicadores_cliente(customer),
    })


def handle_activar_modo_socio(body: dict, headers: dict) -> dict:
    """POST /customers/modo-socio — la propia sesión, o un admin con `customer_add` y `customerId`."""
    body = body or {}
    objetivo = body.get("customerId")
    actor = utils._extract_actor_from_bearer(headers or {})
    propio = actor.get("user_id") if actor.get("isCustomer") else None

    if objetivo not in (None, "") and str(objetivo) != str(propio):
        error = utils._require_admin(headers, "customer_add")
        if error:
            return error
        cid, motivo = objetivo, "admin"
    elif propio:
        cid, motivo = propio, "solicitud"
    else:
        return utils._json_response(401, {"message": "Inicia sesión para activar el modo socio"})

    modo_pedido = str(body.get("mode") or "socio").strip().lower()
    if modo_pedido not in MODOS:
        return utils._json_response(400, {"message": "El modo debe ser 'cliente' o 'socio'"})
    if modo_pedido == "cliente" and motivo != "admin":
        return utils._json_response(403, {"message": "Solo un administrador puede regresar una cuenta a modo cliente"})

    if modo_pedido == "cliente":
        resultado = _volver_a_cliente(cid)
    else:
        resultado = asegurar_socio(cid, motivo, plan_version=body.get("acceptedPlanVersion") or PLAN_VERSION)
    if resultado is None:
        return utils._json_response(404, {"message": "Cliente no encontrado"})

    customer = utils._get_by_id("CUSTOMER", utils._customer_entity_id(cid)) or {}
    utils._audit_event("customer.mode", headers, {"customerId": str(cid), "mode": modo_pedido},
                       {"customerId": str(cid), "mode": modo_pedido, "reason": motivo})
    return utils._json_response(200, {
        **resultado,
        "customerId": str(customer.get("customerId") or cid),
        "name": customer.get("name") or "",
        "modeReason": customer.get("modeReason"),
        "planVersion": PLAN_VERSION,
    })


def _items_validos(items) -> Optional[Decimal]:
    """Bruto de la lista de líneas, o None si alguna es inválida."""
    if not isinstance(items, list) or not items:
        return None
    bruto = utils.D_ZERO
    for linea in items:
        if not isinstance(linea, dict):
            return None
        try:
            precio = utils._to_decimal(linea.get("price", 0))
            cantidad = int(linea.get("quantity", 1))
        except (TypeError, ValueError, ArithmeticError):
            return None
        if precio < 0 or cantidad < 1:
            return None
        bruto += precio * cantidad
    return bruto


def handle_ahorro_socio(body: dict, headers: dict) -> dict:
    """POST /customers/ahorro-socio — público; el neto del mes solo si la sesión es de ese cliente."""
    body = body or {}
    bruto = _items_validos(body.get("items"))
    if bruto is None:
        return utils._json_response(400, {"message": "Manda al menos una línea con price (≥ 0) y quantity (≥ 1)"})
    neto_mes = utils.D_ZERO
    cid = body.get("customerId")
    if cid not in (None, ""):
        actor = utils._extract_actor_from_bearer(headers or {})
        es_propio = actor.get("user_id") and str(actor["user_id"]) == str(cid)
        es_admin = actor.get("role") in ("admin", "employee")
        if es_propio or es_admin:
            neto_mes = _neto_del_mes(cid, utils._month_key())
    return utils._json_response(200, _ahorro_json(calcular_ahorro(bruto, neto_mes)))


def atender(request) -> Optional[dict]:
    """Responde si la ruta es de este módulo; None si no lo es (cascada de `customer_lambda`)."""
    seg = request.segments[1:] if request.segments[:1] == ["customers"] else request.segments
    if seg == ["modo"] and request.method == "GET":
        return handle_modo(request.headers)
    if seg == ["modo-socio"] and request.method == "POST":
        return handle_activar_modo_socio(request.body, request.headers)
    if seg == ["ahorro-socio"] and request.method == "POST":
        return handle_ahorro_socio(request.body, request.headers)
    return None


RUTAS_CATALOGO = [
    Ruta("GET", "catalog/plan", publica=True, descripcion="Plan publicado con los números reales de la configuración",
         handler=lambda p: handle_plan()),
    # ── Paquete B · ronda 26 (propuesta 36) ─────────────────────────────────
    Ruta("POST", "catalog/plan/simular", publica=True,
         descripcion="Simulador de ganancias con los porcentajes y requisitos reales",
         handler=lambda p: handle_simular_plan(p.body)),
]
