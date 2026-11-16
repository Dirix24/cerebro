"""Recuperación semántica local ligera mediante TF-IDF de n-gramas.

No usa embeddings preentrenados ni servicios externos. Es similitud
estadística, no comprensión semántica profunda.
"""
import math
import re
import unicodedata
from collections import Counter


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _rasgos(texto):
    palabras = re.findall(r"[a-z0-9]+", _normalizar(texto))
    rasgos = ["w:" + p for p in palabras]
    rasgos += ["c:" + p[i:i + 3] for p in palabras for i in range(max(0, len(p) - 2))]
    return Counter(rasgos)


def buscar_similares(consulta, documentos, limite=5):
    """Devuelve (indice, similitud_coseno) ordenados, sin inventar respuestas."""
    if limite <= 0 or not consulta.strip():
        return []
    documentos = list(documentos)
    vectores = [_rasgos(t) for t in documentos]
    consulta_v = _rasgos(consulta)
    if not consulta_v:
        return []
    df = Counter()
    for v in vectores:
        df.update(v.keys())
    n = len(vectores)
    def pesos(v):
        return {k: tf * (math.log((n + 1) / (df.get(k, 0) + 1)) + 1)
                for k, tf in v.items()}
    q = pesos(consulta_v)
    norma_q = math.sqrt(sum(x * x for x in q.values()))
    resultados = []
    for i, v in enumerate(vectores):
        w = pesos(v)
        norma = math.sqrt(sum(x * x for x in w.values()))
        score = sum(q.get(k, 0) * x for k, x in w.items()) / (norma_q * norma) if norma_q and norma else 0
        if score > 0:
            resultados.append((i, score))
    return sorted(resultados, key=lambda x: (-x[1], x[0]))[:limite]
