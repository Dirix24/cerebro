"""Prepara un proyecto MicroPython sin ejecutar ni flashear una placa."""
from pathlib import Path
import re

import config

_NOMBRE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
_PLACAS = {"esp32", "rp2040"}


def preparar_robot(nombre, placa, codigo, raiz=None):
    if not _NOMBRE.fullmatch(nombre):
        raise ValueError("Nombre de proyecto inválido.")
    if placa not in _PLACAS:
        raise ValueError("Placa no admitida; opciones: esp32, rp2040.")
    if not isinstance(codigo, str) or not codigo.strip() or len(codigo) > 100_000:
        raise ValueError("Código vacío o demasiado grande.")
    # Se conserva el código del usuario sin transformarlo automáticamente.
    base = Path(raiz or config.WORKSPACE_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    destino = base / nombre
    destino.mkdir()  # Nunca sobrescribir un proyecto.
    (destino / "main.py").write_text(codigo, encoding="utf-8")
    (destino / "README.md").write_text(
        f"# {nombre}\n\nPlaca objetivo declarada: {placa}.\n\n"
        "Proyecto MicroPython sin verificar en hardware. Revisa pines, "
        "alimentación, motores y parada de emergencia antes de cargarlo.\n"
        "Cerebro no ha compilado, ejecutado ni instalado este código.\n",
        encoding="utf-8")
    return {"ruta": str(destino), "placa_declarada": placa,
            "archivos": ["main.py", "README.md"], "flasheado": False,
            "validado_en_placa": False}
