"""Compara versiones del prompt del router en un set de ruteo que NO se usó para escribirlas.

ROUTER_V2 se escribió mirando los fallos de V1 en golden_set.jsonl. Para comprobar que la mejora generaliza
y no es sobreajuste, se mide en eval/ruteo_holdout.jsonl: 20 preguntas nuevas, etiquetadas solo con la ruta.

    uv run python eval/compare_router.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from eciguia import config, prompts
from eciguia.graph import _parse_json, _text, default_llm

EVAL_DIR = Path(__file__).parent


async def route(llm, prompt: str, question: str) -> str:
    try:
        return _parse_json(_text(await llm.ainvoke(prompt.format(question=question)))).get("ruta", "documentos")
    except Exception:
        return "documentos"  # mismo fallback que el agente


async def main() -> None:
    llm = default_llm(json_mode=True)
    with open(EVAL_DIR / "ruteo_holdout.jsonl", encoding="utf-8") as file:
        items = [json.loads(line) for line in file if line.strip()]
    rows = []
    for item in items:
        row = {"id": item["id"], "esperada": item["ruta"], "pregunta": item["pregunta"]}
        for version, prompt in prompts.ROUTER_PROMPTS.items():
            row[version] = await route(llm, prompt, item["pregunta"])
        rows.append(row)
        print(f"{row['id']}  esperada={row['esperada']:<16} " + "  ".join(f"{v}={row[v]:<16}" for v in prompts.ROUTER_PROMPTS))
    summary = {v: round(sum(r[v] == r["esperada"] for r in rows) / len(rows), 3) for v in prompts.ROUTER_PROMPTS}
    print(json.dumps(summary, indent=2))
    out = config.ROOT / "docs" / "resultados" / "ruteo_holdout.json"
    out.write_text(json.dumps({"exactitud": summary, "preguntas": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
