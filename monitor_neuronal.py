"""Monitor local de pesos neuronales propios en checkpoints NumPy.

No interpreta pensamientos ni inventa activaciones. El análisis de atención
requiere instrumentar el forward del modelo en una fase posterior.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def inspeccionar_pesos(ruta, max_tensores=30):
    if not isinstance(max_tensores, int) or not 1 <= max_tensores <= 200:
        raise ValueError("max_tensores fuera de rango")
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe checkpoint: {ruta}")
    if ruta.stat().st_size > 1_000_000_000:
        raise ValueError("Checkpoint demasiado grande para inspección")
    resultado = []
    with np.load(ruta, allow_pickle=False) as datos:
        for nombre in sorted(datos.files):
            if len(resultado) >= max_tensores:
                break
            tensor = datos[nombre]
            if tensor.dtype.kind not in "fiu" or tensor.size == 0:
                continue
            if tensor.ndim == 0:
                continue
            # Estadísticas de pesos reales, no de activaciones neuronales.
            if not np.isfinite(tensor).all():
                continue
            resultado.append({
                "tensor": nombre,
                "forma": list(tensor.shape),
                "media": float(np.mean(tensor, dtype=np.float64)),
                "desviacion": float(np.std(tensor, dtype=np.float64)),
                "magnitud_maxima": float(np.max(np.abs(tensor))),
            })
    return resultado


def main():
    ap = argparse.ArgumentParser(description="Monitor de pesos propios de Cerebro")
    ap.add_argument("--ckpt", default="checkpoints/best.npz")
    ap.add_argument("--max-tensores", type=int, default=30)
    args = ap.parse_args()
    try:
        datos = inspeccionar_pesos(args.ckpt, args.max_tensores)
    except (OSError, ValueError) as exc:
        ap.exit(1, f"Error: {exc}\n")
    print(json.dumps(datos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
