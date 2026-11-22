"""Catálogo y ejecución de herramientas autorizadas del núcleo compartido."""
import re
from dataclasses import dataclass
from threading import Lock

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


class DescargaGit:
    def __init__(self):
        self.cerrojo = Lock()
        self.trabajos = {}

    def consultar(self, orden, clave):
        with self.cerrojo:
            trabajo = self.trabajos.get(clave)
            if not trabajo:
                return {"respuesta": "No hay descargas Git en este chat."}
            if orden == "cancela descarga git" and trabajo["estado"] in {"en cola", "clonando", "verificando"}:
                trabajo["cancelar"] = True
                return {"respuesta": "Cancelación de Git solicitada."}
            return trabajo.get("resultado") or {"respuesta": f"Descarga Git: {trabajo['estado']}."}

    def iniciar(self, nucleo, clave, url):
        with self.cerrojo:
            if any(t.get("resultado") is None for t in self.trabajos.values()):
                return {"respuesta": "Ya hay una descarga Git en curso."}
            if len(self.trabajos) >= 32:
                self.trabajos.pop(next(iter(self.trabajos)))
            trabajo = self.trabajos[clave] = {"estado": "en cola", "cancelar": False}
            nucleo.ejecutor.submit(self._ejecutar, nucleo, url, trabajo)
        return {"respuesta": "Descarga Git en cola. Usa «Estado de descarga Git» o «Cancela descarga Git»."}

    def _ejecutar(self, nucleo, url, trabajo):
        def avanzar(fase):
            with self.cerrojo:
                if trabajo["cancelar"]:
                    raise InterruptedError("Descarga Git cancelada.")
                nucleo.exigir_permisos(*REPOSITORIO.permisos)
                if not nucleo.internet:
                    raise PermissionError("Permiso de internet desactivado.")
                trabajo["estado"] = fase

        resultado = _resultado(nucleo, url, avanzar)
        with self.cerrojo:
            trabajo["resultado"] = resultado
            trabajo["estado"] = "terminada"


def resolver(nucleo, pregunta, intencion, clave=None):
    if intencion in {"estado de descarga git", "cancela descarga git"}:
        nucleo.exigir_permisos("READ")
        return nucleo.descarga_git.consultar(intencion, clave)
    if not re.match(r"(?:descarga(?:me)?|clona|baja)\b", intencion):
        return None
    enlaces = [url.rstrip(".,!?") for url in re.findall(r"https?://[^\s<>]+", pregunta, flags=re.I)]
    explicito = bool(re.match(r"clona\b", intencion) or re.search(r"\brepositorios?\b", intencion))
    if not explicito:
        if (len(enlaces) != 1 or not enlaces[0].startswith("https://")
                or enlaces[0].casefold().endswith(".pdf") or re.search(r"\bpdf\b", intencion)):
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
    return nucleo.descarga_git.iniciar(nucleo, clave, enlaces[0])


def _resultado(nucleo, url, avanzar):
    try:
        datos = descargar(url, nucleo.estudio, avanzar=avanzar)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"respuesta": f"Descarga detenida. {exc}"}
    respuesta = f"Descargué {datos['repositorio']} y verifiqué el commit {datos['commit']}."
    if datos["archivos"]:
        respuesta += "\nArchivos y carpetas en la raíz\n" + "\n".join(datos["archivos"])
    if datos["readme"]:
        respuesta += "\nExtracto del README del repositorio\n" + datos["readme"]
    return {"respuesta": respuesta, "resultado_herramienta": datos}
