# /// script
# requires-python = ">=3.11"
# dependencies = ["imageio-ffmpeg>=0.5", "numpy"]
# ///
"""Mide cuánto cambia cada cuadro de cada toma de la demo.

    uv run docs/video/tools/movimiento.py

Escribe docs/video/raw/demo/movimiento.json con la diferencia media entre cuadros consecutivos (a 192x108,
escala 0-255). montar.py la usa para saber qué tramos están quietos (se pueden estirar o acortar sin que
se note) y cuáles tienen movimiento (cursor, cámara, texto), que van a velocidad real. Se ignora la esquina
del contador de tiempo, que cambia siempre.
"""

from __future__ import annotations

import json
from pathlib import Path

import imageio_ffmpeg
import numpy as np

RAW = Path(__file__).resolve().parents[1] / "raw" / "demo"


def main() -> None:
    salida = {}
    for toma in sorted(RAW.glob("t*.mp4")):
        lector = imageio_ffmpeg.read_frames(str(toma), output_params=["-vf", "scale=192:108"])
        next(lector)
        anterior, difs = None, []
        for cuadro in lector:
            gris = np.frombuffer(cuadro, np.uint8).reshape(108, 192, 3).mean(axis=2)
            gris[84:, 150:] = 0  # contador de tiempo real
            difs.append(0.0 if anterior is None else float(np.abs(gris - anterior).mean()))
            anterior = gris
        salida[toma.stem] = difs
        print(f"{toma.stem}: {len(difs)} cuadros")
    (RAW / "movimiento.json").write_text(json.dumps(salida), encoding="utf-8")


if __name__ == "__main__":
    main()
