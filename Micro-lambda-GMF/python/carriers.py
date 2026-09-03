"""Adaptador de paquetería (paquete D · almacén, despacho y paquetería).

No expone rutas: `despacho_handlers` lo usa para generar guías desde el pedido
y para consultar el rastreo por tarea programada (no por webhook).

    paqueteria = paqueteria_activa()          # según shipping.carrierIntegration
    guia = paqueteria.generar_guia(pedido)    # {carrier, trackingNumber, labelUrl}
    estado = paqueteria.rastrear("Estafeta", "EST-1", order=pedido)
    # {status: "in_transit" | "delivered" | "exception", deliveredAt?, signedBy?, events: [...]}

Implementaciones:

- `EnviaPaqueteria`: la integración de Envia que ya usa `shipping_lambda`
  para cotizar. Endpoints en `ENVIA_GENERATE_URL` y `ENVIA_TRACK_URL`, clave en
  `ENVIA_API_KEY`. Los nombres de los endpoints se toman del entorno porque la
  documentación vigente de Envia debe confirmarlos antes de desplegar.
- `PaqueteriaSimulada`: entrega a los `simDeliveryDays` con firma
  "Recibió: {recipientName}". La usan las pruebas y el harness cuando
  `provider = "simulada"`.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import core_utils as utils


ENVIA_API_KEY = utils.os.getenv("ENVIA_API_KEY", "")
ENVIA_GENERATE_URL = utils.os.getenv("ENVIA_GENERATE_URL", "https://api-test.envia.com/ship/generate/")
ENVIA_TRACK_URL = utils.os.getenv("ENVIA_TRACK_URL", "https://api-test.envia.com/ship/generaltrack/")


def _fecha(iso: str):
    """ISO → datetime con zona; None si viene vacío o roto."""
    texto = str(iso or "").strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def _config_paqueteria(cfg=None) -> dict:
    cfg = cfg if cfg is not None else utils._load_app_config()
    return dict(((cfg.get("shipping") or {}).get("carrierIntegration")) or {})


class Paqueteria:
    """Contrato mínimo que cumplen todas las paqueterías."""

    nombre = "paqueteria"

    def generar_guia(self, order: dict) -> dict:
        raise NotImplementedError

    def rastrear(self, carrier: str, tracking_number: str, order: dict | None = None) -> dict:
        raise NotImplementedError


class PaqueteriaSimulada(Paqueteria):
    """Entrega "sola" pasados `dias_entrega` días desde el envío."""

    nombre = "simulada"

    def __init__(self, dias_entrega: int = 3):
        self.dias_entrega = max(0, int(dias_entrega))

    def generar_guia(self, order: dict) -> dict:
        oid = str(order.get("orderId") or "").strip() or utils.uuid.uuid4().hex[:8].upper()
        tracking = f"SIM-{oid.replace('ORD-', '')}"
        return {"carrier": "Simulada", "trackingNumber": tracking,
                "labelUrl": f"https://paqueteria.simulada/guias/{tracking}.pdf"}

    def rastrear(self, carrier: str, tracking_number: str, order: dict | None = None) -> dict:
        order = order or {}
        salida = _fecha(order.get("shippedAt")) or _fecha(order.get("updatedAt"))
        ahora = datetime.now(timezone.utc)
        if salida is None:
            return {"status": "in_transit", "events": [{"at": utils._now_iso(), "text": "Sin fecha de envío"}]}
        entrega = salida + timedelta(days=self.dias_entrega)
        eventos = [{"at": salida.isoformat().replace("+00:00", "Z"), "text": "Recolectado"}]
        if ahora >= entrega:
            firma = f"Recibió: {order.get('recipientName') or order.get('customerName') or 'destinatario'}"
            entregado = entrega.isoformat().replace("+00:00", "Z")
            eventos.append({"at": entregado, "text": f"Entregado. {firma}"})
            return {"status": "delivered", "deliveredAt": entregado, "signedBy": firma, "events": eventos}
        eventos.append({"at": utils._now_iso(), "text": "En tránsito"})
        return {"status": "in_transit", "events": eventos}


class EnviaPaqueteria(Paqueteria):
    """Integración con Envia (misma cuenta y origen que la cotización)."""

    nombre = "envia"

    def __init__(self, api_key: str | None = None, generate_url: str | None = None, track_url: str | None = None):
        self.api_key = api_key if api_key is not None else ENVIA_API_KEY
        self.generate_url = generate_url or ENVIA_GENERATE_URL
        self.track_url = track_url or ENVIA_TRACK_URL

    def _llamar(self, url: str, payload: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(payload, default=utils._json_default).encode())
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "FindingU/1.0")
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode())

    def generar_guia(self, order: dict) -> dict:
        import shipping_lambda  # origen y empaquetado ya resueltos ahí

        direccion = order.get("shippingAddress") or {}
        destino = {
            "name": order.get("recipientName") or order.get("customerName") or "Cliente",
            "phone": order.get("phone") or direccion.get("phone") or "0000000000",
            "street": order.get("street") or direccion.get("street") or "Calle",
            "number": order.get("number") or direccion.get("number") or "1",
            "city": order.get("city") or direccion.get("city") or "Ciudad",
            "state": order.get("state") or direccion.get("state") or "Estado",
            "country": (order.get("country") or direccion.get("country") or "MX").upper(),
            "postalCode": order.get("postalCode") or direccion.get("postalCode") or "",
        }
        carrier = str(order.get("shippingCarrier") or "estafeta").strip().lower()
        payload = {
            "origin": shipping_lambda.ORIGIN_DATA,
            "destination": destino,
            "packages": shipping_lambda._pack_items_for_shipping(order.get("items") or []),
            "shipment": {"type": 1, "carrier": carrier},
        }
        try:
            respuesta = self._llamar(self.generate_url, payload)
        except urllib.error.HTTPError as exc:
            cuerpo = ""
            try:
                cuerpo = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            raise RuntimeError(f"Envia respondió {exc.code} al generar la guía: {cuerpo}") from exc
        datos = respuesta.get("data") or []
        primero = datos[0] if isinstance(datos, list) and datos else (datos if isinstance(datos, dict) else {})
        tracking = str(primero.get("trackingNumber") or primero.get("tracking_number") or "").strip()
        if not tracking:
            raise RuntimeError("Envia no devolvió número de guía")
        return {
            "carrier": str(primero.get("carrier") or carrier).title(),
            "trackingNumber": tracking,
            "labelUrl": primero.get("label") or primero.get("labelUrl") or "",
        }

    def rastrear(self, carrier: str, tracking_number: str, order: dict | None = None) -> dict:
        payload = {"trackingNumbers": [str(tracking_number)], "carrier": str(carrier or "").lower()}
        try:
            respuesta = self._llamar(self.track_url, payload)
        except Exception as exc:  # noqa: BLE001 — el rastreo nunca tumba la tarea
            return {"status": "exception", "events": [{"at": utils._now_iso(), "text": f"Sin respuesta de Envia: {exc}"}]}
        datos = respuesta.get("data") or []
        primero = datos[0] if isinstance(datos, list) and datos else (datos if isinstance(datos, dict) else {})
        crudo = str(primero.get("status") or primero.get("statusDescription") or "").strip().lower()
        eventos = []
        for ev in primero.get("events") or primero.get("history") or []:
            if isinstance(ev, dict):
                eventos.append({"at": str(ev.get("date") or ev.get("at") or ""), "text": str(ev.get("description") or ev.get("text") or "")})
        if "deliver" in crudo or "entreg" in crudo:
            return {
                "status": "delivered",
                "deliveredAt": str(primero.get("deliveredAt") or primero.get("deliveryDate") or utils._now_iso()),
                "signedBy": str(primero.get("signedBy") or primero.get("receivedBy") or "").strip(),
                "events": eventos,
            }
        if "exception" in crudo or "incidenc" in crudo or "devuel" in crudo:
            return {"status": "exception", "events": eventos or [{"at": utils._now_iso(), "text": crudo or "Incidencia"}]}
        return {"status": "in_transit", "events": eventos}


def paqueteria_activa(cfg=None) -> Paqueteria:
    """La paquetería que dicta `shipping.carrierIntegration.provider`."""
    integracion = _config_paqueteria(cfg)
    if str(integracion.get("provider") or "envia").strip().lower() == "simulada":
        return PaqueteriaSimulada(int(integracion.get("simDeliveryDays") or 3))
    return EnviaPaqueteria()
