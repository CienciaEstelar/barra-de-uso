"""Parseo tolerante del JSON que Claude Code entrega por stdin al status line."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

NOMBRE_RESPALDO = "barra-de-uso"


@dataclass(frozen=True)
class Ventana:
    """Una ventana de rate limit: porcentaje usado y momento del reset (epoch en segundos).

    `estimada` es True cuando el dato viene de la memoria y no del payload actual.
    """

    porcentaje: float | None
    reset_epoch: float | None
    estimada: bool = False


@dataclass(frozen=True)
class Payload:
    modelo: str
    session_id: str | None
    transcript_path: str | None
    cinco_horas: Ventana | None
    semanal: Ventana | None
    contexto: float | None = None


def _numero(valor: object) -> float | None:
    # resets_at y used_percentage pueden llegar como número o como string.
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str):
        try:
            numero = float(valor)
        except ValueError:
            return None
    else:
        return None
    return numero if math.isfinite(numero) else None


def _texto(valor: object) -> str | None:
    return valor if isinstance(valor, str) and valor else None


def _diccionario(valor: object) -> dict:
    return valor if isinstance(valor, dict) else {}


def _ventana(valor: object) -> Ventana | None:
    if not isinstance(valor, dict):
        return None
    return Ventana(_numero(valor.get("used_percentage")), _numero(valor.get("resets_at")))


def parsear_payload(texto: str) -> Payload:
    """Convierte el JSON de stdin en un Payload. Lanza ValueError si no es un objeto JSON."""
    datos = json.loads(texto)
    if not isinstance(datos, dict):
        raise ValueError("el payload no es un objeto JSON")
    info_modelo = _diccionario(datos.get("model"))
    modelo = _texto(info_modelo.get("display_name")) or _texto(info_modelo.get("id")) or NOMBRE_RESPALDO
    limites = _diccionario(datos.get("rate_limits"))
    contexto = _diccionario(datos.get("context_window"))
    return Payload(
        modelo=modelo,
        session_id=_texto(datos.get("session_id")),
        transcript_path=_texto(datos.get("transcript_path")),
        cinco_horas=_ventana(limites.get("five_hour")),
        semanal=_ventana(limites.get("seven_day")),
        # Viene null en el primer refresco, antes de la primera respuesta.
        contexto=_numero(contexto.get("used_percentage")),
    )
