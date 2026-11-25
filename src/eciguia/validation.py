"""Validación de la pregunta antes de gastar el modelo.

Cubre las entradas inválidas que la app debe manejar con un mensaje claro: vacías, demasiado largas,
sin texto legible e intentos de cambiar las instrucciones del asistente (inyección de prompt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 500
MIN_LETRAS = 3

# Frases típicas de inyección de prompt. No pretende ser exhaustivo: el router y los prompts siguen
# siendo la defensa principal; esto ataja los intentos más evidentes con un mensaje honesto.
INYECCION = re.compile(
    r"ignor\w*\s+(todas\s+)?(tus|las|sus)\s+(instrucciones|reglas)|olvid\w*\s+(tus|las)\s+(instrucciones|reglas)"
    r"|system\s*prompt|prompt\s+del\s+sistema|act[uú]a\s+como\s+(si\s+)?(fueras|eres)|jailbreak"
    r"|ignore\s+(all\s+)?(previous|your)\s+instructions",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Validacion:
    ok: bool
    tipo: str = ""       # "vacia", "muy_larga", "sin_texto" o "inyeccion"
    mensaje: str = ""    # qué pasó y cómo corregirlo


def validar_pregunta(texto: str | None) -> Validacion:
    texto = (texto or "").strip()
    if not texto:
        return Validacion(False, "vacia", "Escribe una pregunta sobre reglamentos, fechas del calendario 2027, "
                                          "valores de matrícula o el plan de estudios.")
    if len(texto) > MAX_CHARS:
        return Validacion(False, "muy_larga", f"Tu pregunta tiene {len(texto)} caracteres. Resúmela en menos de "
                                              f"{MAX_CHARS}: una pregunta concreta da una respuesta más precisa.")
    if len(re.findall(r"[a-záéíóúñü]", texto, re.IGNORECASE)) < MIN_LETRAS:
        return Validacion(False, "sin_texto", "No reconozco una pregunta en ese texto. Escríbela con palabras, "
                                              "por ejemplo: ¿cuánto dura la práctica profesional?")
    if INYECCION.search(texto):
        return Validacion(False, "inyeccion", "No puedo cambiar mis instrucciones. Solo respondo con los "
                                              "documentos oficiales de la Escuela; hazme una pregunta académica.")
    return Validacion(True)
