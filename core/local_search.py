"""Búsqueda local en el corpus de Cerebro mediante SQLite FTS5.

No usa Internet, modelos externos ni servicios. Índice reconstruible desde texto.
"""
import argparse
from pathlib import Path
import sqlite3
import re

import config

DB = Path(config._RAIZ) / "data" / "corpus_fts.sqlite3"


def fuentes():
    base = Path(config.CORPUS_FILE)
    if base.is_file() and not base.is_symlink():
        yield base
    # Los artículos de Wikipedia también forman parte del corpus consultable.
    internet = Path(config._RAIZ) / "data" / "aprendizaje_internet" / "corpus_diario.txt"
    if internet.is_file() and not internet.is_symlink():
        yield internet
    carpeta = Path(config.CORPUS_DIR)
    if carpeta.is_dir() and not carpeta.is_symlink():
        for ruta in sorted(carpeta.glob("*.txt")):
            if ruta.is_file() and not ruta.is_symlink():
                yield ruta


def documentos(texto):
    return [p.strip() for p in texto.replace("\r\n", "\n").split("\n\n") if p.strip()]


def indexar(db=DB):
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.is_symlink():
        raise ValueError("No se admite un índice simbólico")
    cantidad = 0
    with sqlite3.connect(db) as con:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS corpus USING fts5(texto, origen UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
        con.execute("DELETE FROM corpus")
        for ruta in fuentes():
            for doc in documentos(ruta.read_text(encoding="utf-8")):
                con.execute("INSERT INTO corpus(texto, origen) VALUES (?, ?)", (doc, ruta.name))
                cantidad += 1
    return cantidad


def buscar(consulta, db=DB, limite=3):
    """Consulta de términos literales: evita interpretar operadores FTS del usuario."""
    palabras = [p for p in re.findall(r"\w+", consulta, flags=re.UNICODE) if p]
    if not palabras:
        return []
    db = Path(db)
    if not db.is_file() or db.is_symlink():
        return []
    terminos = ['"' + p.replace('"', '""') + '"' for p in palabras[:12]]
    expresiones = [" AND ".join(terminos), " OR ".join(terminos)]
    with sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True) as con:
        try:
            for expresion in expresiones:
                filas = con.execute(
                    "SELECT texto, origen FROM corpus WHERE corpus MATCH ? ORDER BY bm25(corpus) LIMIT ?",
                    (expresion, max(1, min(int(limite), 10))),
                ).fetchall()
                if filas:
                    return filas
            return []
        except sqlite3.OperationalError:
            return []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Índice local SQLite FTS5 del corpus Cerebro")
    ap.add_argument("--indexar", action="store_true", help="Reconstruir índice local")
    ap.add_argument("--buscar", metavar="TEXTO", help="Buscar en índice ya creado")
    args = ap.parse_args(argv)
    if args.indexar == (args.buscar is not None):
        ap.error("Elige --indexar o --buscar")
    if args.indexar:
        print(f"Indexados {indexar()} documentos locales.")
    else:
        for texto, origen in buscar(args.buscar):
            print(f"[{origen}] {texto}\n")


if __name__ == "__main__":
    main()
