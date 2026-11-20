"""Interfaz web de EciGuía.

    uv run python app.py   ->  abre http://localhost:7860
"""

import gradio as gr

from eciguia.graph import EciGuiaAgent

agent = EciGuiaAgent()

ROUTE_LABELS = {
    "documentos": "📄 Reglamentos (RAG)",
    "herramienta": "🛠️ Herramienta MCP",
    "fuera_de_alcance": "🚫 Fuera de alcance",
}

EXAMPLES = [
    "¿Qué porcentaje de créditos debo tener aprobado para hacer la práctica profesional?",
    "¿Cuánto dura una práctica profesional internacional?",
    "¿Hasta cuándo puedo cancelar asignaturas en 2027-1?",
    "Saqué 4.2 en una materia de 3 créditos y 3.6 en una de 4 créditos, ¿cuál es mi promedio?",
    "¿Qué certificados de inglés me sirven para el requisito de grado?",
    "¿Cuántos estudiantes pueden hacer un mismo trabajo dirigido?",
]


async def respond(message: str, history: list):
    state = await agent.ask(message)
    answer = state["answer"]
    details = [f"**Ruta:** {ROUTE_LABELS.get(state['route'], state['route'])}"]
    if state.get("tool_name"):
        details.append(f"**Herramienta:** `{state['tool_name']}` con `{state.get('tool_args', {})}`")
    if state.get("sources"):
        details.append("**Fuentes:**\n" + "\n".join(f"- {s}" for s in state["sources"]))
    details.append(f"*{state['latency_s']} s*")
    return f"{answer}\n\n---\n" + "\n\n".join(details)


demo = gr.ChatInterface(
    fn=respond,
    title="EciGuía 🎓",
    description=(
        "Asistente académico de la Escuela Colombiana de Ingeniería. Responde con base en los reglamentos "
        "oficiales y el calendario 2027, citando la fuente. Corre 100 % local con Ollama."
    ),
    examples=EXAMPLES,
)

if __name__ == "__main__":
    demo.launch()
