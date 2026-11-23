"""Consulta conservadora de un catálogo de referencias públicas incluido en el repositorio."""
from functools import lru_cache
import json
from pathlib import Path
import re

from core.respuestas_con_fuentes import normalizar, respuesta_clara


RUTA = Path(__file__).resolve().parents[1] / "data" / "referencias_publicas.json"
ALIAS = {
    "dns": "sistema de nombres de dominio",
    "codigo de barras qr": "codigo qr",
    "capacitor": "condensador electrico",
    "ciclo del agua": "ciclo hidrologico",
    "sistema de control de versiones": "control de versiones",
    "etiqueta nutricional": "etiqueta de informacion nutricional",
    "recursion en programacion": "recursion ciencias de computacion",
}


@lru_cache(maxsize=1)
def _catalogo():
    try:
        datos = json.loads(RUTA.read_text(encoding="utf-8"))
        if datos["version"] != 1 or len(datos["fichas"]) > 1000:
            return {}
        return {normalizar(ficha["tema"]): ficha for ficha in datos["fichas"]}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _una_edicion(a, b):
    """Admite una sustitución, inserción, eliminación o transposición."""
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 6:
        return False
    if len(a) > len(b):
        a, b = b, a
    diferencias = [indice for indice, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(a) != len(b):
        i = diferencias[0] if diferencias else len(a)
        return a[i:] == b[i + 1:]
    if len(diferencias) == 1:
        return True
    if len(diferencias) == 2:
        i, j = diferencias
        return j == i + 1 and a[i] == b[j] and a[j] == b[i]
    return False


def buscar(tema, *, pregunta=""):
    """Devuelve un extracto literal si el tema identifica una única ficha."""
    clave = normalizar(tema)
    clave = re.sub(r" (?:en palabras sencillas|en pocas palabras|por favor)$", "", clave)
    consulta = clave
    clave = ALIAS.get(clave, clave)
    catalogo = _catalogo()
    coincidencia = clave if clave in catalogo else None
    if coincidencia is None and clave:
        palabras = clave.split()
        plurales, erratas = [], []
        for titulo in catalogo:
            tokens = titulo.split()
            if len(palabras) != len(tokens):
                continue
            diferencias = [(a, b) for a, b in zip(palabras, tokens) if a != b]
            if all(len(b) >= 4 and a in {b + "s", b + "es"} for a, b in diferencias):
                plurales.append(titulo)
            elif len(diferencias) == 1 and _una_edicion(*diferencias[0]):
                erratas.append(titulo)
        candidatas = plurales or erratas
        if len(candidatas) == 1:
            coincidencia = candidatas[0]
    if coincidencia is None:
        return None
    ficha = catalogo[coincidencia]
    texto = ficha["texto"]
    if normalizar(pregunta).startswith("para que sirve "):
        frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", texto)
        funciones = r"\b(?:almacenar?|retener?|sirve|permite|se (?:utiliza|emplea|usa|aplica))\b"
        texto = next((frase for frase in frases if re.search(funciones, normalizar(frase))), texto)
    extracto = respuesta_clara(texto)
    url = f"https://es.wikipedia.org/w/index.php?oldid={ficha['revision']}"
    if coincidencia != consulta:
        extracto = f"Si te refieres a «{ficha['tema']}», {extracto[0].lower() + extracto[1:]}"
    return extracto, url
