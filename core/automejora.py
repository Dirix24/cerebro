"""Automejora prudente: inspecciona métricas y propone tareas, nunca ejecuta código."""
import json
from datetime import datetime, timezone
from pathlib import Path

from core.evolucion_adaptativa import leer_historial


def _jsonl(ruta, limite=30):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return []
    salida = []
    for linea in ruta.read_text(encoding="utf-8").splitlines()[-limite:]:
        try:
            dato = json.loads(linea)
            if isinstance(dato, dict):
                salida.append(dato)
        except (ValueError, TypeError):
            continue
    return salida


def analizar(raiz):
    raiz = Path(raiz)
    progreso = _jsonl(raiz / "data" / "historial_evaluaciones.jsonl")
    errores = _jsonl(raiz / "data" / "errores_aprendizaje.jsonl")
    evolucion = leer_historial(raiz / "data" / "aprendizaje_internet" / "evolucion.json")
    tareas = []
    ultima = progreso[-1] if progreso else None
    if ultima is None:
        tareas.append({"prioridad": 1, "objetivo": "Crear evaluación base con fichas aprobadas",
                       "accion": "Registrar fichas y ejecutar /progreso", "automatica": False})
    elif isinstance(ultima.get("precision"), (int, float)) and ultima["precision"] < 0.8:
        tareas.append({"prioridad": 1, "objetivo": "Mejorar respuestas en preguntas aprobadas",
                       "accion": "Revisar errores, ampliar ejemplos aprobados y volver a evaluar",
                       "automatica": False})
    pendientes = sum(x.get("estado") == "pendiente_revision" for x in errores)
    if pendientes:
        tareas.append({"prioridad": 2, "objetivo": "Revisar correcciones registradas",
                       "accion": f"Verificar {pendientes} correcciones antes de usarlas para entrenar",
                       "automatica": False})
    if evolucion and evolucion[-1].get("resultado") == "revertido":
        tareas.append({"prioridad": 1, "objetivo": "Investigar regresión del entrenamiento",
                       "accion": "Revisar corpus, validación y métricas antes de reentrenar",
                       "automatica": False})
    if not tareas:
        tareas.append({"prioridad": 3, "objetivo": "Mantener calidad",
                       "accion": "Continuar evaluando con preguntas nuevas verificadas",
                       "automatica": False})
    return {"fecha": datetime.now(timezone.utc).isoformat(), "modo": "solo propuestas",
            "evaluaciones": len(progreso), "correcciones_pendientes": pendientes,
            "entrenamientos_registrados": len(evolucion),
            "propuestas": sorted(tareas, key=lambda x: x["prioridad"])}


def generar(raiz, salida):
    informe = analizar(raiz)
    salida = Path(salida)
    if salida.is_symlink():
        raise ValueError("No se escriben enlaces simbólicos")
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = salida.with_suffix(".tmp")
    temporal.write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
    temporal.replace(salida)
    return informe
