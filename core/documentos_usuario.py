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
    if not ruta.is_absolute() or not any(ruta.suffix.lower() in extensiones for extensiones in TIPOS.values()):
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


TIPOS = {
    "pdf": {".pdf"},
    "documentos": FORMATOS | {".odt", ".rtf"},
    "fotos": {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"},
    "videos": {".mp4", ".mkv", ".webm", ".mov", ".avi"},
    "blender": {".blend"},
}


def buscar_filtrado(tipo, nombre="", periodo=None, descargas=False, hogar=None, *, extensiones=None):
    """Consulta metadatos dentro de ámbitos existentes, con inventario acotado."""
    from datetime import datetime, time, timedelta
    from difflib import SequenceMatcher

    extensiones = TIPOS[tipo] if extensiones is None else TIPOS[tipo] & extensiones
    tema = _normalizar(nombre)
    if tema and not re.fullmatch(r"[\w .()-]{1,130}", tema):
        raise ValueError("Escribe parte del nombre del archivo, sin rutas.")
    hoy = datetime.now().astimezone().date()
    fecha_inicial = (hoy - timedelta(days=hoy.weekday()) if periodo == "semana"
                     else hoy - timedelta(days=1) if periodo == "ayer" else hoy)
    inicial = datetime.combine(fecha_inicial, time.min).timestamp() if periodo else None
    final = datetime.combine(hoy, time.min).timestamp() if periodo == "ayer" else None
    resultados = []
    vistos = 0
    limitado = False
    for raiz in carpetas(hogar):
        if descargas and raiz.name not in {"Descargas", "Downloads"}:
            continue
        for directorio, subdirectorios, archivos in os.walk(raiz):
            base = Path(directorio)
            subdirectorios[:] = sorted(d for d in subdirectorios
                                       if not d.startswith(".") and not (base / d).is_symlink()
                                       and len(base.relative_to(raiz).parts) < 5)
            vistos += 1
            for archivo in sorted(archivos):
                vistos += 1
                if vistos > 5000:
                    break
                ruta = base / archivo
                if ruta.suffix.lower() not in extensiones or not permitido(ruta, hogar):
                    continue
                try:
                    fecha = ruta.stat().st_mtime
                except OSError:
                    continue
                if (inicial is not None and fecha < inicial) or (final is not None and fecha >= final):
                    continue
                titulo = _normalizar(ruta.stem)
                coincidencia = 2 if not tema or tema in titulo else 0
                if not coincidencia and len(tema) >= 5:
                    candidatos = [titulo, *re.findall(r"\w+", titulo)]
                    coincidencia = int(any(SequenceMatcher(None, tema, t).ratio() >= .8 for t in candidatos))
                if coincidencia:
                    resultados.append((coincidencia, fecha, ruta))
            if vistos >= 5000:
                limitado = True
                break
        if limitado:
            break
    resultados.sort(key=lambda dato: (-dato[0], -dato[1], str(dato[2])))
    return [ruta for _, _, ruta in resultados[:12]], limitado or len(resultados) > 12


def buscar_por_contenido(termino, hogar=None):
    """Busca texto explícito en un conjunto acotado de TXT y Markdown autorizados."""
    objetivo = _normalizar(termino.strip())
    if len(objetivo) < 3 or len(objetivo) > 120:
        raise ValueError("Indica entre 3 y 120 caracteres para buscar en el contenido.")
    rutas, limitado = buscar_filtrado("documentos", hogar=hogar, extensiones={".txt", ".md"})
    resultados = []
    for ruta in rutas:
        if not permitido(ruta, hogar):
            continue
        try:
            with ruta.open("rb") as archivo:
                datos = archivo.read(64 * 1024 + 1)
        except OSError:
            limitado = True
            continue
        if len(datos) > 64 * 1024:
            limitado = True
        if objetivo in _normalizar(datos[:64 * 1024].decode("utf-8", errors="replace")):
            resultados.append(ruta)
    return resultados, limitado
