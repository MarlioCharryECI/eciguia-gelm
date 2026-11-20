# EciGuía

Asistente académico para estudiantes de pregrado de la Escuela Colombiana de Ingeniería Julio Garavito. Responde dudas sobre prácticas profesionales, opción de grado, trabajos dirigidos, movilidad, inglés y el calendario académico 2027, citando el documento y la página de donde sale cada dato. Si algo no está en los documentos, lo dice. Todo corre en local con Ollama, gratis y sin enviar datos a terceros.

Proyecto final de GELM (IA Generativa), 2026-2. El informe completo está en [`proyecto.ipynb`](proyecto.ipynb).

## Cómo funciona

```
pregunta ─▶ router (LLM) ─┬─▶ documentos ─▶ Chroma (top 4, umbral 0,45) ─┬─▶ respuesta con citas [1] [2]
                          │                                              └─▶ "no encontré esa información"
                          ├─▶ herramienta ─▶ servidor MCP (FastMCP, stdio) ─▶ respuesta
                          │                  · consultar_calendario
                          │                  · dias_hasta
                          │                  · calcular_promedio_ponderado
                          └─▶ fuera de alcance ─▶ rechazo amable
```

| Parte | Tecnología | Archivo |
| --- | --- | --- |
| Carga y chunking por artículo | pdfplumber + LangChain text splitters | `src/eciguia/ingest.py` |
| Embeddings y búsqueda | `bge-m3` en Ollama + Chroma | `src/eciguia/retriever.py` |
| Agente con router | LangGraph | `src/eciguia/graph.py` |
| Herramientas | FastMCP | `src/eciguia/mcp_server.py`, `tools_logic.py` |
| Prompts versionados | | `src/eciguia/prompts.py` |
| Interfaz | Gradio | `app.py` |
| Evaluación | 40 preguntas + LLM como juez | `eval/` |

<!-- RESULTADOS -->

## Instalación

Requisitos: [uv](https://docs.astral.sh/uv/) y [Ollama](https://ollama.com). Probado en Windows 11 con una GPU de 6 GB (RTX 3050).

```powershell
# uv en Windows (si no lo tienes)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

ollama pull qwen2.5:7b      # modelo que responde
ollama pull bge-m3          # embeddings multilingües
uv sync                     # instala dependencias (incluye las del notebook)
copy .env.example .env      # opcional, para cambiar modelos o parámetros
```

En PowerShell conviene activar UTF-8 para ver bien las tildes: `$env:PYTHONUTF8=1`.

## Uso

```powershell
uv run python -m eciguia.ingest                    # 1. construye el índice (una sola vez, ~1 min)
uv run python app.py                               # 2. abre la app en http://localhost:7860
uv run python -m eciguia.graph "¿Cuánto dura la práctica?"   # o pregunta desde la terminal
```

El servidor MCP también se puede usar solo, con cualquier cliente MCP: `uv run python -m eciguia.mcp_server`.

## Evaluación

`eval/golden_set.jsonl` tiene 40 preguntas con respuesta conocida: 25 de reglamentos (con documento y artículo esperados), 8 de herramientas y 7 fuera de alcance o trampa.

```powershell
uv run python -m eciguia.ingest --strategy fijo     # índice alterno para comparar chunking
uv run python eval/calibrate.py                     # calibra el umbral de relevancia
uv run python eval/run_eval.py --name 1_base --baseline --prompt basico --strategy fijo
uv run python eval/run_eval.py --name 2_chunk_articulo --baseline --prompt basico
uv run python eval/run_eval.py --name 3_router_tools --prompt basico
uv run python eval/run_eval.py --name 4_prompt_v1 --prompt v1
uv run python eval/run_eval.py --name 5_final
```

Cada experimento cambia una sola cosa respecto al anterior. Métricas: hit@4 del retriever, ruteo correcto, herramienta correcta, rechazo correcto, acierto y fidelidad (LLM como juez, validado a mano) y latencia mediana. El detalle queda en `eval/results/` y los resúmenes finales en `docs/resultados/`.

## Pruebas

```powershell
uv run pytest      # no necesitan Ollama (usan embeddings y LLM simulados)
```

## Documentos usados

En `data/raw/`, descargados de [escuelaing.edu.co](https://www.escuelaing.edu.co/es/estudiantes/reglamentos-y-cronogramas-academicos/): Reglamento de Prácticas Profesionales (julio de 2026), Lineamientos de Opción de Grado, Reglamento de Trabajos Dirigidos (mayo de 2026), Reglamento de Movilidad Estudiantil (mayo de 2026), Reglamento de Inglés 2025 y Modificación al Reglamento Estudiantil (2025). El calendario académico 2027 venía como imagen, así que se transcribió a `data/calendario_2027.json`.

## Limitaciones conocidas

- No incluye el Reglamento Estudiantil de Pregrado completo, solo su modificación de 2025. Por eso no responde preguntas de asistencia, notas mínimas o pérdida de cupo; las reconoce como fuera de sus documentos.
- Los Lineamientos de Opción de Grado piden el 80 % de los créditos y el Reglamento de Prácticas (2026) pide el 75 %. El asistente debe mostrar ambos.
- El calendario se transcribió a mano: ante cualquier duda, manda el calendario oficial.
- El juez de la evaluación es el mismo modelo que responde, lo que puede inflar las métricas. Por eso se validó a mano una muestra de sus veredictos.
