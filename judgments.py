"""Costruzione della ground truth per le query sul contenuto, con il metodo del pooling.

1) pool: unisce i primi --depth risultati di piu' run (configurazioni diverse) per ogni
   query e scrive un file CSV da compilare a mano, con un'anteprima di ogni documento:
       python judgments.py pool --runs runs/content_italian_bm25.txt runs/... --depth 10

   Il file judgments/pool.csv si apre con Excel (separatore ";"). Nella colonna
   "rilevante" si scrive 1 (rilevante) o 0 (non rilevante). Rieseguendo "pool"
   i giudizi gia' inseriti vengono conservati.

2) qrels: converte il CSV compilato nel formato TREC usato da evaluate.py:
       python judgments.py qrels

I documenti fuori dal pool non vengono giudicati e sono considerati non rilevanti:
la recall calcolata e' quindi relativa ai documenti rilevanti trovati nel pool.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

COLUMNS = ["qid", "query", "file", "anteprima", "rilevante"]
YES = {"1", "si", "sì", "s", "x", "y", "yes"}
NO = {"0", "no", "n"}


def read_queries(path):
    queries = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and not line.startswith("#"):
            queries[parts[0]] = parts[2]
    return queries


def read_run(path, depth):
    top = defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            qid, _, filename, rank, _score, _name = line.split()
            if int(rank) <= depth:
                top[qid].append(filename)
    return top


def read_pool(path):
    """Legge il CSV compilato, accettando sia ";" sia "," come separatore (dipende da Excel)."""
    path = Path(path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    delimiter = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delimiter))


def preview(docs_dir, filename, chars):
    try:
        text = (Path(docs_dir) / filename).read_text(encoding="utf-8")
    except OSError:
        return "(file non trovato)"
    return " ".join(text.split())[:chars]


def cmd_pool(a):
    queries = read_queries(a.queries)
    pooled = defaultdict(set)
    for run in a.runs:
        for qid, files in read_run(run, a.depth).items():
            pooled[qid].update(files)

    previous = {(r["qid"], r["file"]): r.get("rilevante", "") for r in read_pool(a.out)}
    rows = []
    for qid in queries:                       # stesso ordine del file di query
        for filename in sorted(pooled.get(qid, ())):
            rows.append({"qid": qid, "query": queries[qid], "file": filename,
                         "anteprima": preview(a.docs, filename, a.chars),
                         "rilevante": previous.get((qid, filename), "")})

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:   # BOM: Excel riconosce gli accenti
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    todo = sum(1 for r in rows if not r["rilevante"].strip())
    print(f"{len(rows)} coppie query-documento in {a.out} ({todo} da giudicare)")
    for qid in queries:
        print(f"  {qid}: {len(pooled.get(qid, ()))} documenti nel pool")


def cmd_qrels(a):
    rows = read_pool(a.pool)
    missing, bad, relevant = [], [], defaultdict(int)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            value = (r.get("rilevante") or "").strip().lower()
            if not value:
                missing.append((r["qid"], r["file"]))
                continue
            if value not in YES | NO:
                bad.append((r["qid"], r["file"], value))
                continue
            grade = 1 if value in YES else 0
            relevant[r["qid"]] += grade
            f.write(f"{r['qid']} 0 {r['file']} {grade}\n")
    print(f"Giudizi scritti in {a.out}")
    for qid in sorted(relevant):
        print(f"  {qid}: {relevant[qid]} documenti rilevanti")
    if missing:
        print(f"ATTENZIONE: {len(missing)} righe senza giudizio (es. {missing[0]})")
    if bad:
        print(f"ATTENZIONE: {len(bad)} valori non riconosciuti (es. {bad[0]}): usare 1 o 0")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pool")
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--queries", default="queries/content.tsv")
    p.add_argument("--docs", default="data/wiki_it/docs")
    p.add_argument("--chars", type=int, default=300)
    p.add_argument("--out", default="judgments/pool.csv")
    q = sub.add_parser("qrels")
    q.add_argument("--pool", default="judgments/pool.csv")
    q.add_argument("--out", default="queries/qrels_content.txt")
    a = ap.parse_args()
    cmd_pool(a) if a.cmd == "pool" else cmd_qrels(a)


if __name__ == "__main__":
    main()
