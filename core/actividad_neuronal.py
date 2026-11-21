"""Telemetría local de Cerebro: eventos de estado sin contenido privado."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import config

ESTADOS = {"analizando", "aprendido", "investigando", "consolidado",
           "asociando", "observando", "error", "razonando", "recuperando", "creando", "verificado"}


def ruta_eventos():
    return Path(config.CEREBRO_HOME) / "data" / "actividad_neuronal.jsonl"


def registrar(estado, detalle=""):
    """No almacena prompts, respuestas ni recuerdos; solo tipo y etiqueta fija."""
    if estado not in ESTADOS:
        raise ValueError("Estado desconocido")
    if detalle not in {"mensaje", "respuesta", "memoria", "consulta", "fallo",
                       "herramienta", "inicio", "relacion"}:
        detalle = ""
    ruta = ruta_eventos()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    evento = {"estado": estado, "texto": detalle,
              "fecha": datetime.now(timezone.utc).isoformat()}
    fd = os.open(str(ruta), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(evento, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def publicar(estado, detalle):
    """Un fallo de telemetría no cancela una operación del núcleo."""
    try:
        registrar(estado, detalle)
    except OSError:
        pass


def ultimos(limite=120):
    try:
        limite = int(limite)
    except (TypeError, ValueError, OverflowError):
        return []
    if limite <= 0:
        return []
    ruta = ruta_eventos()
    try:
        if not ruta.is_file():
            return []
        # Leer solo los últimos 256 KB; tolerar desaparición del archivo.
        with ruta.open("rb") as f:
            f.seek(0, os.SEEK_END)
            tam = f.tell()
            f.seek(max(0, tam - 262144))
            if tam > 262144:
                f.readline()
            lineas = f.readlines()[-min(120, limite):]
    except (OSError, ValueError, TypeError):
        return []
    eventos = []
    for linea in lineas:
        try:
            evento = json.loads(linea)
            if isinstance(evento, dict) and evento.get("estado") in ESTADOS:
                eventos.append({"estado": evento["estado"],
                                "texto": evento.get("texto", "") if isinstance(evento.get("texto", ""), str) else "",
                                "fecha": evento.get("fecha", "")})
        except (ValueError, UnicodeDecodeError):
            continue
    return eventos
