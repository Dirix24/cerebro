"""Medición histórica de Cerebro con conjuntos de preguntas aprobadas.

La evaluación no modifica pesos ni incorpora respuestas generadas al entrenamiento.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from core.autoevaluacion import ejecutar


def medir(ruta_fichas, responder, ruta_historial, limite=20):
    resultados = ejecutar(ruta_fichas, responder, limite=limite)
    if not resultados:
        return {"evaluadas": 0, "aciertos": 0, "precision": None, "variacion": None}
    ruta = Path(ruta_historial)
    if ruta.is_symlink():
        raise ValueError("No se admiten enlaces simbólicos")
    anterior = None
    if ruta.is_file():
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
            for linea in reversed(lineas):
                dato = json.loads(linea)
                if dato.get("evaluadas") == len(resultados):
                    anterior = dato.get("precision")
                    break
        except (OSError, ValueError, TypeError):
            anterior = None
    aciertos = sum(bool(x["correcto"]) for x in resultados)
    precision = round(aciertos / len(resultados), 4)
    resumen = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "evaluadas": len(resultados),
        "aciertos": aciertos,
        "precision": precision,
        "variacion": round(precision - anterior, 4) if isinstance(anterior, (float, int)) else None,
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(resumen, ensure_ascii=False) + "\n")
    return resumen
