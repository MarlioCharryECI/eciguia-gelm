"""Calibra el umbral de relevancia del retriever (MAX_DISTANCE) con datos.

Para cada pregunta mide la distancia coseno del mejor fragmento recuperado y compara dos grupos:
- positivas: las 25 preguntas de tipo "documentos" del set de evaluación (la respuesta sí está).
- negativas: las 7 "fuera_de_alcance" y "trampa" del set, más 20 de eval/calibracion_negativas.jsonl
  (preguntas que suenan a la Escuela pero cuya respuesta no está en los 6 documentos).

Criterio: el umbral más estricto que deja pasar TODAS las positivas, más un margen de 0,02 para
preguntas redactadas distinto. Los errores no cuestan lo mismo: una positiva bloqueada termina en
"no encontré" sin segunda oportunidad, mientras que una negativa que se cuela todavía pasa por el
prompt RAG, que tiene la regla de responder "No encontré..." si ningún fragmento sirve.

Guarda la gráfica en docs/resultados/calibracion.png y los datos (con la curva completa) en
docs/resultados/calibracion.json.

    uv run python eval/calibrate.py [--strategy articulo|fijo]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from eciguia import config
from eciguia.retriever import Retriever

EVAL_DIR = Path(__file__).parent
OUT_DIR = config.ROOT / "docs" / "resultados"
MIN_RECALL = 1.0
MARGIN = 0.02
BLUE, ORANGE = "#2a78d6", "#eb6834"  # slots 1 y 2 de la paleta categórica validada
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def best_distance(retriever: Retriever, question: str) -> float:
    return retriever.store.similarity_search_with_score(question, k=1)[0][1]


def choose_threshold(positives: list[float], negatives: list[float]) -> dict:
    """El umbral más estricto que conserva MIN_RECALL de las positivas, más MARGIN, redondeado hacia arriba."""
    ordered = sorted(positives)
    needed = math.ceil(MIN_RECALL * len(ordered))
    threshold = math.ceil((ordered[needed - 1] + MARGIN) * 100) / 100
    curve = [
        {"umbral": t / 100,
         "positivas_que_pasan": round(sum(d <= t / 100 for d in positives) / len(positives), 3),
         "negativas_bloqueadas": round(sum(d > t / 100 for d in negatives) / len(negatives), 3)}
        for t in range(30, 71, 1)
    ]
    return {
        "curva": curve,
        "umbral": threshold,
        "positivas_que_pasan": sum(d <= threshold for d in positives) / len(positives),
        "negativas_bloqueadas": sum(d > threshold for d in negatives) / len(negatives),
        "umbral_anterior": config.MAX_DISTANCE,
        "negativas_bloqueadas_umbral_anterior": sum(d > config.MAX_DISTANCE for d in negatives) / len(negatives),
    }


def plot(rows: list[dict], result: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [("Respuesta en los documentos", "positiva", BLUE), ("Respuesta fuera de los documentos", "negativa", ORANGE)]
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for y, (label, group, color) in enumerate(groups):
        values = [r["distancia"] for r in rows if r["grupo"] == group]
        # pequeño desplazamiento vertical determinista para que los puntos no se tapen
        jitter = [((i * 37) % 11 - 5) * 0.025 for i in range(len(values))]
        ax.scatter(values, [1 - y + j for j in jitter], s=46, color=color, edgecolors="#fcfcfb", linewidths=1.5,
                   zorder=3, label=f"{label} (n={len(values)})")
    ax.axvline(result["umbral"], color=INK, linewidth=2, zorder=2)
    ax.text(result["umbral"] + 0.004, 1.42, f"umbral elegido {result['umbral']:.2f}", color=INK, fontsize=9, va="center")
    ax.axvline(result["umbral_anterior"], color=MUTED, linewidth=1.5, linestyle=(0, (4, 3)), zorder=2)
    ax.text(result["umbral_anterior"] - 0.004, 1.42, f"umbral sin calibrar {result['umbral_anterior']:.2f}",
            color=MUTED, fontsize=9, va="center", ha="right")
    for r in rows:  # rótulos selectivos: solo las negativas que se cuelan por debajo del umbral
        if r["grupo"] == "negativa" and r["distancia"] <= result["umbral"]:
            ax.annotate(r["id"], (r["distancia"], 0), xytext=(0, -16), textcoords="offset points",
                        fontsize=8, color=MUTED, ha="center")
    ax.set_yticks([1, 0], ["Positivas", "Negativas"], color=INK)
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel("Distancia coseno al fragmento más cercano (menor = más parecido)", color=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(colors=MUTED, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"Calibración del umbral: pasa el {result['positivas_que_pasan']:.0%} de las positivas y se "
                 f"bloquea el {result['negativas_bloqueadas']:.0%} de las negativas", color=INK, fontsize=10.5, loc="left")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=2, frameon=False, fontsize=8.5)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=fig.get_facecolor())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strategy", default="articulo", choices=["articulo", "fijo"])
    args = parser.parse_args()

    retriever = Retriever(strategy=args.strategy)
    golden = load_jsonl(EVAL_DIR / "golden_set.jsonl")
    negatives = load_jsonl(EVAL_DIR / "calibracion_negativas.jsonl")
    rows = []
    for item in golden:
        group = "positiva" if item["tipo"] == "documentos" else "negativa" if item["tipo"] in ("fuera_de_alcance", "trampa") else None
        if group:
            rows.append({"id": item["id"], "grupo": group, "pregunta": item["pregunta"]})
    rows += [{"id": n["id"], "grupo": "negativa", "pregunta": n["pregunta"]} for n in negatives]
    for row in rows:
        row["distancia"] = round(best_distance(retriever, row["pregunta"]), 4)

    for group in ("positiva", "negativa"):
        print(f"\n{group.upper()}S")
        for r in sorted((r for r in rows if r["grupo"] == group), key=lambda r: r["distancia"]):
            print(f"  {r['distancia']:.3f}  {r['id']:<4} {r['pregunta']}")

    result = choose_threshold([r["distancia"] for r in rows if r["grupo"] == "positiva"],
                              [r["distancia"] for r in rows if r["grupo"] == "negativa"])
    print("\n" + json.dumps({k: v for k, v in result.items() if k != "curva"}, indent=2, ensure_ascii=False))

    suffix = "" if args.strategy == "articulo" else f"_{args.strategy}"
    plot(rows, result, OUT_DIR / f"calibracion{suffix}.png")
    (OUT_DIR / f"calibracion{suffix}.json").write_text(
        json.dumps({"estrategia": args.strategy, **result, "preguntas": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Gráfica y datos en {OUT_DIR}")


if __name__ == "__main__":
    main()
