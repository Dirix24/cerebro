"""Autoevaluación reproducible con fichas verificadas; nunca autoaprueba textos web."""
import re
import unicodedata
from pathlib import Path

from core.repaso_espaciado import cargar


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def evaluar_respuesta(prediccion, esperada):
    """Criterio estricto: exactitud normalizada, no equivalencia semántica."""
    return bool(normalizar(esperada)) and normalizar(prediccion) == normalizar(esperada)


def ejecutar(ruta_fichas, responder, limite=5):
    """Evalúa sin modificar fichas ni entrenar; solo usa respuestas aprobadas."""
    fichas = cargar(Path(ruta_fichas))
    resultados = []
    for ficha in fichas[:max(0, min(20, limite))]:
        try:
            salida = str(responder(ficha["pregunta"]))
            correcto = evaluar_respuesta(salida, ficha["respuesta"])
            resultados.append({"pregunta": ficha["pregunta"], "correcto": correcto,
                               "respuesta_modelo": salida[:300]})
        except Exception as exc:
            resultados.append({"pregunta": ficha["pregunta"], "correcto": False,
                               "error": type(exc).__name__})
    return resultados
