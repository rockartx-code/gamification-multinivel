"""Paquete D · ronda 26 — ayuda pública, contacto, sucursales y política de devolución.

Lo que vivió la gente (docs/qa/25 §3.11 y §3.12):

- Julio compró como invitado, le llegó el bote estrellado y, **para encontrar
  el teléfono de la tienda a la que ya le había pagado $1,209, tuvo que crear
  una cuenta y verificar su correo**: `#/ayuda`, `#/contacto`, `#/devoluciones`,
  `#/soporte`, `#/sucursales` y `#/facturacion` rebotaban a la tienda y el pie
  de página decía, completo, "© 2026 finding U".
- Aurora probó cuatro rutas con el mismo resultado, ya habiendo pagado $1,500
  sin saber a qué hora abre la sucursal donde va a recoger.
- Julio preguntó por WhatsApp las cuatro cosas de la devolución —plazo,
  evidencia, quién paga el envío de regreso y a dónde se manda— porque **no
  estaban escritas en ninguna pantalla** (docs/qa/25 §7.3 nº 39).

Este módulo publica esos datos **sin sesión**, en un solo endpoint
(`GET /catalog/ayuda`), y es la **única fuente** del texto de la política de
devolución: la misma que lee `#/devoluciones`, el asistente de devolución, el
correo de entrega y el correo de solicitud recibida. Si el negocio cambia
`returns.motivos[].limiteHoras`, el plazo cambia en las cuatro salidas.

Nunca publica inventario ni `isMainWarehouse`: de las sucursales solo salen
nombre, ubicación, ciudad y estado.
"""
from decimal import Decimal
from typing import Optional

import core_utils as utils
from core.routing import Ruta

#: Reglas de evidencia admitidas y lo que se le pide a la persona en cada una.
EVIDENCIA_TEXTO = {
    "completa": "fotos del producto, del empaque y de la guía de envío",
    "paquete_cerrado": "una foto del paquete cerrado con la guía visible",
}

#: Quién paga el envío de regreso, dicho como lo diría una persona.
RESPONSABLE_TEXTO = {
    "empresa": "lo pagamos nosotros (guarda tu ticket de paquetería y te lo reembolsamos)",
    "cliente": "lo pagas tú",
}


# ---------------------------------------------------------------------------
# Configuración: lectura y validación
# ---------------------------------------------------------------------------

def contacto(cfg: Optional[dict] = None) -> dict:
    """Correo, WhatsApp, horario y dirección que publica el pie de página."""
    cfg = cfg if cfg is not None else utils._load_app_config()
    bloque = (cfg.get("contacto") or {})
    return {
        "email": str(bloque.get("email") or ""),
        "whatsapp": str(bloque.get("whatsapp") or ""),
        "horario": str(bloque.get("horario") or ""),
        "direccion": str(bloque.get("direccion") or ""),
        "avisoPrivacidadUrl": str(bloque.get("avisoPrivacidadUrl") or ""),
    }


def sucursales() -> list:
    """Sucursales que reciben gente, sin un solo dato de inventario."""
    salida = []
    for s in utils._query_bucket("STOCK") or []:
        if not s.get("allowPickup"):
            continue
        salida.append({
            "id": str(s.get("stockId") or ""),
            "name": str(s.get("name") or ""),
            "location": str(s.get("location") or ""),
            "city": str(s.get("city") or ""),
            "state": str(s.get("state") or ""),
        })
    return sorted(salida, key=lambda x: (x["city"], x["name"]))


def direccion_devolucion(cfg: Optional[dict] = None) -> str:
    """A dónde se manda el paquete: la dirección configurada o, si está vacía,
    la sucursal principal (que es lo que el correo ya usaba)."""
    cfg = cfg if cfg is not None else utils._load_app_config()
    escrita = str((cfg.get("returns") or {}).get("direccionDevolucion") or "").strip()
    if escrita:
        return escrita
    from core import order_emails
    return order_emails._direccion_bodega_principal()


def validar_returns(bloque) -> Optional[str]:
    """Valida el bloque `returns` que llega al guardar la configuración.

    Devuelve el motivo del rechazo o `None` si todo está bien. Una sola clave
    inválida rechaza el bloque entero y **no se guarda nada**: el plazo y el
    responsable entran directo en el importe reembolsado y, río abajo, en la
    anulación de comisiones (docs/arquitectura/26 §4.5).
    """
    if bloque is None:
        return None
    if not isinstance(bloque, dict):
        return "La política de devolución debe ser un bloque de configuración."
    if "motivos" not in bloque:
        return None
    motivos = bloque.get("motivos")
    if not isinstance(motivos, list) or not motivos:
        return "Deja al menos un motivo de devolución."
    vistas = set()
    for crudo in motivos:
        if not isinstance(crudo, dict):
            return "Cada motivo de devolución debe traer clave, plazo, responsable del envío y evidencia."
        clave = str(crudo.get("key") or "").strip().upper()
        if not clave:
            return "Hay un motivo de devolución sin clave."
        if clave in vistas:
            return f"El motivo {clave} está repetido."
        vistas.add(clave)
        crudo_horas = crudo.get("limiteHoras")
        try:
            horas = int(Decimal(str(crudo_horas)))
        except (TypeError, ValueError, ArithmeticError):
            return f"El plazo del motivo {clave} debe ser un número de horas."
        if not 1 <= horas <= 8760:
            return f"El plazo del motivo {clave} debe estar entre 1 y 8760 horas (un año)."
        responsable = str(crudo.get("responsableEnvio") or "").strip()
        if responsable not in ("empresa", "cliente"):
            return f"En el motivo {clave}, quien paga el envío de regreso solo puede ser la empresa o el cliente."
        if str(crudo.get("evidencia") or "").strip() not in EVIDENCIA_TEXTO:
            return f"La evidencia del motivo {clave} solo puede ser completa o paquete cerrado."
    return None


# ---------------------------------------------------------------------------
# La política de devolución: una sola fuente, tres salidas
# ---------------------------------------------------------------------------

def _plazo_texto(horas: int) -> str:
    """El plazo como lo diría una persona: las 48 horas de un producto dañado
    son "48 horas", no "2 días"; los 168 de un arrepentimiento son "7 días"."""
    if horas >= 72 and horas % 24 == 0:
        dias = horas // 24
        return "1 día" if dias == 1 else f"{dias} días"
    return "1 hora" if horas == 1 else f"{horas} horas"


def motivos_publicados(cfg: Optional[dict] = None) -> list:
    """Los motivos vigentes, en el orden y con las palabras que ve la persona."""
    import order_lambda
    cfg = cfg if cfg is not None else utils._load_app_config()
    salida = []
    for clave, regla in order_lambda._motivos_devolucion(cfg).items():
        salida.append({
            "key": clave,
            "label": regla.get("label") or clave,
            "limiteHoras": int(regla["limite_horas"]),
            "plazoTexto": _plazo_texto(int(regla["limite_horas"])),
            "responsableEnvio": regla["responsable_envio"],
            "responsableTexto": RESPONSABLE_TEXTO[regla["responsable_envio"]],
            "evidencia": regla["regla_evidencia"],
            "evidenciaTexto": EVIDENCIA_TEXTO[regla["regla_evidencia"]],
        })
    return salida


def texto_politica(cfg: Optional[dict] = None) -> list:
    """El proceso completo en seis puntos, armado con la configuración vigente.

    Se lee **sin reescribir** en `#/devoluciones`, en el asistente
    `#/orden/:id/devolucion`, en el correo de entrega y en el de solicitud
    recibida. Cambiar `returns.motivos[].limiteHoras` cambia el plazo en las
    cuatro salidas: es la prueba de que la fuente es una sola.
    """
    cfg = cfg if cfg is not None else utils._load_app_config()
    returns = (cfg.get("returns") or {})
    motivos = motivos_publicados(cfg)
    metodo = str(returns.get("refundMethod") or "mismo medio de pago")
    dias_reembolso = str(returns.get("refundBusinessDays") or "3 a 5")
    dias_inspeccion = str(returns.get("inspeccionDiasHabiles") or "2")
    direccion = direccion_devolucion(cfg) or "nuestro almacén (te lo confirmamos por correo al abrir la solicitud)"

    plazos = " ".join(f"«{m['label']}»: {m['plazoTexto']}." for m in motivos)
    evidencias = " ".join(f"«{m['label']}»: {m['evidenciaTexto']}." for m in motivos)
    paga_empresa = [f"«{m['label']}»" for m in motivos if m["responsableEnvio"] == "empresa"]
    if paga_empresa:
        quien_paga = (
            "El envío de regreso lo paga quien devuelve. La excepción es cuando el problema es "
            "nuestro: en " + " y ".join(paga_empresa) + " lo pagamos nosotros. Guarda tu ticket de "
            "paquetería y te lo reembolsamos junto con el producto."
        )
    else:
        quien_paga = "El envío de regreso lo paga quien devuelve."

    return [
        {"clave": "que", "titulo": "Qué puedes devolver",
         "texto": ("El pedido completo o solo algunas líneas, con la cantidad que elijas. "
                   "No tienes que regresar todo para que te devolvamos lo que salió mal.")},
        {"clave": "plazo", "titulo": "En qué plazo",
         "texto": f"El plazo se cuenta desde que el pedido se marca entregado. {plazos}"},
        {"clave": "evidencia", "titulo": "Qué evidencia te pedimos",
         "texto": f"Depende del motivo. {evidencias}"},
        {"clave": "envio", "titulo": "Quién paga el envío de regreso",
         "texto": quien_paga},
        {"clave": "direccion", "titulo": "A dónde mandas el paquete",
         "texto": (f"A {direccion}. Escribe el folio de tu solicitud en el paquete "
                   "para que lo identifiquemos al recibirlo.")},
        {"clave": "reembolso", "titulo": "Cuánto tarda y cómo te llega el dinero",
         "texto": (f"Revisamos el paquete en {dias_inspeccion} días hábiles desde que llega. "
                   f"Si todo está bien, te reembolsamos al {metodo} en {dias_reembolso} días hábiles. "
                   "Si devuelves el pedido completo y el motivo fue nuestro, también te "
                   "reembolsamos el envío original.")},
    ]


def politica_devolucion(cfg: Optional[dict] = None) -> dict:
    """La política completa, tal como viaja a pantalla y a correo."""
    cfg = cfg if cfg is not None else utils._load_app_config()
    returns = (cfg.get("returns") or {})
    return {
        "motivos": motivos_publicados(cfg),
        "pasos": texto_politica(cfg),
        "direccionDevolucion": direccion_devolucion(cfg),
        "inspeccionDiasHabiles": str(returns.get("inspeccionDiasHabiles") or "2"),
        "refundMethod": str(returns.get("refundMethod") or "mismo medio de pago"),
        "refundBusinessDays": str(returns.get("refundBusinessDays") or "3 a 5"),
    }


def texto_politica_plano(cfg: Optional[dict] = None) -> str:
    """Los seis puntos en una sola cadena, para el cuerpo de texto de un correo."""
    return "\n".join(f"{i}. {p['titulo']}: {p['texto']}" for i, p in enumerate(texto_politica(cfg), 1))


# ---------------------------------------------------------------------------
# Endpoint público
# ---------------------------------------------------------------------------

def handle_ayuda() -> dict:
    """GET /catalog/ayuda — todo lo que necesita quien ya pagó y no sabe a quién escribirle."""
    cfg = utils._load_app_config()
    return utils._json_response(200, {
        "contacto": contacto(cfg),
        "sucursales": sucursales(),
        "devoluciones": politica_devolucion(cfg),
    })


#: Se engancha en `catalog_lambda` (tabla declarativa) con una sola línea.
RUTAS_CATALOGO = [
    Ruta("GET", "catalog/ayuda", publica=True,
         descripcion="Contacto, sucursales y política de devolución, sin sesión",
         handler=lambda p: handle_ayuda()),
]
