"""Entrenamiento local explícito, con candidatos separados de los checkpoints base."""
from argparse import ArgumentParser
import json

from core.alumno_supervisado import entrenar, retroceder
from core.profesor_local import ProfesorLocal
from universe.nucleo import Nucleo


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--retroceder", action="store_true")
    args = parser.parse_args()
    nucleo = Nucleo("local")
    profesor = ProfesorLocal.desde_entorno()
    try:
        nucleo.exigir_permisos("READ", "WRITE")
        if args.retroceder:
            print(json.dumps({"activo": retroceder(nucleo.raiz_alumno)}))
            return 0
        informe = entrenar(profesor, nucleo.raiz_alumno)
        print(json.dumps(informe, ensure_ascii=False, indent=2))
        return 0 if informe["promovido"] else 2
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Entrenamiento detenido: {error}")
        return 1
    finally:
        if hasattr(profesor, "cerrar"):
            profesor.cerrar()
        nucleo.ejecutor.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
