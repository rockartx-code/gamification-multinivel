"""Único punto de acceso a DynamoDB: patrón bucket+REF, consultas y lotes."""

import json
import time
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .settings import AWS_REGION, MAX_BATCH_GET_RETRIES, TABLE_NAME
from .values import _dedupe_ddb_keys, _json_default, _normalize_ddb_key, _now_iso
from .logs import _log_get_item_failure


_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

_table = _dynamodb.Table(TABLE_NAME)

_ddb_client = _table.meta.client

_ddb_serializer = TypeSerializer()

_ddb_deserializer = TypeDeserializer()

def _bucket_pk(entity: str) -> str:
    return entity.upper()

def _ref_pk(entity: str, entity_id: Any) -> str:
    return f"{entity.upper()}#{entity_id}"

def _make_bucket_sk(created_at_iso: str, entity_id: Any) -> str:
    return f"{created_at_iso}#{entity_id}"

def _put_entity(entity: str, entity_id: Any, item: dict, created_at_iso: Optional[str] = None) -> dict:
    entity = entity.upper()
    created_at = created_at_iso or item.get("createdAt") or _now_iso()
    
    main_item = dict(item)
    main_item["PK"] = _bucket_pk(entity)
    main_item["SK"] = main_item.get("SK") or _make_bucket_sk(created_at, entity_id)
    main_item["createdAt"] = main_item.get("createdAt") or created_at
    main_item["updatedAt"] = _now_iso()

    ref_item = {
        "PK": _ref_pk(entity, entity_id),
        "SK": "REF",
        "entityId": entity_id,
        "refPK": main_item["PK"],
        "refSK": main_item["SK"],
        "updatedAt": main_item["updatedAt"]
    }
    # Si el item principal expira por TTL, su puntero debe expirar con él;
    # sin esto las sesiones purgadas dejaban filas REF huérfanas para siempre.
    if main_item.get("ttl") is not None:
        ref_item["ttl"] = main_item["ttl"]

    _put_entity_atomic(main_item, ref_item)
    return main_item

def _put_entity_atomic(main_item: dict, ref_item: dict) -> None:
    """Escribe el item principal y su puntero REF en una sola transacción.

    Sin transacción, un fallo entre ambos `put_item` deja el item principal
    escrito pero invisible para `_get_by_id` (registro huérfano permanente).
    Si la tabla o el endpoint no soportan `TransactWriteItems`, cae al modo
    secuencial escribiendo primero el REF para no dejar punteros colgando.
    """
    try:
        _ddb_client.transact_write_items(TransactItems=[
            {"Put": {"TableName": TABLE_NAME, "Item": _ddb_serialize_item(main_item)}},
            {"Put": {"TableName": TABLE_NAME, "Item": _ddb_serialize_item(ref_item)}},
        ])
        return
    except ClientError as ex:
        error_code = (ex.response or {}).get("Error", {}).get("Code", "")
        if error_code not in ("ValidationException", "UnknownOperationException", "InternalServerError"):
            raise
        print(json.dumps({
            "event": "transact_write_unavailable_fallback",
            "table": TABLE_NAME,
            "errorType": error_code,
            "key": {"PK": main_item.get("PK"), "SK": main_item.get("SK")},
        }, default=_json_default))

    _table.put_item(Item=main_item)
    _table.put_item(Item=ref_item)

#: Entidades cuya lectura no sigue el patrón bucket+REF y aportan su propio
#: lector. Evita que la capa genérica de datos tenga que conocer entidades de
#: negocio concretas: antes `_get_by_id` traía dentro un `if entity ==
#: "ASSOCIATE_MONTH"`, que es exactamente la clase de acoplamiento que impide
#: separar el acceso a datos del dominio.
_ENTITY_READERS: Dict[str, Any] = {}

#: Lo mismo para las lecturas en lote.
_ENTITY_BATCH_LOADERS: Dict[str, Any] = {}

def register_entity_reader(entity: str, reader) -> None:
    """Registra un lector propio para una entidad con clave no estándar."""
    _ENTITY_READERS[str(entity or "").upper()] = reader

def register_entity_batch_loader(entity: str, loader) -> None:
    """Registra un lector en lote propio para una entidad con clave no estándar."""
    _ENTITY_BATCH_LOADERS[str(entity or "").upper()] = loader

def _get_by_id(entity: str, entity_id: Any) -> Optional[dict]:
    reader = _ENTITY_READERS.get(str(entity or "").upper())
    if reader is not None:
        return reader(entity_id)
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: return None
    resp_main = _table.get_item(Key={"PK": ref["refPK"], "SK": ref["refSK"]})
    return resp_main.get("Item")

def _update_by_id(entity: str, entity_id: Any, expression: str, values: dict, names: Optional[dict] = None) -> dict:
    resp_ref = _table.get_item(Key={"PK": _ref_pk(entity, entity_id), "SK": "REF"})
    ref = resp_ref.get("Item")
    if not ref: raise KeyError(f"{entity}_NOT_FOUND")

    kwargs = {
        "Key": {"PK": ref["refPK"], "SK": ref["refSK"]},
        "UpdateExpression": expression,
        "ExpressionAttributeValues": values,
        "ReturnValues": "ALL_NEW"
    }
    if names: kwargs["ExpressionAttributeNames"] = names
    
    resp = _table.update_item(**kwargs)
    return resp.get("Attributes")

def _query_bucket(entity: str, limit: Optional[int] = None, forward: bool = False,
                  sk_prefix: Optional[str] = None, sk_from: Optional[str] = None,
                  sk_to: Optional[str] = None, projection: Optional[List[str]] = None) -> List[dict]:
    """Lee una colección completa (o un tramo de ella) paginando hasta el final.

    Como `SK` es `"{createdAt}#{id}"`, `sk_prefix`/`sk_from`/`sk_to` permiten
    acotar por fecha **en la condición de clave**, sin traer el histórico
    entero para filtrarlo en memoria:

        _query_bucket("POS_SALE", sk_prefix="2026-09")        # solo septiembre
        _query_bucket("ORDER", sk_from="2026-09-01")          # desde esa fecha

    OJO con `sk_to`: es un tope crudo (`SK <= valor`), no un prefijo. Como el SK
    lleva la hora, `sk_to="2026-08"` deja FUERA todo agosto (`"2026-08-04..."`
    es mayor que `"2026-08"`). Para incluir un mes o día completo hay que
    añadir un centinela alto: `sk_to="2026-08\uffff"`. Usado sin centinela
    equivale a "estrictamente anterior a ese mes", que es justo lo que hace
    falta para comparar contra meses previos.

    `projection` limita los atributos devueltos (menos RCU consumidos).
    OJO: `limit` se aplica antes de cualquier filtro posterior en Python; son
    "N items leídos", no "N resultados tras filtrar".
    """
    pk = _bucket_pk(entity)
    condition = Key("PK").eq(pk)
    if sk_prefix:
        condition = condition & Key("SK").begins_with(str(sk_prefix))
    elif sk_from and sk_to:
        condition = condition & Key("SK").between(str(sk_from), str(sk_to))
    elif sk_from:
        condition = condition & Key("SK").gte(str(sk_from))
    elif sk_to:
        condition = condition & Key("SK").lte(str(sk_to))

    query_kwargs = {"KeyConditionExpression": condition, "ScanIndexForward": forward}
    if limit: query_kwargs["Limit"] = limit
    if projection:
        names = {f"#p{i}": attr for i, attr in enumerate(projection)}
        query_kwargs["ProjectionExpression"] = ", ".join(names)
        query_kwargs["ExpressionAttributeNames"] = names

    items = []
    while True:
        resp = _table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek or (limit and len(items) >= limit): break
        query_kwargs["ExclusiveStartKey"] = lek
    return items

def _iter_bucket(entity: str, forward: bool = False, sk_prefix: Optional[str] = None,
                 sk_from: Optional[str] = None, sk_to: Optional[str] = None,
                 page_size: int = 100):
    """Itera una colección página a página, permitiendo cortar antes del final.

    Útil cuando solo interesa el elemento más reciente que cumple un filtro:
    con `forward=False` el primer acierto suele estar en la primera página, así
    que el consumidor rompe el bucle sin haber leído el histórico entero.
    """
    condition = Key("PK").eq(_bucket_pk(entity))
    if sk_prefix:
        condition = condition & Key("SK").begins_with(str(sk_prefix))
    elif sk_from and sk_to:
        condition = condition & Key("SK").between(str(sk_from), str(sk_to))
    elif sk_from:
        condition = condition & Key("SK").gte(str(sk_from))
    elif sk_to:
        condition = condition & Key("SK").lte(str(sk_to))

    query_kwargs = {
        "KeyConditionExpression": condition,
        "ScanIndexForward": forward,
        "Limit": max(1, int(page_size)),
    }
    while True:
        resp = _table.query(**query_kwargs)
        for item in resp.get("Items", []):
            yield item
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return
        query_kwargs["ExclusiveStartKey"] = lek

def _query_all_pages(**query_kwargs) -> List[dict]:
    """Ejecuta un `query` arbitrario recorriendo TODAS las páginas.

    DynamoDB corta cualquier `Query` en 1 MB y devuelve `LastEvaluatedKey`;
    ignorarlo produce resultados incompletos sin ningún error visible.
    """
    kwargs = dict(query_kwargs)
    items: List[dict] = []
    while True:
        resp = _table.query(**kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        kwargs["ExclusiveStartKey"] = lek
    return items

def _safe_get_item(key: dict, log_event: Optional[str] = None, **extra) -> Optional[dict]:
    try:
        resp = _table.get_item(Key=key)
    except Exception as ex:
        if log_event:
            _log_get_item_failure(log_event, key, ex, **extra)
        raise
    return resp.get("Item")

def _get_item_by_key(key: dict) -> Optional[dict]:
    normalized_key = _normalize_ddb_key(key)
    if not normalized_key:
        return None
    item = _safe_get_item(normalized_key, "ddb_parallel_get_item_failed")
    if not item:
        return None
    return item

def _ddb_serialize_key(key: dict) -> dict:
    return {key_name: _ddb_serializer.serialize(value) for key_name, value in key.items()}

def _ddb_serialize_item(item: dict) -> dict:
    """Convierte un item de alto nivel al formato AttributeValue del cliente crudo.

    Usa el mismo `TypeSerializer` que emplea el recurso de boto3 en `put_item`,
    incluidos los `None` (que viajan como NULL), para que escribir por
    transacción guarde exactamente lo mismo que escribir por el recurso.
    """
    return {
        attr_name: _ddb_serializer.serialize(value)
        for attr_name, value in (item or {}).items()
    }

def _ddb_deserialize_item(item: dict) -> dict:
    return {key_name: _ddb_deserializer.deserialize(value) for key_name, value in item.items()}

def _ddb_key_request_shape(keys: List[dict]) -> str:
    if not keys:
        return "empty"
    sample = keys[0]
    if not isinstance(sample, dict):
        return "invalid"
    if all(isinstance(value, dict) and len(value) == 1 for value in sample.values()):
        return "attribute_value"
    return "plain"

def _batch_get_items(keys: List[dict]) -> List[dict]:
    normalized_keys = _dedupe_ddb_keys(keys)
    if not normalized_keys:
        return []

    loaded_items: List[dict] = []
    pending = list(normalized_keys)

    while pending:
        chunk = pending[:100]
        pending = pending[100:]
        
        # 1. ¡CAMBIO AQUÍ! Pasamos el chunk directo, SIN llamar a _ddb_serialize_key
        request = {
            TABLE_NAME: {
                "Keys": chunk,
            }
        }

        retries = 0
        while True:
            try:
                # 2. ¡CAMBIO AQUÍ! Usamos _dynamodb (Resource) en vez de _ddb_client
                resp = _dynamodb.batch_get_item(RequestItems=request)
            except ClientError as ex:
                error = ex.response.get("Error", {}) if isinstance(ex.response, dict) else {}
                print(json.dumps({
                    "event": "ddb_batch_get_failed",
                    "table": TABLE_NAME,
                    "errorType": error.get("Code") or ex.__class__.__name__,
                    "message": error.get("Message") or str(ex),
                    "requestKeyShape": _ddb_key_request_shape(request.get(TABLE_NAME, {}).get("Keys", [])),
                    "keys": chunk,
                }, default=_json_default))
                raise

            # 3. ¡CAMBIO AQUÍ! _dynamodb ya devuelve diccionarios normales, NO usamos _ddb_deserialize_item
            raw_items = resp.get("Responses", {}).get(TABLE_NAME, [])
            loaded_items.extend(raw_items)

            unprocessed = resp.get("UnprocessedKeys", {}).get(TABLE_NAME, {})
            unprocessed_keys = unprocessed.get("Keys", [])
            if not unprocessed_keys:
                break

            retries += 1
            if retries > MAX_BATCH_GET_RETRIES:
                # Sin tope, un throttling sostenido hace girar el Lambda hasta
                # agotar su timeout en vez de fallar rápido.
                print(json.dumps({
                    "event": "ddb_batch_get_unprocessed_exhausted",
                    "table": TABLE_NAME,
                    "retries": retries,
                    "pendingKeys": len(unprocessed_keys),
                }, default=_json_default))
                raise RuntimeError(
                    f"BatchGetItem dejó {len(unprocessed_keys)} claves sin procesar "
                    f"tras {MAX_BATCH_GET_RETRIES} reintentos"
                )
            time.sleep(min(0.05 * (2 ** (retries - 1)), 1.0))
            request = {
                TABLE_NAME: {
                    "Keys": unprocessed_keys,
                }
            }

    return loaded_items

def _batch_get_entities(entity: str, entity_ids: List[Any]) -> List[dict]:
    entity = str(entity or "").upper()
    normalized_ids: List[Any] = []
    seen = set()
    for raw_id in entity_ids or []:
        entity_id = _normalize_batch_entity_id(entity, raw_id)
        dedupe_key = json.dumps(entity_id, default=str)
        if entity_id in (None, "") or dedupe_key in seen:
            continue
        normalized_ids.append(entity_id)
        seen.add(dedupe_key)

    if not normalized_ids:
        return []

    loader = _ENTITY_BATCH_LOADERS.get(entity)
    if loader is not None:
        return loader(normalized_ids)

    ref_items = _batch_get_items([
        {"PK": _ref_pk(entity, entity_id), "SK": "REF"}
        for entity_id in normalized_ids
    ])
    if not ref_items:
        return []

    main_items = _batch_get_items([
        {"PK": ref_item["refPK"], "SK": ref_item["refSK"]}
        for ref_item in ref_items
        if ref_item.get("refPK") and ref_item.get("refSK")
    ])
    return main_items

#: Normalizadores de id por entidad. Igual que los lectores: la capa genérica
#: no debe decidir según la entidad; cada una aporta el suyo.
_ENTITY_ID_NORMALIZERS: Dict[str, Any] = {}


def register_entity_id_normalizer(entity: str, normalizer) -> None:
    """Registra cómo normalizar el id de una entidad antes de leerla en lote."""
    _ENTITY_ID_NORMALIZERS[str(entity or "").upper()] = normalizer


def _normalize_batch_entity_id(entity: str, raw_id: Any) -> Any:
    normalizer = _ENTITY_ID_NORMALIZERS.get(str(entity or "").upper())
    return normalizer(raw_id) if normalizer else raw_id
