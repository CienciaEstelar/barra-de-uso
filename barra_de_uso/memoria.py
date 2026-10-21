"""Último uso del plan conocido, para no mostrar '--' mientras la sesión no recibe su primera respuesta."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from barra_de_uso.cache import carpeta_cache, guardar
from barra_de_uso.entrada import Payload, Ventana

VERSION = 1
NOMBRE_ARCHIVO = "ultimo-plan.json"
CLAVES = ("cinco_horas", "semanal")


def ruta_memoria() -> Path:
    return carpeta_cache() / NOMBRE_ARCHIVO


def _es_numero(valor: object) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def cargar_memoria(ruta: Path) -> dict[str, Ventana]:
    """Archivo ausente, corrupto o de otra versión: memoria vacía."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(datos, dict) or datos.get("version") != VERSION:
        return {}
    memoria = {}
    for clave in CLAVES:
        ventana = datos.get(clave)
        if not isinstance(ventana, dict):
            continue
        porcentaje = ventana.get("porcentaje")
        reset_epoch = ventana.get("reset_epoch")
        if _es_numero(porcentaje) and _es_numero(reset_epoch):
            memoria[clave] = Ventana(float(porcentaje), float(reset_epoch))
    return memoria


def guardar_memoria(ruta: Path, payload: Payload, memoria: dict[str, Ventana]) -> None:
    """Guarda las ventanas con dato real del payload; conserva las demás. No reescribe si nada cambió."""
    nueva = dict(memoria)
    for clave in CLAVES:
        ventana = getattr(payload, clave)
        if ventana is not None and not ventana.estimada and ventana.porcentaje is not None and ventana.reset_epoch is not None:
            nueva[clave] = Ventana(ventana.porcentaje, ventana.reset_epoch)
    if nueva == memoria:
        return
    datos: dict = {"version": VERSION}
    for clave, ventana in nueva.items():
        datos[clave] = {"porcentaje": ventana.porcentaje, "reset_epoch": ventana.reset_epoch}
    guardar(ruta, datos)


def completar_con_memoria(payload: Payload, memoria: dict[str, Ventana], ahora_epoch: float) -> Payload:
    """Rellena las ventanas sin dato con la memoria, marcadas como estimadas, si su reset aún no pasa."""
    cambios = {}
    for clave in CLAVES:
        actual = getattr(payload, clave)
        if actual is not None and actual.porcentaje is not None:
            continue
        recordada = memoria.get(clave)
        if recordada is not None and recordada.reset_epoch > ahora_epoch:
            cambios[clave] = dataclasses.replace(recordada, estimada=True)
    return dataclasses.replace(payload, **cambios) if cambios else payload
