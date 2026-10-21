from datetime import datetime, timezone

from barra_de_uso.entrada import Payload, Ventana
from barra_de_uso.plan import formatear_reset, formatear_ventana, linea_plan


def epoch_utc(*partes):
    return datetime(*partes, tzinfo=timezone.utc).timestamp()


# Miércoles 21-oct-2026 12:00 hora de Chile (UTC-3 en horario de verano).
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)


def test_reset_hoy_muestra_solo_hora():
    # 21-oct 19:30 UTC = 16:30 en Chile, mismo día.
    assert formatear_reset(epoch_utc(2026, 10, 21, 19, 30), AHORA) == "16:30"


def test_reset_martes_04_00_horario_de_verano():
    # 27-oct-2026 es martes; Chile en UTC-3, así que 04:00 local = 07:00 UTC.
    assert formatear_reset(epoch_utc(2026, 10, 27, 7, 0), AHORA) == "mar 04:00"


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


def test_ventana_con_porcentaje_fraccional():
    assert formatear_ventana("5h", Ventana(23.6, None), AHORA) == "5h 24%"


def test_ventana_sin_porcentaje():
    assert formatear_ventana("sem", Ventana(None, epoch_utc(2026, 10, 27, 7, 0)), AHORA) == "sem --"


def test_ventana_ausente():
    assert formatear_ventana("5h", None, AHORA) == "5h --"


def test_linea_plan_completa():
    payload = Payload(
        modelo="Opus 5.5",
        session_id=None,
        transcript_path=None,
        cinco_horas=Ventana(42, epoch_utc(2026, 10, 21, 19, 30)),
        semanal=Ventana(18, epoch_utc(2026, 10, 27, 7, 0)),
    )
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h 42% ↻ 16:30 · sem 18% ↻ mar 04:00"


def test_linea_plan_sin_rate_limits():
    payload = Payload("Opus 5.5", None, None, None, None)
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h -- · sem --"
