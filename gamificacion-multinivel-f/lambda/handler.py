import base64
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

TABLE_NAME = "multinivel"
BUCKET_NAME = "findingu-ventas"
AWS_REGION = "us-east-1"

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamodb.Table(TABLE_NAME)
_s3 = boto3.client("s3", region_name=AWS_REGION)

_LOGIN_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "user": {
            "userId": "admin-001",
            "name": "Admin Rivera",
            "role": "admin",
        },
    },
    {
        "username": "cliente",
        "password": "cliente123",
        "user": {
            "userId": "client-001",
            "name": "Valeria Torres",
            "role": "cliente",
            "discountPercent": 15,
            "discountActive": True,
            "level": "Oro",
        },
    },
]


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(payload, default=_json_default),
    }


def _parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def _get_http_method(event: dict) -> str:
    return event.get("httpMethod", "")


def _get_path(event: dict) -> str:
    path_params = event.get("pathParameters") or {}
    proxy = path_params.get("proxy")
    if proxy:
        return f"/{proxy}"

    path = event.get("path", "/") or "/"
    stage = (event.get("requestContext") or {}).get("stage")
    if stage and path.startswith(f"/{stage}/"):
        return path[len(stage) + 1 :]
    return path


def _get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _asset_pk(asset_id: str) -> str:
    return f"ASSET#{asset_id}"


def _product_pk(product_id: int) -> str:
    return f"PRODUCT#{product_id}"


def _put_user_profile(payload: dict) -> dict:
    user_id = payload.get("userId") or str(uuid.uuid4())
    user_code = payload.get("userCode")
    if not user_code:
        return _json_response(200, {"message": "userCode es obligatorio", "Error":"BadRequest"})

    item = {
        "PK": _user_pk(user_id),
        "SK": "PROFILE",
        "entityType": "profile",
        "userId": user_id,
        "name": payload.get("name"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        "userCode": user_code,
        "createdAt": _now_iso(),
        "updatedAt": _now_iso(),
        "GSI1PK": f"USERCODE#{user_code}",
        "GSI1SK": f"USER#{user_id}",
    }
    _table.put_item(Item=item)
    return _json_response(201, {"profile": item})


def _login(payload: dict) -> dict:
    username = payload.get("username") or payload.get("user")
    password = payload.get("password")
    if not username or not password:
        return _json_response(200, {"message": "username y password son obligatorios", "Error":"BadRequest"})

    for record in _LOGIN_USERS:
        if record["username"] == username and record["password"] == password:
            return _json_response(200, {"user": record["user"]})

    return _json_response(200, {"message": "Credenciales inválidas", "Error":"BadRequest"})


def _get_user_profile(user_id: str) -> dict:
    response = _table.get_item(Key={"PK": _user_pk(user_id), "SK": "PROFILE"})
    item = response.get("Item")
    if not item:
        return _json_response(200, {"message": "Usuario no encontrado", "Error":"NoEncontrado"})
    return _json_response(200, {"profile": item})


def _put_dashboard(user_id: str, payload: dict) -> dict:
    now = _now_iso()
    pk = _user_pk(user_id)

    dashboard_item = {
        "PK": pk,
        "SK": "DASHBOARD",
        "entityType": "dashboard",
        "userId": user_id,
        "settings": payload.get("settings", {}),
        "buyAgainIds": payload.get("buyAgainIds", []),
        "updatedAt": now,
        "createdAt": payload.get("createdAt", now),
    }

    goals = payload.get("goals", [])
    products = payload.get("products", [])
    featured = payload.get("featured", [])
    network_members = payload.get("networkMembers", [])

    with _table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        batch.put_item(Item=dashboard_item)
        for goal in goals:
            goal_id = goal.get("id") or goal.get("key") or str(uuid.uuid4())
            batch.put_item(
                Item={
                    "PK": pk,
                    "SK": f"GOAL#{goal_id}",
                    "entityType": "goal",
                    "userId": user_id,
                    "goalId": goal_id,
                    "data": goal,
                    "updatedAt": now,
                    "createdAt": now,
                }
            )
        for product in products:
            product_id = product.get("id") or str(uuid.uuid4())
            batch.put_item(
                Item={
                    "PK": pk,
                    "SK": f"PRODUCT#{product_id}",
                    "entityType": "product",
                    "userId": user_id,
                    "productId": product_id,
                    "data": product,
                    "updatedAt": now,
                    "createdAt": now,
                }
            )
        for item in featured:
            featured_id = item.get("id") or str(uuid.uuid4())
            batch.put_item(
                Item={
                    "PK": pk,
                    "SK": f"FEATURED#{featured_id}",
                    "entityType": "featured",
                    "userId": user_id,
                    "featuredId": featured_id,
                    "data": item,
                    "updatedAt": now,
                    "createdAt": now,
                }
            )
        for member in network_members:
            member_id = member.get("id") or str(uuid.uuid4())
            level = member.get("level", "")
            status = member.get("status", "")
            item = {
                "PK": pk,
                "SK": f"NETWORK#{member_id}",
                "entityType": "network",
                "userId": user_id,
                "memberId": member_id,
                "data": member,
                "level": level,
                "status": status,
                "updatedAt": now,
                "createdAt": now,
            }
            if level:
                item["GSI2PK"] = f"LEVEL#{level}"
                item["GSI2SK"] = f"USER#{user_id}#MEMBER#{member_id}"
            if status:
                item["GSI3PK"] = f"STATUS#{status}"
                item["GSI3SK"] = f"USER#{user_id}#MEMBER#{member_id}"
            batch.put_item(Item=item)

    return _json_response(200, {"message": "Dashboard actualizado", "dashboard": dashboard_item})


def _get_dashboard(user_id: str) -> dict:
    pk = _user_pk(user_id)
    response = _table.query(KeyConditionExpression=Key("PK").eq(pk))
    items = response.get("Items", [])
    if not items:
        return _json_response(200, {"message": "Dashboard no encontrado", "Error":"NoEncontrado"})
    return _json_response(200, {"items": items})


def _get_network(user_id: str, query: dict) -> dict:
    level = query.get("level")
    status = query.get("status")
    if level:
        response = _table.query(
            IndexName="GSI2",
            KeyConditionExpression=Key("GSI2PK").eq(f"LEVEL#{level}"),
        )
    elif status:
        response = _table.query(
            IndexName="GSI3",
            KeyConditionExpression=Key("GSI3PK").eq(f"STATUS#{status}"),
        )
    else:
        response = _table.query(
            KeyConditionExpression=Key("PK").eq(_user_pk(user_id)) & Key("SK").begins_with("NETWORK#")
        )
    return _json_response(200, {"items": response.get("Items", [])})


def _create_asset(payload: dict) -> dict:
    if not BUCKET_NAME:
        return _json_response(200, {"message": "BUCKET_NAME no configurado", "Error":"BucketErrr"})
    filename = payload.get("filename")
    content_type = payload.get("contentType") or "application/octet-stream"
    owner_type = payload.get("ownerType", "misc")
    owner_id = payload.get("ownerId", "unknown")
    if not filename:
        return _json_response(200, {"message": "filename es obligatorio", "Error":"BadRequest"})

    asset_id = str(uuid.uuid4())
    key = f"{owner_type}/{owner_id}/{asset_id}/{filename}"
    now = _now_iso()

    item = {
        "PK": _asset_pk(asset_id),
        "SK": "METADATA",
        "entityType": "asset",
        "assetId": asset_id,
        "bucket": BUCKET_NAME,
        "key": key,
        "ownerType": owner_type,
        "ownerId": owner_id,
        "contentType": content_type,
        "createdAt": now,
        "updatedAt": now,
    }

    _table.put_item(Item=item)
    upload_url = _s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=900,
    )

    return _json_response(201, {"asset": item, "uploadUrl": upload_url})


def _create_product_asset(payload: dict) -> dict:
    if not BUCKET_NAME:
        return _json_response(200, {"message": "BUCKET_NAME no configurado", "Error":"BucketErrr"})
    filename = payload.get("filename")
    content_type = payload.get("contentType") or "application/octet-stream"
    product_id = payload.get("productId") or "draft"
    section = payload.get("section")
    if not filename or not section:
        return _json_response(
            200,
            {"message": "filename y section son obligatorios", "Error":"BadRequest"},
        )

    asset_id = str(uuid.uuid4())
    key = f"products/{product_id}/{section}/{asset_id}/{filename}"
    now = _now_iso()

    item = {
        "PK": _asset_pk(asset_id),
        "SK": "METADATA",
        "entityType": "asset",
        "assetId": asset_id,
        "bucket": BUCKET_NAME,
        "key": key,
        "ownerType": "product",
        "ownerId": product_id,
        "section": section,
        "contentType": content_type,
        "createdAt": now,
        "updatedAt": now,
    }

    _table.put_item(Item=item)
    upload_url = _s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=900,
    )

    return _json_response(201, {"asset": item, "uploadUrl": upload_url})


def _get_asset(asset_id: str) -> dict:
    if not BUCKET_NAME:
        return _json_response(200, {"message": "BUCKET_NAME no configurado", "Error":"BucketError"})
    response = _table.get_item(Key={"PK": _asset_pk(asset_id), "SK": "METADATA"})
    item = response.get("Item")
    if not item:
        return _json_response(200, {"message": "Asset no encontrado", "Error":"NoEncontrado"})
    download_url = _s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": item["key"]},
        ExpiresIn=900,
    )
    return _json_response(200, {"asset": item, "downloadUrl": download_url})


def _save_product(payload: dict) -> dict:
    name = payload.get("name")
    price = payload.get("price")
    active = payload.get("active", True)
    if name is None or price is None:
        return _json_response(
            200,
            {"message": "name y price son obligatorios", "Error": "BadRequest"},
        )

    product_id = payload.get("id")
    if product_id is None:
        product_id = int(uuid.uuid4().int % 1000000)

    price_value = Decimal(str(price))
    now = _now_iso()
    item = {
        "PK": _product_pk(int(product_id)),
        "SK": "METADATA",
        "entityType": "product",
        "productId": int(product_id),
        "name": name,
        "price": price_value,
        "active": active,
        "sku": payload.get("sku"),
        "hook": payload.get("hook"),
        "updatedAt": now,
        "createdAt": now,
    }

    _table.put_item(Item=item)
    product_response = {
        "id": int(product_id),
        "name": name,
        "price": float(price_value),
        "active": active,
    }
    return _json_response(201, {"product": product_response})


def _create_order(payload: dict) -> dict:
    customer_id = payload.get("customerId")
    customer_name = payload.get("customerName")
    status = payload.get("status", "pending")
    items = payload.get("items", [])

    if not customer_id or not customer_name or not items:
        return _json_response(
            200,
            {
                "message": "customerId, customerName e items son obligatorios",
                "Error": "BadRequest",
            },
        )

    order_id = payload.get("orderId") or str(uuid.uuid4())
    now = _now_iso()
    normalized_items = []
    total = Decimal("0")

    for item in items:
        quantity = max(1, int(item.get("quantity") or 1))
        price = Decimal(str(item.get("price", 0)))
        normalized_items.append(
            {
                "productId": item.get("productId"),
                "name": item.get("name"),
                "price": price,
                "quantity": quantity,
            }
        )
        total += price * quantity

    order_item = {
        "PK": f"ORDER#{order_id}",
        "SK": "METADATA",
        "entityType": "order",
        "orderId": order_id,
        "customerId": customer_id,
        "customerName": customer_name,
        "status": status,
        "items": normalized_items,
        "total": total,
        "createdAt": now,
        "updatedAt": now,
    }

    _table.put_item(Item=order_item)
    return _json_response(201, {"order": order_item})


def _update_order_status(order_id: str, payload: dict) -> dict:
    status = payload.get("status")
    if status not in {"pending", "paid", "delivered"}:
        return _json_response(
            200,
            {"message": "status inválido", "Error": "BadRequest"},
        )

    now = _now_iso()
    response = _table.update_item(
        Key={"PK": f"ORDER#{order_id}", "SK": "METADATA"},
        UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": status, ":updatedAt": now},
        ReturnValues="ALL_NEW",
    )
    item = response.get("Attributes")
    if not item:
        return _json_response(200, {"message": "Pedido no encontrado", "Error": "NoEncontrado"})

    order_response = {
        "id": item.get("orderId"),
        "customer": item.get("customerName"),
        "total": float(item.get("total") or 0),
        "status": item.get("status"),
    }
    return _json_response(200, {"order": order_response})


def _discount_for_level(level: str) -> str:
    normalized = (level or "").strip().lower()
    if normalized == "oro":
        return "15%"
    if normalized == "plata":
        return "10%"
    return "5%"


def _create_customer(payload: dict) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    level = payload.get("level") or "Oro"
    if not name or not email:
        return _json_response(
            200,
            {"message": "name y email son obligatorios", "Error": "BadRequest"},
        )

    customer_id = payload.get("customerId")
    if not customer_id:
        customer_id = int(datetime.utcnow().timestamp() * 1000)
    now = _now_iso()
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": "PROFILE",
        "entityType": "customer",
        "customerId": customer_id,
        "name": name,
        "email": email,
        "phone": payload.get("phone"),
        "address": payload.get("address"),
        "city": payload.get("city"),
        "leaderId": payload.get("leaderId"),
        "level": level,
        "discount": _discount_for_level(level),
        "commissions": 0,
        "createdAt": now,
        "updatedAt": now,
    }

    _table.put_item(Item=item)
    customer_response = {
        "id": customer_id,
        "name": name,
        "email": email,
        "level": level,
        "discount": item["discount"],
        "commissions": 0,
    }
    return _json_response(201, {"customer": customer_response})


def _scan_entities(pk_prefix: str, sk_value: str, limit: int = 100) -> list:
    items = []
    last_evaluated_key = None
    filter_expression = Attr("PK").begins_with(pk_prefix) & Attr("SK").eq(sk_value)

    while len(items) < limit:
        scan_kwargs = {"FilterExpression": filter_expression}
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
        response = _table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items[:limit]


def _build_admin_warnings(paid_count: int, pending_count: int, commissions_count: int) -> list:
    warnings = []
    if commissions_count:
        warnings.append(
            {
                "type": "commissions",
                "text": f"{commissions_count} comisiones pendientes por depositar",
                "severity": "high",
            }
        )
    if paid_count:
        warnings.append(
            {
                "type": "shipping",
                "text": f"{paid_count} pedidos pagados sin envío",
                "severity": "high",
            }
        )
    if pending_count:
        warnings.append(
            {
                "type": "pending",
                "text": f"{pending_count} pedidos en estado pendiente",
                "severity": "medium",
            }
        )
    return warnings


def _get_admin_dashboard() -> dict:
    customers_raw = _scan_entities("CUSTOMER#", "PROFILE", limit=100)
    orders_raw = _scan_entities("ORDER#", "METADATA", limit=100)
    products_raw = _scan_entities("PRODUCT#", "METADATA", limit=100)

    customers = [
        {
            "id": item.get("customerId"),
            "name": item.get("name"),
            "email": item.get("email"),
            "level": item.get("level"),
            "discount": item.get("discount"),
            "commissions": float(item.get("commissions") or 0),
        }
        for item in customers_raw
    ]

    orders = [
        {
            "id": item.get("orderId"),
            "customer": item.get("customerName"),
            "total": float(item.get("total") or 0),
            "status": item.get("status"),
        }
        for item in orders_raw
    ]

    products = [
        {
            "id": int(item.get("productId")),
            "name": item.get("name"),
            "price": float(item.get("price") or 0),
            "active": bool(item.get("active")),
        }
        for item in products_raw
    ]

    status_counts = {"pending": 0, "paid": 0, "delivered": 0}
    for order in orders:
        status = order.get("status")
        if status in status_counts:
            status_counts[status] += 1

    customers_by_level = {}
    commissions_count = 0
    commissions_total = 0
    for customer in customers:
        level = customer.get("level") or "Sin nivel"
        customers_by_level[level] = customers_by_level.get(level, 0) + 1
        commission_value = float(customer.get("commissions") or 0)
        if commission_value > 0:
            commissions_count += 1
            commissions_total += commission_value

    sales_total = sum(order.get("total", 0) for order in orders)
    average_ticket = sales_total / len(orders) if orders else 0
    active_products = sum(1 for product in products if product.get("active"))

    warnings = _build_admin_warnings(status_counts["paid"], status_counts["pending"], commissions_count)
    asset_slots = [
        {"label": "Miniatura (carrito)", "hint": "square 1:1"},
        {"label": "CTA / Banner", "hint": "landscape 16:9"},
        {"label": "Redes · Story", "hint": "9:16"},
        {"label": "Redes · Feed", "hint": "1:1"},
        {"label": "Producto del Mes", "hint": "landscape 16:9"},
        {"label": "Imagen extra", "hint": "opcional"},
    ]

    stats = {
        "ordersByStatus": status_counts,
        "customersByLevel": customers_by_level,
        "salesTotal": sales_total,
        "averageTicket": average_ticket,
        "activeProducts": active_products,
        "inactiveProducts": max(len(products) - active_products, 0),
        "commissionsTotal": commissions_total,
    }

    return _json_response(
        200,
        {
            "orders": orders,
            "customers": customers,
            "products": products,
            "warnings": warnings,
            "assetSlots": asset_slots,
            "stats": stats,
        },
    )


def lambda_handler(event, context):
    method = _get_http_method(event)
    path = _get_path(event)
    segments = [segment for segment in path.strip("/").split("/") if segment]

    if method == "OPTIONS":
        return _json_response(200, {"status": "ok"})

    if method == "GET" and segments == ["health"]:
        return _json_response(200, {"status": "ok"})

    if not segments:
        return _json_response(200, {"message": "Ruta no encontrada "+path, "Error":"NoEncontrado"})

    if segments[0] == "users":
        if method == "POST":
            return _put_user_profile(_parse_body(event))
        if method == "GET" and len(segments) == 2:
            return _get_user_profile(segments[1])

    if segments[0] == "login" and method == "POST":
        return _login(_parse_body(event))

    if segments[0] == "dashboards" and len(segments) == 2:
        if method == "PUT":
            return _put_dashboard(segments[1], _parse_body(event))
        if method == "GET":
            return _get_dashboard(segments[1])

    if segments[0] == "network" and len(segments) == 2 and method == "GET":
        return _get_network(segments[1], _get_query_params(event))

    if segments[0] == "assets":
        if method == "POST":
            return _create_asset(_parse_body(event))
        if method == "GET" and len(segments) == 2:
            return _get_asset(segments[1])

    if segments[0] == "products" and len(segments) == 2:
        if segments[1] == "assets" and method == "POST":
            return _create_product_asset(_parse_body(event))
    if segments[0] == "products" and len(segments) == 1 and method == "POST":
        return _save_product(_parse_body(event))

    if segments[0] == "orders" and method == "POST":
        return _create_order(_parse_body(event))
    if segments[0] == "orders" and method == "PATCH" and len(segments) == 2:
        return _update_order_status(segments[1], _parse_body(event))

    if segments[0] == "customers" and method == "POST":
        return _create_customer(_parse_body(event))

    if segments == ["admin", "dashboard"] and method == "GET":
        return _get_admin_dashboard()

    return _json_response(200, {"message": "Ruta no encontrada"+segments[0], "Error":"BadRequest"})
