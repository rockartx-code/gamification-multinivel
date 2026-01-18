import base64
import json
import os
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ.get("TABLE_NAME", "Gamificacion")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

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


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(payload),
    }


def _parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body)


def _get_http_method(event: dict) -> str:
    return event.get("httpMethod", "")


def _get_path(event: dict) -> str:
    proxy = event.get("pathParameters", {}).get("proxy")
    if proxy:
        return f"/{proxy}"
    path = event.get("path", "/")
    stage = event.get("requestContext", {}).get("stage")
    if stage and path.startswith(f"/{stage}/"):
        return path[len(stage) + 1 :]
    return path


def _get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _asset_pk(asset_id: str) -> str:
    return f"ASSET#{asset_id}"


def _put_user_profile(payload: dict) -> dict:
    user_id = payload.get("userId") or str(uuid.uuid4())
    user_code = payload.get("userCode")
    if not user_code:
        return _json_response(400, {"message": "userCode es obligatorio"})

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
        return _json_response(400, {"message": "username y password son obligatorios"})

    for record in _LOGIN_USERS:
        if record["username"] == username and record["password"] == password:
            return _json_response(200, {"user": record["user"]})

    return _json_response(401, {"message": "Credenciales inválidas"})


def _get_user_profile(user_id: str) -> dict:
    response = _table.get_item(Key={"PK": _user_pk(user_id), "SK": "PROFILE"})
    item = response.get("Item")
    if not item:
        return _json_response(404, {"message": "Usuario no encontrado"})
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
        return _json_response(404, {"message": "Dashboard no encontrado"})
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
        return _json_response(500, {"message": "BUCKET_NAME no configurado"})
    filename = payload.get("filename")
    content_type = payload.get("contentType") or "application/octet-stream"
    owner_type = payload.get("ownerType", "misc")
    owner_id = payload.get("ownerId", "unknown")
    if not filename:
        return _json_response(400, {"message": "filename es obligatorio"})

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


def _get_asset(asset_id: str) -> dict:
    if not BUCKET_NAME:
        return _json_response(500, {"message": "BUCKET_NAME no configurado"})
    response = _table.get_item(Key={"PK": _asset_pk(asset_id), "SK": "METADATA"})
    item = response.get("Item")
    if not item:
        return _json_response(404, {"message": "Asset no encontrado"})
    download_url = _s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": item["key"]},
        ExpiresIn=900,
    )
    return _json_response(200, {"asset": item, "downloadUrl": download_url})


def handler(event, context):
    method = _get_http_method(event)
    path = _get_path(event)
    segments = [segment for segment in path.strip("/").split("/") if segment]

    if method == "OPTIONS":
        return _json_response(200, {"status": "ok"})

    if method == "GET" and segments == ["health"]:
        return _json_response(200, {"status": "ok"})

    if not segments:
        return _json_response(404, {"message": "Ruta no encontrada"})

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

    return _json_response(404, {"message": "Ruta no encontrada"})
