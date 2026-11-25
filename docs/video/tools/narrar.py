# /// script
# requires-python = ">=3.11"
# dependencies = ["edge-tts>=7.0", "imageio-ffmpeg>=0.5"]
# ///
"""Genera la narración de cada escena con una voz neuronal (edge-tts) y mide su duración.

    uv run docs/video/tools/narrar.py            # todas las escenas
    uv run docs/video/tools/narrar.py S2_problema

Lee docs/video/narracion.json y escribe docs/video/audio/<id>.mp3 y audio/duraciones.json.
Nota: edge-tts usa el servicio en línea de voces de Microsoft Edge (el texto del guion viaja a ese servicio).
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
import imageio_ffmpeg

VIDEO = Path(__file__).resolve().parents[1]
AUDIO = VIDEO / "audio"


def duracion(path: Path) -> float:
    out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def main() -> None:
    guion = json.loads((VIDEO / "narracion.json").read_text(encoding="utf-8"))
    AUDIO.mkdir(parents=True, exist_ok=True)
    pedidas = set(sys.argv[1:])
    duraciones_path = AUDIO / "duraciones.json"
    duraciones = json.loads(duraciones_path.read_text(encoding="utf-8")) if duraciones_path.exists() else {}
    for escena in guion["escenas"]:
        if pedidas and escena["id"] not in pedidas:
            continue
        destino = AUDIO / f"{escena['id']}.mp3"
        await edge_tts.Communicate(escena["texto"], guion["voz"], rate=guion["velocidad"]).save(str(destino))
        duraciones[escena["id"]] = round(duracion(destino), 2)
        print(f"{escena['id']:<16} {duraciones[escena['id']]:6.2f} s")
    duraciones_path.write_text(json.dumps(duraciones, indent=2), encoding="utf-8")
    print(f"Total narración: {sum(duraciones.values()):.1f} s")


if __name__ == "__main__":
    asyncio.run(main())
