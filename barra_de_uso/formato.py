"""Abreviación de cantidades de tokens y tabla alineada por modelo."""

from __future__ import annotations

from barra_de_uso.color import AMARILLO, AZUL, MAGENTA, NEGRITA, TENUE, VERDE, pintar
from barra_de_uso.transcripts import CAMPOS

SEPARADOR = " · "
COLOR_CAMPO = {"in": AZUL, "cr": VERDE, "cw": MAGENTA, "out": AMARILLO}


def abreviar(n: int) -> str:
    """0 a 999 tal cual; luego una decimal con k o M, redondeo hacia arriba en .5 con enteros."""
    if n < 1000:
        return str(n)
    decimas_k = (n + 50) // 100
    if decimas_k < 10_000:
        return f"{decimas_k // 10}.{decimas_k % 10}k"
    decimas_m = (n + 50_000) // 100_000
    return f"{decimas_m // 10}.{decimas_m % 10}M"


def tabla_tokens(totales: dict[str, dict[str, int]], colores: bool = False) -> list[str]:
    """Una línea por modelo, ordenadas por total descendente y luego por nombre.

    El relleno se calcula sobre el texto visible; los colores envuelven solo las palabras,
    así la alineación es la misma con o sin colores.
    """
    filas = sorted(totales.items(), key=lambda par: (-sum(par[1].values()), par[0]))
    ancho_modelo = max(len(modelo) for modelo, _ in filas) + 2
    textos = [{campo: abreviar(total[campo]) for campo in CAMPOS} for _, total in filas]
    anchos = {campo: max(len(texto[campo]) for texto in textos) for campo in CAMPOS}
    separador = pintar(SEPARADOR, TENUE, activo=colores)
    lineas = []
    for (modelo, _), texto in zip(filas, textos):
        cabeza = pintar(modelo, NEGRITA, activo=colores) + " " * (ancho_modelo - len(modelo))
        partes = [
            f"{pintar(campo, COLOR_CAMPO[campo], activo=colores)} {texto[campo].ljust(anchos[campo])}"
            for campo in CAMPOS
        ]
        lineas.append((cabeza + separador.join(partes)).rstrip())
    return lineas
