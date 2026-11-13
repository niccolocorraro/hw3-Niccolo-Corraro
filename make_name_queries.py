"""Genera le query sul nome per la ricerca di un elemento noto (known-item search).

Per ogni file estratto a caso si prendono due parole del nome (di almeno 5 lettere)
e se ne tiene solo l'inizio (--prefix lettere), come farebbe chi ricorda il titolo
solo in parte: "Basilica_di_San_Pietro_in_Vaticano" -> "basi piet".
Il file da cui la query e' stata generata e' l'unico considerato rilevante.

    python make_name_queries.py --docs data/wiki_it/docs [--n 20] [--prefix 4]

Output: queries/name.tsv e queries/qrels_name.txt
"""

import argparse
import random
import re
from pathlib import Path

WORD = re.compile(r"[^\W\d_]{5,}")   # parole di sole lettere, lunghe almeno 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="data/wiki_it/docs")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--prefix", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out-dir", default="queries")
    a = ap.parse_args()

    files = sorted(p.name for p in Path(a.docs).glob("*.txt"))
    rng = random.Random(a.seed)
    rng.shuffle(files)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out / "name.tsv", "w", encoding="utf-8", newline="\n") as fq, \
         open(out / "qrels_name.txt", "w", encoding="utf-8", newline="\n") as fr:
        for filename in files:
            words = WORD.findall(Path(filename).stem)
            if len(words) < 2:
                continue
            chosen = rng.sample(words, 2)
            query = " ".join(w[:a.prefix].lower() for w in chosen)
            written += 1
            qid = f"N{written:02d}"
            fq.write(f"{qid}\tnome\t{query}\n")
            fr.write(f"{qid} 0 {filename} 1\n")
            if written == a.n:
                break
    print(f"{written} query sul nome scritte in {out / 'name.tsv'}")


if __name__ == "__main__":
    main()
