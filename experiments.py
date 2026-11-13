"""Esegue gli esperimenti, una fase alla volta.

    python experiments.py indici   costruisce gli indici da confrontare
    python experiments.py run      esegue le query in batch su tutte le configurazioni
    python experiments.py pool     prepara judgments/pool.csv da giudicare a mano
    python experiments.py valuta   calcola le metriche (dopo "python judgments.py qrels")
    python experiments.py tempi    misura i tempi di indicizzazione e disegna il grafico

Configurazioni:
  indici    italian (contenuto ItalianAnalyzer, nome con n-gram), leggero, whitespace,
            prefix (come italian ma nome senza n-gram, ricerca con PrefixQuery)
  contenuto analyzer: whitespace / italian / leggero (BM25, OR)
            similarity su italian: bm25 / classic / lmdirichlet / constant (nessun ranking)
            operatore su italian+bm25: AND
  nome      n-gram contro PrefixQuery, OR e AND
  tempi     scalabilita' su campioni crescenti; contenuto memorizzato si/no
"""

import sys
from pathlib import Path

import indexer
import searcher
from evaluate import evaluate
from hw3.search import Engine

DOCS = "data/wiki_it/docs"
INDEXES = {
    "italian": ("italian", "ngram"),
    "leggero": ("leggero", "ngram"),
    "whitespace": ("whitespace", "ngram"),
    "prefix": ("italian", "prefix"),
}
CONTENT_RUNS = [  # (nome run, indice, similarity, operatore)
    ("content_whitespace_bm25", "whitespace", "bm25", "OR"),
    ("content_leggero_bm25", "leggero", "bm25", "OR"),
    ("content_italian_bm25", "italian", "bm25", "OR"),
    ("content_italian_classic", "italian", "classic", "OR"),
    ("content_italian_lmdirichlet", "italian", "lmdirichlet", "OR"),
    ("content_italian_constant", "italian", "constant", "OR"),
    ("content_italian_bm25_and", "italian", "bm25", "AND"),
]
NAME_RUNS = [
    ("name_ngram_or", "italian", "bm25", "OR"),
    ("name_ngram_and", "italian", "bm25", "AND"),
    ("name_prefix_or", "prefix", "bm25", "OR"),
    ("name_prefix_and", "prefix", "bm25", "AND"),
]
POOL_RUNS = ["content_italian_bm25", "content_italian_classic",
             "content_italian_lmdirichlet", "content_leggero_bm25"]
SCALABILITY = [1000, 5000, 10000, 25000, 50000]


def phase_indici():
    for name, (content, mode) in INDEXES.items():
        print(f"\n== indice {name}")
        indexer.run(DOCS, f"index/{name}", content, mode, store_content=False,
                    runs=1, timing_csv="results/timing_indici.csv")


def _batch(runs, queries):
    for run_name, index, sim, op in runs:
        engine = Engine(f"index/{index}", sim, op)
        try:
            searcher.batch(engine, queries, f"runs/{run_name}.txt", 100, run_name)
        finally:
            engine.close()


def phase_run():
    _batch(CONTENT_RUNS, "queries/content.tsv")
    _batch(NAME_RUNS, "queries/name.tsv")


def phase_pool():
    import subprocess
    subprocess.run([sys.executable, "judgments.py", "pool", "--depth", "10",
                    "--runs", *[f"runs/{r}.txt" for r in POOL_RUNS]], check=True)


def phase_valuta():
    Path("results").mkdir(exist_ok=True)
    report = evaluate("queries/qrels_content.txt", [f"runs/{r[0]}.txt" for r in CONTENT_RUNS], 10,
                      "results/per_query_content.csv")
    Path("results/metrics_content.md").write_text(report + "\n", encoding="utf-8")
    print()
    report = evaluate("queries/qrels_name.txt", [f"runs/{r[0]}.txt" for r in NAME_RUNS], 5,
                      "results/per_query_name.csv")
    Path("results/metrics_name.md").write_text(report + "\n", encoding="utf-8")


def phase_tempi():
    for n in SCALABILITY:
        print(f"\n== scalabilita': {n} file")
        indexer.run(DOCS, "index/tempi", "italian", "ngram", store_content=False,
                    limit=n, runs=4, timing_csv="results/timing_scalabilita.csv")
    for store in (False, True):
        print(f"\n== contenuto memorizzato: {'si' if store else 'no'}")
        indexer.run(DOCS, "index/tempi", "italian", "ngram", store_content=store,
                    runs=4, timing_csv="results/timing_store.csv")
    plot_scalability("results/timing_scalabilita.csv", "results/scalabilita.png")


def plot_scalability(csv_path, png_path):
    import csv
    import statistics
    from collections import defaultdict
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_n = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["giro"]) > 1:                     # escluso il giro di riscaldamento
                by_n[int(row["n_file"])].append(float(row["totale_ms"]) / 1000)
    xs = sorted(by_n)
    means = [statistics.mean(by_n[x]) for x in xs]
    sds = [statistics.stdev(by_n[x]) if len(by_n[x]) > 1 else 0 for x in xs]
    for x, m, s in zip(xs, means, sds):
        print(f"{x} file: {m:.2f} s +- {s:.2f}")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(xs, means, yerr=sds, marker="o", capsize=4)
    ax.set_xlabel("numero di file")
    ax.set_ylabel("tempo di indicizzazione (s)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    print(f"Grafico salvato in {png_path}")


PHASES = {"indici": phase_indici, "run": phase_run, "pool": phase_pool,
          "valuta": phase_valuta, "tempi": phase_tempi}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PHASES:
        print(__doc__)
        sys.exit(1)
    PHASES[sys.argv[1]]()
