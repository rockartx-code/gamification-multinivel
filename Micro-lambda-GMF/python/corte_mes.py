"""Un solo corte de mes, del servidor (paquete G, propuesta 29).

Había **cuatro** orígenes del mismo número: el servicio del panel, una copia
calcada dentro del propio componente del panel, el carrito (que sin sesión caía
al último día del mes) y el del pedido, que sí venía del servidor. Ximena midió
26 d sin cuenta y 21 d con cuenta **en el mismo minuto**; siete de doce personas
lo anotaron y **ninguna de las siete entendió qué es el corte**:
*"¿se me vence el carrito? ¿se acaba una oferta?"*. Un reloj en cuenta regresiva
sin explicación no apura: asusta.

Este módulo es el único sitio del backend donde vive el día del corte. Publica
dos campos —`cutoffAt`, el instante absoluto, y `serverNow`, el reloj del
servidor— para que el frontend calcule `cutoffAt − (serverNow + transcurrido)`
y deje de fechar el negocio con el reloj del navegador. Sale de valores ya
cargados: **no cuesta ni una consulta más** (§3.6).

Todo el producto trabaja en UTC (`core/values._month_key` incluido), así que el
corte es el día 25 a las 23:59:59 UTC. Es auxiliar y puro: quien no es su dueño
lo importa, no lo edita.
"""
from datetime import datetime, timedelta, timezone

#: Día del mes en que cierra el mes de comisiones y el descuento por volumen.
#: Único sitio donde vive el número: antes estaba escrito a mano en
#: `customer_lambda`, en `dashboard_lambda`, en el servicio del panel y en el
#: componente del panel, y el carrito ni lo usaba.
CUTOFF_DAY = 25
CUTOFF_HOUR = 23
CUTOFF_MINUTE = 59

#: Lo que el reloj cuenta, dicho con todas sus letras. Ninguna de las siete
#: personas que lo vieron entendió de qué era el corte.
CUTOFF_LABEL = "Cierre del mes de comisiones y de tu descuento por volumen"


def _ahora(ahora=None) -> datetime:
    if isinstance(ahora, datetime):
        return ahora.astimezone(timezone.utc)
    if isinstance(ahora, str) and ahora.strip():
        try:
            return datetime.fromisoformat(ahora.strip().replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _iso(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def proximo_corte(ahora=None) -> datetime:
    """Instante del próximo corte: día 25 a las 23:59:59 UTC, este mes o el que viene."""
    momento = _ahora(ahora)
    corte = momento.replace(day=CUTOFF_DAY, hour=CUTOFF_HOUR, minute=CUTOFF_MINUTE,
                            second=59, microsecond=0)
    if corte <= momento:
        # Al primero del mes siguiente y de ahí al día del corte: así no hay que
        # pensar en meses de 28, 30 o 31 días.
        primero = (corte.replace(day=1) + timedelta(days=32)).replace(day=1)
        corte = primero.replace(day=CUTOFF_DAY, hour=CUTOFF_HOUR, minute=CUTOFF_MINUTE,
                                second=59, microsecond=0)
    return corte


def campos_corte(ahora=None) -> dict:
    """Los campos que se añaden a `settings` en cada panel.

    `cutoffDay/Hour/Minute` se conservan para no romper a quien ya los lee;
    `cutoffAt` y `serverNow` son los que mandan a partir de esta ronda.
    """
    momento = _ahora(ahora)
    return {
        "cutoffDay": CUTOFF_DAY,
        "cutoffHour": CUTOFF_HOUR,
        "cutoffMinute": CUTOFF_MINUTE,
        "cutoffAt": _iso(proximo_corte(momento)),
        "cutoffLabel": CUTOFF_LABEL,
        "serverNow": _iso(momento),
    }
