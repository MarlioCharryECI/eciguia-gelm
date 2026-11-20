"""Configuración central. Todo se puede cambiar con variables de entorno o un archivo .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"
CALENDAR_PATH = ROOT / "data" / "calendario_2027.json"
CHROMA_DIR = ROOT / "data" / "chroma"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("ECIGUIA_LLM", "qwen2.5:7b")
EMBED_MODEL = os.getenv("ECIGUIA_EMBED", "bge-m3")
# Con GPUs de 6 GB el LLM y los embeddings no caben juntos y Ollama los intercambia en cada pregunta.
# Embeber solo la consulta en CPU tarda ~0,1 s y deja la GPU para el LLM. La ingesta sí usa GPU.
EMBED_QUERY_ON_CPU = os.getenv("ECIGUIA_EMBED_QUERY_ON_CPU", "1") == "1"
KEEP_ALIVE = int(os.getenv("ECIGUIA_KEEP_ALIVE", "1800"))  # segundos que Ollama mantiene cargados los modelos

CHUNK_STRATEGY = os.getenv("ECIGUIA_CHUNKING", "articulo")  # "articulo" o "fijo"
TOP_K = int(os.getenv("ECIGUIA_TOP_K", "4"))
# Distancia coseno máxima para aceptar un fragmento como relevante (0 = idéntico, 2 = opuesto).
# Calibrada con eval/calibrate.py: con 0,45 pasan las 25 preguntas con respuesta y se bloquea el 81 % de
# 27 preguntas sin respuesta en los documentos (con 0,65, el valor inicial, solo se bloqueaba el 7 %).
MAX_DISTANCE = float(os.getenv("ECIGUIA_MAX_DISTANCE", "0.45"))

# Nombres legibles para citar cada documento
DOCUMENT_TITLES = {
    "modificacion_reglamento_estudiantil_2025.pdf": "Modificación al Reglamento Estudiantil de Pregrado (2025)",
    "reglamento_practicas_profesionales.pdf": "Reglamento de Prácticas Profesionales en Pregrado",
    "lineamientos_opcion_de_grado.pdf": "Lineamientos para Opción de Grado",
    "reglamento_trabajos_dirigidos.pdf": "Reglamento de Trabajos Dirigidos",
    "reglamento_movilidad_estudiantil.pdf": "Reglamento de Movilidad Estudiantil de Pregrado",
    "reglamento_ingles_2025.pdf": "Reglamento de Inglés (2025)",
}
