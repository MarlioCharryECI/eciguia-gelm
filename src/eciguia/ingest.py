"""Carga los PDFs oficiales, los limpia, los divide en fragmentos y construye el índice vectorial.

Uso:
    uv run python -m eciguia.ingest                 # chunking por artículo (por defecto)
    uv run python -m eciguia.ingest --strategy fijo # chunking de tamaño fijo
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from eciguia import config

ARTICLE_RE = re.compile(r"(?m)^(?=Art[ií]culo\s+\d+[°º]?\s*[\.\-:])")
MAX_ARTICLE_CHARS = 1500


@dataclass
class Page:
    source: str
    number: int
    text: str


# ---------------------------------------------------------------- extracción

def _is_boilerplate(text: str) -> bool:
    """Páginas con la lista del Consejo Directivo, créditos de publicación, etc."""
    lowered = text.lower()
    return ("vocales" in lowered and "representante" in lowered) or len(lowered.split()) < 15


def _page_text(page: pdfplumber.page.Page) -> str:
    """Texto de una página. Las tablas 'Versión actual / Nueva versión' se leen solo por la derecha."""
    words = page.extract_words()
    headers = [
        w for i, w in enumerate(words)
        if w["text"] == "Nueva" and i + 1 < len(words) and words[i + 1]["text"].startswith("versi")
    ]
    if not headers:
        return page.extract_text() or ""

    top = min(w["top"] for w in headers)
    column_x = min(w["x0"] for w in headers) - 8
    above = page.crop((0, 0, page.width, top)).extract_text() or ""
    new_version = page.crop((column_x, top, page.width, page.height)).extract_text() or ""
    return f"{above}\n{new_version}"


def _clean(text: str) -> str:
    text = re.sub(r"UNIVERSIDAD ESCUELA COLOMBIANA DE INGENIER[IÍ]A JULIO GARAVITO\s*\d*", " ", text)
    text = re.sub(r"(?im)^.*\|\s*P[aá]gina \d+ de \d+.*$", " ", text)
    text = re.sub(r"(?m)^\s*\d+\s*$", " ", text)            # números de página sueltos
    text = re.sub(r"(?im)^.*(L[ií]nea nacional gratuita|Vigilada Mineducaci[oó]n|www\.escuelaing\.edu\.co).*$", " ", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)              # palabras partidas con guion
    # Une las líneas cortadas de un mismo párrafo, pero respeta artículos, parágrafos y listas
    text = re.sub(r"\n(?!\s*(Art[ií]culo|Par[aá]grafo|T[ií]tulo|Cap[ií]tulo|\d+(\.\d+)*[\.\)]\s|[a-z]\)\s|•|\n))", " ", text)
    text = re.sub(r"Versi[oó]n actual|Nueva versi[oó]n|-{5,}", " ", text)
    text = text.replace("escUela", "Escuela")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _article_titles(page: pdfplumber.page.Page) -> list[str]:
    """Títulos de artículo, que en los reglamentos van en negrita: 'Artículo 10. Requisitos para ...'."""
    words = page.extract_words(extra_attrs=["fontname"])
    titles = []
    for i, word in enumerate(words):
        if not (re.match(r"Art[ií]culo$", word["text"]) and "Bold" in word["fontname"]):
            continue
        title = []
        for w in words[i:i + 30]:
            if title and re.fullmatch(r"[\.:]", w["text"]):  # a veces el punto de "Artículo 12." no va en negrita
                title[-1] += w["text"]
                continue
            if "Bold" not in w["fontname"] or (title and re.match(r"Art[ií]culo$", w["text"])):
                break
            title.append(w["text"])
        if len(title) > 2:
            titles.append(" ".join(title))
    return titles


def _split_titles(text: str, titles: list[str]) -> str:
    """Pone cada título de artículo en su propia línea, separado del cuerpo, para usarlo como sección."""
    for title in titles:
        pattern = r"\s+".join(re.escape(w) for w in title.split())
        text = re.sub(f"({pattern})[ \t]+", lambda m: m.group(1) + "\n", text, count=1)
    return text


def load_pages(raw_dir: Path = config.RAW_DIR) -> list[Page]:
    pages: list[Page] = []
    for path in sorted(raw_dir.glob("*.pdf")):
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                text = _split_titles(_clean(_page_text(page)), _article_titles(page))
                if not _is_boilerplate(text):
                    pages.append(Page(path.name, number, text))
    return pages


# ---------------------------------------------------------------- chunking

def _make_doc(source: str, page: int, section: str, text: str, page_end: int | None = None) -> Document:
    title = config.DOCUMENT_TITLES.get(source, source)
    header = f"{title}. {section}".strip(". ")
    return Document(
        page_content=f"{header}\n{text.strip()}",
        metadata={"source": source, "title": title, "page": page, "page_end": page_end or page, "section": section},
    )


def chunk_fixed(pages: list[Page], size: int = 1000, overlap: int = 150) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    docs = []
    for page in pages:
        for piece in splitter.split_text(page.text):
            docs.append(_make_doc(page.source, page.number, "", piece))
    return docs


def chunk_by_article(pages: list[Page]) -> list[Document]:
    """Un fragmento por artículo. Los artículos muy largos se parten conservando su encabezado.
    Los documentos sin artículos (inglés, lineamientos) caen en el chunking fijo."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=MAX_ARTICLE_CHARS, chunk_overlap=150)
    docs: list[Document] = []

    by_source: dict[str, list[Page]] = {}
    for page in pages:
        by_source.setdefault(page.source, []).append(page)

    for source, source_pages in by_source.items():
        full_text, offsets = "", []
        for page in source_pages:
            offsets.append((len(full_text), page.number))
            full_text += page.text + "\n"

        def page_at(pos: int) -> int:
            return max(num for start, num in offsets if start <= pos)

        starts = [m.start() for m in ARTICLE_RE.finditer(full_text)]
        if not starts:
            docs.extend(chunk_fixed(source_pages))
            continue

        # Texto antes del primer artículo (considerandos, presentación)
        intro = full_text[: starts[0]].strip()
        if len(intro) > 200:
            for piece in splitter.split_text(intro):
                docs.append(_make_doc(source, page_at(0), "Introducción", piece))

        bounds = starts + [len(full_text)]
        pending = ""  # encabezados sueltos (p. ej. el título de una tabla) se pegan al artículo siguiente
        for start, end in zip(bounds, bounds[1:]):
            body = (pending + "\n" + full_text[start:end]).strip() if pending else full_text[start:end].strip()
            if len(body) < 200 and end != len(full_text):
                pending = body
                continue
            pending = ""
            body = re.sub(r"^(Art[ií]culo \d+[^\n]*\n)(?:\s*Art[ií]culo \d+\s*\n|\s*Versi[oó]n actual.*\n|\s*Nueva versi[oó]n\s*\n)+", r"\1", body)
            first_line = body.split("\n", 1)[0]
            section = re.split(r"(?<=\.)\s", first_line, maxsplit=2)
            section = " ".join(section[:2]).strip()[:120]
            for piece in splitter.split_text(body):
                docs.append(_make_doc(source, page_at(start), section, piece, page_end=page_at(max(start, end - 1))))
    return docs


def chunk_documents(pages: list[Page], strategy: str = config.CHUNK_STRATEGY) -> list[Document]:
    if strategy == "articulo":
        return chunk_by_article(pages)
    if strategy == "fijo":
        return chunk_fixed(pages)
    raise ValueError(f"Estrategia desconocida: {strategy}")


# ---------------------------------------------------------------- índice

def get_embeddings(for_query: bool = False):
    from langchain_ollama import OllamaEmbeddings

    cpu = for_query and config.EMBED_QUERY_ON_CPU
    return OllamaEmbeddings(model=config.EMBED_MODEL, base_url=config.OLLAMA_BASE_URL,
                            keep_alive=config.KEEP_ALIVE, num_gpu=0 if cpu else None)


def collection_name(strategy: str) -> str:
    return f"eciguia_{strategy}"


def build_index(strategy: str = config.CHUNK_STRATEGY, embeddings=None, persist_dir: Path = config.CHROMA_DIR):
    from langchain_chroma import Chroma

    embeddings = embeddings or get_embeddings()
    docs = chunk_documents(load_pages(), strategy)
    store = Chroma(
        collection_name=collection_name(strategy),
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )
    store.reset_collection()
    ids = [f"{strategy}-{i}" for i in range(len(docs))]
    store.add_documents(docs, ids=ids)
    return store, docs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", default=config.CHUNK_STRATEGY, choices=["articulo", "fijo"])
    args = parser.parse_args()
    _, docs = build_index(args.strategy)
    sources = {d.metadata["source"] for d in docs}
    print(f"Índice '{collection_name(args.strategy)}' creado con {len(docs)} fragmentos de {len(sources)} documentos")


if __name__ == "__main__":
    main()
