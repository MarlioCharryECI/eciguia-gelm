"""Lógica pura de las herramientas (sin MCP), para poder probarla aparte.

El servidor MCP (mcp_server.py) solo expone estas funciones.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date

from eciguia import config

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "o", "a", "en", "para", "por", "con",
             "que", "cuando", "cual", "es", "fecha", "hasta", "se", "un", "una", "al", "mi"}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _human_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def load_calendar() -> list[dict]:
    with open(config.CALENDAR_PATH, encoding="utf-8") as file:
        return json.load(file)["eventos"]


def consultar_calendario(consulta: str, periodo: str | None = None, max_resultados: int = 5) -> list[dict]:
    """Busca eventos del calendario académico 2027 por palabras clave.

    consulta: palabras del evento, por ejemplo "cancelación de asignaturas" o "exámenes finales".
    periodo: opcional, uno de "2026-2", "2027-1", "2027-i", "2027-2", "2028-1".
    """
    words = [w for w in _normalize(consulta).replace("?", " ").split() if w not in STOPWORDS and len(w) > 2]
    results = []
    for event in load_calendar():
        if periodo and event["periodo"].lower() != periodo.lower():
            continue
        name = _normalize(event["evento"])
        # coincidencia por raíz de 5 letras para tolerar plurales y conjugaciones
        score = sum(1 for w in words if w[:5] in name)
        if score:
            results.append((score, event))
    results.sort(key=lambda item: (-item[0], item[1]["inicio"]))
    best = results[0][0] if results else 0
    return [
        {
            "evento": e["evento"],
            "periodo": e["periodo"],
            "inicio": _human_date(e["inicio"]),
            "fin": _human_date(e["fin"]),
        }
        for score, e in results[:max_resultados]
        if score == best or score >= 2
    ]


def dias_hasta(fecha: str, hoy: str | None = None) -> dict:
    """Días calendario que faltan desde hoy (o desde 'hoy' si se indica) hasta una fecha ISO AAAA-MM-DD."""
    today = date.fromisoformat(hoy) if hoy else date.today()
    target = date.fromisoformat(fecha)
    return {"desde": _human_date(today.isoformat()), "hasta": _human_date(fecha), "dias": (target - today).days}


def calcular_promedio_ponderado(asignaturas: list[dict]) -> dict:
    """Promedio ponderado por créditos, como define el artículo 80 del Reglamento Estudiantil.

    asignaturas: lista de {"nota": float entre 0 y 5, "creditos": int > 0}.
    El resultado se expresa con un solo decimal, igual que el promedio acumulado oficial.
    """
    if not asignaturas:
        raise ValueError("Se necesita al menos una asignatura")
    total_creditos = 0
    suma = 0.0
    for item in asignaturas:
        nota, creditos = float(item["nota"]), int(item["creditos"])
        if not 0 <= nota <= 5 or creditos <= 0:
            raise ValueError(f"Asignatura inválida: {item}")
        suma += nota * creditos
        total_creditos += creditos
    exacto = suma / total_creditos
    # El reglamento dice "con un solo decimal" pero no si se redondea o se trunca, así que devolvemos ambos
    return {
        "promedio_un_decimal": round(exacto, 1),
        "promedio_exacto": round(exacto, 3),
        "creditos": total_creditos,
    }
