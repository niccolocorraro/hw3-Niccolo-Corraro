"""Analyzer dei due campi.

Campo "name" (nome del file senza estensione, es. "Città_di_Castello", "AC_DC",
"Divina_Commedia_(Dante)"):
  - tokenizer pattern che separa su qualsiasi carattere che non sia lettera o cifra;
  - lowercase;
  - asciiFolding: rimuove gli accenti ("Città" -> "citta"), cosi' la ricerca funziona
    anche se l'utente non scrive gli accenti;
  - in modalita' "ngram", edgeNGram (solo in indicizzazione): indicizza anche i prefissi
    di ogni parola ("divina" -> "di", "div", "divi", ...), per la ricerca per prefisso.
    In modalita' "prefix" i prefissi non sono indicizzati e la ricerca per prefisso
    avviene in query con PrefixQuery.
  In query la catena e' la stessa senza edgeNGram: la query "divi" deve restare "divi",
  non diventare "di", "div", "divi".

Campo "content" (testo degli articoli, in italiano):
  - whitespace: separa solo sugli spazi (baseline);
  - italian:    ItalianAnalyzer (elisione, lowercase, stopword italiane, stemmer leggero);
  - leggero:    elisione con gli articoli italiani, lowercase, asciiFolding;
                senza stopword e senza stemming.
"""

from . import jvm  # noqa: F401  (avvia la JVM)

from java.nio.file import Paths
from java.util import HashMap
from org.apache.lucene.analysis.core import WhitespaceAnalyzer
from org.apache.lucene.analysis.custom import CustomAnalyzer
from org.apache.lucene.analysis.it import ItalianAnalyzer
from org.apache.lucene.analysis.miscellaneous import PerFieldAnalyzerWrapper
from org.apache.lucene.analysis.tokenattributes import (
    CharTermAttribute, PositionIncrementAttribute)

CONTENT_ANALYZERS = ("whitespace", "italian", "leggero")
NAME_MODES = ("ngram", "prefix")

# Cartella con i file di configurazione letti da CustomAnalyzer (articoli italiani).
CONFIG_DIR = "config"


def _params(**kwargs):
    """Parametri di un tokenizer o filtro, come Map Java (CustomAnalyzer li consuma)."""
    m = HashMap()
    for k, v in kwargs.items():
        m.put(k, str(v))
    return m


def _name_chain(with_ngrams):
    b = (CustomAnalyzer.builder()
         .withTokenizer("pattern", _params(pattern=r"[^\p{L}\p{N}]+", group=-1))
         .addTokenFilter("lowercase", _params())
         .addTokenFilter("asciiFolding", _params()))
    if with_ngrams:
        b = b.addTokenFilter("edgeNGram",
                             _params(minGramSize=2, maxGramSize=20, preserveOriginal="true"))
    return b.build()


def name_index_analyzer(mode):
    if mode not in NAME_MODES:
        raise ValueError(f"modalita' del nome sconosciuta: {mode}")
    return _name_chain(with_ngrams=(mode == "ngram"))


def name_query_analyzer():
    return _name_chain(with_ngrams=False)


def content_analyzer(name):
    if name == "whitespace":
        return WhitespaceAnalyzer()
    if name == "italian":
        return ItalianAnalyzer()
    if name == "leggero":
        return (CustomAnalyzer.builder(Paths.get(CONFIG_DIR))
                .withTokenizer("standard", _params())
                .addTokenFilter("elision", _params(articles="articoli_it.txt", ignoreCase="true"))
                .addTokenFilter("lowercase", _params())
                .addTokenFilter("asciiFolding", _params())
                .build())
    raise ValueError(f"analyzer del contenuto sconosciuto: {name} "
                     f"(valori ammessi: {', '.join(CONTENT_ANALYZERS)})")


def index_analyzer(content, name_mode):
    """Un solo analyzer per l'IndexWriter: smista ogni campo verso la propria catena."""
    per_field = HashMap()
    per_field.put("name", name_index_analyzer(name_mode))
    per_field.put("content", content_analyzer(content))
    return PerFieldAnalyzerWrapper(content_analyzer(content), per_field)


def analyze(analyzer, field, text):
    """Restituisce la lista di (termine, posizione) prodotta dall'analyzer.
    La posizione tiene conto dei buchi lasciati dalle stopword rimosse."""
    out = []
    stream = analyzer.tokenStream(field, text)
    try:
        term = stream.addAttribute(CharTermAttribute.class_)
        incr = stream.addAttribute(PositionIncrementAttribute.class_)
        stream.reset()
        pos = -1
        while stream.incrementToken():
            pos += incr.getPositionIncrement()
            out.append((term.toString(), pos))
        stream.end()
    finally:
        stream.close()
    return out
