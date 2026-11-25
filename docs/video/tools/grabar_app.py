# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.50"]
# ///
"""Graba la demo de EciGuía: un clip de video por pregunta, con marcas de tiempo para la edición.

Requisitos: la app corriendo (uv run python app.py) y Ollama sano (ver PLAN_VIDEO.md, sección 5).

    uv run docs/video/tools/grabar_app.py                 # todas las preguntas
    uv run docs/video/tools/grabar_app.py --solo q3 q5    # repetir algunas tomas

Cada clip queda en docs/video/raw/E06_<id>.webm y sus marcas en E06_<id>.json:
    t_listo      la página cargó (segundos desde el inicio del video)
    t_envio      se envió la pregunta
    t_respuesta  apareció "Ruta:" (la respuesta completa con su procesamiento)
    t_fin        fin del clip (unos segundos para leer)
    respuesta    texto que mostró la app, para verificar la toma
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7860/"
RAW = Path(__file__).resolve().parents[1] / "raw"
SIZE = {"width": 1920, "height": 1080}
ZOOM = 1.25  # agranda la interfaz para que el texto se lea en el video

PREGUNTAS = {
    "q1": "¿La práctica profesional puede ser de medio tiempo?",
    "q2": "¿Hasta cuándo puedo cancelar el semestre?",
    "q3": "¿Cuánto cuesta la matrícula de ingeniería en 2027?",
    "q4": "¿En qué semestre se ve Arquitecturas de Software?",
    "q5": "¿Qué materias se ven en quinto semestre de Ingeniería Civil?",
    "q6": "¿Cuántas faltas de asistencia se permiten antes de perder una materia?",
    "q7": "¿Me recomiendas una película para el fin de semana?",
}


def grabar(browser, clip_id: str, pregunta: str) -> dict:
    tmp = RAW / "_tmp"
    context = browser.new_context(viewport=SIZE, record_video_dir=str(tmp), record_video_size=SIZE, locale="es-CO")
    t0 = time.monotonic()
    page = context.new_page()
    page.goto(URL)
    page.add_style_tag(content=f"body {{ zoom: {ZOOM}; }} footer {{ display: none !important; }}")
    caja = page.locator("textarea").first
    caja.wait_for(timeout=60_000)
    page.wait_for_timeout(1500)
    t_listo = time.monotonic() - t0

    caja.click()
    caja.press_sequentially(pregunta, delay=45)
    page.wait_for_timeout(600)
    caja.press("Enter")
    t_envio = time.monotonic() - t0

    page.get_by_text("Ruta:").first.wait_for(timeout=240_000)
    t_respuesta = time.monotonic() - t0
    page.wait_for_timeout(800)
    # baja al final del chat para que la sección de fuentes quede a la vista
    page.mouse.move(960, 600)
    page.mouse.wheel(0, 2000)
    page.wait_for_timeout(4500)
    t_fin = time.monotonic() - t0
    respuesta = page.locator("[role='log']").first.inner_text()

    video = page.video
    context.close()
    destino = RAW / f"E06_{clip_id}.webm"
    shutil.move(video.path(), destino)
    marcas = {"id": clip_id, "pregunta": pregunta, "archivo": destino.name, "t_listo": round(t_listo, 2),
              "t_envio": round(t_envio, 2), "t_respuesta": round(t_respuesta, 2), "t_fin": round(t_fin, 2),
              "espera_llm_s": round(t_respuesta - t_envio, 2), "respuesta": respuesta}
    (RAW / f"E06_{clip_id}.json").write_text(json.dumps(marcas, ensure_ascii=False, indent=2), encoding="utf-8")
    return marcas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", nargs="*", help="ids a grabar (por defecto, todos)")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    ids = args.solo or list(PREGUNTAS)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for clip_id in ids:
            m = grabar(browser, clip_id, PREGUNTAS[clip_id])
            print(f"{clip_id}: espera LLM {m['espera_llm_s']} s, clip {m['t_fin']} s -> {m['archivo']}")
        browser.close()
    shutil.rmtree(RAW / "_tmp", ignore_errors=True)


if __name__ == "__main__":
    main()
