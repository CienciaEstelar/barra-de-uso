import json

import pytest

from barra_de_uso.entrada import NOMBRE_RESPALDO, Ventana, parsear_payload


def test_payload_completo():
    texto = json.dumps({
        "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
        "session_id": "abc-123",
        "transcript_path": "/tmp/x.jsonl",
        "rate_limits": {
            "five_hour": {"used_percentage": 42, "resets_at": 1774020000},
            "seven_day": {"used_percentage": 15.5, "resets_at": "1774540000"},
        },
    })
    payload = parsear_payload(texto)
    assert payload.modelo == "Opus 5.5"
    assert payload.session_id == "abc-123"
    assert payload.transcript_path == "/tmp/x.jsonl"
    assert payload.cinco_horas == Ventana(42.0, 1774020000.0)
    assert payload.semanal == Ventana(15.5, 1774540000.0)


def test_usa_id_si_falta_display_name():
    assert parsear_payload('{"model": {"id": "deepseek-flash"}}').modelo == "deepseek-flash"


def test_objeto_vacio_usa_nombre_de_respaldo():
    payload = parsear_payload("{}")
    assert payload.modelo == NOMBRE_RESPALDO
    assert payload.session_id is None
    assert payload.transcript_path is None
    assert payload.cinco_horas is None
    assert payload.semanal is None


def test_rate_limits_null():
    payload = parsear_payload('{"rate_limits": null}')
    assert payload.cinco_horas is None
    assert payload.semanal is None


def test_valores_invalidos_quedan_en_none():
    texto = json.dumps({"rate_limits": {"five_hour": {"used_percentage": "nada", "resets_at": True}}})
    assert parsear_payload(texto).cinco_horas == Ventana(None, None)


def test_nan_queda_en_none():
    texto = json.dumps({"rate_limits": {"five_hour": {"used_percentage": "nan"}}})
    assert parsear_payload(texto).cinco_horas == Ventana(None, None)


def test_json_invalido_lanza_value_error():
    with pytest.raises(ValueError):
        parsear_payload("esto no es json")


def test_json_que_no_es_objeto_lanza_value_error():
    with pytest.raises(ValueError):
        parsear_payload("[1, 2]")


def test_contexto_se_lee_de_context_window():
    texto = json.dumps({"context_window": {"used_percentage": 11, "context_window_size": 1000000}})
    assert parsear_payload(texto).contexto == 11.0


def test_contexto_null_en_el_primer_refresco():
    assert parsear_payload('{"context_window": {"used_percentage": null}}').contexto is None
    assert parsear_payload("{}").contexto is None


def test_ventana_del_payload_nunca_es_estimada():
    texto = json.dumps({"rate_limits": {"five_hour": {"used_percentage": 42, "resets_at": 1}}})
    assert parsear_payload(texto).cinco_horas.estimada is False
