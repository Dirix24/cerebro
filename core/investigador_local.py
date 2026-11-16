"""Comparación de textos y procedencia; la descarga se mantiene en aprendizaje_internet.py."""
import hashlib
from urllib.parse import urlparse


def preparar_fuente(url, texto):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or len(texto) > 100000:
        raise ValueError("Fuente inválida")
    limpio = " ".join(texto.split())
    return {"url": url, "texto": limpio,
            "sha256": hashlib.sha256(limpio.encode("utf-8")).hexdigest()}


def deduplicar(fuentes):
    vistos = set()
    resultado = []
    for fuente in fuentes:
        if fuente["sha256"] not in vistos:
            resultado.append(fuente)
            vistos.add(fuente["sha256"])
    return resultado
