"""Casos dorados del Plan Finding'U abril 2026 (docs/findingu_plan_completo25.04.26.pdf).

Los ejemplos numéricos del plan son la especificación del motor: si un cambio
los rompe, el negocio cambió sin querer. Cubren la escalera de descuentos, la
compresión dinámica de comisiones y el umbral de activación.
"""
from decimal import Decimal

import pytest


# --- Escalera de descuentos (Plan §3) --------------------------------------

@pytest.mark.parametrize("mpn_previo, compra, tasa_esperada", [
    (0,    2950, "0.20"),   # paquete básico sin compras previas → 20%
    (1500, 1000, "0.20"),   # 1,500 + 1,000 = 2,500 → tramo 2,000-2,999
    (2400,  900, "0.30"),   # 2,400 +   900 = 3,300 → tramo 3,000-5,999
    (0,     500, "0.00"),   # por debajo de 1,000 → sin descuento
    (0,    1000, "0.10"),   # justo en el borde inferior del tramo
    (0,    6000, "0.40"),   # tramo superior, sin tope
])
def test_escalera_de_descuentos(utils, mpn_previo, compra, tasa_esperada):
    import order_lambda

    tiers = utils._default_app_config()["rewards"]["discountTiers"]
    base = utils._to_decimal(mpn_previo) + utils._to_decimal(compra)
    assert order_lambda._resolve_discount_rate(tiers, base) == Decimal(tasa_esperada)


def test_descuento_del_paquete_basico_da_2360(utils):
    """$2,950 al 20% = $2,360 netos (ejemplo explícito del plan)."""
    import order_lambda

    tiers = utils._default_app_config()["rewards"]["discountTiers"]
    tasa = order_lambda._resolve_discount_rate(tiers, utils._to_decimal(2950))
    assert utils._to_decimal(2950) * (Decimal("1") - tasa) == Decimal("2360.00")


def test_el_paquete_basico_equivale_a_59_pc(utils):
    """$2,950 / $50 por PC = 59 PC."""
    assert 2950 / utils._mxn_per_vp() == 59


# --- Compresión dinámica (Plan §4) -----------------------------------------

def _sembrar_red(utils, store, cadena, activos, month_key):
    """Cadena ascendente A1←A2←… donde cada eslabón cumple los requisitos del plan.

    Gen3–Gen5 exigen hasta 5 directos activos y 3 líneas con 750 PC, así que a
    cada ascendente se le cuelgan directos adicionales (hojas activas) además
    del eslabón de la cadena. Sin ellos ningún ascendente califica más allá de
    la primera generación y el escenario no probaría la compresión.
    """
    now = "2026-01-01T00:00:00Z"
    siguiente_hoja = 900

    def alta(cid, leader_id, activo):
        store[("CUSTOMER", f"{now}#{cid}")] = {
            "PK": "CUSTOMER", "SK": f"{now}#{cid}", "customerId": cid,
            "name": f"Socio {cid}", "createdAt": now, "leaderId": leader_id,
        }
        store[(f"CUSTOMER#{cid}", "REF")] = {
            "PK": f"CUSTOMER#{cid}", "SK": "REF", "refPK": "CUSTOMER", "refSK": f"{now}#{cid}",
        }
        store[("ASSOCIATE_MONTH", f"{cid}#{month_key}")] = {
            "PK": "ASSOCIATE_MONTH", "SK": f"{cid}#{month_key}",
            "associateId": str(cid), "monthKey": month_key,
            "netVolume": Decimal("50000") if activo else Decimal("0"),
            "netVP": Decimal("1000") if activo else Decimal("0"),
        }

    for i, cid in enumerate(cadena):
        alta(cid, cadena[i + 1] if i + 1 < len(cadena) else None, cid in activos)

    # 4 directos activos extra por ascendente (+1 de la cadena = 5 directos)
    for cid in cadena[1:]:
        for _ in range(4):
            siguiente_hoja += 1
            alta(siguiente_hoja, cid, True)


def test_compresion_dinamica_salta_a_los_no_calificados(utils, store, monkeypatch):
    """Con A2 inactivo, las 5 generaciones las cobran A1, A3, A4, A5 y A6.

    Ejemplo del plan: sobre $2,000 netos, 10/5/4/3/2 % → 200/100/80/60/40,
    total $480 = 24 % (el tope del plan). A2 recibe una fila informativa
    `blocked` y su posición la hereda el siguiente ascendente calificado.
    """
    import commissions_lambda as commissions

    month_key = utils._month_key()
    comprador = 100
    cadena = [comprador, 1, 2, 3, 4, 5, 6]          # 1 = ascendente inmediato
    activos = {comprador, 1, 3, 4, 5, 6}            # 2 NO está activo
    _sembrar_red(utils, store, cadena, activos, month_key)

    now = "2026-01-01T00:00:00Z"
    store[("ORDER", f"{now}#ORD-1")] = {
        "PK": "ORDER", "SK": f"{now}#ORD-1", "orderId": "ORD-1",
        "customerId": comprador, "buyerType": "associate", "monthKey": month_key,
        "netTotal": Decimal("2000"), "grossSubtotal": Decimal("2000"),
        "items": [], "createdAt": now, "status": "paid",
    }
    store[("ORDER#ORD-1", "REF")] = {
        "PK": "ORDER#ORD-1", "SK": "REF", "refPK": "ORDER", "refSK": f"{now}#ORD-1",
    }

    commissions._reset_request_cache()
    commissions.handle_apply_rewards("ORD-1")

    def comision(beneficiario, estado="pending"):
        item = utils._get_ledger_month(beneficiario, month_key)
        return sum(utils._to_decimal(r["amount"]) for r in item["ledger"] if r["status"] == estado)

    assert comision(1) == Decimal("200.00"), "A1 cobra gen1 (10%)"
    assert comision(2) == Decimal("0"), "A2 no califica: no cobra nada"
    assert comision(2, "blocked") > 0, "A2 deja rastro informativo de la posición saltada"
    assert comision(3) == Decimal("100.00"), "A3 hereda gen2 (5%)"
    assert comision(4) == Decimal("80.00"), "A4 hereda gen3 (4%)"
    assert comision(5) == Decimal("60.00"), "A5 hereda gen4 (3%)"
    assert comision(6) == Decimal("40.00"), "A6 hereda gen5 (2%)"

    repartido = sum(comision(b) for b in (1, 2, 3, 4, 5, 6))
    assert repartido == Decimal("480.00")
    assert repartido / Decimal("2000") == Decimal("0.24"), "tope del 24% del plan"


def test_las_comisiones_no_pasan_de_cinco_generaciones(utils, store):
    """Una cadena de 8 ascendentes reparte solo 5 generaciones."""
    import commissions_lambda as commissions

    month_key = utils._month_key()
    comprador = 200
    cadena = [comprador] + list(range(11, 19))
    _sembrar_red(utils, store, cadena, set(cadena), month_key)

    now = "2026-01-01T00:00:00Z"
    store[("ORDER", f"{now}#ORD-2")] = {
        "PK": "ORDER", "SK": f"{now}#ORD-2", "orderId": "ORD-2",
        "customerId": comprador, "buyerType": "associate", "monthKey": month_key,
        "netTotal": Decimal("1000"), "grossSubtotal": Decimal("1000"),
        "items": [], "createdAt": now, "status": "paid",
    }
    store[("ORDER#ORD-2", "REF")] = {
        "PK": "ORDER#ORD-2", "SK": "REF", "refPK": "ORDER", "refSK": f"{now}#ORD-2",
    }

    commissions._reset_request_cache()
    commissions.handle_apply_rewards("ORD-2")

    con_comision = [
        b for b in range(11, 19)
        if any(r["status"] == "pending" for r in utils._get_ledger_month(b, month_key)["ledger"])
    ]
    assert len(con_comision) == 5
    assert con_comision == [11, 12, 13, 14, 15], "las cobran los 5 ascendentes más cercanos"


# --- Compatibilidad del candado optimista con datos anteriores ---------------

def test_el_ledger_legado_sin_version_sigue_siendo_escribible(utils, store):
    """Regresión del hallazgo bloqueante de la revisión.

    Los meses contables escritos ANTES de introducir el candado no tienen
    atributo `version`. En DynamoDB real `version = :cero` falla cuando el
    atributo no existe, así que la condición debe aceptar también
    `attribute_not_exists(version)`; si no, comisiones, confirmaciones y
    anulaciones fallan para todos los beneficiarios existentes.
    """
    from decimal import Decimal as D

    sk = utils._ledger_sk(55, "2026-09")
    store[("COMMISSION_MONTH", sk)] = {
        "PK": "COMMISSION_MONTH", "SK": sk, "entityType": "commissionMonth",
        "beneficiaryId": 55, "monthKey": "2026-09",
        "ledger": [{"rowId": "VIEJA#G1", "orderId": "VIEJA",
                    "amount": D("100"), "status": "pending"}],
        "totalPending": D("100"), "totalConfirmed": D("0"), "totalBlocked": D("0"),
        # sin atributo `version`: así están los items previos al despliegue
    }

    def agregar(item):
        item["ledger"].append({"rowId": "NUEVA#G1", "orderId": "NUEVA",
                               "amount": D("50"), "status": "pending"})
        return True

    resultado = utils._mutate_ledger_month(55, "2026-09", agregar)
    assert len(resultado["ledger"]) == 2
    assert resultado["totalPending"] == D("150")
    assert store[("COMMISSION_MONTH", sk)]["version"] == 1, "el item migra al esquema versionado"

    # Y a partir de ahí el candado protege con normalidad.
    resultado = utils._mutate_ledger_month(55, "2026-09", agregar)
    assert store[("COMMISSION_MONTH", sk)]["version"] == 2
