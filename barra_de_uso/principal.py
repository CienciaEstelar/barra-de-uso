"""Punto de entrada: lee stdin, decide el modo e imprime la barra. Nunca falla hacia afuera."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from barra_de_uso.cache import cargar, estado_vacio, guardar, ruta_cache
from barra_de_uso.color import REINICIO, colores_activos
from barra_de_uso.entrada import NOMBRE_RESPALDO, Payload, parsear_payload
from barra_de_uso.formato import tabla_tokens
from barra_de_uso.memoria import cargar_memoria, completar_con_memoria, guardar_memoria, ruta_memoria
from barra_de_uso.modo import es_modo_plan
from barra_de_uso.plan import linea_plan
from barra_de_uso.transcripts import actualizar_estado, archivos_de_sesion, totales_por_modelo


def lineas_otro_proveedor(payload: Payload, colores: bool = False) -> list[str]:
    if payload.transcript_path is None:
        return [payload.modelo]
    archivos = archivos_de_sesion(Path(payload.transcript_path))
    ruta = ruta_cache(payload.session_id)
    estado = cargar(ruta) if ruta is not None else estado_vacio()
    actualizar_estado(estado, archivos)
    if ruta is not None:
        guardar(ruta, estado)
    totales = totales_por_modelo(estado["mensajes"])
    return tabla_tokens(totales, colores) if totales else [payload.modelo]


def linea_modo_plan(payload: Payload, ahora: datetime, colores: bool = False) -> str:
    ruta = ruta_memoria()
    memoria = cargar_memoria(ruta)
    guardar_memoria(ruta, payload, memoria)
    payload = completar_con_memoria(payload, memoria, ahora.timestamp())
    return linea_plan(payload, ahora, colores)


def generar_salida(texto: str, base_url: str | None, ahora: datetime, colores: bool = False) -> str:
    payload = parsear_payload(texto)
    if es_modo_plan(base_url):
        lineas = [linea_modo_plan(payload, ahora, colores)]
    else:
        lineas = lineas_otro_proveedor(payload, colores)
    if colores:
        lineas = [REINICIO + linea for linea in lineas]
    return "\n".join(lineas)


def nombre_de_respaldo(texto: str) -> str:
    try:
        return parsear_payload(texto).modelo
    except (ValueError, TypeError):
        return NOMBRE_RESPALDO


def principal() -> int:
    texto = ""
    try:
        texto = sys.stdin.read()
        salida = generar_salida(
            texto,
            os.environ.get("ANTHROPIC_BASE_URL"),
            datetime.now(timezone.utc),
            colores_activos(os.environ),
        )
    except Exception:  # Red de seguridad única del proyecto: la barra nunca muestra un traceback.
        salida = nombre_de_respaldo(texto)
    # Bytes UTF-8 directos: "·", "↻", "▲" y "▼" no dependen del locale del proceso.
    sys.stdout.buffer.write((salida + "\n").encode("utf-8"))
    sys.stdout.flush()
    return 0
