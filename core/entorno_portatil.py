"""Detección conservadora de recursos para ejecutar Cerebro desde un SSD.

No cambia automáticamente el modelo ni modifica checkpoints.
"""
import os
import platform
import shutil
from pathlib import Path

import config


def ram_total_bytes():
    """RAM física aproximada; None cuando el sistema no la expone."""
    try:
        if os.path.isfile("/proc/meminfo"):
            with open("/proc/meminfo", encoding="ascii") as archivo:
                for linea in archivo:
                    if linea.startswith("MemTotal:"):
                        return int(linea.split()[1]) * 1024
        if hasattr(os, "sysconf"):
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, TypeError):
        pass
    return None


def detectar_entorno(ruta=None):
    """Devuelve capacidades observables, sin prometer aceleración GPU."""
    destino = Path(ruta or config.CEREBRO_HOME).expanduser().resolve()
    existente = destino
    while not existente.exists() and existente != existente.parent:
        existente = existente.parent
    disco = shutil.disk_usage(existente)
    return {
        "sistema": platform.system(),
        "arquitectura": platform.machine(),
        "cpus_logicas": os.cpu_count(),
        "ram_bytes": ram_total_bytes(),
        "disco_ruta": str(destino),
        "disco_libre_bytes": disco.free,
        "disco_total_bytes": disco.total,
        "motor": "NumPy / CPU (sin GPU automática)",
    }


def recomendar_tamano(ram_bytes=None, fraccion=0.25):
    """Selecciona perfil según memoria mínima estimada, dejando margen.

    Estimación de entrenamiento: 16 bytes por parámetro (float32, gradiente,
    AdamW m/v). Multiplicador adicional para activaciones y runtime.
    No garantiza que el perfil quepa durante el entrenamiento.
    """
    if ram_bytes is None:
        ram_bytes = ram_total_bytes()
    if ram_bytes is None or ram_bytes <= 0:
        return "mini"
    elegible = "mini"
    for tamano, perfil in config.TAMANOS_NUCLEO.items():
        estimacion = config.estimar_parametros(perfil) * 16 * 3
        if estimacion <= ram_bytes * fraccion:
            elegible = tamano
    return elegible
