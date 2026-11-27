# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.50", "imageio-ffmpeg>=0.5"]
# ///
"""Renderiza los gráficos animados del video (docs/video/motion/escenas.html) cuadro a cuadro.

    uv run docs/video/tools/render_motion.py hook:9.5:-0.04 flujo:26.3:1.2   # escena:duración:desfase

Lo llama montar.py, que calcula la duración de cada escena y el desfase L que alinea los tiempos de la
narración (data-d en el HTML) con el video. Con --cuadros t1,t2 guarda PNG sueltos para revisar.

No se graba la pantalla: en cada cuadro se detienen todas las animaciones CSS en el instante exacto
(document.getAnimations) y se toma una captura, así el movimiento sale perfectamente fluido aunque el
PC vaya lento. Salida: docs/video/motion/render/<escena>.mp4 (1920x1080, 30 fps, sin audio).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

MOTION = Path(__file__).resolve().parents[1] / "motion"
OUT = MOTION / "render"
FPS = 30

CONGELAR = """t => {
  for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; }
}"""


def abrir(page, escena: str, lead: float) -> None:
    page.goto(f"{(MOTION / 'escenas.html').as_uri()}?escena={escena}&L={lead}")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)


def render(page, escena: str, dur: float, lead: float) -> Path:
    abrir(page, escena, lead)
    salida = OUT / f"{escena}.mp4"
    ffmpeg = subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
         "-c:v", "png", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
         "-r", str(FPS), str(salida)], stdin=subprocess.PIPE)
    for i in range(round(dur * FPS)):
        page.evaluate(CONGELAR, i * 1000 / FPS)
        ffmpeg.stdin.write(page.screenshot(type="png"))
    ffmpeg.stdin.close()
    ffmpeg.wait()
    return salida


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cuadros = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--cuadros=")), None)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        for arg in args:
            escena, dur, lead = arg.split(":")
            if cuadros:  # capturas sueltas para revisar, en segundos de la escena
                abrir(page, escena, float(lead))
                for t in cuadros.split(","):
                    page.evaluate(CONGELAR, float(t) * 1000)
                    page.screenshot(path=str(OUT / f"{escena}_{t}.png"))
                continue
            print(f"{escena}: {render(page, escena, float(dur), float(lead))}")
        browser.close()


if __name__ == "__main__":
    main()
