# /// script
# requires-python = ">=3.11"
# dependencies = ["imageio-ffmpeg>=0.5", "numpy"]
# ///
"""Monta el video final con la narración del autor: cada imagen sincronizada con lo que dice la voz.

    uv run docs/video/tools/montar.py

Entradas (no se versionan):
    docs/video/audio/voz/01.mp4 … 07.mp4   narración, un bloque por audio
    docs/video/audio/voz/palabras.json     marcas de tiempo por palabra (transcribir.py)
    docs/video/raw/demo/<toma>.mp4 + .json tomas de grabar_demo.py
    docs/video/raw/demo/movimiento.json    cuánto cambia cada cuadro de cada toma (movimiento.py)

Cómo sincroniza:
- La voz manda. Entre algunas frases se agregan pausas (PAUSAS) para que la app alcance a mostrar lo que se
  está diciendo, por ejemplo la espera del modelo.
- Las escenas animadas (motion/escenas.html) tienen cada elemento atado al segundo de la narración en que se
  nombra; aquí solo se calcula el desfase de cada escena.
- Cada toma de la app tiene anclas: "este instante de la toma va cuando la voz dice tal palabra". Entre dos
  anclas, lo que se mueve (cursor, cámara, texto) va a velocidad real y los tramos quietos se estiran o se
  acortan. La espera del modelo ("u") se acelera de forma pareja, y el contador en pantalla muestra el
  tiempo real.

Salida: docs/video/final/eciguia_final.mp4, eciguia_final.srt (subtítulos) y linea_de_tiempo_final.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np

TOOLS = Path(__file__).resolve().parent
VIDEO = TOOLS.parent
VOZ = VIDEO / "audio" / "voz"
RAW = VIDEO / "raw" / "demo"
TMP = VIDEO / "final" / "v3_segmentos"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
T = 0.7        # duración de cada transición
INICIO = 0.6   # segundos antes de la primera palabra
COLA = 2.8     # cierre después de la última palabra
UMBRAL = 0.004  # diferencia media entre cuadros (escala 0-255) a partir de la cual hay movimiento

# silencio entre un bloque de audio y el siguiente
GAP = {"02": 0.6, "03": 1.1, "04": 1.0, "05": 1.0, "06": 1.0, "07": 1.3}
# (segundo del audio en que empieza la frase, pausa que se inserta antes)
PAUSAS = {
    "03": [(19.88, 1.2), (26.98, 0.8)],
    "04": [(12.0, 2.2), (16.08, 0.5), (19.76, 1.6), (35.8, 2.2)],
    "05": [(5.32, 2.2), (8.94, 0.8), (11.54, 0.8), (23.7, 1.2)],
}

# inicio de cada escena: 0, "gap:NN" (mitad del silencio antes del bloque NN) o (bloque, segundo del audio, ajuste)
# anclas de las tomas: (segundo de la toma, momento de la voz[, "u" = tramo acelerado parejo])
ESCENAS = [
    dict(n="hook", m="01", ini=0, tr="smoothleft"),
    dict(n="problema", m="01", ini=("01", 10.0), tr="zoomin"),
    dict(n="flujo", m="02", ini="gap:02", tr="circleopen"),
    dict(n="t1_reglamento", ini="gap:03", tr="smoothleft", fin=57.3, anclas=[
        (2.3, ("03", 4.55)), (5.45, ("03", 7.5)), (30.68, ("03", 17.08, -0.15), "u"),
        (41.1, ("03", 22.0)), (50.0, ("03", 26.98, 0.45))]),
    dict(n="t2_calendario", ini="gap:04", tr="smoothup", fin=52.5, anclas=[
        (2.5, ("04", 3.9, 0.25)), (37.36, ("04", 9.4), "u"), (46.9, ("04", 12.0, 0.6))]),
    dict(n="t3_matricula", ini=("04", 16.08, -0.3), tr="circleopen", fin=39.5, anclas=[
        (2.3, ("04", 16.9)), (5.65, ("04", 19.2)), (28.07, ("04", 19.76, -0.25), "u"), (35.6, ("04", 24.94, -0.3))]),
    dict(n="t4_plan", ini=("04", 28.38, -0.3), tr="smoothleft", fin=33.9, anclas=[
        (2.2, ("04", 29.6)), (4.1, ("04", 32.9)), (7.4, ("04", 35.3)), (25.43, ("04", 35.8, -0.25), "u")]),
    dict(n="t5_civil", ini="gap:05", tr="smoothup", fin=28.9, anclas=[
        (2.3, ("05", 1.82)), (5.95, ("05", 4.9)), (20.66, ("05", 5.32, -0.2), "u")]),
    dict(n="t6_faltas", ini=("05", 8.94, -0.35), tr="smoothleft", fin=25.3, anclas=[
        (2.3, ("05", 9.6)), (6.45, ("05", 11.54, -0.1)), (17.56, ("05", 13.52, -0.2), "u")]),
    dict(n="t7_pelicula", ini=("05", 20.56, -0.3), tr="smoothup", fin=17.1, anclas=[
        (2.3, ("05", 21.2)), (5.45, ("05", 23.25)), (10.02, ("05", 23.7), "u")]),
    dict(n="t8_inyeccion", ini="gap:06", tr="smoothleft", fin=20.83, anclas=[
        (2.3, ("06", 2.76)), (5.75, ("06", 5.4)), (6.16, ("06", 5.8), "u"), (17.2, ("06", 11.48, 0.4))]),
    dict(n="t9_error", ini=("06", 14.84, -0.3), tr="fadeblack", fin=20.9, anclas=[
        (2.3, ("06", 15.6)), (5.65, ("06", 17.9)), (13.28, ("06", 20.14, -0.3), "u")]),
    dict(n="resultados", m="07", ini="gap:07", tr="smoothup"),
    dict(n="evolucion", m="07", ini=("07", 17.84, -0.3), tr="smoothleft"),
    dict(n="limites", m="07", ini=("07", 26.18, -0.25), tr="circleclose"),
    dict(n="cierre", m="07", ini=("07", 35.96, -0.3), tr=None),
]

# correcciones de la transcripción automática para los subtítulos
CORRECCIONES = {
    "ese guía": "EciGuía", "Ese guía": "EciGuía", "en pdf": "en PDF", "de la escuela": "de la Escuela", "un Router": "un router", "chatbos": "chatbot", "LandGraph": "LangGraph",
    "un modelo Coentus .5 corriendo al local con olama": "el modelo Qwen 2.5 corriendo en local con Ollama",
    "o sarraga": "usa RAG", "sintando": "citando", "las respuestas": "la respuesta",
    "llama herramientas de un buen servidor": "llama a herramientas de un servidor",
    "la muestra": "la app muestra", "los tres documentos": "los trece documentos",
    "es del artículo": "es el artículo", "Pagina": "Página", "como lo supe": "«¿Cómo lo supe?»",
    "del cero como 45": "de cero coma cuarenta y cinco",
    "llama la herramienta en si pide el calendario": "llama a la herramienta MCP del calendario",
    "matrícula ingeniería": "matrícula de ingeniería",
    "La herramienta de volver raga oficial según el dinero socioeconómico y la cita a la resolución de la rectoría":
        "La herramienta devuelve el rango oficial según el nivel socioeconómico y cita la resolución de rectoría",
    "tala oficial": "tabla oficial", "semestras": "semestre", "arquitectura de sofá": "Arquitecturas de Software",
    "SETSTO": "sexto", "Distinque": "Distingue", "no están sus documentos": "no está en mis documentos",
    "superlumbral de revelación": "supera el umbral de relevancia", "a quien": "a quién", "reúdo": "router",
    "panel QC": "panel «Qué sé»", "aquí apagueo la más propósito": "aquí apagué Ollama a propósito",
    "no se cada vez ni siquiera cargando": "no se cae ni se queda cargando", "el porqué": "por qué",
    "promos": "prompts", "aceptaba en": "acertaba el", "7 .000 millones": "7000 millones",
    "lo que están sus": "lo que está en sus", "inscripciones": "instrucciones", "el 97 % de": "el 97 % en",
}

PAL = json.loads((VOZ / "palabras.json").read_text(encoding="utf-8"))


class Bloque:
    """Un audio de la narración, con sus pausas insertadas, ubicado en el video."""

    def __init__(self, k: str, inicio: float):
        palabras = PAL[k]
        self.k, self.C = k, inicio
        self.a0, self.a1 = max(palabras[0][0] - 0.12, 0.0), palabras[-1][1] + 0.35
        self.cortes = []
        for frase, pausa in PAUSAS.get(k, []):
            i = next(j for j, w in enumerate(palabras) if abs(w[0] - frase) < 0.02)
            self.cortes.append(((palabras[i - 1][1] + palabras[i][0]) / 2, pausa))

    def G(self, t: float) -> float:
        """Segundo del video en que suena el segundo t de este audio."""
        return self.C + (t - self.a0) + sum(p for c, p in self.cortes if t >= c)

    @property
    def fin(self) -> float:
        return self.G(self.a1)

    def piezas(self) -> list[tuple[float, float, float]]:
        limites = [self.a0] + [c for c, _ in self.cortes] + [self.a1]
        return [(a, b, self.G(a)) for a, b in zip(limites, limites[1:])]


BLOQUES: dict[str, Bloque] = {}
inicio = INICIO
for k in sorted(PAL):
    inicio += GAP.get(k, 0.0)
    BLOQUES[k] = Bloque(k, inicio)
    inicio = BLOQUES[k].fin
FIN = BLOQUES["07"].fin + COLA


def g(spec) -> float:
    if spec == 0:
        return 0.0
    if isinstance(spec, str):
        k = spec.split(":")[1]
        return (BLOQUES[f"{int(k) - 1:02d}"].fin + BLOQUES[k].C) / 2
    k, t, *ajuste = spec
    return BLOQUES[k].G(t) + (ajuste[0] if ajuste else 0.0)


def ffmpeg(*args: str) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def ventanas() -> list[tuple[float, float]]:
    inicios = [g(e["ini"]) for e in ESCENAS]
    out = []
    for i, b in enumerate(inicios):
        c0 = 0.0 if i == 0 else b - T / 2
        c1 = inicios[i + 1] + T / 2 if i + 1 < len(inicios) else FIN
        out.append((c0, c1))
    return out


def toma(escena: dict, c0: float, c1: float, salida: Path, escribir: bool = True) -> None:
    """Re-temporiza una toma para que sus anclas caigan donde la voz las nombra."""
    n = escena["n"]
    d = np.array(json.loads((RAW / "movimiento.json").read_text())[n])
    mov = np.convolve((d > UMBRAL).astype(int), np.ones(9, int), "same") > 0  # con margen de 4 cuadros
    N = len(d)
    puntos = [(0.0, 0.0, "s")] + [(r, g(s) - c0, (m[0] if m else "s")) for r, s, *m in escena["anclas"]]
    puntos.append((escena["fin"], c1 - c0, "s"))
    dur = np.zeros(N)
    for (r0, g0, _), (r1, g1, modo) in zip(puntos, puntos[1:]):
        i0, i1 = round(r0 * FPS), min(round(r1 * FPS), N)
        tramo, objetivo = mov[i0:i1], g1 - g0
        if objetivo <= 0:
            raise SystemExit(f"{n}: el ancla de {r1} s cae antes que la anterior ({g0:.2f} -> {g1:.2f})")
        movil, quieto = tramo.sum() / FPS, (len(tramo) - tramo.sum()) / FPS
        if modo == "u" or quieto == 0:
            w_mov = w_qui = objetivo / ((i1 - i0) / FPS)
        elif objetivo >= movil:
            w_mov, w_qui = 1.0, (objetivo - movil) / quieto
        else:
            w_mov, w_qui = objetivo / movil, 0.0
        dur[i0:i1] = np.where(tramo, w_mov, w_qui) / FPS
        print(f"   {r0:5.1f}-{r1:5.1f} s de la toma -> {objetivo:4.1f} s  "
              f"({'parejo x' + format((r1 - r0) / objetivo, '.1f') if modo == 'u' else f'movimiento x{1 / w_mov:.1f}, quieto x{w_qui:.2f}'})")
    if not escribir:
        return
    inicios = np.concatenate([[0.0], np.cumsum(dur)])
    n_out = round((c1 - c0) * FPS)
    idx = np.clip(np.searchsorted(inicios, (np.arange(n_out) + 0.5) / FPS, side="right") - 1, 0, N - 1)

    lector = imageio_ffmpeg.read_frames(str(RAW / f"{n}.mp4"))
    next(lector)
    escritor = imageio_ffmpeg.write_frames(str(salida), (1920, 1080), fps=FPS, codec="libx264", macro_block_size=1,
                                           pix_fmt_out="yuv420p", output_params=["-crf", "17", "-preset", "medium"])
    escritor.send(None)
    j, ultimo = 0, None
    for i, cuadro in enumerate(lector):
        while j < n_out and idx[j] == i:
            escritor.send(cuadro)
            j += 1
        ultimo = cuadro
        if j >= n_out:
            break
    while j < n_out:  # por si la toma se acabó antes
        escritor.send(ultimo)
        j += 1
    escritor.close()
    lector.close()


def subtitulos() -> str:
    def hms(t: float) -> str:
        ms = round(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    bloques, n = [], 0
    for k, palabras in PAL.items():
        frase = []
        for s, e, w in palabras:
            frase.append((s, e, w))
            if w.endswith((".", "?", "!")) or (s, e, w) == tuple(palabras[-1]):
                texto = " ".join(x[2] for x in frase)
                for mal, bien in CORRECCIONES.items():
                    texto = texto.replace(mal, bien)
                n += 1
                bloques.append(f"{n}\n{hms(BLOQUES[k].G(frase[0][0]))} --> {hms(BLOQUES[k].G(frase[-1][1]) + 0.25)}\n{texto}\n")
                frase = []
    return "\n".join(bloques)


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    vent = ventanas()
    if "--plan" in sys.argv:  # solo revisa los tiempos, sin renderizar
        for e, (c0, c1) in zip(ESCENAS, vent):
            print(f"{e['n']:<14} {c0:6.2f}-{c1:6.2f} s")
            if "anclas" in e:
                toma(e, c0, c1, Path(), escribir=False)
        print(f"total {FIN:.1f} s")
        return

    # 1. escenas animadas, alineadas con su bloque de audio
    args = []
    for e, (c0, c1) in zip(ESCENAS, vent):
        if "m" in e:
            b = BLOQUES[e["m"]]
            args.append(f"{e['n']}:{c1 - c0:.3f}:{b.C - b.a0 - c0:.3f}")
    subprocess.run([os.environ.get("UV", "uv"), "run", str(TOOLS / "render_motion.py"), *args], check=True)

    # 2. tomas de la app, re-temporizadas
    partes = []
    for e, (c0, c1) in zip(ESCENAS, vent):
        if "m" in e:
            partes.append(VIDEO / "motion" / "render" / f"{e['n']}.mp4")
        else:
            print(f"{e['n']}  ({c0:.1f}-{c1:.1f} s)")
            salida = TMP / f"{e['n']}.mp4"
            toma(e, c0, c1, salida)
            partes.append(salida)

    # 3. unir con transiciones + narración
    entradas = [x for p in partes for x in ("-i", str(p))]
    filtros = [f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p,setsar=1[v{i}]" for i in range(len(partes))]
    previo = "[v0]"
    for i in range(1, len(partes)):
        filtros.append(f"{previo}[v{i}]xfade=transition={ESCENAS[i - 1]['tr']}:duration={T}:offset={vent[i][0]:.3f}[x{i}]")
        previo = f"[x{i}]"
    filtros.append(f"{previo}fade=t=in:st=0:d=0.5,fade=t=out:st={FIN - 1.0:.3f}:d=1.0[v]")

    piezas = [(k, a, b, at) for k, blo in BLOQUES.items() for a, b, at in blo.piezas()]
    base = len(partes)
    for j, (k, a, b, at) in enumerate(piezas):
        entradas += ["-i", str(VOZ / f"{k}.mp4")]
        ms = round(at * 1000)
        filtros.append(f"[{base + j}:a]asetpts=PTS-STARTPTS,atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                       f"afade=t=in:d=0.03,afade=t=out:st={b - a - 0.06:.3f}:d=0.06,adelay={ms}:all=1[p{j}]")
    filtros.append("".join(f"[p{j}]" for j in range(len(piezas))) + f"amix=inputs={len(piezas)}:normalize=0,"
                   "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=150:makeup=2,"
                   f"loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000,apad,atrim=0:{FIN:.3f}[a]")
    final = VIDEO / "final" / "eciguia_final.mp4"
    ffmpeg(*entradas, "-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]", "-t", f"{FIN:.3f}",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(final))

    (VIDEO / "final" / "eciguia_final.srt").write_text(subtitulos(), encoding="utf-8")
    linea = [{"escena": e["n"], "inicio": round(g(e["ini"]), 2)} for e in ESCENAS]
    linea += [{"audio": k, "inicio": round(b.C, 2), "fin": round(b.fin, 2)} for k, b in BLOQUES.items()]
    (VIDEO / "final" / "linea_de_tiempo_final.json").write_text(json.dumps(linea, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in linea:
        if "escena" in item:
            print(f"{int(item['inicio'] // 60)}:{item['inicio'] % 60:04.1f}  {item['escena']}")
    print(f"\nVideo: {final}  ({int(FIN // 60)}:{FIN % 60:04.1f}, límite de la rúbrica 5:00)")
    if FIN > 300:
        raise SystemExit("ERROR: el video pasa de 5 minutos")


if __name__ == "__main__":
    main()
