"""Recordatorios locales persistentes, consultados al abrir el chat.

No se envían notificaciones con Cerebro cerrado; no hay servicio de fondo.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import config


def _ruta(ruta=None):
    return Path(ruta or (Path(config.CEREBRO_HOME) / "data" / "recordatorios.json"))


def listar(ruta=None, ahora=None):
    archivo = _ruta(ruta)
    if not archivo.is_file():
        return []
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    if not isinstance(datos, list):
        raise ValueError("Formato de recordatorios inválido")
    return datos


def crear(fecha_iso, texto, ruta=None):
    if not isinstance(texto, str) or not 1 <= len(texto.strip()) <= 500:
        raise ValueError("Texto de 1 a 500 caracteres requerido")
    try:
        fecha = datetime.fromisoformat(fecha_iso)
    except ValueError as exc:
        raise ValueError("Usa fecha ISO con zona horaria: 2027-01-20T10:00:00+01:00") from exc
    if fecha.tzinfo is None or fecha.utcoffset() is None:
        raise ValueError("Incluye la zona horaria, por ejemplo +01:00")
    if fecha <= datetime.now(timezone.utc):
        raise ValueError("La fecha debe ser futura")
    archivo = _ruta(ruta)
    datos = listar(archivo)
    if len(datos) >= 1000:
        raise ValueError("Límite de 1000 recordatorios")
    registro = {"id": uuid4().hex[:12], "fecha": fecha.isoformat(),
                "texto": texto.strip(), "completado": False}
    datos.append(registro)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    temporal = archivo.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(archivo)
    return registro


def pendientes(ruta=None, ahora=None):
    instante = ahora or datetime.now(timezone.utc)
    return [x for x in listar(ruta) if not x["completado"]
            and datetime.fromisoformat(x["fecha"]) <= instante]
