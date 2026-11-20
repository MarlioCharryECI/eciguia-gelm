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

CHUNK_STRATEGY = os.getenv("ECIGUIA_CHUNKING", "articulo")  # "articulo" o "fijo"
TOP_K = int(os.getenv("ECIGUIA_TOP_K", "4"))
# Distancia coseno máxima para aceptar un fragmento como relevante (0 = idéntico, 2 = opuesto)
MAX_DISTANCE = float(os.getenv("ECIGUIA_MAX_DISTANCE", "0.65"))

# Nombres legibles para citar cada documento
DOCUMENT_TITLES = {
    "modificacion_reglamento_estudiantil_2025.pdf": "Modificación al Reglamento Estudiantil de Pregrado (2025)",
    "reglamento_practicas_profesionales.pdf": "Reglamento de Prácticas Profesionales en Pregrado",
    "lineamientos_opcion_de_grado.pdf": "Lineamientos para Opción de Grado",
    "reglamento_trabajos_dirigidos.pdf": "Reglamento de Trabajos Dirigidos",
    "reglamento_movilidad_estudiantil.pdf": "Reglamento de Movilidad Estudiantil de Pregrado",
    "reglamento_ingles_2025.pdf": "Reglamento de Inglés (2025)",
}
