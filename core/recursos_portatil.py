"""Política conservadora para entrenamiento en portátil Linux."""
from pathlib import Path


def bateria_baja(base=Path("/sys/class/power_supply"), umbral=25):
    """Solo pausa si se detecta batería descargándose bajo el umbral."""
    base = Path(base)
    if not base.is_dir():
        return False
    for bateria in base.glob("BAT*"):
        try:
            estado = (bateria / "status").read_text().strip().lower()
            capacidad = int((bateria / "capacity").read_text().strip())
        except (OSError, ValueError):
            continue
        if estado == "discharging" and capacidad < umbral:
            return True
    return False


def memoria_disponible_mb(ruta=Path("/proc/meminfo")):
    try:
        for linea in Path(ruta).read_text().splitlines():
            if linea.startswith("MemAvailable:"):
                return int(linea.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def temperatura_maxima_c(base=Path("/sys/class/thermal")):
    temperaturas = []
    for ruta in Path(base).glob("thermal_zone*/temp"):
        try:
            valor = int(ruta.read_text().strip())
            if 0 < valor < 150000:
                temperaturas.append(valor / 1000)
        except (OSError, ValueError):
            pass
    return max(temperaturas) if temperaturas else None


def motivos_pausa(minimo_ram_mb=512, temperatura_limite_c=85,
                  bateria=None, memoria=None, temperatura=None):
    """Regla conservadora: si hay telemetría, no entrenar con recursos críticos."""
    bateria = bateria_baja() if bateria is None else bateria
    memoria = memoria_disponible_mb() if memoria is None else memoria
    temperatura = temperatura_maxima_c() if temperatura is None else temperatura
    motivos = []
    if bateria:
        motivos.append("batería baja")
    if memoria is not None and memoria < minimo_ram_mb:
        motivos.append("memoria disponible insuficiente")
    if temperatura is not None and temperatura >= temperatura_limite_c:
        motivos.append("temperatura elevada")
    return motivos
