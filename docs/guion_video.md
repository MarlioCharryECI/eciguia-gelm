# Guion del video: EciGuía (v2, unos 9 minutos)

Este guion lo usan tres actores: el **usuario** narra (o aprueba la voz sintética), **Claude** graba el material crudo y genera las diapositivas, y el **agente editor** monta el video. Cada escena tiene un ID (E01 a E08) que coincide con los archivos de `docs/video/` y con `edl.json`. El proceso completo está en `docs/video/PLAN_VIDEO.md`.

Rúbrica: entre 5 y 10 minutos, explicación clara, proyecto completo junto con la problemática. Objetivo: 8:30 a 9:00.

**Cómo leer la narración:**
- Ritmo tranquilo, de unas 150 palabras por minuto.
- `[pausa]` = medio segundo de silencio.
- Si grabas tú la voz (opción A), graba **un archivo por escena** (`E01.wav` … `E08.wav`) y deja un segundo de silencio al inicio y al final. Si te equivocas, repite la frase completa; el editor corta.

---

## E01 · Título (0:00–0:12, unas 30 palabras)

**Visual:** diapositiva de título: "EciGuía: asistente académico con RAG, agentes y MCP" · Marlio José Charry Espitia · IA Generativa (GELM) 2026-2 · Escuela Colombiana de Ingeniería Julio Garavito.

**Narración:**
> Hola, soy Marlio José Charry Espitia, y este es EciGuía: un asistente académico para estudiantes de la Escuela, construido con IA generativa y que corre completamente en mi computador.

## E02 · Problema (0:12–1:15, unas 155 palabras)

**Visual:**
1. `raw/E02_web`: página de reglamentos de escuelaing.edu.co con desplazamiento lento.
2. Diapositiva `E02_dispersion`: los 13 documentos, más el calendario (imagen), las resoluciones de valores y las mallas.
3. Diapositiva `E02_caso`: "Lineamientos de Opción de Grado: 80 % de créditos · Reglamento de Prácticas (2026): 75 %".

**Narración:**
> Cuando un estudiante quiere saber si puede hacer la práctica, cuántas materias puede cancelar o cuánto le va a costar la matrícula del próximo año, la respuesta está repartida en reglamentos en PDF, acuerdos escaneados, resoluciones con tablas y un calendario publicado como imagen. [pausa]
> Muchos de esos documentos cambiaron en 2025 y 2026, y las respuestas informales de los compañeros suelen estar desactualizadas.
> Un chatbot general tampoco sirve: no conoce los reglamentos internos de la Escuela e inventa cifras con mucha seguridad. [pausa]
> Y hay casos delicados. Los lineamientos de opción de grado piden el 80 % de los créditos, mientras que el reglamento de prácticas de 2026 pide el 75 %. Un asistente que dé una sola cifra sin decir de dónde sale confunde al estudiante. [pausa]
> Por eso EciGuía tiene que responder solo con los documentos oficiales, citar documento y página, y decir "no sé" cuando la respuesta no está.

## E03 · Objetivos (1:15–1:45, unas 75 palabras)

**Visual:** diapositiva `E03_objetivos`: el objetivo general y los 3 específicos, que aparecen uno por uno.

**Narración:**
> El objetivo general es un asistente local que responda preguntas académicas citando la fuente y reconociendo lo que está fuera de su alcance. [pausa]
> Tiene tres objetivos específicos: primero, un pipeline de RAG sobre los documentos oficiales, comparando dos formas de partirlos; segundo, un agente con LangGraph que decide si buscar en documentos, usar una herramienta o rechazar la pregunta; y tercero, medir todo con preguntas de respuesta conocida.

## E04 · Trabajos relacionados (1:45–2:25, unas 100 palabras)

**Visual:** diapositiva `E04_trabajos`: RAG (Lewis et al., 2020), BGE-M3 (2024), ReAct (2023), asistentes para la USP (2025), REBot (2025) y Maastricht (2026); a la derecha, "Lo que aporta EciGuía".

**Narración:**
> La base es la generación aumentada con recuperación, o RAG, de Lewis y otros: buscar los fragmentos relevantes y dárselos al modelo para que no invente. La idea de que el modelo use herramientas viene de ReAct. [pausa]
> Hay trabajos muy parecidos: asistentes de reglamentos para la Universidad de São Paulo, para una universidad en Vietnam y para Maastricht. [pausa]
> EciGuía se diferencia en que corre completamente local, en una GPU de portátil de seis gigas; combina RAG con herramientas por MCP para fechas, valores y planes de estudio; y mide con datos cuándo decir que no sabe.

## E05 · Arquitectura (2:25–4:00, unas 235 palabras)

**Visual:**
1. Diapositiva `E05_arquitectura`: diagrama pregunta → router → tres rutas.
2. `docs/resultados/grafo.png` (grafo de LangGraph).
3. Diapositiva `E05_fuentes`: "cada fuente con su tratamiento": prosa → RAG · escaneados → transcripción · tablas → herramientas MCP · reglamento con artículos derogados → descartado.
4. `raw/E05_notebook`: recorrido por el notebook (tabla de fragmentos en 3.2, herramientas MCP en 3.5 y 3.8).

**Narración:**
> Así funciona. Cada pregunta pasa primero por un router: el mismo modelo de lenguaje, Qwen 2.5 de siete mil millones de parámetros, que decide entre tres rutas. [pausa]
> Si es sobre reglamentos, busca los cuatro fragmentos más parecidos en una base vectorial con embeddings BGE-M3. Si ninguno está lo bastante cerca, por debajo de un umbral que calibré con datos, responde "no encontré" sin llamar al modelo. Si hay fragmentos, responde citando documento, artículo y página. [pausa]
> Si la pregunta necesita un dato exacto, como una fecha del calendario, el valor de la matrícula de 2027 o el semestre de una materia, va a un servidor MCP con cinco herramientas. El agente no las tiene programadas: le pregunta al servidor cuáles hay y el modelo elige. [pausa]
> Y si es de otro tema, la rechaza. [pausa]
> La parte más difícil fueron los documentos reales. Los reglamentos con texto se parten por artículo, detectando los títulos por la negrita del PDF. Los acuerdos escaneados los transcribí y verifiqué contra el original. Las tablas de matrícula y las mallas se volvieron datos estructurados para consultarlos con herramientas, porque como texto salían revueltas. Y descarté el reglamento estudiantil de 2018, porque trae artículos que ya fueron derogados. [pausa]
> Todo corre local con Ollama: las preguntas se convierten en embeddings en el procesador, y la GPU queda para el modelo de lenguaje.

## E06 · Demo en vivo (4:00–6:40, unas 300 palabras más el tiempo de lectura)

**Visual:** la app, un clip por pregunta. En cada respuesta, zoom a la sección **Ruta / Herramienta / Fuentes**. Las esperas del LLM se aceleran con rótulo.

**Narración (una entrada por clip, se graban seguidas en `E06.wav`, con 2 s de silencio entre clips):**

**q1 · ¿La práctica profesional puede ser de medio tiempo?**
> Primera pregunta, sobre reglamentos. [pausa] Responde que no, que la práctica es de tiempo completo, y cita el artículo 14 del reglamento de prácticas con su página. Ningún fragmento dice "medio tiempo": el modelo tuvo que deducirlo, y esa fue una de las fallas que corregí durante la evaluación.

**q2 · ¿Hasta cuándo puedo cancelar el semestre?**
> No dije el periodo. Usa la herramienta del calendario por MCP y responde con la fecha del semestre vigente, no con una cualquiera. Un error real que encontré fue que el modelo se inventaba el periodo; ahora el código solo lo filtra si la pregunta lo menciona.

**q3 · ¿Cuánto cuesta la matrícula de ingeniería en 2027?**
> Esta usa una herramienta de la segunda etapa: los valores oficiales de 2027. Da el rango del mínimo al máximo, explica que depende del rango socioeconómico y cita la resolución de rectoría.

**q4 · ¿En qué semestre se ve Arquitecturas de Software?**
> Plan de estudios de Ingeniería de Sistemas. Como hay dos planes vigentes, responde para los dos: sexto semestre en el plan nuevo y octavo en el anterior.

**q5 · ¿Qué materias se ven en quinto semestre de Ingeniería Civil?**
> Ahora una trampa. Solo tengo el plan de Sistemas. Una versión anterior respondía con las materias de Sistemas como si fueran de Civil; ahora la herramienta detecta que es otro programa y lo dice.

**q6 · ¿Cuántas faltas de asistencia se permiten antes de perder una materia?**
> Y la trampa más importante: esa regla no está en los documentos que cargué. En vez de inventar un número, dice que no encontró la información. Para un asistente académico, esto es lo más valioso.

## E07 · Resultados (6:40–8:05, unas 210 palabras)

**Visual:**
1. Diapositiva `E07_corridas`: tabla de las 6 corridas de la primera etapa (de `docs/resultados/comparativa.csv`).
2. `docs/resultados/calibracion_etapa1.png`.
3. Diapositiva `E07_etapa2`: "Corpus de 6 a 13 documentos · 0 regresiones en 40 preguntas · 55/55 correctas en revisión manual · router 97 % en un set aparte".
4. Diapositiva `E07_juez`: "El juez automático coincidió conmigo en 8 de 10; cuando falló, fue más permisivo".

**Narración:**
> Evalué con preguntas de respuesta conocida, cambiando una sola cosa a la vez. [pausa] El RAG solo ya respondía bien los reglamentos; lo que aportó el agente fueron las fechas y los cálculos, que pasaron del 25 al 100 %, y los rechazos correctos. [pausa]
> Esta gráfica es la calibración del umbral. En azul, preguntas cuya respuesta sí está; en naranja, preguntas cuya respuesta no está. El valor inicial casi no filtraba nada. Con el umbral calibrado pasan todas las válidas y se bloquea la mayoría de las demás. [pausa]
> En la segunda etapa amplié el corpus de 6 a 13 documentos y agregué dos herramientas, y lo medí como prueba de regresión: cero preguntas empeoraron, y en revisión manual el sistema respondió bien las 55 preguntas con respuesta. El router acertó el 97 % en un set de preguntas que nunca usé para escribir los prompts. [pausa]
> Y no me fié del juez automático: lo revisé a mano y coincidió conmigo en 8 de 10 casos. Cuando falló, fue demasiado permisivo, así que sus cifras son un techo, no un piso.

## E08 · Conclusión (8:05–8:55, unas 125 palabras)

**Visual:**
1. Diapositiva `E08_conclusion`: los 3 objetivos cumplidos, las limitaciones y el trabajo futuro.
2. `raw/E08_github`: página del repositorio en GitHub.

**Narración:**
> En resumen: cumplí los tres objetivos. Un RAG que cita documento y página y sabe decir "no sé"; un agente que usa herramientas MCP para los datos exactos; y una evaluación que muestra la mejora y que ampliar el sistema no rompió lo anterior. [pausa]
> Las limitaciones: falta el reglamento estudiantil consolidado y vigente, el plan de estudios solo cubre Sistemas, y la latencia es de unos quince segundos por pregunta en mi portátil. [pausa]
> Como trabajo futuro: cargar el reglamento consolidado, agregar los demás programas y probarlo con estudiantes reales. [pausa]
> El código, el informe y los resultados están en GitHub. Gracias.
