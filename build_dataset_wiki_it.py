"""
Costruisce il dataset di file .txt: un file per articolo di Wikipedia italiana,
con il titolo dell'articolo come nome del file.

Uso:
    python build_dataset_wiki_it.py --out data/wiki_it --n 50000

Output in --out:
    docs/                 file .txt (uno per articolo)
    mapping.csv           id, titolo, nome file, url, numero di caratteri
    stats.json            statistiche del corpus

Scelte:
  * Fonte: Wikipedia IT pubblicata su Hugging Face ("wikimedia/wikipedia",
    config "20231101.it"), licenza CC BY-SA.
  * Campionamento: lo stream e' ordinato per id di articolo; uno shuffle con
    buffer evita di prendere solo i primi articoli. Il campione e' approssimato,
    non uniforme sull'intera Wikipedia.
  * Filtro: articoli piu' corti di --min-chars scartati (stub).
  * Nome del file: titolo senza i caratteri non ammessi dai file system
    (es. "AC/DC" -> "AC_DC"), spazi sostituiti da "_", accenti mantenuti.
"""

import argparse
import csv
import json
import os
import re
import statistics
import unicodedata
from datetime import date
from pathlib import Path

# Caratteri vietati su Windows/macOS/Linux, piu' i caratteri di controllo.
INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MAX_NAME_LEN = 100  # i nomi molto lunghi creano problemi su alcuni file system
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL",
                    *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def title_to_filename(title: str) -> str:
    """Trasforma un titolo in un nome di file sicuro (senza estensione)."""
    name = unicodedata.normalize("NFC", title)       # accenti in forma unica
    name = INVALID_CHARS.sub("_", name)
    name = re.sub(r"\s+", "_", name.strip())          # spazi -> underscore
    name = re.sub(r"_+", "_", name).strip("._")       # niente "__" o "." finali
    name = name[:MAX_NAME_LEN].rstrip("._") or "senza_titolo"
    # Nomi riservati da Windows (anche con estensione: "con.txt" non e' creabile)
    if name.upper() in WINDOWS_RESERVED:
        name += "_"
    return name


def unique_name(base: str, used: set) -> str:
    """Evita collisioni: due titoli possono dare lo stesso nome ripulito."""
    name, k = base, 2
    while name.lower() in used:                       # lower: macOS/Windows non
        name = f"{base}_{k}"                          # distinguono maiuscole
        k += 1
    used.add(name.lower())
    return name


def build(articles, out_dir: Path, n: int, min_chars: int) -> dict:
    """Scrive al massimo n articoli in out_dir/docs. `articles` e' un iterabile
    di dict con chiavi id, title, text, url (cosi' la funzione e' testabile
    anche senza scaricare nulla)."""
    docs_dir = out_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    used, lengths = set(), []
    skipped_short = skipped_dup = 0
    seen_ids = set()

    with open(out_dir / "mapping.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "title", "filename", "url", "n_chars"])
        for art in articles:
            if len(lengths) >= n:
                break
            text = (art.get("text") or "").strip()
            if art["id"] in seen_ids:
                skipped_dup += 1
                continue
            if len(text) < min_chars:
                skipped_short += 1
                continue
            seen_ids.add(art["id"])
            fname = unique_name(title_to_filename(art["title"]), used) + ".txt"
            (docs_dir / fname).write_text(text, encoding="utf-8")
            writer.writerow([art["id"], art["title"], fname, art.get("url", ""), len(text)])
            lengths.append(len(text))

    total_bytes = sum(p.stat().st_size for p in docs_dir.glob("*.txt"))
    return {
        "source": "Hugging Face wikimedia/wikipedia, config 20231101.it",
        "license": "CC BY-SA 4.0",
        "built_on": date.today().isoformat(),
        "n_files": len(lengths),
        "skipped_short": skipped_short,
        "skipped_duplicates": skipped_dup,
        "min_chars_filter": min_chars,
        "total_MB": round(total_bytes / 1e6, 2),
        "chars_mean": round(statistics.mean(lengths)) if lengths else 0,
        "chars_median": round(statistics.median(lengths)) if lengths else 0,
        "chars_min": min(lengths, default=0),
        "chars_max": max(lengths, default=0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/wiki_it"))
    ap.add_argument("--n", type=int, default=50000, help="numero di articoli")
    ap.add_argument("--min-chars", type=int, default=500, help="scarta articoli piu' corti")
    ap.add_argument("--seed", type=int, default=42, help="per rendere il campione ripetibile")
    ap.add_argument("--buffer", type=int, default=20000, help="dimensione del buffer di shuffle")
    args = ap.parse_args()

    from datasets import load_dataset  # import qui: build() resta testabile senza la libreria

    # streaming=True: non scarica tutta Wikipedia, legge solo quello che serve
    ds = load_dataset("wikimedia/wikipedia", "20231101.it", split="train", streaming=True)
    ds = ds.shuffle(seed=args.seed, buffer_size=args.buffer)

    stats = build(ds, args.out, args.n, args.min_chars)
    stats.update({"seed": args.seed, "shuffle_buffer": args.buffer})
    (args.out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False), flush=True)
    # Lo streaming di datasets puo' lasciare thread di download attivi che impediscono
    # la chiusura del processo: tutti i file sono gia' scritti, quindi si esce subito.
    os._exit(0)


if __name__ == "__main__":
    main()
