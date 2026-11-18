"""Planificador local de recordatorios, optativo y sin dependencias de IA.

Se mantiene activo únicamente mientras corre este proceso. No crea servicios
del sistema ni abre red. Marca avisos como entregados para no repetirlos.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from core.recordatorios_locales import _ruta, listar


def revisar(archivo=None, ahora=None, notificar=None):
    ruta = _ruta(archivo)
    instante = ahora or datetime.now(timezone.utc)
    datos = listar(ruta)
    avisados = []
    for tarea in datos:
        if tarea.get("completado") or tarea.get("notificado"):
            continue
        if datetime.fromisoformat(tarea["fecha"]) > instante:
            continue
        mensaje = "Cerebro: recordatorio - " + tarea["texto"]
        if notificar:
            notificar(mensaje)
        else:
            print(mensaje, flush=True)
        tarea["notificado"] = True
        avisados.append(tarea["id"])
    if avisados:
        temporal = ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        temporal.replace(ruta)
    return avisados


def main():
    ap = argparse.ArgumentParser(description="Recordatorios Cerebro; proceso local voluntario")
    ap.add_argument("--una-vez", action="store_true")
    ap.add_argument("--intervalo", type=int, default=30)
    args = ap.parse_args()
    if not 5 <= args.intervalo <= 3600:
        ap.error("Intervalo entre 5 y 3600 segundos")
    while True:
        revisar()
        if args.una_vez:
            break
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
