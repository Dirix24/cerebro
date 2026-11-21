"""Separación de preguntas y normalización conservadora de cálculos dictados."""
import re
import unicodedata

_NUMEROS = dict(zip("cero uno dos tres cuatro cinco seis siete ocho nueve diez".split(), map(str, range(11))))
_OPERADORES = {"mas": "+", "menos": "-", "por": "*", "entre": "/"}


def preguntas_multiples(texto):
    segmentos = re.findall(r"[^?]+\?", texto)
    if not 2 <= len(segmentos) <= 4 or "".join(segmentos).strip() != texto.strip():
        return []
    preguntas = [re.sub(r"^\s*(?:y\s+)?¿?\s*", "", parte, flags=re.I) for parte in segmentos]
    if not all(re.match(r"(?:qu[eé]|cu[aá]l(?:es)?|cu[aá]nto|c[oó]mo|d[oó]nde|cu[aá]ndo)\b", p, re.I)
               for p in preguntas):
        return []
    return ["¿" + pregunta for pregunta in preguntas]


def calculo_dictado(texto):
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                    if not unicodedata.combining(c)).strip(" ?¿!¡.")
    coincidencia = re.fullmatch(r"(?:cuanto es|calcula)\s+((?:\w+\s+){2,6}\w+)", texto)
    if not coincidencia:
        return None
    tokens = coincidencia[1].split()
    if len(tokens) % 2 == 0:
        return None
    salida = []
    for i, token in enumerate(tokens):
        valor = (_OPERADORES.get(token) if i % 2 else
                 _NUMEROS.get(token, token if re.fullmatch(r"[0-9]{1,8}", token) else None))
        if valor is None:
            return None
        salida.append(valor)
    return " ".join(salida)
