"""Ayudantes para armar transcripts SINTÉTICOS. Nunca usar datos reales: el repo es público."""

import json
import re
from pathlib import Path

import pytest


def respuesta(id_mensaje, modelo, entrada=0, cache_lectura=0, cache_escritura=0, salida=0, **extra):
    """Una línea 'assistant' con la misma forma que escribe Claude Code."""
    linea = {
        "type": "assistant",
        "message": {
            "id": id_mensaje,
            "model": modelo,
            "usage": {
                "input_tokens": entrada,
                "cache_read_input_tokens": cache_lectura,
                "cache_creation_input_tokens": cache_escritura,
                "output_tokens": salida,
            },
        },
    }
    linea.update(extra)
    return linea


def escribir_jsonl(ruta: Path, lineas, final_incompleto: str = "") -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = "".join(json.dumps(linea) + "\n" for linea in lineas) + final_incompleto
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def agregar_jsonl(ruta: Path, lineas) -> None:
    with ruta.open("a", encoding="utf-8") as archivo:
        for linea in lineas:
            archivo.write(json.dumps(linea) + "\n")


def sin_ansi(texto: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", texto)


@pytest.fixture
def cache_temporal(tmp_path, monkeypatch):
    carpeta = tmp_path / "cache"
    monkeypatch.setenv("BARRA_DE_USO_CACHE_DIR", str(carpeta))
    return carpeta
