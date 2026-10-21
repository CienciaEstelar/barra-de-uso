"""Línea del modo plan: contexto, uso de 5 h y semanal con ritmo, reset en hora de Chile."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from barra_de_uso.color import ROJO, TENUE, VERDE, color_nivel, pintar
from barra_de_uso.entrada import Payload, Ventana

# Se resuelve dentro de la función para que un tzdata faltante caiga en la red de seguridad.
ZONA_CHILE = "America/Santiago"
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
SEPARADOR = " · "

DURACION_SEGUNDOS = {"5h": 5 * 3600, "sem": 7 * 24 * 3600}
# Margen en puntos porcentuales antes de declarar que vas adelantado o holgado.
TOLERANCIA_RITMO = 5
ADELANTADO, HOLGADO, AL_RITMO = "▲", "▼", "="
# Ir al ritmo no es una advertencia: sin color.
COLOR_FLECHA = {ADELANTADO: (ROJO,), HOLGADO: (VERDE,), AL_RITMO: ()}


def formatear_reset(reset_epoch: float, ahora: datetime) -> str:
    """Solo HH:MM si el reset cae hoy (hora de Chile); si no, día abreviado y HH:MM."""
    zona = ZoneInfo(ZONA_CHILE)
    reset = datetime.fromtimestamp(reset_epoch, zona)
    hora = reset.strftime("%H:%M")
    if reset.date() == ahora.astimezone(zona).date():
        return hora
    return f"{DIAS[reset.weekday()]} {hora}"


def flecha_ritmo(porcentaje: float, reset_epoch: float, duracion: float, ahora_epoch: float) -> str:
    """Compara el % usado con el % de la ventana que ya transcurrió.

    ▲ si consumes más rápido que el tiempo, ▼ si vas holgado, = si vas dentro del margen.
    """
    restante = reset_epoch - ahora_epoch
    transcurrido = min(max((duracion - restante) / duracion, 0.0), 1.0) * 100
    diferencia = porcentaje - transcurrido
    if diferencia > TOLERANCIA_RITMO:
        return ADELANTADO
    if diferencia < -TOLERANCIA_RITMO:
        return HOLGADO
    return AL_RITMO


def formatear_ventana(etiqueta: str, ventana: Ventana | None, ahora: datetime, colores: bool = False) -> str:
    if ventana is None or ventana.porcentaje is None:
        return f"{etiqueta} --"
    porcentaje = f"{round(ventana.porcentaje)}%"
    reset = None if ventana.reset_epoch is None else formatear_reset(ventana.reset_epoch, ahora)
    if ventana.estimada:
        # Dato de la memoria: con "~" para que se entienda sin colores, tenue y sin ritmo.
        texto = f"{etiqueta} ~{porcentaje}" + (f" ↻ {reset}" if reset else "")
        return pintar(texto, TENUE, activo=colores)
    partes = [etiqueta, pintar(porcentaje, color_nivel(ventana.porcentaje), activo=colores)]
    if ventana.reset_epoch is not None:
        flecha = flecha_ritmo(ventana.porcentaje, ventana.reset_epoch, DURACION_SEGUNDOS[etiqueta], ahora.timestamp())
        partes.append(pintar(flecha, *COLOR_FLECHA[flecha], activo=colores))
        partes.append(f"↻ {reset}")
    return " ".join(partes)


def formatear_contexto(contexto: float, colores: bool = False) -> str:
    return "ctx " + pintar(f"{round(contexto)}%", color_nivel(contexto), activo=colores)


def linea_plan(payload: Payload, ahora: datetime, colores: bool = False) -> str:
    """`ahora` debe ser un datetime con zona horaria."""
    partes = [payload.modelo]
    if payload.contexto is not None:
        partes.append(formatear_contexto(payload.contexto, colores))
    partes.append(formatear_ventana("5h", payload.cinco_horas, ahora, colores))
    partes.append(formatear_ventana("sem", payload.semanal, ahora, colores))
    return pintar(SEPARADOR, TENUE, activo=colores).join(partes)
