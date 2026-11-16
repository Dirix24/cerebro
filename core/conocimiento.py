"""Base de conocimiento local con fuentes y detección de posibles contradicciones.

Sin modelos externos ni APIs de IA. La detección es heurística: señala
candidatos para revisión, no determina la verdad.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
try:
    from core.semantic_memory import buscar_similares
except ModuleNotFoundError:
    from semantic_memory import buscar_similares

BASE = Path(__file__).resolve().parents[1] / "data" / "conocimiento.sqlite3"


def conectar(ruta=BASE):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.is_symlink():
        raise ValueError("No se permiten bases simbólicas")
    con = sqlite3.connect(ruta)
    con.execute("""CREATE TABLE IF NOT EXISTS hechos (
        id INTEGER PRIMARY KEY, pregunta TEXT NOT NULL,
        respuesta TEXT NOT NULL, fuente TEXT NOT NULL,
        creado TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(pregunta, respuesta, fuente))""")
    return con


def _clave(s):
    return " ".join(re.findall(r"\w+", s.casefold()))


def posibles_contradicciones(pregunta, respuesta, existentes):
    """Detecta negaciones opuestas en la misma pregunta; puede dar falsos positivos."""
    candidatos = []
    nueva = _clave(respuesta)
    for viejo, fuente in existentes:
        anterior = _clave(viejo)
        if anterior == nueva:
            continue
        neg_nueva = bool(re.search(r"\b(no|nunca|jamas|sin)\b", nueva))
        neg_anterior = bool(re.search(r"\b(no|nunca|jamas|sin)\b", anterior))
        if neg_nueva != neg_anterior:
            candidatos.append({"respuesta_anterior": viejo, "fuente": fuente,
                               "motivo": "negación diferente; requiere revisión"})
    return candidatos


def guardar(pregunta, respuesta, fuente, ruta=BASE):
    if not all(isinstance(x, str) and x.strip() for x in (pregunta, respuesta, fuente)):
        raise ValueError("Pregunta, respuesta y fuente obligatorias")
    if len(pregunta) > 300 or len(respuesta) > 12000 or len(fuente) > 2048:
        raise ValueError("Entrada demasiado grande")
    with conectar(ruta) as con:
        existentes = con.execute(
            "SELECT respuesta, fuente FROM hechos WHERE pregunta = ? LIMIT 100",
            (pregunta,)).fetchall()
        alertas = posibles_contradicciones(pregunta, respuesta, existentes)
        con.execute("INSERT OR IGNORE INTO hechos(pregunta,respuesta,fuente) VALUES (?,?,?)",
                    (pregunta, respuesta, fuente))
    return alertas


def respuesta_exacta(consulta, ruta=BASE):
    """Responde solo si la pregunta coincide y las fuentes no discrepan."""
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return None
    with conectar(ruta) as con:
        filas = con.execute("SELECT pregunta,respuesta,fuente FROM hechos ORDER BY id DESC LIMIT 2000").fetchall()
    coinciden = [(r, f) for p, r, f in filas if _clave(p) == _clave(consulta)]
    if not coinciden or len({_clave(r) for r, _ in coinciden}) != 1:
        return None
    respuesta, fuente = coinciden[0]
    return {"respuesta": respuesta, "fuente": fuente}


def buscar(consulta, limite=3, ruta=BASE):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return []
    with conectar(ruta) as con:
        filas = con.execute("SELECT pregunta,respuesta,fuente FROM hechos ORDER BY id DESC LIMIT 2000").fetchall()
    if not filas:
        return []
    orden = buscar_similares(consulta, [p + " " + r[:250] for p, r, _ in filas], limite)
    return [{"pregunta": filas[i][0], "respuesta": filas[i][1],
             "fuente": filas[i][2], "similitud": round(score, 4)}
            for i, score in orden]


def main():
    ap = argparse.ArgumentParser(description="Conocimiento local verificable")
    sub = ap.add_subparsers(dest="accion", required=True)
    a = sub.add_parser("guardar")
    a.add_argument("pregunta")
    a.add_argument("respuesta")
    a.add_argument("--fuente", required=True)
    b = sub.add_parser("buscar")
    b.add_argument("consulta")
    b.add_argument("--limite", type=int, default=3)
    args = ap.parse_args()
    resultado = (guardar(args.pregunta, args.respuesta, args.fuente)
                 if args.accion == "guardar" else buscar(args.consulta, args.limite))
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
