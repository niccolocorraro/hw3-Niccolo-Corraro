"""Costruzione delle query Lucene e ricerca su un indice."""

import json
from pathlib import Path

from . import jvm  # noqa: F401  (avvia la JVM)
from .analyzers import analyze, name_query_analyzer, content_analyzer
from .querysyntax import parse_line, QuerySyntaxError

from java.nio.file import Paths
from org.apache.lucene.index import DirectoryReader, Term
from org.apache.lucene.search import (
    BooleanClause, BooleanQuery, ConstantScoreQuery, IndexSearcher, PhraseQuery,
    PrefixQuery, TermQuery)
from org.apache.lucene.search.similarities import (
    BM25Similarity, ClassicSimilarity, LMDirichletSimilarity)
from org.apache.lucene.store import FSDirectory

SIMILARITIES = ("bm25", "classic", "lmdirichlet", "constant")


def make_similarity(name):
    if name in ("bm25", "constant"):
        return BM25Similarity()
    if name == "classic":
        return ClassicSimilarity()        # tf-idf
    if name == "lmdirichlet":
        return LMDirichletSimilarity()    # modello linguistico con smoothing di Dirichlet
    raise ValueError(f"similarity sconosciuta: {name} (valori ammessi: {', '.join(SIMILARITIES)})")


class Engine:
    """Un indice aperto in lettura, con gli analyzer usati per costruirlo."""

    def __init__(self, index_dir, similarity="bm25", operator="OR"):
        self.index_dir = Path(index_dir)
        self.meta = json.loads((self.index_dir / "meta.json").read_text(encoding="utf-8"))
        self.reader = DirectoryReader.open(FSDirectory.open(Paths.get(str(self.index_dir))))
        self.searcher = IndexSearcher(self.reader)
        self.searcher.setSimilarity(make_similarity(similarity))
        self.constant = (similarity == "constant")
        self.occur = BooleanClause.Occur.MUST if operator.upper() == "AND" else BooleanClause.Occur.SHOULD
        # stesse catene usate in indicizzazione (lette da meta.json), senza gli n-gram
        self.analyzers = {
            "name": name_query_analyzer(),
            "content": content_analyzer(self.meta["content_analyzer"]),
        }
        self.name_mode = self.meta["name_mode"]

    def close(self):
        self.reader.close()

    def _term_query(self, field, token):
        term = Term(field, token)
        if field == "name" and self.name_mode == "prefix":
            return PrefixQuery(term)
        return TermQuery(term)

    def build(self, line):
        """Traduce una riga di testo in una Query Lucene (None se non resta nessun termine)."""
        field, segments = parse_line(line)
        analyzer = self.analyzers[field]
        builder = BooleanQuery.Builder()
        clauses = 0
        for kind, text in segments:
            tokens = analyze(analyzer, field, text)
            if not tokens:
                continue                      # solo stopword: il segmento sparisce
            if kind == "frase" and len(tokens) > 1:
                pb = PhraseQuery.Builder()
                first = tokens[0][1]
                for token, pos in tokens:
                    pb.add(Term(field, token), pos - first)
                builder.add(pb.build(), self.occur)
                clauses += 1
            else:
                # un termine dell'utente puo' produrre piu' token (es. "l'Italia-Francia")
                for token, _ in tokens:
                    builder.add(self._term_query(field, token), self.occur)
                    clauses += 1
        if clauses == 0:
            return None
        query = builder.build()
        return ConstantScoreQuery(query) if self.constant else query

    def search(self, query, k):
        """Restituisce (numero di documenti che soddisfano la query, [(nome file, punteggio)])."""
        top = self.searcher.search(query, k)
        stored = self.searcher.storedFields()
        hits = [(stored.document(sd.doc).get("filename"), sd.score) for sd in top.scoreDocs]
        return self.searcher.count(query), hits


__all__ = ["Engine", "QuerySyntaxError", "SIMILARITIES"]
