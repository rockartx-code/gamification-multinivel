"""Capa común del backend, separada por responsabilidad.

Las dependencias van **siempre hacia abajo** en esta lista; un módulo nunca
importa a otro que esté por debajo suyo:

    settings → domain → values → logs → http → db
                                              ├→ config
                                              ├→ network → entities
                                              ├→ ledger
                                              ├→ security
                                              ├→ email
                                              └→ audit

Importar el paquete deja registrados los lectores de entidades con clave no
estándar (ASSOCIATE_MONTH), así que `core.db._get_by_id` se comporta igual sea
cual sea el punto de entrada.

Los lambdas siguen usando `import core_utils as utils`, que reexporta todo esto.
"""
from . import settings, domain, values, logs, http, db, config, network  # noqa: F401
from . import entities, indexes, ledger, security, email, audit  # noqa: F401

__all__ = ["settings", "domain", "values", "logs", "http", "db", "config",
           "network", "entities", "indexes", "ledger", "security", "email", "audit"]
