"""Búsqueda semántica sobre el índice de Chroma, con filtro por relevancia y formato de citas."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document

from eciguia import config


@dataclass
class Hit:
    doc: Document
    distance: float  # distancia coseno: menor es más parecido

    @property
    def citation(self) -> str:
        meta = self.doc.metadata
        section = f", {meta['section']}" if meta.get("section") else ""
        return f"{meta['title']}{section} (pág. {meta['page']})"


class Retriever:
    def __init__(self, store=None, strategy: str = config.CHUNK_STRATEGY, k: int = config.TOP_K,
                 max_distance: float = config.MAX_DISTANCE):
        if store is None:
            from langchain_chroma import Chroma

            from eciguia.ingest import collection_name, get_embeddings

            store = Chroma(
                collection_name=collection_name(strategy),
                embedding_function=get_embeddings(),
                persist_directory=str(config.CHROMA_DIR),
            )
        self.store = store
        self.k = k
        self.max_distance = max_distance

    def search(self, query: str) -> list[Hit]:
        """Devuelve los k fragmentos más cercanos, ya filtrados por el umbral de distancia."""
        results = self.store.similarity_search_with_score(query, k=self.k)
        return [Hit(doc, score) for doc, score in results if score <= self.max_distance]


def format_context(hits: list[Hit]) -> str:
    """Contexto numerado para el prompt: [1] cita + texto."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        text = hit.doc.page_content.split("\n", 1)[-1]
        blocks.append(f"[{i}] {hit.citation}\n{text}")
    return "\n\n".join(blocks)
