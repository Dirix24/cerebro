"""Modo simbiótico: el SSD conserva identidad; el equipo aporta recursos.

Vinculación explícita, local y reversible. No explora la red ni instala servicios.
"""
import json
import os
from pathlib import Path

import config
from core.entorno_portatil import detectar_entorno, recomendar_tamano, verificar_almacenamiento

ARCHIVO = "huesped_autorizado.json"


def ruta_vinculo():
    return Path(config.CEREBRO_HOME) / "memory" / ARCHIVO


def identidad_equipo(info=None):
    """Descripción no única: no se usa como autenticación ni identificación remota."""
    info = info or detectar_entorno()
    return {"sistema": info["sistema"], "arquitectura": info["arquitectura"],
            "cpus_logicas": info["cpus_logicas"]}


def vincular_huesped(confirmado=False):
    """Solo vincula con confirmación humana explícita y SSD inicializado."""
    if not confirmado:
        raise PermissionError("Debes confirmar expresamente la vinculación.")
    verificar_almacenamiento()
    info = detectar_entorno()
    ruta = ruta_vinculo()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = {"version": 1, "equipo": identidad_equipo(info),
             "nota": "Autorización local; no es autenticación criptográfica."}
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)
    return estado_huesped()


def desvincular_huesped():
    verificar_almacenamiento()
    ruta = ruta_vinculo()
    if ruta.is_file():
        ruta.unlink()
        return True
    return False


def estado_huesped():
    verificar_almacenamiento()
    info = detectar_entorno()
    ruta = ruta_vinculo()
    autorizado = False
    if ruta.is_file() and not ruta.is_symlink():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            autorizado = datos.get("equipo") == identidad_equipo(info)
        except (ValueError, OSError, TypeError):
            pass
    return {"vinculado": autorizado, "equipo": identidad_equipo(info),
            "ram_bytes": info["ram_bytes"],
            "tamano_recomendado": recomendar_tamano(info["ram_bytes"]),
            "motor": info["motor"],
            "aviso": "Comparación orientativa; no verifica identidad única del equipo."}
