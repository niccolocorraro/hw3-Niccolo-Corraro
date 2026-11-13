"""Avvio unico della JVM di PyLucene.

PyLucene esegue Lucene in una JVM incorporata nel processo Python: la JVM va avviata
una sola volta, prima di usare qualsiasi classe Java. Ogni modulo del progetto
importa questo file per primo.
"""

import lucene

if lucene.getVMEnv() is None:
    lucene.initVM(vmargs=["-Djava.awt.headless=true"])
else:
    lucene.getVMEnv().attachCurrentThread()

LUCENE_VERSION = lucene.VERSION
