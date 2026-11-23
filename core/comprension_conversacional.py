"""Normalización conservadora de preguntas informativas."""
import re

from core.respuestas_con_fuentes import concepto_definicion, normalizar


def preparar(pregunta):
    texto = normalizar(pregunta)
    # Conserva la consulta original cuando ya está bien segmentada.
    if texto.startswith("ques "):
        return pregunta, "¿Qué quieres decir con «" + texto.removeprefix("ques ")[:60] + "»?"
    fusion = re.fullmatch(r"que es([a-zñ]{3,})", texto)
    if fusion and not texto.startswith("que est"):
        return "¿Qué es " + fusion[1] + "?", None
    return pregunta, None


def pide_explicacion(pregunta):
    texto = normalizar(pregunta)
    return bool(concepto_definicion(texto) or re.match(r"^(?:explicame|cuentame|por que|como funciona) ", texto))
