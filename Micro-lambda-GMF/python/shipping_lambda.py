import json
import urllib.request
import urllib.error
import core_utils as utils # Importado desde la Lambda Layer

# --- CONFIGURACIÓN DE ORIGEN (Env Vars) ---
ENVIA_API_KEY = utils.os.getenv("ENVIA_API_KEY", "")
ENVIA_API_URL = "https://api-test.envia.com/ship/rate/" # Cambiar a prod en producción

ORIGIN_DATA = {
    "name": utils.os.getenv("SHIPPING_ORIGIN_NAME", "Warehouse MX"),
    "phone": utils.os.getenv("SHIPPING_ORIGIN_PHONE", "8180000000"),
    "street": utils.os.getenv("SHIPPING_ORIGIN_STREET", "Av. Principal"),
    "number": utils.os.getenv("SHIPPING_ORIGIN_NUMBER", "1"),
    "city": utils.os.getenv("SHIPPING_ORIGIN_CITY", "Monterrey"),
    "state": utils.os.getenv("SHIPPING_ORIGIN_STATE", "NL"),
    "country": "MX",
    "postalCode": utils.os.getenv("SHIPPING_ORIGIN_POSTAL_CODE", "64060")
}

# Dimensiones de cajas estándar FindingU (Largo, Ancho, Alto) en cm
_STANDARD_BOXES = [
    (25.0, 17.0, 28.0),   # Chica
    (40.0, 29.0, 20.0),   # Mediana
    (35.0, 23.0, 30.0),   # Grande
]

# --- ALGORITMO DE EMPAQUETADO (PACKING) ---

def _pack_items_for_shipping(raw_items):
    """
    Algoritmo Greedy Bin-Packing:
    Determina cuántas cajas y de qué tamaño se necesitan basándose en las dimensiones
    de los productos.
    """
    expanded = []
    for item in raw_items:
        qty = max(1, int(item.get("quantity") or 1))
        # Dimensiones por defecto si el producto no tiene
        l = max(0.1, float(item.get("lengthCm") or 10))
        w = max(0.1, float(item.get("widthCm") or 10))
        h = max(0.1, float(item.get("heightCm") or 10))
        wt = max(0.05, float(item.get("weightKg") or 0.5))
        for _ in range(qty):
            expanded.append((l, w, h, wt))

    if not expanded:
        return [{
            "type": "box", "content": "Productos", "amount": 1, "declaredValue": 100,
            "weight": 0.5, "dimensions": {"length": 25, "width": 17, "height": 28}
        }]

    # Si es un solo producto, usamos sus dimensiones reales
    if len(expanded) == 1:
        l, w, h, wt = expanded[0]
        dims = sorted([l, w, h], reverse=True)
        return [{
            "type": "box", "content": "Producto", "amount": 1, "declaredValue": 100,
            "weight": wt, "dimensions": {"length": dims[0], "width": dims[1], "height": dims[2]}
        }]

    # Lógica de agrupación en cajas estándar (Greedy)
    boxes_by_vol = sorted(_STANDARD_BOXES, key=lambda b: b[0] * b[1] * b[2])
    remaining = list(range(len(expanded)))
    packages = []

    while remaining:
        chosen_box = None
        packed_indices = []

        for box in boxes_by_vol:
            box_sd = sorted(box, reverse=True)
            box_vol = box[0] * box[1] * box[2]
            
            # Encontrar items que caben en esta caja
            fitting = [idx for idx in remaining if all(
                sorted([expanded[idx][0], expanded[idx][1], expanded[idx][2]], reverse=True)[d] <= box_sd[d]
                for d in range(3)
            )]
            
            if not fitting: continue

            in_box = []
            used_vol = 0.0
            for idx in sorted(fitting, key=lambda i: expanded[i][0]*expanded[i][1]*expanded[i][2], reverse=True):
                item_vol = expanded[idx][0] * expanded[idx][1] * expanded[idx][2]
                if used_vol + item_vol <= box_vol:
                    in_box.append(idx)
                    used_vol += item_vol
            
            if in_box:
                packed_indices = in_box
                chosen_box = box_sd
                break

        if chosen_box:
            total_wt = sum(expanded[i][3] for i in packed_indices)
            packages.append({
                "type": "box", "content": "Productos", "amount": 1,
                "declaredValue": 100 * len(packed_indices),
                "weight": max(0.1, total_wt),
                "dimensions": {"length": chosen_box[0], "width": chosen_box[1], "height": chosen_box[2]}
            })
            for idx in packed_indices: remaining.remove(idx)
        else:
            # Item no cabe en ninguna caja estándar, usar dimensiones del item
            idx = remaining.pop(0)
            packages.append({
                "type": "box", "content": "Sobremedida", "amount": 1, "declaredValue": 100,
                "weight": expanded[idx][3],
                "dimensions": {"length": expanded[idx][0], "width": expanded[idx][1], "height": expanded[idx][2]}
            })

    return packages

# --- HANDLER DE COTIZACIÓN ---

def handle_get_quote(body):
    """POST /shipping/quote"""
    name = str(body.get("name") or body.get("recipientName") or "").strip()
    phone = str(body.get("phone") or "").strip()
    street = str(body.get("street") or body.get("address") or "").strip()
    number = str(body.get("number") or "").strip()
    city = str(body.get("city") or "").strip()
    state = str(body.get("state") or "").strip()
    country = str(body.get("country") or "").strip().upper()
    zip_to = str(body.get("zipTo") or body.get("postalCode") or "").strip()

    has_structured_destination = any([name, phone, street, number, city, state, country])
    if has_structured_destination:
        required_fields = {
            "name": name,
            "phone": phone,
            "street": street,
            "number": number,
            "city": city,
            "state": state,
            "country": country,
            "postalCode": zip_to,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            return utils._json_response(400, {"message": f"Faltan campos requeridos: {', '.join(missing_fields)}"})

    if not zip_to.isdigit() or len(zip_to) != 5:
        return utils._json_response(400, {"message": "Código postal de destino inválido"})

    name = name or "Cliente"
    phone = phone or "0000000000"
    street = street or "Calle"
    number = number or "1"
    city = city or "Ciudad"
    state = state or "Estado"
    country = country or "MX"

    # 1. Cargar Configuración de Negocio (Markup y Carriers)
    app_cfg = utils._load_app_config()
    ship_cfg = app_cfg.get("shipping", {})
    
    if not bool(ship_cfg.get("enabled", True)):
        return utils._json_response(200, {"rates": [], "message": "Envíos deshabilitados temporalmente"})

    markup = float(ship_cfg.get("markup", 0))
    carriers = ship_cfg.get("carriers") or ["dhl", "fedex", "estafeta"]

    # 2. Ejecutar Packing
    raw_items = body.get("items", [])
    packages = _pack_items_for_shipping(raw_items)

    # 3. Consultar API Externa
    destination = {
        "name": name,
        "phone": phone,
        "street": street,
        "number": number,
        "city": city,
        "state": state,
        "country": country,
        "postalCode": zip_to
    }

    all_rates = []
    for carrier in carriers:
        api_payload = {
            "origin": ORIGIN_DATA,
            "destination": destination,
            "packages": packages,
            "shipment": {"type": 1, "carrier": carrier}
        }

        try:
            req = urllib.request.Request(ENVIA_API_URL, data=json.dumps(api_payload).encode())
            print(f"[REQUEST] {carrier.upper()} - Payload: {json.dumps(api_payload)}")
            req.add_header("Authorization", f"Bearer {ENVIA_API_KEY}")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "FinfingU/1.0")
            print(f"[REQUEST] {carrier.upper()} - URL: {ENVIA_API_URL}")
            print(f"[REQUEST] {carrier.upper()} - Headers: {req.header_items()}")
            
            with urllib.request.urlopen(req, timeout=8) as res:
                result = json.loads(res.read().decode())
                print(f"[RESPONSE] {carrier.upper()} - Result: {json.dumps(result)}")
                for rate_item in result.get("data", []):
                    base_price = float(rate_item.get("totalPrice", 0))
                    # Aplicar el markup configurado por el dueño del negocio
                    final_price = round(base_price * (1 + markup), 2)
                    
                    all_rates.append({
                        "carrier": rate_item.get("carrierDescription", carrier),
                        "service": rate_item.get("serviceDescription", ""),
                        "price": base_price,
                        "displayPrice": final_price,
                        "currency": "MXN",
                        "deliveryEstimate": rate_item.get("deliveryEstimate", "")
                    })
        except urllib.error.HTTPError as exc:
            print(f"[shipping_quote] HTTPError carrier={carrier}: {exc.code}")
            print(f"[shipping_quote] HTTPError details: {exc.read().decode()}")
            print(f"[shipping_quote] HTTPError headers: {exc.headers}")
            print(f"[shipping_quote] HTTPError body: {exc.read().decode()}")
        except Exception as exc:
            print(f"[shipping_quote] Error carrier={carrier}: {exc}")
            

    # Ordenar por precio más bajo
    all_rates.sort(key=lambda r: r["displayPrice"])
    
    return utils._json_response(200, {
        "rates": all_rates,
        "packages": len(packages),
        "destZip": zip_to
    })

# --- LAMBDA HANDLER ---

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)

    if "/shipping/quote" in path and method == "POST":
        return handle_get_quote(body)

    return utils._json_response(404, {"message": "Ruta de logística no encontrada"})
