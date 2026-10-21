import pytest

from barra_de_uso.color import AMARILLO, NEGRITA, REINICIO, ROJO, VERDE, color_nivel, colores_activos, pintar


def test_pintar_inactivo_devuelve_el_texto_tal_cual():
    assert pintar("42%", ROJO, activo=False) == "42%"


def test_pintar_activo_envuelve_y_reinicia():
    assert pintar("42%", ROJO, activo=True) == "\x1b[31m42%" + REINICIO


def test_pintar_varios_codigos():
    assert pintar("kimi", NEGRITA, VERDE, activo=True) == "\x1b[1;32mkimi" + REINICIO


def test_pintar_sin_codigos_o_texto_vacio_no_agrega_nada():
    assert pintar("=", activo=True) == "="
    assert pintar("", ROJO, activo=True) == ""


@pytest.mark.parametrize("porcentaje, esperado", [
    (0, VERDE),
    (49.9, VERDE),
    (50, AMARILLO),
    (79.9, AMARILLO),
    (80, ROJO),
    (100, ROJO),
])
def test_color_nivel(porcentaje, esperado):
    assert color_nivel(porcentaje) == esperado


def test_no_color_desactiva_colores():
    assert colores_activos({}) is True
    assert colores_activos({"NO_COLOR": ""}) is True  # vacía no cuenta, según no-color.org
    assert colores_activos({"NO_COLOR": "1"}) is False
