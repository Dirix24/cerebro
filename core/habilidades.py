"""Inducción local de reglas afines a partir de ejemplos aprobados."""
from contextlib import closing
from fractions import Fraction
from pathlib import Path
import re
import sqlite3

NAME = re.compile(r"[a-záéíóúüñ][a-záéíóúüñ0-9_-]{0,31}")
NUMBER = re.compile(r"[+-]?\d{1,9}(?:[.,]\d{1,6})?")


def name_key(name):
    name = name.strip().casefold()
    if not NAME.fullmatch(name):
        raise ValueError("Usa un nombre de hasta 32 letras, números, guiones o guiones bajos.")
    return name


def number(text):
    value = text.strip()
    if not NUMBER.fullmatch(value):
        raise ValueError("Usa un entero o decimal de hasta nueve cifras enteras y seis decimales.")
    return Fraction(value.replace(",", "."))


def induce(spec):
    if len(spec) > 1500:
        raise ValueError("Demasiados datos.")
    rows = spec.split(";")
    if not 3 <= len(rows) <= 20:
        raise ValueError("Da de 3 a 20 ejemplos con entradas distintas: 0:1; 1:3; 2:5.")
    examples = []
    for row in rows:
        pair = row.split(":")
        if len(pair) != 2:
            raise ValueError("Cada ejemplo debe tener el formato entrada:salida.")
        examples.append(tuple(map(number, pair)))
    if len({x for x, _ in examples}) != len(examples):
        raise ValueError("Cada ejemplo necesita una entrada distinta.")
    (x1, y1), (x2, y2), *_ = examples
    slope = (y2 - y1) / (x2 - x1)
    offset = y1 - slope * x1
    if any(slope * x + offset != y for x, y in examples[2:]):
        raise ValueError("Los ejemplos de comprobación contradicen la regla afín.")
    return slope, offset, min(x for x, _ in examples), max(x for x, _ in examples), len(examples)


def connect(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("No se permite una base de habilidades simbólica.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def teach(path, name, spec, *, revise=False):
    name = name_key(name)
    slope, offset, lower, upper, count = induce(spec)
    with closing(connect(path)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY, slope TEXT NOT NULL, offset TEXT NOT NULL,
            lower_bound TEXT NOT NULL, upper_bound TEXT NOT NULL,
            revision INTEGER NOT NULL, examples INTEGER NOT NULL
        )""")
        db.execute("BEGIN IMMEDIATE")
        if revise:
            change = db.execute(
                """UPDATE skills SET slope=?, offset=?, lower_bound=?, upper_bound=?,
                   revision=revision+1, examples=? WHERE name=?""",
                (str(slope), str(offset), str(lower), str(upper), count, name),
            )
            if not change.rowcount:
                raise ValueError("La habilidad todavía no existe.")
        else:
            change = db.execute(
                "INSERT OR IGNORE INTO skills VALUES (?, ?, ?, ?, ?, 1, ?)",
                (name, str(slope), str(offset), str(lower), str(upper), count),
            )
            if not change.rowcount:
                raise ValueError("La habilidad ya existe. Usa /corregir-habilidad para revisarla.")
    return f"{name}: f(x) = ({slope})·x + ({offset}). Regla local guardada tras comprobar {count - 2} ejemplo(s)."


def chain(path, names, raw):
    if not 1 <= len(names) <= 5:
        raise ValueError("Encadena entre una y cinco habilidades.")
    names = [name_key(name) for name in names]
    value = number(raw)
    if not Path(path).is_file():
        raise ValueError("Todavía no hay habilidades enseñadas.")
    results = []
    with closing(connect(path)) as db, db:
        db.execute("BEGIN")
        for name in names:
            row = db.execute(
                "SELECT slope,offset,lower_bound,upper_bound,revision FROM skills WHERE name=?", (name,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Habilidad desconocida: {name}.")
            slope, offset, lower, upper = map(Fraction, row[:4])
            outside = not lower <= value <= upper
            value = slope * value + offset
            results.append((name, value, row[4], outside))
    return results


def apply(path, name, raw):
    _, result, revision, outside = chain(path, [name], raw)[0]
    return result, revision, outside
