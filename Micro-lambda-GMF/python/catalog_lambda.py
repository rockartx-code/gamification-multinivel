import json
import boto3
import base64
import core_utils as utils # Importado desde la Lambda Layer
from datetime import datetime

# Clientes de AWS
s3 = boto3.client('s3', region_name=utils.AWS_REGION)

# --- CONFIGURACIÓN ---
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")

# --- HELPERS DE ASSETS (S3) ---

def _pick_product_image(images, preferred_sections):
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


def _is_product_active(item):
    if not item or not isinstance(item, dict):
        return False
    return bool(item.get("active", True))


def _catalog_product_payload(item):
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
    }


def _catalog_payload():
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

    return {"products": products, "productOfMonth": product_of_month}

def _upload_to_s3(name, content_base64, content_type):
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

def handle_products(method, body, product_id=None):
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
        
        # Listado general
        items = utils._query_bucket("PRODUCT")
        return utils._json_response(200, {"products": items})

    if method == "POST":
        if product_id == "product-of-month":
            pid = body.get("productId")
            now = utils._now_iso()
            utils._put_entity("PRODUCT_OF_MONTH", "current", {"productId": int(pid), "updatedAt": now})
            return utils._json_response(200, {"ok": True})

        # Upsert de Producto — incluye variantes con imagen, tags, dimensiones
        pid = body.get("productId") or body.get("id") or int(datetime.now().timestamp() * 1000)
        now = utils._now_iso()

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
                variant["price"] = float(utils._to_decimal(v.get("price")))
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
            "weightKg": float(utils._to_decimal(body.get("weightKg"))) if body.get("weightKg") is not None else None,
            "lengthCm": float(utils._to_decimal(body.get("lengthCm"))) if body.get("lengthCm") is not None else None,
            "widthCm":  float(utils._to_decimal(body.get("widthCm")))  if body.get("widthCm")  is not None else None,
            "heightCm": float(utils._to_decimal(body.get("heightCm"))) if body.get("heightCm") is not None else None,
            "updatedAt": now,
        }

        saved = utils._put_entity("PRODUCT", pid, product_item)
        utils._audit_event("product.save", None, body, {"productId": pid})
        return utils._json_response(201, {"product": saved})


def handle_catalog(method):
    """GET / - Resumen publico del catalogo para el frontend."""
    if method != "GET":
        return utils._json_response(405, {"message": "Metodo no permitido"})
    return utils._json_response(200, _catalog_payload())

# --- HANDLER DE CONFIGURACIÓN PÚBLICA (landing sin auth) ---

def handle_public_config():
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
            "activationNetMin": float(utils._to_decimal(rewards.get("activationNetMin", 50))),
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

def handle_categories(method, body, cat_id=None):
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

def handle_campaigns(method, body):
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

def handle_assets(method, body, asset_id=None):
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

def handle_notifications(method, body, segments):
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

def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return utils._cors_preflight_response()
    body = utils._parse_body(event)
    headers = event.get("headers") or {}
    segments = [s for s in path.strip("/").split("/") if s]

    if not segments:
        return handle_catalog(method)

    try:
        root = segments[0]

        if root == "catalog" and len(segments) == 1:
            return handle_catalog(method)

        if root == "catalog" and len(segments) > 2 and segments[1] == "config" and segments[2] == "public" and method == "GET":
            return handle_public_config()

        if root == "products":
            p_id = segments[1] if len(segments) > 1 else None
            if method == "POST":
                # product-of-month requiere product_set_month; demás escrituras requieren product_add
                priv = "product_set_month" if p_id == "product-of-month" else "product_add"
                err = utils._require_admin(headers, priv)
                if err: return err
            return handle_products(method, body, p_id)

        if root == "product-categories":
            c_id = segments[1] if len(segments) > 1 else None
            if method in ("POST", "DELETE"):
                err = utils._require_admin(headers, "access_screen_products")
                if err: return err
            return handle_categories(method, body, c_id)

        if root == "campaigns":
            if method == "POST":
                err = utils._require_admin(headers, "access_screen_stocks")
                if err: return err
            return handle_campaigns(method, body)

        if root == "assets":
            a_id = segments[1] if len(segments) > 1 else None
            if method == "POST":
                err = utils._require_admin(headers, "product_add")
                if err: return err
            return handle_assets(method, body, a_id)

        if root == "notifications":
            if method == "POST" and not (len(segments) == 3 and segments[2] == "read"):
                # Crear/editar notificación: solo admin con config_manage
                err = utils._require_admin(headers, "config_manage")
                if err: return err
            return handle_notifications(method, body, segments)

        if root == "config" and len(segments) > 1 and segments[1] == "public" and method == "GET":
            return handle_public_config()

        return utils._json_response(404, {"message": "Ruta no encontrada en Catalog Service"})

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return utils._json_response(500, {"message": "Error interno", "error": str(e)})