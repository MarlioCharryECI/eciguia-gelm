"""Interfaz web de EciGuía.

    uv run python app.py   ->  abre http://localhost:7860

El HTML de los mensajes está en src/eciguia/ui.py; los estilos y el comportamiento, en assets/.
"""

import base64
import json
import time
from datetime import datetime

import gradio as gr

from eciguia import config, ui
from eciguia.graph import EciGuiaAgent

agent = EciGuiaAgent()
FEEDBACK = config.ROOT / "data" / "feedback" / "feedback.jsonl"


async def respond(message: str, history: list):
    """Muestra el proceso en vivo (cada paso del agente), luego el texto mientras se genera y al final
    la respuesta completa con citas, fuentes y "¿Cómo lo supe?"."""
    nodos, estado, parcial, ultimo = [], {}, "", 0.0
    try:
        async for evento in agent.astream(message):
            if evento["tipo"] == "paso":
                nodos.append(evento["nodo"])
                estado = evento["estado"]
                yield ui.streaming_html(estado, nodos, parcial)
            elif evento["tipo"] == "token":
                parcial += evento["texto"]
                if time.monotonic() - ultimo > 0.08:  # no redibujar en cada token
                    ultimo = time.monotonic()
                    yield ui.streaming_html(estado, nodos, parcial)
            else:
                yield ui.final_html(evento["estado"])
    except Exception as exc:  # típicamente Ollama apagado o trabado
        yield ui.error_html(exc)


def registrar_feedback(data: gr.LikeData):
    """Guarda cada 👍/👎 en data/feedback/feedback.jsonl (local, no se versiona)."""
    FEEDBACK.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK, "a", encoding="utf-8") as file:
        file.write(json.dumps({"fecha": datetime.now().isoformat(timespec="seconds"), "util": data.liked,
                               "indice": data.index, "mensaje": str(data.value)[:2000]}, ensure_ascii=False) + "\n")


THEME = gr.themes.Base(
    primary_hue=gr.themes.Color(c50="#fbeef0", c100="#f6e3e6", c200="#ecbfc6", c300="#df8f9b", c400="#cc5367",
                                c500="#a6192e", c600="#911628", c700="#771221", c800="#5c0e19", c900="#430a12", c950="#2b060c"),
    # neutros propios (grafito y gris de plano) en vez de los grises azulados de Gradio
    neutral_hue=gr.themes.Color(c50="#f5f7fa", c100="#eef1f5", c200="#d9dee5", c300="#b8c0cc", c400="#8b95a5",
                                c500="#5b6472", c600="#444c58", c700="#2c323c", c800="#1f242c", c900="#1a1e25", c950="#12151a"),
    font=[gr.themes.GoogleFont("Archivo"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    radius_size="lg",
).set(
    body_background_fill="#f5f7fa", body_background_fill_dark="#12151a",
    block_background_fill="#ffffff", block_background_fill_dark="#1a1e25",
    block_border_color="#d9dee5", block_border_color_dark="#2c323c",
    body_text_color="#23262b", body_text_color_dark="#e7eaf0",
    button_primary_background_fill="#a6192e", button_primary_background_fill_hover="#911628",
    background_fill_secondary="#f5f7fa", background_fill_secondary_dark="#12151a",
    input_background_fill="#ffffff", input_background_fill_dark="#1a1e25",
    border_color_primary="#d9dee5", border_color_primary_dark="#2c323c",
)

FAVICON = base64.b64encode((config.ROOT / "assets" / "logo" / "favicon.svg").read_bytes()).decode()
HEAD = (
    f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{FAVICON}">'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">'
    f"<script>{(config.ROOT / 'assets' / 'eciguia.js').read_text(encoding='utf-8')}</script>"
)

with gr.Blocks(title="EciGuía · asistente académico", fill_height=True) as demo:
    gr.HTML(ui.header_html())
    with gr.Sidebar(open=False, label="Qué sé"):
        gr.HTML(ui.sidebar_html())
    chatbot = gr.Chatbot(
        placeholder=ui.placeholder_html(),
        sanitize_html=False,
        render_markdown=True,
        feedback_options=("Like", "Dislike"),
        show_label=False,
        elem_classes=["eg-chat"],
        scale=1,
    )
    textbox = gr.Textbox(
        placeholder="Pregunta sobre reglamentos, fechas del calendario, matrícula o el plan de estudios",
        show_label=False,
        submit_btn=True,
        max_lines=4,
        elem_classes=["eg-input"],
    )
    gr.ChatInterface(fn=respond, chatbot=chatbot, textbox=textbox, fill_height=True, autofocus=True)
    chatbot.like(registrar_feedback)

if __name__ == "__main__":
    demo.launch(theme=THEME, css_paths=[config.ROOT / "assets" / "eciguia.css"], css=ui.decor_css(), head=HEAD)
