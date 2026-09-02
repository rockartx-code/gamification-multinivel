#!/usr/bin/env python3
"""Puebla el backend local con lo mínimo para que exista un negocio:
empleados con permisos por rol, catálogo oficial, un almacén con existencias
y una socia con red (la patrocinadora que invitará a un prospecto)."""
import json, os, re, sys, urllib.request, time
API = os.environ.get("SIM_API", "http://localhost:4400")
SUPER = os.environ.get("SUPERADMIN_TOKEN", "sim-superadmin-token")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def llamar(metodo, ruta, cuerpo=None, token=None):
    req = urllib.request.Request(API + ruta, method=metodo, data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")

def buzon(correo):
    return llamar("GET", f"/__sim/buzon/{correo}")[1]

TODOS = ["access_screen_orders","access_screen_customers","access_screen_products","access_screen_stocks","access_screen_pos","access_screen_stats","access_screen_settings","order_mark_paid","order_mark_shipped","order_mark_delivered","order_create","customer_add","commissions_register_payment","product_add","product_update","product_delete","product_set_month","stock_create","stock_create_transfer","stock_add_inventory","stock_mark_damaged","stock_receive_transfer","pos_register_sale","user_mark_admin","user_manage_privileges","employee_add","employee_manage_privileges","access_screen_employees","config_manage","access_screen_honor_board"]
EMPLEADOS = [
    {"name": "Sofía Herrera", "email": "sofia@findingu.mx", "phone": "5551000001", "rol": "gerente", "privileges": TODOS},
    {"name": "Beto Salinas",  "email": "beto@findingu.mx",  "phone": "5551000002", "rol": "almacen_y_pedidos",
     "privileges": ["access_screen_orders","order_mark_paid","order_mark_shipped","order_mark_delivered","access_screen_stocks","stock_add_inventory","stock_create_transfer","stock_receive_transfer","stock_mark_damaged"]},
    {"name": "Paco Luna",     "email": "paco@findingu.mx",  "phone": "5551000003", "rol": "cajero_pos",
     "privileges": ["access_screen_pos","pos_register_sale","access_screen_orders","order_mark_delivered","access_screen_stocks"]},
]

def main():
    cred = {"api": API, "empleados": [], "productos": [], "almacen": None, "patrocinadora": None}
    # 1. empleados
    for e in EMPLEADOS:
        st, r = llamar("POST", "/auth/employees", {"name": e["name"], "email": e["email"], "phone": e["phone"], "privileges": {p: True for p in e["privileges"]}}, SUPER)
        assert st == 201, (st, r)
        cred["empleados"].append({"nombre": e["name"], "correo": e["email"], "password": r["tempPassword"], "rol": e["rol"], "id": r["employee"].get("employeeId")})
        print("empleado", e["name"], "→", r["tempPassword"])
    # 2. catálogo oficial
    seed = json.load(open(os.path.join(RAIZ, "Micro-lambda-GMF", "python", "seed", "product_pc_seed.json")))
    DESC = {"finding pro": "Proteína de suero con colágeno. 500 g, 25 porciones.", "klinhart": "Omega-3 de alta pureza, 60 cápsulas.", "longevit": "Antioxidantes con resveratrol y CoQ10.", "boom": "Complejo B con energía sostenida, 30 días.", "naplus": "Electrolitos con sodio y potasio para hidratación."}
    for i, p in enumerate(seed["products"], start=1):
        clave = next((k for k in DESC if k in p["name"].lower() or any(k in a for a in p.get("aliases", []))), None)
        svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'><rect width='400' height='400' fill='#1f3d31'/><text x='200' y='210' font-family='sans-serif' font-size='30' fill='#c8a24a' text-anchor='middle'>{p['name']}</text></svg>"
        import base64; img = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        cuerpo = {"name": p["name"], "price": p["price"], "vpPoints": p["vpPoints"], "sku": f"FU-{i:03d}",
                  "description": DESC.get(clave, "Suplemento Finding'U de uso diario."), "hook": DESC.get(clave, "").split(".")[0],
                  "active": True, "images": [{"section": "miniatura", "url": img}, {"section": "landing", "url": img}], "tags": p.get("aliases", [])}
        st, r = llamar("POST", "/catalog/product", cuerpo, SUPER)
        assert st in (200, 201), (st, r)
        pid = (r.get("product") or r).get("productId") or (r.get("product") or r).get("id")
        cred["productos"].append({"id": pid, "nombre": p["name"], "precio": p["price"], "pc": p["vpPoints"]})
    print("productos:", len(cred["productos"]))
    # producto del mes
    llamar("POST", "/catalog/product/product-of-month", {"productId": cred["productos"][0]["id"]}, SUPER)
    # 3. almacén con existencias
    ids_emp = [e["id"] for e in cred["empleados"] if e["id"] is not None]
    st, r = llamar("POST", "/inventory/stocks", {"name": "Bodega Central", "location": "Av. Insurgentes Sur 1234, Col. Del Valle, CDMX", "postalCode": "03100", "isMainWarehouse": True, "allowPickup": True, "linkedUserIds": ids_emp}, SUPER)
    assert st == 201, (st, r)
    sid = r["stock"]["stockId"]; cred["almacen"] = {"id": sid, "nombre": "Bodega Central"}
    for p in cred["productos"]:
        st, r = llamar("POST", f"/inventory/stocks/{sid}/entries", {"productId": p["id"], "qty": 40, "userId": ids_emp[0]}, SUPER)
        assert st == 200, (st, r)
    print("almacén", sid, "con 40 uds de cada producto")
    # 4. patrocinadora con cuenta verificada
    correo = "marcela.ortiz@gmail.com"
    st, r = llamar("POST", "/auth/crearcuenta", {"name": "Marcela Ortiz", "email": correo, "phone": "5552000001", "password": "Marcela2026!", "confirmPassword": "Marcela2026!"})
    assert st in (200, 201), (st, r)
    time.sleep(0.3)
    tokens = [t for m in buzon(correo) for l in m["enlaces"] for t in re.findall(r"token=([A-Za-z0-9._-]+)", l)]
    assert tokens, "no llegó el correo de verificación"
    st, r = llamar("POST", "/auth/verify-email", {"token": tokens[-1]}); assert st == 200, (st, r)
    st, r = llamar("POST", "/auth/login", {"email": correo, "password": "Marcela2026!"}); assert st == 200, (st, r)
    tok = r["token"]; uid = r["user"].get("userId") or r["user"].get("id")
    st, d = llamar("GET", "/customers/dashboard", token=tok)
    code = (d.get("customer") or {}).get("referralCode") or (d.get("settings") or {}).get("userCode") or str(uid)
    cred["patrocinadora"] = {"nombre": "Marcela Ortiz", "correo": correo, "password": "Marcela2026!", "id": uid, "codigo": code,
                             "link": f"{os.environ.get('SIM_FRONT','http://localhost:4321')}/#/landing/{code}"}
    print("patrocinadora", correo, "código", code)
    json.dump(cred, open(os.path.join(os.path.dirname(__file__), "credenciales.json"), "w"), ensure_ascii=False, indent=1)
    llamar("POST", "/__sim/guardar")
    print("OK → sim/credenciales.json")

if __name__ == "__main__":
    main()
