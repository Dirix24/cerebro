"""Planificador acotado para búsquedas por metadatos y acciones de navegador."""
from dataclasses import dataclass
import re
from urllib.parse import urlencode, urlsplit

from core.documentos_usuario import TIPOS, _normalizar


@dataclass(frozen=True)
class Paso:
    herramienta: str
    argumentos: dict


def url_navegable(texto):
    try:
        ruta = urlsplit(texto)
        puerto = ruta.port
    except ValueError:
        return None
    if (len(texto) > 2048 or any(c.isspace() or ord(c) < 32 or c == "\\" for c in texto)
            or ruta.scheme not in {"https", "http"} or not ruta.hostname
            or ruta.username is not None or ruta.password is not None
            or puerto not in {None, 80, 443}):
        return None
    return texto


def elaborar(pregunta):
    texto = re.sub(r"^cerebro[,\s]+", "", pregunta.strip(" ¡!¿?"), flags=re.I)
    normal = _normalizar(texto.rstrip("."))
    youtube = re.fullmatch(
        r"(?:abre youtube (?:y|e) busca (.+)|busca (.+) en youtube)", normal)
    if youtube:
        termino = (youtube[1] or youtube[2]).strip()
        if not re.fullmatch(r"[\w .,'()-]{2,120}", termino):
            raise ValueError("Indica un tema de búsqueda breve para YouTube.")
        return [Paso("abrir_web", {"url": "https://www.youtube.com/results?" + urlencode({"search_query": termino})})]
    enlace = re.fullmatch(r"(abre|analiza)\s+(?:(?:este enlace|el enlace)\s+)?(https?://\S+)", texto, re.I)
    if enlace:
        url = url_navegable(enlace[2])
        if url is None:
            raise ValueError("Usa un enlace HTTP o HTTPS completo, sin credenciales.")
        return [Paso("analizar_web" if enlace[1].casefold() == "analiza" else "abrir_web", {"url": url})]
    if normal in {"abre este enlace", "abre el enlace", "analiza este enlace", "analiza el enlace"}:
        return [Paso("analizar_web" if normal.startswith("analiza") else "abrir_web", {})]
    if normal in {"que puedes hacer en mi ordenador", "que puedes hacer en mi equipo"}:
        return [Paso("capacidades", {})]

    contenido = re.fullmatch(r"busca (?:en el contenido de (?:mis |los )?documentos|archivos que contengan)"
                              r"[: ]+(.+)", normal)
    if contenido:
        return [Paso("buscar_contenido", {"termino": contenido[1]})]

    resumen = re.fullmatch(r"busca (?:mis )?pdfs? de ([\w .()-]{1,100}), abre el mas reciente, "
                           r"(?:hazme un resumen|resumelo) y guardalo en una carpeta", normal)
    if resumen:
        return [Paso("buscar_archivos", {"tipo": "pdf", "nombre": resumen[1], "reciente": True}),
                Paso("abrir_archivo", {}), Paso("resumir_pdf", {}), Paso("guardar_resumen", {})]

    if normal in {"busca una aplicacion para editar este archivo", "que aplicaciones abren este archivo"}:
        return [Paso("compatibilidad", {})]

    if normal in {"abre blender y busca mi ultimo proyecto", "abre mi ultimo proyecto de blender"}:
        return [Paso("buscar_archivos", {"tipo": "blender", "reciente": True}),
                Paso("abrir_archivo", {})]

    extension = re.fullmatch(
        r"(busca(?:me)?|encuentra|abre) (?:(?:mis|mi|el|los|un) )?"
        r"(?:archivos?|documentos?) (?:con extension )?\.?([a-z0-9]{2,8})(?: de (.+))?",
        normal,
    )
    if extension:
        verbo, formato, nombre = extension.groups()
        sufijo = "." + formato
        tipo = next((tipo for tipo, formatos in TIPOS.items() if sufijo in formatos), None)
        if tipo:
            pasos = [Paso("buscar_archivos", {"tipo": tipo, "nombre": nombre or "", "extensiones": {sufijo}})]
            if verbo == "abre":
                pasos.append(Paso("abrir_archivo", {}))
            return pasos

    archivos = re.fullmatch(
        r"(busca(?:me)?|encuentra|abre|reproduce)\s+"
        r"(?:(?:todos?|todas|mis|mi|el|la|los|las|un|una|este)\s+)*"
        r"(pdfs?|documentos|fotos?|imagenes?|videos?|proyecto de blender|archivos? de blender)"
        r"(?:\s+(.+))?", normal)
    if not archivos:
        return []
    verbo, formato, resto = archivos.groups()
    tipo = ("pdf" if formato.startswith("pdf") else "videos" if formato.startswith("video")
            else "blender" if "blender" in formato else "documentos" if formato == "documentos" else "fotos")
    criterio = {}
    nombre = resto or ""
    if nombre.endswith(" esta semana") or nombre == "esta semana":
        criterio["periodo"] = "semana"
        nombre = nombre.removesuffix("esta semana").strip()
    elif nombre.endswith(" ayer") or nombre == "ayer":
        criterio["periodo"] = "ayer"
        nombre = nombre.removesuffix("ayer").strip()
    if "descargue" in nombre:
        criterio["descargas"] = True
        nombre = re.sub(r"(?:que )?descargue\b", "", nombre).strip()
    nombre = re.sub(r"(?:que )?modifique$", "", nombre).strip()
    nombre = re.sub(r"^de\s+", "", nombre)
    pasos = [Paso("buscar_archivos", {"tipo": tipo, "nombre": nombre, **criterio})]
    if verbo in {"abre", "reproduce"}:
        pasos.append(Paso("abrir_archivo", {}))
    return pasos
