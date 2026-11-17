"""Evolución adaptativa local: registra resultados y ajusta el esfuerzo diario.

No simula neuroplasticidad biológica ni modifica la arquitectura en caliente.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_REGISTROS = 90


def leer_historial(ruta):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    return datos[-MAX_REGISTROS:] if isinstance(datos, list) else []


def pasos_adaptativos(pasos_base, historial, minimo=5, maximo=1000):
    """Aumenta suavemente el esfuerzo tras mejoras y reduce tras retrocesos.

    No altera la tasa de aprendizaje ni la configuración de pesos.
    """
    if not 1 <= pasos_base <= maximo:
        raise ValueError("pasos_base fuera de rango")
    ultimos = [r for r in historial[-5:] if r.get("resultado") in ("aceptado", "revertido")]
    if not ultimos:
        return pasos_base
    if ultimos[-1]["resultado"] == "revertido":
        return max(minimo, pasos_base // 2)
    exitos = sum(r["resultado"] == "aceptado" for r in ultimos)
    if exitos >= 3:
        return min(maximo, max(pasos_base + 1, round(pasos_base * 1.25)))
    return pasos_base


def registrar(ruta, resultado, pasos, detalle=""):
    if resultado not in ("aceptado", "revertido"):
        raise ValueError("resultado inválido")
    ruta = Path(ruta)
    if ruta.is_symlink():
        raise ValueError("No se permiten enlaces simbólicos")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    registros = leer_historial(ruta)
    registros.append({
        "fecha": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
        "pasos": int(pasos),
        "detalle": str(detalle)[:300],
    })
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(registros[-MAX_REGISTROS:], ensure_ascii=False, indent=2),
                        encoding="utf-8")
    temporal.replace(ruta)
