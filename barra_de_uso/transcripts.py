"""Lectura incremental de los transcripts de una sesión y suma de tokens por modelo."""

from __future__ import annotations

import json
from pathlib import Path

# Claves cortas usadas en el caché y en la tabla: entrada, caché lectura, caché escritura, salida.
CAMPOS = ("in", "cr", "cw", "out")
CAMPOS_USAGE = {
    "in": "input_tokens",
    "cr": "cache_read_input_tokens",
    "cw": "cache_creation_input_tokens",
    "out": "output_tokens",
}
MODELO_SINTETICO = "<synthetic>"


def archivos_de_sesion(transcript_path: Path) -> list[Path]:
    """Transcript principal más los de subagentes, buscados recursivamente."""
    if not transcript_path.is_file():
        return []
    archivos = [transcript_path]
    carpeta_subagentes = transcript_path.with_suffix("") / "subagents"
    if carpeta_subagentes.is_dir():
        archivos.extend(sorted(carpeta_subagentes.rglob("agent-*.jsonl")))
    return archivos


def _entero(valor: object) -> int:
    if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0:
        return valor
    return 0


def suma_uso(uso: dict) -> int:
    return sum(uso[campo] for campo in CAMPOS)


def uso_de_entrada(entrada: dict) -> tuple[str, dict] | None:
    """Devuelve (message.id, uso) si la entrada es una respuesta válida; si no, None."""
    if entrada.get("type") != "assistant" or entrada.get("isApiErrorMessage") is True:
        return None
    mensaje = entrada.get("message")
    if not isinstance(mensaje, dict):
        return None
    id_mensaje = mensaje.get("id")
    modelo = mensaje.get("model")
    usage = mensaje.get("usage")
    if not isinstance(id_mensaje, str) or not id_mensaje:
        return None
    if not isinstance(modelo, str) or not modelo or modelo == MODELO_SINTETICO:
        return None
    if not isinstance(usage, dict):
        return None
    uso = {"modelo": modelo}
    for campo, clave in CAMPOS_USAGE.items():
        uso[campo] = _entero(usage.get(clave))
    return id_mensaje, uso


def fusionar(mensajes: dict, id_mensaje: str, uso: dict) -> None:
    """Un mismo message.id aparece repetido; se conserva la repetición con mayor uso total."""
    previo = mensajes.get(id_mensaje)
    if previo is None or suma_uso(uso) > suma_uso(previo):
        mensajes[id_mensaje] = uso


def leer_desde(ruta: Path, offset: int) -> tuple[list[dict], int]:
    """Lee las líneas completas desde `offset`. Devuelve las entradas y el nuevo offset."""
    with ruta.open("rb") as archivo:
        archivo.seek(offset)
        datos = archivo.read()
    corte = datos.rfind(b"\n")
    if corte == -1:
        # Nada completo todavía: la línea a medio escribir se relee en el próximo refresco.
        return [], offset
    entradas = []
    for linea in datos[:corte].split(b"\n"):
        if not linea.strip():
            continue
        try:
            objeto = json.loads(linea)
        except ValueError:  # incluye JSONDecodeError y UnicodeDecodeError
            continue
        if isinstance(objeto, dict):
            entradas.append(objeto)
    return entradas, offset + corte + 1


def actualizar_estado(estado: dict, archivos: list[Path]) -> None:
    """Procesa lo nuevo de cada archivo y lo fusiona en estado['mensajes']."""
    for ruta in archivos:
        try:
            info = ruta.stat()
        except OSError:
            continue
        clave = str(ruta)
        previo = estado["archivos"].get(clave)
        offset = 0
        if previo is not None and previo["inodo"] == info.st_ino and previo["offset"] <= info.st_size:
            offset = previo["offset"]
        try:
            entradas, nuevo_offset = leer_desde(ruta, offset)
        except OSError:
            continue
        for entrada in entradas:
            resultado = uso_de_entrada(entrada)
            if resultado is not None:
                fusionar(estado["mensajes"], *resultado)
        estado["archivos"][clave] = {"inodo": info.st_ino, "offset": nuevo_offset}


def totales_por_modelo(mensajes: dict) -> dict[str, dict[str, int]]:
    totales: dict[str, dict[str, int]] = {}
    for uso in mensajes.values():
        total = totales.setdefault(uso["modelo"], dict.fromkeys(CAMPOS, 0))
        for campo in CAMPOS:
            total[campo] += uso[campo]
    return totales
