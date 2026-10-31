"""Cableado de las entidades con almacenamiento no estándar.

La capa de datos (`core.db`) es genérica: lee y escribe con el patrón
bucket+REF sin saber qué entidad maneja. Las que no siguen ese patrón —hoy
solo `ASSOCIATE_MONTH`, con clave directa y un puntero legado— aportan aquí
su lector, su lector en lote y su normalizador de id.

Este módulo es el ÚNICO sitio donde una entidad concreta se conecta a la capa
genérica. Si mañana otra entidad necesita clave propia, se registra aquí y
`core/db.py` no cambia.
"""

from .db import (
    register_entity_batch_loader,
    register_entity_id_normalizer,
    register_entity_reader,
)
from .network import _batch_get_associate_months, _get_associate_month_by_id
from .values import _associate_month_entity_id, _customer_entity_id


def _normalize_associate_month_id(raw_id):
    """`"<customerId>#<YYYY-MM>"`, tolerando ids ya normalizados o vacíos."""
    raw_value = str(raw_id or "").strip()
    if not raw_value:
        return ""
    associate_id, separator, month_key = raw_value.partition("#")
    if not separator:
        return raw_value
    return _associate_month_entity_id(associate_id, month_key)


register_entity_id_normalizer("CUSTOMER", _customer_entity_id)
register_entity_id_normalizer("ASSOCIATE_MONTH", _normalize_associate_month_id)
register_entity_reader("ASSOCIATE_MONTH", _get_associate_month_by_id)
register_entity_batch_loader("ASSOCIATE_MONTH", _batch_get_associate_months)
