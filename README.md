# HW3 Ingegneria dei Dati: ricerca su file .txt con PyLucene

Il sistema indicizza i file `.txt` di una directory in un indice Lucene con due campi, **nome del file** e **contenuto**, e li interroga da console. È scritto in Python con PyLucene ed eseguito in un container Docker. Il corpus è un campione di articoli di Wikipedia in italiano; i giudizi di rilevanza per le query sul contenuto sono costruiti con il metodo del pooling, seguendo criteri scritti per ogni query (`judgments/criteri.md`).

## Struttura

```
Dockerfile              ambiente PyLucene + librerie Python
run.cmd / run.sh        eseguono uno script nel container (Windows / macOS-Linux)
config/articoli_it.txt  articoli italiani per il filtro di elisione
hw3/
  jvm.py                avvio della JVM di PyLucene
  analyzers.py          analyzer dei campi nome e contenuto
  querysyntax.py        sintassi delle query (nome/contenuto, frasi tra virgolette)
  search.py             costruzione delle query Lucene e ricerca
build_dataset_wiki_it.py  creazione dei file .txt da Wikipedia italiana
make_name_queries.py      query sul nome per la ricerca di un elemento noto
indexer.py                indicizzazione e misura dei tempi
searcher.py               ricerca da console e in batch
analyzer_demo.py          tabelle dei token prodotti dagli analyzer
judgments.py              pooling e giudizi di rilevanza
evaluate.py               metriche: P@k, R@k, F1@k, MRR, Giudicati@k
experiments.py            esecuzione degli esperimenti per fasi
queries/                  query di test e giudizi
judgments/pool.csv        documenti da giudicare / giudicati
results/                  metriche, tempi, grafici
```

Dataset e indici sono salvati in due volumi Docker (`hw3b-data`, `hw3b-index`) e non nel repository.

## Preparazione

```
docker build -t hw3b .
```

Tutti i comandi seguenti si lanciano dalla cartella del progetto con `.\run.cmd` (Windows) o `./run.sh` (macOS/Linux).

## 1. Dataset

```
.\run.cmd build_dataset_wiki_it.py --out data/wiki_it --n 50000
.\run.cmd make_name_queries.py --docs data/wiki_it/docs
```

Il primo comando scarica in streaming un campione di 50.000 articoli di Wikipedia italiana (scartando quelli sotto i 500 caratteri) e scrive un file per articolo, con il titolo come nome. Il secondo genera 20 query sul nome a partire da file estratti a caso.

## 2. Analyzer

```
.\run.cmd analyzer_demo.py
```

| Campo | Analyzer |
| --- | --- |
| nome (indice, modo `ngram`) | pattern su caratteri non alfanumerici, lowercase, asciiFolding, edgeNGram (2-20) |
| nome (indice, modo `prefix`) | come sopra senza edgeNGram; in query PrefixQuery |
| nome (query) | come sopra senza edgeNGram |
| contenuto `whitespace` | WhitespaceAnalyzer (baseline) |
| contenuto `italian` | ItalianAnalyzer: elisione, lowercase, stopword, stemmer leggero |
| contenuto `leggero` | elisione (articoli italiani), lowercase, asciiFolding; senza stopword e stemming |

Un `PerFieldAnalyzerWrapper` applica a ciascun campo il proprio analyzer. L'indice salva in `meta.json` gli analyzer usati, che il programma di ricerca rilegge.

## 3. Indicizzazione

```
.\run.cmd indexer.py --docs data/wiki_it/docs --index index/italian --runs 4
```

Opzioni: `--content-analyzer` (`whitespace`, `italian`, `leggero`), `--name-mode` (`ngram`, `prefix`), `--store-content` (`si`, `no`), `--limit N` (campione casuale con seme fisso), `--runs R` (con più giri il primo è escluso dalla media), `--timing-csv`.

## 4. Ricerca

```
.\run.cmd searcher.py --index index/italian [--op OR|AND] [--similarity bm25|classic|lmdirichlet|constant]
```

```
> nome divi comm
> contenuto "seconda guerra mondiale" italia
> exit
```

La riga viene separata in frasi (tra virgolette) e termini; ciascun pezzo è analizzato con l'analyzer del campo e diventa una `PhraseQuery` o una `TermQuery` (`PrefixQuery` sul nome in modo `prefix`), combinate in una `BooleanQuery` con l'operatore scelto. Errori segnalati: parola chiave sconosciuta, virgolette non chiuse, query senza termini, query composta solo da stopword.

## 5. Esperimenti

```
.\run.cmd experiments.py indici
.\run.cmd experiments.py run
.\run.cmd experiments.py pool
```

`pool` crea `judgments/pool.csv` con i primi 10 risultati di quattro configurazioni per ogni query sul contenuto (372 coppie query-documento). La colonna `rilevante` contiene 1 o 0 secondo i criteri di `judgments/criteri.md`. Poi:

```
.\run.cmd judgments.py qrels
.\run.cmd experiments.py valuta
.\run.cmd experiments.py tempi
```

| Esperimento | Configurazioni |
| --- | --- |
| Analyzer del contenuto | whitespace, italian, leggero (BM25, OR) |
| Ranking | BM25, ClassicSimilarity (tf-idf), LMDirichletSimilarity, ConstantScoreQuery (nessun ranking) |
| Operatore | OR contro AND |
| Nome | edgeNGram contro PrefixQuery, OR e AND |
| Tempi | 1.000-50.000 file; contenuto memorizzato sì/no |

## Limiti

- I giudizi di rilevanza sono stati assegnati con l'aiuto di un modello linguistico (Claude), applicando i criteri scritti di `judgments/criteri.md` a titolo e anteprima di ogni documento.
- I giudizi riguardano solo i documenti nel pool: la recall è relativa al pool e i documenti non giudicati sono considerati non rilevanti. La colonna Giudicati@k indica quanto ogni run resta dentro il pool.
- Il campione di Wikipedia è ottenuto con uno shuffle a buffer, quindi non è uniforme sull'intera Wikipedia.
- I tempi sono misurati dentro Docker su volumi Linux e dipendono dalla macchina.
