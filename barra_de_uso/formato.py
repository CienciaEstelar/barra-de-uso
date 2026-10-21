"""Abreviación de cantidades de tokens y tabla alineada por modelo."""

from __future__ import annotations

from barra_de_uso.transcripts import CAMPOS

SEPARADOR = " · "


def abreviar(n: int) -> str:
    """0 a 999 tal cual; luego una decimal con k o M, redondeo hacia arriba en .5 con enteros."""
    if n < 1000:
        return str(n)
    decimas_k = (n + 50) // 100
    if decimas_k < 10_000:
        return f"{decimas_k // 10}.{decimas_k % 10}k"
    decimas_m = (n + 50_000) // 100_000
    return f"{decimas_m // 10}.{decimas_m % 10}M"


def tabla_tokens(totales: dict[str, dict[str, int]]) -> list[str]:
    """Una línea por modelo, ordenadas por total descendente y luego por nombre."""
    filas = sorted(totales.items(), key=lambda par: (-sum(par[1].values()), par[0]))
    ancho_modelo = max(len(modelo) for modelo, _ in filas) + 2
    textos = [{campo: abreviar(total[campo]) for campo in CAMPOS} for _, total in filas]
    anchos = {campo: max(len(texto[campo]) for texto in textos) for campo in CAMPOS}
    lineas = []
    for (modelo, _), texto in zip(filas, textos):
        partes = [f"{campo} {texto[campo].ljust(anchos[campo])}" for campo in CAMPOS]
        lineas.append((modelo.ljust(ancho_modelo) + SEPARADOR.join(partes)).rstrip())
    return lineas
