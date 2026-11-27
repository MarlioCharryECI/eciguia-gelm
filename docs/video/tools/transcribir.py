# /// script
# requires-python = ">=3.11"
# dependencies = ["faster-whisper>=1.0", "imageio-ffmpeg>=0.5", "numpy"]
# ///
"""Transcribe la narración con marcas de tiempo por palabra (para sincronizar el video con la voz).

    uv run docs/video/tools/transcribir.py

Lee docs/video/audio/voz/01.mp4 … 07.mp4 y escribe docs/video/audio/voz/palabras.json con
{"01": [[inicio, fin, "palabra"], ...], ...}. Usa faster-whisper (modelo small, en CPU).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from faster_whisper import WhisperModel

VOZ = Path(__file__).resolve().parents[1] / "audio" / "voz"


def audio_16k(path: Path) -> np.ndarray:
    """Decodifica con ffmpeg a 16 kHz mono (evita depender del decodificador de faster-whisper)."""
    crudo = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(path), "-ac", "1",
                            "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.int16).astype(np.float32) / 32768


def main() -> None:
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    salida = {}
    for audio in sorted(VOZ.glob("[0-9][0-9].mp4")):
        segmentos, _ = modelo.transcribe(audio_16k(audio), language="es", word_timestamps=True)
        palabras = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segmentos for w in s.words]
        salida[audio.stem] = palabras
        print(f"{audio.stem}: {len(palabras)} palabras, {palabras[0][0]} -> {palabras[-1][1]} s")
    (VOZ / "palabras.json").write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
