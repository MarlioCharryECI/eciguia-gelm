# Plan de producción del video (fase 10)

> **Actualización del 25/11/2026 (rúbrica 2026-2).** La rúbrica nueva pide un video **público de máximo 5 minutos** que muestre el flujo completo: entrada, procesamiento con GenAI, salida y casos representativos. Esto reemplaza el plan de 9 minutos de abajo, que queda como referencia.
>
> **Lo que se hizo:**
> - **Estilo:** demo técnica con ritmo.
> - **Voz:** Gonzalo (es-CO, edge-tts), declarada como sintética en pantalla y en la descripción.
> - **Edición:** la hizo Claude, sin otro agente.
> - **Resultado:** corte de **3:07**, en `final/eciguia_video.mp4`.
>
> **Flujo reproducible** (todo con `uv run`, sin instalar nada en el sistema):
> 1. `tools/grabar_app.py`: 7 clips de la demo con marcas de tiempo (requiere la app y Ollama).
> 2. `narracion.json` → `tools/narrar.py`: un audio por escena y sus duraciones.
> 3. `tools/render_slides.py`: diapositivas por etapas (las cifras se leen de `docs/resultados/`) y rótulos ENTRADA / PROCESAMIENTO / SALIDA.
> 4. `tools/montar.py`: recorta, acelera las esperas (con rótulo), sincroniza con la voz, normaliza el audio y falla si el video pasa de 5:00.
> 5. `descripcion_youtube.md`: título, descripción con la nota de voz sintética y capítulos.

Video de entrega de EciGuía. Este documento lo siguen tres actores:
- **Claude (esta sesión)** graba el material crudo (RAW), genera las diapositivas, prepara la narración y la lista de decisiones de edición (EDL).
- **Un agente editor** (otra sesión) monta el video final a partir del RAW y la EDL, sin tener que entender el proyecto.
- **El usuario** aprueba el guion, decide la voz, revisa el corte final y lo sube.

## 1. Requisitos (rúbrica)

| Requisito | Cómo se cumple |
| --- | --- |
| Duración entre 5 y 10 minutos | Objetivo de **8:30 a 9:00**. La EDL suma la duración de cada escena; si pasa de 9:30, se recorta la demo |
| Explicación clara del proyecto | Narración guionada escena por escena (`docs/guion_video.md`) y diapositivas con un solo mensaje cada una |
| Proyecto completo junto con la problemática | Problema → objetivos → trabajos relacionados → arquitectura → demo en vivo → resultados → conclusión |

## 2. Estructura de archivos

```
docs/video/
├── PLAN_VIDEO.md          # este documento
├── EDITOR_BRIEF.md        # instrucciones autocontenidas para el agente editor
├── tools/                 # scripts de grabación y render (uv run, dependencias inline, no tocan el proyecto)
│   ├── render_slides.py   # HTML -> PNG 1920x1080
│   ├── grabar_app.py      # demo de la app de Gradio con marcas de tiempo
│   ├── grabar_paginas.py  # notebook (HTML local), repo de GitHub y sitio de la Escuela
│   └── narrar.py          # texto -> audio por escena (solo si se elige voz sintética)
├── slides/                # diapositivas fuente (HTML) y PNG renderizados
├── raw/                   # video crudo (.webm/.mp4) + marcas de tiempo (.json)   [NO se versiona]
├── audio/                 # narración por escena (.wav)                         [NO se versiona]
├── edl.json               # lista de decisiones de edición (la genera Claude)
└── final/                 # video montado por el agente editor                  [NO se versiona]
```

Los videos y audios pesan cientos de MB: `raw/`, `audio/` y `final/` van en `.gitignore`. El video final se sube a YouTube como "no listado" (o a Drive) y el enlace va en el README.

## 3. Especificación técnica

| Parámetro | Valor |
| --- | --- |
| Resolución y cuadros | 1920×1080, 30 fps |
| Captura | Playwright (Chromium sin interfaz) con `record_video`, a 1920×1080 aunque la pantalla física sea de 1280×800 |
| Formato RAW | `.webm` (lo produce Playwright); el editor convierte a H.264 |
| Formato final | MP4 H.264 + AAC 48 kHz, audio normalizado a −16 LUFS |
| Herramientas de edición | ffmpeg portátil (`imageio-ffmpeg`), sin instalar nada en el sistema |
| Escritura en pantalla | Las preguntas se escriben carácter por carácter (unos 25 ms por letra), para que se vea que es una demo real |
| Cursor | Playwright no graba el cursor; los clics se resaltan en edición con un zoom suave o un recuadro |

## 4. Escaleta (lo que se graba)

Duraciones objetivo **después de editar**. El detalle de narración y visuales está en `docs/guion_video.md` (v2).

| Escena | Tiempo | Visual | Fuente del material |
| --- | --- | --- | --- |
| E01 Título | 0:00–0:12 | Diapositiva de título | `slides/E01_titulo.png` |
| E02 Problema | 0:12–1:15 | Página de reglamentos de la Escuela, un PDF largo, la imagen del calendario; diapositiva del caso 80 % frente a 75 % | `raw/E02_web.webm` + `slides/E02_*.png` |
| E03 Objetivos | 1:15–1:45 | Diapositiva con el objetivo general y los 3 específicos | `slides/E03_objetivos.png` |
| E04 Trabajos relacionados | 1:45–2:25 | Diapositiva con 5 referencias y la diferencia de EciGuía | `slides/E04_trabajos.png` |
| E05 Arquitectura | 2:25–4:00 | Diagrama de arquitectura, grafo LangGraph, diapositiva "cada fuente con su tratamiento" (RAG, transcripción, tablas a herramientas), recorrido por el notebook (secciones 3.2 y 3.8) | `slides/E05_*.png` + `raw/E05_notebook.webm` |
| E06 Demo en vivo | 4:00–6:40 | La app respondiendo 6 preguntas (una por ruta y capacidad) | `raw/E06_q1..q6.webm` + `.json` |
| E07 Resultados | 6:40–8:05 | Tabla de 6 corridas, gráfica de calibración, diapositiva de la etapa 2 (0 regresiones, 55/55, router 97 %), validación del juez | `slides/E07_*.png` + `docs/resultados/calibracion_etapa1.png` |
| E08 Conclusión | 8:05–8:55 | Diapositiva de logros, limitaciones y trabajo futuro; cierre con la página del repo en GitHub | `slides/E08_conclusion.png` + `raw/E08_github.webm` |

### Preguntas de la demo (E06)

| Clip | Pregunta | Qué demuestra |
| --- | --- | --- |
| q1 | ¿La práctica profesional puede ser de medio tiempo? | RAG con cita (art. 14) e inferencia indirecta (fallo 2 corregido) |
| q2 | ¿Hasta cuándo puedo cancelar el semestre? | Herramienta de calendario, periodo vigente según "hoy" |
| q3 | ¿Cuánto cuesta la matrícula de ingeniería en 2027? | Herramienta de valores 2027 (segunda etapa), cita de la resolución |
| q4 | ¿En qué semestre se ve Arquitecturas de Software? | Herramienta del plan de estudios: los dos planes |
| q5 | ¿Qué materias se ven en quinto semestre de Ingeniería Civil? | Trampa: no inventa con datos de Sistemas |
| q6 | ¿Cuántas faltas de asistencia se permiten antes de perder una materia? | Trampa: "no encontré", sin inventar un número |

Respaldo, si sobra tiempo o falla una: "¿Me recomiendas una película?" (rechazo en unos 3 s) y "¿Qué promedio necesito para que me aprueben créditos adicionales?".

## 5. Procedimiento de grabación (Claude)

**Antes de grabar (bloqueante):**
1. Reiniciar Ollama (en esta GPU se traba después de cargas pesadas). Verificar que qwen responda en menos de 20 s.
2. Lanzar la app (`uv run python app.py`) y hacer **dos preguntas de calentamiento** que no se graban.
3. Revisar que las respuestas que dependen de "hoy" (q2) coincidan con el calendario en la fecha de grabación.
4. Cerrar las evaluaciones o procesos pesados. Nada más debe usar la GPU.

**Grabación:**
1. `render_slides.py`: genera las diapositivas en PNG. No dependen de Ollama y se pueden regenerar cuando cambie el texto.
2. `grabar_app.py`: un clip por pregunta. Cada clip guarda un `.json` con las marcas:
   - `t_inicio`: la página está lista;
   - `t_envio`: se envió la pregunta;
   - `t_respuesta`: aparece "Ruta:" debajo de la respuesta;
   - `t_fin`: unos 4 s después, para leer.

   Con esas marcas el editor recorta o acelera la espera del LLM sin adivinar.
3. `grabar_paginas.py`: el notebook se exporta a HTML local con `nbconvert` y se graba con desplazamiento suave hasta las secciones clave. Después se graba la página del repo en GitHub y la de reglamentos de escuelaing.edu.co (requiere internet).
4. Verificación de cada clip: que dure lo esperado, que no tenga cuadros negros y que la respuesta sea correcta. **Si una respuesta sale mal, se repite la toma**; no se edita el contenido de una respuesta.

**Reglas de honestidad del material:**
- Las respuestas que se ven en la demo son reales, producidas por el sistema en vivo. **No se editan, ni se superponen respuestas "mejores".**
- Se puede acortar la **espera** (corte o aceleración) siempre que se indique en pantalla, por ejemplo con un rótulo "⏩ espera acelerada, la respuesta tardó 14 s". Esto evita insinuar que el sistema es más rápido de lo que es.
- Las cifras de las diapositivas salen de `docs/resultados/`, no se escriben a mano.

## 6. Narración

**Decisión del usuario (pendiente):**
- **A. Voz del autor (recomendada).** El usuario graba la narración de `docs/guion_video.md` escena por escena (un archivo por escena, en un lugar silencioso, con el celular o el micrófono del portátil). Es su proyecto y su presentación, y suele evaluarse mejor.
- **B. Voz sintética local.** `narrar.py` genera la narración con una voz neuronal local (Piper, modelo en español, sin internet). La alternativa con voces de Windows (Sabina, Helena, Laura, Raúl) suena robótica. En la descripción del video se declara que la voz es sintética.

En los dos casos el audio queda en `audio/E0X.wav`, uno por escena. **La duración del audio manda**: el editor ajusta la duración de cada escena visual a su narración.

## 7. Lista de decisiones de edición (`edl.json`)

La genera Claude cuando el RAW y el audio están listos. Formato:

```json
{
  "salida": {"archivo": "final/eciguia_video.mp4", "resolucion": [1920, 1080], "fps": 30, "lufs": -16},
  "escenas": [
    {
      "id": "E06",
      "audio": "audio/E06.wav",
      "segmentos": [
        {"tipo": "video", "archivo": "raw/E06_q1.webm", "desde": 0.0, "hasta": 3.2},
        {"tipo": "video", "archivo": "raw/E06_q1.webm", "desde": 3.2, "hasta": 17.4, "velocidad": 4.0,
         "rotulo": "⏩ espera acelerada (la respuesta tardó 14 s)"},
        {"tipo": "video", "archivo": "raw/E06_q1.webm", "desde": 17.4, "hasta": 23.0,
         "zoom": {"region": [960, 420, 1900, 1000], "desde": 18.0, "hasta": 22.5}}
      ]
    },
    {
      "id": "E03",
      "audio": "audio/E03.wav",
      "segmentos": [{"tipo": "imagen", "archivo": "slides/E03_objetivos.png", "duracion": "audio", "transicion": "fundido"}]
    }
  ]
}
```

- `duracion: "audio"`: la imagen dura lo que dure la narración de la escena.
- `velocidad`: acelera ese tramo (solo esperas, siempre con rótulo).
- `zoom`: acercamiento suave a una región (x1, y1, x2, y2), por ejemplo la sección de fuentes de la respuesta.
- `rotulo`: texto superpuesto abajo a la izquierda.
- Entre escenas: fundido de 0,3 s. Los subtítulos (`.srt` a partir del guion) van como pista aparte y opcional.

## 8. Entrega al agente editor

`EDITOR_BRIEF.md` es autocontenido: qué hay en cada carpeta, cómo leer la EDL, qué herramientas usar (ffmpeg portátil vía `uv run --with imageio-ffmpeg`), las reglas de honestidad (no alterar respuestas, rotular las aceleraciones) y la lista de comprobación de salida. El editor **no necesita Ollama ni conocer el código**.

**Lista de comprobación del corte final** (la revisan el editor y luego el usuario):
- [ ] Dura entre 8:00 y 9:45.
- [ ] Se entiende el problema en el primer minuto.
- [ ] Cada respuesta de la demo se lee completa (mínimo 3 s quieta en pantalla), con su ruta y sus fuentes.
- [ ] Toda espera acelerada tiene su rótulo.
- [ ] Las cifras coinciden con el README (0 regresiones, 55/55, router 97 %, umbral 0,45, juez 8/10).
- [ ] El audio no satura, tiene volumen parejo y no hay silencios de más de 2 s.
- [ ] No aparecen datos personales: ni el correo del usuario ni pestañas o notificaciones ajenas.

## 9. Pasos y responsables

| # | Paso | Quién | Depende de |
| --- | --- | --- | --- |
| 1 | Guion v2 con narración por escena (`docs/guion_video.md`) | Claude | — |
| 2 | Aprobar el guion y elegir la voz (A o B) | **Usuario** | 1 |
| 3 | Diapositivas HTML y render a PNG | Claude | 2 |
| 4 | Scripts de grabación y prueba corta | Claude | — |
| 5 | Grabar el RAW (app, notebook, web) y verificar cada clip | Claude | 3, 4, Ollama sano |
| 6 | Narración: grabada por el usuario (A) o generada (B) | Usuario o Claude | 2 |
| 7 | Generar `edl.json` y `EDITOR_BRIEF.md` | Claude | 5, 6 |
| 8 | Montaje del video final | **Agente editor** | 7 |
| 9 | Revisión del corte y lista de cambios | **Usuario** | 8 |
| 10 | Subir el video, enlazarlo en el README, etiqueta `v1.0-entrega` y release | **Usuario** | 9 |

## 10. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Ollama se traba durante la grabación | Reinicio previo, límite de 180 s en la app, repetir la toma; los clips son independientes |
| Respuesta distinta a la esperada (el LLM varía con el contexto o la fecha) | Temperatura 0; verificar cada clip; repetir la toma; preguntas de respaldo |
| La respuesta de q2 depende de "hoy" | Revisarla el mismo día; la narración no dice la fecha, solo "el semestre vigente" |
| El video pasa de 10 minutos | La EDL suma las duraciones; se recorta primero la demo (q4 o q5) y luego los trabajos relacionados |
| Voz sintética mal recibida | Opción A recomendada; si es B, se declara en la descripción |
| Archivos pesados en git | `raw/`, `audio/` y `final/` ignorados; solo se versionan scripts, diapositivas fuente, EDL y brief |
