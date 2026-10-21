from datetime import datetime, timezone

import pytest

from barra_de_uso.entrada import Payload, Ventana
from barra_de_uso.plan import flecha_ritmo, formatear_contexto, formatear_reset, formatear_ventana, linea_plan
from tests.conftest import sin_ansi


def epoch_utc(*partes):
    return datetime(*partes, tzinfo=timezone.utc).timestamp()


# Miércoles 21-oct-2026 12:00 hora de Chile (UTC-3 en horario de verano).
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)
RESET_5H = epoch_utc(2026, 10, 21, 19, 30)  # 16:30 en Chile: quedan 4,5 h de 5, transcurrió el 10 %
RESET_SEM = epoch_utc(2026, 10, 27, 7, 0)  # martes 04:00 en Chile: quedan 136 h de 168, transcurrió el 19 %


def test_reset_hoy_muestra_solo_hora():
    assert formatear_reset(RESET_5H, AHORA) == "16:30"


def test_reset_martes_04_00_horario_de_verano():
    # 27-oct-2026 es martes; Chile en UTC-3, así que 04:00 local = 07:00 UTC.
    assert formatear_reset(RESET_SEM, AHORA) == "mar 04:00"


def test_reset_martes_04_00_horario_de_invierno():
    # 16-jun-2026 es martes; Chile en UTC-4, así que 04:00 local = 08:00 UTC.
    ahora = datetime(2026, 6, 12, 15, 0, tzinfo=timezone.utc)
    assert formatear_reset(epoch_utc(2026, 6, 16, 8, 0), ahora) == "mar 04:00"


def test_dia_con_tilde():
    # 24-oct-2026 es sábado.
    assert formatear_reset(epoch_utc(2026, 10, 24, 15, 0), AHORA) == "sáb 12:00"


def test_fecha_se_compara_en_hora_de_chile_no_utc():
    # 22-oct 02:00 UTC todavía es 21-oct 23:00 en Chile: cuenta como hoy.
    assert formatear_reset(epoch_utc(2026, 10, 22, 2, 0), AHORA) == "23:00"


# Ventana de 100 s con 50 s restantes: transcurrió el 50 %.
@pytest.mark.parametrize("porcentaje, esperado", [
    (60, "▲"),
    (55.1, "▲"),
    (55, "="),  # justo en el margen de 5 puntos
    (50, "="),
    (45, "="),
    (44.9, "▼"),
    (10, "▼"),
])
def test_flecha_ritmo(porcentaje, esperado):
    assert flecha_ritmo(porcentaje, reset_epoch=1050, duracion=100, ahora_epoch=1000) == esperado


def test_flecha_ritmo_reset_vencido_cuenta_ventana_completa():
    assert flecha_ritmo(90, reset_epoch=900, duracion=100, ahora_epoch=1000) == "▼"


def test_flecha_ritmo_reset_mas_lejos_que_la_ventana_cuenta_cero():
    assert flecha_ritmo(3, reset_epoch=5000, duracion=100, ahora_epoch=1000) == "="
    assert flecha_ritmo(6, reset_epoch=5000, duracion=100, ahora_epoch=1000) == "▲"


def test_ventana_con_porcentaje_fraccional_sin_reset_no_lleva_flecha():
    assert formatear_ventana("5h", Ventana(23.6, None), AHORA) == "5h 24%"


def test_ventana_con_reset_lleva_flecha():
    assert formatear_ventana("5h", Ventana(42, RESET_5H), AHORA) == "5h 42% ▲ ↻ 16:30"


def test_ventana_sin_porcentaje():
    assert formatear_ventana("sem", Ventana(None, RESET_SEM), AHORA) == "sem --"


def test_ventana_ausente():
    assert formatear_ventana("5h", None, AHORA) == "5h --"


def test_ventana_estimada_lleva_tilde_y_no_lleva_flecha():
    assert formatear_ventana("5h", Ventana(42, RESET_5H, estimada=True), AHORA) == "5h ~42% ↻ 16:30"
    assert formatear_ventana("5h", Ventana(42, None, estimada=True), AHORA) == "5h ~42%"


def test_ventana_estimada_con_colores_va_tenue_completa():
    texto = formatear_ventana("5h", Ventana(42, RESET_5H, estimada=True), AHORA, colores=True)
    assert texto == "\x1b[2m5h ~42% ↻ 16:30\x1b[0m"


def test_contexto():
    assert formatear_contexto(11.4) == "ctx 11%"
    assert formatear_contexto(85, colores=True) == "ctx \x1b[31m85%\x1b[0m"


def test_linea_plan_completa():
    payload = Payload("Opus 5.5", None, None, Ventana(42, RESET_5H), Ventana(18, RESET_SEM))
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h 42% ▲ ↻ 16:30 · sem 18% = ↻ mar 04:00"


def test_linea_plan_con_contexto():
    payload = Payload("Opus 5.5", None, None, None, None, contexto=11)
    assert linea_plan(payload, AHORA) == "Opus 5.5 · ctx 11% · 5h -- · sem --"


def test_linea_plan_sin_rate_limits():
    payload = Payload("Opus 5.5", None, None, None, None)
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h -- · sem --"


def test_linea_plan_con_colores_es_la_misma_sin_ansi():
    payload = Payload("Opus 5.5", None, None, Ventana(42, RESET_5H), Ventana(18, RESET_SEM), contexto=85)
    plano = linea_plan(payload, AHORA)
    coloreado = linea_plan(payload, AHORA, colores=True)
    assert sin_ansi(coloreado) == plano
    assert "\x1b[32m42%" in coloreado  # nivel bajo: verde
    assert "\x1b[31m▲" in coloreado  # adelantado: rojo
    assert "\x1b[31m85%" in coloreado  # contexto alto: rojo
    assert "\x1b[2m · \x1b[0m" in coloreado  # separadores tenues
