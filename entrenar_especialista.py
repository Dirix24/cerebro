"""Entrena y certifica un cabezal de intención separado del checkpoint del alumno."""
import argparse
import json

from core.checkpoint import cargar_checkpoint
from core.especialista_escritorio import entrenar


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--origen", default="checkpoints/best.npz")
    cli.add_argument("--salida", required=True)
    cli.add_argument("--ejecutar", action="store_true")
    args = cli.parse_args()
    if not args.ejecutar:
        cli.error("Confirma el ensayo aislado con --ejecutar.")
    modelo = cargar_checkpoint(args.origen, con_optimizador=False)["modelo"]
    print(json.dumps(entrenar(modelo, args.salida), ensure_ascii=False, indent=2))
