"""Ruteo declarativo: una tabla de rutas en vez de una cascada de `if`.

Los `lambda_handler` despachaban con cascadas donde el ORDEN importaba y el
privilegio de cada endpoint quedaba enterrado dentro del `if`. Con una tabla,
la superficie de cada lambda —qué rutas expone y qué privilegio exige cada
una— se lee de un vistazo y es auditable.

    RUTAS = [
        Ruta("GET",  "catalog",              handler=lambda r: handle_catalog(r.method)),
        Ruta("POST", "catalog/product",      privilegio="product_add",
             handler=lambda r: handle_products(r.method, r.body, None)),
        Ruta("GET",  "catalog/product/{id}", handler=lambda r: handle_get(r.params["id"])),
    ]

Reglas del emparejamiento:

- Los patrones se comparan **segmento a segmento**, así que `catalog/product`
  NO atrapa `catalog/product/algo`: cada ruta declara su forma exacta. Es la
  diferencia con las cascadas por prefijo, que despachaban `/campaigns/loquesea`
  al handler de campañas con cualquier método.
- `{nombre}` captura un segmento y llega en `peticion.params`.
- `*` como último segmento captura el resto (para sub-recursos aún sin migrar).
- Una ruta con `metodo=None` acepta cualquier método.
- Si el path existe pero con otro método, se responde 405 (no 404): así el
  cliente distingue "no existe" de "no se puede hacer así".
"""

from typing import Callable, List, Optional

from .http import HttpRequest, _handle_unexpected, _json_response
from .logs import _log


class Ruta:
    """Una entrada de la tabla de rutas."""

    __slots__ = ("metodo", "patron", "segmentos", "privilegio", "handler", "publica", "descripcion")

    def __init__(self, metodo: Optional[str], patron: str, handler: Callable,
                 privilegio: Optional[str] = None, publica: bool = False,
                 descripcion: str = ""):
        self.metodo = metodo.upper() if metodo else None
        self.patron = patron.strip("/")
        self.segmentos = [s for s in self.patron.split("/") if s]
        self.privilegio = privilegio
        self.handler = handler
        self.publica = publica
        self.descripcion = descripcion

    def coincide(self, segmentos: List[str]):
        """Devuelve los parámetros capturados, o None si no coincide."""
        params = {}
        for i, esperado in enumerate(self.segmentos):
            if esperado == "*":
                params["resto"] = segmentos[i:]
                return params
            if i >= len(segmentos):
                return None
            if esperado.startswith("{") and esperado.endswith("}"):
                params[esperado[1:-1]] = segmentos[i]
            elif esperado != segmentos[i]:
                return None
        return params if len(segmentos) == len(self.segmentos) else None


class Peticion(HttpRequest):
    """Petición con los parámetros de ruta ya extraídos."""

    def __init__(self, event: dict, strip_prefix: Optional[str] = None):
        super().__init__(event, strip_prefix)
        self.params = {}


def despachar(rutas: List[Ruta], event: dict, strip_prefix: Optional[str] = None,
              servicio: str = "", raiz=None, requiere_privilegio=None) -> dict:
    """Resuelve el evento contra la tabla y ejecuta el handler que coincida.

    `requiere_privilegio(headers, privilegio)` se inyecta desde el lambda para
    no atar esta capa al módulo de seguridad.
    """
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        from .http import _cors_preflight_response
        return _cors_preflight_response()

    peticion = Peticion(event, strip_prefix)

    if not peticion.segments:
        return raiz(peticion) if raiz else _json_response(200, {"service": servicio})

    ruta_con_otro_metodo = False
    for ruta in rutas:
        params = ruta.coincide(peticion.segments)
        if params is None:
            continue
        if ruta.metodo and ruta.metodo != peticion.method:
            ruta_con_otro_metodo = True
            continue

        peticion.params = params
        if ruta.privilegio and requiere_privilegio:
            error = requiere_privilegio(peticion.headers, ruta.privilegio)
            if error:
                return error
        try:
            return ruta.handler(peticion)
        except Exception as error:                                  # noqa: BLE001
            return _handle_unexpected(
                f"{servicio or 'lambda'}_unhandled_error", error,
                path=peticion.path, method=peticion.method,
            )

    if ruta_con_otro_metodo:
        return _json_response(405, {"message": f"Método {peticion.method} no permitido en {peticion.path}"})

    _log("route_not_found", "INFO", path=peticion.path, method=peticion.method, service=servicio)
    return _json_response(404, {"message": f"Ruta {peticion.path} no encontrada"})


def describir(rutas: List[Ruta]) -> List[dict]:
    """Tabla legible de la superficie del lambda (para docs y auditoría)."""
    return [
        {
            "metodo": ruta.metodo or "ANY",
            "patron": "/" + ruta.patron,
            "privilegio": ruta.privilegio or ("público" if ruta.publica else "sesión"),
            "descripcion": ruta.descripcion,
        }
        for ruta in rutas
    ]
