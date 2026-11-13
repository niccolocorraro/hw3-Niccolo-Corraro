#!/usr/bin/env bash
# Equivalente di run.cmd per macOS e Linux.
# Uso (dalla cartella del progetto):  ./run.sh indexer.py --docs data/wiki_it/docs
exec docker run --rm -it -v "$(pwd):/work" -v hw3b-data:/work/data -v hw3b-index:/work/index \
     -w /work hw3b python "$@"
