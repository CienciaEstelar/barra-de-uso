"""Genera docs/assets/barra-de-uso.svg a partir de la salida REAL de la barra, con colores.

Uso, desde la raíz del repo:  python3 docs/assets/generar_imagen.py

Los números son sintéticos (el repo es público). El texto y los colores salen de
linea_plan() y tabla_tokens() con colores activos: este script solo traduce los
códigos ANSI a SVG, no decide nada por su cuenta.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from barra_de_uso.color import AMARILLO, AZUL, MAGENTA, ROJO, TENUE, VERDE, pintar  # noqa: E402
from barra_de_uso.entrada import Payload, Ventana  # noqa: E402
from barra_de_uso.formato import tabla_tokens  # noqa: E402
from barra_de_uso.plan import linea_plan  # noqa: E402

CHILE = ZoneInfo("America/Santiago")
AHORA = datetime(2026, 10, 21, 12, 0, tzinfo=CHILE)
RESET_5H = datetime(2026, 10, 21, 16, 30, tzinfo=CHILE).timestamp()
RESET_SEM = datetime(2026, 10, 27, 4, 0, tzinfo=CHILE).timestamp()

FONDO, BORDE, TEXTO, TENUE_HEX = "#0d1117", "#30363d", "#c9d1d9", "#6e7681"
HEX_ANSI = {"31": "#ff7b72", "32": "#7ee787", "33": "#e3b341", "34": "#58a6ff", "35": "#d2a8ff", "36": "#39c5cf"}
FUENTE = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
ANCHO, ALTO, X0 = 820, 430, 36


def segmentos_ansi(texto: str) -> list[tuple[str, str, bool]]:
    """Convierte texto con códigos ANSI en (texto, color_hex, negrita)."""
    salida, color, negrita, tenue = [], None, False, False
    for trozo in re.split(r"(\x1b\[[0-9;]*m)", texto):
        codigo = re.fullmatch(r"\x1b\[([0-9;]*)m", trozo)
        if codigo:
            for parte in codigo.group(1).split(";"):
                if parte in ("", "0"):
                    color, negrita, tenue = None, False, False
                elif parte == "1":
                    negrita = True
                elif parte == "2":
                    tenue = True
                elif parte in HEX_ANSI:
                    color = HEX_ANSI[parte]
        elif trozo:
            salida.append((trozo, TENUE_HEX if tenue else (color or TEXTO), negrita))
    return salida


def linea_svg(y: float, texto_ansi: str, tam: float = 15, ancho_car: float = 9.0) -> str:
    """Cada trozo en su <text> con x explícito y textLength: no depende de la fuente."""
    partes, cursor = [], X0
    for texto, color, negrita in segmentos_ansi(texto_ansi):
        visible = texto.strip(" ")
        if visible:
            x = cursor + (len(texto) - len(texto.lstrip(" "))) * ancho_car
            peso = ' font-weight="700"' if negrita else ""
            partes.append(
                f'<text x="{x:.1f}" y="{y}" font-size="{tam}" fill="{color}"{peso} '
                f'textLength="{len(visible) * ancho_car:.1f}" lengthAdjust="spacingAndGlyphs">{escape(visible)}</text>'
            )
        cursor += len(texto) * ancho_car
    return "\n    ".join(partes)


def etiqueta_svg(y: float, texto: str) -> str:
    return linea_svg(y, pintar(texto, TENUE, activo=True), tam=12, ancho_car=7.2)


def generar() -> str:
    prompt = pintar("❯ ", TENUE, activo=True)
    con_datos = Payload("Opus 5.5", None, None, Ventana(42, RESET_5H), Ventana(18, RESET_SEM), contexto=11)
    recien_abierta = Payload(
        "Opus 5.5", None, None, Ventana(42, RESET_5H, estimada=True), Ventana(18, RESET_SEM, estimada=True)
    )
    filas = tabla_tokens({
        "kimi-k3": {"in": 12_400, "cr": 340_100, "cw": 0, "out": 8_200},
        "glm-fast": {"in": 4_100, "cr": 90_300, "cw": 0, "out": 3_000},
    }, colores=True)
    leyenda_plan = (
        pintar("▲", ROJO, activo=True) + pintar(" más rápido que el tiempo   ", TENUE, activo=True)
        + pintar("▼", VERDE, activo=True) + pintar(" holgado   ", TENUE, activo=True)
        + "=" + pintar(" al ritmo   ", TENUE, activo=True)
        + "~" + pintar(" último dato conocido", TENUE, activo=True)
    )
    leyenda_tokens = (
        pintar("in", AZUL, activo=True) + pintar(" entrada   ", TENUE, activo=True)
        + pintar("cr", VERDE, activo=True) + pintar(" lectura de caché   ", TENUE, activo=True)
        + pintar("cw", MAGENTA, activo=True) + pintar(" escritura de caché   ", TENUE, activo=True)
        + pintar("out", AMARILLO, activo=True) + pintar(" salida", TENUE, activo=True)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}" role="img" aria-labelledby="t d">
  <title id="t">barra-de-uso</title>
  <desc id="d">La barra en modo plan, con contexto, ritmo y último dato conocido, y en otro proveedor, con tokens por modelo.</desc>
  <rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="14" fill="{FONDO}" stroke="{BORDE}" stroke-width="2"/>
  <circle cx="30" cy="28" r="6" fill="#ff5f56"/><circle cx="52" cy="28" r="6" fill="#ffbd2e"/><circle cx="74" cy="28" r="6" fill="#27c93f"/>
  <text x="{ANCHO // 2}" y="33" text-anchor="middle" font-family="{FUENTE}" font-size="13" fill="{TENUE_HEX}">barra-de-uso</text>
  <line x1="1" y1="50" x2="{ANCHO - 1}" y2="50" stroke="{BORDE}"/>
  <g font-family="{FUENTE}" xml:space="preserve">
    {etiqueta_svg(86, "MODO PLAN  ·  claude con tu login de Anthropic")}
    {linea_svg(122, prompt + linea_plan(con_datos, AHORA, colores=True))}
    {linea_svg(150, prompt + linea_plan(recien_abierta, AHORA, colores=True))}
    {linea_svg(178, leyenda_plan, tam=12.5, ancho_car=7.5)}
    <line x1="{X0}" y1="206" x2="{ANCHO - X0}" y2="206" stroke="{BORDE}" stroke-dasharray="4 6"/>
    {etiqueta_svg(244, "OTRO PROVEEDOR  ·  ds_mode, kimi_mode, glm_51, multi_mode...")}
    {linea_svg(280, prompt + filas[0])}
    {linea_svg(308, prompt + filas[1])}
    {etiqueta_svg(358, "Una fila por modelo, subagentes incluidos:")}
    {linea_svg(382, leyenda_tokens, tam=12.5, ancho_car=7.5)}
  </g>
</svg>
"""


if __name__ == "__main__":
    destino = Path(__file__).resolve().parent / "barra-de-uso.svg"
    destino.write_text(generar(), encoding="utf-8")
    print(f"escrito {destino.relative_to(RAIZ)}")
