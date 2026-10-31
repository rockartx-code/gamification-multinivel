#!/usr/bin/env python3
"""Recorrido end-to-end contra el mundo simulado. 50 comprobaciones.

Ejercita el codigo real de las 8 Lambdas por HTTP, sin tocar AWS. Es el escalon
que faltaba entre la suite de unidad (631 pruebas, handlers en memoria) y las
rondas con agentes-persona (navegador, caras, horas): aqui se recorre el negocio
entero por la API en unos segundos, y se puede correr en cada despliegue.

Uso:
    python3 sim/servidor.py &        # el mundo
    python3 sim/semilla.py           # el negocio
    python3 sim/recorrido.py         # este recorrido

Es idempotente: se puede volver a correr sobre el mismo mundo.

**Sin pasarela de pago.** El cobro se registra por transferencia (`PATCH
/orders/{id}` con `paymentReference`), que es la via de caja. El checkout de
Mercado Pago —incluso el simulado del arnes en `/__sim/pago/`— queda fuera a
proposito.

Cada persona usa el rol que le toca: Renata gerencia, Tono almacen, Mireya caja,
Alma finanzas. Que a Alma le nieguen el inventario es parte de lo que se mide;
`order_mark_paid` lo tienen gerencia y almacen, ni caja ni finanzas.

Lo que destapo la primera vez que corrio:
  - `POST /dashboard/notifications/{id}` respondia 201 y CREABA una notificacion
    ignorando el id (paso 50). Corregido en dashboard_lambda.
  - El simulador mandaba `/user-dashboard` a customer_lambda cuando el API
    Gateway real lo manda a Multinivel-Dashboard: el tablero de la clienta
    parecia roto y no lo estaba (paso 36).
"""
import json
import re
import sys
import urllib.error
import urllib.request

API = "http://localhost:4400"
import os

_SIM = os.path.dirname(os.path.abspath(__file__))
CRED = json.load(open(os.path.join(_SIM, "credenciales.json"), encoding="utf-8"))

paso_n = 0
fallos = []
notas = []


class _SinRedirigir(urllib.request.HTTPRedirectHandler):
    """La pasarela simulada responde 302 al frontend (:4321), que no corre en
    esta validacion. Seguir la redireccion daria ConnectionRefused y parece un
    fallo del pago cuando el pago si ocurrio."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ABRIDOR = urllib.request.build_opener(_SinRedirigir)


def llamar(metodo, ruta, cuerpo=None, token=None, headers=None):
    req = urllib.request.Request(
        API + ruta, method=metodo,
        data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with _ABRIDOR.open(req, timeout=180) as r:
            c = r.read().decode("utf-8")
            try:
                return r.status, json.loads(c)
            except Exception:
                return r.status, c
    except urllib.error.HTTPError as e:
        c = e.read().decode("utf-8")
        try:
            return e.code, json.loads(c)
        except Exception:
            return e.code, c


def paso(titulo, ok, detalle=""):
    global paso_n
    paso_n += 1
    print(f"  {'ok   ' if ok else 'FALLA'} {paso_n:>2}. {titulo}" + (f"  [{detalle}]" if detalle else ""))
    if not ok:
        fallos.append(f"{paso_n}. {titulo} [{detalle}]")


def nota(t):
    notas.append(t)
    print(f"  nota     {t}")


def sesion(correo):
    e = next(x for x in CRED["empleados"] if x["correo"] == correo)
    st, r = llamar("POST", "/auth/login", {"email": e["correo"], "password": e["password"]})
    return (r or {}).get("token") if isinstance(r, dict) else None, e


print("\n=== 1. Identidad, sesion y encabezados forjados ===")
tok_alma, alma = sesion("alma@findingu.mx")
paso("login de Alma (finanzas)", bool(tok_alma))
tok_renata, _ = sesion("renata@findingu.mx")
paso("login de Renata (gerencia)", bool(tok_renata))
tok_tono, tono = sesion("tono@findingu.mx")
paso("login de Tono (almacen)", bool(tok_tono))
tok_mireya, mireya = sesion("mireya@findingu.mx")
paso("login de Mireya (caja)", bool(tok_mireya))

st, r = llamar("POST", "/auth/login", {"email": alma["correo"], "password": "no-es-la-buena"})
paso("contrasena incorrecta se rechaza", st in (400, 401, 403), f"HTTP {st}")

st, r = llamar("GET", "/customers/getall", token=tok_alma)
paso("sesion valida abre el back office", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/customers/getall")
paso("sin token el back office se cierra", st in (401, 403), f"HTTP {st}")

st, r = llamar("GET", "/customers/getall", headers={"x-user-role": "admin", "x-user-id": "1"})
paso("x-user-role forjado NO abre el back office", st in (401, 403), f"HTTP {st}")

st, r = llamar("GET", "/commissions/pagos/dispersion.csv?month=2027-03",
               headers={"x-user-role": "admin", "x-user-id": "1"})
paso("la CLABE no se filtra con encabezado forjado", st in (401, 403), f"HTTP {st}")

st, r = llamar("POST", "/inventory/turno/resumen/enviar",
               {"para": "atacante@example.com"},
               headers={"x-user-role": "admin", "x-user-id": "1"})
paso("no se manda correo del turno con encabezado forjado", st in (401, 403, 404), f"HTTP {st}")


print("\n=== 2. Privilegios por puesto (cada quien lo suyo) ===")
st, r = llamar("GET", "/catalog/product", token=tok_alma)
paso("Alma (finanzas) NO ve el catalogo de administracion", st == 403, f"HTTP {st}")

st, r = llamar("GET", "/inventory/stocks/movements", token=tok_alma)
paso("Alma NO ve movimientos de almacen", st == 403, f"HTTP {st}")

st, r = llamar("GET", "/inventory/stocks/movements", token=tok_tono)
paso("Tono (almacen) SI ve movimientos de almacen", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/commissions/pagos/dispersion.csv?month=2027-03", token=tok_alma)
paso("Alma (finanzas) SI baja la dispersion bancaria", st in (200, 404), f"HTTP {st}")


print("\n=== 3. Tienda publica ===")
st, prods = llamar("GET", "/catalog/catalog")
lista = prods if isinstance(prods, list) else (prods or {}).get("products") or []
paso("la tienda publica lista productos", st == 200 and len(lista) > 0,
     f"HTTP {st}, {len(lista)} productos")
producto = lista[0] if lista else None
pid = (producto or {}).get("productId") or (producto or {}).get("id")

st, r = llamar("GET", "/catalog/config/public")
paso("configuracion publica sin sesion", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/catalog/categories")
paso("categorias", st == 200, f"HTTP {st}")


print("\n=== 4. Alta de clienta con codigo de patrocinadora ===")
correo = "friendsfamily.recorrido@example.com"
st, r = llamar("POST", "/auth/crearcuenta", {
    "email": correo, "password": "Secreta123!", "name": "Clienta Recorrido",
    "referralCode": "PAULINA-PR"})
paso("alta con codigo PAULINA-PR", st in (200, 201, 409), f"HTTP {st}")

st, buzon = llamar("GET", f"/__sim/buzon/{correo}")
n = len(buzon) if isinstance(buzon, list) else 0
paso("llega el correo de activacion", st == 200 and n > 0, f"{n} correo(s)")

tokv = None
if isinstance(buzon, list):
    m = re.search(r"token=([A-Za-z0-9._\-]+)", json.dumps(buzon, ensure_ascii=False))
    tokv = m.group(1) if m else None
st, r = llamar("POST", "/auth/verify-email", {"token": tokv}) if tokv else (0, None)
paso("se confirma el correo con el enlace del mensaje", st in (200, 201, 409), f"HTTP {st}")

st, r = llamar("POST", "/auth/login", {"email": correo, "password": "Secreta123!"})
tok_cli = (r or {}).get("token") if isinstance(r, dict) else None
uid_cli = ((r or {}).get("user") or {}).get("userId") if isinstance(r, dict) else None
paso("la clienta entra", st == 200 and bool(tok_cli), f"HTTP {st}")

hcli = {"x-user-id": str(uid_cli)} if uid_cli else {}


print("\n=== 5. Pedido y pago (pasarela SIMULADA, nunca Mercado Pago) ===")
oid = None
if pid and tok_cli:
    st, r = llamar("POST", "/orders", {
        "customerId": uid_cli,
        "customerEmail": correo, "customerName": "Clienta Recorrido",
        "items": [{"productId": pid, "quantity": 2}],
        "shippingAddress": {"street": "Calle 1", "number": "10", "city": "Ciudad de Mexico",
                            "state": "CDMX", "postalCode": "01000", "phone": "5550000000"},
        "deliveryMethod": "delivery"}, token=tok_cli, headers=hcli)
    if isinstance(r, dict):
        oid = r.get("orderId") or (r.get("order") or {}).get("orderId")
    paso("se crea el pedido", st in (200, 201) and bool(oid), f"HTTP {st} id={oid}")
else:
    paso("se crea el pedido", False, "falto producto o sesion")

if oid:
    st, r = llamar("GET", f"/orders/{oid}", token=tok_cli, headers=hcli)
    paso("la clienta ve su pedido", st == 200, f"HTTP {st}")

    # SIN pasarela de pago: se registra el cobro por transferencia, que es la
    # via que usa caja. El checkout de Mercado Pago (incluso el simulado del
    # arnes) queda deliberadamente fuera de esta validacion.
    # `order_mark_paid` lo tienen gerencia y almacen; ni caja ni finanzas.
    st, r = llamar("PATCH", f"/orders/{oid}",
                   {"status": "paid", "paymentReference": "SPEI 4482910"},
                   token=tok_renata)
    paso("gerencia registra el cobro por transferencia (sin pasarela)",
         st in (200, 201, 204), f"HTTP {st}")

    st, r = llamar("PATCH", f"/orders/{oid}",
                   {"status": "paid", "paymentReference": "OTRO"}, token=tok_mireya)
    paso("caja NO puede registrar el cobro (privilegio order_mark_paid)",
         st == 403, f"HTTP {st}")

    st, r = llamar("GET", f"/orders/{oid}", token=tok_alma)
    o = r if isinstance(r, dict) else {}
    est = o.get("status") or (o.get("order") or {}).get("status")
    paso("el pedido queda pagado", est in ("paid", "processing", "confirmed"), f"status={est}")

    st, r = llamar("PATCH", f"/orders/{oid}", {"status": "delivered"}, token=tok_tono)
    paso("almacen lo marca entregado", st in (200, 201, 204), f"HTTP {st}")

    st, r = llamar("GET", f"/orders/{oid}", token=tok_alma)
    o = r if isinstance(r, dict) else {}
    est = o.get("status") or (o.get("order") or {}).get("status")
    paso("el pedido queda entregado", est == "delivered", f"status={est}")

    st, r = llamar("GET", "/orders/find", token=tok_cli, headers=hcli)
    paso("aparece en el historial de la clienta", st == 200, f"HTTP {st}")


print("\n=== 6. Comisiones (lo que el pedido dispara) ===")
st, r = llamar("GET", "/commissions/config/app", token=tok_alma)
paso("configuracion del negocio", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/commissions/summary", token=tok_alma)
paso("resumen de comisiones", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/commissions/monthly-stats", token=tok_alma)
paso("estadisticas mensuales", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/commissions/pagos/mes?month=2027-03", token=tok_alma)
paso("mes contable (dia de pago)", st in (200, 404), f"HTTP {st}")

st, disp = llamar("GET", "/commissions/pagos/dispersion.csv?month=2027-03", token=tok_alma)
paso("dispersion bancaria", st in (200, 404), f"HTTP {st}")
if st == 200 and isinstance(disp, str):
    nota(f"layout bancario: {len(disp.splitlines())} linea(s)")

# La comision de Paulina por la compra de su referida.
st, r = llamar("GET", "/customers/getall?q=paulina", token=tok_alma)
socias = r if isinstance(r, list) else (r or {}).get("customers") or []
pau = next((c for c in socias if "paulina" in json.dumps(c, ensure_ascii=False).lower()), None)
if pau:
    pauid = pau.get("customerId") or pau.get("id")
    st, r = llamar("GET", f"/commissions/associates/{pauid}/commissions", token=tok_alma)
    paso("comisiones de la patrocinadora", st == 200, f"HTTP {st}")
    if st == 200:
        filas = r.get("commissions", r) if isinstance(r, dict) else r
        nota(f"la patrocinadora tiene {len(filas) if isinstance(filas, list) else '?'} fila(s) de comision")
else:
    nota("no localice a la patrocinadora en el listado (busqueda por texto)")


print("\n=== 7. Tableros ===")
st, r = llamar("GET", "/user-dashboard", token=tok_cli, headers=hcli)
paso("tablero de la clienta", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/dashboard/honor-board", token=tok_alma)
paso("cuadro de honor (recorre toda la red)", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/dashboard/admin/warnings", token=tok_alma)
paso("avisos de administracion (lo que carga la pantalla admin)", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/dashboard/notifications", token=tok_alma)
paso("notificaciones", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/customers/dashboard", token=tok_cli, headers=hcli)
paso("tablero de clientes (con la clienta, no con una empleada)", st == 200, f"HTTP {st}")


print("\n=== 8. Inventario, caja y envios ===")
st, r = llamar("GET", "/inventory/stocks", token=tok_tono)
paso("sucursales y existencias", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/inventory/pickup-stocks", token=tok_cli, headers=hcli)
paso("sucursales para recoger", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/inventory/pos/cash-control", token=tok_mireya,
               headers={"x-user-id": str(mireya["id"])})
paso("control de caja (Mireya)", st in (200, 404), f"HTTP {st}")

st, r = llamar("POST", "/shipping/quote",
               {"postalCode": "44100", "items": [{"productId": pid, "quantity": 1}]},
               token=tok_cli, headers=hcli)
paso("cotizacion de envio (Envia simulada)", st == 200, f"HTTP {st}")

st, r = llamar("POST", "/orders/checkout/sucursales-recoger", {}, token=tok_cli, headers=hcli)
paso("sucursales de recoger en checkout", st == 200, f"HTTP {st}")

st, r = llamar("GET", "/orders/checkout/envio-info?postalCode=44100",
               token=tok_cli, headers=hcli)
paso("informacion de envio en checkout", st in (200, 400), f"HTTP {st}")


print("\n=== 9. Ruteo: lo que NO debe pasar ===")
st, r = llamar("GET", "/orders/ORD-QUE-NO-EXISTE", token=tok_alma)
paso("pedido inexistente da 404, no 502", st == 404, f"HTTP {st}")

st, r = llamar("DELETE", "/catalog", token=tok_alma)
paso("metodo no permitido da 405, no 502", st in (403, 405), f"HTTP {st}")

st, r = llamar("GET", "/catalog/loquesea/inventado", token=tok_alma)
paso("sub-path inventado da 404, no 502", st == 404, f"HTTP {st}")

st, antes = llamar("GET", "/dashboard/notifications", token=tok_alma)
n_antes = len((antes or {}).get("notifications", [])) if isinstance(antes, dict) else len(antes or [])
st, r = llamar("POST", "/dashboard/notifications/999", {"title": "inyectada"}, token=tok_alma)
st2, desp = llamar("GET", "/dashboard/notifications", token=tok_alma)
n_desp = len((desp or {}).get("notifications", [])) if isinstance(desp, dict) else len(desp or [])
paso("POST a URL no declarada no crea nada", st == 404 and n_desp == n_antes,
     f"HTTP {st}, notificaciones {n_antes}->{n_desp}")


print("\n" + "=" * 72)
print(f"pasos: {paso_n}   fallos: {len(fallos)}   notas: {len(notas)}")
if fallos:
    print("\nFALLOS:")
    for f in fallos:
        print("  -", f)
print("=" * 72)
sys.exit(1 if fallos else 0)
