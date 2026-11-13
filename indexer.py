"""Indicizza i file .txt di una directory in un unico indice Lucene con due campi:
"name" (nome del file senza estensione) e "content" (testo del file).
Un PerFieldAnalyzerWrapper applica a ciascun campo il proprio analyzer.

Uso:
    python indexer.py --docs data/wiki_it/docs --index index/italian
                      [--content-analyzer italian] [--name-mode ngram]
                      [--store-content no] [--limit 0] [--runs 1]
                      [--timing-csv results/timing.csv]

--limit N   indicizza N file estratti a caso (seme fisso)
--runs R    ripete l'indicizzazione R volte; con R > 1 il primo giro (riscaldamento
            della JVM) e' escluso da media e deviazione standard
"""

import argparse
import csv
import json
import random
import statistics
import time
from datetime import datetime
from pathlib import Path

from hw3 import jvm
from hw3.analyzers import CONTENT_ANALYZERS, NAME_MODES, index_analyzer

from java.nio.file import Paths
from org.apache.lucene.document import Document, Field, StringField, TextField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import FSDirectory

TIMING_FIELDS = ["data_ora", "giro", "n_file", "indicizzati", "scartati", "analyzer_contenuto",
                 "modo_nome", "store_contenuto", "lettura_ms", "inserimento_ms", "commit_ms",
                 "totale_ms", "indice_mb"]


def select_files(docs_dir, limit=0, seed=42):
    files = sorted(p for p in Path(docs_dir).iterdir() if p.suffix == ".txt" and p.is_file())
    if 0 < limit < len(files):
        files = sorted(random.Random(seed).sample(files, limit))
    return files


def folder_mb(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) / 1e6


def index_once(files, index_dir, content_analyzer, name_mode, store_content, ram_mb=16.0):
    """Costruisce l'indice da zero e restituisce i tempi delle fasi (in nanosecondi)."""
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    config = IndexWriterConfig(index_analyzer(content_analyzer, name_mode))
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    config.setRAMBufferSizeMB(ram_mb)
    store = Field.Store.YES if store_content else Field.Store.NO

    read_ns = add_ns = 0
    indexed = skipped = 0
    start = time.perf_counter_ns()
    writer = IndexWriter(FSDirectory.open(Paths.get(str(index_dir))), config)
    try:
        for path in files:
            t0 = time.perf_counter_ns()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped += 1
                continue
            t1 = time.perf_counter_ns()
            read_ns += t1 - t0
            if not text.strip():
                skipped += 1
                continue

            doc = Document()
            doc.add(StringField("filename", path.name, Field.Store.YES))
            doc.add(TextField("name", path.stem, Field.Store.YES))
            doc.add(TextField("content", text, store))
            writer.addDocument(doc)
            add_ns += time.perf_counter_ns() - t1
            indexed += 1

        c0 = time.perf_counter_ns()
        writer.commit()
        commit_ns = time.perf_counter_ns() - c0
    finally:
        writer.close()
    total_ns = time.perf_counter_ns() - start   # include la chiusura del writer

    (index_dir / "meta.json").write_text(json.dumps({
        "content_analyzer": content_analyzer,
        "name_mode": name_mode,
        "store_content": store_content,
        "indexed": indexed,
        "lucene_version": jvm.LUCENE_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")

    return {"indicizzati": indexed, "scartati": skipped, "lettura_ms": read_ns / 1e6,
            "inserimento_ms": add_ns / 1e6, "commit_ms": commit_ns / 1e6,
            "totale_ms": total_ns / 1e6, "indice_mb": folder_mb(index_dir)}


def run(docs, index, content_analyzer="italian", name_mode="ngram", store_content=False,
        limit=0, runs=1, ram_mb=16.0, timing_csv="results/timing.csv"):
    files = select_files(docs, limit)
    print(f"File .txt selezionati: {len(files)} ({docs})")
    timing_csv = Path(timing_csv)
    timing_csv.parent.mkdir(parents=True, exist_ok=True)
    new_file = not timing_csv.exists()
    totals = []
    with open(timing_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TIMING_FIELDS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        for giro in range(1, runs + 1):
            s = index_once(files, index, content_analyzer, name_mode, store_content, ram_mb)
            print(f"Giro {giro}: indicizzati {s['indicizzati']}, scartati {s['scartati']} | "
                  f"totale {s['totale_ms']:.0f} ms (lettura {s['lettura_ms']:.0f}, "
                  f"inserimento {s['inserimento_ms']:.0f}, commit {s['commit_ms']:.0f}) | "
                  f"{s['indicizzati'] / (s['totale_ms'] / 1000):.0f} doc/s | indice {s['indice_mb']:.1f} MB")
            writer.writerow({"data_ora": datetime.now().isoformat(timespec="seconds"), "giro": giro,
                             "n_file": len(files), "analyzer_contenuto": content_analyzer,
                             "modo_nome": name_mode, "store_contenuto": "si" if store_content else "no",
                             **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items()}})
            totals.append(s["totale_ms"])
    if runs > 1:
        kept = totals[1:]
        sd = statistics.stdev(kept) if len(kept) > 1 else 0.0
        print(f"Tempo totale su {len(kept)} giri (escluso il primo): "
              f"{statistics.mean(kept):.0f} ms +- {sd:.0f} ms")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs", required=True)
    ap.add_argument("--index", default="index/italian")
    ap.add_argument("--content-analyzer", default="italian", choices=CONTENT_ANALYZERS)
    ap.add_argument("--name-mode", default="ngram", choices=NAME_MODES)
    ap.add_argument("--store-content", default="no", choices=["si", "no"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--ram-mb", type=float, default=16.0)
    ap.add_argument("--timing-csv", default="results/timing.csv")
    a = ap.parse_args()
    run(a.docs, a.index, a.content_analyzer, a.name_mode, a.store_content == "si",
        a.limit, a.runs, a.ram_mb, a.timing_csv)


if __name__ == "__main__":
    main()
