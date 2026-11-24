"""Reporte de regresión: compara dos corridas pregunta por pregunta.

Sirve para comprobar que ampliar el corpus no empeoró lo que ya funcionaba.

    uv run python eval/regresion.py 6_final 7_ampliacion_original

Lee eval/results/<corrida>.csv y escribe docs/resultados/regresion_<antes>_vs_<despues>.csv.
Una pregunta "empeora" si antes estaba bien y ahora no en alguno de estos criterios: ruta, herramienta,
rechazo o acierto según el juez. Como el juez es permisivo y a veces se equivoca, las que cambian se
imprimen con las dos respuestas para revisarlas a mano.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from eciguia import config

RESULTS = Path(__file__).parent / "results"
CRITERIOS = ("ruta_correcta", "herramienta_correcta", "rechazo_correcto", "correcta")


def load(name: str) -> dict[str, dict]:
    with open(RESULTS / f"{name}.csv", encoding="utf-8") as file:
        return {row["id"]: row for row in csv.DictReader(file)}


def ok(row: dict, criterio: str) -> bool | None:
    value = row.get(criterio, "")
    return None if value in ("", None) else value == "True"


def compare(antes: dict, despues: dict) -> list[dict]:
    filas = []
    for qid, a in antes.items():
        d = despues.get(qid)
        if d is None:
            continue
        cambios = []
        for criterio in CRITERIOS:
            va, vd = ok(a, criterio), ok(d, criterio)
            if va is True and vd is False:
                cambios.append(f"empeora:{criterio}")
            elif va is False and vd is True:
                cambios.append(f"mejora:{criterio}")
        filas.append({"id": qid, "tipo": a["tipo"], "pregunta": a["pregunta"], "cambios": " ".join(cambios),
                      "ruta_antes": a["ruta"], "ruta_despues": d["ruta"],
                      "respuesta_antes": a["respuesta"], "respuesta_despues": d["respuesta"]})
    return filas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("antes")
    parser.add_argument("despues")
    args = parser.parse_args()

    filas = compare(load(args.antes), load(args.despues))
    empeoran = [f for f in filas if "empeora" in f["cambios"]]
    mejoran = [f for f in filas if "mejora" in f["cambios"] and "empeora" not in f["cambios"]]
    print(f"{len(filas)} preguntas comparadas: {len(empeoran)} empeoran, {len(mejoran)} mejoran, "
          f"{len(filas) - len(empeoran) - len(mejoran)} sin cambios en los criterios")
    for titulo, grupo in (("EMPEORAN", empeoran), ("MEJORAN", mejoran)):
        print(f"\n===== {titulo}")
        for f in grupo:
            print(f"\n{f['id']} [{f['tipo']}] {f['pregunta']}\n  {f['cambios']}  (ruta {f['ruta_antes']} -> {f['ruta_despues']})")
            print(f"  ANTES:   {f['respuesta_antes'][:300]!r}")
            print(f"  DESPUÉS: {f['respuesta_despues'][:300]!r}")

    out = config.ROOT / "docs" / "resultados" / f"regresion_{args.antes}_vs_{args.despues}.csv"
    with open(out, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(filas[0]))
        writer.writeheader()
        writer.writerows(filas)
    print(f"\nDetalle en {out}")


if __name__ == "__main__":
    main()
