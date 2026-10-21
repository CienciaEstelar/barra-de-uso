import pytest

from barra_de_uso.formato import abreviar, tabla_tokens


@pytest.mark.parametrize("n, esperado", [
    (0, "0"),
    (999, "999"),
    (1000, "1.0k"),
    (12_400, "12.4k"),
    (340_149, "340.1k"),
    (999_949, "999.9k"),
    (999_950, "1.0M"),
    (1_000_000, "1.0M"),
    (1_234_567, "1.2M"),
    (12_350_000, "12.4M"),
])
def test_abreviar(n, esperado):
    assert abreviar(n) == esperado


def test_tabla_alinea_columnas_y_ordena_por_total():
    totales = {
        "glm-fast": {"in": 4_100, "cr": 90_300, "cw": 0, "out": 3_000},
        "kimi-k3": {"in": 12_400, "cr": 340_100, "cw": 0, "out": 8_200},
    }
    assert tabla_tokens(totales) == [
        "kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k",
        "glm-fast  in 4.1k  · cr 90.3k  · cw 0 · out 3.0k",
    ]


def test_tabla_un_modelo():
    totales = {"deepseek-flash": {"in": 781, "cr": 67_456, "cw": 0, "out": 299}}
    assert tabla_tokens(totales) == ["deepseek-flash  in 781 · cr 67.5k · cw 0 · out 299"]


def test_tabla_empate_ordena_alfabetico():
    totales = {
        "b-modelo": {"in": 1, "cr": 0, "cw": 0, "out": 0},
        "a-modelo": {"in": 1, "cr": 0, "cw": 0, "out": 0},
    }
    assert [linea.split()[0] for linea in tabla_tokens(totales)] == ["a-modelo", "b-modelo"]
