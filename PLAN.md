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

---

# Segunda etapa: ampliación del corpus, cierre del repositorio y presentación

Las fases 0 a 5 están terminadas (commit `f6cc4af`). La configuración de referencia es la corrida `6_final`: ruteo 98 %, rechazo 100 %, 32 de 33 respuestas correctas en revisión humana. Esta etapa agrega 12 PDF nuevos **sin empeorar eso**, cierra el repositorio y prepara la presentación.

Las reglas de la primera etapa siguen vigentes. Además: **Claude no hace commit ni push**; al terminar cada fase avisa y sugiere el mensaje, y el usuario lo ejecuta.

## Diagnóstico de los PDF nuevos (24/11/2026)

| # | Archivo actual | Qué es | Texto | Estructura | Tratamiento |
| --- | --- | --- | --- | --- | --- |
| 1 | `01_Reglamento_de_pregrado.pdf` | **Reglamento Estudiantil de Pregrado**, julio de 2018 | Sí, 40 págs | 107 artículos; título sin negrita, termina en punto | RAG por artículo. **Excluir los artículos que la modificación 2025 reemplazó** |
| 2 | `Modificación_al_Reglamento_Estudiatil_de_Pregrado_1.pdf` | Extracto del Acta 375 (26/11/2025): la **misma** modificación que ya está indexada, en otro formato | Sí, 12 págs | Tablas | **Duplicado**: comparar y, si no aporta nada, sacarlo de `data/raw/` |
| 3 | `Condiciones_de_la_Intención_de_Doble_Programa.pdf` | Acta 382 (29/07/2026), condiciones del doble programa (art. 49) | Sí, 3 págs | Prosa | RAG |
| 4 | `Lineamientos_canceación_de_asignatruas_CA.pdf` | Acuerdo 001 de 2025 del Consejo Académico (art. 33) | **Solo la pág. 3**; págs. 1-2 escaneadas | Prosa | Transcribir págs. 1-2 y luego RAG |
| 5 | `Lineamientos_práctica_docente_-_CA_24052023.pdf` | Lineamientos de práctica docente (2023) | Sí, 5 págs | Prosa + 1 tabla | RAG |
| 6 | `Reglamento_certificación_líneas_de_enfásis_….pdf` | Reglamento de certificación de líneas de énfasis | Sí, 10 págs | 20 artículos en negrita | RAG por artículo (igual que movilidad) |
| 7 | `09_Lineamientos_créditos_adicionales.pdf` | Lineamientos de créditos adicionales | **No: escaneado**, 2 págs | ? | Transcribir y luego RAG |
| 8 | `12_Regimen_de_participación_….pdf` | Régimen de participación de estudiantes en órganos de dirección | **No: escaneado**, 8 págs | ? | Baja prioridad: transcribir solo si hay tiempo |
| 9 | `RR014-2026_Valor_de_la_Matrícula_….pdf` | Valor de la matrícula 2027 por programa y rango socioeconómico | Sí, 2 págs | **Tablas** | Transcribir a JSON y consultar con herramienta MCP |
| 10 | `RR016-2026_Derechos_Pecuniarios_2027.pdf` | Derechos pecuniarios 2027 (grado, certificados, validación…) | Sí, 1 pág | **Tabla** concepto/valor | Transcribir a JSON y consultar con herramienta MCP |
| 11 | `Plan_de_estudios_…_a_partir_del_periodo_2025-1….pdf` | Malla de Ingeniería de Sistemas desde 2025-1 | Revuelto | **Tabla** de malla | Transcribir a JSON y consultar con herramienta MCP |
| 12 | `Plan_de_Estudios_…_antes_del_periodo_2025-1….pdf` | Malla de Ingeniería de Sistemas antes de 2025-1 | Revuelto | **Tabla** de malla | Transcribir a JSON y consultar con herramienta MCP |

**Hallazgos que cambian el diseño:**
- **Vigencia de artículos.** El reglamento de 2018 trae la versión **vieja** de los artículos 46, 69, 70, 80 y 84 (y quizá 93), que la modificación de 2025 reemplazó. Si se indexan las dos, el asistente puede citar una norma derogada. Eso es exactamente lo que hay que evitar.
- **f07, la trampa de las faltas.** El art. 38 define la falta de asistencia y el parágrafo dice que la inasistencia a talleres y laboratorios se califica con 0,0, pero **no fija un número máximo de faltas**. f07 sigue siendo trampa, pero la respuesta esperada debe cambiar y hay que pedir permiso para cambiarla.
- **Calibración.** Varias preguntas negativas ahora sí tienen respuesta: n02 (nota mínima, que es 3,0), n03 (costo del semestre, en RR014) y n13 (certificado de notas, en el art. 40 y RR016), y quizá n12 y n20. Hay que reetiquetarlas.
- **Las tablas no sirven para RAG.** El texto que pdfplumber extrae de las mallas sale revuelto ("P y r E o s b t a a b d i í l s id ti a c d a"). Igual que se hizo con el calendario, los datos tabulares van a JSON y se consultan con una herramienta.

## Decisiones del usuario (24/11/2026)

- **Reglamento Estudiantil 2018: fuera del corpus**, para evitar confusión con las versiones derogadas. Se guarda en `data/descartados/` (ignorada por git). Por eso `config.SUPERSEDED` ya no hace falta y **f07 no cambia**: sigue siendo trampa con su respuesta original.
- **Duplicado de la modificación 2025: fuera** (`data/descartados/`).
- **Todos los escaneados se transcriben**, incluido el régimen de participación. Ese PDF trae dos acuerdos (70 y 71 de 2017), así que se transcribió en dos archivos.
- Se conservan los dos planes de estudio de Sistemas, antes y desde 2025-1.
- El repo queda **público** por ahora.

**Estado de la fase 6 (24/11):** archivos renombrados y organizados; transcripciones en `data/transcripciones/` (4 archivos); tablas en `data/valores_2027.json` y `data/plan_estudios_sistemas.json`, con sumas verificadas contra los totales oficiales; títulos en `config.py`; página 1 del acta de doble programa excluida (lista de asistentes). **Falta: la verificación del usuario.**

**Fase 6 verificada por el usuario (24/11).**

**Estado de la fase 7 (24/11): terminada.**
- La ingesta lee las transcripciones, salta los PDF transcritos y las páginas de `SKIP_PAGES`, y el acta de doble programa va con chunking fijo.
- Los fragmentos de los 6 documentos originales siguen **idénticos**: 128 por artículo y 138 fijos, comparados contra una copia previa.
- Índice nuevo: 208 fragmentos de 13 documentos.
- Herramientas MCP nuevas: `consultar_valores_2027` y `consultar_plan_estudios`. También `ROUTER_V3`, la selección y redacción de herramientas, `OUT_OF_SCOPE` y los ejemplos de la app.
- 18 pruebas pasan.
- Prueba de humo (14 preguntas): rutas y herramientas correctas, y la regresión de d18 quedó corregida.
- Pendiente para la fase 8: una cita inventada ("[7]") en cancelación, y las pruebas Saber Pro mencionadas como requisito de ingreso al doble programa.

**Cosas para avisar al usuario (no corregidas):**
- RR016: las notas al pie 1 y 2 parecen intercambiadas en el documento original.
- Cancelación: el Acuerdo 02 de 2017 dice semana 12 (con extemporáneas en las semanas 13 a 16), y el Acuerdo 001 de 2025 lo prorroga hasta el sábado de la semana 15 "del año en curso". Para fechas concretas manda el calendario (2027-1: 8 de mayo).

## Decisiones de diseño

1. **Cada tipo de fuente tiene su tratamiento**, igual que el calendario en la primera etapa:
   - Prosa normativa: RAG.
   - Tablas con valores: JSON + herramienta MCP.
   - PDF escaneados: transcripción a `data/transcripciones/<nombre>.md`, con marcadores de página (`<!-- pág. 2 -->`) e indexada como texto. La cita dice "(transcrito)".
2. **Vigencia explícita.** Un diccionario `config.SUPERSEDED` lista, por documento, los artículos reemplazados (por ejemplo, el reglamento 2018: artículos 46, 69, 70, 80 y 84). La ingesta no indexa esos artículos y el fragmento de la modificación aclara qué artículo reemplaza. Prueba obligatoria: ninguna respuesta cita la versión vieja de un artículo modificado.
3. **Nombres limpios** (`git mv`, sin tildes ni espacios) y títulos con año en `config.DOCUMENT_TITLES`, por ejemplo "Reglamento Estudiantil de Pregrado (2018)".
4. **Herramientas MCP nuevas:**
   - `consultar_valores_2027(concepto, programa?, rango?)`: matrícula 2027 por programa y rango, y derechos pecuniarios.
   - `consultar_plan_estudios(consulta, plan?)`: asignatura, código, semestre y créditos en los planes de Ingeniería de Sistemas antes y desde 2025-1. Fuera de Sistemas responde que no tiene ese plan.
5. **Prompts nuevos con nombre propio:** `ROUTER_V3` (temas nuevos: notas, asistencia, permanencia, traslados, doble programa, énfasis, cancelación, costos 2027, plan de estudios) y, solo si la evaluación lo justifica, `RAG_ANSWER_V4`. Se actualizan también `TOOL_SELECTION` y `OUT_OF_SCOPE`.
6. **No se toca `eval/golden_set.jsonl`** (salvo f07, con permiso). Las preguntas nuevas van en `eval/golden_set_ampliacion.jsonl`, así las 40 originales siguen sirviendo como prueba de regresión.

## Criterios de aceptación ("resultados aceptables")

| Qué | Meta |
| --- | --- |
| Set original (40): ruteo | ≥ 95 % |
| Set original: acierto en reglamentos (revisión humana) | ≥ 23 de 25, con a lo sumo **1 regresión** frente a `6_final`, explicada |
| Set original: rechazo correcto | 100 % |
| Set de ampliación: recuperación hit@4 | ≥ 90 % |
| Set de ampliación: acierto (revisión humana) | ≥ 80 % |
| Set de ampliación: herramienta correcta | ≥ 90 % |
| Citas de artículos derogados | **0** |
| Latencia mediana | ≤ 15 s |
| `uv run pytest` y notebook (con y sin Ollama) | Pasan sin errores |

Si una meta no se cumple después de 2 iteraciones, no se fuerza: se documenta el fallo con su causa, como en la sección 4.4 del notebook.

## Fase 6. Preparar el corpus (sin tocar el índice)

1. **Duplicado:** comparar el texto de `Modificación_al_Reglamento_Estudiatil_de_Pregrado_1.pdf` con `modificacion_reglamento_estudiantil_2025.pdf`. Si no aporta nada nuevo, moverlo a `data/descartados/` (fuera de `data/raw/`, así no se indexa). Si aporta algo, decidir con el usuario.
2. **Renombrar** los nuevos con `git mv` (por ejemplo `reglamento_estudiantil_2018.pdf`, `lineamientos_cancelacion_asignaturas_2025.pdf`, `matricula_2027.pdf`, `derechos_pecuniarios_2027.pdf`, `plan_sistemas_desde_2025_1.pdf`).
3. **Separar datos de documentos.** Mover a `data/fuentes_tabulares/` los PDF que se consultan por herramienta (RR014, RR016 y los dos planes), para que la ingesta RAG no los procese revueltos. Los escaneados se quedan en `data/raw/` como fuente original, pero se indexa su transcripción.
4. **Transcribir los escaneados** (cancelación págs. 1-2 y créditos adicionales; régimen de participación solo si hay tiempo) a `data/transcripciones/*.md`, con encabezado de fuente y marcadores de página. **El usuario los verifica contra el PDF**: es la misma regla del calendario, nada inventado.
5. **Transcribir las tablas** a `data/valores_2027.json` (RR014 + RR016) y `data/plan_estudios_sistemas.json` (los dos planes). Verificación del usuario, por muestreo de al menos 10 valores.
6. Títulos en `config.DOCUMENT_TITLES` y artículos reemplazados en `config.SUPERSEDED`.

**Listo cuando:** cada archivo tiene un destino (RAG, herramienta o descartado) y el usuario verificó las transcripciones.

## Fase 7. Ingesta, herramientas y router

1. Ingesta:
   - Leer también `data/transcripciones/*.md`, respetando los marcadores de página.
   - Chunking por artículo del reglamento de 2018 (títulos sin negrita: el título es la primera oración).
   - Excluir los artículos de `SUPERSEDED` y agregar el año del documento a los metadatos.
2. Herramientas `consultar_valores_2027` y `consultar_plan_estudios`: lógica en `tools_logic.py`, exposición en `mcp_server.py` y pruebas.
3. `ROUTER_V3`, `TOOL_SELECTION`, `OUT_OF_SCOPE`, y descripción y ejemplos de `app.py`.
4. Reconstruir los dos índices y correr `uv run pytest`. Pruebas nuevas: artículos derogados excluidos, transcripciones cargadas y herramientas nuevas.
5. Prueba de humo con 10 preguntas: 5 del set original y 5 de los documentos nuevos.

**Listo cuando:** las pruebas pasan y las 10 preguntas de humo salen bien.

## Fase 8. Evaluación de la ampliación

1. Crear `eval/golden_set_ampliacion.jsonl` con unas 25 preguntas, cada respuesta tomada del PDF con documento y artículo:
   - Unas 13 del reglamento de 2018 y de los documentos nuevos en prosa.
   - Unas 6 de las herramientas nuevas (valores 2027 y plan de estudios).
   - Unas 3 que obliguen a usar la versión **modificada** de un artículo (validación, homologación, promedio). Detectan si se cita la norma derogada.
   - Unas 3 trampas nuevas.

   **El usuario revisa el set antes de correrlo.**
2. Pedir permiso para actualizar f07 y para reetiquetar las negativas de calibración que ahora tienen respuesta.
3. Recalibrar el umbral con `eval/calibrate.py` (positivas de los dos sets y negativas actualizadas).
4. Correr `7_ampliacion` sobre los dos sets y generar un **reporte de regresión pregunta por pregunta** contra `6_final`. Iterar como máximo 2 veces, con prompts nuevos que tengan nombre propio. Extender `eval/ruteo_holdout.jsonl` con los temas nuevos y repetir `compare_router.py`.
5. Revisión humana de las respuestas del set de ampliación y de 10 veredictos del juez.
6. Actualizar el notebook (nueva sección de ampliación, limitaciones resueltas y pendientes), el README y `docs/resultados/`.

**Listo cuando:** se cumplen los criterios de aceptación, o los fallos quedan documentados con su causa.

## Fase 9. Cierre del repositorio

Claude prepara los cambios y los comandos; **el usuario ejecuta los commits, el push y los cambios en GitHub.**

1. Sacar `eciguia.zip` del repo (`git rm --cached eciguia.zip`; el `.gitignore` ya ignora `*.zip`).
2. **Visibilidad:** el profesor debe poder ver el repo. Hay dos opciones: dejarlo público (los documentos son públicos) o volverlo privado y agregar al profesor como colaborador. Decide el usuario.
3. **Prueba de clon limpio:** clonar en una carpeta temporal, correr `uv sync`, `uv run pytest`, `uv run python -m eciguia.ingest` y el notebook sin Ollama, siguiendo **solo** el README. Corregir lo que falle.
4. README final:
   - Capturas o GIF de la app.
   - Estructura del repositorio.
   - Resultados de las dos etapas.
   - Link al video.
   - Licencia, si el usuario quiere una (por ejemplo MIT).
5. Metadatos del repo: descripción y temas (`gh repo edit --description ... --add-topic rag,langgraph,mcp,ollama`).
6. Etiqueta y release: `git tag v1.0-entrega` y un GitHub Release con el notebook y el link del video.

**Listo cuando:** un clon limpio funciona siguiendo solo el README y el profesor puede abrir el repo.

## Fase 10. Planeación de la presentación

1. **Canales:**
   - El video de 5 a 10 minutos, que es obligatorio y vale el 30 %.
   - El notebook ejecutado.
   - El README con capturas.
   - Opcional, si hay sustentación en vivo: demo local con Gradio y un video de respaldo por si falla.
2. **Guion v2** (`docs/guion_video.md`), con el mismo arco: problema → solución → demo → evidencia → limitaciones. Cambios:
   - Incluir las capacidades nuevas: reglamento completo (nota aprobatoria, asistencia), costos 2027 y plan de estudios.
   - Mostrar el caso de la **vigencia**: una pregunta sobre un artículo modificado que responde con la versión 2025 y no con la de 2018.
   - Mantener alrededor de 9 minutos.
3. **Guion de la demo:** 6 preguntas, al menos una por ruta y por documento nuevo, probadas el mismo día de la grabación (las fechas dependen de "hoy").
4. **Producción:**
   - OBS a 1080p, audio revisado y zoom sobre la sección de fuentes.
   - Cortar las esperas del LLM en la edición.
   - Subir como "no listado" a YouTube o a Drive y poner el link en el README.
5. **Ensayo cronometrado** antes de grabar la versión final.
6. Cuando el profesor publique la rúbrica 2026: confirmar fecha, formulario y criterios, y ajustar.

**Listo cuando:** el usuario aprobó el guion v2 e hizo un ensayo.

## Estimación

| Fase | Tiempo aproximado | Depende del usuario |
| --- | --- | --- |
| 6 | 1,5 a 2 h | Verificar las transcripciones |
| 7 | 1,5 h | No |
| 8 | 2 a 3 h (cada corrida dura unos 15 min) | Revisar el set nuevo y aprobar el cambio de f07 |
| 9 | 1 h | Commits, push, visibilidad, release |
| 10 | 1 h de planeación + grabación | Grabar |