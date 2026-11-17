"""Enrutamiento conservador entre herramientas existentes de Cerebro.

Las órdenes que escriben archivos nunca se activan por texto libre.
"""
import re


def seleccionar(texto):
    texto = texto.strip()
    if texto.startswith("/"):
        return "comando"
    if re.match(r"(?i)^\s*[¿]?\s*(?:busca(?:r)?|consulta(?:r)?)\s+(?:en\s+)?(?:el\s+)?(?:corpus|biblioteca)\s*[: ]", texto):
        return "busqueda_local"
    if re.match(r"(?i)^\s*[¿]?\s*(?:qué|que|quién|quien)\s+(?:es|fue|son)\s+.{3,}", texto):
        return "conocimiento"
    return "modelo"
