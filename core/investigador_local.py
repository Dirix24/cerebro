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


def diferencias_numericas(fuentes):
    """Señala cifras distintas en frases casi idénticas de dominios distintos."""
    from decimal import Decimal
    import re

    from core.respuestas_con_fuentes import normalizar

    grupos = {}
    patron = re.compile(r"(?<![\w.,])([+-]?\d+(?:[.,]\d+)?)\s*(°\s*[CF]|%|km|m|kg|g)(?!\w)", re.I)
    for fuente in fuentes:
        url, texto = fuente.get("url"), fuente.get("extracto")
        if not isinstance(url, str) or not isinstance(texto, str):
            continue
        enlace = urlparse(url)
        if enlace.scheme != "https" or not enlace.hostname:
            continue
        for frase in re.split(r"(?<=[.!?])\s+", texto[:400]):
            valores = list(patron.finditer(frase))
            if len(valores) != 1:
                continue
            valor = valores[0]
            inicio, fin = valor.span(1)
            unidad = valor[2].casefold().replace(" ", "")
            clave = (normalizar(frase[:inicio]), unidad, normalizar(frase[fin:]))
            if len((clave[0] + " " + clave[2]).split()) < 5:
                continue
            cifra = Decimal(valor[1].replace(",", "."))
            previos = grupos.setdefault(clave, [])
            for origen, anterior, dominio in previos:
                if anterior != cifra and dominio != enlace.hostname:
                    return origen, url
            previos.append((url, cifra, enlace.hostname))
    return None
