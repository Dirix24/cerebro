"""Registro local de errores reconocidos, sin autoaprobar correcciones."""
import json
from datetime import datetime, timezone
from pathlib import Path


def registrar(ruta, pregunta, respuesta_correcta, respuesta_erronea=""):
    pregunta = pregunta.strip()
    respuesta_correcta = respuesta_correcta.strip()
    if not pregunta or not respuesta_correcta:
        raise ValueError("Se requiere pregunta y respuesta corregida")
    if len(pregunta) > 300 or len(respuesta_correcta) > 2000:
        raise ValueError("Entrada demasiado larga")
    ruta = Path(ruta)
    if ruta.is_symlink():
        raise ValueError("No se permiten enlaces simbólicos")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    registro = {"fecha": datetime.now(timezone.utc).isoformat(),
                "pregunta": pregunta, "correccion": respuesta_correcta,
                "respuesta_erronea": respuesta_erronea[:2000], "estado": "pendiente_revision"}
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def pendientes(ruta, limite=20):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return []
    datos = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            dato = json.loads(linea)
            if dato.get("estado") == "pendiente_revision":
                datos.append(dato)
        except (ValueError, AttributeError):
            continue
    return datos[-max(0, limite):] if limite else []
