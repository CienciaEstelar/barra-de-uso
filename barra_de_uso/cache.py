"""Estado incremental por sesión en ~/.cache/barra-de-uso/<session_id>.json."""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path

from barra_de_uso.transcripts import CAMPOS

VERSION = 1
# session_id va al nombre de archivo: solo se aceptan caracteres seguros.
PATRON_SESSION_ID = re.compile(r"[A-Za-z0-9_-]+")


def carpeta_cache() -> Path:
    personalizada = os.environ.get("BARRA_DE_USO_CACHE_DIR")
    if personalizada:
        return Path(personalizada)
    return Path.home() / ".cache" / "barra-de-uso"


def ruta_cache(session_id: str | None) -> Path | None:
    if session_id is None or not PATRON_SESSION_ID.fullmatch(session_id):
        return None
    return carpeta_cache() / f"{session_id}.json"


def estado_vacio() -> dict:
    return {"version": VERSION, "archivos": {}, "mensajes": {}}


def _es_valido(datos: object) -> bool:
    if not isinstance(datos, dict) or datos.get("version") != VERSION:
        return False
    archivos = datos.get("archivos")
    mensajes = datos.get("mensajes")
    if not isinstance(archivos, dict) or not isinstance(mensajes, dict):
        return False
    for archivo in archivos.values():
        if not isinstance(archivo, dict):
            return False
        if not isinstance(archivo.get("inodo"), int) or not isinstance(archivo.get("offset"), int):
            return False
    for uso in mensajes.values():
        if not isinstance(uso, dict) or not isinstance(uso.get("modelo"), str):
            return False
        if not all(isinstance(uso.get(campo), int) for campo in CAMPOS):
            return False
    return True


def cargar(ruta: Path) -> dict:
    """Caché ilegible, corrupto o de otra versión: se parte de cero."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return estado_vacio()
    return datos if _es_valido(datos) else estado_vacio()


def guardar(ruta: Path, estado: dict) -> None:
    """Escritura atómica. Si falla, se ignora: la barra se imprime igual."""
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp-", suffix=".json")
    except OSError:
        return
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(estado, archivo)
        os.replace(temporal, ruta)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(temporal)
