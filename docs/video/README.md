# Video de EciGuía

**Ver el video (4:05):** [OneDrive](https://pruebacorreoescuelaingeduco-my.sharepoint.com/:v:/g/personal/marlio_charry-e_mail_escuelaing_edu_co/IQDksiJtIJ0HTbxWtPXo79w8ASer20ylCExb8rXgUP-j6fA?e=ZUmnGx)

El video no tiene diapositivas: alterna escenas animadas con la app real respondiendo 9 casos, narrado por el autor. Las respuestas no se editan. Lo único que se acelera es la espera del modelo, y un contador en la esquina muestra cuánto tardó de verdad cada respuesta.

- [`guion.md`](guion.md) trae la narración completa, qué se ve en cada momento, cómo cubre la rúbrica y de dónde sale cada cifra.
- [`motion/escenas.html`](motion/escenas.html) contiene las escenas animadas: apertura, problema, arquitectura, resultados, evolución, límites y cierre.

## Cómo se produce

Todo corre con `uv run`, con las dependencias declaradas en cada script, sin instalar nada en el sistema.

| Paso | Script | Qué hace |
| --- | --- | --- |
| 1 | `tools/grabar_demo.py` | Graba 9 tomas de la app con el screencast de Chromium a 1920×1080. Usa una cámara que hace zoom dentro de la página, un cursor dibujado y un contador del tiempo real. Requiere la app y Ollama encendidos. La toma `t9_error` se graba con Ollama cerrado |
| 2 | `tools/movimiento.py` | Mide cuánto cambia cada cuadro de cada toma, para saber qué tramos están quietos |
| 3 | `tools/transcribir.py` | Transcribe la narración palabra por palabra (faster-whisper) |
| 4 | `tools/montar.py` | Arma el video. La voz marca el ritmo: cada escena animada se ata al segundo en que se nombra cada elemento, y cada toma se re-temporiza con anclas a la narración (lo que se mueve va a velocidad real y lo quieto se estira o se acorta). Une todo con transiciones, limpia y normaliza la voz a −16 LUFS y genera los subtítulos. Falla si el video pasa de 5 minutos |

`tools/render_motion.py` renderiza las escenas animadas cuadro a cuadro: congela cada animación CSS en el instante exacto y la captura. Lo llama `montar.py`.

Los audios, las tomas y el video final pesan cientos de MB, así que no se versionan (`docs/video/audio/`, `raw/` y `final/` están en `.gitignore`).
