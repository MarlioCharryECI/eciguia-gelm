"""Servidor MCP de EciGuía. Expone las herramientas que el agente puede usar.

Se puede correr solo para probarlo con cualquier cliente MCP:
    uv run python -m eciguia.mcp_server
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from eciguia import tools_logic

mcp = FastMCP("eciguia-tools")


class Asignatura(BaseModel):
    nota: Annotated[float, Field(ge=0, le=5, description="Calificación definitiva de 0 a 5")]
    creditos: Annotated[int, Field(gt=0, description="Créditos académicos de la asignatura")]


@mcp.tool
def consultar_calendario(consulta: str, periodo: str | None = None) -> list[dict]:
    """Busca fechas en el calendario académico 2027 de la Escuela (preinscripción, pagos de matrícula,
    horarios, inicio de clases, cancelación de asignaturas o semestre, exámenes finales, vacaciones,
    grados, envío de práctica profesional, becas). Cada evento trae su estado (ya pasó, en curso,
    próximo) y los días que faltan para que empiece.

    consulta: palabras clave del evento, por ejemplo "cancelación de asignaturas".
    periodo: opcional, uno de "2026-2", "2027-1", "2027-i" (intersemestral), "2027-2", "2028-1".
    """
    return tools_logic.consultar_calendario(consulta, periodo)


@mcp.tool
def dias_hasta(fecha: str) -> dict:
    """Calcula cuántos días faltan desde hoy hasta una fecha en formato AAAA-MM-DD."""
    return tools_logic.dias_hasta(fecha)


@mcp.tool
def calcular_promedio_ponderado(asignaturas: list[Asignatura]) -> dict:
    """Calcula el promedio ponderado por créditos de una lista de asignaturas, como el promedio
    acumulado del Reglamento Estudiantil (artículo 80)."""
    return tools_logic.calcular_promedio_ponderado([a.model_dump() for a in asignaturas])


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="WARNING")
