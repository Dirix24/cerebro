"""Repaso espaciado local de conocimientos aprobados por el usuario.

Los artículos descargados no se consideran respuestas verificadas automáticamente.
"""
import json
from datetime import date, timedelta
from pathlib import Path


def cargar(ruta):
    ruta = Path(ruta)
    if not ruta.exists() or ruta.is_symlink():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return datos if isinstance(datos, list) else []
    except (OSError, ValueError):
        return []


def guardar(ruta, tarjetas):
    ruta = Path(ruta)
    if ruta.is_symlink():
        raise ValueError("No se permiten enlaces simbólicos")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(tarjetas, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def anadir(ruta, pregunta, respuesta):
    pregunta, respuesta = pregunta.strip(), respuesta.strip()
    if not pregunta or not respuesta or len(pregunta) > 300 or len(respuesta) > 2000:
        raise ValueError("Pregunta o respuesta vacía o demasiado larga")
    tarjetas = cargar(ruta)
    if any(t["pregunta"].casefold() == pregunta.casefold() for t in tarjetas):
        raise ValueError("Esa pregunta ya existe")
    tarjetas.append({"pregunta": pregunta, "respuesta": respuesta,
                     "intervalo": 0, "aciertos": 0, "fecha": date.today().isoformat()})
    guardar(ruta, tarjetas)


def pendientes(ruta, hoy=None, limite=5):
    hoy = hoy or date.today()
    return [t for t in cargar(ruta) if date.fromisoformat(t["fecha"]) <= hoy][:max(0, limite)]


def calificar(ruta, pregunta, correcto, hoy=None):
    hoy = hoy or date.today()
    tarjetas = cargar(ruta)
    for t in tarjetas:
        if t["pregunta"].casefold() == pregunta.strip().casefold():
            t["aciertos"] = t["aciertos"] + 1 if correcto else 0
            t["intervalo"] = min(60, max(1, t["intervalo"] * 2)) if correcto else 1
            t["fecha"] = (hoy + timedelta(days=t["intervalo"])).isoformat()
            guardar(ruta, tarjetas)
            return t
    raise ValueError("Pregunta no encontrada")
