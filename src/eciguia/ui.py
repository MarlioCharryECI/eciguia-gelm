"""HTML de la interfaz de EciGuía (Gradio personalizado).

Funciones puras que convierten el estado del agente en HTML: el proceso en vivo, la respuesta con citas
interactivas, las tarjetas de fuente, "¿Cómo lo supe?", la tarjeta de "no sé", el estado vacío por
categorías y el panel "Qué sé". Los estilos están en assets/eciguia.css y el comportamiento en assets/eciguia.js.

El HTML se genera en una sola línea a propósito: el chat de Gradio lo pasa por un intérprete de Markdown,
y una línea en blanco dentro de un bloque HTML lo rompería.
"""

from __future__ import annotations

import html
import json
import math
import re
import uuid
from functools import lru_cache
from pathlib import Path

from eciguia import config, prompts

ASSETS = config.ROOT / "assets"

ROUTES = {
    "documentos": ("Reglamentos", "book-open"),
    "herramienta": ("Herramienta MCP", "wrench"),
    "fuera_de_alcance": ("Fuera de alcance", "ban"),
    "entrada_invalida": ("Entrada no válida", "triangle-alert"),
}

CATEGORIAS = [
    ("Prácticas y opción de grado", "briefcase", [
        "¿La práctica profesional puede ser de medio tiempo?",
        "¿Qué promedio necesito para hacer la práctica docente?",
    ]),
    ("Calendario 2027", "calendar-days", [
        "¿Hasta cuándo puedo cancelar el semestre?",
        "¿Cuándo empiezan las clases de 2027-1?",
    ]),
    ("Matrícula y costos", "banknote", [
        "¿Cuánto cuesta la matrícula de ingeniería en 2027?",
        "¿Cuánto valen los derechos de grado?",
    ]),
    ("Plan de estudios", "graduation-cap", [
        "¿En qué semestre se ve Arquitecturas de Software?",
        "¿Cuántos créditos tiene el plan nuevo de Ingeniería de Sistemas?",
    ]),
]
SUGERENCIAS_NO_SE = [
    "¿Cuántas asignaturas puedo cancelar en un semestre?",
    "¿Qué promedio necesito para pedir créditos adicionales?",
    "¿Qué requisitos hay para hacer doble programa?",
]


# ---------------------------------------------------------------- piezas básicas

def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


@lru_cache(maxsize=None)
def _svg(name: str) -> str:
    raw = (ASSETS / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    return " ".join(raw.split())


def icon(name: str, cls: str = "") -> str:
    """Ícono de Lucide en línea (hereda el color del texto)."""
    return _svg(name).replace('class="lucide', f'aria-hidden="true" class="eg-icon {cls} lucide', 1)


# Geometría del logotipo (diseño del autor): marco de cuatro puntas como rosa de los vientos, aguja norte
# roja y aguja sur del color del marco, con un anillo que separa el centro. viewBox 0 0 256 256.
LOGO_MARCO = ("M128 24 C150 74 182 106 232 128 C182 150 150 182 128 232 "
              "C106 182 74 150 24 128 C74 106 106 74 128 24Z")
LOGO_NORTE = "M128 72 L146 128 L128 118 L110 128 Z"
LOGO_SUR = "M128 184 L146 128 L128 138 L110 128 Z"


def logo_svg(size: int = 40) -> str:
    """Logotipo de EciGuía. Los colores salen del CSS (.eg-logo-*), así se adapta al modo claro u oscuro."""
    return (f'<svg class="eg-logo" width="{size}" height="{size}" viewBox="0 0 256 256" fill="none" role="img" aria-label="Logotipo de EciGuía">'
            f'<path class="eg-logo-frame" d="{LOGO_MARCO}"/>'
            f'<path class="eg-logo-north" d="{LOGO_NORTE}"/>'
            f'<path class="eg-logo-south" d="{LOGO_SUR}"/>'
            f'<circle class="eg-logo-gap" cx="128" cy="128" r="14"/>'
            f'<circle class="eg-logo-dot" cx="128" cy="128" r="8"/></svg>')


# Colores del logo en archivos sueltos (README, video, favicon): (marco y aguja sur, norte, anillo, fondo)
LOGO_MODOS = {
    "claro": ("#111827", "#E53935", "#ffffff", None),
    "oscuro": ("#e7eaf0", "#E53935", "#12151a", None),
    "favicon": ("#e7eaf0", "#E53935", "#1a1e25", "#1a1e25"),
}


def logo_svg_archivo(modo: str) -> str:
    """El mismo logo como SVG independiente, con colores fijos (no depende del CSS de la app)."""
    tinta, norte, anillo, fondo = LOGO_MODOS[modo]
    caja = f'<rect width="256" height="256" rx="56" fill="{fondo}"/>' if fondo else ""
    escala = ' transform="translate(23 23) scale(0.82)"' if fondo else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="512" height="512" fill="none">{caja}<g{escala}>'
            f'<path d="{LOGO_MARCO}" stroke="{tinta}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{LOGO_NORTE}" fill="{norte}"/><path d="{LOGO_SUR}" fill="{tinta}"/>'
            f'<circle cx="128" cy="128" r="14" fill="{anillo}"/><circle cx="128" cy="128" r="8" fill="{tinta}"/></g></svg>')


def ask_button(pregunta: str) -> str:
    """Botón que escribe y envía la pregunta (ver assets/eciguia.js)."""
    return f'<button type="button" class="eg-ask" data-q="{esc(pregunta)}">{esc(pregunta)}</button>'


# ---------------------------------------------------------------- texto de la respuesta

CITA = re.compile(r"\[(\d+(?:\s*[,y]\s*\d+)*)\]")


def _inline(text: str) -> str:
    text = esc(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def answer_html(text: str, n_sources: int = 0) -> str:
    """Markdown sencillo (párrafos, listas, negritas) a HTML, con las citas [n] convertidas en botones."""
    bloques, lista, tipo = [], [], None
    for linea in [l.strip() for l in text.strip().splitlines()]:
        m = re.match(r"^(?:[-*•]|(\d+)[.)])\s+(.*)", linea)
        if m:
            nuevo = "ol" if m.group(1) else "ul"
            if lista and nuevo != tipo:
                bloques.append(f"<{tipo}>{''.join(lista)}</{tipo}>")
                lista = []
            tipo = nuevo
            lista.append(f"<li>{_inline(m.group(2))}</li>")
            continue
        if lista:
            bloques.append(f"<{tipo}>{''.join(lista)}</{tipo}>")
            lista = []
        if linea:
            bloques.append(f"<p>{_inline(linea)}</p>")
    if lista:
        bloques.append(f"<{tipo}>{''.join(lista)}</{tipo}>")
    cuerpo = "".join(bloques)

    def chip(match: re.Match) -> str:
        nums = [n for n in re.findall(r"\d+", match.group(1)) if 1 <= int(n) <= n_sources]
        return "".join(f'<button type="button" class="eg-cite" data-cite="{n}" aria-label="Ver fuente {n}">{n}</button>'
                       for n in nums)
    return CITA.sub(chip, cuerpo)


# ---------------------------------------------------------------- proceso en vivo

def _pasos(state: dict, nodos: list[str]) -> list[tuple[str, str]]:
    """Lista de (etiqueta, estado) donde estado es 'hecho', 'activo' o 'pendiente'."""
    route = state.get("route") if "router" in nodos else None
    pasos = [("Clasificar la pregunta", "router")]
    if route == "documentos":
        pasos += [("Buscar en 13 documentos oficiales", "recuperar"), ("Redactar la respuesta con citas", "_redactar")]
    elif route == "herramienta":
        herramienta = state.get("tool_name")
        etiqueta = f"Consultar la herramienta {herramienta}" if herramienta and herramienta != "ninguna" else "Elegir y consultar una herramienta MCP"
        pasos += [(etiqueta, "usar_herramienta"), ("Redactar la respuesta", "responder_herramienta")]
    elif route == "fuera_de_alcance":
        pasos += [("Responder que está fuera de alcance", "rechazar")]
    hechos = set(nodos)
    salida, activo_puesto = [], False
    for etiqueta, nodo in pasos:
        listo = nodo in hechos or (nodo == "_redactar" and hechos & {"responder_documentos", "sin_informacion"})
        if listo:
            salida.append((etiqueta, "hecho"))
        elif not activo_puesto:
            salida.append((etiqueta, "activo"))
            activo_puesto = True
        else:
            salida.append((etiqueta, "pendiente"))
    if route is None:  # todavía no se sabe la ruta: se insinúa el resto
        salida.append(("Buscar en documentos o consultar herramientas", "pendiente"))
    return salida


def progress_html(state: dict, nodos: list[str]) -> str:
    items = []
    for etiqueta, estado in _pasos(state, nodos):
        ico = {"hecho": icon("circle-check"), "activo": icon("loader-circle", "eg-spin"), "pendiente": '<span class="eg-dot"></span>'}[estado]
        items.append(f'<li class="eg-step is-{estado}">{ico}<span>{esc(etiqueta)}</span></li>')
    return f'<ol class="eg-steps" aria-live="polite">{"".join(items)}</ol>'


def streaming_html(state: dict, nodos: list[str], parcial: str = "") -> str:
    texto = f'<div class="eg-answer eg-typing">{answer_html(parcial)}<span class="eg-caret"></span></div>' if parcial.strip() else ""
    return f'<div class="eg-msg">{progress_html(state, nodos)}{texto}</div>'


# ---------------------------------------------------------------- respuesta final

def _fragmento(hit) -> str:
    texto = hit.doc.page_content.split("\n", 1)[-1]
    texto = " ".join(texto.split())
    return texto if len(texto) <= 700 else texto[:700].rsplit(" ", 1)[0] + "…"


def sources_html(state: dict, uid: str) -> str:
    hits = state.get("hits") or []
    sources = state.get("sources") or []
    if not sources:
        return ""
    tarjetas = []
    if hits:  # ruta de documentos: cada cita con su fragmento real
        for n, hit in enumerate(hits, start=1):
            meta = hit.doc.metadata
            seccion = f' · {esc(meta["section"].rstrip(":"))}' if meta.get("section") else ""
            tarjetas.append(
                f'<details class="eg-src" id="src-{uid}-{n}" data-src="{n}"><summary>'
                f'<span class="eg-src-n">{n}</span><span class="eg-src-title">{esc(meta["title"])}{seccion}</span>'
                f'<span class="eg-src-page">pág. {esc(meta["page"])}</span>{icon("chevron-down", "eg-chev")}</summary>'
                f'<blockquote class="eg-quote">{esc(_fragmento(hit))}</blockquote></details>')
    else:  # herramientas: la fuente es el dato oficial consultado
        for fuente in sources:
            tarjetas.append(f'<div class="eg-src eg-src-tool">{icon("database")}<span class="eg-src-title">{esc(fuente)}</span></div>')
    return f'<div class="eg-sources"><div class="eg-sources-h">{icon("file-text")}Fuentes</div>{"".join(tarjetas)}</div>'


def how_html(state: dict) -> str:
    etiqueta, ico = ROUTES.get(state.get("route"), (state.get("route", ""), "info"))
    filas = [("Ruta", f'{icon(ico)} {esc(etiqueta)}')]
    if state.get("tool_name") and state["tool_name"] != "ninguna":
        args = json.dumps(state.get("tool_args", {}), ensure_ascii=False)
        filas.append(("Herramienta", f'<code>{esc(state["tool_name"])}</code>'))
        filas.append(("Argumentos", f'<code class="eg-args">{esc(args)}</code>'))
    if state.get("hits"):
        filas.append(("Distancia de los fragmentos", esc(", ".join(f"{h.distance:.2f}" for h in state["hits"]))
                      + f' <span class="eg-muted">(umbral {str(config.MAX_DISTANCE).replace(".", ",")})</span>'))
    elif state.get("route") == "documentos":
        filas.append(("Fragmentos", "ninguno superó el umbral de relevancia"))
    filas.append(("Modelo", esc(f"{config.LLM_MODEL} en Ollama, local")))
    filas.append(("Tiempo", esc(f"{state.get('latency_s', 0)} s")))
    cuerpo = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in filas)
    return f'<details class="eg-how"><summary>{icon("info")}¿Cómo lo supe?{icon("chevron-down", "eg-chev")}</summary><dl>{cuerpo}</dl></details>'


def _tarjeta(tipo: str, ico: str, titulo: str, texto: str, sugerencias: list[str]) -> str:
    botones = "".join(ask_button(q) for q in sugerencias)
    extra = f'<div class="eg-suggest"><span>Puedo ayudarte, por ejemplo, con:</span>{botones}</div>' if botones else ""
    return (f'<div class="eg-card eg-card-{tipo}">{icon(ico, "eg-card-icon")}<div>'
            f'<div class="eg-card-title">{esc(titulo)}</div><p>{esc(texto)}</p>{extra}</div></div>')


def final_html(state: dict) -> str:
    uid = uuid.uuid4().hex[:8]
    route = state.get("route")
    answer = state.get("answer", "")
    if route == "entrada_invalida":
        ico = "shield-alert" if state.get("validation") == "inyeccion" else "triangle-alert"
        titulo = {"vacia": "Falta la pregunta", "muy_larga": "La pregunta es muy larga",
                  "sin_texto": "No reconozco una pregunta", "inyeccion": "No puedo cambiar mis instrucciones"}.get(
                      state.get("validation"), "Entrada no válida")
        return f'<div class="eg-msg">{_tarjeta("warn", ico, titulo, answer, SUGERENCIAS_NO_SE[:2])}</div>'

    partes = [progress_html(state, ["router", "recuperar", "sin_informacion", "responder_documentos",
                                    "usar_herramienta", "responder_herramienta", "rechazar"])]
    if route == "fuera_de_alcance":
        partes.append(_tarjeta("info", "ban", "Eso está fuera de mi alcance", prompts.OUT_OF_SCOPE,
                               [q for _, _, qs in CATEGORIAS for q in qs][::3]))
    elif route == "documentos" and answer.startswith("No encontré"):
        partes.append(_tarjeta("info", "circle-help", "No está en mis documentos",
                               "No encontré esa información en los documentos que tengo, y prefiero no inventarla. "
                               "Consulta con la decanatura de tu programa o con Registro Académico.", SUGERENCIAS_NO_SE))
    else:
        n = len(state.get("hits") or [])
        partes.append(f'<div class="eg-answer">{answer_html(answer, n)}</div>')
        partes.append(sources_html(state, uid))
    partes.append(how_html(state))
    return f'<div class="eg-msg" data-uid="{uid}">{"".join(partes)}</div>'


def error_html(exc: Exception) -> str:
    return (f'<div class="eg-msg">{_tarjeta("error", "triangle-alert", "No pude responder", f"El modelo no respondió ({type(exc).__name__}). Revisa que Ollama esté abierto (ollama list) y que el índice exista (uv run python -m eciguia.ingest). Si Ollama se trabó, ciérralo y ábrelo de nuevo.", [])}</div>')


# ---------------------------------------------------------------- decoración del estado vacío

def mancha_de_puntos(color: str, acento: str, semilla: int, columnas: int = 46, filas: int = 28,
                     paso: float = 8.0) -> str:
    """SVG de una mancha orgánica de puntos sobre una retícula (diseño propio, generado con semilla fija).
    Unos "centros" encadenados en diagonal forman un campo; cada celda lleva punto si el campo supera un
    umbral, con huecos al azar y algunos puntos sueltos, para que se vea orgánica y no geométrica."""
    import random

    rng = random.Random(semilla)
    x, y, centros = columnas * 0.15, filas * 0.2, []
    for _ in range(6):  # camino serpenteante, como un río de puntos
        centros.append((x, y, rng.uniform(2.2, 4.2)))
        x += rng.uniform(4.5, 8.0)
        y += rng.uniform(-1.5, 4.5)
    puntos = []
    for i in range(columnas):
        for j in range(filas):
            campo = sum(math.exp(-((i - cx) ** 2 + (j - cy) ** 2) / (2 * s * s)) for cx, cy, s in centros)
            if (campo > 0.55 and rng.random() > 0.18) or rng.random() < 0.012:
                fill = acento if rng.random() < 0.06 else color
                puntos.append(f'<circle cx="{i * paso + 4:.0f}" cy="{j * paso + 4:.0f}" r="1.5" fill="{fill}"/>')
    ancho, alto = columnas * paso, filas * paso
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho:.0f} {alto:.0f}" '
            f'width="{ancho:.0f}" height="{alto:.0f}">{"".join(puntos)}</svg>')


def decor_css() -> str:
    """CSS con las manchas del estado vacío incrustadas (claro y oscuro). Va como CSS y no como HTML porque
    el chat de Gradio filtra el HTML de su estado vacío."""
    from urllib.parse import quote

    def url(svg: str) -> str:
        return f'url("data:image/svg+xml,{quote(svg)}")'

    claro_a = url(mancha_de_puntos("rgba(35,38,43,0.30)", "#a6192e", semilla=7))
    claro_b = url(mancha_de_puntos("rgba(35,38,43,0.22)", "#a6192e", semilla=21, columnas=34, filas=20))
    oscuro_a = url(mancha_de_puntos("rgba(231,234,240,0.22)", "#e0566a", semilla=7))
    oscuro_b = url(mancha_de_puntos("rgba(231,234,240,0.16)", "#e0566a", semilla=21, columnas=34, filas=20))
    return (f".eg-empty::before {{ background-image: {claro_a}; }}\n"
            f".eg-empty::after {{ background-image: {claro_b}; }}\n"
            f".dark .eg-empty::before {{ background-image: {oscuro_a}; }}\n"
            f".dark .eg-empty::after {{ background-image: {oscuro_b}; }}\n")


# ---------------------------------------------------------------- pantallas fijas

def header_html() -> str:
    return (f'<header class="eg-header">{logo_svg(44)}<div class="eg-brand"><div class="eg-name">EciGuía</div>'
            f'<div class="eg-tagline">Asistente académico de la Escuela Colombiana de Ingeniería. Responde con documentos oficiales.</div></div>'
            f'<button type="button" class="eg-theme" aria-label="Cambiar entre modo claro y oscuro">{icon("moon", "eg-moon")}{icon("sun", "eg-sun")}</button></header>')


def placeholder_html() -> str:
    grupos = "".join(
        f'<section class="eg-cat"><div class="eg-cat-h">{icon(ico)}{esc(nombre)}</div>{"".join(ask_button(q) for q in qs)}</section>'
        for nombre, ico, qs in CATEGORIAS)
    return (f'<div class="eg-empty">{logo_svg(52)}<h2>¿Qué necesitas saber de la Escuela?</h2>'
            f'<p>Respondo con reglamentos, el calendario 2027, los valores de matrícula y el plan de estudios, y te digo de dónde sale cada dato.</p>'
            f'<div class="eg-cats">{grupos}</div></div>')


def sidebar_html() -> str:
    documentos = sorted(config.DOCUMENT_TITLES.values())
    datos = [("calendar-days", "Calendario académico 2027", "fechas de todos los periodos"),
             ("banknote", "Valores 2027", "matrícula (Res. 014 de 2026) y derechos pecuniarios (Res. 016 de 2026)"),
             ("graduation-cap", "Plan de estudios de Ingeniería de Sistemas", "desde 2025-1 y anterior"),
             ("scale", "Promedio ponderado", "cálculo por créditos")]
    no_sabe = ["Reglamento Estudiantil completo y vigente (asistencia, notas mínimas, pérdida de cupo)",
               "Planes de estudio de otros programas y prerrequisitos", "Posgrados"]
    docs = "".join(f"<li>{esc(t)}</li>" for t in documentos)
    data = "".join(f'<li>{icon(i)}<div><strong>{esc(t)}</strong><span>{esc(d)}</span></div></li>' for i, t, d in datos)
    nope = "".join(f"<li>{esc(t)}</li>" for t in no_sabe)
    return (f'<div class="eg-side"><h3>{icon("library")}Qué sé</h3>'
            f'<p class="eg-muted">Respondo solo con estas fuentes oficiales y cito documento y página.</p>'
            f'<h4>{len(documentos)} documentos normativos</h4><ul class="eg-docs">{docs}</ul>'
            f'<h4>Datos que consulto con herramientas</h4><ul class="eg-data">{data}</ul>'
            f'<h4>Lo que no sé</h4><ul class="eg-nope">{nope}</ul>'
            f'<p class="eg-note">{icon("clock")}Corre 100 % local con Ollama: cada respuesta tarda unos 15 s.</p>'
            f'<p class="eg-note">{icon("info")}Proyecto estudiantil (IA Generativa 2026-2). No es un canal oficial de la Escuela; ante cualquier duda, manda el documento oficial.</p></div>')
