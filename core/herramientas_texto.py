"""Funciones educativas locales: estadísticas, comparación y fichas de estudio."""
import difflib
import re
from collections import Counter


def estadisticas(texto):
    if len(texto) > 100000:
        raise ValueError("Texto demasiado largo")
    palabras = re.findall(r"\b\w+\b", texto, flags=re.UNICODE)
    frases = [f for f in re.split(r"[.!?]+", texto) if f.strip()]
    return {"caracteres": len(texto), "palabras": len(palabras),
            "palabras_unicas": len(set(p.casefold() for p in palabras)),
            "frases": len(frases), "lineas": len(texto.splitlines())}


def comparar_textos(primero, segundo):
    if len(primero) > 10000 or len(segundo) > 10000:
        raise ValueError("Textos demasiado largos")
    a = primero.split()
    b = segundo.split()
    similitud = round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 3)
    cambios = list(difflib.ndiff(a, b))
    return {"similitud": similitud,
            "eliminadas": [x[2:] for x in cambios if x.startswith("- ")][:50],
            "agregadas": [x[2:] for x in cambios if x.startswith("+ ")][:50]}


def fichas_estudio(texto, limite=8):
    """Genera fichas únicamente a partir de líneas 'concepto: definición'."""
    if not 1 <= limite <= 30 or len(texto) > 100000:
        raise ValueError("Entrada fuera de límites")
    fichas = []
    for linea in texto.splitlines():
        if ":" not in linea:
            continue
        concepto, definicion = (x.strip() for x in linea.split(":", 1))
        if concepto and definicion and len(concepto) <= 100 and len(definicion) <= 500:
            fichas.append({"pregunta": f"¿Qué es {concepto}?", "respuesta": definicion})
        if len(fichas) >= limite:
            break
    return fichas
