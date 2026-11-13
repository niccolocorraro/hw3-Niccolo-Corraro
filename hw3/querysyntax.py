"""Sintassi delle query, indipendente da Lucene.

Una query e' una riga del tipo:
    nome <termini>
    contenuto <termini>
dove i termini tra virgolette formano una frase (phrase query):
    contenuto "seconda guerra mondiale" italia
"""

import re

FIELDS = {"nome": "name", "contenuto": "content"}

# Una frase tra virgolette oppure una sequenza di caratteri senza spazi e senza virgolette.
_TOKEN = re.compile(r'"([^"]*)"|([^\s"]+)')


class QuerySyntaxError(ValueError):
    pass


def parse_line(line):
    """Separa una riga in (campo Lucene, segmenti).
    Ogni segmento e' ("frase", testo) oppure ("termine", testo)."""
    text = line.strip()
    if not text:
        raise QuerySyntaxError("query vuota")
    keyword, _, rest = text.partition(" ")
    field = FIELDS.get(keyword.lower())
    if field is None:
        raise QuerySyntaxError(f"parola chiave sconosciuta '{keyword}': usa 'nome' o 'contenuto'")
    rest = rest.strip()
    if not rest:
        raise QuerySyntaxError(f"mancano i termini dopo '{keyword}'")
    if rest.count('"') % 2:
        raise QuerySyntaxError("virgolette non chiuse")

    segments = []
    for phrase, word in _TOKEN.findall(rest):
        if phrase.strip():
            segments.append(("frase", phrase.strip()))
        elif word:
            segments.append(("termine", word))
    if not segments:
        raise QuerySyntaxError("nessun termine da cercare")
    return field, segments
