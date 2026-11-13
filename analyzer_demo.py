"""Stampa, in forma di tabella Markdown, i token prodotti dagli analyzer su alcuni
nomi di file e frasi di esempio.

    python analyzer_demo.py
    python analyzer_demo.py --nomi "Nome_di_un_file" ... --frasi "Una frase." ...
    python analyzer_demo.py > results/analyzer_tables.md
"""

import argparse

from hw3.analyzers import (CONTENT_ANALYZERS, NAME_MODES, analyze, content_analyzer,
                           name_index_analyzer, name_query_analyzer)
from org.apache.lucene.analysis.standard import StandardAnalyzer

DEFAULT_NAMES = ["Basilica_di_San_Pietro_in_Vaticano", "L'Aquila_(città)", "Juventus_Football_Club"]
DEFAULT_SENTENCES = [
    "Dell'antica città romana restano le mura e il teatro.",
    "I calciatori della squadra vinsero due campionati nazionali.",
    "La Seconda guerra mondiale terminò nel 1945.",
]


def tokens(analyzer, field, text):
    return " · ".join(t for t, _ in analyze(analyzer, field, text))


def table(title, field, texts, analyzers):
    print(f"\n### {title}\n")
    print("| Input | Analyzer | Token |")
    print("| --- | --- | --- |")
    for text in texts:
        for label, analyzer in analyzers:
            print(f"| {text} | {label} | {tokens(analyzer, field, text)} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nomi", nargs="*", default=DEFAULT_NAMES)
    ap.add_argument("--frasi", nargs="*", default=DEFAULT_SENTENCES)
    a = ap.parse_args()

    name_analyzers = [("standard (riferimento)", StandardAnalyzer())]
    name_analyzers += [(f"nome, indice ({m})", name_index_analyzer(m)) for m in NAME_MODES]
    name_analyzers += [("nome, query", name_query_analyzer())]
    table("Campo nome", "name", a.nomi, name_analyzers)
    table("Campo contenuto", "content", a.frasi, [(c, content_analyzer(c)) for c in CONTENT_ANALYZERS])


if __name__ == "__main__":
    main()
