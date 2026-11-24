"""Interfaz web de EciGuía.

    uv run python app.py   ->  abre http://localhost:7860
"""

import json

import gradio as gr

from eciguia.graph import EciGuiaAgent

agent = EciGuiaAgent()

ROUTE_LABELS = {
    "documentos": "📄 Reglamentos (RAG)",
    "herramienta": "🛠️ Herramienta MCP",
    "fuera_de_alcance": "🚫 Fuera de alcance",
}

EXAMPLES = [
    "¿La práctica profesional puede ser de medio tiempo?",
    "¿Qué promedio necesito para que me aprueben créditos adicionales?",
    "¿Qué requisitos hay para hacer doble programa?",
    "¿Hasta cuándo puedo cancelar el semestre?",
    "¿Cuánto cuesta la matrícula de ingeniería en 2027?",
    "¿En qué semestre se ve Arquitecturas de Software?",
    "Saqué 4.2 en una materia de 3 créditos y 3.6 en una de 4 créditos, ¿cuál es mi promedio?",
    "¿Cuántas faltas de asistencia se permiten antes de perder una materia?",
    "¿Me recomiendas una película?",
]


def format_details(state: dict) -> str:
    """Bloque bajo la respuesta: por dónde pasó la pregunta, qué herramienta usó y de dónde sale cada dato."""
    lines = [f"**Ruta:** {ROUTE_LABELS.get(state['route'], state['route'])}"]
    if state.get("tool_name") and state["tool_name"] != "ninguna":
        args = json.dumps(state.get("tool_args", {}), ensure_ascii=False)
        lines.append(f"**Herramienta:** `{state['tool_name']}` · argumentos `{args}`")
    if state.get("sources"):
        lines.append("**Fuentes:**\n" + "\n".join(f"- {s}" for s in state["sources"]))
    elif state["route"] == "documentos":
        best = min((h.distance for h in state.get("hits", [])), default=None)
        reason = f"el fragmento más cercano está a distancia {best:.2f}" if best is not None else \
            "ningún fragmento superó el umbral de relevancia"
        lines.append(f"**Fuentes:** ninguna ({reason})")
    lines.append(f"*⏱️ {state['latency_s']} s*")
    return "\n\n".join(lines)


async def respond(message: str, history: list):
    try:
        state = await agent.ask(message)
    except Exception as exc:  # típicamente Ollama apagado
        return (f"⚠️ No pude responder: `{exc}`.\n\n"
                "Revisa que Ollama esté corriendo (`ollama list`) y que el índice exista "
                "(`uv run python -m eciguia.ingest`).")
    return f"{state['answer']}\n\n---\n{format_details(state)}"


demo = gr.ChatInterface(
    fn=respond,
    title="EciGuía 🎓",
    description=(
        "Asistente académico para estudiantes de pregrado de la Escuela Colombiana de Ingeniería Julio Garavito. "
        "Responde con base en 13 documentos oficiales (reglamentos de prácticas, opción de grado, trabajos dirigidos, "
        "movilidad, inglés, líneas de énfasis, doble programa, créditos adicionales, cancelación de asignaturas y otros), "
        "el calendario académico 2027, los valores de matrícula y derechos pecuniarios 2027 y el plan de estudios de "
        "Ingeniería de Sistemas, citando documento y página. Si algo no está en los documentos, lo dice. "
        "Corre 100 % local con Ollama."
    ),
    examples=EXAMPLES,
    cache_examples=False,
)

if __name__ == "__main__":
    demo.launch()
