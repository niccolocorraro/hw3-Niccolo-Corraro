"""Ricerca da console su un indice creato da indexer.py.

Sintassi:
    nome <termini>          cerca nel nome del file
    contenuto <termini>     cerca nel testo
    "parole tra virgolette" formano una frase (phrase query)
    exit                    esce

Uso interattivo:
    python searcher.py --index index/italian [--k 10] [--op OR] [--similarity bm25]

Uso batch (per la valutazione): esegue un file di query "id<TAB>nome|contenuto<TAB>testo"
e scrive i risultati nel formato run di TREC (qid Q0 file rank score nome_run):
    python searcher.py --index index/italian --batch queries/content.tsv --run runs/italian_bm25.txt
"""

import argparse
import time
from pathlib import Path

from hw3.search import Engine, QuerySyntaxError, SIMILARITIES


def interactive(engine, k):
    print("Query: nome <termini> | contenuto <termini> | \"...\" = frase | exit per uscire")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip().lower() == "exit":
            break
        if not line.strip():
            continue
        try:
            query = engine.build(line)
        except QuerySyntaxError as e:
            print(f"Errore: {e}")
            continue
        if query is None:
            print("Dopo l'analisi non resta nessun termine da cercare (solo stopword?).")
            continue
        t0 = time.perf_counter()
        total, hits = engine.search(query, k)
        ms = (time.perf_counter() - t0) * 1000
        print(f"Query Lucene: {query.toString()}")
        print(f"{total} documenti corrispondono ({ms:.1f} ms)")
        for rank, (filename, score) in enumerate(hits, 1):
            print(f"{rank:3d}. {score:7.3f}  {filename}")
        if total == 0:
            print("Nessun risultato.")


def batch(engine, queries_file, run_file, depth, run_name):
    run_file = Path(run_file)
    run_file.parent.mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    with open(queries_file, encoding="utf-8") as fin, open(run_file, "w", encoding="utf-8", newline="\n") as fout:
        for line in fin:
            line = line.rstrip("\r\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                print(f"Riga ignorata (servono 3 colonne separate da tabulazione): {line!r}")
                skipped += 1
                continue
            qid, keyword, text = parts
            try:
                query = engine.build(f"{keyword} {text}")
            except QuerySyntaxError as e:
                print(f"Query {qid} ignorata: {e}")
                skipped += 1
                continue
            if query is not None:
                _, hits = engine.search(query, depth)
                for rank, (filename, score) in enumerate(hits, 1):
                    fout.write(f"{qid} Q0 {filename} {rank} {score:.4f} {run_name}\n")
            done += 1
    print(f"Eseguite {done} query ({skipped} ignorate) -> {run_file}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default="index/italian")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--op", default="OR", choices=["OR", "AND"])
    ap.add_argument("--similarity", default="bm25", choices=SIMILARITIES)
    ap.add_argument("--batch", help="file di query da eseguire")
    ap.add_argument("--run", help="file in cui scrivere i risultati (con --batch)")
    ap.add_argument("--depth", type=int, default=100)
    ap.add_argument("--run-name", default="run")
    a = ap.parse_args()

    engine = Engine(a.index, a.similarity, a.op)
    m = engine.meta
    print(f"Indice {a.index}: {m['indexed']} documenti, contenuto = {m['content_analyzer']}, "
          f"nome = {m['name_mode']}, similarity = {a.similarity}, operatore = {a.op}, "
          f"Lucene {m['lucene_version']}")
    try:
        if a.batch:
            if not a.run:
                ap.error("con --batch serve anche --run")
            batch(engine, a.batch, a.run, a.depth, a.run_name)
        else:
            interactive(engine, a.k)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
