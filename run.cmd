@echo off
REM Esegue uno script Python del progetto dentro il container PyLucene.
REM Uso (dalla cartella del progetto):  .\run.cmd indexer.py --docs data/wiki_it/docs
REM Il codice resta nella cartella del progetto; dataset e indici stanno in due volumi
REM Docker (hw3b-data, hw3b-index), su file system Linux, piu' veloce per molti file piccoli.
docker run --rm -it -v "%cd%:/work" -v hw3b-data:/work/data -v hw3b-index:/work/index -w /work hw3b python %*
