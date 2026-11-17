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


def explicar_seleccion(texto):
    """Describe la decisión de enrutamiento sin ejecutar herramientas."""
    ruta = seleccionar(texto)
    razones = {
        "comando": "Orden explícita: requiere la ejecución del comando solicitado",
        "busqueda_local": "Petición de consultar el corpus local",
        "conocimiento": "Pregunta factual: buscar primero una fuente local",
        "modelo": "No se identificó herramienta determinista ni fuente específica",
    }
    return {"motor": ruta, "razon": razones[ruta],
            "requiere_confirmacion_para_escritura": ruta == "comando"}
