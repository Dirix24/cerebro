"""Historial local JSONL con rutas confinadas y entradas limitadas."""
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_TEXTO = 4000
MAX_LINEA = 10000


def guardar(ruta, rol, texto):
    if rol not in ("usuario", "cerebro"):
        raise ValueError("Rol no permitido")
    if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_TEXTO:
        raise ValueError("Texto vacío o demasiado largo")
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    entrada = {"fecha": datetime.now(timezone.utc).isoformat(),
               "rol": rol, "texto": texto}
    with destino.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return entrada


def consultar(ruta, limite=30):
    if not isinstance(limite, int) or not 1 <= limite <= 200:
        raise ValueError("Límite fuera de rango")
    origen = Path(ruta)
    if not origen.is_file():
        return []
    # Lectura acotada: evita cargar un historial arbitrariamente grande.
    with origen.open("rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - 2_000_000))
        if tam > 2_000_000:
            f.readline()
        lineas = f.readlines()
    resultado = []
    for linea in lineas[-limite:]:
        if len(linea) > MAX_LINEA:
            continue
        try:
            entrada = json.loads(linea)
        except (ValueError, UnicodeError):
            continue
        if (isinstance(entrada, dict) and entrada.get("rol") in ("usuario", "cerebro")
                and isinstance(entrada.get("texto"), str)):
            resultado.append(entrada)
    return resultado
