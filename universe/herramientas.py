"""Catálogo y ejecución de herramientas autorizadas del núcleo compartido."""
import re
from dataclasses import dataclass

from core.github_local import identificar_repositorio
from core.repositorio_descargado import descargar


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    descripcion: str
    parametros: tuple
    permisos: tuple
    requiere_internet: bool


REPOSITORIO = Herramienta("descargar_repositorio", "Descarga e inspección estática de GitHub",
                          ("url",), ("READ", "WRITE"), True)


def resolver(nucleo, pregunta, intencion):
    if not re.match(r"(?:descarga(?:me)?|clona|baja)\b", intencion):
        return None
    enlaces = [url.rstrip(".,!?") for url in re.findall(r"https?://[^\s<>]+", pregunta, flags=re.I)]
    explicito = bool(re.match(r"clona\b", intencion) or re.search(r"\brepositorios?\b", intencion))
    if not explicito:
        if len(enlaces) != 1 or not enlaces[0].startswith("https://"):
            return None
        try:
            identificar_repositorio(enlaces[0])
        except ValueError:
            return None
    if len(enlaces) != 1:
        return {"respuesta": "Indica un único enlace HTTPS al repositorio público de GitHub."}
    if REPOSITORIO.requiere_internet and not nucleo.internet:
        raise PermissionError("El permiso de internet de esta sesión está desactivado.")
    nucleo.exigir_permisos(*REPOSITORIO.permisos)
    try:
        datos = descargar(enlaces[0], nucleo.estudio)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"respuesta": f"Descarga detenida. {exc}"}
    respuesta = f"Descargué {datos['repositorio']} y verifiqué el commit {datos['commit']}."
    if datos["archivos"]:
        respuesta += "\nArchivos y carpetas en la raíz\n" + "\n".join(datos["archivos"])
    if datos["readme"]:
        respuesta += "\nExtracto del README del repositorio\n" + datos["readme"]
    return {"respuesta": respuesta, "resultado_herramienta": datos}
