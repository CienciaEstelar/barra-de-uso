import json
import os

from barra_de_uso.entrada import Payload, Ventana
from barra_de_uso.memoria import (
    VERSION,
    cargar_memoria,
    completar_con_memoria,
    guardar_memoria,
    ruta_memoria,
)

AHORA = 1_800_000_000.0
FUTURO = AHORA + 3600
PASADO = AHORA - 60


def payload(cinco_horas=None, semanal=None):
    return Payload("Opus 5.5", None, None, cinco_horas, semanal)


def test_ruta_memoria_usa_carpeta_de_cache(cache_temporal):
    assert ruta_memoria() == cache_temporal / "ultimo-plan.json"


def test_guardar_y_cargar_ida_y_vuelta(cache_temporal):
    ruta = ruta_memoria()
    guardar_memoria(ruta, payload(Ventana(42, FUTURO), Ventana(18, FUTURO + 99)), {})
    assert cargar_memoria(ruta) == {"cinco_horas": Ventana(42.0, FUTURO), "semanal": Ventana(18.0, FUTURO + 99)}


def test_no_guarda_ventana_sin_reset_ni_estimada(cache_temporal):
    ruta = ruta_memoria()
    guardar_memoria(ruta, payload(Ventana(42, None), Ventana(18, FUTURO, estimada=True)), {})
    assert not ruta.exists()


def test_conserva_la_ventana_que_no_viene(cache_temporal):
    ruta = ruta_memoria()
    previa = {"semanal": Ventana(18.0, FUTURO)}
    guardar_memoria(ruta, payload(cinco_horas=Ventana(42, FUTURO)), previa)
    assert cargar_memoria(ruta) == {"cinco_horas": Ventana(42.0, FUTURO), "semanal": Ventana(18.0, FUTURO)}


def test_no_reescribe_si_nada_cambio(cache_temporal):
    ruta = ruta_memoria()
    guardar_memoria(ruta, payload(Ventana(42, FUTURO)), {})
    os.utime(ruta, ns=(1_000_000_000, 1_000_000_000))  # marca antigua conocida
    guardar_memoria(ruta, payload(Ventana(42, FUTURO)), cargar_memoria(ruta))
    assert ruta.stat().st_mtime_ns == 1_000_000_000


def test_memoria_corrupta_o_de_otra_version_queda_vacia(cache_temporal):
    cache_temporal.mkdir()
    ruta = ruta_memoria()
    ruta.write_text("{roto", encoding="utf-8")
    assert cargar_memoria(ruta) == {}
    ruta.write_text(json.dumps({"version": VERSION + 1, "cinco_horas": {"porcentaje": 1, "reset_epoch": FUTURO}}), encoding="utf-8")
    assert cargar_memoria(ruta) == {}
    ruta.write_text(json.dumps({"version": VERSION, "cinco_horas": {"porcentaje": "x", "reset_epoch": FUTURO}}), encoding="utf-8")
    assert cargar_memoria(ruta) == {}


def test_completar_rellena_lo_que_falta_como_estimado():
    memoria = {"cinco_horas": Ventana(42.0, FUTURO), "semanal": Ventana(18.0, FUTURO)}
    resultado = completar_con_memoria(payload(), memoria, AHORA)
    assert resultado.cinco_horas == Ventana(42.0, FUTURO, estimada=True)
    assert resultado.semanal == Ventana(18.0, FUTURO, estimada=True)


def test_completar_no_pisa_el_dato_real():
    memoria = {"cinco_horas": Ventana(10.0, FUTURO)}
    real = Ventana(42, FUTURO)
    assert completar_con_memoria(payload(cinco_horas=real), memoria, AHORA).cinco_horas == real


def test_completar_ignora_memoria_vencida():
    memoria = {"cinco_horas": Ventana(42.0, PASADO)}
    assert completar_con_memoria(payload(), memoria, AHORA).cinco_horas is None


def test_completar_rellena_ventana_sin_porcentaje():
    memoria = {"semanal": Ventana(18.0, FUTURO)}
    resultado = completar_con_memoria(payload(semanal=Ventana(None, FUTURO)), memoria, AHORA)
    assert resultado.semanal == Ventana(18.0, FUTURO, estimada=True)
