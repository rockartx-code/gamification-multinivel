#!/usr/bin/env python3
"""Backend REAL de Finding'U corriendo en local para la simulación.

Ejecuta las 8 Lambdas tal cual, sin AWS:
  - DynamoDB → la tabla en memoria de la suite de pruebas (tests/conftest.py),
    persistida a disco para sobrevivir reinicios.
  - SES      → buzón en disco: sim/buzon/<correo>.json (los agentes "leen su correo").
  - Reloj    → freezegun con avance real; POST /__sim/reloj salta de fecha.
  - Step Functions → cola drenada tras cada petición (comisiones síncronas).
  - MercadoPago → pasarela simulada en /__sim/pago/<pedido>.
  - Envia.com → cotizaciones fijas.
  - S3 → carpeta sim/s3. Athena → sin datos (Estadísticas queda vacía: limitación conocida).
"""
import json, os, sys, threading, pickle, atexit, base64, time, re
from decimal import Decimal
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(RAIZ, "Micro-lambda-GMF", "python")
SIM = os.path.dirname(os.path.abspath(__file__))
BUZON = os.path.join(SIM, "buzon"); S3DIR = os.path.join(SIM, "s3")
ESTADO = os.path.join(SIM, "estado.pkl")
PUERTO = int(os.environ.get("SIM_PUERTO", "4400"))
FRONT = os.environ.get("SIM_FRONT", "http://localhost:4321")
FECHA_INICIAL = os.environ.get("SIM_FECHA", "2026-09-02T09:00:00")

os.environ.setdefault("TABLE_NAME", "multinivel-sim")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "sim"); os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "sim")
os.environ.setdefault("SUPERADMIN_TOKEN", "sim-superadmin-token")
os.environ.setdefault("FRONTEND_BASE_URL", FRONT)
os.environ.setdefault("SES_FROM_EMAIL", "info@findingu.com.mx")
os.environ.setdefault("ORDER_FULFILLMENT_SFN_ARN", "arn:sim:orders")
os.environ.setdefault("MERCADOPAGO_ACCESS_TOKEN", "sim-mp-token")
os.environ.setdefault("ENVIA_API_KEY", "sim-envia")
os.environ.setdefault("PASSWORD_HASH_ITERATIONS", "20000")  # más rápido en local

sys.path.insert(0, PY); sys.path.insert(0, os.path.join(PY, "tests"))
from conftest import FakeTable, FakeResource, FakeClient  # noqa: E402

# ── estado persistente ────────────────────────────────────────────────
store: dict = {}
PAGOS: dict = {}     # orderId → {"success":..,"failure":..}
reloj_actual = FECHA_INICIAL
if os.path.exists(ESTADO):
    with open(ESTADO, "rb") as fh:
        d = pickle.load(fh)
    store.update(d.get("store", {})); PAGOS.update(d.get("pagos", {}))
    reloj_actual = d.get("reloj", FECHA_INICIAL)
    print(f"[sim] estado cargado: {len(store)} items, reloj={reloj_actual}")

def guardar():
    tmp = ESTADO + ".tmp"
    with open(tmp, "wb") as fh:
        pickle.dump({"store": store, "pagos": PAGOS, "reloj": ahora_iso()}, fh)
    os.replace(tmp, ESTADO)
atexit.register(guardar)

# ── reloj simulado ────────────────────────────────────────────────────
from freezegun import freeze_time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
_freezer = None
def fijar_reloj(iso):
    global _freezer, reloj_actual
    if _freezer: _freezer.stop()
    _freezer = freeze_time(iso, tick=True); _freezer.start()
    reloj_actual = iso
def ahora_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
fijar_reloj(reloj_actual)

# ── dobles de AWS ─────────────────────────────────────────────────────
COLA_SFN = []
class FakeSfn:
    def start_execution(self, stateMachineArn=None, input="{}", **kw):
        COLA_SFN.append(json.loads(input)); return {"executionArn": "sim"}
class FakeS3:
    def put_object(self, Bucket=None, Key=None, Body=b"", **kw):
        ruta = os.path.join(S3DIR, Key.replace("/", "__"))
        with open(ruta, "wb") as fh: fh.write(Body if isinstance(Body, bytes) else str(Body).encode())
        return {}
    def generate_presigned_url(self, *a, **k): return "http://localhost:%d/__sim/s3/no-disponible" % PUERTO
class FakeAthena:
    def start_query_execution(self, **kw): raise RuntimeError("Athena no disponible en local")
class FakeSes:
    def send_email(self, **kw): raise RuntimeError("SES no disponible en local")
class Dummy:
    def __getattr__(self, n): return lambda *a, **k: {}
import boto3  # noqa: E402
boto3.resource = lambda *a, **k: FakeResource(store)
boto3.client = lambda name, *a, **k: {"stepfunctions": FakeSfn(), "s3": FakeS3(), "athena": FakeAthena(), "ses": FakeSes()}.get(name, Dummy())

import core_utils  # noqa: E402
from core import db as core_db  # noqa: E402
for m in (core_db, core_utils):
    m._table = FakeTable(store); m._dynamodb = FakeResource(store)
core_db._ddb_client = FakeClient(store)
core_utils._invalidate_app_config_cache()

import auth_utils, catalog_lambda, customer_lambda, commissions_lambda  # noqa: E402
import order_lambda, inventory_lambda, dashboard_lambda, shipping_lambda  # noqa: E402
LAMBDAS = {"auth": auth_utils, "catalog": catalog_lambda, "customers": customer_lambda,
           "commissions": commissions_lambda, "orders": order_lambda, "inventory": inventory_lambda,
           "dashboard": dashboard_lambda, "shipping": shipping_lambda,
           "verify-email": auth_utils, "user-dashboard": customer_lambda}

# ── correo → buzón ────────────────────────────────────────────────────
def enviar_correo(to_email, subject, text, html):
    to_email = str(to_email or "").strip().lower()
    ruta = os.path.join(BUZON, re.sub(r"[^a-z0-9@._-]", "_", to_email) + ".json")
    lista = json.load(open(ruta)) if os.path.exists(ruta) else []
    enlaces = re.findall(r"https?://[^\s\"'<>]+", text or "") + re.findall(r"href=\"([^\"]+)\"", html or "")
    lista.append({"n": len(lista) + 1, "fecha": ahora_iso(), "para": to_email, "asunto": subject,
                  "texto": text, "enlaces": sorted(set(enlaces)), "leido": False})
    json.dump(lista, open(ruta, "w"), ensure_ascii=False, indent=1)
    print(f"[correo] → {to_email}: {subject}")
for nombre, mod in list(sys.modules.items()):
    if hasattr(mod, "_send_ses_email"):
        try: setattr(mod, "_send_ses_email", enviar_correo)
        except Exception: pass

# ── MercadoPago y Envia simulados ─────────────────────────────────────
class _Resp:
    def __init__(self, payload): self._b = json.dumps(payload).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False
def urlopen_mp(req, timeout=None, **kw):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if "checkout/preferences" in url:
        pref = json.loads(req.data.decode()); oid = str(pref.get("external_reference"))
        PAGOS[oid] = dict(pref.get("back_urls") or {}); PAGOS[oid]["total"] = sum(float(i["unit_price"]) * int(i["quantity"]) for i in pref.get("items", []))
        u = f"http://localhost:{PUERTO}/__sim/pago/{oid}"
        return _Resp({"id": f"pref-{oid}", "init_point": u, "sandbox_init_point": u})
    m = re.search(r"/v1/payments/sim-(.+)$", url)
    if m: return _Resp({"id": f"sim-{m.group(1)}", "status": "approved", "external_reference": m.group(1)})
    raise RuntimeError("URL externa no simulada: " + url)
def urlopen_envia(req, timeout=None, **kw):
    return _Resp({"data": [
        {"carrierDescription": "Estafeta", "serviceDescription": "Terrestre", "totalPrice": 129.0, "deliveryEstimate": "3 a 5 días hábiles"},
        {"carrierDescription": "DHL", "serviceDescription": "Express", "totalPrice": 219.0, "deliveryEstimate": "1 a 2 días hábiles"}]})
# OJO: `order_lambda.urllib.request` y `shipping_lambda.urllib.request` son el
# MISMO módulo global. Parchear urlopen dos veces dejaba solo el último
# (Envia), y todo checkout de MercadoPago recibía una cotización de envíos.
import urllib.request as _ur
def urlopen_sim(req, timeout=None, **kw):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if "mercadopago" in url: return urlopen_mp(req, timeout, **kw)
    if "envia" in url: return urlopen_envia(req, timeout, **kw)
    raise RuntimeError("URL externa no simulada: " + url)
_ur.urlopen = urlopen_sim

# ── Step Functions: drenar la cola ────────────────────────────────────
def drenar_sfn():
    while COLA_SFN:
        ev = COLA_SFN.pop(0)
        try:
            r = commissions_lambda.lambda_handler({"orderId": ev.get("orderId"), "action": ev.get("action")}, None)
            print(f"[sfn] {ev.get('action')} {ev.get('orderId')} → {r}")
            dashboard_lambda.lambda_handler({"task": "sync_iceberg", "orderId": ev.get("orderId")}, None)
        except Exception as e:
            print(f"[sfn] ERROR {ev}: {e!r}")

# ── HTTP ──────────────────────────────────────────────────────────────
LOCK = threading.Lock()
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-User-Id,X-User-Name,X-User-Role,X-User-Privileges"}

PAGINA_PAGO = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Mercado Pago · Checkout</title>
<style>body{font-family:system-ui;background:#f5f5f5;margin:0}main{max-width:420px;margin:48px auto;background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 12px #0002}
h1{font-size:18px;color:#009ee3;margin:0 0 4px}small{color:#666}.tot{font-size:32px;font-weight:700;margin:18px 0}button{width:100%;padding:14px;border:0;border-radius:8px;font-size:16px;cursor:pointer;margin-top:8px}
.ok{background:#009ee3;color:#fff}.no{background:#eee}</style></head><body><main>
<h1>Mercado Pago</h1><small>Pago simulado · Finding'U · Pedido {oid}</small>
<div class="tot">${total}</div>
<p>Estás fuera de la tienda. Este es el checkout de la pasarela.</p>
<form method="post" action="/__sim/pago/{oid}/confirmar"><button class="ok">Pagar ${total}</button></form>
<form method="post" action="/__sim/pago/{oid}/cancelar"><button class="no">Cancelar y volver</button></form>
</main></body></html>"""

class Manejador(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write(f"[http] {self.command} {self.path} {args[1] if len(args)>1 else ''}\n")

    def _responder(self, code, cuerpo=b"", headers=None, ctype="application/json"):
        self.send_response(code)
        for k, v in {**CORS, "Content-Type": ctype, **(headers or {})}.items(): self.send_header(k, v)
        if isinstance(cuerpo, str): cuerpo = cuerpo.encode()
        self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)

    def do_OPTIONS(self): self._responder(200, b'{"ok":true}')
    def do_GET(self): self._despachar()
    def do_POST(self): self._despachar()
    def do_PUT(self): self._despachar()
    def do_PATCH(self): self._despachar()
    def do_DELETE(self): self._despachar()

    def _leer_cuerpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n).decode() if n else ""

    def _despachar(self):
        u = urlparse(self.path); ruta = unquote(u.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        cuerpo = self._leer_cuerpo()
        with LOCK:
            if ruta.startswith("/__sim/"): return self._sim(ruta, q, cuerpo)
            seg = [s for s in ruta.strip("/").split("/") if s]
            mod = LAMBDAS.get(seg[0]) if seg else None
            if not mod: return self._responder(404, json.dumps({"message": f"Ruta no simulada: {ruta}"}))
            headers = {}
            for k, v in self.headers.items(): headers[k] = v; headers[k.lower()] = v
            event = {"httpMethod": self.command, "path": ruta, "headers": headers,
                     "queryStringParameters": q or None, "body": cuerpo or None, "isBase64Encoded": False}
            try:
                r = mod.lambda_handler(event, None)
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._responder(500, json.dumps({"message": f"Error interno simulado: {e!r}"}))
            drenar_sfn()
            # Guardar tras cada escritura: un reinicio del contenedor perdía todo lo hecho
            # desde el último cambio de reloj (entregas, transferencias, turnos enteros).
            if self.command in ("POST", "PUT", "PATCH", "DELETE"):
                try: guardar()
                except Exception as e: print(f"[sim] guardar tras {self.command} falló: {e!r}")
            body = r.get("body", "")
            if r.get("isBase64Encoded"): body = base64.b64decode(body)
            hdr = {k: v for k, v in (r.get("headers") or {}).items()}
            self._responder(int(r.get("statusCode", 200)), body, hdr, hdr.get("Content-Type", "application/json"))

    def _sim(self, ruta, q, cuerpo):
        if ruta == "/__sim/reloj":
            if self.command == "POST":
                fijar_reloj(json.loads(cuerpo)["fecha"]); guardar()
            return self._responder(200, json.dumps({"ahora": ahora_iso()}))
        if ruta.startswith("/__sim/buzon/"):
            correo = ruta.split("/__sim/buzon/", 1)[1].lower()
            f = os.path.join(BUZON, re.sub(r"[^a-z0-9@._-]", "_", correo) + ".json")
            return self._responder(200, json.dumps(json.load(open(f)) if os.path.exists(f) else [], ensure_ascii=False))
        if ruta == "/__sim/estado":
            tipos = {}
            for (pk, sk) in store: tipos[pk.split("#")[0]] = tipos.get(pk.split("#")[0], 0) + 1
            return self._responder(200, json.dumps({"items": len(store), "porTipo": tipos, "reloj": ahora_iso(), "pagosPendientes": list(PAGOS)}))
        if ruta == "/__sim/sfn" and self.command == "POST":
            # Reprocesar una acción del motor de comisiones (lo que en AWS haría
            # re-ejecutar la máquina de estados). Uso: soporte reacredita un pedido.
            ev = json.loads(cuerpo); COLA_SFN.append({"orderId": ev["orderId"], "action": ev["action"]}); drenar_sfn(); guardar()
            return self._responder(200, b'{"ok":true}')
        if ruta == "/__sim/guardar":
            guardar(); return self._responder(200, b'{"ok":true}')
        if ruta == "/__sim/patch" and self.command == "POST":
            # Corrección de datos por "sistemas" (lo que en AWS sería editar el item en la consola).
            ev = json.loads(cuerpo)
            item = core_db._update_by_id(ev["entity"], ev["id"], ev["expression"],
                                         {k: (Decimal(str(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in ev["values"].items()},
                                         ev.get("names"))
            guardar(); return self._responder(200, json.dumps(item, default=str))
        if ruta == "/__sim/reevaluar" and self.command == "POST":
            ev = json.loads(cuerpo)
            commissions_lambda._reset_request_cache()
            r = commissions_lambda._reevaluate_blocked_rows([str(b) for b in ev["beneficiaryIds"]], ev["month"])
            guardar(); return self._responder(200, json.dumps({"reprocesadas": r}))
        m = re.match(r"^/__sim/pago/([^/]+)$", ruta)
        if m and self.command == "GET":
            oid = m.group(1); tot = PAGOS.get(oid, {}).get("total", 0)
            return self._responder(200, PAGINA_PAGO.replace("{oid}", oid).replace("{total}", f"{tot:,.2f}"), ctype="text/html; charset=utf-8")
        m = re.match(r"^/__sim/pago/([^/]+)/(confirmar|cancelar)$", ruta)
        if m:
            oid, acc = m.group(1), m.group(2); back = PAGOS.get(oid, {})
            if acc == "confirmar":
                ev = {"httpMethod": "POST", "path": "/orders/webhooks/mercadolibre", "headers": {},
                      "queryStringParameters": {"topic": "payment", "id": f"sim-{oid}"}, "body": "{}"}
                r = order_lambda.lambda_handler(ev, None); drenar_sfn(); print(f"[pago] {oid} → {r.get('statusCode')} {r.get('body','')[:120]}")
                destino = back.get("success") or f"{FRONT}/#/orden/{oid}"
            else:
                destino = back.get("failure") or f"{FRONT}/#/orden/{oid}"
            return self._responder(303, b"", {"Location": destino}, "text/plain")
        return self._responder(404, b'{"message":"sim: ruta desconocida"}')

def _autoguardado():
    while True:
        time.sleep(20)
        with LOCK:
            try: guardar()
            except Exception as e: print("[sim] autoguardado falló:", e)

if __name__ == "__main__":
    threading.Thread(target=_autoguardado, daemon=True).start()
    print(f"[sim] backend real en http://localhost:{PUERTO}  reloj={ahora_iso()}  front={FRONT}")
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()
