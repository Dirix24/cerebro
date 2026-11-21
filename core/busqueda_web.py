"""Búsqueda web opcional que devuelve referencias, sin generar respuestas."""
import re
from html import unescape
from urllib.parse import urlencode, urlsplit

from core.fuentes_publicas import consultar_json


def buscar(tema, clave, *, abrir=None):
    if not clave:
        raise ValueError("Para búsqueda web general, configura CEREBRO_BRAVE_API_KEY.")
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode({
        "q": tema, "count": 5, "search_lang": "es", "safesearch": "moderate",
    })
    datos = consultar_json(url, {"X-Subscription-Token": clave}, abrir=abrir)
    if not isinstance(datos, dict) or not isinstance(datos.get("web", {}), dict):
        raise ValueError("El buscador devolvió un formato inesperado.")
    resultados = datos.get("web", {}).get("results", [])
    if not isinstance(resultados, list):
        raise ValueError("El buscador devolvió un formato inesperado.")
    referencias = []
    for resultado in resultados[:5]:
        if not isinstance(resultado, dict):
            continue
        enlace, titulo = resultado.get("url"), resultado.get("title")
        if not isinstance(enlace, str) or not isinstance(titulo, str) or re.search(r"\s", enlace):
            continue
        try:
            destino = urlsplit(enlace)
            if destino.scheme != "https" or not destino.hostname or destino.username or destino.password:
                continue
        except ValueError:
            continue
        contexto = resultado.get("description")
        extracto = unescape(re.sub(r"<[^>]+>", "", contexto))[:400] if isinstance(contexto, str) else ""
        referencias.append((unescape(re.sub(r"<[^>]+>", "", titulo))[:180], extracto, enlace))
    return referencias
