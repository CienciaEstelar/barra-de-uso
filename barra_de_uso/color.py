"""Códigos ANSI mínimos. Sin colores si NO_COLOR está definida y no vacía (no-color.org)."""

from __future__ import annotations

from collections.abc import Mapping

# Claude Code atenúa (dim) el status line: cada línea parte con un reinicio para que
# los colores se vean con su intensidad real.
REINICIO = "\x1b[0m"

NEGRITA = "1"
TENUE = "2"
ROJO = "31"
VERDE = "32"
AMARILLO = "33"
AZUL = "34"
MAGENTA = "35"
CIAN = "36"

UMBRAL_AMARILLO = 50
UMBRAL_ROJO = 80


def colores_activos(entorno: Mapping[str, str]) -> bool:
    return not entorno.get("NO_COLOR")


def pintar(texto: str, *codigos: str, activo: bool) -> str:
    if not activo or not codigos or not texto:
        return texto
    return f"\x1b[{';'.join(codigos)}m{texto}{REINICIO}"


def color_nivel(porcentaje: float) -> str:
    """Verde bajo 50 %, amarillo desde 50 %, rojo desde 80 %."""
    if porcentaje >= UMBRAL_ROJO:
        return ROJO
    if porcentaje >= UMBRAL_AMARILLO:
        return AMARILLO
    return VERDE
