"""Respuestas factuales conservadoras a partir de fichas y corpus local.

Sin red, sin IA externa y sin inventar información. No confunde similitud con verdad.
"""
import re
import unicodedata

ALIAS = {"ia": "inteligencia artificial", "i a": "inteligencia artificial"}
VACIAS = {"que", "es", "son", "un", "una", "el", "la", "los", "las", "de", "del", "en", "por"}


def normalizar(texto):
    texto = texto.casefold().replace("ñ", "\ufff0")
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto)
                    if not unicodedata.combining(c)).replace("\ufff0", "ñ")
    return " ".join(re.findall(r"\w+", texto))


def concepto_definicion(pregunta):
    m = re.fullmatch(r"\s*¿?\s*(?:qué|que)\s+(?:es|son)\s+(.+?)\s*\??\s*",
                     pregunta, re.IGNORECASE)
    if not m:
        return None
    concepto = normalizar(m.group(1))
    concepto = re.sub(r"^(?:un|una|el|la|los|las)\s+", "", concepto)
    return ALIAS.get(concepto, concepto)


def _extraer_respuesta(documento, concepto):
    """Solo acepta un par de pregunta-respuesta sobre el concepto consultado."""
    patron = re.compile(r"usuario:\s*(.*?)\s*\n\s*cerebro:\s*(.*?)(?=\n\s*usuario:|\Z)",
                        re.IGNORECASE | re.DOTALL)
    for pregunta, respuesta in patron.findall(documento):
        if concepto_definicion(pregunta) == concepto:
            respuesta = respuesta.strip()
            if respuesta and len(respuesta) <= 1200:
                return respuesta
    return None


def responder_definicion(pregunta, buscador=None, buscar_hechos=None):
    """Devuelve respuesta y fuente, o None si falta evidencia local."""
    concepto = concepto_definicion(pregunta)
    if not concepto:
        return None
    if buscar_hechos is None:
        from core.conocimiento import respuesta_exacta
        buscar_hechos = respuesta_exacta
    variantes = [f"¿Qué es {concepto}?", f"¿Qué es un {concepto}?",
                 f"¿Qué es una {concepto}?", f"¿Qué son {concepto}?"]
    for variante in variantes:
        dato = buscar_hechos(variante)
        if dato:
            return dato["respuesta"][:1200], dato["fuente"]
    if buscador is None:
        from core.local_search import buscar
        buscador = buscar
    # Una coincidencia de palabras no es suficiente: verificar la pregunta del documento.
    for texto, origen in buscador(concepto, limite=10):
        respuesta = _extraer_respuesta(texto, concepto)
        if respuesta:
            return respuesta, origen
    return None
