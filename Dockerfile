# Ambiente di esecuzione: PyLucene (Lucene + JVM + Python) con le librerie Python usate
# dagli script. Tutti i programmi del progetto vengono eseguiti dentro questo container.
FROM coady/pylucene

ENV PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN pip install --no-cache-dir datasets matplotlib

WORKDIR /work
