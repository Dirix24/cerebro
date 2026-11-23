"""Historiales separados con selección persistente y compatibilidad con JSONL anterior."""
from collections import OrderedDict, deque
from datetime import datetime, timezone
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
        self.temporales = OrderedDict()
        self.revisiones_temporales = {}
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
        if ruta.is_symlink() or (not ruta.is_file() and identificador not in self.temporales):
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

    def registrar_temporal(self, pregunta, respuesta):
        identificador = self.activa()
        turnos = self.temporales.setdefault(identificador, deque(maxlen=60))
        fecha = datetime.now(timezone.utc).isoformat()
        turnos.extend({"fecha": fecha, "rol": rol, "texto": texto[:4000], "temporal": True}
                     for rol, texto in (("usuario", pregunta), ("cerebro", respuesta)))
        self.revisiones_temporales[identificador] = uuid4().hex
        self.temporales.move_to_end(identificador)
        if len(self.temporales) > 32:
            anterior, _ = self.temporales.popitem(last=False)
            self.revisiones_temporales.pop(anterior, None)

    def quitar_temporal(self, identificador):
        self.temporales.pop(identificador, None)
        self.revisiones_temporales.pop(identificador, None)

    def turnos(self, identificador=None, *, incluir_temporales=True):
        activa = self.activa() if identificador is None else identificador
        guardados = consultar(self.ruta(activa), limite=60)
        temporales = self.temporales.get(activa, ()) if incluir_temporales else ()
        return sorted([*guardados, *temporales], key=lambda turno: str(turno.get("fecha", "")))[-60:]

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
        temporal = self.revisiones_temporales.get(activa)
        if temporal:
            version += ":" + temporal
        return {"activa": activa, "revision": version}

    def estado(self):
        version = self.version_activa()
        archivos = [ruta for ruta in self.carpeta.glob("*.jsonl")
                    if _ID.fullmatch(ruta.stem) and ruta.is_file() and not ruta.is_symlink()]
        archivos.sort(key=lambda ruta: ruta.stat().st_mtime, reverse=True)
        chats = [{"id": ruta.stem, "titulo": datetime.fromtimestamp(ruta.stat().st_ctime).strftime("Conversación · %d/%m %H:%M:%S")}
                 for ruta in archivos]
        original = self.ruta("original")
        if not original.is_symlink() and (original.is_file() or "original" in self.temporales):
            chats.append({"id": "original", "titulo": "Conversación anterior"})
        return {**version, "chats": chats, "turnos": self.turnos(version["activa"])}
