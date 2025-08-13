# core/gmail_client.py
"""Compatibilidad temporal. Usa core.gmail directamente en código nuevo."""
from typing import List
import os

from core.gmail import (
    remitentes_hoy as _remitentes_hoy,
    leer_ultimo as _leer_ultimo,
    contar_no_leidos as _contar_no_leidos,
)
from utils.summarizer import resumen_correos_hoy as _resumen_correos_hoy

GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "10"))


def contar_correos_no_leidos(service):
    """
    Compat: reporta string con conteo de no leídos en Primary.
    """
    cantidad = _contar_no_leidos(service)
    if cantidad == 0:
        return "No tienes correos sin leer."
    if cantidad == 1:
        return "Tienes 1 correo sin leer."
    return f"Tienes {cantidad} correos sin leer."


def remitentes_hoy(service):
    """
    Compat: devuelve string con remitentes únicos de las últimas 24h (Primary).
    """
    remitentes: List[str] = _remitentes_hoy(service)
    if not remitentes:
        return "Hoy no has recibido correos nuevos."

    remitentes = sorted(set(remitentes))
    if len(remitentes) == 1:
        return f"Hoy te escribió {remitentes[0]}."
    nombres = ", ".join(remitentes[:-1]) + " y " + remitentes[-1]
    return f"Hoy te escribieron {nombres}."


def leer_ultimo_correo(service):
    """
    Compat: retorna dict con metadata del último correo (Primary).
    """
    return _leer_ultimo(service)


def resumen_correos_hoy(service, cantidad: int = 10):
    """
    Delegado al summarizer actual. Mantiene la firma para código legado.
    """
    return _resumen_correos_hoy(service, cantidad=cantidad)
