"""Ejemplos de entrenamiento aprobados explícitamente, almacenados localmente."""
import json
from datetime import datetime, timezone
from pathlib import Path


def aprobar(ruta, pregunta, respuesta, *, procedencia=None):
    if not all(isinstance(t, str) and 1 <= len(t.strip()) <= 2000
               for t in (pregunta, respuesta)):
        raise ValueError("Pregunta y respuesta deben tener entre 1 y 2000 caracteres")
    registro = {"pregunta": pregunta.strip(), "respuesta": respuesta.strip(),
                "aprobado": True, "fecha": datetime.now(timezone.utc).isoformat()}
    if procedencia is not None:
        registro["procedencia"] = procedencia
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def listar(ruta, limite=20):
    if not isinstance(limite, int) or not 1 <= limite <= 100:
        raise ValueError("Límite fuera de rango")
    origen = Path(ruta)
    if not origen.is_file():
        return []
    with origen.open("rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - 1_000_000))
        if tam > 1_000_000:
            f.readline()
        lineas = f.readlines()
    ejemplos = []
    for linea in lineas[-limite:]:
        if len(linea) > 6000:
            continue
        try:
            obj = json.loads(linea)
        except (ValueError, UnicodeError):
            continue
        if (isinstance(obj, dict) and obj.get("aprobado") is True
                and isinstance(obj.get("pregunta"), str)
                and isinstance(obj.get("respuesta"), str)):
            ejemplos.append(obj)
    return ejemplos
