"""Interpretación conservadora de peticiones en español.

No usa servicios ni modelos externos. Solo enruta consultas inequívocas;
acciones físicas, escrituras y ambigüedades requieren diálogo explícito.
"""
import re
import unicodedata


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn").strip()


def interpretar(texto):
    t = _normalizar(texto)
    if not t or texto.lstrip().startswith("/"):
        return None
    if re.search(r"\b(placa|arduino|esp32|usb|dispositivos conectados|puertos serie)\b", t):
        if re.search(r"\b(busca|detecta|revisa|mira|hay|tengo|conectad[oa]s?|enumera|lista)\b", t):
            return {"accion": "usb", "requiere_confirmacion": False}
    if "github" in t or "repositorio" in t:
        if re.search(r"\b(corrige|modifica|sube|publica|commit|fusiona|merge|borra)\b", t):
            return {"accion": "github_escritura", "requiere_confirmacion": True}
        if re.search(r"\b(errores?|fallos?|incidencias?|issues?|problemas?)\b", t):
            return {"accion": "github_errores", "requiere_confirmacion": False}
        return {"accion": "github_estado", "requiere_confirmacion": False}
    if re.search(r"\b(recordatorios|tareas pendientes|que tengo pendiente)\b", t):
        return {"accion": "recordatorios", "requiere_confirmacion": False}
    if re.search(r"\b(recuerdame|avisame|ponme un recordatorio)\b", t):
        return {"accion": "recordatorio_nuevo", "requiere_confirmacion": True}
    if re.search(r"\b(camara|foto|imagen|fotografia)\b", t) and re.search(
            r"\b(mira|enciende|captura|saca|haz|analiza|ve)\b", t):
        return {"accion": "camara", "requiere_confirmacion": True}
    return None
