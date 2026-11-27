"""Genera las imágenes del README: el banner (claro y oscuro) y capturas reales de la app.

    uv run python app.py                                          # en otra terminal, con Ollama encendido
    uv run --with playwright python docs/img/capturar.py          # todo
    uv run --with playwright python docs/img/capturar.py banner   # solo el banner (no necesita la app)

La primera vez: uv run --with playwright playwright install chromium
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from eciguia import ui

IMG = Path(__file__).resolve().parent
URL = "http://127.0.0.1:7860/"

TEMAS = {
    "claro": dict(fondo="#f5f7fa", tinta="#23262b", tinta2="#5b6472", rojo="#a6192e", linea="#d9dee5",
                  superficie="#ffffff", punto="rgba(35,38,43,.16)", mancha=("rgba(35,38,43,0.30)", "#a6192e")),
    "oscuro": dict(fondo="#12151a", tinta="#e7eaf0", tinta2="#a3adbd", rojo="#e0566a", linea="#2c323c",
                   superficie="#1a1e25", punto="rgba(231,234,240,.14)", mancha=("rgba(231,234,240,0.26)", "#e0566a")),
}


def banner_html(tema: str) -> str:
    t = TEMAS[tema]
    mancha = ui.mancha_de_puntos(*t["mancha"], semilla=7, columnas=58, filas=34, paso=9)
    logo = ui.logo_svg_archivo(tema)
    chips = "".join(f"<span>{c}</span>" for c in ("RAG con citas", "Agente LangGraph", "Herramientas MCP", "Ollama · 100 % local"))
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; box-sizing: border-box; }}
  body {{ width: 1280px; height: 400px; overflow: hidden; background: {t['fondo']}; font-family: Archivo, system-ui, sans-serif; position: relative; }}
  .grid {{ position: absolute; inset: 0; background-image: radial-gradient({t['punto']} 1.2px, transparent 1.6px); background-size: 22px 22px;
    -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 55%, #000 100%); }}
  .wash {{ position: absolute; inset: 0; background: linear-gradient(100deg, {t['fondo']} 30%, transparent 75%); }}
  .mancha {{ position: absolute; right: -40px; top: -10px; width: 560px; opacity: .95;
    -webkit-mask-image: radial-gradient(ellipse 70% 70% at 60% 50%, #000 40%, transparent 80%); }}
  .mancha svg {{ width: 100%; height: auto; }}
  .box {{ position: absolute; left: 84px; top: 0; bottom: 0; display: flex; align-items: center; gap: 34px; }}
  .logo svg {{ width: 132px; height: 132px; display: block; }}
  h1 {{ font-size: 92px; font-weight: 800; letter-spacing: -3px; color: {t['tinta']}; line-height: 1; }}
  h1 b {{ color: {t['rojo']}; }}
  p {{ font-size: 25px; color: {t['tinta2']}; margin-top: 12px; }}
  .chips {{ display: flex; gap: 10px; margin-top: 22px; }}
  .chips span {{ font-size: 17px; font-weight: 600; color: {t['tinta']}; padding: 7px 15px; border-radius: 999px;
    border: 1px solid {t['linea']}; background: {t['superficie']}; }}
</style></head><body>
<div class="grid"></div><div class="mancha">{mancha}</div><div class="wash"></div>
<div class="box"><div class="logo">{logo}</div><div>
  <h1>Eci<b>Guía</b></h1>
  <p>Asistente académico de la Escuela Colombiana de Ingeniería</p>
  <div class="chips">{chips}</div>
</div></div></body></html>"""


def banner(browser) -> None:
    page = browser.new_page(viewport={"width": 1280, "height": 400}, device_scale_factor=2)
    for tema in TEMAS:
        page.set_content(banner_html(tema))
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(500)
        page.screenshot(path=str(IMG / f"banner-{tema}.png"))
    page.close()


def preguntar(page, texto: str) -> None:
    caja = page.locator(".eg-input textarea")
    caja.fill(texto)
    page.locator(".eg-input button.submit-button").click()
    page.wait_for_selector(".eg-msg[data-uid], .eg-card-warn, .eg-card-error", timeout=300_000)
    page.wait_for_timeout(800)


def captura(page, nombre: str) -> None:
    page.mouse.move(5, 5)
    page.wait_for_timeout(400)
    page.screenshot(path=str(IMG / f"{nombre}.png"))


def app(browser) -> None:
    def nueva(tema: str):
        ctx = browser.new_context(viewport={"width": 1280, "height": 860}, device_scale_factor=1.5, locale="es-CO")
        ctx.add_init_script(f"try {{ localStorage.setItem('eciguia-theme', '{'dark' if tema == 'oscuro' else 'light'}') }} catch (e) {{}}")
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_selector(".eg-empty", timeout=90_000)
        page.add_style_tag(content="footer { display: none !important; }")
        page.wait_for_timeout(1500)
        return ctx, page

    ctx, page = nueva("claro")
    captura(page, "app-inicio")
    preguntar(page, "¿La práctica profesional puede ser de medio tiempo?")
    page.locator(".eg-msg[data-uid] .eg-cite").first.click()
    page.locator(".eg-msg[data-uid] .eg-how summary").click()
    page.wait_for_timeout(600)
    page.evaluate("() => { const w = document.querySelector('.eg-chat .bubble-wrap'); w.scrollTop = 120; }")
    captura(page, "app-reglamento")
    ctx.close()

    ctx, page = nueva("oscuro")
    preguntar(page, "¿En qué semestre se ve Arquitecturas de Software?")
    page.locator(".eg-msg[data-uid] .eg-how summary").click()
    page.wait_for_timeout(600)
    captura(page, "app-herramienta")
    ctx.close()

    ctx, page = nueva("oscuro")
    preguntar(page, "¿Cuántas faltas de asistencia se permiten antes de perder una materia?")
    captura(page, "app-no-sabe")
    ctx.close()


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        banner(browser)
        if "banner" not in sys.argv:
            app(browser)
        browser.close()


if __name__ == "__main__":
    main()
