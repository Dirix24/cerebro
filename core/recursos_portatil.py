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
