"""Línea del modo plan: uso de la ventana de 5 h y de la semanal, con reset en hora de Chile."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from barra_de_uso.entrada import Payload, Ventana

# Se resuelve dentro de la función para que un tzdata faltante caiga en la red de seguridad.
ZONA_CHILE = "America/Santiago"
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
SEPARADOR = " · "


def formatear_reset(reset_epoch: float, ahora: datetime) -> str:
    """Solo HH:MM si el reset cae hoy (hora de Chile); si no, día abreviado y HH:MM."""
    zona = ZoneInfo(ZONA_CHILE)
    reset = datetime.fromtimestamp(reset_epoch, zona)
    hora = reset.strftime("%H:%M")
    if reset.date() == ahora.astimezone(zona).date():
        return hora
    return f"{DIAS[reset.weekday()]} {hora}"


def formatear_ventana(etiqueta: str, ventana: Ventana | None, ahora: datetime) -> str:
    if ventana is None or ventana.porcentaje is None:
        return f"{etiqueta} --"
    texto = f"{etiqueta} {round(ventana.porcentaje)}%"
    if ventana.reset_epoch is not None:
        texto += f" ↻ {formatear_reset(ventana.reset_epoch, ahora)}"
    return texto


def linea_plan(payload: Payload, ahora: datetime) -> str:
    """`ahora` debe ser un datetime con zona horaria."""
    return SEPARADOR.join([
        payload.modelo,
        formatear_ventana("5h", payload.cinco_horas, ahora),
        formatear_ventana("sem", payload.semanal, ahora),
    ])
