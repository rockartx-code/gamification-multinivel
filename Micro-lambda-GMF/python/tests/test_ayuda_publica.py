"""Paquete D · propuestas 8 y 39 — la puerta de salida de quien ya pagó.

Julio compró como invitado, le llegó el bote estrellado y **para encontrar el
teléfono de la tienda a la que ya le había pagado $1,209 tuvo que crear una
cuenta y verificar su correo** (docs/qa/25 §3.11). Aurora probó cuatro rutas
con el mismo resultado, ya habiendo pagado $1,500 sin saber a qué hora abre la
sucursal donde va a recoger. Y Julio preguntó por WhatsApp las cuatro cosas de
la devolución —plazo, evidencia, quién paga el envío y a dónde se manda—
porque no estaban escritas en ninguna pantalla (§7.3 nº 39).

`GET /catalog/ayuda` responde las tres cosas **sin sesión**.
"""
import json

import pytest


def _sucursales(utils):
    utils._put_entity("STOCK", "STK-GDL", {
        "entityType": "stock", "stockId": "STK-GDL", "name": "Sucursal Guadalajara",
        "location": "Av. Chapultepec 480", "city": "Guadalajara", "state": "JAL",
        "allowPickup": True, "isMainWarehouse": True, "linkedUserIds": [],
        "inventory": {"7": 5}})
    utils._put_entity("STOCK", "STK-BOD", {
        "entityType": "stock", "stockId": "STK-BOD", "name": "Bodega Vallejo",
        "location": "Vallejo", "city": "Ciudad de México", "state": "CMX",
        "allowPickup": False, "linkedUserIds": [], "inventory": {"7": 500}})


def _ayuda(utils, headers=None):
    import catalog_lambda
    r = catalog_lambda.lambda_handler(
        {"path": "/catalog/ayuda", "httpMethod": "GET", "headers": headers or {},
         "queryStringParameters": {}, "body": "{}"}, None)
    assert r["statusCode"] == 200, r["body"]
    return json.loads(r["body"])


def test_sin_sesion_se_publica_el_telefono_y_el_horario_de_la_tienda(utils):
    """Julio no debería tener que crear una cuenta para saber a quién escribirle."""
    _sucursales(utils)
    datos = _ayuda(utils)
    contacto = datos["contacto"]
    assert contacto["email"] and "@" in contacto["email"]
    assert contacto["whatsapp"].startswith("+52")
    assert "Lunes a viernes" in contacto["horario"]
    assert contacto["direccion"]


def test_las_sucursales_salen_con_su_ciudad_y_sin_un_solo_dato_de_inventario(utils):
    """Aurora pagó $1,500 sin saber a qué hora abre la sucursal donde va a recoger;
    lo que nunca debe salir de aquí es el inventario ni cuál es la bodega principal."""
    _sucursales(utils)
    sucursales = _ayuda(utils)["sucursales"]
    assert [s["name"] for s in sucursales] == ["Sucursal Guadalajara"]
    gdl = sucursales[0]
    assert gdl["city"] == "Guadalajara" and gdl["location"] == "Av. Chapultepec 480"
    assert "inventory" not in gdl and "isMainWarehouse" not in gdl


def test_la_politica_de_devolucion_responde_las_seis_preguntas_de_julio(utils):
    _sucursales(utils)
    pasos = _ayuda(utils)["devoluciones"]["pasos"]
    assert [p["clave"] for p in pasos] == [
        "que", "plazo", "evidencia", "envio", "direccion", "reembolso"]
    texto = " ".join(p["texto"] for p in pasos)
    assert "48 horas" in texto and "7 días" in texto          # los dos plazos de hoy
    assert "foto del paquete cerrado" in texto                 # la evidencia por motivo
    assert "lo paga quien devuelve" in texto                   # decisión de negocio 39
    assert "Av. Chapultepec 480" in texto                      # a dónde se manda
    assert "2 días hábiles" in texto and "3 a 5 días hábiles" in texto


def test_el_envio_de_regreso_lo_paga_la_empresa_solo_cuando_el_error_es_nuestro(utils):
    motivos = {m["key"]: m for m in _ayuda(utils)["devoluciones"]["motivos"]}
    assert motivos["DANADO_DEFECTUOSO"]["responsableEnvio"] == "empresa"
    assert motivos["ERROR_ENVIO"]["responsableEnvio"] == "empresa"
    assert motivos["DESISTIMIENTO"]["responsableEnvio"] == "cliente"


def test_cambiar_el_plazo_en_configuracion_cambia_el_texto_publicado(utils):
    """La política se muda a configuración con los valores de hoy; si el negocio
    cambia el plazo, cambia en la misma frase que leen pantalla y correo."""
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"motivos": [
            {"key": "DESISTIMIENTO", "label": "Cambié de opinión", "limiteHoras": 240,
             "responsableEnvio": "cliente", "evidencia": "paquete_cerrado"}]}}})
    utils._invalidate_app_config_cache()
    pasos = {p["clave"]: p["texto"] for p in _ayuda(utils)["devoluciones"]["pasos"]}
    assert "10 días" in pasos["plazo"]
    assert "48 horas" not in pasos["plazo"]


def test_la_direccion_de_devolucion_configurada_gana_a_la_sucursal_principal(utils):
    _sucursales(utils)
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"direccionDevolucion": "Almacén de devoluciones, Calle 5 de Mayo 12, Zapopan"}}})
    utils._invalidate_app_config_cache()
    devoluciones = _ayuda(utils)["devoluciones"]
    assert devoluciones["direccionDevolucion"].startswith("Almacén de devoluciones")
    assert "Zapopan" in [p for p in devoluciones["pasos"] if p["clave"] == "direccion"][0]["texto"]


@pytest.mark.parametrize("motivo, error_esperado", [
    ({"key": "", "limiteHoras": 48, "responsableEnvio": "empresa", "evidencia": "completa"}, "sin clave"),
    ({"key": "X", "limiteHoras": "pronto", "responsableEnvio": "empresa", "evidencia": "completa"}, "número de horas"),
    ({"key": "X", "limiteHoras": 0, "responsableEnvio": "empresa", "evidencia": "completa"}, "entre 1 y 8760"),
    ({"key": "X", "limiteHoras": 9000, "responsableEnvio": "empresa", "evidencia": "completa"}, "entre 1 y 8760"),
    ({"key": "X", "limiteHoras": 48, "responsableEnvio": "la vecina", "evidencia": "completa"}, "solo puede ser la empresa o el cliente"),
    ({"key": "X", "limiteHoras": 48, "responsableEnvio": "empresa", "evidencia": "selfie"}, "completa o paquete cerrado"),
])
def test_una_politica_mal_escrita_se_rechaza_con_su_motivo(utils, motivo, error_esperado):
    import ayuda_handlers
    error = ayuda_handlers.validar_returns({"motivos": [motivo]})
    assert error and error_esperado in error


def test_una_politica_correcta_se_acepta(utils):
    import ayuda_handlers
    assert ayuda_handlers.validar_returns({"motivos": [
        {"key": "DANADO_DEFECTUOSO", "label": "Llegó dañado", "limiteHoras": 72,
         "responsableEnvio": "empresa", "evidencia": "completa"}]}) is None
    assert ayuda_handlers.validar_returns({"refundBusinessDays": "3 a 5"}) is None


def test_una_configuracion_rota_nunca_deja_al_cliente_sin_regla(utils):
    """La validación dura corre al guardar; si algo se coló, la lectura cae a los
    valores por omisión en vez de dejar el pedido sin motivos válidos."""
    import order_lambda
    utils._put_entity("CONFIG", "app-v1", {"entityType": "config", "configId": "app-v1", "config": {
        "returns": {"motivos": [{"key": "X", "limiteHoras": "ayer", "responsableEnvio": "nadie", "evidencia": "?"}]}}})
    utils._invalidate_app_config_cache()
    motivos = order_lambda._motivos_devolucion()
    assert set(motivos) == {"DANADO_DEFECTUOSO", "ERROR_ENVIO", "DESISTIMIENTO"}
