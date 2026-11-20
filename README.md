# EciGuía

Asistente académico para estudiantes de pregrado de la Escuela Colombiana de Ingeniería Julio Garavito. Responde dudas sobre prácticas profesionales, opción de grado, trabajos dirigidos, movilidad, inglés y el calendario académico 2027, citando el documento y la página de donde sale cada dato. Todo corre en local con Ollama, gratis y sin enviar datos a terceros.

Proyecto final de GELM (IA Generativa), 2026-2.

## Cómo funciona

```
pregunta ─▶ router (LLM) ─┬─▶ documentos ─▶ Chroma (top 4) ─▶ ¿hay contexto? ─┬─▶ respuesta con citas [1] [2]
                          │                                                    └─▶ "no encontré esa información"
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
| Prompts | | `src/eciguia/prompts.py` |
| Interfaz | Gradio | `app.py` |
| Evaluación | 40 preguntas + LLM como juez | `eval/` |

## Instalación

Requisitos: [uv](https://docs.astral.sh/uv/) y [Ollama](https://ollama.com).

```bash
ollama pull qwen2.5:7b      # modelo que responde (si tu equipo tiene poca RAM: llama3.2:3b)
ollama pull bge-m3          # embeddings multilingües
uv sync                     # instala dependencias
cp .env.example .env        # opcional, para cambiar modelos o parámetros
```

## Uso

```bash
uv run python -m eciguia.ingest                    # 1. construye el índice (una sola vez)
uv run python app.py                               # 2. abre la app en http://localhost:7860
uv run python -m eciguia.graph "¿Cuánto dura la práctica?"   # o pregunta desde la terminal
```

## Evaluación

`eval/golden_set.jsonl` tiene 40 preguntas con respuesta conocida: 25 de reglamentos (con documento y artículo esperados), 8 de herramientas y 7 fuera de alcance o trampa.

```bash
uv run python -m eciguia.ingest --strategy fijo     # índice alterno para comparar chunking
uv run python eval/run_eval.py --name 1_base --baseline --prompt basico --strategy fijo
uv run python eval/run_eval.py --name 2_chunk_articulo --baseline --prompt basico
uv run python eval/run_eval.py --name 3_router_tools --prompt basico
uv run python eval/run_eval.py --name 4_final
```

Métricas: hit@4 del retriever, ruteo correcto, herramienta correcta, rechazo correcto, acierto y fidelidad (LLM como juez, revisar a mano) y latencia mediana. Resultados en `eval/results/`.

## Pruebas

```bash
uv run pytest      # 11 pruebas, no necesitan Ollama (usan embeddings y LLM simulados)
```

## Documentos usados

En `data/raw/`, descargados de [escuelaing.edu.co](https://www.escuelaing.edu.co/es/estudiantes/reglamentos-y-cronogramas-academicos/): Reglamento de Prácticas Profesionales, Lineamientos de Opción de Grado, Reglamento de Trabajos Dirigidos, Reglamento de Movilidad Estudiantil, Reglamento de Inglés 2025 y Modificación al Reglamento Estudiantil (2025). El calendario académico 2027 venía como imagen, así que se transcribió a `data/calendario_2027.json`.

## Limitaciones conocidas

- No incluye el Reglamento Estudiantil de Pregrado completo, solo su modificación de 2025.
- Los Lineamientos de Opción de Grado piden el 80 % de los créditos y el Reglamento de Prácticas (2026) pide el 75 %. El asistente debe mostrar ambos.
- El calendario se transcribió a mano: ante cualquier duda, manda el calendario oficial.
