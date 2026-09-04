"""IVA y base de la comisión: una sola cuenta y una sola redacción (paquete B).

Dos huecos medidos en la ronda 6 (docs/qa/25):

- **El IVA no se desglosa en ningún lado.** Los precios de lista ya lo
  incluyen, pero ni el carrito, ni el recibo, ni el correo, ni el corte de
  caja lo dicen: la persona que compara con su estado de cuenta no sabe
  cuánto pagó de impuesto ni sobre qué base se calculó.
- **Nadie escribió sobre qué se paga la comisión.** Ximena Paredes lo buscó
  en tres pantallas: *"$135 de $1,350 o de $1,500, ¿de cuál?"*. El motor
  siempre pagó sobre el neto por producto, sin envío; faltaba decirlo.

Este módulo es **auxiliar puro**: no lee la tabla, no escribe nada y no
depende de ningún lambda. Otros paquetes lo **importan**, no lo editan
(docs/arquitectura/26 §0.2.4).

Supuesto exacto del IVA (docs/arquitectura/26 §3.1 y §4.1-§4.2), escrito una
sola vez y aquí:

- Los precios de lista se manejan **con IVA incluido**. El IVA nunca se suma:
  se **desglosa** de un total que no cambia ni un centavo.
- La base gravable es **todo lo que se cobra**: producto después de descuento
  y cupón **más el envío**, que es un servicio gravado (`taxes.appliesToShipping`).
- Se redondea **una sola vez, al final, a dos decimales y mitad arriba**,
  sobre el total del pedido; nunca por línea (redondear por línea y sumar
  produce el descuadre de un centavo).

      base = redondear(total / (1 + tasa), 2, mitad_arriba)
      iva  = total - base          # base + iva == total, siempre, al centavo
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import core_utils as utils

#: Dos decimales, que es como se cobra y como se lee en pantalla.
CENTAVO = Decimal("0.01")


def _taxes(cfg: Optional[dict] = None) -> dict:
    cfg = cfg if cfg is not None else utils._load_app_config()
    return (cfg or {}).get("taxes") or {}


def tasa_iva(cfg: Optional[dict] = None) -> Decimal:
    """Tasa vigente (`taxes.vatRate`). Fuera de [0, 1) se ignora y vale 0."""
    tasa = utils._to_decimal(_taxes(cfg).get("vatRate", 0))
    return tasa if Decimal("0") <= tasa < Decimal("1") else Decimal("0")


def etiqueta_iva(cfg: Optional[dict] = None) -> str:
    """Cómo se llama el impuesto en pantalla (`taxes.label`)."""
    return str(_taxes(cfg).get("label") or "IVA")


def precios_con_iva(cfg: Optional[dict] = None) -> bool:
    return bool(_taxes(cfg).get("pricesIncludeVat", True))


def iva_incluye_envio(cfg: Optional[dict] = None) -> bool:
    return bool(_taxes(cfg).get("appliesToShipping", True))


def desglose_iva(total_cobrado, cfg: Optional[dict] = None) -> dict:
    """Desglosa el IVA de un total que ya lo incluye.

    Devuelve `{"total", "base", "iva", "rate", "label"}` con
    `base + iva == total` al centavo, siempre. Un total ≤ 0 (o una tasa en
    cero) devuelve el total como base y cero de impuesto: nunca un negativo
    ni un "IVA" inventado.
    """
    cfg = cfg if cfg is not None else utils._load_app_config()
    total = utils._to_decimal(total_cobrado).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    tasa = tasa_iva(cfg)
    if total <= 0 or tasa <= 0:
        return {"total": total, "base": total, "iva": Decimal("0.00"),
                "rate": tasa, "label": etiqueta_iva(cfg)}
    base = (total / (Decimal("1") + tasa)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return {"total": total, "base": base, "iva": (total - base).quantize(CENTAVO),
            "rate": tasa, "label": etiqueta_iva(cfg)}


def campos_pedido(total_cobrado, cfg: Optional[dict] = None) -> dict:
    """Los tres campos que el pedido guarda al crearse: `vatRate`, `taxBase`,
    `taxAmount`.

    Se guardan con el pedido —no se recalculan al leerlo— para que un cambio
    futuro de tasa no reescriba la historia (docs/arquitectura/26 §4.4).
    """
    desglose = desglose_iva(total_cobrado, cfg)
    return {"vatRate": desglose["rate"], "taxBase": desglose["base"], "taxAmount": desglose["iva"]}


def desglose_de_pedido(order: dict, cfg: Optional[dict] = None) -> dict:
    """El desglose de un pedido ya guardado.

    Si el pedido trae `taxBase`/`taxAmount` (nació después de esta ronda), se
    respetan tal cual: son los de su día. Los pedidos anteriores no se migran
    y su desglose se calcula al vuelo con la tasa vigente.
    """
    order = order or {}
    total = utils._to_decimal(order.get("total", 0))
    if order.get("taxBase") is not None and order.get("taxAmount") is not None:
        return {
            "total": total.quantize(CENTAVO, rounding=ROUND_HALF_UP),
            "base": utils._to_decimal(order.get("taxBase")).quantize(CENTAVO),
            "iva": utils._to_decimal(order.get("taxAmount")).quantize(CENTAVO),
            "rate": utils._to_decimal(order.get("vatRate", 0)),
            "label": etiqueta_iva(cfg),
        }
    return desglose_iva(total, cfg)


# ---------------------------------------------------------------------------
# Sobre qué base se paga la comisión (propuesta 37)
# ---------------------------------------------------------------------------

#: Cómo llama el negocio a la base de la comisión, con las palabras del plan.
BASE_COMISION = "neto pagado por producto, sin envío"

#: La frase larga, para la página del plan, el simulador y el correo de comisión.
FRASE_BASE_COMISION = (
    "Tu comisión se calcula sobre el neto que pagó tu referida por producto "
    "—el precio ya con su descuento, con IVA incluido— y sin contar el envío."
)


def _pesos(monto) -> str:
    """`$1,350.00`, siempre con centavos: es un importe de dinero, no un dato."""
    return "${:,.2f}".format(utils._to_decimal(monto))


def _porcentaje(tasa) -> str:
    """0.10 → `10 %`; 0.075 → `7.5 %`. Sin ceros de relleno."""
    valor = utils._to_decimal(tasa) * Decimal("100")
    texto = format(valor.normalize(), "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return f"{texto or '0'} %"


def texto_base_comision(neto, tasa, importe) -> str:
    """La frase por fila: *"10 % de $1,350.00 netos, sin envío = $135.00"*.

    Se escribe **una sola vez** y se usa en los cinco sitios donde aparece un
    importe de comisión (docs/arquitectura/26 §3.2): la página del plan, el
    simulador, la fila del panel de la socia, el correo de comisión y Pagos
    del mes. Ningún paquete escribe su propia versión.
    """
    return f"{_porcentaje(tasa)} de {_pesos(neto)} netos, sin envío = {_pesos(importe)}"
