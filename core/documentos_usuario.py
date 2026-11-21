"""Búsqueda acotada de documentos del propietario del escritorio."""
import os
from pathlib import Path
import re
import unicodedata

FORMATOS = {".txt", ".md", ".pdf", ".docx", ".csv", ".json"}


def _normalizar(texto):
    return "".join(caracter for caracter in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(caracter))


def carpetas(hogar=None):
    hogar = Path.home() if hogar is None else Path(hogar)
    return tuple(hogar / nombre for nombre in ("Documentos", "Documents", "Descargas", "Downloads")
                 if (hogar / nombre).is_dir() and not (hogar / nombre).is_symlink())


def permitido(ruta, hogar=None):
    if not ruta.is_absolute() or ruta.suffix.lower() not in FORMATOS:
        return False
    try:
        real = ruta.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if real != ruta or not real.is_file():
        return False
    for raiz in carpetas(hogar):
        if real.is_relative_to(raiz):
            partes = real.relative_to(raiz).parts
            return len(partes) <= 6 and all(not parte.startswith(".") for parte in partes)
    return False


def buscar(nombre, hogar=None):
    if not re.fullmatch(r"[\w .()-]{2,130}", nombre) or not any(c.isalnum() for c in nombre):
        raise ValueError("Indica el nombre del documento, sin introducir una ruta.")
    tema = _normalizar(nombre)
    coincidencias = []
    vistos = 0
    for raiz in carpetas(hogar):
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
