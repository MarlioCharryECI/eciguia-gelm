"""Dobles de prueba: permiten probar todo el pipeline sin Ollama."""

from __future__ import annotations

import json
import re

import numpy as np
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import HashingVectorizer


class HashEmbeddings(Embeddings):
    """Embeddings por bolsa de palabras con hashing. No son semánticos, pero son deterministas."""

    def __init__(self, dim: int = 1024):
        self.vectorizer = HashingVectorizer(n_features=dim, alternate_sign=False, norm="l2", ngram_range=(1, 2))

    def _embed(self, texts):
        return self.vectorizer.transform(texts).toarray().astype(np.float32).tolist()

    def embed_documents(self, texts):
        return self._embed(texts)

    def embed_query(self, text):
        return self._embed([text])[0]


class Reply:
    def __init__(self, content: str):
        self.content = content


class ScriptedLLM:
    """Responde según el tipo de prompt, imitando lo que haría un LLM real."""

    async def ainvoke(self, prompt: str):
        if "Eres el enrutador" in prompt:
            question = prompt.rsplit("Pregunta:", 1)[1].lower()
            if any(w in question for w in ("película", "receta", "andes", "fútbol")):
                route = "fuera_de_alcance"
            elif any(w in question for w in ("cuándo", "fecha", "promedio", "días")):
                route = "herramienta"
            else:
                route = "documentos"
            return Reply(json.dumps({"ruta": route, "razon": "prueba"}))
        if "herramientas disponibles por MCP" in prompt:
            question = prompt.rsplit("Pregunta:", 1)[1]
            if "promedio" in question.lower():
                pairs = re.findall(r"(\d[\.,]\d)\D+?(\d) créditos", question)
                args = {"asignaturas": [{"nota": float(n.replace(",", ".")), "creditos": int(c)} for n, c in pairs]}
                return Reply(json.dumps({"herramienta": "calcular_promedio_ponderado", "argumentos": args}))
            return Reply(json.dumps({"herramienta": "consultar_calendario",
                                     "argumentos": {"consulta": "cancelación de asignaturas", "periodo": "2027-1"}}))
        if "Fragmentos:" in prompt:
            first = prompt.split("[1]", 1)[1].split("\n", 2)
            return Reply(f"Según el reglamento [1]: {first[1][:150]}...")
        if "Usaste la herramienta" in prompt:
            result = prompt.split("resultado:", 1)[1].split("Responde", 1)[0].strip()
            return Reply(f"Resultado: {result[:200]}")
        return Reply("respuesta genérica")
