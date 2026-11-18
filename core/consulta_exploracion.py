"""Consulta privada de los documentos indexados por exploracion_autonoma.

No usa Internet ni ejecuta documentos. Las coincidencias no son hechos verificados.
"""
from pathlib import Path
import re
import sqlite3

from exploracion_autonoma import DB

STOP = {"de", "del", "la", "las", "el", "los", "en", "un", "una", "que",
        "sobre", "datos", "informacion", "información", "documentos",
        "archivo", "archivos", "busca", "buscar", "mis", "mi", "por", "para"}


def consultar(consulta, db=DB, limite=3):
    """Devuelve fragmentos coincidentes y rutas locales, o [] sin índice."""
    db = Path(db)
    if not db.is_file() or db.is_symlink():
        return []
    palabras = [p for p in re.findall(r"\w+", consulta.casefold())
                if len(p) > 2 and p not in STOP][:8]
    if not palabras:
        return []
    expresion = " OR ".join('"' + p.replace('"', '""') + '"' for p in palabras)
    try:
        with sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True) as con:
            filas = con.execute(
                "SELECT snippet(documentos, 0, '', '', ' … ', 35), origen "
                "FROM documentos WHERE documentos MATCH ? "
                "ORDER BY bm25(documentos) LIMIT ?",
                (expresion, min(max(1, limite), 5)),
            ).fetchall()
        return [(texto.strip(), ruta) for texto, ruta in filas]
    except (sqlite3.Error, OSError):
        return []


def respuesta_documental(consulta, db=DB):
    resultados = consultar(consulta, db=db)
    if not resultados:
        return ("No encontré coincidencias en los documentos locales explorados. "
                "Prueba otra palabra o vuelve a ejecutar la exploración.")
    bloques = []
    for texto, ruta in resultados:
        bloques.append(f"Coincidencia (no verificada): {texto[:500]}\nArchivo local: {ruta}")
    return "\n\n".join(bloques)
