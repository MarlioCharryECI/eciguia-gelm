# Datos para publicar el video

**Visibilidad:** **Público**. La rúbrica 2026-2 exige un video público, y "no listado" podría no contar como público. Otra opción es subirlo a Drive con "Cualquier persona con el enlace puede ver".

**Título:**
EciGuía: asistente académico con RAG, agentes y MCP (100 % local) · Proyecto final GELM 2026-2

**Descripción:**

EciGuía responde preguntas de estudiantes de pregrado de la Escuela Colombiana de Ingeniería Julio Garavito con base en documentos oficiales: reglamentos, acuerdos, calendario 2027, valores de matrícula 2027 y plan de estudios de Ingeniería de Sistemas. Cita el documento y la página, y dice "no sé" cuando la respuesta no está en sus documentos.

Cómo funciona: un agente con LangGraph enruta cada pregunta a una de tres rutas: RAG sobre 13 documentos (bge-m3 + Chroma, con un umbral de relevancia calibrado), herramientas por MCP (calendario, valores 2027, plan de estudios, promedio) o rechazo. El modelo es Qwen 2.5 7B en Ollama y todo corre en un portátil con una GPU de 6 GB.

Evaluación: 66 preguntas de respuesta conocida; 55/55 respuestas correctas y 12/12 trampas rechazadas en revisión manual; 0 regresiones al ampliar el corpus de 6 a 13 documentos.

Código, pruebas y evaluación: https://github.com/MarlioCharryECI/eciguia-gelm

Autor: Marlio José Charry Espitia · IA Generativa (GELM) 2026-2

Nota: la narración usa una voz sintética (Microsoft Edge TTS, voz "Gonzalo", es-CO). Las respuestas que aparecen en la demo son reales, producidas por el sistema en vivo; solo se acortó la espera del modelo, y en pantalla se indica cuánto tardó cada respuesta.

**Capítulos** (pegar en la descripción; revisar los tiempos si el corte cambia):
```
0:00 EciGuía
0:12 El problema
0:35 Cómo funciona
1:04 Demo: reglamento con cita
1:16 Demo: calendario
1:28 Demo: valores de matrícula 2027
1:40 Demo: plan de estudios
1:52 Demo: trampas y fuera de alcance
2:31 Resultados
2:53 Límites y código
```
