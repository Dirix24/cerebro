"""Historiales separados con selección persistente y compatibilidad con JSONL anterior."""
from datetime import datetime
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from uuid import uuid4

from core.historial_local import consultar

_ID = re.compile(r"[a-f0-9]{32}")


class Conversaciones:
    def __init__(self, datos):
        self.datos = Path(datos)
        self.carpeta = self.datos / "conversaciones"
        self.selector = self.carpeta / "activa"
        if self.carpeta.is_symlink() or self.selector.is_symlink():
            raise ValueError("El historial de conversaciones requiere un directorio local.")

    def ruta(self, identificador):
        if identificador == "original":
            return self.datos / "historial_cerebro.jsonl"
        if not isinstance(identificador, str) or not _ID.fullmatch(identificador):
            raise ValueError("Conversación desconocida.")
        return self.carpeta / (identificador + ".jsonl")

    def activa(self):
        try:
            identificador = self.selector.read_text(encoding="ascii").strip()
            ruta = self.ruta(identificador)
            if ruta.is_file() and not ruta.is_symlink():
                return identificador
        except (FileNotFoundError, ValueError):
            pass
        return "original"

    def seleccionar(self, identificador):
        ruta = self.ruta(identificador)
        if ruta.is_symlink() or not ruta.is_file():
            raise ValueError("La conversación ya no está disponible.")
        self.carpeta.mkdir(mode=0o700, parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=self.carpeta, mode="w", encoding="ascii", delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(identificador)
        try:
            temporal.replace(self.selector)
        finally:
            temporal.unlink(missing_ok=True)

    def nueva(self):
        self.carpeta.mkdir(mode=0o700, parents=True, exist_ok=True)
        identificador = uuid4().hex
        self.ruta(identificador).touch(mode=0o600, exist_ok=False)
        self.seleccionar(identificador)

    def version_activa(self):
        activa = self.activa()
        ruta = self.ruta(activa)
        version = ""
        if not ruta.is_symlink():
            try:
                datos = ruta.stat()
                version = f"{datos.st_mtime_ns}:{datos.st_size}"
            except FileNotFoundError:
                pass
        return {"activa": activa, "revision": version}

    def estado(self):
        version = self.version_activa()
        archivos = [ruta for ruta in self.carpeta.glob("*.jsonl")
                    if _ID.fullmatch(ruta.stem) and ruta.is_file() and not ruta.is_symlink()]
        archivos.sort(key=lambda ruta: ruta.stat().st_mtime, reverse=True)
        chats = [{"id": ruta.stem, "titulo": datetime.fromtimestamp(ruta.stat().st_ctime).strftime("Conversación · %d/%m %H:%M:%S")}
                 for ruta in archivos]
        if self.ruta("original").is_file() and not self.ruta("original").is_symlink():
            chats.append({"id": "original", "titulo": "Conversación anterior"})
        return {**version, "chats": chats, "turnos": consultar(self.ruta(version["activa"]), limite=60)}
