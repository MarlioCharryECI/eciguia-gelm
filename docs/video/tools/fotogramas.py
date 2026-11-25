# /// script
# requires-python = ">=3.11"
# dependencies = ["imageio-ffmpeg>=0.5"]
# ///
"""Extrae fotogramas de un clip para revisarlo sin abrir un reproductor.

    uv run docs/video/tools/fotogramas.py docs/video/raw/E06_q1.webm 2 10 18
"""

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video = Path(sys.argv[1])
for t in sys.argv[2:]:
    out = video.with_name(f"{video.stem}_t{t}.png")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", t, "-i", str(video), "-frames:v", "1", str(out)], check=True)
    print(out)
