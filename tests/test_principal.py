"""End to end: ejecuta barra.py como lo haría Claude Code."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from tests.conftest import agregar_jsonl, escribir_jsonl, respuesta, sin_ansi

BARRA = Path(__file__).resolve().parent.parent / "barra.py"


def ejecutar(stdin: str, cache_dir: Path, base_url: str | None = None, colores: bool = False) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_BASE_URL", "NO_COLOR")}
    entorno["BARRA_DE_USO_CACHE_DIR"] = str(cache_dir)
    entorno["LC_ALL"] = "C"  # el locale no debe romper "·", "↻", "▲" ni "▼"
    if not colores:
        entorno["NO_COLOR"] = "1"
    if base_url is not None:
        entorno["ANTHROPIC_BASE_URL"] = base_url
    return subprocess.run(
        [sys.executable, str(BARRA)],
        input=stdin.encode("utf-8"),
        capture_output=True,
        env=entorno,
        timeout=10,
        check=False,
    )


def test_stdin_vacio(tmp_path):
    resultado = ejecutar("", tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "barra-de-uso\n"
    assert resultado.stderr == b""


def test_json_invalido(tmp_path):
    resultado = ejecutar("{roto", tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "barra-de-uso\n"


def test_modo_plan(tmp_path):
    payload = {
        "model": {"display_name": "Opus 5.5"},
        "rate_limits": {"five_hour": {"used_percentage": 42}, "seven_day": {"used_percentage": 18}},
    }
    resultado = ejecutar(json.dumps(payload), tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "Opus 5.5 · 5h 42% · sem 18%\n"


def test_modo_plan_con_contexto(tmp_path):
    payload = {"model": {"display_name": "Opus 5.5"}, "context_window": {"used_percentage": 11}}
    resultado = ejecutar(json.dumps(payload), tmp_path)
    assert resultado.stdout.decode("utf-8") == "Opus 5.5 · ctx 11% · 5h -- · sem --\n"


def test_modo_plan_con_colores(tmp_path):
    payload = {
        "model": {"display_name": "Opus 5.5"},
        "rate_limits": {"five_hour": {"used_percentage": 85}, "seven_day": {"used_percentage": 18}},
    }
    resultado = ejecutar(json.dumps(payload), tmp_path, colores=True)
    salida = resultado.stdout.decode("utf-8")
    assert salida.startswith("\x1b[0m")  # anula el atenuado de Claude Code
    assert "\x1b[31m85%" in salida
    assert sin_ansi(salida) == "Opus 5.5 · 5h 85% · sem 18%\n"


def test_memoria_entre_sesiones(tmp_path):
    futuro = time.time() + 3600
    con_datos = {
        "model": {"display_name": "Opus 5.5"},
        "rate_limits": {
            "five_hour": {"used_percentage": 42, "resets_at": futuro},
            "seven_day": {"used_percentage": 18, "resets_at": futuro},
        },
    }
    ejecutar(json.dumps(con_datos), tmp_path)
    assert (tmp_path / "ultimo-plan.json").is_file()

    sesion_nueva = {"model": {"display_name": "Opus 5.5"}}  # primer refresco: aún sin rate_limits
    salida = ejecutar(json.dumps(sesion_nueva), tmp_path).stdout.decode("utf-8")
    assert "5h ~42%" in salida
    assert "sem ~18%" in salida
    assert "▲" not in salida and "▼" not in salida  # lo estimado no lleva ritmo


def test_modo_otro_proveedor_con_subagente_e_incremental(tmp_path):
    transcript = escribir_jsonl(tmp_path / "proyecto" / "sesion1.jsonl", [respuesta("m1", "kimi-k3", 12_400, 340_100, 0, 8_200)] * 3)
    escribir_jsonl(
        tmp_path / "proyecto" / "sesion1" / "subagents" / "agent-a.jsonl",
        [respuesta("s1", "glm-fast", 4_100, 90_300, 0, 3_000)],
    )
    payload = {"model": {"display_name": "kimi-k3"}, "session_id": "sesion1", "transcript_path": str(transcript)}
    cache_dir = tmp_path / "cache"

    resultado = ejecutar(json.dumps(payload), cache_dir, base_url="http://localhost:4000")
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == (
        "kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k\n"
        "glm-fast  in 4.1k  · cr 90.3k  · cw 0 · out 3.0k\n"
    )
    assert (cache_dir / "sesion1.json").is_file()

    agregar_jsonl(transcript, [respuesta("m2", "kimi-k3", 100, 0, 0, 0)])
    segundo = ejecutar(json.dumps(payload), cache_dir, base_url="http://localhost:4000")
    assert segundo.stdout.decode("utf-8").splitlines()[0] == "kimi-k3   in 12.5k · cr 340.1k · cw 0 · out 8.2k"

    con_colores = ejecutar(json.dumps(payload), cache_dir, base_url="http://localhost:4000", colores=True)
    lineas = con_colores.stdout.decode("utf-8").splitlines()
    assert all(linea.startswith("\x1b[0m") for linea in lineas)
    assert sin_ansi(lineas[0]) == "kimi-k3   in 12.5k · cr 340.1k · cw 0 · out 8.2k"


def test_otro_proveedor_sin_transcript_muestra_modelo(tmp_path):
    payload = {"model": {"display_name": "deepseek-flash"}, "transcript_path": str(tmp_path / "no.jsonl")}
    resultado = ejecutar(json.dumps(payload), tmp_path, base_url="https://api.deepseek.com/anthropic")
    assert resultado.stdout.decode("utf-8") == "deepseek-flash\n"
