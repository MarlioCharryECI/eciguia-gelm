"""Evalúa EciGuía contra el set de 40 preguntas con respuesta conocida.

Ejemplos:
    uv run python eval/run_eval.py --name base --baseline --prompt basico      # experimento 1
    uv run python eval/run_eval.py --name fijo --strategy fijo                 # experimento 2a
    uv run python eval/run_eval.py --name articulo --strategy articulo         # experimento 2b
    uv run python eval/run_eval.py --name final                                # sistema completo

Cada corrida guarda eval/results/<name>.csv (detalle) y eval/results/<name>.json (resumen).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
from pathlib import Path

from eciguia import prompts
from eciguia.graph import EciGuiaAgent, _parse_json, _text
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


def retrieval_hit(retriever: Retriever, item: dict) -> bool:
    """¿Aparece el fragmento correcto (documento y artículo) entre los recuperados?"""
    for hit in retriever.search(item["pregunta"]):
        meta = hit.doc.metadata
        if meta["source"] == item["fuente"] and meta["section"].startswith(item.get("seccion", "")):
            return True
    return False


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
    rag_prompt = prompts.RAG_ANSWER_BASICO if args.prompt == "basico" else prompts.RAG_ANSWER
    agent = EciGuiaAgent(retriever=retriever, rag_prompt=rag_prompt, use_router=not args.baseline)
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
        }
        if item["tipo"] == "documentos":
            row["hit_retriever"] = retrieval_hit(retriever, item)
        if item["tipo"] == "herramienta":
            row["herramienta_correcta"] = state.get("tool_name") == item["herramienta"]
        if item["tipo"] in ("fuera_de_alcance", "trampa"):
            row["rechazo_correcto"] = any(m in state["answer"] for m in REJECTION_MARKERS)
        if args.judge and item["tipo"] in ("documentos", "herramienta"):
            verdict = await judge(agent.json_llm, item, state)
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


def rate(rows: list[dict], key: str) -> float | None:
    values = [r[key] for r in rows if r.get(key) is not None]
    return round(sum(values) / len(values), 3) if values else None


def summarize(rows: list[dict], args) -> dict:
    return {
        "corrida": args.name,
        "config": {"chunking": args.strategy, "prompt": args.prompt, "router": not args.baseline},
        "n": len(rows),
        "hit@k_retriever": rate(rows, "hit_retriever"),
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
    parser.add_argument("--prompt", default="reglas", choices=["reglas", "basico"])
    parser.add_argument("--baseline", action="store_true", help="sin router ni herramientas: todo va al RAG")
    parser.add_argument("--no-judge", dest="judge", action="store_false", help="no usar LLM como juez")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
