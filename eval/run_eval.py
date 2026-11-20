"""Evalúa EciGuía contra el set de 40 preguntas con respuesta conocida.

Experimentos del proyecto (cada uno cambia una sola cosa respecto al anterior):
    uv run python eval/run_eval.py --name 1_base --baseline --prompt basico --strategy fijo
    uv run python eval/run_eval.py --name 2_chunk_articulo --baseline --prompt basico
    uv run python eval/run_eval.py --name 3_router_tools --prompt basico
    uv run python eval/run_eval.py --name 4_prompt_v1 --prompt v1
    uv run python eval/run_eval.py --name 5_prompt_v2 --prompt v2
    uv run python eval/run_eval.py --name 6_final --router v2 --prompt v3    # la configuración de la app

Cada corrida guarda eval/results/<name>.csv (detalle) y eval/results/<name>.json (resumen).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import functools
import json
import statistics
from pathlib import Path

from eciguia import prompts
from eciguia.ingest import chunk_documents, load_pages
from eciguia.graph import EciGuiaAgent, _parse_json, _text, default_llm
from eciguia.retriever import Retriever, format_context

EVAL_DIR = Path(__file__).parent
REJECTION_MARKERS = ("Solo puedo ayudarte", "No encontré")

JUDGE_PROMPT = """Eres un evaluador estricto. Compara la respuesta de un asistente con la respuesta esperada.

Pregunta: {question}
Respuesta esperada: {expected}
Respuesta del asistente: {answer}
Contexto que tenía el asistente: {context}

Evalúa:
- "correcta": true si la respuesta del asistente contiene la información clave de la esperada sin contradecirla.
- "fiel": true si todo lo que afirma el asistente está respaldado por el contexto (o si no hay contexto y no afirma datos).

Responde SOLO con JSON: {{"correcta": true|false, "fiel": true|false, "comentario": "<máximo 15 palabras>"}}"""


def load_golden() -> list[dict]:
    with open(EVAL_DIR / "golden_set.jsonl", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


@functools.cache
def article_pages() -> dict[tuple[str, str], tuple[int, int]]:
    """Páginas que ocupa cada artículo: (documento, "Artículo N") -> (primera, última)."""
    spans: dict[tuple[str, str], tuple[int, int]] = {}
    for doc in chunk_documents(load_pages(), "articulo"):
        meta = doc.metadata
        key = (meta["source"], meta["section"].split(".")[0])
        first, last = spans.get(key, (meta["page"], meta["page_end"]))
        spans[key] = (min(first, meta["page"]), max(last, meta["page_end"]))
    return spans


def _is_expected(meta: dict, item: dict, exact: bool = False) -> bool:
    """¿El fragmento es del documento y artículo esperados?

    Por defecto el criterio es por páginas: el fragmento cuenta si es del documento esperado y cae en las
    páginas que ocupa el artículo. Sirve igual para las dos estrategias (los fragmentos de tamaño fijo no
    tienen sección), aunque es laxo: en la misma página puede haber otro artículo.
    Con exact=True se exige la sección exacta ("Artículo 1" no acepta "Artículo 10. ..."); solo tiene
    sentido con chunking por artículo.
    """
    section = item.get("seccion", "")
    if meta["source"] != item["fuente"]:
        return False
    if not section:
        return True
    if exact:
        return meta.get("section", "").split(".")[0] == section
    first, last = article_pages()[(item["fuente"], section)]
    return first <= meta["page"] <= last


def retrieval_metrics(retriever: Retriever, item: dict, strategy: str) -> dict:
    """¿Aparece el fragmento correcto entre los k recuperados?
    Se mide antes y después del umbral, para separar la calidad del retriever del efecto del filtro."""
    raw = retriever.store.similarity_search_with_score(item["pregunta"], k=retriever.k)
    return {
        "hit_retriever": any(_is_expected(doc.metadata, item) for doc, _ in raw),
        "hit_con_umbral": any(_is_expected(doc.metadata, item) for doc, d in raw if d <= retriever.max_distance),
        "hit_articulo_exacto": any(_is_expected(doc.metadata, item, exact=True) for doc, _ in raw)
        if strategy == "articulo" else None,
    }


async def judge(llm, item: dict, state: dict) -> dict:
    context = format_context(state.get("hits", [])) or json.dumps(state.get("tool_result"), ensure_ascii=False, default=str)
    reply = await llm.ainvoke(JUDGE_PROMPT.format(
        question=item["pregunta"], expected=item["respuesta_esperada"], answer=state["answer"], context=context[:4000]
    ))
    try:
        return _parse_json(_text(reply))
    except Exception:
        return {"correcta": None, "fiel": None, "comentario": "el juez no devolvió JSON"}


async def run(args) -> None:
    retriever = Retriever(strategy=args.strategy)
    agent = EciGuiaAgent(retriever=retriever, rag_prompt=prompts.RAG_PROMPTS[args.prompt],
                         router_prompt=prompts.ROUTER_PROMPTS[args.router], use_router=not args.baseline)
    judge_llm = default_llm(json_mode=True, model=args.judge_model) if args.judge_model else agent.json_llm
    rows = []

    for item in load_golden():
        state = await agent.ask(item["pregunta"])
        expected_route = item["tipo"]
        row = {
            "id": item["id"],
            "tipo": item["tipo"],
            "pregunta": item["pregunta"],
            "ruta": state["route"],
            "ruta_correcta": state["route"] == expected_route
            or (expected_route == "trampa" and state["route"] in ("documentos", "fuera_de_alcance")),
            "herramienta": state.get("tool_name", ""),
            "respuesta": state["answer"],
            "fuentes": " | ".join(state.get("sources", [])),
            "latencia_s": state["latency_s"],
            "distancias": " ".join(f"{h.distance:.3f}" for h in state.get("hits", [])),
            "error": state.get("error", ""),
        }
        if item["tipo"] == "documentos":
            row.update(retrieval_metrics(retriever, item, args.strategy))
        if item["tipo"] == "herramienta":
            row["herramienta_correcta"] = state.get("tool_name") == item["herramienta"]
        if item["tipo"] in ("fuera_de_alcance", "trampa"):
            row["rechazo_correcto"] = any(m in state["answer"] for m in REJECTION_MARKERS)
        if args.judge and item["tipo"] in ("documentos", "herramienta"):
            verdict = await judge(judge_llm, item, state)
            row["correcta"] = verdict.get("correcta")
            row["fiel"] = verdict.get("fiel")
            row["comentario_juez"] = verdict.get("comentario", "")
        rows.append(row)
        print(f"{item['id']:>4}  ruta={row['ruta']:<16} {row['latencia_s']:>5}s  {state['answer'][:70]!r}")

    summary = summarize(rows, args)
    out = EVAL_DIR / "results"
    out.mkdir(exist_ok=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(out / f"{args.name}.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (out / f"{args.name}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def recompute_retrieval(name: str) -> None:
    """Recalcula solo las métricas de recuperación de una corrida guardada, sin volver a llamar al LLM."""
    out = EVAL_DIR / "results"
    summary = json.loads((out / f"{name}.json").read_text(encoding="utf-8"))
    with open(out / f"{name}.csv", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    strategy = summary["config"]["chunking"]
    retriever = Retriever(strategy=strategy)
    golden = {item["id"]: item for item in load_golden()}
    for row in rows:
        if row["tipo"] == "documentos":
            row.update(retrieval_metrics(retriever, golden[row["id"]], strategy))
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    hits = [r for r in rows if r["tipo"] == "documentos"]
    summary = {k: v for k, v in summary.items() if not k.startswith("hit@")}
    hit_metrics = {}
    for key, column in (("hit@k_retriever", "hit_retriever"), ("hit@k_con_umbral", "hit_con_umbral"),
                        ("hit@k_articulo_exacto", "hit_articulo_exacto")):
        values = [r[column] for r in hits if r.get(column) not in (None, "")]
        hit_metrics[key] = round(sum(str(v) == "True" for v in values) / len(values), 3) if values else None
    # se reinsertan las métricas de recuperación después de "n" para conservar el orden del resumen
    ordered = {}
    for k, v in summary.items():
        ordered[k] = v
        if k == "n":
            ordered.update(hit_metrics)
    (out / f"{name}.json").write_text(json.dumps(ordered, indent=2, ensure_ascii=False), encoding="utf-8")
    print(name, hit_metrics)


def rate(rows: list[dict], key: str) -> float | None:
    values = [r[key] for r in rows if r.get(key) is not None]
    return round(sum(values) / len(values), 3) if values else None


def summarize(rows: list[dict], args) -> dict:
    return {
        "corrida": args.name,
        "config": {"chunking": args.strategy, "prompt": args.prompt,
                   "router": None if args.baseline else args.router, "juez": args.judge_model or "mismo LLM"},
        "n": len(rows),
        "hit@k_retriever": rate(rows, "hit_retriever"),
        "hit@k_con_umbral": rate(rows, "hit_con_umbral"),
        "hit@k_articulo_exacto": rate(rows, "hit_articulo_exacto"),
        "ruteo_correcto": rate(rows, "ruta_correcta"),
        "herramienta_correcta": rate(rows, "herramienta_correcta"),
        "rechazo_correcto": rate(rows, "rechazo_correcto"),
        "acierto_respuesta": rate(rows, "correcta"),
        "fidelidad": rate(rows, "fiel"),
        "latencia_mediana_s": statistics.median(r["latencia_s"] for r in rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="final")
    parser.add_argument("--strategy", default="articulo", choices=["articulo", "fijo"])
    parser.add_argument("--prompt", default="v3", choices=list(prompts.RAG_PROMPTS), help="versión del prompt RAG")
    parser.add_argument("--router", default="v2", choices=list(prompts.ROUTER_PROMPTS), help="versión del prompt del router")
    parser.add_argument("--baseline", action="store_true", help="sin router ni herramientas: todo va al RAG")
    parser.add_argument("--no-judge", dest="judge", action="store_false", help="no usar LLM como juez")
    parser.add_argument("--judge-model", default=None, help="modelo de Ollama para el juez (por defecto, el mismo que responde)")
    parser.add_argument("--recompute-retrieval", action="store_true",
                        help="solo recalcula hit@k de la corrida --name ya guardada, sin llamar al LLM")
    args = parser.parse_args()
    if args.recompute_retrieval:
        recompute_retrieval(args.name)
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
