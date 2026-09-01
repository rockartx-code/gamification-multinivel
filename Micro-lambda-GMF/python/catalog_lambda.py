import boto3
import base64
import core_utils as utils # Importado desde la Lambda Layer
from datetime import datetime

# Clientes de AWS
s3 = boto3.client('s3', region_name=utils.AWS_REGION)

# --- CONFIGURACIÓN ---
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

# --- HELPERS DE ASSETS (S3) ---

def _pick_product_image(images: list, preferred_sections: list) -> str:
    if not images or not isinstance(images, list):
        return ""
    for section in preferred_sections:
        for img in images:
            if img.get("section") == section and img.get("url"):
                return img.get("url")
    for img in images:
        if img.get("url"):
            return img.get("url")
    return ""


def _is_product_active(item: dict) -> bool:
    if not item or not isinstance(item, dict):
        return False
    return bool(item.get("active", True))


def _catalog_product_payload(item: dict) -> dict:
    images = item.get("images") or []
    tags = item.get("tags") or []
    badge = str(tags[0]) if tags else ""
    raw_variants = item.get("variants") or []
    variants = []

    for variant_raw in raw_variants:
        if not isinstance(variant_raw, dict):
            continue
        variant = {
            "id": str(variant_raw.get("id") or ""),
            "name": str(variant_raw.get("name") or ""),
            "active": bool(variant_raw.get("active", True)),
        }
        if variant_raw.get("price") is not None:
            variant["price"] = float(utils._to_decimal(variant_raw.get("price")))
        if variant_raw.get("sku"):
            variant["sku"] = str(variant_raw.get("sku"))
        if variant_raw.get("img"):
            variant["img"] = str(variant_raw.get("img"))
        variants.append(variant)

    return {
        "id": str(item.get("productId") or ""),
        "name": str(item.get("name") or ""),
        "price": float(utils._to_decimal(item.get("price") or 0)),
        "badge": badge,
        "img": _pick_product_image(images, ["miniatura", "landing", "redes"]),
        "hook": str(item.get("hook") or ""),
        "description": str(item.get("description") or ""),
        "copyFacebook": str(item.get("copyFacebook") or ""),
        "copyInstagram": str(item.get("copyInstagram") or ""),
        "copyWhatsapp": str(item.get("copyWhatsapp") or ""),
        "images": images,
        "tags": tags,
        "variants": variants,
        "categoryIds": list(item.get("categoryIds") or []),
        "weightKg": item.get("weightKg"),
        "lengthCm": item.get("lengthCm"),
        "widthCm": item.get("widthCm"),
        "heightCm": item.get("heightCm"),
        "inOnlineStore": bool(item.get("inOnlineStore", True)),
        "inPOS": bool(item.get("inPOS", True)),
        "commissionable": bool(item.get("commissionable", True)),
        "vpPoints": float(utils._to_decimal(item["vpPoints"])) if item.get("vpPoints") is not None else None,
    }


def _catalog_payload() -> dict:
    products = []
    for item in utils._query_bucket("PRODUCT"):
        if not _is_product_active(item):
            continue
        if not bool(item.get("inOnlineStore", True)):
            continue
        products.append(_catalog_product_payload(item))

    pom_item = utils._get_by_id("PRODUCT_OF_MONTH", "current")
    product_of_month = None
    if pom_item:
        product = utils._get_by_id("PRODUCT", utils._customer_entity_id(pom_item.get("productId")))
        if isinstance(product, dict) and _is_product_active(product) and bool(product.get("inOnlineStore", True)):
            product_of_month = _catalog_product_payload(product)

    # Categorías y campañas activas: la tienda las necesitaba y por eso seguía
    # llamando al monolítico `/user-dashboard`, que cargaba además la red
    # completa del sistema. Ambas colecciones son pequeñas y públicas.
    categories = [
        {
            "id": str(c.get("categoryId") or c.get("id") or ""),
            "name": str(c.get("name") or ""),
            "parentId": c.get("parentId"),
            "position": int(c.get("position") or 0),
            "active": True,
        }
        for c in utils._query_bucket("PRODUCT_CATEGORY")
        if bool(c.get("active", True))
    ]
    categories.sort(key=lambda c: (c["position"], c["name"]))

    campaigns = [
        {
            "id": c.get("campaignId") or c.get("id"),
            "title": c.get("title"),
            "description": c.get("description"),
            "imageUrl": c.get("imageUrl"),
            "linkUrl": c.get("linkUrl"),
            "active": True,
            "startAt": c.get("startAt"),
            "endAt": c.get("endAt"),
        }
        for c in utils._query_bucket("CAMPAIGN")
        if bool(c.get("active", True))
    ]

    return {
        "products": products,
        "productOfMonth": product_of_month,
        "categories": categories,
        "campaigns": campaigns,
    }

def _upload_to_s3(name: str, content_base64: str, content_type: str) -> str:
    """Sube un archivo a S3 y devuelve la URL pública."""
    try:
        raw_data = base64.b64decode(content_base64)
        asset_id = f"assets/{utils.uuid.uuid4()}-{name}"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=asset_id,
            Body=raw_data,
            ContentType=content_type,
            ACL='public-read'
        )
        return asset_id, f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    except Exception as e:
        print(f"[S3_ERROR] {e}")
        return None, None

# --- HANDLERS DE PRODUCTOS ---

def _get_catalog_product_of_month() -> dict:
    """Devuelve el producto del mes completo para el catálogo, o None."""
    pom_item = utils._get_by_id("PRODUCT_OF_MONTH", "current")
    if not pom_item or pom_item.get("productId") is None:
        return None
    try:
        product = utils._get_by_id("PRODUCT", int(pom_item.get("productId")))
    except (TypeError, ValueError):
        return None
    if not isinstance(product, dict) or not _is_product_active(product):
        return None
    return product


def handle_products(method: str, body: dict, product_id=None) -> dict:
    """GET /products, GET /products/{id}, POST /products"""
    if method == "GET":
        if product_id:
            # /products/product-of-month
            if product_id == "product-of-month":
                pom = utils._get_by_id("PRODUCT_OF_MONTH", "current")
                return utils._json_response(200, {"productOfMonth": pom})

            # /products/{id}
            p = utils._get_by_id("PRODUCT", int(product_id))
            return utils._json_response(200, {"product": p}) if p else utils._json_response(404, {"message": "No encontrado"})

        # /catalog/catalog — catálogo completo para el frontend (activos + en tienda + productOfMonth)
        products = []
        for item in utils._query_bucket("PRODUCT"):
            if not _is_product_active(item):
                continue
            if not bool(item.get("inOnlineStore", True)):
                continue
            products.append(item)

        pom_product = _get_catalog_product_of_month()

        return utils._json_response(200, {
            "products": products,
            "productOfMonth": pom_product,
        })

    if method == "POST":
        if product_id == "product-of-month":
            pid = body.get("productId")
            now = utils._now_iso()
            utils._put_entity("PRODUCT_OF_MONTH", "current", {"productId": int(pid), "updatedAt": now})
            return utils._json_response(200, {"ok": True})

        # Upsert de Producto — incluye variantes con imagen, tags, dimensiones
        pid = body.get("productId") or body.get("id") or int(datetime.now().timestamp() * 1000)
        now = utils._now_iso()

        # Preservar createdAt del registro existente para que _put_entity use el mismo SK
        # y haga overwrite en lugar de insertar un duplicado en el bucket.
        existing = utils._get_by_id("PRODUCT", int(pid)) if (body.get("productId") or body.get("id")) else None
        original_created_at = existing.get("createdAt") if existing else None

        # Normalizar variantes: guardar id, name, price, sku, active, img
        raw_variants = body.get("variants") or []
        variants = []
        for v in raw_variants:
            if not isinstance(v, dict):
                continue
            variant = {
                "id": str(v.get("id") or utils.uuid.uuid4()),
                "name": str(v.get("name") or ""),
                "active": bool(v.get("active", True)),
            }
            if v.get("price") is not None:
                variant["price"] = utils._to_decimal(v.get("price"))
            if v.get("sku"):
                variant["sku"] = str(v.get("sku"))
            if v.get("img"):
                variant["img"] = str(v.get("img"))
            variants.append(variant)

        # Normalizar tags (puede llegar como lista o string csv)
        raw_tags = body.get("tags")
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags if t]
        else:
            tags = []

        product_item = {
            "entityType": "product",
            "productId": int(pid),
            "name": body.get("name"),
            "price": utils._to_decimal(body.get("price")),
            "active": bool(body.get("active", True)),
            "inOnlineStore": bool(body["inOnlineStore"]) if "inOnlineStore" in body else True,
            "inPOS": bool(body["inPOS"]) if "inPOS" in body else True,
            "commissionable": bool(body["commissionable"]) if "commissionable" in body else True,
            "vpPoints": utils._to_decimal(body["vpPoints"]) if body.get("vpPoints") is not None else None,
            "sku": body.get("sku") or "",
            "hook": body.get("hook") or "",
            "description": body.get("description") or "",
            "copyFacebook": body.get("copyFacebook") or "",
            "copyInstagram": body.get("copyInstagram") or "",
            "copyWhatsapp": body.get("copyWhatsapp") or "",
            "tags": tags,
            "images": body.get("images") or [],
            "variants": variants,
            "categoryIds": body.get("categoryIds") or [],
            "weightKg": utils._to_decimal(body.get("weightKg")) if body.get("weightKg") is not None else None,
            "lengthCm": utils._to_decimal(body.get("lengthCm")) if body.get("lengthCm") is not None else None,
            "widthCm":  utils._to_decimal(body.get("widthCm"))  if body.get("widthCm")  is not None else None,
            "heightCm": utils._to_decimal(body.get("heightCm")) if body.get("heightCm") is not None else None,
            "updatedAt": now,
        }

        saved = utils._put_entity("PRODUCT", pid, product_item, created_at_iso=original_created_at)
        utils._audit_event("product.save", None, body, {"productId": pid})
        return utils._json_response(201, {"product": saved})


def handle_catalog(method: str) -> dict:
    """GET / - Resumen publico del catalogo para el frontend."""
    if method != "GET":
        return utils._json_response(405, {"message": "Metodo no permitido"})
    return utils._json_response(200, _catalog_payload())

# --- HANDLER DE CONFIGURACIÓN PÚBLICA (landing sin auth) ---

def handle_public_config() -> dict:
    """GET /config/public — Devuelve descuentos, comisiones y bonos para el landing."""
    app_cfg = utils._load_app_config()
    rewards = app_cfg.get("rewards") or {}
    bonuses = app_cfg.get("bonuses") or {}

    public = {
        "rewards": {
            "discountTiers": [
                {"min": float(utils._to_decimal(t.get("min"))),
                 "max": float(utils._to_decimal(t.get("max"))) if t.get("max") is not None else None,
                 "rate": float(utils._to_decimal(t.get("rate")))}
                for t in (rewards.get("discountTiers") or [])
            ],
            "commissionLevels": [
                {"rate": float(utils._to_decimal(lvl.get("rate"))),
                 "minActiveUsers": int(utils._to_decimal(lvl.get("minActiveUsers") or 0)),
                 "minIndividualPurchase": float(utils._to_decimal(lvl.get("minIndividualPurchase") or 0)),
                 "minGroupPurchase": float(utils._to_decimal(lvl.get("minGroupPurchase") or 0))}
                for lvl in (rewards.get("commissionLevels") or [])
            ],
            "activationNetMin": utils._activation_vp(),
        },
        "bonuses": {
            "vpConfig": bonuses.get("vpConfig") or {"mxnPerVp": 50, "maxNetworkLevels": 5},
            "rankThresholds": [
                {"rank": rt.get("rank"), "vgMin": float(utils._to_decimal(rt.get("vgMin", 0)))}
                for rt in (bonuses.get("rankThresholds") or [])
            ],
            "rules": [
                {k: v for k, v in rule.items()}
                for rule in (bonuses.get("rules") or [])
                if rule.get("active")
            ],
        },
    }
    return utils._json_response(200, {"config": public})


# --- HANDLERS DE CATEGORÍAS ---

def handle_categories(method: str, body: dict, cat_id=None) -> dict:
    """GET, POST, DELETE /product-categories"""
    if method == "GET":
        items = utils._query_bucket("PRODUCT_CATEGORY")
        # Filtrar solo activas para el front
        active_cats = [c for c in items if c.get("active", True)]
        return utils._json_response(200, {"categories": active_cats})

    if method == "POST":
        cid = cat_id or body.get("id") or str(utils.uuid.uuid4())
        item = {
            "entityType": "productCategory", "categoryId": cid,
            "name": body.get("name"), "parentId": body.get("parentId"),
            "position": int(body.get("position", 0)), "active": True
        }
        saved = utils._put_entity("PRODUCT_CATEGORY", cid, item)
        return utils._json_response(201, {"category": saved})

    if method == "DELETE" and cat_id:
        utils._update_by_id("PRODUCT_CATEGORY", cat_id, "SET active = :f", {":f": False})
        return utils._json_response(200, {"ok": True})

# --- HANDLERS DE CAMPAÑAS ---

def handle_campaigns(method: str, body: dict) -> dict:
    """GET, POST /campaigns"""
    if method == "GET":
        items = utils._query_bucket("CAMPAIGN")
        return utils._json_response(200, {"campaigns": items})

    if method == "POST":
        cid = body.get("id") or f"CMP-{utils.uuid.uuid4().hex[:8].upper()}"
        campaign = {
            "entityType": "campaign", "campaignId": cid,
            "name": body.get("name"), "active": bool(body.get("active", True)),
            "banner": body.get("banner"), "story": body.get("story"), "feed": body.get("feed"),
            "ctaPrimaryText": body.get("ctaPrimaryText"), "updatedAt": utils._now_iso()
        }
        saved = utils._put_entity("CAMPAIGN", cid, campaign)
        return utils._json_response(201, {"campaign": saved})

# --- HANDLERS DE ASSETS (IMÁGENES/PDF) ---

def handle_assets(method: str, body: dict, asset_id=None) -> dict:
    """POST /assets, GET /assets/{id}"""
    if method == "GET" and asset_id:
        asset = utils._get_by_id("ASSET", asset_id)
        return utils._json_response(200, {"asset": asset})

    if method == "POST":
        name = body.get("name", "upload")
        b64_data = body.get("contentBase64")
        content_type = body.get("contentType", "image/png")
        
        s3_key, s3_url = _upload_to_s3(name, b64_data, content_type)
        if not s3_key:
            return utils._json_response(500, {"message": "Error al subir a S3"})

        asset_item = {
            "entityType": "asset", "assetId": s3_key, "name": name,
            "url": s3_url, "contentType": content_type, "createdAt": utils._now_iso()
        }
        utils._put_entity("ASSET", s3_key, asset_item)
        return utils._json_response(201, {"asset": asset_item})

# --- HANDLERS DE NOTIFICACIONES ---

def handle_notifications(method: str, body: dict, segments: list) -> dict:
    """GET /notifications, POST /notifications, POST /notifications/{id}/read"""
    if method == "GET":
        items = utils._query_bucket("NOTIFICATION")
        return utils._json_response(200, {"notifications": items})

    if method == "POST":
        # Caso: Marcar como leída /notifications/{id}/read
        if len(segments) == 3 and segments[2] == "read":
            ntf_id = segments[1]
            user_id = body.get("userId")
            pk = f"NOTIFICATION_READ#{user_id}"
            utils._table.put_item(Item={
                "PK": pk, "SK": ntf_id, "readAt": utils._now_iso(), "entityType": "notificationRead"
            })
            return utils._json_response(200, {"ok": True})

        # Caso: Crear/Editar
        nid = body.get("id") or f"NTF-{utils.uuid.uuid4().hex[:8].upper()}"
        ntf = {
            "entityType": "notification", "notificationId": nid,
            "title": body.get("title"), "description": body.get("description"),
            "linkUrl": body.get("linkUrl"), "startAt": body.get("startAt"),
            "endAt": body.get("endAt"), "active": True, "createdAt": utils._now_iso()
        }
        saved = utils._put_entity("NOTIFICATION", nid, ntf)
        return utils._json_response(201, {"notification": saved})

# --- LAMBDA HANDLER ---

def _eliminar_producto(peticion) -> dict:
    """POST /catalog/product/remove — borra el producto y su puntero REF."""
    raw_id = peticion.body.get("productId") or peticion.body.get("id")
    if not raw_id:
        return utils._json_response(400, {"message": "Se requiere productId en el body."})
    try:
        product_id = int(raw_id)
    except (TypeError, ValueError):
        return utils._json_response(400, {"message": "productId debe ser numérico."})

    product = utils._get_by_id("PRODUCT", product_id)
    if not product:
        return utils._json_response(404, {"message": "Producto no encontrado."})

    created_at = product.get("createdAt") or ""
    utils._table.delete_item(Key={"PK": "PRODUCT", "SK": f"{created_at}#{product_id}"})
    utils._table.delete_item(Key={"PK": f"PRODUCT#{product_id}", "SK": "REF"})
    utils._audit_event("product.delete", peticion.headers, peticion.body, {"productId": product_id})
    return utils._json_response(200, {"ok": True, "productId": product_id})


def _subir_asset_de_producto(peticion) -> dict:
    """POST /catalog/product/{productId}/assets — sube una imagen a S3."""
    product_id = peticion.params["productId"]
    section = str(peticion.body.get("section", "general")).strip()
    file_name = str(peticion.body.get("fileName", f"{section}.jpg")).strip() or f"{section}.jpg"
    content_b64 = peticion.body.get("contentBase64", "")
    content_type = str(peticion.body.get("contentType", "image/jpeg")).strip()
    if not content_b64:
        return utils._json_response(400, {"message": "contentBase64 requerido"})
    try:
        raw_data = base64.b64decode(content_b64)
        unique = utils.uuid.uuid4().hex[:8]
        s3_key = f"products/{product_id}/{section}/{unique}-{file_name}"
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=raw_data,
                      ContentType=content_type, ACL="public-read")
        url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{s3_key}"
    except Exception as error:                                        # noqa: BLE001
        utils._log_error("product_asset_upload_failed", error, productId=product_id)
        return utils._json_response(500, {"message": "Error al subir imagen"})
    return utils._json_response(201, {"asset": {
        "assetId": s3_key, "url": url, "section": section,
        "productId": product_id, "contentType": content_type,
    }})


def _listar_productos_admin(peticion) -> dict:
    """GET /catalog/product — catálogo completo, sin filtros de visibilidad."""
    return utils._json_response(200, {
        "products": list(utils._query_bucket("PRODUCT")),
        "productOfMonth": _get_catalog_product_of_month(),
    })


def _privilegio_de_producto(peticion) -> dict:
    """POST /products/{id}: `product-of-month` exige un privilegio distinto."""
    product_id = peticion.params.get("id")
    privilegio = "product_set_month" if product_id == "product-of-month" else "product_add"
    error = utils._require_admin(peticion.headers, privilegio)
    return error or handle_products(peticion.method, peticion.body, product_id)


Ruta = utils.routing.Ruta

#: Superficie del servicio de catálogo. El privilegio de cada endpoint se lee
#: aquí, en una tabla, en vez de estar enterrado en una cascada de `if`.
RUTAS = [
    # ── Catálogo público ────────────────────────────────────────────────────
    Ruta("GET", "catalog", publica=True, descripcion="Catálogo público de la tienda",
         handler=lambda p: handle_catalog(p.method)),
    Ruta("GET", "catalog/config/public", publica=True, descripcion="Config pública del negocio",
         handler=lambda p: handle_public_config()),
    Ruta("GET", "config/public", publica=True, descripcion="Alias legado de la config pública",
         handler=lambda p: handle_public_config()),

    # ── Productos (admin) ───────────────────────────────────────────────────
    Ruta("GET", "catalog/catalog", publica=True, descripcion="Alias legado de listado de productos",
         handler=lambda p: handle_products(p.method, p.body, None)),
    Ruta("POST", "catalog/catalog", privilegio="product_add",
         descripcion="Alias legado de alta de producto",
         handler=lambda p: handle_products(p.method, p.body, None)),
    Ruta("GET", "catalog/product", privilegio="product_add",
         descripcion="Listado completo para el panel", handler=_listar_productos_admin),
    Ruta("POST", "catalog/product", privilegio="product_add",
         descripcion="Crear o actualizar producto",
         handler=lambda p: handle_products(p.method, p.body, None)),
    Ruta("POST", "catalog/product/product-of-month", privilegio="product_set_month",
         descripcion="Fijar el producto del mes",
         handler=lambda p: handle_products(p.method, p.body, "product-of-month")),
    Ruta("POST", "catalog/product/remove", privilegio="product_delete",
         descripcion="Eliminar un producto", handler=_eliminar_producto),
    Ruta("POST", "catalog/product/{productId}/assets", privilegio="product_add",
         descripcion="Subir imagen de producto", handler=_subir_asset_de_producto),

    # ── Productos (rutas legadas sin prefijo) ───────────────────────────────
    Ruta("GET", "products", publica=True, handler=lambda p: handle_products(p.method, p.body, None)),
    Ruta("POST", "products", privilegio="product_add",
         handler=lambda p: handle_products(p.method, p.body, None)),
    Ruta("GET", "products/{id}", publica=True, handler=lambda p: handle_products(p.method, p.body, p.params["id"])),
    # El privilegio depende del id (`product-of-month` exige otro), así que se
    # resuelve dentro del handler; ver `_privilegio_de_producto`.
    Ruta("POST", "products/{id}", handler=_privilegio_de_producto),

    # ── Categorías ──────────────────────────────────────────────────────────
    Ruta("GET", "catalog/categories", publica=True, handler=lambda p: handle_categories(p.method, p.body, None)),
    Ruta("POST", "catalog/categories", privilegio="access_screen_products",
         handler=lambda p: handle_categories(p.method, p.body, None)),
    Ruta("GET", "catalog/categories/{id}", publica=True, handler=lambda p: handle_categories(p.method, p.body, p.params["id"])),
    Ruta("DELETE", "catalog/categories/{id}", privilegio="access_screen_products",
         handler=lambda p: handle_categories(p.method, p.body, p.params["id"])),
    Ruta("GET", "product-categories", publica=True, handler=lambda p: handle_categories(p.method, p.body, None)),
    # `handle_categories` ignora el id en GET y devuelve la colección completa.
    # Se conserva tal cual: cambiar esa semántica es una decisión de API, no de
    # ruteo, y no toca hacerla en este refactor.
    Ruta("GET", "product-categories/{id}", publica=True,
         handler=lambda p: handle_categories(p.method, p.body, p.params["id"])),
    Ruta("POST", "product-categories", privilegio="access_screen_products",
         handler=lambda p: handle_categories(p.method, p.body, None)),
    Ruta("DELETE", "product-categories/{id}", privilegio="access_screen_products",
         handler=lambda p: handle_categories(p.method, p.body, p.params["id"])),

    # ── Campañas y assets ───────────────────────────────────────────────────
    Ruta("GET", "campaigns", publica=True, handler=lambda p: handle_campaigns(p.method, p.body)),
    Ruta("POST", "campaigns", privilegio="access_screen_stocks",
         handler=lambda p: handle_campaigns(p.method, p.body)),
    Ruta("GET", "assets", publica=True, handler=lambda p: handle_assets(p.method, p.body, None)),
    Ruta("POST", "assets", privilegio="product_add",
         handler=lambda p: handle_assets(p.method, p.body, None)),

    # ── Notificaciones ──────────────────────────────────────────────────────
    Ruta("GET", "notifications", publica=True, handler=lambda p: handle_notifications(p.method, p.body, p.segments)),
    # Ídem: el GET con id devuelve la lista completa. Comportamiento preservado.
    Ruta("GET", "notifications/{id}", publica=True,
         handler=lambda p: handle_notifications(p.method, p.body, p.segments)),
    Ruta("POST", "notifications", privilegio="config_manage",
         handler=lambda p: handle_notifications(p.method, p.body, p.segments)),
    Ruta("DELETE", "notifications/{id}", privilegio="config_manage",
         handler=lambda p: handle_notifications(p.method, p.body, p.segments)),
    # El acuse de lectura lo hace el propio cliente: no exige privilegio de admin.
    Ruta("POST", "notifications/{id}/read", publica=True,
         descripcion="Marcar notificación como leída",
         handler=lambda p: handle_notifications(p.method, p.body, p.segments)),
]


def lambda_handler(event: dict, context) -> dict:
    return utils.routing.despachar(
        RUTAS, event, servicio="catalog",
        raiz=lambda p: handle_catalog(p.method),
        requiere_privilegio=utils._require_admin,
    )
