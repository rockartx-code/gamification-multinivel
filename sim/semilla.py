#!/usr/bin/env python3
"""Puebla el backend local con lo mínimo para que exista un negocio (ronda 6).

Mundo nuevo, sin rastro de las rondas 1 a 5 (archivadas en
`sim/archivo/rondas-01-05-diarios-mensajes.zip`): personal nuevo, catálogo con
fichas de producto de verdad, tres sucursales con ciudad y estado, la
configuración que las mejoras de `docs/qa/23` necesitan para poder probarse, y
una socia con red vacía que invitará a los prospectos.
"""
import json, os, re, sys, urllib.request, time, base64

API = os.environ.get("SIM_API", "http://localhost:4400")
SUPER = os.environ.get("SUPERADMIN_TOKEN", "sim-superadmin-token")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def llamar(metodo, ruta, cuerpo=None, token=None):
    req = urllib.request.Request(API + ruta, method=metodo,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def buzon(correo):
    return llamar("GET", f"/__sim/buzon/{correo}")[1]


TODOS = ["access_screen_orders", "access_screen_customers", "access_screen_products", "access_screen_stocks",
         "access_screen_pos", "access_screen_stats", "access_screen_settings", "order_mark_paid", "order_mark_shipped",
         "order_mark_delivered", "order_create", "customer_add", "commissions_register_payment", "product_add",
         "product_update", "product_delete", "product_set_month", "stock_create", "stock_create_transfer",
         "stock_add_inventory", "stock_mark_damaged", "stock_receive_transfer", "pos_register_sale", "user_mark_admin",
         "user_manage_privileges", "employee_add", "employee_manage_privileges", "access_screen_employees",
         "config_manage", "access_screen_honor_board"]

EMPLEADOS = [
    {"name": "Renata Bustos", "email": "renata@findingu.mx", "phone": "5551100001",
     "rol": "gerente de operaciones", "puesto": "Gerencia", "privileges": TODOS},
    {"name": "Toño Vera", "email": "tono@findingu.mx", "phone": "5551100002",
     "rol": "almacén y pedidos", "puesto": "Almacén",
     "privileges": ["access_screen_orders", "order_mark_paid", "order_mark_shipped", "order_mark_delivered",
                    "access_screen_stocks", "stock_add_inventory", "stock_create_transfer", "stock_receive_transfer",
                    "stock_mark_damaged"]},
    {"name": "Mireya Solano", "email": "mireya@findingu.mx", "phone": "5551100003",
     "rol": "cajera de mostrador", "puesto": "Caja",
     "privileges": ["access_screen_pos", "pos_register_sale", "access_screen_orders", "order_mark_delivered",
                    "access_screen_stocks", "customer_add"]},
    {"name": "Gaby Ledesma", "email": "gaby@findingu.mx", "phone": "5551100004",
     "rol": "ejecutiva de cuentas (coach)", "puesto": "Coach",
     "privileges": ["access_screen_customers", "access_screen_orders", "access_screen_stats",
                    "access_screen_honor_board", "customer_add"]},
    {"name": "Alma Rentería", "email": "alma@findingu.mx", "phone": "5551100005",
     "rol": "administración y finanzas", "puesto": "Finanzas",
     "privileges": ["access_screen_customers", "access_screen_orders", "access_screen_stats",
                    "commissions_register_payment", "access_screen_settings", "config_manage",
                    "access_screen_honor_board"]},
]

# Fichas de producto de verdad: en las rondas 1 a 5, tres personas no compraron
# por catálogo vacío ("sigo sin saber cuántos gramos de proteína tiene").
FICHAS = {
    "finding pro": {
        "hook": "Proteína de suero con colágeno hidrolizado",
        "desc": ("Bote de 500 g · 20 porciones de 25 g. Por porción: 21 g de proteína de suero aislada, "
                 "5 g de colágeno hidrolizado tipo I y III, 2.4 g de BCAA, 110 kcal, 1 g de azúcares. "
                 "Sabor vainilla. Sin gluten. Disuelve en 250 ml de agua o leche. "
                 "Una porción al día, de preferencia después de entrenar."),
        "tags": ["proteina", "colageno", "suero", "polvo", "vainilla"]},
    "klinhart": {
        "hook": "Omega 3 de alta pureza (EPA + DHA)",
        "desc": ("60 cápsulas blandas · 2 meses de consumo. Por cápsula: 1,000 mg de aceite de pescado con "
                 "660 mg de EPA y 440 mg de DHA, en forma de triglicérido reesterificado. Destilado molecular, "
                 "libre de metales pesados. Una cápsula al día con alimentos."),
        "tags": ["omega 3", "epa", "dha", "corazon", "capsulas"]},
    "longevit": {
        "hook": "Antioxidantes con resveratrol y CoQ10",
        "desc": ("60 cápsulas · 2 meses. Por cápsula: 250 mg de resveratrol (extracto de vid), 100 mg de "
                 "coenzima Q10 (ubiquinona), 50 mg de extracto de té verde y 200 UI de vitamina E. "
                 "Una cápsula al día con el desayuno."),
        "tags": ["antioxidante", "resveratrol", "coq10", "energia celular"]},
    "boom": {
        "hook": "Complejo B con energía sostenida",
        "desc": ("30 tabletas · 1 mes. Cada tableta aporta el 100 % del valor diario de B1, B2, B3, B5, B6, "
                 "biotina, ácido fólico y B12 (500 mcg de metilcobalamina), más 50 mg de ginseng. "
                 "Sin cafeína. Una tableta con el desayuno."),
        "tags": ["complejo b", "b12", "energia", "vitaminas"]},
    "naplus": {
        "hook": "Electrolitos para hidratación",
        "desc": ("20 sobres de 6 g · sabor limón. Por sobre: 500 mg de sodio, 250 mg de potasio, 60 mg de "
                 "magnesio, 12 mg de vitamina C y 5 g de carbohidratos. Sin azúcar añadida. "
                 "Disuelve un sobre en 500 ml de agua durante o después del ejercicio."),
        "tags": ["electrolitos", "hidratacion", "sodio", "potasio", "limon"]},
    # Ronda 7 · Valeria, y antes Ximena, Aurora, Mariana y Ernesto: ocho de los
    # catorce productos caían al texto de relleno ("Presentación y modo de uso en
    # la etiqueta del producto") y el botón "Ver detalle" abría exactamente esa
    # misma frase. «Pagué $700 por un bote sin saber cuántos gramos trae.»
    "colageno": {
        "hook": "Colágeno hidrolizado tipo I y III con vitamina C",
        "desc": ("Bote de 300 g · 30 porciones de 10 g. Por porción: 10 g de colágeno hidrolizado "
                 "tipo I y III (péptidos bioactivos, peso molecular 2,000 Da), 80 mg de vitamina C y "
                 "50 mg de ácido hialurónico. Sin sabor, sin azúcar, se disuelve en frío o en caliente. "
                 "Una porción al día en agua, café o jugo. Rinde un mes."),
        "tags": ["colageno", "piel", "articulaciones", "acido hialuronico", "sin sabor"]},
    "creatina": {
        "hook": "Creatina monohidratada micronizada",
        "desc": ("Bote de 300 g · 60 porciones de 5 g. Por porción: 5 g de creatina monohidratada "
                 "micronizada al 99.9 %, sin aditivos ni saborizantes. Una porción al día, cualquier "
                 "hora, disuelta en 250 ml de agua. No requiere fase de carga. Rinde dos meses."),
        "tags": ["creatina", "fuerza", "monohidratada", "sin sabor"]},
    "gel reductivo": {
        "hook": "Gel de aplicación tópica con cafeína y centella",
        "desc": ("Envase de 250 ml · uso externo. Fórmula con 5 % de cafeína, extracto de centella "
                 "asiática, algas marinas y mentol. Textura en gel, de rápida absorción, no graso. "
                 "Aplica una capa delgada sobre abdomen, muslos o brazos con masaje circular, dos veces "
                 "al día. No aplicar sobre piel irritada. Rinde entre 6 y 8 semanas."),
        "tags": ["gel", "topico", "cafeina", "centella", "uso externo"]},
    "crt-1200": {
        "hook": "L-carnitina líquida de 1,200 mg por toma",
        "desc": ("Frasco de 480 ml · 16 tomas de 30 ml. Por toma: 1,200 mg de L-carnitina tartrato, "
                 "50 mg de vitamina B6 y 30 mg de extracto de té verde. Sabor frutos rojos, sin azúcar. "
                 "Toma 30 ml treinta minutos antes de entrenar, o en ayunas los días de descanso."),
        "tags": ["carnitina", "liquida", "frutos rojos", "pre entreno"]},
    "keto": {
        "hook": "Electrolitos sin carbohidratos para dieta cetogénica",
        "desc": ("Bote de 300 g · 30 porciones de 10 g. Por porción: 1,000 mg de sodio, 400 mg de "
                 "potasio, 120 mg de magnesio y 200 mg de calcio. Cero carbohidratos y cero azúcares: "
                 "no rompe el ayuno. Sabor mango. Disuelve una porción en 500 ml de agua al día."),
        "tags": ["keto", "electrolitos", "sin carbohidratos", "ayuno", "mango"]},
    "biotina": {
        "hook": "Biotina de 10,000 mcg para cabello, piel y uñas",
        "desc": ("60 cápsulas · 2 meses. Por cápsula: 10,000 mcg de biotina (vitamina B7), 100 mg de "
                 "MSM, 50 mg de extracto de cola de caballo y 30 mg de zinc. Apto para vegetarianos. "
                 "Una cápsula al día con alimentos."),
        "tags": ["biotina", "cabello", "unas", "piel", "zinc"]},
    "bhb": {
        "hook": "Sales de BHB (beta-hidroxibutirato) para cetosis",
        "desc": ("Bote de 240 g · 30 porciones de 8 g. Por porción: 6,000 mg de beta-hidroxibutirato "
                 "en sales de calcio, sodio y magnesio, más 500 mg de MCT en polvo. Sabor limón, sin "
                 "azúcar. Disuelve una porción en 350 ml de agua, una vez al día, de preferencia en ayunas."),
        "tags": ["bhb", "cetosis", "keto", "mct", "limon"]},
    "glu-10": {
        "hook": "Ácido alfa lipoico con cromo para el metabolismo de la glucosa",
        "desc": ("60 cápsulas · 2 meses. Por cápsula: 600 mg de ácido alfa lipoico, 200 mcg de picolinato "
                 "de cromo, 250 mg de extracto de canela y 100 mg de berberina. Una cápsula al día con "
                 "la comida principal. No sustituye ningún tratamiento médico: consulta a tu médico si "
                 "tomas medicamento para la glucosa."),
        "tags": ["acido alfa lipoico", "cromo", "glucosa", "berberina", "canela"]},
}

SUCURSALES = [
    {"name": "Bodega Central", "location": "Av. Insurgentes Sur 1234, Col. Del Valle", "postalCode": "03100",
     "city": "Ciudad de México", "state": "CDMX", "isMainWarehouse": True, "allowPickup": True, "uds": 60},
    {"name": "Tienda Del Valle", "location": "Av. Coyoacán 1200, Col. Del Valle", "postalCode": "03104",
     "city": "Ciudad de México", "state": "CDMX", "isMainWarehouse": False, "allowPickup": True, "uds": 12},
    {"name": "Sucursal Guadalajara", "location": "Av. Chapultepec 480, Col. Americana", "postalCode": "44160",
     "city": "Guadalajara", "state": "Jalisco", "isMainWarehouse": False, "allowPickup": True, "uds": 10},
]


def main():
    cred = {"api": API, "empleados": [], "productos": [], "almacenes": [], "patrocinadora": None}

    # 1. personal
    for e in EMPLEADOS:
        st, r = llamar("POST", "/auth/employees",
                       {"name": e["name"], "email": e["email"], "phone": e["phone"],
                        # El puesto es lo que pinta la insignia del back office: decía ADMIN
                        # sobre el nombre de la cajera igual que sobre el de la gerente.
                        "jobTitle": e["puesto"],
                        "privileges": {p: True for p in e["privileges"]}}, SUPER)
        assert st == 201, (st, r)
        cred["empleados"].append({"nombre": e["name"], "correo": e["email"], "password": r["tempPassword"],
                                  "rol": e["rol"], "id": r["employee"].get("employeeId")})
        print("empleado", e["name"], "→", r["tempPassword"])

    # 2. catálogo con fichas completas
    seed = json.load(open(os.path.join(RAIZ, "Micro-lambda-GMF", "python", "seed", "product_pc_seed.json")))
    for i, p in enumerate(seed["products"], start=1):
        clave = next((k for k in FICHAS if k in p["name"].lower() or any(k in a for a in p.get("aliases", []))), None)
        ficha = FICHAS.get(clave, {"hook": "Suplemento Finding'U de uso diario",
                                   "desc": "Presentación y modo de uso en la etiqueta del producto.", "tags": []})
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'>"
               f"<rect width='400' height='400' fill='#1f3d31'/>"
               f"<text x='200' y='210' font-family='sans-serif' font-size='30' fill='#c8a24a' "
               f"text-anchor='middle'>{p['name']}</text></svg>")
        img = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        cuerpo = {"name": p["name"], "price": p["price"], "vpPoints": p["vpPoints"], "sku": f"FU-{i:03d}",
                  "description": ficha["desc"], "hook": ficha["hook"], "active": True,
                  "images": [{"section": "miniatura", "url": img}, {"section": "landing", "url": img}],
                  "tags": ficha["tags"] or p.get("aliases", [])}
        st, r = llamar("POST", "/catalog/product", cuerpo, SUPER)
        assert st in (200, 201), (st, r)
        pid = (r.get("product") or r).get("productId") or (r.get("product") or r).get("id")
        cred["productos"].append({"id": pid, "nombre": p["name"], "precio": p["price"], "pc": p["vpPoints"]})
    print("productos:", len(cred["productos"]))
    llamar("POST", "/catalog/product/product-of-month", {"productId": cred["productos"][0]["id"]}, SUPER)

    # 3. sucursales con ciudad y estado (propuesta 11) y existencias
    ids_emp = [e["id"] for e in cred["empleados"] if e["id"] is not None]
    for s in SUCURSALES:
        st, r = llamar("POST", "/inventory/stocks",
                       {k: s[k] for k in ("name", "location", "postalCode", "city", "state",
                                          "isMainWarehouse", "allowPickup")} | {"linkedUserIds": ids_emp}, SUPER)
        assert st == 201, (st, r)
        sid = r["stock"]["stockId"]
        cred["almacenes"].append({"id": sid, "nombre": s["name"], "ciudad": s["city"]})
        for p in cred["productos"]:
            st, _ = llamar("POST", f"/inventory/stocks/{sid}/entries",
                           {"productId": p["id"], "qty": s["uds"], "userId": ids_emp[0]}, SUPER)
            assert st == 200, (st, _)
        print("sucursal", s["name"], f"({s['city']}) con {s['uds']} uds de cada producto")

    # 4. configuración que las mejoras necesitan para poder probarse
    st, actual = llamar("GET", "/commissions/config/app", token=SUPER)
    cfg = actual.get("config", {})
    pagos = dict(cfg.get("payments", {}))
    ml = dict(pagos.get("mercadoLibre", {}))
    ml["webhookSecret"] = "sim-webhook-2027"
    # Sin notificationUrl el checkout no anexa el secreto y el webhook llega sin él (401):
    # con el secreto puesto y la URL vacía, ningún pago se acreditaría.
    ml["notificationUrl"] = f"{API}/orders/webhooks/mercadolibre"
    pagos["mercadoLibre"] = ml
    pos = dict(cfg.get("pos", {}))
    pos["cashCutNotifyEmail"] = "renata@findingu.mx"
    envios = dict(cfg.get("shipping", {}))
    integracion = dict(envios.get("carrierIntegration", {}))
    integracion.update({"enabled": True, "provider": "simulada", "autoLabel": True, "trackingEnabled": True})
    envios["carrierIntegration"] = integracion
    st, r = llamar("PUT", "/commissions/config/app", {"payments": pagos, "pos": pos, "shipping": envios}, SUPER)
    assert st == 200, (st, r)
    print("config: webhook con secreto, correo del corte, paquetería simulada encendida")

    # 5. socia con red vacía que invitará a los prospectos
    correo = "paulina.rios@gmail.com"
    st, r = llamar("POST", "/auth/crearcuenta", {"name": "Paulina Ríos", "email": correo, "phone": "5552100001",
                                                 "password": "Paulina2027!", "confirmPassword": "Paulina2027!"})
    assert st in (200, 201), (st, r)
    time.sleep(0.3)
    tokens = [t for m in buzon(correo) for l in m["enlaces"] for t in re.findall(r"token=([A-Za-z0-9._-]+)", l)]
    assert tokens, "no llegó el correo de verificación"
    st, r = llamar("POST", "/auth/verify-email", {"token": tokens[-1]})
    assert st == 200, (st, r)
    st, r = llamar("POST", "/auth/login", {"email": correo, "password": "Paulina2027!"})
    assert st == 200, (st, r)
    tok = r["token"]
    uid = r["user"].get("userId") or r["user"].get("id")
    # Es socia desde el principio: alguien la invitó el año pasado.
    llamar("POST", "/customers/modo-socio", {"customerId": uid, "reason": "semilla"}, tok)
    st, d = llamar("GET", "/customers/dashboard", token=tok)
    code = (d.get("customer") or {}).get("referralCode") or (d.get("settings") or {}).get("userCode") or str(uid)
    cred["patrocinadora"] = {"nombre": "Paulina Ríos", "correo": correo, "password": "Paulina2027!", "id": uid,
                             "codigo": code,
                             "link": f"{os.environ.get('SIM_FRONT', 'http://localhost:4321')}/#/landing/{code}"}
    print("patrocinadora", correo, "código", code)

    json.dump(cred, open(os.path.join(os.path.dirname(__file__), "credenciales.json"), "w"),
              ensure_ascii=False, indent=1)
    llamar("POST", "/__sim/guardar")
    print("OK → sim/credenciales.json")


if __name__ == "__main__":
    main()
