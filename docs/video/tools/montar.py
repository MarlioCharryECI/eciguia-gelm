# /// script
# requires-python = ">=3.11"
# dependencies = ["imageio-ffmpeg>=0.5"]
# ///
"""Monta el video final a partir de las diapositivas, los clips de la demo y la narración.

    uv run docs/video/tools/montar.py

Entradas:  docs/video/narracion.json, audio/*.mp3 + duraciones.json, slides/*.png, raw/E06_q*.webm + .json
Salida:    docs/video/final/eciguia_video.mp4 (1920x1080, 30 fps, H.264 + AAC, audio a -16 LUFS)

Reglas de honestidad (PLAN_VIDEO.md): las respuestas de la demo no se alteran; la espera del modelo se
acelera y el rótulo dice cuánto se aceleró y cuánto tardó de verdad.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

VIDEO = Path(__file__).resolve().parents[1]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SEG = VIDEO / "final" / "segmentos"
ANTES, DESPUES = 0.4, 0.7      # silencio antes y después de cada narración (s)
ESPERA = 2.5                   # duración en pantalla de la espera del modelo, ya acelerada (s)
FUNDIDO = 0.25
CODEC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]

# Frase de la narración en la que aparece cada etapa de una diapositiva (la etapa 0 está desde el inicio)
ETAPAS = {
    "S2_problema": ["Un chatbot genérico"],
    "S3_arquitectura": ["Si es sobre reglamentos", "Si necesita un dato exacto", "Y si no es un tema"],
    "S5_resultados": ["respondió bien", "rechazó todas", "Al ampliar", "Y el umbral"],
}


def ffmpeg(*args: str) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def momento(texto: str, frase: str, dur_narracion: float) -> float:
    """Segundo aproximado en que la narración dice `frase`, por proporción de caracteres."""
    i = texto.find(frase)
    if i < 0:
        raise ValueError(f"No encuentro '{frase}' en la narración")
    return ANTES + dur_narracion * i / len(texto)


def audio_filtro(indice: int, total: float) -> str:
    ms = int(ANTES * 1000)
    return f"[{indice}:a]adelay={ms}|{ms},apad,atrim=0:{total:.3f},aresample=48000[a]"


def escena_diapositiva(escena: dict, dur: float, salida: Path) -> float:
    total = dur + ANTES + DESPUES
    base = VIDEO / "slides" / escena["id"]
    frases = ETAPAS.get(escena["id"], [])
    cortes = [0.0] + [momento(escena["texto"], f, dur) for f in frases] + [total]
    imagenes = [f"{base}_{i}.png" for i in range(len(frases) + 1)] if frases else [f"{base}.png"]
    entradas, filtros = [], []
    for i, img in enumerate(imagenes):
        entradas += ["-loop", "1", "-framerate", "30", "-t", f"{cortes[i + 1] - cortes[i]:.3f}", "-i", img]
        filtros.append(f"[{i}:v]format=yuv420p,setsar=1[v{i}]")
    n = len(imagenes)
    filtros.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,"
                   f"fade=t=in:st=0:d={FUNDIDO},fade=t=out:st={total - FUNDIDO:.3f}:d={FUNDIDO}[v]")
    filtros.append(audio_filtro(n, total))
    ffmpeg(*entradas, "-i", str(VIDEO / "audio" / f"{escena['id']}.mp3"), "-filter_complex", ";".join(filtros),
           "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", *CODEC, str(salida))
    return total


def escena_demo(escena: dict, dur: float, salida: Path) -> float:
    m = json.loads((VIDEO / "raw" / f"{escena['clip']}.json").read_text(encoding="utf-8"))
    a0, a1 = max(m["t_listo"] - 0.3, 0), m["t_envio"] + 0.4          # escribe la pregunta (velocidad real)
    b0, b1 = a1, m["t_respuesta"]                                     # espera del modelo (acelerada)
    c0, c1 = m["t_respuesta"], m["t_fin"]                             # respuesta (velocidad real)
    factor = max((b1 - b0) / ESPERA, 1.0)
    visual = (a1 - a0) + (b1 - b0) / factor + (c1 - c0)
    total = max(visual, dur + ANTES + DESPUES)
    q = m["id"]
    chips = [VIDEO / "slides" / f"chip_{q}_{fase}.png" for fase in ("entrada", "proceso", "salida")]
    filtros = [
        f"[0:v]trim={a0:.3f}:{a1:.3f},setpts=PTS-STARTPTS,fps=30[a]",
        f"[0:v]trim={b0:.3f}:{b1:.3f},setpts=(PTS-STARTPTS)/{factor:.4f},fps=30[b]",
        f"[0:v]trim={c0:.3f}:{c1:.3f},setpts=PTS-STARTPTS,fps=30[c]",
        "[a][1:v]overlay=0:0[a2]", "[b][2:v]overlay=0:0[b2]", "[c][3:v]overlay=0:0[c2]",
        f"[a2][b2][c2]concat=n=3:v=1:a=0,tpad=stop_mode=clone:stop_duration={total - visual + 0.05:.3f},"
        f"format=yuv420p,setsar=1,fade=t=in:st=0:d={FUNDIDO},fade=t=out:st={total - FUNDIDO:.3f}:d={FUNDIDO}[v]",
        audio_filtro(4, total),
    ]
    ffmpeg("-i", str(VIDEO / "raw" / m["archivo"]), *[x for c in chips for x in ("-i", str(c))],
           "-i", str(VIDEO / "audio" / f"{escena['id']}.mp3"), "-filter_complex", ";".join(filtros),
           "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", *CODEC, str(salida))
    return total


def duracion(path: Path) -> float:
    out = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    h, mi, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def main() -> None:
    guion = json.loads((VIDEO / "narracion.json").read_text(encoding="utf-8"))
    duraciones = json.loads((VIDEO / "audio" / "duraciones.json").read_text(encoding="utf-8"))
    SEG.mkdir(parents=True, exist_ok=True)
    lista, acumulado = [], 0.0
    for escena in guion["escenas"]:
        salida = SEG / f"{escena['id']}.mp4"
        armar = escena_demo if "clip" in escena else escena_diapositiva
        t = armar(escena, duraciones[escena["id"]], salida)
        print(f"{escena['id']:<16} {acumulado:6.1f} s -> {acumulado + t:6.1f} s")
        acumulado += t
        lista.append(f"file '{salida.as_posix()}'")
    (SEG / "lista.txt").write_text("\n".join(lista), encoding="utf-8")
    final = VIDEO / "final" / "eciguia_video.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(SEG / "lista.txt"), "-c:v", "copy",
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
           "-movflags", "+faststart", str(final))
    d = duracion(final)
    print(f"\nVideo final: {final}  ({int(d // 60)}:{d % 60:04.1f}, límite de la rúbrica 5:00)")
    if d > 300:
        raise SystemExit("ERROR: el video pasa de 5 minutos")


if __name__ == "__main__":
    main()
