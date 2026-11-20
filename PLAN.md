# Plan de trabajo: EciGuía (proyecto final GELM 2026-2)

Este archivo es para Claude Code. Léelo completo antes de empezar y sigue las fases en orden. Al terminar cada fase, haz un commit y resume en pocas líneas qué cambió y qué falta.

## Contexto

EciGuía es un asistente académico para estudiantes de pregrado de la Universidad Escuela Colombiana de Ingeniería Julio Garavito. Responde dudas sobre reglamentos (prácticas, opción de grado, trabajos dirigidos, movilidad, inglés) y sobre el calendario académico 2027. Cita el documento y la página de cada dato, y si algo no está en los documentos, dice que no sabe.

Es el proyecto final del curso de IA Generativa (GELM). Lo que se entrega:

1. Un notebook `proyecto.ipynb` con esta estructura obligatoria del profesor: Problemática (objetivo general y 3 específicos), Trabajos relacionados, Metodología (el código), Resultados y discusión, Conclusión.
2. Un video de 5 a 10 minutos con una demo.

Rúbrica (la de 2025, probablemente igual en 2026):
- Aplicación, 30 %: que la herramienta resuelva un problema real con GenAI.
- Código, 40 %: que corra sin errores y use librerías o APIs de GenAI.
- Video, 30 %.

Objetivos específicos ya definidos:
1. Pipeline RAG sobre 6 documentos oficiales, comparando dos estrategias de chunking (por artículo y de tamaño fijo).
2. Agente LangGraph que enruta cada pregunta: documentos, herramienta MCP o fuera de alcance.
3. Evaluación con 40 preguntas de respuesta conocida, midiendo la mejora entre versiones.

## Estado actual (ya implementado)

| Parte | Archivo | Estado |
| --- | --- | --- |
| Configuración | `src/eciguia/config.py` | Listo. Variables en `.env` |
| Ingesta y chunking | `src/eciguia/ingest.py` | Listo. Probado |
| Retriever con umbral | `src/eciguia/retriever.py` | Listo. Umbral `MAX_DISTANCE=0.65` **sin calibrar** |
| Lógica de herramientas | `src/eciguia/tools_logic.py` | Listo. Probado |
| Servidor MCP | `src/eciguia/mcp_server.py` | Listo. Probado por stdio |
| Agente LangGraph | `src/eciguia/graph.py` | Listo. Probado solo con LLM simulado |
| Prompts | `src/eciguia/prompts.py` | Primera versión, **sin probar con modelo real** |
| App Gradio | `app.py` | Se construye; no se ha usado con Ollama |
| Set de evaluación | `eval/golden_set.jsonl` | 40 preguntas |
| Script de evaluación | `eval/run_eval.py` | Probado con dobles |
| Pruebas | `tests/` | 11 pruebas, pasan sin Ollama |

Stack: Python con uv, Ollama local (`qwen2.5:7b` para el LLM y `bge-m3` para embeddings), Chroma, LangChain, LangGraph, FastMCP y Gradio. Todo gratis y local. No hay que agregar APIs de pago.

El usuario trabaja en **Windows**. Usa comandos compatibles con PowerShell.

## Reglas

- No cambies fechas de `data/calendario_2027.json` ni respuestas de `eval/golden_set.jsonl` sin preguntarle al usuario. Las dos cosas se transcribieron de documentos oficiales; si encuentras algo que parece un error, avisa y no lo corrijas por tu cuenta.
- `uv run pytest` debe seguir pasando después de cada cambio.
- No inventes contenido de los reglamentos. Si necesitas un dato, búscalo en los PDFs de `data/raw/`.
- La interfaz y las respuestas van en español.
- No subas `.env`, `data/chroma/` ni `eval/results/` a git (ya están en `.gitignore`), salvo los resultados finales que se citen en el notebook. Esos se copian a `docs/resultados/`.
- Si un cambio afecta mucho el diseño (cambiar de modelo, de base vectorial o de framework), pregunta antes.

## Fase 0. Preparar el entorno

1. Verifica que `uv`, `git` y `ollama` estén instalados (`uv --version`, `ollama list`).
2. Si faltan los modelos, corre `ollama pull qwen2.5:7b` y `ollama pull bge-m3`.
3. `uv sync` y `uv run pytest`.
4. `git init`, primer commit con todo, y crea el repositorio `eciguia` en GitHub con `gh repo create eciguia --private --source . --push` (si `gh` no está autenticado, pídele al usuario que lo haga).

**Listo cuando:** las pruebas pasan y el repo está en GitHub.

## Fase 1. Primera corrida real

1. `uv run python -m eciguia.ingest` y `uv run python -m eciguia.ingest --strategy fijo`.
2. Prueba estas preguntas con `uv run python -m eciguia.graph "<pregunta>"` y muestra al usuario ruta, respuesta, fuentes y latencia:
   - ¿Qué porcentaje de créditos necesito para hacer la práctica?
   - ¿Hasta cuándo puedo cancelar asignaturas en 2027-1?
   - Saqué 4.2 en una materia de 3 créditos y 3.6 en una de 4, ¿cuál es mi promedio?
   - ¿Me recomiendas una película?
   - ¿Cuántas faltas se permiten antes de perder una materia?
3. Corrige los errores que aparezcan (por ejemplo JSON mal formado del router o herramientas mal elegidas). Prioriza que el modelo real funcione sobre la elegancia del código.

**Listo cuando:** las 5 preguntas pasan por la ruta correcta y las respuestas son coherentes.

## Fase 2. Calibrar el umbral de relevancia

1. Crea `eval/calibrate.py`: para cada pregunta del set, imprime la distancia coseno del mejor fragmento recuperado, separando las de tipo `documentos` de las de `fuera_de_alcance` y `trampa`.
2. Elige un `MAX_DISTANCE` que deje pasar casi todas las de documentos y bloquee las trampas. Guarda una gráfica de las dos distribuciones en `docs/resultados/calibracion.png`, que sirve para el notebook.
3. Actualiza el valor por defecto en `config.py` y en `.env.example`.

**Listo cuando:** hay un umbral justificado con datos.

## Fase 3. Evaluación y mejora

1. Corre los cuatro experimentos del README:
   - `1_base`: sin router, prompt básico, chunking fijo.
   - `2_chunk_articulo`: sin router, prompt básico, chunking por artículo.
   - `3_router_tools`: con router y herramientas, prompt básico.
   - `4_final`: todo, con el prompt con reglas.
2. Revisa a mano 10 veredictos del juez LLM y reporta cuántos coinciden con tu criterio. Un juez sin validar no es creíble.
3. Itera sobre `prompts.py` (router y RAG) mirando los fallos. Cada versión de prompt nueva debe quedar guardada con nombre propio (`RAG_ANSWER_V2`, etc.), para poder mostrar la comparación.
4. Escoge 3 fallos concretos y explica su causa (chunk partido, pregunta ambigua, dato que no está en los documentos, error del router, etc.).
5. Copia los `.json` de resumen finales y una tabla comparativa a `docs/resultados/`.

**Listo cuando:** hay una tabla de 4 o más corridas con métricas que mejoran, y 3 fallos analizados.

## Fase 4. Notebook de entrega

Crea `proyecto.ipynb` con la estructura del profesor. El notebook **importa** del paquete `eciguia`; no copies el código en celdas largas.

1. **Problemática:** el problema, el usuario (estudiante de la ECI), el objetivo general y los 3 específicos.
2. **Trabajos relacionados:** 3 referencias reales y verificables (por ejemplo el paper original de RAG de Lewis et al. 2020, documentación de LangGraph y MCP, y algún trabajo de chatbots universitarios), y en qué se diferencia EciGuía. Dale los links al usuario para que los verifique.
3. **Metodología:** el diagrama de arquitectura, la ingesta con ejemplos de fragmentos, el retriever, el grafo (muestra el grafo dibujado con `agent.graph.get_graph().draw_mermaid_png()` si funciona), las herramientas MCP y 3 preguntas de demo ejecutadas.
4. **Resultados y discusión:** la tabla de experimentos, la gráfica de calibración y los 3 fallos analizados. Incluye la contradicción entre el 80 % de los lineamientos de opción de grado y el 75 % del reglamento de prácticas como caso de estudio.
5. **Conclusión:** qué se logró por objetivo, las limitaciones (falta el Reglamento Estudiantil completo, el corpus es pequeño, el calendario se transcribió a mano) y el trabajo futuro.

El notebook debe correr de principio a fin con "Restart & Run All". Si alguna celda tarda más de 2 minutos, carga los resultados guardados en vez de recalcular.

**Listo cuando:** el notebook corre completo y sin errores, y el usuario lo revisó.

## Fase 5. Pulido para el video

1. Revisa `app.py`: que los ejemplos funcionen y que la respuesta muestre la ruta, la herramienta y las fuentes de forma clara.
2. Escribe `docs/guion_video.md` con el guion de 9 minutos: problema (1 min), trabajos relacionados (1), arquitectura (2), demo en vivo con 4 preguntas (2.5), resultados (1.5) y conclusión (1).
3. Actualiza el README con los resultados finales y las instrucciones definitivas.

**Listo cuando:** el usuario puede grabar el video siguiendo el guion.

## Problemas conocidos

- El Reglamento Estudiantil de Pregrado completo no está cargado, solo su modificación de 2025. Si el usuario lo consigue, agrégalo a `data/raw/`, añade su título en `config.DOCUMENT_TITLES`, reconstruye el índice y agrega preguntas al set.
- Los prompts nunca se probaron con un modelo real. Espera tener que ajustarlos.
- El juez LLM usa el mismo modelo que responde, y eso puede inflar las métricas. Menciónalo como limitación o usa un modelo distinto para juzgar si el equipo lo soporta.