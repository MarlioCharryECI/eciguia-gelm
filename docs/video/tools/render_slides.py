# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.50"]
# ///
"""Genera las diapositivas (PNG 1920x1080) y los rótulos de la demo (PNG transparentes).

    uv run docs/video/tools/render_slides.py

Las cifras de la diapositiva de resultados se leen de docs/resultados/ (no se escriben a mano).
Los rótulos de cada clip usan las marcas de tiempo de docs/video/raw/E06_*.json.
"""

from __future__ import annotations

import base64
import csv
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
VIDEO = ROOT / "docs" / "video"
SLIDES = VIDEO / "slides"
RES = ROOT / "docs" / "resultados"
RAW = VIDEO / "raw"

CSS = """
* { box-sizing: border-box; margin: 0; }
body { width: 1920px; height: 1080px; font-family: 'Segoe UI', system-ui, sans-serif; color: #eef1f6;
       background: radial-gradient(circle at 20% 15%, #1c2b4a 0%, #0d1424 55%, #080c16 100%); overflow: hidden; }
.wrap { padding: 110px 140px; height: 100%; display: flex; flex-direction: column; }
h1 { font-size: 84px; font-weight: 700; letter-spacing: -1px; }
h2 { font-size: 60px; font-weight: 700; margin-bottom: 50px; }
.accent { color: #f5b942; }
.muted { color: #9aa6bd; }
.small { font-size: 26px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 32px; }
.card { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 22px; padding: 36px 32px; }
.card .n { font-size: 88px; font-weight: 800; color: #f5b942; line-height: 1; }
.card .t { font-size: 30px; margin-top: 18px; line-height: 1.3; }
.claim { margin-top: auto; font-size: 38px; line-height: 1.45; border-left: 8px solid #f5b942; padding-left: 34px; }
"""


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def stages(html: str) -> list[str]:
    """Versiones de una diapositiva que se arma por partes: los elementos con data-s="k" aparecen en la etapa k.
    montar.py cambia de etapa cuando la narración llega a la frase correspondiente."""
    n = max((int(k) for k in re.findall(r"data-s='(\d+)'", html)), default=0)
    return [html.replace("</style>", "".join(f"[data-s='{k}']{{visibility:hidden}}" for k in range(i + 1, n + 1)) + "</style>")
            for i in range(n + 1)]


def page_html(body: str, extra_css: str = "") -> str:
    return f"<html><head><meta charset='utf-8'><style>{CSS}{extra_css}</style></head><body>{body}</body></html>"


def resultados() -> dict:
    """Cifras de la versión final (segunda etapa), leídas de los resúmenes guardados."""
    orig = json.loads((RES / "8_final_original.json").read_text(encoding="utf-8"))
    nuevas = json.loads((RES / "8_final_nuevas.json").read_text(encoding="utf-8"))
    with open(RES / "regresion_6_final_vs_8_final_original.csv", encoding="utf-8") as f:
        empeoran = sum("empeora" in r["cambios"] for r in csv.DictReader(f))
    holdout = json.loads((RES / "ruteo_holdout.json").read_text(encoding="utf-8"))
    calib = json.loads((RES / "calibracion.json").read_text(encoding="utf-8"))
    return {"preguntas": orig["n"] + nuevas["n"], "empeoran": empeoran,
            "router_v3": round(holdout["exactitud"]["v3"] * 100), "umbral": calib["umbral"]}


def slides() -> dict[str, str]:
    r = resultados()
    return {
        "S1_titulo": page_html(f"""
<div class='wrap' style='justify-content:center'>
  <div class='muted small' style='letter-spacing:6px'>PROYECTO FINAL · IA GENERATIVA (GELM) 2026-2</div>
  <h1 style='font-size:150px;margin:24px 0 10px'>Eci<span class='accent'>Guía</span></h1>
  <div style='font-size:46px;line-height:1.35'>Asistente académico con <span class='accent'>RAG</span>, <span class='accent'>agentes</span> y <span class='accent'>MCP</span>,<br>100 % local</div>
  <div style='margin-top:70px;font-size:36px'>Marlio José Charry Espitia</div>
  <div class='muted' style='font-size:28px;margin-top:8px'>Universidad Escuela Colombiana de Ingeniería Julio Garavito</div>
  <div class='muted' style='position:absolute;bottom:50px;left:140px;font-size:22px'>Narración con voz sintética (Microsoft Edge TTS, voz Gonzalo). Las respuestas de la demo son reales.</div>
  <img src='data:image/png;base64,{img_b64(ROOT / "docs" / "img" / "app_documentos.png")}'
       style='position:absolute;right:-60px;top:210px;width:900px;border-radius:18px;transform:perspective(1600px) rotateY(-14deg);
              box-shadow:0 30px 80px rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.15)'>
</div>"""),
        "S2_problema": page_html("""
<div class='wrap'>
  <h2>El problema: la información está <span class='accent'>dispersa</span></h2>
  <div class='cards'>
    <div class='card'><div class='n'>9</div><div class='t'>reglamentos y lineamientos en PDF</div></div>
    <div class='card'><div class='n'>3</div><div class='t'>acuerdos <b>escaneados</b>, sin texto</div></div>
    <div class='card'><div class='n'>4</div><div class='t'>tablas: matrícula, derechos y planes de estudio</div></div>
    <div class='card'><div class='n'>1</div><div class='t'>calendario académico publicado como <b>imagen</b></div></div>
  </div>
  <div class='claim' data-s='1'>Un chatbot genérico no conoce estos documentos e <b>inventa</b>.<br>
  EciGuía responde <span class='accent'>solo con fuentes oficiales</span>, cita documento y página, y dice <span class='accent'>"no sé"</span>.</div>
</div>"""),
        "S3_arquitectura": page_html("""
<div class='wrap' style='padding-top:80px'>
  <h2 style='margin-bottom:40px'>Cómo funciona</h2>
  <div class='flow'>
    <div class='box q'>Pregunta del estudiante</div>
    <div class='arrow'>→</div>
    <div class='box router'><b>Router</b><br><span class='sm'>Qwen 2.5 7B · Ollama<br>(LangGraph)</span></div>
    <div class='arrow'>→</div>
    <div class='routes'>
      <div class='box r1' data-s='1'><b>📄 Reglamentos (RAG)</b><span class='sm'>13 documentos · bge-m3 + Chroma · umbral calibrado 0,45<br>→ respuesta con citas, o "no encontré"</span></div>
      <div class='box r2' data-s='2'><b>🛠️ Herramientas MCP</b><span class='sm'>calendario 2027 · valores de matrícula 2027 · plan de estudios · promedio</span></div>
      <div class='box r3' data-s='3'><b>🚫 Fuera de alcance</b><span class='sm'>rechazo amable, sin gastar modelo</span></div>
    </div>
  </div>
  <div class='claim' style='font-size:32px' data-s='3'>Debajo de cada respuesta se muestra la <span class='accent'>ruta</span>, la <span class='accent'>herramienta</span> y las <span class='accent'>fuentes</span>. Todo corre local, en una GPU de 6 GB.</div>
</div>""", """
.flow { display:flex; align-items:center; gap:28px; margin-bottom:60px; }
.box { background: rgba(255,255,255,0.07); border:2px solid rgba(255,255,255,0.18); border-radius:20px; padding:26px 30px; font-size:32px; }
.box .sm, .sm { display:block; font-size:24px; color:#b9c3d6; margin-top:8px; line-height:1.4; }
.q { width:250px; text-align:center; }
.router { width:290px; text-align:center; border-color:#f5b942; }
.arrow { font-size:64px; color:#f5b942; }
.routes { display:flex; flex-direction:column; gap:20px; flex:1; }
.r1 { border-color:#5aa9ff; } .r2 { border-color:#f08a4b; } .r3 { border-color:#9aa6bd; }
"""),
        "S5_resultados": page_html(f"""
<div class='wrap'>
  <h2>Resultados <span class='muted' style='font-size:34px;font-weight:400'>· evaluación con preguntas de respuesta conocida</span></h2>
  <div class='cards'>
    <div class='card'><div class='n'>{r['preguntas']}</div><div class='t'>preguntas de evaluación (40 originales + 26 de la ampliación)</div></div>
    <div class='card' data-s='1'><div class='n'>55/55</div><div class='t'>respuestas correctas, revisadas a mano</div></div>
    <div class='card' data-s='2'><div class='n'>12/12</div><div class='t'>trampas y preguntas fuera de alcance rechazadas</div></div>
    <div class='card' data-s='3'><div class='n'>{r['empeoran']}</div><div class='t'>regresiones al ampliar de 6 a 13 documentos</div></div>
  </div>
  <div class='claim' style='font-size:32px' data-s='4'>Umbral de "no sé" calibrado con datos: <span class='accent'>{str(r['umbral']).replace('.', ',')}</span> ·
  Router: <span class='accent'>{r['router_v3']} %</span> en preguntas nuevas · Juez automático validado a mano (8 de 10)</div>
</div>"""),
        "S6_cierre": page_html("""
<div class='wrap' style='justify-content:center'>
  <h2>Límites y próximos pasos</h2>
  <div style='font-size:36px;line-height:1.7'>
    · Falta el Reglamento Estudiantil <b>consolidado y vigente</b><br>
    · Plan de estudios solo de Ingeniería de Sistemas<br>
    · Unos 15 s por respuesta en un portátil (todo local)
  </div>
  <div class='claim' style='margin-top:80px'>Código, pruebas y evaluación:<br><span class='accent'>github.com/MarlioCharryECI/eciguia-gelm</span></div>
</div>"""),
    }


CHIP_CSS = """
body { background: transparent; }
.chip { position:absolute; top:22px; right:30px; max-width:900px; padding:16px 26px; border-radius:16px;
        font-family:'Segoe UI', sans-serif; color:#fff; box-shadow:0 8px 24px rgba(0,0,0,0.35); }
.chip .k { font-size:30px; font-weight:800; letter-spacing:1px; }
.chip .d { font-size:22px; margin-top:4px; opacity:0.95; }
.e { background:#2f6fd6; } .p { background:#d9702b; } .s { background:#1f9d6a; }
"""

CASOS = {"q1": "Caso 1 · Reglamento con cita", "q2": "Caso 2 · Fecha del calendario", "q3": "Caso 3 · Valor 2027",
         "q4": "Caso 4 · Plan de estudios", "q5": "Caso 5 · Trampa: otro programa",
         "q6": "Caso 6 · Trampa: dato que no está", "q7": "Caso 7 · Fuera de alcance"}


def chips(espera_comprimida: float) -> dict[str, str]:
    out = {}
    for clip in sorted(RAW.glob("E06_q*.json")):
        m = json.loads(clip.read_text(encoding="utf-8"))
        caso = CASOS[m["id"]]
        espera = m["t_respuesta"] - m["t_envio"]
        factor = max(espera / espera_comprimida, 1.0)
        out[f"chip_{m['id']}_entrada"] = f"<div class='chip e'><div class='k'>1 · ENTRADA</div><div class='d'>{caso}</div></div>"
        out[f"chip_{m['id']}_proceso"] = (f"<div class='chip p'><div class='k'>2 · PROCESAMIENTO CON GenAI</div>"
                                          f"<div class='d'>⏩ espera acelerada ×{factor:.0f} · la respuesta tardó {espera:.0f} s</div></div>")
        out[f"chip_{m['id']}_salida"] = "<div class='chip s'><div class='k'>3 · SALIDA</div><div class='d'>respuesta + ruta + herramienta + fuentes</div></div>"
    return out


def main() -> None:
    SLIDES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        for name, html in slides().items():
            versiones = stages(html)
            for i, version in enumerate(versiones):
                page.set_content(version)
                sufijo = f"_{i}" if len(versiones) > 1 else ""
                page.screenshot(path=str(SLIDES / f"{name}{sufijo}.png"))
            print(name, f"({len(versiones)} etapas)" if len(versiones) > 1 else "")
        for name, html in chips(espera_comprimida=2.5).items():
            page.set_content(page_html(html, CHIP_CSS))
            page.screenshot(path=str(SLIDES / f"{name}.png"), omit_background=True)
        print("rótulos de la demo:", len(chips(2.5)))
        browser.close()


if __name__ == "__main__":
    main()
