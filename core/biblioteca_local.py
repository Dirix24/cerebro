"""Indexación documental sencilla, sin ejecutar archivos ni extraer datos remotos."""
from pathlib import Path
import re

EXTENSIONES = {".txt", ".md"}
MAX_ARCHIVO = 1_000_000


def leer_documento(ruta, raiz):
    raiz = Path(raiz).resolve()
    archivo = Path(ruta).resolve()
    if not archivo.is_relative_to(raiz):
        raise ValueError("Ruta fuera de la biblioteca")
    if archivo.suffix.lower() not in EXTENSIONES or not archivo.is_file():
        raise ValueError("Solo se admiten archivos TXT y Markdown")
    if archivo.stat().st_size > MAX_ARCHIVO:
        raise ValueError("Archivo demasiado grande")
    return archivo.read_text(encoding="utf-8")


def buscar_en_biblioteca(consulta, raiz, limite=5):
    raiz = Path(raiz).resolve()
    if not raiz.is_dir():
        return []
    terminos = set(re.findall(r"\w+", consulta.casefold()))
    if not terminos:
        return []
    resultados = []
    for archivo in raiz.rglob("*"):
        if archivo.is_symlink() or not archivo.is_file() or archivo.suffix.lower() not in EXTENSIONES:
            continue
        try:
            contenido = leer_documento(archivo, raiz)
        except (OSError, UnicodeError, ValueError):
            continue
        puntuacion = sum(contenido.casefold().count(t) for t in terminos)
        if puntuacion:
            resultados.append({"archivo": str(archivo.relative_to(raiz)),
                               "puntuacion": puntuacion, "fragmento": contenido[:350]})
    return sorted(resultados, key=lambda x: (-x["puntuacion"], x["archivo"]))[:limite]
