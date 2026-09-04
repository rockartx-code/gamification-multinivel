"""Vocabulario único de estados (paquete G, propuesta 25).

Julio contó cuatro nombres para el mismo estado en cuatro pantallas: "Pago
registrado", "Pagada", "Pendiente/Pagada/Enviada/Entregada" y `paid` crudo.
*"«Estado: paid», así, en inglés, es el cuarto nombre distinto que le veo al
mismo estado en cuatro pantallas"* (`julio-2027-03-02.md`).

Alma, en el corte de caja: *"`mixed` es exactamente el número que vine a
cuadrar y la pantalla me lo esconde detrás de una palabra en inglés"*.

Ernesto, con la fecha: *"«Creada: 2027-03-02T11:18:04Z»: ¿qué es esa T y esa Z?"*.

Esta prueba fija la tabla y su gemela del frontend: si alguien añade un quinto
nombre en cualquiera de las dos, aquí se cae.
"""
import re
from pathlib import Path

import pytest

import vocabulario

MODELO_TS = (Path(__file__).resolve().parents[3]
             / "gamificacion-multinivel-f" / "src" / "app" / "models" / "vocabulario.model.ts")


def test_los_estados_se_dicen_en_espanol_y_sin_genero():
    assert vocabulario.estado_pedido("paid") == "Pagado"
    assert vocabulario.estado_pedido("delivered") == "Entregado"
    assert vocabulario.estado_pedido("cancelled") == "Cancelado"
    assert vocabulario.estado_pedido("pending") == "Pendiente de pago"
    assert vocabulario.estado_pedido("en_devolucion") == "Devolución en curso"
    # Los estados del pedido concuerdan con "el pedido", nunca con la persona:
    # al señor de 63 años el sistema le dijo "socia" cinco veces, y "Pagada"
    # en la fila de su pedido es el mismo defecto visto por otro lado. Las
    # únicas palabras en femenino permitidas son las que concuerdan con
    # "devolución", que es una cosa y no quien compra.
    for texto in vocabulario.ESTADOS_PEDIDO.values():
        if texto.startswith("Devolución "):
            continue
        assert not texto.endswith("ada") and not texto.endswith("ida"), texto


def test_recoger_en_sucursal_tiene_su_propio_matiz():
    """Paulina llevaba 21 días sin saber en qué tienda estaba su pedido."""
    assert vocabulario.estado_pedido("paid", "pickup") == "Listo para recoger"
    assert vocabulario.estado_pedido("delivered", "pickup") == "Entregado en sucursal"
    # El envío a domicilio no cambia de nombre.
    assert vocabulario.estado_pedido("paid", "delivery") == "Pagado"
    assert vocabulario.estado_pedido("shipped", "pickup") == "Enviado"


def test_los_alias_historicos_caen_en_el_mismo_texto():
    assert vocabulario.estado_pedido("canceled") == "Cancelado"
    assert vocabulario.estado_pedido("CANCELLED") == "Cancelado"
    assert vocabulario.estado_pedido("in_return") == "Devolución en curso"


def test_un_estado_desconocido_se_devuelve_crudo_y_no_se_inventa_un_quinto_nombre():
    assert vocabulario.estado_pedido("marciano") == "marciano"
    assert vocabulario.estado_pedido("") == ""
    assert vocabulario.estado_pedido(None) == ""


def test_mixed_se_dice_completo_y_con_su_desglose():
    """La emoción de intensidad 5 de Alma fue por esta palabra."""
    assert vocabulario.metodo_pago("mixed") == "Mixto (efectivo + tarjeta)"
    assert vocabulario.metodo_pago("mixed", 500, 260) == (
        "Mixto (efectivo + tarjeta) · $500.00 en efectivo · $260.00 con tarjeta")
    assert vocabulario.metodo_pago("cash") == "Efectivo"
    assert vocabulario.metodo_pago("card") == "Tarjeta"
    assert vocabulario.metodo_pago("branch") == "Pago en sucursal"


def test_las_fechas_se_escriben_como_las_escribe_la_gente():
    assert vocabulario.fecha_larga("2027-03-02T11:18:04Z") == "2 de marzo de 2027, 11:18"
    assert vocabulario.fecha_larga("2027-03-02T11:18:04Z", con_hora=False) == "2 de marzo de 2027"
    assert vocabulario.mes_largo("2027-03") == "marzo de 2027"
    assert vocabulario.mes_largo("2027-13") == "2027-13"
    assert vocabulario.fecha_larga("") == ""


def test_el_modelo_del_frontend_dice_exactamente_lo_mismo():
    """Dos tablas con textos distintos son otra vez cuatro nombres del mismo estado."""
    assert MODELO_TS.exists(), f"falta el gemelo del frontend en {MODELO_TS}"
    fuente = MODELO_TS.read_text(encoding="utf-8")
    for clave, texto in vocabulario.ESTADOS_PEDIDO.items():
        assert re.search(rf"\b{clave}: '{re.escape(texto)}'", fuente), f"{clave} difiere del backend"
    for clave, texto in vocabulario.METODOS_PAGO.items():
        assert re.search(rf"\b{clave}: '{re.escape(texto)}'", fuente), f"{clave} difiere del backend"
    for clave, texto in vocabulario.ESTADOS_PEDIDO_PICKUP.items():
        assert f"'{texto}'" in fuente, f"falta el matiz de recolección {texto}"
