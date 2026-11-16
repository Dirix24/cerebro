"""Herramientas de estudio deterministas; no usan modelos preentrenados."""
import re
from collections import Counter


def resumir(texto, max_frases=3):
    if not 1 <= max_frases <= 10:
        raise ValueError("Número de frases fuera de rango")
    if len(texto) > 100000:
        raise ValueError("Texto demasiado largo")
    frases = [s.strip() for s in re.split(r"(?<=[.!?])\s+", texto.strip()) if s.strip()]
    if len(frases) <= max_frases:
        return " ".join(frases)
    palabras = re.findall(r"\b\w{4,}\b", texto.casefold())
    comunes = {"para", "como", "esta", "este", "pero", "porque", "sobre", "entre",
               "desde", "hasta", "tiene", "también", "donde", "cuando"}
    frecuencia = Counter(p for p in palabras if p not in comunes)
    puntuaciones = [
        sum(frecuencia[p] for p in re.findall(r"\b\w{4,}\b", frase.casefold()))
        / max(1, len(frase.split()))
        for frase in frases
    ]
    indices = sorted(sorted(range(len(frases)), key=lambda i: (-puntuaciones[i], i))[:max_frases])
    return " ".join(frases[i] for i in indices)


def palabras_clave(texto, limite=8):
    if not 1 <= limite <= 30:
        raise ValueError("Límite fuera de rango")
    if len(texto) > 100000:
        raise ValueError("Texto demasiado largo")
    excluidas = {"para", "como", "esta", "este", "pero", "porque", "sobre", "entre",
                 "desde", "hasta", "tiene", "también", "donde", "cuando"}
    contador = Counter(p for p in re.findall(r"\b\w{4,}\b", texto.casefold())
                       if p not in excluidas)
    return [p for p, _ in contador.most_common(limite)]
