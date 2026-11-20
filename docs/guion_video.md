# Guion del video: EciGuía (9 minutos)

Rúbrica: el video debe durar entre 5 y 10 minutos, explicar el proyecto con claridad y presentarlo completo junto con la problemática. Este guion apunta a 9 minutos para tener margen.

## Antes de grabar (lista de chequeo)

- [ ] Ollama abierto. Precargar el modelo para que la primera respuesta no tarde 1 minuto: `ollama run qwen2.5:7b "hola"` y salir con `/bye`.
- [ ] `$env:PYTHONUTF8=1; uv run python app.py` y abrir http://localhost:7860. Hacer una pregunta de calentamiento **antes** de grabar (la primera carga el servidor MCP y los embeddings).
- [ ] Tener abiertos en pestañas: `proyecto.ipynb` (ya ejecutado), `docs/resultados/calibracion.png`, `docs/resultados/grafo.png`, `src/eciguia/prompts.py`.
- [ ] Cerrar notificaciones y programas pesados (la GPU es de 6 GB: cada respuesta tarda entre 10 y 20 s).
- [ ] Grabar con OBS o con la grabación de pantalla de Windows (Win + Alt + R), micrófono revisado.
- [ ] Las respuestas que dependen de "hoy" (cancelación del semestre, días que faltan) cambian según el día en que grabes. Revisa que lo que dice la app coincida con el calendario.

Consejo: las respuestas tardan entre 10 y 20 s. Mientras el modelo piensa, explica lo que está pasando ("ahora el router clasificó la pregunta, está buscando en Chroma…") y en la edición recorta la espera si hace falta.

---

## 1. Problema (0:00 a 1:00)

**En pantalla:** la página de reglamentos de escuelaing.edu.co con la lista de PDFs, luego la imagen del calendario 2027.

**Guion:**
> "Hola, soy Marlio José Charry Espitia y este es EciGuía, mi proyecto final de IA Generativa.
> Como estudiante de la Escuela, cuando quiero saber cuándo puedo hacer la práctica, cuánto pago si me voy de intercambio o hasta cuándo cancelo una materia, la respuesta está repartida en seis reglamentos en PDF, 76 páginas, y en un calendario que se publica como imagen. Y cinco de esos seis documentos cambiaron en 2025 o 2026.
> Si le pregunto a ChatGPT, no conoce los reglamentos internos e inventa cifras con mucha seguridad. Y hay un caso que muestra el problema: los lineamientos de opción de grado piden el 80 % de los créditos, pero el reglamento de prácticas de 2026 pide el 75 %.
> El objetivo: un asistente que responda con base en los documentos oficiales, que cite de dónde sale cada dato y que diga 'no sé' cuando la respuesta no está. Y que corra 100 % local, gratis, con modelos abiertos."

**Objetivos (mostrar la celda de objetivos del notebook):** RAG con dos estrategias de chunking, agente LangGraph con herramientas MCP y evaluación con 40 preguntas.

## 2. Trabajos relacionados (1:00 a 2:00)

**En pantalla:** sección 2 del notebook.

**Guion:**
> "La base es RAG, de Lewis y otros, 2020: recuperar fragmentos relevantes y dárselos al modelo para que no invente. Para los embeddings uso BGE-M3, que funciona bien en español. La idea de que el modelo decida usar herramientas viene de ReAct.
> Hay trabajos muy parecidos: un asistente RAG para la Universidad de São Paulo, donde el acierto sube de 14 % a 54 % cuando el modelo recibe los fragmentos correctos; REBot, para los reglamentos de una universidad vietnamita; y un asistente para los proyectos de grado de Maastricht.
> ¿En qué se diferencia EciGuía? Corre completamente local en una GPU de portátil de 6 GB, combina RAG con herramientas por MCP para fechas y cálculos, calibra con datos cuándo decir 'no sé' y muestra las contradicciones entre reglamentos en vez de esconderlas."

## 3. Arquitectura (2:00 a 4:00)

**En pantalla:** diagrama de la sección 3.1 y luego `grafo.png`.

**Guion (2:00 a 3:00), el flujo:**
> "Cuando llega una pregunta, un router, que es el mismo LLM en modo JSON, la clasifica en tres rutas.
> Si es sobre reglamentos, va a la ruta de documentos: busca los 4 fragmentos más parecidos en Chroma. Si ninguno está lo bastante cerca, por debajo de un umbral que calibré, responde 'no encontré' sin siquiera llamar al modelo. Si hay fragmentos, el LLM responde citando [1], [2].
> Si la pregunta necesita una fecha del calendario o un cálculo, va a la ruta de herramientas: un servidor MCP que expone tres herramientas, el calendario, los días que faltan y el promedio ponderado. El agente no las tiene programadas: le pregunta al servidor qué herramientas hay y el modelo elige.
> Y si es de otro tema, la rechaza amablemente."

**En pantalla (3:00 a 4:00):** notebook, sección 3.2. Mostrar la tabla de fragmentos y el ejemplo del artículo 12.

> "Dos detalles de ingeniería. Primero, el chunking: comparé fragmentos de tamaño fijo contra un fragmento por artículo. Para que cada fragmento lleve el nombre de su artículo detecto los títulos por la negrita del PDF. Así la cita dice 'Artículo 12. Duración de la práctica profesional nacional, página 10'.
> Segundo, la modificación al reglamento viene en tablas de versión actual y nueva versión: solo leo la nueva, para no citar normas derogadas.
> Todo corre local: Qwen 2.5 de 7 mil millones de parámetros en Ollama. Como la GPU es de 6 GB, los dos modelos no caben juntos y Ollama los intercambiaba en cada pregunta. Los embeddings de las preguntas ahora van en CPU, que tarda una décima de segundo, y la GPU queda para el LLM: cada respuesta tarda unos 10 a 20 segundos."

## 4. Demo en vivo (4:00 a 6:30)

**En pantalla:** la app de Gradio. Cuatro preguntas; después de cada una, señalar la **ruta**, la **herramienta** y las **fuentes** debajo de la respuesta.

1. **"¿La práctica profesional puede ser de medio tiempo?"** (ruta documentos)
   > "Ruta reglamentos. Responde que no, que es de tiempo completo, y cita el artículo 14 con su página. Esta pregunta fallaba en una versión anterior del prompt; ahora vuelvo a eso."
2. **"¿Hasta cuándo puedo cancelar el semestre?"** (ruta herramienta)
   > "No dije el periodo. Usó la herramienta consultar_calendario por MCP y me da la fecha del semestre en curso, no la de 2027. Este fue un error real que encontré: el modelo se inventaba el periodo 2027-1, y lo corregí en el código."
3. **"Saqué 4.2 en una materia de 3 créditos y 3.6 en una de 4, ¿cuál es mi promedio?"** (herramienta de promedio)
   > "Extrae las notas y los créditos, llama a la herramienta y da 3,9 con un decimal, como el promedio oficial, y el valor exacto. El cálculo lo hace la herramienta, no el LLM, que suele equivocarse con la aritmética."
4. **"¿Cuántas faltas de asistencia se permiten antes de perder una materia?"** (trampa)
   > "Esta es una trampa: está en el Reglamento Estudiantil completo, que no cargué. En vez de inventar un número, dice que no tiene esa información. Esto es lo más importante en un asistente académico."
   (Según la redacción, a veces responde "no encontré" por la ruta de documentos y a veces la rechaza el router. Las dos son correctas: lo importante es que no invente un número.)

Si sobra tiempo: **"¿Me recomiendas una película?"**, que se rechaza en unos 3 segundos.

## 5. Resultados (6:30 a 8:00)

**En pantalla:** la tabla de experimentos del notebook (sección 4.1), luego la gráfica de calibración.

**Guion:**
> "Evalué con 40 preguntas de respuesta conocida, en 6 corridas donde cada una cambia una sola cosa." *(Leer las cifras de la tabla del notebook: recuperación de fijo frente a artículo, el salto de ruteo y herramientas al agregar el router, y el acierto final.)*
> "Esta gráfica es la calibración del umbral: azul, preguntas cuya respuesta sí está; naranja, preguntas que no. Con el valor inicial de 0,65 casi no se bloqueaba nada, el 7 %. Con 0,45, elegido con estos datos, pasan todas las preguntas válidas y se bloquea el 81 % de las que no tienen respuesta. Las que se cuelan las frena el prompt.
> Y no me fié del juez automático: revisé 10 veredictos a mano y coincidió en 8. En los otros 2 fue demasiado permisivo, así que las cifras de acierto son un techo, no un piso."
> *(Mencionar 1 de los 3 fallos analizados, por ejemplo el router mandando preguntas de costos de matrícula a 'fuera de alcance' por un ejemplo mal elegido en el prompt, y cómo se comprobó la corrección en un set aparte.)*

## 6. Conclusión (8:00 a 9:00)

**En pantalla:** sección 5 del notebook.

**Guion:**
> "En resumen: cumplí los tres objetivos. Un RAG que cita artículo y página y sabe decir 'no sé', un agente con LangGraph que usa herramientas MCP para fechas y cálculos, y una evaluación que muestra con datos la mejora entre versiones.
> Las limitaciones: falta el Reglamento Estudiantil completo, el corpus es pequeño, el calendario se transcribió a mano y el juez es el mismo modelo que responde.
> Como trabajo futuro: cargar el reglamento completo, buscar en los documentos relacionados para mostrar siempre las contradicciones, y probarlo con estudiantes reales.
> El código está en GitHub. Gracias."
