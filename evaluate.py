"""Calcola le metriche di valutazione di uno o piu' run rispetto ai giudizi di rilevanza.

    python evaluate.py --qrels queries/qrels_content.txt --runs runs/a.txt runs/b.txt --k 10

Metriche (media sulle query giudicate):
  P@k          frazione dei primi k risultati che e' rilevante
  R@k          frazione dei documenti rilevanti presenti nei primi k
  F1@k         media armonica di P@k e R@k
  MRR          media di 1/posizione del primo risultato rilevante (0 se assente)
  Giudicati@k  frazione dei primi k risultati che ha un giudizio (rilevante o no):
               se e' bassa, il run restituisce molti documenti fuori dal pool e P@k
               e' sottostimata

Le query senza documenti rilevanti sono escluse dalla media; una query senza risultati
nel run conta 0. I documenti senza giudizio sono considerati non rilevanti.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_qrels(path):
    """-> (rilevanti per query, giudicati per query)"""
    relevant, judged = defaultdict(set), defaultdict(set)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            qid, _, doc, grade = line.split()
            judged[qid].add(doc)
            if int(grade) > 0:
                relevant[qid].add(doc)
    return relevant, judged


def load_run(path):
    ranking = defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            qid, _, doc, rank, _score, _name = line.split()
            ranking[qid].append((int(rank), doc))
    return {qid: [doc for _, doc in sorted(items)] for qid, items in ranking.items()}


def query_metrics(ranked, relevant, judged, k):
    top = ranked[:k]
    found = sum(doc in relevant for doc in top)
    p, r = found / k, found / len(relevant)
    first = next((i for i, doc in enumerate(ranked, 1) if doc in relevant), None)
    return {
        "P@k": p,
        "R@k": r,
        "F1@k": 2 * p * r / (p + r) if found else 0.0,
        "MRR": 1 / first if first else 0.0,
        "Giudicati@k": sum(doc in judged for doc in top) / k,
    }


def evaluate(qrels_path, run_paths, k, per_query_csv=None):
    relevant, judged = load_qrels(qrels_path)
    qids = [q for q in relevant if relevant[q]]
    lines = [f"{len(qids)} query con almeno un documento rilevante, k = {k}", "",
             f"| Run | P@{k} | R@{k} | F1@{k} | MRR | Giudicati@{k} |",
             "| --- | --- | --- | --- | --- | --- |"]
    rows = []
    for path in run_paths:
        run = load_run(path)
        per_query = {q: query_metrics(run.get(q, []), relevant[q], judged[q], k) for q in qids}
        means = {m: sum(v[m] for v in per_query.values()) / len(qids) for m in next(iter(per_query.values()))}
        lines.append(f"| {Path(path).stem} | " + " | ".join(f"{v:.3f}" for v in means.values()) + " |")
        rows += [{"run": Path(path).stem, "qid": q, "rilevanti": len(relevant[q]),
                  **{m: f"{v:.3f}" for m, v in metrics.items()}} for q, metrics in per_query.items()]
    report = "\n".join(lines)
    print(report)
    if per_query_csv and rows:
        Path(per_query_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(per_query_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--qrels", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--per-query", help="CSV con le metriche di ogni query")
    a = ap.parse_args()
    evaluate(a.qrels, a.runs, a.k, a.per_query)


if __name__ == "__main__":
    main()
