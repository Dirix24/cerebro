"""Búsqueda acotada de documentos del propietario del escritorio."""
import os
from pathlib import Path
import re
import unicodedata

FORMATOS = {".txt", ".md", ".pdf", ".docx", ".csv", ".json"}


def _normalizar(texto):
    return "".join(caracter for caracter in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(caracter))


def buscar(nombre, hogar=None):
    if not re.fullmatch(r"[\w .()-]{2,130}", nombre) or not any(c.isalnum() for c in nombre):
        raise ValueError("Indica el nombre del documento, sin introducir una ruta.")
    tema = _normalizar(nombre)
    hogar = Path.home() if hogar is None else Path(hogar)
    coincidencias = []
    vistos = 0
    for carpeta in ("Documentos", "Documents", "Descargas", "Downloads"):
        raiz = hogar / carpeta
        if not raiz.is_dir() or raiz.is_symlink():
            continue
        for directorio, subdirectorios, archivos in os.walk(raiz):
            base = Path(directorio)
            subdirectorios[:] = sorted(d for d in subdirectorios
                                       if not d.startswith(".") and not (base / d).is_symlink()
                                       and len(base.relative_to(raiz).parts) < 5)
            vistos += 1
            for archivo in sorted(archivos):
                vistos += 1
                ruta = base / archivo
                if (not archivo.startswith(".") and ruta.suffix.lower() in FORMATOS
                        and tema in _normalizar(archivo) and not ruta.is_symlink() and ruta.is_file()):
                    coincidencias.append(ruta)
                if vistos >= 5000 or len(coincidencias) >= 12:
                    return _priorizar(coincidencias, tema)
            if vistos >= 5000:
                return _priorizar(coincidencias, tema)
    return _priorizar(coincidencias, tema)


def _priorizar(coincidencias, tema):
    exactas = [ruta for ruta in coincidencias if tema in (_normalizar(ruta.name), _normalizar(ruta.stem))]
    return exactas or coincidencias
