"""Configuración del negocio: valores por defecto, fusión y accesores."""

import time
from decimal import Decimal
from typing import Any, Dict, Optional

from .settings import APP_CONFIG_TTL_SECONDS
from .values import _merge_dict, _to_decimal
from .db import _get_by_id


def _default_app_config() -> dict:
    return {
        "version": "app-v1",
        "rewards": {
            # Activación mensual: $1,000 MXN netos = 20 PC (con mxnPerVp=50). Plan abril 2026 §3.
            "activationNetMin": Decimal("20"),
            "payoutDay": Decimal("10"),
            # Compresión dinámica activa: salta posiciones no calificadas y paga al
            # siguiente ascendente calificado (Plan abril 2026 §4).
            "cutRule": "dynamic_compression",
            # Al activarse un socio dentro del mes se recalculan las comisiones
            # que le quedaron bloqueadas por estar inactivo al pagar sus referidos.
            "reevaluateBlockedOnActivation": True,
            # Paquete A · pagos-comisiones. Política de bloqueadas (opción b):
            # días del mes en que se avisa a la socia inactiva cuánto tiene
            # bloqueado y qué producto la activa. Vacío = sin avisos.
            "blockedNoticeDays": [Decimal("20"), Decimal("27")],
            # Opción a (apagada): si vale N > 0, una socia que se activa en los
            # primeros N días del mes libera también lo bloqueado del mes anterior.
            "blockedGraceDays": Decimal("0"),
            # Aviso "registra tu CLABE" al activarse por primera vez sin CLABE.
            "clabeReminderOnActivation": True,
            # Escalera de descuentos por MPN (Monto Personal Neto) acumulado en el mes
            # calendario. Importes en MXN. Plan abril 2026 §3.
            "discountTiers": [
                {"min": Decimal("0"),    "max": Decimal("1000"), "rate": Decimal("0.00")},
                {"min": Decimal("1000"), "max": Decimal("2000"), "rate": Decimal("0.10")},
                {"min": Decimal("2000"), "max": Decimal("3000"), "rate": Decimal("0.20")},
                {"min": Decimal("3000"), "max": Decimal("6000"), "rate": Decimal("0.30")},
                {"min": Decimal("6000"), "max": None,                  "rate": Decimal("0.40")},
            ],
            # Comisiones por generación con requisitos de desbloqueo. Plan abril 2026 §4.
            # reqActiveDirects = directos activos; reqPersonalPC = PC netos personales;
            # reqLines = líneas calificadas; reqPCPerLine = PC netos mínimos por línea.
            "commissionLevels": [
                {"gen": 1, "rate": Decimal("0.10"), "reqActiveDirects": 0, "reqPersonalPC": 0,   "reqLines": 0, "reqPCPerLine": 0},
                {"gen": 2, "rate": Decimal("0.05"), "reqActiveDirects": 2, "reqPersonalPC": 0,   "reqLines": 0, "reqPCPerLine": 0},
                {"gen": 3, "rate": Decimal("0.04"), "reqActiveDirects": 3, "reqPersonalPC": 80,  "reqLines": 2, "reqPCPerLine": 300},
                {"gen": 4, "rate": Decimal("0.03"), "reqActiveDirects": 4, "reqPersonalPC": 120, "reqLines": 3, "reqPCPerLine": 450},
                {"gen": 5, "rate": Decimal("0.02"), "reqActiveDirects": 5, "reqPersonalPC": 160, "reqLines": 3, "reqPCPerLine": 750},
            ],
        },
        # agingRedDays (paquete F · ronda 26): días a partir de los cuales un pedido
        # pagado sin envío se pinta en rojo en la tabla y su aviso sube a urgente.
        # "37 días se ven igual que 1 día" (renata-2027-04-10).
        "orders": {"requireStockOnShipped": True, "requireDispatchLinesOnShipped": True,
                   "agingRedDays": 7},
        "pos": {
            "defaultCustomerName": "Publico en General",
            "defaultPaymentStatus": "paid_branch",
            "defaultDeliveryStatus": "delivered_branch",
            "orderStatusByDeliveryStatus": {"delivered_branch": "delivered", "paid_branch": "paid"},
            # Arqueo (paquete E): correo de la gerente al que se manda el comprobante
            # del corte (vacío = el botón "Enviar por correo" pide uno), billetes y
            # monedas para contar por denominación, y si una diferencia entre lo
            # contado y lo esperado exige motivo.
            "cashCutNotifyEmail": "",
            # Paquete F · ronda 26: a quién se le entrega el turno desde
            # "Resumen de turno" (vacío = el botón pide escribir el correo).
            # Toño se lo mandaba a Renata por WhatsApp.
            "shiftSummaryNotifyEmail": "",
            "denominations": [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1],
            "requireDifferenceReason": True,
            # Paquete F · ronda 26: abrir turno. Con True, una caja que nunca ha
            # cerrado un corte pide el fondo con el que arranca en vez de enseñar
            # un "$0.00" de solo lectura (el sobrante falso de $540 de Mireya).
            "requireOpeningCash": True,
        },
        # minStockDefault (paquete F · ronda 26): mínimo de piezas por producto y
        # sucursal cuando el producto no trae el suyo (`PRODUCT.minStock`). Con 0
        # no se vigila nada; con un número, la tabla lo pinta en rojo y sale en
        # Acciones urgentes.
        "stocks": {"requireLinkedUserForTransferReceive": True, "minStockDefault": 0},
        "payments": {
            "mercadoLibre": {
                "enabled": False, "accessToken": "", "currencyId": "MXN",
                "checkoutPreferencesUrl": "https://api.mercadopago.com/checkout/preferences",
                "paymentInfoUrlTemplate": "https://api.mercadopago.com/v1/payments/{payment_id}",
                # Conciliación (paquete H): búsqueda de pagos por referencia externa (el orderId).
                "paymentSearchUrlTemplate": "https://api.mercadopago.com/v1/payments/search?external_reference={order_id}&sort=date_created&criteria=desc",
                "notificationUrl": "", "successUrl": "", "failureUrl": "", "pendingUrl": "", "webhookSecret": "",
            },
            # Ventana (horas) de pedidos pendientes que revisa "Conciliar pagos" (paquete H).
            "reconciliationHours": Decimal("72"),
        },
        "adminWarnings": {
            "showCommissions": True, "showShipping": True, "showPendingPayments": True,
            "showPendingTransfers": True, "showPosSalesToday": True,
            # Paquete F · ronda 26: productos por debajo de su mínimo.
            "showLowStock": True,
        },
        # freeShippingMin: importe a partir del cual el envío es gratis; 0 = sin regla.
        # freeShippingBasis: "gross" mide la regla sobre el subtotal bruto (lo que el
        # carrito enseña antes de descuentos, paquete C); "net" conserva la regla
        # anterior sobre el neto pagado. baseRateMxn: tarifa desde la que se
        # anuncia el envío antes de cotizar ("Envío desde $129").
        "shipping": {
            "enabled": True, "markup": 0.0, "carriers": ["dhl", "fedex"], "freeShippingMin": Decimal("0"),
            "freeShippingBasis": "gross", "baseRateMxn": Decimal("129"),
            # Paquetería integrada (paquete D): generación de guía desde el pedido y
            # rastreo por consulta programable. Apagada por omisión; provider
            # "envia" en producción o "simulada" en pruebas y en el harness.
            # askDays: días tras el envío para preguntar "¿te llegó?";
            # autoCloseDays: días para marcar entregado automáticamente;
            # simDeliveryDays: días en que la paquetería simulada "entrega".
            "carrierIntegration": {
                "enabled": False, "provider": "envia", "autoLabel": False, "trackingEnabled": False,
                "askDays": Decimal("7"), "autoCloseDays": Decimal("10"), "simDeliveryDays": Decimal("3"),
            },
        },
        "customerDocumentTypes": [
            {"key": "constancia", "label": "Constancia de situación fiscal", "required": True},
            {"key": "ine",        "label": "INE (frente y reverso)",          "required": True},
            {"key": "curp",       "label": "CURP",                            "required": True},
        ],
        "bonuses": {
            "vpConfig": {"mxnPerVp": 50, "maxNetworkLevels": 5},
            # Rangos de liderazgo. Plan abril 2026 §6. PC netos (proporcionales al neto pagado).
            # vpMin = PC personal mín.; vgMin = VG mín.; minLines = líneas activas;
            # pcMinPerLine = PC mín. por línea; requiredLeaders/requiredLeaderRank = líderes
            # del rango inferior requeridos en la red.
            "rankThresholds": [
                {"rank": "BRONCE",   "vpMin": 60,  "vgMin": 4500,  "minLines": 3, "pcMinPerLine": 900,  "requiredLeaders": 0, "requiredLeaderRank": "",        "monthlyBonus": 500,   "annualBonus": 6000},
                {"rank": "PLATA",    "vpMin": 90,  "vgMin": 9000,  "minLines": 4, "pcMinPerLine": 1500, "requiredLeaders": 2, "requiredLeaderRank": "BRONCE",  "monthlyBonus": 1500,  "annualBonus": 18000},
                {"rank": "ORO",      "vpMin": 140, "vgMin": 15000, "minLines": 4, "pcMinPerLine": 2500, "requiredLeaders": 2, "requiredLeaderRank": "PLATA",   "monthlyBonus": 3000,  "annualBonus": 36000},
                {"rank": "PLATINO",  "vpMin": 200, "vgMin": 21000, "minLines": 5, "pcMinPerLine": 3000, "requiredLeaders": 2, "requiredLeaderRank": "ORO",     "monthlyBonus": 6000,  "annualBonus": 72000},
                {"rank": "DIAMANTE", "vpMin": 280, "vgMin": 25000, "minLines": 5, "pcMinPerLine": 4000, "requiredLeaders": 2, "requiredLeaderRank": "PLATINO", "monthlyBonus": 10000, "annualBonus": 120000},
            ],
            "rules": [
                {
                    # §7.1 Bono de Inicio Rápido: 600 PC grupales en los primeros 30 días, una sola vez.
                    "id": "inicio_rapido", "name": "Bono de Inicio Rápido", "active": True,
                    "conditions": [{"type": "first_30_days"}, {"type": "vg_min", "value": 600}],
                    "rewards": [{"type": "cash_mxn", "amount": 5000}],
                    "cooldown": "once",
                    "notes": "Primeros 30 días: 600 PC grupales del equipo → $5,000 MXN (una vez).",
                },
                # §7.2 Bono Mensual por Rango: se mantiene el rango 3 meses (calificación, no cobra)
                # y se cobra a partir del 4º mes consecutivo. consecutive_months=4 sobre el vgMin del rango.
                {
                    "id": "bono_rango_bronce", "name": "Bono Mensual BRONCE", "active": True, "rank": "BRONCE",
                    "conditions": [{"type": "vg_min", "value": 4500}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 500}],
                    "cooldown": "monthly",
                    "notes": "$500/mes desde el 4º mes consecutivo en BRONCE.",
                },
                {
                    "id": "bono_rango_plata", "name": "Bono Mensual PLATA", "active": True, "rank": "PLATA",
                    "conditions": [{"type": "vg_min", "value": 9000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 1500}],
                    "cooldown": "monthly",
                    "notes": "$1,500/mes desde el 4º mes consecutivo en PLATA.",
                },
                {
                    "id": "bono_rango_oro", "name": "Bono Mensual ORO", "active": True, "rank": "ORO",
                    "conditions": [{"type": "vg_min", "value": 15000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 3000}],
                    "cooldown": "monthly",
                    "notes": "$3,000/mes desde el 4º mes consecutivo en ORO.",
                },
                {
                    "id": "bono_rango_platino", "name": "Bono Mensual PLATINO", "active": True, "rank": "PLATINO",
                    "conditions": [{"type": "vg_min", "value": 21000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 6000}],
                    "cooldown": "monthly",
                    "notes": "$6,000/mes desde el 4º mes consecutivo en PLATINO.",
                },
                {
                    "id": "bono_rango_diamante", "name": "Bono Mensual DIAMANTE", "active": True, "rank": "DIAMANTE",
                    "conditions": [{"type": "vg_min", "value": 25000}, {"type": "consecutive_months", "value": 4}],
                    "rewards": [{"type": "monthly_cash", "amount": 10000}],
                    "cooldown": "monthly",
                    "notes": "$10,000/mes desde el 4º mes consecutivo en DIAMANTE.",
                },
                # §7.3 Premios físicos por sostenimiento de rango (una sola vez por rango).
                {
                    "id": "premio_bronce_3m", "name": "Premio BRONCE (3 meses)", "active": True, "rank": "BRONCE",
                    "conditions": [{"type": "vg_min", "value": 4500}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Licuadora o Air Fryer", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_plata_3m", "name": "Premio PLATA (3 meses)", "active": True, "rank": "PLATA",
                    "conditions": [{"type": "vg_min", "value": 9000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Microondas o equivalente", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_oro_3m", "name": "Premio ORO (3 meses)", "active": True, "rank": "ORO",
                    "conditions": [{"type": "vg_min", "value": 15000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Pantalla Smart TV", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_platino_3m", "name": "Premio PLATINO (3 meses)", "active": True, "rank": "PLATINO",
                    "conditions": [{"type": "vg_min", "value": 21000}, {"type": "consecutive_months", "value": 3}],
                    "rewards": [{"type": "item", "itemLabel": "Experiencia premium", "triggerMonths": 3}],
                    "cooldown": "once",
                },
                {
                    "id": "premio_diamante_6m", "name": "Premio DIAMANTE (6 meses)", "active": True, "rank": "DIAMANTE",
                    "conditions": [{"type": "vg_min", "value": 25000}, {"type": "consecutive_months", "value": 6}],
                    "rewards": [{"type": "item", "itemLabel": "Viaje internacional elite", "triggerMonths": 6}],
                    "cooldown": "once",
                },
            ],
        },
        # Paquete C · sesión: sin "recordarme" la sesión dura sessionShortSeconds
        # (24 h); el enlace de acceso por correo vale loginLinkMinutes; en la
        # recuperación de contraseña se aceptan los últimos recoveryCodesKept
        # códigos vigentes (el primero no se invalida si el correo llega tarde).
        "auth": {
            "sessionShortSeconds": Decimal("86400"),
            "loginLinkMinutes": Decimal("15"),
            "recoveryCodesKept": Decimal("3"),
        },
        # Paquete C · checkout: casilla "Quiero factura" y catálogos SAT acotados
        # que se ofrecen al capturar los datos fiscales (sin timbrado CFDI).
        "checkout": {
            "invoiceEnabled": True,
            "regimenesFiscales": [
                {"key": "601", "label": "601 · General de Ley Personas Morales"},
                {"key": "605", "label": "605 · Sueldos y Salarios e Ingresos Asimilados a Salarios"},
                {"key": "606", "label": "606 · Arrendamiento"},
                {"key": "612", "label": "612 · Personas Físicas con Actividades Empresariales y Profesionales"},
                {"key": "616", "label": "616 · Sin obligaciones fiscales"},
                {"key": "621", "label": "621 · Incorporación Fiscal"},
                {"key": "626", "label": "626 · Régimen Simplificado de Confianza"},
            ],
            "usosCfdi": [
                {"key": "G01", "label": "G01 · Adquisición de mercancías"},
                {"key": "G03", "label": "G03 · Gastos en general"},
                {"key": "S01", "label": "S01 · Sin efectos fiscales"},
            ],
        },
        # Seguimiento de la coach (paquete F). defaultExecutiveId: empleada dueña de
        # la cartera "FindingU" (clientes sin patrocinadora ni ejecutiva); vacío =
        # cualquier admin/empleada con la pantalla. Umbrales en días para decidir la
        # situación de cada cliente. templates: sobreescribe por clave las plantillas
        # de WhatsApp que viven en `seguimiento_handlers.PLANTILLAS`.
        "seguimiento": {
            "defaultExecutiveId": "",
            "coldDays": Decimal("30"),
            "welcomeDays": Decimal("7"),
            "lateOrderDays": Decimal("5"),
            "templates": {},
        },
        # Paquete G · devoluciones. Medio y plazo del reembolso que se prometen en
        # pantalla y en el correo ("al mismo medio de pago, en 3 a 5 días hábiles
        # tras validar el paquete"). Texto libre para que el negocio lo ajuste.
        "returns": {"refundMethod": "mismo medio de pago", "refundBusinessDays": "3 a 5"},
        # Suscripción mensual (paquete H): el día elegido se crea el pedido y se manda
        # el enlace de pago por correo; no hay cobro automático. Día permitido 1–28.
        "subscriptions": {"enabled": True, "minDay": Decimal("1"), "maxDay": Decimal("28"), "reminderDaysBefore": Decimal("0")},
    }

def _normalize_app_config(raw) -> dict:
    base = _default_app_config()
    merged = _merge_dict(base, raw if isinstance(raw, dict) else {})
    return merged

_app_config_cache: Dict[str, Any] = {"value": None, "loadedAt": 0.0}

def _load_app_config(force_reload: bool = False) -> dict:
    """Configuración global del negocio, cacheada con TTL corto.

    Antes usaba `lru_cache(maxsize=1)` sin invalidación: tras guardar la
    configuración, los contenedores tibios del resto de lambdas seguían
    calculando comisiones, descuentos y rangos con los valores viejos hasta
    que AWS los reciclaba. Con TTL la propagación está acotada a
    APP_CONFIG_TTL_SECONDS.
    """
    now = time.time()
    if (not force_reload
            and _app_config_cache["value"] is not None
            and (now - _app_config_cache["loadedAt"]) < APP_CONFIG_TTL_SECONDS):
        return _app_config_cache["value"]

    cfg = _get_by_id("CONFIG", "app-v1")
    # Se fusiona sobre los defaults: así toda clave existe siempre y nadie
    # necesita repetir un valor por defecto en el punto de lectura.
    value = _normalize_app_config(cfg.get("config") if cfg else None)
    _app_config_cache["value"] = value
    _app_config_cache["loadedAt"] = now
    return value

def _mxn_per_vp(cfg: Optional[dict] = None) -> float:
    """Pesos mexicanos que equivalen a 1 PC (punto de comisión)."""
    cfg = cfg if cfg is not None else _load_app_config()
    vp_cfg = ((cfg.get("bonuses") or {}).get("vpConfig") or {})
    value = float(_to_decimal(vp_cfg.get("mxnPerVp", 50)))
    return value if value > 0 else 50.0

def _max_network_levels(cfg: Optional[dict] = None) -> int:
    """Profundidad de red que se considera para VG y comisiones."""
    cfg = cfg if cfg is not None else _load_app_config()
    vp_cfg = ((cfg.get("bonuses") or {}).get("vpConfig") or {})
    return int(_to_decimal(vp_cfg.get("maxNetworkLevels", 5)))

def _activation_vp(cfg: Optional[dict] = None) -> float:
    """Umbral de activación mensual, **en PC** (no en MXN).

    Plan abril 2026 §3: $1,000 MXN netos = 20 PC. La unidad importa — comparar
    `netVolume` (MXN) contra este valor da "activo" a casi cualquiera.
    Para comparar contra un importe en pesos, usar `_activation_mxn`.
    """
    cfg = cfg if cfg is not None else _load_app_config()
    return float(_to_decimal((cfg.get("rewards") or {}).get("activationNetMin", 20)))

def _activation_mxn(cfg: Optional[dict] = None) -> float:
    """Mismo umbral de activación expresado en MXN netos."""
    cfg = cfg if cfg is not None else _load_app_config()
    return _activation_vp(cfg) * _mxn_per_vp(cfg)

def _invalidate_app_config_cache() -> None:
    """Fuerza la recarga de la configuración en la próxima lectura."""
    _app_config_cache["value"] = None
    _app_config_cache["loadedAt"] = 0.0
