"""Telemetría local de Cerebro: eventos de estado sin contenido privado."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import config

ESTADOS = {"analizando", "aprendido", "investigando", "consolidado",
           "asociando", "observando", "error"}


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


def ultimos(limite=120):
    ruta = ruta_eventos()
    if not ruta.is_file():
        return []
    # Limita lectura a últimos 256 KB; evita cargar un registro ilimitado.
    with ruta.open("rb") as f:
        f.seek(0, os.SEEK_END)
        tam = f.tell()
        f.seek(max(0, tam - 262144))
        if tam > 262144:
            f.readline()
        lineas = f.readlines()[-max(1, min(120, limite)):]
    eventos = []
    for linea in lineas:
        try:
            evento = json.loads(linea)
            if evento.get("estado") in ESTADOS:
                eventos.append(evento)
        except (ValueError, UnicodeDecodeError):
            continue
    return eventos
